"""持久化路径配置契约。"""

from pathlib import Path

from src.utils import app_paths


def test_default_paths_preserve_legacy_layout():
    assert app_paths.PROJECTS_DIR == app_paths.APP_HOME / "projects"
    assert app_paths.PREFS_FILE == app_paths.APP_HOME / "user_prefs.json"
    assert app_paths.LEGACY_AUTOSAVE_FILE == app_paths.APP_HOME / "autosave.json"
    assert app_paths.ARCHIVE_ROOT.name == "archive"


def test_explicit_path_configuration_is_resolved(tmp_path, monkeypatch):
    monkeypatch.setenv("PSY_ANALYSIS_HOME", str(tmp_path / "portable"))
    assert app_paths._configured_path("PSY_ANALYSIS_HOME", Path("unused")) == tmp_path / "portable"
