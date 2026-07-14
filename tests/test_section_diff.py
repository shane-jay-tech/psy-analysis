"""AI 论文差异对比工具测试。"""
import pytest

from src.paper_writer.section_diff import (
    ParagraphDiff,
    SectionDiff,
    compute_section_diff,
)


class TestComputeSectionDiff:
    def test_identical_texts(self):
        text = "第一段内容。\n\n第二段内容。"
        diff = compute_section_diff(text, text, "method")
        assert diff.change_count == 0
        assert diff.total_paragraphs == 2

    def test_modified_paragraph(self):
        original = "第一段。\n\n第二段原文。\n\n第三段。"
        revised = "第一段。\n\n第二段AI修改版。\n\n第三段。"
        diff = compute_section_diff(original, revised, "method")
        assert diff.change_count == 1
        modified = [p for p in diff.paragraphs if p.change_type == "modified"]
        assert len(modified) == 1
        assert "原文" in modified[0].original
        assert "AI修改" in modified[0].revised

    def test_added_paragraph(self):
        original = "第一段。"
        revised = "第一段。\n\n新增段落。"
        diff = compute_section_diff(original, revised, "result")
        added = [p for p in diff.paragraphs if p.change_type == "added"]
        assert len(added) == 1
        assert "新增" in added[0].revised

    def test_removed_paragraph(self):
        original = "第一段。\n\n要删除的段。\n\n第三段。"
        revised = "第一段。\n\n第三段。"
        diff = compute_section_diff(original, revised, "discussion")
        removed = [p for p in diff.paragraphs if p.change_type == "removed"]
        assert len(removed) == 1
        assert "删除" in removed[0].original

    def test_empty_original(self):
        diff = compute_section_diff("", "新内容。", "intro")
        assert diff.total_paragraphs == 1
        assert diff.paragraphs[0].change_type == "added"

    def test_empty_revised(self):
        diff = compute_section_diff("原始内容。", "", "intro")
        assert diff.total_paragraphs == 1
        assert diff.paragraphs[0].change_type == "removed"


class TestSectionDiffSelection:
    def test_default_selection_is_original(self):
        diff = compute_section_diff("原文。\n\nA段。", "原文。\n\nB段。", "test")
        for p in diff.paragraphs:
            if p.change_type == "unchanged":
                assert p.selected == "original"

    def test_select_revised(self):
        diff = compute_section_diff("段A。", "段B。", "test")
        diff.select_paragraph(0, "revised")
        assert diff.paragraphs[0].selected == "revised"

    def test_select_all_revised(self):
        diff = compute_section_diff("A。\n\nB。", "C。\n\nD。", "test")
        diff.select_all_revised()
        assert all(p.selected == "revised" for p in diff.paragraphs)

    def test_get_selected_text_original(self):
        diff = compute_section_diff("原始段落。", "AI段落。", "test")
        diff.select_all_original()
        text = diff.get_selected_text()
        assert "原始" in text

    def test_get_selected_text_revised(self):
        diff = compute_section_diff("原始段落。", "AI段落。", "test")
        diff.select_all_revised()
        text = diff.get_selected_text()
        assert "AI" in text

    def test_mixed_selection(self):
        original = "第一段原文。\n\n第二段原文。"
        revised = "第一段AI版。\n\n第二段AI版。"
        diff = compute_section_diff(original, revised, "test")
        diff.select_paragraph(0, "revised")
        diff.select_paragraph(1, "original")
        text = diff.get_selected_text()
        assert "AI" in text
        assert "原文" in text
