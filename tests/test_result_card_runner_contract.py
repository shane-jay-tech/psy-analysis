"""结果卡 runner 合同测试 — 验证 10 种方法的 build_card_from_output 能正确工作。

每种方法用真实 runner 输出格式构造输入，确保：
- 能生成 AnalysisResultCard
- APA 文本非空
- 缺失字段不崩溃（给 warning）
- to_markdown() 可用
"""

import pytest
from dataclasses import dataclass
from typing import Optional

from src.analysis.result_card import AnalysisResultCard, build_card_from_output


# ---------------------------------------------------------------------------
# Fixtures: 模拟 runner 输出对象
# ---------------------------------------------------------------------------

@dataclass
class MockTTestResult:
    t_statistic: float = 2.45
    p_value: float = 0.018
    df: float = 58.0
    cohens_d: float = 0.63


@dataclass
class MockAnovaResult:
    f_statistic: float = 4.82
    p_value: float = 0.012
    df_between: float = 2.0
    df_within: float = 57.0
    eta_squared: float = 0.14


@dataclass
class MockCorrResult:
    r: float = -0.42
    p_value: float = 0.001
    n: int = 60


@dataclass
class MockRegressionResult:
    r_squared: float = 0.35
    adj_r_squared: float = 0.33
    f_statistic: float = 15.4
    p_value: float = 0.0001


@dataclass
class MockRepeatedAnovaResult:
    f_statistic: float = 8.72
    p_value: float = 0.001
    eta_squared: float = 0.13
    epsilon: float = 0.82


@dataclass
class MockMediationResult:
    indirect_effect: float = 0.15
    direct_effect: float = 0.30
    total_effect: float = 0.45
    ci_lower: float = 0.05
    ci_upper: float = 0.28


@dataclass
class MockModerationResult:
    interaction_b: float = 0.24
    interaction_p: float = 0.03
    r2_change: float = 0.04


