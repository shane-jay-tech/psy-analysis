"""分析调度器：AnalysisPlan → 执行统计检验 → 返回结构化结果
使用注册表模式（Registry Pattern）替代 if/elif 分支。
"""

import hashlib
import json
import time
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Callable, Optional

from src.parser.intent_resolver import AnalysisPlan
from src.output.reasoning import generate_reasoning
from src.utils.friendly_errors import friendly_explain
from . import assumptions
from . import descriptive
from . import ttest
from . import anova
from . import correlation
from . import chi_square
from . import nonparametric
from . import regression
from . import logistic_regression
from . import manova as manova_mod
from . import hlm as hlm_mod
from . import sem as sem_mod
from . import reliability
from . import factor_analysis
from . import advanced
from . import validity
from . import assumption_router
from . import post_hoc_power as _post_hoc_power
from .data_quality import data_quality_check, DataQualityReport, handle_missing


# ===========================================================================
# 注册表：test_type → handler(df, plan, output)
# ===========================================================================
AnalysisRegistry: Dict[str, Callable] = {}


def _register(test_type: str):
    """装饰器：将函数注册到 AnalysisRegistry"""
    def decorator(func: Callable):
        AnalysisRegistry[test_type] = func
        return func
    return decorator


@_register("descriptive")
def _run_descriptive(df, plan, output):
    dv_cols = plan.dependent_vars
    if not dv_cols:
        dv_cols = df.select_dtypes(include=["number"]).columns.tolist()
    desc_df = descriptive.descriptive_stats(df, dv_cols)
    output["descriptive"] = desc_df
    output["charts_data"]["bar_data"] = desc_df
    output["charts_data"]["histogram_cols"] = dv_cols[:5]


# ==================== t检验 ====================

