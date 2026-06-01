"""回归分析：简单线性 / 多元回归 / 层次回归"""
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class RegressionResult:
    test_type: str  # "linear", "multiple", "hierarchical"
    model_summary: pd.DataFrame
    coef_table: pd.DataFrame
    r_squared: float = 0.0
    adj_r_squared: float = 0.0
    f_stat: float = 0.0
    f_p: float = 1.0
    vif_table: Optional[pd.DataFrame] = None
    block_tests: Optional[pd.DataFrame] = None
    diagnostics: Optional[pd.DataFrame] = None  # 影响点诊断
    f2_effect_sizes: Optional[pd.DataFrame] = None  # Cohen's f²
    high_influence_cases: List[int] = field(default_factory=list)
    warning: str = ""


def linear_regression(df: pd.DataFrame, dv: str, iv: str) -> RegressionResult:
    """
    简单线性回归：一个因变量 ~ 一个自变量。
    """
    import statsmodels.api as sm

    clean = df[[dv, iv]].copy()
    clean[dv] = pd.to_numeric(clean[dv], errors="coerce")
    clean[iv] = pd.to_numeric(clean[iv], errors="coerce")
    clean = clean.dropna()

    x = clean[iv].values
    y = clean[dv].values

    slope, intercept, r, p, std_err = stats.linregress(x, y)

    X = sm.add_constant(clean[iv])
    model = sm.OLS(clean[dv], X).fit()

    coef_table = pd.DataFrame({
        "变量": ["截距", iv],
        "B": [round(intercept, 3), round(slope, 3)],
        "SE": [round(float(model.bse.iloc[0]), 3), round(float(model.bse.iloc[1]), 3)],
        "t": [round(float(model.tvalues.iloc[0]), 3), round(float(model.tvalues.iloc[1]), 3)],
        "p": [round(float(model.pvalues.iloc[0]), 4), round(float(model.pvalues.iloc[1]), 4)],
    })

    r2 = round(r * r, 4)
    n = len(clean)

    # Cohen's f² overall
    f2 = r2 / (1 - r2) if r2 < 1 else float("inf")

    # 诊断
    diagnostics, high_cases, diag_warning = _compute_diagnostics(model, clean, dv, n)

    warning = ""
    if diag_warning:
        warning += diag_warning

    return RegressionResult(
        test_type="linear",
        model_summary=pd.DataFrame({
            "指标": ["R", "R²", "调整R²", "F", "p", "Cohen's f²"],
            "值": [
                round(abs(r), 3),
                r2,
                r2,
                "-",
                "-",
                round(f2, 3),
            ],
        }),
        coef_table=coef_table,
        r_squared=r2,
        adj_r_squared=r2,
        diagnostics=diagnostics,
        high_influence_cases=high_cases,
        f2_effect_sizes=pd.DataFrame({"变量": [iv], "Cohen's f²": [round(f2, 3)]}),
        warning=warning,
    )


