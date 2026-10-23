# -*- coding: utf-8 -*-
"""锁竞争/回退两场景细化测试（s1023-05，锁粒度/回退设计稿回退节落地验证）。

材料：docs/insights/psy-lock-granularity-design-20260918.md 回退节 1-3——
- 场景①锁竞争：活持有者在位 → 非阻塞立即抛 ProjectLockedError（含 pid）；
  统一提示含 holder/since 明确段（2a）；
- 场景②回退：死持有者/损坏锁过 stale → 自动接管＋告警日志＋接管计数累加（2b/2c）；
- 禁止语义：无自动等待重试循环（竞争路径 <5s 判定）。
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from src.utils import instance_lock as il
from src.utils.instance_lock import ProjectLockedError, project_lock, takeover_count


def _dead_pid() -> int:
    """产一个确定已退出的 pid（起真子进程跑完再取其 pid，不猜活 pid 的平台差）。"""
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def _seed_lock(lock_dir: Path, pid: int, content: str | None = None) -> Path:
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / il.LOCK_FILENAME
    text = content if content is not None else f"{pid} 2026-01-01T00:00:00+00:00"
    lock_path.write_text(text, encoding="ascii")
    return lock_path


def _age_the_lock(lock_path: Path, seconds: float = 700.0) -> None:
    old = time.time() - seconds
    os.utime(lock_path, (old, old))


def test_scenario1_lock_contention_live_holder_raises_immediately(tmp_path):
    """场景①：活持有者（本进程 pid）→ 非阻塞立即抛错，消息含 pid，零接管。"""
    _seed_lock(tmp_path, os.getpid())
    before = takeover_count(tmp_path / il.LOCK_FILENAME)
    t0 = time.monotonic()
    with pytest.raises(ProjectLockedError) as excinfo:
        with project_lock(tmp_path):
            pass  # pragma: no cover — 不得到达
    elapsed = time.monotonic() - t0
    assert excinfo.value.holder_pid == os.getpid()
    assert "pid=" in str(excinfo.value)
    assert elapsed < 5.0, "竞争必须非阻塞立即失败（设计稿回退节 3：禁止自动等待重试）"
    assert takeover_count(tmp_path / il.LOCK_FILENAME) == before, "活持有者竞争不得触发接管计数"


def test_scenario1b_unified_prompt_includes_holder_and_since():
    """回退节 2a：统一提示 holder/since 两段齐；均空则括号整段省略。"""
    assert "（持有者: pid=123）" in il.locked_user_prompt("项目", "pid=123")
    assert "自 2026-10-24T03:00:00+00:00 起持有" in il.locked_user_prompt(
        "项目", "pid=123", since="2026-10-24T03:00:00+00:00"
    )
    assert "（" not in il.locked_user_prompt("项目")


def test_scenario2_stale_dead_holder_takeover_increments_counter(tmp_path):
    """场景②：死持有者＋过 stale → 自动接管成功、告警计数 +1、锁文件重写为持有态。"""
    dead = _dead_pid()
    lock_path = _seed_lock(tmp_path, dead)
    _age_the_lock(lock_path)
    before = takeover_count(lock_path)
    with project_lock(tmp_path):
        assert lock_path.exists()
        assert str(os.getpid()) in lock_path.read_text(encoding="ascii")
    assert takeover_count(lock_path) == before + 1
    assert not lock_path.exists(), "正常释放后锁文件应清理"


def test_scenario2b_corrupt_lock_takeover_also_counted(tmp_path):
    """回退节 2c：锁文件损坏（读不出 pid）过 stale 走同分支接管＋计数。"""
    lock_path = _seed_lock(tmp_path, 0, content="not-a-pid garbage")
    _age_the_lock(lock_path)
    before = takeover_count()
    with project_lock(tmp_path):
        pass
    assert takeover_count() == before + 1
