"""APA 表格生成器 v5.2。

将统计结果格式化为 APA 第7版标准表格。
支持描述统计、相关矩阵、t 检验、ANOVA、回归、信度、EFA。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List
import numpy as np
import pandas as pd


@dataclass
class APATable:
    table_id: str
    method_id: str
    title: str
    note: str
    columns: list[str]
    rows: list[dict]
    apa_number: Optional[int] = None
    source_result_card_id: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


def _fmt_p(p: float) -> str:
    if p < 0.001:
        return "< .001"
    return f"{p:.3f}".lstrip("0")


def _fmt_num(val, decimals: int = 2) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "-"
    return f"{val:.{decimals}f}"


def descriptive_stats_table(
    df: pd.DataFrame,
    variables: list[str],
    group_var: Optional[str] = None,
    table_id: str = "desc",
) -> APATable:
    """生成描述统计表（M, SD, N, Range）。"""
    rows = []

    if group_var and group_var in df.columns:
        groups = df[group_var].dropna().unique()
        for var in variables:
            for g in sorted(groups):
                subset = pd.to_numeric(df[df[group_var] == g][var], errors="coerce").dropna()
                rows.append({
                    "变量": var,
                    "组别": str(g),
                    "N": int(len(subset)),
                    "M": _fmt_num(subset.mean()),
                    "SD": _fmt_num(subset.std()),
                    "Min": _fmt_num(subset.min()),
                    "Max": _fmt_num(subset.max()),
                })
        columns = ["变量", "组别", "N", "M", "SD", "Min", "Max"]
    else:
        for var in variables:
            series = pd.to_numeric(df[var], errors="coerce").dropna()
            rows.append({
                "变量": var,
                "N": int(len(series)),
                "M": _fmt_num(series.mean()),
                "SD": _fmt_num(series.std()),
                "Min": _fmt_num(series.min()),
                "Max": _fmt_num(series.max()),
            })
        columns = ["变量", "N", "M", "SD", "Min", "Max"]

    return APATable(
        table_id=table_id,
        method_id="descriptive",
        title="Descriptive Statistics",
        note="M = mean; SD = standard deviation.",
        columns=columns,
        rows=rows,
    )


def correlation_matrix_table(
    df: pd.DataFrame,
    variables: list[str],
    table_id: str = "corr",
) -> APATable:
    """生成相关矩阵表（下三角 + 对角线描述统计）。"""
    numeric_df = df[variables].apply(pd.to_numeric, errors="coerce").dropna()
    corr = numeric_df.corr()
    n = len(numeric_df)

    from scipy import stats as sp_stats

    rows = []
    for i, var in enumerate(variables):
        row = {"变量": f"{i+1}. {var}"}
        for j, other in enumerate(variables):
            if j < i:
                r_val = corr.loc[var, other]
                _, p_val = sp_stats.pearsonr(numeric_df[var], numeric_df[other])
                star = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
                row[str(j + 1)] = f"{r_val:.2f}{star}"
            elif j == i:
                row[str(j + 1)] = "—"
            else:
                row[str(j + 1)] = ""
        row["M"] = _fmt_num(numeric_df[var].mean())
        row["SD"] = _fmt_num(numeric_df[var].std())
        rows.append(row)

    columns = ["变量"] + [str(k + 1) for k in range(len(variables))] + ["M", "SD"]

    return APATable(
        table_id=table_id,
        method_id="correlation",
        title="Correlations Among Study Variables",
        note=f"N = {n}. *p < .05. **p < .01. ***p < .001.",
        columns=columns,
        rows=rows,
    )


def ttest_result_table(
    result,
    table_id: str = "ttest",
) -> APATable:
    """从 t 检验结果生成 APA 表格。"""
    rows = []

    if hasattr(result, "group_stats") and result.group_stats is not None:
        for _, row in result.group_stats.iterrows():
            rows.append({
                "组别": str(row.iloc[0]),
                "N": int(row.get("N", row.get("n", 0))),
                "M": _fmt_num(row.get("均值", row.get("M", row.get("Mean", 0)))),
                "SD": _fmt_num(row.get("标准差", row.get("SD", row.get("Std", 0)))),
            })

    stat_row = {
        "t": _fmt_num(result.t_statistic if hasattr(result, "t_statistic") else result.statistic, 3),
        "df": str(int(result.df)) if hasattr(result, "df") else "-",
        "p": _fmt_p(result.p_value),
        "Cohen's d": _fmt_num(result.effect_size, 2),
    }
    rows.append(stat_row)

    columns = ["组别", "N", "M", "SD", "t", "df", "p", "Cohen's d"]

    return APATable(
        table_id=table_id,
        method_id="ttest",
        title="Independent Samples t-test Results",
        note="Cohen's d effect size interpretation: small (0.2), medium (0.5), large (0.8).",
        columns=columns,
        rows=rows,
    )


def anova_result_table(
    result,
    table_id: str = "anova",
) -> APATable:
    """从方差分析结果生成 APA 表格。"""
    rows = []

    table = result.table
    if table is not None:
        source_col = "来源" if "来源" in table.columns else table.columns[0]
        for _, row in table.iterrows():
            apa_row = {"来源": str(row[source_col])}
            for col in ["SS", "df", "df1", "df2", "MS", "F", "p", "ηp²", "η²"]:
                if col in row.index:
                    val = row[col]
                    if val == "-" or val == "" or (isinstance(val, float) and np.isnan(val)):
                        apa_row[col] = "-"
                    elif col == "p":
                        apa_row[col] = _fmt_p(float(val))
                    elif col in ("df", "df1", "df2"):
                        apa_row[col] = str(int(float(val)))
                    else:
                        apa_row[col] = _fmt_num(float(val), 3)
            rows.append(apa_row)

    columns = [c for c in ["来源", "SS", "df", "df1", "df2", "MS", "F", "p", "ηp²", "η²"]
               if any(c in r for r in rows)]

    test_type = result.test_type if hasattr(result, "test_type") else "anova"
    title_map = {
        "one_way": "One-Way ANOVA Results",
        "two_way": "Two-Way ANOVA Results",
        "mixed": "Mixed-Design ANOVA Results",
        "repeated": "Repeated-Measures ANOVA Results",
    }

    return APATable(
        table_id=table_id,
        method_id=test_type,
        title=title_map.get(test_type, "ANOVA Results"),
        note="ηp² = partial eta-squared. Interpretation: small (.01), medium (.06), large (.14).",
        columns=columns,
        rows=rows,
    )


def regression_result_table(
    result,
    table_id: str = "reg",
) -> APATable:
    """从回归结果生成 APA 表格。"""
    rows = []

    if hasattr(result, "coef_table") and result.coef_table is not None:
        for _, row in result.coef_table.iterrows():
            apa_row = {}
            for col in row.index:
                val = row[col]
                if col == "p":
                    apa_row[col] = _fmt_p(float(val)) if pd.notna(val) else "-"
                elif col == "变量":
                    apa_row[col] = str(val)
                else:
                    apa_row[col] = _fmt_num(float(val), 3) if pd.notna(val) else "-"
            rows.append(apa_row)

    columns = list(result.coef_table.columns) if hasattr(result, "coef_table") and result.coef_table is not None else []

    test_type = result.test_type if hasattr(result, "test_type") else "regression"
    title_map = {
        "multiple": "Multiple Regression Results",
        "hierarchical": "Hierarchical Regression Results",
    }
    note_parts = []
    if hasattr(result, "r_squared"):
        note_parts.append(f"R² = {_fmt_num(result.r_squared, 4)}")
    if hasattr(result, "adj_r_squared"):
        note_parts.append(f"Adjusted R² = {_fmt_num(result.adj_r_squared, 4)}")

    return APATable(
        table_id=table_id,
        method_id=test_type,
        title=title_map.get(test_type, "Regression Results"),
        note="; ".join(note_parts) + "." if note_parts else "",
        columns=columns,
        rows=rows,
    )


def reliability_table(
    result,
    table_id: str = "rel",
) -> APATable:
    """从信度结果生成 APA 表格。"""
    rows = [{
        "指标": result.test_type.replace("_", " ").title(),
        "值": _fmt_num(result.alpha if hasattr(result, "alpha") else result.omega_value, 3),
        "95% CI": f"[{_fmt_num(result.ci_lower, 3)}, {_fmt_num(result.ci_upper, 3)}]",
        "题目数": str(result.n_items),
        "样本量": str(result.n_cases),
    }]

    if hasattr(result, "item_stats") and result.item_stats is not None:
        for _, item_row in result.item_stats.iterrows():
            rows.append({
                "指标": f"  删除 {item_row.get('题目', item_row.iloc[0])}",
                "值": _fmt_num(item_row.get("删除后α", item_row.get("alpha_if_deleted", 0)), 3),
                "95% CI": "",
                "题目数": "",
                "样本量": "",
            })

    return APATable(
        table_id=table_id,
        method_id=result.test_type,
        title="Reliability Analysis Results",
        note="CI = confidence interval (bootstrap).",
        columns=["指标", "值", "95% CI", "题目数", "样本量"],
        rows=rows,
    )


def table_to_dataframe(table: APATable) -> pd.DataFrame:
    """将 APATable 转换为 DataFrame（用于 Word/CSV 导出）。"""
    return pd.DataFrame(table.rows)


def table_to_markdown(table: APATable) -> str:
    """将 APATable 转换为 Markdown 格式。"""
    lines = []
    if table.apa_number:
        lines.append(f"**Table {table.apa_number}**")
    lines.append(f"*{table.title}*")
    lines.append("")

    df = pd.DataFrame(table.rows)
    if df.empty:
        return "\n".join(lines) + "\n(No data)\n"

    cols = [c for c in table.columns if c in df.columns]
    if not cols:
        cols = list(df.columns)

    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    lines.append(header)
    lines.append(sep)

    for _, row in df.iterrows():
        vals = [str(row.get(c, "")) for c in cols]
        lines.append("| " + " | ".join(vals) + " |")

    lines.append("")
    lines.append(f"*Note.* {table.note}")
    return "\n".join(lines)


def table_to_csv(table: APATable) -> str:
    """将 APATable 转换为 CSV 字符串。"""
    df = pd.DataFrame(table.rows)
    return df.to_csv(index=False)


def factor_loading_table(
    loadings,
    item_labels: list[str],
    factor_labels: list[str],
    rotation: str = "varimax",
    table_id: str = "efa",
) -> APATable:
    """生成因子载荷表（EFA）。

    载荷 >= 0.40 在数值后标注 * 表示粗体高亮。
    """
    loadings_arr = np.array(loadings)
    rows = []

    for i, item in enumerate(item_labels):
        row = {"题目": item}
        for j, factor in enumerate(factor_labels):
            val = loadings_arr[i, j]
            formatted = _fmt_num(val, 3)
            if abs(val) >= 0.40:
                formatted += "*"
            row[factor] = formatted
        rows.append(row)

    columns = ["题目"] + list(factor_labels)

    return APATable(
        table_id=table_id,
        method_id="efa",
        title="Factor Loadings",
        note=f"Rotation: {rotation}. * indicates loading >= .40.",
        columns=columns,
        rows=rows,
    )


def model_fit_table(
    fit_indices: dict,
    model_name: str = "Model",
    table_id: str = "fit",
) -> APATable:
    """生成模型拟合指标表（CFA/SEM）。"""
    row = {"模型": model_name}

    index_keys = ["chi2", "df", "p", "CFI", "TLI", "RMSEA", "SRMR", "AIC", "BIC"]
    for key in index_keys:
        val = fit_indices.get(key)
        if val is None:
            continue
        if key == "p":
            row[key] = _fmt_p(float(val))
        elif key == "df":
            row[key] = str(int(val))
        elif key in ("AIC", "BIC"):
            row[key] = _fmt_num(val, 1)
        elif key == "chi2":
            row["χ²"] = _fmt_num(val, 2)
        else:
            row[key] = _fmt_num(val, 3)

    columns = ["模型"]
    col_map = {"chi2": "χ²"}
    for key in index_keys:
        if fit_indices.get(key) is not None:
            columns.append(col_map.get(key, key))

    return APATable(
        table_id=table_id,
        method_id="model_fit",
        title="Model Fit Indices",
        note=(
            "Acceptable thresholds: CFI/TLI >= .90 (good >= .95); "
            "RMSEA <= .08 (good <= .05); SRMR <= .08."
        ),
        columns=columns,
        rows=[row],
    )


def hlm_result_table(card: dict) -> List[APATable]:
    """从 HLM（多层线性模型）结果卡生成 APA 表格。

    返回两张表：
    1. 固定效应表（Term, Estimate, SE, t, p）
    2. 随机效应表（Group, Variance, SD）
    """
    tables = []

    # --- Fixed Effects Table ---
    fixed_effects = card.get("fixed_effects", {})
    fe_rows = []

    if isinstance(fixed_effects, dict):
        for term, info in fixed_effects.items():
            if isinstance(info, dict):
                fe_rows.append({
                    "Term": term,
                    "Estimate": _fmt_num(info.get("estimate", info.get("coef", info.get("b"))), 4),
                    "SE": _fmt_num(info.get("se", info.get("SE", info.get("std_err"))), 4),
                    "t": _fmt_num(info.get("t", info.get("t_value")), 3),
                    "p": _fmt_p(info["p"]) if "p" in info or "p_value" in info else "-",
                })
                # Fix p key fallback
                if fe_rows[-1]["p"] == "-" and "p_value" in info:
                    fe_rows[-1]["p"] = _fmt_p(info["p_value"])
            elif isinstance(info, (int, float)):
                fe_rows.append({
                    "Term": term,
                    "Estimate": _fmt_num(info, 4),
                    "SE": "-",
                    "t": "-",
                    "p": "-",
                })
    elif isinstance(fixed_effects, list):
        for fe in fixed_effects:
            if isinstance(fe, dict):
                term = fe.get("name", fe.get("term", "?"))
                fe_rows.append({
                    "Term": term,
                    "Estimate": _fmt_num(fe.get("estimate", fe.get("coef", fe.get("b"))), 4),
                    "SE": _fmt_num(fe.get("se", fe.get("SE")), 4),
                    "t": _fmt_num(fe.get("t", fe.get("t_value")), 3),
                    "p": _fmt_p(fe.get("p", fe.get("p_value", float("nan")))),
                })

    fe_columns = ["Term", "Estimate", "SE", "t", "p"]
    model_spec = card.get("model_spec", "")
    note_parts = []
    if model_spec:
        note_parts.append(f"Model: {model_spec}")
    icc = card.get("icc")
    if icc is not None:
        note_parts.append(f"ICC = {_fmt_num(icc, 3)}")
    aic = card.get("aic")
    bic = card.get("bic")
    if aic is not None:
        note_parts.append(f"AIC = {_fmt_num(aic, 1)}")
    if bic is not None:
        note_parts.append(f"BIC = {_fmt_num(bic, 1)}")

    fe_table = APATable(
        table_id=f"tbl_hlm_fixed",
        method_id="hlm",
        title="Fixed Effects of Multilevel Model",
        note="; ".join(note_parts) + "." if note_parts else "",
        columns=fe_columns,
        rows=fe_rows,
    )
    tables.append(fe_table)

    # --- Random Effects Table ---
    random_effects = card.get("random_effects", {})
    re_rows = []

    group_var_name = card.get("group_var", "Group")
    group_variance = random_effects.get("group_variance", random_effects.get("intercept_variance"))
    residual_variance = random_effects.get("residual_variance", random_effects.get("residual"))

    if group_variance is not None:
        re_rows.append({
            "Group": group_var_name,
            "Variance": _fmt_num(group_variance, 4),
            "SD": _fmt_num(group_variance ** 0.5, 4) if group_variance >= 0 else "-",
        })
    if residual_variance is not None:
        re_rows.append({
            "Group": "Residual",
            "Variance": _fmt_num(residual_variance, 4),
            "SD": _fmt_num(residual_variance ** 0.5, 4) if residual_variance >= 0 else "-",
        })

    # Check for random slope variance
    slope_variance = random_effects.get("slope_variance", random_effects.get("random_slope_var"))
    if slope_variance is not None:
        re_rows.append({
            "Group": "Slope",
            "Variance": _fmt_num(slope_variance, 4),
            "SD": _fmt_num(slope_variance ** 0.5, 4) if slope_variance >= 0 else "-",
        })

    re_columns = ["Group", "Variance", "SD"]
    n_groups = card.get("n_groups")
    n_obs = card.get("n")
    re_note_parts = []
    if n_groups is not None:
        re_note_parts.append(f"Number of groups = {n_groups}")
    if n_obs is not None:
        re_note_parts.append(f"N = {n_obs}")

    re_table = APATable(
        table_id=f"tbl_hlm_random",
        method_id="hlm",
        title="Random Effects of Multilevel Model",
        note="; ".join(re_note_parts) + "." if re_note_parts else "",
        columns=re_columns,
        rows=re_rows,
    )
    tables.append(re_table)

    return tables


def nonparametric_result_table(
    result,
    table_id: str = "nonparam",
) -> APATable:
    """从非参数检验结果生成 APA 表格。"""
    rows = []

    if hasattr(result, "group_stats") and result.group_stats is not None:
        for _, row in result.group_stats.iterrows():
            r = {}
            for col in result.group_stats.columns:
                val = row[col]
                if isinstance(val, float):
                    r[col] = _fmt_num(val)
                else:
                    r[col] = str(val)
            rows.append(r)

    stat_name = {"mann_whitney": "U", "wilcoxon": "W", "kruskal_wallis": "H"}.get(
        result.test_type, "Statistic"
    )
    stat_row = {
        stat_name: _fmt_num(result.statistic, 2),
        "p": _fmt_p(result.p_value),
        result.effect_size_name: _fmt_num(result.effect_size, 3),
    }
    rows.append(stat_row)

    title_map = {
        "mann_whitney": "Mann-Whitney U Test Results",
        "wilcoxon": "Wilcoxon Signed-Rank Test Results",
        "kruskal_wallis": "Kruskal-Wallis H Test Results",
    }
    note_map = {
        "mann_whitney": "r = rank-biserial correlation. Interpretation: small (.1), medium (.3), large (.5).",
        "wilcoxon": "r = effect size (Z/√N). Interpretation: small (.1), medium (.3), large (.5).",
        "kruskal_wallis": "η²H = eta-squared. Interpretation: small (.01), medium (.06), large (.14).",
    }

    return APATable(
        table_id=table_id,
        method_id=result.test_type,
        title=title_map.get(result.test_type, "Nonparametric Test Results"),
        note=note_map.get(result.test_type, ""),
        columns=list(rows[0].keys()) if rows else [],
        rows=rows,
    )


def chi_square_result_table(
    result,
    table_id: str = "chi_sq",
) -> APATable:
    """从卡方检验结果生成 APA 表格。"""
    rows = []

    if hasattr(result, "contingency_table") and result.contingency_table is not None:
        ct = result.contingency_table
        for idx, row in ct.iterrows():
            r = {"": str(idx)}
            for col in ct.columns:
                r[str(col)] = str(int(row[col])) if pd.notna(row[col]) else "-"
            rows.append(r)

    stat_row = {
        "χ²": _fmt_num(result.chi_sq, 2),
        "df": str(result.df),
        "p": _fmt_p(result.p_value),
        result.effect_size_name: _fmt_num(result.effect_size, 3),
    }
    rows.append(stat_row)

    title = "Chi-Square Test of Independence" if result.test_type == "independence" else "Chi-Square Goodness-of-Fit Test"

    return APATable(
        table_id=table_id,
        method_id="chi_square",
        title=title,
        note=f"{result.effect_size_name} interpretation: small (.1), medium (.3), large (.5).",
        columns=list(rows[0].keys()) if rows else [],
        rows=rows,
    )


def mediation_result_table(
    result,
    table_id: str = "mediation",
) -> List[APATable]:
    """从中介分析结果生成 APA 表格（路径系数表 + Bootstrap CI 表）。"""
    tables = []

    if hasattr(result, "coef_table") and result.coef_table is not None:
        rows = []
        for _, row in result.coef_table.iterrows():
            r = {}
            for col in result.coef_table.columns:
                val = row[col]
                if col == "p" and isinstance(val, float):
                    r[col] = _fmt_p(val)
                elif isinstance(val, float):
                    r[col] = _fmt_num(val, 3)
                else:
                    r[col] = str(val)
            rows.append(r)

        tables.append(APATable(
            table_id=f"{table_id}_paths",
            method_id="mediation",
            title="Mediation Analysis: Path Coefficients",
            note="Standardized coefficients (β). Bootstrap bias-corrected CI for indirect effects.",
            columns=list(result.coef_table.columns),
            rows=rows,
        ))

    if hasattr(result, "bootstrap_ci") and result.bootstrap_ci is not None:
        ci_rows = []
        for _, row in result.bootstrap_ci.iterrows():
            r = {}
            for col in result.bootstrap_ci.columns:
                val = row[col]
                if isinstance(val, float):
                    r[col] = _fmt_num(val, 3)
                else:
                    r[col] = str(val)
            ci_rows.append(r)

        tables.append(APATable(
            table_id=f"{table_id}_ci",
            method_id="mediation",
            title="Bootstrap Confidence Intervals for Indirect Effects",
            note="5000 bootstrap samples. Bias-corrected percentile method. CI excluding 0 indicates significance.",
            columns=list(result.bootstrap_ci.columns),
            rows=ci_rows,
        ))

    return tables


def moderation_result_table(
    result,
    table_id: str = "moderation",
) -> List[APATable]:
    """从调节分析结果生成 APA 表格（回归系数表 + 简单斜率表）。"""
    tables = []

    if hasattr(result, "coef_table") and result.coef_table is not None:
        rows = []
        for _, row in result.coef_table.iterrows():
            r = {}
            for col in result.coef_table.columns:
                val = row[col]
                if col == "p" and isinstance(val, float):
                    r[col] = _fmt_p(val)
                elif isinstance(val, float):
                    r[col] = _fmt_num(val, 3)
                else:
                    r[col] = str(val)
            rows.append(r)

        tables.append(APATable(
            table_id=f"{table_id}_coef",
            method_id="moderation",
            title="Moderation Analysis: Regression Coefficients",
            note="Variables are mean-centered. Interaction term tests moderation effect.",
            columns=list(result.coef_table.columns),
            rows=rows,
        ))

    if hasattr(result, "simple_slopes") and result.simple_slopes is not None:
        ss_rows = []
        for _, row in result.simple_slopes.iterrows():
            r = {}
            for col in result.simple_slopes.columns:
                val = row[col]
                if col == "p" and isinstance(val, float):
                    r[col] = _fmt_p(val)
                elif isinstance(val, float):
                    r[col] = _fmt_num(val, 3)
                else:
                    r[col] = str(val)
            ss_rows.append(r)

        tables.append(APATable(
            table_id=f"{table_id}_slopes",
            method_id="moderation",
            title="Simple Slopes Analysis",
            note="Simple slopes at -1SD, mean, and +1SD of moderator.",
            columns=list(result.simple_slopes.columns),
            rows=ss_rows,
        ))

    return tables


def logistic_result_table(
    result,
    table_id: str = "logistic",
) -> List[APATable]:
    """从 Logistic 回归结果生成 APA 表格（系数 + OR 表）。"""
    tables = []

    if hasattr(result, "coef_table") and result.coef_table is not None:
        rows = []
        for _, row in result.coef_table.iterrows():
            r = {}
            for col in result.coef_table.columns:
                val = row[col]
                if col == "p" and isinstance(val, float):
                    r[col] = _fmt_p(val)
                elif isinstance(val, float):
                    r[col] = _fmt_num(val, 3)
                else:
                    r[col] = str(val)
            rows.append(r)

        note_parts = []
        if hasattr(result, "pseudo_r2") and result.pseudo_r2:
            for name, val in result.pseudo_r2.items():
                note_parts.append(f"{name} = {_fmt_num(val, 4)}")
        if hasattr(result, "accuracy"):
            note_parts.append(f"Classification accuracy = {_fmt_num(result.accuracy * 100, 1)}%")

        tables.append(APATable(
            table_id=f"{table_id}_coef",
            method_id="logistic_regression",
            title="Logistic Regression Results",
            note="; ".join(note_parts) + "." if note_parts else "OR = odds ratio.",
            columns=list(result.coef_table.columns),
            rows=rows,
        ))

    return tables


def generate_tables_from_card(card: dict) -> list[APATable]:
    """根据结果卡的 method 字段自动生成对应的 APA 表格。"""
    from src.analysis.method_ids import resolve_method_id

    tables = []
    method = resolve_method_id(
        card.get("method", "") or card.get("method_id", "")
    )

    if method == "descriptive":
        df = card.get("df")
        variables = card.get("variables", [])
        if df is not None and variables:
            table = descriptive_stats_table(
                df, variables,
                group_var=card.get("group_var"),
                table_id=f"tbl_{method}_1",
            )
            tables.append(table)

    elif method in ("pearson_corr", "pearson_correlation", "spearman_corr"):
        df = card.get("df")
        variables = card.get("variables", [])
        if df is not None and variables:
            table = correlation_matrix_table(
                df, variables,
                table_id=f"tbl_{method}_1",
            )
            tables.append(table)

    elif method in ("independent_ttest", "paired_ttest", "one_sample_ttest"):
        result = card.get("result")
        if result is not None:
            table = ttest_result_table(result, table_id=f"tbl_{method}_1")
            tables.append(table)

    elif method in ("mann_whitney", "wilcoxon", "kruskal_wallis"):
        result = card.get("result")
        if result is not None:
            table = nonparametric_result_table(result, table_id=f"tbl_{method}_1")
            tables.append(table)

    elif method in ("chi_square", "chi_square_independence", "chi_square_gof"):
        result = card.get("result")
        if result is not None:
            table = chi_square_result_table(result, table_id=f"tbl_{method}_1")
            tables.append(table)

    elif method in ("one_way_anova", "two_way_anova", "repeated_measures_anova", "mixed_anova"):
        result = card.get("result")
        if result is not None:
            table = anova_result_table(result, table_id=f"tbl_{method}_1")
            tables.append(table)

    elif method in ("multiple_regression", "hierarchical_regression", "linear_regression"):
        result = card.get("result")
        if result is not None:
            table = regression_result_table(
                result,
                table_id=f"tbl_{method}_1",
            )
            tables.append(table)

    elif method in ("cronbach_alpha", "mcdonalds_omega"):
        result = card.get("result")
        if result is not None:
            table = reliability_table(
                result,
                table_id=f"tbl_{method}_1",
            )
            tables.append(table)

    elif method == "efa":
        loadings = card.get("factor_loadings")
        item_labels = card.get("item_labels", [])
        factor_labels = card.get("factor_labels", [])
        if loadings is not None and item_labels and factor_labels:
            table = factor_loading_table(
                loadings, item_labels, factor_labels,
                rotation=card.get("rotation", "varimax"),
                table_id=f"tbl_{method}_1",
            )
            tables.append(table)

    elif method in ("cfa", "sem"):
        fit_indices = card.get("fit_indices", {})
        if fit_indices:
            table = model_fit_table(
                fit_indices,
                model_name=card.get("model_name", "Model"),
                table_id=f"tbl_{method}_1",
            )
            tables.append(table)

    elif method in ("hlm", "hierarchical_linear_model", "mixed_effects"):
        tables.extend(hlm_result_table(card))

    elif method == "mediation":
        result = card.get("result")
        if result is not None:
            tables.extend(mediation_result_table(result, table_id=f"tbl_{method}"))

    elif method == "moderation":
        result = card.get("result")
        if result is not None:
            tables.extend(moderation_result_table(result, table_id=f"tbl_{method}"))

    elif method in ("logistic_regression", "binary_logistic"):
        result = card.get("result")
        if result is not None:
            tables.extend(logistic_result_table(result, table_id=f"tbl_{method}"))

    return tables
