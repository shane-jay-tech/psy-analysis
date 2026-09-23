# -*- coding: utf-8 -*-
"""instance_lock 的 OSError 分支补面（s923-26，2026-09-23）。

工单口径来自 `zcode-bridge/done/s922-109-lock-stale-boundary.result.md`，
但**开工实测否证了它对代码形状的两处描述**，本文件按磁盘实况钉，差异留在这里：

1. 工单说「`stat()` 抛 OSError 的分支（`:141-144`）无覆盖」。实测 `src/utils/instance_lock.py`
   只有两枚 `except OSError:`（`:126` 陈旧锁挪走失败、`:143` 释放时 unlink 失败），
   **`lock_path.stat()`（`:117`）根本没有 OSError 分支**——它唯一的兜子是 `:118`
   的 `except FileNotFoundError:`。⇒ 「补 stat 的 OSError 分支用例」这个说法在现盘上不成立；
   本文件把两件事分开钉：`:118` 的 FileNotFoundError 真分支（用例 2）、
   以及「非 FNF 的 OSError 会**穿出** project_lock」这一现状缺口（用例 1）。
2. 工单说「断言陈旧锁判定按设计**返回 False 不抛**」。`project_lock` 是 `@contextmanager`，
   **不返回布尔**；陈旧判定是一个 `if`（`:120`），其唯一返回 bool 的下游是 `_pid_alive`，
   而 `_pid_alive` 不碰 `stat()`。⇒ 该断言对象不存在，本文件不硬凑，改为钉现盘真实出口：
   三次尝试耗尽后 `:130-131` 抛 `ProjectLockedError(pid=-1)`。

工单的「只加测试不改锁实现」照办：本文件**零改动** `src/`，用例 1 因此是**现状缺口钉桩**
（`_registers_gap` 后缀），真去补 `except OSError` 会让它翻红——那是预期信号，不是回归。

防假绿：每枚注入都带**命中计数自证**（`hits`），注入没被真正调用就当场判红，
不会出现「0 次命中而测试全绿」。注入一律按**锁文件的完整路径串**前缀限定，
其余路径透传原实现 ⇒ `lock_dir.mkdir(exist_ok=True)`（会对目录调 `Path.stat`）不受影响。
零 app、零 AppTest、零 Streamlit、零网络、零 literature_feed：全部跑在 `tmp_path` 上。
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from src.utils import instance_lock
from src.utils.instance_lock import LOCK_FILENAME, ProjectLockedError, project_lock

_ORIG_PATH_STAT = Path.stat
_ORIG_PATH_UNLINK = Path.unlink
_ORIG_OS_REPLACE = os.replace

DEAD_PID = 999999  # 与 tests/test_instance_lock.py 同一口径：OpenProcess 打不开 ⇒ 判死


def _seed_lock(lock_dir: Path, *, pid: int = DEAD_PID, age_seconds: float = 0.0) -> Path:
    """造一枚锁文件（目录先建好，避免与注入器抢 mkdir）。"""
    lock_dir.mkdir(parents=True, exist_ok=True)
    lp = lock_dir / LOCK_FILENAME
    lp.write_text(f"{pid} 2020-01-01T00:00:00", encoding="utf-8")
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(lp, (old, old))
    return lp


def _guarded_raiser(monkeypatch, target_name: str, holder: type, prefix: str, exc_factory):
    """把 holder.<target_name> 换成「路径含 prefix 则抛、否则透传」的版本，返回命中列表。"""
    original = getattr(holder, target_name)
    hits: list[str] = []

    def fake(self_or_path, *args, **kwargs):
        if prefix in str(self_or_path):
            hits.append(str(self_or_path))
            raise exc_factory(prefix)
        return original(self_or_path, *args, **kwargs)

    monkeypatch.setattr(holder, target_name, fake)
    return hits


# --------------------------------------------------------------------------- 1. stat 的 OSError：现盘无兜子


def test_stat_oserror_other_than_filenotfound_escapes_project_lock(monkeypatch, tmp_path):
    """**缺口钉桩**：`stat()` 抛非 FileNotFoundError 的 OSError 时，异常**穿出** `project_lock`。

    现盘 `:115-119` 只兜 FileNotFoundError ⇒ 权限类 stat 失败不会退化成「稍后重试」，
    也不会得到面向用户的 `ProjectLockedError`，而是裸 OSError 崩在锁获取路径上。
    补上 `except OSError` 之后本用例应当红——请连带改写本文件的 docstring 第 1 条。
    """
    lp = _seed_lock(tmp_path / "a")
    hits = _guarded_raiser(monkeypatch, "stat", Path, str(lp), lambda p: PermissionError(13, "denied", p))

    with pytest.raises(PermissionError):
        with project_lock(lp.parent, stale_seconds=1.0):
            pass

    assert hits, "注入未命中：stat() 没被调用，本用例是空转假绿"
    # 存在性用 os.path.exists：Path.exists() 在 3.12 内部调 self.stat()，
    # 而 PermissionError 不在 pathlib 的 _ignore_error 白名单里，会二次抛出、把断言变成噪声。
    assert os.path.exists(str(lp)), "崩在锁路径上却把锁文件删了，属另一回事"


# --------------------------------------------------------------------------- 2. stat 的 FileNotFoundError：真分支


def test_stat_filenotfound_retries_then_raises_locked_with_sentinel_pid(monkeypatch, tmp_path):
    """工单描述的真实形态：锁在「`os.open` 撞 FileExistsError」与「`stat()`」之间消失。

    `:118-119` 命中 ⇒ `continue` 重试；本轮共 3 次尝试都拿不到 fd ⇒ `:130-131`
    抛 `ProjectLockedError`，持有者以哨兵 `-1`/空 since 表示「读不到」。
    """
    lp = _seed_lock(tmp_path / "b")
    hits = _guarded_raiser(monkeypatch, "stat", Path, str(lp), lambda p: FileNotFoundError(2, "gone", p))

    with pytest.raises(ProjectLockedError) as ei:
        with project_lock(lp.parent, stale_seconds=1.0):
            pass

    assert ei.value.holder_pid == -1
    assert ei.value.holder_since == ""
    assert len(hits) == 3, f"重试次数与 range(3) 不符：{hits}"


def test_stat_retry_loop_terminates_after_three_attempts(monkeypatch, tmp_path):
    """判别力自证：钉住「FileNotFoundError 走的是**重试**而不是陈旧夺取」。

    与上一条同注入、唯一区别是 `stale_seconds` 取极大值禁用夺取；关键断言是
    `os.replace` 保持真身且**一次都没被调用**——若哪天判定顺序被改成
    「stat 失败即视为陈旧」，夺取分支会去挪文件，本用例当场翻红（命中数仍为 3
    则说明重试上限没被动过）。
    """
    lp = _seed_lock(tmp_path / "c")
    replace_hits: list[str] = []
    real_replace = os.replace

    def spy_replace(src, dst, *args, **kwargs):
        if str(lp) in str(src):
            replace_hits.append(str(src))
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", spy_replace)
    hits = _guarded_raiser(monkeypatch, "stat", Path, str(lp), lambda p: FileNotFoundError(2, "gone", p))

    with pytest.raises(ProjectLockedError):
        with project_lock(lp.parent, stale_seconds=1e9):
            pass

    assert len(hits) == 3
    assert replace_hits == [], "FileNotFoundError 竟走了陈旧夺取分支 ⇒ 判定顺序已变"


# --------------------------------------------------------------------------- 3. 陈旧夺取时 os.replace 失败：:126


def test_stale_takeover_replace_oserror_is_swallowed_and_lock_survives(monkeypatch, tmp_path):
    """`:126 except OSError: pass`：挪走陈旧锁失败时**不崩**，退化成重试，最终抛 `ProjectLockedError`。

    现盘后果要说清：锁文件留在原地、用户收到的是 `pid=-1` 的「被另一实例占用」，
    而不是「陈旧锁清不掉」的专门提示——本用例只钉「不崩 + 不自愈」这两点现状。
    """
    lp = _seed_lock(tmp_path / "d", age_seconds=3600.0)
    hits = _guarded_raiser(monkeypatch, "replace", os, str(lp), lambda p: OSError(5, "replace blocked"))

    with pytest.raises(ProjectLockedError) as ei:
        with project_lock(lp.parent, stale_seconds=1.0):
            pass

    assert ei.value.holder_pid == -1
    assert len(hits) == 3, f"每次重试都该撞一次 os.replace：{hits}"
    assert lp.exists(), "os.replace 已被注入拦下，锁文件不该消失"
    assert not list(lp.parent.glob("*.stale-*")), "夺取失败却留下挪走痕迹"
    assert lp.read_text(encoding="utf-8").startswith(str(DEAD_PID)), "原锁内容被改动"


# --------------------------------------------------------------------------- 4. 释放时 unlink 失败：:143


def test_release_unlink_oserror_is_swallowed_and_depth_state_cleaned(monkeypatch, tmp_path):
    """`:143 except OSError: pass`：退出时删不掉锁文件也**不得**把异常抛给用户。

    同时钉住状态面：`_depth_by_path` 的清理在 `:140`（`try` 之前），所以注入 unlink
    也不会留下重入计数残值——否则下一次进同一目录会走「depth>0 放行」的**假可重入**，
    那才是真事故面，故一并断言。
    """
    lock_dir = tmp_path / "e"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lp = lock_dir / LOCK_FILENAME
    assert not lp.exists(), "前提：锁文件由被测的 project_lock 自己创建"
    key = str(lp)
    assert key not in instance_lock._depth_by_path

    hits = _guarded_raiser(monkeypatch, "unlink", Path, key, lambda p: OSError(5, "unlink blocked"))

    with project_lock(lp.parent) as got:
        assert str(got) == key
        assert Path(got).read_text(encoding="utf-8").startswith(str(os.getpid()))

    assert hits, "注入未命中：释放路径没调 Path.unlink，本用例是空转假绿"
    assert key not in instance_lock._depth_by_path, "unlink 失败却清了 depth ⇒ 或 depth 清了却没走 :140"
    assert lp.exists(), "unlink 被拦下后锁文件仍在原地，是本用例的前提"


# --------------------------------------------------------------------------- 5. 还原自证


def test_monkeypatch_left_no_trace_on_path_and_os():
    """完成标准「monkeypatch 在 teardown 完整还原」的可复算形态。

    跑在本文件最后（pytest 按文件内定义序执行）⇒ 前面 4 枚注入若泄漏到 teardown 之外，
    这里必然拿到不同的对象；同文件其余用例与 `tests/test_instance_lock.py` 合跑仍全绿
    是同一件事的第二路证据。
    """
    assert Path.stat is _ORIG_PATH_STAT
    assert Path.unlink is _ORIG_PATH_UNLINK
    assert os.replace is _ORIG_OS_REPLACE
    assert Path.stat.__qualname__ == "Path.stat"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([str(Path(__file__).relative_to(Path(__file__).resolve().parents[1])), "-q"]))
