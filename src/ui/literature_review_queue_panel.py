"""文献审核队列 Streamlit 面板。

把 review_queue_ui.py 的数据转换层接入 Streamlit，
用户可在此完成文献候选的纳入/排除/待定/合并和查看历史。
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from src.literature_feed.review_queue_ui import (
    QueueItem,
    QueueSummary,
    ReviewAction,
    REJECTION_REASON_LABELS,
    STATUS_LABELS,
    build_queue_items,
    compute_queue_summary,
    filter_queue,
    format_review_event,
)
from src.literature_feed.review_service import (
    ReviewDecision,
    review_candidate,
    bulk_review_candidates,
    list_review_events,
)


def render_review_queue(store: Any) -> None:
    """文献审核队列主入口。"""
    st.subheader("📋 文献审核队列")

    rows = _load_candidates(store)
    items = build_queue_items(rows)

    _render_summary_bar(items)

    filtered = _render_filters(items)
    if not filtered:
        st.info("当前筛选条件下无待处理文献。")
        return

    _render_queue_list(store, filtered)
    _render_review_history(store)


def render_review_sidebar_badge(store: Any) -> None:
    """侧栏审核进度摘要。"""
    rows = _load_candidates(store)
    items = build_queue_items(rows)
    summary = compute_queue_summary(items)

    if summary.pending > 0:
        st.sidebar.metric("待审核文献", summary.pending)
    if summary.total > 0:
        st.sidebar.progress(
            summary.review_progress,
            text=f"审核进度 {summary.review_progress:.0%}",
        )


# ---------------------------------------------------------------------------
# 内部实现
# ---------------------------------------------------------------------------


def _load_candidates(store: Any) -> list[dict]:
    """从 store 加载候选文献。"""
    conn = store.connection
    rows = conn.execute(
        "SELECT * FROM llm_candidates ORDER BY candidate_id DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def _render_summary_bar(items: list[QueueItem]) -> None:
    """展示审核进度统计卡。"""
    summary = compute_queue_summary(items)
    cols = st.columns(5)
    cols[0].metric("总计", summary.total)
    cols[1].metric("待审核", summary.pending)
    cols[2].metric("已纳入", summary.approved)
    cols[3].metric("已排除", summary.rejected)
    cols[4].metric("待定/合并", summary.deferred + summary.merged)


def _render_filters(items: list[QueueItem]) -> list[QueueItem]:
    """筛选控件，返回筛选后列表。"""
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "状态筛选",
            options=["全部"] + list(STATUS_LABELS.keys()),
            format_func=lambda x: STATUS_LABELS.get(x, "全部"),
            key="rq_status_filter",
        )
    with col2:
        sources = sorted({i.source for i in items if i.source})
        source_filter = st.selectbox(
            "来源筛选",
            options=["全部"] + sources,
            key="rq_source_filter",
        )
    with col3:
        min_rel = st.slider("最低相关度", 0.0, 1.0, 0.0, 0.1, key="rq_min_rel")

    return filter_queue(
        items,
        status=status_filter if status_filter != "全部" else None,
        source=source_filter if source_filter != "全部" else None,
        min_relevance=min_rel,
    )


def _render_queue_list(store: Any, items: list[QueueItem]) -> None:
    """渲染文献队列列表和操作区。"""
    for item in items:
        with st.expander(item.display_title, expanded=(item.status == "pending")):
            _render_candidate_detail(item)
            if item.status == "pending":
                _render_review_actions(store, item)
            elif item.status == "deferred":
                _render_review_actions(store, item)


def _render_candidate_detail(item: QueueItem) -> None:
    """展示单条文献详情。"""
    if item.authors:
        st.caption(f"👤 {item.authors}  |  📅 {item.year}  |  📂 {item.source}")
    if item.abstract:
        st.markdown(f"**摘要**: {item.abstract[:300]}{'...' if len(item.abstract) > 300 else ''}")
    if item.relevance_score > 0:
        st.progress(item.relevance_score, text=f"相关度: {item.relevance_score:.2f}")


def _render_review_actions(store: Any, item: QueueItem) -> None:
    """审核操作按钮组。"""
    st.markdown("---")
    cols = st.columns(4)

    with cols[0]:
        if st.button("✅ 纳入", key=f"approve_{item.candidate_id}"):
            _do_review(store, item.candidate_id, "approved")

    with cols[1]:
        if st.button("⏸️ 待定", key=f"defer_{item.candidate_id}"):
            _do_review(store, item.candidate_id, "deferred")

    with cols[2]:
        reason = st.selectbox(
            "排除原因",
            options=list(REJECTION_REASON_LABELS.keys()),
            format_func=lambda x: REJECTION_REASON_LABELS[x],
            key=f"reject_reason_{item.candidate_id}",
        )
        if st.button("❌ 排除", key=f"reject_{item.candidate_id}"):
            _do_review(store, item.candidate_id, "rejected", rejection_reason=reason)

    with cols[3]:
        target = st.text_input("合并目标 ID", key=f"merge_target_{item.candidate_id}")
        if st.button("🔗 合并", key=f"merge_{item.candidate_id}"):
            if not target:
                st.error("合并操作必须填写目标文献 ID")
            else:
                _do_review(store, item.candidate_id, "merged", target_kb_id=target)


def _do_review(
    store: Any,
    candidate_id: int,
    decision: str,
    *,
    rejection_reason: str | None = None,
    target_kb_id: str | None = None,
) -> None:
    """执行审核操作（带前端校验）。"""
    action = ReviewAction(
        candidate_id=candidate_id,
        decision=decision,
        reviewer="user",
        rejection_reason=rejection_reason,
        target_kb_id=target_kb_id,
    )
    errors = action.validate()
    if errors:
        for e in errors:
            st.error(e)
        return

    try:
        review_candidate(
            store, candidate_id, decision, "user",
            rejection_reason=rejection_reason,
            target_kb_id=target_kb_id,
        )
        st.success(f"已{STATUS_LABELS.get(decision, decision)}")
        st.rerun()
    except Exception as e:
        st.error(f"审核失败: {e}")


def _render_review_history(store: Any) -> None:
    """展示审核历史事件。"""
    with st.expander("📜 审核历史", expanded=False):
        events = list_review_events(store, limit=50)
        if not events:
            st.caption("暂无审核记录。")
            return
        for evt in events:
            formatted = format_review_event(evt)
            st.markdown(
                f"**{formatted['时间']}** — {formatted['审核人']} "
                f"将文献 {formatted['操作']}（原: {formatted['原状态']}）"
            )
            if formatted["原因"]:
                st.caption(f"原因: {formatted['原因']}")
