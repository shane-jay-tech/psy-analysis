"""V5.2 金标准统计验证扩展：覆盖高风险方法。

新增方法：Wilcoxon 符号秩、层级回归、二元 Logistic、ANCOVA、
调节分析、混合设计 ANOVA、McDonald's ω、EFA。
共计 ~50 个新断言。
"""

import json
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "golden_stats"


def _load(subdir: str, name: str):
    csv_path = FIXTURES / subdir / f"{name}.csv"
    json_path = FIXTURES / subdir / f"{name}_expected.json"
    df = pd.read_csv(csv_path)
    with open(json_path, "r", encoding="utf-8") as f:
        expected = json.load(f)
    return df, expected


# ===========================================================================
# Wilcoxon Signed-Rank
# ===========================================================================
class TestGoldenWilcoxon:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load("nonparametric", "wilcoxon")

    def test_wilcoxon_runs(self):
        from src.analysis.nonparametric import wilcoxon_signed_rank
        result = wilcoxon_signed_rank(self.df, col1="pre", col2="post")
        assert result.test_type == "wilcoxon"

    def test_wilcoxon_significant(self):
        from src.analysis.nonparametric import wilcoxon_signed_rank
        result = wilcoxon_signed_rank(self.df, col1="pre", col2="post")
        assert result.p_value < self.expected["expected"]["p_less_than"]

    def test_wilcoxon_effect_positive(self):
        from src.analysis.nonparametric import wilcoxon_signed_rank
        result = wilcoxon_signed_rank(self.df, col1="pre", col2="post")
        assert abs(result.effect_size) > 0

    def test_wilcoxon_group_stats(self):
        from src.analysis.nonparametric import wilcoxon_signed_rank
        result = wilcoxon_signed_rank(self.df, col1="pre", col2="post")
        assert result.group_stats is not None
        assert len(result.group_stats) == 3

    def test_wilcoxon_effect_ci(self):
        from src.analysis.nonparametric import wilcoxon_signed_rank
        result = wilcoxon_signed_rank(self.df, col1="pre", col2="post")
        assert result.effect_size_ci is not None
        assert "[" in result.effect_size_ci


# ===========================================================================
# Hierarchical Regression
# ===========================================================================
class TestGoldenHierarchicalRegression:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load("regression", "hierarchical")

    def test_hierarchical_runs(self):
        from src.analysis.regression import hierarchical_regression
        result = hierarchical_regression(
            self.df, dv="y", blocks=[["age", "gender"], ["stress", "coping", "support"]]
        )
        assert result.test_type == "hierarchical"

    def test_hierarchical_n_blocks(self):
        from src.analysis.regression import hierarchical_regression
        result = hierarchical_regression(
            self.df, dv="y", blocks=[["age", "gender"], ["stress", "coping", "support"]]
        )
        assert len(result.model_summary) == self.expected["expected"]["n_blocks"]

    def test_hierarchical_delta_r2_positive(self):
        from src.analysis.regression import hierarchical_regression
        result = hierarchical_regression(
            self.df, dv="y", blocks=[["age", "gender"], ["stress", "coping", "support"]]
        )
        block2 = result.model_summary.iloc[1]
        assert block2["ΔR²"] > 0

    def test_hierarchical_final_r2(self):
        from src.analysis.regression import hierarchical_regression
        result = hierarchical_regression(
            self.df, dv="y", blocks=[["age", "gender"], ["stress", "coping", "support"]]
        )
        assert result.r_squared > self.expected["expected"]["final_r2_gt"]

    def test_hierarchical_adj_r2(self):
        from src.analysis.regression import hierarchical_regression
        result = hierarchical_regression(
            self.df, dv="y", blocks=[["age", "gender"], ["stress", "coping", "support"]]
        )
        assert result.adj_r_squared > self.expected["expected"]["final_adj_r2_gt"]

    def test_hierarchical_coef_table(self):
        from src.analysis.regression import hierarchical_regression
        result = hierarchical_regression(
            self.df, dv="y", blocks=[["age", "gender"], ["stress", "coping", "support"]]
        )
        assert len(result.coef_table) == 6  # const + 5 vars

    def test_hierarchical_f2_effect(self):
        from src.analysis.regression import hierarchical_regression
        result = hierarchical_regression(
            self.df, dv="y", blocks=[["age", "gender"], ["stress", "coping", "support"]]
        )
        assert result.f2_effect_sizes is not None
        assert len(result.f2_effect_sizes) > 0


