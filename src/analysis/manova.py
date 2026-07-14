"""MANOVA / MANCOVA：多元方差分析（多个因变量的组间差异检验）"""
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class MANOVAResult:
    test_type: str  # "manova" or "mancova"
    multivariate_tests: pd.DataFrame
    univariate_tests: Optional[pd.DataFrame] = None
    descriptive: Optional[pd.DataFrame] = None
    box_m: Optional[Dict[str, float]] = None
    eta_squared: Optional[pd.DataFrame] = None
    n_obs: int = 0
    n_groups: int = 0
    dependent_vars: List[str] = field(default_factory=list)
    warning: str = ""


def manova(
    df: pd.DataFrame,
    dvs: List[str],
    iv: str,
    covariates: Optional[List[str]] = None,
) -> MANOVAResult:
    """
    MANOVA（多元方差分析）/ MANCOVA（含协变量时）。

    检验多个因变量作为整体在组间是否有显著差异。
    输出四种多元检验统计量：Pillai's Trace, Wilks' Lambda,
    Hotelling's Trace, Roy's Largest Root。

    参数：
        df: 数据框
        dvs: 因变量列表（≥2 个连续变量）
        iv: 分组自变量（类别型）
        covariates: 协变量列表（可选，有则为 MANCOVA）
    """
    from statsmodels.multivariate.manova import MANOVA as SM_MANOVA

    cols = dvs + [iv] + (covariates or [])
    clean = df[cols].copy()
    for dv in dvs:
        clean[dv] = pd.to_numeric(clean[dv], errors="coerce")
    if covariates:
        for cov in covariates:
            clean[cov] = pd.to_numeric(clean[cov], errors="coerce")
    clean = clean.dropna()

    n_obs = len(clean)
    groups = clean[iv].unique()
    n_groups = len(groups)

    if n_groups < 2:
        raise ValueError(f"MANOVA 要求分组变量至少有 2 组，当前「{iv}」只有 {n_groups} 组。")
    if len(dvs) < 2:
        raise ValueError("MANOVA 至少需要 2 个因变量。如只有 1 个，请用单因素 ANOVA。")

    test_type = "mancova" if covariates else "manova"

    if covariates:
        formula = " + ".join(dvs) + " ~ " + iv + " + " + " + ".join(covariates)
    else:
        formula = " + ".join(dvs) + " ~ " + iv

    mv = SM_MANOVA.from_formula(formula, data=clean)
    mv_test = mv.mv_test()

    mv_rows = []
    iv_result = mv_test.results.get(iv)
    if iv_result is not None:
        stat_table = iv_result["stat"]
        for test_name in ["Pillai's trace", "Wilks' lambda", "Hotelling-Lawley trace", "Roy's greatest root"]:
            if test_name in stat_table.index:
                row = stat_table.loc[test_name]
                mv_rows.append({
                    "检验": test_name,
                    "统计量": round(float(row["Value"]), 4),
                    "F": round(float(row["F Value"]), 3),
                    "假设 df": int(row["Num DF"]),
                    "误差 df": round(float(row["Den DF"]), 1),
                    "p": round(float(row["Pr > F"]), 4),
                    "偏 η²": round(_partial_eta2_mv(row), 4),
                })

    multivariate_tests = pd.DataFrame(mv_rows)

    univariate_rows = []
    for dv in dvs:
        group_data = [
            clean[clean[iv] == g][dv].values for g in groups
        ]
        f_stat, p_val = stats.f_oneway(*group_data)

        ss_between = sum(
            len(gd) * (gd.mean() - clean[dv].mean()) ** 2
            for gd in group_data
        )
        ss_total = ((clean[dv] - clean[dv].mean()) ** 2).sum()
        eta2 = ss_between / ss_total if ss_total > 0 else 0

        univariate_rows.append({
            "因变量": dv,
            "F": round(float(f_stat), 3),
            "p": round(float(p_val), 4),
            "η²": round(eta2, 4),
        })

    univariate_tests = pd.DataFrame(univariate_rows)

    desc_rows = []
    for dv in dvs:
        for g in sorted(groups):
            g_data = clean[clean[iv] == g][dv]
            desc_rows.append({
                "因变量": dv,
                "组别": str(g),
                "M": round(float(g_data.mean()), 3),
                "SD": round(float(g_data.std()), 3),
                "N": len(g_data),
            })
    descriptive_table = pd.DataFrame(desc_rows)

    box_m = _box_m_test(clean, dvs, iv)

    warning = ""
    if box_m and box_m["p"] < 0.001:
        warning = "⚠ Box's M 检验显著（p < .001），协方差矩阵齐性假设可能不满足。建议优先参考 Pillai's Trace（对违反较稳健）。"
    if n_obs < n_groups * len(dvs) * 5:
        warning += " ⚠ 样本量偏小，建议每组至少有 因变量数×5 个观测。"

    return MANOVAResult(
        test_type=test_type,
        multivariate_tests=multivariate_tests,
        univariate_tests=univariate_tests,
        descriptive=descriptive_table,
        box_m=box_m,
        n_obs=n_obs,
        n_groups=n_groups,
        dependent_vars=dvs,
        warning=warning.strip(),
    )


# ===========================================================================
# 辅助函数
# ===========================================================================

def _partial_eta2_mv(row) -> float:
    """从多元检验行计算近似偏 η²"""
    try:
        f_val = float(row["F Value"])
        num_df = float(row["Num DF"])
        den_df = float(row["Den DF"])
        return (f_val * num_df) / (f_val * num_df + den_df)
    except (KeyError, ZeroDivisionError):
        return 0.0


def _box_m_test(df: pd.DataFrame, dvs: List[str], iv: str) -> Optional[Dict[str, float]]:
    """
    Box's M 检验：检验各组协方差矩阵是否相等。
    使用近似 F 检验。
    """
    try:
        groups = df[iv].unique()
        k = len(groups)
        p = len(dvs)
        n_total = len(df)

        cov_matrices = []
        ns = []
        for g in groups:
            g_data = df[df[iv] == g][dvs].values
            ns.append(len(g_data))
            cov_matrices.append(np.cov(g_data, rowvar=False))

        S_pooled = np.zeros((p, p))
        for i, cov in enumerate(cov_matrices):
            S_pooled += (ns[i] - 1) * cov
        S_pooled /= (n_total - k)

        M = 0.0
        for i, cov in enumerate(cov_matrices):
            ni = ns[i]
            if ni <= 1:
                continue
            sign, logdet_cov = np.linalg.slogdet(cov)
            sign_p, logdet_pool = np.linalg.slogdet(S_pooled)
            if sign <= 0 or sign_p <= 0:
                return None
            M += (ni - 1) * (logdet_pool - logdet_cov)

        c = (2 * p * p + 3 * p - 1) / (6 * (p + 1) * (k - 1))
        c *= sum(1.0 / (ni - 1) for ni in ns) - 1.0 / (n_total - k)

        df_chi = p * (p + 1) * (k - 1) / 2
        chi2 = (1 - c) * M
        p_val = 1 - stats.chi2.cdf(chi2, df_chi)

        return {
            "M": round(float(M), 3),
            "chi2_approx": round(float(chi2), 3),
            "df": int(df_chi),
            "p": round(float(p_val), 4),
        }
    except Exception:
        return None
