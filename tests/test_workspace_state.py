"""WorkspaceState 顶层 dataclass 测试（v3.5）。"""

import streamlit as st

from src.utils.workspace import (
    LITERATURE_REVIEW_SESSION_KEY,
    UPSTREAM_SESSION_KEY,
    build_workspace_snapshot,
    restore_workspace,
)
from src.utils.workspace_state import (
    AdvancedMeta,
    AnalysisState,
    FunnelState,
    LiteratureReviewState,
    UIState,
    WizardState,
    WORKSPACE_KEY,
    WorkspaceState,
    get_workspace,
    set_workspace,
)


class TestSubStates:
    def test_funnel_state_defaults(self):
        f = FunnelState()
        assert f.tier == "beginner"
        assert f.phase == "funnel"
        assert f.current_stage == 1
        assert f.candidate_vars["dependent_vars"] == []

    def test_lr_state_defaults(self):
        lr = LiteratureReviewState()
        assert "样本量" in lr.matrix["dimensions"]
        assert lr.literature_items == []

    def test_advanced_meta_defaults(self):
        a = AdvancedMeta()
        assert a.source == ""
        assert a.why == ""


class TestWorkspaceStateBasics:
    def test_default_workspace(self):
        ws = WorkspaceState()
        assert isinstance(ws.funnel, FunnelState)
        assert isinstance(ws.literature_review, LiteratureReviewState)
        assert isinstance(ws.wizard, WizardState)
        assert isinstance(ws.analysis, AnalysisState)
        assert isinstance(ws.advanced, AdvancedMeta)
        assert isinstance(ws.ui, UIState)

    def test_to_dict_round_trip(self):
        ws = WorkspaceState()
        ws.funnel.tier = "advanced"
        ws.funnel.research_question = "X 影响 Y？"
        ws.advanced.why = "实习启发"
        ws.ui.undergrad_mode = True

        data = ws.to_dict()
        restored = WorkspaceState.from_dict(data)
        assert restored.funnel.tier == "advanced"
        assert restored.funnel.research_question == "X 影响 Y？"
        assert restored.advanced.why == "实习启发"
        assert restored.ui.undergrad_mode is True

    def test_from_dict_handles_unknown_fields(self):
        """从含未知字段的 dict 构造时不应崩。"""
        data = {
            "funnel": {"tier": "beginner", "_unknown_field": "garbage"},
            "literature_review": {},
            "_extra_top_level": "garbage",
        }
        ws = WorkspaceState.from_dict(data)
        assert ws.funnel.tier == "beginner"

    def test_from_dict_with_none_returns_empty(self):
        ws = WorkspaceState.from_dict(None)
        assert isinstance(ws, WorkspaceState)
        assert ws.funnel.tier == "beginner"


class TestLegacySessionMigration:
    def test_from_legacy_v3_4_session(self):
        st.session_state.clear()
        # 模拟 v3.4 散落字段
        st.session_state[UPSTREAM_SESSION_KEY] = {
            "tier": "advanced",
            "phase": "literature_review",
            "current_stage": 5,
            "research_question": "已有问题",
            "advanced_meta": {
                "source": "实习观察",
                "why": "现象普遍",
                "most_care": "X 是否预测 Y",
            },
        }
        st.session_state[LITERATURE_REVIEW_SESSION_KEY] = {
            "literature_items": [{"key": "k1", "title": "X"}],
            "notes": [{"note_id": "n1", "content": "笔记"}],
            "matrix": {"dimensions": ["d"], "cells": {}, "highlighted_keys": []},
            "themes": [],
            "gaps": [],
        }
        st.session_state["undergrad_mode"] = True
        st.session_state["undergrad_path"] = "survey"
        st.session_state["undergrad_step"] = 3
        st.session_state["undergrad_wizard_data"] = {"title": "T"}

        ws = WorkspaceState.from_legacy_session(st.session_state)
        assert ws.funnel.tier == "advanced"
        assert ws.funnel.phase == "literature_review"
        assert ws.funnel.research_question == "已有问题"
        assert ws.advanced.source == "实习观察"
        assert ws.advanced.why == "现象普遍"
        assert len(ws.literature_review.literature_items) == 1
        assert ws.wizard.undergrad_path == "survey"
        assert ws.wizard.undergrad_step == 3
        assert ws.ui.undergrad_mode is True

    def test_sync_to_legacy_writes_back(self):
        st.session_state.clear()
        ws = WorkspaceState()
        ws.funnel.research_question = "新问题"
        ws.funnel.tier = "advanced"
        ws.literature_review.last_search_query = "X 与 Y"
        ws.wizard.undergrad_step = 5

        ws.sync_to_legacy_session(st.session_state)
        assert st.session_state[UPSTREAM_SESSION_KEY]["research_question"] == "新问题"
        assert st.session_state[UPSTREAM_SESSION_KEY]["tier"] == "advanced"
        assert st.session_state[LITERATURE_REVIEW_SESSION_KEY]["last_search_query"] == "X 与 Y"
        assert st.session_state["undergrad_step"] == 5


class TestGetWorkspace:
    def test_get_creates_new_when_missing(self):
        st.session_state.clear()
        ws = get_workspace(st.session_state)
        assert isinstance(ws, WorkspaceState)
        assert WORKSPACE_KEY in st.session_state

    def test_get_returns_existing(self):
        st.session_state.clear()
        ws1 = WorkspaceState()
        ws1.funnel.tier = "advanced"
        st.session_state[WORKSPACE_KEY] = ws1
        ws2 = get_workspace(st.session_state)
        assert ws2 is ws1
        assert ws2.funnel.tier == "advanced"

    def test_get_rebuilds_from_legacy(self):
        st.session_state.clear()
        st.session_state[UPSTREAM_SESSION_KEY] = {
            "tier": "advanced", "phase": "wizard", "research_question": "X？",
        }
        ws = get_workspace(st.session_state)
        assert ws.funnel.tier == "advanced"
        assert ws.funnel.research_question == "X？"

    def test_get_unmarshals_dict_form(self):
        """如果 session_state[WORKSPACE_KEY] 是 dict（来自反序列化），自动转 dataclass。"""
        st.session_state.clear()
        st.session_state[WORKSPACE_KEY] = {
            "funnel": {"tier": "advanced", "research_question": "Z？"},
        }
        ws = get_workspace(st.session_state)
        assert isinstance(ws, WorkspaceState)
        assert ws.funnel.tier == "advanced"


class TestWorkspacePersistence:
    """v3.5 持久化：build_workspace_snapshot 应包含 workspace_state_v35。"""

    def test_round_trip_workspace_state(self):
        st.session_state.clear()
        ws = get_workspace(st.session_state)
        ws.funnel.research_question = "持久化测试"
        ws.funnel.tier = "advanced"
        ws.advanced.why = "动机"
        ws.literature_review.last_search_query = "X"
        # 手动同步到 legacy 字段，以便 build_workspace_snapshot 也能保存
        ws.sync_to_legacy_session(st.session_state)

        snapshot = build_workspace_snapshot()
        assert snapshot["_schema"] == "v3.5"
        assert "workspace_state_v35" in snapshot

        # 清空 + 恢复
        st.session_state.clear()
        restore_workspace(snapshot)
        ws_restored = get_workspace(st.session_state)
        assert ws_restored.funnel.research_question == "持久化测试"
        assert ws_restored.funnel.tier == "advanced"
        assert ws_restored.advanced.why == "动机"
        assert ws_restored.literature_review.last_search_query == "X"
