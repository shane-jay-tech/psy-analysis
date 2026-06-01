"""将统计检验结果转换为通俗易懂的中文解释"""

import pandas as pd
from typing import Dict, Any

from src.analysis.ttest import TTestResult
from src.analysis.anova import ANOVAResult
from src.analysis.correlation import CorrResult
from src.analysis.chi_square import ChiSquareResult
from src.analysis.nonparametric import NonParamResult
from src.analysis.regression import RegressionResult
from src.analysis.reliability import ReliabilityResult
from src.analysis.factor_analysis import EFAResult
from src.analysis.advanced import AdvancedResult
from src.analysis.cfa import CFAResult
from src.analysis.validity import ValidityResult


def generate_interpretation(output: Dict[str, Any]) -> str:
    """
    根据分析结果生成面向心理学学生的中文解释。
    语言风格：通俗、有教育意义，帮助理解统计结果的含义。
    """
    result = output.get("result")
    test_type = output.get("test_type", "")
    test_name = output.get("test_name_zh", "")

    if result is None:
        return "未能生成解释，因为分析没有产生有效结果。"

    if isinstance(result, TTestResult):
        return _interpret_ttest(result, test_type)
    elif isinstance(result, ANOVAResult):
        return _interpret_anova(result, test_type)
    elif isinstance(result, CorrResult):
        return _interpret_correlation(result)
    elif isinstance(result, ChiSquareResult):
        return _interpret_chi_square(result)
    elif isinstance(result, NonParamResult):
        return _interpret_nonparametric(result)
    elif isinstance(result, RegressionResult):
        return _interpret_regression(result)
    elif isinstance(result, ReliabilityResult):
        return _interpret_reliability(result)
    elif isinstance(result, EFAResult):
        return _interpret_efa(result)
    elif isinstance(result, CFAResult):
        return _interpret_cfa(result)
    elif isinstance(result, ValidityResult):
        return _interpret_validity(result)
    elif isinstance(result, AdvancedResult):
        return _interpret_advanced(result)

    desc = output.get("descriptive")
    if desc is not None and not desc.empty:
        return _interpret_descriptive(desc)

    return f"已完成{test_name}，请查看上方的统计结果表格。"


def _interpret_ttest(r: TTestResult, test_type: str) -> str:
    """解释t检验结果"""
    lines = []
    alpha = 0.05

    if test_type == "independent_ttest":
        lines.append("📊 **结果解读：独立样本t检验**\n")
        lines.append(
            "独立样本t检验用于比较**两个独立组**在某项指标上的均值是否存在显著差异。"
        )

        g1, g2 = r.group_stats["组别"].values[:2]
        m1, m2 = r.group_stats["M"].values[:2]

        if r.p_value < alpha:
            direction = "高于" if m1 > m2 else "低于"
            lines.append(f"\n✅ **结论：存在显著差异**")
            lines.append(
                f"{g1}组的均值（{m1}）显著{direction}{g2}组（{m2}），"
                f"t({r.df:.2f})={r.t_statistic:.3f}, p={r.p_value:.4f}。"
            )
        else:
            lines.append(f"\n❌ **结论：未发现显著差异**")
            lines.append(
                f"{g1}组（{m1}）和{g2}组（{m2}）之间的差异未达到统计显著水平，"
                f"t({r.df:.2f})={r.t_statistic:.3f}, p={r.p_value:.4f}。"
            )

        lines.append(f"\n📏 **效应量：{r.effect_size_name} = {r.effect_size:.3f}**")
        lines.append(_interpret_cohens_d(r.effect_size))

    elif test_type == "paired_ttest":
        lines.append("📊 **结果解读：配对样本t检验**\n")
        lines.append(
            "配对样本t检验用于比较**同一组被试在两种条件下**（如前后测）的均值是否有显著差异。"
        )

        if r.p_value < alpha:
            direction = "上升" if r.mean_diff > 0 else "下降"
            lines.append(f"\n✅ **结论：存在显著差异**")
            lines.append(
                f"处理后得分显著{direction}（均值差={r.mean_diff:.3f}），"
                f"t({r.df})={r.t_statistic:.3f}, p={r.p_value:.4f}。"
            )
        else:
            lines.append(f"\n❌ **结论：未发现显著变化**")
            lines.append(
                f"前后测之间未发现显著差异，"
                f"t({r.df})={r.t_statistic:.3f}, p={r.p_value:.4f}。"
            )

        lines.append(f"\n📏 **效应量：{r.effect_size_name} = {r.effect_size:.3f}**")

    elif test_type == "one_sample_ttest":
        lines.append("📊 **结果解读：单样本t检验**\n")
        lines.append(
            "单样本t检验用于比较**样本均值与某个已知值（如常模、理论值）**是否有显著差异。"
        )

        if r.p_value < alpha:
            direction = "高于" if r.mean_diff > 0 else "低于"
            lines.append(f"\n✅ **结论：存在显著差异**")
            lines.append(
                f"样本均值显著{direction}检验值（均值差={r.mean_diff:.3f}），"
                f"t({r.df})={r.t_statistic:.3f}, p={r.p_value:.4f}。"
            )

    # Welch校正提示
    if r.is_welch:
        lines.append(
            "\n⚠ 由于两组方差不齐（Levene检验p<0.05），已自动使用Welch校正，"
            "结果仍可靠。"
        )

    return "\n".join(lines)


