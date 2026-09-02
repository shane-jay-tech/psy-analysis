"""v5.9: 图表工厂回归测试。

覆盖两处历史崩溃：
1. bar_with_error 对独立 t 检验的 group_stats（无 SEM 列）调用
   list.tolist() → 每个独立样本 t 检验渲染必崩（AttributeError）。
2. box_plot 在配对检验分支收到 iv=None → df[None] TypeError，
   配对分析结果页渲染必崩。
"""
import pandas as pd
import numpy as np

from src.visualization.charts import bar_with_error, box_plot, contingency_heatmap


class TestBarWithError:
    def test_ttest_style_group_stats_without_sem(self):
        """独立 t 检验 group_stats：组别/N/M/SD，无 SEM → SD/√N 推导误差线。"""
        data = pd.DataFrame({
            "组别": ["实验组", "对照组"],
            "N": [60, 60],
            "M": [52.0, 44.0],
            "SD": [9.0, 9.0],
        })
        fig = bar_with_error(data, "焦虑得分", "组别")
        assert len(fig.data) == 1
        error_y = fig.data[0].error_y.array
        # SEM = 9/sqrt(60) ≈ 1.162
        assert abs(error_y[0] - 9 / np.sqrt(60)) < 1e-6
        assert list(fig.data[0].x) == ["实验组", "对照组"]

    def test_grouped_descriptive_with_sem(self):
        data = pd.DataFrame({
            "组别": ["A", "B"],
            "N": [10, 10],
            "M": [1.0, 2.0],
            "SD": [0.5, 0.5],
            "SEM": [0.158, 0.158],
        })
        fig = bar_with_error(data, "dv", "iv")
        assert fig.data[0].error_y.array[0] == 0.158

    def test_list_input_and_missing_mean_column(self):
        """list[dict] 输入、无 M 列时降级不崩。"""
        fig = bar_with_error([{"组别": "A", "N": 5, "SD": 1.0}], "dv", "iv")
        assert len(fig.data) == 1

    def test_empty_input_returns_empty_figure(self):
        fig = bar_with_error(pd.DataFrame(), "dv", "iv")
        assert len(fig.data) == 0

    def test_english_group_column_name(self):
        data = pd.DataFrame({
            "group": ["g1", "g2"],
            "M": [3.0, 4.0],
            "SEM": [0.1, 0.2],
        })
        fig = bar_with_error(data, "dv", "iv")
        assert list(fig.data[0].x) == ["g1", "g2"]


class TestBoxPlot:
    def test_iv_none_paired_columns(self):
        df = pd.DataFrame({
            "前测": np.random.default_rng(0).normal(50, 8, 60),
            "后测": np.random.default_rng(1).normal(54, 8, 60),
        })
        fig = box_plot(df, ["前测", "后测"], None)
        assert len(fig.data) == 2
        assert [t.name for t in fig.data] == ["前测", "后测"]

    def test_iv_none_single_column(self):
        df = pd.DataFrame({"得分": [1.0, 2.0, 3.0]})
        fig = box_plot(df, "得分", None)
        assert len(fig.data) == 1

    def test_grouped_box(self):
        df = pd.DataFrame({
            "组别": ["A"] * 30 + ["B"] * 30,
            "得分": np.concatenate([np.random.default_rng(0).normal(10, 2, 30),
                                    np.random.default_rng(1).normal(12, 2, 30)]),
        })
        fig = box_plot(df, "得分", "组别")
        assert len(fig.data) == 2


class TestRenderChartsIsolation:
    def test_broken_chart_data_does_not_raise(self):
        """单图数据损坏时 render_charts 应跳过该图而不是抛异常。"""
        from src.ui.renderers import render_charts
        df = pd.DataFrame({"x": [1, 2, 3]})
        charts_data = {
            "corr_matrix": [1, 2, 3],  # correlation_heatmap 无法处理 list → 跳过
            "bar_data": pd.DataFrame({"组别": ["A"], "M": [1.0]}),  # 正常渲染
        }
        render_charts(charts_data, df)  # 不抛异常即通过


class TestContingencyHeatmap:
    def test_renders_heatmap_from_crosstab(self):
        ct = pd.DataFrame(
            [[30, 5], [10, 25]],
            index=["男", "女"],
            columns=["A组", "B组"],
        )
        fig = contingency_heatmap(ct)
        assert len(fig.data) == 1
        assert fig.data[0].type == "heatmap"

    def test_empty_table_returns_empty_figure(self):
        assert len(contingency_heatmap(pd.DataFrame()).data) == 0
