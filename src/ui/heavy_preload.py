"""后台预热线程（d914-23 第三批拆分自 app.py:336-352，行为零变更）。

v5.8 预热语义逐字保持：daemon 线程、进程内只起一次（_heavy_preload_started
session 门）、导入失败静默——真正用到时会有明确的懒加载错误提示。
"""
import threading

import streamlit as st


def preload_heavy_deps() -> None:
    try:
        import scipy.stats  # noqa: F401
        import statsmodels.api  # noqa: F401
        import pingouin  # noqa: F401
        import sklearn.cluster  # noqa: F401
        import factor_analyzer  # noqa: F401
        import openpyxl  # noqa: F401
        import jieba  # noqa: F401
        import semopy  # noqa: F401
        import kaleido  # noqa: F401
    except Exception:
        pass  # 预热失败静默——真正用到时会有明确的懒加载错误提示


def start_heavy_preload_once() -> None:
    """每会话只起一次预热线程（session 门语义与原内联块一致）。"""
    if not st.session_state.get("_heavy_preload_started"):
        st.session_state._heavy_preload_started = True
        try:
            threading.Thread(target=preload_heavy_deps, daemon=True, name="heavy-preload").start()
        except Exception:
            pass