def _interpret_anova(r: ANOVAResult, test_type: str) -> str:
    """解释ANOVA结果"""
    lines = ["📊 **结果解读：方差分析（ANOVA）**\n"]

    if test_type == "one_way_anova":
        lines.append(
            "单因素方差分析用于比较**三个或更多组**在某项指标上的均值是否存在显著差异。"
        )

        f_row = r.table[r.table["来源"] == "组间"].iloc[0]
        p_val = float(f_row["p"])

        if p_val < 0.05:
            lines.append(f"\n✅ **结论：存在显著组间差异**")
            lines.append(
                f"至少有一组与其他组之间存在显著差异，"
                f"F({f_row['df']}, {r.table[r.table['来源']=='组内'].iloc[0]['df']})"
                f"={f_row['F']}, p={f_row['p']}。"
            )
        else:
            lines.append(f"\n❌ **结论：未发现显著组间差异**")
            lines.append(f"各组之间无显著差异，F={f_row['F']}, p={f_row['p']}。")

        lines.append(f"\n📏 **效应量：{r.effect_size_name} = {r.effect_size:.3f}**")
        lines.append(_interpret_eta_sq(r.effect_size))

        # 事后检验
        if r.post_hoc is not None and not r.post_hoc.empty:
            lines.append("\n🔍 **事后多重比较（Tukey HSD）：**")
            sig_pairs = r.post_hoc[r.post_hoc["p (Tukey HSD)"] < 0.05]
            for _, row in sig_pairs.iterrows():
                lines.append(f"  • {row['比较']}：p={row['p (Tukey HSD)']:.4f} ⭐")

    elif test_type == "two_way_anova":
        lines.append(
            "双因素方差分析用于检验**两个自变量的主效应及其交互作用**。"
        )
        for _, row in r.table.iterrows():
            if row["F"] and row["F"] != "":
                p = float(row["p"])
                sig = "显著" if p < 0.05 else "不显著"
                icon = "✅" if p < 0.05 else "❌"
                lines.append(f"\n{icon} {row['来源']}：{sig}（F={row['F']}, p={row['p']}）")

    # 假设检验提示
    if r.assumption_homogeneity and not r.assumption_homogeneity.get("passed", True):
        lines.append(
            "\n⚠ 方差齐性假设未满足，建议考虑使用Welch ANOVA或非参数检验。"
        )

    return "\n".join(lines)


def _interpret_correlation(r: CorrResult) -> str:
    """解释相关分析结果"""
    lines = ["📊 **结果解读：相关分析**\n"]
    method = "Pearson" if r.test_type == "pearson" else "Spearman"
    lines.append(
        f"{method}相关分析用于衡量两个变量之间的**线性关联程度**。\n"
        "r的取值范围为[-1, 1]：正值表示正相关（一个变量增大，另一个也增大），"
        "负值表示负相关（一个变量增大，另一个减小）。"
    )

    # 找出显著相关（只看下三角）
    n_vars = len(r.corr_matrix)
    sig_pairs = []
    for i in range(n_vars):
        for j in range(i + 1, n_vars):
            p = r.p_matrix.iloc[i, j]
            if pd.notna(p) and p < 0.05:
                r_val = r.corr_matrix.iloc[i, j]
                sig = r.sig_mask.iloc[i, j]
                sig_pairs.append((
                    r.corr_matrix.index[i],
                    r.corr_matrix.columns[j],
                    r_val, p, sig,
                ))

    if sig_pairs:
        lines.append("\n**显著相关：**")
        for v1, v2, rv, pv, sig in sorted(sig_pairs, key=lambda x: abs(x[2]), reverse=True):
            strength = _correlation_strength(abs(rv))
            lines.append(f"  • {v1} ↔ {v2}：r={rv:.3f}{sig}, p={pv:.4f}（{strength}）")
    else:
        lines.append("\n未发现显著相关（所有p > 0.05）。")

    return "\n".join(lines)


