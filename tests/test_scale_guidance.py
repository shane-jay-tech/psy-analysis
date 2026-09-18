# -*- coding: utf-8 -*-
"""s918-40：量表指导五个纯函数钉桩（scale_guidance.py，110 行盲区）。"""
import pytest

from src.questionnaire.scale_guidance import (
    recommend_scale_points,
    get_anchor_labels,
    recommend_scoring,
    recommend_item_count,
    reverse_item_ratio,
)


def test_recommend_scale_points_boundaries():
    """推荐点数边界：临床焦虑/抑郁 4 点；一般 5 点。"""
    assert recommend_scale_points({"domain": "临床与健康", "name_zh": "焦虑自评量表"}) == 4
    assert recommend_scale_points({"domain": "人格", "name_zh": "大五人格"}) == 5


def test_get_anchor_labels_count_and_fallback():
    """标签数=点数；未知点数回落 5 点 agreement 标签。"""
    assert len(get_anchor_labels(5)) == 5
    assert len(get_anchor_labels(7)) == 7
    assert len(get_anchor_labels(4, "frequency")) == 4
    fallback = get_anchor_labels(99)
    assert len(fallback) == 5, "未知点数回落 5 点标签"


def test_recommend_scoring_returns_string():
    """评分建议返回字符串（含反向题比例信息）。"""
    advice = recommend_scoring({"domain": "人格", "name_zh": "大五人格"}, 20, 5)
    assert isinstance(advice, str)
    assert len(advice) > 0


def test_recommend_item_count_returns_expected_keys():
    """条数建议返回 total/per_dim/dimensions 三键（dimensions 为维度 dict 列表）。"""
    dims = [{"name": "维度A", "item_count": 5}, {"name": "维度B", "item_count": 5}, {"name": "维度C", "item_count": 5}]
    result = recommend_item_count({"domain": "人格", "name_zh": "大五人格", "dimensions": dims})
    assert set(result.keys()) == {"total", "per_dim", "dimensions"}
    assert result["total"] == 15
    assert result["dimensions"] == 3


def test_reverse_item_ratio_bounds():
    """反向比例：总数 20 → 约 20-25% 反向，字段为数值。"""
    ratio = reverse_item_ratio(20)
    assert isinstance(ratio, dict)
    values = [v for v in ratio.values() if isinstance(v, (int, float))]
    assert any(0 < v <= 10 for v in values), f"反向题数量应在 1-10 区间：{ratio}"
