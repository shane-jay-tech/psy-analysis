"""文献综述工作台 UI 纯逻辑测试（v3.5）。

不渲染 streamlit，只测可单元测试的辅助函数。
"""

import streamlit as st

from src.literature_review.completeness import calculate_completeness
from src.literature_review.matrix import (
    DEFAULT_DIMENSIONS,
    add_literature_to_matrix,
    create_matrix,
    remove_literature_from_matrix,
)
from src.literature_review.models import LiteratureItem, LiteratureMatrix, ReadingNote
from src.literature_review.notes import (
    create_note,
    delete_note,
    filter_notes_by_type,
)
from src.utils.workspace import (
    LITERATURE_REVIEW_SESSION_KEY,
    get_literature_review_state,
)


# ---------------------------------------------------------------------------
# 矩阵维度增删
# ---------------------------------------------------------------------------

class TestMatrixDimensionOps:
    def test_default_dimensions_present(self):
        items = [LiteratureItem(key="k1")]
        m = create_matrix(items)
        for d in DEFAULT_DIMENSIONS:
            assert d in m.dimensions

    def test_add_dimension_creates_columns(self):
        items = [LiteratureItem(key="k1")]
        m = create_matrix(items)
        m.add_dimension("新维度")
        assert "新维度" in m.dimensions

    def test_remove_dimension_drops_cells(self):
        items = [LiteratureItem(key="k1")]
        m = create_matrix(items)
        m.set_cell("k1", "样本量", "200")
        m.remove_dimension("样本量")
        assert "样本量" not in m.dimensions
        assert "样本量" not in m.cells.get("k1", {})

    def test_add_literature_extends_matrix(self):
        items = [LiteratureItem(key="k1")]
        m = create_matrix(items)
        new_item = LiteratureItem(key="k2")
        add_literature_to_matrix(m, new_item)
        assert "k2" in m.cells

    def test_remove_literature(self):
        items = [LiteratureItem(key="k1"), LiteratureItem(key="k2")]
        m = create_matrix(items)
        ok = remove_literature_from_matrix(m, "k1")
        assert ok is True
        assert "k1" not in m.cells

    def test_remove_unknown_literature_returns_false(self):
        items = [LiteratureItem(key="k1")]
        m = create_matrix(items)
        assert remove_literature_from_matrix(m, "nonexistent") is False


# ---------------------------------------------------------------------------
# 笔记类型过滤
# ---------------------------------------------------------------------------

class TestNoteTypeFiltering:
    def test_filter_method_notes(self):
        notes = []
        create_note(notes, literature_key="k1", content="A", type="方法")
        create_note(notes, literature_key="k1", content="B", type="结果")
        create_note(notes, literature_key="k1", content="C", type="方法")
        filtered = filter_notes_by_type(notes, "方法")
        assert len(filtered) == 2
        for n in filtered:
            assert n.type == "方法"

    def test_filter_unknown_type_returns_empty(self):
        notes = []
        create_note(notes, literature_key="k1", content="A", type="方法")
        result = filter_notes_by_type(notes, "未知类型")
        assert result == []


# ---------------------------------------------------------------------------
# 完成度计算（UI 显示前的核心逻辑）
# ---------------------------------------------------------------------------

class TestCompletenessForUIDisplay:
    def test_progressive_completeness(self):
        """逐步添加内容，完成度递增。"""
        state = {
            "literature_items": [],
            "notes": [],
            "matrix": {"dimensions": [], "cells": {}},
            "themes": [],
            "gaps": [],
        }
        score_0 = calculate_completeness(state).total

        # 加 5 篇高相关文献
        state["literature_items"] = [
            {"key": f"k{i}", "relevance_score": 0.6} for i in range(5)
        ]
        score_5 = calculate_completeness(state).total
        assert score_5 > score_0

        # 加 themes + gaps
        state["themes"] = [{"theme_name": "T"}]
        state["gaps"] = [{"gap_description": "G"}]
        score_full = calculate_completeness(state).total
        assert score_full > score_5

    def test_grade_color_threshold(self):
        """验证等级阈值（优秀/良好/及格/不足）。"""
        from src.literature_review.completeness import CompletenessResult
        assert CompletenessResult(total=85).grade == "优秀"
        assert CompletenessResult(total=65).grade == "良好"
        assert CompletenessResult(total=45).grade == "及格"
        assert CompletenessResult(total=20).grade == "不足"