def _interpret_chi_square(r: ChiSquareResult) -> str:
    """解释卡方检验结果"""
    lines = ["📊 **结果解读：卡方独立性检验**\n"]
    lines.append(
        "卡方检验用于判断**两个分类变量**之间是否存在关联（是否独立）。"
    )

    if r.p_value < 0.05:
        lines.append(f"\n✅ **结论：存在显著关联**")
        lines.append(
            f"两个分类变量之间存在显著关联，"
            f"χ²({r.df})={r.chi_sq:.3f}, p={r.p_value:.4f}。"
        )
    else:
        lines.append(f"\n❌ **结论：未发现显著关联**")
        lines.append(
            f"两个分类变量之间未发现显著关联（即相互独立），"
            f"χ²({r.df})={r.chi_sq:.3f}, p={r.p_value:.4f}。"
        )

    lines.append(f"\n📏 **效应量：{r.effect_size_name} = {r.effect_size:.3f}**")

    if r.warning:
        lines.append(f"\n⚠ {r.warning}")

    return "\n".join(lines)


def _interpret_nonparametric(r: NonParamResult) -> str:
    """解释非参数检验结果"""
    lines = [f"📊 **结果解读：{r.test_type}**\n"]
    alpha = 0.05

    if r.test_type == "mann_whitney":
        lines.append("Mann-Whitney U检验用于比较**两组独立样本**的分布差异，不要求正态分布。\n")
        if r.group_stats is not None and len(r.group_stats) >= 2:
            g1, g2 = r.group_stats.iloc[0], r.group_stats.iloc[1]
            if r.p_value < alpha:
                lines.append(f"✅ **结论：存在显著差异**")
                lines.append(f"{g1['组别']}组（中位数={g1['中位数']}）和{g2['组别']}组（中位数={g2['中位数']}）之间存在显著差异，U={r.statistic}, p={r.p_value}。")
            else:
                lines.append(f"❌ **结论：未发现显著差异**，U={r.statistic}, p={r.p_value}。")
            lines.append(f"\n📏 **效应量：{r.effect_size_name} = {r.effect_size}**")

    elif r.test_type == "wilcoxon":
        lines.append("Wilcoxon符号秩检验用于比较**配对样本**的差异，不要求正态分布。\n")
        if r.p_value < alpha:
            lines.append(f"✅ **结论：存在显著差异**，W={r.statistic}, p={r.p_value}。")
        else:
            lines.append(f"❌ **结论：未发现显著差异**，W={r.statistic}, p={r.p_value}。")
        lines.append(f"\n📏 **效应量：{r.effect_size_name} = {r.effect_size}**")

    elif r.test_type == "kruskal_wallis":
        lines.append("Kruskal-Wallis H检验用于比较**三组及以上独立样本**的分布差异。\n")
        if r.p_value < alpha:
            lines.append(f"✅ **结论：至少有一组与其他组存在显著差异**，H={r.statistic}, p={r.p_value}。")
            if r.post_hoc is not None and not r.post_hoc.empty:
                lines.append("\n🔍 **Dunn事后多重比较：**")
                sig = r.post_hoc[r.post_hoc["p (Bonferroni)"] < 0.05]
                for _, row in sig.iterrows():
                    lines.append(f"  • {row['比较']}：p={row['p (Bonferroni)']:.4f} ⭐")
        else:
            lines.append(f"❌ **结论：未发现显著差异**，H={r.statistic}, p={r.p_value}。")
        lines.append(f"\n📏 **效应量：{r.effect_size_name} = {r.effect_size}**")

    elif r.test_type == "friedman":
        lines.append("Friedman检验用于比较**重复测量**多个时间点的差异。\n")
        if r.p_value < alpha:
            lines.append(f"✅ **结论：不同测量条件间存在显著差异**，χ²={r.statistic}, p={r.p_value}。")
        else:
            lines.append(f"❌ **结论：未发现显著差异**，χ²={r.statistic}, p={r.p_value}。")
        lines.append(f"\n📏 **效应量：{r.effect_size_name} = {r.effect_size}**")

    return "\n".join(lines)


