"""LLM-as-judge 反问质量评估（v3.5）。

设计：
- 强模型（gpt-4 / Claude / DeepSeek-R1）作为 judge
- 评分维度：启发性 1-5 + 跨阶段一致性 pass/fail + 是否触及核心维度 pass/fail
- 连续 3 次取众数（缓解 LLM 抖动）
- LLM 不可用时降级到规则评估

API:
- evaluate_with_judge(question, student_context, expected_dimensions, judge_model=None)
  -> JudgeScore
- batch_evaluate_benchmark(benchmark_path, judge_model=None) -> Dict[str, Any]
- compare_judge_vs_human(judge_results, human_labels) -> Dict[str, Any]
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class JudgeScore:
    inspirational_score: float = 0.0       # 1-5（连续值，3 次众数）
    cross_stage_consistent: bool = False
    touches_core_dimensions: bool = False
    rationale: str = ""
    method: str = "rule"                    # "llm" | "rule"
    raw_runs: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def total(self) -> float:
        """合成总分（0-100，启发性占 60%，一致性 + 核心维度各 20%）。"""
        ins = max(0, min(5, self.inspirational_score)) * 12   # 60 max
        consist = 20 if self.cross_stage_consistent else 0
        core = 20 if self.touches_core_dimensions else 0
        return round(ins + consist + core, 1)

    @property
    def grade(self) -> str:
        t = self.total
        if t >= 80:
            return "优秀"
        if t >= 60:
            return "合格"
        return "不足"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

JUDGE_PROMPT_TEMPLATE = """\
你是研究方法学专家，正在评估一个 AI 苏格拉底反问的质量。
学生处于「选题漏斗」的某个阶段，AI 应该用反问帮助学生想清楚研究问题。

# 学生上下文
{student_context}

# 期望反问触及的核心维度
{dimensions}

# AI 实际反问
"{question}"

# 你的任务
严格按以下三项评估，输出 JSON 对象：
1. inspirational_score（1-5 整数）：启发性 — 反问是否引导学生深入思考？是否引用学生表述的具体词？
2. cross_stage_consistent（true/false）：跨阶段一致性 — 反问是否聚焦当前阶段，未退行也未跨越？
3. touches_core_dimensions（true/false）：是否触及上述期望维度的至少一项？

