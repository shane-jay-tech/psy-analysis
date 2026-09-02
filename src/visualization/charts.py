"""Plotly 图表工厂函数"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats

from .fonts import get_chinese_font
from config.settings import COLOR_PALETTE, CHART_TEMPLATE, CHART_HEIGHT

FONT = dict(family=get_chinese_font(), size=12)
TITLE_FONT = dict(family=get_chinese_font(), size=16)


def _base_layout(title: str, xlabel: str = "", ylabel: str = "") -> dict:
    """通用图表布局"""
    return dict(
        title=dict(text=title, font=TITLE_FONT),
        template=CHART_TEMPLATE,
        height=CHART_HEIGHT,
        font=FONT,
        xaxis=dict(title=dict(text=xlabel, font=FONT)) if xlabel else None,
        yaxis=dict(title=dict(text=ylabel, font=FONT)) if ylabel else None,
        hoverlabel=dict(font=FONT),
    )


def bar_with_error(
    data: pd.DataFrame,
    dv: str,
    iv: str,
    title: str = "各组均值比较",
) -> go.Figure:
    """分组柱状图 + 标准误误差线。

    v5.9 修复：独立 t 检验的 group_stats（组别/N/M/SD）没有 SEM 列，
    旧实现 data.get("SEM", [0]*n).tolist() 对 list 调 .tolist() 直接崩，
    导致**每个独立样本 t 检验**在图表渲染阶段抛 AttributeError。
    现在：SEM 缺失时由 SD/√N 推导；列名兼容 组别/组/group；输入可为
    DataFrame 或 list[dict]；数值统一 pd.to_numeric 归一。
    """
    if isinstance(data, pd.DataFrame):
        table = data
    else:
        try:
            table = pd.DataFrame(data)
        except Exception:
            table = pd.DataFrame()

    if table.empty:
        return go.Figure()

    group_col = next(
        (c for c in ("组别", "组", "group", "Group", "分组") if c in table.columns),
        table.columns[0],
    )
    x = table[group_col].astype(str).tolist()

    if "M" in table.columns:
        y_src = table["M"]
    elif "mean" in table.columns:
        y_src = table["mean"]
    else:
        # 没有均值列时降级为分组列本身（如纯频数表）
        y_src = table[group_col]
    y = pd.to_numeric(y_src, errors="coerce").fillna(0).tolist()

    # SEM：显式列 > SD/√N 推导 > 0
    if "SEM" in table.columns:
        sem_src = pd.to_numeric(table["SEM"], errors="coerce")
    elif "SD" in table.columns and "N" in table.columns:
        sd = pd.to_numeric(table["SD"], errors="coerce")
        n = pd.to_numeric(table["N"], errors="coerce").replace(0, np.nan)
        sem_src = sd / np.sqrt(n)
    else:
        sem_src = None
    sem = (
        np.nan_to_num(sem_src.to_numpy(dtype=float), nan=0.0).tolist()
        if sem_src is not None
        else [0.0] * len(y)
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x,
        y=y,
        error_y=dict(type="data", array=sem, visible=True),
        marker_color=COLOR_PALETTE[:len(x)],
        text=[f"{v:.2f}" for v in y],
        textposition="outside",
        hovertemplate="%{x}<br>均值: %{y:.2f} ± %{error_y.array:.3f}<extra></extra>",
    ))

    fig.update_layout(**_base_layout(title, xlabel=iv, ylabel=dv))
    return fig


def box_plot(
    df: pd.DataFrame,
    dv: str,
    iv: str,
    title: str = "分组箱线图",
) -> go.Figure:
    """分组箱线图 + 散点叠加。

    v5.9: iv 为 None 时按「每列一个箱」渲染（配对检验的两列对比场景，
    如 render_charts 的 paired_cols 分支传入 box_plot(df, col1, None)），
    旧实现 df[None] 直接 TypeError 导致配对分析整页渲染崩溃。
    """
    fig = go.Figure()

    if iv is None:
        # 配对/多列对比：dv 本身视为列名列表或单列
        cols = dv if isinstance(dv, (list, tuple)) else [dv]
        palette = COLOR_PALETTE[:len(cols)]
        for i, col in enumerate(cols):
            if col not in df.columns:
                continue
            col_data = pd.to_numeric(df[col], errors="coerce").dropna()
            fig.add_trace(go.Box(
                y=col_data,
                name=str(col),
                marker_color=palette[i % len(palette)],
                boxpoints="outliers",
                boxmean="sd",
            ))
        fig.update_layout(**_base_layout(title, xlabel="变量", ylabel="得分"))
        return fig

    groups = df[iv].dropna().unique()
    palette = COLOR_PALETTE[:len(groups)]

    for i, group in enumerate(groups):
        group_data = pd.to_numeric(df[df[iv] == group][dv], errors="coerce").dropna()

        fig.add_trace(go.Box(
            y=group_data,
            name=str(group),
            marker_color=palette[i % len(palette)],
            boxpoints="outliers",
            boxmean="sd",
        ))

    fig.update_layout(**_base_layout(title, xlabel=iv, ylabel=dv))
    return fig


def contingency_heatmap(
    table: pd.DataFrame,
    title: str = "列联表频数热力图",
) -> go.Figure:
    """v5.9: 卡方检验列联表频数热力图。

    此前卡方检验 charts_data 里有 contingency 但 render_charts 没有对应
    分支，用户做完卡方一张图都看不到。用频数着色，单元格标注数值。
    """
    if not isinstance(table, pd.DataFrame) or table.empty:
        return go.Figure()

    z = table.astype(float).fillna(0).values
    x_labels = [str(c) for c in table.columns]
    y_labels = [str(i) for i in table.index]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=x_labels,
        y=y_labels,
        colorscale="Blues",
        text=[[f"{v:g}" for v in row] for row in z],
        texttemplate="%{text}",
        hovertemplate="%{y} × %{x}<br>频数: %{z}<extra></extra>",
        colorbar=dict(title="频数"),
    ))
    fig.update_layout(**_base_layout(title, xlabel="", ylabel=""))
    return fig


def scatter_with_regression(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "散点图与回归线",
    color_by: str = None,
) -> go.Figure:
    """散点图 + 回归线 + 置信区间"""
    clean = df[[x_col, y_col]].copy()
    clean[x_col] = pd.to_numeric(clean[x_col], errors="coerce")
    clean[y_col] = pd.to_numeric(clean[y_col], errors="coerce")
    clean = clean.dropna()

    x = clean[x_col].values
    y = clean[y_col].values

    fig = go.Figure()

    # 散点
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode="markers",
        name="数据点",
        marker=dict(
            color=COLOR_PALETTE[0],
            size=8,
            opacity=0.6,
        ),
        hovertemplate=f"{x_col}: %{{x:.2f}}<br>{y_col}: %{{y:.2f}}<extra></extra>",
    ))

    # 回归线
    if len(x) > 2:
        slope, intercept, r, p, std_err = stats.linregress(x, y)
        x_line = np.linspace(x.min(), x.max(), 100)
        y_line = slope * x_line + intercept

        # 置信区间
        n = len(x)
        y_pred = slope * x + intercept
        residual_std = np.sqrt(np.sum((y - y_pred) ** 2) / (n - 2))
        x_mean = x.mean()
        se_line = residual_std * np.sqrt(
            1 / n + (x_line - x_mean) ** 2 / np.sum((x - x_mean) ** 2)
        )
        t_val = stats.t.ppf(0.975, n - 2)

        fig.add_trace(go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            name=f"回归线 (r={r:.3f}, p={p:.4f})",
            line=dict(color=COLOR_PALETTE[1], width=2),
        ))
        fig.add_trace(go.Scatter(
            x=np.concatenate([x_line, x_line[::-1]]),
            y=np.concatenate([y_line + t_val * se_line, (y_line - t_val * se_line)[::-1]]),
            fill="toself",
            fillcolor="rgba(237,125,49,0.2)",
            line=dict(color="rgba(255,255,255,0)"),
            name="95% CI",
        ))

    fig.update_layout(**_base_layout(title, xlabel=x_col, ylabel=y_col))
    return fig


def correlation_heatmap(
    corr_matrix: pd.DataFrame,
    sig_mask: pd.DataFrame = None,
    title: str = "相关矩阵热力图",
) -> go.Figure:
    """相关矩阵热力图"""
    # 标注文本：r值 + 显著性标记
    annot = corr_matrix.copy().astype(object)
    if sig_mask is not None:
        for i in annot.index:
            for j in annot.columns:
                val = corr_matrix.loc[i, j]
                sig = sig_mask.loc[i, j] if sig_mask is not None else ""
                if pd.notna(val):
                    annot.loc[i, j] = f"{val:.2f}{sig}"
                else:
                    annot.loc[i, j] = ""

    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns.tolist(),
        y=corr_matrix.index.tolist(),
        colorscale="RdBu_r",
        zmid=0,
        text=annot.values,
        texttemplate="%{text}",
        textfont=dict(size=11),
        hoverongaps=False,
        colorbar=dict(title="r"),
    ))

    fig.update_layout(**_base_layout(title))
    fig.update_xaxes(tickangle=45)
    return fig


def distribution_plot(
    df: pd.DataFrame,
    col: str,
    group_col: str = None,
    title: str = "分布图",
) -> go.Figure:
    """直方图 + KDE 密度曲线"""
    fig = go.Figure()

    s = pd.to_numeric(df[col], errors="coerce").dropna()

    if group_col and group_col in df.columns:
        for i, (name, group) in enumerate(df.groupby(group_col)):
            gs = pd.to_numeric(group[col], errors="coerce").dropna()
            fig.add_trace(go.Histogram(
                x=gs,
                name=str(name),
                opacity=0.6,
                marker_color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
                histnorm="probability density",
                nbinsx=20,
            ))
    else:
        fig.add_trace(go.Histogram(
            x=s,
            name="频数分布",
            marker_color=COLOR_PALETTE[0],
            opacity=0.7,
            histnorm="probability density",
            nbinsx=20,
        ))

        # KDE
        kde_x = np.linspace(s.min(), s.max(), 200)
        kde = stats.gaussian_kde(s)
        fig.add_trace(go.Scatter(
            x=kde_x,
            y=kde(kde_x),
            mode="lines",
            name="密度曲线",
            line=dict(color=COLOR_PALETTE[1], width=2),
        ))

        # 正态参考线
        norm_y = stats.norm.pdf(kde_x, s.mean(), s.std())
        fig.add_trace(go.Scatter(
            x=kde_x,
            y=norm_y,
            mode="lines",
            name="正态参考",
            line=dict(color="gray", width=1, dash="dash"),
        ))

    stat_text = f"n={len(s)}, M={s.mean():.2f}, SD={s.std():.2f}"
    fig.update_layout(**_base_layout(f"{title}<br><sup>{stat_text}</sup>", xlabel=col, ylabel="密度"))
    return fig


def qq_plot(
    df: pd.DataFrame,
    col: str,
    title: str = "Q-Q 图",
) -> go.Figure:
    """Q-Q 图（评估正态性）"""
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    n = len(s)

    # 理论分位数
    theoretical = np.sort(stats.norm.rvs(size=n, loc=0, scale=1))
    # 样本分位数
    observed = np.sort((s - s.mean()) / s.std())

    fig = go.Figure()

    # QQ散点
    fig.add_trace(go.Scatter(
        x=theoretical,
        y=observed,
        mode="markers",
        name="数据点",
        marker=dict(color=COLOR_PALETTE[0], size=6, opacity=0.6),
    ))

    # 参考线 y=x
    lims = [min(theoretical.min(), observed.min()), max(theoretical.max(), observed.max())]
    fig.add_trace(go.Scatter(
        x=lims,
        y=lims,
        mode="lines",
        name="正态参考线",
        line=dict(color="gray", dash="dash", width=1),
    ))

    # Shapiro-Wilk
    if 3 <= n <= 5000:
        sw_stat, sw_p = stats.shapiro(s)
        note = f"Shapiro-Wilk: W={sw_stat:.3f}, p={sw_p:.3f}"
    else:
        note = ""

    fig.update_layout(**_base_layout(
        f"{title}<br><sup>{note}</sup>",
        xlabel="理论正态分位数",
        ylabel="样本分位数",
    ))
    return fig


def forest_plot(
    coef_table: pd.DataFrame,
    title: str = "回归系数森林图",
) -> go.Figure:
    """回归系数森林图（显示B值和95%置信区间）"""
    # 排除截距
    plot_data = coef_table[~coef_table.iloc[:, 0].isin(["截距", "常量", "const"])].copy()

    if plot_data.empty:
        fig = go.Figure()
        fig.update_layout(**_base_layout(title))
        return fig

    names = plot_data.iloc[:, 0].tolist()
    b_vals = plot_data["B"].astype(float).tolist()

    # 简单估计CI：B ± 1.96*SE
    se_vals = plot_data["SE"].astype(float).tolist()
    ci_lower = [b - 1.96 * se for b, se in zip(b_vals, se_vals)]
    ci_upper = [b + 1.96 * se for b, se in zip(b_vals, se_vals)]

    p_vals = plot_data["p"].tolist()
    colors = [COLOR_PALETTE[0] if p < 0.05 else "#A5A5A5" for p in p_vals]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=b_vals,
        y=names,
        mode="markers",
        name="B估计值",
        marker=dict(color=colors, size=12),
        error_x=dict(
            type="data",
            symmetric=False,
            array=[cu - b for cu, b in zip(ci_upper, b_vals)],
            arrayminus=[b - cl for cl, b in zip(ci_lower, b_vals)],
        ),
        hovertemplate="%{y}<br>B=%{x:.3f}<br>95%CI: [%{customdata[0]:.3f}, %{customdata[1]:.3f}]<extra></extra>",
        customdata=list(zip(ci_lower, ci_upper)),
    ))

    # 零参考线
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(**_base_layout(title, xlabel="回归系数 (B)", ylabel="预测变量"))
    return fig


def scree_plot(
    eigenvalues: pd.DataFrame,
    title: str = "因素分析碎石图",
) -> go.Figure:
    """EFA碎石图（特征值 + 平行分析参考线）"""
    fig = go.Figure()

    factors = eigenvalues["因素"].tolist()
    ev = eigenvalues["特征值"].astype(float).tolist()

    fig.add_trace(go.Scatter(
        x=list(range(1, len(factors) + 1)),
        y=ev,
        mode="lines+markers",
        name="实际特征值",
        marker=dict(size=8, color=COLOR_PALETTE[0]),
        line=dict(width=2, color=COLOR_PALETTE[0]),
    ))

    # 特征值=1 参考线
    fig.add_hline(y=1, line_dash="dash", line_color="red", opacity=0.5,
                  annotation_text="特征值=1")

    fig.update_layout(**_base_layout(
        title,
        xlabel="因素序号",
        ylabel="特征值",
    ))
    fig.update_xaxes(tickvals=list(range(1, len(factors) + 1)))
    return fig


def mediation_diagram(
    coef_table: pd.DataFrame,
    bootstrap_ci: pd.DataFrame,
    title: str = "中介效应路径图",
) -> go.Figure:
    """中介效应路径系数图（简化版，使用Sankey或annotated scatter）"""
    fig = go.Figure()

    # 提取路径系数
    paths = {}
    for _, row in coef_table.iterrows():
        path_name = str(row.iloc[0])
        b_val = float(row["B"])
        p_val = float(row["p"]) if row["p"] != "-" else 1.0
        paths[path_name] = {"B": b_val, "p": p_val}

    # 绘制路径图：使用annotations + 箭头风格线条
    # 三个节点：X, M, Y 呈三角形布局
    nodes = {
        "X": (0, 1),
        "M": (1, 1),
        "Y": (2, 1),
    }

    # 节点
    for name, (x, y) in nodes.items():
        label_map = {
            "X": "自变量\\n(X)",
            "M": "中介变量\\n(M)",
            "Y": "因变量\\n(Y)",
        }
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            name=name,
            marker=dict(size=40, color=COLOR_PALETTE[0]),
            text=[label_map.get(name, name)],
            textposition="middle center",
            textfont=dict(color="white", size=10),
            showlegend=False,
        ))

    # 路径a: X→M
    a_val = paths.get("a (X→M)", {}).get("B", 0)
    a_p = paths.get("a (X→M)", {}).get("p", 1.0)
    _add_path_arrow(fig, 0.15, 0.97, "a", a_val, a_p, COLOR_PALETTE[1])

    # 路径b: M→Y
    b_val = paths.get("b (M→Y)", {}).get("B", 0)
    b_p = paths.get("b (M→Y)", {}).get("p", 1.0)
    _add_path_arrow(fig, 1.15, 0.97, "b", b_val, b_p, COLOR_PALETTE[2])

    # 路径c': X→Y (直接效应)
    cp_val = paths.get("c' (直接效应)", {}).get("B", 0)
    cp_p = paths.get("c' (直接效应)", {}).get("p", 1.0)
    _add_path_arrow(fig, 0.15, 0.75, "c'", cp_val, cp_p, "gray", dash="dash")

    # 总效应
    c_val = paths.get("c (总效应)", {}).get("B", 0)
    c_p = paths.get("c (总效应)", {}).get("p", 1.0)

    # 标注间接效应
    ci_text = ""
    if bootstrap_ci is not None and len(bootstrap_ci) > 0:
        ci = bootstrap_ci.iloc[0]
        ci_text = f"<br>间接效应(a*b)={ci['B']:.3f}<br>Bootstrap 95%CI: [{ci['CI下限']:.3f}, {ci['CI上限']:.3f}]"

    fig.add_annotation(
        x=1, y=0.5,
        text=f"总效应(c)={c_val:.3f}<br>直接效应(c')={cp_val:.3f}{ci_text}",
        showarrow=False,
        font=dict(size=11),
    )

    fig.update_layout(
        **_base_layout(title),
        xaxis=dict(range=[-0.5, 2.5], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[0.3, 1.3], showgrid=False, zeroline=False, showticklabels=False),
        showlegend=False,
    )
    fig.update_layout(height=400)
    return fig


def _add_path_arrow(fig, x, y, label, value, p_val, color, dash=None):
    """在中介路径图上添加标注"""
    sig = "*" if p_val < 0.05 else ""
    style = "dash" if dash else "solid"
    fig.add_annotation(
        x=x if x < 1.5 else x - 0.05,
        y=y,
        text=f"{label}={value:.3f}{sig}",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor=color,
        ax=20 if x < 1.5 else -20,
        ay=0,
        font=dict(size=10, color=color),
    )


def interaction_plot(
    df: pd.DataFrame,
    dv: str,
    iv1: str,
    iv2: str,
    title: str = "交互作用图",
) -> go.Figure:
    """双因素交互作用折线图"""
    fig = go.Figure()

    means = df.groupby([iv1, iv2])[dv].mean().unstack()

    for i, col in enumerate(means.columns):
        fig.add_trace(go.Scatter(
            x=means.index.astype(str),
            y=means[col].values,
            mode="lines+markers",
            name=str(col),
            marker=dict(size=10, color=COLOR_PALETTE[i % len(COLOR_PALETTE)]),
            line=dict(width=2),
        ))

    fig.update_layout(**_base_layout(title, xlabel=iv1, ylabel=f"{dv} (均值)"))
    return fig
