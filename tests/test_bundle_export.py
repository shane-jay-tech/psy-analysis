"""PaperDraftBundle 导出桥接测试。"""
import pytest

from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.paper_writer.bundle_export import (
    ExportMeta,
    ExportResult,
    bundle_to_markdown,
    bundle_to_docx_args,
    bundle_to_export_result,
    validate_bundle_for_export,
)


def _make_bundle(**kwargs) -> PaperDraftBundle:
    sections = {
        "introduction": PaperSection(name="引言", markdown="这是引言段落。", source="template"),
        "method": PaperSection(name="方法", markdown="本研究采用实验设计。", source="ai"),
        "result": PaperSection(name="结果", markdown="t(28)=2.45, p<.05。", source="data"),
        "discussion": PaperSection(name="讨论", markdown="结果支持假设。", source="template"),
    }
    defaults = dict(title="心理学论文", sections=sections)
    defaults.update(kwargs)
    return PaperDraftBundle(**defaults)


class TestBundleToMarkdown:
    def test_basic_output(self):
        bundle = _make_bundle()
        md = bundle_to_markdown(bundle)
        assert "# 心理学论文" in md
        assert "## 引言" in md
        assert "## 方法" in md
        assert "## 结果" in md
        assert "## 讨论" in md
        assert "这是引言段落。" in md

    def test_section_order(self):
        bundle = _make_bundle()
        md = bundle_to_markdown(bundle)
        intro_pos = md.index("## 引言")
        method_pos = md.index("## 方法")
        result_pos = md.index("## 结果")
        discussion_pos = md.index("## 讨论")
        assert intro_pos < method_pos < result_pos < discussion_pos

    def test_source_tags_included(self):
        bundle = _make_bundle()
        md = bundle_to_markdown(bundle, include_source_tags=True)
        assert "<!-- source: template -->" in md
        assert "<!-- source: ai -->" in md

    def test_source_tags_excluded(self):
        bundle = _make_bundle()
        md = bundle_to_markdown(bundle, include_source_tags=False)
        assert "<!-- source:" not in md

    def test_provenance_section(self):
        bundle = _make_bundle(provenance={"method": "wizard_v3"})
        md = bundle_to_markdown(bundle, include_provenance=True)
        assert "来源追溯" in md
        assert "wizard_v3" in md

    def test_warnings_section(self):
        bundle = _make_bundle(warnings=["效应量未报告"])
        md = bundle_to_markdown(bundle)
        assert "效应量未报告" in md


class TestBundleToDocxArgs:
    def test_basic_args(self):
        bundle = _make_bundle()
        meta = ExportMeta(title="测试论文", author="张三")
        args = bundle_to_docx_args(bundle, meta)
        assert args["title"] == "测试论文"
        assert args["author"] == "张三"
        assert "introduction" in args["sections"]
        assert "method" in args["sections"]

    def test_default_meta(self):
        bundle = _make_bundle()
        args = bundle_to_docx_args(bundle)
        assert args["title"] == "心理学论文"


class TestBundleToExportResult:
    def test_markdown_export(self):
        bundle = _make_bundle()
        result = bundle_to_export_result(bundle, format="markdown")
        assert result.format == "markdown"
        assert "心理学论文" in result.content
        assert result.filename.endswith(".md")

    def test_docx_export(self):
        bundle = _make_bundle()
        result = bundle_to_export_result(bundle, format="docx")
        assert result.format == "docx"
        assert result.filename.endswith(".docx")

    def test_unsupported_format(self):
        bundle = _make_bundle()
        with pytest.raises(ValueError, match="Unsupported"):
            bundle_to_export_result(bundle, format="pdf")

    def test_warnings_propagated(self):
        bundle = _make_bundle(warnings=["有问题"])
        result = bundle_to_export_result(bundle, format="markdown")
        assert "有问题" in result.warnings


class TestValidateBundleForExport:
    def test_valid_bundle(self):
        bundle = _make_bundle()
        issues = validate_bundle_for_export(bundle)
        assert issues == []

    def test_empty_title(self):
        bundle = _make_bundle(title="")
        issues = validate_bundle_for_export(bundle)
        assert any("标题" in i for i in issues)

    def test_no_sections(self):
        bundle = PaperDraftBundle(title="空论文", sections={})
        issues = validate_bundle_for_export(bundle)
        assert any("无任何章节" in i for i in issues)

    def test_empty_section_content(self):
        sections = {
            "method": PaperSection(name="方法", markdown="   ", source="template"),
        }
        bundle = PaperDraftBundle(title="论文", sections=sections)
        issues = validate_bundle_for_export(bundle)
        assert any("方法" in i and "为空" in i for i in issues)

    def test_warnings_noted(self):
        bundle = _make_bundle(warnings=["问题1", "问题2"])
        issues = validate_bundle_for_export(bundle)
        assert any("2 条警告" in i for i in issues)
