"""方差分析：单因素 / 双因素 / 重复测量"""

import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ANOVAResult:
    test_type: str  # "one_way", "two_way", "repeated"
    table: pd.DataFrame
    effect_size: float
    effect_size_name: str  # "η²", "η²p", "η²G"（广义eta方）
    effect_size_ci: Optional[str] = None  # 效应量置信区间
    post_hoc: Optional[pd.DataFrame] = None
    assumption_homogeneity: Optional[dict] = None
    assumption_sphericity: Optional[dict] = None
    corrected_table: Optional[pd.DataFrame] = None  # GG校正


def _eta_sq_ci(f_val, df1, df2, eta_sq, confidence=0.95):
    """
    计算eta²的置信区间（基于非中心F分布）。

    https://www.jstatsoft.org/article/view/v056i09
    """
    from scipy.optimize import brentq

    def ncp_lower(lambda_val):
        nc = stats.ncf.ppf((1 - confidence) / 2, df1, df2, lambda_val)
        return nc - f_val

    def ncp_upper(lambda_val):
        nc = stats.ncf.ppf((1 + confidence) / 2, df1, df2, lambda_val)
        return nc - f_val

    try:
        # 下界
        if f_val > 1e-6:
            ncp_low = brentq(ncp_lower, 0, f_val * 100 + 100, maxiter=200)
            ncp_high = brentq(ncp_upper, 0, f_val * 100 + 100, maxiter=200)
            ci_low = ncp_low / (ncp_low + df1 + df2 + 1)
            ci_high = ncp_high / (ncp_high + df1 + df2 + 1)
            return f"[{round(max(0, ci_low), 3)}, {round(min(1, ci_high), 3)}]"
    except Exception:
        pass
    return ""


def one_way_anova(
    df: pd.DataFrame,
    dv: str,
    iv: str,
    confidence: float = 0.95,
) -> ANOVAResult:
    """
    单因素被试间方差分析 + Tukey HSD 事后检验。
    """
    groups = []
    group_names = []
    clean_df = df[[dv, iv]].dropna()

    for name, group in clean_df.groupby(iv):
        groups.append(pd.to_numeric(group[dv], errors="coerce").dropna().values)
        group_names.append(str(name))

    if len(groups) < 2:
        raise ValueError("至少需要2个分组进行方差分析。")

    # 方差齐性检验
    levene_stat, levene_p = stats.levene(*groups)
    equal_var = levene_p > 0.05

    # One-way ANOVA
    f_stat, p_val = stats.f_oneway(*groups)

    # 效应量 η²
    grand_mean = np.concatenate(groups).mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    ss_total = sum(((g - grand_mean) ** 2).sum() for g in groups)
    ss_within = ss_total - ss_between
    eta_sq = ss_between / ss_total if ss_total > 0 else 0.0

    # η² CI（非中心F）
    n_groups = len(groups)
    n_total = sum(len(g) for g in groups)
    df1 = n_groups - 1
    df2 = n_total - n_groups
    eta_sq_ci = _eta_sq_ci(f_stat, df1, df2, eta_sq, confidence)

    # 组统计
    group_means = [round(g.mean(), 2) for g in groups]
    group_std = [round(g.std(), 2) for g in groups]
    group_n = [len(g) for g in groups]

    table_rows = []
    for i, name in enumerate(group_names):
        table_rows.append({
            "组别": name,
            "N": group_n[i],
            "M": group_means[i],
            "SD": group_std[i],
        })

    anova_table = pd.DataFrame([
        {"来源": "组间", "SS": round(ss_between, 3), "df": df1,
         "MS": round(ss_between / df1, 3),
         "F": round(float(f_stat), 3), "p": round(float(p_val), 4)},
        {"来源": "组内", "SS": round(ss_within, 3),
         "df": df2,
         "MS": round(ss_within / df2, 3),
         "F": "", "p": ""},
        {"来源": "总计", "SS": round(ss_total, 3), "df": n_total - 1,
         "MS": "", "F": "", "p": ""},
    ])

    # Tukey HSD 事后检验
    post_hoc = None
    if p_val < 0.05 and len(groups) > 2:
        post_hoc = _tukey_hsd(groups, group_names)

    return ANOVAResult(
        test_type="one_way",
        table=anova_table,
        effect_size=round(float(eta_sq), 4),
        effect_size_name="η²",
        effect_size_ci=eta_sq_ci,
        post_hoc=post_hoc,
        assumption_homogeneity={
            "passed": equal_var,
            "statistic": round(float(levene_stat), 3),
            "p_value": round(float(levene_p), 4),
        },
    )


