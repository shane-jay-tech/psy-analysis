"""t 检验：独立样本 / 配对样本 / 单样本"""

import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class TTestResult:
    test_type: str  # "independent", "paired", "one_sample"
    t_statistic: float
    df: float
    p_value: float
    mean_diff: float
    ci_lower: float
    ci_upper: float
    effect_size: float
    effect_size_name: str  # "Cohen's d", "Cohen's dz"
    effect_size_ci_lower: Optional[float] = None  # Cohen's d 的95% CI下限
    effect_size_ci_upper: Optional[float] = None  # Cohen's d 的95% CI上限
    group_stats: Optional[pd.DataFrame] = None
    assumption_normality: Optional[dict] = None
    assumption_equal_var: Optional[dict] = None
    is_welch: bool = False


def independent_ttest(
    df: pd.DataFrame,
    dv: str,
    iv: str,
    confidence: float = 0.95,
) -> TTestResult:
    """
    独立样本t检验。
    自动检测方差异质并使用Welch校正。
    """
    groups = df[iv].dropna().unique()
    if len(groups) != 2:
        raise ValueError(
            f"独立样本t检验需要恰好2个分组，但'{iv}'有{len(groups)}个水平。"
            f"如需比较多组，请使用单因素方差分析。"
        )

    g1 = pd.to_numeric(df[df[iv] == groups[0]][dv], errors="coerce").dropna()
    g2 = pd.to_numeric(df[df[iv] == groups[1]][dv], errors="coerce").dropna()

    # 方差齐性检验
    levene_stat, levene_p = stats.levene(g1, g2)
    equal_var = levene_p > 0.05

    # 选择t检验方式
    if equal_var:
        t_stat, p_val = stats.ttest_ind(g1, g2)
        df_t = len(g1) + len(g2) - 2
        is_welch = False
    else:
        t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)
        df_t = _welch_df(g1, g2)
        is_welch = True

    # 效应量 Cohen's d
    d = _cohens_d(g1, g2)

    # 均值差置信区间
    mean_diff = g1.mean() - g2.mean()
    se_pooled = np.sqrt(g1.var() / len(g1) + g2.var() / len(g2))
    alpha = 1 - confidence
    t_crit = stats.t.ppf(1 - alpha / 2, df_t)
    ci_lower = mean_diff - t_crit * se_pooled
    ci_upper = mean_diff + t_crit * se_pooled

    # 分组描述
    group_stats = pd.DataFrame({
        "组别": [str(groups[0]), str(groups[1])],
        "N": [len(g1), len(g2)],
        "M": [round(g1.mean(), 2), round(g2.mean(), 2)],
        "SD": [round(g1.std(), 2), round(g2.std(), 2)],
    })

    # Cohen's d 的95% CI
    d_ci_low, d_ci_high = _cohens_d_ci(d, len(g1), len(g2), confidence)

    return TTestResult(
        test_type="independent",
        t_statistic=round(float(t_stat), 3),
        df=round(float(df_t), 2),
        p_value=round(float(p_val), 4),
        mean_diff=round(float(mean_diff), 3),
        ci_lower=round(float(ci_lower), 3),
        ci_upper=round(float(ci_upper), 3),
        effect_size=round(float(d), 3),
        effect_size_name="Cohen's d",
        effect_size_ci_lower=round(float(d_ci_low), 3) if d_ci_low is not None else None,
        effect_size_ci_upper=round(float(d_ci_high), 3) if d_ci_high is not None else None,
        group_stats=group_stats,
        assumption_equal_var={
            "passed": equal_var,
            "statistic": round(float(levene_stat), 3),
            "p_value": round(float(levene_p), 4),
        },
        is_welch=is_welch,
    )


