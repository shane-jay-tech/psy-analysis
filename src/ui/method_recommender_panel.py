"""方法推荐向导 Streamlit 面板。

交互式向导：研究目的 → 变量类型 → 样本关系 → 推荐结果 → 一键进入分析。
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from src.analysis.method_recommender import (
    MethodRecommendation,
    ResearchDesignInput,
    recommend_method,
)

PURPOSE_OPTIONS = {
    "差异比较": "difference",
    "相关关系": "correlation",
    "预测/回归": "prediction",
    "中介效应": "mediation",
    "调节效应": "moderation",
    "信效度": "reliability",
}

DV_TYPE_OPTIONS = {
    "连续变量": "continuous",
    "二分类": "binary",
    "有序变量": "ordinal",
    "计数变量": "count",
}

IV_TYPE_OPTIONS = {
    "分组变量（分类）": "categorical",
    "连续变量": "continuous",
    "多因素": "multi_factor",
}

SAMPLE_RELATION_OPTIONS = {
    "独立样本": "independent",
    "配对样本": "paired",
    "重复测量": "repeated",
}

ASSUMPTION_OPTIONS = {
    "已满足": "met",
    "部分满足": "partial",
    "违反": "violated",
    "未检查": "unknown",
}

_STATE_KEY = "method_recommendation_result"
_HISTORY_KEY = "method_recommendation_history"


def render_method_recommender_panel(session_state: dict | None = None):
    """渲染方法推荐向导面板。"""
    if session_state is None:
        session_state = st.session_state

    st.subheader("🧭 方法推荐向导")
    st.caption("根据你的研究设计，推荐最合适的统计方法")

    col1, col2 = st.columns(2)

    with col1:
        purpose_label = st.selectbox(
            "研究目的",
            list(PURPOSE_OPTIONS.keys()),
            help="你想回答什么类型的研究问题？",
        )
        purpose = PURPOSE_OPTIONS[purpose_label]

        dv_label = st.selectbox(
            "因变量类型",
            list(DV_TYPE_OPTIONS.keys()),
            help="你要分析的结果变量是什么类型？",
        )
        dv_type = DV_TYPE_OPTIONS[dv_label]

        sample_size = st.number_input(
            "样本量 (N)", min_value=0, value=0, step=1,
            help="填 0 表示暂不设置",
        )

    with col2:
        iv_label = st.selectbox(
            "自变量类型",
            list(IV_TYPE_OPTIONS.keys()),
            help="你的预测变量/分组变量是什么类型？",
        )
        iv_type = IV_TYPE_OPTIONS[iv_label]

        relation_label = st.selectbox(
            "样本关系",
            list(SAMPLE_RELATION_OPTIONS.keys()),
        )
        sample_relation = SAMPLE_RELATION_OPTIONS[relation_label]

        assumption_label = st.selectbox(
            "假设检查状态",
            list(ASSUMPTION_OPTIONS.keys()),
        )
        assumptions_met = ASSUMPTION_OPTIONS[assumption_label]

    with st.expander("高级选项", expanded=False):
        adv_col1, adv_col2 = st.columns(2)
        with adv_col1:
            n_groups = st.number_input("组数", min_value=2, value=2, step=1)
            time_points = st.number_input("测量时间点", min_value=1, value=1, step=1)
        with adv_col2:
            has_covariate = st.checkbox("有协变量")
            n_covariates = st.number_input("协变量数量", min_value=0, value=0, step=1) if has_covariate else 0

    if st.button("🔍 获取推荐", type="primary"):
        design = ResearchDesignInput(
            purpose=purpose,
            dv_type=dv_type,
            iv_type=iv_type,
            sample_relation=sample_relation,
            time_points=time_points,
            n_groups=n_groups,
            has_covariate=has_covariate,
            n_covariates=n_covariates,
            sample_size=sample_size,
            assumptions_met=assumptions_met,
        )
        rec = recommend_method(design)
        session_state[_STATE_KEY] = rec

        history = session_state.get(_HISTORY_KEY, [])
        history.append({"design": design.__dict__, "recommendation": rec.primary_method})
        session_state[_HISTORY_KEY] = history

    rec = session_state.get(_STATE_KEY)
    if rec:
        _render_recommendation(rec)
        _render_recipe_button(session_state)


def _render_recommendation(rec: MethodRecommendation):
    """渲染推荐结果。"""
    st.markdown("---")
    st.subheader(f"✅ 推荐方法: {rec.primary_method_zh}")

    confidence_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(rec.confidence, "⚪")
    st.markdown(f"**置信度**: {confidence_color} {rec.confidence}")
    st.markdown(f"**说明**: {rec.explanation}")

    if rec.warnings:
        for w in rec.warnings:
            st.warning(w)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**备选方法**")
        for alt in rec.alternative_methods:
            st.markdown(f"- `{alt['method']}` — {alt['reason']}")

    with col2:
        st.markdown("**不推荐方法**")
        for rej in rec.rejected_methods:
            st.markdown(f"- ~~{rej['method']}~~ — {rej['reason']}")

    st.markdown("**前提假设检查**")
    for check in rec.assumption_checks:
        st.markdown(f"- {check}")

    st.markdown("**所需变量**")
    for var in rec.required_variables:
        st.markdown(f"- {var}")

    st.info(f"📎 下一步: {rec.next_action}")


from src.ui.state_keys import ANALYSIS_RECIPE_KEY as _RECIPE_KEY


def _render_recipe_button(session_state: dict):
    """渲染'使用此方法分析'按钮。"""
    from src.analysis.method_recommender import recommendation_to_recipe, AnalysisRecipe

    rec = session_state.get(_STATE_KEY)
    history = session_state.get(_HISTORY_KEY, [])
    if not rec:
        return

    if st.button("🚀 使用此方法分析", type="primary", key="use_recipe_btn"):
        last_design = history[-1]["design"] if history else {}
        design = ResearchDesignInput(**last_design) if last_design else ResearchDesignInput()
        recipe = recommendation_to_recipe(rec, design, recommendation_id=f"rec_{len(history)}")
        session_state[_RECIPE_KEY] = recipe
        st.success(f"已生成分析方案: {recipe.method_zh}。请切换到「📈 数据分析」使用。")
        st.markdown("**变量角色要求:**")
        for role, desc in recipe.variable_roles.items():
            st.markdown(f"- `{role}`: {desc}")


def get_analysis_recipe(session_state: dict):
    """获取当前分析方案（供数据分析页使用）。"""
    return session_state.get(_RECIPE_KEY)


def get_recommendation_for_deliverable(session_state: dict) -> list[dict]:
    """获取推荐历史用于交付包。"""
    return session_state.get(_HISTORY_KEY, [])


def get_current_recommendation(session_state: dict) -> MethodRecommendation | None:
    """获取当前推荐结果。"""
    return session_state.get(_STATE_KEY)
