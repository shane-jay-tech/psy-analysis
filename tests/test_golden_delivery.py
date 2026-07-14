"""v5.4 P1-4: Golden Delivery Packages 质量基准测试。

验证至少 3 个模板的完整交付包符合质量基准：
- ZIP 结构完整
- manifest.json 符合 schema
- 包含 AI_USAGE_DISCLOSURE.md
- 包含 PRIVACY_PRECHECK_SUMMARY.json
- 包含 REPRODUCIBILITY_MANIFEST.json
- analysis_cards 可追溯
"""
import io
import json
import zipfile

import pandas as pd
import pytest

from src.templates.registry import get_template
from src.analysis.runner import run_analysis
from src.parser.intent_resolver import AnalysisPlan
from src.analysis.result_card import build_card_from_output
from src.output.zip_exporter import build_deliverable_zip
from src.paper_writer.research_deliverable import ResearchDeliverableBundle

GOLDEN_TEMPLATES = [
    "questionnaire_correlation",
    "independent_group_comparison",
    "pre_post_experiment",
]


def _build_delivery_zip(template_id: str) -> bytes:
    """为指定模板构建标准交付包。"""
    t = get_template(template_id)
    df = pd.read_csv(t.get_path() / "data.csv")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    method = t.recommended_method
    if method in ("pearson_corr",):
        dvs, ivs = numeric_cols[:2], []
    elif method in ("independent_ttest",):
        dvs, ivs = numeric_cols[:1], cat_cols[:1]
    elif method in ("paired_ttest",):
        dvs, ivs = numeric_cols[:2], []
    else:
        dvs, ivs = numeric_cols[:1], cat_cols[:1] if cat_cols else numeric_cols[1:2]

    plan = AnalysisPlan(test_type=method, dependent_vars=dvs, independent_vars=ivs, raw_request="golden")
    output = run_analysis(df, plan)
    card = build_card_from_output(output)

    bundle = ResearchDeliverableBundle(
        project_id=f"golden_{template_id}",
        title=t.name,
        analysis_cards=[card.to_dict() if hasattr(card, "to_dict") else card.__dict__],
    )
    return build_deliverable_zip(bundle, mode="standard")


class TestGoldenDeliveryStructure:
    """验证交付包 ZIP 结构。"""

    @pytest.mark.parametrize("template_id", GOLDEN_TEMPLATES)
    def test_zip_valid(self, template_id):
        z = _build_delivery_zip(template_id)
        assert len(z) > 100
        with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
            assert zf.testzip() is None

    @pytest.mark.parametrize("template_id", GOLDEN_TEMPLATES)
    def test_has_manifest(self, template_id):
        z = _build_delivery_zip(template_id)
        with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
            assert "manifest.json" in zf.namelist()

    @pytest.mark.parametrize("template_id", GOLDEN_TEMPLATES)
    def test_has_ai_disclosure(self, template_id):
        z = _build_delivery_zip(template_id)
        with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
            assert "AI_USAGE_DISCLOSURE.md" in zf.namelist()
            content = zf.read("AI_USAGE_DISCLOSURE.md").decode("utf-8")
            assert "学术诚信" in content
            assert "研究者责任" in content

    @pytest.mark.parametrize("template_id", GOLDEN_TEMPLATES)
    def test_has_privacy_precheck(self, template_id):
        z = _build_delivery_zip(template_id)
        with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
            assert "PRIVACY_PRECHECK_SUMMARY.json" in zf.namelist()
            data = json.loads(zf.read("PRIVACY_PRECHECK_SUMMARY.json"))
            assert "precheck_performed" in data
            assert "safe" in data

    @pytest.mark.parametrize("template_id", GOLDEN_TEMPLATES)
    def test_has_reproducibility_manifest(self, template_id):
        z = _build_delivery_zip(template_id)
        with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
            assert "REPRODUCIBILITY_MANIFEST.json" in zf.namelist()
            data = json.loads(zf.read("REPRODUCIBILITY_MANIFEST.json"))
            assert data["analysis_count"] >= 1
            assert len(data["analyses"]) >= 1


class TestGoldenDeliveryManifestSchema:
    """验证 manifest 符合 schema。"""

    @pytest.mark.parametrize("template_id", GOLDEN_TEMPLATES)
    def test_manifest_required_fields(self, template_id):
        z = _build_delivery_zip(template_id)
        with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))

        assert manifest["project_id"] == f"golden_{template_id}"
        assert manifest["mode"] == "standard"
        assert manifest["file_count"] >= 4
        assert isinstance(manifest["files"], list)
        assert len(manifest["files"]) >= 4

    @pytest.mark.parametrize("template_id", GOLDEN_TEMPLATES)
    def test_manifest_files_have_type(self, template_id):
        z = _build_delivery_zip(template_id)
        with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))

        for entry in manifest["files"]:
            assert "path" in entry
            assert "type" in entry


class TestGoldenDeliveryCards:
    """验证 analysis cards 可追溯。"""

    @pytest.mark.parametrize("template_id", GOLDEN_TEMPLATES)
    def test_cards_exist_in_zip(self, template_id):
        z = _build_delivery_zip(template_id)
        with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
            card_files = [n for n in zf.namelist() if "analysis_cards/" in n]
            assert len(card_files) >= 1

    @pytest.mark.parametrize("template_id", GOLDEN_TEMPLATES)
    def test_card_json_valid(self, template_id):
        z = _build_delivery_zip(template_id)
        with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
            card_files = [n for n in zf.namelist() if "analysis_cards/" in n and n.endswith(".json")]
            for cf in card_files:
                data = json.loads(zf.read(cf))
                assert "method_id" in data or "method_name" in data
