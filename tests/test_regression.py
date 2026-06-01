"""测试回归分析模块"""
import pandas as pd
import numpy as np
from src.analysis.regression import (
    linear_regression, multiple_regression, hierarchical_regression,
    RegressionResult,
)


def test_linear_regression_basic():
    """简单线性回归基本测试"""
    np.random.seed(42)
    x = np.random.normal(0, 1, 100)
    y = 2 * x + np.random.normal(0, 0.5, 100)
    df = pd.DataFrame({"x": x, "y": y})
    result = linear_regression(df, "y", "x")
    assert isinstance(result, RegressionResult)
    assert result.test_type == "linear"
    assert 0 <= result.r_squared <= 1
    assert len(result.coef_table) == 2


def test_multiple_regression_basic():
    """多元回归基本测试"""
    np.random.seed(42)
    n = 100
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(0, 1, n)
    y = 2 * x1 + 1.5 * x2 + np.random.normal(0, 1, n)
    df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})
    result = multiple_regression(df, "y", ["x1", "x2"])
    assert isinstance(result, RegressionResult)
    assert result.test_type == "multiple"
    assert 0 <= result.r_squared <= 1
    assert result.vif_table is not None


def test_hierarchical_regression_basic():
    """层次回归基本测试"""
    np.random.seed(42)
    n = 100
    age = np.random.normal(30, 5, n)
    anxiety = np.random.normal(10, 3, n)
    stress = np.random.normal(15, 4, n)
    y = 50 + 0.1 * age + 0.5 * anxiety + 0.3 * stress + np.random.normal(0, 5, n)
    df = pd.DataFrame({"age": age, "anxiety": anxiety, "stress": stress, "wellbeing": y})
    result = hierarchical_regression(
        df, "wellbeing",
        [["age"], ["anxiety", "stress"]],
    )
    assert isinstance(result, RegressionResult)
    assert result.test_type == "hierarchical"
    assert result.block_tests is not None
    assert len(result.block_tests) == 2
