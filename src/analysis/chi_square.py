"""卡方检验：独立性检验 / 拟合优度"""

import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChiSquareResult:
    test_type: str  # "independence", "gof"
    chi_sq: float
    df: int
    p_value: float
    effect_size: float
    effect_size_name: str  # "Cramer's V", "Cohen's w"
    contingency_table: pd.DataFrame
    expected_table: pd.DataFrame = None
    warning: str = ""
    effect_size_ci_lower: Optional[float] = None  # 非中心 χ² 近似 CI 下限
    effect_size_ci_upper: Optional[float] = None  # 非中心 χ² 近似 CI 上限


def chi_square_independence(
    df: pd.DataFrame,
    col1: str,
    col2: str,
) -> ChiSquareResult:
    """
    卡方独立性检验（列联表分析）。
    自动检测小期望频数并提示。
    """
    # 构建列联表
    clean = df[[col1, col2]].dropna()
    contingency = pd.crosstab(clean[col1], clean[col2])

    chi2, p, dof, expected = stats.chi2_contingency(contingency)

    # Cramer's V
    n = contingency.sum().sum()
    min_dim = min(contingency.shape) - 1
    cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else 0.0

    # 小期望频数警告
    warning = ""
    if np.any(expected < 5):
        pct = np.mean(expected < 5) * 100
        warning = (
            f"有 {pct:.0f}% 的单元格期望频数小于5。"
            "对于2×2表建议使用Fisher精确检验。"
        )

    expected_df = pd.DataFrame(
        expected,
        index=contingency.index,
        columns=contingency.columns,
    )

    # 非中心 χ² 近似 CI（Phase 1.3 补缺口）
    from .effect_size_ci import chi_square_v_ci
    ci_low, ci_high = chi_square_v_ci(
        chi_sq=float(chi2),
        df=int(dof),
        n=int(n),
        k_min=max(min_dim, 1),
        confidence=0.95,
    )

    return ChiSquareResult(
        test_type="independence",
        chi_sq=round(float(chi2), 3),
        df=dof,
        p_value=round(float(p), 4),
        effect_size=round(float(cramers_v), 4),
        effect_size_name="Cramer's V",
        contingency_table=contingency,
        expected_table=expected_df,
        warning=warning,
        effect_size_ci_lower=round(ci_low, 4) if ci_low is not None else None,
        effect_size_ci_upper=round(ci_high, 4) if ci_high is not None else None,
    )


def chi_square_gof(
    df: pd.DataFrame,
    col: str,
    expected_props: Optional[list] = None,
) -> ChiSquareResult:
    """
    卡方拟合优度检验。
    检验观察频数是否与期望分布一致。

    参数：
        col: 分类变量列名
        expected_props: 期望比例列表（None则假设均匀分布）
    """
    clean = df[col].dropna()
    observed = clean.value_counts().sort_index()

    if expected_props is None:
        expected_props = [1.0 / len(observed)] * len(observed)

    # 确保长度匹配
    if len(expected_props) != len(observed):
        raise ValueError(f"期望比例数量({len(expected_props)})与类别数({len(observed)})不匹配。")

    total = observed.sum()
    expected_freq = [total * p for p in expected_props]

    chi2, p = stats.chisquare(observed.values, f_exp=expected_freq)

    # Cohen's w
    prop_obs = observed.values / total
    w = np.sqrt(sum((prop_obs[i] - expected_props[i])**2 / expected_props[i] for i in range(len(prop_obs))))

    contingency = pd.DataFrame({
        "类别": observed.index.tolist(),
        "观测频数": observed.values,
        "期望频数": [round(e, 2) for e in expected_freq],
        "期望比例": expected_props,
        "残差": (observed.values - expected_freq).round(2),
    })

    # 非中心 χ² 近似 CI for Cohen's w
    from .effect_size_ci import chi_square_w_ci
    ci_low, ci_high = chi_square_w_ci(
        chi_sq=float(chi2),
        df=len(observed) - 1,
        n=int(total),
        confidence=0.95,
    )

    return ChiSquareResult(
        test_type="gof",
        chi_sq=round(float(chi2), 3),
        df=len(observed) - 1,
        p_value=round(float(p), 4),
        effect_size=round(float(w), 4),
        effect_size_name="Cohen's w",
        contingency_table=contingency,
        effect_size_ci_lower=round(ci_low, 4) if ci_low is not None else None,
        effect_size_ci_upper=round(ci_high, 4) if ci_high is not None else None,
    )
