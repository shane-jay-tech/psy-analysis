"""苏格拉底反问引擎测试。"""

import pytest
from unittest.mock import MagicMock

from src.paper_writer.ai_tutor import (
    ChatMessage,
    TutorContext,
    build_tutor_system_prompt,
)
from src.upstream.socratic_engine import (
    _truncate_to_first_questions,
    _validate_socratic_output,
    ask_socratic,
)
from src.upstream.topic_funnel_kb import FALLBACK_QUESTIONS, get_fallback_question


# ---------------------------------------------------------------------------
# Phase 切换：funnel → 加载苏格拉底 prompt
# ---------------------------------------------------------------------------

class TestFunnelPromptSwitch:
    def test_funnel_phase_uses_socratic_prompt(self):
        ctx = TutorContext(phase="funnel", funnel_stage=1)
        prompt = build_tutor_system_prompt(ctx)
        # 苏格拉底标志性短语
        assert "唯一任务是反问" in prompt or "反问" in prompt
        assert "禁止陈述句" in prompt or "禁止给答案" in prompt
        # 不应有论文导师标题
        assert "学生当前研究上下文" not in prompt

    def test_default_phase_uses_paper_tutor_prompt(self):
        ctx = TutorContext()  # phase=""
        prompt = build_tutor_system_prompt(ctx, has_result=False)
        assert "学生当前研究上下文" in prompt
        # 不应是苏格拉底
        assert "禁止陈述句" not in prompt

    def test_funnel_stage_focus_injected(self):
        ctx = TutorContext(phase="funnel", funnel_stage=3)
        prompt = build_tutor_system_prompt(ctx)
        assert "阶段 3" in prompt


# ---------------------------------------------------------------------------
# 输出校验
# ---------------------------------------------------------------------------

class TestValidateOutput:
    def test_valid_one_question(self):
        assert _validate_socratic_output("你最关心的是什么？")

    def test_valid_two_questions(self):
        assert _validate_socratic_output("是哪个人群？还是哪个场景？")

    def test_no_question_mark_invalid(self):
        assert not _validate_socratic_output("这是一个陈述句。")

    def test_too_long_invalid(self):
        long = "你好" * 100
        assert not _validate_socratic_output(long + "？")

    def test_too_many_sentences_invalid(self):
        # 5 个问句 → 超出 max_sentences=2
        text = "什么人？什么时候？为什么？怎样？多久？"
        assert not _validate_socratic_output(text)

    def test_empty_invalid(self):
        assert not _validate_socratic_output("")
        assert not _validate_socratic_output("   ")


class TestTruncateToFirstQuestions:
    def test_extracts_first_two(self):
        text = "什么人群？什么场景？还有什么差异？以及别的？"
        result = _truncate_to_first_questions(text, max_questions=2)
        assert "什么人群？" in result
        assert "什么场景？" in result
        assert "还有什么差异" not in result


# ---------------------------------------------------------------------------
# ask_socratic 主流程（mock LLM）
# ---------------------------------------------------------------------------

def _mock_requests_with_response(content: str):
    """构造返回指定 content 的 mock requests 模块（OpenAI 兼容格式）。"""
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}],
    }
    mock_requests = MagicMock()
    mock_requests.post.return_value = mock_resp
    return mock_requests


def _llm_config():
    return {
        "provider": "openai",
        "base_url": "https://api.test.com",
        "api_key": "sk-test",
        "model": "gpt-4",
    }


