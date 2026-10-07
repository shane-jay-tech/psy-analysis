"""literature_feed 域统一 UTC 时间戳单源（s1010-14 收编）。

格式：秒精度 ISO8601 Z 串（例 ``2026-10-08T02:55:07Z``）——存储/归档外部接口面。
历史两形态（review_service strftime 形、crossref/psy_science isoformat 形）已经
tests/test_literature_feed_utcnow_s1010_14.py 钉桩证明逐字节等价；本单源取 strftime 形。
"""
from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
