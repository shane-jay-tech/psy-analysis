"""Logistic 回归：二元 / 有序 / 多项（心理学因变量为分类变量时使用）"""
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class LogisticResult:
    test_type: str  # "binary", "ordinal", "multinomial"
    model_summary: pd.DataFrame
    coef_table: pd.DataFrame
    classification_table: Optional[pd.DataFrame] = None
    accuracy: float = 0.0
    pseudo_r2: Dict[str, float] = field(default_factory=dict)
    odds_ratios: Optional[pd.DataFrame] = None
    hosmer_lemeshow: Optional[Dict[str, float]] = None
    n_obs: int = 0
    n_events: int = 0
    categories: List[str] = field(default_factory=list)
    warning: str = ""


def binary_logistic(
    df: pd.DataFrame,
    dv: str,
    ivs: List[str],
    reference: Optional[str] = None,
) -> LogisticResult:
    """
    二元 Logistic 回归。

    参数：
        df: 数据框
        dv: 因变量（二分类：0/1 或两个类别）
        ivs: 自变量列表（连续或二分类）
        reference: 参照类别（默认取频率最高的为 0）
    """
    import statsmodels.api as sm

    cols = [dv] + ivs
    clean = df[cols].copy()

    for iv in ivs:
        clean[iv] = pd.to_numeric(clean[iv], errors="coerce")
    clean = clean.dropna()

    y = clean[dv].copy()
    unique_vals = sorted(y.unique())

    if len(unique_vals) != 2:
        raise ValueError(
            f"二元 Logistic 回归要求因变量恰好有 2 个类别，"
            f"当前「{dv}」有 {len(unique_vals)} 个类别：{unique_vals}"
        )

    if not pd.api.types.is_numeric_dtype(y) or set(unique_vals) != {0, 1}:
        if reference is not None:
            ref_val = reference
        else:
            ref_val = y.value_counts().idxmax()
        y = (y != ref_val).astype(int)
        unique_vals = [0, 1]

    X = sm.add_constant(clean[ivs].astype(float))
    model = sm.Logit(y, X).fit(disp=0, maxiter=100)

    if not model.mle_retvals.get("converged", True):
        raise ValueError("模型未收敛，可能存在完美分离或样本量不足。建议检查因变量与自变量的关系。")

    n_obs = len(clean)
    n_events = int(y.sum())

    coef_rows = []
    for var_name in ["const"] + ivs:
        display_name = "常量" if var_name == "const" else var_name
        b = float(model.params.get(var_name, 0))
        se = float(model.bse.get(var_name, 0))
        z = float(model.tvalues.get(var_name, 0))
        p = float(model.pvalues.get(var_name, 0))
        or_val = np.exp(b)
        ci_lo = np.exp(b - 1.96 * se)
        ci_hi = np.exp(b + 1.96 * se)
        coef_rows.append({
            "变量": display_name,
            "B": round(b, 3),
            "SE": round(se, 3),
            "Wald χ²": round(z ** 2, 3),
            "p": round(p, 4),
            "OR": round(or_val, 3),
            "OR 95%CI": f"[{ci_lo:.3f}, {ci_hi:.3f}]",
        })

    coef_table = pd.DataFrame(coef_rows)

    odds_ratios = pd.DataFrame([
        {"变量": r["变量"], "OR": r["OR"], "95% CI": r["OR 95%CI"]}
        for r in coef_rows if r["变量"] != "常量"
    ])

    y_pred = (model.predict(X) >= 0.5).astype(int)
    correct = (y_pred == y).sum()
    accuracy = correct / n_obs

    ct = pd.crosstab(y, y_pred, rownames=["实际"], colnames=["预测"])
    classification_table = ct

    pseudo_r2 = {
        "McFadden R²": round(float(model.prsquared), 4),
        "Cox-Snell R²": round(_cox_snell_r2(model, n_obs), 4),
        "Nagelkerke R²": round(_nagelkerke_r2(model, n_obs), 4),
    }

    hl = _hosmer_lemeshow(y.values, model.predict(X).values)

    model_chi2 = float(model.llr)
    model_p = float(model.llr_pvalue)
    model_df = int(model.df_model)

    model_summary = pd.DataFrame({
        "指标": [
            "观测数", "事件数", "模型 χ²", "df", "p",
            "McFadden R²", "Cox-Snell R²", "Nagelkerke R²",
            "分类准确率",
        ],
        "值": [
            n_obs, n_events,
            round(model_chi2, 3), model_df, round(model_p, 4),
            pseudo_r2["McFadden R²"],
            pseudo_r2["Cox-Snell R²"],
            pseudo_r2["Nagelkerke R²"],
            f"{accuracy * 100:.1f}%",
        ],
    })

    warning = ""
    max_coef = max(abs(float(v)) for v in model.params.values)
    if max_coef > 20:
        warning += "⚠ 存在极大系数（可能完美分离），OR 和置信区间可能不可靠。建议检查数据或使用 Firth 校正。"
    if n_events < 10 * len(ivs):
        warning += (
            f"⚠ 事件数（{n_events}）相对于自变量数（{len(ivs)}）偏少，"
            f"建议至少 EPV≥10（即事件数 ≥ {10 * len(ivs)}）。"
        )

    return LogisticResult(
        test_type="binary",
        model_summary=model_summary,
        coef_table=coef_table,
        classification_table=classification_table,
        accuracy=round(accuracy, 4),
        pseudo_r2=pseudo_r2,
        odds_ratios=odds_ratios,
        hosmer_lemeshow=hl,
        n_obs=n_obs,
        n_events=n_events,
        categories=[str(v) for v in unique_vals],
        warning=warning,
    )