def paired_ttest(
    df: pd.DataFrame,
    col1: str,
    col2: str,
    confidence: float = 0.95,
) -> TTestResult:
    """配对样本t检验"""
    x = pd.to_numeric(df[col1], errors="coerce")
    y = pd.to_numeric(df[col2], errors="coerce")

    # 成对删除
    mask = x.notna() & y.notna()
    x, y = x[mask], y[mask]

    t_stat, p_val = stats.ttest_rel(x, y)
    diff = x - y
    n = len(diff)

    # Cohen's dz（配对设计效应量）
    # CI计算：基于非中心t分布，与独立样本d相同原理
    # 参考：Hedges & Olkin (1985)
    d_z = float(diff.mean() / diff.std()) if diff.std() > 0 else 0.0

    alpha = 1 - confidence
    t_crit = stats.t.ppf(1 - alpha / 2, n - 1)
    se = diff.std() / np.sqrt(n)
    ci_lower = diff.mean() - t_crit * se
    ci_upper = diff.mean() + t_crit * se

    # Cohen's dz 的95% CI（基于非中心t分布）
    # 配对设计的ncp = dz * sqrt(n)，与单样本设计相同
    dz_ci_low, dz_ci_high = _cohens_d_ci_one_sample(d_z, n, confidence)

    group_stats = pd.DataFrame({
        "测量": [col1, col2, "差值"],
        "N": [n, n, n],
        "M": [round(x.mean(), 2), round(y.mean(), 2), round(diff.mean(), 2)],
        "SD": [round(x.std(), 2), round(y.std(), 2), round(diff.std(), 2)],
    })

    return TTestResult(
        test_type="paired",
        t_statistic=round(float(t_stat), 3),
        df=n - 1,
        p_value=round(float(p_val), 4),
        mean_diff=round(float(diff.mean()), 3),
        ci_lower=round(float(ci_lower), 3),
        ci_upper=round(float(ci_upper), 3),
        effect_size=round(float(d_z), 3),
        effect_size_name="Cohen's dz",
        effect_size_ci_lower=round(float(dz_ci_low), 3) if dz_ci_low is not None else None,
        effect_size_ci_upper=round(float(dz_ci_high), 3) if dz_ci_high is not None else None,
        group_stats=group_stats,
    )


def one_sample_ttest(
    df: pd.DataFrame,
    dv: str,
    test_value: float,
    confidence: float = 0.95,
) -> TTestResult:
    """单样本t检验"""
    x = pd.to_numeric(df[dv], errors="coerce").dropna()

    t_stat, p_val = stats.ttest_1samp(x, test_value)
    n = len(x)

    # Cohen's d (单样本设计)
    # 基于非中心t分布计算CI，参考 Hedges & Olkin (1985)
    d = (x.mean() - test_value) / x.std() if x.std() > 0 else 0.0
    # 单样本设计：ncp = d * sqrt(n), df = n - 1
    d_ci_low, d_ci_high = _cohens_d_ci_one_sample(d, n, confidence)

    alpha = 1 - confidence
    t_crit = stats.t.ppf(1 - alpha / 2, n - 1)
    se = x.std() / np.sqrt(n)
    mean_diff = x.mean() - test_value
    ci_lower = mean_diff - t_crit * se
    ci_upper = mean_diff + t_crit * se

    group_stats = pd.DataFrame({
        "": ["样本", "检验值"],
        "N": [n, "-"],
        "M": [round(x.mean(), 2), test_value],
        "SD": [round(x.std(), 2), "-"],
    })

    return TTestResult(
        test_type="one_sample",
        t_statistic=round(float(t_stat), 3),
        df=n - 1,
        p_value=round(float(p_val), 4),
        mean_diff=round(float(mean_diff), 3),
        ci_lower=round(float(ci_lower), 3),
        ci_upper=round(float(ci_upper), 3),
        effect_size=round(float(d), 3),
        effect_size_name="Cohen's d",
        effect_size_ci_lower=round(float(d_ci_low), 3) if d_ci_low is not None else None,
        effect_size_ci_upper=round(float(d_ci_high), 3) if d_ci_high is not None else None,
        group_stats=group_stats,
    )


def _cohens_d(x: pd.Series, y: pd.Series) -> float:
    """
    计算 Cohen's d（独立样本）。

    CI计算方法：基于非中心t分布的迭代搜索（brentq），
    参考文献：Hedges, L. V., & Olkin, I. (1985). Statistical Methods for Meta-Analysis.
    """
    n1, n2 = len(x), len(y)
    s1, s2 = x.var(), y.var()

    # 合并方差
    pooled_std = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return (x.mean() - y.mean()) / pooled_std


def _welch_df(x: pd.Series, y: pd.Series) -> float:
    """Welch-Satterthwaite 自由度"""
    n1, n2 = len(x), len(y)
    v1, v2 = x.var(), y.var()
    se1 = v1 / n1
    se2 = v2 / n2
    num = (se1 + se2) ** 2
    den = (se1 ** 2) / (n1 - 1) + (se2 ** 2) / (n2 - 1)
    return num / den if den > 0 else n1 + n2 - 2


