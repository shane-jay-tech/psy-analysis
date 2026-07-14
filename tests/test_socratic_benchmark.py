"""LLM-as-judge 反问质量评估测试（v3.5）。"""

import json
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.benchmark

from src.upstream.socratic_benchmark import (
    JudgeScore,
    _rule_evaluate,
    _safe_parse_judge_json,
    batch_evaluate_benchmark,
    compare_judge_vs_human,
    evaluate_with_judge,
)


def _llm_config():
    return {
        "provider": "openai", "base_url": "https://x",
        "api_key": "sk-test", "model": "gpt-4",
    }


def _mock_requests_returning(content: str):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    req = MagicMock()
    req.post.return_value = resp
    return req


# ---------------------------------------------------------------------------
# 规则评估（降级）
# ---------------------------------------------------------------------------

class TestRuleEvaluate:
    def test_high_quality_question_scores_well(self):
        score = _rule_evaluate("你说的「焦虑」具体指考前几天的紧张，还是考试当下的躯体反应？")
        assert score.inspirational_score >= 4
        assert score.touches_core_dimensions is True
        assert score.method == "rule"

    def test_short_question_scores_low(self):
        score = _rule_evaluate("是吗？")
        assert score.inspirational_score <= 3
        assert score.method == "rule"

    def test_no_question_mark_low_score(self):
        score = _rule_evaluate("这个研究方向值得探索")
        assert score.inspirational_score <= 2

    def test_empty_returns_zero(self):
        score = _rule_evaluate("")
        assert score.inspirational_score == 0


# ---------------------------------------------------------------------------
# JudgeScore 总分与等级
# ---------------------------------------------------------------------------

class TestJudgeScoreScale:
    def test_total_calculation(self):
        s = JudgeScore(
            inspirational_score=5.0,
            cross_stage_consistent=True,
            touches_core_dimensions=True,
        )
        # 5×12 + 20 + 20 = 100
        assert s.total == 100.0
        assert s.grade == "优秀"

    def test_partial_score(self):
        s = JudgeScore(
            inspirational_score=3.0,
            cross_stage_consistent=True,
            touches_core_dimensions=False,
        )
        # 3×12 + 20 + 0 = 56
        assert s.total == 56.0
        assert s.grade == "不足"

    def test_grade_thresholds(self):
        assert JudgeScore(inspirational_score=5.0, cross_stage_consistent=True,
                            touches_core_dimensions=True).grade == "优秀"
        assert JudgeScore(inspirational_score=4.0, cross_stage_consistent=True,
                            touches_core_dimensions=True).grade == "优秀"  # 88
        assert JudgeScore(inspirational_score=3.0, cross_stage_consistent=True,
                            touches_core_dimensions=True).grade == "合格"  # 76
        assert JudgeScore(inspirational_score=2.0, cross_stage_consistent=False,
                            touches_core_dimensions=False).grade == "不足"


# ---------------------------------------------------------------------------
# JSON 解析
# ---------------------------------------------------------------------------

class TestSafeParseJSON:
    def test_clean_json(self):
        result = _safe_parse_judge_json('{"inspirational_score": 4, "cross_stage_consistent": true}')
        assert result["inspirational_score"] == 4
        assert result["cross_stage_consistent"] is True

    def test_markdown_wrapped(self):
        text = "```json\n{\"inspirational_score\": 5}\n```"
        result = _safe_parse_judge_json(text)
        assert result["inspirational_score"] == 5

    def test_invalid_returns_none(self):
        assert _safe_parse_judge_json("not json at all") is None
        assert _safe_parse_judge_json("") is None


# ---------------------------------------------------------------------------
# evaluate_with_judge 集成
# ---------------------------------------------------------------------------

class TestEvaluateWithJudge:
    def test_no_llm_falls_back_to_rule(self):
        score = evaluate_with_judge(
            question="什么人群让你最关心？",
            student_context="我想研究焦虑",
            expected_dimensions=["人群定位"],
            llm_config={"provider": "openai", "api_key": ""},   # 无 key
        )
        assert score.method == "rule"

    def test_llm_call_returns_parsed_score(self):
        # mock 3 次相同输出
        ok_json = json.dumps({
            "inspirational_score": 4,
            "cross_stage_consistent": True,
            "touches_core_dimensions": True,
            "rationale": "有效反问",
        })
        score = evaluate_with_judge(
            question="什么人群？",
            student_context="焦虑",
            expected_dimensions=["人群"],
            llm_config=_llm_config(),
            requests_module=_mock_requests_returning(ok_json),
            n_runs=3,
        )
        assert score.method == "llm"
        assert score.inspirational_score == 4
        assert score.cross_stage_consistent is True
        assert "有效反问" in score.rationale
        assert len(score.raw_runs) == 3

    def test_llm_returns_invalid_json_falls_back(self):
        score = evaluate_with_judge(
            question="什么人？",
            student_context="X",
            expected_dimensions=["d1"],
            llm_config=_llm_config(),
            requests_module=_mock_requests_returning("not json garbage"),
            n_runs=2,
        )
        # 解析失败 3 次 → fallback 规则评估
        assert score.method == "rule"