@_register("independent_ttest")
def _run_independent_ttest(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    iv = plan.independent_vars[0] if plan.independent_vars else None
    if not dv or not iv:
        output["errors"].append({"severity": "error", "message": "独立样本t检验需要指定一个因变量和一个分组变量。"})
        return
    output["descriptive"] = descriptive.grouped_descriptive(df, dv, iv)
    groups = {}
    for name, g in df.groupby(iv):
        groups[str(name)] = pd.to_numeric(g[dv], errors="coerce").dropna()
    output["assumptions"]["normality"] = assumptions.check_normality_groups(groups)
    result = ttest.independent_ttest(df, dv, iv)
    output["result"] = result
    output["charts_data"]["box_data"] = {"dv": dv, "iv": iv}
    output["charts_data"]["bar_data"] = result.group_stats


@_register("paired_ttest")
def _run_paired_ttest(df, plan, output):
    if len(plan.dependent_vars) < 2:
        output["errors"].append({"severity": "error", "message": "配对样本t检验需要指定两个测量变量。"})
        return
    col1, col2 = plan.dependent_vars[0], plan.dependent_vars[1]
    result = ttest.paired_ttest(df, col1, col2)
    output["result"] = result
    output["descriptive"] = result.group_stats
    output["charts_data"]["paired_cols"] = (col1, col2)


@_register("one_sample_ttest")
def _run_one_sample_ttest(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    test_value = plan.test_value if plan.test_value is not None else 0
    if not dv:
        output["errors"].append({"severity": "error", "message": "单样本t检验需要指定一个因变量和检验值。"})
        return
    result = ttest.one_sample_ttest(df, dv, test_value)
    output["result"] = result
    output["descriptive"] = result.group_stats


# ==================== ANOVA ====================

@_register("one_way_anova")
def _run_one_way_anova(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    iv = plan.independent_vars[0] if plan.independent_vars else None
    if not dv or not iv:
        output["errors"].append({"severity": "error", "message": "单因素方差分析需要指定一个因变量和一个分组变量。"})
        return
    output["descriptive"] = descriptive.grouped_descriptive(df, dv, iv)
    result = anova.one_way_anova(df, dv, iv)
    output["result"] = result
    output["assumptions"]["homogeneity"] = result.assumption_homogeneity
    output["charts_data"]["box_data"] = {"dv": dv, "iv": iv}
    output["charts_data"]["anova_result"] = result


@_register("welch_anova")
def _run_welch_anova(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    iv = plan.independent_vars[0] if plan.independent_vars else None
    if not dv or not iv:
        output["errors"].append({"severity": "error", "message": "Welch ANOVA 需要指定一个因变量和一个分组变量。"})
        return
    output["descriptive"] = descriptive.grouped_descriptive(df, dv, iv)
    result = anova.welch_anova(df, dv, iv)
    output["result"] = result
    output["assumptions"]["homogeneity"] = result.assumption_homogeneity
    output["charts_data"]["box_data"] = {"dv": dv, "iv": iv}
    output["charts_data"]["anova_result"] = result


@_register("two_way_anova")
def _run_two_way_anova(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    ivs = plan.independent_vars[:2]
    if not dv or len(ivs) < 2:
        output["errors"].append({"severity": "error", "message": "双因素方差分析需要指定一个因变量和两个自变量。"})
        return
    result = anova.two_way_anova(df, dv, ivs[0], ivs[1])
    output["result"] = result
    output["charts_data"]["interaction_data"] = {"dv": dv, "iv1": ivs[0], "iv2": ivs[1]}


@_register("repeated_anova")
def _run_repeated_anova(df, plan, output):
    if len(plan.dependent_vars) < 2:
        output["errors"].append({"severity": "error", "message": "重复测量方差分析需要至少2个测量时间点。"})
        return
    result = anova.repeated_measures_anova(df, plan.dependent_vars)
    output["result"] = result
    output["charts_data"]["paired_cols"] = (plan.dependent_vars[0], plan.dependent_vars[1])


@_register("mixed_anova")
def _run_mixed_anova(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    ivs = plan.independent_vars
    if not dv or len(ivs) < 2:
        output["errors"].append({"severity": "error", "message": "混合设计ANOVA需要指定因变量、组间因子和组内因子。请用长格式数据，并指定 subject 列。"})
        return
    between = ivs[0]
    within = ivs[1]
    subject_col = plan.grouping_var or "subject"
    if subject_col not in df.columns:
        output["errors"].append({"severity": "error", "message": f"未找到被试ID列「{subject_col}」。请通过 grouping_var 指定被试标识列。"})
        return
    result = anova.mixed_anova(df, dv, within=within, subject=subject_col, between=between)
    output["result"] = result


# ==================== 相关分析 ====================

@_register("pearson_corr")
def _run_correlation(df, plan, output):
    cols = plan.dependent_vars
    result = correlation.correlation_matrix(df, cols, "pearson")
    output["result"] = result
    output["descriptive"] = descriptive.descriptive_stats(df, cols)
    output["charts_data"]["corr_matrix"] = result.corr_matrix
    output["charts_data"]["scatter_cols"] = cols[:5]


@_register("spearman_corr")
def _run_spearman_corr(df, plan, output):
    cols = plan.dependent_vars
    result = correlation.correlation_matrix(df, cols, "spearman")
    output["result"] = result
    output["descriptive"] = descriptive.descriptive_stats(df, cols)
    output["charts_data"]["corr_matrix"] = result.corr_matrix
    output["charts_data"]["scatter_cols"] = cols[:5]


@_register("partial_corr")
def _run_partial_corr(df, plan, output):
    cols = plan.dependent_vars
    if len(cols) < 3:
        output["errors"].append({"severity": "error", "message": "偏相关分析至少需要3个变量（2个分析变量 + 至少1个控制变量）。"})
        return
    result = correlation.partial_correlation(df, cols)
    output["result"] = result
    output["descriptive"] = descriptive.descriptive_stats(df, cols)
    output["charts_data"]["corr_matrix"] = result.corr_matrix


@_register("point_biserial")
def _run_point_biserial(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    iv = plan.independent_vars[0] if plan.independent_vars else None
    if not dv or not iv:
        output["errors"].append({"severity": "error", "message": "点二列相关需要指定一个连续变量和一个二分类变量。"})
        return
    result = correlation.point_biserial_corr(df, dv, iv)
    output["result"] = result
    output["descriptive"] = descriptive.grouped_descriptive(df, dv, iv)


# ==================== 卡方检验 ====================

@_register("chi_square_independence")
def _run_chi_square(df, plan, output):
    if len(plan.independent_vars) >= 2:
        col1, col2 = plan.independent_vars[0], plan.independent_vars[1]
    elif len(plan.independent_vars) >= 1 and len(plan.dependent_vars) >= 1:
        col1, col2 = plan.independent_vars[0], plan.dependent_vars[0]
    else:
        output["errors"].append({"severity": "error", "message": "卡方检验需要指定两个分类变量。"})
        return
    result = chi_square.chi_square_independence(df, col1, col2)
    output["result"] = result
    output["charts_data"]["contingency"] = result.contingency_table


@_register("chi_square_gof")
def _run_chi_square_gof(df, plan, output):
    if not plan.dependent_vars:
        output["errors"].append({"severity": "error", "message": "卡方拟合优度检验需要指定一个分类变量。"})
        return
    col = plan.dependent_vars[0]
    result = chi_square.chi_square_gof(df, col)
    output["result"] = result
    output["charts_data"]["contingency"] = result.contingency_table


# ==================== 回归分析 ====================

@_register("linear_regression")
def _run_linear_regression(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    iv = plan.independent_vars[0] if plan.independent_vars else None
    if not dv or not iv:
        output["errors"].append({"severity": "error", "message": "线性回归需要指定一个因变量和一个自变量。"})
        return
    result = regression.linear_regression(df, dv, iv)
    output["result"] = result
    output["descriptive"] = descriptive.descriptive_stats(df, [dv, iv])
    output["charts_data"]["scatter_cols"] = [iv, dv]


@_register("multiple_regression")
def _run_multiple_regression(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    ivs = plan.independent_vars
    if not dv or len(ivs) < 2:
        output["errors"].append({"severity": "error", "message": "多元回归需要指定一个因变量和至少两个自变量。"})
        return
    result = regression.multiple_regression(df, dv, ivs)
    output["result"] = result
    output["descriptive"] = descriptive.descriptive_stats(df, [dv] + ivs)
    output["charts_data"]["scatter_cols"] = ([ivs[0], dv] if ivs else [])


@_register("hierarchical_regression")
def _run_hierarchical_regression(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    blocks = plan.blocks
    if not dv or not blocks or len(blocks) < 2:
        output["errors"].append({"severity": "error", "message": "层次回归需要指定一个因变量和至少2个变量块（blocks）。"})
        return
    result = regression.hierarchical_regression(df, dv, blocks)
    output["result"] = result
    all_ivs = [v for block in blocks for v in block]
    output["descriptive"] = descriptive.descriptive_stats(df, [dv] + all_ivs)


# ==================== Logistic 回归 ====================

@_register("binary_logistic")
def _run_binary_logistic(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    ivs = plan.independent_vars
    if not dv or not ivs:
        output["errors"].append({"severity": "error", "message": "二元Logistic回归需要指定一个二分类因变量和至少一个自变量。"})
        return
    result = logistic_regression.binary_logistic(df, dv, ivs)
    output["result"] = result
    output["descriptive"] = descriptive.descriptive_stats(df, ivs)


@_register("ordinal_logistic")
def _run_ordinal_logistic(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    ivs = plan.independent_vars
    if not dv or not ivs:
        output["errors"].append({"severity": "error", "message": "有序Logistic回归需要指定一个有序因变量和至少一个自变量。"})
        return
    result = logistic_regression.ordinal_logistic(df, dv, ivs)
    output["result"] = result
    output["descriptive"] = descriptive.descriptive_stats(df, ivs)


@_register("multinomial_logistic")
def _run_multinomial_logistic(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    ivs = plan.independent_vars
    if not dv or not ivs:
        output["errors"].append({"severity": "error", "message": "多项Logistic回归需要指定一个多分类因变量和至少一个自变量。"})
        return
    result = logistic_regression.multinomial_logistic(df, dv, ivs)
    output["result"] = result
    output["descriptive"] = descriptive.descriptive_stats(df, ivs)


# ==================== MANOVA ====================

@_register("manova")
def _run_manova(df, plan, output):
    dvs = plan.dependent_vars
    iv = plan.independent_vars[0] if plan.independent_vars else None
    if not dvs or len(dvs) < 2 or not iv:
        output["errors"].append({"severity": "error", "message": "MANOVA需要指定至少2个因变量和1个分组自变量。"})
        return
    covs = plan.covariates if plan.covariates else None
    result = manova_mod.manova(df, dvs, iv, covariates=covs)
    output["result"] = result
    output["descriptive"] = result.descriptive


# ==================== HLM 多层线性模型 ====================

@_register("hlm")
def _run_hlm(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    ivs = plan.independent_vars
    group_col = plan.grouping_var
    if not dv or not ivs or not group_col:
        output["errors"].append({"severity": "error", "message": "多层线性模型需要指定因变量、固定效应预测变量和分组变量（grouping_var，如班级/学校）。"})
        return
    if group_col not in df.columns:
        output["errors"].append({"severity": "error", "message": f"未找到分组列「{group_col}」。"})
        return
    result = hlm_mod.run_hlm(df, dv, group_col, ivs)
    output["result"] = result


# ==================== SEM 结构方程模型 ====================

@_register("sem")
def _run_sem(df, plan, output):
    factor_structure = getattr(plan, "factor_structure", None)
    structural_paths = getattr(plan, "structural_paths", None)
    if not factor_structure or not structural_paths:
        output["errors"].append({"severity": "error", "message": "SEM 需要指定因子结构（factor_structure）和结构路径（structural_paths，如 ['焦虑 ~ 自尊', '孤独 ~ 焦虑']）。"})
        return
    result = sem_mod.structural_equation_model(df, factor_structure, structural_paths)
    output["result"] = result


# ==================== 信度分析 ====================

@_register("cronbach_alpha")
def _run_cronbach_alpha(df, plan, output):
    items = plan.dependent_vars
    if len(items) < 2:
        output["errors"].append({"severity": "error", "message": "Cronbach's α 至少需要2道题目。"})
        return
    result = reliability.cronbach_alpha(df, items)
    output["result"] = result
    output["descriptive"] = result.item_stats


@_register("split_half")
def _run_split_half(df, plan, output):
    items = plan.dependent_vars
    if len(items) < 4:
        output["errors"].append({"severity": "error", "message": "分半信度至少需要4道题目（每半至少2道）。"})
        return
    result = reliability.split_half_reliability(df, items)
    output["result"] = result


@_register("mcdonald_omega")
def _run_mcdonald_omega(df, plan, output):
    items = plan.dependent_vars
    if len(items) < 3:
        output["errors"].append({"severity": "error", "message": "McDonald's ω 至少需要 3 道题目。"})
        return
    try:
        result = reliability.mcdonald_omega(df, items)
        output["result"] = result
        output["descriptive"] = descriptive.descriptive_stats(df, items)
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"McDonald's ω 计算失败：{e}"})


@_register("composite_reliability")
def _run_composite_reliability(df, plan, output):
    factor_structure = getattr(plan, "factor_structure", None)
    if not factor_structure or not isinstance(factor_structure, dict):
        output["errors"].append({
            "severity": "error",
            "message": "组合信度（CR）需要指定因子结构（哪些题目属于哪个因子）。",
        })
        return
    try:
        result = reliability.composite_reliability(df, factor_structure)
        output["result"] = result
        all_items = [it for items in factor_structure.values() for it in items]
        output["descriptive"] = descriptive.descriptive_stats(df, all_items)
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"CR 计算失败：{e}"})


@_register("icc")
def _run_icc(df, plan, output):
    raters = plan.rater_cols or plan.dependent_vars
    icc_type = getattr(plan, "icc_type", "ICC2")
    if len(raters) < 2:
        output["errors"].append({"severity": "error", "message": "ICC 至少需要 2 个评分者列。"})
        return
    try:
        result = reliability.intraclass_correlation(df, raters, icc_type=icc_type)
        output["result"] = result
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"ICC 计算失败：{e}"})


@_register("test_retest")
def _run_test_retest(df, plan, output):
    t1 = plan.time1_col or (plan.dependent_vars[0] if plan.dependent_vars else None)
    t2 = plan.time2_col or (plan.dependent_vars[1] if len(plan.dependent_vars) > 1 else None)
    if not t1 or not t2:
        output["errors"].append({
            "severity": "error",
            "message": "重测信度需要指定两次测量列（time1_col 与 time2_col）。",
        })
        return
    try:
        result = reliability.test_retest_reliability(df, t1, t2)
        output["result"] = result
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"重测信度计算失败：{e}"})


@_register("cohens_kappa")
def _run_cohens_kappa(df, plan, output):
    r1 = plan.rater1_col or (plan.dependent_vars[0] if plan.dependent_vars else None)
    r2 = plan.rater2_col or (plan.dependent_vars[1] if len(plan.dependent_vars) > 1 else None)
    if not r1 or not r2:
        output["errors"].append({
            "severity": "error",
            "message": "Cohen's κ 需要指定两个评分者列（rater1_col 与 rater2_col）。",
        })
        return
    try:
        result = reliability.cohens_kappa(df, r1, r2, weights=plan.kappa_weights)
        output["result"] = result
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"Cohen's κ 计算失败：{e}"})


@_register("fleiss_kappa")
def _run_fleiss_kappa(df, plan, output):
    raters = plan.rater_cols or plan.dependent_vars
    if len(raters) < 3:
        output["errors"].append({
            "severity": "error",
            "message": "Fleiss' κ 至少需要 3 个评分者。两人一致请用 Cohen's κ。",
        })
        return
    try:
        result = reliability.fleiss_kappa(df, raters)
        output["result"] = result
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"Fleiss' κ 计算失败：{e}"})


# ==================== 效度分析 ====================

@_register("cvi")
def _run_cvi(df, plan, output):
    """内容效度指数（CVI）。
    评分矩阵优先从 plan.expert_ratings（DataFrame）读取；
    若未提供，则尝试用主数据 df 中 plan.dependent_vars 列（每列=一位专家）。
    """
    ratings = plan.expert_ratings
    if ratings is None and plan.dependent_vars:
        ratings = df[plan.dependent_vars]
    if ratings is None or (hasattr(ratings, "empty") and ratings.empty):
        output["errors"].append({
            "severity": "error",
            "message": "CVI 需要专家评分矩阵：题目×专家（每格 1-4 分相关性评分）。",
        })
        return
    try:
        result = validity.content_validity_index(ratings)
        output["result"] = result
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"CVI 计算失败：{e}"})


