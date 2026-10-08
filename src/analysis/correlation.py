"""相关分析：Pearson / Spearman"""

import logging
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CorrResult:
    test_type: str  # "pearson", "spearman"
    corr_matrix: pd.DataFrame
    p_matrix: pd.DataFrame
    n_matrix: pd.DataFrame
    sig_mask: pd.DataFrame  # 显著标记
    ci_low_matrix: Optional[pd.DataFrame] = None  # Fisher-z CI 下限矩阵
    ci_high_matrix: Optional[pd.DataFrame] = None  # Fisher-z CI 上限矩阵




def _stars(p: float) -> str:
    """相关显著性星号（s1007-19 S1 单源化）：阈值 0.001/0.01/0.05 三处同源。

    历史：:83/:164/:219 三处逐字同构 lambda 各写一份 ⇒ 改阈值必漏（s1004-55 钉桩）。
    s1008-01/S2 起：矩阵面（correlation_matrix/partial_correlation）传入本函数前
    已做族内 Holm 校正（见 _stars_matrix_holm）；本函数阈值语义零改动。
    """
    return "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))


def _stars_matrix_holm(p_df: pd.DataFrame) -> pd.DataFrame:
    """相关矩阵星号（s1008-01/S2 校正化）：矩阵内 k(k−1)/2 族 Holm 校正后再打星。

    材料：docs/insights/gh-label-corr-stars-20261004.md s1004-55 §三 S2 案
    （用户 2026-10-08 拍板三件全落）。族＝上三角非 NaN p（行主序定序）；
    对角线（p=0 自身相关）与 NaN 元不入族，各按原值打星/空串（零阈值改动，
    星号阈值仍 0.001/0.01/0.05）。Holm 选型对齐全仓 mc_method 缺省
    （runner.py:735，44a0:45）。点二列（族大小=1，Holm 恒等）不走本函数，
    维持单 p 单星（材料 s1004-55 §一明示无校正问题）。
    """
    from statsmodels.stats.multitest import multipletests

    n = len(p_df)
    idx = [
        (i, j)
        for i in range(n)
        for j in range(i + 1, n)
        if pd.notna(p_df.iloc[i, j])
    ]
    adj = p_df.astype(float).copy()
    if idx:
        pvals = [float(p_df.iloc[i, j]) for i, j in idx]
        _, p_holm, _, _ = multipletests(pvals, method="holm")
        for (i, j), pa in zip(idx, p_holm):
            adj.iloc[i, j] = pa
            adj.iloc[j, i] = pa
    sig = adj.copy()
    for c in sig.columns:
        sig[c] = sig[c].apply(_stars)
    return sig

def correlation_matrix(
    df: pd.DataFrame,
    columns: List[str],
    method: str = "pearson",
) -> CorrResult:
    """
    计算相关矩阵。
    method: "pearson" 或 "spearman"
    """
    # 只保留数值列
    valid_cols = []
    for col in columns:
        if col in df.columns:
            try:
                pd.to_numeric(df[col], errors="raise")
                valid_cols.append(col)
            except (ValueError, TypeError):
                continue

    if len(valid_cols) < 2:
        raise ValueError("至少需要2个数值型变量进行相关分析。")

    data = df[valid_cols].apply(pd.to_numeric, errors="coerce")
    n = len(valid_cols)

    corr_arr = np.zeros((n, n))
    p_arr = np.ones((n, n))
    n_arr = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            if i == j:
                corr_arr[i, j] = 1.0
                p_arr[i, j] = 0.0
                n_arr[i, j] = data[valid_cols[i]].notna().sum()
            else:
                x = data[valid_cols[i]]
                y = data[valid_cols[j]]
                mask = x.notna() & y.notna()
                x_clean, y_clean = x[mask], y[mask]
                n_arr[i, j] = len(x_clean)

                if len(x_clean) < 3:
                    corr_arr[i, j] = np.nan
                    p_arr[i, j] = np.nan
                elif method == "pearson":
                    r, p = stats.pearsonr(x_clean, y_clean)
                    corr_arr[i, j] = r
                    p_arr[i, j] = p
                else:
                    r, p = stats.spearmanr(x_clean, y_clean)
                    corr_arr[i, j] = r
                    p_arr[i, j] = p

    corr_df = pd.DataFrame(corr_arr, index=valid_cols, columns=valid_cols)
    p_df = pd.DataFrame(p_arr, index=valid_cols, columns=valid_cols)
    n_df = pd.DataFrame(n_arr, index=valid_cols, columns=valid_cols)

    # 显著性标记（s1008-01/S2：k(k−1)/2 族 Holm 校正后再打星，阈值零改动）
    sig_mask = _stars_matrix_holm(p_df)

    # Round numeric matrices (avoid DataFrame.map which changed across pandas versions)
    corr_vals = corr_df.to_numpy(dtype=float, copy=True)
    p_vals = p_df.to_numpy(dtype=float, copy=True)
    corr_vals[~np.isnan(corr_vals)] = np.round(corr_vals[~np.isnan(corr_vals)], 3)
    p_vals[~np.isnan(p_vals)] = np.round(p_vals[~np.isnan(p_vals)], 4)
    corr_matrix_rounded = pd.DataFrame(corr_vals, index=corr_df.index, columns=corr_df.columns)
    p_matrix_rounded = pd.DataFrame(p_vals, index=p_df.index, columns=p_df.columns)

    # Fisher-z CI for each cell（Phase 1.3 补缺口）
    from .effect_size_ci import correlation_matrix_ci
    ci_low_df, ci_high_df = correlation_matrix_ci(
        corr_matrix_rounded, n_df, confidence=0.95
    )

    return CorrResult(
        test_type=method,
        corr_matrix=corr_matrix_rounded,
        p_matrix=p_matrix_rounded,
        n_matrix=n_df,
        sig_mask=sig_mask,
        ci_low_matrix=ci_low_df,
        ci_high_matrix=ci_high_df,
    )


