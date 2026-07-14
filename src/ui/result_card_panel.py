"""统计结果卡 Streamlit 面板。

在分析结果后展示 AnalysisResultCard：APA 文本、效应量、假设检查状态、warning。
支持复制 APA 文本、导出 Markdown、插入论文结果章。
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from src.analysis.result_card import AnalysisResultCard, build_card_from_output


def render_result_card(analysis_output: dict[str, Any]) -> Optional[AnalysisResultCard]:
    """分析结果后渲染结果卡。返回构建的卡片供后续引用。

    如果当前方法不支持结果卡，显示提示但不报错。
    """
    card = build_card_from_output(analysis_output)
    if card is None:
        st.info("💡 当前统计方法暂未覆盖结果卡，后续版本将支持更多方法。")
        return None

    _render_card_content(card)
    return card


def render_result_card_from_card(card: AnalysisResultCard) -> None:
    """直接从已构建的 card 渲染（用于从 session_state 恢复）。"""
    _render_card_content(card)


# ---------------------------------------------------------------------------
# 内部渲染
# ---------------------------------------------------------------------------


def _render_card_content(card: AnalysisResultCard) -> None:
    """渲染结果卡主体内容。"""
    st.markdown("### 📊 统计结果卡")

    # 方法信息
    st.markdown(f"**方法**: {card.method_name}")

    # 变量角色
    if card.variables:
        var_parts = [f"{k}: {v}" for k, v in card.variables.items()]
        st.markdown(f"**变量**: {' | '.join(var_parts)}")

    # 假设检查状态
    _render_assumption_status(card)

    # APA 文本（核心展示）
    _render_apa_text(card)

    # 效应量
    if card.effect_sizes:
        st.markdown("**效应量**:")
        for es in card.effect_sizes:
            if isinstance(es, dict):
                st.markdown(f"- {es.get('name', '')}: {es.get('value', '')}")
            else:
                st.markdown(f"- {es}")

    # 通俗解释
    if card.plain_language_summary:
        with st.expander("💬 通俗解释", expanded=True):
            st.markdown(card.plain_language_summary)

    # Warnings
    _render_warnings(card)

    # 操作按钮
    _render_actions(card)


def _render_assumption_status(card: AnalysisResultCard) -> None:
    """渲染前提假设检查状态。"""
    if not card.assumption_status:
        return

    status = card.assumption_status
    if status == "met":
        st.success("✅ 前提假设满足")
    elif status == "violated":
        st.warning("⚠️ 前提假设不满足，结果需谨慎解读")
    elif status == "partial":
        st.info("ℹ️ 部分前提假设满足")
    elif status == "not_checked":
        st.caption("前提假设未检查")


def _render_apa_text(card: AnalysisResultCard) -> None:
    """渲染 APA 格式结果文本（支持复制）。"""
    if not card.apa_text:
        return

    st.markdown("**APA 结果报告**:")
    st.code(card.apa_text, language=None)


def _render_warnings(card: AnalysisResultCard) -> None:
    """渲染结果卡警告。"""
    if not card.warnings:
        return

    for w in card.warnings:
        st.warning(f"⚠️ {w}")


def _render_actions(card: AnalysisResultCard) -> None:
    """渲染操作按钮：复制 APA、导出 Markdown、插入论文。"""
    cols = st.columns(3)

    with cols[0]:
        if card.apa_text:
            st.download_button(
                "📋 导出 APA 文本",
                data=card.apa_text,
                file_name="apa_result.txt",
                mime="text/plain",
                key=f"copy_apa_{card.method_id}",
            )

    with cols[1]:
        md_content = card.to_markdown()
        st.download_button(
            "📄 导出 Markdown",
            data=md_content,
            file_name=f"result_card_{card.method_id}.md",
            mime="text/markdown",
            key=f"export_md_{card.method_id}",
        )

    with cols[2]:
        if st.button("📝 插入论文结果章", key=f"insert_{card.method_id}"):
            _insert_to_paper_bundle(card)


def _insert_to_paper_bundle(card: AnalysisResultCard) -> None:
    """将结果卡 APA 文本插入论文 Bundle 的结果章。"""
    bundle = st.session_state.get("paper_bundle")
    if bundle is None:
        st.warning("请先生成论文草稿，再插入结果。")
        return

    result_section = bundle.sections.get("result")
    if result_section:
        result_section.markdown += f"\n\n{card.apa_text}"
    else:
        from src.paper_writer.draft_bundle import PaperSection
        bundle.sections["result"] = PaperSection(
            name="结果",
            markdown=card.apa_text,
            source="data",
        )
    st.success("已插入论文结果章。")


def render_result_cards_list(cards: list[AnalysisResultCard]) -> None:
    """批量展示多个结果卡（用于项目汇总页面）。"""
    if not cards:
        st.info("暂无统计结果卡。")
        return

    st.markdown(f"### 已生成 {len(cards)} 张结果卡")
    for i, card in enumerate(cards):
        with st.expander(f"{card.method_name} — {card.apa_text[:60]}...", expanded=False):
            _render_card_content(card)