def _interpret_regression(r: RegressionResult) -> str:
    """解释回归分析结果"""
    lines = ["📊 **结果解读：回归分析**\n"]
    alpha = 0.05

    if r.r_squared > 0:
        lines.append(f"模型解释了因变量 **{r.r_squared*100:.1f}%** 的变异（R²={r.r_squared:.3f}）。")

    if r.f_p < alpha:
        lines.append(f"✅ 整体回归模型显著，F={r.f_stat}, p={r.f_p}。")
    else:
        lines.append(f"❌ 整体回归模型不显著，F={r.f_stat}, p={r.f_p}。")

    # 系数
    sig_coefs = r.coef_table[r.coef_table["p"].apply(lambda x: isinstance(x, (int, float)) and x < 0.05)]
    if len(sig_coefs) > 0:
        lines.append("\n**显著预测变量：**")
        for _, row in sig_coefs.iterrows():
            if row["变量"] != "常量" and row["变量"] != "截距":
                beta_info = f", β={row.get('β', '')}" if 'β' in row and row.get('β') != 0 else ""
                lines.append(f"  • {row['变量']}：B={row['B']}{beta_info}, p={row['p']}")

    # VIF
    if r.vif_table is not None:
        high_vif = r.vif_table[r.vif_table["VIF"] > 10]
        if len(high_vif) > 0:
            lines.append(f"\n⚠ {', '.join(high_vif['变量'])} 的VIF>10，存在严重共线性问题。")

    if r.warning:
        lines.append(f"\n⚠ {r.warning}")

    return "\n".join(lines)


def _interpret_reliability(r: ReliabilityResult) -> str:
    """解释信度分析结果（覆盖 7 种类型）"""
    # 主指标名称映射
    metric_name = {
        "cronbach_alpha": ("Cronbach's α", "α"),
        "split_half": ("分半信度（Spearman-Brown 校正）", "r"),
        "mcdonald_omega": ("McDonald's ω", "ω"),
        "composite_reliability": ("组合信度（CR）", "CR"),
        "icc": (f"组内相关系数 {r.icc_type}".strip(), "ICC"),
        "test_retest": ("重测信度", "r"),
        "cohens_kappa": ("Cohen's κ 评分者一致性", "κ"),
        "fleiss_kappa": ("Fleiss' κ 多评分者一致性", "κ"),
    }
    title, sym = metric_name.get(r.test_type, ("信度分析", "值"))
    lines = [f"📊 **结果解读：{title}**\n"]

    # 通用阈值解读（κ 用 Landis & Koch；其他用 0.70/0.80/0.90）
    if r.test_type in ("cohens_kappa", "fleiss_kappa"):
        if r.alpha >= 0.81:
            level = "几乎完美（Landis & Koch 1977）"
        elif r.alpha >= 0.61:
            level = "高度一致"
        elif r.alpha >= 0.41:
            level = "中等一致"
        elif r.alpha >= 0.21:
            level = "尚可"
        elif r.alpha >= 0.0:
            level = "微弱"
        else:
            level = "比偶然还差"
    else:
        if r.alpha >= 0.90:
            level = "优秀"
        elif r.alpha >= 0.80:
            level = "良好"
        elif r.alpha >= 0.70:
            level = "可接受"
        elif r.alpha >= 0.60:
            level = "偏低（仅探索性研究可接受）"
        else:
            level = "不可接受"

    lines.append(f"{sym} = **{r.alpha}**（95% CI: [{r.ci_lower}, {r.ci_upper}]），属于**{level}**水平。")
    lines.append(f"基于 {r.n_items} 个观测和 {r.n_cases} 个有效样本。")

    # 类型专属补充
    if r.test_type == "split_half" and r.split_half_r is not None:
        lines.append(f"两半之间的原始 Pearson r = {r.split_half_r}（已用 Spearman-Brown 校正为 SB-r）。")
    elif r.test_type == "composite_reliability" and r.cr_per_factor:
        lines.append("\n**各因子组合信度：**")
        for f, cr in r.cr_per_factor.items():
            mark = "✅" if cr >= 0.70 else "⚠"
            lines.append(f"- {mark} {f}: CR = {cr}")
    elif r.test_type == "icc":
        lines.append(f"ICC 类型：**{r.icc_type}**。"
                     "Koo & Li (2016) 建议：<0.50 较差，0.50-0.75 中等，0.75-0.90 良好，>0.90 优秀。")
    elif r.test_type == "test_retest":
        lines.append("两次测量的 Pearson r 反映量表得分的时间稳定性，要求间隔 2-4 周。")
    elif r.test_type in ("cohens_kappa", "fleiss_kappa"):
        method_zh = "Cohen's κ（两评分者）" if r.kappa_method == "cohen" else "Fleiss' κ（≥3 评分者）"
        lines.append(f"采用 {method_zh}。")

    if r.warning:
        lines.append(f"\n{r.warning}")

    return "\n".join(lines)