输出格式（严格 JSON，不要 markdown 代码块）：
{{
  "inspirational_score": <int>,
  "cross_stage_consistent": <true|false>,
  "touches_core_dimensions": <true|false>,
  "rationale": "<≤60 字简短理由>"
}}
"""


def evaluate_with_judge(
    question: str,
    student_context: str,
    expected_dimensions: List[str],
    *,
    judge_model: Optional[str] = None,
    n_runs: int = 3,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
) -> JudgeScore:
    """用强模型评估反问质量。LLM 不可用时降级规则评估。"""
    # 尝试 LLM
    try:
        from src.llm_gateway import LLMUnavailableError, is_llm_available, llm_chat

        if not is_llm_available(llm_config):
            return _rule_evaluate(question)

        prompt = JUDGE_PROMPT_TEMPLATE.format(
            student_context=student_context or "（未提供）",
            dimensions="；".join(expected_dimensions) if expected_dimensions else "（未指定）",
            question=question,
        )
        messages = [
            {"role": "system", "content": "你是严谨的研究方法学评估专家。"},
            {"role": "user", "content": prompt},
        ]

        runs: List[Dict[str, Any]] = []
        for _ in range(max(1, n_runs)):
            try:
                response = llm_chat(
                    messages,
                    model=judge_model,
                    temperature=0.1,
                    llm_config=llm_config,
                    requests_module=requests_module,
                    retries=0,
                )
                if response.ok:
                    parsed = _safe_parse_judge_json(response.content)
                    if parsed:
                        runs.append(parsed)
            except (LLMUnavailableError, Exception):
                continue

        if not runs:
            return _rule_evaluate(question)

        # 取 3 次的众数（启发性中位数 + 布尔字段多数）
        ins_scores = [r.get("inspirational_score", 0) for r in runs]
        try:
            ins_mode = statistics.median(ins_scores)
        except statistics.StatisticsError:
            ins_mode = 0
        consist_votes = [bool(r.get("cross_stage_consistent")) for r in runs]
        consist_mode = sum(consist_votes) >= len(consist_votes) / 2
        core_votes = [bool(r.get("touches_core_dimensions")) for r in runs]
        core_mode = sum(core_votes) >= len(core_votes) / 2
        # 选最长的 rationale
        rationale = max((r.get("rationale", "") for r in runs), key=len, default="")

        return JudgeScore(
            inspirational_score=float(ins_mode),
            cross_stage_consistent=consist_mode,
            touches_core_dimensions=core_mode,
            rationale=rationale[:120],
            method="llm",
            raw_runs=runs,
        )
    except Exception:
        return _rule_evaluate(question)


def _safe_parse_judge_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = text.strip()
    # 去 markdown
    if cleaned.startswith("```"):
        first_nl = cleaned.find("\n")
        if first_nl > 0:
            cleaned = cleaned[first_nl + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -3]
    cleaned = cleaned.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(cleaned[start: end + 1])
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# 规则评估（降级）
# ---------------------------------------------------------------------------

_HEURISTIC_KEYWORDS = ["具体", "为什么", "如果", "什么", "哪", "怎样", "怎么"]


def _rule_evaluate(question: str) -> JudgeScore:
    """LLM 不可用时的规则评估。"""
    if not question:
        return JudgeScore(method="rule", rationale="空反问")

    q = question.strip()
    has_question_mark = "?" in q or "？" in q
    has_keyword = any(k in q for k in _HEURISTIC_KEYWORDS)
    is_short = len(q) < 30
    is_long = len(q) > 150

    # 启发性评分
    ins = 3
    if has_question_mark and has_keyword and not is_short and not is_long:
        ins = 4
    if has_question_mark and has_keyword and len(q) >= 50:
        ins = 5
    if is_short or not has_question_mark:
        ins = max(1, ins - 2)
    if not has_keyword:
        ins = max(1, ins - 1)

    return JudgeScore(
        inspirational_score=float(ins),
        cross_stage_consistent=has_question_mark,    # 规则无法判断阶段，保守 OK
        touches_core_dimensions=has_keyword,
        rationale=f"规则评估：长度 {len(q)}，含问号={has_question_mark}，含启发词={has_keyword}",
        method="rule",
    )


# ---------------------------------------------------------------------------
# 批量评估 + 与人工对比
# ---------------------------------------------------------------------------

def batch_evaluate_benchmark(
    benchmark_data: Dict[str, Any],
    questions_by_case: Dict[str, str],
    *,
    judge_model: Optional[str] = None,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
    n_runs: int = 3,
) -> Dict[str, Any]:
    """对 benchmark fixture 中的所有案例批量评估。

    Args:
        benchmark_data: 加载自 socratic_benchmark.json 的 dict
        questions_by_case: {case_id: ai_question}（先跑过反问的输出）

    Returns:
        {"results": [...{case_id, judge_score, ...}], "method_summary": {...}}
    """
    results: List[Dict[str, Any]] = []
    method_count = {"llm": 0, "rule": 0}

    for stage_str, cases in (benchmark_data.get("stages") or {}).items():
        for case in cases:
            cid = case.get("id", "")
            question = questions_by_case.get(cid, "")
            student_ctx = case.get("input", "")
            dims = case.get("expected_dimensions", []) or []
            score = evaluate_with_judge(
                question, student_ctx, dims,
                judge_model=judge_model,
                n_runs=n_runs,
                llm_config=llm_config,
                requests_module=requests_module,
            )
            method_count[score.method] = method_count.get(score.method, 0) + 1
            results.append({
                "case_id": cid,
                "stage": int(stage_str),
                "input": student_ctx,
                "ai_question": question,
                "judge": score.as_dict(),
            })
    return {"results": results, "method_summary": method_count}


def compare_judge_vs_human(
    judge_results: List[Dict[str, Any]],
    human_labels: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """与人工标注比对，计算一致性比例。

    human_labels: {case_id: {"manual_score": int, "manual_passes": bool}}
    返回：每个案例的偏差 + 总体一致率。
    """
    matches = 0
    total = 0
    discrepancies: List[Dict[str, Any]] = []
    for r in judge_results:
        cid = r.get("case_id")
        human = human_labels.get(cid)
        if not human:
            continue
        total += 1
        # 比较 inspirational_score 是否在人工 ±1 范围内
        judge_ins = r["judge"].get("inspirational_score", 0)
        human_score = human.get("manual_score") or 0
        diff = abs(float(judge_ins) - float(human_score))
        is_match = diff <= 1
        if is_match:
            matches += 1
        else:
            discrepancies.append({
                "case_id": cid,
                "judge": judge_ins,
                "human": human_score,
                "diff": diff,
            })

    consistency = (matches / total) if total else 0.0
    return {
        "consistency_rate": round(consistency, 3),
        "matches": matches,
        "total": total,
        "discrepancies": discrepancies,
        "needs_human_review": consistency < 0.8,
    }
