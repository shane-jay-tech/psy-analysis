"""项目管理核心测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.utils import project_manager as pm


@pytest.fixture
def temp_projects(tmp_path, monkeypatch):
    """重定向 PROJECTS_DIR 到 tmp_path，测试隔离。"""
    monkeypatch.setattr(pm, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(pm, "INDEX_FILE", tmp_path / "index.json")
    yield tmp_path


def test_list_empty_when_no_index(temp_projects):
    assert pm.list_projects() == []


def test_create_project_returns_with_id_and_files(temp_projects):
    proj = pm.create_project("毕业论文")
    assert proj.id
    assert proj.name == "毕业论文"
    assert proj.created_at != ""
    assert proj.file_path.exists()  # 工作区文件已创建
    assert (temp_projects / "index.json").exists()


def test_create_empty_name_falls_back_to_default(temp_projects):
    proj = pm.create_project("   ")
    assert proj.name == "未命名项目"


def test_create_multiple_projects_listed_in_recency_order(temp_projects):
    import time
    p1 = pm.create_project("项目1")
    time.sleep(1.1)  # 确保 updated_at 不同
    p2 = pm.create_project("项目2")
    time.sleep(1.1)
    pm.touch_project(p1.id)  # p1 重新成为最近访问

    listed = pm.list_projects()
    assert len(listed) == 2
    assert listed[0].id == p1.id  # 最近访问在前


def test_get_project_returns_none_for_unknown_id(temp_projects):
    assert pm.get_project("nonexistent") is None


def test_rename_project(temp_projects):
    p = pm.create_project("原名")
    assert pm.rename_project(p.id, "新名")
    assert pm.get_project(p.id).name == "新名"


def test_rename_with_empty_name_fails(temp_projects):
    p = pm.create_project("原名")
    assert not pm.rename_project(p.id, "  ")


def test_delete_project_removes_index_and_file(temp_projects):
    p = pm.create_project("待删")
    assert p.file_path.exists()
    assert pm.delete_project(p.id)
    assert pm.get_project(p.id) is None
    assert not p.file_path.exists()


def test_copy_project_duplicates_workspace_data(temp_projects):
    p1 = pm.create_project("原始")
    pm.save_workspace(p1.id, {"_schema": "v2.9", "file_name": "data.csv", "marker": "abc"})

    p2 = pm.copy_project(p1.id)
    assert p2 is not None
    assert p2.id != p1.id
    assert "副本" in p2.name

    ws = pm.load_workspace(p2.id)
    assert ws["marker"] == "abc"


def test_save_and_load_workspace_round_trip(temp_projects):
    p = pm.create_project("RT")
    ws = {
        "_schema": "v2.9",
        "df_b64": "abc",
        "figure_collection": [{"figure_id": "x"}],
    }
    assert pm.save_workspace(p.id, ws)
    loaded = pm.load_workspace(p.id)
    assert loaded["df_b64"] == "abc"
    assert loaded["figure_collection"][0]["figure_id"] == "x"


def test_save_workspace_to_nonexistent_project_fails(temp_projects):
    assert not pm.save_workspace("nonexistent", {"x": 1})


def test_failed_atomic_save_keeps_previous_workspace(temp_projects, monkeypatch):
    p = pm.create_project("atomic")
    assert pm.save_workspace(p.id, {"marker": "before"})

    def fail_replace(_src, _dst):
        raise OSError("disk interrupted")

    monkeypatch.setattr(pm.os, "replace", fail_replace)
    assert not pm.save_workspace(p.id, {"marker": "after"})
    assert pm.load_workspace(p.id)["marker"] == "before"
    assert list(temp_projects.glob(".*.tmp")) == []


def test_corrupt_index_is_quarantined_and_workspaces_are_recovered(temp_projects):
    first = pm.create_project("项目一")
    second = pm.create_project("项目二")
    pm.save_workspace(first.id, {"marker": "first"})
    pm.save_workspace(second.id, {"marker": "second"})
    (temp_projects / "index.json").write_text("{broken", encoding="utf-8")

    recovered = pm.list_projects()

    assert {project.id for project in recovered} == {first.id, second.id}
    assert all("恢复的项目" in project.name for project in recovered)
    assert len(list(temp_projects.glob("index.corrupt.*.bak"))) == 1
    assert pm.load_workspace(first.id)["marker"] == "first"

    third = pm.create_project("项目三")
    assert {project.id for project in pm.list_projects()} == {first.id, second.id, third.id}


def test_update_note(temp_projects):
    p = pm.create_project("p", note="原备注")
    assert pm.update_note(p.id, "新备注")
    assert pm.get_project(p.id).note == "新备注"


def test_session_state_active_project(temp_projects):
    fake_state = {}
    p = pm.create_project("active")
    pm.set_active_project(fake_state, p.id)
    assert pm.get_active_project_id(fake_state) == p.id
    assert pm.get_active_project(fake_state).id == p.id


def test_active_project_returns_none_when_unset(temp_projects):
    assert pm.get_active_project_id({}) is None
    assert pm.get_active_project({}) is None


def test_migrate_legacy_autosave_creates_project(tmp_path, monkeypatch):
    """v3.0 autosave.json → v3.1 项目。"""
    # 设置自定义 home
    home = tmp_path / "fake_home"
    psy_dir = home / ".psy_analysis"
    psy_dir.mkdir(parents=True)

    # 模拟旧 autosave 文件
    legacy = psy_dir / "autosave.json"
    legacy.write_text(
        json.dumps({"_schema": "v2.9", "file_name": "old.csv"}, ensure_ascii=False),
        encoding="utf-8",
    )
    legacy_meta = psy_dir / "autosave_meta.json"
    legacy_meta.write_text("{}", encoding="utf-8")

    # 重定向所有路径到自定义 home
    monkeypatch.setattr(pm.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(pm, "PROJECTS_DIR", psy_dir / "projects")
    monkeypatch.setattr(pm, "INDEX_FILE", psy_dir / "projects" / "index.json")

    proj = pm.migrate_legacy_autosave()
    assert proj is not None
    assert "自动恢复" in proj.name or "未命名" in proj.name
    # 旧文件应已清除
    assert not legacy.exists()
    # 工作区数据应能加载
    ws = pm.load_workspace(proj.id)
    assert ws["file_name"] == "old.csv"


def test_migrate_legacy_returns_none_when_no_legacy(tmp_path, monkeypatch):
    home = tmp_path / "no_legacy"
    home.mkdir()
    monkeypatch.setattr(pm.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(pm, "PROJECTS_DIR", home / "projects")
    monkeypatch.setattr(pm, "INDEX_FILE", home / "projects" / "index.json")
    assert pm.migrate_legacy_autosave() is None
