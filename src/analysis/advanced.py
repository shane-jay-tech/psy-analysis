"""高级分析：ANCOVA / 中介效应 / 调节效应"""
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass, field
from typing import Optional, List, Callable


@dataclass
class AdvancedResult:
    test_type: str  # "ancova", "mediation", "moderation"
    model_summary: pd.DataFrame
    coef_table: pd.DataFrame
    effect_size: float = 0.0
    effect_size_name: str = ""
    bootstrap_ci: Optional[pd.DataFrame] = None
    simple_slopes: Optional[pd.DataFrame] = None
    std_coef_table: Optional[pd.DataFrame] = None  # 完全标准化系数
    missing_warning: str = ""
    warning: str = ""


def ancova(
    df: pd.DataFrame,
    dv: str,
    iv: str,
    covs: List[str],
) -> AdvancedResult:
    """
    协方差分析（ANCOVA）。
    在控制协变量的影响下，比较分组之间的因变量均值差异。

    参数：
        dv: 因变量
        iv: 自变量（分组变量，分类）
        covs: 协变量列表（连续变量）
    """
    import statsmodels.api as sm
    from statsmodels.formula.api import ols

    cols = [dv, iv] + covs
    clean = df[cols].copy()
    clean[dv] = pd.to_numeric(clean[dv], errors="coerce")
    for c in covs:
        clean[c] = pd.to_numeric(clean[c], errors="coerce")
    clean = clean.dropna()
    clean[iv] = clean[iv].astype(str)

    cov_str = " + ".join(covs)
    formula = f"Q('{dv}') ~ C(Q('{iv}')) + {cov_str}"

    model = ols(formula, data=clean).fit()
    anova_table = sm.stats.anova_lm(model, typ=3)

    rows = []
    for source in anova_table.index:
        row_data = anova_table.loc[source]
        rows.append({
            "来源": source,
            "平方和(SS)": round(float(row_data["sum_sq"]), 3),
            "df": int(row_data["df"]),
            "均方(MS)": round(float(row_data["sum_sq"] / row_data["df"]), 3) if row_data["df"] > 0 else 0,
            "F": round(float(row_data["F"]), 3) if not np.isnan(row_data["F"]) else "-",
            "p": round(float(row_data["PR(>F)"]), 4) if not np.isnan(row_data["PR(>F)"]) else "-",
        })

    ss_resid = model.ssr
    ss_iv = 0
    for source in anova_table.index:
        if source == f"C(Q('{iv}'))":
            ss_iv = anova_table.loc[source, "sum_sq"]
    eta_sq_p = ss_iv / (ss_iv + ss_resid) if (ss_iv + ss_resid) > 0 else 0.0

    # 调整后均值
    adj_means = _adjusted_means(clean, dv, iv, covs)

    return AdvancedResult(
        test_type="ancova",
        model_summary=pd.DataFrame(rows),
        coef_table=adj_means,
        effect_size=round(eta_sq_p, 3),
        effect_size_name="η²p (偏eta²)",
    )


def _adjusted_means(clean, dv, iv, covs):
    """计算调整后均值"""
    import statsmodels.api as sm

    groups = clean[iv].unique()
    rows = []
    for g in groups:
        g_data = clean[clean[iv] == g]
        X = sm.add_constant(g_data[covs])
        y = g_data[dv]
        try:
            model = sm.OLS(y, X).fit()
            X_mean = sm.add_constant(pd.DataFrame([clean[covs].mean()], columns=covs))
            adj_mean = model.predict(X_mean).iloc[0]
        except Exception:
            adj_mean = g_data[dv].mean()

        rows.append({
            "组别": str(g),
            "N": len(g_data),
            "原始均值": round(g_data[dv].mean(), 2),
            "调整后均值": round(adj_mean, 2),
        })
    return pd.DataFrame(rows)


# ===========================================================================
# 中介效应分析（Bootstrap法，仅用偏差校正Bootstrap CI判断）
# ===========================================================================

