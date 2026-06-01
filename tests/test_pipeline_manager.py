"""分析 Pipeline 保存与复跑测试"""

import pytest
import pandas as pd
import streamlit as st

from src.parser.intent_resolver import AnalysisPlan
from src.utils.pipeline_manager import (
    save_current_analysis_to_pipeline,
    replay_pipeline,
    export_pipeline,
    import_pipeline,
    clear_pipeline,
    AnalysisPipeline,
)


class TestPipelineManager:
    def test_save_and_replay_pipeline(self):
        st.session_state.clear()
        st.session_state.df = pd.DataFrame({
            "group": ["A", "A", "B", "B"],
            "score": [1, 2, 3, 4],
        })
        plan = AnalysisPlan(
            test_type="independent_ttest",
            dependent_vars=["score"],
            independent_vars=["group"],
        )
        output = {"test_type": "independent_ttest", "test_name_zh": "独立样本t检验"}
        st.session_state.plan = plan
        st.session_state.analysis_output = output

        assert save_current_analysis_to_pipeline() is True
        pipeline = st.session_state.analysis_pipeline
        assert isinstance(pipeline, AnalysisPipeline)
        assert len(pipeline.steps) == 1

        results = replay_pipeline()
        assert len(results) == 1
        assert results[0]["success"] is True

    def test_export_import_roundtrip(self):
        st.session_state.clear()
        st.session_state.df = pd.DataFrame({"x": [1, 2]})
        plan = AnalysisPlan(test_type="descriptive")
        st.session_state.plan = plan
        st.session_state.analysis_output = {"test_type": "descriptive"}
        save_current_analysis_to_pipeline()

        json_str = export_pipeline()
        assert "descriptive" in json_str

        clear_pipeline()
        assert len(st.session_state.analysis_pipeline.steps) == 0

        assert import_pipeline(json_str) is True
        assert len(st.session_state.analysis_pipeline.steps) == 1

    def test_replay_without_pipeline(self):
        st.session_state.clear()
        st.session_state.df = pd.DataFrame({"x": [1, 2]})
        results = replay_pipeline()
        assert results == []

    def test_save_without_output(self):
        st.session_state.clear()
        assert save_current_analysis_to_pipeline() is False
