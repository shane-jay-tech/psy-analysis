# -*- coding: utf-8 -*-
"""特征测试（characterization tests）第二包：sem.py 与 advanced.py 红线。

红线编号见 docs/optimization/2026-09-04/02-psy-analysis-优化方案.md 第 6 节：
  ◆3 sem.py R² 分母错误（用观测题目均值的方差，而非模型隐含的潜变量方差）
  ◆4 间接效应只报 a×b，无任何显著性检验（无 SE / CI / p）
  ◆5 advanced.py 中介 bootstrap 失败路径置零：失败样本混入 CI，全失败时输出
     NaN 却判定「不显著」（应为「无法计算」）

CHARACTERIZATION：断言固化"现状"，不是"正确值"。日间修复红线后应人工更新
期望值；本文件的 diff 即行为变化清单。数据固定 RandomState(42)，离线确定性。
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.sem import structural_equation_model
from src.analysis.advanced import mediation_analysis

N = 200


def _make_sem_df():
    rng = np.random.RandomState(42)
    se = rng.normal(0, 1, N)
    anx = 0.6 * se + rng.normal(0, 0.8, N)
    lon = 0.4 * anx + 0.2 * se + rng.normal(0, 0.9, N)
    return pd.DataFrame({
        "SE1": se + rng.normal(0, .3, N), "SE2": se + rng.normal(0, .3, N), "SE3": se + rng.normal(0, .3, N),
        "ANX1": anx + rng.normal(0, .3, N), "ANX2": anx + rng.normal(0, .3, N), "ANX3": anx + rng.normal(0, .3, N),
        "LON1": lon + rng.normal(0, .3, N), "LON2": lon + rng.normal(0, .3, N), "LON3": lon + rng.normal(0, .3, N),
    })


SEM_MM = {"自尊": ["SE1", "SE2", "SE3"],
          "焦虑": ["ANX1", "ANX2", "ANX3"],
          "孤独": ["LON1", "LON2", "LON3"]}


@pytest.fixture(scope="module")
def sem_result():
    return structural_equation_model(
        _make_sem_df(), SEM_MM, ["焦虑 ~ 自尊", "孤独 ~ 焦虑 + 自尊"])


class TestRedline3RSquared:
    """◆3 R² 分母：观测题目均值方差（当前实现），修复后这些值会变。"""

    def test_r2_pinned_current_values(self, sem_result):
        assert sem_result.r_squared == {"焦虑": 0.361, "孤独": 0.245}


class TestRedline4IndirectNoTest:
    """◆4 间接效应无检验：结果表只有 a/b/a×b 三列，无 SE、无 CI、无 p。"""

    def test_indirect_table_has_no_significance_columns(self, sem_result):
        ie = sem_result.indirect_effects
        assert ie is not None
        assert list(ie.columns) == ["路径", "a (X→M)", "b (M→Y)", "间接效应 (a×b)"]

    def test_indirect_value_pinned(self, sem_result):
        rows = sem_result.indirect_effects.to_dict("records")
        assert rows == [{"路径": "自尊 → 焦虑 → 孤独",
                         "a (X→M)": 0.613, "b (M→Y)": 0.39, "间接效应 (a×b)": 0.239}]


def _make_med_df(y_constant=False, n=150):
    rng = np.random.RandomState(42)
    x = rng.normal(0, 1, n)
    m = 0.5 * x + rng.normal(0, 1, n)
    y = np.full(n, 3.0) if y_constant else 0.4 * m + rng.normal(0, 1, n)
    return pd.DataFrame({"X": x, "M": m, "Y": y})


class TestRedline5MediationBootstrap:
    """◆5 bootstrap 失败路径：失败置 0/NaN 混入区间，全失败时误判「不显著」。"""

    def test_normal_run_pinned(self):
        r = mediation_analysis(_make_med_df(), "X", "M", "Y",
                               n_bootstrap=50, seed=42)
        ci = r.bootstrap_ci.iloc[0].to_dict()
        assert ci["β"] == pytest.approx(0.184, abs=1e-3)
        assert ci["CI下限"] == pytest.approx(0.117, abs=1e-3)
        assert ci["CI上限"] == pytest.approx(0.252, abs=1e-3)
        assert ci["Bootstrap n"] == 50
        assert ci["判断"] == "✅ 显著"

    def test_all_bootstraps_fail_yields_nan_but_reports_not_significant(self):
        """失败注入：Y 恒定 → 每次 OLS 退化 → CI 全 NaN，现状仍输出「⚠ 不显著」。

        期望日间修复后：应判定「无法计算」并给出错误说明，而非「不显著」。"""
        r = mediation_analysis(_make_med_df(y_constant=True), "X", "M", "Y",
                               n_bootstrap=30, seed=42)
        ci = r.bootstrap_ci.iloc[0].to_dict()
        assert np.isnan(ci["CI下限"]) and np.isnan(ci["CI上限"])
        assert ci["判断"] == "⚠ 不显著"
        summary = {row["指标"]: row["值"] for row in r.model_summary.to_dict("records")}
        assert np.isnan(summary["总间接效应"])