def multiple_regression(
    df: pd.DataFrame,
    dv: str,
    ivs: List[str],
    method: str = "enter",
) -> RegressionResult:
    """
    多元回归（同时进入法）。
    """
    import statsmodels.api as sm

    cols = [dv] + ivs
    clean = df[cols].copy()
    for c in cols:
        clean[c] = pd.to_numeric(clean[c], errors="coerce")
    clean = clean.dropna()

    n = len(clean)
    k = len(ivs)

    X = sm.add_constant(clean[ivs])
    y = clean[dv]
    model = sm.OLS(y, X).fit()

    # 系数表
    coef_rows = []
    for var_name in ["const"] + ivs:
        param_key = var_name
        display_name = "常量" if var_name == "const" else var_name
        coef_rows.append({
            "变量": display_name,
            "B": round(float(model.params.get(param_key, 0)), 3),
            "SE": round(float(model.bse.get(param_key, 0)), 3),
            "β": round(float(_standardized_beta(model, param_key, clean, dv, ivs)), 3),
            "t": round(float(model.tvalues.get(param_key, 0)), 3),
            "p": round(float(model.pvalues.get(param_key, 0)), 4),
        })

    # VIF 共线性诊断
    vif_warning = ""
    vif = None
    try:
        vif = _calc_vif(clean[ivs])
        high_vif = vif[vif["VIF"] > 10]
        if len(high_vif) > 0:
            vif_warning = f"⚠ {', '.join(high_vif['变量'])} 的VIF>10，可能存在严重共线性问题。"
    except Exception:
        pass

    # Cohen's f²
    r2 = model.rsquared
    if r2 < 1:
        f2_overall = r2 / (1 - r2)
    else:
        f2_overall = float("inf")

    # Per-predictor f²
    f2_rows = []
    for var_name in ivs:
        # f² for predictor = (R²_full - R²_reduced) / (1 - R²_full)
        reduced_ivs = [v for v in ivs if v != var_name]
        if len(reduced_ivs) >= 1:
            X_red = sm.add_constant(clean[reduced_ivs])
            model_red = sm.OLS(y, X_red).fit()
            delta_r2 = r2 - model_red.rsquared
            f2_var = delta_r2 / (1 - r2) if r2 < 1 else 0.0
        else:
            f2_var = 0.0
        f2_rows.append({"变量": var_name, "Cohen's f²": round(f2_var, 3)})
    f2_rows.append({"变量": "整体模型", "Cohen's f²": round(f2_overall, 3)})

    # 诊断
    diagnostics, high_cases, diag_warning = _compute_diagnostics(model, clean, dv, n, k + 1)

    all_warnings = vif_warning
    if diag_warning:
        all_warnings += (" " if all_warnings else "") + diag_warning
    if n < (k + 1) * 10:
        all_warnings += f" ⚠ 样本量（N={n}）相对于自变量数量（k={k}）偏小，建议N ≥ 10×k={10*k}。"

    return RegressionResult(
        test_type="multiple",
        model_summary=pd.DataFrame({
            "指标": ["R", "R²", "调整R²", "F", "p", "Cohen's f²"],
            "值": [
                round(np.sqrt(r2), 3),
                round(r2, 4),
                round(model.rsquared_adj, 4),
                round(float(model.fvalue), 3),
                round(float(model.f_pvalue), 4),
                round(f2_overall, 3),
            ],
        }),
        coef_table=pd.DataFrame(coef_rows),
        r_squared=round(r2, 4),
        adj_r_squared=round(model.rsquared_adj, 4),
        f_stat=round(float(model.fvalue), 3),
        f_p=round(float(model.f_pvalue), 4),
        vif_table=vif,
        diagnostics=diagnostics,
        high_influence_cases=high_cases,
        f2_effect_sizes=pd.DataFrame(f2_rows),
        warning=all_warnings.strip(),
    )


def hierarchical_regression(
    df: pd.DataFrame,
    dv: str,
    blocks: List[List[str]],
) -> RegressionResult:
    """
    层次回归（分块进入法）。
    """
    import statsmodels.api as sm

    all_ivs = [v for block in blocks for v in block]
    cols = [dv] + all_ivs
    clean = df[cols].copy()
    for c in cols:
        clean[c] = pd.to_numeric(clean[c], errors="coerce")
    clean = clean.dropna()

    n = len(clean)
    block_results = []
    cumulative_vars = []
    prev_r2 = 0.0

    for i, block in enumerate(blocks):
        cumulative_vars.extend(block)
        X = sm.add_constant(clean[cumulative_vars])
        y = clean[dv]
        model = sm.OLS(y, X).fit()

        delta_r2 = model.rsquared - prev_r2
        prev_r2 = model.rsquared

        n = len(clean)
        k2 = len(cumulative_vars)
        k1 = k2 - len(block)
        if (1 - model.rsquared) > 0 and (n - k2 - 1) > 0:
            f_change = (delta_r2 / len(block)) / ((1 - model.rsquared) / (n - k2 - 1))
            p_change = 1 - stats.f.cdf(f_change, len(block), n - k2 - 1)
        else:
            f_change = 0
            p_change = 1.0

        # Cohen's f² for ΔR²
        f2_delta = delta_r2 / (1 - model.rsquared) if model.rsquared < 1 else 0.0

        block_results.append({
            "模型": f"模型{i+1}",
            "进入变量": ", ".join(block),
            "R²": round(model.rsquared, 4),
            "ΔR²": round(delta_r2, 4),
            "ΔF": round(f_change, 3),
            "ΔF p": round(p_change, 4),
            "Cohen's f² (ΔR²)": round(f2_delta, 3),
        })

    # 最终模型
    X_final = sm.add_constant(clean[all_ivs])
    final_model = sm.OLS(y, X_final).fit()

    coef_rows = []
    for var_name in ["常量"] + all_ivs:
        param_key = "const" if var_name == "常量" else var_name
        coef_rows.append({
            "变量": var_name,
            "B": round(float(final_model.params.get(param_key, 0)), 3),
            "SE": round(float(final_model.bse.get(param_key, 0)), 3),
            "β": round(float(_standardized_beta(final_model, param_key, clean, dv, all_ivs)), 3),
            "t": round(float(final_model.tvalues.get(param_key, 0)), 3),
            "p": round(float(final_model.pvalues.get(param_key, 0)), 4),
        })

    # 诊断
    diagnostics, high_cases, diag_warning = _compute_diagnostics(
        final_model, clean, dv, n, len(all_ivs) + 1
    )

    # Cohen's f² for overall model
    r2_final = final_model.rsquared
    f2_overall = r2_final / (1 - r2_final) if r2_final < 1 else float("inf")

    # Per-predictor f²
    f2_rows = []
    for var_name in all_ivs:
        reduced_ivs = [v for v in all_ivs if v != var_name]
        if len(reduced_ivs) >= 1:
            X_red = sm.add_constant(clean[reduced_ivs])
            model_red = sm.OLS(y, X_red).fit()
            delta = r2_final - model_red.rsquared
            f2_var = delta / (1 - r2_final) if r2_final < 1 else 0.0
        else:
            f2_var = 0.0
        f2_rows.append({"变量": var_name, "Cohen's f²": round(f2_var, 3)})
    f2_rows.append({"变量": "整体模型", "Cohen's f²": round(f2_overall, 3)})

    return RegressionResult(
        test_type="hierarchical",
        model_summary=pd.DataFrame(block_results),
        coef_table=pd.DataFrame(coef_rows),
        r_squared=round(r2_final, 4),
        adj_r_squared=round(final_model.rsquared_adj, 4),
        block_tests=pd.DataFrame(block_results),
        diagnostics=diagnostics,
        high_influence_cases=high_cases,
        f2_effect_sizes=pd.DataFrame(f2_rows),
        warning=diag_warning,
    )


