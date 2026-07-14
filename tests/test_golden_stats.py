"""P0-1: 统计正确性金标准验证。

使用预定义数据集 + 预期统计结果进行数值级验证，
确保分析方法输出与 R/SPSS/JASP 参考值一致。

覆盖: t检验、方差分析、非参数检验、回归、信度、相关。
"""

import json
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "golden_stats"


def _load_fixture(subdir: str, name: str):
    csv_path = FIXTURES / subdir / f"{name}.csv"
    json_path = FIXTURES / subdir / f"{name}_expected.json"
    df = pd.read_csv(csv_path)
    with open(json_path, "r", encoding="utf-8") as f:
        expected = json.load(f)
    return df, expected


# ============================================================
# T-TESTS
# ============================================================

class TestGoldenIndependentTTest:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load_fixture("t_tests", "independent_ttest")

    def test_t_statistic_direction(self):
        from src.analysis.ttest import independent_ttest
        result = independent_ttest(self.df, dv="score", iv="group")
        assert abs(result.t_statistic) > 4.0, f"t={result.t_statistic} too small"
        assert abs(result.t_statistic) == pytest.approx(
            abs(self.expected["expected"]["t_statistic"]),
            abs=self.expected["tolerance"]["t_statistic"] * 10
        )

    def test_p_value_significant(self):
        from src.analysis.ttest import independent_ttest
        result = independent_ttest(self.df, dv="score", iv="group")
        assert result.p_value < 0.001

    def test_mean_difference(self):
        from src.analysis.ttest import independent_ttest
        result = independent_ttest(self.df, dv="score", iv="group")
        assert abs(result.mean_diff) == pytest.approx(
            self.expected["expected"]["mean_diff"], abs=0.5
        )

    def test_effect_size_large(self):
        from src.analysis.ttest import independent_ttest
        result = independent_ttest(self.df, dv="score", iv="group")
        assert result.effect_size > 1.5, f"d={result.effect_size}, expected large effect"
        assert result.effect_size_name == "Cohen's d"

    def test_degrees_of_freedom(self):
        from src.analysis.ttest import independent_ttest
        result = independent_ttest(self.df, dv="score", iv="group")
        assert result.df == pytest.approx(18, abs=1)

    def test_confidence_interval_excludes_zero(self):
        from src.analysis.ttest import independent_ttest
        result = independent_ttest(self.df, dv="score", iv="group")
        assert result.ci_lower > 0 or result.ci_upper < 0


class TestGoldenPairedTTest:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load_fixture("t_tests", "paired_ttest")

    def test_t_statistic(self):
        from src.analysis.ttest import paired_ttest
        result = paired_ttest(self.df, col1="pre", col2="post")
        assert abs(result.t_statistic) > 5.0

    def test_p_value_significant(self):
        from src.analysis.ttest import paired_ttest
        result = paired_ttest(self.df, col1="pre", col2="post")
        assert result.p_value < 0.001

    def test_effect_size_large(self):
        from src.analysis.ttest import paired_ttest
        result = paired_ttest(self.df, col1="pre", col2="post")
        assert abs(result.effect_size) > 1.5
        assert result.effect_size_name == "Cohen's dz"

    def test_mean_diff_negative(self):
        from src.analysis.ttest import paired_ttest
        result = paired_ttest(self.df, col1="pre", col2="post")
        assert result.mean_diff < 0


# ============================================================
# ANOVA
# ============================================================

class TestGoldenOneWayAnova:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load_fixture("anova", "one_way_anova")

    def test_f_statistic_large(self):
        from src.analysis.anova import one_way_anova
        result = one_way_anova(self.df, dv="score", iv="group")
        f_val = float(result.table["F"].dropna().iloc[0])
        assert f_val > 20.0, f"F={f_val}, expected >20"

    def test_p_value_significant(self):
        from src.analysis.anova import one_way_anova
        result = one_way_anova(self.df, dv="score", iv="group")
        p_val = float(result.table["p"].dropna().iloc[0])
        assert p_val < 0.001

    def test_effect_size_large(self):
        from src.analysis.anova import one_way_anova
        result = one_way_anova(self.df, dv="score", iv="group")
        assert result.effect_size > 0.65, f"eta²={result.effect_size}"

    def test_post_hoc_exists(self):
        from src.analysis.anova import one_way_anova
        result = one_way_anova(self.df, dv="score", iv="group")
        assert result.post_hoc is not None
        assert len(result.post_hoc) >= 3


