# -*- coding: utf-8 -*-
"""s927-35：`break_stale()` / `acquire()` 补 `now` 时钟接缝后的压线用例。

背景：s921-13 只给 `is_stale` 加了接缝（`lock_manager.py:137`），`break_stale`/`acquire`
两个公开入口没接 ⇒ s922-109 在 `tests/test_lock_manager.py:299` 钉了一枚"签名里没有 now"
的结构桩，并把根治出口登记在自己的「遗留问题 1」（原话："行为改动，待放行"）。
本档就是那条出口的落地验收：**恰好超时／恰好未超时两边界**各一条，零 sleep、零裕量、
零真实时钟依赖，两侧共用同一个固定基准 `BASE_MTIME`。

锚点复核（2026-09-28 本班按磁盘实况，HEAD `4ad0664` ＋ 本班 diff）：
- `src/literature_feed/scheduler/lock_manager.py:101` `def acquire(self, now: Optional[float] = None):`（本班新增接缝）
- `:112` `self._open_and_lock(now=now)`（本班新增透传）
- `:166` `def break_stale(self, now: Optional[float] = None) -> bool:`（本班新增接缝）
- `:175` `if not self.is_stale(now=now):`（原 `self.is_stale()` 不带参）
- `:186-192` `_open_and_lock(self, now=…)` → `is_stale(now=now)` → `break_stale(now=now)`（本班新增透传）
- 判据本体未动：`:157` `stale = age > self.ttl_seconds` —— **改成 `>=` 则本文件全部压线用例必红**
  （与 `tests/test_lock_stale_boundary.py:9-10` 同一口径，两档不重复计账）

写了什么 / 没写什么（s927-35 波次口径）：
- ✅ 只**补**用例；`tests/test_lock_manager.py:133` / `:147` 两条既有用例**一字未动**，
  任务书「既有用例一字不改仍要绿」的可达部分在此自证：接缝缺省 `None` ⇒ 老写法仍走真实时钟、仍绿。
- ❌ 没动 `tests/test_lock_manager.py:299` 那枚结构桩（它断的是"签名里没有 now"）。
  加接缝必然把它翻红，而它自己的 docstring 早已写明"若哪天实现补了 `now` 参数，本用例会红
  ——那是设计内翻正"。本班不改既有桩来凑绿（＝越界），只把它的处置口径交回主班：
  删掉、或按本文件 `test_the_two_entries_now_expose_the_seam` 反转成正向签名钉。

隔离口径（与 `tests/test_lock_manager.py:20-25`、`tests/test_lock_stale_boundary.py:39-44` 同款）：
`LockManager.__init__:61` 会调 `ensure_dirs()`，而 `src/literature_feed/paths.py` 的 `ensure_dirs()`
实打实 mkdir 三个生产目录（含 `data/literature_feed/locks/`）⇒ 本文件用 autouse 桩换成
记录调用次数的 no-op，锁文件一律落 `tmp_path`。零 sqlite、零网络、零 LLM、零子进程、零 sleep、零 data/ 写。
"""
from __future__ import annotations

import inspect
import math
import os
import time

import pytest

import src.literature_feed.scheduler.lock_manager as lmk
from src.literature_feed.scheduler.lock_manager import LockManager

# 固定基准取自 1970 附近（与 test_lock_stale_boundary.py:36 同一常量口径）：
# 这个量级 double 的 ulp 约 1.1e-13，`BASE_MTIME + TTL` 精确可表示 ⇒ age 正好落在 ttl 上。
BASE_MTIME = 1_000.0
TTL = 100
_LINE = BASE_MTIME + TTL                      # 恰好未超时（age == ttl，`>` 判不陈旧）
_MARKER = "MARKER-HELD-BY-SOMEONE-ELSE"       # 用来判"抢锁时到底有没有先删档"


@pytest.fixture(autouse=True)
def no_real_dirs(monkeypatch):
    """挡住构造函数的 `ensure_dirs()`：不挡就会在真实 data/literature_feed/ 下建目录。"""
    calls: list[int] = []
    monkeypatch.setattr(lmk, "ensure_dirs", lambda: calls.append(1))
    return calls


def _aged(tmp_path, *, content="\n", mtime=BASE_MTIME, ttl=TTL, name="feed.lock"):
    """造一个 mtime 精确等于 `mtime` 的锁文件，并回读校验文件系统没把它量化掉。"""
    path = tmp_path / name
    mgr = LockManager(path, ttl_seconds=ttl)
    path.write_text(content, encoding="utf-8")
    os.utime(path, (mtime, mtime))
    assert path.stat().st_mtime == mtime, "文件系统未原样存下固定基准 mtime ⇒ 压线断言不成立"
    return mgr, path