# ---------------------------------------------------------------------------
# 批量评估 + 与人工对比
# ---------------------------------------------------------------------------

class TestBatchAndCompare:
    def test_batch_evaluate_iterates_all(self):
        benchmark = {
            "stages": {
                "1": [
                    {"id": "1-01", "input": "我想研究焦虑", "expected_dimensions": ["人群"]},
                ],
                "2": [
                    {"id": "2-01", "input": "X 现象具体化", "expected_dimensions": ["场景"]},
                ],
            }
        }
        questions = {"1-01": "哪种人群？", "2-01": "什么场景？"}

        result = batch_evaluate_benchmark(
            benchmark, questions,
            llm_config={"provider": "openai", "api_key": ""},   # 触发 rule fallback
        )
        assert len(result["results"]) == 2
        # 都用了 rule
        assert result["method_summary"]["rule"] == 2

    def test_compare_judge_vs_human(self):
        judge_results = [
            {"case_id": "c1", "judge": {"inspirational_score": 4}},
            {"case_id": "c2", "judge": {"inspirational_score": 5}},
            {"case_id": "c3", "judge": {"inspirational_score": 2}},
        ]
        human = {
            "c1": {"manual_score": 4},   # 一致
            "c2": {"manual_score": 4},   # 差 1，仍算一致
            "c3": {"manual_score": 5},   # 差 3，不一致
        }
        result = compare_judge_vs_human(judge_results, human)
        assert result["matches"] == 2
        assert result["total"] == 3
        assert abs(result["consistency_rate"] - 0.667) < 0.01
        assert result["needs_human_review"] is True


# ---------------------------------------------------------------------------
# v3.7 N2: human_labels 结构验证 + 与 judge 对比集成测试
# ---------------------------------------------------------------------------

class TestN2HumanLabels:
    """v3.7 N2: 加载人工标注的边界案例，与 LLM-as-judge 协同回归。"""

    def _load_benchmark(self):
        from pathlib import Path
        path = Path(__file__).parent / "fixtures" / "socratic_benchmark.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_benchmark_has_human_labels_section(self):
        bm = self._load_benchmark()
        assert "human_labels" in bm
        labels = bm["human_labels"]
        # 元数据键带下划线
        assert "_annotated_at" in labels
        assert "_annotator" in labels

    def test_at_least_5_boundary_cases_annotated(self):
        bm = self._load_benchmark()
        labels = bm["human_labels"]
        case_keys = [k for k in labels.keys() if not k.startswith("_")]
        assert len(case_keys) >= 5, f"至少需 5 个人工标注，实际 {len(case_keys)}"

    def test_each_label_has_required_fields(self):
        bm = self._load_benchmark()
        labels = bm["human_labels"]
        for cid, lbl in labels.items():
            if cid.startswith("_"):
                continue
            assert "manual_score" in lbl, f"{cid} 缺 manual_score"
            assert "manual_passes" in lbl, f"{cid} 缺 manual_passes"
            assert "rationale" in lbl, f"{cid} 缺 rationale"
            assert 1 <= lbl["manual_score"] <= 5, f"{cid} score 越界"
            assert isinstance(lbl["manual_passes"], bool)

    def test_labeled_case_ids_exist_in_stages(self):
        """每个人工标注的 case_id 必须能在 stages 中找到对应案例。"""
        bm = self._load_benchmark()
        all_case_ids = {
            c["id"]
            for cases in bm["stages"].values()
            for c in cases
        }
        for cid in bm["human_labels"]:
            if cid.startswith("_"):
                continue
            assert cid in all_case_ids, f"human_labels.{cid} 在 stages 中不存在"

    def test_judge_vs_human_consistency_on_synthetic(self):
        """模拟 judge 对人工标注 case 给出 ±1 范围内的分数 → consistency = 1.0。"""
        bm = self._load_benchmark()
        labels = {k: v for k, v in bm["human_labels"].items() if not k.startswith("_")}
        # 构造 judge 输出：对每个人工 case 给一个 ±1 范围内的分数
        judge_results = []
        for cid, lbl in labels.items():
            judge_results.append({
                "case_id": cid,
                "judge": {"inspirational_score": lbl["manual_score"]},   # 同分
            })
        # 转 human dict
        human = {cid: {"manual_score": lbl["manual_score"]} for cid, lbl in labels.items()}
        result = compare_judge_vs_human(judge_results, human)
        assert result["consistency_rate"] == 1.0
        assert result["needs_human_review"] is False

    def test_judge_drift_detected_when_off_by_2(self):
        """模拟 judge 评分系统性高估 2 分 → consistency 应 < 0.8。"""
        bm = self._load_benchmark()
        labels = {k: v for k, v in bm["human_labels"].items() if not k.startswith("_")}
        judge_results = []
        for cid, lbl in labels.items():
            judge_results.append({
                "case_id": cid,
                "judge": {"inspirational_score": min(5, lbl["manual_score"] + 2)},
            })
        human = {cid: {"manual_score": lbl["manual_score"]} for cid, lbl in labels.items()}
        result = compare_judge_vs_human(judge_results, human)
        # 系统性偏差 → judge 不可信
        assert result["needs_human_review"] is True
