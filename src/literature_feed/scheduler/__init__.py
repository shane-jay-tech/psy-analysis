"""调度层：双触发去重锁 + 启动懒检查 + Task Scheduler 入口。"""

from .bootstrap_check import (
    BootstrapDecision,
    DEFAULT_STALE_HOURS,
    evaluate,
    maybe_trigger_async,
)
from .daily_runner import (
    DEFAULT_DAYS_BACK,
    DEFAULT_FETCH_LIMIT,
    MAX_EXTRACT_ARTICLES_PER_RUN,
    DailyRunner,
    RunSummary,
    SourceSummary,
    build_fetcher,
    run_daily,
)
from .lock_manager import LockBusyError, LockManager

__all__ = [
    "BootstrapDecision",
    "DEFAULT_DAYS_BACK",
    "DEFAULT_FETCH_LIMIT",
    "DEFAULT_STALE_HOURS",
    "DailyRunner",
    "LockBusyError",
    "LockManager",
    "MAX_EXTRACT_ARTICLES_PER_RUN",
    "RunSummary",
    "SourceSummary",
    "build_fetcher",
    "evaluate",
    "maybe_trigger_async",
    "run_daily",
]
