"""P0-5: 项目模板库测试。

验证 3 个模板可正确加载、数据有效、配置完整。
"""

import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.templates.registry import (
    TEMPLATES_DIR,
    ProjectTemplate,
    list_templates,
    get_template,
    create_project_from_template,
)


class TestTemplateRegistry:
    def test_list_templates_returns_expected_count(self):
        templates = list_templates()
        assert len(templates) >= 6

    def test_template_ids_unique(self):
        templates = list_templates()
        ids = [t.template_id for t in templates]
        assert len(ids) == len(set(ids))

    def test_get_template_by_id(self):
        t = get_template("questionnaire_correlation")
        assert t is not None
        assert t.name == "问卷相关研究"

    def test_get_unknown_template_returns_none(self):
        assert get_template("nonexistent") is None

    def test_template_has_required_fields(self):
        for t in list_templates():
            assert t.template_id
            assert t.name
            assert t.description
            assert t.research_type
            assert t.recommended_method
            assert t.variable_roles
            assert t.paper_sections


class TestTemplateData:
    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_template_has_data_csv(self, template_id):
        t = get_template(template_id)
        assert t.has_data()

    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_template_data_loadable(self, template_id):
        t = get_template(template_id)
        df = pd.read_csv(t.get_path() / "data.csv")
        assert len(df) >= 30
        assert len(df.columns) >= 3

    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_template_has_config(self, template_id):
        t = get_template(template_id)
        config_path = t.get_path() / "template_config.json"
        assert config_path.exists()
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert config["template_id"] == template_id
        assert "design" in config

    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_template_has_paper_skeleton(self, template_id):
        t = get_template(template_id)
        paper_path = t.get_path() / "paper_skeleton.md"
        assert paper_path.exists()
        content = paper_path.read_text(encoding="utf-8")
        assert "## 引言" in content
        assert "## 方法" in content
        assert "## 结果" in content

    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_template_has_evidence_seeds(self, template_id):
        t = get_template(template_id)
        seeds_path = t.get_path() / "evidence_seeds.json"
        assert seeds_path.exists()
        with open(seeds_path, encoding="utf-8") as f:
            seeds = json.load(f)
        assert len(seeds) >= 3
        for s in seeds:
            assert "citation_key" in s
            assert "relevance" in s

    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_template_has_readme(self, template_id):
        t = get_template(template_id)
        readme = t.get_path() / "README.md"
        assert readme.exists()


class TestTemplateProjectCreation:
    def test_create_from_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            project = create_project_from_template("questionnaire_correlation", target, "my_project")
            assert project.exists()
            assert (project / "data.csv").exists()
            assert (project / "template_config.json").exists()
            assert (project / "paper_skeleton.md").exists()

    def test_create_fails_for_unknown_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                create_project_from_template("nonexistent", Path(tmpdir))

    def test_create_fails_for_existing_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            (target / "questionnaire_correlation").mkdir()
            with pytest.raises(FileExistsError):
                create_project_from_template("questionnaire_correlation", target)


class TestTemplateToDict:
    def test_template_serializable(self):
        t = get_template("pre_post_experiment")
        d = t.to_dict()
        assert d["template_id"] == "pre_post_experiment"
        assert d["recommended_method"] == "paired_ttest"
        assert "dv" in d["variable_roles"]
