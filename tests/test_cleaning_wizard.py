"""数据清洗向导测试 — 只测试纯函数部分（清洗动作 + 日志格式化）。

UI 渲染部分依赖 streamlit session_state，留给 e2e/playwright 测试。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ui.cleaning_wizard import (
    CleaningStep, cleaning_log_to_method_paragraph,
    coerce_to_numeric, drop_constant_columns, drop_rows_with_missing,
    impute_mean, impute_median, winsorize_outliers,
)


@pytest.fixture
def dirty_df():
    return pd.DataFrame({
        "age": [20, 21, np.nan, 22, 23, 100],
        "gender": [1, 1, 1, 1, 1, 1],  # 常数列
        "score": [50, np.nan, 70, 80, 90, 95],
    })


def test_drop_rows_with_missing(dirty_df):
    new_df, step = drop_rows_with_missing(dirty_df, ["age"])
    assert len(new_df) == 5  # 删 1 行
    assert step.before_shape == (6, 3)
    assert step.after_shape == (5, 3)
    assert "缺失" in step.description_zh


def test_drop_constant_columns(dirty_df):
    new_df, step = drop_constant_columns(dirty_df, ["gender"])
    assert "gender" not in new_df.columns
    assert step.before_shape == (6, 3)
    assert step.after_shape == (6, 2)


def test_impute_mean_fills_missing(dirty_df):
    new_df, step = impute_mean(dirty_df, ["age"])
    assert new_df["age"].isna().sum() == 0
    # 均值应为 (20+21+22+23+100)/5 = 37.2
    assert new_df.shape == (6, 3)  # 形状不变
    expected_mean = pd.Series([20, 21, 22, 23, 100]).mean()
    assert new_df["age"].iloc[2] == pytest.approx(expected_mean, rel=1e-3)


def test_impute_median_robust_to_outlier(dirty_df):
    """100 是异常值，中位数填补应给一个合理值（不被异常值带偏）。"""
    new_df, step = impute_median(dirty_df, ["age"])
    expected_median = pd.Series([20, 21, 22, 23, 100]).median()
    assert new_df["age"].iloc[2] == pytest.approx(expected_median)
    assert expected_median < 50  # 中位数不应被异常值 100 拉得很高


def test_winsorize_caps_outliers(dirty_df):
    new_df, step = winsorize_outliers(dirty_df, ["age"], k=1.5)
    # age=100 应被压缩
    assert new_df["age"].max() < 100


def test_coerce_to_numeric_handles_strings():
    df = pd.DataFrame({"x": ["1", "2", "abc", "4"]})
    new_df, step = coerce_to_numeric(df, ["x"])
    assert pd.api.types.is_numeric_dtype(new_df["x"])
    assert pd.isna(new_df["x"].iloc[2])  # "abc" -> NaN


def test_cleaning_step_summary_describes_row_change():
    step = CleaningStep(
        action="drop", target_cols=["x"],
        before_shape=(100, 5), after_shape=(95, 5),
        description_zh="删除缺失行",
    )
    assert "5 行" in step.summary() or "5行" in step.summary()


def test_log_to_method_paragraph_empty():
    assert cleaning_log_to_method_paragraph([]) == ""


def test_high_missing_rate_triggers_complex_scenario():
    """v2.8: 缺失率 >10% 应判为复杂场景。"""
    from src.analysis.data_quality import data_quality_check
    from src.ui.cleaning_wizard import is_complex_missing_scenario

    # 30% 缺失（高）
    df_high = pd.DataFrame({
        "x": [1, 2, np.nan, np.nan, np.nan, 6, 7, 8, 9, 10],
        "y": [10, np.nan, 30, np.nan, 50, np.nan, 70, 80, 90, 100],
    })
    report = data_quality_check(df_high, numeric_cols=["x", "y"])
    assert report.missing_pct > 10
    assert is_complex_missing_scenario(report) is True


def test_low_missing_rate_not_complex():
    """v2.8: 缺失率 <10% 应判为非复杂场景。"""
    from src.analysis.data_quality import data_quality_check
    from src.ui.cleaning_wizard import is_complex_missing_scenario

    df_low = pd.DataFrame({
        "x": list(range(100)),
        "y": [np.nan if i < 5 else i for i in range(100)],  # 2.5% 缺失
    })
    report = data_quality_check(df_low, numeric_cols=["x", "y"])
    assert report.missing_pct < 10
    assert is_complex_missing_scenario(report) is False


def test_no_missing_not_complex():
    from src.analysis.data_quality import data_quality_check
    from src.ui.cleaning_wizard import is_complex_missing_scenario
    df_clean = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    report = data_quality_check(df_clean, numeric_cols=["x", "y"])
    assert is_complex_missing_scenario(report) is False


def test_log_to_method_paragraph_with_steps():
    log = [
        CleaningStep(
            action="drop_const", before_shape=(100, 5), after_shape=(100, 4),
            description_zh="删除常数列 gender",
        ),
        CleaningStep(
            action="drop_missing", before_shape=(100, 4), after_shape=(95, 4),
            description_zh="删除缺失行",
        ),
    ]
    para = cleaning_log_to_method_paragraph(log)
    assert "预处理" in para
    assert "(1)" in para and "(2)" in para
    assert "删除常数列" in para
    assert "删除缺失行" in para
