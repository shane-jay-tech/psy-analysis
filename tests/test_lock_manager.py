"""src/literature_feed/scheduler/lock_manager.py 锁语义特征化测试（s918-57）。

锁文件一律放 `tmp_path`，并 autouse 挡掉 `ensure_dirs()`——**否则构造 LockManager 就会在
真实 `data/literature_feed/` 下建目录**（见 `_alert_once` 之外的唯一副作用）。零网络、零真实调度器。
锚点：:54 `ttl_seconds: int = 21600,  # 6h`；判陈旧在 :123 起（s919-05 修 `_read_owner_pid` 后行号位移）。
"""
import os
import time

import pytest

import src.literature_feed.scheduler.lock_manager as lmk
from src.literature_feed.scheduler.lock_manager import LockBusyError, LockManager


@pytest.fixture(autouse=True)
def no_real_dirs(monkeypatch):
    """构造函数里的 ensure_dirs() 会碰生产 data 目录，测试里一律换成 no-op。"""
    calls = []
    monkeypatch.setattr(lmk, "ensure_dirs", lambda: calls.append(1))
    return calls


def _lock_file(tmp_path, name="feed.lock"):
    return tmp_path / name


def test_default_ttl_is_six_hours(tmp_path):
    assert LockManager(_lock_file(tmp_path)).ttl_seconds == 21600


def test_no_op_when_lock_file_absent(tmp_path):
    mgr = LockManager(_lock_file(tmp_path, "never-created.lock"), ttl_seconds=5)

    assert mgr.is_stale() is False
    assert mgr.break_stale() is False


def test_acquire_writes_owner_pid_and_releases_afterwards(tmp_path):
    path = _lock_file(tmp_path)
    mgr = LockManager(path, ttl_seconds=60)

    with mgr.acquire():
        assert path.exists()
        assert mgr._fh is not None                     # 持锁中句柄在手上

    assert mgr._fh is None                             # finally 里必定解锁并清空
    assert f"pid={os.getpid()}" in path.read_text(encoding="utf-8")


def test_second_instance_is_refused_while_held(tmp_path):
    path = _lock_file(tmp_path)
    holder = LockManager(path, ttl_seconds=60)

    with holder.acquire():
        other = LockManager(path, ttl_seconds=60)
        with pytest.raises(LockBusyError):
            with other.acquire():
                pass                                   # 不该进来

    after = LockManager(path, ttl_seconds=60)
    with after.acquire():                              # 释放后可再抢
        assert after._fh is not None


def test_nested_acquire_on_same_instance_raises_runtime_error(tmp_path):
    mgr = LockManager(_lock_file(tmp_path), ttl_seconds=60)

    with mgr.acquire():
        with pytest.raises(RuntimeError, match="不要嵌套 acquire"):
            with mgr.acquire():
                pass


def test_is_stale_uses_margin_on_both_sides_of_ttl(tmp_path):
    """陈旧判据是 `lock_manager.py:123` 的 `(time.time() - mtime) > ttl`——**现算 wall clock**。

    因此不能拿"mtime 正好等于 ttl"当断言点：`os.utime` 里取的 `time.time()` 与 `is_stale()` 里那次
    之间必然已过去若干微秒，age 恒 > ttl ⇒ 断"不陈旧"会随机/近乎必然地红（本用例前一版正是这个坑，
    全量跑里稳定失败，s919-22 收口时改写成两侧留裕量）。
    没走"注入时钟"是因为 psy 有后台 autosave 线程，patch 全局 `time.time` 会牵连别人。
    """
    path = _lock_file(tmp_path)
    mgr = LockManager(path, ttl_seconds=10)
    path.write_text("\n", encoding="utf-8")

    os.utime(path, (time.time() - 9, time.time() - 9))
    assert mgr.is_stale() is False                     # ttl 内 1 秒：必不陈旧

    os.utime(path, (time.time() - 15, time.time() - 15))
    assert mgr.is_stale() is True                      # 超 ttl 5 秒：必陈旧


def test_break_stale_deletes_only_when_stale(tmp_path):
    path = _lock_file(tmp_path)
    mgr = LockManager(path, ttl_seconds=10)
    path.write_text("\n", encoding="utf-8")

    assert mgr.break_stale() is False                  # 未过期不删
    assert path.exists()

    os.utime(path, (time.time() - 30, time.time() - 30))
    assert mgr.break_stale() is True
    assert not path.exists()
    assert mgr.break_stale() is False                  # 文件已没了，二次调用不炸


def test_acquire_steals_a_stale_lock(tmp_path):
    path = _lock_file(tmp_path)
    path.write_text("\n", encoding="utf-8")
    os.utime(path, (time.time() - 60, time.time() - 60))

    mgr = LockManager(path, ttl_seconds=5)
    with mgr.acquire():
        assert mgr._fh is not None


def test_is_held_by_other_false_when_free_and_lock_released_after_probe(tmp_path):
    path = _lock_file(tmp_path)
    mgr = LockManager(path, ttl_seconds=60)

    assert mgr.is_held_by_other() is False
    assert mgr._fh is None                             # 探测完必须自己放开


def test_alert_fires_once_per_kind(tmp_path, caplog):
    mgr = LockManager(_lock_file(tmp_path), ttl_seconds=1)
    path = mgr.lock_path
    path.write_text("\n", encoding="utf-8")
    os.utime(path, (time.time() - 5, time.time() - 5))

    with caplog.at_level("WARNING"):
        assert mgr.is_stale() is True
        assert mgr.is_stale() is True                  # 第二次不再告警
    assert sum('stale_lock' in r.message for r in caplog.records) == 1


def test_read_owner_pid_sees_the_pid_while_the_lock_is_held(tmp_path):
    """s919-05 翻正：从 offset 1 起读绕开被独占的 byte 0 ⇒ 持锁期就能拿到持有者 pid。

    旧口径（`read_text()` 整读）在持锁期必 PermissionError ⇒ `is_held_by_other()` 的告警恒为 pid=unknown；
    持有者信息本就写在 byte 1 之后（`_write_owner_info` 用 `\n` 当 sentinel），偏移 1 即够。
    """
    path = _lock_file(tmp_path)
    holder = LockManager(path, ttl_seconds=60)

    with holder.acquire():
        assert LockManager(path, ttl_seconds=60)._read_owner_pid() == os.getpid()

    assert LockManager(path, ttl_seconds=60)._read_owner_pid() == os.getpid()


def test_held_by_other_alert_carries_the_real_pid(tmp_path, caplog):
    """告警文案是用户唯一能看到的持锁者身份：`pid=<真值>`，不再是 unknown。"""
    path = _lock_file(tmp_path)
    holder = LockManager(path, ttl_seconds=60)

    with holder.acquire(), caplog.at_level("WARNING"):
        assert LockManager(path, ttl_seconds=60).is_held_by_other() is True

    msgs = [r.message for r in caplog.records if "held_by_other" in r.message]
    assert len(msgs) == 1
    assert f"pid={os.getpid()}" in msgs[0] and "pid=unknown" not in msgs[0]


def test_read_owner_pid_tolerates_missing_or_pidless_file(tmp_path):
    path = _lock_file(tmp_path, "junk.lock")
    mgr = LockManager(path, ttl_seconds=60)

    assert mgr._read_owner_pid() is None
    path.write_text("no pid marker here", encoding="utf-8")
    assert mgr._read_owner_pid() is None
    path.write_text("\npid=4242 acquired_at=x\n", encoding="utf-8")
    assert mgr._read_owner_pid() == 4242