def partial_correlation(
    df: pd.DataFrame,
    columns: List[str],
    method: str = "pearson",
) -> CorrResult:
    """
    偏相关矩阵（控制其他变量的影响后，两两之间的净相关）。

    method: "pearson" 或 "spearman"
    """
    import pingouin as pg

    data = df[columns].apply(pd.to_numeric, errors="coerce").dropna()
    n_vars = len(columns)

    corr_arr = np.zeros((n_vars, n_vars))
    p_arr = np.ones((n_vars, n_vars))
    n_arr = np.full((n_vars, n_vars), len(data))

    for i in range(n_vars):
        for j in range(n_vars):
            if i == j:
                corr_arr[i, j] = 1.0
                p_arr[i, j] = 0.0
            else:
                # 控制变量 = 除 i, j 外的所有变量
                covars = [columns[k] for k in range(n_vars) if k != i and k != j]
                try:
                    if not covars:
                        r, p = stats.pearsonr(data[columns[i]], data[columns[j]]) if method == "pearson" else stats.spearmanr(data[columns[i]], data[columns[j]])
                    else:
                        pc = pg.partial_corr(
                            data=data,
                            x=columns[i],
                            y=columns[j],
                            covar=covars,
                            method=method,
                        )
                        r = pc["r"].values[0]
                        p = pc["p-val"].values[0]
                    corr_arr[i, j] = r
                    p_arr[i, j] = p
                except Exception as exc:
                    logger.debug("pairwise 相关计算失败，置 NaN: %s", exc)
                    corr_arr[i, j] = np.nan
                    p_arr[i, j] = np.nan

    corr_df = pd.DataFrame(corr_arr, index=columns, columns=columns)
    p_df = pd.DataFrame(p_arr, index=columns, columns=columns)
    n_df = pd.DataFrame(n_arr, index=columns, columns=columns)

    sig_mask = _stars_matrix_holm(p_df)  # s1008-01/S2：族内 Holm 校正后再打星

    corr_vals = corr_df.to_numpy(dtype=float, copy=True)
    p_vals = p_df.to_numpy(dtype=float, copy=True)
    corr_vals[~np.isnan(corr_vals)] = np.round(corr_vals[~np.isnan(corr_vals)], 3)
    p_vals[~np.isnan(p_vals)] = np.round(p_vals[~np.isnan(p_vals)], 4)
    corr_rounded = pd.DataFrame(corr_vals, index=columns, columns=columns)
    p_rounded = pd.DataFrame(p_vals, index=columns, columns=columns)

    # Fisher-z CI for partial correlations
    from .effect_size_ci import correlation_matrix_ci
    ci_low_df, ci_high_df = correlation_matrix_ci(corr_rounded, n_df, confidence=0.95)

    return CorrResult(
        test_type=f"partial_{method}",
        corr_matrix=corr_rounded,
        p_matrix=p_rounded,
        n_matrix=n_df,
        sig_mask=sig_mask,
        ci_low_matrix=ci_low_df,
        ci_high_matrix=ci_high_df,
    )


def point_biserial_corr(
    df: pd.DataFrame,
    continuous_col: str,
    binary_col: str,
) -> CorrResult:
    """
    点二列相关（一个连续变量 × 一个真正的二分类变量）。

    返回格式与 CorrResult 兼容。
    """
    data = df[[continuous_col, binary_col]].copy()
    data[continuous_col] = pd.to_numeric(data[continuous_col], errors="coerce")
    data = data.dropna()

    unique_vals = data[binary_col].dropna().unique()
    if len(unique_vals) != 2:
        raise ValueError(f"点二列相关需要二分类变量，但'{binary_col}'有{len(unique_vals)}个水平。")

    # 将分类变量编码为 0/1
    mapping = {unique_vals[0]: 0, unique_vals[1]: 1}
    data["_binary"] = data[binary_col].map(mapping)

    r, p = stats.pointbiserialr(data[continuous_col], data["_binary"])

    cols = [continuous_col, binary_col]
    corr_arr = np.array([[1.0, r], [r, 1.0]])
    p_arr = np.array([[0.0, p], [p, 0.0]])
    n = len(data)
    n_arr = np.array([[n, n], [n, n]])

    sig = _stars(p)
    sig_mask_arr = np.array([["", sig], [sig, ""]])

    # Fisher-z CI for point-biserial r
    from .effect_size_ci import fisher_z_ci
    ci = fisher_z_ci(float(r), int(n), confidence=0.95)
    ci_lo, ci_hi = (ci[0] if ci[0] is not None else np.nan,
                    ci[1] if ci[1] is not None else np.nan)
    ci_low_arr = np.array([[1.0, ci_lo], [ci_lo, 1.0]])
    ci_high_arr = np.array([[1.0, ci_hi], [ci_hi, 1.0]])

    return CorrResult(
        test_type="point_biserial",
        corr_matrix=pd.DataFrame(np.round(corr_arr, 3), index=cols, columns=cols),
        p_matrix=pd.DataFrame(np.round(p_arr, 4), index=cols, columns=cols),
        n_matrix=pd.DataFrame(n_arr, index=cols, columns=cols),
        sig_mask=pd.DataFrame(sig_mask_arr, index=cols, columns=cols),
        ci_low_matrix=pd.DataFrame(np.round(ci_low_arr, 3), index=cols, columns=cols),
        ci_high_matrix=pd.DataFrame(np.round(ci_high_arr, 3), index=cols, columns=cols),
    )
