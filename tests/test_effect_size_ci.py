"""Phase 1.3：效应量 CI 测试。

Fisher-z（Pearson/Spearman）+ 非中心 χ²（Cramer's V / Cohen's w）。
"""

import numpy as np
import pandas as pd

from src.analysis import effect_size_ci
from src.analysis.chi_square import chi_square_independence, chi_square_gof
from src.analysis.correlation import correlation_matrix


class TestFisherZ:
    def test_zero_correlation_ci_straddles_zero(self):
        lo, hi = effect_size_ci.fisher_z_ci(r=0.0, n=100)
        assert lo < 0 < hi

    def test_strong_correlation_ci_excludes_zero(self):
        lo, hi = effect_size_ci.fisher_z_ci(r=0.7, n=100)
        assert lo > 0 and hi > 0
        assert lo < 0.7 < hi

    def test_small_n_returns_none(self):
        lo, hi = effect_size_ci.fisher_z_ci(r=0.5, n=3)
        assert lo is None and hi is None

    def test_invalid_r_returns_none(self):
        lo, hi = effect_size_ci.fisher_z_ci(r=float("nan"), n=100)
        assert lo is None and hi is None

    def test_ci_widens_at_smaller_n(self):
        lo_big, hi_big = effect_size_ci.fisher_z_ci(r=0.3, n=500)
        lo_small, hi_small = effect_size_ci.fisher_z_ci(r=0.3, n=30)
        assert (hi_small - lo_small) > (hi_big - lo_big)


class TestChiSquareCI:
    def test_chi_square_v_ci_returns_valid_range(self):
        # 2x2 列联表，强效应
        lo, hi = effect_size_ci.chi_square_v_ci(
            chi_sq=20.0, df=1, n=100, k_min=1
        )
        assert lo is not None and hi is not None
        assert 0 <= lo <= hi <= 1

    def test_chi_square_w_ci_for_gof(self):
        lo, hi = effect_size_ci.chi_square_w_ci(chi_sq=15.0, df=3, n=100)
        assert lo is not None and hi is not None
        assert 0 <= lo <= hi

    def test_chi_square_zero_ci_truncated_to_zero(self):
        lo, hi = effect_size_ci.chi_square_v_ci(
            chi_sq=0.01, df=1, n=100, k_min=1
        )
        assert lo == 0.0 or lo is None


class TestCorrelationMatrixCI:
    def test_correlation_matrix_now_has_ci(self):
        rng = np.random.default_rng(7)
        df = pd.DataFrame({
            "x": rng.normal(0, 1, 100),
            "y": rng.normal(0, 1, 100),
            "z": rng.normal(0, 1, 100),
        })
        result = correlation_matrix(df, ["x", "y", "z"], method="pearson")
        assert result.ci_low_matrix is not None
        assert result.ci_high_matrix is not None
        # 对角线为 1
        assert result.ci_low_matrix.loc["x", "x"] == 1.0
        # 非对角线 lo <= corr <= hi
        for i in ["x", "y", "z"]:
            for j in ["x", "y", "z"]:
                if i == j:
                    continue
                r_val = result.corr_matrix.loc[i, j]
                lo = result.ci_low_matrix.loc[i, j]
                hi = result.ci_high_matrix.loc[i, j]
                if pd.notna(r_val) and pd.notna(lo):
                    assert lo - 0.001 <= r_val <= hi + 0.001


class TestChiSquareResultCI:
    def test_chi_square_independence_now_has_ci(self):
        # 模拟 200 行 2x2 表，有显著关联
        rng = np.random.default_rng(11)
        df = pd.DataFrame({
            "x": rng.choice(["A", "B"], 200, p=[0.3, 0.7]),
        })
        # 让 y 和 x 相关
        df["y"] = df["x"].apply(
            lambda v: rng.choice([0, 1], p=[0.2, 0.8] if v == "A" else [0.7, 0.3])
        )
        result = chi_square_independence(df, "x", "y")
        assert result.effect_size_ci_lower is not None
        assert result.effect_size_ci_upper is not None
        assert 0 <= result.effect_size_ci_lower <= result.effect_size_ci_upper

    def test_chi_square_gof_now_has_ci(self):
        df = pd.DataFrame({
            "cat": ["A"] * 30 + ["B"] * 25 + ["C"] * 45,
        })
        result = chi_square_gof(df, "cat")
        assert result.effect_size_ci_lower is not None
        assert result.effect_size_ci_upper is not None
