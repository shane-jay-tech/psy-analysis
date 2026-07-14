import pytest

from src.utils.method_exposure import (
    get_method_level,
    get_method_warning,
    is_safe_for_newbie,
    list_methods_by_level,
)


@pytest.mark.parametrize(
    ("method_id", "level"),
    [
        ("pearson_corr", "default"),
        ("logistic_regression", "advanced"),
        ("totally_unknown", "experimental"),
    ],
)
def test_method_level_classification(method_id, level):
    assert get_method_level(method_id) == level


def test_method_warning_and_newbie_safety_follow_level():
    assert get_method_warning("pearson_corr") == ""
    assert get_method_warning("logistic_regression")
    assert get_method_warning("totally_unknown")
    assert is_safe_for_newbie("pearson_corr") is True
    assert is_safe_for_newbie("logistic_regression") is False


def test_grouped_methods_are_sorted_disjoint_and_consistent():
    grouped = list_methods_by_level()

    assert set(grouped) == {"default", "advanced", "experimental"}
    assert grouped["default"] == sorted(grouped["default"])
    assert grouped["advanced"] == sorted(grouped["advanced"])
    assert grouped["experimental"] == []
    assert set(grouped["default"]).isdisjoint(grouped["advanced"])
    assert all(get_method_level(method) == "default" for method in grouped["default"])
    assert all(get_method_level(method) == "advanced" for method in grouped["advanced"])
