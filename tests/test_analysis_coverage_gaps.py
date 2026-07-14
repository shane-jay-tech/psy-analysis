from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.analysis.logistic_regression import (
    _cox_snell_r2,
    _hosmer_lemeshow,
    _nagelkerke_r2,
    binary_logistic,
    multinomial_logistic,
    ordinal_logistic,
)
from src.analysis.manova import _box_m_test, _partial_eta2_mv, manova


def make_manova_data(n_per_group=20):
    rng = np.random.default_rng(20260714)
    groups = np.repeat(["control", "treatment"], n_per_group)
    shift = np.repeat([0.0, 0.8], n_per_group)
    return pd.DataFrame(
        {
            "group": groups,
            "anxiety": rng.normal(0, 1, n_per_group * 2) + shift,
            "wellbeing": rng.normal(0, 1, n_per_group * 2) - shift,
            "age": rng.normal(30, 4, n_per_group * 2),
        }
    )


def test_manova_returns_multivariate_univariate_descriptive_and_box_m_results():
    result = manova(make_manova_data(), ["anxiety", "wellbeing"], "group")

    assert result.test_type == "manova"
    assert len(result.multivariate_tests) == 4
    assert len(result.univariate_tests) == 2
    assert len(result.descriptive) == 4
    assert result.box_m is not None
    assert result.n_obs == 40 and result.n_groups == 2
    assert result.dependent_vars == ["anxiety", "wellbeing"]


def test_mancova_path_accepts_numeric_covariates_and_drops_invalid_rows():
    df = make_manova_data()
    df["age"] = df["age"].astype(object)
    df.loc[0, "age"] = "bad"

    result = manova(df, ["anxiety", "wellbeing"], "group", covariates=["age"])

    assert result.test_type == "mancova"
    assert result.n_obs == 39
    assert len(result.multivariate_tests) == 4


def test_manova_validates_group_and_dependent_variable_counts():
    df = make_manova_data()

    with pytest.raises(ValueError):
        manova(df[df["group"] == "control"], ["anxiety", "wellbeing"], "group")
    with pytest.raises(ValueError):
        manova(df, ["anxiety"], "group")


def test_manova_small_sample_emits_warning():
    result = manova(make_manova_data(n_per_group=6), ["anxiety", "wellbeing"], "group")
    assert result.warning


def test_partial_eta_squared_helper_and_error_fallback():
    row = pd.Series({"F Value": 4.0, "Num DF": 2.0, "Den DF": 20.0})

    assert _partial_eta2_mv(row) == pytest.approx(8 / 28)
    assert _partial_eta2_mv(pd.Series(dtype=float)) == 0.0


def test_box_m_returns_none_for_singular_covariance_and_result_for_regular_data():
    regular = _box_m_test(make_manova_data(), ["anxiety", "wellbeing"], "group")
    singular_df = pd.DataFrame(
        {
            "group": ["a", "a", "b", "b"],
            "x": [1, 1, 2, 2],
            "y": [1, 1, 2, 2],
        }
    )

    assert regular is not None and set(regular) == {"M", "chi2_approx", "df", "p"}
    assert _box_m_test(singular_df, ["x", "y"], "group") is None


def test_binary_logistic_supports_string_categories_and_reference_choice():
    rng = np.random.default_rng(42)
    x = rng.normal(size=120)
    probability = 1 / (1 + np.exp(-(0.8 * x)))
    y = np.where(rng.random(120) < probability, "yes", "no")
    df = pd.DataFrame({"outcome": y, "x": x})

    result = binary_logistic(df, "outcome", ["x"], reference="no")

    assert result.test_type == "binary"
    assert result.n_obs == 120
    assert 0 <= result.accuracy <= 1
    assert result.n_events == int((y == "yes").sum())
    assert len(result.coef_table) == 2
    assert len(result.odds_ratios) == 1
    assert set(result.pseudo_r2) == {"McFadden R²", "Cox-Snell R²", "Nagelkerke R²"}


def test_logistic_variants_validate_category_counts():
    binary_bad = pd.DataFrame({"y": [0, 1, 2, 0, 1, 2], "x": range(6)})
    ordinal_bad = pd.DataFrame({"y": [0, 1, 0, 1], "x": range(4)})

    with pytest.raises(ValueError):
        binary_logistic(binary_bad, "y", ["x"])
    with pytest.raises(ValueError):
        ordinal_logistic(ordinal_bad, "y", ["x"])
    with pytest.raises(ValueError):
        multinomial_logistic(ordinal_bad, "y", ["x"])


def test_pseudo_r_squared_helpers_cover_regular_and_zero_denominator_cases():
    model = SimpleNamespace(llf=-40.0, llnull=-50.0)
    zero_max = SimpleNamespace(llf=0.0, llnull=0.0)

    assert 0 < _cox_snell_r2(model, 100) < 1
    assert 0 < _nagelkerke_r2(model, 100) < 1
    assert _nagelkerke_r2(zero_max, 100) == 0.0


def test_hosmer_lemeshow_handles_small_and_sufficient_samples():
    small = _hosmer_lemeshow(np.array([0, 1] * 10), np.linspace(0.1, 0.9, 20))
    enough = _hosmer_lemeshow(np.array([0, 1] * 30), np.linspace(0.05, 0.95, 60))

    assert np.isnan(small["chi2"])
    assert enough["df"] == 8
    assert enough["chi2"] >= 0
    assert 0 <= enough["p"] <= 1
