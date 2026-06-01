"""效应量置信区间计算。

补 chi_square / correlation 矩阵的 CI 缺口（ttest / anova 已在各自模块算 CI）。

方法选择（Phase 1.3 仲裁）：
- Pearson r / Spearman ρ：Fisher z 变换 → CI 反变换。Spearman 用 Fisher-z 是
  常见近似（Bishara & Hittner 2017）。
- Cramer's V / Cohen's w：非中心 χ² 分布 + brentq 求 NCP CI → 反推 V/w。
  不用 bootstrap：Streamlit UI 阻塞风险。
"""

from __future__ import annotations

from typing import Tuple, Optional

import numpy as np
from scipy import stats
from scipy.optimize import brentq


def fisher_z_ci(
    r: float, n: int, confidence: float = 0.95
) -> Tuple[Optional[float], Optional[float]]:
    """Fisher z 变换计算相关系数置信区间。

    Args:
        r: 相关系数（-1 < r < 1）。
        n: 样本量（必须 >= 4 才有意义）。
        confidence: 置信水平（默认 0.95）。

    Returns:
        (ci_low, ci_high)，r 不可计算时返回 (None, None)。
    """
    if not np.isfinite(r):
        return (None, None)
    if n < 4:
        return (None, None)
    # 边界：r=±1 时 z 发散，返回与 r 等值的边界
    r_clip = max(min(r, 0.999999), -0.999999)
    z = np.arctanh(r_clip)
    se = 1.0 / np.sqrt(n - 3)
    alpha = 1.0 - confidence
    z_crit = stats.norm.ppf(1 - alpha / 2)
    z_low = z - z_crit * se
    z_high = z + z_crit * se
    return (float(np.tanh(z_low)), float(np.tanh(z_high)))


def chi_square_v_ci(
    chi_sq: float,
    df: int,
    n: int,
    k_min: int,
    confidence: float = 0.95,
) -> Tuple[Optional[float], Optional[float]]:
    """Cramer's V 的非中心 χ² CI。

    思路：对 NCP λ 求 confidence 区间 → V = sqrt(λ / (n * k_min))。
    若 χ² 接近 0（无效应），CI 下界截断到 0。

    Args:
        chi_sq: 观测到的 χ² 值。
        df: χ² 检验自由度。
        n: 样本量。
        k_min: min(行数, 列数) - 1（V 公式中的分母维度）。
        confidence: 置信水平。

    Returns:
        (ci_low, ci_high)，无法计算时返回 (None, None)。
    """
    if not np.isfinite(chi_sq) or chi_sq < 0:
        return (None, None)
    if df < 1 or n <= 0 or k_min <= 0:
        return (None, None)

    alpha = 1.0 - confidence

    def _ncp_at(target_p, lam):
        # P(NCχ² <= chi_sq | df, lam) - target_p
        return stats.ncx2.cdf(chi_sq, df, lam) - target_p

    def _solve(target_p, lo, hi):
        try:
            f_lo = _ncp_at(target_p, lo)
            f_hi = _ncp_at(target_p, hi)
            # 若同号说明 chi_sq 在该 NCP 范围外
            # 两端都为负：cdf(chi_sq, df, 0) < target_p，意味着 chi_sq 没"那么极端"，
            #   该侧 NCP 边界截断到 0（NCP 的边界不能为负）。
            # 两端都为正：chi_sq 比 lam=large 时还更极端，需要扩大 hi。
            if f_lo * f_hi > 0:
                return 0.0  # 任意一边同号都截断到 0
            return brentq(lambda x: _ncp_at(target_p, x), lo, hi, maxiter=300)
        except Exception:
            return None

    upper_search = max(chi_sq * 4 + 100, df + 100)
    ncp_low = _solve(1 - alpha / 2, 0.0, upper_search)
    ncp_high = _solve(alpha / 2, 0.0, upper_search * 4)

    if ncp_low is None or ncp_high is None:
        return (None, None)

    v_low = np.sqrt(max(ncp_low, 0.0) / (n * k_min))
    v_high = np.sqrt(max(ncp_high, 0.0) / (n * k_min))
    return (float(min(1.0, v_low)), float(min(1.0, v_high)))


def chi_square_w_ci(
    chi_sq: float,
    df: int,
    n: int,
    confidence: float = 0.95,
) -> Tuple[Optional[float], Optional[float]]:
    """Cohen's w 的非中心 χ² CI（拟合优度专用）。

    w = sqrt(χ²/n)，是 V 在 k_min=1 的特例。
    """
    return chi_square_v_ci(chi_sq, df, n, k_min=1, confidence=confidence)


def correlation_matrix_ci(
    corr_matrix,
    n_matrix,
    confidence: float = 0.95,
):
    """对相关矩阵中的每一格计算 Fisher-z CI。

    Args:
        corr_matrix: pd.DataFrame，相关系数矩阵。
        n_matrix: pd.DataFrame，每格样本量。
        confidence: 置信水平。

    Returns:
        (ci_low_df, ci_high_df) 两个 pd.DataFrame，与 corr_matrix 同形。
        对角线和无法计算的格子为 NaN。
    """
    import pandas as pd

    n_rows, n_cols = corr_matrix.shape
    low = np.full((n_rows, n_cols), np.nan)
    high = np.full((n_rows, n_cols), np.nan)

    arr_corr = corr_matrix.to_numpy(dtype=float, copy=True)
    arr_n = n_matrix.to_numpy(dtype=float, copy=True)

    for i in range(n_rows):
        for j in range(n_cols):
            if i == j:
                low[i, j] = 1.0
                high[i, j] = 1.0
                continue
            r = arr_corr[i, j]
            n = arr_n[i, j]
            if not np.isfinite(r) or not np.isfinite(n):
                continue
            n_int = int(n)
            ci = fisher_z_ci(r, n_int, confidence)
            if ci[0] is not None:
                low[i, j] = round(ci[0], 3)
                high[i, j] = round(ci[1], 3)

    low_df = pd.DataFrame(low, index=corr_matrix.index, columns=corr_matrix.columns)
    high_df = pd.DataFrame(high, index=corr_matrix.index, columns=corr_matrix.columns)
    return low_df, high_df
