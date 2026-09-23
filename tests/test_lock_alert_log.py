# -*- coding: utf-8 -*-
"""d914-19：锁告警日志单测（一次性告警 + stale 告警 + 原语义对照）。

caplog 断言 logging.warning；不改加锁/解锁/抢锁语义（对照用例沿用既有契约）。
"""
from __future__ import annotations

import logging
import time

import pytest


@pytest.fixture
def feed_root(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    import sys
    for m in list(sys.modules):
        if m.startswith("src.literature_feed"):
            del sys.modules[m]
    return tmp_path


def test_held_by_other_alerts_once(caplog, feed_root):
    from src.literature_feed.scheduler import LockManager

    with caplog.at_level(logging.WARNING, logger="src.literature_feed.scheduler.lock_manager"):
        holder = LockManager()
        with holder.acquire():  # 真实持有方（写 owner pid）
            probe = LockManager()
            assert probe.is_held_by_other() is True
            probe.is_held_by_other()  # 重复探测
            probe.is_held_by_other()

    warnings = [r for r in caplog.records if "held_by_other" in r.message]
    assert len(warnings) == 1, "一次性告警：重复探测不得刷屏"
    assert "lock=" in warnings[0].message


def test_stale_lock_alerts_once(caplog, feed_root):
    from src.literature_feed.scheduler import LockManager

    stale = LockManager(ttl_seconds=1)
    with stale.acquire():
        stale._write_owner_info()
    # 把锁文件 mtime 拨老，越过 TTL
    old = time.time() - 7200
    import os
    os.utime(stale.lock_path, (old, old))

    with caplog.at_level(logging.WARNING, logger="src.literature_feed.scheduler.lock_manager"):
        probe = LockManager(ttl_seconds=1)
        assert probe.is_stale() is True
        assert probe.is_stale() is True  # 重复探测

    warnings = [r for r in caplog.records if "stale_lock" in r.message]
    assert len(warnings) == 1, "stale 告警一次性"
    assert "stale for" in warnings[0].message


def test_acquire_semantics_unchanged(feed_root, caplog):
    """对照断言：告警落地后，加锁/释放/抢占语义与既有契约一致。"""
    from src.literature_feed.scheduler import LockBusyError, LockManager

    lock = LockManager()
    with lock.acquire():
        with pytest.raises(LockBusyError):
            LockManager().acquire().__enter__()
    # 释放后可重新获取
    with lock.acquire():
        pass
    # 告警不影响正常 acquire（无 held/stale 告警产生）
    alerts = [r for r in caplog.records if "lock-alert" in r.message]
    assert alerts == []
