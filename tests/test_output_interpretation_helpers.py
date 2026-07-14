import pandas as pd
import pytest

from src.output import interpretation


@pytest.mark.parametrize(
    ("value", "bucket"),
    [(0.0, 0), (0.2, 1), (0.5, 2), (0.8, 3), (-1.2, 3)],
)
def test_cohens_d_interpretation_has_four_magnitude_buckets(value, bucket):
    labels = [interpretation._interpret_cohens_d(v) for v in [0.0, 0.2, 0.5, 0.8]]
    assert interpretation._interpret_cohens_d(value) == labels[bucket]


@pytest.mark.parametrize(
    ("value", "bucket"),
    [(0.0, 0), (0.01, 1), (0.06, 2), (0.14, 3)],
)
def test_eta_squared_interpretation_has_four_magnitude_buckets(value, bucket):
    labels = [interpretation._interpret_eta_sq(v) for v in [0.0, 0.01, 0.06, 0.14]]
    assert interpretation._interpret_eta_sq(value) == labels[bucket]


@pytest.mark.parametrize(
    ("value", "bucket"),
    [(0.0, 0), (0.1, 1), (0.3, 2), (0.5, 3), (0.7, 4)],
)
def test_correlation_strength_has_five_buckets(value, bucket):
    labels = [interpretation._correlation_strength(v) for v in [0.0, 0.1, 0.3, 0.5, 0.7]]
    assert interpretation._correlation_strength(value) == labels[bucket]


def test_generate_interpretation_handles_missing_unknown_and_descriptive_results():
    missing = interpretation.generate_interpretation({})
    unknown = interpretation.generate_interpretation(
        {"result": object(), "test_name_zh": "Custom"}
    )
    descriptive = interpretation.generate_interpretation(
        {
            "result": object(),
            "descriptive": pd.DataFrame(
                {"变量": ["score"], "N": [10], "M": [3.2], "SD": [0.5]}
            ),
        }
    )

    assert missing
    assert "Custom" in unknown
    assert "10" in descriptive and "3.2" in descriptive