# ===========================================================================
# 辅助函数
# ===========================================================================

def _standardized_beta(model, param_name: str, df: pd.DataFrame, dv: str, ivs: List[str]) -> float:
    """从非标准化系数计算标准化 β"""
    try:
        b = model.params.get(param_name, 0)
        if param_name == "const":
            return 0.0
        sd_x = df[param_name].std()
        sd_y = df[dv].std()
        return b * sd_x / sd_y if sd_y > 0 else 0.0
    except Exception:
        return 0.0


def _calc_vif(df: pd.DataFrame) -> pd.DataFrame:
    """计算方差膨胀因子"""
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    vif_data = []
    for i, col in enumerate(df.columns):
        try:
            vif = variance_inflation_factor(df.values, i)
            vif_data.append({"变量": col, "VIF": round(vif, 2)})
        except Exception:
            vif_data.append({"变量": col, "VIF": float("nan")})

    return pd.DataFrame(vif_data)


def _compute_diagnostics(
    model,
    clean_df: pd.DataFrame,
    dv: str,
    n: int,
    p: int = None,
) -> tuple:
    """
    计算回归诊断指标：Cook's D, 学生化删除残差, 杠杆值。
    标记高影响点。

    返回: (diagnostics_df, high_influence_indices, warning_text)
    """
    try:
        influence = model.get_influence()
        cooks_d = influence.cooks_distance[0]
        # 学生化删除残差
        try:
            studentized_resid = influence.resid_studentized_external
        except Exception:
            studentized_resid = influence.resid_studentized_internal
        leverage = influence.hat_matrix_diag

        if p is None:
            p = len(model.params)

        # Cook's D 阈值：4/n（常用经验阈值）
        n_actual = len(clean_df)
        cook_threshold = 4.0 / n_actual
        # 杠杆阈值：2p/n
        leverage_threshold = 2 * p / n_actual

        high_cook = np.where(cooks_d > cook_threshold)[0]
        # 学生化残差异常：|t| > 2
        high_studentized = np.where(np.abs(studentized_resid) > 2)[0]
        high_leverage = np.where(leverage > leverage_threshold)[0]

        high_influence = sorted(set(
            list(high_cook) + list(high_studentized) + list(high_leverage)
        ))

        # 构建诊断表（仅对可能有问题的个案）
        warnings = ""
        if len(high_influence) > 0:
            warnings = (
                f"⚠ 检测到{len(high_influence)}个可能的高影响个案（索引：{high_influence[:10]}"
                f"{'...' if len(high_influence) > 10 else ''}）。"
                f" Cook's D 阈值={cook_threshold:.4f}（4/n），这些个案可能过度影响回归结果，建议逐一检查原始数据和数据录入。"
            )

        # 构建完整诊断表
        diagnostics = pd.DataFrame({
            "观测序号": range(1, n_actual + 1),
            "Cook's D": np.round(cooks_d, 4),
            "学生化删除残差": np.round(studentized_resid, 3),
            "杠杆值": np.round(leverage, 3),
            "高影响点": ["是" if i in high_influence else "否" for i in range(n_actual)],
        })

        return diagnostics, high_influence, warnings

    except Exception:
        return None, [], ""
