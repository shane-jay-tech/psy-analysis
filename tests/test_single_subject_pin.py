"""src/experiment_design/single_subject.py 现状钉测（s918-33）。

characterization：固定 8 点合成数据，断言 _compute_pnd / _compute_nap / _interpret_pnd
**当前产出值与分档文案边界**。不做方法学评价、不改算法、src 零改动。
数值一律由被测函数自身跑出后回填，非人工推导。
"""
import math

import numpy as np
import pytest

from src.experiment_design.single_subject import (
    _compute_nap,
    _interpret_pnd,
    _compute_pnd,
)

BASELINE = np.array([3, 4, 4, 5, 5, 6, 6, 7], dtype=float)
INTERVENTION = np.array([5, 6, 6, 7, 8, 8, 9, 10], dtype=float)
DECLINE_BASE = np.array([8, 9, 9, 10, 10, 11, 11, 12], dtype=float)
DECLINE_INTER = np.array([3, 4, 5, 5, 6, 6, 7, 9], dtype=float)


def _arr(values):
    return np.array(values, dtype=float)


def test_pnd_increase_branch_pins_current_value():
    assert float(_compute_pnd(BASELINE, INTERVENTION)) == 0.5


def test_pnd_decrease_branch_pins_current_value():
    assert float(_compute_pnd(DECLINE_BASE, DECLINE_INTER)) == 0.875


def test_pnd_counts_strictly_beyond_the_extreme_point():
    """与基线极端点等值的干预点算重叠，不计入分子。"""
    baseline = _arr([5, 5, 5, 5, 5, 5, 5, 5])
    intervention = _arr([5, 5, 5, 5, 6, 6, 6, 6])

    assert float(_compute_pnd(baseline, intervention)) == 0.5


def test_pnd_branch_choice_is_mean_comparison_only():
    """两均值相等时走「提升」分支——此处干预实际逐点下降，PND 仍按基线最大值判。"""
    baseline = _arr([3, 4, 5, 6, 7, 8, 9, 10])
    intervention = _arr([10, 9, 8, 7, 6, 5, 4, 3])

    assert float(intervention.mean()) == float(baseline.mean())
    assert float(_compute_pnd(baseline, intervention)) == 0.0


def test_pnd_with_empty_intervention_returns_nan_not_an_error():
    with np.errstate(all="ignore"):
        value = _compute_pnd(BASELINE, _arr([]))

    assert math.isnan(float(value))


def test_nap_increase_branch_pins_current_value():
    assert float(_compute_nap(BASELINE, INTERVENTION)) == 0.8671875


def test_nap_decrease_branch_pins_current_value():
    assert float(_compute_nap(DECLINE_BASE, DECLINE_INTER)) == 0.03125


def test_nap_half_when_every_pair_ties():
    same = _arr([5] * 8)

    assert float(_compute_nap(same, same)) == 0.5


def test_nap_half_when_either_side_is_empty():
    assert float(_compute_nap(BASELINE, _arr([]))) == 0.5
    assert float(_compute_nap(_arr([]), INTERVENTION)) == 0.5


@pytest.mark.parametrize(
    "pnd,expected",
    [
        (1.0, "非常有效（PND ≥ 90%）"),
        (0.90, "非常有效（PND ≥ 90%）"),
        (0.8999, "中等有效（70% ≤ PND < 90%）"),
        (0.70, "中等有效（70% ≤ PND < 90%）"),
        (0.6999, "效果存疑（50% ≤ PND < 70%）"),
        (0.50, "效果存疑（50% ≤ PND < 70%）"),
        (0.4999, "无效（PND < 50%）"),
        (0.0, "无效（PND < 50%）"),
    ],
)
def test_interpret_pnd_tier_copy_and_boundaries(pnd, expected):
    assert _interpret_pnd(pnd) == expected


def test_interpret_pnd_of_nan_falls_through_to_invalid_copy():
    assert _interpret_pnd(float("nan")) == "无效（PND < 50%）"
