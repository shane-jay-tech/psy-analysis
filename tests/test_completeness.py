"""文献综述完成度评分测试（v3.5）。"""

from src.literature_review.completeness import (
    CompletenessResult,
    calculate_completeness,
)


def _empty_state():
    return {
        "literature_items": [],
        "notes": [],
        "matrix": {"dimensions": [], "cells": {}},
        "themes": [],
        "gaps": [],
    }


def _full_state():
    items = [
        {"key": f"k{i}", "relevance_score": 0.6, "title": f"T{i}", "year": 2024}
        for i in range(15)
    ]
    notes = [{"literature_key": f"k{i}", "content": "n"} for i in range(8)]
    cells = {f"k{i}": {"样本量": "200", "研究设计": "实验"} for i in range(15)}
    return {
        "literature_items": items,
        "notes": notes,
        "matrix": {
            "dimensions": ["样本量", "研究设计"],
            "cells": cells,
            "highlighted_keys": [],
        },
        "themes": [{"theme_name": "T1"}],
        "gaps": [{"gap_description": "G1"}],
    }


class TestCompletenessBasics:
    def test_empty_state_total_is_zero(self):
        result = calculate_completeness(_empty_state())
        assert result.total == 0.0
        assert result.grade == "不足"
        assert len(result.sub_scores) == 6

    def test_full_state_total_high(self):
        result = calculate_completeness(_full_state())
        assert result.total >= 80.0
        assert result.grade == "优秀"

    def test_grade_thresholds(self):
        assert CompletenessResult(total=85).grade == "优秀"
        assert CompletenessResult(total=65).grade == "良好"
        assert CompletenessResult(total=45).grade == "及格"
        assert CompletenessResult(total=20).grade == "不足"


class TestSubScores:
    def test_15_items_gets_full_lit_score(self):
        state = _empty_state()
        state["literature_items"] = [{"key": f"k{i}", "relevance_score": 0.5} for i in range(15)]
        result = calculate_completeness(state)
        sub = next(s for s in result.sub_scores if s.name == "文献量")
        assert sub.score == 20.0

    def test_5_items_partial_lit_score(self):
        state = _empty_state()
        state["literature_items"] = [{"key": f"k{i}", "relevance_score": 0.5} for i in range(5)]
        result = calculate_completeness(state)
        sub = next(s for s in result.sub_scores if s.name == "文献量")
        assert 0 < sub.score < 20.0

    def test_high_relevance_ratio_score(self):
        state = _empty_state()
        # 全部高相关
        state["literature_items"] = [{"key": f"k{i}", "relevance_score": 0.7} for i in range(10)]
        result = calculate_completeness(state)
        sub = next(s for s in result.sub_scores if s.name == "高相关占比")
        assert sub.score == 20.0

    def test_no_themes_no_score(self):
        state = _empty_state()
        state["literature_items"] = [{"key": "k1", "relevance_score": 0.5}]
        result = calculate_completeness(state)
        sub = next(s for s in result.sub_scores if s.name == "主题聚类")
        assert sub.score == 0.0
        assert "尚未" in sub.suggestion

    def test_no_gaps_no_score(self):
        state = _empty_state()
        result = calculate_completeness(state)
        sub = next(s for s in result.sub_scores if s.name == "Gap 分析")
        assert sub.score == 0.0


class TestSerialization:
    def test_as_dict_format(self):
        state = _full_state()
        result = calculate_completeness(state)
        data = result.as_dict()
        assert "total" in data
        assert "grade" in data
        assert "sub_scores" in data
        assert len(data["sub_scores"]) == 6
        assert all("name" in s and "score" in s for s in data["sub_scores"])
