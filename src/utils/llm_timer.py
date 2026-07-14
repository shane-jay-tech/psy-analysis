"""LLM 调用等待体验：动态计时 + 分阶段提示 + 取消支持。

增强逻辑：
- 0s: "正在思考..."
- 10s: 显示已等待秒数
- 30s: 提示可能较慢
- 60s: 提供取消建议
- 失败: 显示模型名、耗时、可操作建议
"""
import time
import threading
from contextlib import contextmanager

import streamlit as st


_CANCEL_KEY = "_llm_cancel_requested"
_ACTIVE_CANCEL_ID_KEY = "_llm_active_cancel_id"


def request_cancel():
    """用户主动取消 LLM 调用 — 同时通知底层 gateway 中断请求。"""
    st.session_state[_CANCEL_KEY] = True
    cancel_id = st.session_state.get(_ACTIVE_CANCEL_ID_KEY)
    if cancel_id:
        try:
            from src.llm_gateway.gateway import cancel_request
            cancel_request(cancel_id)
        except Exception:
            pass


def set_active_cancel_id(cancel_id: str):
    """由调用方设置当前 LLM 请求的 cancel_id，以便 UI 取消时联动。"""
    st.session_state[_ACTIVE_CANCEL_ID_KEY] = cancel_id


def is_cancel_requested() -> bool:
    return st.session_state.get(_CANCEL_KEY, False)


def clear_cancel():
    st.session_state.pop(_CANCEL_KEY, None)
    st.session_state.pop(_ACTIVE_CANCEL_ID_KEY, None)


@contextmanager
def llm_status(label: str = "AI 思考中", timeout_hint: int = 60, model_name: str = ""):
    """Context manager: 动态计时 + 分阶段提示。

    Usage:
        with llm_status("AI 正在审阅", model_name="deepseek-v4-pro"):
            result = call_llm(...)
    """
    container = st.empty()
    start = time.time()
    stop_event = threading.Event()
    clear_cancel()

    def _tick():
        while not stop_event.is_set():
            elapsed = time.time() - start
            if elapsed < 3:
                msg = f"⏳ {label}..."
            elif elapsed < 10:
                msg = f"⏳ {label}... ({elapsed:.0f}s)"
            elif elapsed < 30:
                msg = f"⏳ {label}... 已等待 {elapsed:.0f}s"
            elif elapsed < 60:
                msg = f"⏳ {label}... 已等待 {elapsed:.0f}s（较慢，可能是网络或模型排队）"
            else:
                msg = f"⏳ {label}... 已等待 {elapsed:.0f}s（超过1分钟，如无响应可取消重试）"
            try:
                container.info(msg)
            except Exception:
                break
            stop_event.wait(1.0)

    ticker = threading.Thread(target=_tick, daemon=True)
    ticker.start()

    exc_occurred = False
    try:
        yield container
    except BaseException as e:
        exc_occurred = True
        stop_event.set()
        ticker.join(timeout=2)
        elapsed = time.time() - start
        model_info = f"（模型: {model_name}）" if model_name else ""
        container.error(
            f"❌ {label} — 失败 ({elapsed:.0f}s){model_info}\n\n"
            f"建议：检查网络连接，或稍后重试。"
        )
        raise
    finally:
        stop_event.set()
        ticker.join(timeout=2)
        if not exc_occurred:
            elapsed = time.time() - start
            if elapsed > 2:
                container.success(f"✅ {label} — 完成 ({elapsed:.0f}s)")
            else:
                container.empty()
