# -*- coding: utf-8 -*-
"""s1007-26 sem/卡方两族 existing 覆盖断言（s927-24 类 I 实装在产、注册表占位缺口面）。

只断言生产行为不改数值：sem 样本量守卫（sem.py:71 n_obs<指标数×5）与
chi_square_independence 小期望频数守卫（chi_square.py:47-52 expected<5）均已在产，
注册表侧仍是 _ph 占位（接线缺口留案①裁决，见 assumption_router 注记）。
"""
import numpy as np
import pandas as pd

from src.analysis.chi_square import chi_square_independence
from src.analysis.sem import structural_equation_model


def test_sem_sample_size_guard_fires():
    """existing 实装断言：n_obs < 指标数×5 时样本量告警在 warnings。"""
    n_obs = 8  # 指标数 3 → 阈值 15，8 < 15 必触发
    df = pd.DataFrame({
        "x1": np.random.default_rng(42).normal(size=n_obs),
        "x2": np.random.default_rng(43).normal(size=n_obs),
        "x3": np.random.default_rng(44).normal(size=n_obs),
    })
    result = structural_equation_model(
        df, measurement_model={"f1": ["x1", "x2", "x3"]},
        structural_paths=["f1"],
    )
    assert any("样本量" in w and "偏小" in w for w in result.warnings), result.warnings


def test_chi_square_low_expected_frequency_guard_fires():
    """existing 实装断言：小期望频数场景告警含 Fisher 建议。"""
    # 不均衡列联表制造 expected<5：一行仅 2 个观测
    df = pd.DataFrame({
        "a": ["x"] * 2 + ["y"] * 60,
        "b": ["p"] * 1 + ["q"] * 1 + ["p"] * 30 + ["q"] * 30,
    })
    res = chi_square_independence(df, "a", "b")
    warning = getattr(res, "warning", "") or "".join(getattr(res, "warnings", []))
    assert "期望频数" in warning and "Fisher" in warning, warning
