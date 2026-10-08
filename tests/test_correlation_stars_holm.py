"""s1008-01/S2 钉桩：相关矩阵星号 Holm 校正化。

材料：docs/insights/gh-label-corr-stars-20261004.md s1004-55 §三 S2 案
（用户 2026-10-08 拍板三件全落）。阈值零改动：_stars 本体与 s1007-19 S1 版同语义；
矩阵面（correlation_matrix/partial_correlation）打星前做 k(k−1)/2 族内 Holm；
点二列（族大小=1，Holm 恒等）维持单 p 单星。
"""

import numpy as np
import pandas as pd
import pytest

from src.analysis.correlation import (
    _stars,
    _stars_matrix_holm,
    correlation_matrix,
    partial_correlation,
    point_biserial_corr,
)


class TestStarsThresholdsUnchanged:
    def test_thresholds_zero_change(self):
        # 阈值零改动：_stars 本体保持 s1007-19 S1 单源化版语义
        assert _stars(0.0009) == "***"
        assert _stars(0.004) == "**"
        assert _stars(0.03) == "*"
        assert _stars(0.5) == ""
        assert _stars(float("nan")) == ""


class TestStarsMatrixHolm:
    def test_known_family_demotion(self):
        # 族（行主序）＝{(0,1)=0.03, (0,2)=0.20, (1,2)=0.004}
        # Holm 逐序 ×3/×2/×1 → 0.06 / 0.20 / 0.012
        p = pd.DataFrame(
            np.array([[0.0, 0.03, 0.20], [0.03, 0.0, 0.004], [0.20, 0.004, 0.0]])
        )
        sig = _stars_matrix_holm(p)
        assert sig.iloc[0, 1] == ""  # 裸 p=0.03 原打 "*"，Holm 0.06 → ""
        assert sig.iloc[1, 2] == "*"  # 裸 p=0.004 原打 "**"，Holm 0.012 → "*"
        assert sig.iloc[0, 2] == ""
        assert sig.iloc[0, 0] == "***"  # 对角线 p=0 不入族，保原样
        assert sig.iloc[1, 0] == sig.iloc[0, 1]  # 对称

    def test_nan_cells_excluded_and_blank(self):
        p = pd.DataFrame(
            np.array([[0.0, np.nan, 0.01], [np.nan, 0.0, 0.30], [0.01, 0.30, 0.0]])
        )
        sig = _stars_matrix_holm(p)
        assert sig.iloc[0, 1] == ""  # NaN 不入族、不打星
        assert sig.iloc[0, 2] == "*"  # 族=2：Holm 0.01×2=0.02 → "*"
        assert sig.iloc[1, 2] == ""

    def test_single_pair_identity(self):
        # 族大小=1：Holm 恒等（点二列面零变化）
        p = pd.DataFrame(np.array([[0.0, 0.03], [0.03, 0.0]]))
        sig = _stars_matrix_holm(p)
        assert sig.iloc[0, 1] == "*"


class TestMatrixWiring:
    def _fixture(self, n=40, seed=7):
        rng = np.random.default_rng(seed)
        x1 = rng.normal(size=n)
        x2 = 0.9 * x1 + rng.normal(scale=0.2, size=n)  # 与 x1 强相关
        x3 = rng.normal(size=n)  # 独立
        return pd.DataFrame({"x1": x1, "x2": x2, "x3": x3})

    def test_correlation_matrix_mask_equals_holm_helper(self):
        df = self._fixture()
        r = correlation_matrix(df, columns=["x1", "x2", "x3"], method="pearson")
        expected = _stars_matrix_holm(r.p_matrix)
        pd.testing.assert_frame_equal(r.sig_mask, expected)

    def test_strong_pair_survives_holm(self):
        df = self._fixture()
        r = correlation_matrix(df, columns=["x1", "x2", "x3"], method="pearson")
        assert r.p_matrix.iloc[0, 1] < 0.001
        assert r.sig_mask.iloc[0, 1] == "***"  # 强相关族校正后仍满星

    def test_weak_pair_star_is_holm_controlled(self):
        # 3 变量族=3：最小 Holm 乘数=3。裸 p∈(0.05/3, 0.05) 的对裸星 "*" 必被拨掉
        rng = np.random.default_rng(11)
        n = 60
        x1 = rng.normal(size=n)
        x3 = rng.normal(size=n)
        x2 = 0.25 * x1 + np.sqrt(1 - 0.25**2) * rng.normal(size=n)  # ρ≈0.25
        df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3})
        r = correlation_matrix(df, columns=["x1", "x2", "x3"], method="pearson")
        p_weak = float(r.p_matrix.iloc[0, 1])
        if not (0.05 / 3 < p_weak < 0.05):
            pytest.skip("样本未落在 Holm 拨星演示区（语义由 known_family_demotion 钉死）")
        assert r.sig_mask.iloc[0, 1] == ""

    def test_partial_correlation_mask_equals_holm_helper(self):
        df = self._fixture()
        r = partial_correlation(df, columns=["x1", "x2", "x3"], method="pearson")
        expected = _stars_matrix_holm(r.p_matrix)
        pd.testing.assert_frame_equal(r.sig_mask, expected)

    def test_point_biserial_family_one_uncorrected_pin(self):
        # 材料 s1004-55 §一：点二列单 p 单星、族大小=1 无校正问题——维持单 p 打星
        rng = np.random.default_rng(3)
        n = 60
        df = pd.DataFrame(
            {
                "score": np.concatenate(
                    [rng.normal(0, 1, n), rng.normal(0.8, 1, n)]
                ),
                "flag": ["A"] * n + ["B"] * n,
            }
        )
        r = point_biserial_corr(df, "score", "flag")
        p_raw = float(r.p_matrix.iloc[0, 1])
        assert r.sig_mask.iloc[0, 1] == _stars(p_raw)


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