class TestAskSocratic:
    def test_normal_response_passes_through(self):
        mock_req = _mock_requests_with_response("是哪个人群让你想研究？")
        result = ask_socratic(
            stage=1,
            user_input="我想研究焦虑",
            llm_config=_llm_config(),
            requests_module=mock_req,
        )
        assert "？" in result
        assert "人群" in result

    def test_long_response_gets_truncated(self):
        # LLM 返回 4 个问句，应被截到前 2 个
        long_text = "什么人？什么时候？为什么？怎样？"
        mock_req = _mock_requests_with_response(long_text)
        result = ask_socratic(
            stage=1,
            user_input="我想研究X",
            llm_config=_llm_config(),
            requests_module=mock_req,
        )
        # 应该是前 2 个问句之一，而不是 fallback
        assert "什么人？" in result
        assert "为什么？" not in result

    def test_non_question_falls_back(self):
        from src.llm_gateway import clear_cache
        clear_cache()
        # LLM 完全不听话给陈述句 → 重试也是这个 → fallback
        mock_req = _mock_requests_with_response("我觉得你应该研究焦虑。")
        result = ask_socratic(
            stage=1,
            user_input="我想研究焦虑 unique-test-1",
            llm_config=_llm_config(),
            requests_module=mock_req,
        )
        # 应是阶段 1 的 fallback 之一
        assert result in FALLBACK_QUESTIONS[1] or any(
            f.replace("{topic}", "") in result for f in FALLBACK_QUESTIONS[1]
        )

    def test_llm_http_error_falls_back(self):
        # mock 返回 500 → chat_with_tutor 抛 TutorAPIError → safe_chat 返回 None → fallback
        mock_resp = MagicMock(status_code=500)
        mock_resp.text = "Internal Error"
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_resp

        result = ask_socratic(
            stage=2,
            user_input="我想研究压力",
            llm_config=_llm_config(),
            requests_module=mock_requests,
            topic_hint="压力",
        )
        # 应是阶段 2 的 fallback（含 topic 替换或不含）
        assert "?" in result or "？" in result
        # 不应是空字符串或异常
        assert len(result) > 0

    def test_history_injects_previous_user_message(self):
        """ask_socratic 应在 user message 前注入「学生上一轮说」提示。"""
        mock_req = _mock_requests_with_response("继续问？")
        history = [
            ChatMessage(role="user", content="一开始我说想研究睡眠"),
            ChatMessage(role="assistant", content="是哪种人的睡眠？"),
        ]
        ask_socratic(
            stage=2,
            user_input="大学生",
            history=history,
            llm_config=_llm_config(),
            requests_module=mock_req,
        )
        # 检查 mock 被调用，并且 payload 中含「学生上一轮说」
        args, kwargs = mock_req.post.call_args
        payload = kwargs.get("json", {})
        msgs = payload.get("messages", [])
        # 最后一条 user message 应含注入提示
        last_user = next((m for m in reversed(msgs) if m["role"] == "user"), None)
        assert last_user is not None
        assert "学生上一轮说" in last_user["content"]
        assert "睡眠" in last_user["content"]

    def test_temperature_starts_at_03(self):
        """第一次调用 temperature 应为 0.3（苏格拉底反问降温）。"""
        from src.llm_gateway import clear_cache
        clear_cache()
        mock_req = _mock_requests_with_response("你最关心什么？")
        ask_socratic(
            stage=1,
            user_input="我想研究 unique-temperature-test",
            llm_config=_llm_config(),
            requests_module=mock_req,
        )
        args, kwargs = mock_req.post.call_args
        payload = kwargs["json"]
        assert payload["temperature"] == 0.3


class TestFallbackCoversAllStages:
    def test_each_stage_has_at_least_5_fallbacks(self):
        for stage in range(1, 6):
            assert len(FALLBACK_QUESTIONS[stage]) >= 5

    def test_get_fallback_question_with_topic(self):
        result = get_fallback_question(2, topic="手机依赖")
        # 阶段 2 第一条含 {topic}，应被替换
        assert "{topic}" not in result
        assert "?" in result or "？" in result


# ---------------------------------------------------------------------------
# v3.3 退行检测 + 重复检测
# ---------------------------------------------------------------------------

from src.upstream.socratic_engine import (
    _check_no_regression,
    extract_theme_from_question,
)


