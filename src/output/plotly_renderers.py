"""Plotly 交互式图表渲染器 — 用于报告导出和 UI 展示"""

import pandas as pd
import numpy as np

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False
    go = None

from src.visualization.charts import (
    correlation_heatmap,
    interaction_plot,
    _base_layout,
    FONT,
    TITLE_FONT,
    COLOR_PALETTE,
    CHART_HEIGHT,
)
from src.analysis.meta_analysis import MetaResult


def plotly_correlation_heatmap(
    corr_matrix: pd.DataFrame,
    sig_mask: pd.DataFrame = None,
    title: str = "相关矩阵热力图",
) -> "go.Figure | None":
    """相关矩阵热力图（Plotly 交互式）"""
    if not HAS_PLOTLY:
        return None
    return correlation_heatmap(corr_matrix, sig_mask=sig_mask, title=title)


def plotly_interaction_plot(
    df: pd.DataFrame,
    dv: str,
    iv1: str,
    iv2: str,
    title: str = "交互作用图",
) -> "go.Figure | None":
    """双因素交互效应图（Plotly 交互式）"""
    if not HAS_PLOTLY:
        return None
    return interaction_plot(df, dv, iv1, iv2, title=title)


def plotly_meta_forest(
    result: MetaResult,
    title: str = "元分析森林图",
) -> "go.Figure | None":
    """元分析森林图（Plotly 交互式）

    显示各研究效应量、95% CI、权重，以及汇总效应量菱形。
    """
    if not HAS_PLOTLY:
        return None

    fig = go.Figure()

    k = result.k
    y_positions = list(range(k, 0, -1))

    # 各研究
    for i, (y, effect, (ci_l, ci_u), weight) in enumerate(
        zip(y_positions, result.study_effects, result.study_cis, result.study_weights)
    ):
        marker_size = max(8, min(20, weight / 5))
        color = COLOR_PALETTE[0] if result.study_weights[i] > 10 else "#666"

        fig.add_trace(go.Scatter(
            x=[effect],
            y=[y],
            mode="markers",
            name=result.study_labels[i],
            marker=dict(size=marker_size, color=color),
            showlegend=False,
            hovertemplate=(
                f"{result.study_labels[i]}<br>"
                f"效应量={effect:.3f}<br>"
                f"95%CI: [{ci_l:.3f}, {ci_u:.3f}]<br>"
                f"权重={weight:.1f}%<extra></extra>"
            ),
        ))

        # 误差线（CI）
        fig.add_trace(go.Scatter(
            x=[ci_l, ci_u],
            y=[y, y],
            mode="lines",
            line=dict(color="black", width=1.5),
            showlegend=False,
            hoverinfo="skip",
        ))

    # 汇总效应量（菱形）
    y_summary = 0
    summ = result.pooled_effect
    ci_l = result.ci_lower
    ci_u = result.ci_upper

    diamond_x = [ci_l, summ, ci_u, summ, ci_l]
    diamond_y = [y_summary, y_summary + 0.4, y_summary, y_summary - 0.4, y_summary]

    fig.add_trace(go.Scatter(
        x=diamond_x,
        y=diamond_y,
        fill="toself",
        fillcolor="rgba(0,0,0,0.8)",
        line=dict(color="black", width=1),
        name="汇总效应",
        showlegend=False,
        hovertemplate=(
            f"汇总 ({result.model.upper()})<br>"
            f"效应量={summ:.3f}<br>"
            f"95%CI: [{ci_l:.3f}, {ci_u:.3f}]<extra></extra>"
        ),
    ))

    # 零参考线
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)

    all_y = y_positions + [y_summary]
    all_labels = result.study_labels + [
        f"汇总 ({result.model.upper()}) [{result.ci_lower:.3f}, {result.ci_upper:.3f}]"
    ]

    if result.effect_type == "d":
        xlabel = "Cohen's d"
    elif result.effect_type == "z":
        xlabel = "Fisher's z"
    else:
        xlabel = "r"

    fig.update_layout(
        title=dict(
            text=(
                f"{title}<br><sup>"
                f"{result.model.upper()}模型, k={result.k}, "
                f"I²={result.i_squared:.1f}%, "
                f"Q({result.q_df})={result.q_statistic:.2f}, p={result.q_p_value:.4f}</sup>"
            ),
            font=TITLE_FONT,
        ),
        template="simple_white",
        height=max(400, k * 40 + 150),
        font=FONT,
        xaxis=dict(title=dict(text=f"{xlabel} (95% CI)", font=FONT)),
        yaxis=dict(
            tickmode="array",
            tickvals=all_y,
            ticktext=all_labels,
        ),
        hoverlabel=dict(font=FONT),
        margin=dict(l=180),
    )

    return fig
