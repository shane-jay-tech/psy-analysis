"""方法推荐向导规则引擎测试。

验证 12+ 高频研究场景的推荐准确性、假设违反降级、样本量警告等。
"""

import pytest

from src.analysis.method_recommender import (
    MethodRecommendation,
    ResearchDesignInput,
    recommend_method,
)


class TestTwoGroupDifference:
    """两独立组 + 连续因变量。"""

    def test_default_recommends_ttest(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=2
        )
        rec = recommend_method(d)
        assert rec.primary_method == "independent_ttest"
        assert rec.primary_method_zh == "独立样本 t 检验"
        assert rec.confidence == "high"

    def test_violated_assumptions_recommends_mann_whitney(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent",
            n_groups=2, assumptions_met="violated"
        )
        rec = recommend_method(d)
        assert rec.primary_method == "mann_whitney"

    def test_has_alternative_methods(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=2
        )
        rec = recommend_method(d)
        alt_methods = [a["method"] for a in rec.alternative_methods]
        assert "mann_whitney" in alt_methods
        assert "welch_ttest" in alt_methods

    def test_has_rejected_methods(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=2
        )
        rec = recommend_method(d)
        rej_methods = [r["method"] for r in rec.rejected_methods]
        assert "chi_square" in rej_methods


class TestPairedDifference:
    """配对/前后测。"""

    def test_default_recommends_paired_ttest(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            sample_relation="paired", time_points=2
        )
        rec = recommend_method(d)
        assert rec.primary_method == "paired_ttest"

    def test_violated_recommends_wilcoxon(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            sample_relation="paired", time_points=2, assumptions_met="violated"
        )
        rec = recommend_method(d)
        assert rec.primary_method == "wilcoxon"


class TestMultiGroupDifference:
    """三组及以上。"""

    def test_three_groups_recommends_anova(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=3
        )
        rec = recommend_method(d)
        assert rec.primary_method == "one_way_anova"

    def test_four_groups_recommends_anova(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=4
        )
        rec = recommend_method(d)
        assert rec.primary_method == "one_way_anova"

    def test_violated_recommends_kruskal(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent",
            n_groups=3, assumptions_met="violated"
        )
        rec = recommend_method(d)
        assert rec.primary_method == "kruskal_wallis"

    def test_rejects_ttest_for_multiple_groups(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=3
        )
        rec = recommend_method(d)
        rej_methods = [r["method"] for r in rec.rejected_methods]
        assert "independent_ttest" in rej_methods


class TestRepeatedMeasures:
    """重复测量。"""

    def test_three_timepoints_recommends_repeated_anova(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            sample_relation="repeated", time_points=3
        )
        rec = recommend_method(d)
        assert rec.primary_method == "repeated_anova"

    def test_has_sphericity_check(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            sample_relation="repeated", time_points=4
        )
        rec = recommend_method(d)
        assert any("球形" in c or "Mauchly" in c for c in rec.assumption_checks)


class TestCorrelation:
    """相关分析。"""

    def test_default_recommends_pearson(self):
        d = ResearchDesignInput(purpose="correlation", dv_type="continuous")
        rec = recommend_method(d)
        assert rec.primary_method == "pearson_corr"

    def test_violated_recommends_spearman(self):
        d = ResearchDesignInput(
            purpose="correlation", dv_type="continuous", assumptions_met="violated"
        )
        rec = recommend_method(d)
        assert rec.primary_method == "spearman_corr"


class TestPrediction:
    """预测/回归。"""

    def test_continuous_dv_recommends_regression(self):
        d = ResearchDesignInput(purpose="prediction", dv_type="continuous")
        rec = recommend_method(d)
        assert rec.primary_method == "multiple_regression"

    def test_binary_dv_recommends_logistic(self):
        d = ResearchDesignInput(purpose="prediction", dv_type="binary")
        rec = recommend_method(d)
        assert rec.primary_method == "binary_logistic"


class TestMediation:
    """中介效应。"""

    def test_recommends_mediation(self):
        d = ResearchDesignInput(purpose="mediation")
        rec = recommend_method(d)
        assert rec.primary_method == "mediation"
        assert "自变量 X" in rec.required_variables[0]

    def test_has_causal_warning(self):
        d = ResearchDesignInput(purpose="mediation")
        rec = recommend_method(d)
        assert any("因果" in w or "横断面" in w for w in rec.warnings)


class TestModeration:
    """调节效应。"""

    def test_recommends_moderation(self):
        d = ResearchDesignInput(purpose="moderation")
        rec = recommend_method(d)
        assert rec.primary_method == "moderation"


class TestReliability:
    """信度分析。"""

    def test_recommends_cronbach(self):
        d = ResearchDesignInput(purpose="reliability")
        rec = recommend_method(d)
        assert rec.primary_method == "cronbach_alpha"

    def test_has_likert_assumption(self):
        d = ResearchDesignInput(purpose="reliability")
        rec = recommend_method(d)
        assert any("Likert" in c for c in rec.assumption_checks)


class TestChiSquare:
    """卡方检验。"""

    def test_binary_dv_categorical_iv(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="binary", iv_type="categorical"
        )
        rec = recommend_method(d)
        assert rec.primary_method == "chi_square_independence"

    def test_ordinal_dv_categorical_iv(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="ordinal", iv_type="categorical"
        )
        rec = recommend_method(d)
        assert rec.primary_method == "chi_square_independence"


class TestANCOVA:
    """协方差分析。"""

    def test_covariate_triggers_ancova(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent",
            n_groups=2, has_covariate=True
        )
        rec = recommend_method(d)
        assert rec.primary_method == "ancova"


class TestSampleSizeWarnings:
    """样本量相关警告。"""

    def test_small_sample_warning(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent",
            n_groups=2, sample_size=20
        )
        rec = recommend_method(d)
        assert any("偏小" in w for w in rec.warnings)

    def test_very_small_sample_mediation_low_confidence(self):
        d = ResearchDesignInput(purpose="mediation", sample_size=15)
        rec = recommend_method(d)
        assert rec.confidence == "low"
        assert any("50" in w for w in rec.warnings)

    def test_no_warning_when_size_not_provided(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent",
            n_groups=2, sample_size=0
        )
        rec = recommend_method(d)
        assert not any("偏小" in w for w in rec.warnings)


class TestFallback:
    """无法匹配时的兜底。"""

    def test_empty_design_falls_back(self):
        d = ResearchDesignInput()
        rec = recommend_method(d)
        assert rec.primary_method == "descriptive"
        assert rec.confidence == "low"

    def test_unknown_purpose_falls_back(self):
        d = ResearchDesignInput(purpose="something_exotic")
        rec = recommend_method(d)
        assert rec.primary_method == "descriptive"


class TestRecommendationStructure:
    """推荐结果结构完整性。"""

    def test_all_fields_present(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=2
        )
        rec = recommend_method(d)
        assert rec.primary_method
        assert rec.primary_method_zh
        assert rec.alternative_methods
        assert rec.rejected_methods
        assert rec.required_variables
        assert rec.assumption_checks
        assert rec.explanation
        assert rec.next_action
        assert rec.confidence in ("high", "medium", "low")

    def test_alternative_methods_have_reason(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=2
        )
        rec = recommend_method(d)
        for alt in rec.alternative_methods:
            assert "method" in alt
            assert "reason" in alt

    def test_rejected_methods_have_reason(self):
        d = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=2
        )
        rec = recommend_method(d)
        for rej in rec.rejected_methods:
            assert "method" in rej
            assert "reason" in rej
