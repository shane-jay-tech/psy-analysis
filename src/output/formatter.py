"""结果格式化：将分析结果转换为 APA7 格式文本（支持中英双语）

包含效应量强制检查：APA7 要求所有推断统计必须报告效应量。
"""

import pandas as pd
from typing import Dict, Any, Optional, Tuple

from src.analysis.ttest import TTestResult
from src.analysis.anova import ANOVAResult
from src.analysis.correlation import CorrResult
from src.analysis.chi_square import ChiSquareResult
from config.settings import get_output_language


def _lang() -> str:
    return get_output_language()


def format_result_summary(output: Dict[str, Any]) -> str:
    """生成分析结果的 APA7 格式摘要文本（根据当前语言）"""
    result = output.get("result")
    if result is None:
        return _T("无分析结果。", "No analysis result.")

    if isinstance(result, TTestResult):
        return _format_ttest(result)
    elif isinstance(result, ANOVAResult):
        return _format_anova(result)
    elif isinstance(result, CorrResult):
        return _format_correlation(result)
    elif isinstance(result, ChiSquareResult):
        return _format_chi_square(result)
    else:
        return _T("未知结果类型。", "Unknown result type.")


def _T(zh: str, en: str) -> str:
    """根据当前输出语言返回对应文本"""
    return zh if _lang() == "zh" else en


def _format_ttest(r: TTestResult) -> str:
    lang = _lang()
    is_en = (lang == "en")
    sig_zh = "显著" if r.p_value < 0.05 else "不显著"
    sig_en = "significant" if r.p_value < 0.05 else "not significant"
    welch_note_zh = "（Welch校正）" if r.is_welch else ""
    welch_note_en = " (Welch's correction)" if r.is_welch else ""

    if r.test_type == "independent":
        g1, g2 = r.group_stats["组别"].values[:2]
        m1, m2 = r.group_stats["M"].values[:2]
        if is_en:
            return (
                f"An independent-samples t-test{welch_note_en} revealed a {sig_en} difference "
                f"between the {g1} group (M = {m1}) and the {g2} group (M = {m2}), "
                f"t({r.df:.2f}) = {r.t_statistic:.3f}, p = {r.p_value:.4f}, "
                f"{r.effect_size_name} = {r.effect_size:.3f}. "
                f"Mean difference = {r.mean_diff:.3f}, 95% CI [{r.ci_lower:.3f}, {r.ci_upper:.3f}]."
            )
        return (
            f"独立样本t检验{welch_note_zh}结果显示，{g1}组和{g2}组之间"
            f"存在{sig_zh}差异（t({r.df:.2f})={r.t_statistic:.3f}, "
            f"p={r.p_value:.4f}, {r.effect_size_name}={r.effect_size:.3f}）。\n\n"
            f"均值：{g1}组={m1}, {g2}组={m2}, "
            f"均值差={r.mean_diff:.3f} [95%CI: {r.ci_lower:.3f}, {r.ci_upper:.3f}]"
        )

    elif r.test_type == "paired":
        if is_en:
            return (
                f"A paired-samples t-test revealed a {sig_en} difference between pre- and post-test, "
                f"t({r.df}) = {r.t_statistic:.3f}, p = {r.p_value:.4f}, "
                f"{r.effect_size_name} = {r.effect_size:.3f}. "
                f"Mean difference = {r.mean_diff:.3f}, 95% CI [{r.ci_lower:.3f}, {r.ci_upper:.3f}]."
            )
        return (
            f"配对样本t检验结果显示，前后测之间存在{sig_zh}差异"
            f"（t({r.df})={r.t_statistic:.3f}, p={r.p_value:.4f}, "
            f"{r.effect_size_name}={r.effect_size:.3f}）。\n\n"
            f"均值差={r.mean_diff:.3f} [95%CI: {r.ci_lower:.3f}, {r.ci_upper:.3f}]"
        )

    elif r.test_type == "one_sample":
        if is_en:
            sig_desc = (
                "significantly higher than"
                if (r.p_value < 0.05 and r.mean_diff > 0) else
                ("significantly lower than" if (r.p_value < 0.05 and r.mean_diff < 0) else "not significantly different from")
            )
            return (
                f"A one-sample t-test showed that the sample mean was {sig_desc} the test value, "
                f"t({r.df}) = {r.t_statistic:.3f}, p = {r.p_value:.4f}, "
                f"{r.effect_size_name} = {r.effect_size:.3f}. "
                f"Mean difference = {r.mean_diff:.3f}, 95% CI [{r.ci_lower:.3f}, {r.ci_upper:.3f}]."
            )
        sig_zh = "显著高于" if (r.p_value < 0.05 and r.mean_diff > 0) else \
              ("显著低于" if (r.p_value < 0.05 and r.mean_diff < 0) else "与...无显著差异于")
        return (
            f"单样本t检验结果显示，样本均值{sig_zh}检验值"
            f"（t({r.df})={r.t_statistic:.3f}, p={r.p_value:.4f}, "
            f"{r.effect_size_name}={r.effect_size:.3f}）。\n\n"
            f"均值差={r.mean_diff:.3f} [95%CI: {r.ci_lower:.3f}, {r.ci_upper:.3f}]"
        )

    return ""