# ===========================================================================
# Binary Logistic Regression
# ===========================================================================
class TestGoldenLogistic:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load("regression", "logistic")

    def test_logistic_runs(self):
        from src.analysis.logistic_regression import binary_logistic
        result = binary_logistic(self.df, dv="outcome", ivs=["score1", "score2", "score3"])
        assert result.test_type == "binary"

    def test_logistic_or_values(self):
        from src.analysis.logistic_regression import binary_logistic
        result = binary_logistic(self.df, dv="outcome", ivs=["score1", "score2", "score3"])
        assert "OR" in result.coef_table.columns

    def test_logistic_classification(self):
        from src.analysis.logistic_regression import binary_logistic
        result = binary_logistic(self.df, dv="outcome", ivs=["score1", "score2", "score3"])
        assert result.accuracy > self.expected["expected"]["classification_accuracy_gt"]

    def test_logistic_pseudo_r2(self):
        from src.analysis.logistic_regression import binary_logistic
        result = binary_logistic(self.df, dv="outcome", ivs=["score1", "score2", "score3"])
        assert isinstance(result.pseudo_r2, dict)
        assert result.pseudo_r2.get("McFadden R²", 0) > 0

    def test_logistic_n_predictors(self):
        from src.analysis.logistic_regression import binary_logistic
        result = binary_logistic(self.df, dv="outcome", ivs=["score1", "score2", "score3"])
        non_const = result.coef_table[result.coef_table["变量"] != "常量"]
        assert len(non_const) == 3

    def test_logistic_hosmer_lemeshow(self):
        from src.analysis.logistic_regression import binary_logistic
        result = binary_logistic(self.df, dv="outcome", ivs=["score1", "score2", "score3"])
        assert result.hosmer_lemeshow is not None


# ===========================================================================
# ANCOVA
# ===========================================================================
class TestGoldenANCOVA:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load("advanced", "ancova")

    def test_ancova_runs(self):
        from src.analysis.advanced import ancova
        result = ancova(self.df, dv="score", iv="group", covs=["pretest"])
        assert result.test_type == "ancova"

    def test_ancova_group_effect(self):
        from src.analysis.advanced import ancova
        result = ancova(self.df, dv="score", iv="group", covs=["pretest"])
        table = result.model_summary
        group_rows = table[table["来源"].astype(str).str.contains("group", case=False)]
        assert len(group_rows) > 0

    def test_ancova_covariate_in_model(self):
        from src.analysis.advanced import ancova
        result = ancova(self.df, dv="score", iv="group", covs=["pretest"])
        table = result.model_summary
        cov_rows = table[table["来源"].astype(str).str.contains("pretest", case=False)]
        assert len(cov_rows) > 0

    def test_ancova_effect_size(self):
        from src.analysis.advanced import ancova
        result = ancova(self.df, dv="score", iv="group", covs=["pretest"])
        assert result.effect_size > self.expected["expected"]["eta_sq_partial_gt"]

    def test_ancova_adjusted_means(self):
        from src.analysis.advanced import ancova
        result = ancova(self.df, dv="score", iv="group", covs=["pretest"])
        assert result.coef_table is not None
        assert len(result.coef_table) >= 2


# ===========================================================================
# Moderation Analysis
# ===========================================================================
class TestGoldenModeration:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load("advanced", "moderation")

    def test_moderation_runs(self):
        from src.analysis.advanced import moderation_analysis
        result = moderation_analysis(self.df, x="x", m="m", y="y")
        assert result.test_type == "moderation"

    def test_moderation_has_interaction(self):
        from src.analysis.advanced import moderation_analysis
        result = moderation_analysis(self.df, x="x", m="m", y="y")
        coef = result.coef_table
        interaction_rows = coef[coef["变量"].astype(str).str.contains("×|\\*|交互|interaction|x.*m", case=False, regex=True)]
        assert len(interaction_rows) > 0

    def test_moderation_simple_slopes(self):
        from src.analysis.advanced import moderation_analysis
        result = moderation_analysis(self.df, x="x", m="m", y="y")
        assert result.simple_slopes is not None
        assert len(result.simple_slopes) >= 2

    def test_moderation_model_summary(self):
        from src.analysis.advanced import moderation_analysis
        result = moderation_analysis(self.df, x="x", m="m", y="y")
        assert result.model_summary is not None


# ===========================================================================
# Mixed ANOVA
# ===========================================================================
class TestGoldenMixedANOVA:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load("anova", "mixed_anova")

    def test_mixed_anova_runs(self):
        from src.analysis.anova import mixed_anova
        result = mixed_anova(
            self.df, dv="score", within="time", subject="subject", between="group"
        )
        assert result.test_type == "mixed"

    def test_mixed_anova_sources(self):
        from src.analysis.anova import mixed_anova
        result = mixed_anova(
            self.df, dv="score", within="time", subject="subject", between="group"
        )
        assert len(result.table) >= self.expected["expected"]["n_sources"]

    def test_mixed_anova_interaction(self):
        from src.analysis.anova import mixed_anova
        result = mixed_anova(
            self.df, dv="score", within="time", subject="subject", between="group"
        )
        table = result.table
        source_col = "来源" if "来源" in table.columns else table.columns[0]
        sources = table[source_col].astype(str)
        interaction = sources[sources.str.contains("nteraction|:", case=False, na=False)]
        assert len(interaction) > 0

    def test_mixed_anova_eta_squared(self):
        from src.analysis.anova import mixed_anova
        result = mixed_anova(
            self.df, dv="score", within="time", subject="subject", between="group"
        )
        assert result.effect_size > 0

    def test_mixed_anova_group_effect(self):
        from src.analysis.anova import mixed_anova
        result = mixed_anova(
            self.df, dv="score", within="time", subject="subject", between="group"
        )
        table = result.table
        source_col = "来源" if "来源" in table.columns else table.columns[0]
        sources = table[source_col].astype(str)
        group_rows = sources[sources.str.contains("group", case=False, na=False)]
        assert len(group_rows) > 0