def _interpret_cfa(r: CFAResult) -> str:
    """解释 CFA 结果（含 AVE/CR/HTMT/Fornell-Larcker）"""
    lines = ["📊 **结果解读：验证性因素分析（CFA）**\n"]

    if r.is_fallback:
        lines.append(f"⚠ {r.fallback_note}")
        if r.loadings is not None:
            lines.append(f"\n基于 {r.n_obs} 个观测、{r.n_factors} 个因子、{r.n_items} 道题目的探索性参考结果。")
        return "\n".join(lines)

    lines.append(f"模型：{r.n_factors} 个因子、{r.n_items} 道题目、N = {r.n_obs}（{r.estimator} 估计）。\n")
    lines.append(f"**拟合指标**：χ²({r.chi2_df}) = {r.chi2}, p = {r.chi2_p}; "
                 f"CFI = {r.cfi}, TLI = {r.tli}, RMSEA = {r.rmsea} "
                 f"[{r.rmsea_ci_lower}, {r.rmsea_ci_upper}], SRMR = {r.srmr}.")
    lines.append(f"\n{r.fit_summary_zh}")

    # 显著载荷统计
    if r.loadings is not None and "p值" in r.loadings.columns:
        sig_count = int((r.loadings["p值"] < 0.05).sum())
        total = len(r.loadings)
        lines.append(f"\n**因子载荷**：{total} 个标准化载荷中 {sig_count} 个达到 p<.05 显著。")

    # 聚合效度（AVE）
    if r.ave_per_factor:
        lines.append("\n**聚合效度（AVE）：**")
        for f, ave in r.ave_per_factor.items():
            mark = "✅" if ave >= 0.50 else "⚠"
            lines.append(f"- {mark} {f}: AVE = {ave}")

    # 组合信度（CR）
    if r.cr_per_factor:
        lines.append("\n**组合信度（CR）：**")
        for f, cr in r.cr_per_factor.items():
            mark = "✅" if cr >= 0.70 else "⚠"
            lines.append(f"- {mark} {f}: CR = {cr}")

    # 区分效度
    if r.discriminant_fl_pass is not None:
        fl_mark = "✅ 通过" if r.discriminant_fl_pass else "⚠ 未通过"
        lines.append(f"\n**Fornell-Larcker 区分效度**：{fl_mark}（√AVE 应大于因子相关）。")
    if r.discriminant_htmt_pass is not None:
        ht_mark = "✅ 通过" if r.discriminant_htmt_pass else "⚠ 未通过"
        lines.append(f"**HTMT 区分效度**：{ht_mark}（阈值 0.85）。")

    if r.warnings:
        lines.append("\n" + "\n".join(r.warnings))

    return "\n".join(lines)


