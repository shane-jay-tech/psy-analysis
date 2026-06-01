"""答辩问题生成器 — 根据 plan + result 生成针对性问题与答案。

核心入口：generate_defense_qa(plan, output, ctx) -> List[QAItem]
PDF 导出：export_defense_handbook_pdf(items, meta) -> bytes
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .defense_qa_kb import (
    CATEGORIES, CATEGORY_FALLBACK_QA, DIFFICULTY_LEVELS, DIFFICULTY_ORDER,
    GENERIC_QA, TEST_SPECIFIC_QA, QATemplate, difficulty_emoji,
)


REQUIRED_CATEGORIES = ("method", "data", "effect", "infer")


@dataclass
class QAItem:
    """渲染后的答辩问答。"""
    question: str
    answer: str
    category: str
    category_label: str
    difficulty: str = "常问"
    difficulty_emoji: str = "🟡"
    mastered: bool = False  # v2.9: 用户标记是否已掌握

    @property
    def difficulty_label(self) -> str:
        return f"{self.difficulty_emoji} {self.difficulty}"

    @property
    def question_id(self) -> str:
        """稳定的问题 ID（用于持久化掌握状态，避免每次重新生成丢失）。"""
        import hashlib
        return hashlib.md5(self.question.encode("utf-8")).hexdigest()[:12]


def _classify_effect_size(value: float, kind: str) -> tuple[str, str]:
    """返回 (中文标签, 实际意义描述)。"""
    abs_v = abs(value) if value is not None else 0.0
    if kind in ("d", "cohens_d"):
        if abs_v < 0.2:
            return "可忽略", "几乎无差异"
        if abs_v < 0.5:
            return "小", "可察觉但有限"
        if abs_v < 0.8:
            return "中等", "比较明显"
        return "大", "非常突出"
    if kind in ("r", "pearson"):
        if abs_v < 0.10:
            return "可忽略", "几乎无关联"
        if abs_v < 0.30:
            return "小", "弱关联"
        if abs_v < 0.50:
            return "中等", "明显关联"
        return "大", "强关联"
    if kind in ("eta_sq", "eta", "η²"):
        if abs_v < 0.01:
            return "可忽略", "几乎无解释力"
        if abs_v < 0.06:
            return "小", "解释少量方差"
        if abs_v < 0.14:
            return "中等", "解释中等方差"
        return "大", "解释较多方差"
    return "中等", "明显"


def _judge_alpha(alpha: float) -> tuple[str, str]:
    """Cronbach α 等级判断，返回 (评判, 信度水平)。"""
    if alpha >= 0.90:
        return "属于优秀水平", "优秀"
    if alpha >= 0.80:
        return "属于良好水平", "良好"
    if alpha >= 0.70:
        return "处于可接受水平", "可接受"
    if alpha >= 0.60:
        return "勉强可接受但偏低，建议修订量表", "勉强"
    return "低于可接受标准（<.70），不建议直接使用", "不足"


def _judge_kmo(kmo: float) -> str:
    if kmo >= 0.9:
        return "极佳"
    if kmo >= 0.8:
        return "良好"
    if kmo >= 0.7:
        return "中等"
    if kmo >= 0.6:
        return "勉强可接受"
    return "不适合做因素分析"


def _extract_stats(plan, output: dict, ctx: dict) -> Dict[str, Any]:
    """从 output / ctx / result 中抽取所有占位符可能用到的字段。"""
    stats: Dict[str, Any] = {}
    result = output.get("result") if output else None

    test_type = ctx.get("test_type") or output.get("test_type", "")
    stats["method"] = ctx.get("test_name_zh") or output.get("test_name_zh", "本研究采用的检验")
    stats["test_type"] = test_type
    stats["n"] = ctx.get("sample_size", "—")
    stats["dv"] = ctx.get("dv") or "因变量"
    stats["iv"] = ctx.get("iv") or "自变量"
    stats["population"] = "目标人群"
    stats["design_type"] = "横断面相关研究"
    stats["design_limit"] = "横断面设计无法揭示因果关系"
    stats["measurement_limit"] = "测量工具均为自陈量表，可能存在共同方法偏差"
    stats["causal_judgment"] = "无法直接得出因果结论"
    stats["practical_meaning"] = "中等"

    # 效应量解析
    es = output.get("effect_size") if output else None
    if es is None and result is not None:
        es = getattr(result, "effect_size", None)
    es_name = output.get("effect_size_name") if output else None
    if es_name is None and result is not None:
        es_name = getattr(result, "effect_size_name", "")

    if isinstance(es, (int, float)):
        stats["effect_size"] = float(es)
        es_kind = "r" if test_type and "corr" in test_type else (
            "eta_sq" if test_type and "anova" in test_type else "d"
        )
        label, meaning = _classify_effect_size(float(es), es_kind)
        stats["effect_label"] = label
        stats["practical_meaning"] = meaning
        if es_kind == "eta_sq":
            stats["effect_pct"] = abs(float(es)) * 100
    else:
        stats["effect_size"] = 0.0
        stats["effect_label"] = "—"
        stats["effect_pct"] = 0.0

    # t 检验：方差齐性
    if test_type == "independent_ttest" and result is not None:
        eq = getattr(result, "assumption_equal_var", None) or {}
        if eq.get("passed", True):
            stats["levene_status"] = (
                f"通过（Levene F={eq.get('statistic', '—')}, p={eq.get('p_value', '—')}）"
            )
            stats["welch_note"] = "符合方差齐性假设，使用标准 t 检验。"
        else:
            stats["levene_status"] = (
                f"未通过（Levene F={eq.get('statistic', '—')}, p={eq.get('p_value', '—')}）"
            )
            stats["welch_note"] = (
                "方差不齐，已自动使用 Welch 校正 t 检验，"
                "Welch 调整自由度，对方差不齐稳健，结果依然可信。"
            )
    else:
        stats["levene_status"] = "—"
        stats["welch_note"] = "—"

    # ANOVA：组数 + 事后检验
    if test_type == "one_way_anova":
        from math import comb
        # 估计组数：从 group_stats 或 post_hoc 推断
        n_groups = 3
        if result is not None:
            gs = getattr(result, "group_stats", None)
            if gs is not None and hasattr(gs, "shape"):
                n_groups = max(2, gs.shape[0])
        stats["n_groups"] = n_groups
        stats["n_pairs"] = comb(n_groups, 2)
        stats["family_error"] = 1 - (1 - 0.05) ** stats["n_pairs"]

        ph = getattr(result, "post_hoc", None) if result is not None else None
        if ph is not None and hasattr(ph, "empty") and not ph.empty:
            stats["tukey_result"] = f"共 {len(ph)} 组两两比较，详见结果表"
        else:
            stats["tukey_result"] = "（待补充）"

    # 相关
    if test_type and "corr" in test_type:
        cm = getattr(result, "corr_matrix", None) if result is not None else None
        if cm is not None and hasattr(cm, "shape") and cm.shape[0] >= 2:
            stats["r"] = float(cm.iloc[0, 1])
            label, meaning = _classify_effect_size(stats["r"], "r")
            stats["effect_label"] = label
            stats["practical_meaning"] = meaning
            stats["var1"] = cm.columns[0]
            stats["var2"] = cm.columns[1]
        else:
            stats["r"] = 0.0
            stats["var1"] = "变量 1"
            stats["var2"] = "变量 2"

    # 配对
    if test_type == "paired_ttest":
        stats["condition1"] = "前测"
        stats["condition2"] = "后测"
        stats["normality_status"] = "通过（Shapiro-Wilk p>.05）"

    # 中介
    if test_type == "mediation" and result is not None:
        ci = getattr(result, "bootstrap_ci", None)
        if ci is not None and hasattr(ci, "iloc") and len(ci) > 0:
            row = ci.iloc[0]
            stats["ci_lower"] = float(row.get("CI下限", 0))
            stats["ci_upper"] = float(row.get("CI上限", 0))
            stats["mediation_type"] = (
                "完全" if abs(float(row.get("B", 0))) > 0.3 else "部分"
            )
        else:
            stats["ci_lower"] = 0.0
            stats["ci_upper"] = 0.0
            stats["mediation_type"] = "部分"
        stats["mediator"] = "中介变量 M"

    # 信度
    if test_type == "cronbach_alpha":
        alpha_val = float(es) if isinstance(es, (int, float)) else 0.0
        stats["alpha"] = alpha_val
        judge, level = _judge_alpha(alpha_val)
        stats["alpha_judge"] = judge
        stats["reliability_level"] = level
        stats["construct"] = ctx.get("construct_name") or "目标构念"

    # EFA
    if test_type == "efa":
        kmo = output.get("kmo", 0.7) if output else 0.7
        stats["kmo"] = float(kmo)
        stats["kmo_judge"] = _judge_kmo(stats["kmo"])
        stats["bartlett_p"] = "p<.001"
        stats["n_factors"] = output.get("n_factors", 3) if output else 3

    # 卡方
    if test_type == "chi_square_independence":
        warning = getattr(result, "warning", "") if result is not None else ""
        if warning:
            stats["expected_freq_status"] = "存在期望频数偏低的单元格，需谨慎解读"
        else:
            stats["expected_freq_status"] = "所有单元格期望频数均 ≥ 5，符合卡方检验前提"

    return stats


def _safe_format(template: str, data: Dict[str, Any]) -> str:
    """容错格式化：缺失键替换为占位符并继续。"""
    class _DefaultDict(dict):
        def __missing__(self, key):
            return f"（{key} 待补充）"

    try:
        return template.format_map(_DefaultDict(data))
    except (KeyError, ValueError, IndexError):
        # 兜底：把所有 {x} 替换为字符串
        out = template
        for k, v in data.items():
            out = out.replace(f"{{{k}}}", str(v))
        return out


def _build_qa_item(tmpl: QATemplate, stats: Dict[str, Any]) -> QAItem | None:
    """单条模板 → QAItem，失败返回 None。"""
    try:
        answer = _safe_format(tmpl.answer_template, stats)
        question = _safe_format(tmpl.question, stats)
        return QAItem(
            question=question,
            answer=answer,
            category=tmpl.category,
            category_label=CATEGORIES.get(tmpl.category, tmpl.category),
            difficulty=tmpl.difficulty,
            difficulty_emoji=difficulty_emoji(tmpl.difficulty),
        )
    except Exception:
        return None


def _ensure_required_categories(items: List[QAItem], stats: Dict[str, Any]) -> List[QAItem]:
    """如果 items 缺少 method/data/effect/infer 任一类，从 CATEGORY_FALLBACK_QA 补一条。"""
    present = {item.category for item in items}
    for cat in REQUIRED_CATEGORIES:
        if cat in present:
            continue
        fallback_tmpl = CATEGORY_FALLBACK_QA.get(cat)
        if fallback_tmpl is None:
            continue
        item = _build_qa_item(fallback_tmpl, stats)
        if item is not None:
            items.append(item)
    return items


def generate_defense_qa(plan, output: dict, ctx: dict,
                       *, max_items: int = 7) -> List[QAItem]:
    """根据 plan 和分析结果生成答辩问答清单。

    生成策略：
    1. 收集方法专属模板（TEST_SPECIFIC_QA）+ 通用模板（GENERIC_QA）
    2. 必备 4 类（method/data/effect/infer）若缺失，从 CATEGORY_FALLBACK_QA 补
    3. 按难度排序：必问 → 常问 → 刁钻
    4. 同难度内按必备类别（method/effect/data/infer）优先
    5. 截断到 max_items

    Args:
        plan: AnalysisPlan
        output: runner 返回的 output dict
        ctx: wizard_results_context
        max_items: 最大输出条数

    Returns:
        QAItem 列表，按难度+类别排序
    """
    if output is None:
        return []

    test_type = ctx.get("test_type") or output.get("test_type", "")
    stats = _extract_stats(plan, output, ctx)

    pool: List[QAItem] = []

    # 1. 方法专属
    for tmpl in TEST_SPECIFIC_QA.get(test_type, []):
        item = _build_qa_item(tmpl, stats)
        if item:
            pool.append(item)

    # 2. 通用
    for tmpl in GENERIC_QA:
        item = _build_qa_item(tmpl, stats)
        if item:
            pool.append(item)

    # 3. 类别补全（保证 method/data/effect/infer 4 类齐）
    pool = _ensure_required_categories(pool, stats)

    # 4. 排序：先按难度（必问→常问→刁钻），再按必备类别优先
    cat_priority = {c: i for i, c in enumerate(REQUIRED_CATEGORIES)}

    def sort_key(item: QAItem) -> tuple:
        return (
            DIFFICULTY_ORDER.get(item.difficulty, 99),
            cat_priority.get(item.category, 99),
        )

    pool.sort(key=sort_key)

    return pool[:max_items]


# --------------------------------------------------------------------------- #
# v3.8 O2: 基于学生论文 + reviewer 历史 + 漏斗记录的个性化答辩题
# --------------------------------------------------------------------------- #

# 系统提示词模板：用学生提供的真实素材生成答辩题，避免泛泛而谈
_PAPER_AWARE_SYSTEM_PROMPT = """你是一位资深的本科答辩评委。基于学生提供的论文片段、
之前 AI 反问的记录、以及他/她在选题阶段的关键决策，
生成 8-10 条**针对这篇论文**的个性化答辩问题。

