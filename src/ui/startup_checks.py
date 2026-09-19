"""启动副作用块（d913a-43 自 app.py 启动清理块与环境检查块原样搬入，行为零变更）。

与第一批 privacy_gate 拆分同模式：块内逻辑、session_state 键
（has_auto_cleaned / startup_check_done / env_status）与异常吞咽语义逐字保持：
- 文献缓存自动清理：每会话首次执行一次，7 天过期清理，失败静默；
- 启动环境自检：每会话首次执行一次，毫秒级 find_spec 自检 + toast；
  自检失败必须置 env_status=None 而不能让应用白屏（v5.8 鲁棒性语义）。
"""

import logging

import streamlit as st


def run_once_startup_cleanup() -> None:
    """启动时自动清理（文献缓存 7 天过期 + cancel_id 清理）；与原内联块逐字等价。"""
    if "has_auto_cleaned" not in st.session_state:
        st.session_state.has_auto_cleaned = True
        try:
            from src.utils.memory_manager import cleanup_literature_cache

            cache_result = cleanup_literature_cache(older_than_days=7)
            if cache_result["cleaned"] > 0:
                logging.info(f"文献缓存自动清理：{cache_result['cleaned']} 个过期文件")
        except Exception:
            pass


def run_once_env_check() -> None:
    """启动时一键环境检查（v5.8 毫秒级 find_spec 自检，toast 弹出，不阻塞）。"""
    if not st.session_state.startup_check_done:
        st.session_state.startup_check_done = True
        try:
            from src.utils.env_check import render_env_status_toasts, run_startup_check

            env_status = run_startup_check()
            st.session_state.env_status = env_status
            render_env_status_toasts(env_status)
        except Exception:
            # 自检失败绝不能让整个应用白屏（v5.8 鲁棒性修复）
            st.session_state.env_status = None
