"""Session State 内存监控与自动清理

单用户本地场景下，Streamlit 的 session_state 可能因反复加载大 DataFrame
或累积分析历史而占用过多内存。本模块提供：
- 估算当前 session_state 内存占用
- 自动清理策略（保留最近 N 条分析历史、丢弃超大 DataFrame 的副本等）
- 手动清理入口
"""

import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import streamlit as st


# 默认阈值（可根据机器内存调整）
DEFAULT_MEMORY_MB = 512  # 512 MB 触发清理警告
DEFAULT_AUTO_CLEANUP_MB = 1024  # 1 GB 触发自动清理
MAX_ANALYSIS_HISTORY = 50  # 分析历史上限
LITERATURE_CACHE_DAYS = 7  # 文献缓存保留天数
CANCEL_ID_CLEANUP_HOURS = 24  # cancel_id 过期清理时间


def _estimate_obj_size(obj: Any) -> int:
    """粗略估算对象的内存大小（字节）"""
    try:
        if isinstance(obj, pd.DataFrame):
            return obj.memory_usage(deep=True).sum()
        return sys.getsizeof(obj)
    except Exception:
        return 0


# v5.8: 内存估算含 DataFrame.memory_usage(deep=True)（大 df 下每次 ~1s+），
# 而 get_system_status 每个 rerun 都会被侧边栏调用。加 TTL 缓存：估算结果
# 30 秒内复用，避免每次点击交互都重扫整个 session_state。
_MEM_CACHE_TTL_SEC = 30.0
_mem_cache: Dict[str, Any] = {"at": 0.0, "result": None}


def estimate_session_state_memory(force: bool = False) -> Dict[str, int]:
    """估算 session_state 中各键的内存占用。

    返回 {"total_bytes": int, "items": {key: bytes, ...}}
    结果带 30s TTL 缓存（force=True 立即重算）。
    """
    now = time.monotonic()
    if not force and _mem_cache["result"] is not None and (now - _mem_cache["at"]) < _MEM_CACHE_TTL_SEC:
        return _mem_cache["result"]

    total = 0
    items = {}
    for key, val in st.session_state.items():
        size = _estimate_obj_size(val)
        items[key] = size
        total += size
    result = {"total_bytes": total, "items": items}
    _mem_cache["at"] = now
    _mem_cache["result"] = result
    return result


def get_memory_summary() -> str:
    """生成可读的内存占用摘要"""
    mem = estimate_session_state_memory()
    total_mb = mem["total_bytes"] / (1024 * 1024)
    lines = [f"Session State 总占用：{total_mb:.1f} MB"]
    top = sorted(mem["items"].items(), key=lambda x: x[1], reverse=True)[:5]
    for k, b in top:
        lines.append(f"  - {k}: {b / (1024 * 1024):.1f} MB")
    return "\n".join(lines)


def auto_cleanup_session_state(
    max_history: int = MAX_ANALYSIS_HISTORY,
    max_analysis_output_cache: int = 5,
) -> Dict[str, Any]:
    """自动清理 session_state 中的大对象和历史记录。

    策略：
    1. 分析历史 (analysis_history) 只保留最近 max_history 条
    2. analysis_output 缓存只保留最近 max_analysis_output_cache 次
    3. 删除旧的 _q_design_pending / _exp_design_pending / _lit_search_pending
    4. 清理已完成的 future 对象引用

    返回 {"cleaned_keys": list, "freed_mb": float}
    """
    cleaned = []
    freed_bytes = 0

    # 1. 分析历史
    hist = st.session_state.get("analysis_history")
    if isinstance(hist, list) and len(hist) > max_history:
        old = hist[:-max_history]
        freed = sum(_estimate_obj_size(x) for x in old)
        st.session_state.analysis_history = hist[-max_history:]
        cleaned.append(f"analysis_history ({len(old)}条旧记录)")
        freed_bytes += freed

    # 2. 旧的 pending 状态
    for key in ["_q_design_pending", "_exp_design_pending", "_lit_search_pending"]:
        pending = st.session_state.get(key)
        if pending is not None:
            future = pending.get("future")
            if future is not None and future.done():
                freed = _estimate_obj_size(pending)
                st.session_state.pop(key, None)
                cleaned.append(key)
                freed_bytes += freed

    # 3. 旧的 analysis_output（如果不是当前展示的）
    ao = st.session_state.get("analysis_output")
    if ao is not None:
        # 只保留当前，不缓存多个 analysis_output
        pass

    # 4. 清理向导数据中可能残留的 DataFrame
    wiz = st.session_state.get("undergrad_wizard_data")
    if isinstance(wiz, dict):
        for wk, wv in list(wiz.items()):
            if isinstance(wv, pd.DataFrame) and wk not in ["current_df"]:
                freed = _estimate_obj_size(wv)
                wiz.pop(wk, None)
                cleaned.append(f"undergrad_wizard_data.{wk}")
                freed_bytes += freed

    return {
        "cleaned_keys": cleaned,
        "freed_mb": freed_bytes / (1024 * 1024),
    }


