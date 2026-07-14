"""P0-1: 新增 10 类结果卡方法测试。

验证 two_way_anova, mixed_anova, ancova, mann_whitney, wilcoxon,
kruskal_wallis, hierarchical_regression, logistic_regression,
mcdonalds_omega, efa 的结果卡构建。
"""

from types import SimpleNamespace

import pytest

from src.analysis.result_card import build_card_from_output, _CARD_BUILDERS


class TestTwoWayAnova:
    def test_builds_card(self):
        output = {
            "test_type": "two_way_anova",
            "result": SimpleNamespace(
                factor_a_f=4.5, factor_a_p=0.02,
                factor_b_f=2.1, factor_b_p=0.15,
                interaction_f=6.3, interaction_p=0.005,
                eta2_a=0.08, eta2_b=0.03, eta2_ab=0.11,
            ),
            "plan": SimpleNamespace(
                dependent_vars=["成绩"],
                independent_vars=["性别", "教学方法"],
                covariates=None,
            ),
        }
        card = build_card_from_output(output)
        assert "双因素方差分析" in card.apa_text
        assert "显著" in card.apa_text
        assert len(card.effect_sizes) >= 2
        assert card.method_id == "two_way_anova"

    def test_interaction_note(self):
        output = {
            "test_type": "two_way_anova",
            "result": SimpleNamespace(
                factor_a_f=1.0, factor_a_p=0.3,
                factor_b_f=1.0, factor_b_p=0.3,
                interaction_f=5.0, interaction_p=0.03,
                eta2_a=None, eta2_b=None, eta2_ab=None,
            ),
        }
        card = build_card_from_output(output)
        assert any("简单效应" in n for n in card.technical_notes)


class TestMixedAnova:
    def test_builds_card(self):
        output = {
            "test_type": "mixed_anova",
            "result": SimpleNamespace(
                between_f=3.2, between_p=0.04,
                within_f=8.7, within_p=0.001,
                interaction_f=2.1, interaction_p=0.08,
                epsilon=0.85,
            ),
            "plan": SimpleNamespace(
                dependent_vars=["焦虑得分"],
                independent_vars=["组别", "时间"],
                covariates=None,
            ),
        }
        card = build_card_from_output(output)
        assert "混合设计" in card.apa_text
        assert "组间" in card.apa_text or "组别" in card.apa_text

    def test_sphericity_warning(self):
        output = {
            "test_type": "mixed_anova",
            "result": SimpleNamespace(
                between_f=3.0, between_p=0.05,
                within_f=5.0, within_p=0.01,
                interaction_f=1.0, interaction_p=0.3,
                epsilon=0.6,
            ),
        }
        card = build_card_from_output(output)
        assert any("球形性" in w for w in card.warnings)


class TestAncova:
    def test_builds_card(self):
        output = {
            "test_type": "ancova",
            "result": SimpleNamespace(
                f_statistic=7.2, p_value=0.008,
                eta_squared=0.12, adjusted_means={"A": 4.2, "B": 3.8},
            ),
            "plan": SimpleNamespace(
                dependent_vars=["成绩"],
                independent_vars=["教学法"],
                covariates=["入学成绩"],
            ),
        }
        card = build_card_from_output(output)
        assert "协方差" in card.apa_text
        assert "入学成绩" in card.apa_text
        assert len(card.effect_sizes) >= 1

    def test_no_result(self):
        output = {"test_type": "ancova", "result": None}
        card = build_card_from_output(output)
        assert any("未产生结果" in w for w in card.warnings)


class TestMannWhitney:
    def test_builds_card(self):
        output = {
            "test_type": "mann_whitney",
            "result": SimpleNamespace(
                u_statistic=245.0, p_value=0.03,
                z_value=-2.15, r_effect=0.35, n1=20, n2=22,
            ),
            "plan": SimpleNamespace(
                dependent_vars=["满意度"],
                independent_vars=["性别"],
                covariates=None,
            ),
        }
        card = build_card_from_output(output)
        assert "Mann-Whitney" in card.apa_text
        assert "U = 245" in card.apa_text
        assert any("非参数" in n for n in card.technical_notes)
        assert len(card.effect_sizes) >= 1


class TestWilcoxon:
    def test_builds_card(self):
        output = {
            "test_type": "wilcoxon",
            "result": SimpleNamespace(
                w_statistic=45.0, p_value=0.02,
                z_value=-2.3, r_effect=0.42, n=30,
            ),
            "plan": SimpleNamespace(
                dependent_vars=["抑郁得分"],
                independent_vars=None,
                covariates=None,
            ),
        }
        card = build_card_from_output(output)
        assert "Wilcoxon" in card.apa_text
        assert "W = 45" in card.apa_text
        assert len(card.effect_sizes) >= 1

    def test_non_significant(self):
        output = {
            "test_type": "wilcoxon",
            "result": SimpleNamespace(
                w_statistic=120.0, p_value=0.45,
                z_value=-0.75, r_effect=0.12, n=25,
            ),
        }
        card = build_card_from_output(output)
        assert "不显著" in card.apa_text