def ordinal_logistic(
    df: pd.DataFrame,
    dv: str,
    ivs: List[str],
) -> LogisticResult:
    """
    有序 Logistic 回归（累积 Logit 模型 / 比例优势模型）。

    因变量有自然排序（如：低/中/高，轻度/中度/重度）。
    """
    from statsmodels.miscmodels.ordinal_model import OrderedModel

    cols = [dv] + ivs
    clean = df[cols].copy()
    for iv in ivs:
        clean[iv] = pd.to_numeric(clean[iv], errors="coerce")
    clean = clean.dropna()

    y = clean[dv].copy()
    unique_vals = sorted(y.unique())

    if len(unique_vals) < 3:
        raise ValueError(
            f"有序 Logistic 回归要求因变量至少 3 个有序类别，"
            f"当前「{dv}」只有 {len(unique_vals)} 个类别。如为二分类，请用二元 Logistic。"
        )

    if not pd.api.types.is_numeric_dtype(y):
        cat_type = pd.CategoricalDtype(categories=unique_vals, ordered=True)
        y = y.astype(cat_type)
    else:
        cat_type = pd.CategoricalDtype(categories=unique_vals, ordered=True)
        y = y.astype(cat_type)

    clean[dv] = y
    n_obs = len(clean)

    X = clean[ivs].astype(float)
    model = OrderedModel(clean[dv], X, distr="logit").fit(method="bfgs", disp=0)

    coef_rows = []
    for var_name in ivs:
        b = float(model.params.get(var_name, 0))
        se = float(model.bse.get(var_name, 0))
        z = b / se if se > 0 else 0
        p = float(2 * (1 - stats.norm.cdf(abs(z))))
        or_val = np.exp(b)
        ci_lo = np.exp(b - 1.96 * se)
        ci_hi = np.exp(b + 1.96 * se)
        coef_rows.append({
            "变量": var_name,
            "B": round(b, 3),
            "SE": round(se, 3),
            "Wald χ²": round(z ** 2, 3),
            "p": round(p, 4),
            "OR": round(or_val, 3),
            "OR 95%CI": f"[{ci_lo:.3f}, {ci_hi:.3f}]",
        })

    threshold_names = [k for k in model.params.index if k not in ivs]
    for thr in threshold_names:
        b = float(model.params[thr])
        se = float(model.bse[thr])
        coef_rows.append({
            "变量": f"阈值: {thr}",
            "B": round(b, 3),
            "SE": round(se, 3),
            "Wald χ²": round((b / se) ** 2 if se > 0 else 0, 3),
            "p": round(float(2 * (1 - stats.norm.cdf(abs(b / se)))) if se > 0 else 1.0, 4),
            "OR": "-",
            "OR 95%CI": "-",
        })

    coef_table = pd.DataFrame(coef_rows)

    odds_ratios = pd.DataFrame([
        {"变量": r["变量"], "OR": r["OR"], "95% CI": r["OR 95%CI"]}
        for r in coef_rows if not str(r["变量"]).startswith("阈值")
    ])

    pseudo_r2 = {
        "McFadden R²": round(float(1 - model.llf / model.llnull), 4),
    }

    model_chi2 = float(-2 * (model.llnull - model.llf))
    model_df = len(ivs)
    model_p = float(1 - stats.chi2.cdf(model_chi2, model_df))

    model_summary = pd.DataFrame({
        "指标": [
            "观测数", "类别数", "模型 χ²", "df", "p",
            "McFadden R²",
        ],
        "值": [
            n_obs, len(unique_vals),
            round(model_chi2, 3), model_df, round(model_p, 4),
            pseudo_r2["McFadden R²"],
        ],
    })

    warning = ""
    min_cat_n = min(y.value_counts())
    if min_cat_n < 10 * len(ivs):
        warning = f"⚠ 最小类别样本量（{min_cat_n}）偏少，结果可能不稳定。"

    return LogisticResult(
        test_type="ordinal",
        model_summary=model_summary,
        coef_table=coef_table,
        accuracy=0.0,
        pseudo_r2=pseudo_r2,
        odds_ratios=odds_ratios,
        n_obs=n_obs,
        categories=[str(v) for v in unique_vals],
        warning=warning,
    )