@dataclass
class MockCronbachResult:
    alpha: float = 0.85
    n_items: int = 10
    item_total_correlations: Optional[list] = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestResultCardRunnerContract:
    """10 种方法的 runner 合同测试。"""

    def test_descriptive(self):
        output = {
            "test_type": "descriptive",
            "test_name_zh": "描述统计",
            "variables": {"target": "anxiety"},
            "results": {"mean": 3.2, "std": 1.1, "n": 60, "min": 1, "max": 5,
                        "skewness": 0.1, "kurtosis": -0.3},
        }
        card = build_card_from_output(output)
        assert card.method_id == "descriptive"
        assert card.apa_text
        assert card.to_markdown()

    def test_independent_ttest(self):
        output = {
            "test_type": "independent_ttest",
            "test_name_zh": "独立样本 t 检验",
            "result": MockTTestResult(),
        }
        card = build_card_from_output(output)
        assert card.method_id == "independent_ttest"
        assert "t" in card.apa_text.lower() or "t(" in card.apa_text
        assert card.effect_sizes
        assert card.plain_language_summary

    def test_paired_ttest(self):
        output = {
            "test_type": "paired_ttest",
            "test_name_zh": "配对样本 t 检验",
            "result": MockTTestResult(t_statistic=3.1, p_value=0.003, df=29, cohens_d=0.57),
        }
        card = build_card_from_output(output)
        assert card.method_id == "paired_ttest"
        assert "配对" in card.apa_text
        assert card.effect_sizes

    def test_one_way_anova(self):
        output = {
            "test_type": "one_way_anova",
            "test_name_zh": "单因素方差分析",
            "result": MockAnovaResult(),
        }
        card = build_card_from_output(output)
        assert card.method_id == "one_way_anova"
        assert "F" in card.apa_text
        assert any(e["name"] == "η²" for e in card.effect_sizes)

    def test_pearson_corr(self):
        output = {
            "test_type": "pearson_corr",
            "test_name_zh": "Pearson 相关",
            "result": MockCorrResult(),
        }
        card = build_card_from_output(output)
        assert card.method_id == "pearson_corr"
        assert "r" in card.apa_text.lower()
        assert any(e["name"] == "r" for e in card.effect_sizes)

    def test_multiple_regression(self):
        output = {
            "test_type": "multiple_regression",
            "test_name_zh": "多元线性回归",
            "result": MockRegressionResult(),
        }
        card = build_card_from_output(output)
        assert card.method_id == "multiple_regression"
        assert "R²" in card.apa_text
        assert any(e["name"] == "R²" for e in card.effect_sizes)
        assert card.plain_language_summary

    def test_repeated_anova(self):
        output = {
            "test_type": "repeated_anova",
            "test_name_zh": "重复测量方差分析",
            "result": MockRepeatedAnovaResult(),
        }
        card = build_card_from_output(output)
        assert card.method_id == "repeated_anova"
        assert "重复测量" in card.apa_text
        assert any("η²" in e["name"] for e in card.effect_sizes)

    def test_mediation(self):
        output = {
            "test_type": "mediation",
            "test_name_zh": "中介效应分析",
            "result": MockMediationResult(),
        }
        card = build_card_from_output(output)
        assert card.method_id == "mediation"
        assert "中介" in card.apa_text
        assert "间接效应" in card.apa_text
        assert card.effect_sizes

    def test_moderation(self):
        output = {
            "test_type": "moderation",
            "test_name_zh": "调节效应分析",
            "result": MockModerationResult(),
        }
        card = build_card_from_output(output)
        assert card.method_id == "moderation"
        assert "调节" in card.apa_text
        assert card.effect_sizes

    def test_cronbach_alpha(self):
        output = {
            "test_type": "cronbach_alpha",
            "test_name_zh": "Cronbach's α 信度分析",
            "result": MockCronbachResult(),
        }
        card = build_card_from_output(output)
        assert card.method_id == "cronbach_alpha"
        assert "α" in card.apa_text
        assert any("α" in e["name"] for e in card.effect_sizes)

    # --- 缺失字段容错 ---

    def test_missing_result_gives_warning(self):
        output = {
            "test_type": "independent_ttest",
            "test_name_zh": "独立样本 t 检验",
            "result": None,
        }
        card = build_card_from_output(output)
        assert card.warnings

    def test_unknown_method_gives_warning(self):
        output = {
            "test_type": "unknown_exotic_method",
            "test_name_zh": "未知方法",
        }
        card = build_card_from_output(output)
        assert any("暂无" in w for w in card.warnings)

    def test_all_10_methods_to_markdown(self):
        methods = [
            {"test_type": "descriptive", "test_name_zh": "描述统计",
             "results": {"mean": 3, "std": 1, "n": 60, "min": 1, "max": 5, "skewness": 0, "kurtosis": 0}},
            {"test_type": "independent_ttest", "result": MockTTestResult()},
            {"test_type": "paired_ttest", "result": MockTTestResult()},
            {"test_type": "one_way_anova", "result": MockAnovaResult()},
            {"test_type": "pearson_corr", "result": MockCorrResult()},
            {"test_type": "multiple_regression", "result": MockRegressionResult()},
            {"test_type": "repeated_anova", "result": MockRepeatedAnovaResult()},
            {"test_type": "mediation", "result": MockMediationResult()},
            {"test_type": "moderation", "result": MockModerationResult()},
            {"test_type": "cronbach_alpha", "result": MockCronbachResult()},
        ]
        for m in methods:
            m.setdefault("test_name_zh", m["test_type"])
            card = build_card_from_output(m)
            md = card.to_markdown()
            assert md, f"{m['test_type']} to_markdown() returned empty"
            assert card.method_id == m["test_type"]

    def test_cronbach_low_alpha_warning(self):
        output = {
            "test_type": "cronbach_alpha",
            "test_name_zh": "信度",
            "result": MockCronbachResult(alpha=0.55, n_items=5),
        }
        card = build_card_from_output(output)
        assert any("0.70" in w for w in card.warnings)

    def test_repeated_anova_sphericity_warning(self):
        output = {
            "test_type": "repeated_anova",
            "test_name_zh": "重复测量",
            "result": MockRepeatedAnovaResult(epsilon=0.6),
        }
        card = build_card_from_output(output)
        assert any("球形" in w or "Greenhouse" in w for w in card.warnings)
