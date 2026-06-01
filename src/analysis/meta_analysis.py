"""元分析：固定效应 / 随机效应模型 + 森林图

基于 numpy/scipy 实现 DerSimonian–Laird 随机效应模型。
生成森林图（matplotlib）和 APA7 格式报告。

输入格式：CSV 包含各研究的效应量（d/r/z）和标准误或 CI 边界。
"""

import numpy as np
import pandas as pd
from scipy import stats
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import io


@dataclass
class MetaResult:
    """元分析结果"""
    model: str               # "fixed" or "random"
    effect_type: str         # "d", "r", "z"
    k: int                   # 研究数
    pooled_effect: float
    pooled_se: float
    ci_lower: float
    ci_upper: float
    z_value: float
    p_value: float
    q_statistic: float       # 异质性 Q
    q_df: int
    q_p_value: float
    i_squared: float         # I² (%)
    tau_squared: float       # τ²（随机效应模型）
    study_weights: List[float]
    study_effects: List[float]
    study_cis: List[Tuple[float, float]]
    study_labels: List[str]
    forest_fig: Optional[object] = None  # matplotlib Figure


def run_meta_analysis(
    df: pd.DataFrame,
    effect_col: str = "effect_size",
    se_col: Optional[str] = None,
    ci_lower_col: Optional[str] = None,
    ci_upper_col: Optional[str] = None,
    label_col: Optional[str] = None,
    effect_type: str = "d",
    model: str = "random",
    confidence: float = 0.95,
    generate_plot: bool = True,
) -> MetaResult:
    """
    运行元分析。

    参数：
        df: 包含效应量及变异性指标的 DataFrame
        effect_col: 效应量列名
        se_col: 标准误列名（优先使用，如有）
        ci_lower_col / ci_upper_col: 置信区间边界（se_col 为空时使用）
        label_col: 研究标签列名
        effect_type: 效应量类型 "d" | "r" | "z"
        model: "fixed" 或 "random"
        confidence: 置信水平（默认 0.95）
        generate_plot: 是否生成森林图

    返回：
        MetaResult 包含汇总效应量、异质性指标和森林图
    """
    effects = df[effect_col].values.astype(float)
    k = len(effects)
    if k < 2:
        raise ValueError(f"元分析至少需要2项研究，当前仅有 {k} 项。")

    # 确定标准误
    if se_col and se_col in df.columns:
        ses = df[se_col].values.astype(float)
    elif ci_lower_col and ci_upper_col:
        z_crit = stats.norm.ppf(1 - (1 - confidence) / 2)
        ses = (df[ci_upper_col].values.astype(float) - df[ci_lower_col].values.astype(float)) / (2 * z_crit)
    else:
        raise ValueError("必须提供 se_col 或 (ci_lower_col + ci_upper_col)。")

    # 研究标签
    if label_col and label_col in df.columns:
        labels = df[label_col].tolist()
    else:
        labels = [f"研究{i+1}" for i in range(k)]

    # 计算 CI
    z_crit = stats.norm.ppf(1 - (1 - confidence) / 2)
    study_cis = [(e - z_crit * s, e + z_crit * s) for e, s in zip(effects, ses)]

    if model == "fixed":
        result = _fixed_effect_meta(effects, ses, labels, study_cis, z_crit, effect_type, k)
    else:
        result = _random_effect_meta(effects, ses, labels, study_cis, z_crit, effect_type, k)

    if generate_plot:
        result.forest_fig = _generate_forest_plot(result)

    return result


