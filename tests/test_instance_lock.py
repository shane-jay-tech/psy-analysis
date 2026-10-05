# -*- coding: utf-8 -*-
"""instance_lock 对抗与行为用例（任务 20260905-110400-1003，≥6 用例）。"""
import os
import subprocess
import time
from pathlib import Path

import pytest

from src.utils.instance_lock import ProjectLockedError, project_lock

REPO = Path(__file__).resolve().parents[1]

HOLDER_TEMPLATE = """\
import os, sys, time
sys.path.insert(0, r'{repo}')
from src.utils.instance_lock import project_lock
with project_lock(r'{lock_dir}'):
    print('HELD', flush=True)
    print(os.getpid(), flush=True)
    time.sleep(8)
"""

WORKER_TEMPLATE = """\
import sys
sys.path.insert(0, r'{repo}')
from src.utils.instance_lock import project_lock, ProjectLockedError
try:
    import time
    with project_lock(r'{lock_dir}'):
        print('WIN', flush=True)
        time.sleep(0.5)
except ProjectLockedError as e:
    print('LOCKED', e.holder_pid)
"""


@pytest.fixture
def lock_dir(tmp_path):
    return tmp_path / "projects"


def test_acquire_release_removes_lock_file(lock_dir):
    with project_lock(lock_dir):
        assert (lock_dir / ".psy_project.lock").exists()
    assert not (lock_dir / ".psy_project.lock").exists()


def test_lock_file_contains_pid_and_timestamp(lock_dir):
    with project_lock(lock_dir) as lp:
        text = Path(lp).read_text(encoding="utf-8")
        pid_str, since = text.split(" ")
        assert int(pid_str) == os.getpid()
        # s1002-17 加严（s924-63 遗留 1：原 "T" in since 零判别力）——内容戳必须是
        # tz-aware UTC ISO 串：含日期 T 分隔＋末尾 +00:00 时区偏移。
        assert "T" in since
        assert since.endswith("+00:00"), f"内容戳应为 tz-aware UTC（…+00:00），实得 {since!r}"
        assert "T" in since and "+" in since.split("T")[1]


def test_same_process_reentrant(lock_dir):
    """同进程嵌套获取放行（depth 语义），最外层才删文件。"""
    with project_lock(lock_dir):
        with project_lock(lock_dir):
            assert (lock_dir / ".psy_project.lock").exists()
        assert (lock_dir / ".psy_project.lock").exists()
    assert not (lock_dir / ".psy_project.lock").exists()


def test_stale_lock_taken_over(lock_dir):
    """伪造陈旧锁（mtime 调老 + 不存在的 pid）：夺取成功且旧文件被挪走删除。"""
    lp = lock_dir / ".psy_project.lock"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lp.write_text("999999 2020-01-01T00:00:00", encoding="utf-8")
    old = time.time() - 3600
    os.utime(lp, (old, old))

    with project_lock(lock_dir):
        assert lp.read_text(encoding="utf-8").startswith(str(os.getpid()))
    assert not lp.exists()
    assert not list(lock_dir.glob("*.stale-*"))


def test_fresh_lock_with_dead_pid_not_taken_over(lock_dir):
    """锁龄未超限且 pid 已死：按设计**不可**夺取，抛 ProjectLockedError。"""
    lp = lock_dir / ".psy_project.lock"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lp.write_text("999999 2020-01-01T00:00:00", encoding="utf-8")  # 新鲜 mtime + 死 pid
    with pytest.raises(ProjectLockedError):
        with project_lock(lock_dir):
            pass


def test_fresh_lock_with_alive_pid_rejected(lock_dir):
    """pid 存活（本进程）但锁龄已老：不夺取（存活优先于陈旧判定）。"""
    lp = lock_dir / ".psy_project.lock"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lp.write_text(f"{os.getpid()} 2020-01-01T00:00:00", encoding="utf-8")
    old = time.time() - 3600
    os.utime(lp, (old, old))
    with pytest.raises(ProjectLockedError) as ei:
        with project_lock(lock_dir):
            pass
    assert ei.value.holder_pid == os.getpid()


def test_foreign_holder_blocks_with_pid(lock_dir, tmp_path):
    """另一实例持锁时，本实例获取失败且异常携带持有者 pid。"""
    holder = tmp_path / "holder.py"
    holder.write_text(
        HOLDER_TEMPLATE.format(repo=str(REPO), lock_dir=str(lock_dir)),
        encoding="utf-8",
    )
    venv_py = str(REPO / ".venv" / "Scripts" / "python.exe")
    proc = subprocess.Popen([venv_py, str(holder)], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    first_line = proc.stdout.readline().strip()
    assert first_line == "HELD", f"holder crashed: {first_line!r}"
    holder_pid = int(proc.stdout.readline().strip())
    try:
        with pytest.raises(ProjectLockedError) as ei:
            with project_lock(lock_dir, stale_seconds=1e9):  # 禁用陈旧夺取
                pass
        assert ei.value.holder_pid == holder_pid
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_concurrent_subprocesses_exactly_one_wins(lock_dir, tmp_path):
    """并发冒烟：两个子进程抢同一把锁，恰好一个成功一个收 ProjectLockedError。"""
    worker = tmp_path / "worker.py"
    worker.write_text(
        WORKER_TEMPLATE.format(repo=str(REPO), lock_dir=str(lock_dir)),
        encoding="utf-8",
    )
    venv_py = str(REPO / ".venv" / "Scripts" / "python.exe")
    procs = [
        subprocess.Popen([venv_py, str(worker)], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
        for _ in range(2)
    ]
    outs = [p.communicate(timeout=60)[0].strip() for p in procs]
    wins = sum(1 for o in outs if o == "WIN")
    locked = sum(1 for o in outs if o.startswith("LOCKED "))
    assert wins == 1 and locked == 1, (outs,)
