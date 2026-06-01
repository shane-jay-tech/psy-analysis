"""Session State 内存管理测试"""

import pytest
import pandas as pd
import streamlit as st

from src.utils.memory_manager import (
    _estimate_obj_size,
    estimate_session_state_memory,
    auto_cleanup_session_state,
)


class TestEstimateObjSize:
    def test_dataframe_size(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        size = _estimate_obj_size(df)
        assert size > 0

    def test_int_size(self):
        assert _estimate_obj_size(42) > 0

    def test_none_size(self):
        # None has a small but non-zero size in CPython
        assert _estimate_obj_size(None) >= 0


class TestSessionStateMemory:
    def test_estimate_session_state_memory(self):
        st.session_state.clear()
        st.session_state.df = pd.DataFrame({"x": [1, 2]})
        st.session_state.meta = {"key": "value"}
        mem = estimate_session_state_memory()
        assert mem["total_bytes"] > 0
        assert "df" in mem["items"]
        assert "meta" in mem["items"]

    def test_auto_cleanup_history(self):
        st.session_state.clear()
        st.session_state.analysis_history = [{"i": i} for i in range(30)]
        result = auto_cleanup_session_state(max_history=10)
        assert len(st.session_state.analysis_history) == 10
        assert "analysis_history" in str(result["cleaned_keys"])

    def test_auto_cleanup_pending(self):
        st.session_state.clear()
        from concurrent.futures import Future
        f = Future()
        f.set_result(None)
        st.session_state._q_design_pending = {"future": f, "cancel_id": 1}
        result = auto_cleanup_session_state()
        assert "_q_design_pending" in result["cleaned_keys"]
        assert "_q_design_pending" not in st.session_state
