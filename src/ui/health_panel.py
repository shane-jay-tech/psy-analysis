"""项目健康检查 Streamlit 面板。

侧栏摘要 + 主页面详情 + ERROR 阻止导出。
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from src.utils.project_health import (
    ProjectHealthIssue,
    run_health_checks,
    has_blocking_issues,
    issues_summary,
)


LEVEL_ICONS = {
    "ERROR": "🚫",
    "WARN": "⚠️",
    "INFO": "ℹ️",
}

LEVEL_COLORS = {
    "ERROR": "red",
    "WARN": "orange",
    "INFO": "blue",
}


def render_health_sidebar() -> list[ProjectHealthIssue]:
    """侧栏健康状态摘要。返回 issues 列表供主面板复用。"""
    issues = _collect_issues()
    summary = issues_summary(issues)

    if summary["ERROR"] > 0:
        st.sidebar.error(f"🚫 {summary['ERROR']} 个阻断问题")
    elif summary["WARN"] > 0:
        st.sidebar.warning(f"⚠️ {summary['WARN']} 个建议修复")
    else:
        st.sidebar.success("✅ 项目状态良好")

    return issues


def render_health_panel(issues: list[ProjectHealthIssue] | None = None) -> None:
    """项目健康检查主面板。"""
    if issues is None:
        issues = _collect_issues()

    st.subheader("🏥 项目健康检查")

    if not issues:
        st.success("✅ 项目状态良好，无问题发现。")
        return

    summary = issues_summary(issues)
    _render_summary_metrics(summary)

    # 按级别分组展示
    errors = [i for i in issues if i.level == "ERROR"]
    warns = [i for i in issues if i.level == "WARN"]
    infos = [i for i in issues if i.level == "INFO"]

    if errors:
        st.markdown("### 🚫 阻断项（必须修复才能导出）")
        for issue in errors:
            _render_issue(issue)

    if warns:
        st.markdown("### ⚠️ 建议修复")
        for issue in warns:
            _render_issue(issue)

    if infos:
        st.markdown("### ℹ️ 信息")
        for issue in infos:
            _render_issue(issue)


def check_export_allowed(issues: list[ProjectHealthIssue] | None = None) -> bool:
    """检查是否允许导出。有 ERROR 时阻止并显示原因。"""
    if issues is None:
        issues = _collect_issues()

    if has_blocking_issues(issues):
        errors = [i for i in issues if i.level == "ERROR"]
        st.error("🚫 存在阻断性问题，无法导出：")
        for e in errors:
            st.markdown(f"- **{e.title}**: {e.detail}")
        return False
    return True


# ---------------------------------------------------------------------------
# 内部实现
# ---------------------------------------------------------------------------


def _collect_issues() -> list[ProjectHealthIssue]:
    """从 session_state 收集状态并运行检查。"""
    has_data = st.session_state.get("df") is not None
    variable_types_set = bool(st.session_state.get("variable_roles"))
    lit_pending = st.session_state.get("literature_pending_count", 0)
    lit_approved = st.session_state.get("literature_approved_count", 0)
    bundle = st.session_state.get("paper_bundle")
    analysis_results = st.session_state.get("analysis_results", None)

    return run_health_checks(
        has_data=has_data,
        variable_types_set=variable_types_set,
        literature_pending_count=lit_pending,
        literature_approved_count=lit_approved,
        paper_bundle=bundle,
        analysis_results=analysis_results,
    )


def _render_summary_metrics(summary: dict[str, int]) -> None:
    """展示问题数量指标。"""
    cols = st.columns(3)
    cols[0].metric("阻断", summary["ERROR"], delta_color="inverse")
    cols[1].metric("建议修复", summary["WARN"])
    cols[2].metric("信息", summary["INFO"])


def _render_issue(issue: ProjectHealthIssue) -> None:
    """渲染单个健康问题。"""
    icon = LEVEL_ICONS.get(issue.level, "")
    st.markdown(f"{icon} **{issue.title}**")
    st.caption(f"{issue.detail}  |  模块: {issue.module}")
    if issue.action_label:
        st.button(
            issue.action_label,
            key=f"health_action_{issue.code}",
            help=f"跳转到 {issue.action_target}",
        )
