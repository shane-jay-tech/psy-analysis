"""问卷导入清洗面板测试。"""

import numpy as np
import pandas as pd
import pytest

from src.questionnaire.import_cleaning import ScaleDimension, CleaningResult
from src.ui.questionnaire_import_panel import (
    _CLEANED_KEY,
    _DIMENSIONS_KEY,
    _RAW_DF_KEY,
    get_cleaned_result,
    get_cleaning_log_for_deliverable,
)
from src.questionnaire.import_cleaning import run_questionnaire_cleaning


@pytest.fixture
def session_state():
    return {}


@pytest.fixture
def sample_df():
    np.random.seed(42)
    n = 30
    return pd.DataFrame({
        "id": range(1, n + 1),
        "gender": np.random.choice(["M", "F"], n),
        "Q1": np.random.randint(1, 6, n),
        "Q2": np.random.randint(1, 6, n),
        "Q3": np.random.randint(1, 6, n),
        "Q4": np.random.randint(1, 6, n),
        "duration": np.random.randint(30, 300, n),
    })


@pytest.fixture
def dimensions():
    return [
        ScaleDimension(name="scale_a", items=["Q1", "Q2"], reverse_items=["Q2"]),
        ScaleDimension(name="scale_b", items=["Q3", "Q4"], reverse_items=[]),
    ]


class TestPanelState:
    def test_raw_df_stored(self, session_state, sample_df):
        session_state[_RAW_DF_KEY] = sample_df
        assert session_state[_RAW_DF_KEY] is not None
        assert len(session_state[_RAW_DF_KEY]) == 30

    def test_dimensions_stored(self, session_state, dimensions):
        session_state[_DIMENSIONS_KEY] = dimensions
        assert len(session_state[_DIMENSIONS_KEY]) == 2
        assert session_state[_DIMENSIONS_KEY][0].name == "scale_a"

    def test_get_cleaned_result_none_initially(self, session_state):
        assert get_cleaned_result(session_state) is None

    def test_cleaning_stored_and_retrievable(self, session_state, sample_df, dimensions):
        result = run_questionnaire_cleaning(
            sample_df, dimensions=dimensions, duration_column="duration", min_duration_seconds=60
        )
        session_state[_CLEANED_KEY] = result
        retrieved = get_cleaned_result(session_state)
        assert retrieved is not None
        assert retrieved.summary["original_n"] == 30


class TestCleaningIntegration:
    def test_full_flow_from_panel_state(self, session_state, sample_df, dimensions):
        session_state[_RAW_DF_KEY] = sample_df
        session_state[_DIMENSIONS_KEY] = dimensions
        result = run_questionnaire_cleaning(
            session_state[_RAW_DF_KEY],
            dimensions=session_state[_DIMENSIONS_KEY],
            duration_column="duration",
            min_duration_seconds=60,
        )
        session_state[_CLEANED_KEY] = result
        assert result.df_scored is not None
        assert "scale_a_mean" in result.df_scored.columns
        assert "scale_b_mean" in result.df_scored.columns

    def test_cleaning_log_for_deliverable(self, session_state, sample_df, dimensions):
        result = run_questionnaire_cleaning(sample_df, dimensions=dimensions)
        session_state[_CLEANED_KEY] = result
        log = get_cleaning_log_for_deliverable(session_state)
        assert len(log) >= 3
        assert log[0]["step"] == "列分类"

    def test_empty_deliverable_log(self, session_state):
        log = get_cleaning_log_for_deliverable(session_state)
        assert log == []

    def test_no_dimensions_still_works(self, session_state, sample_df):
        result = run_questionnaire_cleaning(sample_df)
        session_state[_CLEANED_KEY] = result
        assert result.df_scored is None
        assert result.summary["valid_n"] <= 30
