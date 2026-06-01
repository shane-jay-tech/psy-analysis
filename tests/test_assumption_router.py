"""Phase 1.3：假设违反路由仲裁器测试。"""

import pandas as pd
import numpy as np
import pytest

from src.analysis import assumption_router
from src.analysis.assumptions import AssumptionResult
from src.parser.intent_resolver import AnalysisPlan


def _plan(test_type, dvs=None, ivs=None):
    return AnalysisPlan(
        test_type=test_type,
        dependent_vars=dvs or ["dv"],
        independent_vars=ivs or ["iv"],
    )


def _failed(name="Shapiro-Wilk"):
    return AssumptionResult(
        test_name=name, statistic=0.85, p_value=0.001,
        passed=False, message_zh="不正态", suggested_action="改非参",
    )


def _passed(name="Shapiro-Wilk"):
    return AssumptionResult(
        test_name=name, statistic=0.99, p_value=0.5,
        passed=True, message_zh="正态", suggested_action="",
    )


def _make_df(n=100):
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "dv": rng.normal(0, 1, n),
        "iv": rng.choice(["A", "B"], n),
    })


class TestRouteSuggestion:
    def test_normality_violated_for_independent_ttest_suggests_mann_whitney(self):
        df = _make_df(60)
        plan = _plan("independent_ttest")
        output = {
            "assumptions": {"normality": {"A": _failed(), "B": _passed()}},
            "test_type": "independent_ttest",
            "descriptive": pd.DataFrame({"组别": ["A", "B"], "N": [30, 30]}),
        }
        d = assumption_router.check_route(df, plan, output)
        assert d.suggested_test == "mann_whitney"
        assert "normality" in d.violated_assumptions
        assert d.has_suggestion

    def test_homogeneity_violated_for_oneway_anova_suggests_welch(self):
        df = _make_df(60)
        plan = _plan("one_way_anova")
        output = {
            "assumptions": {
                "homogeneity": _failed("Levene"),
            },
            "test_type": "one_way_anova",
            "descriptive": pd.DataFrame({"组别": ["A", "B"], "N": [30, 30]}),
        }
        d = assumption_router.check_route(df, plan, output)
        assert d.suggested_test == "welch_anova"
        assert "homogeneity" in d.violated_assumptions

    def test_no_violation_no_suggestion(self):
        df = _make_df(60)
        plan = _plan("independent_ttest")
        output = {
            "assumptions": {"normality": {"A": _passed(), "B": _passed()}},
            "test_type": "independent_ttest",
            "descriptive": pd.DataFrame({"组别": ["A", "B"], "N": [30, 30]}),
        }
        d = assumption_router.check_route(df, plan, output)
        assert not d.has_suggestion
        assert d.violated_assumptions == []

    def test_paired_ttest_suggests_wilcoxon(self):
        df = _make_df(60)
        plan = _plan("paired_ttest", dvs=["pre", "post"])
        # paired 的 normality 在 result 里，这里模拟 assumptions dict 中的 normality
        output = {
            "assumptions": {"normality": _failed()},
            "test_type": "paired_ttest",
            "descriptive": pd.DataFrame({"N": [30, 30]}),
        }
        d = assumption_router.check_route(df, plan, output)
        assert d.suggested_test == "wilcoxon"


class TestHardRouteGuards:
    def test_small_sample_disables_hard_route(self):
        df = _make_df(15)
        plan = _plan("independent_ttest")
        output = {
            "assumptions": {"normality": {"A": _failed()}},
            "test_type": "independent_ttest",
            "descriptive": pd.DataFrame({"组别": ["A"], "N": [15]}),
        }
        d = assumption_router.check_route(df, plan, output)
        assert d.hard_route_allowed is False
        assert "样本量过小" in d.hard_route_reason

    def test_large_sample_disables_hard_route(self):
        df = _make_df(6000)
        plan = _plan("independent_ttest")
        output = {
            "assumptions": {"normality": {"A": _failed()}},
            "test_type": "independent_ttest",
            "descriptive": pd.DataFrame({"组别": ["A"], "N": [6000]}),
        }
        d = assumption_router.check_route(df, plan, output)
        assert d.hard_route_allowed is False
        assert "过大" in d.hard_route_reason

    def test_normal_sample_allows_hard_route(self):
        df = _make_df(100)
        plan = _plan("independent_ttest")
        output = {
            "assumptions": {"normality": {"A": _failed(), "B": _passed()}},
            "test_type": "independent_ttest",
            "descriptive": pd.DataFrame({"组别": ["A", "B"], "N": [50, 50]}),
        }
        d = assumption_router.check_route(df, plan, output)
        assert d.hard_route_allowed is True


class TestRouteToDict:
    def test_to_dict_serializable(self):
        df = _make_df(60)
        plan = _plan("independent_ttest")
        output = {
            "assumptions": {"normality": {"A": _failed()}},
            "test_type": "independent_ttest",
            "descriptive": pd.DataFrame({"组别": ["A"], "N": [30]}),
        }
        d = assumption_router.check_route(df, plan, output)
        out = assumption_router.to_dict(d)
        assert isinstance(out, dict)
        assert out["original_test"] == "independent_ttest"
        assert out["suggested_test"] == "mann_whitney"
        # 必须是 JSON 友好（无 numpy/pandas 对象）
        import json
        json.dumps(out)


class TestRoutingNoSilentSwitch:
    """关键设计：路由器只输出建议，绝不修改 effective test_type。"""

    def test_router_does_not_mutate_output_test_type(self):
        df = _make_df(60)
        plan = _plan("independent_ttest")
        output = {
            "assumptions": {"normality": {"A": _failed()}},
            "test_type": "independent_ttest",
            "descriptive": pd.DataFrame({"组别": ["A"], "N": [30]}),
        }
        before = dict(output)
        assumption_router.check_route(df, plan, output)
        # 路由器只返回 RouteDecision，不应碰 output 的核心字段
        assert output["test_type"] == before["test_type"]
        assert output["assumptions"] is before["assumptions"]