def _fixed_effect_meta(
    effects: np.ndarray, ses: np.ndarray,
    labels: List[str], study_cis: List[Tuple[float, float]],
    z_crit: float, effect_type: str, k: int,
) -> MetaResult:
    """固定效应模型（逆方差加权）"""
    # 权重 = 1/方差
    variances = ses ** 2
    weights = 1.0 / variances
    sum_w = np.sum(weights)

    # 汇总效应量
    pooled = np.sum(weights * effects) / sum_w
    pooled_se = np.sqrt(1.0 / sum_w)

    ci_lower = pooled - z_crit * pooled_se
    ci_upper = pooled + z_crit * pooled_se

    z_val = pooled / pooled_se
    p_val = 2 * (1 - stats.norm.cdf(abs(z_val)))

    # 异质性 Q
    q_stat = np.sum(weights * (effects - pooled) ** 2)
    q_df = k - 1
    q_p = 1 - stats.chi2.cdf(q_stat, q_df) if q_df > 0 else 1.0

    # I²
    i_sq = max(0, (q_stat - q_df) / q_stat * 100) if q_stat > 0 else 0.0

    return MetaResult(
        model="fixed",
        effect_type=effect_type,
        k=k,
        pooled_effect=round(float(pooled), 4),
        pooled_se=round(float(pooled_se), 4),
        ci_lower=round(float(ci_lower), 4),
        ci_upper=round(float(ci_upper), 4),
        z_value=round(float(z_val), 3),
        p_value=round(float(p_val), 4),
        q_statistic=round(float(q_stat), 3),
        q_df=q_df,
        q_p_value=round(float(q_p), 4),
        i_squared=round(float(i_sq), 1),
        tau_squared=0.0,
        study_weights=[round(float(w / sum_w * 100), 1) for w in weights],
        study_effects=[round(float(e), 4) for e in effects],
        study_cis=study_cis,
        study_labels=labels,
    )


def _random_effect_meta(
    effects: np.ndarray, ses: np.ndarray,
    labels: List[str], study_cis: List[Tuple[float, float]],
    z_crit: float, effect_type: str, k: int,
) -> MetaResult:
    """随机效应模型（DerSimonian–Laird 方法）"""
    variances = ses ** 2
    weights_fe = 1.0 / variances

    # 固定效应汇总（用于 Q 计算）
    pooled_fe = np.sum(weights_fe * effects) / np.sum(weights_fe)
    q_stat = np.sum(weights_fe * (effects - pooled_fe) ** 2)
    q_df = k - 1

    # 计算 τ² (DerSimonian–Laird)
    c = np.sum(weights_fe) - np.sum(weights_fe ** 2) / np.sum(weights_fe)
    tau_sq = max(0, (q_stat - q_df) / c) if c > 0 and q_stat > q_df else 0.0

    # 随机效应权重
    weights_re = 1.0 / (variances + tau_sq)
    sum_w_re = np.sum(weights_re)

    pooled_re = np.sum(weights_re * effects) / sum_w_re
    pooled_se_re = np.sqrt(1.0 / sum_w_re)

    ci_lower = pooled_re - z_crit * pooled_se_re
    ci_upper = pooled_re + z_crit * pooled_se_re

    z_val = pooled_re / pooled_se_re
    p_val = 2 * (1 - stats.norm.cdf(abs(z_val)))

    # I²
    i_sq = max(0, (q_stat - q_df) / q_stat * 100) if q_stat > 0 else 0.0

    q_p = 1 - stats.chi2.cdf(q_stat, q_df) if q_df > 0 else 1.0

    return MetaResult(
        model="random",
        effect_type=effect_type,
        k=k,
        pooled_effect=round(float(pooled_re), 4),
        pooled_se=round(float(pooled_se_re), 4),
        ci_lower=round(float(ci_lower), 4),
        ci_upper=round(float(ci_upper), 4),
        z_value=round(float(z_val), 3),
        p_value=round(float(p_val), 4),
        q_statistic=round(float(q_stat), 3),
        q_df=q_df,
        q_p_value=round(float(q_p), 4),
        i_squared=round(float(i_sq), 1),
        tau_squared=round(float(tau_sq), 4),
        study_weights=[round(float(w / sum_w_re * 100), 1) for w in weights_re],
        study_effects=[round(float(e), 4) for e in effects],
        study_cis=study_cis,
        study_labels=labels,
    )