@_register("ave")
def _run_ave(df, plan, output):
    """聚合效度（AVE）：基于 CFA 标准化载荷。"""
    factor_structure = getattr(plan, "factor_structure", None)
    if not factor_structure or not isinstance(factor_structure, dict):
        output["errors"].append({
            "severity": "error",
            "message": "AVE 需要指定因子结构（与 CFA 一致）。",
        })
        return
    try:
        from . import cfa as cfa_mod
        cfa_result = cfa_mod.confirmatory_factor_analysis(df, factor_structure)
        if cfa_result.loadings is None:
            output["errors"].append({
                "severity": "error",
                "message": "CFA 载荷估计失败，无法计算 AVE。请检查因子结构与样本量。",
            })
            return
        loadings_long = cfa_mod._extract_loadings_long(cfa_result.loadings, factor_structure)
        result = validity.average_variance_extracted(loadings_long)
        output["result"] = result
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"AVE 计算失败：{e}"})


@_register("discriminant_fl")
def _run_discriminant_fl(df, plan, output):
    """区分效度（Fornell-Larcker）：先跑 CFA 拿载荷与因子相关。"""
    factor_structure = getattr(plan, "factor_structure", None)
    if not factor_structure or len(factor_structure) < 2:
        output["errors"].append({
            "severity": "error",
            "message": "Fornell-Larcker 至少需要 2 个因子。",
        })
        return
    try:
        from . import cfa as cfa_mod
        cfa_result = cfa_mod.confirmatory_factor_analysis(df, factor_structure)
        if cfa_result.fl_matrix is not None:
            result = validity.ValidityResult(
                test_type="discriminant_fl",
                main_value=1.0 if cfa_result.discriminant_fl_pass else 0.0,
                detail=cfa_result.fl_matrix,
                interpretation="对角线为 √AVE，下三角为因子相关。√AVE 应大于该行/列因子相关。",
                warning="" if cfa_result.discriminant_fl_pass else "⚠ Fornell-Larcker 区分效度未通过。",
                fornell_larcker_pass=cfa_result.discriminant_fl_pass,
                n_cases=len(factor_structure),
            )
            output["result"] = result
        else:
            output["errors"].append({
                "severity": "error",
                "message": "Fornell-Larcker 矩阵生成失败，可能是 CFA 拟合失败。",
            })
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"Fornell-Larcker 计算失败：{e}"})