def mediation_analysis(
    df: pd.DataFrame,
    x: str,
    m,  # str or List[str] — 支持单个或多个并列中介
    y: str,
    n_bootstrap: int = 5000,
    seed: int = 42,
    progress_callback: Optional[Callable] = None,
) -> AdvancedResult:
    """
    中介效应分析（Bias-Corrected Bootstrap）。

    仅用Bootstrap直接检验间接效应a*b的95%偏差校正置信区间，
    不再报告Baron & Kenny逐步法或Sobel Z检验。

    参数：
        x: 自变量
        m: 中介变量（str）或多个并列中介变量（List[str]）
        y: 因变量
        n_bootstrap: Bootstrap次数（默认5000）
        seed: 随机种子
        progress_callback: 进度回调函数 callback(current, total)，若为None则静默运行
    """
    import statsmodels.api as sm

    # 标准化 m 为列表
    if isinstance(m, str):
        mediators = [m]
    else:
        mediators = list(m)

    all_vars = [x] + mediators + [y]
    cols_in_df = [c for c in all_vars if c in df.columns]
    clean = df[cols_in_df].copy()
    for c in cols_in_df:
        clean[c] = pd.to_numeric(clean[c], errors="coerce")

    n_before = len(clean)
    clean = clean.dropna()
    n_after = len(clean)

    missing_warning = ""
    if n_before > n_after:
        pct = (n_before - n_after) / n_before * 100
        missing_warning = (
            f"⚠ 数据存在缺失值：原始{n_before}条记录，列表删除后保留{n_after}条"
            f"（删除{n_before - n_after}条，占{pct:.1f}%）。"
        )

    n = len(clean)
    if n < 30:
        missing_warning += f" 样本量较小（N={n}），Bootstrap结果可能不稳定。"

    # ========== 路径系数估计（OLS） ==========
    # 标准化所有变量
    z_clean = clean.copy()
    for col in [x] + mediators + [y]:
        z_clean[col] = (clean[col] - clean[col].mean()) / clean[col].std()

    # 总效应 c: Y ~ X
    model_c = sm.OLS(z_clean[y], sm.add_constant(z_clean[x])).fit()
    c_total = model_c.params[x]

    # 对每个中介变量：路径a (M_i ~ X), 路径b (Y ~ X + M_1 + ... + M_k)
    path_a = {}
    for i, med in enumerate(mediators):
        model_a = sm.OLS(z_clean[med], sm.add_constant(z_clean[x])).fit()
        path_a[med] = {
            "b": model_a.params[x],
            "se": model_a.bse[x],
            "p": model_a.pvalues[x],
        }

    # 完整模型: Y ~ X + M_1 + ... + M_k
    X_b = sm.add_constant(z_clean[[x] + mediators])
    model_b = sm.OLS(z_clean[y], X_b).fit()

    path_b = {}
    direct_effect = model_b.params[x]
    for med in mediators:
        path_b[med] = {
            "b": model_b.params[med],
            "se": model_b.bse[med],
            "p": model_b.pvalues[med],
        }

    # 间接效应
    indirect_effects = {}
    total_indirect = 0.0
    for med in mediators:
        ie = path_a[med]["b"] * path_b[med]["b"]
        indirect_effects[med] = ie
        total_indirect += ie

    # ========== Bootstrap（偏差校正） ==========
    rng = np.random.default_rng(seed)
    boot_indirect = []  # list of tuples: (total_indirect, indirect_m1, indirect_m2, ...)
    boot_indirect_per_med = {med: [] for med in mediators}

    for b in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        sample = clean.iloc[idx]

        # 标准化bootstrap样本
        z_sample = sample.copy()
        for col in [x] + mediators + [y]:
            z_sample[col] = (sample[col] - sample[col].mean()) / sample[col].std()

        # 路径a
        boot_a = {}
        for med in mediators:
            try:
                ma = sm.OLS(z_sample[med], sm.add_constant(z_sample[x])).fit()
                boot_a[med] = ma.params[x]
            except Exception:
                boot_a[med] = 0.0

        # 路径b
        try:
            mb = sm.OLS(z_sample[y], sm.add_constant(z_sample[[x] + mediators])).fit()
        except Exception:
            continue

        boot_total = 0.0
        for med in mediators:
            b_val = mb.params[med] if med in mb.params.index else 0.0
            ie_val = boot_a.get(med, 0.0) * b_val
            boot_indirect_per_med[med].append(ie_val)
            boot_total += ie_val
        boot_indirect.append(boot_total)

        if progress_callback is not None and (b + 1) % 500 == 0:
            progress_callback(b + 1, n_bootstrap)

    boot_indirect = np.array(boot_indirect)
    for med in mediators:
        boot_indirect_per_med[med] = np.array(boot_indirect_per_med[med])

    # 偏差校正 95% CI
    def bc_ci(boot_array, point_est):
        """Bias-corrected percentile CI"""
        if len(boot_array) == 0:
            return 0.0, 0.0, 0.0
        boot_sorted = np.sort(boot_array)
        # 偏差校正因子 z0
        p_less = np.mean(boot_array < point_est)
        z0 = stats.norm.ppf(max(0.001, min(0.999, p_less)))
        # 校正后的百分位
        z_alpha_2 = stats.norm.ppf(0.025)
        p_lower = stats.norm.cdf(2 * z0 + z_alpha_2)
        p_upper = stats.norm.cdf(2 * z0 - z_alpha_2)
        idx_lower = int(np.clip(p_lower * len(boot_sorted), 0, len(boot_sorted) - 1))
        idx_upper = int(np.clip(p_upper * len(boot_sorted), 0, len(boot_sorted) - 1))
        return boot_sorted[idx_lower], boot_sorted[idx_upper], z0

    total_ci_low, total_ci_high, _ = bc_ci(boot_indirect, total_indirect)

    # 构建系数表（标准化 β）
    coef_rows = []
    # 总效应
    coef_rows.append({
        "路径": "c (总效应 X→Y)",
        "β": round(c_total, 3),
        "SE": round(float(model_c.bse[x]), 3),
        "t": round(float(model_c.tvalues[x]), 3),
        "p": round(float(model_c.pvalues[x]), 4),
    })
    # 直接效应
    coef_rows.append({
        "路径": "c' (直接效应 X→Y)",
        "β": round(direct_effect, 3),
        "SE": round(float(model_b.bse[x]), 3),
        "t": round(float(model_b.tvalues[x]), 3),
        "p": round(float(model_b.pvalues[x]), 4),
    })
    for med in mediators:
        coef_rows.append({
            "路径": f"a (X→{med})",
            "β": round(path_a[med]["b"], 3),
            "SE": round(path_a[med]["se"], 3),
            "t": round(path_a[med]["b"] / path_a[med]["se"], 3) if path_a[med]["se"] > 0 else 0,
            "p": round(path_a[med]["p"], 4),
        })
    for med in mediators:
        coef_rows.append({
            "路径": f"b ({med}→Y)",
            "β": round(path_b[med]["b"], 3),
            "SE": round(path_b[med]["se"], 3),
            "t": round(path_b[med]["b"] / path_b[med]["se"], 3) if path_b[med]["se"] > 0 else 0,
            "p": round(path_b[med]["p"], 4),
        })

    # 间接效应汇总
    for med in mediators:
        ie_val = indirect_effects[med]
        ci_l, ci_h, _ = bc_ci(boot_indirect_per_med[med], ie_val)
        coef_rows.append({
            "路径": f"间接效应 (X→{med}→Y)",
            "β": round(ie_val, 3),
            "SE": "-",
            "t": "-",
            "p": "-",
            "CI95": f"[{round(ci_l, 3)}, {round(ci_h, 3)}]",
        })

    if len(mediators) > 1:
        coef_rows.append({
            "路径": "总间接效应 (Σ a*b)",
            "β": round(total_indirect, 3),
            "SE": "-",
            "t": "-",
            "p": "-",
            "CI95": f"[{round(total_ci_low, 3)}, {round(total_ci_high, 3)}]",
        })

    # Bootstrap CI 表
    ci_rows = []
    for med in mediators:
        ie_val = indirect_effects[med]
        ci_l, ci_h, _ = bc_ci(boot_indirect_per_med[med], ie_val)
        sig = "✅ 显著" if ci_l * ci_h > 0 else "⚠ 不显著"
        ci_rows.append({
            "效应": f"X→{med}→Y",
            "β": round(ie_val, 3),
            "CI下限": round(ci_l, 3),
            "CI上限": round(ci_h, 3),
            "Bootstrap n": n_bootstrap,
            "判断": sig,
        })

    if len(mediators) > 1:
        ci_rows.append({
            "效应": "总间接效应",
            "β": round(total_indirect, 3),
            "CI下限": round(total_ci_low, 3),
            "CI上限": round(total_ci_high, 3),
            "Bootstrap n": n_bootstrap,
            "判断": "✅ 显著" if total_ci_low * total_ci_high > 0 else "⚠ 不显著",
        })
    bootstrap_ci = pd.DataFrame(ci_rows)

    # 模型拟合摘要
    effect_proportion = total_indirect / c_total if c_total != 0 else 0.0
    model_summary = pd.DataFrame([
        {"指标": "R²_M~X", "值": round(model_b.rsquared, 3)},
        {"指标": "总效应 (c)", "值": round(c_total, 3)},
        {"指标": "直接效应 (c')", "值": round(direct_effect, 3)},
        {"指标": "总间接效应", "值": round(total_indirect, 3)},
        {"指标": "中介效应占比", "值": f"{round(effect_proportion * 100, 1)}%"},
        {"指标": "Bootstrap", "值": f"{n_bootstrap}次（偏差校正）"},
    ])

    # 判断
    if total_ci_low * total_ci_high > 0:
        warning = "✅ Bootstrap偏差校正CI不包含0，中介效应显著。"
    else:
        warning = "⚠ Bootstrap偏差校正CI包含0，中介效应不显著。"

    return AdvancedResult(
        test_type="mediation",
        model_summary=model_summary,
        coef_table=pd.DataFrame(coef_rows),
        effect_size=round(effect_proportion, 3),
        effect_size_name="中介效应占比",
        bootstrap_ci=bootstrap_ci,
        missing_warning=missing_warning,
        warning=warning,
    )


