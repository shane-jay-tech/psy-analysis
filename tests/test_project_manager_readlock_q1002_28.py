# -*- coding: utf-8 -*-
"""s1002-28：project_manager 读路径锁行为级测试（s923-44 遗留 1 施工）。

施工形态：_read_locked 装饰器委托 _locked（复用在册唯一 project_lock 调用点，
不撞 test_only_production_consumer_is_project_manager 的「恰 1 处」门禁）。

形态注记（实测定谳）：instance_lock 的可重入按**进程**记账（_depth_by_path 模块级
dict、无线程守卫）——同进程第二线程 depth>0 直接走重入支，**不构成 OS 锁竞争**。
⇒ 占用态断言必须用 **subprocess 跨实例**形态；同进程线程只测嵌套与正常态。
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from src.utils import project_manager as pm

_REPO = Path(__file__).resolve().parents[1]

HOLD_CHILD_TEMPLATE = """
import sys, time
sys.path.insert(0, r"{repo}")
from pathlib import Path
from src.utils.instance_lock import project_lock
with project_lock(Path(r"{pm_dir}")):
    print("HELD", flush=True)
    time.sleep({hold})
"""


@pytest.fixture
def seeded_projects(monkeypatch, tmp_path):
    """PROJECTS_DIR/INDEX_FILE 重定向 tmp 并种两个项目。"""
    monkeypatch.setattr(pm, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(pm, "INDEX_FILE", tmp_path / "projects" / "index.json")
    pm.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    a = pm.create_project("甲项目")
    b = pm.create_project("乙项目")
    return a, b


def test_read_paths_return_real_data_when_lock_free(seeded_projects):
    a, _ = seeded_projects
    assert sorted(p.name for p in pm.list_projects()) == ["乙项目", "甲项目"]
    assert pm.get_project(a.id).name == "甲项目"


def test_nested_read_via_load_workspace_does_not_deadlock(seeded_projects):
    """load_workspace→get_project 双读嵌套：可重入 ⇒ 不死锁且返回工作区。"""
    a, _ = seeded_projects
    ws = pm.load_workspace(a.id)
    assert isinstance(ws, dict)


def _hold_lock_and_run(fn, tmp_path, hold_s: float):
    """子进程持锁 hold_s；父进程等 HELD 后执行 fn（此刻父进程的读/写必然撞跨实例锁）。"""
    pm_dir = tmp_path / "projects"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    script = (HOLD_CHILD_TEMPLATE
              .replace("{repo}", _REPO.as_posix())
              .replace("{pm_dir}", pm_dir.as_posix())
              .replace("{hold}", str(hold_s)))
    child = subprocess.Popen(
        [sys.executable, "-c", script],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    try:
        line = child.stdout.readline().strip()
        assert line == "HELD", f"子进程未按预期持锁：{line!r}"
        return fn()
    finally:
        child.wait(30)


def test_held_cross_instance_lock_degrades_reads(monkeypatch, seeded_projects, tmp_path):
    """跨实例占用 ⇒ 读路径自旋降级 []/None 不抛；锁释放后恢复。"""
    a, _ = seeded_projects

    def probe():
        assert pm.list_projects() == []      # 降级空表
        assert pm.get_project(a.id) is None  # 降级 None

    _hold_lock_and_run(probe, tmp_path, hold_s=6.0)
    time.sleep(0.2)                          # 等子进程锁释放
    assert len(pm.list_projects()) == 2      # 释放后恢复真数据


def test_write_still_raises_when_cross_instance_lock_held(monkeypatch, seeded_projects, tmp_path):
    """写路径语义不变：跨实例持锁时 create_project 仍抛 ProjectLockedError。"""
    from src.utils.instance_lock import ProjectLockedError

    def probe():
        with pytest.raises(ProjectLockedError):
            pm.create_project("会被拒")

    _hold_lock_and_run(probe, tmp_path, hold_s=6.0)