def _format_anova(r: ANOVAResult) -> str:
    lang = _lang()
    is_en = (lang == "en")

    if r.test_type == "one_way":
        f_row = r.table[r.table["来源"] == "组间"].iloc[0]
        p_val = float(f_row["p"])
        if is_en:
            sig = "significant" if p_val < 0.05 else "not significant"
            return (
                f"A one-way ANOVA revealed a {sig} difference among groups, "
                f"F({f_row['df']}, {r.table[r.table['来源']=='组内'].iloc[0]['df']}) "
                f"= {f_row['F']}, p = {f_row['p']}, {r.effect_size_name} = {r.effect_size}."
            )
        sig = "显著" if p_val < 0.05 else "不显著"
        return (
            f"单因素方差分析结果显示，各组之间存在{sig}差异"
            f"（F({f_row['df']}, {r.table[r.table['来源']=='组内'].iloc[0]['df']})"
            f"={f_row['F']}, p={f_row['p']}, {r.effect_size_name}={r.effect_size}）。"
        )
    elif r.test_type == "two_way":
        parts = []
        for _, row in r.table.iterrows():
            if row["F"] and row["F"] != "":
                p = float(row["p"])
                if is_en:
                    sig = "significant" if p < 0.05 else "not significant"
                    parts.append(f"{row['来源']} effect was {sig} (F = {row['F']}, p = {row['p']})")
                else:
                    sig = "显著" if p < 0.05 else "不显著"
                    parts.append(f"{row['来源']}效应{sig}（F={row['F']}, p={row['p']}）")
        if is_en:
            return "Two-way ANOVA results:\n" + "\n".join(parts)
        return "双因素方差分析结果：\n" + "\n".join(parts)
    return ""


def _format_correlation(r: CorrResult) -> str:
    lang = _lang()
    method = "Pearson" if r.test_type == "pearson" else "Spearman"
    n_vars = len(r.corr_matrix)
    if lang == "en":
        return (
            f"{method} correlation analysis completed, analyzing {n_vars} variables. "
            f"Significance: *p < .05, **p < .01, ***p < .001"
        )
    return f"{method}相关分析完成，共分析{n_vars}个变量。显著性标记：*p<.05, **p<.01, ***p<.001"


def _format_chi_square(r: ChiSquareResult) -> str:
    lang = _lang()
    if lang == "en":
        sig = "significant" if r.p_value < 0.05 else "not significant"
        result = (
            f"A chi-square test of independence revealed a {sig} association "
            f"between the two variables, "
            f"χ²({r.df}) = {r.chi_sq:.3f}, p = {r.p_value:.4f}, "
            f"{r.effect_size_name} = {r.effect_size:.3f}."
        )
    else:
        sig = "显著" if r.p_value < 0.05 else "不显著"
        result = (
            f"卡方独立性检验结果显示，两个变量之间存在{sig}关联"
            f"（χ²({r.df})={r.chi_sq:.3f}, p={r.p_value:.4f}, "
            f"{r.effect_size_name}={r.effect_size:.3f}）。"
        )
    if r.warning:
        result += f"\n\n⚠ {r.warning}"
    return result


