"""P0-4: 模板中心 UI 面板测试。

验证模板浏览、详情展示、项目创建、session_state 更新。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from src.utils import project_manager as pm

from src.templates.registry import list_templates, get_template, create_project_from_template
from src.ui.template_center_panel import (
    _CREATED_PROJECT_KEY,
    _SELECTED_TEMPLATE_KEY,
    _create_project,
    _get_research_icon,
    _translate_research_type,
    _translate_method,
)


@pytest.fixture(autouse=True)
def isolated_project_store(tmp_path, monkeypatch):
    projects_dir = tmp_path / "projects"
    monkeypatch.setattr(pm, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(pm, "INDEX_FILE", projects_dir / "index.json")


class TestTemplateListDisplay:
    def test_all_templates_available(self):
        templates = list_templates()
        assert len(templates) >= 3

    def test_each_template_has_display_fields(self):
        for tpl in list_templates():
            assert tpl.name
            assert tpl.description
            assert tpl.research_type
            assert tpl.recommended_method


class TestTemplateDetail:
    def test_questionnaire_has_data(self):
        tpl = get_template("questionnaire_correlation")
        assert tpl.has_data()
        df = pd.read_csv(tpl.get_path() / "data.csv")
        assert len(df) >= 30

    def test_template_has_readme(self):
        for tpl in list_templates():
            readme = tpl.get_path() / "README.md"
            assert readme.exists()

    def test_template_has_evidence_seeds(self):
        for tpl in list_templates():
            seeds_path = tpl.get_path() / "evidence_seeds.json"
            assert seeds_path.exists()
            with open(seeds_path, encoding="utf-8") as f:
                seeds = json.load(f)
            assert len(seeds) >= 3


class TestProjectCreation:
    def test_create_populates_session_state(self):
        tpl = get_template("questionnaire_correlation")
        session_state = {}

        with patch("streamlit.error"):
            _create_project(tpl, session_state)

        assert _CREATED_PROJECT_KEY in session_state
        info = session_state[_CREATED_PROJECT_KEY]
        assert info["template_id"] == "questionnaire_correlation"
        assert info["template_name"] == "问卷相关研究"
        assert info["recommended_method"] == "pearson_corr"
        assert "data_path" in info

    def test_create_loads_dataframe(self):
        tpl = get_template("independent_group_comparison")
        session_state = {}

        with patch("streamlit.error"):
            _create_project(tpl, session_state)

        assert "uploaded_df" in session_state
        df = session_state["uploaded_df"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 30
        assert session_state["df"] is df
        assert session_state["file_name"].endswith("样例数据.csv")
        assert session_state["meta"]["source_type"] == "template"
        assert session_state["inspector"]
        assert session_state["analysis_output"] is None

    def test_create_loads_config(self):
        tpl = get_template("pre_post_experiment")
        session_state = {}

        with patch("streamlit.error"):
            _create_project(tpl, session_state)

        info = session_state[_CREATED_PROJECT_KEY]
        assert "config" in info
        assert info["config"]["template_id"] == "pre_post_experiment"

    def test_create_loads_evidence_seeds(self):
        tpl = get_template("questionnaire_correlation")
        session_state = {}

        with patch("streamlit.error"):
            _create_project(tpl, session_state)

        info = session_state[_CREATED_PROJECT_KEY]
        assert "evidence_seeds" in info
        assert len(info["evidence_seeds"]) >= 3

    def test_create_sets_project_id(self):
        tpl = get_template("questionnaire_correlation")
        session_state = {}

        with patch("streamlit.error"):
            _create_project(tpl, session_state)

        project_id = session_state.get("project_id")
        assert project_id
        assert project_id != "questionnaire_correlation"
        assert session_state.get("_active_project_id") == project_id
        assert pm.get_project(project_id).name == tpl.name
        workspace = pm.load_workspace(project_id)
        assert workspace and "df_b64" in workspace
        assert session_state.get("template_source") == "questionnaire_correlation"

    def test_create_saves_previous_project_before_switching(self):
        previous = pm.create_project("旧研究")
        old_df = pd.DataFrame({"old_score": [1, 2, 3]})
        session_state = {
            "_active_project_id": previous.id,
            "df": old_df,
            "file_name": "old.csv",
            "analysis_history": [{"test_type": "descriptive"}],
        }

        tpl = get_template("questionnaire_correlation")
        with patch("streamlit.error"):
            _create_project(tpl, session_state)

        previous_workspace = pm.load_workspace(previous.id)
        assert previous_workspace and "df_b64" in previous_workspace
        assert previous_workspace["file_name"] == "old.csv"
        assert session_state["_active_project_id"] != previous.id

    def test_create_failure_does_not_clear_current_session(self, monkeypatch):
        previous = pm.create_project("旧研究")
        old_df = pd.DataFrame({"old_score": [1, 2, 3]})
        session_state = {"_active_project_id": previous.id, "df": old_df}
        monkeypatch.setattr(pm, "create_project", MagicMock(side_effect=OSError("disk full")))

        tpl = get_template("questionnaire_correlation")
        with patch("streamlit.error") as show_error:
            _create_project(tpl, session_state)

        assert session_state["df"] is old_df
        assert session_state["_active_project_id"] == previous.id
        show_error.assert_called_once()


class TestHelperFunctions:
    def test_research_icons(self):
        assert _get_research_icon("correlational") == "🔗"
        assert _get_research_icon("experimental") == "🧪"
        assert _get_research_icon("pre_post") == "📊"
        assert _get_research_icon("unknown") == "📄"

    def test_translate_research_type(self):
        assert "相关" in _translate_research_type("correlational")
        assert "实验" in _translate_research_type("experimental")
        assert "前后测" in _translate_research_type("pre_post")

    def test_translate_method(self):
        assert "Pearson" in _translate_method("pearson_corr")
        assert "t 检验" in _translate_method("independent_ttest")
        assert "配对" in _translate_method("paired_ttest")

    def test_unknown_values_passthrough(self):
        assert _translate_research_type("xyz") == "xyz"
        assert _translate_method("abc") == "abc"


class TestSessionStateFlow:
    def test_selection_flow(self):
        session_state = {}
        session_state[_SELECTED_TEMPLATE_KEY] = "questionnaire_correlation"
        assert session_state[_SELECTED_TEMPLATE_KEY] == "questionnaire_correlation"

    def test_reset_clears_state(self):
        session_state = {
            _CREATED_PROJECT_KEY: {"template_id": "x"},
            _SELECTED_TEMPLATE_KEY: "x",
        }
        session_state.pop(_CREATED_PROJECT_KEY, None)
        session_state.pop(_SELECTED_TEMPLATE_KEY, None)
        assert _CREATED_PROJECT_KEY not in session_state
        assert _SELECTED_TEMPLATE_KEY not in session_state
