"""导出强制门禁 — 所有导出入口必须经此检查。

流程：collect_project_state -> run_health_checks -> check_export_allowed
-> validate_bundle_for_export -> 放行或阻止。
"""

from __future__ import annotations

from typing import Any

from src.utils.project_health import (
    run_health_checks,
    has_blocking_issues,
    ProjectHealthIssue,
)
from src.paper_writer.bundle_export import validate_bundle_for_export
from src.ui.state_keys import (
    DATA_FRAME_KEY,
    ANALYSIS_CARDS_KEY,
    PAPER_BUNDLE_KEY,
    PAPER_DIFF_SELECTION_KEY,
)


def collect_project_state(session_state: dict) -> dict:
    """从 session_state 收集健康检查所需状态。"""
    df = session_state.get(DATA_FRAME_KEY)
    cards = session_state.get(ANALYSIS_CARDS_KEY, [])
    bundle = session_state.get(PAPER_BUNDLE_KEY)
    diff_selection = session_state.get(PAPER_DIFF_SELECTION_KEY)

    has_data = df is not None and (hasattr(df, "__len__") and len(df) > 0)
    variable_types_set = session_state.get("meta") is not None

    literature_pending = 0
    literature_approved = 0
    try:
        feed_cache = session_state.get("_feed_badge_cache")
        if feed_cache:
            literature_pending = feed_cache[1] if len(feed_cache) > 1 else 0
    except (TypeError, IndexError):
        pass

    return {
        "has_data": has_data,
        "variable_types_set": variable_types_set,
        "literature_pending_count": literature_pending,
        "literature_approved_count": literature_approved,
        "paper_bundle": bundle,
        "analysis_results": cards if cards else None,
    }


def run_export_gate(session_state: dict) -> tuple[bool, list[str], list[ProjectHealthIssue]]:
    """运行完整导出门禁检查。

    Returns:
        (allowed, block_reasons, all_issues)
    """
    state = collect_project_state(session_state)
    issues = run_health_checks(**state)

    block_reasons = []

    if has_blocking_issues(issues):
        block_reasons.extend(
            f"[{i.code}] {i.title}: {i.detail}"
            for i in issues
            if i.level == "ERROR"
        )

    bundle = session_state.get(PAPER_BUNDLE_KEY)
    if bundle is not None:
        bundle_issues = validate_bundle_for_export(bundle)
        for bi in bundle_issues:
            block_reasons.append(f"[BUNDLE] {bi}")

    diff_sel = session_state.get(PAPER_DIFF_SELECTION_KEY)
    if diff_sel is not None and hasattr(diff_sel, "has_unconfirmed"):
        if bundle and hasattr(bundle, "sections"):
            section_keys = list(bundle.sections.keys())
            if diff_sel.has_unconfirmed(section_keys):
                block_reasons.append("[UNCONFIRMED_AI] 有未确认的 AI 修改，请先完成差异对比选择")

    # 正式交付物中出现手机号、身份证、API key 等高风险文本时必须阻止，
    # 不能只显示提醒后仍允许下载。
    from src.utils.privacy_ethics import export_pre_check

    export_text_parts = []
    for key in ("analysis_output", PAPER_BUNDLE_KEY, "research_deliverable_bundle"):
        value = session_state.get(key)
        if value is not None:
            export_text_parts.append(str(value))
    if export_text_parts:
        privacy = export_pre_check("\n".join(export_text_parts), source="正式交付物")
        if not privacy["safe"]:
            block_reasons.append(
                f"[PRIVACY_HIGH] 检测到 {privacy['high_count']} 项高风险敏感信息，请脱敏后再导出"
            )

    allowed = len(block_reasons) == 0
    return allowed, block_reasons, issues


def render_export_gate(session_state: dict) -> bool:
    """在 Streamlit UI 中运行导出门禁并展示结果。

    Returns:
        True if export is allowed.
    """
    import streamlit as st

    allowed, reasons, issues = run_export_gate(session_state)

    if not allowed:
        st.error("导出被阻止 — 请先修复以下问题：")
        for r in reasons:
            st.markdown(f"- {r}")
        return False

    warn_issues = [i for i in issues if i.level == "WARN"]
    if warn_issues:
        with st.expander(f"导出提醒（{len(warn_issues)} 个警告）", expanded=False):
            for i in warn_issues:
                st.warning(f"**{i.title}**：{i.detail}")

    return True