def check_effect_size_required(output: Dict[str, Any]) -> Tuple[bool, str]:
    """检查分析结果是否包含效应量。APA7 要求所有推断统计必须报告效应量。

    返回 (is_ok, message)
    """
    test_type = output.get("test_type", "")

    # 描述性统计不需要效应量
    if test_type == "descriptive":
        return True, ""

    result = output.get("result")
    if result is None:
        return False, "未找到分析结果对象。"

    # 检查结果对象上的效应量属性
    effect_size_attrs = [
        "effect_size", "eta_squared", "partial_eta_squared",
        "cohens_d", "hedges_g", "cramers_v", "omega_squared",
        "r_squared", "adj_r_squared", "kappa",
    ]

    found_attrs = []
    for attr in effect_size_attrs:
        val = getattr(result, attr, None)
        if val is not None and val != "" and val != 0:
            found_attrs.append(f"{attr}={val}")

    # 检查 output 字典中的顶级效应量字段
    for k in ["effect_size", "eta_squared", "cohens_d"]:
        if k not in found_attrs and output.get(k) is not None:
            found_attrs.append(f"{k}={output[k]}")

    if not found_attrs:
        lang = get_output_language()
        if lang == "en":
            msg = (
                "APA 7th Edition requires reporting effect sizes for all inferential statistics.\n\n"
                "No effect size field was found in the analysis result (checked: Cohen's d, η², "
                "Cramér's V, r, R², partial η², ω²).\n\n"
                "Please verify:\n"
                "1. The statistical method supports effect size calculation\n"
                "2. The data meets the requirements for effect size computation"
            )
        else:
            msg = (
                "APA 第7版要求所有推断统计必须报告效应量。\n\n"
                "当前分析结果中未检测到效应量字段（已检查：Cohen's d、η²、"
                "Cramér's V、r、R²、偏η²、ω²）。\n\n"
                "请确认：\n"
                "1. 所选的统计方法是否支持效应量计算\n"
                "2. 数据是否满足效应量计算的条件"
            )
        return False, msg

    return True, ""


def build_apa7_report(output: Dict[str, Any]) -> str:
    """生成 APA7 报告，在生成前强制检查效应量。效应量缺失时拒绝生成。"""
    lang = get_output_language()

    # 效应量强制检查
    ok, err_msg = check_effect_size_required(output)
    if not ok:
        if lang == "en":
            return (
                "## Missing Effect Size — APA 7th Edition Requirement\n\n"
                + err_msg
                + "\n\n> APA 7 states: 'For all inferential statistical tests, "
                  "include effect sizes' (APA, 2020, p. 89)."
            )
        return (
            "## 效应量缺失 — APA 第7版强制要求\n\n"
            + err_msg
            + "\n\n> APA 第7版明确规定：'对于所有推断统计检验，必须包含效应量'"
              "（APA, 2020, p. 89）。"
        )

    # 生成摘要
    summary = format_result_summary(output)
    if not summary:
        return ""

    # 构建完整报告
    test_name = output.get("test_name_zh", "")
    result = output.get("result")

    # 收集效应量信息
    es_parts = []
    for attr in ["effect_size", "eta_squared", "partial_eta_squared",
                  "cohens_d", "hedges_g", "cramers_v", "omega_squared",
                  "r_squared", "adj_r_squared"]:
        val = getattr(result, attr, None) if result else None
        if val is not None and val != "":
            es_name = getattr(result, "effect_size_name", attr)
            es_parts.append(f"{es_name} = {val:.3f}" if isinstance(val, float) else f"{es_name} = {val}")

    es_line = "; ".join(es_parts) if es_parts else "效应量已计算（见上方输出）"

    if lang == "en":
        report = (
            f"## {test_name} Results\n\n"
            f"{summary}\n\n"
            f"**Effect size:** {es_line}\n\n"
            f"---\n"
            f"*Report generated in APA 7th Edition format.*"
        )
    else:
        report = (
            f"## {test_name} 结果\n\n"
            f"{summary}\n\n"
            f"**效应量：**{es_line}\n\n"
            f"---\n"
            f"*报告按 APA 第7版格式生成。*"
        )

    return report
