# -*- coding: utf-8 -*-
"""autosave 30s 节流计时语义测试（d913b-49）：提交计时口径锁定（注入假时钟）。"""
import sys
import time as _time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # psy-analysis 根（d913b-49 归位：原误放 zcode-bridge/tests，导入 psy src 失败、连带整个桥测试套件 collect error）
sys.path.insert(0, str(ROOT))

from src.utils import autosave, project_manager as pm  # noqa: E402


class FakeClock:
    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, s):
        self.now += s


def _setup(tmp_path, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(autosave.time, "time", clock)
    monkeypatch.setattr(autosave, "BACKGROUND_AUTOSAVE_ENABLED", False)  # 同步路径
    monkeypatch.setattr(pm, "PROJECTS_DIR", tmp_path / "projects")
    # 造一个活跃项目（save_workspace 走 tmp projects 目录）
    monkeypatch.setattr(pm, "list_projects", lambda: [])
    from types import SimpleNamespace
    monkeypatch.setattr(pm, "get_project", lambda pid: SimpleNamespace(id=pid, file_path=tmp_path / "projects" / f"{pid}.json"))
    def _fake_save(pid, ws):
        (tmp_path / "projects").mkdir(parents=True, exist_ok=True)
        (tmp_path / "projects" / f"{pid}.json").write_text("{}", encoding="utf-8")
        return True
    monkeypatch.setattr(pm, "save_workspace", _fake_save)
    state = {pm.ACTIVE_PROJECT_KEY: "proj-1"}
    return clock, state


def test_within_threshold_no_second_save(tmp_path, monkeypatch):
    """阈值内（30s）第二次 trigger 不再落盘（节流命中）。"""
    clock, state = _setup(tmp_path, monkeypatch)
    assert autosave.trigger_autosave(state, lambda: {"k": 1}) is True
    first_last = state[autosave.SESSION_LAST_SAVE_KEY]
    clock.advance(10)  # 阈值内
    assert autosave.trigger_autosave(state, lambda: {"k": 2}) is False
    assert state[autosave.SESSION_LAST_SAVE_KEY] == first_last


def test_across_threshold_triggers_new_save(tmp_path, monkeypatch):
    """跨阈值（>30s）第二次 trigger 重新落盘并刷新提交时刻。"""
    clock, state = _setup(tmp_path, monkeypatch)
    assert autosave.trigger_autosave(state, lambda: {"k": 1}) is True
    clock.advance(31)
    assert autosave.trigger_autosave(state, lambda: {"k": 2}) is True
    assert state[autosave.SESSION_LAST_SAVE_KEY] > 1000.0 + 30
