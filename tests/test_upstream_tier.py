"""ResearchTier 系统测试。"""

import pytest
import streamlit as st

from src.upstream.tier import (
    ResearchTier,
    detect_tier_from_input,
    get_active_tier,
    set_active_tier,
    tier_at_least,
)
from src.utils.workspace import UPSTREAM_SESSION_KEY


class TestResearchTierEnum:
    def test_enum_string_values(self):
        assert ResearchTier.BEGINNER.value == "beginner"
        assert ResearchTier.ADVANCED.value == "advanced"
        assert ResearchTier.AUTO.value == "auto"


class TestDetectTierFromInput:
    def test_empty_or_short_returns_beginner(self):
        assert detect_tier_from_input("") == ResearchTier.BEGINNER
        assert detect_tier_from_input("我想研究焦虑") == ResearchTier.BEGINNER

    def test_two_or_more_keywords_triggers_advanced(self):
        # 含 "假设" + "中介" 两个关键词
        text = "我想检验假设：压力是焦虑的中介变量"
        assert detect_tier_from_input(text) == ResearchTier.ADVANCED

    def test_long_text_with_one_keyword_triggers_advanced(self):
        # 长文本（≥150字）+ 1 个关键词 "假设"
        text = "我打算研究大学生的学业压力对心理健康的影响。" * 8 + "需要检验一个假设。"
        assert len(text) >= 150
        assert detect_tier_from_input(text) == ResearchTier.ADVANCED

    def test_short_text_with_one_keyword_stays_beginner(self):
        # 短文本即使含 1 个关键词也是 BEGINNER（可能只是听过术语）
        text = "我想研究假设关系"
        assert len(text) < 150
        assert detect_tier_from_input(text) == ResearchTier.BEGINNER


class TestSessionReadWrite:
    def test_get_default_when_missing(self):
        st.session_state.clear()
        assert get_active_tier(st.session_state) == ResearchTier.BEGINNER

    def test_set_then_get_round_trip(self):
        st.session_state.clear()
        set_active_tier(st.session_state, ResearchTier.ADVANCED)
        assert get_active_tier(st.session_state) == ResearchTier.ADVANCED
        # 持久化到 upstream_state
        assert st.session_state[UPSTREAM_SESSION_KEY]["tier"] == "advanced"

    def test_set_accepts_string(self):
        st.session_state.clear()
        set_active_tier(st.session_state, "advanced")
        assert get_active_tier(st.session_state) == ResearchTier.ADVANCED

    def test_invalid_string_falls_back_to_beginner(self):
        st.session_state.clear()
        set_active_tier(st.session_state, "professor")  # 未知值
        assert get_active_tier(st.session_state) == ResearchTier.BEGINNER


class TestTierAtLeast:
    def test_basic_ordering(self):
        assert tier_at_least(ResearchTier.BEGINNER, ResearchTier.BEGINNER)
        assert tier_at_least(ResearchTier.BEGINNER, ResearchTier.ADVANCED)
        assert not tier_at_least(ResearchTier.ADVANCED, ResearchTier.BEGINNER)

    def test_auto_treated_as_beginner(self):
        # current=AUTO 视为 BEGINNER
        assert tier_at_least(ResearchTier.BEGINNER, ResearchTier.AUTO)
        assert not tier_at_least(ResearchTier.ADVANCED, ResearchTier.AUTO)

    def test_accepts_strings(self):
        assert tier_at_least("beginner", "advanced")
        assert not tier_at_least("advanced", "beginner")


# ---------------------------------------------------------------------------
# v3.3 ADVANCED 留痕字段 + 答辩问答自动引用
# ---------------------------------------------------------------------------

class TestAdvancedMeta:
    def test_advanced_meta_persists_in_workspace(self):
        """advanced_meta 应跨保存-加载完整恢复。"""
        from src.utils.workspace import (
            UPSTREAM_SESSION_KEY,
            build_workspace_snapshot,
            get_upstream_state,
            restore_workspace,
        )
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        upstream["tier"] = "advanced"
        upstream["advanced_meta"] = {
            "source": "实习观察",
            "why": "实习时发现该现象很普遍",
            "most_care": "X 是否真能预测 Y",
        }

        ws = build_workspace_snapshot()
        assert "advanced_meta" in ws["upstream_state"]

        st.session_state.clear()
        restore_workspace(ws)
        upstream = get_upstream_state(st.session_state)
        assert upstream["advanced_meta"]["source"] == "实习观察"
        assert upstream["advanced_meta"]["why"] == "实习时发现该现象很普遍"

    def test_motivation_qa_generated_from_advanced_meta(self):
        from src.upstream.topic_funnel import generate_motivation_qa_from_advanced
        meta = {
            "source": "文献启发",
            "why": "已有研究忽略了女性群体",
            "most_care": "性别效应是否存在",
        }
        items = generate_motivation_qa_from_advanced(meta)
        assert len(items) >= 2
        # 应有"为什么选择这个题目"问题
        questions = [it["question"] for it in items]
        assert any("为什么选择" in q for q in questions)
        # 应有"最希望发现"问题
        assert any("发现什么" in q or "发现" in q for q in questions)
        # 答案模板应引用 advanced_meta 内容
        first_answer = items[0]["answer_template"]
        assert "文献启发" in first_answer or "已有研究" in first_answer

    def test_empty_advanced_meta_returns_empty(self):
        from src.upstream.topic_funnel import generate_motivation_qa_from_advanced
        assert generate_motivation_qa_from_advanced({}) == []
        assert generate_motivation_qa_from_advanced(None) == []
        assert generate_motivation_qa_from_advanced(
            {"source": "", "why": "", "most_care": ""}
        ) == []

    def test_partial_advanced_meta_skips_empty_questions(self):
        """仅填了 source 不应生成「最希望发现」问题。"""
        from src.upstream.topic_funnel import generate_motivation_qa_from_advanced
        items = generate_motivation_qa_from_advanced({"source": "已有想法"})
        # 应有一个动机问题但没有「最希望发现」
        questions = [it["question"] for it in items]
        assert not any("最希望" in q for q in questions)
