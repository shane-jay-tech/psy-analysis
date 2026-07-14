"""ResearchDeliverableBundle 测试。"""

import pytest

from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.paper_writer.research_deliverable import ResearchDeliverableBundle


@pytest.fixture
def paper_bundle():
    return PaperDraftBundle(
        title="焦虑与自尊关系研究",
        sections={
            "introduction": PaperSection(name="引言", markdown="研究背景...", source="template"),
            "method": PaperSection(name="方法", markdown="问卷法...", source="template"),
            "result": PaperSection(name="结果", markdown="M=3.0...", source="data"),
            "discussion": PaperSection(name="讨论", markdown="支持假设...", source="template"),
        },
        source="template",
    )


@pytest.fixture
def full_bundle(paper_bundle):
    return ResearchDeliverableBundle(
        project_id="proj_001",
        title="焦虑与自尊关系研究",
        paper_bundle=paper_bundle,
        analysis_cards=[{"method": "pearson_corr", "apa_text": "r=-0.42, p<.001"}],
        evidence_records=[{"citation_key": "wang2023", "claim": "焦虑正相关倦怠"}],
        references=[{"key": "wang2023", "title": "Anxiety study"}],
        data_cleaning_log=[{"step": "列分类", "action": "识别 8 题项列"}],
        method_recommendations=[{"primary": "pearson_corr"}],
        health_report=[{"level": "WARN", "message": "文献 < 5 篇"}],
        ai_diff_log={"introduction": "revised", "method": "original"},
        figures=["fig1.png"],
    )


class TestExportability:
    def test_full_bundle_exportable(self, full_bundle):
        exportable, reasons = full_bundle.is_exportable()
        assert exportable is True
        assert reasons == []

    def test_no_paper_not_exportable(self):
        bundle = ResearchDeliverableBundle(
            analysis_cards=[{"method": "ttest"}],
        )
        exportable, reasons = bundle.is_exportable()
        assert exportable is False
        assert any("论文" in r for r in reasons)

    def test_no_cards_not_exportable(self, paper_bundle):
        bundle = ResearchDeliverableBundle(paper_bundle=paper_bundle)
        exportable, reasons = bundle.is_exportable()
        assert exportable is False
        assert any("结果卡" in r for r in reasons)

    def test_health_error_blocks(self, paper_bundle):
        bundle = ResearchDeliverableBundle(
            paper_bundle=paper_bundle,
            analysis_cards=[{"method": "ttest"}],
            health_report=[{"level": "ERROR", "message": "无数据"}],
        )
        exportable, reasons = bundle.is_exportable()
        assert exportable is False
        assert any("ERROR" in r for r in reasons)

    def test_health_warn_allows(self, paper_bundle):
        bundle = ResearchDeliverableBundle(
            paper_bundle=paper_bundle,
            analysis_cards=[{"method": "ttest"}],
            health_report=[{"level": "WARN", "message": "文献少"}],
        )
        exportable, _ = bundle.is_exportable()
        assert exportable is True


class TestFileManifest:
    def test_full_manifest(self, full_bundle):
        manifest = full_bundle.file_manifest()
        types = [f["type"] for f in manifest]
        assert "paper" in types
        assert "cards" in types
        assert "evidence" in types
        assert "references" in types
        assert "cleaning" in types
        assert "recommendations" in types
        assert "health" in types
        assert "ai_diff" in types
        assert "figure" in types
        assert "meta" in types

    def test_minimal_manifest(self):
        bundle = ResearchDeliverableBundle(project_id="test")
        manifest = bundle.file_manifest()
        assert len(manifest) == 1  # only meta
        assert manifest[0]["type"] == "meta"

    def test_manifest_uses_project_id(self, full_bundle):
        manifest = full_bundle.file_manifest()
        assert all("proj_001" in f["path"] for f in manifest)


class TestMarkdownIndex:
    def test_index_contains_title(self, full_bundle):
        md = full_bundle.to_markdown_index()
        assert "焦虑与自尊" in md

    def test_index_shows_exportable(self, full_bundle):
        md = full_bundle.to_markdown_index()
        assert "可导出" in md

    def test_index_shows_counts(self, full_bundle):
        md = full_bundle.to_markdown_index()
        assert "1 张" in md  # cards
        assert "1 条" in md  # evidence

    def test_index_shows_health(self, full_bundle):
        md = full_bundle.to_markdown_index()
        assert "WARN: 1" in md


class TestExportMeta:
    def test_meta_contains_all_fields(self, full_bundle):
        meta = full_bundle.export_meta_dict()
        assert meta["project_id"] == "proj_001"
        assert meta["title"] == "焦虑与自尊关系研究"
        assert meta["analysis_card_count"] == 1
        assert meta["evidence_record_count"] == 1
        assert meta["figure_count"] == 1
        assert meta["reference_count"] == 1
        assert meta["health_errors"] == 0
        assert meta["health_warns"] == 1
        assert meta["has_ai_diff_log"] is True

    def test_meta_paper_sections(self, full_bundle):
        meta = full_bundle.export_meta_dict()
        assert "introduction" in meta["paper_sections"]
        assert "result" in meta["paper_sections"]