@_register("discriminant_htmt")
def _run_discriminant_htmt(df, plan, output):
    factor_structure = getattr(plan, "factor_structure", None)
    if not factor_structure or len(factor_structure) < 2:
        output["errors"].append({
            "severity": "error",
            "message": "HTMT 至少需要 2 个因子。",
        })
        return
    try:
        result = validity.discriminant_htmt(df, factor_structure)
        output["result"] = result
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"HTMT 计算失败：{e}"})


@_register("criterion_validity")
def _run_criterion_validity(df, plan, output):
    items = plan.dependent_vars
    crit = plan.criterion_col or (plan.independent_vars[0] if plan.independent_vars else None)
    kind = getattr(plan, "criterion_kind", "concurrent")
    if not items or not crit:
        output["errors"].append({
            "severity": "error",
            "message": "效标效度需要量表题目（dependent_vars）和外部效标列（criterion_col）。",
        })
        return
    try:
        result = validity.criterion_validity(df, items, crit, kind=kind)
        output["result"] = result
        output["charts_data"]["scatter_cols"] = [items[0], crit] if items else []
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"效标效度计算失败：{e}"})


# ==================== AI 题目预审（v3.8） ====================

@_register("ai_item_review")
def _run_ai_item_review(df, plan, output):
    """AI 模拟 4 位专家对题目相关性预审（**非正式 CVI**）。"""
    from src.questionnaire.ai_content_review import ai_content_review
    from src.llm_gateway import LLMUnavailableError

    # 题目源：textarea 文本优先；fallback 到 dependent_vars（即列头）
    items: list = []
    if plan.items_text and plan.items_text.strip():
        items = [ln.strip() for ln in plan.items_text.splitlines() if ln.strip()]
    elif plan.dependent_vars:
        items = list(plan.dependent_vars)

    if not items:
        output["errors"].append({
            "severity": "error",
            "message": "题目列表为空：请在 items_text 中粘贴题目，或在 dependent_vars 中选择题目列。",
        })
        return

    if len(items) < 3:
        output["errors"].append({
            "severity": "error",
            "message": f"AI 预审至少需要 3 道题，当前 {len(items)} 道。",
        })
        return

    if not plan.construct_name or not plan.construct_definition:
        output["errors"].append({
            "severity": "error",
            "message": "构念名（construct_name）和构念定义（construct_definition）都必填。",
        })
        return

    # 可选 KB 查询（直接 dict 命中即可，不做模糊匹配）
    kb_def = None
    try:
        from src.questionnaire.construct_kb import CONSTRUCTS
        rec = CONSTRUCTS.get(plan.construct_name)
        if rec:
            kb_def = rec.get("definition")
    except Exception:
        pass

    try:
        result = ai_content_review(
            items=items,
            construct_name=plan.construct_name,
            construct_definition=plan.construct_definition,
            kb_definition=kb_def,
            n_personas=plan.n_personas or 4,
        )
        output["result"] = result
    except LLMUnavailableError as e:
        output["errors"].append({
            "severity": "error",
            "message": f"AI 预审失败：{e}。请检查 LLM 配置或稍后重试。",
        })
    except Exception as e:
        output["errors"].append({
            "severity": "error",
            "message": f"AI 预审失败：{e}",
        })