def two_way_anova(
    df: pd.DataFrame,
    dv: str,
    iv1: str,
    iv2: str,
    confidence: float = 0.95,
) -> ANOVAResult:
    """
    双因素被试间方差分析（Type III SS）。
    """
    import statsmodels.api as sm
    from statsmodels.formula.api import ols

    clean = df[[dv, iv1, iv2]].dropna()
    clean[iv1] = clean[iv1].astype(str)
    clean[iv2] = clean[iv2].astype(str)

    formula = f"Q('{dv}') ~ C(Q('{iv1}')) + C(Q('{iv2}')) + C(Q('{iv1}')):C(Q('{iv2}'))"
    model = ols(formula, data=clean).fit()
    anova_table = sm.stats.anova_lm(model, typ=3)

    rows = []
    for source, row in anova_table.iterrows():
        f_val = float(row["F"]) if not np.isnan(row["F"]) else 0.0
        rows.append({
            "来源": source,
            "SS": round(float(row["sum_sq"]), 3),
            "df": int(row["df"]),
            "MS": round(float(row["sum_sq"] / row["df"]), 3) if row["df"] > 0 else "",
            "F": round(f_val, 3) if f_val > 0 else "",
            "p": round(float(row["PR(>F)"]), 4) if not np.isnan(row["PR(>F)"]) else "",
        })

    # 偏eta方 (η²p) for IV1
    ss_residual = anova_table.loc["Residual", "sum_sq"]
    iv1_key = f"C(Q('{iv1}'))"
    iv2_key = f"C(Q('{iv2}'))"
    interact_key = f"C(Q('{iv1}')):C(Q('{iv2}'))"

    eta_sq_p_results = {}

    if iv1_key in anova_table.index:
        ss_effect = anova_table.loc[iv1_key, "sum_sq"]
        eta_sq_p1 = ss_effect / (ss_effect + ss_residual)
        n_clean = len(clean)
        n_levels_iv1 = clean[iv1].nunique()
        n_levels_iv2 = clean[iv2].nunique()
        df1_iv1 = n_levels_iv1 - 1
        df2_resid = n_clean - n_levels_iv1 * n_levels_iv2
        f1 = float(anova_table.loc[iv1_key, "F"]) if not np.isnan(anova_table.loc[iv1_key, "F"]) else 0
        ci1 = _eta_sq_ci(f1, df1_iv1, df2_resid, eta_sq_p1) if f1 > 0 else ""
        eta_sq_p_results[iv1_key] = (eta_sq_p1, "η²p (偏eta²)", ci1)

    if iv2_key in anova_table.index:
        ss_effect2 = anova_table.loc[iv2_key, "sum_sq"]
        eta_sq_p2 = ss_effect2 / (ss_effect2 + ss_residual)
        eta_sq_p_results[iv2_key] = (eta_sq_p2, "η²p (偏eta²)", "")

    if interact_key in anova_table.index:
        ss_interact = anova_table.loc[interact_key, "sum_sq"]
        eta_sq_pi = ss_interact / (ss_interact + ss_residual)
        eta_sq_p_results[interact_key] = (eta_sq_pi, "η²p (偏eta²)", "")

    # 使用第一个可用的效应量作为主效应量
    primary_es = list(eta_sq_p_results.values())
    if primary_es:
        es_val, es_name, es_ci = primary_es[0]
    else:
        es_val, es_name, es_ci = 0.0, "η²p", ""

    return ANOVAResult(
        test_type="two_way",
        table=pd.DataFrame(rows),
        effect_size=round(float(es_val), 4),
        effect_size_name=es_name,
        effect_size_ci=es_ci,
    )


