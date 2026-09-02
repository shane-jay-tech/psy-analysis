"""5 分钟引导路径测试。"""

from __future__ import annotations

import pytest
import streamlit as st

from src.ui.onboarding import (
    is_first_visit, mark_onboarding_done, restart_onboarding, skip_onboarding,
    FORCE_SHOW_KEY, ONBOARDING_KEY, ONBOARDING_STAGE_KEY, SKIP_KEY,
)


@pytest.fixture(autouse=True)
def clean_session(tmp_path, monkeypatch):
    from src.utils import user_prefs
    prefs_dir = tmp_path / ".psy_analysis"
    monkeypatch.setattr(user_prefs, "PREFS_DIR", prefs_dir)
    monkeypatch.setattr(user_prefs, "PREFS_FILE", prefs_dir / "user_prefs.json")
    st.session_state.clear()
    yield
    st.session_state.clear()


def test_is_first_visit_true_for_clean_session():
    assert is_first_visit() is True


def test_is_first_visit_false_when_skipped():
    st.session_state[SKIP_KEY] = True
    assert is_first_visit() is False


def test_is_first_visit_false_when_onboarding_done():
    st.session_state[ONBOARDING_KEY] = True
    assert is_first_visit() is False


def test_is_first_visit_false_when_df_loaded():
    """已上传数据时不再显示引导。"""
    import pandas as pd
    st.session_state.df = pd.DataFrame({"x": [1, 2, 3]})
    assert is_first_visit() is False


def test_is_first_visit_false_when_analysis_history():
    st.session_state.analysis_history = [{"test_type": "t"}]
    assert is_first_visit() is False


def test_mark_onboarding_done_sets_flag():
    st.session_state[ONBOARDING_STAGE_KEY] = "running"
    mark_onboarding_done()
    assert st.session_state.get(ONBOARDING_KEY) is True
    assert ONBOARDING_STAGE_KEY not in st.session_state


def test_skip_onboarding_marks_both_flags():
    skip_onboarding()
    assert st.session_state.get(SKIP_KEY) is True
    assert st.session_state.get(ONBOARDING_KEY) is True
    assert is_first_visit() is False


def test_restart_onboarding_forces_show_even_with_existing_data():
    import pandas as pd
    st.session_state[ONBOARDING_KEY] = True
    st.session_state[SKIP_KEY] = True
    st.session_state.df = pd.DataFrame({"x": [1]})
    restart_onboarding()
    assert st.session_state[FORCE_SHOW_KEY] is True
    assert is_first_visit() is True