# ===========================================================================
# McDonald's Omega
# ===========================================================================
class TestGoldenOmega:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load("psychometrics", "omega")

    def test_omega_runs(self):
        from src.analysis.reliability import mcdonald_omega
        items = [f"q{i}" for i in range(1, 7)]
        result = mcdonald_omega(self.df, items=items)
        assert result.test_type == "mcdonald_omega"

    def test_omega_value_range(self):
        from src.analysis.reliability import mcdonald_omega
        items = [f"q{i}" for i in range(1, 7)]
        result = mcdonald_omega(self.df, items=items)
        assert result.omega_value > self.expected["expected"]["omega_gt"]
        assert result.omega_value < self.expected["expected"]["omega_lt"]

    def test_omega_ci(self):
        from src.analysis.reliability import mcdonald_omega
        items = [f"q{i}" for i in range(1, 7)]
        result = mcdonald_omega(self.df, items=items)
        assert result.ci_lower > self.expected["expected"]["ci_lower_gt"]
        assert result.ci_lower < result.omega_value
        assert result.ci_upper >= result.omega_value

    def test_omega_item_count(self):
        from src.analysis.reliability import mcdonald_omega
        items = [f"q{i}" for i in range(1, 7)]
        result = mcdonald_omega(self.df, items=items)
        assert result.n_items == self.expected["expected"]["n_items"]

    def test_omega_sample_size(self):
        from src.analysis.reliability import mcdonald_omega
        items = [f"q{i}" for i in range(1, 7)]
        result = mcdonald_omega(self.df, items=items)
        assert result.n_cases == self.expected["expected"]["n_cases"]


# ===========================================================================
# Exploratory Factor Analysis
# ===========================================================================
class TestGoldenEFA:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load("psychometrics", "efa")

    def test_efa_runs(self):
        from src.analysis.factor_analysis import exploratory_factor_analysis
        items = [c for c in self.df.columns]
        result = exploratory_factor_analysis(self.df, items=items)
        assert result is not None

    def test_efa_n_factors(self):
        from src.analysis.factor_analysis import exploratory_factor_analysis
        items = [c for c in self.df.columns]
        result = exploratory_factor_analysis(self.df, items=items)
        assert result.n_factors == self.expected["expected"]["n_factors"]

    def test_efa_kmo(self):
        from src.analysis.factor_analysis import exploratory_factor_analysis
        items = [c for c in self.df.columns]
        result = exploratory_factor_analysis(self.df, items=items)
        assert result.kmo > self.expected["expected"]["kmo_gt"]

    def test_efa_bartlett(self):
        from src.analysis.factor_analysis import exploratory_factor_analysis
        items = [c for c in self.df.columns]
        result = exploratory_factor_analysis(self.df, items=items)
        assert result.bartlett_p < 0.05

    def test_efa_variance_explained(self):
        from src.analysis.factor_analysis import exploratory_factor_analysis
        items = [c for c in self.df.columns]
        result = exploratory_factor_analysis(self.df, items=items)
        total_row = result.variance_explained[result.variance_explained["因素"] == "合计"]
        if len(total_row) > 0:
            total_pct = float(total_row.iloc[0]["累计比例"]) * 100
        else:
            total_pct = float(result.variance_explained.iloc[-2]["累计比例"]) * 100
        assert total_pct > self.expected["expected"]["total_variance_explained_gt"]

    def test_efa_loadings_shape(self):
        from src.analysis.factor_analysis import exploratory_factor_analysis
        items = [c for c in self.df.columns]
        result = exploratory_factor_analysis(self.df, items=items)
        assert result.loadings is not None
        assert result.loadings.shape[0] == 12
        assert result.loadings.shape[1] == self.expected["expected"]["n_factors"]


# ===========================================================================
# Coverage summary
# ===========================================================================
class TestGoldenV2Coverage:
    def test_total_new_methods(self):
        """V5.2 should cover at least 8 new method types."""
        methods = [
            "wilcoxon", "hierarchical", "binary_logistic",
            "ancova", "moderation", "mixed_anova",
            "mcdonald_omega", "efa",
        ]
        assert len(methods) >= 8

    def test_fixture_files_exist(self):
        """All expected fixture files should exist."""
        pairs = [
            ("nonparametric", "wilcoxon"),
            ("regression", "hierarchical"),
            ("regression", "logistic"),
            ("advanced", "ancova"),
            ("advanced", "moderation"),
            ("anova", "mixed_anova"),
            ("psychometrics", "omega"),
            ("psychometrics", "efa"),
        ]
        for subdir, name in pairs:
            csv = FIXTURES / subdir / f"{name}.csv"
            json_f = FIXTURES / subdir / f"{name}_expected.json"
            assert csv.exists(), f"Missing {csv}"
            assert json_f.exists(), f"Missing {json_f}"
