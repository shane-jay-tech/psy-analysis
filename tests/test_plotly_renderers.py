"""Plotly 交互式图表渲染器测试"""

import pytest
import pandas as pd
import numpy as np

from src.output.plotly_renderers import (
    plotly_correlation_heatmap,
    plotly_interaction_plot,
    plotly_meta_forest,
    HAS_PLOTLY,
)
from src.analysis.meta_analysis import MetaResult


class TestPlotlyCorrelationHeatmap:
    def test_returns_figure(self):
        df = pd.DataFrame(
            np.random.randn(5, 3),
            columns=["A", "B", "C"],
        )
        corr = df.corr()
        fig = plotly_correlation_heatmap(corr)
        if HAS_PLOTLY:
            assert fig is not None
            assert hasattr(fig, "data")
        else:
            assert fig is None

    def test_with_sig_mask(self):
        df = pd.DataFrame(
            np.random.randn(5, 3),
            columns=["A", "B", "C"],
        )
        corr = df.corr()
        sig = pd.DataFrame("*", index=corr.index, columns=corr.columns)
        fig = plotly_correlation_heatmap(corr, sig_mask=sig, title="测试热力图")
        if HAS_PLOTLY:
            assert fig is not None


class TestPlotlyInteractionPlot:
    def test_returns_figure(self):
        df = pd.DataFrame({
            "dv": [1, 2, 3, 4, 5, 6],
            "iv1": ["A", "A", "B", "B", "A", "B"],
            "iv2": ["X", "Y", "X", "Y", "X", "Y"],
        })
        fig = plotly_interaction_plot(df, "dv", "iv1", "iv2")
        if HAS_PLOTLY:
            assert fig is not None
            assert hasattr(fig, "data")
        else:
            assert fig is None


class TestPlotlyMetaForest:
    def test_returns_figure(self):
        result = MetaResult(
            model="random",
            effect_type="d",
            k=3,
            pooled_effect=0.5,
            pooled_se=0.1,
            ci_lower=0.3,
            ci_upper=0.7,
            z_value=5.0,
            p_value=0.001,
            q_statistic=2.0,
            q_df=2,
            q_p_value=0.5,
            i_squared=0.0,
            tau_squared=0.0,
            study_weights=[33.3, 33.3, 33.4],
            study_effects=[0.4, 0.5, 0.6],
            study_cis=[(0.2, 0.6), (0.3, 0.7), (0.4, 0.8)],
            study_labels=["Study 1", "Study 2", "Study 3"],
        )
        fig = plotly_meta_forest(result)
        if HAS_PLOTLY:
            assert fig is not None
            assert hasattr(fig, "data")
            assert hasattr(fig, "layout")
        else:
            assert fig is None

    def test_fixed_effect_model(self):
        result = MetaResult(
            model="fixed",
            effect_type="r",
            k=2,
            pooled_effect=0.3,
            pooled_se=0.05,
            ci_lower=0.2,
            ci_upper=0.4,
            z_value=6.0,
            p_value=0.0001,
            q_statistic=1.0,
            q_df=1,
            q_p_value=0.3,
            i_squared=0.0,
            tau_squared=0.0,
            study_weights=[50.0, 50.0],
            study_effects=[0.28, 0.32],
            study_cis=[(0.18, 0.38), (0.22, 0.42)],
            study_labels=["A", "B"],
        )
        fig = plotly_meta_forest(result, title="固定效应森林图")
        if HAS_PLOTLY:
            assert fig is not None

    def test_k_zero_edge_case(self):
        result = MetaResult(
            model="fixed",
            effect_type="d",
            k=0,
            pooled_effect=0.0,
            pooled_se=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            z_value=0.0,
            p_value=1.0,
            q_statistic=0.0,
            q_df=0,
            q_p_value=1.0,
            i_squared=0.0,
            tau_squared=0.0,
            study_weights=[],
            study_effects=[],
            study_cis=[],
            study_labels=[],
        )
        fig = plotly_meta_forest(result)
        if HAS_PLOTLY:
            assert fig is not None
