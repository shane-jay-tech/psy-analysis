"""测试 v3.7 新增信度方法：ω / CR / ICC / 重测 / Cohen's κ / Fleiss' κ"""
import pandas as pd
import numpy as np
import pytest

from src.analysis.reliability import (
    mcdonald_omega,
    composite_reliability,
    intraclass_correlation,
    test_retest_reliability as compute_test_retest,
    cohens_kappa,
    fleiss_kappa,
    ReliabilityResult,
)


# ---------------------------------------------------------------------------
# McDonald's ω
# ---------------------------------------------------------------------------
def test_mcdonald_omega_high_consistency():
    """高内部一致性数据集，ω 应 > 0.7 且接近 α 范围"""
    np.random.seed(42)
    n = 200
    true_score = np.random.normal(0, 1, n)
    items = {f"item{i}": true_score + np.random.normal(0, 0.4, n) for i in range(1, 6)}
    df = pd.DataFrame(items)
    result = mcdonald_omega(df, list(items.keys()), n_bootstrap=100)
    assert isinstance(result, ReliabilityResult)
    assert result.test_type == "mcdonald_omega"
    assert result.omega_value is not None
    assert result.omega_value > 0.7
    assert 0.0 <= result.ci_lower <= result.alpha <= result.ci_upper <= 1.0


def test_mcdonald_omega_too_few_items():
    """少于 3 题应拒绝"""
    df = pd.DataFrame({"a": [1, 2, 3] * 50, "b": [2, 3, 4] * 50})
    with pytest.raises(ValueError):
        mcdonald_omega(df, ["a", "b"])


# ---------------------------------------------------------------------------
# 组合信度 CR
# ---------------------------------------------------------------------------
def test_composite_reliability_two_factors():
    """两个独立潜变量，每个 4 题；CR_per_factor 都应 > 0.7"""
    np.random.seed(42)
    n = 200
    f1 = np.random.normal(0, 1, n)
    f2 = np.random.normal(0, 1, n)
    data = {}
    for i in range(1, 5):
        data[f"a{i}"] = f1 + np.random.normal(0, 0.4, n)
        data[f"b{i}"] = f2 + np.random.normal(0, 0.4, n)
    df = pd.DataFrame(data)
    factors = {"焦虑": [f"a{i}" for i in range(1, 5)],
               "抑郁": [f"b{i}" for i in range(1, 5)]}
    result = composite_reliability(df, factors)
    assert result.test_type == "composite_reliability"
    assert result.cr_per_factor is not None
    assert set(result.cr_per_factor.keys()) == {"焦虑", "抑郁"}
    assert all(v > 0.7 for v in result.cr_per_factor.values())


# ---------------------------------------------------------------------------
# ICC 组内相关系数
# ---------------------------------------------------------------------------
def test_icc_high_agreement():
    """高一致性合成评分数据，ICC(2,1) 应 > 0.7"""
    np.random.seed(42)
    n_targets = 60
    truth = np.random.normal(50, 10, n_targets)
    df = pd.DataFrame({
        f"rater{i}": truth + np.random.normal(0, 2, n_targets)
        for i in range(1, 4)
    })
    result = intraclass_correlation(df, [f"rater{i}" for i in range(1, 4)],
                                     icc_type="ICC2")
    assert result.test_type == "icc"
    assert result.icc_value is not None
    assert result.icc_type == "ICC2"
    assert result.icc_value > 0.7


# ---------------------------------------------------------------------------
# 重测信度
# ---------------------------------------------------------------------------
def test_test_retest_high_stability():
    """两次测量高度相关 → r > 0.7"""
    np.random.seed(42)
    n = 100
    t1 = np.random.normal(50, 10, n)
    t2 = t1 + np.random.normal(0, 3, n)
    df = pd.DataFrame({"T1": t1, "T2": t2})
    result = compute_test_retest(df, "T1", "T2")
    assert result.test_type == "test_retest"
    assert result.test_retest_r is not None
    assert result.test_retest_r > 0.7
    assert result.ci_lower <= result.test_retest_r <= result.ci_upper


# ---------------------------------------------------------------------------
# Cohen's κ（两评分者）
# ---------------------------------------------------------------------------
def test_cohens_kappa_perfect_agreement():
    """完全一致评分 → κ ≈ 1"""
    np.random.seed(42)
    ratings = np.random.choice(["A", "B", "C"], size=80)
    df = pd.DataFrame({"r1": ratings, "r2": ratings})
    result = cohens_kappa(df, "r1", "r2")
    assert result.test_type == "cohens_kappa"
    assert result.kappa_method == "cohen"
    assert result.kappa_value >= 0.99


def test_cohens_kappa_random_agreement():
    """完全随机分类 → κ 接近 0"""
    np.random.seed(0)
    df = pd.DataFrame({
        "r1": np.random.choice(["A", "B"], size=100),
        "r2": np.random.choice(["A", "B"], size=100),
    })
    result = cohens_kappa(df, "r1", "r2")
    assert abs(result.kappa_value) < 0.30


# ---------------------------------------------------------------------------
# Fleiss' κ（多评分者）
# ---------------------------------------------------------------------------
def test_fleiss_kappa_high_agreement():
    """4 个评分者高度一致 → Fleiss' κ > 0.6"""
    np.random.seed(42)
    n = 80
    truth = np.random.choice(["A", "B", "C"], size=n)
    df = pd.DataFrame({
        f"r{i}": [t if np.random.rand() > 0.1 else np.random.choice(["A", "B", "C"])
                  for t in truth]
        for i in range(1, 5)
    })
    result = fleiss_kappa(df, [f"r{i}" for i in range(1, 5)])
    assert result.test_type == "fleiss_kappa"
    assert result.kappa_method == "fleiss"
    assert result.kappa_value > 0.6


def test_fleiss_kappa_too_few_raters():
    """少于 3 评分者应拒绝（建议用 Cohen's κ）"""
    df = pd.DataFrame({"a": ["A"] * 30, "b": ["A"] * 30})
    with pytest.raises(ValueError):
        fleiss_kappa(df, ["a", "b"])