class TestRegressionDetection:
    def test_stage_3_question_with_stage_1_keywords_is_regression(self):
        """在阶段 3 反问「为什么对X感兴趣」应被标记退行。"""
        result = _check_no_regression(
            "你为什么对睡眠感兴趣？",
            current_stage=3,
            asked_themes=[],
        )
        assert result["ok"] is False
        assert result["violation"] == "regression"

    def test_stage_4_question_with_stage_2_keywords_is_regression(self):
        """阶段 4 反问「具体场景」属退行（应聚焦可证伪/可测量）。"""
        result = _check_no_regression(
            "你能描述一个典型场景吗？",
            current_stage=4,
            asked_themes=[],
        )
        assert result["ok"] is False
        assert result["violation"] == "regression"

    def test_duplicate_theme_detected(self):
        """与 asked_themes 高度相似的反问应被标记重复。"""
        result = _check_no_regression(
            "你说的睡眠具体是哪种睡眠？",
            current_stage=2,
            asked_themes=["你说的睡眠具体是什么睡眠"],   # 几乎相同
        )
        assert result["ok"] is False
        assert result["violation"] == "duplicate"

    def test_consecutive_duplicates_detected(self):
        """连续命中已问主题应被标记。"""
        themes = [
            "什么人群感到这种焦虑",
            "在什么场景下出现",
        ]
        result = _check_no_regression(
            "什么人群感到焦虑？",   # 与第一条高度相似
            current_stage=2,
            asked_themes=themes,
        )
        assert result["ok"] is False

    def test_normal_progression_not_flagged(self):
        """正常推进（阶段 3 问变量）不应触发警告。"""
        result = _check_no_regression(
            "X 越多，Y 就越什么？",
            current_stage=3,
            asked_themes=["你为什么对手机依赖感兴趣"],
        )
        assert result["ok"] is True
        assert result["violation"] is None

    def test_stage_1_no_regression_possible(self):
        """阶段 1 不可能退行（已是最早）。"""
        result = _check_no_regression(
            "你为什么对X感兴趣？",
            current_stage=1,
            asked_themes=[],
        )
        assert result["ok"] is True


class TestRegressionFalsePositiveProtection:
    """v3.4 退行检测的学生侧误判保护。"""

    def test_student_quoting_history_not_flagged(self):
        """学生在阶段 4 引用阶段 1 内容作为论据 → 不应标记退行。"""
        result = _check_no_regression(
            "正如我之前说的，我对手机依赖感兴趣，所以选了 SIAS 量表",
            current_stage=4,
            asked_themes=[],
            is_from_student=True,
        )
        assert result["ok"] is True

    def test_student_substantive_method_discussion_not_flagged(self):
        """学生 >100 字含方法关键词的实质讨论 → 不应标记退行。"""
        long_text = (
            "我打算用问卷调查方式做横断面研究，"
            "样本量定为 200 人，使用 SIAS 量表测量社交焦虑，"
            "用 SES 量表测量自尊，"
            "考虑到为什么对这个话题感兴趣这件事我前面已经讨论过，"
            "现在主要关心的是测量工具的信度和效度问题。"
        )
        assert len(long_text) > 100
        result = _check_no_regression(
            long_text,
            current_stage=4,
            asked_themes=[],
            is_from_student=True,
        )
        assert result["ok"] is True

    def test_ai_regression_still_flagged_even_with_keywords(self):
        """AI 反问仍受完整退行检测保护，不受学生侧豁免影响。"""
        # 同样的内容，但来自 AI（is_from_student=False）→ 仍标记
        result = _check_no_regression(
            "你为什么对手机依赖感兴趣？",
            current_stage=4,
            asked_themes=[],
            is_from_student=False,    # AI 反问
        )
        assert result["ok"] is False
        assert result["violation"] == "regression"


class TestExtractTheme:
    def test_basic_extraction(self):
        t = extract_theme_from_question("你最关心的是什么？")
        assert "?" not in t and "？" not in t
        assert "你最关心" in t

    def test_strips_polite_prefix(self):
        t = extract_theme_from_question("请问你具体指什么？")
        assert not t.startswith("请问")

    def test_truncates_long(self):
        t = extract_theme_from_question("你" * 100 + "？")
        assert len(t) <= 30
