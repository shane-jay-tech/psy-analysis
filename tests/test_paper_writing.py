"""v3.6: 论文「反问式审阅」核心函数测试。"""

import json
from unittest.mock import MagicMock

from src.paper_writer.paper_engine import (
    _rule_reviewer_questions,
    _parse_reviewer_output,
    generate_reviewer_questions,
    generate_revised_with_questions,
)


def _ok_llm_config():
    return {
        "provider": "openai", "base_url": "https://x",
        "api_key": "sk-test", "model": "gpt-4", "timeout": 30,
    }


def _mock_requests(content: str):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    req = MagicMock()
    req.post.return_value = resp
    return req


# ---------------------------------------------------------------------------
# generate_reviewer_questions
# ---------------------------------------------------------------------------

class TestReviewerQuestionsLLM:
    def test_llm_returns_3_to_5_questions(self):
        from src.llm_gateway import clear_cache
        clear_cache()
        text = ("本研究采用独立样本 t 检验比较两组焦虑水平。"
                "结果显示实验组（M=3.2）显著低于对照组（M=4.1），p=0.024。"
                "未报告效应量。")
        # mock 返回 4 条追问
        llm_output = (
            "1. 你的样本量是多少？为什么没报告？\n"
            "2. 是否检查了正态性和方差齐性假设？\n"
            "3. 你提到 p=0.024，但没给效应量——Cohen's d 是多少？\n"
            "4. 95% 置信区间是多少？为什么没报告？"
        )
        result = generate_reviewer_questions(
            text, section="results",
            llm_config=_ok_llm_config(),
            requests_module=_mock_requests(llm_output),
        )
        assert result["method"] == "llm"
        assert 3 <= len(result["questions"]) <= 5
        assert all("？" in q or "?" in q for q in result["questions"])

    def test_does_not_return_rewritten_text(self):
        """关键哲学测试：返回的 questions 应是问句，不应是改写文本。"""
        text = "我使用 t 检验。"
        llm_output = (
            "1. 为什么选择 t 检验而非非参数检验？\n"
            "2. 你的样本量是否足够？\n"
            "3. 是否报告了效应量？"
        )
        result = generate_reviewer_questions(
            text, section="methods",
            llm_config=_ok_llm_config(),
            requests_module=_mock_requests(llm_output),
        )
        for q in result["questions"]:
            # 反问应以问号结尾，不应是「建议改成 X」式陈述
            assert q.endswith("？") or q.endswith("?")
            assert "建议改成" not in q
            assert "请改为" not in q


class TestReviewerQuestionsRuleFallback:
    def test_no_llm_falls_back_to_rule(self):
        result = generate_reviewer_questions(
            "我使用了独立样本 t 检验来比较两组的焦虑水平。两组样本量均为 60。",
            section="methods",
            llm_config={"provider": "openai", "api_key": ""},   # 无 key
        )
        assert result["method"] == "rule"
        assert len(result["questions"]) >= 3

    def test_short_text_returns_skip(self):
        result = generate_reviewer_questions("太短", section="methods")
        assert result["method"] == "skip"
        assert result["questions"] == []

    def test_apa7_checklist_per_section(self):
        """每个章节的规则模板应覆盖 APA7 关键检查点。"""
        for section, keywords in [
            ("methods", ["样本量", "信度", "缺失"]),
            ("results", ["效应量", "置信区间", "p"]),
            ("discussion", ["局限", "未来", "启示"]),
        ]:
            result = generate_reviewer_questions(
                "x" * 100,
                section=section,
                llm_config={"provider": "openai", "api_key": ""},
            )
            joined = " ".join(result["questions"])
            # 至少命中 1 个 APA7 关键词
            assert any(k in joined for k in keywords), \
                f"{section} 模板未覆盖 APA7 关键词 {keywords}"


# ---------------------------------------------------------------------------
# generate_revised_with_questions
# ---------------------------------------------------------------------------

class TestRevisedWithQuestions:
    def test_revised_only_when_questions_provided(self):
        result = generate_revised_with_questions(
            "原文", questions_with_answers=[],
            llm_config=_ok_llm_config(),
        )
        assert result["method"] == "skip"
        assert result["revised_text"] == "原文"

    def test_stream_yields_chunks_then_dict(self):
        """v3.7 N1: 流式变体应先 yield 文本片段，最后 yield 结果 dict。"""
        from src.paper_writer.paper_engine import generate_revised_with_questions_stream
        # 空 questions → 直接 yield dict
        gen = generate_revised_with_questions_stream(
            "原文", questions_with_answers=[], llm_config=_ok_llm_config(),
        )
        chunks = list(gen)
        assert len(chunks) == 1
        assert isinstance(chunks[0], dict)
        assert chunks[0]["method"] == "skip"

    def test_revised_invokes_llm(self):
        from src.llm_gateway import clear_cache
        clear_cache()
        qa = [
            {"question": "样本量是多少？", "answer": "120 名大学生"},
            {"question": "是否报告效应量？", "answer": "已计算 d=0.42"},
        ]
        result = generate_revised_with_questions(
            "原文：本研究 t 检验。",
            questions_with_answers=qa,
            section="methods",
            llm_config=_ok_llm_config(),
            requests_module=_mock_requests("修订后的方法部分文字"),
        )
        assert result["method"] == "llm"
        assert "修订后的方法部分文字" in result["revised_text"]


# ---------------------------------------------------------------------------
# _parse_reviewer_output 解析鲁棒性
# ---------------------------------------------------------------------------

