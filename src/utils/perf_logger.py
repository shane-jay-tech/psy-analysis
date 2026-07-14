"""性能事件日志 v5.1。

记录核心流程耗时到本地 JSONL 文件，用于性能趋势分析。
默认保存到 data/perf_log.jsonl，可通过环境变量 PERF_LOG=0 关闭。
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional


PERF_LOG_PATH = Path("data/perf_log.jsonl")
_ENABLED = os.environ.get("PERF_LOG", "1") != "0"


@contextmanager
def perf_timer(event: str, **metadata):
    """上下文管理器：自动计时并记录性能事件。

    用法:
        with perf_timer("zip_export", project_id="demo"):
            build_zip(...)
    """
    start = time.perf_counter()
    result = {"status": "success"}
    try:
        yield result
    except Exception as e:
        result["status"] = "error"
        result["error_type"] = type(e).__name__
        raise
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        log_perf_event(event, duration_ms=duration_ms, **metadata, **result)


def log_perf_event(
    event: str,
    duration_ms: int = 0,
    **kwargs,
):
    """记录一条性能事件。"""
    if not _ENABLED:
        return

    entry = {
        "event": event,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "duration_ms": duration_ms,
    }
    entry.update(kwargs)

    try:
        PERF_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PERF_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_perf_log(last_n: int = 100) -> list[dict]:
    """读取最近 N 条性能日志。"""
    if not PERF_LOG_PATH.exists():
        return []
    lines = PERF_LOG_PATH.read_text(encoding="utf-8").strip().split("\n")
    entries = []
    for line in lines[-last_n:]:
        try:
            entries.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue
    return entries


def clear_perf_log() -> int:
    """清除性能日志。返回删除的条目数。"""
    if not PERF_LOG_PATH.exists():
        return 0
    count = len(PERF_LOG_PATH.read_text(encoding="utf-8").strip().split("\n"))
    PERF_LOG_PATH.unlink()
    return count


def perf_summary(last_n: int = 50) -> dict:
    """获取性能摘要统计。"""
    entries = read_perf_log(last_n)
    if not entries:
        return {"total_events": 0}

    by_event = {}
    for e in entries:
        evt = e.get("event", "unknown")
        if evt not in by_event:
            by_event[evt] = []
        by_event[evt].append(e.get("duration_ms", 0))

    summary = {"total_events": len(entries), "by_event": {}}
    for evt, durations in by_event.items():
        summary["by_event"][evt] = {
            "count": len(durations),
            "avg_ms": int(sum(durations) / len(durations)),
            "max_ms": max(durations),
            "min_ms": min(durations),
        }
    return summary