# ───────────────────── 签名面：接缝存在，且缺省是 None（向后兼容） ─────────────────────
def test_the_two_entries_now_expose_the_seam():
    """接缝确实加上了，且**可选**：默认值必须是 ``None``，否则"缺省＝真实时钟"就没了。

    本条是 `tests/test_lock_manager.py:299` 那枚"签名里没有 now"桩的反面；
    那枚桩按自己的 docstring 设计在实现补接缝时翻红（s922-109 遗留 1 的"设计内翻正"），
    本班不改它、只在此登记其处置口径。
    """
    stale_params = list(inspect.signature(LockManager.is_stale).parameters)
    break_params = list(inspect.signature(LockManager.break_stale).parameters)
    acquire_params = list(inspect.signature(LockManager.acquire).parameters)

    assert stale_params == ["self", "now"], stale_params                 # s921-13 原样未动
    assert break_params == ["self", "now"], break_params
    assert acquire_params == ["self", "now"], acquire_params
    # 缺省必须是 None（= 真实时钟），否则"向后兼容"这句就不成立
    assert inspect.signature(LockManager.break_stale).parameters["now"].default is None
    assert inspect.signature(LockManager.acquire).parameters["now"].default is None


# ─────────────────────────── break_stale 的两条压线边界 ───────────────────────────
def test_break_stale_exactly_at_ttl_does_not_delete(tmp_path):
    """**恰好未超时**（age == ttl）⇒ 不删档：钉 `:157` 的 `>` 而非 `>=`。

    生效反证（"接缝不是装饰"）：同一文件在真实时钟下 mtime 是 1970 年 ⇒ `is_stale()` 恒 True。
    若 `break_stale` 没把 `now` 透传给 `is_stale`（旧写法 `self.is_stale()`），这里就会把文件删掉，
    本用例必红；传了才谈得上"注入的时钟里它恰好没过期"。
    """
    mgr, path = _aged(tmp_path, content=f"{_MARKER}\n")

    assert mgr.is_stale() is True                       # 真实时钟口径：它早过期
    assert mgr.break_stale(now=_LINE) is False          # 注入 age==ttl：`>` 判未超时
    assert path.exists()
    assert _MARKER in path.read_text(encoding="utf-8")   # 没删档 ⇒ 内容原样


def test_break_stale_one_ulp_past_ttl_deletes(tmp_path):
    """**恰好超时**（age = 线上方 1 ulp）⇒ 删档；二次调用返回 False 且不炸。

    ulp 用 `math.nextafter` 现取（`_LINE` 的 ulp 约 2.3e-13），不硬写小数 ⇒
    边界两侧只差一个可表示的最小步长，`>` 的开闭被钉死；若判据改成 `>=`，
    上一条（age==ttl 期望 False）必红，本条不会替你兜住。
    """
    mgr, path = _aged(tmp_path)
    just_over = math.nextafter(_LINE, math.inf)
    assert just_over - BASE_MTIME > TTL                  # 前提自证：确实过了线

    assert mgr.break_stale(now=just_over) is True
    assert not path.exists()
    assert mgr.break_stale(now=just_over) is False       # 文件已没了，二次调用不炸


def test_break_stale_integer_second_past_the_line_also_deletes(tmp_path):
    """整数秒口径的同侧复测（age = ttl + 1）：生产 ttl 是整秒，这档才是实际会遇到的形状。"""
    mgr, path = _aged(tmp_path)

    assert mgr.break_stale(now=_LINE + 1) is True
    assert not path.exists()


def test_break_stale_default_now_still_reads_wall_clock(tmp_path):
    """缺省不改语义（完成标准 ③）：不传 `now` 时与改接缝前逐字一致——真实时钟说了算。

    同一份文件先按真实"现在"（age≈0）⇒ 不删；拨老到 ttl 之外 ⇒ 删。
    这一步不依赖任何注入值，正是 `tests/test_lock_manager.py:133` 那种裕量写法的行为面。
    """
    mgr, path = _aged(tmp_path, mtime=time.time())
    assert mgr.break_stale() is False
    assert path.exists()

    aged = time.time() - TTL - 5
    os.utime(path, (aged, aged))
    assert mgr.break_stale() is True
    assert not path.exists()


