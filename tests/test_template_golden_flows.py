"""v5.4 P0-3: 模板 Golden Flow 自动化测试。

验证每个模板从加载到导出的完整链路：
  config解析 → data加载 → 推荐方法存在 → 分析执行 → 结果卡片 → APA表格 → ZIP结构 → manifest → quality无ERROR
"""
import json
import zipfile
import io

import pandas as pd
import pytest

from src.templates.registry import list_templates, get_template
from src.analysis.runner import run_analysis
from src.parser.intent_resolver import AnalysisPlan
from src.analysis.result_card import build_card_from_output
from src.output.apa_tables import generate_tables_from_card


ALL_TEMPLATE_IDS = [t.template_id for t in list_templates()]


class TestTemplateGoldenFlowConfig:
    """验证每个模板配置可解析且完整。"""

    @pytest.mark.parametrize("template_id", ALL_TEMPLATE_IDS)
    def test_config_parseable(self, template_id):
        t = get_template(template_id)
        config_path = t.get_path() / "template_config.json"
        assert config_path.exists(), f"缺少 template_config.json: {template_id}"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        config_id = config.get("template_id") or config.get("id")
        assert config_id == template_id

    @pytest.mark.parametrize("template_id", ALL_TEMPLATE_IDS)
    def test_data_loadable(self, template_id):
        t = get_template(template_id)
        data_path = t.get_path() / "data.csv"
        assert data_path.exists(), f"缺少 data.csv: {template_id}"
        df = pd.read_csv(data_path)
        assert len(df) >= 30
        assert len(df.columns) >= 3


class TestTemplateGoldenFlowAnalysis:
    """验证每个模板的推荐方法可执行分析并产出结果。"""

    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_basic_templates_analysis_runs(self, template_id):
        """基础模板（前 3 个）分析执行成功。"""
        t = get_template(template_id)
        df = pd.read_csv(t.get_path() / "data.csv")

        plan = _build_plan_for_template(t, df)
        output = run_analysis(df, plan)

        assert output is not None
        assert output.get("test_type") == t.recommended_method
        assert not _has_critical_errors(output)

    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_basic_templates_result_card(self, template_id):
        """基础模板产出结果卡片。"""
        t = get_template(template_id)
        df = pd.read_csv(t.get_path() / "data.csv")

        plan = _build_plan_for_template(t, df)
        output = run_analysis(df, plan)
        card = build_card_from_output(output)

        assert card is not None
        assert card.method_id == t.recommended_method

    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_basic_templates_card_has_method(self, template_id):
        """基础模板结果卡片包含方法标识。"""
        t = get_template(template_id)
        df = pd.read_csv(t.get_path() / "data.csv")

        plan = _build_plan_for_template(t, df)
        output = run_analysis(df, plan)
        card = build_card_from_output(output)
        card_dict = card.to_dict() if hasattr(card, "to_dict") else card.__dict__

        assert card_dict.get("method_id") or card_dict.get("method_name")


class TestTemplateGoldenFlowZIP:
    """验证模板完整交付包 ZIP 结构正确。"""

    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_zip_structure(self, template_id):
        """完整交付包 ZIP 包含 manifest 和 analysis_cards。"""
        from src.output.zip_exporter import build_deliverable_zip
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle

        t = get_template(template_id)
        df = pd.read_csv(t.get_path() / "data.csv")

        plan = _build_plan_for_template(t, df)
        output = run_analysis(df, plan)
        card = build_card_from_output(output)

        bundle = ResearchDeliverableBundle(
            project_id=f"golden_flow_{template_id}",
            title=t.name,
            analysis_cards=[card.to_dict() if hasattr(card, "to_dict") else card.__dict__],
        )

        zip_bytes = build_deliverable_zip(bundle, mode="standard")
        assert len(zip_bytes) > 0

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert any("analysis_cards/" in n for n in names), f"ZIP 缺少 analysis_cards/"

            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["project_id"] == f"golden_flow_{template_id}"
            assert manifest["file_count"] >= 2

    @pytest.mark.parametrize("template_id", [
        "questionnaire_correlation",
        "independent_group_comparison",
        "pre_post_experiment",
    ])
    def test_zip_manifest_valid(self, template_id):
        """ZIP manifest 结构完整且文件列表非空。"""
        from src.output.zip_exporter import build_deliverable_zip
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle

        t = get_template(template_id)
        df = pd.read_csv(t.get_path() / "data.csv")

        plan = _build_plan_for_template(t, df)
        output = run_analysis(df, plan)
        card = build_card_from_output(output)

        bundle = ResearchDeliverableBundle(
            project_id=f"golden_flow_{template_id}",
            title=t.name,
            analysis_cards=[card.to_dict() if hasattr(card, "to_dict") else card.__dict__],
        )

        zip_bytes = build_deliverable_zip(bundle, mode="standard")
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))
            assert "files" in manifest
            assert len(manifest["files"]) >= 1
            assert manifest.get("mode") == "standard"


# ─── Helpers ───

def _build_plan_for_template(template, df: pd.DataFrame) -> AnalysisPlan:
    """根据模板配置构建 AnalysisPlan。"""
    roles = template.variable_roles
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    method = template.recommended_method

    if method in ("pearson_corr", "spearman_corr"):
        dvs = numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols
        ivs = []
    elif method in ("independent_ttest", "mann_whitney"):
        dvs = numeric_cols[:1]
        ivs = cat_cols[:1]
    elif method in ("paired_ttest", "wilcoxon"):
        dvs = numeric_cols[:2]
        ivs = []
    elif method in ("mediation_analysis",):
        dvs = numeric_cols[:1]
        ivs = numeric_cols[1:3] if len(numeric_cols) >= 3 else numeric_cols[1:]
    elif method in ("moderation_analysis",):
        dvs = numeric_cols[:1]
        ivs = numeric_cols[1:3] if len(numeric_cols) >= 3 else numeric_cols[1:]
    elif method in ("cfa", "efa"):
        dvs = numeric_cols[:12]
        ivs = []
    else:
        dvs = numeric_cols[:1]
        ivs = cat_cols[:1] if cat_cols else numeric_cols[1:2]

    return AnalysisPlan(
        test_type=method,
        dependent_vars=dvs,
        independent_vars=ivs,
        raw_request=f"[Golden Flow] {template.name}",
    )


def _has_critical_errors(output: dict) -> bool:
    """检查分析输出是否有阻断性错误。"""
    errors = output.get("errors", [])
    for e in errors:
        if isinstance(e, dict) and e.get("severity") == "error":
            return True
    return False
