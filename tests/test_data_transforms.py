import numpy as np
import pandas as pd
import pytest

from src.data.transforms import (
    compute_formula,
    compute_mean,
    compute_sum,
    filter_by_condition,
    filter_by_values,
    filter_outliers,
    recode_bins,
    recode_map,
    reverse_score,
)


@pytest.fixture
def survey_df():
    return pd.DataFrame(
        {
            "q1": [1, 2, "bad", 4],
            "q2": [3, np.nan, 5, 1],
            "group": ["a", "a", "b", "c"],
        }
    )


@pytest.mark.parametrize("operation", [compute_mean, compute_sum])
def test_compute_aggregates_coerce_values_without_mutating_input(survey_df, operation):
    original = survey_df.copy(deep=True)

    result = operation(survey_df, ["q1", "q2"], "score")

    assert result.success is True
    assert result.rows_before == result.rows_after == 4
    assert result.new_columns == ["score"]
    assert "score" not in survey_df
    pd.testing.assert_frame_equal(survey_df, original)
    expected = [2.0, 2.0, 5.0, 2.5] if operation is compute_mean else [4.0, 2.0, 5.0, 5.0]
    assert result.df["score"].tolist() == expected


@pytest.mark.parametrize("operation", [compute_mean, compute_sum])
def test_compute_aggregates_report_missing_columns(survey_df, operation):
    result = operation(survey_df, ["q1", "missing"], "score")

    assert result.success is False
    assert result.df is None
    assert "missing" in result.description
    assert result.rows_before == 4


def test_compute_formula_success_and_failure_are_returned_as_results(survey_df):
    success = compute_formula(survey_df, "double", "q2 * 2")
    failure = compute_formula(survey_df, "broken", "does_not_exist + 1")

    assert success.success is True
    assert success.df["double"].iloc[[0, 2, 3]].tolist() == [6.0, 10.0, 2.0]
    assert success.new_columns == ["double"]
    assert failure.success is False
    assert failure.df is None
    assert "does_not_exist" in failure.description


def test_reverse_score_handles_custom_range_and_non_numeric_values(survey_df):
    result = reverse_score(survey_df, ["q1", "q2"], scale_max=5, scale_min=1, suffix="_rev")

    assert result.success is True
    assert result.new_columns == ["q1_rev", "q2_rev"]
    assert result.df["q1_rev"].iloc[[0, 1, 3]].tolist() == [5.0, 4.0, 2.0]
    assert np.isnan(result.df.loc[2, "q1_rev"])
    assert result.df["q2_rev"].iloc[[0, 2, 3]].tolist() == [3.0, 1.0, 5.0]


def test_reverse_score_rejects_missing_items(survey_df):
    result = reverse_score(survey_df, ["q3"], scale_max=5)

    assert result.success is False
    assert result.df is None
    assert "q3" in result.description


def test_recode_bins_uses_default_name_and_includes_lowest_boundary():
    df = pd.DataFrame({"age": [0, 18, 19, 35, "bad"]})

    result = recode_bins(df, "age", [0, 18, 35], ["young", "adult"])

    assert result.success is True
    assert result.new_columns == ["age_group"]
    assert result.df["age_group"].astype(object).iloc[:4].tolist() == ["young", "young", "adult", "adult"]
    assert pd.isna(result.df.loc[4, "age_group"])


def test_recode_bins_rejects_missing_source_column(survey_df):
    result = recode_bins(survey_df, "age", [0, 18], ["young"])

    assert result.success is False
    assert result.df is None


def test_recode_map_can_copy_or_replace_and_preserves_unmapped_values(survey_df):
    copied = recode_map(survey_df, "group", {"a": "A"}, new_col="group_label")
    replaced = recode_map(survey_df, "group", {"a": "A"})

    assert copied.new_columns == ["group_label"]
    assert copied.df["group_label"].tolist() == ["A", "A", "b", "c"]
    assert copied.df["group"].tolist() == survey_df["group"].tolist()
    assert replaced.new_columns == []
    assert replaced.df["group"].tolist() == ["A", "A", "b", "c"]


def test_recode_map_rejects_missing_source_column(survey_df):
    assert recode_map(survey_df, "missing", {}).success is False


def test_filter_by_condition_covers_success_empty_and_invalid_queries(survey_df):
    success = filter_by_condition(survey_df, "q2 >= 3")
    empty = filter_by_condition(survey_df, "q2 > 100")
    invalid = filter_by_condition(survey_df, "missing > 1")

    assert success.success is True
    assert success.df.index.tolist() == [0, 2]
    assert success.rows_before == 4 and success.rows_after == 2
    assert empty.success is True and empty.rows_after == 0
    assert empty.warnings
    assert invalid.success is False and invalid.df is None


@pytest.mark.parametrize("method", ["zscore", "iqr"])
def test_filter_outliers_removes_extreme_values_and_warns(method):
    df = pd.DataFrame({"score": [1, 1, 1, 1, 100], "label": list("abcde")})

    result = filter_outliers(df, ["score"], method=method, threshold=1.5)

    assert result.success is True
    assert result.rows_before == 5 and result.rows_after == 4
    assert result.df["label"].tolist() == list("abcd")
    assert result.warnings


def test_filter_outliers_preserves_missing_values_for_iqr():
    df = pd.DataFrame({"score": [1.0, 2.0, np.nan, 3.0]})

    result = filter_outliers(df, ["score"], method="iqr")

    assert result.df.index.tolist() == [0, 1, 2, 3]


def test_filter_outliers_rejects_missing_columns(survey_df):
    result = filter_outliers(survey_df, ["missing"])

    assert result.success is False
    assert result.df is None


def test_filter_by_values_supports_keep_exclude_and_keep_precedence(survey_df):
    kept = filter_by_values(survey_df, "group", keep_values=["a", "c"])
    excluded = filter_by_values(survey_df, "group", exclude_values=["a"])
    precedence = filter_by_values(
        survey_df, "group", keep_values=["b"], exclude_values=["b"]
    )

    assert kept.df.index.tolist() == [0, 1, 3]
    assert excluded.df.index.tolist() == [2, 3]
    assert precedence.df.index.tolist() == [2]


def test_filter_by_values_reports_missing_configuration_and_column(survey_df):
    no_values = filter_by_values(survey_df, "group")
    missing_col = filter_by_values(survey_df, "missing", keep_values=[1])

    assert no_values.success is False and no_values.df is None
    assert missing_col.success is False and missing_col.df is None