def test_break_stale_forwards_the_injected_now_once(tmp_path):
    """接缝接线自证：`break_stale(now=X)` 把**同一个** X 交给 `is_stale`，不二次取时；
    缺省那条仍传 None（真实时钟），两分支的差别就落在这一个参数上。"""
    mgr, path = _aged(tmp_path)
    seen: list = []
    real_is_stale = mgr.is_stale

    def spy(now: float | None = None) -> bool:
        seen.append(now)
        return real_is_stale(now=now)

    mgr.is_stale = spy                                   # 只桩实例方法，生产判据不动

    assert mgr.break_stale(now=_LINE) is False           # 注入时钟里恰好没过期 ⇒ 不删
    assert seen == [_LINE]
    assert path.exists()

    assert mgr.break_stale() is True                     # 真实时钟下这份 1970 的档早过期 ⇒ 删
    assert seen == [_LINE, None]                         # 缺省传 None ⇒ 接缝没被绕开
    assert not path.exists()


# ─────────────────────────── acquire 的两条压线边界 ───────────────────────────
def test_acquire_exactly_at_ttl_does_not_steal_the_file(tmp_path):
    """**恰好未超时**：`_open_and_lock:191-192` 的 stale 强抢不触发 ⇒ 锁文件不被删、内容保留。

    与上一条同构的生效反证：文件 mtime 是 1970 年，真实时钟下早过 ttl ⇒
    没接缝时这条路径必先 `unlink` 再新建（marker 消失）。锁最终仍能拿到（本地无持有者），
    所以钉的不是"抢没抢到"，而是**有没有越界删掉一份按注入时钟还没过期的锁档**。
    """
    mgr, path = _aged(tmp_path, content=f"{_MARKER}\n")

    with mgr.acquire(now=_LINE) as got:
        assert got is mgr
        assert mgr._fh is not None

    assert path.exists()
    assert _MARKER in path.read_text(encoding="utf-8")
    assert f"pid={os.getpid()}" in path.read_text(encoding="utf-8")  # 持有者信息照旧追加


def test_acquire_one_ulp_past_ttl_steals_and_rewrites(tmp_path):
    """**恰好超时**（线上方 1 ulp）⇒ 强抢：旧档被删、marker 随之消失、只剩本进程的持有者信息。"""
    mgr, path = _aged(tmp_path, content=f"{_MARKER}\n")
    just_over = math.nextafter(_LINE, math.inf)

    with mgr.acquire(now=just_over):
        assert mgr._fh is not None

    text = path.read_text(encoding="utf-8")
    assert _MARKER not in text
    assert f"pid={os.getpid()}" in text


def test_acquire_default_now_still_steals_on_wall_clock(tmp_path):
    """缺省面回归自证（对应既有 `tests/test_lock_manager.py:147`，本文件未改它）：
    真实时钟下的老锁照样抢得到，接缝不加也不改这条行为。"""
    mgr, path = _aged(tmp_path, content=f"{_MARKER}\n", mtime=time.time() - 60, ttl=5)

    with mgr.acquire():
        assert mgr._fh is not None

    assert _MARKER not in path.read_text(encoding="utf-8")


def test_acquire_forwards_one_reading_to_both_sides(tmp_path):
    """一次读数口径：`acquire(now=X)` → `_open_and_lock` → `is_stale` 与 `break_stale`
    （后者内部再调同一条 `is_stale`）拿到的**全是同一个** X，全程没有第二次取时
    （旧写法两侧各调一次 `time.time()`，中间夹着 stat 与字符串格式化，会差出调度抖动）。"""
    mgr, _path = _aged(tmp_path)
    seen: list = []
    real_is_stale = mgr.is_stale
    real_break_stale = mgr.break_stale

    def spy_stale(now: float | None = None) -> bool:
        seen.append(("is_stale", now))
        return real_is_stale(now=now)

    def spy_break(now: float | None = None) -> bool:
        seen.append(("break_stale", now))
        return real_break_stale(now=now)

    mgr.is_stale = spy_stale
    mgr.break_stale = spy_break

    just_over = math.nextafter(_LINE, math.inf)
    with mgr.acquire(now=just_over):
        assert mgr._fh is not None

    assert [k for k, _ in seen] == ["is_stale", "break_stale", "is_stale"], seen
    # break_stale 内部会再调一次 is_stale（既有委托结构，本班未动）；关键是三次全用同一个注入值，
    # 没有任何一次偷偷回落到 time.time()。
    assert {v for _, v in seen} == {just_over}, seen


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