# ===========================================================================
# 调节效应分析（交互项检验 + 简单斜率分析）
# ===========================================================================

def moderation_analysis(
    df: pd.DataFrame,
    x: str,
    m: str,
    y: str,
) -> AdvancedResult:
    """
    调节效应分析（交互项检验 + 简单斜率分析）。

    参数：
        x: 自变量
        m: 调节变量
        y: 因变量
    """
    import statsmodels.api as sm

    cols = [x, m, y]
    clean = df[cols].copy()
    for c in cols:
        clean[c] = pd.to_numeric(clean[c], errors="coerce")
    clean = clean.dropna()

    x_mean = clean[x].mean()
    m_mean = clean[m].mean()
    clean["X_c"] = clean[x] - x_mean
    clean["M_c"] = clean[m] - m_mean
    clean["XM"] = clean["X_c"] * clean["M_c"]

    X_mat = sm.add_constant(clean[["X_c", "M_c", "XM"]])
    model = sm.OLS(clean[y], X_mat).fit()

    coef_table = pd.DataFrame([
        {"变量": "截距", "B": round(float(model.params["const"]), 3),
         "SE": round(float(model.bse["const"]), 3),
         "t": round(float(model.tvalues["const"]), 3),
         "p": round(float(model.pvalues["const"]), 4)},
        {"变量": f"{x} (中心化)", "B": round(float(model.params["X_c"]), 3),
         "SE": round(float(model.bse["X_c"]), 3),
         "t": round(float(model.tvalues["X_c"]), 3),
         "p": round(float(model.pvalues["X_c"]), 4)},
        {"变量": f"{m} (中心化)", "B": round(float(model.params["M_c"]), 3),
         "SE": round(float(model.bse["M_c"]), 3),
         "t": round(float(model.tvalues["M_c"]), 3),
         "p": round(float(model.pvalues["M_c"]), 4)},
        {"变量": f"{x} × {m}", "B": round(float(model.params["XM"]), 3),
         "SE": round(float(model.bse["XM"]), 3),
         "t": round(float(model.tvalues["XM"]), 3),
         "p": round(float(model.pvalues["XM"]), 4)},
    ])

    simple_slopes = _simple_slopes(clean, x, m, y, x_mean, m_mean)

    interact_p = float(model.pvalues["XM"])
    # Cohen's f² for the interaction term
    # f² = (R²_with_interaction - R²_without_interaction) / (1 - R²_with_interaction)
    X_no_interact = sm.add_constant(clean[["X_c", "M_c"]])
    model_no_interact = sm.OLS(clean[y], X_no_interact).fit()
    f2_interact = (model.rsquared - model_no_interact.rsquared) / (1 - model.rsquared) if model.rsquared < 1 else 0.0

    warning = ""
    if interact_p < 0.05:
        warning = f"✅ 交互项显著（p={interact_p:.4f}），{m}对{x}→{y}的路径存在调节效应。Cohen's f²={f2_interact:.3f}（交互效应量：0.02小/0.15中/0.35大）。"
    else:
        warning = f"⚠ 交互项不显著（p={interact_p:.4f}），调节效应不成立。"

    model_summary = pd.DataFrame([
        {"指标": "R²", "值": round(model.rsquared, 3)},
        {"指标": "调整R²", "值": round(model.rsquared_adj, 3)},
        {"指标": "F", "值": round(float(model.fvalue), 3)},
        {"指标": "p", "值": round(float(model.f_pvalue), 4)},
        {"指标": "Cohen's f² (交互项)", "值": round(f2_interact, 3)},
    ])

    return AdvancedResult(
        test_type="moderation",
        model_summary=model_summary,
        coef_table=coef_table,
        effect_size=round(model.rsquared, 3),
        effect_size_name="R²",
        simple_slopes=simple_slopes,
        warning=warning,
    )


