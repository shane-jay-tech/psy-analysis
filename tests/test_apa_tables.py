"""V5.2 P0-3: APA 表格生成测试。"""

import pytest
import pandas as pd
import numpy as np
from src.output.apa_tables import (
    APATable,
    descriptive_stats_table,
    correlation_matrix_table,
    ttest_result_table,
    anova_result_table,
    regression_result_table,
    reliability_table,
    table_to_dataframe,
    table_to_markdown,
    table_to_csv,
)


@pytest.fixture
def sample_df():
    np.random.seed(42)
    return pd.DataFrame({
        "score": np.random.normal(70, 10, 40),
        "age": np.random.randint(18, 25, 40),
        "anxiety": np.random.normal(50, 15, 40),
        "group": ["A"] * 20 + ["B"] * 20,
    })


class TestDescriptiveTable:
    def test_basic(self, sample_df):
        t = descriptive_stats_table(sample_df, ["score", "anxiety"])
        assert t.method_id == "descriptive"
        assert len(t.rows) == 2
        assert "M" in t.columns

    def test_with_groups(self, sample_df):
        t = descriptive_stats_table(sample_df, ["score"], group_var="group")
        assert len(t.rows) == 2
        assert "组别" in t.columns

    def test_table_id(self, sample_df):
        t = descriptive_stats_table(sample_df, ["score"], table_id="desc1")
        assert t.table_id == "desc1"


class TestCorrelationTable:
    def test_basic(self, sample_df):
        t = correlation_matrix_table(sample_df, ["score", "age", "anxiety"])
        assert t.method_id == "correlation"
        assert len(t.rows) == 3
        assert "M" in t.columns
        assert "SD" in t.columns

    def test_lower_triangle(self, sample_df):
        t = correlation_matrix_table(sample_df, ["score", "age", "anxiety"])
        row0 = t.rows[0]
        assert row0["1"] == "—"
        assert row0["2"] == ""

    def test_significance_stars(self, sample_df):
        t = correlation_matrix_table(sample_df, ["score", "age", "anxiety"])
        all_cells = "".join(str(v) for row in t.rows for v in row.values())
        assert "." in all_cells


class TestTtestTable:
    def test_from_result(self, sample_df):
        from src.analysis.ttest import independent_ttest
        result = independent_ttest(sample_df, dv="score", iv="group")
        t = ttest_result_table(result)
        assert t.method_id == "ttest"
        assert len(t.rows) >= 1


class TestAnovaTable:
    def test_from_result(self):
        from src.analysis.anova import one_way_anova
        df = pd.DataFrame({
            "score": [10, 12, 11, 15, 17, 16, 20, 22, 21],
            "group": ["A"] * 3 + ["B"] * 3 + ["C"] * 3,
        })
        result = one_way_anova(df, dv="score", iv="group")
        t = anova_result_table(result)
        assert t.method_id in ("one_way", "anova")
        assert len(t.rows) >= 1


class TestRegressionTable:
    def test_from_result(self, sample_df):
        from src.analysis.regression import multiple_regression
        result = multiple_regression(sample_df, dv="score", ivs=["age", "anxiety"])
        t = regression_result_table(result)
        assert t.method_id in ("multiple", "regression")
        assert len(t.rows) >= 2


class TestReliabilityTable:
    def test_from_result(self):
        from src.analysis.reliability import cronbach_alpha
        np.random.seed(42)
        df = pd.DataFrame({f"q{i}": np.random.randint(1, 6, 50) for i in range(1, 6)})
        result = cronbach_alpha(df, items=[f"q{i}" for i in range(1, 6)])
        t = reliability_table(result)
        assert t.method_id == "cronbach_alpha"
        assert len(t.rows) >= 1


class TestExportFormats:
    def test_to_dataframe(self, sample_df):
        t = descriptive_stats_table(sample_df, ["score"])
        df = table_to_dataframe(t)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_to_markdown(self, sample_df):
        t = descriptive_stats_table(sample_df, ["score", "anxiety"])
        md = table_to_markdown(t)
        assert "| " in md
        assert "---" in md
        assert "*Note.*" in md

    def test_to_csv(self, sample_df):
        t = descriptive_stats_table(sample_df, ["score"])
        csv_str = table_to_csv(t)
        assert "M" in csv_str or "变量" in csv_str

    def test_apa_number(self, sample_df):
        t = descriptive_stats_table(sample_df, ["score"])
        t.apa_number = 1
        md = table_to_markdown(t)
        assert "Table 1" in md


class TestAPATableDataclass:
    def test_creation(self):
        t = APATable(
            table_id="test",
            method_id="test_method",
            title="Test Table",
            note="Test note.",
            columns=["a", "b"],
            rows=[{"a": 1, "b": 2}],
        )
        assert t.table_id == "test"
        assert t.warnings == []

    def test_optional_fields(self):
        t = APATable(
            table_id="t2",
            method_id="m",
            title="T",
            note="N",
            columns=[],
            rows=[],
            apa_number=5,
            source_result_card_id="rc_001",
            warnings=["warn1"],
        )
        assert t.apa_number == 5
        assert t.source_result_card_id == "rc_001"
        assert len(t.warnings) == 1
