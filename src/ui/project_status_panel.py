"""项目状态面板 v5.1 — 论文就绪度评分和进度可视化。"""

import streamlit as st
from src.utils.readiness_scorer import compute_readiness, ReadinessReport


def render_project_status_panel(session_state: dict):
    """渲染论文就绪度评分面板。"""
    report = compute_readiness(session_state)

    _render_score_header(report)
    _render_dimension_breakdown(report)
    _render_action_items(report)
    _render_next_step(report)


def _render_score_header(report: ReadinessReport):
    grade_colors = {
        "未就绪": "🔴",
        "基本就绪": "🟡",
        "接近完成": "🟢",
        "可提交前检查": "✅",
    }
    icon = grade_colors.get(report.grade, "⚪")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.metric("总分", f"{report.total_score:.0f} / 100")
    with col2:
        st.metric("等级", f"{icon} {report.grade}")
    with col3:
        st.metric("阻断项", f"{len(report.blockers)} 个")


def _render_dimension_breakdown(report: ReadinessReport):
    st.subheader("各维度评分")

    for item in report.items:
        status_icon = {
            "good": "✅", "warning": "⚠️", "error": "❌", "missing": "⬜",
        }.get(item.status, "⬜")

        weight_pct = int(item.weight * 100)
        weighted_score = item.score * item.weight

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"{status_icon} **{item.dimension}** ({weight_pct}%)")
            if item.detail:
                st.caption(item.detail)
        with col2:
            st.progress(min(1.0, item.score / 100))
        with col3:
            st.write(f"{item.score:.0f}")


def _render_action_items(report: ReadinessReport):
    if report.blockers:
        st.subheader("❌ 必须处理")
        for b in report.blockers:
            st.error(b)

    if report.high_priority:
        st.subheader("⚠️ 建议处理")
        for h in report.high_priority:
            st.warning(h)

    if report.optional:
        with st.expander("📝 可选优化"):
            for o in report.optional:
                st.info(o)


def _render_next_step(report: ReadinessReport):
    if report.next_step:
        st.divider()
        st.info(f"🎯 **{report.next_step}**")
