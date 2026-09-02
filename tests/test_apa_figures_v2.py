"""P0-2: 新增 APA 图表类型测试。

验证 8 + 3 种图表: repeated_measures_line, interaction_plot,
regression_fit, mediation_path, reliability_item,
regression_diagnostics, simple_slopes, factor_loading_heatmap。
"""

import pytest
import warnings

from src.output.apa_figures import (
    APAFigure,
    generate_repeated_measures_line,
    generate_interaction_plot,
    generate_regression_fit_figure,
    generate_mediation_path_figure,
    generate_reliability_item_figure,
    generate_regression_diagnostics_figure,
    generate_simple_slopes_figure,
    generate_factor_loading_heatmap,
    generate_figures_from_card,
)


class TestRepeatedMeasuresLine:
    def test_single_group(self):
        fig = generate_repeated_measures_line(
            time_labels=["Pre", "Post", "Follow-up"],
            group_data={"All": [3.5, 4.2, 4.0]},
        )
        assert isinstance(fig, APAFigure)
        assert fig.png_bytes[:4] == b"\x89PNG"
        assert "repeated" in fig.method

    def test_multiple_groups(self):
        fig = generate_repeated_measures_line(
            time_labels=["T1", "T2", "T3"],
            group_data={"Control": [3.0, 3.1, 3.0], "Treatment": [3.0, 4.5, 4.8]},
            group_errors={"Control": [0.3, 0.3, 0.3], "Treatment": [0.3, 0.4, 0.3]},
        )
        assert fig.png_bytes[:4] == b"\x89PNG"

    def test_custom_labels(self):
        fig = generate_repeated_measures_line(
            time_labels=["Baseline", "Week 4"],
            group_data={"G1": [2.0, 3.0]},
            dv_label="Anxiety",
            time_label="Measurement Point",
        )
        assert "Anxiety" in fig.caption


class TestInteractionPlot:
    def test_basic_interaction(self):
        fig = generate_interaction_plot(
            x_labels=["Low", "High"],
            group_data={"Male": [3.0, 5.0], "Female": [4.0, 4.5]},
            dv_label="Score",
            x_factor_label="Stress",
            legend_label="Gender",
        )
        assert isinstance(fig, APAFigure)
        assert fig.png_bytes[:4] == b"\x89PNG"
        assert "two_way_anova" in fig.method

    def test_three_levels(self):
        fig = generate_interaction_plot(
            x_labels=["A1", "A2", "A3"],
            group_data={"B1": [2, 3, 5], "B2": [4, 4, 3], "B3": [3, 5, 6]},
        )
        assert fig.png_bytes[:4] == b"\x89PNG"


class TestRegressionFit:
    def test_basic_fit(self):
        x = [1, 2, 3, 4, 5, 6, 7, 8]
        y = [2.1, 3.8, 5.2, 7.1, 8.9, 10.5, 12.0, 14.2]
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig = generate_regression_fit_figure(x, y, r_squared=0.98)
        assert isinstance(fig, APAFigure)
        assert fig.png_bytes[:4] == b"\x89PNG"
        assert "regression" in fig.method
        assert not any("Glyph 178" in str(item.message) for item in caught)

    def test_with_predicted(self):
        x = [1, 2, 3, 4, 5]
        y = [2.0, 4.1, 5.9, 8.1, 10.2]
        y_pred = [2.0, 4.0, 6.0, 8.0, 10.0]
        fig = generate_regression_fit_figure(x, y, y_pred=y_pred)
        assert fig.png_bytes[:4] == b"\x89PNG"

    def test_custom_labels(self):
        fig = generate_regression_fit_figure(
            [1, 2, 3], [2, 4, 6],
            x_label="Self-Esteem",
            y_label="Life Satisfaction",
        )
        assert "Self-Esteem" in fig.caption


class TestMediationPath:
    def test_full_model(self):
        fig = generate_mediation_path_figure(
            x_name="Stress",
            m_name="Coping",
            y_name="Depression",
            a_coef=0.45,
            b_coef=-0.38,
            c_prime=0.12,
            indirect=-0.171,
        )
        assert isinstance(fig, APAFigure)
        assert fig.png_bytes[:4] == b"\x89PNG"
        assert "mediation" in fig.method

    def test_partial_coefficients(self):
        fig = generate_mediation_path_figure(
            x_name="X", m_name="M", y_name="Y",
            a_coef=0.5, b_coef=None, c_prime=0.3, indirect=None,
        )
        assert fig.png_bytes[:4] == b"\x89PNG"

    def test_default_names(self):
        fig = generate_mediation_path_figure()
        assert "X" in fig.caption and "Y" in fig.caption


