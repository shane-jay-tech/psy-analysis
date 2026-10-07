# -*- coding: utf-8 -*-
"""s1010-14 _utc_now 三份同体收编：等价性钉桩（红线——无等价断言不得收编）。

历史两形态（收编前，result 存档）：
  A strftime 形  review_service.py:39   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  B isoformat 形 crossref.py:175 等      now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
"""
import re
from datetime import datetime, timezone

from src.literature_feed import timestamps


def _form_a(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def _form_b(now: datetime) -> str:
    return now.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_two_historical_forms_byte_equivalent():
    """两形态对同一受控 now 输出逐字节相同（秒精度 ISO8601 Z 串）。"""
    for now in (
        datetime(2026, 10, 8, 2, 55, 7, 123456, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 0, 0, 999999, tzinfo=timezone.utc),
        datetime(2026, 12, 31, 23, 59, 59, 1, tzinfo=timezone.utc),
    ):
        assert _form_a(now) == _form_b(now)
    assert _form_a(datetime(2026, 10, 8, 2, 55, 7, 123456, tzinfo=timezone.utc)) == "2026-10-08T02:55:07Z"


def test_single_source_shape():
    """单源输出为秒精度 ISO8601 Z 串。"""
    out = timestamps.utc_now()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", out), out


def test_legacy_utcnow_defs_absent():
    """域内三件不再有 def _utc_now（收编后单源唯一）。"""
    import importlib
    import inspect

    for modname in (
        "src.literature_feed.review_service",
        "src.literature_feed.fetchers.crossref",
        "src.literature_feed.fetchers.psy_science_official",
    ):
        mod = importlib.import_module(modname)
        src = inspect.getsource(mod)
        assert "def _utc_now" not in src, modname
        assert "timestamps import utc_now" in src or "timestamps.utc_now" in src, modname
