# -*- coding: utf-8 -*-
"""s922-109：`LockManager.is_stale` 的 `>` 边界真值测试（时钟接缝口径，零 sleep、零裕量）。

背景：`psy-timesensitive-20260919` 遗留 2 记的「`>` vs `>=` 无真值测」，在 s921-13 给
`is_stale` 加 `now` 接缝（`lock_manager.py:128-137` docstring 自述）之后才谈得上可测。
`tests/test_lock_manager.py:83` 已有一条压线例（ttl=100 单点），本班把它扩成**真值表**，
并补上「边界的开闭有可观察副作用」这一层（告警记录数、`age_min` 截断）。

⚠️ 本班只钉现状、不改判据：`lock_manager.py:148` 的 `stale = age > self.ttl_seconds`
**改成 `>=` 则本文件全部压线用例必红**（各用例 docstring 逐条重申这一判定方向）。

锚点复核（2026-09-22 本班按磁盘实况，HEAD `9551e1d`，任务书两处锚点**零漂移**）：
- `src/literature_feed/scheduler/lock_manager.py:128` `def is_stale(self, now: Optional[float] = None) -> bool:`
- `:148` `stale = age > self.ttl_seconds`
- 另取到任务书未点名的三段现场：`:139-140` 文件不存在直接 return False、`:141-144` stat 抛 OSError 也 return False、
  `:149-154` 陈旧才告警且 `age_min = int(age / 60)`

隔离口径（本波要点 3「写 data/ 类动作一律禁」）：`LockManager.__init__:61` 会调 `ensure_dirs()`，
而 `src/literature_feed/paths.py:36-39` 的 `ensure_dirs()` 实打实 `mkdir` 三个生产目录
（`DATA_ROOT` / `JSONL_RAW_DIR` / `LOCK_DIR`，含 `data/literature_feed/locks/`）⇒
本班用**模块内 autouse 桩**把它换成记录调用次数的 no-op，锁文件一律落 `tmp_path`。
零 sqlite、零网络、零 LLM、零子进程、零 sleep。
"""
from __future__ import annotations

import math
import os

import pytest

import src.literature_feed.scheduler.lock_manager as lmk
from src.literature_feed.scheduler.lock_manager import LockManager

# 固定基准取自 1970 附近：这个量级上 double 的 ulp 约 1.1e-13，
# 1000.0 + 100 是**精确可表示**的，age = now - mtime 因此能正好等于 ttl（大 epoch 值会栽在量化上）。
BASE_MTIME = 1_000.0


@pytest.fixture(autouse=True)
def no_real_dirs(monkeypatch):
    """挡住构造函数的 `ensure_dirs()`：不挡就会在真实 data/literature_feed/ 下建目录。"""
    calls: list[int] = []
    monkeypatch.setattr(lmk, "ensure_dirs", lambda: calls.append(1))
    return calls


