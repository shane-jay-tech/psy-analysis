"""方案B 后台保存测试（2026-09-11 新增；不改动 test_autosave.py 既有断言）。

覆盖：模式分发（dict=同步 / 非 dict=后台）、后台落盘 + 标签结转、
pending 合并取最新、私有副本不污染 sys.modules。
"""

from __future__ import annotations

import sys
import time

import pytest

from src.utils import autosave as autosave_mod
from src.utils import autosave_bg
from src.utils import project_manager as pm


@pytest.fixture
def temp_projects(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(pm, "INDEX_FILE", tmp_path / "index.json")
    yield tmp_path


def test_fake_session_state_is_not_dict():
    """模式分发的判据：FakeSessionState 必须不是 dict，否则会被误派到同步路径。"""
    assert not isinstance(autosave_mod.FakeSessionState({"a": 1}), dict)


def test_dict_session_state_stays_synchronous(temp_projects):
    """dict 会话态（测试/脚本环境）保持同步语义：返回 True 时已落盘。"""
    proj = pm.create_project("sync")
    state = {}
    pm.set_active_project(state, proj.id)
    ok = autosave_mod.trigger_autosave(state, lambda: {"marker": "sync"}, force=True)
    assert ok
    assert pm.load_workspace(proj.id)["marker"] == "sync"


def test_background_submit_then_flush_saves_and_drains(temp_projects):
    """非 dict 会话态走后台：submit 立即返回，flush 后真配方落盘、结果结转标签键。"""
    proj = pm.create_project("bg1")
    fss = autosave_mod.FakeSessionState({"meta": {"who": "bg"}, "file_name": "x.csv"})
    pm.set_active_project(fss, proj.id)
    t0 = time.perf_counter()
    ok = autosave_mod.trigger_autosave(fss, lambda: {"never_used": True}, force=True)
    submit_ms = (time.perf_counter() - t0) * 1000
    assert ok
    assert submit_ms < 1000  # 引用捕获+提交应远低于序列化耗时（宽松护栏）
    done, worker_ms = autosave_mod.flush_background(timeout=15)
    assert done
    ws = pm.load_workspace(proj.id)
    assert ws is not None
    assert ws["meta"] == {"who": "bg"}  # 真配方从引用捕获重建（builder 未被调用）
    assert "never_used" not in ws
    assert fss.get(autosave_mod.SESSION_LAST_SAVE_KEY) is not None
    # 下一次 trigger 会先 drain 上一次结果 → 标签键出现
    assert autosave_mod.trigger_autosave(fss, lambda: {}, force=True)
    assert autosave_mod.flush_background(timeout=15)[0]
    assert fss.get(autosave_mod.SESSION_LAST_SAVED_LABEL_KEY)


def test_pending_coalesce_keeps_latest_capture(temp_projects):
    """连续两次提交应合并：最终落盘的是最新捕获。"""
    proj = pm.create_project("bg2")
    fss = autosave_mod.FakeSessionState({"meta": "capture-A"})
    pm.set_active_project(fss, proj.id)
    assert autosave_mod.trigger_autosave(fss, lambda: {}, force=True)
    fss["meta"] = "capture-B"
    assert autosave_mod.trigger_autosave(fss, lambda: {}, force=True)
    done, _ = autosave_mod.flush_background(timeout=15)
    assert done
    ws = pm.load_workspace(proj.id)
    assert ws["meta"] == "capture-B"


def test_private_module_copy_does_not_pollute_sys_modules():
    """私有副本不注册 sys.modules，主线程拿到的 workspace 模块是原对象。"""
    import src.utils.workspace as orig

    autosave_bg._get_private_builder()  # 触发加载
    assert sys.modules["src.utils.workspace"] is orig
    # 副本的 st 是壳，原模块的 st 是真 streamlit
    import streamlit as real_st

    assert orig.st is real_st


def test_rollback_switch_returns_to_sync(temp_projects, monkeypatch):
    """回滚开关：BACKGROUND_AUTOSAVE_ENABLED=False 时非 dict 会话态也走同步。"""
    monkeypatch.setattr(autosave_mod, "BACKGROUND_AUTOSAVE_ENABLED", False)
    proj = pm.create_project("rb")
    fss = autosave_mod.FakeSessionState({"meta": "rollback"})
    pm.set_active_project(fss, proj.id)
    ok = autosave_mod.trigger_autosave(fss, lambda: {"marker": "rb"}, force=True)
    assert ok
    # 同步语义：不等 flush 即已落盘（builder 直接被调用）
    assert pm.load_workspace(proj.id)["marker"] == "rb"
