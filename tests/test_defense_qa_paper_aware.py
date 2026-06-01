"""v3.8 O2: 个性化答辩题（基于学生论文 + reviewer 历史 + 漏斗记录）测试。"""

import json
from unittest.mock import MagicMock

import pytest

from src.paper_writer.defense_qa import (
    PaperAwareQAResult,
    _format_paper_context,
    _format_reviewer_history,
    _format_funnel_decisions,
    _parse_paper_aware_qa_response,
    _build_paper_aware_item,
    generate_paper_aware_qa,
)


# ---------------------------------------------------------------------------
# 上下文格式化
# ---------------------------------------------------------------------------

class TestPaperContext:
    def test_short_paper_returned_unchanged(self):
        text = "这是一段不到 2500 字的论文片段。"
        out = _format_paper_context(text)
        assert out == text

    def test_long_paper_truncated_with_marker(self):
        text = "短句。" * 2000  # 远超 2500
        out = _format_paper_context(text)
        assert len(out) < len(text)
        assert "中间内容省略" in out

    def test_empty_paper_returns_marker(self):
        out = _format_paper_context("")
        assert "未提供" in out


class TestReviewerHistory:
    def test_empty_history_returns_marker(self):
        assert "无反问历史" in _format_reviewer_history(None)
        assert "无反问历史" in _format_reviewer_history([])

    def test_dict_format_extracted(self):
        history = [
            {"question": "样本量为何选 100？", "answer": "基于 G*Power 计算"},
            {"question": "为什么用 t 而不是 ANOVA？", "answer": "只有两组"},
        ]
        out = _format_reviewer_history(history)
        assert "样本量为何选 100" in out
        assert "G*Power" in out
        assert "ANOVA" in out

    def test_caps_at_8_items(self):
        history = [{"question": f"问题{i}", "answer": f"答案{i}"} for i in range(20)]
        out = _format_reviewer_history(history)
        # 第 9 个不应出现
        assert "问题8" not in out  # 0-indexed: 第 9 个 = idx 8
        assert "问题0" in out

    def test_truncates_long_qa(self):
        history = [{"question": "问" * 500, "answer": "答" * 500}]
        out = _format_reviewer_history(history)
        # 不会无限长
        assert len(out) < 1500


class TestFunnelDecisions:
    def test_empty_returns_marker(self):
        assert "无选题决策记录" in _format_funnel_decisions(None)
        assert "无选题决策记录" in _format_funnel_decisions({})

    def test_extracts_known_keys(self):
        funnel = {
            "research_question": "社交焦虑如何影响学业表现",
            "variables": "焦虑、GPA、年级",
            "design": "横断面相关",
            "sample_size": "N=120",
            "hypothesis": "焦虑负向预测 GPA",
        }
        out = _format_funnel_decisions(funnel)
        assert "社交焦虑" in out
        assert "GPA" in out
        assert "横断面" in out
        assert "120" in out
        assert "负向预测" in out

    def test_partial_keys_ok(self):
        out = _format_funnel_decisions({"research_question": "Q1"})
        assert "Q1" in out


# ---------------------------------------------------------------------------
# JSON 解析
# ---------------------------------------------------------------------------

class TestParseResponse:
    def test_clean_json_array(self):
        content = json.dumps([
            {"question": "Q1", "answer_outline": "A1", "category": "method", "difficulty": "必问"},
        ], ensure_ascii=False)
        items = _parse_paper_aware_qa_response(content)
        assert len(items) == 1
        assert items[0]["question"] == "Q1"

    def test_markdown_code_block_stripped(self):
        content = '```json\n[{"question": "Q1", "answer_outline": "A1"}]\n```'
        items = _parse_paper_aware_qa_response(content)
        assert len(items) == 1

    def test_array_extracted_from_surrounding_text(self):
        content = '我会生成如下 JSON：\n[{"question": "Q1", "answer_outline": "A1"}]\n以上即为答案。'
        items = _parse_paper_aware_qa_response(content)
        assert len(items) == 1

    def test_invalid_returns_empty(self):
        assert _parse_paper_aware_qa_response("not json at all") == []
        assert _parse_paper_aware_qa_response("") == []

    def test_non_array_top_level_returns_empty(self):
        assert _parse_paper_aware_qa_response('{"question": "Q1"}') == []


# ---------------------------------------------------------------------------
# QAItem 构造
# ---------------------------------------------------------------------------

class TestBuildItem:
    def test_minimal_valid(self):
        raw = {
            "question": "为什么样本量选 100？",
            "answer_outline": "1. G*Power 算出\n2. 中等效应",
            "category": "data",
            "difficulty": "必问",
            "rationale": "你的论文 N=100 但未说明依据",
        }
        item = _build_paper_aware_item(raw)
        assert item is not None
        assert item.category == "data"
        assert item.difficulty == "必问"
        assert "rationale" not in item.answer  # 但 _ 包裹的 rationale 在
        assert "为什么问这题" in item.answer

    def test_missing_question_returns_none(self):
        raw = {"answer_outline": "A"}
        assert _build_paper_aware_item(raw) is None

    def test_missing_answer_returns_none(self):
        raw = {"question": "Q"}
        assert _build_paper_aware_item(raw) is None

    def test_invalid_category_falls_back(self):
        raw = {"question": "Q", "answer_outline": "A", "category": "weird_cat"}
        item = _build_paper_aware_item(raw)
        assert item.category == "method"

    def test_invalid_difficulty_falls_back(self):
        raw = {"question": "Q", "answer_outline": "A", "difficulty": "weird"}
        item = _build_paper_aware_item(raw)
        assert item.difficulty == "常问"


