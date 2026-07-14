"""研究交付包导出中心 Streamlit 面板。

展示交付包内容清单、健康检查、三种导出模式（简版/标准版/完整版）。
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from src.paper_writer.research_deliverable import ResearchDeliverableBundle
from src.ui.export_gate import run_export_gate

_BUNDLE_KEY = "research_deliverable_bundle"

EXPORT_MODES = {
    "简版": "basic",
    "标准版": "standard",
    "完整版": "full",
}

EXPORT_MODE_CONTENTS = {
    "basic": ["论文正文", "参考文献"],
    "standard": ["论文正文", "统计结果卡", "文献证据表", "数据清洗日志", "参考文献"],
    "full": ["论文正文", "统计结果卡", "文献证据表", "参考文献",
             "数据清洗日志", "方法推荐记录", "项目健康报告", "AI差异记录", "导出元数据"],
}


def render_deliverable_center_panel(session_state: dict | None = None):
    """渲染导出中心面板。"""
    if session_state is None:
        session_state = st.session_state

    st.subheader("📦 研究交付包导出中心")

    bundle = _get_or_build_bundle(session_state)
    if bundle is None:
        st.warning("交付包信息不足，请先完成统计分析和论文写作")
        return

    session_state[_BUNDLE_KEY] = bundle

    tab1, tab2, tab3 = st.tabs(["内容清单", "导出前检查", "导出"])

    with tab1:
        _render_manifest(bundle)
    with tab2:
        _render_pre_export_check(bundle, session_state)
    with tab3:
        _render_export(bundle, session_state)


def _get_or_build_bundle(session_state: dict) -> ResearchDeliverableBundle | None:
    """从 session_state 组装交付包。"""
    from src.ui.state_keys import PAPER_BUNDLE_KEY, ANALYSIS_CARDS_KEY

    paper_bundle = session_state.get(PAPER_BUNDLE_KEY)
    cards = session_state.get(ANALYSIS_CARDS_KEY, [])

    if not paper_bundle and not cards:
        return None

    bundle = ResearchDeliverableBundle(
        project_id=session_state.get("project_id", "project"),
        title=paper_bundle.title if paper_bundle else "未命名研究",
        paper_bundle=paper_bundle,
        analysis_cards=cards,
    )

    from src.ui.evidence_table_panel import _STORE_KEY
    evidence_store = session_state.get(_STORE_KEY)
    if evidence_store and hasattr(evidence_store, "records"):
        bundle.evidence_records = [r.to_dict() for r in evidence_store.records]

    from src.ui.questionnaire_import_panel import _CLEANED_KEY
    cleaned = session_state.get(_CLEANED_KEY)
    if cleaned and hasattr(cleaned, "log"):
        bundle.data_cleaning_log = [
            {"step": e.step, "action": e.action} for e in cleaned.log
        ]

    from src.ui.method_recommender_panel import _HISTORY_KEY
    recommendations = session_state.get(_HISTORY_KEY, [])
    bundle.method_recommendations = recommendations

    from src.ui.state_keys import PROJECT_HEALTH_ISSUES_KEY, PAPER_DIFF_SELECTION_KEY
    health = session_state.get(PROJECT_HEALTH_ISSUES_KEY, [])
    bundle.health_report = health if health else []

    diff_sel = session_state.get(PAPER_DIFF_SELECTION_KEY)
    if diff_sel and hasattr(diff_sel, "section_choices"):
        bundle.ai_diff_log = diff_sel.section_choices
    elif isinstance(diff_sel, dict):
        bundle.ai_diff_log = diff_sel

    return bundle


def _render_manifest(bundle: ResearchDeliverableBundle):
    """内容清单视图。"""
    st.markdown(bundle.to_markdown_index())


def _check_asset_completeness(bundle: ResearchDeliverableBundle) -> tuple[list[str], list[str]]:
    """检查交付资产完整度。返回 (errors, warnings)。"""
    errors = []
    warnings = []

    if not bundle.analysis_cards:
        errors.append("无统计结果卡 — 结果章不可交付")

    manifest = bundle.file_manifest()
    if not manifest:
        errors.append("交付包 manifest 为空 — 导出结构异常")

    if not bundle.method_recommendations:
        warnings.append("无方法推荐记录 — 缺少方法选择依据")

    if not bundle.evidence_records:
        warnings.append("无文献证据表 — 综述可信度不足")
    elif len(bundle.evidence_records) < 3:
        warnings.append("文献证据少于 3 条 — 覆盖可能不充分")

    if not bundle.data_cleaning_log:
        warnings.append("无数据清洗日志 — 数据处理不可追溯")

    return errors, warnings


def _render_pre_export_check(bundle: ResearchDeliverableBundle, session_state: dict):
    """导出前检查。"""
    exportable, reasons = bundle.is_exportable()

    if exportable:
        st.success("交付包可导出")
    else:
        st.error("交付包不可导出:")
        for r in reasons:
            st.markdown(f"- {r}")

    asset_errors, asset_warnings = _check_asset_completeness(bundle)
    if asset_errors:
        st.error("交付资产完整度 — 阻止导出:")
        for e in asset_errors:
            st.markdown(f"- ❌ {e}")
    if asset_warnings:
        st.warning("交付资产完整度 — 建议补充:")
        for w in asset_warnings:
            st.markdown(f"- ⚠️ {w}")
    if not asset_errors and not asset_warnings:
        st.success("交付资产完整度: 全部就绪")

    from src.utils.professional_consistency import check_consistency
    consistency_issues = check_consistency(bundle)
    cons_errors = [i for i in consistency_issues if i.level == "ERROR"]
    cons_warnings = [i for i in consistency_issues if i.level == "WARN"]
    if cons_errors:
        st.error("专业一致性检查 — 阻止导出:")
        for i in cons_errors:
            st.markdown(f"- ❌ **{i.title}**: {i.detail}")
            st.caption(f"  修复: {i.action}")
    if cons_warnings:
        st.warning("专业一致性检查 — 建议修复:")
        for i in cons_warnings:
            st.markdown(f"- ⚠️ **{i.title}**: {i.detail}")
    if not cons_errors and not cons_warnings:
        st.success("专业一致性检查: 全部通过")

    gate_result = run_export_gate(session_state)
    allowed, gate_reasons, issues = gate_result
    if not allowed:
        st.warning("导出门禁检查:")
        for r in gate_reasons:
            st.markdown(f"- {r}")


def _render_export(bundle: ResearchDeliverableBundle, session_state: dict):
    """导出操作。"""
    exportable, reasons = bundle.is_exportable()

    mode_label = st.radio("导出模式", list(EXPORT_MODES.keys()), horizontal=True)
    mode = EXPORT_MODES[mode_label]

    st.markdown(f"**{mode_label}包含:**")
    for item in EXPORT_MODE_CONTENTS[mode]:
        st.markdown(f"- {item}")

    if not exportable:
        st.error("当前不满足导出条件")
        for r in reasons:
            st.markdown(f"  - {r}")
        return

    export_format = st.radio("导出格式", ["Markdown", "Word (.docx)", "PDF", "ZIP 完整包"], horizontal=True)

    if st.button(f"📥 生成{mode_label}交付包", type="primary"):
        if export_format == "Markdown":
            content = _generate_export_content(bundle, mode)
            st.download_button(
                f"下载 {mode_label} (Markdown)",
                content,
                f"research_deliverable_{mode}.md",
                "text/markdown",
            )
        elif export_format == "Word (.docx)":
            try:
                from src.output.docx_exporter import build_deliverable_docx
                docx_bytes = build_deliverable_docx(bundle, mode=mode)
                st.download_button(
                    f"下载 {mode_label} (Word)",
                    docx_bytes,
                    f"research_deliverable_{mode}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            except Exception as e:
                st.error(f"Word 导出失败: {e}")
        elif export_format == "PDF":
            try:
                from src.output.pdf_exporter import convert_docx_to_pdf, check_pdf_availability
                available, method_name = check_pdf_availability()
                if not available:
                    st.warning("当前环境不支持自动 PDF 转换。请先导出 Word 文件后手动另存为 PDF。")
                    st.info("支持的转换工具：Microsoft Word (Windows) 或 LibreOffice (跨平台)")
                else:
                    from src.output.docx_exporter import build_deliverable_docx
                    docx_bytes = build_deliverable_docx(bundle, mode=mode)
                    pdf_result = convert_docx_to_pdf(docx_bytes)
                    if pdf_result.success:
                        st.download_button(
                            f"下载 {mode_label} (PDF)",
                            pdf_result.pdf_bytes,
                            f"research_deliverable_{mode}.pdf",
                            "application/pdf",
                        )
                        st.caption(f"转换方式: {pdf_result.method}")
                    else:
                        st.error(f"PDF 转换失败: {pdf_result.error}")
                        if pdf_result.suggestion:
                            st.info(pdf_result.suggestion)
            except Exception as e:
                st.error(f"PDF 导出异常: {e}")
        else:
            try:
                from src.output.zip_exporter import build_deliverable_zip
                zip_bytes = build_deliverable_zip(bundle, mode=mode)
                st.download_button(
                    f"下载 {mode_label} (ZIP)",
                    zip_bytes,
                    f"research_deliverable_{mode}.zip",
                    "application/zip",
                )
            except Exception as e:
                st.error(f"ZIP 导出失败: {e}")

    meta_json = json.dumps(bundle.export_meta_dict(), ensure_ascii=False, indent=2)
    st.download_button("📋 下载导出元数据", meta_json, "export_meta.json", "application/json")


def _generate_export_content(bundle: ResearchDeliverableBundle, mode: str) -> str:
    """根据模式生成导出内容。"""
    sections = []
    sections.append(f"# {bundle.title}\n")
    sections.append(f"导出模式: {mode} | 生成时间: {bundle.created_at}\n")

    if bundle.paper_bundle:
        sections.append("---\n## 论文正文\n")
        for key, sec in bundle.paper_bundle.sections.items():
            sections.append(f"### {sec.name}\n")
            sections.append(sec.markdown + "\n")

    if mode in ("standard", "full") and bundle.analysis_cards:
        sections.append("---\n## 统计结果卡\n")
        for card in bundle.analysis_cards:
            if hasattr(card, "to_markdown"):
                sections.append(card.to_markdown() + "\n")
            elif isinstance(card, dict):
                sections.append(f"- {card.get('method', 'unknown')}: {card.get('apa_text', '')}\n")

    if mode in ("standard", "full") and bundle.evidence_records:
        sections.append("---\n## 文献证据表\n")
        for rec in bundle.evidence_records:
            if isinstance(rec, dict):
                sections.append(f"- [{rec.get('citation_key', '')}] {rec.get('claim', '')}\n")

    if mode in ("standard", "full") and bundle.data_cleaning_log:
        sections.append("---\n## 数据清洗日志\n")
        for entry in bundle.data_cleaning_log:
            if isinstance(entry, dict):
                sections.append(f"- {entry.get('step', '')}: {entry.get('action', '')}\n")

    if mode == "full":
        if bundle.method_recommendations:
            sections.append("---\n## 方法推荐记录\n")
            for rec in bundle.method_recommendations:
                if isinstance(rec, dict):
                    sections.append(f"- {rec.get('recommendation', '')}\n")

        if bundle.health_report:
            sections.append("---\n## 项目健康报告\n")
            for issue in bundle.health_report:
                if isinstance(issue, dict):
                    sections.append(f"- [{issue.get('level', '')}] {issue.get('message', '')}\n")

        if bundle.ai_diff_log:
            sections.append("---\n## AI 差异选择记录\n")
            sections.append(f"```json\n{json.dumps(bundle.ai_diff_log, ensure_ascii=False, indent=2)}\n```\n")

    return "\n".join(sections)


def get_deliverable_bundle(session_state: dict) -> ResearchDeliverableBundle | None:
    """获取当前交付包（供外部使用）。"""
    return session_state.get(_BUNDLE_KEY)
