"""文献综述工作台 UI（v3.4）：搜索栏 + 三栏布局 + 底部 tab。

入口：render_literature_review(tier="beginner")
- 顶部：搜索栏（自动填漏斗 research_q）+ 摘要信息
- 三栏：
  * 左：文献列表（按 relevance 排序，状态图标 📖📗📘）
  * 中：选中文献详情 + 阅读笔记编辑器
  * 右：文献矩阵（可切换全部/单篇）
- 底部 tab：📊 主题聚类 / 🕳️ Gap 分析 / 📝 导出综述
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

from src.utils.export_naming import export_filename as _efn

from src.literature_review.completeness import calculate_completeness
from src.literature_review.matrix import (
    add_literature_to_matrix,
    auto_fill_abstract_info,
    create_matrix,
    export_matrix_csv,
    render_matrix_html,
)
from src.literature_review.models import (
    NOTE_TYPES,
    GapAnalysis,
    LiteratureItem,
    LiteratureMatrix,
    ReadingNote,
    ThemeCluster,
)
from src.literature_review.notes import (
    create_note,
    delete_note,
    edit_note,
    export_notes_markdown,
    get_notes_by_literature,
    notes_from_dict_list,
    notes_to_dict_list,
)
from src.literature_review.search import (
    rescore_existing_items,
    search_literature,
    search_summary,
)
from src.literature_review.themes import (
    auto_cluster_themes,
    cluster_themes_with_meta,
    generate_gap_report,
    identify_gaps,
)
from src.literature_review.ingest import ingest_files
from src.literature_review.summarize import summarize_papers
from src.literature_review.synthesize import synthesize_review
from src.output.docx_exporter import build_review_docx
from src.utils.concurrency import SessionLock, ensure_tab_id
from src.utils.workspace import (
    LITERATURE_REVIEW_SESSION_KEY,
    get_literature_review_state,
    get_upstream_state,
)


# v3.6 文献综述写入资源锁
_LR_NOTES_LOCK = "literature_notes"
_LR_MATRIX_LOCK = "literature_matrix"
_LR_ITEMS_LOCK = "literature_items"


def _check_lock_or_warn(resource: str) -> bool:
    """检查锁；若被其他 tab 占用，显示警告并返回 False。"""
    lock = SessionLock(st.session_state)
    if lock.is_locked(resource, by_others=True):
        holder = lock.get_holder(resource)
        st.warning(
            f"⚠️ 当前数据正在另一个标签页中被编辑（持有者: {holder}）。"
            "请稍后再试或关闭其他标签页。"
        )
        return False
    # 尝试获取锁（即便没人锁也获取，TTL 30s 自动过期）
    my_id = ensure_tab_id(st.session_state)
    return lock.acquire(resource, holder_id=my_id, ttl=30)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def render_literature_review(tier: str = "beginner") -> None:
    """文献综述工作台主入口。"""
    upstream = get_upstream_state(st.session_state)
    lr_state = get_literature_review_state(st.session_state)

    _render_header(tier=tier)

    # v3.5: 完成度评分（顶部右上角）
    _render_completeness_badge(lr_state)

    # v3.5: 修订研究问题入口（跨 phase 反向修订）
    _render_revise_research_q_button(upstream, lr_state)

    # v4.7: 丢文献 → 自动写综述（常驻，无需先有文献）
    _render_drop_and_review_section(upstream)

    # 顶部：搜索栏
    _render_search_bar(upstream, lr_state)

    # v3.5: 漏斗修订后回到此页时触发 relevance rescore
    if st.session_state.get("_lr_pending_rescore"):
        _do_relevance_rescore(upstream, lr_state)
        st.session_state["_lr_pending_rescore"] = False

    # 三栏布局
    items = _materialize_items(lr_state.get("literature_items") or [])
    if items:
        col_left, col_mid, col_right = st.columns([2, 3, 3])
        with col_left:
            selected_key = _render_literature_list(items)
        with col_mid:
            _render_literature_detail(items, selected_key, lr_state)
        with col_right:
            _render_matrix_view(items, lr_state)
    else:
        st.info("👈 在上方点「🔍 搜索」开始；或手动添加文献。")

    # 底部 tabs
    if items:
        st.divider()
        tabs = st.tabs(["📊 主题聚类", "🕳️ Gap 分析", "📝 导出综述", "🚪 完成 → 进入 wizard"])
        with tabs[0]:
            _render_themes_tab(items, lr_state)
        with tabs[1]:
            _render_gaps_tab(upstream, lr_state)
        with tabs[2]:
            _render_export_tab(items, lr_state)
        with tabs[3]:
            _render_finish_tab()


# ---------------------------------------------------------------------------
# 顶部
# ---------------------------------------------------------------------------

def _render_revise_research_q_button(
    upstream: Dict[str, Any],
    lr_state: Dict[str, Any],
) -> None:
    """v3.5: 顶部「🔄 修订研究问题」按钮，回到漏斗修订选题。"""
    cols = st.columns([4, 1])
    with cols[1]:
        if st.button("🔄 修订研究问题", key="_lr_revise_rq",
                     help="回到漏斗修改研究问题，文献综述状态保留并重新打分"):
            st.session_state["_lr_revise_dialog"] = True

    if st.session_state.get("_lr_revise_dialog"):
        st.warning(
            "⚠️ 这将回到选题漏斗修改研究问题。\n\n"
            "当前文献综述状态会被保留，回来后系统会**根据新研究问题重新计算文献相关性**——"
            "部分文献可能从「高相关」降为「低相关」，请重新筛选。\n\n"
            "继续？"
        )
        cols_dialog = st.columns([1, 1, 1])
        if cols_dialog[0].button("✅ 微调现有研究问题（回到 stage 5）", key="_lr_rev_finetune", type="primary"):
            from src.utils.workspace import update_last_position
            upstream["phase"] = "funnel"
            upstream["current_stage"] = 5
            update_last_position("funnel", step=5, session_state=st.session_state)
            st.session_state["_lr_pending_rescore"] = True
            st.session_state["_lr_revise_dialog"] = False
            _save_workspace_now()
            st.rerun()
        if cols_dialog[1].button("🌱 重新选题（回到 stage 1）", key="_lr_rev_restart"):
            from src.utils.workspace import update_last_position
            upstream["phase"] = "funnel"
            upstream["current_stage"] = 1
            update_last_position("funnel", step=1, session_state=st.session_state)
            st.session_state["_lr_pending_rescore"] = True
            st.session_state["_lr_revise_dialog"] = False
            _save_workspace_now()
            st.rerun()
        if cols_dialog[2].button("取消", key="_lr_rev_cancel"):
            st.session_state["_lr_revise_dialog"] = False
            st.rerun()


def _do_relevance_rescore(upstream: Dict[str, Any], lr_state: Dict[str, Any]) -> None:
    """v3.5: 修订完研究问题回到此页时，基于新 research_q 重打分所有文献。"""
    items_raw = lr_state.get("literature_items") or []
    if not items_raw:
        return
    new_rq = upstream.get("research_question", "")
    candidate_vars = upstream.get("candidate_vars") or {}
    rescored = rescore_existing_items(items_raw, new_rq, candidate_vars)
    lr_state["literature_items"] = rescored
    st.success(
        "📊 文献相关性已根据新研究问题重新计算。"
        "请到左侧列表查看排名变化，重新筛选高相关文献。"
    )


def _save_workspace_now() -> None:
    try:
        from src.utils.autosave import trigger_autosave
        from src.utils.workspace import build_workspace_snapshot
        trigger_autosave(st.session_state, build_workspace_snapshot, force=True)
    except Exception:
        pass


def _render_completeness_badge(lr_state: Dict[str, Any]) -> None:
    """v3.5 完成度评分显示。"""
    try:
        result = calculate_completeness(lr_state)
    except Exception:
        return
    tone_map = {
        "优秀": "success",
        "良好": "warning",
        "及格": "warning",
        "不足": "danger",
    }
    tone = tone_map.get(result.grade, "neutral")
    cols = st.columns([3, 1])
    with cols[1]:
        st.markdown(
            f"""<div class="psy-score-badge psy-score-badge--{tone}">
            <strong>📊 完成度 {result.total:.0f}/100</strong><br>
            <span>{result.grade}</span></div>""",
            unsafe_allow_html=True,
        )
    with st.expander("📈 完成度子项详情", expanded=False):
        for sub in result.sub_scores:
            mark = "✅" if sub.score >= sub.weight * 0.8 else (
                "🟡" if sub.score > 0 else "⚪"
            )
            st.markdown(f"{mark} **{sub.name}**：{sub.score:.0f}/{sub.weight:.0f}")
            if sub.suggestion:
                st.caption(f"   {sub.suggestion}")


def _render_header(tier: str = "beginner") -> None:
    label = "（研究生模式）" if tier == "advanced" else ""
    st.markdown(
        f"""<div class="psy-hero psy-hero--info">
        <span class="psy-hero__eyebrow">证据工作流</span>
        <h3>📚 文献综述工作台 {label}</h3>
        <p class="psy-hero__lead">
        从已确定的研究问题出发，搜索 → 精读 → 矩阵 → 主题 → 识别 gap。
        所有笔记和矩阵随项目自动保存。
        </p></div>""",
        unsafe_allow_html=True,
    )


def _render_search_bar(upstream: Dict[str, Any], lr_state: Dict[str, Any]) -> None:
    """顶部搜索栏：自动填 research_q，点搜索调 search_literature。"""
    research_q = upstream.get("research_question", "")
    last_query = lr_state.get("last_search_query", "")

    cols = st.columns([5, 1, 1])
    with cols[0]:
        query = st.text_input(
            "搜索关键词（自动填入漏斗的研究问题，可编辑）",
            value=research_q or last_query,
            key="_lr_search_query",
        )
    with cols[1]:
        max_results = st.number_input(
            "结果数", min_value=5, max_value=50, value=20, step=5,
            key="_lr_max_results",
        )
    with cols[2]:
        st.write("")
        st.write("")
        do_search = st.button("🔍 搜索", type="primary", width="stretch",
                                key="_lr_do_search")

    if do_search and query.strip():
        with st.spinner(f"正在搜索「{query[:30]}...」（含中文文献）..."):
            try:
                result = search_literature(
                    research_q=query,
                    candidate_vars=upstream.get("candidate_vars") or {},
                    max_results=int(max_results),
                    include_chinese=True,
                )
                items = result["items"]
            except Exception as exc:
                st.error(f"搜索失败：{exc}")
                items, result = [], {"method": "offline", "sources": []}

        if items:
            lr_state["literature_items"] = [it.to_dict() for it in items]
            lr_state["last_search_query"] = query
            lr_state["last_search_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lr_state["last_search_method"] = result.get("method", "")
            sources_str = ", ".join(result.get("sources") or [])
            st.success(f"✓ 搜索成功（{sources_str}），去重后 {len(items)} 篇文献")
            st.rerun()
        else:
            st.warning("未找到结果，请尝试不同关键词。")

    # 显示上次搜索摘要
    if lr_state.get("last_search_query"):
        st.caption(
            f"📌 上次搜索：{lr_state['last_search_query'][:60]} "
            f"（{lr_state.get('last_search_at', '')}，"
            f"共 {len(lr_state.get('literature_items') or [])} 篇）"
        )


# ---------------------------------------------------------------------------
# 三栏：文献列表
# ---------------------------------------------------------------------------

def _render_literature_list(items: List[LiteratureItem]) -> Optional[str]:
    """左侧：文献列表，按 relevance 排序。返回当前选中的 literature_key。"""
    st.markdown("### 📖 文献列表")
    selected = st.session_state.get("_lr_selected_key")

    # 排序
    items_sorted = sorted(items, key=lambda x: -x.relevance_score)

    # 选项
    options = [it.key for it in items_sorted]
    labels = {
        it.key: f"{it.reading_status_emoji} ({it.relevance_score:.0%}) {it.short_citation[:50]}"
        for it in items_sorted
    }
    if not selected or selected not in options:
        selected = options[0] if options else None

    chosen = st.radio(
        "选择文献查看详情",
        options=options,
        format_func=lambda k: labels.get(k, k),
        key="_lr_lit_radio",
        index=options.index(selected) if selected in options else 0,
        label_visibility="collapsed",
    )
    st.session_state["_lr_selected_key"] = chosen

    # 一键标记高相关（>=0.5）
    if st.button("⭐ 标记高相关（>=0.5）", key="_lr_mark_high"):
        for it in items_sorted:
            if it.relevance_score >= 0.5:
                it.tags = list(set(it.tags + ["高相关"]))
        # 写回
        _persist_items(items_sorted)
        st.success("已标记")
        st.rerun()

    return chosen


# ---------------------------------------------------------------------------
# 三栏：文献详情 + 笔记编辑器
# ---------------------------------------------------------------------------

def _render_literature_detail(
    items: List[LiteratureItem],
    selected_key: Optional[str],
    lr_state: Dict[str, Any],
) -> None:
    st.markdown("### 📑 文献详情 + 笔记")
    if not selected_key:
        st.info("请在左侧选择文献")
        return

    item = next((it for it in items if it.key == selected_key), None)
    if not item:
        st.warning("未找到该文献")
        return

    # 元信息
    st.markdown(f"**{item.title}**")
    st.caption(
        f"{', '.join(item.authors[:3])} ({item.year}) · "
        f"{item.journal} · 引用 {item.citation_count}"
    )
    if item.doi:
        st.markdown(f"DOI: [{item.doi}](https://doi.org/{item.doi})")

    # 阅读状态
    status_options = ["unread", "reading", "done"]
    status_labels = {"unread": "📖 未读", "reading": "📗 在读", "done": "📘 已读"}
    new_status = st.selectbox(
        "阅读状态",
        options=status_options,
        format_func=lambda s: status_labels[s],
        index=status_options.index(item.reading_status) if item.reading_status in status_options else 0,
        key=f"_lr_status_{item.key}",
    )
    if new_status != item.reading_status:
        item.reading_status = new_status
        _persist_items(items)
        st.rerun()

    if item.abstract:
        with st.expander("📜 摘要", expanded=False):
            st.write(item.abstract)

    # v3.5 自审批注显示（如有）
    raw_dict = next(
        (d for d in (lr_state.get("literature_items") or [])
         if isinstance(d, dict) and d.get("key") == item.key),
        None,
    )
    if raw_dict and raw_dict.get("review_comments"):
        with st.expander(f"💬 自审批注（{len(raw_dict['review_comments'])} 条）", expanded=True):
            for c in raw_dict["review_comments"]:
                st.markdown(f"- {c.get('text', '')} _（{c.get('imported_at', '')}）_")

    # 笔记编辑器
    st.markdown("#### 📝 阅读笔记")
    notes = notes_from_dict_list(lr_state.get("notes") or [])
    lit_notes = get_notes_by_literature(notes, item.key)

    # 现有笔记
    for n in lit_notes:
        with st.container():
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(f"**[{n.type}]** {n.page_or_section or ''}")
                edited = st.text_area(
                    "笔记内容",
                    value=n.content,
                    key=f"_lr_note_edit_{n.note_id}",
                    height=80,
                    label_visibility="collapsed",
                )
                if edited != n.content:
                    edit_note(notes, n.note_id, edited)
                    lr_state["notes"] = notes_to_dict_list(notes)
            with col_b:
                if st.button("🗑️", key=f"_lr_note_del_{n.note_id}", help="删除"):
                    delete_note(notes, n.note_id)
                    lr_state["notes"] = notes_to_dict_list(notes)
                    st.rerun()
            st.divider()

    # 新建笔记
    with st.expander("➕ 添加笔记", expanded=False):
        new_type = st.selectbox("类型", NOTE_TYPES, key=f"_lr_new_type_{item.key}")
        new_page = st.text_input("页码/章节（可选）", key=f"_lr_new_page_{item.key}")
        new_content = st.text_area("内容", key=f"_lr_new_content_{item.key}", height=100)
        if st.button("保存笔记", key=f"_lr_save_note_{item.key}", type="primary"):
            if new_content.strip():
                # v3.6 SessionLock 保护
                if _check_lock_or_warn(_LR_NOTES_LOCK):
                    create_note(
                        notes, literature_key=item.key,
                        content=new_content.strip(), type=new_type,
                        page_or_section=new_page.strip(),
                    )
                    lr_state["notes"] = notes_to_dict_list(notes)
                    st.rerun()


# ---------------------------------------------------------------------------
# 三栏：矩阵视图
# ---------------------------------------------------------------------------

def _render_matrix_view(items: List[LiteratureItem], lr_state: Dict[str, Any]) -> None:
    st.markdown("### 📊 文献矩阵")
    matrix_data = lr_state.get("matrix") or {}
    matrix = LiteratureMatrix.from_dict(matrix_data)

    # 同步：确保矩阵覆盖所有当前文献
    for it in items:
        if it.key not in matrix.cells:
            add_literature_to_matrix(matrix, it)

    # 维度管理
    with st.expander("⚙️ 自定义维度", expanded=False):
        new_dim = st.text_input("新增维度", key="_lr_new_dim")
        if st.button("➕ 添加维度", key="_lr_add_dim") and new_dim.strip():
            matrix.add_dimension(new_dim.strip())
            lr_state["matrix"] = matrix.to_dict()
            st.rerun()
        for d in list(matrix.dimensions):
            cols = st.columns([3, 1])
            cols[0].write(f"- {d}")
            if cols[1].button("🗑️", key=f"_lr_rm_dim_{d}"):
                matrix.remove_dimension(d)
                lr_state["matrix"] = matrix.to_dict()
                st.rerun()

    # 一键自动填充（v3.5: LLM 优先，正则兜底；v3.6: 加锁保护）
    cols_fill = st.columns([2, 1])
    use_llm_fill = cols_fill[0].checkbox("✨ 用 LLM 提取（更准确，需 API key）",
                                           value=True, key="_lr_use_llm_fill")
    if cols_fill[1].button("一键自动填充", key="_lr_auto_fill", type="primary"):
        if _check_lock_or_warn(_LR_MATRIX_LOCK):
            filled_count = 0
            method_counts = {"llm": 0, "regex": 0}
            llm_cfg = _get_llm_config() if use_llm_fill else None
            for it in items:
                if it.abstract:
                    result = auto_fill_abstract_info(
                        it, matrix, overwrite=False,
                        use_llm=use_llm_fill,
                        llm_config=llm_cfg,
                    )
                    filled_count += len(result["extracted"])
                    method_counts[result["method"]] = method_counts.get(result["method"], 0) + 1
            lr_state["matrix"] = matrix.to_dict()
            method_summary = (
                f"LLM 提取 {method_counts.get('llm', 0)} 篇 + "
                f"正则提取 {method_counts.get('regex', 0)} 篇"
            )
            st.success(f"已自动填充 {filled_count} 个单元格（{method_summary}）")
            st.rerun()

    # 渲染矩阵
    if matrix.cells:
        lookup = {it.key: it for it in items}
        html = render_matrix_html(matrix, literature_lookup=lookup)
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("矩阵为空——添加文献到矩阵或新建维度后查看")

    # 写回（确保维度同步即便没有自动填充）
    lr_state["matrix"] = matrix.to_dict()


# ---------------------------------------------------------------------------
# 底部 tabs
# ---------------------------------------------------------------------------

def _render_themes_tab(items: List[LiteratureItem], lr_state: Dict[str, Any]) -> None:
    st.markdown("### 📊 主题聚类")
    st.caption("基于阅读笔记自动识别 2-4 个主要主题。先添加 ≥4 条笔记再聚类。")

    # v3.5 显示当前所用方法
    last_method = lr_state.get("last_cluster_method", "")
    if last_method:
        method_display = {
            "kmeans": ("🧠 KMeans 自动聚类（基于 TF-IDF）", "info"),
            "keyword_overlap": ("⚠️ sklearn 不可用，使用关键词重叠分组（结果仅供参考）", "warning"),
            "by_literature": ("📑 笔记数较少，按文献分组", "info"),
            "empty": ("尚无聚类结果", "info"),
        }.get(last_method, (f"方法：{last_method}", "info"))
        if method_display[1] == "warning":
            st.warning(method_display[0])
        else:
            st.info(method_display[0])

    notes = notes_from_dict_list(lr_state.get("notes") or [])
    if not notes:
        st.info("尚无阅读笔记，无法聚类。请先在中间面板添加笔记。")
        return

    cols = st.columns([1, 1, 3])
    n_clusters = cols[0].number_input("聚类数", min_value=2, max_value=6, value=3, key="_lr_n_clusters")
    if cols[1].button("🚀 自动聚类", key="_lr_run_cluster"):
        with st.spinner("正在聚类..."):
            result = cluster_themes_with_meta(notes, n_clusters=int(n_clusters))
        themes = result["themes"]
        lr_state["themes"] = [t.to_dict() for t in themes]
        lr_state["last_cluster_method"] = result["method"]
        st.success(f"✓ 识别出 {len(themes)} 个主题（方法：{result['method']}）")
        st.rerun()

    themes = [ThemeCluster.from_dict(t) for t in (lr_state.get("themes") or [])]
    if not themes:
        return

    for t in themes:
        with st.container():
            st.markdown(f"#### {t.theme_name}")
            st.write(f"**关键词**：{', '.join(t.centroid_keywords)}")
            st.caption(t.summary)
            if t.literature_keys:
                with st.expander(f"📑 涉及文献（{len(t.literature_keys)}）", expanded=False):
                    lookup = {it.key: it for it in items}
                    for k in t.literature_keys:
                        item = lookup.get(k)
                        if item:
                            st.markdown(f"- {item.short_citation}")
            st.divider()


def _render_gaps_tab(upstream: Dict[str, Any], lr_state: Dict[str, Any]) -> None:
    st.markdown("### 🕳️ Gap 分析")
    st.caption("识别已有文献尚未充分覆盖的研究空白。")

    # v3.5 显示当前所用方法
    last_source = lr_state.get("last_gap_source", "")
    if last_source == "llm":
        st.info("💡 当前 Gap 基于 LLM 深度分析")
    elif last_source == "heuristic":
        st.warning(
            "⚠️ 当前 LLM 不可用，仅基于矩阵空白和「疑问」类型笔记检测，可能遗漏部分 gap"
        )

    research_q = upstream.get("research_question", "")
    notes = notes_from_dict_list(lr_state.get("notes") or [])
    matrix = LiteratureMatrix.from_dict(lr_state.get("matrix") or {})

    if st.button("🔍 识别 Gap", key="_lr_identify_gap", type="primary"):
        with st.spinner("正在分析..."):
            llm_config = _get_llm_config()
            gaps = identify_gaps(
                research_q=research_q,
                notes=notes,
                matrix=matrix,
                llm_config=llm_config,
            )
        lr_state["gaps"] = [g.to_dict() for g in gaps]
        # 记录所用方法（gap.source 已含 llm/heuristic）
        if gaps:
            lr_state["last_gap_source"] = gaps[0].source
        st.rerun()

    gaps = [GapAnalysis.from_dict(g) for g in (lr_state.get("gaps") or [])]
    if not gaps:
        st.info("点上方按钮开始分析。LLM 不可用时自动降级到启发式。")
        return

    for i, g in enumerate(gaps, 1):
        with st.container():
            st.markdown(f"#### Gap {i} _(来源: {g.source}, 置信度 {g.confidence:.0%})_")
            st.write(g.gap_description)
            if g.supporting_notes:
                with st.expander("支撑证据", expanded=False):
                    for note in g.supporting_notes:
                        st.markdown(f"- {note}")
            if g.suggested_direction:
                st.info(f"💡 建议方向：{g.suggested_direction}")
            st.divider()


def _render_export_tab(items: List[LiteratureItem], lr_state: Dict[str, Any]) -> None:
    st.markdown("### 📝 导出文献综述")
    notes = notes_from_dict_list(lr_state.get("notes") or [])
    matrix = LiteratureMatrix.from_dict(lr_state.get("matrix") or {})
    themes = [ThemeCluster.from_dict(t) for t in (lr_state.get("themes") or [])]
    gaps = [GapAnalysis.from_dict(g) for g in (lr_state.get("gaps") or [])]
    lookup = {it.key: it for it in items}

    # v3.5 自审导出 + 批注导入
    with st.expander("🪞 自审循环（导出带标记 → 批注 → 导回）", expanded=False):
        try:
            from src.literature_review.review_import import (
                apply_review_comments_to_state,
                export_for_review,
                import_review_comments,
            )
            review_md = export_for_review(items, notes,
                                            matrix=lr_state.get("matrix") or {})
            st.download_button(
                "📥 导出自审版（带 [REVIEW:...] 标记）",
                data=review_md,
                file_name=_efn("文献综述_自审版", "md"),
                mime="text/markdown",
                key="_lr_dl_review",
            )
            st.caption(
                "💡 在导出的 Markdown 中插入 `[COMMENT: 你的批注]`，再上传以下载文件导回。"
                "批注会显示在文献/笔记详情区域。"
            )
            uploaded = st.file_uploader(
                "上传批注后的 Markdown",
                type=["md", "txt"],
                key="_lr_review_upload",
            )
            if uploaded is not None:
                annotated_md = uploaded.read().decode("utf-8", errors="ignore")
                parsed = import_review_comments(annotated_md)
                counts = apply_review_comments_to_state(lr_state, parsed)
                total = counts["literature"] + counts["notes"] + counts["matrix"]
                st.success(
                    f"✓ 导入 {total} 条批注（"
                    f"文献 {counts['literature']} + 笔记 {counts['notes']} + 矩阵 {counts['matrix']}）"
                )
        except Exception as exc:
            st.warning(f"自审循环不可用：{exc}")

    # 笔记 Markdown
    notes_md = export_notes_markdown(notes, literature_lookup=lookup, title="阅读笔记")
    st.download_button(
        "📥 阅读笔记（Markdown）",
        data=notes_md,
        file_name=_efn("阅读笔记", "md"),
        mime="text/markdown",
        key="_lr_dl_notes",
    )

    # 矩阵 CSV
    matrix_csv = export_matrix_csv(matrix, literature_lookup=lookup)
    st.download_button(
        "📥 文献矩阵（CSV）",
        data=matrix_csv,
        file_name=_efn("文献矩阵", "csv"),
        mime="text/csv",
        key="_lr_dl_matrix",
    )

    # 综合报告
    summary_md = _build_review_summary_md(
        research_q=get_upstream_state(st.session_state).get("research_question", ""),
        items=items,
        notes=notes,
        themes=themes,
        gaps=gaps,
    )
    st.download_button(
        "📥 文献综述草稿（Markdown）",
        data=summary_md,
        file_name=_efn("文献综述草稿", "md"),
        mime="text/markdown",
        type="primary",
        key="_lr_dl_review",
    )


def _render_finish_tab() -> None:
    st.markdown("### 🚪 完成文献综述，进入 wizard")
    st.write(
        "完成文献综述后，将切换到 wizard 阶段（数据上传 → 分析 → 论文写作）。"
        "你随时可以从 wizard 顶部「📚 文献综述」按钮回到此页面。"
    )
    if st.button("✅ 完成文献综述，进入 wizard", type="primary", key="_lr_finish"):
        upstream = get_upstream_state(st.session_state)
        upstream["phase"] = "wizard"
        # 强制保存
        try:
            from src.utils.autosave import trigger_autosave
            from src.utils.workspace import build_workspace_snapshot
            trigger_autosave(st.session_state, build_workspace_snapshot, force=True)
        except Exception:
            pass
        st.success("已切换到 wizard，正在跳转...")
        st.rerun()


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _materialize_items(items_dict_list: List[Dict[str, Any]]) -> List[LiteratureItem]:
    """从 session_state 的 dict 列表实例化 LiteratureItem。"""
    return [LiteratureItem.from_dict(d) for d in (items_dict_list or [])]


def _persist_items(items: List[LiteratureItem]) -> None:
    lr = get_literature_review_state(st.session_state)
    lr["literature_items"] = [it.to_dict() for it in items]


def _get_llm_config() -> Optional[Dict[str, Any]]:
    """v4.6 单轨化：从顶部「🤖 AI 模型」激活的预设读。未激活返回 None。"""
    from src.llm_gateway.active_config import get_active_llm_config
    cfg = get_active_llm_config()
    if cfg is None:
        return None
    out = dict(cfg)
    out.setdefault("timeout", 60)
    return out


# ---------------------------------------------------------------------------
# v4.7 丢文献 → 自动写综述
# ---------------------------------------------------------------------------

# session_state 键（结果跨 rerun 持久，避免点下载按钮后丢失）
_DROP_SUMMARIES_KEY = "_lr_drop_summaries"   # List[PaperSummary.__dict__-like]
_DROP_REVIEW_KEY = "_lr_drop_review"         # dict: markdown/title/warnings/ok
_DROP_TOPIC_KEY = "_lr_drop_topic"


def _render_drop_and_review_section(upstream: Dict[str, Any]) -> None:
    """上传文献 → 逐篇摘要 → 合成综述 → 导出 Word 的自包含区块。"""
    with st.expander("📥 丢文献 → 自动写综述（上传 PDF / Word / txt）", expanded=False):
        from src.llm_gateway.active_config import is_llm_active

        st.caption(
            "上传一批文献，系统先对每篇生成结构化摘要，再合成一篇连贯的中文文献综述，可导出 Word。"
            "给定研究主题时会围绕主题组织。"
        )

        default_topic = (upstream.get("research_question") or "").strip()
        topic = st.text_input(
            "研究主题（可选）",
            value=st.session_state.get(_DROP_TOPIC_KEY, default_topic),
            placeholder="例如：工作压力与员工敬业度的关系",
            key="_lr_drop_topic_input",
        )

        uploaded = st.file_uploader(
            "选择文献文件（可多选）",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="_lr_drop_uploader",
        )

        if not is_llm_active():
            st.warning("⚠️ 尚未激活 AI 模型（见左上「🤖 AI 模型」）。未激活时只能解析文件，无法生成摘要/综述。")

        run = st.button(
            "🚀 开始：逐篇摘要 + 合成综述",
            type="primary",
            disabled=not uploaded,
            key="_lr_drop_run",
        )

        if run and uploaded:
            files = [(f.name, f.getvalue()) for f in uploaded]
            with st.spinner(f"正在解析 {len(files)} 个文件……"):
                docs = ingest_files(files)

            # 解析告警
            for d in docs:
                if d.warnings:
                    st.warning(f"「{d.source_filename}」：{'；'.join(d.warnings)}")

            with st.spinner("正在逐篇生成摘要……（依赖网络，文献多时较慢）"):
                summaries = summarize_papers(docs, topic=topic, model=None)
            with st.spinner("正在合成综述正文……"):
                review = synthesize_review(summaries, topic=topic, model=None)

            # 持久化到 session_state
            st.session_state[_DROP_TOPIC_KEY] = topic
            st.session_state[_DROP_SUMMARIES_KEY] = [
                {"title": s.title, "structured": s.structured, "ok": s.ok, "error": s.error}
                for s in summaries
            ]
            st.session_state[_DROP_REVIEW_KEY] = {
                "markdown": review.markdown, "title": review.title,
                "warnings": review.warnings, "ok": review.ok, "error": review.error,
            }

        _render_drop_results()


def _render_drop_results() -> None:
    """展示已生成的逐篇摘要 + 综述 + 下载按钮（从 session_state 读）。"""
    summaries = st.session_state.get(_DROP_SUMMARIES_KEY)
    review = st.session_state.get(_DROP_REVIEW_KEY)
    if not summaries and not review:
        return

    st.divider()

    # 逐篇摘要
    if summaries:
        st.markdown(f"#### 📄 逐篇摘要（共 {len(summaries)} 篇）")
        for i, s in enumerate(summaries, start=1):
            ok_mark = "✅" if s.get("ok") else "⚠️"
            with st.expander(f"{ok_mark} [{i}] {s.get('title') or '无标题'}", expanded=False):
                structured = s.get("structured") or {}
                if structured:
                    for k, v in structured.items():
                        st.markdown(f"**{k}**：{v}")
                if not s.get("ok") and s.get("error"):
                    st.caption(f"说明：{s['error']}")

    # 综述正文
    if review:
        st.markdown("#### 📝 文献综述")
        for w in (review.get("warnings") or []):
            st.warning(w)
        if not review.get("ok"):
            st.info(f"未能生成完整综述正文（{review.get('error') or 'LLM 不可用'}），以下为可用内容：")
        md = review.get("markdown") or ""
        if md:
            st.markdown(md)
            try:
                docx_bytes = build_review_docx(
                    review.get("title") or "文献综述",
                    md,
                    date=datetime.now().strftime("%Y-%m-%d"),
                )
                st.download_button(
                    "📥 导出综述（Word）",
                    data=docx_bytes,
                    file_name=_efn("文献综述", "docx", title=review.get('title')),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    key="_lr_drop_dl_docx",
                )
            except Exception as exc:  # noqa: BLE001
                st.caption(f"Word 导出暂不可用：{exc}")
        if st.button("🗑️ 清空本次结果", key="_lr_drop_clear"):
            for k in (_DROP_SUMMARIES_KEY, _DROP_REVIEW_KEY):
                st.session_state.pop(k, None)
            st.rerun()


def _build_review_summary_md(
    research_q: str,
    items: List[LiteratureItem],
    notes: List[ReadingNote],
    themes: List[ThemeCluster],
    gaps: List[GapAnalysis],
) -> str:
    """生成文献综述草稿 Markdown，含 4 部分：研究问题 / 文献列表 / 主题小结 / Gap 分析。"""
    lines: List[str] = []
    lines.append("# 文献综述草稿")
    lines.append("")
    lines.append(f"_生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
    lines.append("")

    if research_q:
        lines.append("## 1. 研究问题")
        lines.append("")
        lines.append(f"> {research_q}")
        lines.append("")

    lines.append(f"## 2. 文献列表（共 {len(items)} 篇）")
    lines.append("")
    for it in sorted(items, key=lambda x: -x.relevance_score)[:20]:
        first_author = it.authors[0] if it.authors else "Unknown"
        doi_part = f"https://doi.org/{it.doi}" if it.doi else ""
        lines.append(f"- {first_author} ({it.year}). *{it.title}*. {it.journal}. {doi_part}")
    lines.append("")

    if themes:
        lines.append(f"## 3. 主题小结（{len(themes)} 个主题）")
        lines.append("")
        for t in themes:
            lines.append(f"### {t.theme_name}")
            lines.append("")
            lines.append(f"**关键词**：{', '.join(t.centroid_keywords)}")
            lines.append("")
            lines.append(t.summary)
            lines.append("")

    if gaps:
        lines.append(f"## 4. Gap 分析（{len(gaps)} 个）")
        lines.append("")
        for i, g in enumerate(gaps, 1):
            lines.append(f"### Gap {i}")
            lines.append("")
            lines.append(g.gap_description)
            lines.append("")
            if g.suggested_direction:
                lines.append(f"**建议方向**：{g.suggested_direction}")
                lines.append("")

    if notes:
        lines.append(f"## 5. 笔记摘要（{len(notes)} 条）")
        lines.append("")
        from collections import Counter
        type_counter = Counter(n.type for n in notes)
        for tp, cnt in type_counter.most_common():
            lines.append(f"- {tp}：{cnt} 条")
        lines.append("")

    return "\n".join(lines)
