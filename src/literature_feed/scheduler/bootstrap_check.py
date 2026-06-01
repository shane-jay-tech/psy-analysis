"""Streamlit 应用启动时的"懒检查"——决定要不要后台触发一次抓取。

工作机制：
- 读 ``fetch_runs.last_completed.ended_at``，算出距今小时数
- 默认阈值 24 小时；超过就在后台线程里跑 ``run_daily(trigger='app_startup')``
- 锁冲突自动让位（Task Scheduler 已经在跑就跳过）
- 不阻塞 UI；后台失败/成功通过 ``last_async_result()`` 暴露给 UI 轮询（DeepSeek #4）

调用方典型用法（Streamlit 页头）::

    from src.literature_feed.scheduler.bootstrap_check import maybe_trigger_async, last_async_result
    maybe_trigger_async()
    # 别处：
    res = last_async_result()
    if res and res["status"] == "failed":
        st.warning(f"上次自动抓取失败：{res['error']}")
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..storage.feed_store import FeedStore
from .daily_runner import run_daily

logger = logging.getLogger(__name__)

DEFAULT_STALE_HOURS = 24.0
_LAST_TRIGGER_LOCK = threading.Lock()
_BACKGROUND_THREAD: Optional[threading.Thread] = None
_LAST_ASYNC_RESULT: Optional[Dict[str, Any]] = None  # UI 可读最近一次后台运行结果


@dataclass
class BootstrapDecision:
    should_run: bool
    last_success_hours: Optional[float]
    reason: str


def evaluate(*, stale_hours: float = DEFAULT_STALE_HOURS) -> BootstrapDecision:
    """只读判断：现在该不该跑。返回决定不触发副作用。"""
    try:
        store = FeedStore()
    except Exception as exc:  # noqa: BLE001 — DB 还没建？让上层显式启动
        return BootstrapDecision(False, None, f"FeedStore 打开失败: {exc}")
    try:
        hours = store.hours_since_last_success()
    except Exception as exc:  # noqa: BLE001
        return BootstrapDecision(False, None, f"hours_since_last_success 失败: {exc}")
    finally:
        try:
            store.close()
        except Exception:  # noqa: BLE001
            pass

    if hours is None:
        return BootstrapDecision(True, None, "从未成功跑过 daily_runner，建议立刻跑一次")
    if hours >= stale_hours:
        return BootstrapDecision(
            True, hours, f"距上次成功 {hours:.1f}h ≥ 阈值 {stale_hours}h",
        )
    return BootstrapDecision(False, hours, f"距上次成功 {hours:.1f}h，无需触发")


def maybe_trigger_async(
    *,
    stale_hours: float = DEFAULT_STALE_HOURS,
    do_extract: bool = True,
) -> BootstrapDecision:
    """读 + 决定 + 后台启动。同一进程内已经在跑就跳过。"""
    decision = evaluate(stale_hours=stale_hours)
    if not decision.should_run:
        return decision

    global _BACKGROUND_THREAD
    with _LAST_TRIGGER_LOCK:
        if _BACKGROUND_THREAD is not None and _BACKGROUND_THREAD.is_alive():
            logger.info("bootstrap_check：已有后台抓取线程在跑，跳过")
            return BootstrapDecision(False, decision.last_success_hours, "进程内已有后台任务")
        thread = threading.Thread(
            target=_safe_run,
            kwargs={"do_extract": do_extract},
            name="literature-feed-bootstrap",
            daemon=True,
        )
        _BACKGROUND_THREAD = thread
        thread.start()
        logger.info("bootstrap_check：已后台触发 run_daily（do_extract=%s）", do_extract)
    return decision


def last_async_result() -> Optional[Dict[str, Any]]:
    """UI 轮询专用。返回最近一次后台运行的精简结果（status / error / counts），未跑过返回 None。"""
    return _LAST_ASYNC_RESULT


def is_running() -> bool:
    """后台线程是否正在跑。"""
    return _BACKGROUND_THREAD is not None and _BACKGROUND_THREAD.is_alive()


def _safe_run(*, do_extract: bool) -> None:
    global _LAST_ASYNC_RESULT
    try:
        summary = run_daily(trigger="app_startup", do_extract=do_extract)
        logger.info("bootstrap async run done: status=%s sources=%d",
                    summary.status, len(summary.sources))
        _LAST_ASYNC_RESULT = {
            "status": summary.status,
            "ended_at": summary.ended_at,
            "sources_ok": sum(1 for s in summary.sources.values() if s.status.startswith("ok")),
            "sources_total": len(summary.sources),
            "extracted_constructs": summary.extracted_constructs,
            "extracted_methods": summary.extracted_methods,
            "budget_exceeded": summary.budget_exceeded,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("bootstrap async run 失败：%s", exc)
        _LAST_ASYNC_RESULT = {
            "status": "failed",
            "ended_at": None,
            "sources_ok": 0,
            "sources_total": 0,
            "extracted_constructs": 0,
            "extracted_methods": 0,
            "budget_exceeded": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
