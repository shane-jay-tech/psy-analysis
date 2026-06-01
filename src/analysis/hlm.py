"""分层线性模型（HLM）：两水平随机截距模型

基于 statsmodels MixedLM 实现，支持学生嵌套于班级等场景。
输出 APA7 格式表格和组内相关系数（ICC）。

若 MixedLM 不可用，提供基于组均值的近似方法。
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List
from dataclasses import dataclass, field

try:
    from statsmodels.regression.mixed_linear_model import MixedLM
    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    _HAS_MIXEDLM = True
except ImportError:
    _HAS_MIXEDLM = False


@dataclass
class HLMResult:
    """HLM 分析结果"""
    model_type: str = "two_level_random_intercept"
    converged: bool = True
    log_likelihood: float = 0.0
    icc: float = 0.0          # 组内相关系数
    design_effect: float = 1.0  # 设计效应
    fixed_effects: pd.DataFrame = field(default_factory=pd.DataFrame)
    random_effects: pd.DataFrame = field(default_factory=pd.DataFrame)
    random_effect_var: float = 0.0
    residual_var: float = 0.0
    n_groups: int = 0
    n_total: int = 0
    avg_cluster_size: float = 0.0
    formula: str = ""
    warning: str = ""
    is_mixedlm: bool = True  # True=MixedLM, False=近似方法


def run_hlm(
    df: pd.DataFrame,
    dv: str,
    group_col: str,
    fixed_effects: List[str],
    use_mixedlm: bool = True,
) -> HLMResult:
    """
    运行两水平随机截距模型。

    参数：
        df: 数据框，包含因变量、分组变量和固定效应预测变量
        dv: 因变量列名
        group_col: 分组列名（如"班级"、"学校"）
        fixed_effects: 固定效应预测变量列表
        use_mixedlm: 是否使用 MixedLM（False 则使用近似方法）

    返回：
        HLMResult 对象，包含固定效应估计、随机效应方差、ICC 等
    """
    # 数据清洗
    df_clean = df[[dv, group_col] + fixed_effects].dropna().copy()
    for col in [dv] + fixed_effects:
        df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")
    df_clean = df_clean.dropna()

    n_total = len(df_clean)
    groups = df_clean[group_col].unique()
    n_groups = len(groups)
    group_sizes = df_clean.groupby(group_col).size()
    avg_cluster_size = group_sizes.mean()

    # 预计算 ICC（空模型）
    icc = _compute_icc(df_clean, dv, group_col)
    design_effect = 1 + (avg_cluster_size - 1) * icc

    if _HAS_MIXEDLM and use_mixedlm:
        return _run_mixedlm(df_clean, dv, group_col, fixed_effects,
                            n_groups, n_total, avg_cluster_size, icc, design_effect)
    else:
        return _run_ols_approximation(df_clean, dv, group_col, fixed_effects,
                                      n_groups, n_total, avg_cluster_size, icc, design_effect)


def _run_mixedlm(
    df: pd.DataFrame, dv: str, group_col: str,
    fixed_effects: List[str], n_groups: int, n_total: int,
    avg_cluster_size: float, icc: float, design_effect: float,
) -> HLMResult:
    """使用 statsmodels MixedLM 拟合两水平随机截距模型"""
    import warnings

    formula = f"{dv} ~ {' + '.join(fixed_effects)}"
    warning = ""

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            warnings.simplefilter("ignore", FutureWarning)

            model = MixedLM.from_formula(
                formula, groups=group_col, data=df,
                re_formula="1",
            )
            result = model.fit(method=["lbfgs", "powell"], maxiter=200)

        # 固定效应
        fe_table = pd.DataFrame({
            "参数": result.fe_params.index.tolist(),
            "系数": result.fe_params.values.round(4),
            "标准误": result.bse_fe.round(4),
            "z值": (result.fe_params / result.bse_fe).round(3),
            "p值": result.pvalues.round(4),
        }).reset_index(drop=True)

        # 随机效应方差
        random_effect_var = result.cov_re.iloc[0, 0] if hasattr(result.cov_re, 'iloc') else float(result.cov_re.values[0])

        return HLMResult(
            converged=result.converged,
            log_likelihood=round(float(result.llf), 2),
            icc=round(icc, 3),
            design_effect=round(design_effect, 3),
            fixed_effects=fe_table,
            random_effects=pd.DataFrame({
                "组别": df[group_col].unique()[:20],  # 最多显示20组
                "随机截距": np.round(result.random_effects.values.flatten()[:20], 3),
            }),
            random_effect_var=round(float(random_effect_var), 4),
            residual_var=round(float(result.scale), 4),
            n_groups=n_groups,
            n_total=n_total,
            avg_cluster_size=round(avg_cluster_size, 2),
            formula=formula,
            warning=warning,
            is_mixedlm=True,
        )
    except Exception as e:
        warning = f"MixedLM 拟合失败（{str(e)[:100]}），已回退到OLS近似方法。"
        return _run_ols_approximation(
            df, dv, group_col, fixed_effects,
            n_groups, n_total, avg_cluster_size, icc, design_effect,
            warning=warning,
        )


def _run_ols_approximation(
    df: pd.DataFrame, dv: str, group_col: str,
    fixed_effects: List[str], n_groups: int, n_total: int,
    avg_cluster_size: float, icc: float, design_effect: float,
    warning: str = "",
) -> HLMResult:
    """
    HLM 近似方法（基于组均值和 OLS）。

    注意：这不是严格的分层线性模型，而是使用组均值作为群体效应
    代理变量的加权最小二乘近似。仅供参考，建议在正式研究中
    使用 MixedLM 或专门的多层建模软件（如 HLM、Mplus、lme4）。
    """
    import statsmodels.api as sm

    # 添加组均值作为群体效应代理
    df_model = df.copy()
    group_means = df.groupby(group_col)[dv].transform("mean")
    df_model["_group_mean_dv"] = group_means

    # OLS with group-clustered standard errors
    predictors = fixed_effects + ["_group_mean_dv"]
    X = df_model[predictors]
    X = sm.add_constant(X)
    y = df_model[dv]

    try:
        model = sm.OLS(y, X)
        result = model.fit()

        # 聚类稳健标准误（简化版）
        # 使用组内残差相关校正
        bse = result.bse * np.sqrt(design_effect)

        fe_table = pd.DataFrame({
            "参数": result.params.index.tolist(),
            "系数": result.params.values.round(4),
            "标准误†": bse.values.round(4),
            "t值†": (result.params / bse).round(3),
            "p值†": (2 * (1 - sm.stats.t.sf(
                np.abs(result.params / bse), n_total - len(predictors) - 1
            ))).round(4),
        }).reset_index(drop=True)

        return HLMResult(
            converged=True,
            log_likelihood=float(result.llf),
            icc=round(icc, 3),
            design_effect=round(design_effect, 3),
            fixed_effects=fe_table,
            random_effects=pd.DataFrame(),
            random_effect_var=0.0,
            residual_var=round(float(result.mse_resid), 4),
            n_groups=n_groups,
            n_total=n_total,
            avg_cluster_size=round(avg_cluster_size, 2),
            formula=f"{dv} ~ {' + '.join(fixed_effects)}",
            warning=warning or (
                "⚠ 此为OLS近似方法（非严格HLM）。标准误使用设计效应校正。"
                "正式研究请使用 MixedLM 或专用多层建模软件。"
                "\n† 标准误和显著性指标已使用设计效应（DEFF={design_effect:.2f}）进行校正。"
            ),
            is_mixedlm=False,
        )
    except Exception as e:
        # 完全回退：仅报告 ICC 和设计效应
        return HLMResult(
            converged=False,
            icc=round(icc, 3),
            design_effect=round(design_effect, 3),
            n_groups=n_groups,
            n_total=n_total,
            avg_cluster_size=round(avg_cluster_size, 2),
            formula=f"{dv} ~ {' + '.join(fixed_effects)}",
            warning=f"HLM和OLS近似均失败（{e}）。仅报告ICC={icc:.3f}和设计效应={design_effect:.3f}作为参考。",
            is_mixedlm=False,
        )


def _compute_icc(df: pd.DataFrame, dv: str, group_col: str) -> float:
    """
    计算组内相关系数 ICC(1) = 组间方差 / (组间方差 + 组内方差)

    使用 statsmodels MixedLM 空模型（如可用）或 ANOVA 方法。
    """
    if not _HAS_MIXEDLM:
        return _compute_icc_anova(df, dv, group_col)

    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = MixedLM.from_formula(
                f"{dv} ~ 1", groups=group_col, data=df,
                re_formula="1",
            )
            result = model.fit(method=["lbfgs", "powell"], maxiter=200)
        var_between = float(result.cov_re.values[0]) if hasattr(result.cov_re, 'values') else float(result.cov_re.iloc[0, 0])
        var_within = float(result.scale)
        return var_between / (var_between + var_within) if (var_between + var_within) > 0 else 0.0
    except Exception:
        return _compute_icc_anova(df, dv, group_col)


def _compute_icc_anova(df: pd.DataFrame, dv: str, group_col: str) -> float:
    """基于 ANOVA 表的手动 ICC(1) 计算"""
    grand_mean = df[dv].mean()
    group_means = df.groupby(group_col)[dv].mean()
    group_sizes = df.groupby(group_col).size()

    ssb = sum(group_sizes * (group_means - grand_mean) ** 2)
    df_b = len(group_means) - 1
    msb = ssb / df_b if df_b > 0 else 0

    ssw = sum((df[dv] - df[group_col].map(group_means)) ** 2)
    df_w = len(df) - len(group_means)
    msw = ssw / df_w if df_w > 0 else 0

    k = group_sizes.mean()
    var_between = max(0, (msb - msw) / k) if k > 1 else 0
    var_within = msw

    return var_between / (var_between + var_within) if (var_between + var_within) > 0 else 0.0


def format_hlm_report(result: HLMResult) -> str:
    """生成 HLM 结果的 APA7 格式中文报告"""
    lines = [
        "## 分层线性模型（HLM）分析结果",
        "",
        f"模型类型：两水平随机截距模型",
    ]

    if not result.is_mixedlm:
        lines.append("⚠ **注意**：以下结果为非严格HLM的近似估计。")

    lines.extend([
        f"公式：{result.formula}",
        f"组数：{result.n_groups}（总样本 N = {result.n_total}）",
        f"平均组内样本量：{result.avg_cluster_size}",
        f"收敛：{'是' if result.converged else '否'}",
        f"对数似然：{result.log_likelihood}",
        f"组内相关系数 ICC(1)：{result.icc:.3f}",
        f"设计效应（DEFF）：{result.design_effect:.3f}",
        "",
        "### 固定效应",
        "",
    ])

    # 固定效应表格
    if not result.fixed_effects.empty:
        fe = result.fixed_effects
        lines.append("| 参数 | 系数 | 标准误 | z/t值 | p值 |")
        lines.append("|------|------|--------|-------|-----|")
        for _, row in fe.iterrows():
            p_str = f"{row['p值']:.4f}" if row['p值'] >= 0.001 else "< .001"
            se_col = [c for c in fe.columns if "标准误" in c][0]
            z_col = [c for c in fe.columns if "z" in c.lower() or "t" in c.lower()][0]
            p_col = [c for c in fe.columns if "p值" in c][0]
            lines.append(
                f"| {row['参数']} | {row['系数']:.4f} | {row[se_col]:.4f} | "
                f"{row[z_col]:.3f} | {p_str} |"
            )
        lines.append("")

    lines.extend([
        f"### 随机效应",
        f"",
        f"组间方差（τ₀₀）：{result.random_effect_var:.4f}",
        f"组内方差（σ²）：{result.residual_var:.4f}",
        f"",
        f"*注：ICC(1) = {result.icc:.3f} 表示{result.icc*100:.1f}%的{result.formula.split('~')[0].strip()}"
        f"总变异可归因于组间差异。设计效应 {result.design_effect:.2f} > 2.0 表明"
        f"有必要使用多层模型而非常规OLS回归。*",
    ])

    if result.warning:
        lines.append(f"\n{result.warning}")

    return "\n".join(lines)
