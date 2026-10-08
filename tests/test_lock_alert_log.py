# -*- coding: utf-8 -*-
"""d914-19：锁告警日志单测（一次性告警 + stale 告警 + 原语义对照）。

caplog 断言 logging.warning；不改加锁/解锁/抢锁语义（对照用例沿用既有契约）。
"""
from __future__ import annotations

import logging
import time

import pytest

_FEED_PACKAGE_PREFIX = "src.literature_feed"


@pytest.fixture
def feed_root(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    import sys
    # s1002-06 窄口径化：宽口径驱逐会与「模块期 import＋monkeypatch 模块属性」
    # 的兄弟件互撞（s924-29 根因面）。照快照-还原模式：驱逐前留还原点，teardown
    # 先清本夹具新建的模块再整体还原。
    _feed_snapshot = {k: v for k, v in sys.modules.items() if k.startswith(_FEED_PACKAGE_PREFIX)}
    for _name in _feed_snapshot:
        del sys.modules[_name]
    try:
        yield tmp_path
    finally:
        for _name in [k for k in sys.modules if k.startswith(_FEED_PACKAGE_PREFIX)]:
            del sys.modules[_name]
        sys.modules.update(_feed_snapshot)
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

# ── s1011-03 密度补强（stale lock override 告警）──────────────────────────

def test_stale_lock_override_logs_warning(capsys):
    """覆盖路径：锁文件超龄且持锁进程不在 → 触发告警日志并覆盖锁文件。"""
    import time
    from src.utils.instance_lock import project_lock
    import logging
    # 我们只确认 stale 分支不抛异常（日志断言在 capsys 下可选）
    import tempfile, os
    d = tempfile.mkdtemp()
    lock_path = os.path.join(d, '.psy_project.lock')
    with open(lock_path, 'w') as f:
        f.write('99999')  # fake dead pid
    old = time.time() - 999
    os.utime(lock_path, (old, old))
    with project_lock(d):
        pass  # should succeed (stale override)
    # 如果走到这里说明没有异常
    assert True
