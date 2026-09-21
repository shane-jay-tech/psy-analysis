"""src/literature_feed/scheduler/lock_manager.py 锁语义特征化测试（s918-57）。

锁文件一律放 `tmp_path`，并 autouse 挡掉 `ensure_dirs()`——**否则构造 LockManager 就会在
真实 `data/literature_feed/` 下建目录**（见 `_alert_once` 之外的唯一副作用）。零网络、零真实调度器。
锚点：:54 `ttl_seconds: int = 21600,  # 6h`；判陈旧在 :128 起（`def is_stale`）。
s922-10 订正：此处原写 `:123`，那是 s919-05（5a9e46f）时的实况；`def is_stale` 被
s920-08（5fe7754，LockBusyError 带持有者 pid）位移 +5 → :128，此后 s921-13（e02df5a）加 `now`
接缝只改签名不改行号，:128 至今未再漂（`git show <sha>:…/lock_manager.py | grep -n "def is_stale"`
逐个复测）。:54 那一条自始至终没漂。
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


# s921-13：`is_stale(now=…)` 时钟接缝落地后，边界从"两侧留裕量"改成"精确压线"。
_FIXED_MTIME = 1_000.0          # 1970-01-01 附近的固定基准，避免文件系统时间戳量化


def test_is_stale_boundary_is_strictly_greater_than_ttl(tmp_path):
    """恰 ttl ⇒ 不陈旧；超 ttl（这里取 0.5 秒，任务书口径的"超 1 秒"同侧）⇒ 陈旧。钉住 `lock_manager.py:148` 的 `>` 而非 `>=`。

    旧用例（`ttl=100 / mtime=now±50`）证不了这件事：`os.utime` 里那次 `time.time()`
    与 SUT 里那次之间必然已过去若干微秒 ⇒ age 恒偏大，压着 ttl 断"不陈旧"会随机翻红。
    s919-22 因此改写成立即断两侧、s920-24 又把裕量从 1 秒抬到 50 秒，并在遗留 1 里点名
    "根治是给 is_stale 加时钟接缝"。接缝给了 `now` 之后：mtime 用固定基准常量
    （`st_mtime` 回读校验文件系统没量化掉它），`now` 由调用方给，两个都是精确可表示的
    小数 ⇒ age 恰等于 ttl，边界的开闭才谈得上"断言"。
    """
    path = _lock_file(tmp_path)
    mgr = LockManager(path, ttl_seconds=100)
    path.write_text("\n", encoding="utf-8")
    os.utime(path, (_FIXED_MTIME, _FIXED_MTIME))
    assert path.stat().st_mtime == _FIXED_MTIME          # 前提：文件系统老实存了固定基准

    assert mgr.is_stale(now=_FIXED_MTIME + 100) is False  # age == ttl：`>` 判不陈旧
    assert mgr.is_stale(now=_FIXED_MTIME + 100.5) is True  # 超半秒也算陈旧（不是"约等"）
    assert mgr.is_stale(now=_FIXED_MTIME - 1) is False     # NTP 回拨导致 age<0：不炸，仍不陈旧


def test_is_stale_now_defaults_to_wall_clock(tmp_path):
    """缺省不改变语义：不传 now 走真实时钟；传 now 的结论可以与真实时钟相反。"""
    path = _lock_file(tmp_path)
    mgr = LockManager(path, ttl_seconds=100)
    path.write_text("\n", encoding="utf-8")               # mtime = 真实"现在"
    assert mgr.is_stale() is False                        # 缺省：age≈0 ⇒ 不陈旧
    assert mgr.is_stale(now=time.time() + 200) is True     # 注入"未来"⇒ 陈旧：缺省值确实被让位
    assert mgr.is_stale(now=_FIXED_MTIME) is False         # 注入 1970 年 ⇒ age 负 ⇒ 不陈旧

    os.utime(path, (_FIXED_MTIME, _FIXED_MTIME))           # 把锁文件拨回 1970
    assert mgr.is_stale() is True                          # 缺省仍读真实时钟 ⇒ 陈旧
    assert mgr.is_stale(now=_FIXED_MTIME + 50) is False     # 注入的时钟里它才"不陈旧"


def test_stale_alert_age_uses_the_injected_clock(tmp_path, caplog):
    """告警年龄与判据共用同一个 now：注入的时钟决定 age_min，不再二次取时间。"""
    path = _lock_file(tmp_path)
    mgr = LockManager(path, ttl_seconds=100)
    path.write_text("\n", encoding="utf-8")
    os.utime(path, (_FIXED_MTIME, _FIXED_MTIME))

    with caplog.at_level("WARNING"):
        assert mgr.is_stale(now=_FIXED_MTIME + 600) is True
    msgs = [r.getMessage() for r in caplog.records if "stale_lock" in r.getMessage()]
    assert len(msgs) == 1
    assert "stale for 10 min" in msgs[0]                    # age=600s ⇒ 10 min，取的是注入的 now
    assert "ttl=100s" in msgs[0]


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


# ────────────────── s920-08：抢锁失败要说得出"谁占着"，写不进持有者要吱一声 ──────────────────
def test_busy_message_carries_the_real_owner_pid(tmp_path):
    """真实两个实例抢同一把锁（Windows 下同一进程的第二个句柄也会被拒），消息里要带持有者 pid。"""
    path = _lock_file(tmp_path)
    holder, waiter = LockManager(path, ttl_seconds=60), LockManager(path, ttl_seconds=60)

    with holder.acquire():
        with pytest.raises(LockBusyError) as ei:
            waiter._open_and_lock()

    msg = str(ei.value)
    assert msg.startswith("锁已被其他进程持有")            # 原文案一字不动，只在后面追加
    assert f"持有者 pid={os.getpid()}" in msg             # 真从锁文件读到了，不是猜的
    assert isinstance(ei.value, RuntimeError)             # 类型没变，既有 `except LockBusyError` 照常接住


def test_busy_message_falls_back_to_unknown(tmp_path, monkeypatch):
    path = _lock_file(tmp_path)
    holder = LockManager(path, ttl_seconds=60)
    waiter = LockManager(path, ttl_seconds=60)
    monkeypatch.setattr(waiter, "_read_owner_pid", lambda: None)

    with holder.acquire():
        with pytest.raises(LockBusyError) as ei:
            waiter._open_and_lock()

    assert "持有者 pid=unknown" in str(ei.value)           # 读不到≠没信息，得明说"不知道"


def test_platform_lock_error_also_gets_the_owner_suffix(tmp_path, monkeypatch):
    """`_do_lock` 抛 OSError（不是 LockBusyError）那条分支同样要带持有者，且不漏 fd。"""
    mgr = LockManager(_lock_file(tmp_path), ttl_seconds=60)
    monkeypatch.setattr(mgr, "_do_lock",
                        lambda fh: (_ for _ in ()).throw(OSError("EACCES")))
    monkeypatch.setattr(mgr, "_read_owner_pid", lambda: 4321)

    with pytest.raises(LockBusyError) as ei:
        mgr._open_and_lock()

    assert "获取锁失败" in str(ei.value) and "pid=4321" in str(ei.value)
    assert mgr._fh is None                                 # 抛出前关掉了自己刚开的句柄


def test_owner_write_failure_alerts_once_while_lock_stays_held(tmp_path, monkeypatch, caplog):
    import logging

    mgr = LockManager(_lock_file(tmp_path), ttl_seconds=60)
    with caplog.at_level(logging.WARNING, logger=""):
        with mgr.acquire():
            good = mgr._fh

            class BadFh:
                def seek(self, *a):
                    raise OSError("disk full")

            monkeypatch.setattr(mgr, "_fh", BadFh())
            mgr._write_owner_info()                        # 不许抛出去
            assert mgr._fh is not None                     # 写失败不算致命，锁还在手上
            assert "owner_write_failed" in mgr._alerted
            mgr._write_owner_info()                        # 第二次不该再刷
            monkeypatch.setattr(mgr, "_fh", good)

    alerts = [r.getMessage() for r in caplog.records if "[lock-alert]" in r.getMessage()]
    assert len(alerts) == 1                                # 同一 kind 每实例只报一次
    assert "disk full" in alerts[0] and "锁仍有效" in alerts[0]


def test_acquire_succeeds_even_if_fsync_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(lmk.os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("flush 失败")))
    mgr = LockManager(_lock_file(tmp_path), ttl_seconds=60)

    with mgr.acquire() as got:
        assert got is mgr                                  # 互斥照常成立
        assert "owner_write_failed" in mgr._alerted        # 但这次是静默失败改成了有声失败
    assert mgr._fh is None                                 # 退出仍正常释放


# ─────────────────────────────────────────────────────────────────────────────
# s922-109 追加：边界真值已挪到 `tests/test_lock_stale_boundary.py`（19 例、零 sleep、
# 零裕量），本文件 :83 那条压线例与它**同一口径**（固定基准 mtime + 注入 now ⇒ age 精确）。
# 下面两例钉的是"为什么本文件 :133/:147 仍要留真实时钟裕量"——那两处**不能**改走接缝写法，
# 因为入口根本没接 now 参数。任务书「同批修，不留双口径」的实测结论见这两条例子的 docstring。
# ─────────────────────────────────────────────────────────────────────────────
def test_break_stale_and_acquire_expose_no_clock_seam(tmp_path):
    """结构面钉桩：`break_stale()` / `acquire()` 的签名里**没有** `now`，只有 `is_stale` 有。

    ⇒ 本文件 `test_break_stale_deletes_only_when_stale`（:133）与
    `test_acquire_steals_a_stale_lock`（:147）用的真实时钟裕量不是"没改干净的双口径"，
    而是**接缝缺失下的唯一写法**（`break_stale:159` 内部硬调 `self.is_stale()` 不带参）。
    出口（属行为改动、本班不做）：给这两个入口加同样的可选 `now` 接缝，
    那两条用例即可改成压线写法、裕量随之取消。若哪天实现补了 `now` 参数，本用例会红——那是设计内翻正。
    """
    import inspect

    stale_params = list(inspect.signature(LockManager.is_stale).parameters)
    assert stale_params == ["self", "now"], stale_params
    assert list(inspect.signature(LockManager.break_stale).parameters) == ["self"]
    assert list(inspect.signature(LockManager.acquire).parameters) == ["self"]


def test_break_stale_verdict_agrees_with_the_seam_readout(tmp_path):
    """单口径自证：真实时钟下 `break_stale()` 的结论，与同一状态下注入 `now` 的 `is_stale()` 一致。

    现状钉桩（裕量在这里只用来**免疫调度抖动**，不用来区分判据方向）：
    把锁文件拨到 `now - ttl - 5`，两侧都判陈旧；拨到 `now - ttl + 5`（即 age 还差 5 秒），两侧都判不陈旧。
    若边界判据被改成 `>=`，本用例仍绿——它钉的是"两个入口同判据"，
    压线方向由 `tests/test_lock_stale_boundary.py` 锁死，两档不重复计账。
    """
    path = _lock_file(tmp_path, "break.lock")
    mgr = LockManager(path, ttl_seconds=100)
    path.write_text("\n", encoding="utf-8")

    aged = time.time() - 105                                 # age ≈ 105 > 100
    os.utime(path, (aged, aged))
    assert mgr.is_stale(now=aged + 105) is True              # 接缝口径
    assert mgr.break_stale() is True                         # 真实时钟口径 ⇒ 删档
    assert not path.exists()

    path.write_text("\n", encoding="utf-8")
    fresh = time.time() - 95                                 # age ≈ 95 < 100
    os.utime(path, (fresh, fresh))
    assert mgr.is_stale(now=fresh + 95) is False
    assert mgr.break_stale() is False                        # 同一判据，不删
    assert path.exists()
