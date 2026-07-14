"""论文预览、AI 差异对比与导出 Streamlit 面板。

接入 PaperDraftBundle、section_diff.py、bundle_export.py，
让用户完成预览、段落选择、导出校验和最终导出。
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.paper_writer.section_diff import SectionDiff, compute_section_diff
from src.paper_writer.bundle_export import (
    ExportMeta,
    bundle_to_markdown,
    bundle_to_export_result,
    validate_bundle_for_export,
    SECTION_TITLES_ZH,
    SECTION_ORDER,
)


def render_paper_preview(bundle: PaperDraftBundle) -> None:
    """论文预览主入口。"""
    st.subheader("📄 论文预览")

    _render_bundle_info(bundle)
    _render_sections_preview(bundle)
    _render_warnings(bundle)


def render_ai_diff_panel(
    original_bundle: PaperDraftBundle,
    revised_bundle: PaperDraftBundle,
) -> PaperDraftBundle:
    """AI 差异对比面板。返回用户选择后的最终 Bundle。"""
    st.subheader("🔄 AI 修改对比")
    st.caption("逐段选择保留原文或 AI 修改版。")

    diffs: dict[str, SectionDiff] = {}
    for key in SECTION_ORDER:
        orig_sec = original_bundle.sections.get(key)
        rev_sec = revised_bundle.sections.get(key)
        if orig_sec and rev_sec and orig_sec.markdown != rev_sec.markdown:
            diff = compute_section_diff(
                orig_sec.markdown, rev_sec.markdown,
                section_name=SECTION_TITLES_ZH.get(key, key),
            )
            diffs[key] = diff

    if not diffs:
        st.success("原文与 AI 版本无差异，无需选择。")
        return original_bundle

    # 批量操作
    col1, col2 = st.columns(2)
    with col1:
        if st.button("全部保留原文", key="diff_all_original"):
            for d in diffs.values():
                d.select_all_original()
            st.rerun()
    with col2:
        if st.button("全部接受 AI", key="diff_all_revised"):
            for d in diffs.values():
                d.select_all_revised()
            st.rerun()

    # 逐章逐段对比
    for key, diff in diffs.items():
        title_zh = SECTION_TITLES_ZH.get(key, key)
        with st.expander(f"📝 {title_zh}（{diff.change_count} 处修改）", expanded=True):
            _render_section_diff(diff, key)

    # 生成最终 bundle
    final_sections = dict(original_bundle.sections)
    for key, diff in diffs.items():
        final_text = diff.get_selected_text()
        final_sections[key] = PaperSection(
            name=SECTION_TITLES_ZH.get(key, key),
            markdown=final_text,
            source="mixed",
        )

    return PaperDraftBundle(
        title=original_bundle.title,
        sections=final_sections,
        source="mixed",
        provenance={**original_bundle.provenance, "ai_diff": "user_selected"},
        meta=original_bundle.meta,
        figures=original_bundle.figures,
        warnings=original_bundle.warnings,
    )


def render_export_panel(bundle: PaperDraftBundle) -> None:
    """导出面板：校验 + Markdown/Word 导出。"""
    st.subheader("📦 导出")

    # 导出前校验
    issues = validate_bundle_for_export(bundle)
    if issues:
        st.markdown("**导出前检查发现以下问题：**")
        for issue in issues:
            if "为空" in issue or "标题" in issue:
                st.error(f"🚫 {issue}")
            else:
                st.warning(f"⚠️ {issue}")

        has_blocking = any("为空" in i or "标题" in i or "无任何章节" in i for i in issues)
        if has_blocking:
            st.error("存在阻断性问题，请修复后再导出。")
            return

    # 导出操作
    col1, col2 = st.columns(2)

    with col1:
        md_result = bundle_to_export_result(bundle, format="markdown")
        st.download_button(
            "📄 导出 Markdown",
            data=md_result.content,
            file_name=md_result.filename,
            mime="text/markdown",
            key="export_paper_md",
        )

    with col2:
        st.download_button(
            "📝 导出 Word（参数包）",
            data=bundle_to_markdown(bundle, include_source_tags=False),
            file_name=f"{bundle.title}_论文.md",
            mime="text/markdown",
            key="export_paper_docx_prep",
            help="导出纯 Markdown 作为 Word 转换的中间格式",
        )


# ---------------------------------------------------------------------------
# 内部渲染
# ---------------------------------------------------------------------------


def _render_bundle_info(bundle: PaperDraftBundle) -> None:
    """展示 Bundle 基本信息。"""
    cols = st.columns(3)
    cols[0].metric("论文标题", bundle.title)
    cols[1].metric("章节数", len(bundle.sections))
    cols[2].metric("来源", bundle.source)


def _render_sections_preview(bundle: PaperDraftBundle) -> None:
    """逐章节预览。"""
    for key in SECTION_ORDER:
        sec = bundle.sections.get(key)
        if sec:
            title_zh = SECTION_TITLES_ZH.get(key, key)
            with st.expander(f"📖 {title_zh}  [来源: {sec.source}]", expanded=False):
                st.markdown(sec.markdown)
                if sec.confidence_note:
                    st.caption(f"置信度说明: {sec.confidence_note}")

    # 非标准章节
    for key, sec in bundle.sections.items():
        if key not in SECTION_ORDER:
            with st.expander(f"📖 {key}  [来源: {sec.source}]", expanded=False):
                st.markdown(sec.markdown)


def _render_warnings(bundle: PaperDraftBundle) -> None:
    """展示 Bundle 警告。"""
    if bundle.warnings:
        st.markdown("---")
        for w in bundle.warnings:
            st.warning(f"⚠️ {w}")


def _render_section_diff(diff: SectionDiff, section_key: str) -> None:
    """渲染单个章节的段落级差异对比。"""
    for para in diff.paragraphs:
        if para.change_type == "unchanged":
            continue

        col1, col2, col3 = st.columns([4, 4, 2])
        with col1:
            st.markdown("**原文:**")
            if para.original:
                st.markdown(f"> {para.original[:200]}")
            else:
                st.caption("（无）")
        with col2:
            st.markdown("**AI 修改:**")
            if para.revised:
                st.markdown(f"> {para.revised[:200]}")
            else:
                st.caption("（已删除）")
        with col3:
            choice = st.radio(
                "选择",
                options=["original", "revised"],
                index=0 if para.selected == "original" else 1,
                format_func=lambda x: "原文" if x == "original" else "AI版",
                key=f"diff_{section_key}_{para.index}",
                horizontal=True,
            )
            para.selected = choice
        st.markdown("---")