def multinomial_logistic(
    df: pd.DataFrame,
    dv: str,
    ivs: List[str],
    reference: Optional[str] = None,
) -> LogisticResult:
    """
    多项 Logistic 回归。

    因变量为无序多分类（如：选 A/B/C 治疗方案，职业类型）。
    """
    import statsmodels.api as sm

    cols = [dv] + ivs
    clean = df[cols].copy()
    for iv in ivs:
        clean[iv] = pd.to_numeric(clean[iv], errors="coerce")
    clean = clean.dropna()

    y = clean[dv].copy()
    unique_vals = sorted(y.unique())

    if len(unique_vals) < 3:
        raise ValueError(
            f"多项 Logistic 回归要求因变量至少 3 个类别，"
            f"当前「{dv}」只有 {len(unique_vals)} 个。如为二分类，请用二元 Logistic。"
        )

    if reference is None:
        reference = str(y.value_counts().idxmax())

    y_dummies = pd.get_dummies(y, prefix="", prefix_sep="")
    ref_col = str(reference)
    if ref_col in y_dummies.columns:
        other_cols = [c for c in y_dummies.columns if c != ref_col]
    else:
        other_cols = list(y_dummies.columns[1:])
        ref_col = str(y_dummies.columns[0])

    X = sm.add_constant(clean[ivs].astype(float))
    n_obs = len(clean)

    model = sm.MNLogit(y.astype(str), X).fit(disp=0, maxiter=100)

    coef_rows = []
    for i, cat in enumerate(model.model.J_label[1:] if hasattr(model.model, 'J_label') else range(model.model.J - 1)):
        cat_label = str(cat) if hasattr(model.model, 'J_label') else f"类别{i+1}"
        params_i = model.params.iloc[:, i] if model.params.ndim > 1 else model.params
        bse_i = model.bse.iloc[:, i] if model.bse.ndim > 1 else model.bse
        pvalues_i = model.pvalues.iloc[:, i] if model.pvalues.ndim > 1 else model.pvalues

        for var_name in ["const"] + ivs:
            display_name = "常量" if var_name == "const" else var_name
            b = float(params_i.get(var_name, 0))
            se = float(bse_i.get(var_name, 0))
            p = float(pvalues_i.get(var_name, 1))
            or_val = np.exp(b)
            coef_rows.append({
                "对比": f"{cat_label} vs {ref_col}",
                "变量": display_name,
                "B": round(b, 3),
                "SE": round(se, 3),
                "Wald χ²": round((b / se) ** 2 if se > 0 else 0, 3),
                "p": round(p, 4),
                "OR": round(or_val, 3),
            })

    coef_table = pd.DataFrame(coef_rows)

    pseudo_r2 = {
        "McFadden R²": round(float(model.prsquared), 4),
    }

    model_chi2 = float(model.llr)
    model_p = float(model.llr_pvalue)
    model_df = int(model.df_model)

    model_summary = pd.DataFrame({
        "指标": [
            "观测数", "类别数", "参照类别",
            "模型 χ²", "df", "p", "McFadden R²",
        ],
        "值": [
            n_obs, len(unique_vals), ref_col,
            round(model_chi2, 3), model_df, round(model_p, 4),
            pseudo_r2["McFadden R²"],
        ],
    })

    return LogisticResult(
        test_type="multinomial",
        model_summary=model_summary,
        coef_table=coef_table,
        pseudo_r2=pseudo_r2,
        n_obs=n_obs,
        categories=[str(v) for v in unique_vals],
        warning="",
    )


# ===========================================================================
# 辅助函数
# ===========================================================================

def _cox_snell_r2(model, n: int) -> float:
    """Cox-Snell 伪 R²"""
    return 1 - np.exp((2 / n) * (model.llnull - model.llf))


def _nagelkerke_r2(model, n: int) -> float:
    """Nagelkerke 伪 R²（Cox-Snell 的修正版，上界为 1）"""
    cs = _cox_snell_r2(model, n)
    max_cs = 1 - np.exp((2 / n) * model.llnull)
    return cs / max_cs if max_cs > 0 else 0.0


def _hosmer_lemeshow(y_true: np.ndarray, y_pred_prob: np.ndarray, g: int = 10) -> Dict[str, float]:
    """
    Hosmer-Lemeshow 拟合优度检验。

    将预测概率分成 g 组，比较观测频率与期望频率。
    p > 0.05 表明模型拟合良好。
    """
    n = len(y_true)
    if n < g * 5:
        return {"chi2": np.nan, "df": np.nan, "p": np.nan}

    order = np.argsort(y_pred_prob)
    y_sorted = y_true[order]
    p_sorted = y_pred_prob[order]

    groups = np.array_split(np.arange(n), g)

    chi2 = 0.0
    for group_idx in groups:
        if len(group_idx) == 0:
            continue
        obs_1 = y_sorted[group_idx].sum()
        obs_0 = len(group_idx) - obs_1
        exp_1 = p_sorted[group_idx].sum()
        exp_0 = len(group_idx) - exp_1

        if exp_1 > 0:
            chi2 += (obs_1 - exp_1) ** 2 / exp_1
        if exp_0 > 0:
            chi2 += (obs_0 - exp_0) ** 2 / exp_0

    df = g - 2
    p_val = 1 - stats.chi2.cdf(chi2, df)

    return {
        "chi2": round(chi2, 3),
        "df": df,
        "p": round(p_val, 4),
    }