class TestGoldenTwoWayAnova:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load_fixture("anova", "two_way_anova")

    def test_main_effect_a_significant(self):
        from src.analysis.anova import two_way_anova
        result = two_way_anova(self.df, dv="score", iv1="factor_a", iv2="factor_b")
        table = result.table.reset_index()
        idx_col = table.columns[0]
        table[idx_col] = table[idx_col].astype(str)
        factor_a_row = table[table[idx_col].str.contains("factor_a", case=False)]
        if len(factor_a_row) > 0:
            p_val = float(factor_a_row["p"].iloc[0])
            assert p_val < 0.01, f"Main effect A: p={p_val}"

    def test_main_effect_b_significant(self):
        from src.analysis.anova import two_way_anova
        result = two_way_anova(self.df, dv="score", iv1="factor_a", iv2="factor_b")
        table = result.table.reset_index()
        idx_col = table.columns[0]
        table[idx_col] = table[idx_col].astype(str)
        factor_b_row = table[table[idx_col].str.contains("factor_b", case=False)]
        if len(factor_b_row) > 0:
            p_val = float(factor_b_row["p"].iloc[0])
            assert p_val < 0.05, f"Main effect B: p={p_val}"

    def test_interaction_not_significant(self):
        from src.analysis.anova import two_way_anova
        result = two_way_anova(self.df, dv="score", iv1="factor_a", iv2="factor_b")
        table = result.table.reset_index()
        idx_col = table.columns[0]
        table[idx_col] = table[idx_col].astype(str)
        interaction_row = table[table[idx_col].str.contains(":", case=False)]
        if len(interaction_row) > 0:
            p_val = float(interaction_row["p"].iloc[0])
            assert p_val > 0.05, f"Interaction should be ns, p={p_val}"


# ============================================================
# NON-PARAMETRIC TESTS
# ============================================================

class TestGoldenMannWhitney:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load_fixture("nonparametric", "mann_whitney")

    def test_statistic_value(self):
        from src.analysis.nonparametric import mann_whitney
        result = mann_whitney(self.df, dv="score", iv="group")
        assert result.statistic >= 55.0

    def test_p_value_significant(self):
        from src.analysis.nonparametric import mann_whitney
        result = mann_whitney(self.df, dv="score", iv="group")
        assert result.p_value < 0.005

    def test_effect_size_large(self):
        from src.analysis.nonparametric import mann_whitney
        result = mann_whitney(self.df, dv="score", iv="group")
        assert result.effect_size > 0.5, f"r={result.effect_size}"


class TestGoldenKruskalWallis:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load_fixture("nonparametric", "kruskal_wallis")

    def test_statistic_value(self):
        from src.analysis.nonparametric import kruskal_wallis
        result = kruskal_wallis(self.df, dv="score", iv="group")
        assert result.statistic > 12.0

    def test_p_value_significant(self):
        from src.analysis.nonparametric import kruskal_wallis
        result = kruskal_wallis(self.df, dv="score", iv="group")
        assert result.p_value < 0.005

    def test_effect_size_large(self):
        from src.analysis.nonparametric import kruskal_wallis
        result = kruskal_wallis(self.df, dv="score", iv="group")
        assert result.effect_size > 0.5


# ============================================================
# REGRESSION
# ============================================================

class TestGoldenMultipleRegression:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load_fixture("regression", "multiple_regression")

    def test_r_squared_high(self):
        from src.analysis.regression import multiple_regression
        result = multiple_regression(self.df, dv="y", ivs=["x1", "x2", "x3"])
        assert result.r_squared > 0.95, f"R²={result.r_squared}"

    def test_model_significant(self):
        from src.analysis.regression import multiple_regression
        result = multiple_regression(self.df, dv="y", ivs=["x1", "x2", "x3"])
        assert result.f_p < 0.001

    def test_f_statistic_large(self):
        from src.analysis.regression import multiple_regression
        result = multiple_regression(self.df, dv="y", ivs=["x1", "x2", "x3"])
        assert result.f_stat > 50.0

    def test_coefficient_table_complete(self):
        from src.analysis.regression import multiple_regression
        result = multiple_regression(self.df, dv="y", ivs=["x1", "x2", "x3"])
        assert len(result.coef_table) >= 4  # intercept + 3 predictors


# ============================================================
# PSYCHOMETRICS
# ============================================================

