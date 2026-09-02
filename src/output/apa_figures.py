"""APA 风格图表生成器 — 11 种统计图表。

根据 AnalysisResultCard 数据生成 matplotlib 图表（PNG bytes），
用于嵌入 Word 交付包和 ZIP 归档。
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


@dataclass
class APAFigure:
    """APA 图表数据结构。"""
    figure_id: str
    title: str
    caption: str
    png_bytes: bytes
    method: str
    recommendation_id: str = ""


def _apply_apa_style(ax: plt.Axes):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=4)
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=0.3, linewidth=0.5)


def generate_mean_se_figure(
    group_labels: list[str],
    means: list[float],
    std_errors: list[float],
    dv_label: str = "Score",
    iv_label: str = "Group",
    title: str = "",
    figure_id: str = "fig_mean_se",
    recommendation_id: str = "",
) -> APAFigure:
    """生成均值和标准误柱状图。"""
    fig, ax = plt.subplots(figsize=(5, 4), dpi=150)
    x = np.arange(len(group_labels))
    bars = ax.bar(x, means, yerr=std_errors, capsize=4,
                  color="#4C72B0", edgecolor="black", linewidth=0.5, width=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(group_labels, fontsize=9)
    ax.set_ylabel(dv_label, fontsize=10)
    ax.set_xlabel(iv_label, fontsize=10)
    _apply_apa_style(ax)
    fig.tight_layout()

    caption = title or f"Figure. Mean {dv_label} by {iv_label}. Error bars represent ±1 SE."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id,
        title=caption,
        caption=caption,
        png_bytes=buf.getvalue(),
        method="descriptive",
        recommendation_id=recommendation_id,
    )


def generate_group_comparison_figure(
    group_labels: list[str],
    means: list[float],
    std_errors: list[float],
    p_value: Optional[float] = None,
    dv_label: str = "Score",
    iv_label: str = "Group",
    title: str = "",
    figure_id: str = "fig_group_comp",
    recommendation_id: str = "",
) -> APAFigure:
    """生成组间比较图（ANOVA 用）。"""
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    x = np.arange(len(group_labels))
    colors = plt.cm.Set2(np.linspace(0, 1, len(group_labels)))
    bars = ax.bar(x, means, yerr=std_errors, capsize=4,
                  color=colors, edgecolor="black", linewidth=0.5, width=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(group_labels, fontsize=9)
    ax.set_ylabel(dv_label, fontsize=10)
    ax.set_xlabel(iv_label, fontsize=10)
    _apply_apa_style(ax)

    if p_value is not None:
        sig_label = "***" if p_value < .001 else "**" if p_value < .01 else "*" if p_value < .05 else "ns"
        ax.text(0.95, 0.95, f"p = {p_value:.3f} ({sig_label})",
                transform=ax.transAxes, ha="right", va="top", fontsize=8,
                style="italic")

    fig.tight_layout()
    caption = title or f"Figure. Group comparison of {dv_label} across {iv_label}. Error bars represent ±1 SE."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id,
        title=caption,
        caption=caption,
        png_bytes=buf.getvalue(),
        method="one_way_anova",
        recommendation_id=recommendation_id,
    )


def generate_scatter_figure(
    x_data: list[float],
    y_data: list[float],
    r_value: Optional[float] = None,
    p_value: Optional[float] = None,
    x_label: str = "X",
    y_label: str = "Y",
    title: str = "",
    figure_id: str = "fig_scatter",
    recommendation_id: str = "",
) -> APAFigure:
    """生成相关散点图。"""
    fig, ax = plt.subplots(figsize=(5, 4.5), dpi=150)
    ax.scatter(x_data, y_data, alpha=0.6, edgecolors="black", linewidth=0.3,
               s=40, color="#4C72B0")

    if len(x_data) >= 2:
        z = np.polyfit(x_data, y_data, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(x_data), max(x_data), 100)
        ax.plot(x_line, p(x_line), "--", color="#C44E52", linewidth=1.2)

    ax.set_xlabel(x_label, fontsize=10)
    ax.set_ylabel(y_label, fontsize=10)
    _apply_apa_style(ax)

    if r_value is not None:
        stat_text = f"r = {r_value:.2f}"
        if p_value is not None:
            stat_text += f", p = {p_value:.3f}"
        ax.text(0.05, 0.95, stat_text, transform=ax.transAxes,
                ha="left", va="top", fontsize=9, style="italic")

    fig.tight_layout()
    caption = title or f"Figure. Scatter plot of {x_label} and {y_label} with best-fit line."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id,
        title=caption,
        caption=caption,
        png_bytes=buf.getvalue(),
        method="pearson_corr",
        recommendation_id=recommendation_id,
    )


def generate_repeated_measures_line(
    time_labels: list[str],
    group_data: dict[str, list[float]],
    group_errors: Optional[dict[str, list[float]]] = None,
    dv_label: str = "Score",
    time_label: str = "Time",
    title: str = "",
    figure_id: str = "fig_repeated_line",
    recommendation_id: str = "",
) -> APAFigure:
    """生成重复测量折线图（含多组时展示各组趋势）。"""
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    colors = ["#4C72B0", "#C44E52", "#55A868", "#8172B2", "#CCB974"]
    markers = ["o", "s", "^", "D", "v"]

    x = np.arange(len(time_labels))
    for i, (group_name, means) in enumerate(group_data.items()):
        color = colors[i % len(colors)]
        marker = markers[i % len(markers)]
        errors = group_errors.get(group_name) if group_errors else None
        if errors:
            ax.errorbar(x, means, yerr=errors, label=group_name,
                        color=color, marker=marker, capsize=3, linewidth=1.5, markersize=6)
        else:
            ax.plot(x, means, label=group_name,
                    color=color, marker=marker, linewidth=1.5, markersize=6)

    ax.set_xticks(x)
    ax.set_xticklabels(time_labels, fontsize=9)
    ax.set_ylabel(dv_label, fontsize=10)
    ax.set_xlabel(time_label, fontsize=10)
    if len(group_data) > 1:
        ax.legend(frameon=False, fontsize=8)
    _apply_apa_style(ax)
    fig.tight_layout()

    caption = title or f"Figure. {dv_label} across {time_label}. Error bars represent ±1 SE."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id, title=caption, caption=caption,
        png_bytes=buf.getvalue(), method="repeated_measures",
        recommendation_id=recommendation_id,
    )


def generate_interaction_plot(
    x_labels: list[str],
    group_data: dict[str, list[float]],
    dv_label: str = "Score",
    x_factor_label: str = "Factor A",
    legend_label: str = "Factor B",
    title: str = "",
    figure_id: str = "fig_interaction",
    recommendation_id: str = "",
) -> APAFigure:
    """生成交互作用图（双因素 ANOVA / 调节分析）。"""
    fig, ax = plt.subplots(figsize=(5.5, 4), dpi=150)
    colors = ["#4C72B0", "#C44E52", "#55A868", "#8172B2"]
    line_styles = ["-", "--", "-.", ":"]

    x = np.arange(len(x_labels))
    for i, (group_name, means) in enumerate(group_data.items()):
        ax.plot(x, means, label=group_name,
                color=colors[i % len(colors)],
                linestyle=line_styles[i % len(line_styles)],
                marker="o", linewidth=1.8, markersize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=9)
    ax.set_ylabel(dv_label, fontsize=10)
    ax.set_xlabel(x_factor_label, fontsize=10)
    ax.legend(title=legend_label, frameon=False, fontsize=8)
    _apply_apa_style(ax)
    fig.tight_layout()

    caption = title or f"Figure. Interaction of {x_factor_label} and {legend_label} on {dv_label}."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id, title=caption, caption=caption,
        png_bytes=buf.getvalue(), method="two_way_anova",
        recommendation_id=recommendation_id,
    )


def generate_regression_fit_figure(
    x_data: list[float],
    y_data: list[float],
    y_pred: Optional[list[float]] = None,
    r_squared: Optional[float] = None,
    x_label: str = "Predictor",
    y_label: str = "Outcome",
    title: str = "",
    figure_id: str = "fig_regression",
    recommendation_id: str = "",
) -> APAFigure:
    """生成回归拟合图（散点 + 回归线 + 置信带）。"""
    fig, ax = plt.subplots(figsize=(5, 4.5), dpi=150)
    ax.scatter(x_data, y_data, alpha=0.5, edgecolors="black", linewidth=0.3,
               s=35, color="#4C72B0", label="Observed")

    x_arr = np.array(x_data)
    y_arr = np.array(y_data)
    if y_pred is not None:
        sort_idx = np.argsort(x_arr)
        ax.plot(x_arr[sort_idx], np.array(y_pred)[sort_idx],
                color="#C44E52", linewidth=1.8, label="Predicted")
    elif len(x_data) >= 2:
        z = np.polyfit(x_data, y_data, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(x_data), max(x_data), 100)
        ax.plot(x_line, p(x_line), color="#C44E52", linewidth=1.8, label="Fit")
        residuals = y_arr - p(x_arr)
        se = np.std(residuals)
        ax.fill_between(x_line, p(x_line) - 1.96 * se, p(x_line) + 1.96 * se,
                        alpha=0.1, color="#C44E52")

    ax.set_xlabel(x_label, fontsize=10)
    ax.set_ylabel(y_label, fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    _apply_apa_style(ax)

    if r_squared is not None:
        # 用 mathtext 渲染上标，避免中文字体缺少 Unicode ² 导致导出方框。
        ax.text(0.05, 0.95, rf"$R^2$ = {r_squared:.3f}",
                transform=ax.transAxes, ha="left", va="top", fontsize=9, style="italic")

    fig.tight_layout()
    caption = title or f"Figure. Regression fit: {y_label} predicted by {x_label}."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id, title=caption, caption=caption,
        png_bytes=buf.getvalue(), method="regression",
        recommendation_id=recommendation_id,
    )


def generate_mediation_path_figure(
    x_name: str = "X",
    m_name: str = "M",
    y_name: str = "Y",
    a_coef: Optional[float] = None,
    b_coef: Optional[float] = None,
    c_prime: Optional[float] = None,
    indirect: Optional[float] = None,
    title: str = "",
    figure_id: str = "fig_mediation",
    recommendation_id: str = "",
) -> APAFigure:
    """生成中介效应路径图。"""
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=150)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    box_style = dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="black", linewidth=1.2)
    ax.text(1, 3, x_name, fontsize=11, ha="center", va="center", bbox=box_style)
    ax.text(5, 5.5, m_name, fontsize=11, ha="center", va="center", bbox=box_style)
    ax.text(9, 3, y_name, fontsize=11, ha="center", va="center", bbox=box_style)

    ax.annotate("", xy=(4, 5.2), xytext=(1.8, 3.5),
                arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(8.2, 3.5), xytext=(6, 5.2),
                arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(8, 3), xytext=(2, 3),
                arrowprops=dict(arrowstyle="->", lw=1.2, linestyle="dashed"))

    if a_coef is not None:
        ax.text(2.5, 4.8, f"a = {a_coef:.3f}", fontsize=9, ha="center")
    if b_coef is not None:
        ax.text(7.2, 4.8, f"b = {b_coef:.3f}", fontsize=9, ha="center")
    if c_prime is not None:
        ax.text(5, 2.3, f"c' = {c_prime:.3f}", fontsize=9, ha="center")
    if indirect is not None:
        ax.text(5, 1.2, f"indirect (ab) = {indirect:.3f}", fontsize=8,
                ha="center", style="italic", color="#C44E52")

    fig.tight_layout()
    caption = title or f"Figure. Mediation model: {x_name} → {m_name} → {y_name}."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id, title=caption, caption=caption,
        png_bytes=buf.getvalue(), method="mediation",
        recommendation_id=recommendation_id,
    )


def generate_reliability_item_figure(
    item_labels: list[str],
    item_total_corrs: list[float],
    alpha_if_deleted: Optional[list[float]] = None,
    overall_alpha: Optional[float] = None,
    title: str = "",
    figure_id: str = "fig_reliability",
    recommendation_id: str = "",
) -> APAFigure:
    """生成信度条目分析图（题总相关 + 删除后 α）。"""
    fig, ax1 = plt.subplots(figsize=(7, 4), dpi=150)
    x = np.arange(len(item_labels))

    bars = ax1.bar(x, item_total_corrs, color="#4C72B0", edgecolor="black",
                   linewidth=0.5, width=0.6, alpha=0.8, label="Item-Total Correlation")
    ax1.set_ylabel("Item-Total r", fontsize=10, color="#4C72B0")
    ax1.axhline(y=0.3, color="#4C72B0", linestyle="--", alpha=0.5, linewidth=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(item_labels, fontsize=8, rotation=45 if len(item_labels) > 6 else 0)
    _apply_apa_style(ax1)

    if alpha_if_deleted:
        ax2 = ax1.twinx()
        ax2.plot(x, alpha_if_deleted, color="#C44E52", marker="D",
                 markersize=5, linewidth=1.2, label="α if deleted")
        ax2.set_ylabel("Cronbach's α if item deleted", fontsize=10, color="#C44E52")
        if overall_alpha is not None:
            ax2.axhline(y=overall_alpha, color="#C44E52", linestyle=":",
                        alpha=0.5, linewidth=0.8)
        ax2.spines["top"].set_visible(False)

    fig.tight_layout()
    caption = title or "Figure. Item analysis: item-total correlations and alpha if item deleted."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id, title=caption, caption=caption,
        png_bytes=buf.getvalue(), method="reliability",
        recommendation_id=recommendation_id,
    )


def generate_regression_diagnostics_figure(
    residuals: list[float],
    fitted_values: list[float],
    title: str = "",
    figure_id: str = "fig_regression_diag",
    recommendation_id: str = "",
) -> APAFigure:
    """生成回归诊断图（残差 vs 拟合值 + QQ 图）。"""
    from scipy import stats as sp_stats

    fig, axes = plt.subplots(1, 2, figsize=(9, 4), dpi=150)

    res_arr = np.array(residuals)
    fit_arr = np.array(fitted_values)

    # Panel 1: Residuals vs Fitted
    ax1 = axes[0]
    ax1.scatter(fit_arr, res_arr, alpha=0.5, edgecolors="black", linewidth=0.3,
                s=30, color="#4C72B0")
    ax1.axhline(0, color="#C44E52", linestyle="--", linewidth=1)
    ax1.set_xlabel("Fitted Values", fontsize=9)
    ax1.set_ylabel("Residuals", fontsize=9)
    ax1.set_title("Residuals vs Fitted", fontsize=10)
    _apply_apa_style(ax1)

    # Panel 2: QQ plot
    ax2 = axes[1]
    sorted_res = np.sort((res_arr - res_arr.mean()) / max(res_arr.std(), 1e-9))
    theoretical = sp_stats.norm.ppf(
        np.linspace(0.01, 0.99, len(sorted_res))
    )
    ax2.scatter(theoretical, sorted_res, alpha=0.5, edgecolors="black",
                linewidth=0.3, s=30, color="#4C72B0")
    lim = max(abs(theoretical.min()), abs(theoretical.max()), abs(sorted_res.min()), abs(sorted_res.max()))
    ax2.plot([-lim, lim], [-lim, lim], color="#C44E52", linewidth=1, linestyle="--")
    ax2.set_xlabel("Theoretical Quantiles", fontsize=9)
    ax2.set_ylabel("Standardized Residuals", fontsize=9)
    ax2.set_title("Normal Q-Q", fontsize=10)
    _apply_apa_style(ax2)

    fig.tight_layout()
    caption = title or "Figure. Regression diagnostics: residuals vs fitted values and Q-Q plot."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id, title=caption, caption=caption,
        png_bytes=buf.getvalue(), method="regression_diagnostics",
        recommendation_id=recommendation_id,
    )


def generate_simple_slopes_figure(
    x_range: tuple[float, float] = (1.0, 5.0),
    slopes: Optional[dict[str, tuple[float, float]]] = None,
    x_label: str = "Predictor (X)",
    y_label: str = "Outcome (Y)",
    moderator_label: str = "Moderator (W)",
    title: str = "",
    figure_id: str = "fig_simple_slopes",
    recommendation_id: str = "",
) -> APAFigure:
    """生成调节效应简单斜率图。

    slopes: dict mapping level label -> (intercept, slope)
        e.g. {"High (+1SD)": (2.0, 0.8), "Mean": (3.0, 0.4), "Low (-1SD)": (4.0, 0.1)}
    """
    if slopes is None:
        slopes = {
            "High (+1SD)": (2.0, 0.6),
            "Mean": (2.5, 0.3),
            "Low (-1SD)": (3.0, 0.05),
        }

    fig, ax = plt.subplots(figsize=(5.5, 4.5), dpi=150)
    colors = ["#C44E52", "#4C72B0", "#55A868"]
    linestyles = ["-", "--", ":"]

    x_vals = np.linspace(x_range[0], x_range[1], 50)
    for i, (label, (intercept, slope)) in enumerate(slopes.items()):
        y_vals = intercept + slope * x_vals
        ax.plot(x_vals, y_vals,
                color=colors[i % len(colors)],
                linestyle=linestyles[i % len(linestyles)],
                linewidth=2, label=f"{moderator_label}: {label}")

    ax.set_xlabel(x_label, fontsize=10)
    ax.set_ylabel(y_label, fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="best")
    _apply_apa_style(ax)

    fig.tight_layout()
    caption = title or f"Figure. Simple slopes of {x_label} on {y_label} at different levels of {moderator_label}."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id, title=caption, caption=caption,
        png_bytes=buf.getvalue(), method="moderation",
        recommendation_id=recommendation_id,
    )


def generate_factor_loading_heatmap(
    loadings: list[list[float]],
    item_labels: list[str],
    factor_labels: Optional[list[str]] = None,
    title: str = "",
    figure_id: str = "fig_factor_heatmap",
    recommendation_id: str = "",
) -> APAFigure:
    """生成因子载荷热力图（EFA）。

    loadings: 2D list [items x factors], each entry is a loading value.
    """
    arr = np.array(loadings)
    n_items, n_factors = arr.shape
    if factor_labels is None:
        factor_labels = [f"Factor {i+1}" for i in range(n_factors)]

    fig_height = max(3.5, 0.4 * n_items + 1)
    fig, ax = plt.subplots(figsize=(max(4, n_factors * 1.2 + 1.5), fig_height), dpi=150)

    im = ax.imshow(arr, aspect="auto", cmap="RdBu_r", vmin=-1, vmax=1)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Loading", fontsize=9)

    ax.set_xticks(np.arange(n_factors))
    ax.set_xticklabels(factor_labels, fontsize=9)
    ax.set_yticks(np.arange(n_items))
    ax.set_yticklabels(item_labels, fontsize=8)

    for i in range(n_items):
        for j in range(n_factors):
            val = arr[i, j]
            color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7, color=color)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    caption = title or "Figure. Factor loading matrix (EFA). Values represent standardized loadings."
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return APAFigure(
        figure_id=figure_id, title=caption, caption=caption,
        png_bytes=buf.getvalue(), method="efa",
        recommendation_id=recommendation_id,
    )


def generate_figures_from_card(card: dict) -> list[APAFigure]:
    """根据结果卡自动生成适合的图表。"""
    figures = []
    method = card.get("method", "")
    rec_id = card.get("recommendation_id", "")

    if method in ("independent_ttest", "descriptive", "mann_whitney"):
        groups = card.get("group_stats", [])
        if groups:
            labels = [g.get("label", f"G{i}") for i, g in enumerate(groups)]
            means = [g.get("mean", 0) for g in groups]
            ses = [g.get("se", g.get("std", 1) / max(g.get("n", 1), 1) ** 0.5) for g in groups]
            fig = generate_mean_se_figure(
                labels, means, ses,
                dv_label=card.get("dv_label", "Score"),
                iv_label=card.get("iv_label", "Group"),
                figure_id=f"fig_{method}_1",
                recommendation_id=rec_id,
            )
            figures.append(fig)

    elif method in ("one_way_anova", "kruskal_wallis"):
        groups = card.get("group_stats", [])
        if groups:
            labels = [g.get("label", f"G{i}") for i, g in enumerate(groups)]
            means = [g.get("mean", 0) for g in groups]
            ses = [g.get("se", g.get("std", 1) / max(g.get("n", 1), 1) ** 0.5) for g in groups]
            fig = generate_group_comparison_figure(
                labels, means, ses,
                p_value=card.get("p_value"),
                dv_label=card.get("dv_label", "Score"),
                iv_label=card.get("iv_label", "Group"),
                figure_id=f"fig_{method}_1",
                recommendation_id=rec_id,
            )
            figures.append(fig)

    elif method in ("pearson_corr", "spearman_corr"):
        x_data = card.get("x_data", [])
        y_data = card.get("y_data", [])
        if x_data and y_data:
            fig = generate_scatter_figure(
                x_data, y_data,
                r_value=card.get("r_value"),
                p_value=card.get("p_value"),
                x_label=card.get("x_label", "X"),
                y_label=card.get("y_label", "Y"),
                figure_id=f"fig_{method}_1",
                recommendation_id=rec_id,
            )
            figures.append(fig)

    elif method in ("repeated_anova", "repeated_measures_anova", "mixed_anova", "paired_ttest"):
        time_labels = card.get("time_labels", [])
        group_data = card.get("group_data", {})
        if time_labels and group_data:
            fig = generate_repeated_measures_line(
                time_labels, group_data,
                group_errors=card.get("group_errors"),
                dv_label=card.get("dv_label", "Score"),
                time_label=card.get("time_label", "Time"),
                figure_id=f"fig_{method}_1",
                recommendation_id=rec_id,
            )
            figures.append(fig)

    elif method in ("two_way_anova", "factorial_anova"):
        x_labels = card.get("x_labels", [])
        interaction_data = card.get("interaction_data", {})
        if x_labels and interaction_data:
            fig = generate_interaction_plot(
                x_labels, interaction_data,
                dv_label=card.get("dv_label", "Score"),
                x_factor_label=card.get("x_factor_label", "Factor A"),
                legend_label=card.get("legend_label", "Factor B"),
                figure_id=f"fig_{method}_1",
                recommendation_id=rec_id,
            )
            figures.append(fig)

    elif method in ("multiple_regression", "hierarchical_regression", "logistic_regression"):
        x_data = card.get("x_data", [])
        y_data = card.get("y_data", [])
        if x_data and y_data:
            fig = generate_regression_fit_figure(
                x_data, y_data,
                y_pred=card.get("y_pred"),
                r_squared=card.get("r_squared"),
                x_label=card.get("x_label", "Predictor"),
                y_label=card.get("y_label", "Outcome"),
                figure_id=f"fig_{method}_1",
                recommendation_id=rec_id,
            )
            figures.append(fig)

    elif method == "mediation":
        fig = generate_mediation_path_figure(
            x_name=card.get("x_name", "X"),
            m_name=card.get("m_name", "M"),
            y_name=card.get("y_name", "Y"),
            a_coef=card.get("a_coef"),
            b_coef=card.get("b_coef"),
            c_prime=card.get("c_prime"),
            indirect=card.get("indirect"),
            figure_id=f"fig_{method}_1",
            recommendation_id=rec_id,
        )
        figures.append(fig)

    elif method in ("cronbach_alpha", "mcdonalds_omega"):
        items = card.get("item_labels", [])
        corrs = card.get("item_total_corrs", [])
        if items and corrs:
            fig = generate_reliability_item_figure(
                items, corrs,
                alpha_if_deleted=card.get("alpha_if_deleted"),
                overall_alpha=card.get("overall_alpha"),
                figure_id=f"fig_{method}_1",
                recommendation_id=rec_id,
            )
            figures.append(fig)

    elif method == "moderation":
        slopes = card.get("simple_slopes")
        if slopes:
            fig = generate_simple_slopes_figure(
                x_range=card.get("x_range", (1.0, 5.0)),
                slopes=slopes,
                x_label=card.get("x_label", "Predictor"),
                y_label=card.get("y_label", "Outcome"),
                moderator_label=card.get("moderator_label", "Moderator"),
                figure_id=f"fig_{method}_1",
                recommendation_id=rec_id,
            )
            figures.append(fig)

    elif method in ("efa", "exploratory_factor_analysis"):
        loadings = card.get("factor_loadings", [])
        items = card.get("item_labels", [])
        if loadings and items:
            fig = generate_factor_loading_heatmap(
                loadings, items,
                factor_labels=card.get("factor_labels"),
                figure_id=f"fig_{method}_1",
                recommendation_id=rec_id,
            )
            figures.append(fig)

    # Regression diagnostics (supplementary) for regression methods
    if method in ("multiple_regression", "hierarchical_regression") and card.get("residuals"):
        residuals = card.get("residuals", [])
        fitted = card.get("fitted_values", [])
        if residuals and fitted:
            fig = generate_regression_diagnostics_figure(
                residuals, fitted,
                figure_id=f"fig_{method}_diag",
                recommendation_id=rec_id,
            )
            figures.append(fig)

    return figures