def _interpret_validity(r: ValidityResult) -> str:
    """解释效度分析结果（6 种类型）"""
    title_map = {
        "cvi": "内容效度指数（CVI）",
        "ave": "聚合效度（AVE）",
        "discriminant_fl": "区分效度（Fornell-Larcker）",
        "discriminant_htmt": "区分效度（HTMT）",
        "criterion_validity": "效标效度",
        "known_groups_validity": "已知组别效度",
    }
    title = title_map.get(r.test_type, "效度分析")
    lines = [f"📊 **结果解读：{title}**\n"]

    if r.test_type == "cvi":
        lines.append(f"S-CVI/Ave = **{r.main_value}**（{r.n_cases} 位专家）。")
        if r.main_value >= 0.90:
            lines.append("✅ 整体内容效度优秀（S-CVI/Ave ≥ 0.90，Polit & Beck 2006）。")
        elif r.main_value >= 0.80:
            lines.append("整体内容效度可接受（S-CVI/Ave ≥ 0.80）。")
        else:
            lines.append("⚠ S-CVI/Ave < 0.80，整体内容效度不足。")
        lines.append("评估准则：每题 I-CVI ≥ 0.78，整表 S-CVI/Ave ≥ 0.90 为推荐阈值。")

    elif r.test_type == "ave":
        lines.append(f"AVE 均值 = **{r.main_value}**。AVE ≥ 0.50（Fornell & Larcker 1981）表示该因子解释了"
                     "题目方差的一半以上，达到聚合效度标准。")
        if r.warning:
            lines.append(r.warning)

    elif r.test_type == "discriminant_fl":
        if r.fornell_larcker_pass:
            lines.append("✅ 所有因子的 √AVE 均大于其与其他因子的相关绝对值，区分效度通过。")
        else:
            lines.append("⚠ 部分因子 √AVE 小于其与其他因子的相关，区分效度未通过——可能存在共线或概念重叠。")
        lines.append("准则：对每个因子，√AVE > 该因子与其他任何因子的 |r|。")

    elif r.test_type == "discriminant_htmt":
        lines.append(f"最大 HTMT = **{r.main_value}**。Henseler et al. (2015) 严格阈值 0.85，宽松阈值 0.90。")
        if r.fornell_larcker_pass:
            lines.append("✅ 所有因子对的 HTMT 均低于阈值，区分效度通过。")
        else:
            lines.append("⚠ 存在 HTMT 超阈值的因子对，区分效度可能不足。")

    elif r.test_type == "criterion_validity":
        kind_zh = "同时" if (r.detail is not None and "同时效度" in str(r.detail.iloc[0].get("类型", ""))) else "效标"
        lines.append(f"量表与效标的相关 r = **{r.criterion_r}**（95% CI: "
                     f"[{r.criterion_ci_lower}, {r.criterion_ci_upper}], p = {r.criterion_p}, n = {r.n_cases}）。")
        if abs(r.criterion_r or 0) >= 0.50:
            lines.append("✅ 效标效度良好（|r| ≥ 0.50）。")
        elif abs(r.criterion_r or 0) >= 0.30:
            lines.append("效标效度中等（0.30 ≤ |r| < 0.50）。")
        else:
            lines.append("⚠ 效标效度偏低（|r| < 0.30），需检查效标选择是否恰当。")
        lines.append(f"_{kind_zh}效度_：与外部效标的同期/延迟相关。")

    elif r.test_type == "known_groups_validity":
        test_zh = "独立样本 t 检验" if r.known_groups_test == "ttest" else "单因素 ANOVA"
        stat_sym = "t" if r.known_groups_test == "ttest" else "F"
        lines.append(f"{test_zh}：{stat_sym} = {r.known_groups_stat}, p = {r.known_groups_p}; "
                     f"{r.known_groups_effect_name} = {r.known_groups_effect_size}。")
        if (r.known_groups_p or 1.0) < 0.05:
            lines.append("✅ 量表能显著区分预先已知差异的群体，已知组别效度有支持证据。")
        else:
            lines.append("⚠ 组间差异不显著，已知组别效度证据不足。")

    if r.warning and r.warning not in "".join(lines):
        lines.append(f"\n{r.warning}")

    return "\n".join(lines)


def _interpret_efa(r: EFAResult) -> str:
    """解释EFA结果"""
    lines = ["📊 **结果解读：探索性因素分析（EFA）**\n"]

    if r.kmo >= 0.80:
        kmo_level = "良好"
    elif r.kmo >= 0.70:
        kmo_level = "中等"
    elif r.kmo >= 0.60:
        kmo_level = "勉强可接受"
    else:
        kmo_level = "不足"

    lines.append(f"KMO = **{r.kmo}**（{kmo_level}），Bartlett χ²({r.bartlett_df})={r.bartlett_chi2}, p={r.bartlett_p}。")

    if r.kmo < 0.60:
        lines.append("⚠ KMO值偏低，数据不太适合因素分析，建议增加样本量或删除低相关题目。")
    else:
        lines.append(f"✅ 数据适合进行因素分析。共提取 **{r.n_factors}** 个因素（{r.rotation}旋转）。")

    if r.variance_explained is not None:
        total_var = r.variance_explained[r.variance_explained["因素"] == "合计"]
        if not total_var.empty:
            cum_var = float(total_var["累计比例"].values[0])
            lines.append(f"累计解释方差：**{cum_var*100:.1f}%**。")

    if r.warning:
        lines.append(f"\n{r.warning}")

    return "\n".join(lines)