class TestParseReviewerOutput:
    def test_numbered_format(self):
        text = "1. 第一问？\n2. 第二问？\n3. 第三问？"
        result = _parse_reviewer_output(text)
        assert len(result) == 3
        assert "第一问？" in result[0]

    def test_chinese_punctuation(self):
        text = "1、问题一？\n2、问题二？"
        result = _parse_reviewer_output(text)
        assert len(result) == 2

    def test_empty_returns_empty(self):
        assert _parse_reviewer_output("") == []
        assert _parse_reviewer_output(None) == []


# ---------------------------------------------------------------------------
# v3.7 N4: gap_analysis 注入
# ---------------------------------------------------------------------------

class TestReviewerGapInjection:
    def test_no_gap_no_context_used(self):
        from src.llm_gateway import clear_cache
        clear_cache()
        text = "本研究采用 t 检验，样本量 N=60。"
        result = generate_reviewer_questions(
            text, section="methods",
            llm_config=_ok_llm_config(),
            requests_module=_mock_requests("1. q1?\n2. q2?\n3. q3?"),
            gap_analysis=None,
        )
        assert result.get("gap_context_used") is False

    def test_empty_gap_list_no_context(self):
        from src.llm_gateway import clear_cache
        clear_cache()
        result = generate_reviewer_questions(
            "学生写的方法段落足够长足够长足够长" * 3,
            section="methods",
            llm_config=_ok_llm_config(),
            requests_module=_mock_requests("1. q?\n2. q?\n3. q?"),
            gap_analysis=[],
        )
        assert result["gap_context_used"] is False

    def test_gap_dict_injected_into_prompt(self):
        from src.llm_gateway import clear_cache
        clear_cache()
        gaps = [
            {"gap_description": "已有研究多在西方样本，缺乏中国大学生数据"},
            {"gap_description": "情绪调节策略与社交焦虑的关联未在纵向设计中检验"},
        ]
        text = "本研究采用独立样本 t 检验比较两组的社交焦虑得分。" * 2
        captured_messages = []

        def _capture_post(*args, **kwargs):
            json_body = kwargs.get("json") or {}
            captured_messages.extend(json_body.get("messages", []))
            return _mock_requests("1. q1？\n2. q2？\n3. q3？").post(*args, **kwargs)

        req = MagicMock()
        req.post.side_effect = _capture_post
        result = generate_reviewer_questions(
            text, section="methods",
            llm_config=_ok_llm_config(),
            requests_module=req,
            gap_analysis=gaps,
        )
        assert result["gap_context_used"] is True
        sys_msg = next((m["content"] for m in captured_messages if m["role"] == "system"), "")
        assert "已在文献综述阶段识别" in sys_msg
        assert "西方样本" in sys_msg
        assert "纵向设计" in sys_msg
        assert "避免重复追问" in sys_msg

    def test_gap_dataclass_compatible(self):
        from src.llm_gateway import clear_cache
        from src.literature_review.models import GapAnalysis
        clear_cache()
        gaps = [
            GapAnalysis(gap_description="X 与 Y 在低自尊群体中的特殊机制未被检验"),
        ]
        text = "学生写的初稿足够长" * 5
        result = generate_reviewer_questions(
            text, section="methods",
            llm_config=_ok_llm_config(),
            requests_module=_mock_requests("1. q1？\n2. q2？\n3. q3？"),
            gap_analysis=gaps,
        )
        assert result["gap_context_used"] is True

    def test_gap_falls_back_to_rule_with_context_flag(self):
        """LLM 失败时 rule fallback 也应保留 gap_context_used 标志。"""
        gaps = [{"gap_description": "fake gap"}]
        result = generate_reviewer_questions(
            "学生方法段落需要至少 20 字以上才能触发审阅" * 2,
            section="methods",
            llm_config={"provider": "openai", "api_key": ""},  # 无 key → rule
            gap_analysis=gaps,
        )
        assert result["method"] == "rule"
        assert result["gap_context_used"] is True

    def test_gap_with_no_description_filtered(self):
        from src.llm_gateway import clear_cache
        clear_cache()
        gaps = [{"gap_description": ""}, {"gap_description": "  "}]
        text = "学生写的初稿足够长" * 5
        result = generate_reviewer_questions(
            text, section="methods",
            llm_config=_ok_llm_config(),
            requests_module=_mock_requests("1. q?\n2. q?\n3. q?"),
            gap_analysis=gaps,
        )
        # 全部 gap 描述为空 → 视为无 gap
        assert result["gap_context_used"] is False


class TestFormatGapContext:
    def test_empty_returns_empty_string(self):
        from src.paper_writer.paper_engine import _format_gap_context
        assert _format_gap_context(None) == ""
        assert _format_gap_context([]) == ""

    def test_truncates_long_descriptions(self):
        from src.paper_writer.paper_engine import _format_gap_context
        long_gap = [{"gap_description": "x" * 500}]
        out = _format_gap_context(long_gap)
        # 单条 gap 截断到 200 字符
        assert "x" * 200 in out
        assert "x" * 300 not in out

    def test_caps_at_5_gaps(self):
        from src.paper_writer.paper_engine import _format_gap_context
        gaps = [{"gap_description": f"gap {i}"} for i in range(10)]
        out = _format_gap_context(gaps)
        assert "gap 0" in out
        assert "gap 4" in out
        assert "gap 5" not in out  # 第 6 条不应出现
