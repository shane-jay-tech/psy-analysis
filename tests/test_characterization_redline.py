# -*- coding: utf-8 -*-
"""特征测试（characterization tests）：钉住统计红线函数的当前行为。

红线编号与问题定义见 docs/optimization/2026-09-04/02-psy-analysis-优化方案.md 第 6 节：
  ◆1 independent_ttest 等方差分支的 CI 口径
  ◆2 Cohen's d 的 CI 混合渐近口径（_cohens_d_ci：se_d 近似 + 非中心 t 反解混用）
  ◆6 chi_square_v_ci 的 NCP 边界截断（下界截 0；极小 χ² 时上界亦为 0）
  ◆7 CI 下界 falsy 语义（0.0 与 None 的边界契约）

CHARACTERIZATION：这些断言固化的是"现状"，不是"正确值"。
日间红线修复后应人工更新期望值，并以本文件 diff 作为行为变化清单。

数据：固定 RandomState(42) 合成样本，全部离线、确定性。
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.ttest import independent_ttest, _cohens_d_ci
from src.analysis.effect_size_ci import chi_square_v_ci


@pytest.fixture(scope="module")
def ttest_df():
    rng = np.random.RandomState(42)
    return pd.DataFrame({
        "dv": np.concatenate([rng.normal(50, 10, 30), rng.normal(53, 12, 34)]),
        "iv": ["A"] * 30 + ["B"] * 34,
    })


class TestRedline1EqualVarCI:
    """◆1 等方差分支 CI 口径（含 t/df/CI 全链路）。"""

    def test_equal_var_branch_pinned(self, ttest_df):
        r = independent_ttest(ttest_df, "dv", "iv")
        # Levene p=0.1875 > 0.05 → 走等方差分支（is_welch=False）
        assert r.is_welch is False
        assert r.df == 62.0
        assert r.t_statistic == pytest.approx(-1.013, abs=1e-3)
        assert r.p_value == pytest.approx(0.315, abs=1e-3)
        # 红线 ◆1：合并方差口径的均值差 CI（修复若改为独立方差口径，此值会变）
        assert r.ci_lower == pytest.approx(-7.526, abs=1e-3)
        assert r.ci_upper == pytest.approx(2.423, abs=1e-3)

    def test_equal_var_effect_size_ci_pinned(self, ttest_df):
        """◆2 一并覆盖：effect_size CI 由 _cohens_d_ci（混合渐近）产生。"""
        r = independent_ttest(ttest_df, "dv", "iv")
        assert r.effect_size == pytest.approx(-0.254, abs=1e-3)
        assert r.effect_size_ci_lower == pytest.approx(-0.745, abs=1e-3)
        assert r.effect_size_ci_upper == pytest.approx(0.241, abs=1e-3)


class TestRedline2CohensDCI:
    """◆2 _cohens_d_ci：se_d 用 Hedges-Olkin 近似、搜索轴却用 nct 反解 ncp 的混合口径。"""

    def test_mixed_asymptotic_pinned(self):
        assert _cohens_d_ci(0.35, 30, 34) == (-0.149, 0.841)

    def test_zero_effect_contract(self):
        """◆7 相关契约：零效应时下界非 None 而是 -0.491（0.0 下界不视为缺失）。"""
        assert _cohens_d_ci(0.0, 30, 34) == (-0.491, 0.491)
        assert _cohens_d_ci(0.001, 30, 34) == (-0.49, 0.492)


class TestRedline6NCPTruncation:
    """◆6 NCP 边界截断：下界截 0 是文档行为；极小 χ² 时上界=0 是可疑现状。"""

    def test_naeff_upper_clamped_to_zero(self):
        # χ²=0.05（df=2, n=100, k_min=1）：NCP 上界同样截断为 0 —— 现状可疑，
        # 期望修复后上界 > 0（χ² 再小其上置信界也应为正）。
        assert chi_square_v_ci(0.05, 2, 100, 1) == (0.0, 0.0)

    def test_lower_clamped_to_zero(self):
        # 中等效应：下界截 0（文档声明的行为），上界为正。
        low, high = chi_square_v_ci(6.0, 2, 100, 1)
        assert low == 0.0
        assert high == pytest.approx(0.4253765281097388, abs=1e-9)
