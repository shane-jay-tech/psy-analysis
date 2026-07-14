"""PaperDraftBundle 和适配器测试。"""
import pytest

from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.paper_writer.adapters import (
    bundle_from_wizard_template,
    bundle_from_ai_result,
    bundle_from_paper_engine,
    bundle_with_selected_sections,
)


class TestPaperSection:
    def test_auto_generated_at(self):
        sec = PaperSection(name="方法", markdown="text", source="template")
        assert sec.generated_at != ""

    def test_explicit_generated_at(self):
        sec = PaperSection(name="方法", markdown="text", source="ai", generated_at="2026-01-01")
        assert sec.generated_at == "2026-01-01"


class TestPaperDraftBundle:
    def test_method_md_property(self):
        bundle = PaperDraftBundle(
            title="test",
            sections={"method": PaperSection(name="方法", markdown="# Method", source="template")},
        )
        assert bundle.method_md == "# Method"

    def test_missing_section_returns_empty(self):
        bundle = PaperDraftBundle(title="test")
        assert bundle.method_md == ""
        assert bundle.result_md == ""

    def test_all_markdown(self):
        bundle = PaperDraftBundle(
            title="test",
            sections={
                "method": PaperSection(name="方法", markdown="M", source="template"),
                "result": PaperSection(name="结果", markdown="R", source="template"),
            },
        )
        md = bundle.all_markdown()
        assert "M" in md
        assert "R" in md

    def test_section_sources(self):
        bundle = PaperDraftBundle(
            title="test",
            sections={
                "method": PaperSection(name="方法", markdown="M", source="template"),
                "result": PaperSection(name="结果", markdown="R", source="ai"),
            },
        )
        sources = bundle.section_sources()
        assert sources == {"method": "template", "result": "ai"}


class TestAdapterFromTemplate:
    def test_basic(self):
        bundle = bundle_from_wizard_template("方法内容", "结果内容", title="测试论文")
        assert bundle.title == "测试论文"
        assert bundle.source == "template"
        assert bundle.method_md == "方法内容"
        assert bundle.result_md == "结果内容"

    def test_empty_sections_excluded(self):
        bundle = bundle_from_wizard_template("方法", "")
        assert "method" in bundle.sections
        assert "result" not in bundle.sections


class TestAdapterFromAI:
    def test_basic(self):
        bundle = bundle_from_ai_result("AI方法", "AI结果", title="AI论文", model_name="gpt-5")
        assert bundle.source == "ai"
        assert bundle.method_md == "AI方法"
        assert bundle.meta.get("model") == "gpt-5"

    def test_all_sections(self):
        bundle = bundle_from_ai_result("M", "R", discussion_md="D")
        assert "discussion" in bundle.sections


class TestAdapterFromPaperEngine:
    def test_basic(self):
        result = {
            "method": "引擎方法",
            "result": "引擎结果",
            "title": "引擎论文",
            "meta": {"engine_version": "1.0"},
        }
        bundle = bundle_from_paper_engine(result)
        assert bundle.source == "paper_engine"
        assert bundle.method_md == "引擎方法"
        assert bundle.title == "引擎论文"

    def test_with_md_suffix(self):
        result = {"method_md": "方法2", "result_md": "结果2"}
        bundle = bundle_from_paper_engine(result)
        assert bundle.method_md == "方法2"


class TestBundleWithSelectedSections:
    def test_mixed_selection(self):
        template = bundle_from_wizard_template("模板方法", "模板结果", title="T")
        ai = bundle_from_ai_result("AI方法", "AI结果", title="A")

        mixed = bundle_with_selected_sections(
            {"template": template, "ai": ai},
            {"method": "ai", "result": "template"},
        )
        assert mixed.source == "mixed"
        assert mixed.method_md == "AI方法"
        assert mixed.result_md == "模板结果"
        assert mixed.provenance["method"] == "ai"
        assert mixed.provenance["result"] == "template"

    def test_all_from_template(self):
        template = bundle_from_wizard_template("M", "R", title="Only Template")
        mixed = bundle_with_selected_sections(
            {"template": template},
            {"method": "template", "result": "template"},
        )
        assert mixed.method_md == "M"
        assert mixed.result_md == "R"
