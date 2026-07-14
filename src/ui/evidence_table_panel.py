"""文献证据表 Streamlit 面板。

在文献审核后提供证据管理：创建、编辑、章节绑定、覆盖率检查、BibTeX/RIS 导入导出。
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.literature.evidence_record import EvidenceRecord, EvidenceStore
from src.literature.bibtex_ris_io import (
    BibEntry,
    parse_bibtex,
    parse_ris,
    entries_to_bibtex,
    entries_to_ris,
)

_STORE_KEY = "evidence_store"
_SECTION_OPTIONS = ["introduction", "method", "discussion", "limitation"]
_SECTION_LABELS = {
    "introduction": "引言",
    "method": "方法",
    "discussion": "讨论",
    "limitation": "局限",
}


def _get_store(session_state: dict) -> EvidenceStore:
    if _STORE_KEY not in session_state or session_state[_STORE_KEY] is None:
        session_state[_STORE_KEY] = EvidenceStore()
    return session_state[_STORE_KEY]


def render_evidence_table_panel(session_state: dict | None = None):
    """渲染证据表面板。"""
    if session_state is None:
        session_state = st.session_state

    st.subheader("📋 文献证据表")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["证据列表", "添加证据", "覆盖率检查", "引用导入导出", "🔍 证据质量"]
    )

    store = _get_store(session_state)

    with tab1:
        _render_evidence_list(store)
    with tab2:
        _render_add_evidence(store, session_state)
    with tab3:
        _render_coverage_check(store, session_state)
    with tab4:
        _render_import_export(store, session_state)
    with tab5:
        _render_evidence_quality(store, session_state)


def _render_evidence_list(store: EvidenceStore):
    """证据列表视图。"""
    if not store.records:
        st.info("暂无证据记录。从【添加证据】开始整理文献证据。")
        return

    filter_section = st.selectbox(
        "按章节筛选",
        ["全部"] + [_SECTION_LABELS.get(s, s) for s in _SECTION_OPTIONS],
    )

    records = store.records
    if filter_section != "全部":
        section_key = next(
            (k for k, v in _SECTION_LABELS.items() if v == filter_section), ""
        )
        records = store.get_by_section(section_key)

    st.caption(f"共 {len(records)} 条证据")
    for i, rec in enumerate(records):
        with st.expander(f"[{rec.citation_key}] {rec.claim}"):
            if rec.evidence_quote:
                st.markdown(f"> {rec.evidence_quote}")
            col1, col2 = st.columns(2)
            with col1:
                if rec.research_design:
                    st.markdown(f"**研究设计**: {rec.research_design}")
                if rec.sample:
                    st.markdown(f"**样本**: {rec.sample}")
            with col2:
                if rec.section_target:
                    st.markdown(f"**章节**: {_SECTION_LABELS.get(rec.section_target, rec.section_target)}")
                if rec.tags:
                    st.markdown(f"**标签**: {', '.join(rec.tags)}")
            if rec.main_findings:
                st.markdown(f"**主要发现**: {rec.main_findings}")

    md = store.to_markdown()
    st.download_button("📥 导出证据表 (Markdown)", md, "evidence_table.md", "text/markdown")
    csv_data = store.to_csv()
    st.download_button("📥 导出证据表 (CSV)", csv_data, "evidence_table.csv", "text/csv")


def _render_add_evidence(store: EvidenceStore, session_state: dict):
    """添加新证据记录。"""
    st.markdown("### 新增证据记录")

    with st.form("add_evidence_form"):
        citation_key = st.text_input("引用键 (如 wang2023)")
        claim = st.text_area("支撑论点", placeholder="该文献支撑什么观点？")
        evidence_quote = st.text_area("原文引用", placeholder="关键数据或结论原文")
        section = st.selectbox(
            "绑定章节",
            _SECTION_OPTIONS,
            format_func=lambda s: _SECTION_LABELS.get(s, s),
        )
        col1, col2 = st.columns(2)
        with col1:
            research_design = st.text_input("研究设计", placeholder="如：横断面问卷")
            sample = st.text_input("样本", placeholder="如：大学生 N=300")
        with col2:
            main_findings = st.text_input("主要发现")
            tags_str = st.text_input("标签（逗号分隔）")

        submitted = st.form_submit_button("➕ 添加证据")
        if submitted and citation_key and claim:
            tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
            record = EvidenceRecord(
                literature_id=f"lit_{len(store.records) + 1:03d}",
                citation_key=citation_key,
                claim=claim,
                evidence_quote=evidence_quote,
                section_target=section,
                research_design=research_design,
                sample=sample,
                main_findings=main_findings,
                tags=tags,
            )
            store.add(record)
            st.success(f"已添加: [{citation_key}] {claim[:30]}...")


def _render_coverage_check(store: EvidenceStore, session_state: dict):
    """引用覆盖率检查。"""
    st.markdown("### 引用覆盖率")
    cited_input = st.text_area(
        "论文中引用的引用键（每行一个）",
        placeholder="wang2023\nli2022\nzhang2021",
    )

    if st.button("检查覆盖率"):
        cited_keys = [k.strip() for k in cited_input.splitlines() if k.strip()]
        if cited_keys:
            result = store.check_citation_coverage(cited_keys)
            rate = result["coverage_rate"]
            color = "🟢" if rate >= 0.8 else ("🟡" if rate >= 0.5 else "🔴")
            st.metric("覆盖率", f"{color} {rate:.0%}")

            if result["covered"]:
                st.success(f"已覆盖: {', '.join(result['covered'])}")
            if result["missing"]:
                st.error(f"缺失证据: {', '.join(result['missing'])}")
        else:
            st.warning("请输入引用键")


def _render_import_export(store: EvidenceStore, session_state: dict):
    """BibTeX/RIS 导入导出。"""
    st.markdown("### 导入")
    import_format = st.radio("格式", ["BibTeX", "RIS"], horizontal=True)
    uploaded = st.text_area(
        f"粘贴 {import_format} 内容",
        height=150,
        placeholder="@article{...}" if import_format == "BibTeX" else "TY  - JOUR\n...",
    )
    if st.button("📤 导入"):
        if uploaded.strip():
            entries = parse_bibtex(uploaded) if import_format == "BibTeX" else parse_ris(uploaded)
            for e in entries:
                store.add(EvidenceRecord(
                    literature_id=f"imported_{e.citation_key}",
                    citation_key=e.citation_key or e.author.split(",")[0] + e.year if e.author else f"entry_{len(store.records)}",
                    claim=e.title,
                    section_target="introduction",
                ))
            st.success(f"导入 {len(entries)} 条文献")
        else:
            st.warning("请粘贴内容")

    st.markdown("### 导出")
    if store.records:
        bib_entries = [
            BibEntry(citation_key=r.citation_key, title=r.claim, year="")
            for r in store.records
        ]
        bibtex_text = entries_to_bibtex(bib_entries)
        ris_text = entries_to_ris(bib_entries)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 BibTeX", bibtex_text, "references.bib", "text/plain")
        with col2:
            st.download_button("📥 RIS", ris_text, "references.ris", "text/plain")


def _render_evidence_quality(store: EvidenceStore, session_state: dict):
    """证据质量分层与引用审计。"""
    from src.utils.evidence_quality import grade_evidence, audit_citations, generate_quality_report

    if not store.records:
        st.info("暂无证据记录，添加证据后可进行质量评估。")
        return

    st.markdown("### 证据质量评估")

    report = generate_quality_report(
        store.records,
        paper_text=session_state.get("paper_draft", ""),
        cards=session_state.get("result_cards", []),
    )

    grade_colors = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🔴", "Missing": "⚫"}

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("证据总数", len(report.grades))
    with col2:
        high_quality = sum(1 for g in report.grades if g.grade in ("A", "B"))
        st.metric("高质量 (A/B)", high_quality)
    with col3:
        issues = len(report.audit_issues)
        st.metric("审计问题", issues)

    filter_grade = st.selectbox(
        "按质量等级筛选",
        ["全部", "A", "B", "C", "D", "Missing"],
    )

    for g in report.grades:
        if filter_grade != "全部" and g.grade != filter_grade:
            continue
        icon = grade_colors.get(g.grade, "⚪")
        label = f"{icon} [{g.grade}] {g.citation_key}"
        with st.expander(label):
            st.markdown(f"**等级**: {g.grade}")
            if g.dimensions:
                cols = st.columns(4)
                dim_labels = {"source": "来源", "recency": "时效", "relevance": "相关性", "completeness": "完整性"}
                for i, (dim, score) in enumerate(g.dimensions.items()):
                    with cols[i % 4]:
                        st.progress(min(score / 100, 1.0), text=f"{dim_labels.get(dim, dim)}: {score}")
            if g.reasons:
                for reason in g.reasons:
                    st.caption(f"• {reason}")

    if report.audit_issues:
        st.markdown("### 引用审计问题")
        level_icons = {"ERROR": "🔴", "WARN": "🟡", "INFO": "ℹ️"}
        for issue in report.audit_issues:
            icon = level_icons.get(issue.level, "•")
            st.markdown(f"{icon} **{issue.title}**")
            st.caption(f"{issue.detail}")
            if issue.action:
                st.markdown(f"  → 建议: {issue.action}")

    st.markdown("---")
    summary_text = report.summary if hasattr(report, "summary") and report.summary else "质量评估完成"
    st.info(summary_text)


def get_evidence_store(session_state: dict) -> EvidenceStore:
    """获取当前证据库（供外部使用）。"""
    return _get_store(session_state)