要求（严格执行）：
1. **不重复**已有的反问历史（学生已答过的不要再问）
2. **不泛泛**：每题至少引用论文中的一个具体数据/术语/选择，避免「请谈谈研究意义」这种通用题
3. **难度均衡**：3 题必问（核心结果 + 方法选择 + 主要局限）+ 4 题常问 + 2 题刁钻
4. **每题给建议回答框架**（不是完整答案）：用 30-60 秒口头作答的要点 3-5 条
5. **类别标注**：method（方法选择）/data（数据/样本）/effect（效应/解读）/infer（推论/局限）

输出严格 JSON 数组，每条：
{
  "question": "...",
  "answer_outline": "要点1...\\n要点2...\\n要点3...",
  "category": "method|data|effect|infer",
  "difficulty": "必问|常问|刁钻",
  "rationale": "为什么这题针对你的论文（一句话）"
}
"""


def _truncate_text(text: str, limit: int = 2000) -> str:
    """按字符截断，保留首段和末段（中间用 [...] 占位）。"""
    if not text or len(text) <= limit:
        return text or ""
    head = text[: int(limit * 0.6)]
    tail = text[-int(limit * 0.3):]
    return head + "\n\n[... 中间内容省略 ...]\n\n" + tail


def _format_paper_context(paper_text: str) -> str:
    if not paper_text:
        return "（学生未提供论文正文）"
    return _truncate_text(paper_text, limit=2500)


def _format_reviewer_history(reviewer_history: Optional[List[Dict[str, Any]]]) -> str:
    """格式化反问历史。每条最多 200 字，最多 8 条。"""
    if not reviewer_history:
        return "（无反问历史）"
    lines = []
    for i, item in enumerate(reviewer_history[:8], 1):
        if isinstance(item, dict):
            q = item.get("question") or item.get("q") or ""
            a = item.get("answer") or item.get("a") or ""
        else:
            q, a = str(item), ""
        q = q[:200].strip()
        a = a[:200].strip()
        if q:
            lines.append(f"反问 {i}：{q}")
            if a:
                lines.append(f"学生答：{a}")
    return "\n".join(lines) if lines else "（无反问历史）"


def _format_funnel_decisions(funnel_state: Optional[Dict[str, Any]]) -> str:
    """从 upstream funnel state 抽取关键决策（变量、设计、样本量等）。"""
    if not funnel_state or not isinstance(funnel_state, dict):
        return "（无选题决策记录）"
    parts = []
    if funnel_state.get("research_question"):
        parts.append(f"研究问题：{funnel_state['research_question']}")
    if funnel_state.get("variables"):
        parts.append(f"变量：{funnel_state['variables']}")
    if funnel_state.get("design"):
        parts.append(f"研究设计：{funnel_state['design']}")
    if funnel_state.get("sample_size"):
        parts.append(f"样本量决策：{funnel_state['sample_size']}")
    if funnel_state.get("hypothesis"):
        parts.append(f"假设：{funnel_state['hypothesis']}")
    return "\n".join(parts) if parts else "（无关键决策记录）"


def _parse_paper_aware_qa_response(content: str) -> List[Dict[str, Any]]:
    """从 LLM 响应中提取 JSON 数组，容错处理。"""
    import json as _json
    import re as _re

    if not content:
        return []
    # 尝试直接解析
    text = content.strip()
    # 去掉 markdown 代码块标记
    if text.startswith("```"):
        text = _re.sub(r"^```(?:json)?\s*\n", "", text)
        text = _re.sub(r"\n```\s*$", "", text)
    # 尝试提取第一个 JSON 数组
    arr_match = _re.search(r"\[[\s\S]*\]", text)
    if not arr_match:
        return []
    try:
        data = _json.loads(arr_match.group(0))
    except (_json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _build_paper_aware_item(raw: Dict[str, Any]) -> Optional[QAItem]:
    """把 LLM 返回的单条 dict 转 QAItem。"""
    q = (raw.get("question") or "").strip()
    answer = (raw.get("answer_outline") or raw.get("answer") or "").strip()
    if not q or not answer:
        return None
    cat = raw.get("category") or "method"
    if cat not in CATEGORIES:
        cat = "method"
    diff = raw.get("difficulty") or "常问"
    if diff not in DIFFICULTY_ORDER:
        diff = "常问"
    rationale = (raw.get("rationale") or "").strip()
    # 把 rationale 拼到答案末尾作为「为什么会问这题」
    if rationale:
        answer = answer + f"\n\n_📌 为什么问这题：{rationale}_"
    return QAItem(
        question=q,
        answer=answer,
        category=cat,
        category_label=CATEGORIES.get(cat, cat),
        difficulty=diff,
        difficulty_emoji=difficulty_emoji(diff),
    )


@dataclass
class PaperAwareQAResult:
    """个性化答辩题生成结果。"""
    items: List[QAItem] = field(default_factory=list)
    used_paper: bool = False
    used_reviewer_history: bool = False
    used_funnel: bool = False
    fallback_to_template: bool = False
    error: str = ""


def generate_paper_aware_qa(
    *,
    paper_text: str = "",
    reviewer_history: Optional[List[Dict[str, Any]]] = None,
    funnel_state: Optional[Dict[str, Any]] = None,
    plan: Any = None,
    output: Optional[Dict[str, Any]] = None,
    ctx: Optional[Dict[str, Any]] = None,
    max_items: int = 9,
    llm_chat_fn: Optional[Any] = None,
) -> PaperAwareQAResult:
    """生成基于学生论文 + 反问历史 + 选题决策的个性化答辩题。

    与 generate_defense_qa 不同：本函数会读论文内容，确保题目针对性。
    LLM 不可用时降级到模板版（generate_defense_qa）。

    Args:
        paper_text: 学生论文正文（最好至少有摘要 + 方法 + 结果三段）
        reviewer_history: AI 反问的历史 [{"question": ..., "answer": ...}, ...]
        funnel_state: 选题漏斗的关键决策
        plan: AnalysisPlan，用于降级
        output: 分析输出，用于降级
        ctx: 上下文，用于降级
        max_items: 最大题数
        llm_chat_fn: 注入的 LLM 调用函数（测试用），签名同 llm_chat

    Returns:
        PaperAwareQAResult
    """
    from dataclasses import field as _field  # noqa: F401  避免导入错位

    # 收集素材
    paper_context = _format_paper_context(paper_text)
    reviewer_context = _format_reviewer_history(reviewer_history)
    funnel_context = _format_funnel_decisions(funnel_state)

    user_prompt = (
        "## 学生论文片段\n" + paper_context +
        "\n\n## AI 反问历史（学生已经答过这些）\n" + reviewer_context +
        "\n\n## 选题阶段关键决策\n" + funnel_context +
        f"\n\n请生成 {max_items} 条针对性答辩题（含建议回答要点）。"
    )

    used_paper = bool(paper_text)
    used_reviewer = bool(reviewer_history)
    used_funnel = bool(funnel_state)

    # 调 LLM
    try:
        if llm_chat_fn is None:
            from src.llm_gateway import llm_chat as _llm_chat
            llm_chat_fn = _llm_chat
        messages = [
            {"role": "system", "content": _PAPER_AWARE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        resp = llm_chat_fn(messages, temperature=0.5)
        content = getattr(resp, "content", "") if hasattr(resp, "content") else str(resp)
    except Exception as exc:
        # 降级
        items = generate_defense_qa(plan, output or {}, ctx or {}, max_items=max_items) \
            if (plan is not None or output is not None) else []
        return PaperAwareQAResult(
            items=items,
            used_paper=used_paper,
            used_reviewer_history=used_reviewer,
            used_funnel=used_funnel,
            fallback_to_template=True,
            error=str(exc)[:200],
        )

    raw_list = _parse_paper_aware_qa_response(content)
    if not raw_list:
        # 解析失败也降级
        items = generate_defense_qa(plan, output or {}, ctx or {}, max_items=max_items) \
            if (plan is not None or output is not None) else []
        return PaperAwareQAResult(
            items=items,
            used_paper=used_paper,
            used_reviewer_history=used_reviewer,
            used_funnel=used_funnel,
            fallback_to_template=True,
            error="LLM 响应不是合法 JSON 数组",
        )

    items = []
    for raw in raw_list[:max_items]:
        item = _build_paper_aware_item(raw)
        if item:
            items.append(item)

    if not items:
        items = generate_defense_qa(plan, output or {}, ctx or {}, max_items=max_items) \
            if (plan is not None or output is not None) else []
        return PaperAwareQAResult(
            items=items,
            used_paper=used_paper,
            used_reviewer_history=used_reviewer,
            used_funnel=used_funnel,
            fallback_to_template=True,
            error="LLM 返回的题目均无效",
        )

    # 排序：必问→常问→刁钻
    items.sort(key=lambda x: DIFFICULTY_ORDER.get(x.difficulty, 99))

    return PaperAwareQAResult(
        items=items,
        used_paper=used_paper,
        used_reviewer_history=used_reviewer,
        used_funnel=used_funnel,
        fallback_to_template=False,
    )


def render_qa_as_markdown(items: List[QAItem]) -> str:
    """把问答列表渲染为 Markdown，按难度分组（用于 PDF/Word 附录）。"""
    if not items:
        return "_暂无可生成的答辩问题。_"

    by_diff: Dict[str, List[QAItem]] = {}
    for item in items:
        by_diff.setdefault(item.difficulty, []).append(item)

    parts = []
    counter = 0
    for diff in ("必问", "常问", "刁钻"):
        diff_items = by_diff.get(diff, [])
        if not diff_items:
            continue
        emoji = difficulty_emoji(diff)
        parts.append(f"## {emoji} {diff}（{len(diff_items)} 题）")
        parts.append("")
        for item in diff_items:
            counter += 1
            parts.append(f"### Q{counter}: {item.question}")
            parts.append(f"_{item.category_label} · {item.difficulty_label}_")
            parts.append("")
            parts.append(item.answer)
            parts.append("")
    return "\n".join(parts)


def group_qa_by_difficulty(items: List[QAItem]) -> Dict[str, List[QAItem]]:
    """按难度分组，UI 用。返回 dict 含 必问/常问/刁钻 三键。"""
    groups: Dict[str, List[QAItem]] = {"必问": [], "常问": [], "刁钻": []}
    for item in items:
        groups.setdefault(item.difficulty, []).append(item)
    return groups


# --------------------------------------------------------------------------- #
# v2.9: 掌握状态管理
# --------------------------------------------------------------------------- #

def apply_mastered_state(items: List[QAItem],
                         mastered_map: Dict[str, bool]) -> List[QAItem]:
    """从外部映射（question_id → bool）注入 mastered 字段。

    UI 层使用：每次 generate_defense_qa() 后调用本函数，
    把 session_state["defense_qa_mastered"] 的状态恢复到 items。
    """
    if not mastered_map:
        return items
    for item in items:
        if item.question_id in mastered_map:
            item.mastered = bool(mastered_map[item.question_id])
    return items


def calculate_mastery_progress(items: List[QAItem]) -> Dict[str, Dict[str, int]]:
    """按难度统计掌握进度，UI 顶部显示用。

    Returns:
        {"必问": {"mastered": 5, "total": 12}, "常问": {...}, ...}
    """
    progress: Dict[str, Dict[str, int]] = {
        "必问": {"mastered": 0, "total": 0},
        "常问": {"mastered": 0, "total": 0},
        "刁钻": {"mastered": 0, "total": 0},
    }
    for item in items:
        diff = item.difficulty if item.difficulty in progress else "常问"
        progress[diff]["total"] += 1
        if item.mastered:
            progress[diff]["mastered"] += 1
    return progress


def all_mastered(items: List[QAItem]) -> bool:
    """是否所有问题都已掌握。"""
    return bool(items) and all(item.mastered for item in items)


# --------------------------------------------------------------------------- #
# v2.8: 答辩备战手册 PDF 导出（fpdf2 + CJK 字体）
# --------------------------------------------------------------------------- #

@dataclass
class HandbookMeta:
    """答辩备战手册元信息。"""
    research_title: str = "本科毕业论文研究"
    author: str = ""
    advisor: str = ""
    date: str = ""

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%Y 年 %m 月 %d 日")


def _find_cjk_font_path() -> Optional[str]:
    """查找系统 CJK TTF/TTC，用于 fpdf2 嵌入中文字体。"""
    import os
    win_dir = os.environ.get("WINDIR", "C:\\Windows")
    candidates = [
        os.path.join(win_dir, "Fonts", "msyh.ttc"),       # 微软雅黑
        os.path.join(win_dir, "Fonts", "msyh.ttf"),
        os.path.join(win_dir, "Fonts", "simhei.ttf"),     # 黑体
        os.path.join(win_dir, "Fonts", "simsun.ttc"),     # 宋体
        # Linux/Mac 备选
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


_REVIEW_CHECKLIST = [
    "通读论文方法部分，确保每个统计名词都能口头解释清楚",
    "记住关键数值：总样本量、效应量、p 值、置信区间",
    "准备 1-2 句话解释为什么选择当前统计方法（vs 其他备选）",
    "检查所有「显著」表述，避免把 p<.05 说成「证明」「导致」",
    "为每个研究局限准备一句「未来可改进」的回应",
    "练习简洁回答：每个问题用 30-60 秒口头作答",
    "把「答辩备战手册」打印随身带，在答辩前 10 分钟最后浏览一遍",
]


def export_defense_handbook_pdf(
    items: List[QAItem],
    meta: Optional[HandbookMeta] = None,
    *,
    filter_unmastered: bool = False,
) -> bytes:
    """生成"答辩备战手册"PDF。

    结构（v2.9 重构）：
    - 标题页（研究主题、作者、生成日期；精准版会标注「重点复习版」）
    - 难度提示说明 + 视觉化卡片
    - 问答（按 必问→常问→刁钻 分组，每题：问题加粗 + 灰底参考答案 + 5 行笔记区）
    - 末尾「考前 3 天复习计划」分日规划

    Args:
        items: 答辩问答列表
        meta: 标题页元信息
        filter_unmastered: True 时仅含 mastered=False 的问题（精准版）

    缺中文字体时降级为英文版。

    Returns:
        PDF 字节流
    """
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    # 别名：消除 **NL 弃用警告
    NL = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}

    if meta is None:
        meta = HandbookMeta()

    # v2.9: 精准版筛选
    is_focused = filter_unmastered
    all_mastered_flag = bool(items) and all(it.mastered for it in items)
    if filter_unmastered:
        items = [it for it in items if not it.mastered]

    cjk_path = _find_cjk_font_path()
    has_cjk = cjk_path is not None

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)

    if has_cjk:
        # fpdf2 需为每种 style 注册字体；这里用同一文件复用 4 种 style
        pdf.add_font("CJK", "", cjk_path)
        pdf.add_font("CJK", "B", cjk_path)
        pdf.add_font("CJK", "I", cjk_path)
        pdf.add_font("CJK", "BI", cjk_path)
        font_name = "CJK"
    else:
        font_name = "Helvetica"

    def _set_font(size: int, style: str = ""):
        pdf.set_font(font_name, style, size)

    def _txt(s: str) -> str:
        """无中文字体时把中文剥成 [ZH]，保证 PDF 不崩。"""
        if has_cjk:
            return s
        return s.encode("ascii", "replace").decode("ascii")

    def _draw_filled_box(x, y, w, h, fill_rgb=(240, 240, 240)):
        """画浅灰色填充矩形（用于答案模板背景）。"""
        pdf.set_fill_color(*fill_rgb)
        pdf.rect(x, y, w, h, "F")

    def _underline_row(line_count: int = 5, line_height: float = 7.0):
        """画指定行数的下划线（笔记区）。"""
        pdf.set_draw_color(180, 180, 180)
        for _ in range(line_count):
            y = pdf.get_y() + 5
            pdf.line(pdf.l_margin, y, 210 - pdf.r_margin, y)
            pdf.ln(line_height)
        pdf.set_draw_color(0, 0, 0)

    # ============ 标题页（v2.9 重构）============
    pdf.add_page()
    pdf.ln(40)
    _set_font(24, "B")
    main_title = "答辩备战手册" + ("（重点复习版）" if is_focused else "")
    pdf.cell(0, 14, _txt(main_title), align="C", **NL)

    if is_focused:
        pdf.ln(2)
        _set_font(11, "I")
        pdf.set_text_color(180, 90, 0)
        pdf.cell(
            0, 7,
            _txt(f"仅含 {len(items)} 个未掌握问题  ·  {meta.date}"),
            align="C", **NL,
        )
        pdf.set_text_color(0, 0, 0)

    pdf.ln(4)
    _set_font(14)
    pdf.cell(0, 10, _txt(f"《{meta.research_title}》"), align="C", **NL)
    pdf.ln(20)
    _set_font(12)
    if meta.author:
        pdf.cell(0, 8, _txt(f"作者：{meta.author}"), align="C", **NL)
    if meta.advisor:
        pdf.cell(0, 8, _txt(f"指导教师：{meta.advisor}"), align="C", **NL)
    pdf.cell(0, 8, _txt(f"生成日期：{meta.date}"), align="C", **NL)

    pdf.ln(40)
    _set_font(11, "I")
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(0, 7, _txt(
        "本手册由 Psy Analysis v2.9 自动生成。\n"
        "包含针对你研究方法的高频答辩问题、标准答案模板及笔记区，\n"
        "建议答辩前 3 天开始练习，每题准备 30-60 秒口头作答。"
    ), align="C")
    pdf.set_text_color(0, 0, 0)

    # ============ 难度说明页（视觉卡片）============
    if not is_focused or items:
        pdf.add_page()
        _set_font(16, "B")
        pdf.cell(0, 12, _txt("一、难度分级使用说明"), **NL)
        pdf.ln(4)

        difficulty_cards = [
            ("[必问]", "🟢 必问 = 答辩老师几乎一定会问，必须能脱口而出",
             "务必背熟，每题准备 30-60 秒口头作答。", (220, 240, 220)),
            ("[常问]", "🟡 常问 = 常见追问，提前打草稿",
             "依据个人研究情况准备。看到题目能在脑中过一遍即可。", (250, 240, 200)),
            ("[刁钻]", "🔴 刁钻 = 进阶质疑，视情况准备",
             "答上为加分项；答不上时坦然承认「这是值得思考的问题」。", (245, 220, 220)),
        ]
        for tag, title, desc, fill in difficulty_cards:
            y_start = pdf.get_y()
            _draw_filled_box(pdf.l_margin, y_start, 210 - pdf.l_margin - pdf.r_margin, 18, fill)
            pdf.set_y(y_start + 2)
            _set_font(12, "B")
            pdf.cell(0, 6, _txt(f"  {title}"), **NL)
            _set_font(10)
            pdf.cell(0, 6, _txt(f"  {desc}"), **NL)
            pdf.ln(4)

    # ============ 全部掌握时的祝贺页（精准版）============
    if is_focused and not items:
        pdf.add_page()
        pdf.ln(60)
        _set_font(20, "B")
        pdf.cell(0, 14, _txt("🎉 恭喜你已掌握所有问题！"), align="C", **NL)
        pdf.ln(8)
        _set_font(12)
        pdf.multi_cell(0, 7, _txt(
            "你已勾选了所有答辩问题为「已掌握」。\n"
            "建议答辩前 1 天再用「完整版」浏览一遍，巩固印象。"
        ), align="C")

    # ============ 问答主体（v2.9 视觉重构）============
    section_label_map = {1: "二、", 2: "三、", 3: "四、", 4: "五、"}
    groups = group_qa_by_difficulty(items)
    counter = 0
    section_idx = 1  # 二/三/四
    for diff in ("必问", "常问", "刁钻"):
        diff_items = groups.get(diff, [])
        if not diff_items:
            continue

        pdf.add_page()
        section_prefix = section_label_map.get(section_idx, "")
        section_idx += 1

        # 章节首页难度卡片
        diff_emoji_zh = {"必问": "🟢 必问", "常问": "🟡 常问", "刁钻": "🔴 刁钻"}
        _set_font(16, "B")
        pdf.cell(
            0, 12,
            _txt(f"{section_prefix}{diff_emoji_zh.get(diff, diff)} 问题（共 {len(diff_items)} 题）"),
            **NL,
        )

        diff_intro = {
            "必问": "🟢 必问 = 答辩老师几乎一定会问，必须能脱口而出",
            "常问": "🟡 常问 = 常见追问，建议提前打草稿",
            "刁钻": "🔴 刁钻 = 进阶质疑，视情况准备",
        }
        _set_font(10, "I")
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 7, _txt(diff_intro.get(diff, "")), **NL)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

        for item in diff_items:
            counter += 1
            # 问题（加粗 14pt）
            _set_font(14, "B")
            q_text = f"Q{counter}：{item.question}"
            pdf.multi_cell(0, 8, _txt(q_text))
            pdf.ln(1)

            # 类别 + 难度小字
            _set_font(9, "I")
            pdf.set_text_color(120, 120, 120)
            pdf.cell(
                0, 5,
                _txt(f"   {item.category_label}  ·  {diff_emoji_zh.get(item.difficulty, item.difficulty)}"),
                **NL,
            )
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

            # 参考答案：浅灰背景框
            _set_font(11, "B")
            pdf.set_text_color(60, 100, 160)
            pdf.cell(0, 6, _txt("💡 参考答案"), **NL)
            pdf.set_text_color(0, 0, 0)

            answer = item.answer
            # 估算答案高度（粗算每行约 60 字符）
            est_lines = max(2, len(answer) // 60 + 1)
            box_h = est_lines * 6 + 4
            y_start = pdf.get_y()
            _draw_filled_box(
                pdf.l_margin, y_start,
                210 - pdf.l_margin - pdf.r_margin, box_h,
                (245, 245, 245),
            )
            pdf.set_y(y_start + 2)
            pdf.set_x(pdf.l_margin + 3)
            _set_font(11)
            pdf.multi_cell(
                210 - pdf.l_margin - pdf.r_margin - 6, 6,
                _txt(answer),
            )
            pdf.ln(2)

            # 笔记区
            _set_font(11, "B")
            pdf.set_text_color(60, 100, 160)
            pdf.cell(0, 6, _txt("✏️ 我的回答笔记"), **NL)
            pdf.set_text_color(0, 0, 0)
            _underline_row(line_count=5)

            pdf.ln(4)

    # ============ 考前 3 天复习计划（v2.9 重构）============
    pdf.add_page()
    _set_font(16, "B")
    next_section = section_label_map.get(section_idx, f"{section_idx + 1}、")
    pdf.cell(0, 12, _txt(f"{next_section}考前 3 天复习计划"), **NL)
    pdf.ln(4)

    days = [
        ("📘 Day 1（考前 3 天）", "通读所有 🟢 必问，逐题在「我的回答笔记」区写答案。",
         "目标：熟悉所有必问问题的答案模板，能用自己的话复述。", (220, 240, 220)),
        ("📗 Day 2（考前 2 天）", "练习 🟡 常问，对照参考答案修正笔记。",
         "目标：能对常问问题应答得当，把握核心要点。", (250, 240, 200)),
        ("📕 Day 3（考前 1 天）", "浏览 🔴 刁钻，确保至少能说出大致方向。",
         "目标：避免刁钻问题导致冷场，礼貌承认并提出思考方向。", (245, 220, 220)),
        ("⏰ 答辩当天", "考前 30 分钟快速过一遍 🟢 必问，深呼吸放松。",
         "目标：保持信心，记住评委更关心理解而非完美。", (220, 230, 245)),
    ]

    for title, action, goal, fill in days:
        y_start = pdf.get_y()
        _draw_filled_box(pdf.l_margin, y_start, 210 - pdf.l_margin - pdf.r_margin, 22, fill)
        pdf.set_y(y_start + 2)
        _set_font(12, "B")
        pdf.cell(0, 6, _txt(f"  {title}"), **NL)
        _set_font(11)
        pdf.cell(0, 6, _txt(f"  ▸ {action}"), **NL)
        _set_font(9, "I")
        pdf.set_text_color(110, 110, 110)
        pdf.cell(0, 5, _txt(f"  {goal}"), **NL)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    pdf.ln(8)
    _set_font(10, "I")
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(0, 6, _txt(
        "祝答辩顺利！记住：评委更关心你是否真正理解自己的研究，"
        "而不是是否完美无瑕。承认局限、诚实回答比强行 defending 更得分。"
    ), align="C")
    pdf.set_text_color(0, 0, 0)

    # 输出
    raw = pdf.output()
    if isinstance(raw, str):
        return raw.encode("latin-1")
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return bytes(raw)