class TestKruskalWallis:
    def test_builds_card(self):
        output = {
            "test_type": "kruskal_wallis",
            "result": SimpleNamespace(
                h_statistic=12.5, p_value=0.002,
                df=3, eta_squared=0.15,
            ),
            "plan": SimpleNamespace(
                dependent_vars=["满意度"],
                independent_vars=["年级"],
                covariates=None,
            ),
        }
        card = build_card_from_output(output)
        assert "Kruskal-Wallis" in card.apa_text
        assert "H(3)" in card.apa_text
        assert any("事后" in n for n in card.technical_notes)

    def test_non_significant(self):
        output = {
            "test_type": "kruskal_wallis",
            "result": SimpleNamespace(
                h_statistic=3.1, p_value=0.21, df=2, eta_squared=0.04,
            ),
        }
        card = build_card_from_output(output)
        assert "不显著" in card.apa_text


class TestHierarchicalRegression:
    def test_builds_with_steps(self):
        output = {
            "test_type": "hierarchical_regression",
            "result": SimpleNamespace(
                steps=[
                    {"r2": 0.15, "delta_r2": 0.15, "f_change": 5.2, "p_change": 0.02},
                    {"r2": 0.28, "delta_r2": 0.13, "f_change": 4.8, "p_change": 0.03},
                ],
                r_squared=0.28, adj_r_squared=0.25,
            ),
            "plan": SimpleNamespace(
                dependent_vars=["学业成绩"],
                independent_vars=["自尊", "焦虑"],
                covariates=None,
            ),
        }
        card = build_card_from_output(output)
        assert "层级回归" in card.apa_text
        assert "ΔR²" in card.apa_text
        assert len(card.effect_sizes) >= 2

    def test_builds_without_steps(self):
        output = {
            "test_type": "hierarchical_regression",
            "result": SimpleNamespace(
                steps=None, r_squared=0.35, adj_r_squared=0.32,
            ),
        }
        card = build_card_from_output(output)
        assert "R²" in card.apa_text


class TestLogisticRegression:
    def test_builds_card(self):
        output = {
            "test_type": "logistic_regression",
            "result": SimpleNamespace(
                chi2=15.3, p_value=0.001,
                pseudo_r2=0.22, accuracy=0.78,
                odds_ratios={"自尊": 1.45, "焦虑": 0.82},
            ),
            "plan": SimpleNamespace(
                dependent_vars=["是否辍学"],
                independent_vars=["自尊", "焦虑"],
                covariates=None,
            ),
        }
        card = build_card_from_output(output)
        assert "Logistic" in card.apa_text
        assert "χ²" in card.apa_text
        assert "78.0%" in card.apa_text
        assert len(card.effect_sizes) >= 1

    def test_no_result(self):
        output = {"test_type": "logistic_regression", "result": None}
        card = build_card_from_output(output)
        assert any("未产生结果" in w for w in card.warnings)


class TestMcdonaldsOmega:
    def test_builds_card(self):
        output = {
            "test_type": "mcdonalds_omega",
            "result": SimpleNamespace(
                omega=0.87, omega_hierarchical=0.72,
                n_items=10, alpha=0.84,
            ),
        }
        card = build_card_from_output(output)
        assert "ω = 0.870" in card.apa_text
        assert "良好" in card.apa_text
        assert len(card.effect_sizes) >= 1

    def test_low_omega_warning(self):
        output = {
            "test_type": "mcdonalds_omega",
            "result": SimpleNamespace(
                omega=0.55, omega_hierarchical=None,
                n_items=6, alpha=None,
            ),
        }
        card = build_card_from_output(output)
        assert any("低于 0.70" in w for w in card.warnings)


class TestEFA:
    def test_builds_card(self):
        output = {
            "test_type": "efa",
            "result": SimpleNamespace(
                kmo=0.85, bartlett_p=0.0001,
                n_factors=3, variance_explained=62.5,
                loadings=[[0.7, 0.1], [0.8, 0.2]],
            ),
        }
        card = build_card_from_output(output)
        assert "EFA" in card.apa_text or "探索性因素" in card.apa_text
        assert "KMO" in card.apa_text
        assert "3" in card.apa_text
        assert len(card.effect_sizes) >= 1

    def test_low_kmo_warning(self):
        output = {
            "test_type": "efa",
            "result": SimpleNamespace(
                kmo=0.45, bartlett_p=0.08,
                n_factors=None, variance_explained=None, loadings=None,
            ),
        }
        card = build_card_from_output(output)
        assert any("KMO" in w for w in card.warnings)
        assert any("Bartlett" in w for w in card.warnings)


class TestCardBuildersRegistry:
    def test_has_at_least_20_methods(self):
        assert len(_CARD_BUILDERS) >= 20

    @pytest.mark.parametrize("method_id", [
        "two_way_anova", "factorial_anova", "mixed_anova", "ancova",
        "mann_whitney", "mann_whitney_u", "wilcoxon", "wilcoxon_signed_rank",
        "kruskal_wallis", "hierarchical_regression", "logistic_regression",
        "binary_logistic", "mcdonalds_omega", "omega", "efa",
        "exploratory_factor_analysis",
    ])
    def test_new_method_registered(self, method_id):
        assert method_id in _CARD_BUILDERS

    @pytest.mark.parametrize("method_id", [
        "descriptive", "independent_ttest", "paired_ttest",
        "one_way_anova", "pearson_corr", "multiple_regression",
        "repeated_anova", "mediation", "moderation", "cronbach_alpha",
    ])
    def test_original_methods_still_registered(self, method_id):
        assert method_id in _CARD_BUILDERS