class TestReliabilityItem:
    def test_basic_item_analysis(self):
        fig = generate_reliability_item_figure(
            item_labels=["Q1", "Q2", "Q3", "Q4", "Q5"],
            item_total_corrs=[0.65, 0.72, 0.45, 0.58, 0.80],
        )
        assert isinstance(fig, APAFigure)
        assert fig.png_bytes[:4] == b"\x89PNG"
        assert "reliability" in fig.method

    def test_with_alpha_if_deleted(self):
        fig = generate_reliability_item_figure(
            item_labels=["I1", "I2", "I3", "I4"],
            item_total_corrs=[0.55, 0.62, 0.70, 0.48],
            alpha_if_deleted=[0.82, 0.80, 0.78, 0.85],
            overall_alpha=0.81,
        )
        assert fig.png_bytes[:4] == b"\x89PNG"

    def test_many_items(self):
        items = [f"Item{i}" for i in range(1, 16)]
        corrs = [0.4 + i * 0.02 for i in range(15)]
        fig = generate_reliability_item_figure(items, corrs)
        assert fig.png_bytes[:4] == b"\x89PNG"


class TestRegressionDiagnostics:
    def test_basic_diagnostics(self):
        residuals = [0.1, -0.3, 0.2, -0.1, 0.4, -0.2, 0.0, 0.3]
        fitted = [2.0, 3.5, 5.0, 6.5, 8.0, 9.5, 11.0, 12.5]
        fig = generate_regression_diagnostics_figure(residuals, fitted)
        assert isinstance(fig, APAFigure)
        assert fig.png_bytes[:4] == b"\x89PNG"
        assert "diagnostics" in fig.method

    def test_large_sample(self):
        import numpy as np
        np.random.seed(42)
        residuals = list(np.random.randn(100))
        fitted = list(np.linspace(1, 10, 100))
        fig = generate_regression_diagnostics_figure(residuals, fitted)
        assert len(fig.png_bytes) > 1000

    def test_custom_title(self):
        fig = generate_regression_diagnostics_figure(
            [0.1, -0.1, 0.2], [1.0, 2.0, 3.0],
            title="Figure 3. Regression diagnostics for Model 1."
        )
        assert "Model 1" in fig.caption


class TestSimpleSlopes:
    def test_default_slopes(self):
        fig = generate_simple_slopes_figure()
        assert isinstance(fig, APAFigure)
        assert fig.png_bytes[:4] == b"\x89PNG"
        assert "moderation" in fig.method

    def test_custom_slopes(self):
        slopes = {
            "High (+1SD)": (1.0, 0.9),
            "Mean": (2.0, 0.5),
            "Low (-1SD)": (3.0, 0.1),
        }
        fig = generate_simple_slopes_figure(
            slopes=slopes,
            x_label="Workload",
            y_label="Stress",
            moderator_label="Resilience",
        )
        assert "Workload" in fig.caption
        assert "Resilience" in fig.caption

    def test_two_levels(self):
        slopes = {"High": (1.0, 0.8), "Low": (2.0, 0.2)}
        fig = generate_simple_slopes_figure(slopes=slopes)
        assert fig.png_bytes[:4] == b"\x89PNG"

    def test_custom_range(self):
        fig = generate_simple_slopes_figure(x_range=(0, 7))
        assert fig.png_bytes[:4] == b"\x89PNG"


