"""P0-6: ZIP 交付包导出测试。

验证 ZIP 包结构、manifest 完整度、各模式内容差异。
"""

import json
import zipfile
import io

import pytest

from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.paper_writer.research_deliverable import ResearchDeliverableBundle
from src.output.zip_exporter import build_deliverable_zip


@pytest.fixture
def full_bundle():
    paper = PaperDraftBundle(
        title="测试论文",
        sections={
            "intro": PaperSection(name="引言", markdown="研究背景", source="t"),
            "result": PaperSection(name="结果", markdown="r = .45", source="t"),
        },
        source="test",
    )
    return ResearchDeliverableBundle(
        project_id="zip_test",
        title="ZIP 导出测试",
        paper_bundle=paper,
        analysis_cards=[
            {"method": "pearson_corr", "apa_text": "r = .45, p < .01"},
            {"method": "ttest", "apa_text": "t(28) = 2.1, p = .04"},
        ],
        evidence_records=[
            {"citation_key": "wang2023", "claim": "焦虑负相关"},
            {"citation_key": "li2022", "claim": "自尊保护"},
        ],
        data_cleaning_log=[
            {"step": "列分类", "action": "识别 Q1-Q10"},
            {"step": "计分", "action": "反向计分 Q3"},
        ],
        method_recommendations=[{"recommendation": "Pearson 相关"}],
        health_report=[{"level": "PASS", "message": "所有检查通过"}],
    )


class TestZipBasicMode:
    def test_generates_valid_zip(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="basic")
        assert zip_bytes[:2] == b"PK"

    def test_basic_contains_paper(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="basic")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "paper.md" in names
            assert "paper.docx" in names

    def test_basic_contains_manifest(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="basic")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "manifest.json" in zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["project_id"] == "zip_test"
            assert manifest["mode"] == "basic"

    def test_basic_contains_cards(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="basic")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            card_files = [n for n in names if n.startswith("analysis_cards/")]
            assert len(card_files) == 2


class TestZipStandardMode:
    def test_standard_contains_evidence(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="standard")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "evidence/evidence_table.json" in zf.namelist()

    def test_standard_contains_cleaning_log(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="standard")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "cleaning_log/cleaning_log.json" in zf.namelist()

    def test_standard_no_health_report(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="standard")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "health_report.md" not in zf.namelist()


class TestZipFullMode:
    def test_full_contains_health_report(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="full")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "health_report.md" in zf.namelist()

    def test_full_contains_method_recommendations(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="full")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "method_recommendations.json" in zf.namelist()

    def test_full_manifest_complete(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="full")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            types = {f["type"] for f in manifest["files"]}
            assert "paper" in types
            assert "analysis_card" in types
            assert "evidence" in types
            assert "cleaning_log" in types
            assert "health_report" in types
            assert "method_recommendation" in types


class TestZipWithFigures:
    def test_zip_includes_figures(self, full_bundle):
        from src.output.apa_figures import generate_mean_se_figure
        fig = generate_mean_se_figure(["A", "B"], [3, 5], [0.5, 0.6])
        full_bundle.figures = [fig]
        zip_bytes = build_deliverable_zip(full_bundle, mode="standard")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            fig_files = [n for n in zf.namelist() if n.startswith("figures/")]
            assert len(fig_files) == 1
            assert fig_files[0].endswith(".png")


class TestZipManifest:
    def test_manifest_file_count_matches(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="standard")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            actual_files = [n for n in zf.namelist() if n != "manifest.json"]
            assert manifest["file_count"] == len(actual_files) + 1

    def test_manifest_traceable(self, full_bundle):
        zip_bytes = build_deliverable_zip(full_bundle, mode="standard")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            assert "created_at" in manifest
            assert manifest["title"] == "ZIP 导出测试"

    def test_empty_bundle_still_has_manifest(self):
        bundle = ResearchDeliverableBundle(project_id="empty", title="空项目")
        zip_bytes = build_deliverable_zip(bundle, mode="basic")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "manifest.json" in zf.namelist()