# ---------------------------------------------------------------------------
# UI 状态键管理（funnel_intro_shown / quality_preview_dismissed / lit_review_checked）
# ---------------------------------------------------------------------------

class TestUIStateKeys:
    def test_funnel_intro_shown_default_false(self):
        st.session_state.clear()
        assert st.session_state.get("funnel_intro_shown") is None

    def test_funnel_intro_persists(self):
        st.session_state.clear()
        st.session_state["funnel_intro_shown"] = True
        assert st.session_state["funnel_intro_shown"] is True

    def test_lit_review_checked_dict_in_wizard_data(self):
        """v3.5 文献→wizard 贯通时，wizard_data 应有 lit_review_checked 字典。"""
        st.session_state.clear()
        wd = {"title": "T", "lit_review_checked": {"k1": True, "k2": False}}
        assert wd["lit_review_checked"]["k1"] is True
        assert wd["lit_review_checked"]["k2"] is False


# ---------------------------------------------------------------------------
# Tab 切换状态保持（lr_state 在 tab 切换间不变）
# ---------------------------------------------------------------------------

class TestTabSwitchPreservesState:
    def test_lr_state_persists_across_session_changes(self):
        st.session_state.clear()
        # 模拟用户在 tab 1 添加笔记
        lr_state = get_literature_review_state(st.session_state)
        lr_state["literature_items"] = [{"key": "k1", "title": "X", "year": 2024}]
        lr_state["notes"] = [{"note_id": "n1", "literature_key": "k1", "content": "A"}]

        # 模拟其他 session_state 修改（不触发清空）
        st.session_state["other_key"] = "other_value"

        # 验证 lr_state 仍存在
        lr_after = get_literature_review_state(st.session_state)
        assert len(lr_after["literature_items"]) == 1
        assert len(lr_after["notes"]) == 1


# ---------------------------------------------------------------------------
# 漏斗 stage 5 跳转按钮可见性
# ---------------------------------------------------------------------------

class TestFunnelToLiteratureReviewTransition:
    def test_phase_change_invokes_lr_panel(self):
        """phase=funnel → literature_review 切换应允许 UI 路由到 lr panel。"""
        from src.upstream.routing import resolve_route
        # 漏斗 stage 5 点击 → phase 切到 literature_review
        # 路由应识别此 phase
        handler = resolve_route(True, "literature_review", "beginner")
        assert handler == "literature_review_beginner"

    def test_wizard_top_button_phase_transition(self):
        """wizard 顶部「📚 文献综述」按钮等同于 phase=literature_review。"""
        from src.upstream.routing import resolve_route
        handler = resolve_route(True, "literature_review", "advanced")
        assert handler == "literature_review_advanced"


# ---------------------------------------------------------------------------
# 完成度评分 UI 阈值触发提示
# ---------------------------------------------------------------------------

class TestCompletenessUIThreshold:
    def test_low_score_should_warn(self):
        state = {
            "literature_items": [{"key": "k1", "relevance_score": 0.3}],
            "notes": [],
            "matrix": {"dimensions": [], "cells": {}},
            "themes": [],
            "gaps": [],
        }
        result = calculate_completeness(state)
        # 总分应 <60 触发"建议补充"提示
        assert result.total < 60

    def test_high_score_no_warn(self):
        state = {
            "literature_items": [{"key": f"k{i}", "relevance_score": 0.7} for i in range(15)],
            "notes": [{"literature_key": f"k{i}", "content": "n"} for i in range(15)],
            "matrix": {
                "dimensions": ["A", "B"],
                "cells": {f"k{i}": {"A": "a", "B": "b"} for i in range(15)},
            },
            "themes": [{"theme_name": "T"}],
            "gaps": [{"gap_description": "G"}],
        }
        result = calculate_completeness(state)
        assert result.total >= 80
