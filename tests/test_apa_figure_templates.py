"""P0-2: APA 图表生成测试。

验证三种基础图表可正确生成 PNG 并嵌入 Word。
"""

import pytest

from src.output.apa_figures import (
    APAFigure,
    generate_mean_se_figure,
    generate_group_comparison_figure,
    generate_scatter_figure,
    generate_figures_from_card,
)


class TestMeanSEFigure:
    def test_generates_png_bytes(self):
        fig = generate_mean_se_figure(
            group_labels=["男", "女"],
            means=[3.5, 4.2],
            std_errors=[0.3, 0.25],
            dv_label="焦虑得分",
            iv_label="性别",
        )
        assert isinstance(fig, APAFigure)
        assert fig.png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(fig.png_bytes) > 1000

    def test_has_correct_metadata(self):
        fig = generate_mean_se_figure(
            group_labels=["A", "B"],
            means=[10, 12],
            std_errors=[1, 1.5],
            figure_id="fig_test_1",
            recommendation_id="rec_3",
        )
        assert fig.figure_id == "fig_test_1"
        assert fig.recommendation_id == "rec_3"
        assert fig.method == "descriptive"

    def test_single_group(self):
        fig = generate_mean_se_figure(
            group_labels=["全样本"],
            means=[5.0],
            std_errors=[0.5],
        )
        assert fig.png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


class TestGroupComparisonFigure:
    def test_generates_png_with_p_value(self):
        fig = generate_group_comparison_figure(
            group_labels=["低", "中", "高"],
            means=[3.0, 4.5, 6.0],
            std_errors=[0.4, 0.3, 0.5],
            p_value=0.003,
        )
        assert fig.png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        assert fig.method == "one_way_anova"

    def test_generates_without_p_value(self):
        fig = generate_group_comparison_figure(
            group_labels=["A", "B", "C", "D"],
            means=[1, 2, 3, 4],
            std_errors=[0.1, 0.2, 0.3, 0.4],
        )
        assert fig.png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    def test_ns_result(self):
        fig = generate_group_comparison_figure(
            group_labels=["G1", "G2", "G3"],
            means=[5.0, 5.1, 4.9],
            std_errors=[0.5, 0.6, 0.4],
            p_value=0.87,
        )
        assert fig.png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


class TestScatterFigure:
    def test_generates_png_with_stats(self):
        import random
        random.seed(42)
        x = [random.gauss(0, 1) for _ in range(30)]
        y = [xi * 0.7 + random.gauss(0, 0.3) for xi in x]
        fig = generate_scatter_figure(
            x_data=x, y_data=y,
            r_value=0.85, p_value=0.001,
            x_label="焦虑", y_label="抑郁",
        )
        assert fig.png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        assert fig.method == "pearson_corr"

    def test_generates_without_stats(self):
        fig = generate_scatter_figure(
            x_data=[1, 2, 3, 4, 5],
            y_data=[2, 4, 5, 4, 5],
        )
        assert fig.png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    def test_minimal_data(self):
        fig = generate_scatter_figure(
            x_data=[1, 2],
            y_data=[3, 4],
        )
        assert len(fig.png_bytes) > 500


class TestGenerateFiguresFromCard:
    def test_ttest_card_generates_figure(self):
        card = {
            "method": "independent_ttest",
            "group_stats": [
                {"label": "实验组", "mean": 4.5, "std": 1.2, "n": 30},
                {"label": "对照组", "mean": 3.8, "std": 1.0, "n": 30},
            ],
            "dv_label": "成绩",
            "iv_label": "组别",
            "recommendation_id": "rec_1",
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
        assert figs[0].method == "descriptive"
        assert figs[0].recommendation_id == "rec_1"

    def test_anova_card_generates_figure(self):
        card = {
            "method": "one_way_anova",
            "group_stats": [
                {"label": "大一", "mean": 70, "std": 10, "n": 40},
                {"label": "大二", "mean": 75, "std": 8, "n": 40},
                {"label": "大三", "mean": 78, "std": 12, "n": 40},
            ],
            "p_value": 0.02,
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
        assert figs[0].method == "one_way_anova"

    def test_correlation_card_generates_figure(self):
        card = {
            "method": "pearson_corr",
            "x_data": [1, 2, 3, 4, 5, 6, 7],
            "y_data": [2, 3, 4, 3, 5, 6, 7],
            "r_value": 0.92,
            "p_value": 0.003,
            "x_label": "自尊",
            "y_label": "生活满意度",
        }
        figs = generate_figures_from_card(card)
        assert len(figs) == 1
        assert figs[0].method == "pearson_corr"

    def test_unknown_method_no_figure(self):
        card = {"method": "some_unknown_method"}
        figs = generate_figures_from_card(card)
        assert figs == []

    def test_empty_card_no_figure(self):
        figs = generate_figures_from_card({})
        assert figs == []

    def test_card_without_data_no_figure(self):
        card = {"method": "independent_ttest", "group_stats": []}
        figs = generate_figures_from_card(card)
        assert figs == []


class TestFigureInDocx:
    def test_docx_with_figures(self):
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.output.docx_exporter import build_deliverable_docx

        fig = generate_mean_se_figure(
            group_labels=["A", "B"],
            means=[3, 5],
            std_errors=[0.5, 0.6],
        )
        paper = PaperDraftBundle(
            title="测试论文",
            sections={"intro": PaperSection(name="引言", markdown="测试", source="t")},
            source="test",
        )
        bundle = ResearchDeliverableBundle(
            project_id="test",
            title="图表测试",
            paper_bundle=paper,
            analysis_cards=[{"method": "ttest", "apa_text": "t=2.0"}],
            figures=[fig],
        )
        docx_bytes = build_deliverable_docx(bundle, mode="standard")
        assert docx_bytes[:2] == b"PK"
        assert len(docx_bytes) > 5000
