"""upstream_panel 测试：用户契约、质量预检、低质量警告。

注：UI 函数大多依赖 streamlit runtime（无法在裸测试中渲染），
本文件仅测试纯逻辑函数与状态管理。
"""

import streamlit as st

from src.ui.upstream_panel import (
    _is_first_funnel_visit,
    warn_if_low_quality_reply,
)


class TestFirstFunnelVisit:
    def test_empty_state_is_first_visit(self):
        """无 stages 视为首次访问。"""
        assert _is_first_funnel_visit({"stages": {}}) is True
        assert _is_first_funnel_visit({}) is True

    def test_has_interest_text_not_first_visit(self):
        upstream = {"stages": {"1": {"interest_text": "已填", "ai_history": []}}}
        assert _is_first_funnel_visit(upstream) is False

    def test_has_ai_history_not_first_visit(self):
        upstream = {"stages": {"1": {"interest_text": "", "ai_history": [{"role": "assistant", "content": "X?"}]}}}
        assert _is_first_funnel_visit(upstream) is False


class TestUserContractFlag:
    def test_funnel_intro_shown_persists_through_session(self):
        st.session_state.clear()
        # 默认未显示
        assert st.session_state.get("funnel_intro_shown") is None
        # 模拟用户接受
        st.session_state["funnel_intro_shown"] = True
        # 标志应保留
        assert st.session_state["funnel_intro_shown"] is True


class TestLowQualityWarning:
    def test_short_reply_triggers_warning(self):
        warn = warn_if_low_quality_reply("是吗？")
        assert warn is not None
        assert "偏短" in warn or "<30" in warn

    def test_no_keyword_triggers_warning(self):
        # 30 字以上但无启发词
        reply = "我觉得你的研究方向很好，可以进一步推进，加油。" * 2
        assert len(reply) >= 30
        warn = warn_if_low_quality_reply(reply)
        # 不含「具体/为什么/如果/什么/哪/怎样」
        assert warn is not None
        assert "启发词" in warn

    def test_high_quality_reply_no_warning(self):
        warn = warn_if_low_quality_reply(
            "你说的「焦虑」具体指什么——是考前几天的紧张，还是考试当下的躯体反应？"
        )
        assert warn is None

    def test_empty_reply_returns_none(self):
        assert warn_if_low_quality_reply("") is None
        assert warn_if_low_quality_reply(None) is None
