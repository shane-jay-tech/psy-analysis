"""自审批注导入/导出测试（v3.5）。"""

from src.literature_review.models import LiteratureItem, ReadingNote
from src.literature_review.review_import import (
    apply_review_comments_to_state,
    export_for_review,
    import_review_comments,
)


def _sample_items():
    return [
        LiteratureItem(
            key="lit_a", title="A 研究", authors=["Smith"], year=2024,
            journal="J Psy", doi="10.1/a", abstract="本研究 n=200，β=0.45",
            relevance_score=0.8,
        ),
        LiteratureItem(
            key="lit_b", title="B 研究", authors=["Li"], year=2023,
            relevance_score=0.5,
        ),
    ]


def _sample_notes():
    return [
        ReadingNote(note_id="n1", literature_key="lit_a", content="A 笔记", type="方法"),
        ReadingNote(note_id="n2", literature_key="lit_b", content="B 笔记", type="结果"),
    ]


class TestExportForReview:
    def test_export_contains_review_markers(self):
        items = _sample_items()
        notes = _sample_notes()
        md = export_for_review(items, notes)
        assert "[REVIEW:lit_a]" in md
        assert "[REVIEW:lit_b]" in md
        assert "[REVIEW_NOTE:n1]" in md
        assert "[REVIEW_NOTE:n2]" in md
        assert "Smith (2024)" in md
        assert "A 笔记" in md

    def test_export_includes_matrix_markers(self):
        matrix = {
            "dimensions": ["样本量", "设计"],
            "cells": {
                "lit_a": {"样本量": "200", "设计": "实验"},
            },
        }
        md = export_for_review(_sample_items(), [], matrix=matrix)
        assert "[REVIEW_MATRIX:lit_a:样本量]" in md
        assert "[REVIEW_MATRIX:lit_a:设计]" in md


class TestImportReviewComments:
    def test_parse_literature_comment(self):
        md = """
## [REVIEW:lit_a] Smith (2024)
正文...
[COMMENT: 这篇文献质量很高，值得精读]
"""
        result = import_review_comments(md)
        assert "lit_a" in result["literature"]
        assert len(result["literature"]["lit_a"]) == 1
        assert "质量很高" in result["literature"]["lit_a"][0]["text"]

    def test_parse_note_comment(self):
        md = """
### [REVIEW_NOTE:n1] [方法]
笔记内容
[COMMENT: 这个方法可以借鉴]
"""
        result = import_review_comments(md)
        assert "n1" in result["notes"]
        assert "借鉴" in result["notes"]["n1"][0]["text"]

    def test_parse_matrix_comment(self):
        md = """
- [REVIEW_MATRIX:lit_a:样本量] 200
[COMMENT: 样本量略小]
"""
        result = import_review_comments(md)
        assert "lit_a:样本量" in result["matrix"]
        assert "样本量略小" in result["matrix"]["lit_a:样本量"][0]["text"]

    def test_multiple_comments_under_one_target(self):
        md = """
## [REVIEW:lit_a] Smith (2024)
[COMMENT: 第一条批注]
[COMMENT: 第二条批注]
"""
        result = import_review_comments(md)
        assert len(result["literature"]["lit_a"]) == 2

    def test_empty_input(self):
        result = import_review_comments("")
        assert result == {"literature": {}, "notes": {}, "matrix": {}}


class TestApplyToState:
    def test_apply_literature_comments(self):
        state = {
            "literature_items": [
                {"key": "lit_a", "title": "A"},
                {"key": "lit_b", "title": "B"},
            ],
            "notes": [{"note_id": "n1", "literature_key": "lit_a", "content": "..."}],
            "matrix": {"dimensions": [], "cells": {}},
        }
        parsed = {
            "literature": {"lit_a": [{"text": "C1", "imported_at": "t"}]},
            "notes": {"n1": [{"text": "N1", "imported_at": "t"}]},
            "matrix": {"lit_a:d1": [{"text": "M1", "imported_at": "t"}]},
        }
        counts = apply_review_comments_to_state(state, parsed)
        assert counts == {"literature": 1, "notes": 1, "matrix": 1}
        # 验证写入
        assert state["literature_items"][0]["review_comments"][0]["text"] == "C1"
        assert state["notes"][0]["review_comments"][0]["text"] == "N1"
        assert state["matrix"]["review_comments"]["lit_a:d1"][0]["text"] == "M1"

    def test_round_trip_export_import(self):
        items = _sample_items()
        notes = _sample_notes()
        md = export_for_review(items, notes)
        # 模拟用户在 lit_a 下加批注
        annotated = md.replace(
            "[REVIEW:lit_a]",
            "[REVIEW:lit_a]\n[COMMENT: 这是 lit_a 的批注]",
            1,
        )
        result = import_review_comments(annotated)
        assert "lit_a" in result["literature"]
        assert "lit_a 的批注" in result["literature"]["lit_a"][0]["text"]