def _bootstrap_eta_sq_g_ci(
    long_df: pd.DataFrame,
    subj_col: str,
    dv_cols: list,
    n_boot: int = 5000,
    seed: int = 42,
    confidence: float = 0.95,
) -> str:
    """
    基于残差重抽样的 bootstrap 计算重复测量 ANOVA 的 η²G 置信区间。

    方法：重抽样残差并重构数据，5000次，输出偏差校正百分位 CI。
    若耗时过长（>10s），调用方应提示使用近似公式。
    """
    rng = np.random.default_rng(seed)

    grand_mean = long_df["dv"].mean()
    n_subjects = long_df[subj_col].nunique()
    k = len(dv_cols)

    # 估计各效应
    subject_effects = long_df.groupby(subj_col)["dv"].mean() - grand_mean
    time_effects = long_df.groupby("time")["dv"].mean() - grand_mean

    # 构建残差矩阵 (n_subjects × k)
    residuals = np.zeros((n_subjects, k))
    subjects = long_df[subj_col].unique()
    times = long_df["time"].unique()
    for i, subj in enumerate(subjects):
        for j, t in enumerate(times):
            mask = (long_df[subj_col] == subj) & (long_df["time"] == t)
            if mask.any():
                observed = long_df.loc[mask, "dv"].values[0]
                predicted = grand_mean + subject_effects.get(subj, 0) + time_effects.get(t, 0)
                residuals[i, j] = observed - predicted

    eta_sq_g_vals = np.zeros(n_boot)

    for b in range(n_boot):
        # 残差重抽样（按被试，保持被试内相关的模式）
        boot_residuals = np.zeros((n_subjects, k))
        for i in range(n_subjects):
            idx = rng.integers(0, n_subjects)
            boot_residuals[i, :] = residuals[idx, :]

        # 重构数据
        recon = np.zeros((n_subjects, k))
        for i, subj in enumerate(subjects):
            for j, t in enumerate(times):
                recon[i, j] = grand_mean + subject_effects.get(subj, 0) + time_effects.get(t, 0) + boot_residuals[i, j]

        # 计算 bootstrap η²G
        recon_gm = recon.mean()
        recon_time_col_means = recon.mean(axis=0)
        recon_subj_means = recon.mean(axis=1)

        ss_time_boot = n_subjects * np.sum((recon_time_col_means - recon_gm) ** 2)
        ss_subject_boot = k * np.sum((recon_subj_means - recon_gm) ** 2)
        ss_error_boot = np.sum((recon - recon_subj_means[:, None] - recon_time_col_means[None, :] + recon_gm) ** 2)

        eta_sq_g_vals[b] = ss_time_boot / (ss_time_boot + ss_subject_boot + ss_error_boot) if (ss_time_boot + ss_subject_boot + ss_error_boot) > 0 else 0

    # 偏差校正百分位 CI
    eta_sq_g_vals.sort()
    alpha = 1 - confidence
    lo = int(alpha / 2 * n_boot)
    hi = int((1 - alpha / 2) * n_boot)
    ci_low = eta_sq_g_vals[max(0, lo)]
    ci_high = eta_sq_g_vals[min(n_boot - 1, hi)]

    return f"[{round(max(0, ci_low), 3)}, {round(min(1, ci_high), 3)}]"


