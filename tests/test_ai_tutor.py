"""AI 助教测试 — mock LLM 调用，专注 prompt 构造与上下文注入。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.paper_writer.ai_tutor import (
    ChatMessage, TutorAPIError, TutorContext,
    build_tutor_messages, build_tutor_system_prompt,
    chat_with_tutor, context_from_analysis, get_suggested_questions,
)


# --------------------------------------------------------------------------- #
# system prompt 构造
# --------------------------------------------------------------------------- #

def test_system_prompt_includes_research_context():
    ctx = TutorContext(
        test_type="independent_ttest",
        test_name_zh="独立样本t检验",
        sample_size=200,
        dv="社交焦虑总分",
        iv="性别",
        p_value=0.024,
        effect_size=0.55,
        effect_size_name="Cohen's d",
    )
    prompt = build_tutor_system_prompt(ctx)
    assert "独立样本t检验" in prompt
    assert "n = 200" in prompt
    assert "社交焦虑总分" in prompt
    assert "0.0240" in prompt or "0.024" in prompt
    assert "0.550" in prompt or "0.55" in prompt
    assert "Cohen's d" in prompt
    assert "显著" in prompt  # p<.05 应被标注


def test_system_prompt_marks_not_significant_when_p_high():
    ctx = TutorContext(p_value=0.30, sample_size=50)
    prompt = build_tutor_system_prompt(ctx)
    assert "不显著" in prompt


def test_system_prompt_no_result_section_when_has_result_false():
    ctx = TutorContext(test_name_zh="t检验", sample_size=100)
    prompt = build_tutor_system_prompt(ctx, has_result=False)
    assert "学生当前的分析结果" not in prompt
    assert "t检验" in prompt


def test_system_prompt_includes_extra_stats():
    ctx = TutorContext(
        test_name_zh="t检验",
        extra_stats={"Levene 方差齐性": "通过（p=0.32）", "t_statistic": 2.45},
    )
    prompt = build_tutor_system_prompt(ctx)
    assert "Levene" in prompt
    assert "通过" in prompt


# --------------------------------------------------------------------------- #
# messages 构造
# --------------------------------------------------------------------------- #

def test_build_messages_has_system_first_user_last():
    history = [
        ChatMessage(role="user", content="第一轮提问"),
        ChatMessage(role="assistant", content="第一轮回答"),
    ]
    msgs = build_tutor_messages("system_text", history, "新提问")
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "system_text"
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"] == "新提问"
    assert len(msgs) == 4  # system + 2 history + 1 new


def test_build_messages_truncates_long_history():
    history = [
        ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"msg{i}")
        for i in range(20)
    ]
    msgs = build_tutor_messages("sys", history, "new", history_limit=4)
    # system + 4 history + 1 new = 6
    assert len(msgs) == 6
    # 应保留最近 4 条（msg16-msg19）
    assert "msg19" in [m["content"] for m in msgs]
    assert "msg0" not in [m["content"] for m in msgs]


# --------------------------------------------------------------------------- #
# LLM 调用（mock requests）
# --------------------------------------------------------------------------- #

def test_chat_ollama_success():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"message": {"content": "你好，本科生！"}}
    mock_requests = MagicMock()
    mock_requests.post.return_value = mock_resp

    answer = chat_with_tutor(
        messages=[{"role": "user", "content": "你好"}],
        provider="ollama",
        base_url="http://localhost:11434",
        model="llama3",
        requests_module=mock_requests,
    )
    assert answer == "你好，本科生！"
    mock_requests.post.assert_called_once()
    # 确认 URL 正确
    args, kwargs = mock_requests.post.call_args
    assert "/api/chat" in args[0]


def test_chat_openai_compat_success():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "回答内容"}}],
    }
    mock_requests = MagicMock()
    mock_requests.post.return_value = mock_resp

    answer = chat_with_tutor(
        messages=[{"role": "user", "content": "你好"}],
        provider="deepseek",
        base_url="https://api.deepseek.com",
        api_key="sk-test",
        model="deepseek-chat",
        requests_module=mock_requests,
    )
    assert answer == "回答内容"
    args, kwargs = mock_requests.post.call_args
    assert "/v1/chat/completions" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test"


def test_chat_raises_friendly_error_on_http_failure():
    mock_resp = MagicMock(status_code=401)
    mock_resp.text = "Unauthorized"
    mock_requests = MagicMock()
    mock_requests.post.return_value = mock_resp

    with pytest.raises(TutorAPIError) as exc_info:
        chat_with_tutor(
            messages=[{"role": "user", "content": "test"}],
            provider="openai",
            base_url="https://api.openai.com",
            api_key="bad",
            model="gpt-4",
            requests_module=mock_requests,
        )
    assert exc_info.value.status_code == 401
    assert "401" in str(exc_info.value)


def test_chat_raises_on_malformed_response():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {}  # 缺 choices/message
    mock_requests = MagicMock()
    mock_requests.post.return_value = mock_resp

    with pytest.raises(TutorAPIError) as exc_info:
        chat_with_tutor(
            messages=[{"role": "user", "content": "test"}],
            provider="openai",
            base_url="https://x", api_key="k", model="m",
            requests_module=mock_requests,
        )
    assert "格式异常" in str(exc_info.value)


# --------------------------------------------------------------------------- #
# 上下文从 output 抽取
# --------------------------------------------------------------------------- #

def test_context_from_analysis_extracts_p_and_effect():
    result = SimpleNamespace(
        p_value=0.018, t_statistic=2.41, df=78,
        effect_size=0.55, effect_size_name="Cohen's d",
        assumption_equal_var={"passed": True, "p_value": 0.32},
    )
    output = {
        "test_type": "independent_ttest",
        "test_name_zh": "独立样本t检验",
        "result": result,
        "p_value": 0.018, "effect_size": 0.55,
    }
    ctx = {"sample_size": 200, "dv": "焦虑", "iv": "性别"}
    tc = context_from_analysis(output, ctx)
    assert tc.test_name_zh == "独立样本t检验"
    assert tc.sample_size == 200
    assert tc.p_value == 0.018
    assert tc.effect_size == 0.55
    assert "Levene" in str(tc.extra_stats) or any("Levene" in k for k in tc.extra_stats)


def test_context_from_empty_output():
    tc = context_from_analysis({}, {})
    assert tc.sample_size == 0
    assert tc.p_value is None


def test_suggested_questions_returns_list():
    qs = get_suggested_questions("independent_ttest")
    assert isinstance(qs, list)
    assert len(qs) >= 4
    assert all(isinstance(q, str) and len(q) > 5 for q in qs)


# --------------------------------------------------------------------------- #
# v3.1: 对话持久化 — 通过 workspace serialize/restore
# --------------------------------------------------------------------------- #

def test_tutor_history_serializes_to_workspace():
    import streamlit as st
    from src.paper_writer.ai_tutor import ChatMessage
    from src.utils.workspace import build_workspace_snapshot

    st.session_state.clear()
    st.session_state["_tutor_history_step6"] = [
        ChatMessage(role="user", content="问题1"),
        ChatMessage(role="assistant", content="答案1"),
    ]
    st.session_state["_tutor_history_step7"] = [
        ChatMessage(role="user", content="问题2"),
    ]

    ws = build_workspace_snapshot()
    assert "tutor_histories" in ws
    assert "_tutor_history_step6" in ws["tutor_histories"]
    msgs6 = ws["tutor_histories"]["_tutor_history_step6"]
    assert len(msgs6) == 2
    assert msgs6[0]["role"] == "user"
    assert msgs6[0]["content"] == "问题1"


def test_tutor_history_restores_from_workspace():
    import streamlit as st
    from src.paper_writer.ai_tutor import ChatMessage
    from src.utils.workspace import build_workspace_snapshot, restore_workspace

    # 准备数据
    st.session_state.clear()
    st.session_state["_tutor_history_step6"] = [
        ChatMessage(role="user", content="原始问题"),
        ChatMessage(role="assistant", content="原始答案"),
    ]
    ws = build_workspace_snapshot()

    # 清空再恢复
    st.session_state.clear()
    restore_workspace(ws)

    restored = st.session_state.get("_tutor_history_step6")
    assert isinstance(restored, list)
    assert len(restored) == 2
    assert isinstance(restored[0], ChatMessage)
    assert restored[0].content == "原始问题"
    assert restored[1].role == "assistant"


def test_tutor_history_round_trip_keeps_independent_locations():
    """step6 和 step7 历史应独立保留。"""
    import streamlit as st
    from src.paper_writer.ai_tutor import ChatMessage
    from src.utils.workspace import build_workspace_snapshot, restore_workspace

    st.session_state.clear()
    st.session_state["_tutor_history_step6"] = [ChatMessage("user", "step6-q")]
    st.session_state["_tutor_history_step7"] = [ChatMessage("user", "step7-q")]

    ws = build_workspace_snapshot()
    st.session_state.clear()
    restore_workspace(ws)

    assert st.session_state["_tutor_history_step6"][0].content == "step6-q"
    assert st.session_state["_tutor_history_step7"][0].content == "step7-q"
