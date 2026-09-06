"""two_way_anova 假设产出与假设集注册的定向测试（101f 漂移修复验收）。"""

import numpy as np
import pandas as pd
import pytest

from src.analysis import assumption_router, runner
from src.parser.intent_resolver import AnalysisPlan


def _plan():
    return AnalysisPlan(
        test_type="two_way_anova",
        dependent_vars=["y"],
        independent_vars=["a", "b"],
    )


def _df(hetero: bool, n_per_cell=30):
    """2×2 设计：hetero=True 时 (a1,b1) 单元格方差是其余的 9 倍。"""
    rng = np.random.default_rng(42)
    rows = []
    for a in ("a1", "a2"):
        for b in ("b1", "b2"):
            sd = 3.0 if (hetero and a == "a1" and b == "b1") else 1.0
            vals = rng.normal(0, sd, n_per_cell)
            rows += [{"a": a, "b": b, "y": v} for v in vals]
    return pd.DataFrame(rows)


def test_two_way_anova_reports_cell_homogeneity():
    out = runner.run_analysis(_df(hetero=True), _plan())
    hom = out["assumptions"].get("homogeneity")
    assert hom is not None, "双因素 ANOVA 应产出 Levene 齐性结果"
    assert hom["passed"] is False
    assert 0.0 <= hom["p_value"] <= 1.0


def test_two_way_anova_homogeneity_passes_on_equal_var():
    out = runner.run_analysis(_df(hetero=False), _plan())
    hom = out["assumptions"].get("homogeneity")
    assert hom is not None
    assert hom["passed"] is True


def test_two_way_anova_singleton_cell_does_not_crash():
    df = _df(hetero=False)
    df.loc[df.index[-1], "y"] = np.nan  # 制造一个 n=1 单元格
    out = runner.run_analysis(df, _plan())
    assert out["errors"] == [] or all(e.get("severity") != "error" for e in out["errors"])


def test_check_route_on_two_way_output_is_advisory_only():
    out = runner.run_analysis(_df(hetero=True), _plan())
    decision = assumption_router.check_route(_df(hetero=True), _plan(), out)
    assert decision.original_test == "two_way_anova"
    # 双因素无非参数等价：不提供一键切换建议（避免误路由到单因素 Welch/KW）
    assert decision.suggested_test is None


def test_two_way_anova_assumption_set_registered():
    aset = assumption_router.get_assumption_set("two_way_anova")
    assert aset is not None
    names = {a.check_name for a in aset.existing_checks}
    assert {"check_normality", "check_homogeneity"} <= names
    assert len(aset.placeholders) == 2