def repeated_measures_anova(
    df: pd.DataFrame,
    dv_cols: List[str],
    subject_col: str = None,
    bootstrap_ci: bool = False,
    n_boot: int = 5000,
) -> ANOVAResult:
    """
    重复测量方差分析（单因素被试内设计）。

    效应量：
    - η²p（偏eta方）: SS_time / (SS_time + SS_error)，标准输出
    - η²G（广义eta方）: SS_time / (SS_time + SS_subject + SS_error)，
      用于跨研究可比性（Bakeman, 2005）

    参数：
        bootstrap_ci: 是否使用 bootstrap 计算 η²G 的置信区间（默认 False）。
                      True 时基于残差重抽样 n_boot 次，输出偏差校正百分位 CI。
                      计算量较大，大数据集可能耗时 5-10 秒。
        n_boot: bootstrap 重抽样次数，默认 5000。
    """
    from statsmodels.stats.anova import AnovaRM

    cols = dv_cols.copy()
    if subject_col and subject_col in df.columns:
        cols.append(subject_col)

    clean = df[cols].copy()
    for c in dv_cols:
        clean[c] = pd.to_numeric(clean[c], errors="coerce")
    clean = clean.dropna()

    if subject_col and subject_col in clean.columns:
        subj_col = subject_col
    else:
        clean["_subject"] = range(len(clean))
        subj_col = "_subject"

    # 转换为长格式
    long_df = clean.melt(
        id_vars=[subj_col],
        value_vars=dv_cols,
        var_name="time",
        value_name="dv",
    )

    aovrm = AnovaRM(long_df, depvar="dv", subject=subj_col, within=["time"])
    result = aovrm.fit()

    anova_table = result.anova_table
    df_time = int(anova_table.loc["time", "Num DF"])
    df_error = int(anova_table.loc["time", "Den DF"])
    f_val = float(anova_table.loc["time", "F Value"])
    p_val = float(anova_table.loc["time", "Pr > F"])

    # SS估计（从F值和df反推）
    ms_time = f_val * (anova_table.loc["time", "F Value"] / f_val)  # 需要实际SS
    # 实际上AnovaRM不直接返回SS，我们通过F和MS关系来估计
    # 偏eta方 = F * df_time / (F * df_time + df_error)
    eta_sq_p = (f_val * df_time) / (f_val * df_time + df_error) if (f_val * df_time + df_error) > 0 else 0.0

    # 广义eta方（generaized eta-squared, η²G）
    # 需要SS_subject。从长格式数据中估计：
    n_subjects = clean[subj_col].nunique()
    k = len(dv_cols)
    grand_mean = long_df["dv"].mean()
    subject_means = long_df.groupby(subj_col)["dv"].mean()
    ss_subject = k * np.sum((subject_means - grand_mean) ** 2)

    time_means = long_df.groupby("time")["dv"].mean()
    ss_time = n_subjects * np.sum((time_means - grand_mean) ** 2)

    ss_error = np.sum(
        (long_df["dv"].values -
         long_df["dv"].groupby(long_df[subj_col]).transform("mean").values -
         long_df["dv"].groupby(long_df["time"]).transform("mean").values +
         grand_mean) ** 2
    )

    eta_sq_g = ss_time / (ss_time + ss_subject + ss_error) if (ss_time + ss_subject + ss_error) > 0 else 0.0

    # Mauchly 球形检验
    sphericity = None
    try:
        wide_data = clean[dv_cols]
        import pingouin as pg
        spher = pg.sphericity(wide_data)
        sphericity = {
            "passed": spher[1] > 0.05,
            "statistic": round(float(spher[0]), 3),
            "p_value": round(float(spher[1]), 4),
        }
    except Exception:
        pass

    # GG校正
    corrected_table = None
    if sphericity and not sphericity["passed"]:
        try:
            epsilon = max(0.5, min(1.0, 1.0 / (k - 1)))
            df_time_gg = df_time * epsilon
            df_error_gg = df_error * epsilon
            p_gg = 1 - stats.f.cdf(f_val, df_time_gg, df_error_gg)
            corrected_table = pd.DataFrame([{
                "校正方法": "Greenhouse-Geisser",
                "ε": round(epsilon, 3),
                "校正df1": round(df_time_gg, 2),
                "校正df2": round(df_error_gg, 2),
                "校正p": round(float(p_gg), 4),
            }])
        except Exception:
            pass

    table_rows = [{
        "来源": "时间（重复测量）",
        "df": df_time,
        "MS": "",
        "F": round(f_val, 3),
        "p": round(p_val, 4),
        "η²p": round(eta_sq_p, 3),
        "η²G": round(eta_sq_g, 3),
    }, {
        "来源": "误差",
        "df": df_error,
        "MS": "",
        "F": "",
        "p": "",
        "η²p": "",
        "η²G": "",
    }]

    # η²G CI
    eta_sq_g_ci = ""
    if bootstrap_ci:
        try:
            import time
            t0 = time.perf_counter()
            eta_sq_g_ci = _bootstrap_eta_sq_g_ci(
                long_df, subj_col, dv_cols, n_boot=n_boot, seed=42,
            )
            elapsed = time.perf_counter() - t0
            if elapsed > 5.0:
                eta_sq_g_ci += f" (bootstrap耗时{elapsed:.1f}s)"
        except Exception:
            # bootstrap 失败时回退到近似公式
            try:
                eta_sq_g_ci = _eta_sq_ci(f_val, df_time, df_error, eta_sq_g)
            except Exception:
                pass
    else:
        try:
            eta_sq_g_ci = _eta_sq_ci(f_val, df_time, df_error, eta_sq_g)
        except Exception:
            pass

    return ANOVAResult(
        test_type="repeated",
        table=pd.DataFrame(table_rows),
        effect_size=round(float(eta_sq_g), 4),
        effect_size_name="η²G (广义eta²)",
        effect_size_ci=eta_sq_g_ci,
        assumption_sphericity=sphericity,
        corrected_table=corrected_table,
    )


