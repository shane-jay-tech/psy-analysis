"""AnalysisResultCard — 统计结果标准化卡片。

把 run_analysis() 输出转为可解释、可写入论文的结构化结果卡：
- APA 格式结果文本
- 通俗语言解释
- 效应量
- 假设检查状态
- 风险提示
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pandas as pd


@dataclass
class AnalysisResultCard:
    """统计结果卡 — 连接统计分析和论文写作。"""
    method_id: str
    method_name: str
    variables: dict[str, list[str]]
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    assumption_status: str = "not_checked"  # passed / partial / failed / not_checked
    tables: list[dict[str, Any]] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)
    effect_sizes: list[dict[str, Any]] = field(default_factory=list)
    apa_text: str = ""
    plain_language_summary: str = ""
    technical_notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    def to_markdown(self) -> str:
        """导出为 Markdown 格式。"""
        lines = [f"### {self.method_name}"]
        if self.apa_text:
            lines.append(f"\n**APA 结果**：{self.apa_text}")
        if self.plain_language_summary:
            lines.append(f"\n**通俗解释**：{self.plain_language_summary}")
        if self.effect_sizes:
            es_parts = [f"{e['name']}={e['value']:.3f}" for e in self.effect_sizes if 'value' in e]
            if es_parts:
                lines.append(f"\n**效应量**：{', '.join(es_parts)}")
        if self.warnings:
            lines.append("\n**注意**：")
            for w in self.warnings:
                lines.append(f"- {w}")
        return "\n".join(lines)


def build_card_from_output(output: dict[str, Any]) -> AnalysisResultCard:
    """从 run_analysis() 输出构建结果卡。"""
    method_id = output.get("test_type", "unknown")
    method_name = output.get("test_name_zh", method_id)
    plan = output.get("plan")

    variables = {}
    if plan:
        if hasattr(plan, "dependent_vars") and plan.dependent_vars:
            variables["dependent"] = list(plan.dependent_vars)
        if hasattr(plan, "independent_vars") and plan.independent_vars:
            variables["independent"] = list(plan.independent_vars)
        if hasattr(plan, "covariates") and plan.covariates:
            variables["covariates"] = list(plan.covariates)

    card = AnalysisResultCard(
        method_id=method_id,
        method_name=method_name,
        variables=variables,
    )

    # Assumptions
    assumptions_raw = output.get("assumptions", {})
    if assumptions_raw:
        for name, info in assumptions_raw.items():
            if isinstance(info, dict):
                card.assumptions.append({
                    "name": name,
                    "passed": info.get("passed", None),
                    "detail": info.get("detail", ""),
                })
            else:
                card.assumptions.append({"name": name, "passed": bool(info)})
        passed_count = sum(1 for a in card.assumptions if a.get("passed"))
        total = len(card.assumptions)
        if total == 0:
            card.assumption_status = "not_checked"
        elif passed_count == total:
            card.assumption_status = "passed"
        elif passed_count == 0:
            card.assumption_status = "failed"
        else:
            card.assumption_status = "partial"

    # Dispatch to method-specific card builder
    builder = _CARD_BUILDERS.get(method_id)
    if builder:
        builder(card, output)
    else:
        card.warnings.append(f"方法 '{method_id}' 暂无专用结果卡模板")
        _generic_card(card, output)

    # Provenance
    card.provenance = {
        "method_id": method_id,
        "generated_by": "AnalysisResultCard",
    }

    return card


# ---------------------------------------------------------------------------
# Method-specific builders
# ---------------------------------------------------------------------------

def _build_descriptive(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    desc_df = output.get("descriptive")

    if desc_df is not None and isinstance(desc_df, pd.DataFrame):
        card.tables.append({"name": "描述统计", "data": desc_df.to_dict()})
        n = int(desc_df.iloc[0].get("count", 0)) if "count" in desc_df.columns else 0
        vars_list = card.variables.get("dependent", [])
        card.apa_text = f"对{len(vars_list)}个变量进行了描述统计分析（N={n}）。"
        card.plain_language_summary = "描述统计展示了各变量的集中趋势和离散程度。"
    elif result and hasattr(result, "summary_df"):
        card.apa_text = "描述统计分析已完成。"
        card.plain_language_summary = "描述统计展示了各变量的均值、标准差等基本特征。"
    else:
        card.apa_text = "描述统计分析已完成。"
        card.plain_language_summary = "描述统计展示了数据的基本分布特征。"


def _build_independent_ttest(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("t 检验未产生结果")
        return

    t_val = getattr(result, "t_statistic", None) or getattr(result, "t", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    df = getattr(result, "df", None) or getattr(result, "dof", None)
    d = getattr(result, "cohens_d", None) or getattr(result, "effect_size", None)

    dv = card.variables.get("dependent", ["因变量"])[0]
    iv = card.variables.get("independent", ["分组变量"])[0]

    if t_val is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"独立样本 t 检验结果表明，{iv}对{dv}的影响{sig}"
        if df is not None:
            apa += f"，t({df:.0f}) = {t_val:.3f}, p = {p_val:.3f}"
        else:
            apa += f"，t = {t_val:.3f}, p = {p_val:.3f}"
        if d is not None:
            apa += f", Cohen's d = {d:.3f}"
            card.effect_sizes.append({"name": "Cohen's d", "value": float(d)})
        card.apa_text = apa + "。"
        card.plain_language_summary = f"两组在{dv}上的差异{'达到统计显著水平' if p_val < 0.05 else '未达到统计显著水平'}。"
    else:
        card.warnings.append("t 检验结果缺少关键统计量")

    if not card.effect_sizes:
        card.warnings.append("缺少效应量（Cohen's d），建议补充")


def _build_paired_ttest(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("配对 t 检验未产生结果")
        return

    t_val = getattr(result, "t_statistic", None) or getattr(result, "t", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    df = getattr(result, "df", None) or getattr(result, "dof", None)
    d = getattr(result, "cohens_d", None) or getattr(result, "effect_size", None)

    dvs = card.variables.get("dependent", ["测量1", "测量2"])

    if t_val is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"配对样本 t 检验结果表明，前后测差异{sig}"
        if df is not None:
            apa += f"，t({df:.0f}) = {t_val:.3f}, p = {p_val:.3f}"
        else:
            apa += f"，t = {t_val:.3f}, p = {p_val:.3f}"
        if d is not None:
            apa += f", Cohen's d = {d:.3f}"
            card.effect_sizes.append({"name": "Cohen's d", "value": float(d)})
        card.apa_text = apa + "。"
        card.plain_language_summary = f"两次测量之间的差异{'达到统计显著水平' if p_val < 0.05 else '未达到统计显著水平'}。"
    else:
        card.warnings.append("配对 t 检验结果缺少关键统计量")

    if not card.effect_sizes:
        card.warnings.append("缺少效应量（Cohen's d），建议补充")


def _build_one_way_anova(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("方差分析未产生结果")
        return

    f_val = getattr(result, "f_statistic", None) or getattr(result, "F", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    df_between = getattr(result, "df_between", None)
    df_within = getattr(result, "df_within", None)
    eta2 = getattr(result, "eta_squared", None) or getattr(result, "effect_size", None)

    dv = card.variables.get("dependent", ["因变量"])[0]
    iv = card.variables.get("independent", ["分组变量"])[0]

    if f_val is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"单因素方差分析结果表明，{iv}对{dv}的主效应{sig}"
        if df_between is not None and df_within is not None:
            apa += f"，F({df_between:.0f}, {df_within:.0f}) = {f_val:.3f}, p = {p_val:.3f}"
        else:
            apa += f"，F = {f_val:.3f}, p = {p_val:.3f}"
        if eta2 is not None:
            apa += f", η² = {eta2:.3f}"
            card.effect_sizes.append({"name": "η²", "value": float(eta2)})
        card.apa_text = apa + "。"
        card.plain_language_summary = f"不同{iv}组别在{dv}上的差异{'达到统计显著水平' if p_val < 0.05 else '未达到统计显著水平'}。"
    else:
        card.warnings.append("方差分析结果缺少关键统计量")

    if not card.effect_sizes:
        card.warnings.append("缺少效应量（η²），建议补充")


def _build_pearson_corr(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("相关分析未产生结果")
        return

    r_val = getattr(result, "r", None) or getattr(result, "correlation", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    n = getattr(result, "n", None) or getattr(result, "sample_size", None)

    dvs = card.variables.get("dependent", ["变量1", "变量2"])
    var1 = dvs[0] if len(dvs) > 0 else "变量1"
    var2 = dvs[1] if len(dvs) > 1 else "变量2"

    if r_val is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        strength = "强" if abs(r_val) > 0.7 else ("中等" if abs(r_val) > 0.4 else "弱")
        direction = "正" if r_val > 0 else "负"
        apa = f"Pearson 相关分析表明，{var1}与{var2}之间存在{sig}的{strength}{direction}相关"
        if n is not None:
            apa += f"，r({n-2}) = {r_val:.3f}, p = {p_val:.3f}"
        else:
            apa += f"，r = {r_val:.3f}, p = {p_val:.3f}"
        card.apa_text = apa + "。"
        card.effect_sizes.append({"name": "r", "value": float(r_val)})
        card.effect_sizes.append({"name": "r²", "value": float(r_val ** 2)})
        card.plain_language_summary = f"{var1}和{var2}之间呈{strength}{direction}相关关系（{'显著' if p_val < 0.05 else '不显著'}）。"
    else:
        card.warnings.append("相关分析结果缺少关键统计量")


def _build_multiple_regression(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("多元回归未产生结果")
        return

    r2 = getattr(result, "r_squared", None) or getattr(result, "r2", None)
    adj_r2 = getattr(result, "adj_r_squared", None) or getattr(result, "adj_r2", None)
    f_val = getattr(result, "f_statistic", None) or getattr(result, "F", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    coefficients = getattr(result, "coefficients", None) or getattr(result, "coefs", None)

    dv = card.variables.get("dependent", ["因变量"])[0]
    ivs = card.variables.get("independent", ["自变量"])

    if r2 is not None:
        apa = f"多元回归分析表明，{', '.join(ivs)}对{dv}的联合解释力"
        sig = "显著" if (p_val is not None and p_val < 0.05) else ""
        if f_val is not None and p_val is not None:
            apa += f"{sig}，F = {f_val:.3f}, p = {p_val:.3f}"
        apa += f", R² = {r2:.3f}"
        if adj_r2 is not None:
            apa += f", 调整 R² = {adj_r2:.3f}"
        card.apa_text = apa + "。"
        card.effect_sizes.append({"name": "R²", "value": float(r2)})
        if adj_r2 is not None:
            card.effect_sizes.append({"name": "Adjusted R²", "value": float(adj_r2)})
        pct = r2 * 100
        card.plain_language_summary = f"这些预测变量共同解释了{dv}变异的 {pct:.1f}%。"
    else:
        card.warnings.append("多元回归结果缺少 R² 统计量")


def _build_repeated_anova(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("重复测量方差分析未产生结果")
        return

    f_val = getattr(result, "f_statistic", None) or getattr(result, "F", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    eta2 = getattr(result, "eta_squared", None) or getattr(result, "partial_eta2", None)
    epsilon = getattr(result, "epsilon", None) or getattr(result, "greenhouse_geisser", None)

    dv = card.variables.get("dependent", ["因变量"])[0]

    if f_val is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"重复测量方差分析结果表明，时间/条件对{dv}的主效应{sig}"
        apa += f"，F = {f_val:.3f}, p = {p_val:.3f}"
        if eta2 is not None:
            apa += f", η²p = {eta2:.3f}"
            card.effect_sizes.append({"name": "η²p", "value": float(eta2)})
        if epsilon is not None and epsilon < 0.75:
            apa += f"（Greenhouse-Geisser 校正 ε = {epsilon:.3f}）"
            card.warnings.append("球形性假设违反，已使用 Greenhouse-Geisser 校正")
        card.apa_text = apa + "。"
        card.plain_language_summary = f"不同时间点/条件下的{dv}{'存在显著变化' if p_val < 0.05 else '未发现显著变化'}。"
    else:
        card.warnings.append("重复测量方差分析结果缺少关键统计量")


def _build_mediation(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("中介效应分析未产生结果")
        return

    indirect = getattr(result, "indirect_effect", None) or getattr(result, "ab", None)
    direct = getattr(result, "direct_effect", None) or getattr(result, "c_prime", None)
    total = getattr(result, "total_effect", None) or getattr(result, "c", None)
    ci_lower = getattr(result, "ci_lower", None) or getattr(result, "boot_ci_low", None)
    ci_upper = getattr(result, "ci_upper", None) or getattr(result, "boot_ci_high", None)

    ivs = card.variables.get("independent", ["X"])
    dvs = card.variables.get("dependent", ["Y"])
    mediators = card.variables.get("covariates", ["M"])
    x = ivs[0] if ivs else "X"
    y = dvs[0] if dvs else "Y"
    m = mediators[0] if mediators else "M"

    if indirect is not None:
        sig = ""
        if ci_lower is not None and ci_upper is not None:
            sig = "显著" if (ci_lower > 0 or ci_upper < 0) else "不显著"
        apa = f"中介效应分析（Bootstrap 5000 次）表明，{m}在{x}与{y}之间的中介效应{sig}"
        apa += f"，间接效应 ab = {indirect:.4f}"
        if ci_lower is not None and ci_upper is not None:
            apa += f", 95% CI [{ci_lower:.4f}, {ci_upper:.4f}]"
        if direct is not None:
            apa += f"；直接效应 c' = {direct:.4f}"
        if total is not None:
            apa += f"；总效应 c = {total:.4f}"
        card.apa_text = apa + "。"
        card.effect_sizes.append({"name": "间接效应 ab", "value": float(indirect)})
        if total and total != 0:
            ratio = abs(indirect / total)
            card.effect_sizes.append({"name": "中介效应占比", "value": float(ratio)})
            card.plain_language_summary = f"{x}对{y}的影响中，约 {ratio*100:.1f}% 通过{m}传递。"
        else:
            card.plain_language_summary = f"{m}在{x}与{y}之间{'存在' if sig == '显著' else '不存在'}显著中介效应。"
    else:
        card.warnings.append("中介效应分析结果缺少间接效应统计量")


def _build_moderation(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("调节效应分析未产生结果")
        return

    interaction_b = getattr(result, "interaction_b", None) or getattr(result, "interaction_coef", None)
    interaction_p = getattr(result, "interaction_p", None)
    r2_change = getattr(result, "r2_change", None) or getattr(result, "delta_r2", None)
    f_change = getattr(result, "f_change", None)

    ivs = card.variables.get("independent", ["X"])
    dvs = card.variables.get("dependent", ["Y"])
    moderators = card.variables.get("covariates", ["W"])
    x = ivs[0] if ivs else "X"
    y = dvs[0] if dvs else "Y"
    w = moderators[0] if moderators else "W"

    if interaction_b is not None:
        sig = ""
        if interaction_p is not None:
            sig = "显著" if interaction_p < 0.05 else "不显著"
        apa = f"调节效应分析表明，{w}对{x}与{y}关系的调节作用{sig}"
        apa += f"，交互项 b = {interaction_b:.4f}"
        if interaction_p is not None:
            apa += f", p = {interaction_p:.3f}"
        if r2_change is not None:
            apa += f", ΔR² = {r2_change:.4f}"
            card.effect_sizes.append({"name": "ΔR²", "value": float(r2_change)})
        card.apa_text = apa + "。"
        card.plain_language_summary = f"{w}{'显著调节' if sig == '显著' else '未显著调节'}{x}对{y}的影响。"
    else:
        card.warnings.append("调节效应分析结果缺少交互项统计量")


def _build_cronbach_alpha(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("信度分析未产生结果")
        return

    alpha = getattr(result, "alpha", None) or getattr(result, "cronbach_alpha", None)
    n_items = getattr(result, "n_items", None) or getattr(result, "num_items", None)
    item_total = getattr(result, "item_total_correlations", None)

    if alpha is not None:
        level = "良好" if alpha >= 0.8 else ("可接受" if alpha >= 0.7 else "偏低")
        apa = f"Cronbach's α 信度分析结果为 α = {alpha:.3f}"
        if n_items is not None:
            apa += f"（{n_items} 个题项）"
        apa += f"，内部一致性{level}"
        card.apa_text = apa + "。"
        card.effect_sizes.append({"name": "Cronbach's α", "value": float(alpha)})
        card.plain_language_summary = f"量表信度为 {alpha:.3f}，{'达到' if alpha >= 0.7 else '未达到'}可接受标准（0.70）。"
        if alpha < 0.7:
            card.warnings.append("Cronbach's α 低于 0.70，建议检查题项质量或删除弱相关题项")
        if item_total is not None and hasattr(item_total, '__iter__'):
            low_items = [i for i, v in enumerate(item_total) if v < 0.3]
            if low_items:
                card.warnings.append(f"有 {len(low_items)} 个题项的题总相关低于 0.30，建议审视")
    else:
        card.warnings.append("信度分析结果缺少 α 值")


def _build_two_way_anova(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("双因素方差分析未产生结果")
        return

    main_a_f = getattr(result, "factor_a_f", None) or getattr(result, "f_a", None)
    main_a_p = getattr(result, "factor_a_p", None) or getattr(result, "p_a", None)
    main_b_f = getattr(result, "factor_b_f", None) or getattr(result, "f_b", None)
    main_b_p = getattr(result, "factor_b_p", None) or getattr(result, "p_b", None)
    interact_f = getattr(result, "interaction_f", None) or getattr(result, "f_ab", None)
    interact_p = getattr(result, "interaction_p", None) or getattr(result, "p_ab", None)
    eta2_a = getattr(result, "eta2_a", None)
    eta2_b = getattr(result, "eta2_b", None)
    eta2_ab = getattr(result, "eta2_ab", None)

    ivs = card.variables.get("independent", ["因素A", "因素B"])
    dv = card.variables.get("dependent", ["因变量"])[0]
    factor_a = ivs[0] if len(ivs) > 0 else "因素A"
    factor_b = ivs[1] if len(ivs) > 1 else "因素B"

    parts = [f"双因素方差分析结果表明："]
    if main_a_f is not None and main_a_p is not None:
        sig_a = "显著" if main_a_p < 0.05 else "不显著"
        parts.append(f"{factor_a}的主效应{sig_a}，F = {main_a_f:.3f}, p = {main_a_p:.3f}")
        if eta2_a is not None:
            parts[-1] += f", η²p = {eta2_a:.3f}"
            card.effect_sizes.append({"name": f"η²p ({factor_a})", "value": float(eta2_a)})
    if main_b_f is not None and main_b_p is not None:
        sig_b = "显著" if main_b_p < 0.05 else "不显著"
        parts.append(f"{factor_b}的主效应{sig_b}，F = {main_b_f:.3f}, p = {main_b_p:.3f}")
        if eta2_b is not None:
            parts[-1] += f", η²p = {eta2_b:.3f}"
            card.effect_sizes.append({"name": f"η²p ({factor_b})", "value": float(eta2_b)})
    if interact_f is not None and interact_p is not None:
        sig_ab = "显著" if interact_p < 0.05 else "不显著"
        parts.append(f"{factor_a}×{factor_b}交互效应{sig_ab}，F = {interact_f:.3f}, p = {interact_p:.3f}")
        if eta2_ab is not None:
            parts[-1] += f", η²p = {eta2_ab:.3f}"
            card.effect_sizes.append({"name": "η²p (交互)", "value": float(eta2_ab)})
        if interact_p < 0.05:
            card.technical_notes.append("交互效应显著，建议进行简单效应分析")

    card.apa_text = "；".join(parts) + "。"
    card.plain_language_summary = f"分析了{factor_a}和{factor_b}对{dv}的独立和联合影响。"


def _build_mixed_anova(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("混合设计方差分析未产生结果")
        return

    between_f = getattr(result, "between_f", None) or getattr(result, "f_between", None)
    between_p = getattr(result, "between_p", None) or getattr(result, "p_between", None)
    within_f = getattr(result, "within_f", None) or getattr(result, "f_within", None)
    within_p = getattr(result, "within_p", None) or getattr(result, "p_within", None)
    interact_f = getattr(result, "interaction_f", None) or getattr(result, "f_interaction", None)
    interact_p = getattr(result, "interaction_p", None) or getattr(result, "p_interaction", None)
    epsilon = getattr(result, "epsilon", None) or getattr(result, "greenhouse_geisser", None)

    dv = card.variables.get("dependent", ["因变量"])[0]
    ivs = card.variables.get("independent", ["组间因素", "组内因素"])
    between_name = ivs[0] if len(ivs) > 0 else "组间因素"
    within_name = ivs[1] if len(ivs) > 1 else "组内因素"

    parts = ["混合设计方差分析结果表明："]
    if between_f is not None and between_p is not None:
        sig = "显著" if between_p < 0.05 else "不显著"
        parts.append(f"{between_name}的组间主效应{sig}，F = {between_f:.3f}, p = {between_p:.3f}")
    if within_f is not None and within_p is not None:
        sig = "显著" if within_p < 0.05 else "不显著"
        parts.append(f"{within_name}的组内主效应{sig}，F = {within_f:.3f}, p = {within_p:.3f}")
    if interact_f is not None and interact_p is not None:
        sig = "显著" if interact_p < 0.05 else "不显著"
        parts.append(f"交互效应{sig}，F = {interact_f:.3f}, p = {interact_p:.3f}")

    if epsilon is not None and epsilon < 0.75:
        parts.append(f"Greenhouse-Geisser 校正 ε = {epsilon:.3f}")
        card.warnings.append("球形性假设违反，已使用 Greenhouse-Geisser 校正")

    card.apa_text = "；".join(parts) + "。"
    card.plain_language_summary = f"分析了{between_name}（组间）和{within_name}（组内）对{dv}的影响。"


def _build_ancova(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("协方差分析未产生结果")
        return

    f_val = getattr(result, "f_statistic", None) or getattr(result, "F", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    eta2 = getattr(result, "eta_squared", None) or getattr(result, "partial_eta2", None)
    adj_means = getattr(result, "adjusted_means", None)

    dv = card.variables.get("dependent", ["因变量"])[0]
    iv = card.variables.get("independent", ["分组变量"])[0]
    covariates = card.variables.get("covariates", ["协变量"])

    if f_val is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"协方差分析（控制{', '.join(covariates)}后）结果表明，{iv}对{dv}的影响{sig}"
        apa += f"，F = {f_val:.3f}, p = {p_val:.3f}"
        if eta2 is not None:
            apa += f", η²p = {eta2:.3f}"
            card.effect_sizes.append({"name": "η²p", "value": float(eta2)})
        card.apa_text = apa + "。"
        card.plain_language_summary = f"在控制了{', '.join(covariates)}的影响后，{iv}对{dv}的效应{'显著' if p_val < 0.05 else '不显著'}。"
    else:
        card.warnings.append("协方差分析结果缺少关键统计量")

    if adj_means is not None:
        card.technical_notes.append("已计算调整后均值（校正协变量影响）")


def _build_mann_whitney(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("Mann-Whitney U 检验未产生结果")
        return

    u_val = getattr(result, "u_statistic", None) or getattr(result, "U", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    z_val = getattr(result, "z_value", None) or getattr(result, "z", None)
    r_effect = getattr(result, "r_effect", None) or getattr(result, "rank_biserial", None)
    n1 = getattr(result, "n1", None)
    n2 = getattr(result, "n2", None)

    dv = card.variables.get("dependent", ["因变量"])[0]
    iv = card.variables.get("independent", ["分组变量"])[0]

    if u_val is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"Mann-Whitney U 检验结果表明，{iv}对{dv}的影响{sig}，U = {u_val:.1f}"
        if z_val is not None:
            apa += f", Z = {z_val:.3f}"
        apa += f", p = {p_val:.3f}"
        if r_effect is not None:
            apa += f", r = {r_effect:.3f}"
            card.effect_sizes.append({"name": "r (rank-biserial)", "value": float(r_effect)})
        if n1 is not None and n2 is not None:
            apa += f" (n₁ = {n1}, n₂ = {n2})"
        card.apa_text = apa + "。"
        card.plain_language_summary = f"两组在{dv}上的秩均值差异{'达到统计显著水平' if p_val < 0.05 else '未达到统计显著水平'}（非参数检验）。"
        card.technical_notes.append("使用非参数检验（数据不满足正态性假设）")
    else:
        card.warnings.append("Mann-Whitney U 检验结果缺少关键统计量")


def _build_wilcoxon(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("Wilcoxon 符号秩检验未产生结果")
        return

    w_val = getattr(result, "w_statistic", None) or getattr(result, "W", None) or getattr(result, "T", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    z_val = getattr(result, "z_value", None) or getattr(result, "z", None)
    r_effect = getattr(result, "r_effect", None) or getattr(result, "effect_size", None)
    n = getattr(result, "n", None)

    dv = card.variables.get("dependent", ["因变量"])[0]

    if p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"Wilcoxon 符号秩检验结果表明，前后测差异{sig}"
        if w_val is not None:
            apa += f"，W = {w_val:.1f}"
        if z_val is not None:
            apa += f", Z = {z_val:.3f}"
        apa += f", p = {p_val:.3f}"
        if r_effect is not None:
            apa += f", r = {r_effect:.3f}"
            card.effect_sizes.append({"name": "r (effect size)", "value": float(r_effect)})
        if n is not None:
            apa += f" (N = {n})"
        card.apa_text = apa + "。"
        card.plain_language_summary = f"两次测量在{dv}上的差异{'达到统计显著水平' if p_val < 0.05 else '未达到统计显著水平'}（非参数配对检验）。"
        card.technical_notes.append("使用非参数配对检验（数据不满足正态性假设）")
    else:
        card.warnings.append("Wilcoxon 检验结果缺少关键统计量")


def _build_kruskal_wallis(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("Kruskal-Wallis 检验未产生结果")
        return

    h_val = getattr(result, "h_statistic", None) or getattr(result, "H", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    df = getattr(result, "df", None)
    eta2 = getattr(result, "eta_squared", None) or getattr(result, "epsilon_squared", None)

    dv = card.variables.get("dependent", ["因变量"])[0]
    iv = card.variables.get("independent", ["分组变量"])[0]

    if h_val is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"Kruskal-Wallis 检验结果表明，{iv}对{dv}的影响{sig}"
        if df is not None:
            apa += f"，H({df}) = {h_val:.3f}, p = {p_val:.3f}"
        else:
            apa += f"，H = {h_val:.3f}, p = {p_val:.3f}"
        if eta2 is not None:
            apa += f", η²H = {eta2:.3f}"
            card.effect_sizes.append({"name": "η²H", "value": float(eta2)})
        card.apa_text = apa + "。"
        card.plain_language_summary = f"多组在{dv}上的秩均值差异{'达到统计显著水平' if p_val < 0.05 else '未达到统计显著水平'}（非参数检验）。"
        card.technical_notes.append("使用非参数多组比较（数据不满足正态性或方差齐性假设）")
        if p_val < 0.05:
            card.technical_notes.append("建议进行事后两两比较（Dunn 检验或 Mann-Whitney U）")
    else:
        card.warnings.append("Kruskal-Wallis 检验结果缺少关键统计量")


def _build_hierarchical_regression(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("层级回归未产生结果")
        return

    steps = getattr(result, "steps", None) or getattr(result, "model_steps", None)
    final_r2 = getattr(result, "r_squared", None) or getattr(result, "r2", None)
    final_adj_r2 = getattr(result, "adj_r_squared", None) or getattr(result, "adj_r2", None)

    dv = card.variables.get("dependent", ["因变量"])[0]
    ivs = card.variables.get("independent", ["预测变量"])

    parts = [f"层级回归分析以{dv}为因变量："]

    if steps and hasattr(steps, '__iter__'):
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                r2 = step.get("r2", step.get("R2"))
                delta_r2 = step.get("delta_r2", step.get("r2_change"))
                f_change = step.get("f_change")
                p_change = step.get("p_change")
                if r2 is not None:
                    step_desc = f"第{i+1}步 R² = {r2:.3f}"
                    if delta_r2 is not None:
                        step_desc += f", ΔR² = {delta_r2:.3f}"
                        card.effect_sizes.append({"name": f"ΔR² (Step {i+1})", "value": float(delta_r2)})
                    if f_change is not None and p_change is not None:
                        step_desc += f", F变化 = {f_change:.3f}, p = {p_change:.3f}"
                    parts.append(step_desc)
    elif final_r2 is not None:
        parts.append(f"最终模型 R² = {final_r2:.3f}")
        card.effect_sizes.append({"name": "R²", "value": float(final_r2)})
        if final_adj_r2 is not None:
            parts.append(f"调整 R² = {final_adj_r2:.3f}")

    card.apa_text = "；".join(parts) + "。"
    card.plain_language_summary = f"通过分步加入预测变量，分析了对{dv}的逐步解释力变化。"


def _build_logistic_regression(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("Logistic 回归未产生结果")
        return

    chi2 = getattr(result, "chi2", None) or getattr(result, "model_chi2", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    pseudo_r2 = getattr(result, "pseudo_r2", None) or getattr(result, "nagelkerke_r2", None)
    accuracy = getattr(result, "accuracy", None) or getattr(result, "classification_accuracy", None)
    odds_ratios = getattr(result, "odds_ratios", None) or getattr(result, "OR", None)

    dv = card.variables.get("dependent", ["因变量"])[0]
    ivs = card.variables.get("independent", ["预测变量"])

    if chi2 is not None or pseudo_r2 is not None:
        apa = f"二元 Logistic 回归分析以{dv}为结局变量"
        if chi2 is not None and p_val is not None:
            sig = "显著" if p_val < 0.05 else "不显著"
            apa += f"，模型{sig}（χ² = {chi2:.3f}, p = {p_val:.3f}）"
        if pseudo_r2 is not None:
            apa += f", Nagelkerke R² = {pseudo_r2:.3f}"
            card.effect_sizes.append({"name": "Nagelkerke R²", "value": float(pseudo_r2)})
        if accuracy is not None:
            apa += f"，分类正确率 {accuracy*100:.1f}%"
        card.apa_text = apa + "。"

        if odds_ratios and hasattr(odds_ratios, '__iter__'):
            or_parts = []
            for name, or_val in (odds_ratios.items() if isinstance(odds_ratios, dict) else enumerate(odds_ratios)):
                if isinstance(or_val, (int, float)):
                    or_parts.append(f"{name}: OR = {or_val:.3f}")
            if or_parts:
                card.technical_notes.append("优势比：" + "；".join(or_parts[:5]))

        card.plain_language_summary = f"分析了预测变量对{dv}（二分类）的预测效果。"
    else:
        card.warnings.append("Logistic 回归结果缺少关键统计量")


def _build_mcdonalds_omega(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("McDonald's ω 分析未产生结果")
        return

    omega = getattr(result, "omega", None) or getattr(result, "omega_total", None)
    omega_h = getattr(result, "omega_hierarchical", None) or getattr(result, "omega_h", None)
    n_items = getattr(result, "n_items", None) or getattr(result, "num_items", None)
    alpha = getattr(result, "alpha", None)

    if omega is not None:
        level = "良好" if omega >= 0.8 else ("可接受" if omega >= 0.7 else "偏低")
        apa = f"McDonald's ω 信度分析结果为 ω = {omega:.3f}"
        if n_items is not None:
            apa += f"（{n_items} 个题项）"
        apa += f"，组合信度{level}"
        if omega_h is not None:
            apa += f"；层级 ω_h = {omega_h:.3f}"
            card.effect_sizes.append({"name": "ω_h", "value": float(omega_h)})
        if alpha is not None:
            apa += f"（对比 Cronbach's α = {alpha:.3f}）"
        card.apa_text = apa + "。"
        card.effect_sizes.append({"name": "McDonald's ω", "value": float(omega)})
        card.plain_language_summary = f"量表组合信度为 {omega:.3f}，{'达到' if omega >= 0.7 else '未达到'}可接受标准（0.70）。"
        if omega < 0.7:
            card.warnings.append("McDonald's ω 低于 0.70，建议检查量表结构")
    else:
        card.warnings.append("McDonald's ω 结果缺少 ω 值")


def _build_efa(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("探索性因素分析未产生结果")
        return

    kmo = getattr(result, "kmo", None) or getattr(result, "kmo_value", None)
    bartlett_p = getattr(result, "bartlett_p", None) or getattr(result, "bartlett_pvalue", None)
    n_factors = getattr(result, "n_factors", None) or getattr(result, "num_factors", None)
    variance_explained = getattr(result, "variance_explained", None) or getattr(result, "total_variance", None)
    loadings = getattr(result, "loadings", None) or getattr(result, "factor_loadings", None)

    parts = ["探索性因素分析（EFA）结果："]

    if kmo is not None:
        kmo_level = "优秀" if kmo >= 0.9 else ("良好" if kmo >= 0.8 else ("中等" if kmo >= 0.7 else ("勉强" if kmo >= 0.6 else "不适合")))
        parts.append(f"KMO = {kmo:.3f}（{kmo_level}）")
        card.effect_sizes.append({"name": "KMO", "value": float(kmo)})
        if kmo < 0.6:
            card.warnings.append("KMO 值过低，数据可能不适合进行因素分析")

    if bartlett_p is not None:
        sig = "显著" if bartlett_p < 0.05 else "不显著"
        parts.append(f"Bartlett 球形检验{sig}（p = {bartlett_p:.4f}）")
        if bartlett_p >= 0.05:
            card.warnings.append("Bartlett 检验不显著，变量间可能缺乏足够相关")

    if n_factors is not None:
        parts.append(f"提取 {n_factors} 个因子")
        if variance_explained is not None:
            total_var = variance_explained if isinstance(variance_explained, (int, float)) else sum(variance_explained)
            parts.append(f"累计解释方差 {total_var:.1f}%")
            card.effect_sizes.append({"name": "累计方差解释率", "value": float(total_var)})

    card.apa_text = "，".join(parts) + "。"
    card.plain_language_summary = f"因素分析探索了量表的潜在结构，" + (f"发现 {n_factors} 个因子。" if n_factors else "结果待确认。")

    if loadings is not None:
        card.technical_notes.append("因子载荷矩阵已生成，建议检查各条目的载荷分布")


def _build_one_sample_ttest(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("单样本 t 检验未产生结果")
        return

    t_val = getattr(result, "t_statistic", None) or getattr(result, "t", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    df = getattr(result, "df", None) or getattr(result, "dof", None)
    d = getattr(result, "cohens_d", None) or getattr(result, "effect_size", None)
    test_value = getattr(result, "test_value", None) or getattr(result, "mu", None) or 0

    dv = card.variables.get("dependent", ["因变量"])[0]

    if t_val is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"单样本 t 检验结果表明，{dv}与检验值({test_value})差异{sig}"
        if df is not None:
            apa += f"，t({df:.0f}) = {t_val:.3f}, p = {p_val:.3f}"
        else:
            apa += f"，t = {t_val:.3f}, p = {p_val:.3f}"
        if d is not None:
            apa += f", Cohen's d = {d:.3f}"
            card.effect_sizes.append({"name": "Cohen's d", "value": float(d)})
        card.apa_text = apa + "。"
        card.plain_language_summary = f"样本在{dv}上的均值与检验值({test_value}){'存在显著差异' if p_val < 0.05 else '无显著差异'}。"
    else:
        card.warnings.append("单样本 t 检验结果缺少关键统计量")

    if not card.effect_sizes:
        card.warnings.append("缺少效应量（Cohen's d），建议补充")


def _build_spearman_corr(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("Spearman 秩相关分析未产生结果")
        return

    r_s = getattr(result, "r_s", None) or getattr(result, "rho", None) or getattr(result, "correlation", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    n = getattr(result, "n", None) or getattr(result, "sample_size", None)

    dvs = card.variables.get("dependent", ["变量1", "变量2"])
    var1 = dvs[0] if len(dvs) > 0 else "变量1"
    var2 = dvs[1] if len(dvs) > 1 else "变量2"

    if r_s is not None and p_val is not None:
        abs_r = abs(r_s)
        strength = "强" if abs_r > 0.5 else ("中等" if abs_r >= 0.3 else "弱")
        direction = "正" if r_s > 0 else "负"
        apa = f"Spearman 秩相关分析表明，{var1}与{var2}之间存在{strength}{direction}相关"
        apa += f"，r_s = {r_s:.3f}, p = {p_val:.3f}"
        if n is not None:
            apa += f", N = {n}"
        card.apa_text = apa + "。"
        card.effect_sizes.append({"name": "r_s", "value": float(r_s)})
        card.effect_sizes.append({"name": "r_s²", "value": float(r_s ** 2)})
        card.plain_language_summary = f"{var1}和{var2}之间呈{strength}{direction}相关关系（{'显著' if p_val < 0.05 else '不显著'}）。"
    else:
        card.warnings.append("Spearman 秩相关结果缺少关键统计量")


def _build_partial_corr(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("偏相关分析未产生结果")
        return

    r_val = getattr(result, "r", None) or getattr(result, "partial_r", None) or getattr(result, "correlation", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    df = getattr(result, "df", None) or getattr(result, "dof", None)
    control_vars = getattr(result, "control_vars", None) or getattr(result, "covariates", None)

    dvs = card.variables.get("dependent", ["变量1", "变量2"])
    var1 = dvs[0] if len(dvs) > 0 else "变量1"
    var2 = dvs[1] if len(dvs) > 1 else "变量2"
    covariates = card.variables.get("covariates", [])

    if control_vars is None:
        control_vars = covariates
    control_str = ", ".join(control_vars) if control_vars else "控制变量"

    if r_val is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"在控制{control_str}后，{var1}与{var2}的偏相关为 r = {r_val:.3f}, p = {p_val:.3f}"
        if df is not None:
            apa += f", df = {df}"
        card.apa_text = apa + "。"
        card.effect_sizes.append({"name": "partial r", "value": float(r_val)})
        card.plain_language_summary = f"控制{control_str}后，{var1}与{var2}的相关{'显著' if p_val < 0.05 else '不显著'}（偏相关 r = {r_val:.3f}）。"
    else:
        card.warnings.append("偏相关分析结果缺少关键统计量")


def _build_chi_square(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("卡方检验未产生结果")
        return

    chi2 = getattr(result, "chi2", None) or getattr(result, "chi_square", None) or getattr(result, "statistic", None)
    p_val = getattr(result, "p_value", None) or getattr(result, "p", None)
    df = getattr(result, "df", None) or getattr(result, "dof", None)
    cramers_v = getattr(result, "cramers_v", None) or getattr(result, "effect_size", None)

    ivs = card.variables.get("independent", ["变量"])
    dvs = card.variables.get("dependent", ["变量"])

    if chi2 is not None and p_val is not None:
        sig = "显著" if p_val < 0.05 else "不显著"
        apa = f"卡方检验结果显示，变量间关联{sig}"
        if df is not None:
            apa += f"，χ²({df}) = {chi2:.3f}, p = {p_val:.3f}"
        else:
            apa += f"，χ² = {chi2:.3f}, p = {p_val:.3f}"
        if cramers_v is not None:
            v = float(cramers_v)
            v_level = "大" if v > 0.5 else ("中" if v >= 0.3 else ("小" if v >= 0.1 else "微弱"))
            apa += f", Cramér's V = {v:.3f}（效应量{v_level}）"
            card.effect_sizes.append({"name": "Cramér's V", "value": v})
        card.apa_text = apa + "。"
        card.plain_language_summary = f"变量间的关联{'达到统计显著水平' if p_val < 0.05 else '未达到统计显著水平'}。"
    else:
        card.warnings.append("卡方检验结果缺少关键统计量")

    if not card.effect_sizes:
        card.warnings.append("缺少效应量（Cramér's V），建议补充")


def _build_cfa(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("验证性因子分析未产生结果")
        return

    fit_indices = getattr(result, "fit_indices", None) or getattr(result, "fit", None)
    if fit_indices is None:
        # Try extracting individual attributes
        fit_indices = {}
        for key in ("chi2", "df", "p", "CFI", "TLI", "RMSEA", "SRMR",
                    "cfi", "tli", "rmsea", "srmr", "p_value"):
            val = getattr(result, key, None)
            if val is not None:
                fit_indices[key] = val

    if not fit_indices:
        card.warnings.append("验证性因子分析结果缺少拟合指标")
        return

    if isinstance(fit_indices, dict):
        chi2 = fit_indices.get("chi2", fit_indices.get("chi_square"))
        df = fit_indices.get("df")
        p_val = fit_indices.get("p", fit_indices.get("p_value"))
        cfi = fit_indices.get("CFI", fit_indices.get("cfi"))
        tli = fit_indices.get("TLI", fit_indices.get("tli"))
        rmsea = fit_indices.get("RMSEA", fit_indices.get("rmsea"))
        srmr = fit_indices.get("SRMR", fit_indices.get("srmr"))
    else:
        card.warnings.append("拟合指标格式无法解析")
        return

    parts = ["验证性因子分析模型拟合指标："]
    if chi2 is not None and df is not None:
        chi_part = f"χ²({df}) = {chi2:.3f}"
        if p_val is not None:
            chi_part += f", p = {p_val:.3f}"
        parts.append(chi_part)
    if cfi is not None:
        parts.append(f"CFI = {cfi:.3f}")
        card.effect_sizes.append({"name": "CFI", "value": float(cfi)})
    if tli is not None:
        parts.append(f"TLI = {tli:.3f}")
        card.effect_sizes.append({"name": "TLI", "value": float(tli)})
    if rmsea is not None:
        parts.append(f"RMSEA = {rmsea:.3f}")
        card.effect_sizes.append({"name": "RMSEA", "value": float(rmsea)})
    if srmr is not None:
        parts.append(f"SRMR = {srmr:.3f}")
        card.effect_sizes.append({"name": "SRMR", "value": float(srmr)})

    card.apa_text = "，".join(parts) + "。"

    # Evaluate model fit
    fit_acceptable = True
    if cfi is not None and cfi < 0.90:
        fit_acceptable = False
    if rmsea is not None and rmsea > 0.08:
        fit_acceptable = False

    if fit_acceptable and (cfi is not None or rmsea is not None):
        card.plain_language_summary = "模型拟合可接受，验证性因子分析支持预设的因子结构。"
    else:
        card.plain_language_summary = "模型拟合不佳，建议修正模型或检查因子结构。"
        card.warnings.append("模型拟合不佳（CFI < 0.90 或 RMSEA > 0.08），建议修正")


def _build_sem(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("结构方程模型未产生结果")
        return

    fit_indices = getattr(result, "fit_indices", None) or getattr(result, "fit", None)
    path_coefficients = getattr(result, "path_coefficients", None) or getattr(result, "paths", None)

    if fit_indices is None:
        fit_indices = {}
        for key in ("chi2", "df", "p", "CFI", "TLI", "RMSEA", "SRMR",
                    "cfi", "tli", "rmsea", "srmr", "p_value"):
            val = getattr(result, key, None)
            if val is not None:
                fit_indices[key] = val

    # Build fit indices part
    parts = ["结构方程模型（SEM）分析结果："]

    if isinstance(fit_indices, dict) and fit_indices:
        chi2 = fit_indices.get("chi2", fit_indices.get("chi_square"))
        df = fit_indices.get("df")
        p_val = fit_indices.get("p", fit_indices.get("p_value"))
        cfi = fit_indices.get("CFI", fit_indices.get("cfi"))
        tli = fit_indices.get("TLI", fit_indices.get("tli"))
        rmsea = fit_indices.get("RMSEA", fit_indices.get("rmsea"))
        srmr = fit_indices.get("SRMR", fit_indices.get("srmr"))

        fit_parts = []
        if chi2 is not None and df is not None:
            chi_part = f"χ²({df}) = {chi2:.3f}"
            if p_val is not None:
                chi_part += f", p = {p_val:.3f}"
            fit_parts.append(chi_part)
        if cfi is not None:
            fit_parts.append(f"CFI = {cfi:.3f}")
            card.effect_sizes.append({"name": "CFI", "value": float(cfi)})
        if tli is not None:
            fit_parts.append(f"TLI = {tli:.3f}")
            card.effect_sizes.append({"name": "TLI", "value": float(tli)})
        if rmsea is not None:
            fit_parts.append(f"RMSEA = {rmsea:.3f}")
            card.effect_sizes.append({"name": "RMSEA", "value": float(rmsea)})
        if srmr is not None:
            fit_parts.append(f"SRMR = {srmr:.3f}")
            card.effect_sizes.append({"name": "SRMR", "value": float(srmr)})

        if fit_parts:
            parts.append("拟合指标——" + "，".join(fit_parts))

        # Evaluate model fit
        fit_acceptable = True
        if cfi is not None and cfi < 0.90:
            fit_acceptable = False
        if rmsea is not None and rmsea > 0.08:
            fit_acceptable = False
        if not fit_acceptable:
            card.warnings.append("SEM 模型拟合不佳（CFI < 0.90 或 RMSEA > 0.08），建议修正")
    else:
        card.warnings.append("结构方程模型缺少拟合指标")

    # Path coefficients
    if path_coefficients and hasattr(path_coefficients, '__iter__'):
        path_parts = []
        for path in path_coefficients:
            if isinstance(path, dict):
                from_var = path.get("from", path.get("predictor", "?"))
                to_var = path.get("to", path.get("outcome", "?"))
                beta = path.get("beta", path.get("estimate", path.get("coef")))
                p = path.get("p", path.get("p_value"))
                if beta is not None:
                    p_str = f"p = {p:.3f}" if p is not None else ""
                    path_parts.append(f"{from_var} → {to_var}: β = {beta:.3f}" + (f", {p_str}" if p_str else ""))
        if path_parts:
            parts.append("路径系数——" + "；".join(path_parts))
            card.technical_notes.append(f"共估计 {len(path_parts)} 条路径")

    card.apa_text = "。".join(parts) + "。"
    card.plain_language_summary = "结构方程模型检验了变量间的假设路径关系。"


def _build_ave_cr(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("AVE/CR 分析未产生结果")
        return

    constructs = getattr(result, "constructs", None) or getattr(result, "factors", None)

    if not constructs or not hasattr(constructs, '__iter__'):
        card.warnings.append("AVE/CR 结果缺少构念数据")
        return

    parts = ["平均方差抽取量（AVE）与组合信度（CR）分析结果："]
    all_valid = True

    for construct in constructs:
        if isinstance(construct, dict):
            name = construct.get("name", "未知构念")
            ave = construct.get("AVE", construct.get("ave"))
            cr = construct.get("CR", construct.get("cr"))

            if ave is not None and cr is not None:
                valid = cr >= 0.7 and ave >= 0.5
                status = "良好" if valid else "不达标"
                parts.append(f"{name}：CR = {cr:.3f}, AVE = {ave:.3f}（{status}）")
                card.effect_sizes.append({"name": f"CR ({name})", "value": float(cr)})
                card.effect_sizes.append({"name": f"AVE ({name})", "value": float(ave)})
                if not valid:
                    all_valid = False
                    if cr < 0.7:
                        card.warnings.append(f"{name} 的组合信度 CR = {cr:.3f} < 0.70，聚合效度不足")
                    if ave < 0.5:
                        card.warnings.append(f"{name} 的 AVE = {ave:.3f} < 0.50，聚合效度不足")

    card.apa_text = "；".join(parts) + "。"
    if all_valid:
        card.plain_language_summary = "所有构念的聚合效度良好（CR ≥ 0.70 且 AVE ≥ 0.50）。"
    else:
        card.plain_language_summary = "部分构念的聚合效度未达标，建议检查测量模型。"


def _build_discriminant_validity(card: AnalysisResultCard, output: dict):
    result = output.get("result")
    if not result:
        card.warnings.append("区分效度分析未产生结果")
        return

    htmt_matrix = getattr(result, "htmt_matrix", None) or getattr(result, "htmt", None)
    ave_sqrt_vs_corr = getattr(result, "ave_sqrt_vs_corr", None) or getattr(result, "fornell_larcker", None)

    if htmt_matrix is not None:
        # HTMT criterion
        parts = ["区分效度分析（HTMT 准则）结果："]
        all_pass = True

        if isinstance(htmt_matrix, dict):
            for pair, value in htmt_matrix.items():
                if isinstance(value, (int, float)):
                    status = "通过" if value < 0.85 else "未通过"
                    parts.append(f"{pair}: HTMT = {value:.3f}（{status}）")
                    if value >= 0.85:
                        all_pass = False
                        card.warnings.append(f"{pair} 的 HTMT = {value:.3f} ≥ 0.85，区分效度不足")
        elif hasattr(htmt_matrix, '__iter__'):
            for item in htmt_matrix:
                if isinstance(item, dict):
                    pair = item.get("pair", item.get("constructs", "?"))
                    value = item.get("htmt", item.get("value"))
                    if value is not None:
                        status = "通过" if value < 0.85 else "未通过"
                        parts.append(f"{pair}: HTMT = {value:.3f}（{status}）")
                        if value >= 0.85:
                            all_pass = False
                            card.warnings.append(f"{pair} 的 HTMT = {value:.3f} ≥ 0.85，区分效度不足")

        card.apa_text = "；".join(parts) + "。"
        if all_pass:
            card.plain_language_summary = "所有构念间的 HTMT 值均 < 0.85，区分效度良好。"
        else:
            card.plain_language_summary = "部分构念间区分效度不足（HTMT ≥ 0.85），建议合并或修正模型。"

    elif ave_sqrt_vs_corr is not None:
        # Fornell-Larcker criterion
        parts = ["区分效度分析（Fornell-Larcker 准则）结果："]
        all_pass = True

        if isinstance(ave_sqrt_vs_corr, dict):
            for construct, info in ave_sqrt_vs_corr.items():
                if isinstance(info, dict):
                    sqrt_ave = info.get("sqrt_ave", info.get("sqrt_AVE"))
                    max_corr = info.get("max_corr", info.get("max_correlation"))
                    if sqrt_ave is not None and max_corr is not None:
                        passed = sqrt_ave > max_corr
                        status = "通过" if passed else "未通过"
                        parts.append(f"{construct}: √AVE = {sqrt_ave:.3f}, 最大相关 = {max_corr:.3f}（{status}）")
                        if not passed:
                            all_pass = False
                            card.warnings.append(f"{construct} 的 √AVE < 与其他构念的最大相关，区分效度不足")

        card.apa_text = "；".join(parts) + "。"
        if all_pass:
            card.plain_language_summary = "Fornell-Larcker 准则满足，各构念区分效度良好。"
        else:
            card.plain_language_summary = "部分构念未满足 Fornell-Larcker 准则，区分效度不足。"
    else:
        card.warnings.append("区分效度分析缺少 HTMT 矩阵或 Fornell-Larcker 数据")
        card.apa_text = "区分效度分析数据不足，无法判定。"
        card.plain_language_summary = "缺少区分效度所需的数据，建议补充 HTMT 或 AVE/相关矩阵。"


def _build_hlm(card: AnalysisResultCard, output: dict):
    """多层线性模型（HLM / 混合效应模型）结果卡构建。"""
    result = output.get("result")
    if not result:
        card.warnings.append("多层线性模型未产生结果")
        return

    # Model type
    model_type = getattr(result, "model_type", None) or getattr(result, "hlm_type", "random_intercept")

    # Basic structure
    n_groups = getattr(result, "n_groups", None) or getattr(result, "groups", None)
    avg_group_size = getattr(result, "avg_group_size", None) or getattr(result, "mean_group_size", None)
    group_var_name = getattr(result, "group_var", None) or getattr(result, "cluster_var", None)

    # ICC
    icc = getattr(result, "icc", None) or getattr(result, "intraclass_correlation", None)

    # Fixed effects
    fixed_effects = getattr(result, "fixed_effects", None) or getattr(result, "coefficients", None)

    # Random effects
    group_variance = getattr(result, "group_variance", None) or getattr(result, "random_intercept_var", None)
    residual_variance = getattr(result, "residual_variance", None) or getattr(result, "residual_var", None)

    # Fit indices
    aic = getattr(result, "aic", None) or getattr(result, "AIC", None)
    bic = getattr(result, "bic", None) or getattr(result, "BIC", None)

    # OLS fallback flag
    ols_fallback = getattr(result, "ols_fallback", False) or getattr(result, "used_ols", False)

    # Variables
    dv = card.variables.get("dependent", ["因变量"])[0]
    ivs = card.variables.get("independent", ["预测变量"])
    grouping = group_var_name or card.variables.get("covariates", ["分组变量"])[0] if card.variables.get("covariates") else "分组变量"

    # Build APA text
    model_type_zh = "随机截距模型" if "intercept" in str(model_type) else "随机斜率模型"
    parts = [f"多层线性模型（{model_type_zh}）分析结果："]

    if n_groups is not None:
        parts.append(f"分组变量 {grouping}（{n_groups} 组")
        if avg_group_size is not None:
            parts[-1] += f"，平均每组 {avg_group_size:.1f} 人"
        parts[-1] += "）"

    if icc is not None:
        icc_val = float(icc)
        parts.append(f"ICC = {icc_val:.3f}")
        card.effect_sizes.append({"name": "ICC", "value": icc_val})
        if icc_val < 0.05:
            card.warnings.append(f"ICC = {icc_val:.3f} 很低，组间差异微小，OLS 近似可能已足够")

    # Fixed effects reporting
    if fixed_effects is not None:
        fe_parts = []
        if isinstance(fixed_effects, dict):
            for name, info in fixed_effects.items():
                if isinstance(info, dict):
                    est = info.get("estimate", info.get("coef", info.get("b")))
                    se = info.get("se", info.get("SE", info.get("std_err")))
                    t_val = info.get("t", info.get("t_value"))
                    p_val = info.get("p", info.get("p_value"))
                    if est is not None:
                        fe_str = f"{name}: b = {est:.3f}"
                        if se is not None:
                            fe_str += f", SE = {se:.3f}"
                        if t_val is not None:
                            fe_str += f", t = {t_val:.3f}"
                        if p_val is not None:
                            fe_str += f", p = {p_val:.3f}"
                        fe_parts.append(fe_str)
                elif isinstance(info, (int, float)):
                    fe_parts.append(f"{name}: b = {info:.3f}")
        elif hasattr(fixed_effects, '__iter__'):
            for fe in fixed_effects:
                if isinstance(fe, dict):
                    name = fe.get("name", fe.get("term", "?"))
                    est = fe.get("estimate", fe.get("coef", fe.get("b")))
                    se = fe.get("se", fe.get("SE"))
                    t_val = fe.get("t", fe.get("t_value"))
                    p_val = fe.get("p", fe.get("p_value"))
                    if est is not None:
                        fe_str = f"{name}: b = {est:.3f}"
                        if se is not None:
                            fe_str += f", SE = {se:.3f}"
                        if t_val is not None:
                            fe_str += f", t = {t_val:.3f}"
                        if p_val is not None:
                            fe_str += f", p = {p_val:.3f}"
                        fe_parts.append(fe_str)
        if fe_parts:
            parts.append("固定效应——" + "；".join(fe_parts))

    # Random effects reporting
    re_parts = []
    if group_variance is not None:
        re_parts.append(f"组间方差 = {group_variance:.4f}（SD = {group_variance**0.5:.4f}）")
    if residual_variance is not None:
        re_parts.append(f"残差方差 = {residual_variance:.4f}（SD = {residual_variance**0.5:.4f}）")
    if re_parts:
        parts.append("随机效应——" + "；".join(re_parts))

    # Fit indices
    fit_parts = []
    if aic is not None:
        fit_parts.append(f"AIC = {aic:.1f}")
    if bic is not None:
        fit_parts.append(f"BIC = {bic:.1f}")
    if fit_parts:
        parts.append("模型拟合——" + "，".join(fit_parts))

    if ols_fallback:
        parts.append("（注：因 ICC 过低已退化为 OLS 近似）")
        card.warnings.append("模型已 fallback 到 OLS 近似（ICC 过低，多层结构意义不大）")

    card.apa_text = "。".join(parts) + "。"

    # Plain language summary
    if icc is not None:
        icc_pct = float(icc) * 100
        card.plain_language_summary = (
            f"在{dv}的总变异中，约 {icc_pct:.1f}% 可归因于{grouping}间的差异"
            f"（{model_type_zh}）。"
        )
    else:
        card.plain_language_summary = f"多层线性模型分析了{dv}在不同{grouping}间的变异来源。"

    # Warnings
    if n_groups is not None and n_groups < 10:
        card.warnings.append(f"分组数仅 {n_groups}，建议至少 20 组以保证随机效应估计稳定")
    if avg_group_size is not None and avg_group_size < 5:
        card.warnings.append(f"平均组大小仅 {avg_group_size:.1f}，组内样本过少可能影响估计精度")


def _generic_card(card: AnalysisResultCard, output: dict):
    """通用 fallback：从 result 属性中提取基本信息。"""
    result = output.get("result")
    if result:
        card.technical_notes.append(f"结果对象类型: {type(result).__name__}")


_CARD_BUILDERS = {
    "descriptive": _build_descriptive,
    "independent_ttest": _build_independent_ttest,
    "paired_ttest": _build_paired_ttest,
    "one_way_anova": _build_one_way_anova,
    "pearson_correlation": _build_pearson_corr,
    "pearson_corr": _build_pearson_corr,
    "multiple_regression": _build_multiple_regression,
    "repeated_anova": _build_repeated_anova,
    "repeated_measures_anova": _build_repeated_anova,
    "mediation": _build_mediation,
    "moderation": _build_moderation,
    "cronbach_alpha": _build_cronbach_alpha,
    "two_way_anova": _build_two_way_anova,
    "factorial_anova": _build_two_way_anova,
    "mixed_anova": _build_mixed_anova,
    "ancova": _build_ancova,
    "mann_whitney": _build_mann_whitney,
    "mann_whitney_u": _build_mann_whitney,
    "wilcoxon": _build_wilcoxon,
    "wilcoxon_signed_rank": _build_wilcoxon,
    "kruskal_wallis": _build_kruskal_wallis,
    "hierarchical_regression": _build_hierarchical_regression,
    "logistic_regression": _build_logistic_regression,
    "binary_logistic": _build_logistic_regression,
    "mcdonalds_omega": _build_mcdonalds_omega,
    "omega": _build_mcdonalds_omega,
    "efa": _build_efa,
    "exploratory_factor_analysis": _build_efa,
    "one_sample_ttest": _build_one_sample_ttest,
    "spearman_corr": _build_spearman_corr,
    "spearman_correlation": _build_spearman_corr,
    "partial_corr": _build_partial_corr,
    "partial_correlation": _build_partial_corr,
    "chi_square": _build_chi_square,
    "chi_square_test": _build_chi_square,
    "cfa": _build_cfa,
    "confirmatory_factor_analysis": _build_cfa,
    "sem": _build_sem,
    "structural_equation_model": _build_sem,
    "ave_cr": _build_ave_cr,
    "discriminant_validity": _build_discriminant_validity,
    "hlm": _build_hlm,
    "hierarchical_linear_model": _build_hlm,
    "mixed_effects": _build_hlm,
}
