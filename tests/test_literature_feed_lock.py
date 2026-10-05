"""v4.7 自学习模块 — 跨进程文件锁测试。

覆盖：
- 单进程内同时持锁 → 第二个 LockBusyError
- is_held_by_other 正确反映状态
- stale 锁文件可被强抢
"""

from __future__ import annotations

import os
import time

import pytest

_FEED_PACKAGE_PREFIX = "src.literature_feed"


@pytest.fixture
def feed_root(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    import sys
    # s1002-06 窄口径化：宽口径驱逐（删全部 src.literature_feed* 不还原）会与
    # 「模块期 import＋monkeypatch 模块属性」的兄弟件互撞（s924-29 根因面）。
    # 照 test_feed_panel_trending_override 的快照-还原模式：驱逐前留还原点，
    # teardown 先清本夹具新建的模块再整体还原。
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


class TestLockManager:

    def test_single_acquire_releases(self, feed_root):
        from src.literature_feed.scheduler import LockManager

        lock = LockManager()
        with lock.acquire():
            pass
        # 释放后再来一次应该 OK
        with lock.acquire():
            pass

    def test_concurrent_acquire_blocks_second(self, feed_root):
        from src.literature_feed.scheduler import LockManager, LockBusyError

        lock1 = LockManager()
        lock2 = LockManager()
        with lock1.acquire():
            with pytest.raises(LockBusyError):
                with lock2.acquire():
                    pass

    def test_is_held_by_other(self, feed_root):
        from src.literature_feed.scheduler import LockManager

        lock = LockManager()
        probe = LockManager()
        assert probe.is_held_by_other() is False
        with lock.acquire():
            assert probe.is_held_by_other() is True
        assert probe.is_held_by_other() is False

    def test_stale_lock_break(self, feed_root):
        from src.literature_feed.scheduler import LockManager
        from src.literature_feed.paths import FETCH_LOCK_FILE

        # 手动制造一个老锁文件
        FETCH_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        FETCH_LOCK_FILE.write_text("zombie", encoding="utf-8")
        old = time.time() - 7200  # 2 小时前
        os.utime(FETCH_LOCK_FILE, (old, old))

        lock = LockManager(ttl_seconds=3600)
        assert lock.is_stale() is True
        assert lock.break_stale() is True
        assert FETCH_LOCK_FILE.exists() is False

    def test_nested_acquire_raises(self, feed_root):
        from src.literature_feed.scheduler import LockManager

        lock = LockManager()
        with lock.acquire():
            with pytest.raises(RuntimeError):
                # 同一实例不允许嵌套
                lock._open_and_lock()