def _locked(tmp_path, ttl, *, mtime=BASE_MTIME, name="feed.lock"):
    """造一个 mtime 精确等于 `mtime` 的锁文件并回读校验（文件系统不许偷偷量化掉它）。"""
    path = tmp_path / name
    mgr = LockManager(path, ttl_seconds=ttl)
    path.write_text("\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))
    assert path.stat().st_mtime == mtime, "文件系统未原样存下固定基准 mtime，压线断言不成立"
    return mgr, path


# ───────────────────────────── 边界本体 ─────────────────────────────
def test_age_exactly_equal_to_ttl_is_not_stale(tmp_path, no_real_dirs):
    """age == ttl ⇒ **不陈旧**。判据是 `:148` 的严格大于 ⇒ 若实现改为 `>=` 本用例必红。

    现状钉桩（本档判定方向锁死，不留"约等"余地）：`now` 由调用方精确给 `mtime + ttl`，
    两个操作数都是精确可表示的 double，age 落回整数 ttl，无浮点残差、无 sleep、无裕量。
    """
    mgr, _path = _locked(tmp_path, 100)

    assert mgr.is_stale(now=BASE_MTIME + 100) is False
    assert no_real_dirs, "ensure_dirs 桩没被调用 ⇒ 构造函数路径没走通，本用例的隔离前提失效"


def test_one_ulp_either_side_of_the_boundary_flips_the_verdict(tmp_path):
    """紧邻边界两侧各挪 1 ulp：上侧判陈旧、下侧不判 ⇒ 证明上一个是"恰等于"而不是"略小于"。

    若实现改为 `>=` 本用例必红（下侧那半句仍绿，但上侧从"必须 True"变成"两种都行"的
    说法不再成立，且与 `test_age_exactly_equal_to_ttl_is_not_stale` 合起来必然报红）。
    ulp 用 `math.nextafter` 现取，不硬写小数。
    """
    mgr, _path = _locked(tmp_path, 100)
    line = BASE_MTIME + 100
    just_over = math.nextafter(line, math.inf)
    just_under = math.nextafter(line, -math.inf)
    assert just_over - BASE_MTIME > 100 and just_under - BASE_MTIME < 100  # 前提自证

    assert mgr.is_stale(now=just_over) is True
    assert mgr.is_stale(now=just_under) is False


@pytest.mark.parametrize("ttl", [1, 60, 3_600, 21_600])
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_boundary_truth_table_over_ttl_grid(tmp_path, ttl, delta):
    """真值表：ttl ∈ {1s, 1min, 1h, 生产默认 6h} × age = ttl + {-1, 0, +1} ⇒ 只有 `> ttl` 那侧为 True。

    若实现改为 `>=` 本用例必红（delta=0 那一档 4 个参数组全部翻成 True）。
    delta 一律取整数秒、mtime 固定 ⇒ age 精确，不涉及真实时钟。
    生产默认 21600 单独进表：`:54` 的 `ttl_seconds: int = 21600` 是唯一实际跑的档位。
    """
    mgr, _path = _locked(tmp_path, ttl)

    expected = delta > 0
    assert mgr.is_stale(now=BASE_MTIME + ttl + delta) is expected, (ttl, delta)


def test_negative_age_is_not_stale_on_either_side_of_zero(tmp_path):
    """NTP 回拨面：age 恰为 0（不陈旧）、age 为负（也不陈旧）——`>` 不报警，且没有 `abs()`。

    现状钉桩。若实现改成 `abs(age) > ttl`（把回拨也当陈旧）本用例必红。
    """
    mgr, _path = _locked(tmp_path, 100)

    assert mgr.is_stale(now=BASE_MTIME) is False
    assert mgr.is_stale(now=BASE_MTIME - 1) is False
    assert mgr.is_stale(now=BASE_MTIME - 10**9) is False   # 负到 1938 年也不炸


# ─────────────────── 边界的可观察副作用（判据不只落在返回值上） ───────────────────
def test_no_stale_alert_record_is_emitted_exactly_at_the_boundary(tmp_path, caplog):
    """age == ttl 时 `:149` 的 if 不进 ⇒ **零条** stale_lock 告警；age = ttl+1 才有一条。

    若实现改为 `>=` 本用例必红（边界那侧会多出一条告警）。
    这一条与"同一 kind 每实例只告警一次"（`tests/test_lock_alert_log.py` 的 d914-19 面）**不是同一件事**：
    这里钉的是"边界是否触发告警"，那里钉的是"触发几次"。
    """
    mgr, _path = _locked(tmp_path, 100)

    with caplog.at_level("WARNING"):
        assert mgr.is_stale(now=BASE_MTIME + 100) is False
    assert [r for r in caplog.records if "stale_lock" in r.getMessage()] == []

    with caplog.at_level("WARNING"):
        assert mgr.is_stale(now=BASE_MTIME + 101) is True
    fired = [r.getMessage() for r in caplog.records if "stale_lock" in r.getMessage()]
    assert len(fired) == 1
    assert "stale for 1 min" in fired[0] and "ttl=100s" in fired[0]


def test_just_past_the_line_reports_zero_minutes(tmp_path, caplog):
    """刚过线时告警文案可见性钉（s930-09 翻面）。

    原现状钉：`age_min = int(age / 60)` 向下截断 ⇒ 刚过线告警文案是 "stale for 0 min"
    （误导——实际只过了 1 秒却报 0 分钟）。s930-09 落地文案修正：<1 分钟改显式秒数
    `stale for {int(age)}s (<1 min)`——钉由「钉 0 min 现状」翻为「钉秒级文案」，
    可见性意图保持（刚过线即有告警且时长如实）。
    """
    mgr, _path = _locked(tmp_path, 1)

    with caplog.at_level("WARNING"):
        assert mgr.is_stale(now=BASE_MTIME + 1.5) is True
    fired = [r.getMessage() for r in caplog.records if "stale_lock" in r.getMessage()]
    assert len(fired) == 1 and "stale for 1s (<1 min)" in fired[0], fired


# ───────────────────────── 短路面（不取时钟就不该算术） ─────────────────────────
def test_absent_lock_file_short_circuits_before_any_age_arithmetic(tmp_path):
    """`:139-140` 的 exists() 短路在取 `now` 与做减法**之前** ⇒ 传个不可减的对象也不炸。

    现状钉桩。判据：`now=object()` 若能安全返回 False，说明默认分支的 `time.time()`
    与 `age = now - mtime` 都没被执行。若实现改成"先算 age 再判存在性"，本用例会以 TypeError 红。
    """
    mgr = LockManager(tmp_path / "never-created.lock", ttl_seconds=5)

    assert mgr.is_stale(now=object()) is False


def test_default_branch_still_reads_the_wall_clock(tmp_path):
    """缺省 `now=None` 仍走真实时钟（`:145-146`）：同一条锁在注入时钟里可以结论相反。

    现状钉桩（接缝是**可选**的，不是强制的 ⇒ 生产调用方 `break_stale()` 拿不到注入能力）。
    与 `tests/test_lock_manager.py:104` 的缺省面用例同向但不重复：那条钉"缺省值会被让位"，
    这条只钉"压线时缺省分支给不出确定答案"——因为真实 age 恒在漂移。
    """
    mgr, _path = _locked(tmp_path, 100)

    assert mgr.is_stale(now=BASE_MTIME + 100) is False      # 接缝里它不陈旧
    assert mgr.is_stale() is True                            # 真实时钟下 mtime 是 1970 年 ⇒ 必然陈旧


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