def _generate_forest_plot(result: MetaResult):
    """生成森林图（matplotlib）"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, max(5, result.k * 0.5 + 2)))

    y_positions = list(range(result.k, 0, -1))

    # 各研究
    for i, (y, effect, (ci_l, ci_u), weight) in enumerate(
        zip(y_positions, result.study_effects, result.study_cis, result.study_weights)
    ):
        marker_size = max(20, weight * 2)
        ax.plot(effect, y, "o", markersize=np.sqrt(marker_size), color="black")
        ax.plot([ci_l, ci_u], [y, y], "k-", linewidth=1.5)

    # 汇总效应量（菱形）
    y_summary = 0
    summ = result.pooled_effect
    ci_l = result.ci_lower
    ci_u = result.ci_upper
    diamond_x = [ci_l, summ, ci_u, summ, ci_l]
    diamond_y = [y_summary, y_summary + 0.4, y_summary, y_summary - 0.4, y_summary]
    ax.fill(diamond_x, diamond_y, "black", alpha=0.8)

    ax.axvline(x=0, color="gray", linestyle="--", linewidth=0.8)

    all_y = y_positions + [y_summary]
    all_labels = result.study_labels + [
        f"汇总 ({result.model.upper()}) [{result.ci_lower:.3f}, {result.ci_upper:.3f}]"
    ]
    ax.set_yticks(all_y)
    ax.set_yticklabels(all_labels, fontsize=9)

    if result.effect_type == "d":
        xlabel = "Cohen's d"
    elif result.effect_type == "z":
        xlabel = "Fisher's z"
    else:
        xlabel = "r"
    ax.set_xlabel(f"{xlabel} (95% CI)")
    ax.set_title(
        f"森林图 ({result.model.upper()}模型, k={result.k}, "
        f"I²={result.i_squared:.1f}%, Q({result.q_df})={result.q_statistic:.2f}, p={result.q_p_value:.4f})",
        fontsize=11,
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    return fig


def format_meta_report(result: MetaResult) -> str:
    """生成 APA7 格式元分析报告"""
    effect_names = {"d": "Cohen's d", "r": "r", "z": "Fisher's z"}
    ename = effect_names.get(result.effect_type, result.effect_type)

    lines = [
        "## 元分析结果",
        "",
        f"模型：{result.model.upper()}（{'固定效应' if result.model == 'fixed' else '随机效应，DerSimonian–Laird法'}）",
        f"效应量指标：{ename}",
        f"纳入研究数：k = {result.k}",
        "",
        "### 汇总效应量",
        "",
        f"{ename} = {result.pooled_effect:.3f}, "
        f"95% CI [{result.ci_lower:.3f}, {result.ci_upper:.3f}], "
        f"z = {result.z_value:.3f}, p = {result.p_value:.4f}",
        "",
        "### 异质性检验",
        "",
        f"Q({result.q_df}) = {result.q_statistic:.3f}, p = {result.q_p_value:.4f}",
        f"I² = {result.i_squared:.1f}%",
    ]

    # I² 解释
    if result.i_squared < 25:
        lines.append("异质性低（I² < 25%），各研究间效应量变异较小。")
    elif result.i_squared < 50:
        lines.append("异质性中等（25% ≤ I² < 50%），存在一定程度的效应量变异。")
    elif result.i_squared < 75:
        lines.append("异质性较高（50% ≤ I² < 75%），效应量存在较大变异，建议探索调节变量。")
    else:
        lines.append("异质性很高（I² ≥ 75%），各研究间效应量变异极大，应谨慎解释汇总结果。")

    if result.model == "random" and result.tau_squared > 0:
        lines.append(
            f"\nτ² = {result.tau_squared:.4f}（组间变异估计），"
            f"表明真实效应量在研究间存在差异。"
        )

    lines.extend([
        "",
        "### 各研究权重与效应量",
        "",
        "| 研究 | 效应量 | 95% CI | 权重(%) |",
        "|------|--------|--------|---------|",
    ])

    for i in range(result.k):
        lines.append(
            f"| {result.study_labels[i]} | {result.study_effects[i]:.3f} | "
            f"[{result.study_cis[i][0]:.3f}, {result.study_cis[i][1]:.3f}] | "
            f"{result.study_weights[i]:.1f} |"
        )

    lines.extend([
        "",
        f"| **汇总** | **{result.pooled_effect:.3f}** | "
        f"**[{result.ci_lower:.3f}, {result.ci_upper:.3f}]** | **100.0** |",
        "",
        "*统计分析基于 APA 第7版报告规范。*",
    ])

    return "\n".join(lines)