def _interpret_advanced(r: AdvancedResult) -> str:
    """解释高级分析结果"""
    lines = [f"📊 **结果解读：{r.test_type}**\n"]

    if r.test_type == "ancova":
        lines.append("协方差分析（ANCOVA）在排除协变量影响后比较组间差异。\n")
        lines.append(f"效应量 η²p = {r.effect_size}，表示排除协变量后组间差异的解释比例。")

    elif r.test_type == "mediation":
        lines.append("中介分析检验自变量是否通过中介变量间接影响因变量。\n")
        lines.append(f"中介效应占比：**{r.effect_size*100:.1f}%**。")
        if r.bootstrap_ci is not None and len(r.bootstrap_ci) > 0:
            ci = r.bootstrap_ci.iloc[0]
            if ci["CI下限"] * ci["CI上限"] > 0:
                lines.append(f"✅ Bootstrap 95% CI = [{ci['CI下限']}, {ci['CI上限']}]，不包含0，中介效应显著。")
            else:
                lines.append(f"⚠ Bootstrap 95% CI = [{ci['CI下限']}, {ci['CI上限']}]，包含0，中介效应不显著。")
        if r.warning:
            lines.append(f"\n{r.warning}")

    elif r.test_type == "moderation":
        lines.append("调节分析检验某个变量是否改变自变量对因变量的影响强度。\n")
        interact_row = r.coef_table[r.coef_table["变量"].str.contains("×")]
        if len(interact_row) > 0:
            p_val = float(interact_row.iloc[0]["p"])
            if p_val < 0.05:
                lines.append(f"✅ 交互项显著（p={p_val:.4f}），存在调节效应。")
            else:
                lines.append(f"⚠ 交互项不显著（p={p_val:.4f}），未发现调节效应。")
        if r.simple_slopes is not None:
            lines.append("\n**简单斜率分析：**")
            for _, row in r.simple_slopes.iterrows():
                sig_marker = " ⭐" if row["p"] < 0.05 else ""
                lines.append(f"  • {row.iloc[0]}：斜率={row['简单斜率']}, p={row['p']}{sig_marker}")

    return "\n".join(lines)


def _interpret_descriptive(desc_df: pd.DataFrame) -> str:
    """解释描述统计结果"""
    lines = ["📊 **描述性统计结果**\n"]
    n_vars = len(desc_df)
    total_n = desc_df["N"].max() if "N" in desc_df.columns else "?"

    lines.append(f"共分析了 {n_vars} 个变量，样本量 N = {total_n}。")

    if "M" in desc_df.columns and "SD" in desc_df.columns:
        lines.append("\n**变量概况：**")
        for _, row in desc_df.iterrows():
            lines.append(f"  • {row['变量']}：M = {row['M']}, SD = {row['SD']}")

    return "\n".join(lines)


def _interpret_cohens_d(d: float) -> str:
    """解释 Cohen's d 效应量的大小"""
    d = abs(d)
    if d < 0.2:
        return "效应量很小，实际意义可能有限。"
    elif d < 0.5:
        return "属于小到中等效应量。"
    elif d < 0.8:
        return "属于中等偏大效应量。"
    else:
        return "属于大效应量，差异具有明显的实际意义。"


def _interpret_eta_sq(eta: float) -> str:
    """解释 η² 效应量的大小"""
    if eta < 0.01:
        return "效应量很小。"
    elif eta < 0.06:
        return "属于小效应量。"
    elif eta < 0.14:
        return "属于中等效应量。"
    else:
        return "属于大效应量，组间差异具有重要的实际意义。"


def _correlation_strength(r_abs: float) -> str:
    """解释相关系数的强度"""
    if r_abs < 0.1:
        return "极弱相关"
    elif r_abs < 0.3:
        return "弱相关"
    elif r_abs < 0.5:
        return "中等相关"
    elif r_abs < 0.7:
        return "较强相关"
    else:
        return "强相关"