def _cohens_d_ci(d: float, n1: int, n2: int, confidence: float = 0.95) -> Tuple[Optional[float], Optional[float]]:
    """计算 Cohen's d 的置信区间（基于非中心t分布）。

    d 的标准误：se_d = sqrt((n1+n2)/(n1*n2) + d²/(2*(n1+n2)))
    然后使用非中心t分布的迭代搜索确定CI边界。
    """
    import numpy as np
    from scipy.stats import nct as _nct
    from scipy.optimize import brentq

    df = n1 + n2 - 2
    if df <= 0:
        return None, None

    try:
        # d 的标准误（Hedges & Olkin, 1985的近似）
        n_harm = 1.0 / (1.0 / n1 + 1.0 / n2)  # 调和均值的一半? 实际上 d 的方差 ≈ (n1+n2)/(n1*n2) + d²/(2*(n1+n2))
        se_d = np.sqrt((n1 + n2) / (n1 * n2) + d ** 2 / (2 * (n1 + n2)))

        alpha = 1 - confidence
        t_obs = d / se_d if se_d > 0 else 0.0

        # 使用非中心t分布求解CI
        # lambda (ncp) = d / sqrt(1/n1 + 1/n2) — 对于独立样本t检验
        ncp_obs = d * np.sqrt(n1 * n2 / (n1 + n2))

        t_crit_upper = _nct.ppf(1 - alpha / 2, df, 0)
        t_crit_lower = _nct.ppf(alpha / 2, df, 0)

        def _diff_lower(ncp):
            return _nct.ppf(alpha / 2, df, ncp) - t_obs

        def _diff_upper(ncp):
            return _nct.ppf(1 - alpha / 2, df, ncp) - t_obs

        # 搜索 ncp 然后转换为 d
        ncp_range = max(abs(ncp_obs) * 3, 10)

        try:
            ncp_low = brentq(_diff_lower, -ncp_range, ncp_range, maxiter=100)
            d_low = ncp_low / np.sqrt(n1 * n2 / (n1 + n2))
        except (ValueError, ZeroDivisionError):
            d_low = None

        try:
            ncp_high = brentq(_diff_upper, -ncp_range, ncp_range, maxiter=100)
            d_high = ncp_high / np.sqrt(n1 * n2 / (n1 + n2))
        except (ValueError, ZeroDivisionError):
            d_high = None

        d_low_val = round(float(d_low), 3) if d_low is not None else None
        d_high_val = round(float(d_high), 3) if d_high is not None else None
        # 确保 lower <= upper
        if d_low_val is not None and d_high_val is not None:
            if d_low_val > d_high_val:
                d_low_val, d_high_val = d_high_val, d_low_val
        return d_low_val, d_high_val
    except Exception:
        return None, None


def _cohens_d_ci_one_sample(d: float, n: int, confidence: float = 0.95):
    """
    计算单样本Cohen's d的95%置信区间（基于非中心t分布）。

    参考文献：Hedges, L. V., & Olkin, I. (1985). Statistical Methods for Meta-Analysis. Academic Press.

    单样本设计：ncp = d * sqrt(n), df = n - 1
    """
    import numpy as np
    from scipy.stats import nct as _nct
    from scipy.optimize import brentq

    df = n - 1
    if df <= 0:
        return None, None

    try:
        ncp_obs = d * np.sqrt(n)
        alpha = 1 - confidence

        t_obs = d / (1.0 / np.sqrt(n)) if np.sqrt(n) > 0 else 0.0

        def _diff_lower(ncp):
            return _nct.ppf(alpha / 2, df, ncp) - t_obs

        def _diff_upper(ncp):
            return _nct.ppf(1 - alpha / 2, df, ncp) - t_obs

        ncp_range = max(abs(ncp_obs) * 3, 10)

        ncp_low = brentq(_diff_lower, -ncp_range, ncp_range, maxiter=100)
        d_low = ncp_low / np.sqrt(n)

        ncp_high = brentq(_diff_upper, -ncp_range, ncp_range, maxiter=100)
        d_high = ncp_high / np.sqrt(n)

        d_low_val = round(float(d_low), 3)
        d_high_val = round(float(d_high), 3)
        if d_low_val > d_high_val:
            d_low_val, d_high_val = d_high_val, d_low_val
        return d_low_val, d_high_val
    except Exception:
        return None, None