@_register("known_groups_validity")
def _run_known_groups_validity(df, plan, output):
    items = plan.dependent_vars
    group = plan.grouping_var or (plan.independent_vars[0] if plan.independent_vars else None)
    if not items or not group:
        output["errors"].append({
            "severity": "error",
            "message": "已知组别效度需要量表题目和分组变量。",
        })
        return
    try:
        result = validity.known_groups_validity(df, items, group)
        output["result"] = result
    except Exception as e:
        output["errors"].append({"severity": "error", "message": f"已知组别效度计算失败：{e}"})


# ==================== 非参数检验 ====================

@_register("mann_whitney")
def _run_mann_whitney(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    iv = plan.independent_vars[0] if plan.independent_vars else None
    if not dv or not iv:
        output["errors"].append({"severity": "error", "message": "Mann-Whitney U检验需要指定一个因变量和一个二分类分组变量。"})
        return
    result = nonparametric.mann_whitney(df, dv, iv)
    output["result"] = result
    output["descriptive"] = result.group_stats
    output["charts_data"]["box_data"] = {"dv": dv, "iv": iv}


@_register("wilcoxon")
def _run_wilcoxon(df, plan, output):
    if len(plan.dependent_vars) < 2:
        output["errors"].append({"severity": "error", "message": "Wilcoxon符号秩检验需要指定两个配对测量变量。"})
        return
    col1, col2 = plan.dependent_vars[0], plan.dependent_vars[1]
    result = nonparametric.wilcoxon_signed_rank(df, col1, col2)
    output["result"] = result
    output["descriptive"] = result.group_stats


@_register("kruskal_wallis")
def _run_kruskal_wallis(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    iv = plan.independent_vars[0] if plan.independent_vars else None
    if not dv or not iv:
        output["errors"].append({"severity": "error", "message": "Kruskal-Wallis H检验需要指定一个因变量和一个多分类分组变量。"})
        return
    # 支持通过 plan 传入 mc_method
    mc_method = getattr(plan, "mc_method", "holm") or "holm"
    result = nonparametric.kruskal_wallis(df, dv, iv, mc_method=mc_method)
    output["result"] = result
    output["descriptive"] = result.group_stats
    output["charts_data"]["box_data"] = {"dv": dv, "iv": iv}


@_register("friedman")
def _run_friedman(df, plan, output):
    items = plan.dependent_vars
    if len(items) < 2:
        output["errors"].append({"severity": "error", "message": "Friedman检验需要至少2个重复测量变量。"})
        return
    result = nonparametric.friedman_test(df, items)
    output["result"] = result


# ==================== 因素分析 ====================

@_register("efa")
def _run_efa(df, plan, output):
    items = plan.dependent_vars
    if len(items) < 3:
        output["errors"].append({"severity": "error", "message": "探索性因素分析（EFA）至少需要3道题目。"})
        return
    result = factor_analysis.exploratory_factor_analysis(df, items)
    output["result"] = result
    output["descriptive"] = descriptive.descriptive_stats(df, items)
    output["charts_data"]["scree_data"] = result.eigenvalues


@_register("cfa")
def _run_cfa(df, plan, output):
    """验证性因素分析（CFA）"""
    from . import cfa as cfa_mod
    items = plan.dependent_vars
    if len(items) < 3:
        output["errors"].append({"severity": "error", "message": "CFA至少需要3个观测变量（题目）。"})
        return

    # 从plan中提取因子信息（如果有的话）
    n_factors_hint = getattr(plan, "n_factors", None) or 1
    factor_names = getattr(plan, "factor_names", None)
    factor_structure = getattr(plan, "factor_structure", None)

    if factor_structure and isinstance(factor_structure, dict):
        # v3.7：UI 直接传入因子结构
        factors = factor_structure
    elif factor_names and isinstance(factor_names, dict):
        # 用户指定了因子-题目映射（向后兼容旧字段）
        factors = factor_names
    else:
        # 自动将题目均分到n_factors_hint个因子
        n_items = len(items)
        factors = {}
        for f_idx in range(int(n_factors_hint)):
            f_name = f"因子{f_idx + 1}"
            start = f_idx * (n_items // int(n_factors_hint))
            end = start + (n_items // int(n_factors_hint)) if f_idx < int(n_factors_hint) - 1 else n_items
            factors[f_name] = items[start:end]

    try:
        result = cfa_mod.confirmatory_factor_analysis(df, factors)
        output["result"] = result
        output["descriptive"] = descriptive.descriptive_stats(df, items)
    except ImportError as e:
        output["errors"].append({
            "severity": "warning",
            "message": f"CFA需要 semopy 库，请执行 pip install semopy。已降级为探索性参考分析。错误: {e}",
        })
        # 降级到 EFA
        _run_efa(df, plan, output)
    except Exception as e:
        output["errors"].append({
            "severity": "error",
            "message": f"CFA分析失败: {e}",
        })


# ==================== 高级分析 ====================

@_register("ancova")
def _run_ancova(df, plan, output):
    dv = plan.dependent_vars[0] if plan.dependent_vars else None
    iv = plan.independent_vars[0] if plan.independent_vars else None
    covs = plan.covariates if plan.covariates else []
    if not dv or not iv or not covs:
        output["errors"].append({"severity": "error", "message": "ANCOVA需要指定一个因变量、一个分组变量和至少一个协变量。"})
        return
    result = advanced.ancova(df, dv, iv, covs)
    output["result"] = result
    output["descriptive"] = descriptive.grouped_descriptive(df, dv, iv)


@_register("mediation")
def _run_mediation(df, plan, output):
    all_vars = plan.independent_vars + plan.dependent_vars
    if len(all_vars) < 3:
        output["errors"].append({"severity": "error", "message": "中介分析需要指定自变量(X)、中介变量(M)和因变量(Y)共3个不同变量。"})
        return
    x = all_vars[0]
    # 支持多个中介变量：中间所有变量都是中介变量
    mediators = all_vars[1:-1]
    y = all_vars[-1]
    # 如果只有一个中介，保持向后兼容（传字符串）
    if len(mediators) == 1:
        m_arg = mediators[0]
    else:
        m_arg = mediators
    result = advanced.mediation_analysis(df, x, m_arg, y)
    output["result"] = result


@_register("moderation")
def _run_moderation(df, plan, output):
    if len(plan.dependent_vars) < 1 or len(plan.independent_vars) < 2:
        output["errors"].append({"severity": "error", "message": "调节分析需要指定自变量(X)、调节变量(M)和因变量(Y)。"})
        return
    x = plan.independent_vars[0]
    m = plan.independent_vars[1] if len(plan.independent_vars) > 1 else None
    y = plan.dependent_vars[0]
    if not m:
        output["errors"].append({"severity": "error", "message": "调节分析需要两个自变量（预测变量和调节变量）。"})
        return
    result = advanced.moderation_analysis(df, x, m, y)
    output["result"] = result


# ===========================================================================
# 主调度函数
# ===========================================================================

def run_analysis(df: pd.DataFrame, plan: AnalysisPlan) -> Dict[str, Any]:
    """
    根据 AnalysisPlan 执行对应的统计分析（注册表模式）。

    返回统一格式的字典：
    {
        "test_type": str,
        "test_name_zh": str,
        "plan": AnalysisPlan,
        "descriptive": pd.DataFrame | None,
        "result": dataclass | None,
        "assumptions": dict,
        "errors": list,
        "charts_data": dict,
        "reasoning": AnalysisReasoning | None,
        "data_quality": DataQualityReport | None,
    }
    """
    # 确定缺失值处理策略（可从plan传入，默认listwise）
    missing_strategy = getattr(plan, "missing_strategy", "listwise") or "listwise"
    analysis_df = df

    output = {
        "test_type": plan.test_type,
        "test_name_zh": _test_name(plan.test_type),
        "plan": plan,
        "descriptive": None,
        "result": None,
        "assumptions": {},
        "errors": [],
        "charts_data": {},
        "reasoning": None,
        "data_quality": None,
        "missing_strategy": missing_strategy,
        "missing_meta": None,
        "snapshot_id": None,
        "routing": None,           # Phase 1.3: 假设违反路由建议（仅建议，不切换）
        "post_hoc_power": None,    # Phase 1.3: 事后样本量建议（仅 power<0.8 时填充）
    }

    # ====== 统一数据前置检查 ======
    try:
        numeric_vars = _collect_numeric_vars(df, plan)
        dq_report = data_quality_check(
            df,
            numeric_cols=numeric_vars,
            check_normality=_needs_normality_check(plan.test_type),
        )
        output["data_quality"] = dq_report
        # 将DQ警告合并到errors
        for w in dq_report.warnings:
            output["errors"].append({"severity": "warning", "message": w})
    except Exception:
        pass

    # ====== 缺失值处理 ======
    try:
        numeric_vars = _collect_numeric_vars(df, plan)
        analysis_df, missing_meta = handle_missing(
            df, numeric_cols=numeric_vars, strategy=missing_strategy
        )
        output["missing_meta"] = missing_meta
    except Exception:
        analysis_df = df
        output["missing_meta"] = {"strategy": "none", "description_zh": "缺失值处理未执行（出错）。"}

    # ====== 查找并执行注册的处理器 ======
    handler = AnalysisRegistry.get(plan.test_type)
    if handler is None:
        output["errors"].append({
            "severity": "warning",
            "message": f"未识别的检验方法「{plan.test_type}」，已执行描述统计作为替代。",
        })
        _run_descriptive(analysis_df, plan, output)
    else:
        try:
            handler(analysis_df, plan, output)
        except Exception as e:
            fe = friendly_explain(e)
            output["errors"].append({
                "severity": "error",
                "message": f"{fe.title}：{fe.explanation}",
                "friendly_title": fe.title,
                "friendly_explanation": fe.explanation,
                "friendly_action": fe.suggested_action,
                "technical": fe.technical_detail,
            })

    # ====== Phase 1.3: 假设违反路由检查（仅计算建议，不切换检验） ======
    try:
        decision = assumption_router.check_route(analysis_df, plan, output)
        if decision.has_suggestion or not decision.hard_route_allowed:
            output["routing"] = assumption_router.to_dict(decision)
    except Exception:
        output["routing"] = None

    # ====== Phase 1.3: 事后样本量建议（仅 power<0.80 时填充） ======
    try:
        ph = _post_hoc_power.estimate_post_hoc(output)
        if ph is not None:
            output["post_hoc_power"] = ph
    except Exception:
        output["post_hoc_power"] = None

    # ====== 生成分析思路 ======
    try:
        output["reasoning"] = generate_reasoning(output)
    except Exception:
        output["reasoning"] = None

    # ====== 生成可复现快照 ======
    try:
        output["snapshot_id"] = _generate_snapshot_id(df, plan)
    except Exception:
        output["snapshot_id"] = f"snapshot_{int(time.time())}"

    return output


# ===========================================================================
# 辅助函数
# ===========================================================================

def _test_name(test_type: str) -> str:
    from config.settings import get_test_name
    return get_test_name(test_type)


def _collect_numeric_vars(df: pd.DataFrame, plan: AnalysisPlan) -> list:
    """收集分析涉及的所有数值变量"""
    numeric = df.select_dtypes(include=["number"]).columns.tolist()
    return [c for c in numeric if c in df.columns]


def _needs_normality_check(test_type: str) -> bool:
    """判断分析是否需要进行正态性检查"""
    normality_tests = {
        "independent_ttest", "paired_ttest", "one_sample_ttest",
        "one_way_anova", "pearson_corr", "linear_regression",
        "multiple_regression", "ancova",
    }
    return test_type in normality_tests


def register_custom_handler(test_type: str, handler: Callable):
    """允许外部注册自定义检验处理器"""
    AnalysisRegistry[test_type] = handler


def _generate_snapshot_id(df: pd.DataFrame, plan: AnalysisPlan) -> str:
    """生成分析快照ID：基于输入数据哈希 + 参数哈希 + 时间戳。"""
    data_hash = hashlib.sha256(
        pd.util.hash_pandas_object(df).values.tobytes()
    ).hexdigest()[:12]
    param_str = f"{plan.test_type}_{plan.dependent_vars}_{plan.independent_vars}_{plan.confidence_level}"
    param_hash = hashlib.sha256(param_str.encode("utf-8")).hexdigest()[:8]
    ts = int(time.time())
    return f"snap_{data_hash}_{param_hash}_{ts}"


def export_snapshot(output: Dict[str, Any], file_path: str = None) -> str:
    """导出分析快照为JSON文件。

    参数：
        output: run_analysis() 的返回值
        file_path: 保存路径（None则自动生成文件名）

    返回：保存的文件路径"""
    snapshot = {
        "snapshot_id": output.get("snapshot_id", ""),
        "test_type": output.get("test_type", ""),
        "test_name_zh": output.get("test_name_zh", ""),
        "missing_strategy": output.get("missing_strategy", "listwise"),
        "missing_meta": output.get("missing_meta", {}),
        "errors": output.get("errors", []),
        "timestamp": int(time.time()),
    }
    plan = output.get("plan")
    if plan is not None:
        snapshot["plan"] = {
            "test_type": getattr(plan, "test_type", ""),
            "dependent_vars": getattr(plan, "dependent_vars", []),
            "independent_vars": getattr(plan, "independent_vars", []),
            "confidence_level": getattr(plan, "confidence_level", 0.95),
        }
    result = output.get("result")
    if result is not None:
        try:
            from dataclasses import asdict
            snapshot["result"] = asdict(result)
        except Exception:
            snapshot["result"] = str(result)
    dq = output.get("data_quality")
    if dq is not None and hasattr(dq, "warnings"):
        try:
            from dataclasses import asdict
            dq_dict = asdict(dq)
            dq_dict.pop("normality_checks", None)
            snapshot["data_quality"] = dq_dict
        except Exception:
            snapshot["data_quality"] = {"warnings": getattr(dq, "warnings", [])}
    desc = output.get("descriptive")
    if desc is not None and hasattr(desc, "to_dict"):
        try:
            snapshot["descriptive"] = desc.to_dict(orient="records")
        except Exception:
            pass
    if file_path is None:
        snap_dir = Path("reports/snapshots")
        snap_dir.mkdir(parents=True, exist_ok=True)
        file_path = str(snap_dir / f"{output.get('snapshot_id', 'snapshot')}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, default=str)
    return file_path
