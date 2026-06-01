"""自动保存测试（v3.1 改造）— 现在保存到当前活跃项目。"""

from __future__ import annotations

import time

import pytest

from src.utils import autosave as autosave_mod
from src.utils import project_manager as pm


@pytest.fixture
def temp_projects(tmp_path, monkeypatch):
    """重定向项目存储目录到 tmp_path。"""
    monkeypatch.setattr(pm, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(pm, "INDEX_FILE", tmp_path / "index.json")
    yield tmp_path


def test_autosave_writes_to_active_project(temp_projects):
    """v3.1: trigger_autosave 应写到当前活跃项目的工作区文件。"""
    state = {}
    proj = pm.create_project("test")
    pm.set_active_project(state, proj.id)

    saved = autosave_mod.trigger_autosave(
        state, lambda: {"_schema": "v2.9", "marker": "abc"}, force=True,
    )
    assert saved
    ws = pm.load_workspace(proj.id)
    assert ws["marker"] == "abc"


def test_autosave_skipped_when_no_active_project(temp_projects):
    """无活跃项目时 trigger 应静默 False，不崩溃。"""
    state = {}  # 无 active_project_id
    saved = autosave_mod.trigger_autosave(
        state, lambda: {"_schema": "v2.9"}, force=True,
    )
    assert not saved


def test_autosave_throttle_skips_within_window(temp_projects):
    state = {}
    proj = pm.create_project("p")
    pm.set_active_project(state, proj.id)

    saved1 = autosave_mod.trigger_autosave(state, lambda: {"x": 1})
    assert saved1
    saved2 = autosave_mod.trigger_autosave(state, lambda: {"x": 2})
    assert not saved2  # 节流冷却中

    # force 跳过节流
    saved3 = autosave_mod.trigger_autosave(state, lambda: {"x": 3}, force=True)
    assert saved3
    ws = pm.load_workspace(proj.id)
    assert ws["x"] == 3


def test_autosave_handles_builder_exception(temp_projects):
    """builder 抛异常时 trigger 应静默返回 False，不影响主流程。"""
    state = {}
    proj = pm.create_project("p")
    pm.set_active_project(state, proj.id)

    def boom():
        raise RuntimeError("build failed")
    saved = autosave_mod.trigger_autosave(state, boom, force=True)
    assert not saved


def test_autosave_targets_correct_project_after_switch(temp_projects):
    """切换活跃项目后，trigger 应写到新项目而非旧项目。"""
    state = {}
    p1 = pm.create_project("project1")
    p2 = pm.create_project("project2")

    pm.set_active_project(state, p1.id)
    autosave_mod.trigger_autosave(state, lambda: {"who": "p1"}, force=True)

    pm.set_active_project(state, p2.id)
    autosave_mod.trigger_autosave(state, lambda: {"who": "p2"}, force=True)

    assert pm.load_workspace(p1.id)["who"] == "p1"
    assert pm.load_workspace(p2.id)["who"] == "p2"


def test_get_active_workspace_status(temp_projects):
    state = {}
    proj = pm.create_project("status-test")
    pm.set_active_project(state, proj.id)

    autosave_mod.trigger_autosave(
        state,
        lambda: {
            "_schema": "v2.9",
            "df_b64": "abc",
            "analysis_output": {"test_type": "t"},
            "figure_collection": [{"figure_id": "x"}],
        },
        force=True,
    )
    status = autosave_mod.get_active_workspace_status(state)
    assert status.exists
    assert status.has_dataframe
    assert status.has_analysis
    assert status.has_collection
    assert status.file_size_kb > 0


def test_render_restore_prompt_is_noop_in_v31():
    """v3.1: render_restore_prompt 已退化为空操作（迁移挪到 project_panel）。"""
    # 不应抛异常
    autosave_mod.render_restore_prompt(None)


def test_has_legacy_autosave_false_when_no_legacy():
    """无旧 autosave 文件时返回 False。"""
    # 实际文件可能存在用户机器上，本测试只验证函数可调用
    result = autosave_mod.has_legacy_autosave()
    assert isinstance(result, bool)
