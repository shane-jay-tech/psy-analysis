from types import SimpleNamespace

import pandas as pd
import pytest

from src.analysis.anova import ANOVAResult
from src.analysis.chi_square import ChiSquareResult
from src.analysis.correlation import CorrResult
from src.analysis.ttest import TTestResult
from src.output import formatter


@pytest.fixture(autouse=True)
def english_output(monkeypatch):
    monkeypatch.setattr(formatter, "get_output_language", lambda: "en")


def make_ttest(test_type="independent", p_value=0.01, mean_diff=1.5, is_welch=False):
    return TTestResult(
        test_type=test_type,
        t_statistic=2.5,
        df=18,
        p_value=p_value,
        mean_diff=mean_diff,
        ci_lower=0.2,
        ci_upper=2.8,
        effect_size=0.6,
        effect_size_name="Cohen's d",
        group_stats=pd.DataFrame({"组别": ["A", "B"], "M": [5.0, 3.5]}),
        is_welch=is_welch,
    )


@pytest.mark.parametrize(
    ("test_type", "p_value", "mean_diff", "expected"),
    [
        ("independent", 0.01, 1.5, "independent-samples"),
        ("paired", 0.20, 1.5, "paired-samples"),
        ("one_sample", 0.01, 1.5, "significantly higher"),
        ("one_sample", 0.01, -1.5, "significantly lower"),
        ("one_sample", 0.20, -1.5, "not significantly different"),
    ],
)
def test_ttest_formatter_covers_supported_variants(test_type, p_value, mean_diff, expected):
    summary = formatter.format_result_summary(
        {"result": make_ttest(test_type, p_value, mean_diff, is_welch=True)}
    )

    assert expected in summary
    assert "Cohen's d = 0.600" in summary
    if test_type == "independent":
        assert "Welch's correction" in summary


def test_ttest_formatter_returns_empty_for_unknown_subtype():
    assert formatter._format_ttest(make_ttest(test_type="other")) == ""


def test_anova_formatter_covers_one_way_and_two_way_results():
    one_way = ANOVAResult(
        test_type="one_way",
        table=pd.DataFrame(
            {
                "来源": ["组间", "组内"],
                "df": [2, 27],
                "F": [4.2, ""],
                "p": [0.02, ""],
            }
        ),
        effect_size=0.24,
        effect_size_name="eta squared",
    )
    two_way = ANOVAResult(
        test_type="two_way",
        table=pd.DataFrame(
            {
                "来源": ["A", "B", "error"],
                "F": [5.0, 0.5, ""],
                "p": [0.01, 0.60, ""],
            }
        ),
        effect_size=0.1,
        effect_size_name="partial eta squared",
    )

    one_text = formatter.format_result_summary({"result": one_way})
    two_text = formatter.format_result_summary({"result": two_way})

    assert "one-way ANOVA" in one_text and "significant" in one_text
    assert "A effect was significant" in two_text
    assert "B effect was not significant" in two_text


def test_anova_formatter_returns_empty_for_unknown_subtype():
    result = ANOVAResult("other", pd.DataFrame(), 0.1, "eta")
    assert formatter._format_anova(result) == ""


@pytest.mark.parametrize("method", ["pearson", "spearman"])
def test_correlation_formatter_reports_method_and_variable_count(method):
    matrix = pd.DataFrame([[1, 0.5], [0.5, 1]], columns=["x", "y"])
    result = CorrResult(method, matrix, matrix, matrix, matrix)

    text = formatter.format_result_summary({"result": result})

    assert ("Pearson" if method == "pearson" else "Spearman") in text
    assert "2 variables" in text


def test_chi_square_formatter_includes_warning_and_significance():
    result = ChiSquareResult(
        test_type="independence",
        chi_sq=6.2,
        df=1,
        p_value=0.01,
        effect_size=0.3,
        effect_size_name="Cramer's V",
        contingency_table=pd.DataFrame([[10, 5], [3, 12]]),
        warning="small expected counts",
    )

    text = formatter.format_result_summary({"result": result})

    assert "significant association" in text
    assert "Cramer's V = 0.300" in text
    assert "small expected counts" in text


def test_summary_handles_missing_and_unknown_result_types():
    assert formatter.format_result_summary({}) == "No analysis result."
    assert formatter.format_result_summary({"result": object()}) == "Unknown result type."


def test_effect_size_guard_covers_exempt_missing_object_and_top_level_values():
    assert formatter.check_effect_size_required({"test_type": "descriptive"}) == (True, "")
    ok, missing_object = formatter.check_effect_size_required({"test_type": "ttest"})
    assert ok is False and "No effect size" not in missing_object

    ok, missing_effect = formatter.check_effect_size_required(
        {"test_type": "ttest", "result": SimpleNamespace()}
    )
    assert ok is False and "No effect size field" in missing_effect

    assert formatter.check_effect_size_required(
        {"test_type": "ttest", "result": SimpleNamespace(effect_size=0)}
    ) == (True, "")

    assert formatter.check_effect_size_required(
        {"test_type": "custom", "result": object(), "effect_size": 0.2}
    ) == (True, "")


def test_build_apa7_report_blocks_missing_effect_and_builds_complete_report():
    blocked = formatter.build_apa7_report(
        {"test_type": "ttest", "result": SimpleNamespace()}
    )
    complete = formatter.build_apa7_report(
        {
            "test_type": "ttest",
            "test_name_zh": "Independent t test",
            "result": make_ttest(),
        }
    )

    assert blocked.startswith("## Missing Effect Size")
    assert "APA 7th Edition" in blocked
    assert complete.startswith("## Independent t test Results")
    assert "**Effect size:** Cohen's d = 0.600" in complete
    assert "Report generated in APA 7th Edition format" in complete


def test_chinese_language_path_is_selected(monkeypatch):
    monkeypatch.setattr(formatter, "get_output_language", lambda: "zh")

    missing = formatter.format_result_summary({})
    report = formatter.build_apa7_report(
        {"test_type": "ttest", "result": SimpleNamespace()}
    )

    assert missing != "No analysis result."
    assert not report.startswith("## Missing Effect Size")
