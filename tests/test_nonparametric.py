"""测试非参数检验模块"""
import pandas as pd
import numpy as np
from src.analysis.nonparametric import (
    mann_whitney, wilcoxon_signed_rank, kruskal_wallis, friedman_test,
    NonParamResult,
)


def test_mann_whitney_basic():
    """Mann-Whitney U 基本测试"""
    df = pd.DataFrame({
        "score": [3, 4, 5, 4, 6, 7, 8, 7, 9, 8],
        "group": ["A", "A", "A", "A", "A", "B", "B", "B", "B", "B"],
    })
    result = mann_whitney(df, "score", "group")
    assert isinstance(result, NonParamResult)
    assert result.test_type == "mann_whitney"
    assert result.p_value is not None
    assert 0 <= result.effect_size <= 1
    assert result.group_stats is not None


def test_wilcoxon_basic():
    """Wilcoxon 符号秩检验基本测试"""
    df = pd.DataFrame({
        "pre": [10, 12, 15, 11, 13, 14, 10, 12],
        "post": [8, 10, 12, 10, 11, 12, 9, 11],
    })
    result = wilcoxon_signed_rank(df, "pre", "post")
    assert isinstance(result, NonParamResult)
    assert result.test_type == "wilcoxon"
    assert result.p_value is not None
    assert result.group_stats is not None


def test_kruskal_wallis_basic():
    """Kruskal-Wallis H 检验基本测试"""
    np.random.seed(42)
    df = pd.DataFrame({
        "score": np.concatenate([
            np.random.normal(10, 2, 20),
            np.random.normal(12, 2, 20),
            np.random.normal(8, 2, 20),
        ]),
        "group": ["A"] * 20 + ["B"] * 20 + ["C"] * 20,
    })
    result = kruskal_wallis(df, "score", "group")
    assert isinstance(result, NonParamResult)
    assert result.test_type == "kruskal_wallis"
    assert result.p_value is not None


def test_friedman_basic():
    """Friedman 检验基本测试"""
    np.random.seed(42)
    df = pd.DataFrame({
        "t1": np.random.normal(10, 2, 30),
        "t2": np.random.normal(9, 2, 30),
        "t3": np.random.normal(8, 2, 30),
    })
    result = friedman_test(df, ["t1", "t2", "t3"])
    assert isinstance(result, NonParamResult)
    assert result.test_type == "friedman"
    assert result.p_value is not None
    assert 0 <= result.effect_size <= 1