# ---------------------------------------------------------------------------
# generate_paper_aware_qa 集成
# ---------------------------------------------------------------------------

def _mock_llm_response(content: str):
    """构造一个 mock llm_chat 函数，返回固定 content。"""
    def _fake(messages, **kwargs):
        resp = MagicMock()
        resp.content = content
        return resp
    return _fake


class TestGeneratePaperAwareQA:
    def test_happy_path_with_all_inputs(self):
        mock_llm = _mock_llm_response(json.dumps([
            {
                "question": "你的样本量 N=120 是怎么定的？",
                "answer_outline": "1. G*Power 估算\n2. 中等效应",
                "category": "data",
                "difficulty": "必问",
                "rationale": "你的论文写到 N=120 但没说依据",
            },
            {
                "question": "为什么用 t 检验而不是 Mann-Whitney？",
                "answer_outline": "1. 数据近似正态\n2. n>30 中心极限",
                "category": "method",
                "difficulty": "常问",
                "rationale": "论文方法部分提到了正态性检验",
            },
        ], ensure_ascii=False))

        result = generate_paper_aware_qa(
            paper_text="本研究招募了 N=120 名大学生...",
            reviewer_history=[
                {"question": "为何选大学生？", "answer": "便于抽样"},
            ],
            funnel_state={"research_question": "焦虑与 GPA"},
            llm_chat_fn=mock_llm,
        )
        assert isinstance(result, PaperAwareQAResult)
        assert len(result.items) == 2
        assert result.used_paper
        assert result.used_reviewer_history
        assert result.used_funnel
        assert not result.fallback_to_template
        # 必问优先
        assert result.items[0].difficulty == "必问"

    def test_llm_failure_falls_back_to_template(self):
        def _fail_llm(messages, **kwargs):
            raise RuntimeError("API down")
        result = generate_paper_aware_qa(
            paper_text="some paper",
            llm_chat_fn=_fail_llm,
            output={"test_type": "independent_ttest", "effect_size": 0.5},
            ctx={"test_type": "independent_ttest"},
        )
        assert result.fallback_to_template
        assert "API down" in result.error
        # 模板版应该返回非空
        assert len(result.items) > 0

    def test_llm_returns_garbage_falls_back(self):
        mock_llm = _mock_llm_response("not json at all")
        result = generate_paper_aware_qa(
            paper_text="paper",
            llm_chat_fn=mock_llm,
            output={"test_type": "independent_ttest", "effect_size": 0.5},
            ctx={"test_type": "independent_ttest"},
        )
        assert result.fallback_to_template
        assert "JSON" in result.error or "合法" in result.error

    def test_max_items_respected(self):
        # 让 LLM 返回 15 条
        many = [
            {"question": f"Q{i}", "answer_outline": f"A{i}",
             "category": "method", "difficulty": "常问"}
            for i in range(15)
        ]
        mock_llm = _mock_llm_response(json.dumps(many, ensure_ascii=False))
        result = generate_paper_aware_qa(
            paper_text="paper",
            llm_chat_fn=mock_llm,
            max_items=5,
        )
        assert len(result.items) == 5

    def test_no_paper_no_history_still_works(self):
        """完全空输入 → 仍然调 LLM，不崩。"""
        mock_llm = _mock_llm_response(json.dumps([
            {"question": "Q1", "answer_outline": "A1",
             "category": "method", "difficulty": "常问"}
        ], ensure_ascii=False))
        result = generate_paper_aware_qa(llm_chat_fn=mock_llm)
        assert not result.used_paper
        assert not result.used_reviewer_history
        assert not result.used_funnel
        assert len(result.items) == 1

    def test_rationale_appended_to_answer(self):
        mock_llm = _mock_llm_response(json.dumps([
            {
                "question": "Q",
                "answer_outline": "要点1\n要点2",
                "category": "method",
                "difficulty": "常问",
                "rationale": "针对你论文中的 X 部分",
            }
        ], ensure_ascii=False))
        result = generate_paper_aware_qa(paper_text="x", llm_chat_fn=mock_llm)
        assert "针对你论文中的 X 部分" in result.items[0].answer
        assert "为什么问这题" in result.items[0].answer

    def test_difficulty_sort_order(self):
        mock_llm = _mock_llm_response(json.dumps([
            {"question": "Q1", "answer_outline": "A1",
             "category": "method", "difficulty": "刁钻"},
            {"question": "Q2", "answer_outline": "A2",
             "category": "method", "difficulty": "必问"},
            {"question": "Q3", "answer_outline": "A3",
             "category": "method", "difficulty": "常问"},
        ], ensure_ascii=False))
        result = generate_paper_aware_qa(paper_text="x", llm_chat_fn=mock_llm)
        diffs = [it.difficulty for it in result.items]
        assert diffs == ["必问", "常问", "刁钻"]