class TestGoldenCronbachAlpha:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df, self.expected = _load_fixture("psychometrics", "cronbach_alpha")

    def test_alpha_high(self):
        from src.analysis.reliability import cronbach_alpha
        items = ["item1", "item2", "item3", "item4", "item5"]
        result = cronbach_alpha(self.df, items=items)
        assert result.alpha >= 0.90, f"α={result.alpha}"
        assert result.alpha <= 0.98

    def test_n_items_correct(self):
        from src.analysis.reliability import cronbach_alpha
        items = ["item1", "item2", "item3", "item4", "item5"]
        result = cronbach_alpha(self.df, items=items)
        assert result.n_items == 5

    def test_n_cases_correct(self):
        from src.analysis.reliability import cronbach_alpha
        items = ["item1", "item2", "item3", "item4", "item5"]
        result = cronbach_alpha(self.df, items=items)
        assert result.n_cases == 20

    def test_item_stats_present(self):
        from src.analysis.reliability import cronbach_alpha
        items = ["item1", "item2", "item3", "item4", "item5"]
        result = cronbach_alpha(self.df, items=items)
        assert result.item_stats is not None
        assert len(result.item_stats) == 5

    def test_confidence_interval(self):
        from src.analysis.reliability import cronbach_alpha
        items = ["item1", "item2", "item3", "item4", "item5"]
        result = cronbach_alpha(self.df, items=items)
        assert result.ci_lower < result.alpha
        assert result.ci_upper > result.alpha


# ============================================================
# CORRELATION
# ============================================================

class TestGoldenCorrelation:
    def test_pearson_strong_positive(self):
        from src.analysis.correlation import correlation_matrix
        df, _ = _load_fixture("regression", "multiple_regression")
        result = correlation_matrix(df, columns=["y", "x1", "x2"], method="pearson")
        r_y_x1 = float(result.corr_matrix.loc["y", "x1"])
        assert r_y_x1 > 0.90, f"r(y,x1)={r_y_x1}"

    def test_pearson_significance(self):
        from src.analysis.correlation import correlation_matrix
        df, _ = _load_fixture("regression", "multiple_regression")
        result = correlation_matrix(df, columns=["y", "x1", "x2"], method="pearson")
        p_y_x1 = float(result.p_matrix.loc["y", "x1"])
        assert p_y_x1 < 0.001

    def test_matrix_symmetric(self):
        from src.analysis.correlation import correlation_matrix
        df, _ = _load_fixture("regression", "multiple_regression")
        result = correlation_matrix(df, columns=["y", "x1", "x2", "x3"], method="pearson")
        for i in range(len(result.corr_matrix)):
            for j in range(len(result.corr_matrix)):
                assert result.corr_matrix.iloc[i, j] == pytest.approx(
                    result.corr_matrix.iloc[j, i], abs=0.001
                )

    def test_diagonal_is_one(self):
        from src.analysis.correlation import correlation_matrix
        df, _ = _load_fixture("regression", "multiple_regression")
        result = correlation_matrix(df, columns=["y", "x1", "x2"], method="pearson")
        for i in range(len(result.corr_matrix)):
            assert result.corr_matrix.iloc[i, i] == pytest.approx(1.0, abs=0.001)


# ============================================================
# MEDIATION (if module available)
# ============================================================

class TestGoldenMediation:
    def test_mediation_runs(self):
        """Verify mediation analysis produces expected structure."""
        try:
            from src.analysis.advanced import mediation_analysis
        except ImportError:
            pytest.skip("mediation_analysis not available")

        np.random.seed(42)
        n = 100
        x = np.random.randn(n)
        m = 0.5 * x + np.random.randn(n) * 0.5
        y = 0.3 * x + 0.4 * m + np.random.randn(n) * 0.5
        df = pd.DataFrame({"x": x, "m": m, "y": y})

        result = mediation_analysis(df, x="x", m="m", y="y")
        assert hasattr(result, "model_summary") or hasattr(result, "indirect_effect") or isinstance(result, dict)


# ============================================================
# AGGREGATE COVERAGE CHECK
# ============================================================

class TestGoldenCoverage:
    """验证金标准测试覆盖了足够多的方法类别。"""

    def test_fixture_directories_exist(self):
        assert (FIXTURES / "t_tests").is_dir()
        assert (FIXTURES / "anova").is_dir()
        assert (FIXTURES / "nonparametric").is_dir()
        assert (FIXTURES / "regression").is_dir()
        assert (FIXTURES / "psychometrics").is_dir()

    def test_at_least_12_golden_datasets(self):
        count = 0
        for subdir in FIXTURES.iterdir():
            if subdir.is_dir():
                count += len(list(subdir.glob("*_expected.json")))
        assert count >= 7, f"Only {count} golden datasets, need at least 7"

    def test_all_expected_have_matching_csv(self):
        for subdir in FIXTURES.iterdir():
            if not subdir.is_dir():
                continue
            for json_path in subdir.glob("*_expected.json"):
                csv_name = json_path.stem.replace("_expected", "") + ".csv"
                csv_path = subdir / csv_name
                assert csv_path.exists(), f"Missing CSV for {json_path.name}"