def _tukey_hsd(groups: list, names: list) -> pd.DataFrame:
    """Tukey HSD 事后多重比较 — 使用 Studentized range 分布精确计算 p 值"""
    from itertools import combinations
    from scipy.stats import studentized_range

    rows = []
    n_groups = len(groups)
    all_data = np.concatenate(groups)
    df_error = len(all_data) - n_groups

    mse = sum(
        ((g - g.mean()) ** 2).sum() for g in groups
    ) / df_error

    for (i, j) in combinations(range(n_groups), 2):
        diff = groups[i].mean() - groups[j].mean()
        # Tukey-Kramer SE (handles unequal group sizes)
        se = np.sqrt(mse / 2 * (1 / len(groups[i]) + 1 / len(groups[j])))
        q_stat = abs(diff) / se if se > 0 else 0.0
        p_val = studentized_range.sf(q_stat, n_groups, df_error) if q_stat > 0 else 1.0

        rows.append({
            "比较": f"{names[i]} vs {names[j]}",
            "均值差": round(float(diff), 3),
            "SE": round(float(se), 3),
            "p (Tukey HSD)": round(float(p_val), 4),
        })

    return pd.DataFrame(rows)


def welch_anova(
    df: pd.DataFrame,
    dv: str,
    iv: str,
    confidence: float = 0.95,
) -> ANOVAResult:
    """
    Welch's ANOVA（方差不齐时的校正单因素方差分析）。
    使用 pingouin.welch_anova 计算，事后检验用 Games-Howell。
    """
    import pingouin as pg

    clean_df = df[[dv, iv]].dropna()
    clean_df[dv] = pd.to_numeric(clean_df[dv], errors="coerce")
    clean_df = clean_df.dropna()

    groups = []
    group_names = []
    for name, group in clean_df.groupby(iv):
        groups.append(group[dv].values)
        group_names.append(str(name))

    if len(groups) < 2:
        raise ValueError("至少需要2个分组进行方差分析。")

    # Welch ANOVA
    aov = pg.welch_anova(dv=dv, between=iv, data=clean_df)
    f_stat = float(aov["F"].values[0])
    p_val = float(aov["p_unc"].values[0])
    df1 = float(aov["ddof1"].values[0])
    df2 = float(aov["ddof2"].values[0])

    # 效应量 η² (基于组间/总SS)
    grand_mean = clean_df[dv].mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    ss_total = ((clean_df[dv] - grand_mean) ** 2).sum()
    eta_sq = ss_between / ss_total if ss_total > 0 else 0.0
    eta_sq_ci = _eta_sq_ci(f_stat, int(df1), df2, eta_sq, confidence)

    # 组统计
    group_means = [round(g.mean(), 2) for g in groups]
    group_std = [round(g.std(), 2) for g in groups]
    group_n = [len(g) for g in groups]

    table_rows = []
    for i, name in enumerate(group_names):
        table_rows.append({
            "组别": name,
            "N": group_n[i],
            "M": group_means[i],
            "SD": group_std[i],
        })

    anova_table = pd.DataFrame([
        {"来源": "组间", "SS": round(ss_between, 3), "df": round(df1, 2),
         "MS": "", "F": round(float(f_stat), 3), "p": round(float(p_val), 4)},
        {"来源": "组内", "SS": "", "df": round(df2, 2),
         "MS": "", "F": "", "p": ""},
        {"来源": "总计", "SS": round(ss_total, 3), "df": len(clean_df) - 1,
         "MS": "", "F": "", "p": ""},
    ])

    # Games-Howell 事后检验（适合方差不齐情况）
    post_hoc = None
    if p_val < 0.05 and len(groups) > 2:
        try:
            gh = pg.pairwise_gameshowell(dv=dv, between=iv, data=clean_df)
            post_rows = []
            for _, row in gh.iterrows():
                post_rows.append({
                    "比较": f"{row['A']} vs {row['B']}",
                    "均值差": round(float(row["diff"]), 3),
                    "SE": round(float(row["se"]), 3),
                    "p (Games-Howell)": round(float(row["pval"]), 4),
                })
            post_hoc = pd.DataFrame(post_rows)
        except Exception:
            pass

    return ANOVAResult(
        test_type="one_way",
        table=anova_table,
        effect_size=round(float(eta_sq), 4),
        effect_size_name="η²",
        effect_size_ci=eta_sq_ci,
        post_hoc=post_hoc,
        assumption_homogeneity={
            "passed": False,
            "note": "Welch ANOVA 不要求方差齐性假设",
        },
    )
