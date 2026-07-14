"""AnalysisResultCard 统计结果卡测试。"""
from dataclasses import dataclass

import pytest

from src.analysis.result_card import (
    AnalysisResultCard,
    build_card_from_output,
)


@dataclass
class _MockTTestResult:
    t_statistic: float = 2.45
    p_value: float = 0.016
    df: float = 98
    cohens_d: float = 0.49


@dataclass
class _MockAnovaResult:
    f_statistic: float = 4.32
    p_value: float = 0.015
    df_between: float = 2
    df_within: float = 97
    eta_squared: float = 0.082


@dataclass
class _MockCorrResult:
    r: float = 0.52
    p_value: float = 0.001
    n: int = 100


class _MockPlan:
    def __init__(self, test_type, dependent_vars=None, independent_vars=None):
        self.test_type = test_type
        self.dependent_vars = dependent_vars or []
        self.independent_vars = independent_vars or []
        self.covariates = []


class TestAnalysisResultCard:
    def test_basic_creation(self):
        card = AnalysisResultCard(
            method_id="independent_ttest",
            method_name="独立样本t检验",
            variables={"dependent": ["score"], "independent": ["group"]},
        )
        assert card.method_id == "independent_ttest"
        assert card.created_at != ""

    def test_to_markdown(self):
        card = AnalysisResultCard(
            method_id="test",
            method_name="测试方法",
            variables={},
            apa_text="t(98) = 2.45, p = .016",
            plain_language_summary="差异显著",
            effect_sizes=[{"name": "d", "value": 0.49}],
            warnings=["样本量偏小"],
        )
        md = card.to_markdown()
        assert "测试方法" in md
        assert "APA" in md
        assert "d=0.490" in md
        assert "样本量偏小" in md


class TestBuildCardIndependentTtest:
    def test_produces_apa_text(self):
        output = {
            "test_type": "independent_ttest",
            "test_name_zh": "独立样本t检验",
            "plan": _MockPlan("independent_ttest", ["score"], ["group"]),
            "result": _MockTTestResult(),
            "assumptions": {},
        }
        card = build_card_from_output(output)
        assert "t(98)" in card.apa_text
        assert "2.45" in card.apa_text
        assert "0.016" in card.apa_text
        assert "Cohen's d" in card.apa_text
        assert card.effect_sizes[0]["name"] == "Cohen's d"
        assert abs(card.effect_sizes[0]["value"] - 0.49) < 0.01

    def test_significant_result(self):
        output = {
            "test_type": "independent_ttest",
            "test_name_zh": "独立样本t检验",
            "plan": _MockPlan("independent_ttest", ["score"], ["group"]),
            "result": _MockTTestResult(p_value=0.003),
            "assumptions": {},
        }
        card = build_card_from_output(output)
        assert "显著" in card.apa_text
        assert "显著" in card.plain_language_summary

    def test_missing_effect_size_warns(self):
        result = _MockTTestResult()
        result.cohens_d = None
        output = {
            "test_type": "independent_ttest",
            "test_name_zh": "独立样本t检验",
            "plan": _MockPlan("independent_ttest", ["score"], ["group"]),
            "result": result,
            "assumptions": {},
        }
        card = build_card_from_output(output)
        assert any("效应量" in w for w in card.warnings)


class TestBuildCardAnova:
    def test_produces_apa_text(self):
        output = {
            "test_type": "one_way_anova",
            "test_name_zh": "单因素方差分析",
            "plan": _MockPlan("one_way_anova", ["score"], ["condition"]),
            "result": _MockAnovaResult(),
            "assumptions": {},
        }
        card = build_card_from_output(output)
        assert "F(2, 97)" in card.apa_text
        assert "η²" in card.apa_text
        assert card.effect_sizes[0]["name"] == "η²"


class TestBuildCardCorrelation:
    def test_produces_apa_text(self):
        output = {
            "test_type": "pearson_correlation",
            "test_name_zh": "Pearson相关",
            "plan": _MockPlan("pearson_correlation", ["x", "y"]),
            "result": _MockCorrResult(),
            "assumptions": {},
        }
        card = build_card_from_output(output)
        assert "r(98)" in card.apa_text
        assert "0.52" in card.apa_text
        assert len(card.effect_sizes) == 2  # r and r²

    def test_negative_correlation(self):
        result = _MockCorrResult(r=-0.65)
        output = {
            "test_type": "pearson_correlation",
            "test_name_zh": "Pearson相关",
            "plan": _MockPlan("pearson_correlation", ["x", "y"]),
            "result": result,
            "assumptions": {},
        }
        card = build_card_from_output(output)
        assert "负" in card.apa_text or "负" in card.plain_language_summary


class TestBuildCardAssumptions:
    def test_assumption_status_passed(self):
        output = {
            "test_type": "independent_ttest",
            "test_name_zh": "独立样本t检验",
            "plan": _MockPlan("independent_ttest", ["score"], ["group"]),
            "result": _MockTTestResult(),
            "assumptions": {
                "normality": {"passed": True, "detail": "Shapiro-Wilk p > .05"},
                "homogeneity": {"passed": True, "detail": "Levene p > .05"},
            },
        }
        card = build_card_from_output(output)
        assert card.assumption_status == "passed"

    def test_assumption_status_partial(self):
        output = {
            "test_type": "independent_ttest",
            "test_name_zh": "独立样本t检验",
            "plan": _MockPlan("independent_ttest", ["score"], ["group"]),
            "result": _MockTTestResult(),
            "assumptions": {
                "normality": {"passed": True},
                "homogeneity": {"passed": False},
            },
        }
        card = build_card_from_output(output)
        assert card.assumption_status == "partial"


class TestBuildCardUnknownMethod:
    def test_fallback_with_warning(self):
        output = {
            "test_type": "exotic_method",
            "test_name_zh": "奇特方法",
            "plan": _MockPlan("exotic_method"),
            "result": None,
            "assumptions": {},
        }
        card = build_card_from_output(output)
        assert any("暂无" in w for w in card.warnings)