class TestFactorLoadingHeatmap:
    def test_two_factors(self):
        loadings = [
            [0.82, 0.1], [0.75, 0.2], [0.68, 0.15],
            [0.1, 0.85], [0.2, 0.78], [0.05, 0.72],
        ]
        items = ["Item1", "Item2", "Item3", "Item4", "Item5", "Item6"]
        fig = generate_factor_loading_heatmap(loadings, items)
        assert isinstance(fig, APAFigure)
        assert fig.png_bytes[:4] == b"\x89PNG"
        assert "efa" in fig.method

    def test_custom_factor_labels(self):
        loadings = [[0.8, 0.1, 0.0], [0.1, 0.9, 0.1], [0.0, 0.1, 0.85]]
        items = ["A", "B", "C"]
        fig = generate_factor_loading_heatmap(
            loadings, items,
            factor_labels=["Cognitive", "Affective", "Behavioral"],
        )
        assert "loading" in fig.caption.lower()

    def test_many_items(self):
        import numpy as np
        np.random.seed(42)
        loadings = np.random.uniform(-0.3, 0.9, (12, 3)).tolist()
        items = [f"Q{i}" for i in range(1, 13)]
        fig = generate_factor_loading_heatmap(loadings, items)
        assert len(fig.png_bytes) > 1000

    def test_negative_loadings(self):
        loadings = [[-0.7, 0.2], [0.8, -0.1], [-0.5, 0.6]]
        items = ["R1", "R2", "R3"]
        fig = generate_factor_loading_heatmap(loadings, items)
        assert fig.png_bytes[:4] == b"\x89PNG"


class TestFiguresFromCardV2:
    def test_repeated_measures_card(self):
        card = {
            "method": "repeated_anova",
            "time_labels": ["Pre", "Post"],
            "group_data": {"Group": [3.0, 4.5]},
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
        assert figs[0].method == "repeated_measures"

    def test_two_way_anova_card(self):
        card = {
            "method": "two_way_anova",
            "x_labels": ["Low", "High"],
            "interaction_data": {"M": [3, 5], "F": [4, 4]},
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
        assert figs[0].method == "two_way_anova"

    def test_regression_card(self):
        card = {
            "method": "multiple_regression",
            "x_data": [1, 2, 3, 4, 5],
            "y_data": [2, 4, 5, 7, 9],
            "r_squared": 0.95,
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
        assert figs[0].method == "regression"

    def test_mediation_card(self):
        card = {
            "method": "mediation",
            "x_name": "A",
            "m_name": "B",
            "y_name": "C",
            "a_coef": 0.4,
            "b_coef": 0.3,
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
        assert figs[0].method == "mediation"

    def test_reliability_card(self):
        card = {
            "method": "cronbach_alpha",
            "item_labels": ["Q1", "Q2", "Q3"],
            "item_total_corrs": [0.5, 0.6, 0.7],
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
        assert figs[0].method == "reliability"

    def test_empty_data_no_crash(self):
        card = {"method": "two_way_anova", "x_labels": [], "interaction_data": {}}
        figs = generate_figures_from_card(card)
        assert figs == []

    def test_moderation_card(self):
        card = {
            "method": "moderation",
            "simple_slopes": {
                "High (+1SD)": (2.0, 0.8),
                "Mean": (2.5, 0.4),
                "Low (-1SD)": (3.0, 0.05),
            },
            "x_label": "Job Demands",
            "y_label": "Burnout",
            "moderator_label": "Social Support",
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
        assert figs[0].method == "moderation"

    def test_efa_card(self):
        card = {
            "method": "efa",
            "factor_loadings": [
                [0.82, 0.1], [0.75, 0.2], [0.1, 0.85], [0.2, 0.78],
            ],
            "item_labels": ["Q1", "Q2", "Q3", "Q4"],
            "factor_labels": ["Engagement", "Satisfaction"],
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
        assert figs[0].method == "efa"

    def test_regression_with_diagnostics(self):
        card = {
            "method": "multiple_regression",
            "x_data": [1, 2, 3, 4, 5, 6, 7, 8],
            "y_data": [2, 4, 5, 7, 9, 11, 12, 14],
            "r_squared": 0.97,
            "residuals": [0.1, -0.2, 0.3, -0.1, 0.0, 0.2, -0.3, 0.1],
            "fitted_values": [1.9, 4.2, 4.7, 7.1, 9.0, 10.8, 12.3, 13.9],
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 2
        methods = [f.method for f in figs]
        assert "regression" in methods
        assert "regression_diagnostics" in methods

    def test_original_methods_still_work(self):
        card = {
            "method": "one_way_anova",
            "group_stats": [
                {"label": "A", "mean": 3.0, "se": 0.5},
                {"label": "B", "mean": 4.0, "se": 0.4},
            ],
            "p_value": 0.03,
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
