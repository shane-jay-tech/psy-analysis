"""假设检验：正态性 / 方差齐性 / 球形检验"""

import numpy as np
import pandas as pd
from scipy import stats
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AssumptionResult:
    test_name: str
    statistic: float
    p_value: float
    passed: bool
    message_zh: str
    suggested_action: str = ""


def check_normality(data: pd.Series, alpha: float = 0.05) -> AssumptionResult:
    """
    Shapiro-Wilk 正态性检验。
    当样本量 > 5000 时自动切换为 Kolmogorov-Smirnov。
    """
    clean = data.dropna()
    n = len(clean)

    if n < 3:
        return AssumptionResult(
            test_name="Shapiro-Wilk",
            statistic=np.nan,
            p_value=np.nan,
            passed=False,
            message_zh=f"样本量过小 (n={n})，无法进行正态性检验。",
            suggested_action="建议使用非参数检验。",
        )

    if n > 5000:
        # KS检验
        z_score = (clean - clean.mean()) / clean.std()
        stat, p = stats.kstest(z_score, "norm")
        test_name = "Kolmogorov-Smirnov"
    else:
        stat, p = stats.shapiro(clean)
        test_name = "Shapiro-Wilk"

    passed = p > alpha
    if passed:
        msg = f"数据符合正态分布 ({test_name}: W={stat:.3f}, p={p:.3f})"
        action = ""
    else:
        msg = f"数据不符合正态分布 ({test_name}: W={stat:.3f}, p={p:.3f})"
        action = "建议使用非参数检验（Mann-Whitney U 或 Wilcoxon）作为替代。"

    return AssumptionResult(
        test_name=test_name,
        statistic=round(float(stat), 4),
        p_value=round(float(p), 4),
        passed=passed,
        message_zh=msg,
        suggested_action=action,
    )


def check_normality_groups(
    groups: dict, alpha: float = 0.05
) -> dict:
    """对每个分组分别检验正态性"""
    results = {}
    for name, data in groups.items():
        results[name] = check_normality(data, alpha)
    return results


def check_homogeneity(groups: dict, alpha: float = 0.05) -> AssumptionResult:
    """
    Levene 方差齐性检验。
    groups: {"组名": pd.Series, ...}
    """
    group_data = [v.dropna().values for v in groups.values()]
    n_groups = len(group_data)

    if n_groups < 2:
        return AssumptionResult(
            test_name="Levene",
            statistic=np.nan,
            p_value=np.nan,
            passed=True,
            message_zh="组数不足2组，跳过节方差齐性检验。",
        )

    stat, p = stats.levene(*group_data)
    passed = p > alpha

    if passed:
        msg = f"方差齐性假设成立 (Levene: F={stat:.3f}, p={p:.3f})"
        action = ""
    else:
        msg = f"方差不齐 (Levene: F={stat:.3f}, p={p:.3f})"
        action = "t检验已自动使用Welch校正；ANOVA建议使用Welch ANOVA或非参数检验。"

    return AssumptionResult(
        test_name="Levene",
        statistic=round(float(stat), 4),
        p_value=round(float(p), 4),
        passed=passed,
        message_zh=msg,
        suggested_action=action,
    )


def check_sphericity(data: pd.DataFrame, alpha: float = 0.05) -> AssumptionResult:
    """
    Mauchly 球形检验（用于重复测量ANOVA）。
    data: 每列为一个测量时间点
    """
    n, k = data.shape
    if k < 2:
        return AssumptionResult(
            test_name="Mauchly",
            statistic=np.nan,
            p_value=np.nan,
            passed=True,
            message_zh="测量次数不足，跳过球形检验。",
        )

    # 计算协方差矩阵的特征值
    cov_matrix = np.cov(data.dropna().values, rowvar=False)
    eigvals = np.linalg.eigvalsh(cov_matrix)
    if np.any(eigvals <= 0):
        return AssumptionResult(
            test_name="Mauchly",
            statistic=np.nan,
            p_value=np.nan,
            passed=False,
            message_zh="协方差矩阵非正定，无法进行球形检验。",
            suggested_action="建议使用多变量方法（MANOVA）或Greenhouse-Geisser校正。",
        )

    # Mauchly's W
    geom_mean = np.exp(np.mean(np.log(eigvals)))
    arith_mean = np.mean(eigvals)
    W = geom_mean / arith_mean if arith_mean > 0 else 0

    # 卡方近似
    df = (k * (k - 1)) // 2 - 1
    chi_sq = -(n - 1 - (2 * k + 1) / 6) * np.log(W) if W > 0 else np.inf
    p = 1 - stats.chi2.cdf(chi_sq, df) if df > 0 else 1.0

    passed = p > alpha
    if passed:
        msg = f"球形假设成立 (Mauchly: W={W:.3f}, χ²={chi_sq:.2f}, p={p:.3f})"
        action = ""
    else:
        msg = f"球形假设违反 (Mauchly: W={W:.3f}, χ²={chi_sq:.2f}, p={p:.3f})"
        action = "已自动应用Greenhouse-Geisser校正。"

    return AssumptionResult(
        test_name="Mauchly",
        statistic=round(float(W), 4),
        p_value=round(float(p), 4),
        passed=passed,
        message_zh=msg,
        suggested_action=action,
    )
