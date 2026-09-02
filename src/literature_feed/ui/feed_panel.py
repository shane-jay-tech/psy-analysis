"""📡 文献雷达 UI（Phase 4f）。

四个 tab：每日动态 / 趋势分析 / 来源管理 / 设置。

设计：
- FeedStore 在每次 render 顶部打开，render 末尾 close（Streamlit 每次交互都 rerun，
  连接生命周期跟着 render 走，避免连接积累）
- bootstrap_check.maybe_trigger_async() 在 session 内只调一次（_BOOTSTRAP_TRIGGERED key）
- 域权重保存写回 D:\\code\\psy-analysis\\data\\literature_feed\\domain_weights.yaml
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from ..paths import DOMAIN_WEIGHTS_PATH, METHOD_WEIGHTS_PATH, TRENDING_WEIGHTS_PATH
from ..scheduler.bootstrap_check import (
    evaluate as bootstrap_evaluate,
    is_running as bootstrap_is_running,
    last_async_result as bootstrap_last_result,
    maybe_trigger_async,
)
from ..scheduler.lock_manager import LockManager
from ..storage.budget_tracker import BudgetTracker
from ..storage.feed_store import FeedStore
from ..trend import (
    DomainWeights,
    MethodWeights,
    TrendingWeights,
    compute_domain_summary,
    compute_keyword_trends,
    load_default_method_weights,
    load_default_weights,
)
from ..trend.trending_weights import load_default_trending, write_trending_yaml

logger = logging.getLogger(__name__)

_DOMAIN_COLORS = {
    "IO": "#3498db",     # 蓝
    "HR": "#27ae60",     # 绿
    "OB": "#e67e22",     # 橙
    "其他": "#95a5a6",   # 灰
}
_BOOTSTRAP_SESSION_KEY = "_lit_feed_bootstrap_triggered"


# ====================================================================
# 入口
# ====================================================================

def render_literature_feed() -> None:
    """主入口：📡 文献雷达。"""
    st.title("📡 文献雷达")
    st.caption(
        "每日抓取心理学顶刊新文 → LLM 抽取构念/方法 → IO/HR/OB 加权排序。"
        "Streamlit 启动时若距上次抓取 ≥24h 会后台触发；也可在「来源管理」手动跑。"
    )

    # session 内只触发一次 bootstrap（避免 rerun 风暴）
    if not st.session_state.get(_BOOTSTRAP_SESSION_KEY):
        try:
            maybe_trigger_async()
        except Exception as exc:  # noqa: BLE001
            logger.warning("bootstrap_check 触发失败：%s", exc)
        st.session_state[_BOOTSTRAP_SESSION_KEY] = True

    # FeedStore 短生命周期：本 render 用完关
    try:
        store = FeedStore()
    except Exception as exc:  # noqa: BLE001
        st.error(f"❌ 数据库打开失败：{exc}")
        st.info(
            "如果是首次运行，请先在终端跑一次：`python -m src.literature_feed.scheduler --trigger init`"
        )
        return

    try:
        weights = load_default_weights()
    except Exception as exc:  # noqa: BLE001
        st.warning(f"加载域权重失败（使用空词表继续）：{exc}")
        weights = DomainWeights.empty()

    tab_daily, tab_trend, tab_sources, tab_settings = st.tabs(
        ["📰 每日动态", "📊 趋势分析", "🛰 来源管理", "⚙️ 设置"]
    )

    try:
        with tab_daily:
            _render_daily_tab(store)
        with tab_trend:
            try:
                trending_weights = load_default_trending()
            except Exception as _exc:
                logger.warning("load_default_trending failed: %s", _exc)
                trending_weights = TrendingWeights.empty()
            _render_trend_tab(store, weights, trending_weights)
        with tab_sources:
            _render_sources_tab(store)
        with tab_settings:
            _render_settings_tab(store, weights)
    finally:
        try:
            store.close()
        except Exception:  # noqa: BLE001
            pass


# ====================================================================
# Tab 1: 每日动态
# ====================================================================

def _render_daily_tab(store: FeedStore) -> None:
    # ── 状态 banner ──
    decision = bootstrap_evaluate()
    last_result = bootstrap_last_result()
    running = bootstrap_is_running()

    col_status, col_btn = st.columns([4, 1])
    with col_status:
        if running:
            st.info("🔄 后台抓取进行中... 本 tab 内容是数据库已落盘的部分。")
        elif decision.last_success_hours is None:
            st.warning("从未跑过自动抓取。点右侧按钮立即触发，或运行 Task Scheduler。")
        elif decision.last_success_hours < 24:
            st.success(
                f"✅ 上次成功抓取于 {decision.last_success_hours:.1f} 小时前。"
            )
        else:
            st.warning(
                f"⏰ 距上次成功 {decision.last_success_hours:.1f}h（≥24h），可考虑手动触发。"
            )

        if last_result is not None:
            status = last_result.get("status", "")
            if status == "failed":
                st.error(f"❌ 上次后台运行失败：{last_result.get('error')}")
            else:
                ok = last_result.get("sources_ok", 0)
                total = last_result.get("sources_total", 0)
                cons = last_result.get("extracted_constructs", 0)
                meth = last_result.get("extracted_methods", 0)
                budget_ex = last_result.get("budget_exceeded")
                msg = (
                    f"上次后台抓取（{status}）：来源 {ok}/{total}，"
                    f"抽取构念 {cons}、方法 {meth}"
                )
                if budget_ex:
                    msg += "（⚠️ 触及月度预算）"
                st.caption(msg)

    with col_btn:
        disabled = running
        if st.button("🚀 立即抓取", disabled=disabled, width="stretch",
                     help="后台异步触发；不会阻塞页面"):
            try:
                maybe_trigger_async()
                st.toast("已后台触发，几分钟后回这个 tab 看结果", icon="🚀")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"触发失败：{exc}")

    st.divider()

    # ── 高优先级候选（快速审核） ──
    st.markdown("### 🔥 高优先级候选（待审）")
    pending = store.list_candidates(status="pending", limit=20)
    if not pending:
        st.caption("当前没有待审候选。LLM 抽取还没跑过，或全部已审。")
    else:
        total_pending = store.count_candidates(status="pending")
        high_conf = [c for c in pending if (c.get("confidence") or 0) >= 0.8]

        # ── 批量操作栏 ──
        batch_col1, batch_col2, batch_col3 = st.columns([2, 2, 4])
        with batch_col1:
            if high_conf and st.button(
                f"⚡ 一键批准高置信 ({len(high_conf)})",
                width="stretch",
                help="批准置信度 >= 0.8 的全部候选",
            ):
                for c in high_conf:
                    store.update_candidate_status(
                        c["candidate_id"], status="approved", reviewer="batch_high_conf"
                    )
                st.toast(f"已批准 {len(high_conf)} 条高置信度候选", icon="⚡")
                st.rerun()
        with batch_col2:
            _reject_key = "_confirm_batch_reject"
            if st.session_state.get(_reject_key):
                st.warning(f"确定拒绝全部 {len(pending)} 条候选？")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("确认拒绝", type="primary", width="stretch"):
                        for c in pending:
                            store.update_candidate_status(
                                c["candidate_id"], status="rejected", reviewer="batch_reject"
                            )
                        st.session_state[_reject_key] = False
                        st.toast(f"已拒绝全部 {len(pending)} 条候选", icon="🗑️")
                        st.rerun()
                with c2:
                    if st.button("取消", width="stretch"):
                        st.session_state[_reject_key] = False
                        st.rerun()
            else:
                if st.button("🗑️ 全部拒绝", width="stretch", type="secondary"):
                    st.session_state[_reject_key] = True
                    st.rerun()
        with batch_col3:
            st.caption(f"共 {total_pending} 条待审 · 显示前 20 · 高置信(>=0.8): {len(high_conf)} 条")

        # ── 逐条审核卡片 ──
        for idx, c in enumerate(pending):
            cid = c["candidate_id"]
            kind_label = "构念" if c["kind"] == "construct" else "方法"
            conf = round(c.get("confidence") or 0, 2)
            priority = round(c.get("priority_score") or 0, 3)
            definition = c.get("definition") or c.get("method_category") or ""
            evidence = (c.get("evidence_quote") or "")[:80]

            iohr_raw = c.get("iohr_hits_json") or "[]"
            try:
                import json as _json
                iohr_list = _json.loads(iohr_raw) if isinstance(iohr_raw, str) else iohr_raw
                if not isinstance(iohr_list, list):
                    iohr_list = []
            except (TypeError, ValueError):
                iohr_list = []

            with st.container(border=True):
                top_l, top_r = st.columns([5, 1])
                with top_l:
                    st.markdown(
                        f"**{c['name']}** &nbsp; `{kind_label}` &nbsp; "
                        f"置信 {conf} · 优先级 {priority}"
                    )
                with top_r:
                    if conf >= 0.8:
                        st.success("高置信", icon="✅")
                    elif conf >= 0.5:
                        st.info("中置信", icon="ℹ️")
                    else:
                        st.warning("低置信", icon="⚠️")

                if definition:
                    st.caption(definition[:120])
                if evidence:
                    st.text(f"证据: {evidence}")
                if iohr_list:
                    st.caption(f"域命中: {', '.join(iohr_list[:5])}")

                btn_l, btn_r, _ = st.columns([1, 1, 4])
                with btn_l:
                    if st.button("✅ 批准", key=f"approve_{cid}_{idx}", width="stretch"):
                        store.update_candidate_status(cid, status="approved", reviewer="manual")
                        st.rerun()
                with btn_r:
                    if st.button("❌ 拒绝", key=f"reject_{cid}_{idx}", width="stretch", type="secondary"):
                        store.update_candidate_status(cid, status="rejected", reviewer="manual")
                        st.rerun()

    st.divider()

    # ── 近 14 天文章 ──
    since = (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat()
    articles = store.list_articles(since=since, limit=30)
    st.markdown(f"### 📚 近 14 天新文（共 {len(articles)} 篇展示）")

    if not articles:
        st.caption("近 14 天没有新文章。如果是新装机，先在「来源管理」点击立即抓取。")
    else:
        rows = []
        for a in articles:
            rows.append({
                "source": a.get("source_id", ""),
                "title": a.get("title", "")[:80],
                "issued": a.get("issued_date") or "",
                "doi": a.get("doi") or "",
            })
        st.dataframe(rows, width="stretch", hide_index=True,
                     column_config={
                         "source": st.column_config.TextColumn("来源", width="small"),
                         "title": st.column_config.TextColumn("标题", width="large"),
                         "issued": st.column_config.TextColumn("发表日", width="small"),
                         "doi": st.column_config.TextColumn("DOI", width="medium"),
                     })


# ====================================================================
# Tab 2: 趋势分析
# ====================================================================

def _render_trend_tab(store: FeedStore, weights: DomainWeights, trending: "TrendingWeights") -> None:
    st.markdown("### 📊 关键词趋势（IO/HR/OB 加权）")

    col_w, col_n, col_filter = st.columns([1, 1, 1])
    with col_w:
        window = st.selectbox("时间窗口", [7, 30, 90, 180], index=2,
                              format_func=lambda d: f"{d} 天")
    with col_n:
        top_n = st.slider("展示 Top N", min_value=5, max_value=50, value=20, step=5)
    with col_filter:
        domain_only = st.checkbox("只看 IO/HR/OB 命中", value=False,
                                  help="勾选后过滤掉未在词表里的 keyword")

    try:
        rows = compute_keyword_trends(
            store,
            weights=weights,
            window_days=window,
            top_n=top_n,
            domain_only=domain_only,
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"计算趋势失败：{exc}")
        return

    if not rows:
        st.info(f"近 {window} 天还没有可统计的关键词。先抓几次数据再来看。")
        return

    # ── 域汇总 ──
    summary = compute_domain_summary(rows)
    cols = st.columns(4)
    for col, dom in zip(cols, ("IO", "HR", "OB", "其他")):
        bucket = summary.get(dom, {"count": 0, "weighted": 0.0})
        with col:
            color = _DOMAIN_COLORS.get(dom, "#000")
            st.markdown(
                f"<div style='border-left:4px solid {color}; padding:6px 12px;'>"
                f"<div style='font-size:0.75em; color:#666;'>{dom}</div>"
                f"<div style='font-size:1.4em; font-weight:600;'>{int(bucket['count'])}</div>"
                f"<div style='font-size:0.7em; color:#888;'>加权 {bucket['weighted']:.1f}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── 详情表 ──
    table = []
    for i, r in enumerate(rows, start=1):
        dom = r.domain or "其他"
        table.append({
            "#": i,
            "关键词": r.canonical or r.keyword,
            "域": dom,
            "原始": r.keyword if r.canonical and r.keyword != r.canonical else "",
            "篇数": r.count,
            "加权": round(r.weighted_count, 2),
            "最新": r.latest_issued_date or "",
        })
    st.dataframe(table, width="stretch", hide_index=True,
                 column_config={
                     "#": st.column_config.NumberColumn(width="small"),
                     "关键词": st.column_config.TextColumn(width="medium"),
                     "域": st.column_config.TextColumn(width="small"),
                     "原始": st.column_config.TextColumn(
                         "同义词原文", width="medium",
                         help="若有同义词归一化，这里显示原始 keyword",
                     ),
                     "篇数": st.column_config.NumberColumn(width="small"),
                     "加权": st.column_config.NumberColumn(format="%.2f", width="small"),
                     "最新": st.column_config.TextColumn(width="small"),
                 })

    st.caption(
        "**权重逻辑**：IO/HR/OB 命中 × {mult:.2f} ；其他 × {dw:.2f}。"
        "在「⚙️ 设置」里编辑词表。".format(
            mult=weights.domain_multiplier, dw=weights.default_weight,
        )
    )

    st.divider()
    _render_trending_section(trending)


# ====================================================================
# Trending section (inside Tab 2)
# ====================================================================

def _render_trending_section(trending: "TrendingWeights") -> None:
    """Render the 30-day trending keywords with human-in-the-loop promote/ignore."""
    st.markdown("### 📈 近期热门（30 天滑动窗口）")

    if not trending.entries:
        st.info(
            "暂无热门词条数据。请等待每日自动跑（周一自动重算），"
            "或在来源管理页手动触发一次抓取后回来看。"
        )
        if trending.generated_at:
            st.caption(f"最近生成时间：{trending.generated_at}")
        return

    st.caption(
        f"基于近 {trending.window_days} 天 vs 基线 {trending.baseline_days} 天的关键词 spike ratio。"
        f"multiplier 最高封顶 {trending.multiplier_cap:.2f}x。"
        f"生成时间：{trending.generated_at or '未知'}。"
    )

    table = []
    for e in trending.entries:
        table.append({
            "关键词": e.keyword,
            "spike ratio": round(e.spike_ratio, 3),
            "multiplier": round(e.multiplier, 3),
            "窗口篇数": e.window_count,
            "基线篇数": e.baseline_count,
            "状态": ("★ 已推广" if trending.is_promoted(e.keyword)
                     else ("✗ 已忽略" if trending.is_ignored(e.keyword) else "自动")),
        })
    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            "关键词": st.column_config.TextColumn(width="medium"),
            "spike ratio": st.column_config.NumberColumn(format="%.3f", width="small",
                                                          help="窗口加权计数 / 基线加权计数"),
            "multiplier": st.column_config.NumberColumn(format="%.3f", width="small",
                                                         help="priority 乘以该值（1.0=无加成）"),
            "窗口篇数": st.column_config.NumberColumn(width="small"),
            "基线篇数": st.column_config.NumberColumn(width="small"),
            "状态": st.column_config.TextColumn(width="small"),
        },
    )

    # Human-in-the-loop: promote or ignore trending entries
    with st.expander("手动干预（推广 / 忽略）", expanded=False):
        kw_options = [e.keyword for e in trending.entries]
        if not kw_options:
            st.caption("没有可操作的词条。")
            return

        col_action, col_kw = st.columns([1, 2])
        with col_action:
            action = st.selectbox(
                "操作", ["推广（锁定加成）", "忽略（排除计算）", "取消推广", "取消忽略"],
                key="trending_action",
            )
        with col_kw:
            target_kw = st.selectbox("关键词", kw_options, key="trending_target_kw")

        if st.button("执行", key="trending_apply"):
            try:
                _apply_trending_override(trending, action, target_kw)
                st.success(f"已对 '{target_kw}' 执行：{action}")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"操作失败：{exc}")


def _apply_trending_override(
    trending: "TrendingWeights",
    action: str,
    keyword: str,
) -> None:
    """Mutate ignored/promoted lists and re-save trending_weights.yaml."""
    from ..trend.trending_weights import write_trending_yaml, TrendingWeights, TrendingEntry

    ignored = list(trending.ignored)
    promoted = list(trending.promoted)
    promoted_log = list(trending.promoted_log)
    key = keyword.strip().lower()

    if action.startswith("推广"):
        if keyword not in promoted:
            promoted.append(keyword)
        promoted_log.append(
            f"{__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(timespec='seconds')} promoted: {keyword}"
        )
        # remove from ignored if present
        ignored = [k for k in ignored if k.strip().lower() != key]
    elif action.startswith("忽略"):
        if keyword not in ignored:
            ignored.append(keyword)
        # remove from promoted if present
        promoted = [k for k in promoted if k.strip().lower() != key]
    elif action.startswith("取消推广"):
        promoted = [k for k in promoted if k.strip().lower() != key]
    elif action.startswith("取消忽略"):
        ignored = [k for k in ignored if k.strip().lower() != key]

    # Rebuild TrendingWeights with updated lists
    updated = TrendingWeights(
        entries=trending.entries,
        generated_at=trending.generated_at,
        window_days=trending.window_days,
        baseline_days=trending.baseline_days,
        multiplier_cap=trending.multiplier_cap,
        ignored=tuple(ignored),
        promoted=tuple(promoted),
        promoted_log=tuple(promoted_log),
    )
    write_trending_yaml(updated, TRENDING_WEIGHTS_PATH)


# ====================================================================
# Tab 3: 来源管理
# ====================================================================

def _render_sources_tab(store: FeedStore) -> None:
    st.markdown("### 🛰 抓取来源")

    sources = store.list_sources()
    if not sources:
        st.warning("还没有配置抓取来源。请运行一次 `python -m src.literature_feed.scheduler` 自动落种。")
        return

    rows = []
    for s in sources:
        rows.append({
            "source_id": s["source_id"],
            "期刊": s.get("journal_name", ""),
            "抓取器": s.get("fetcher_type", ""),
            "状态": s.get("status", ""),
            "上次成功": (s.get("last_success_at") or "")[:19].replace("T", " "),
            "启用": bool(s.get("enabled", 1)),
        })
    st.dataframe(rows, width="stretch", hide_index=True,
                 column_config={
                     "启用": st.column_config.CheckboxColumn(disabled=True, width="small"),
                 })

    st.divider()
    st.markdown("### 📜 最近抓取审计")

    recent_runs = store.connection.execute(
        "SELECT run_id, trigger, started_at, ended_at, status, summary_json "
        "FROM fetch_runs ORDER BY run_id DESC LIMIT 10"
    ).fetchall()

    if not recent_runs:
        st.caption("还没有跑过抓取。")
    else:
        run_rows = []
        for r in recent_runs:
            summary = {}
            if r["summary_json"]:
                try:
                    summary = json.loads(r["summary_json"])
                except json.JSONDecodeError:
                    pass
            run_rows.append({
                "run_id": r["run_id"],
                "触发": r["trigger"],
                "开始": (r["started_at"] or "")[:19].replace("T", " "),
                "结束": (r["ended_at"] or "")[:19].replace("T", " "),
                "状态": r["status"],
                "新文章": summary.get("articles_new", 0),
                "构念": summary.get("constructs", 0),
                "方法": summary.get("methods", 0),
            })
        st.dataframe(run_rows, width="stretch", hide_index=True)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 立即抓取所有来源", width="stretch",
                     help="启动子进程跑一次完整抓取（异步 / 不阻塞页面）"):
            _spawn_scheduler_subprocess()
            st.toast("子进程已启动，几分钟后看「📰 每日动态」", icon="🚀")
    with col2:
        if st.button("🔄 刷新此页", width="stretch"):
            st.rerun()


def _spawn_scheduler_subprocess() -> None:
    """启动 `python -m src.literature_feed.scheduler` 子进程，不等结果。

    注意：使用 DETACHED_PROCESS（Windows）/ start_new_session（POSIX），
    防止 Streamlit 进程退出时把抓取进程一起带走。
    """
    repo_root = Path(__file__).resolve().parents[3]
    cmd = [sys.executable, "-m", "src.literature_feed.scheduler",
           "--trigger", "ui_manual", "--log-level", "INFO"]
    kwargs: Dict[str, Any] = {
        "cwd": str(repo_root),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x00000008  # DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


# ====================================================================
# Tab 4: 设置
# ====================================================================

def _render_settings_tab(store: FeedStore, weights: DomainWeights) -> None:
    # ── LLM 预算 ──
    st.markdown("### 💰 月度 LLM 预算")
    try:
        budget = BudgetTracker()
        usage = budget.current_usage()
    except Exception as exc:  # noqa: BLE001
        st.error(f"读取预算失败：{exc}")
        usage = None

    if usage:
        ratio = float(usage.get("ratio", 0))
        st.progress(min(ratio, 1.0))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("已用", f"${usage['total_usd']:.3f}")
        c2.metric("上限", f"${usage['limit_usd']:.2f}")
        c3.metric("调用次数", usage["calls"])
        c4.metric("缓存命中", usage["cache_hits"])
        if usage.get("exceeded"):
            st.error("⚠️ 已触及月度预算，新的 LLM 调用会被拒。")
        elif usage.get("warn"):
            st.warning(f"接近预算上限（{ratio*100:.0f}%）。")

    st.divider()

    # ── 锁状态 ──
    st.markdown("### 🔒 抓取互斥锁")
    lock = LockManager()
    held_by_other = lock.is_held_by_other()
    is_stale = lock.is_stale()
    c1, c2 = st.columns(2)
    with c1:
        if held_by_other and not is_stale:
            st.info("锁正在被某进程持有（抓取中）")
        elif is_stale:
            st.warning("锁文件 stale（>6h 未更新），下一次 acquire 会强抢")
        else:
            st.success("锁空闲")
    with c2:
        st.caption(f"锁文件路径：`{lock.lock_path}`")

    st.divider()

    # ── 域权重编辑 ──
    st.markdown("### 🎯 IO / HR / OB 域权重编辑")
    st.caption(
        f"YAML 路径：`{DOMAIN_WEIGHTS_PATH}`。命中以下任意 canonical 或 synonyms 的关键词，"
        f"会被乘以 `domain_multiplier`；其他默认 `default_weight`。"
    )

    with st.form("domain_weights_form", clear_on_submit=False):
        col_dw, col_dm = st.columns(2)
        with col_dw:
            new_default = st.number_input(
                "default_weight（不命中域时）", min_value=0.0, max_value=10.0,
                value=float(weights.default_weight), step=0.1,
            )
        with col_dm:
            new_multiplier = st.number_input(
                "domain_multiplier（命中域时）", min_value=0.0, max_value=10.0,
                value=float(weights.domain_multiplier), step=0.1,
            )

        # 把 by_domain 摊平成 data_editor 友好的 list[dict]
        editor_rows = []
        for dom in ("IO", "HR", "OB"):
            for canonical, synonyms in weights.by_domain.get(dom, ()):
                editor_rows.append({
                    "domain": dom,
                    "canonical": canonical,
                    "synonyms": ", ".join(synonyms),
                })
        if not editor_rows:
            editor_rows = [{"domain": "IO", "canonical": "", "synonyms": ""}]

        edited = st.data_editor(
            editor_rows,
            num_rows="dynamic",
            width="stretch",
            column_config={
                "domain": st.column_config.SelectboxColumn(
                    "域", options=["IO", "HR", "OB"], width="small", required=True,
                ),
                "canonical": st.column_config.TextColumn(
                    "标准词", width="medium",
                    help="该 domain 内的标准化术语（中英任选）",
                ),
                "synonyms": st.column_config.TextColumn(
                    "同义词", width="large",
                    help="逗号分隔，命中其中任一会被映射到 canonical",
                ),
            },
            key="domain_weights_editor",
        )

        submitted = st.form_submit_button("💾 保存词表", type="primary")
        if submitted:
            try:
                _save_domain_weights(
                    edited,
                    default_weight=new_default,
                    domain_multiplier=new_multiplier,
                )
                st.success(
                    f"✅ 已保存 → `{DOMAIN_WEIGHTS_PATH}`。下次抓取/打分会用新词表。"
                )
                # 清掉 module-level 缓存（如果有的话）
                load_default_weights.cache_clear() if hasattr(
                    load_default_weights, "cache_clear"
                ) else None
            except Exception as exc:  # noqa: BLE001
                st.error(f"❌ 保存失败：{exc}")

    st.divider()

    # ── 方法权重编辑（Round 2 加） ──
    st.markdown("### 🔬 研究方法加权编辑")
    st.caption(
        f"YAML 路径：`{METHOD_WEIGHTS_PATH}`。命中以下任意 canonical 或 synonyms 的"
        f"方法关键词，候选 priority 会多乘 (1 + method_score)；与域权重相乘叠加。"
    )

    method_weights = load_default_method_weights()

    with st.form("method_weights_form", clear_on_submit=False):
        col_mdw, col_mdm = st.columns(2)
        with col_mdw:
            new_m_default = st.number_input(
                "default_weight（不命中方法时）", min_value=0.0, max_value=10.0,
                value=float(method_weights.default_weight), step=0.1,
                key="method_default_weight",
            )
        with col_mdm:
            new_m_multiplier = st.number_input(
                "method_multiplier（命中方法时）", min_value=0.0, max_value=10.0,
                value=float(method_weights.method_multiplier), step=0.1,
                key="method_multiplier",
            )

        method_rows = []
        for canonical, synonyms in method_weights.methods:
            method_rows.append({
                "canonical": canonical,
                "synonyms": ", ".join(synonyms),
            })
        if not method_rows:
            method_rows = [{"canonical": "", "synonyms": ""}]

        m_edited = st.data_editor(
            method_rows,
            num_rows="dynamic",
            width="stretch",
            column_config={
                "canonical": st.column_config.TextColumn(
                    "标准方法名", width="medium",
                    help="研究方法的标准化术语（中英任选，如「纵向设计」「HLM」）",
                ),
                "synonyms": st.column_config.TextColumn(
                    "同义词", width="large",
                    help="逗号分隔，命中其中任一会被映射到 canonical",
                ),
            },
            key="method_weights_editor",
        )

        m_submitted = st.form_submit_button("💾 保存方法词表", type="primary")
        if m_submitted:
            try:
                _save_method_weights(
                    m_edited,
                    default_weight=new_m_default,
                    method_multiplier=new_m_multiplier,
                )
                st.success(
                    f"✅ 已保存 → `{METHOD_WEIGHTS_PATH}`。下次抓取/打分会用新方法词表。"
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"❌ 保存失败：{exc}")

    st.divider()

    # ── danger zone ──
    with st.expander("⚠️ 危险操作", expanded=False):
        st.markdown(
            "**重置 pending 候选**：把所有待审候选标记为 rejected。"
            "下次抓取重跑 LLM 时会重新生成（注意会扣预算）。"
        )
        confirm = st.checkbox("我明白此操作不可逆", key="_lit_reset_confirm")
        if st.button("🗑 重置所有 pending 候选", disabled=not confirm,
                     type="secondary"):
            n = store.connection.execute(
                "UPDATE llm_candidates SET status='rejected' WHERE status='pending'"
            ).rowcount
            store.connection.commit()
            st.success(f"已标记 {n} 条 pending → rejected。")
            st.session_state["_lit_reset_confirm"] = False


def _save_domain_weights(
    edited_rows: List[Dict[str, Any]],
    *,
    default_weight: float,
    domain_multiplier: float,
) -> None:
    """把 data_editor 输出反向构造成 YAML 并原子写入。"""
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("缺少 PyYAML，无法保存") from exc

    domains: Dict[str, List[Dict[str, Any]]] = {"IO": [], "HR": [], "OB": []}
    for row in edited_rows:
        dom = (row.get("domain") or "").strip().upper()
        canonical = (row.get("canonical") or "").strip()
        if not canonical or dom not in domains:
            continue
        syns_raw = row.get("synonyms") or ""
        synonyms = [s.strip() for s in syns_raw.split(",") if s.strip()]
        domains[dom].append({"canonical": canonical, "synonyms": synonyms})

    payload = {
        "version": 1,
        "default_weight": float(default_weight),
        "domain_multiplier": float(domain_multiplier),
        "domains": {
            dom: {"concepts": entries}
            for dom, entries in domains.items()
        },
    }

    target = DOMAIN_WEIGHTS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("# 心理学构念 IO / HR / OB 加权配置（UI 自动保存）\n")
        f.write(f"# 保存时间：{datetime.now(timezone.utc).isoformat(timespec='seconds')}\n\n")
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    tmp.replace(target)


def _save_method_weights(
    edited_rows: List[Dict[str, Any]],
    *,
    default_weight: float,
    method_multiplier: float,
    target_path: Optional[Path] = None,
) -> None:
    """把 data_editor 输出反向构造成 YAML 并原子写入 method_weights.yaml。

    target_path 可选 — 不传则写到 METHOD_WEIGHTS_PATH（生产路径），仅测试注入临时文件用。
    """
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("缺少 PyYAML，无法保存") from exc

    methods: List[Dict[str, Any]] = []
    for row in edited_rows:
        canonical = (row.get("canonical") or "").strip()
        if not canonical:
            continue
        syns_raw = row.get("synonyms") or ""
        synonyms = [s.strip() for s in syns_raw.split(",") if s.strip()]
        methods.append({"canonical": canonical, "synonyms": synonyms})

    payload = {
        "version": 1,
        "default_weight": float(default_weight),
        "method_multiplier": float(method_multiplier),
        "methods": methods,
    }

    target = target_path or METHOD_WEIGHTS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("# 心理学研究方法加权配置（UI 自动保存）\n")
        f.write(f"# 保存时间：{datetime.now(timezone.utc).isoformat(timespec='seconds')}\n\n")
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    tmp.replace(target)