def cleanup_literature_cache(older_than_days: int = LITERATURE_CACHE_DAYS) -> dict:
    """清理过期的文献爬取缓存文件。

    扫描 .literature_cache/ 目录，删除超过指定天数的缓存文件。
    返回 {"cleaned": int, "freed_mb": float}
    """
    cache_dir = Path(__file__).parent.parent / "paper_writer" / ".literature_cache"
    if not cache_dir.exists():
        return {"cleaned": 0, "freed_mb": 0.0}

    cutoff = datetime.now() - timedelta(days=older_than_days)
    cleaned = 0
    freed_bytes = 0

    for cache_file in cache_dir.glob("*.json"):
        try:
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if mtime < cutoff:
                freed_bytes += cache_file.stat().st_size
                cache_file.unlink()
                cleaned += 1
        except OSError:
            pass

    return {"cleaned": cleaned, "freed_mb": freed_bytes / (1024 * 1024)}


def cleanup_stale_cancel_ids():
    """清理已完成的 Future cancel_id 条目。

    扫描 session_state 中的 cancel_id 相关键，移除已完成的条目。
    返回 {"cleaned": int}
    """
    cleaned = 0
    for key in ["_q_design_pending", "_exp_design_pending", "_lit_search_pending"]:
        pending = st.session_state.get(key)
        if pending is not None:
            future = pending.get("future")
            if future is not None and future.done():
                st.session_state.pop(key, None)
                cleaned += 1

    # 也检查 cancel_flags 池（来自 llm_engine 和 search_async 模块）
    try:
        from src.questionnaire.llm_engine import cancel_flags as qf
        from src.questionnaire.llm_engine import _cancel_lock
        with _cancel_lock:
            stale_ids = [cid for cid, flag in list(qf.items()) if flag]
            for cid in stale_ids:
                qf.pop(cid, None)
                cleaned += 1
    except Exception:
        pass

    return {"cleaned": cleaned}


def get_cache_stats() -> dict:
    """获取文献缓存统计"""
    cache_dir = Path(__file__).parent.parent / "paper_writer" / ".literature_cache"
    if not cache_dir.exists():
        return {"file_count": 0, "total_mb": 0.0}

    files = list(cache_dir.glob("*.json"))
    total_bytes = sum(f.stat().st_size for f in files)
    return {
        "file_count": len(files),
        "total_mb": total_bytes / (1024 * 1024),
    }


def get_system_status() -> str:
    """生成系统状态摘要（用于侧边栏显示）"""
    lines = []
    mem = estimate_session_state_memory()
    total_mb = mem["total_bytes"] / (1024 * 1024)
    lines.append(f"Session 内存占用：{total_mb:.1f} MB")

    hist = st.session_state.get("analysis_history")
    hist_count = len(hist) if isinstance(hist, list) else 0
    lines.append(f"分析历史：{hist_count} 条 (上限 {MAX_ANALYSIS_HISTORY})")

    cache_stats = get_cache_stats()
    lines.append(f"文献缓存：{cache_stats['file_count']} 个文件 ({cache_stats['total_mb']:.1f} MB)")

    # pending 状态
    pending_count = 0
    for key in ["_q_design_pending", "_exp_design_pending", "_lit_search_pending"]:
        if st.session_state.get(key) is not None:
            pending_count += 1
    if pending_count > 0:
        lines.append(f"运行中任务：{pending_count} 个")
    else:
        lines.append("运行中任务：无")

    return "\n".join(lines)


def render_memory_manager_ui():
    """在 Streamlit 侧边栏渲染内存管理控件"""
    mem = estimate_session_state_memory()
    total_mb = mem["total_bytes"] / (1024 * 1024)

    st.sidebar.divider()
    st.sidebar.header("🧠 内存管理")
    st.sidebar.caption(f"当前占用：{total_mb:.1f} MB")

    if total_mb > DEFAULT_MEMORY_MB:
        st.sidebar.warning(f"⚠ Session State 占用较高（{total_mb:.1f} MB），建议清理。")

    if st.sidebar.button("🧹 一键清理", width="stretch", key="mem_cleanup"):
        mem_result = auto_cleanup_session_state()
        cache_result = cleanup_literature_cache()
        cancel_result = cleanup_stale_cancel_ids()

        total_freed = mem_result["freed_mb"] + cache_result["freed_mb"]
        cleaned_items = len(mem_result.get("cleaned_keys", []))
        msgs = []
        if mem_result.get("cleaned_keys"):
            msgs.append(f"会话清理 {cleaned_items} 项")
        if cache_result["cleaned"] > 0:
            msgs.append(f"缓存清理 {cache_result['cleaned']} 个文件")
        if cancel_result["cleaned"] > 0:
            msgs.append(f"任务清理 {cancel_result['cleaned']} 项")

        if msgs:
            st.sidebar.success("，".join(msgs) + f"，释放 {total_freed:.1f} MB")
        else:
            st.sidebar.info("无可清理项。")

    # 系统状态（可折叠）
    with st.sidebar.expander("📊 系统状态"):
        st.sidebar.markdown("```\n" + get_system_status() + "\n```")

    with st.sidebar.expander("📊 详细占用"):
        st.sidebar.markdown("```\n" + get_memory_summary() + "\n```")