def _simple_slopes(clean, x_name, m_name, y_name, x_mean, m_mean):
    """简单斜率分析：在调节变量的低(-1SD)和高(+1SD)水平上检验X→Y的简单斜率"""
    import statsmodels.api as sm

    m_sd = clean["M_c"].std()
    levels = {
        "低 (-1SD)": -m_sd,
        "均值": 0,
        "高 (+1SD)": m_sd,
    }

    rows = []
    for label, m_level in levels.items():
        clean_temp = clean.copy()
        clean_temp["M_shifted"] = clean_temp["M_c"] - m_level
        clean_temp["XM_shifted"] = clean_temp["X_c"] * clean_temp["M_shifted"]
        X_s = sm.add_constant(clean_temp[["X_c", "M_shifted", "XM_shifted"]])
        model_s = sm.OLS(clean_temp[y_name], X_s).fit()

        b_x = float(model_s.params["X_c"])
        se_x = float(model_s.bse["X_c"])
        t_x = b_x / se_x if se_x > 0 else 0
        p_x = 2 * stats.t.sf(abs(t_x), len(clean_temp) - 4)

        rows.append({
            f"{m_name}的水平": label,
            f"{m_name}实际值": round(m_mean + m_level, 2),
            "简单斜率": round(b_x, 3),
            "SE": round(se_x, 3),
            "t": round(t_x, 3),
            "p": round(p_x, 4),
        })

    return pd.DataFrame(rows)
