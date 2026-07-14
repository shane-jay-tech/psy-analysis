"""v5.4 P1-3: 方法暴露分级策略。

公开发布版区分三档方法：
- DEFAULT: 有完整交付链（结果卡片 + APA 表格路由），新手默认推荐
- ADVANCED: 有结果卡片但缺 APA 表格路由，需手动处理表格
- EXPERIMENTAL: 无结果卡片或仅有基础输出，明确标注限制

判断依据：
1. 该方法是否在 _CARD_BUILDERS 注册
2. 该方法是否在 generate_tables_from_card 路由中有条目
"""
from typing import Literal

MethodLevel = Literal["default", "advanced", "experimental"]

_CARD_BUILDER_METHODS: set[str] = {
    "descriptive", "independent_ttest", "paired_ttest", "one_way_anova",
    "pearson_correlation", "pearson_corr", "multiple_regression",
    "repeated_anova", "repeated_measures_anova",
    "mediation", "moderation", "cronbach_alpha",
    "two_way_anova", "factorial_anova", "mixed_anova", "ancova",
    "mann_whitney", "mann_whitney_u", "wilcoxon", "wilcoxon_signed_rank",
    "kruskal_wallis", "hierarchical_regression",
    "logistic_regression", "binary_logistic",
    "mcdonalds_omega", "omega",
    "efa", "exploratory_factor_analysis",
    "one_sample_ttest",
    "spearman_corr", "spearman_correlation",
    "partial_corr", "partial_correlation",
    "chi_square", "chi_square_test",
    "cfa", "confirmatory_factor_analysis",
    "sem", "structural_equation_model",
    "ave_cr", "discriminant_validity",
    "hlm", "hierarchical_linear_model", "mixed_effects",
}

_TABLE_ROUTER_METHODS: set[str] = {
    "descriptive",
    "pearson_corr", "pearson_correlation", "spearman_corr",
    "independent_ttest", "paired_ttest", "one_sample_ttest",
    "mann_whitney", "wilcoxon", "kruskal_wallis",
    "chi_square", "chi_square_test",
    "one_way_anova", "two_way_anova", "repeated_measures_anova", "mixed_anova",
    "multiple_regression", "hierarchical_regression", "linear_regression",
    "cronbach_alpha", "mcdonalds_omega",
    "efa",
    "cfa", "sem",
    "hlm", "hierarchical_linear_model", "mixed_effects",
    "mediation", "moderation",
    "logistic_regression", "binary_logistic",
}

_DEFAULT_METHODS: set[str] = {
    "pearson_corr", "pearson_correlation",
    "spearman_corr", "spearman_correlation",
    "independent_ttest", "paired_ttest", "one_sample_ttest",
    "one_way_anova", "two_way_anova", "factorial_anova",
    "repeated_anova", "repeated_measures_anova",
    "mann_whitney", "wilcoxon", "kruskal_wallis",
    "chi_square", "chi_square_test",
    "multiple_regression", "hierarchical_regression",
    "cronbach_alpha", "mcdonalds_omega", "omega",
    "descriptive",
}


def get_method_level(method_id: str) -> MethodLevel:
    """获取方法的暴露级别。"""
    has_card = method_id in _CARD_BUILDER_METHODS
    if not has_card:
        return "experimental"
    if method_id in _DEFAULT_METHODS:
        return "default"
    return "advanced"


def get_method_warning(method_id: str) -> str:
    """获取方法级别对应的警告文本（空字符串=无警告）。"""
    level = get_method_level(method_id)
    if level == "experimental":
        return "⚠️ 实验性方法：尚无完整结果卡片，输出需要手动整理"
    if level == "advanced":
        return "ℹ️ 高级方法：结果卡片可用，但 APA 表格可能需要手动排版"
    return ""


def is_safe_for_newbie(method_id: str) -> bool:
    """判断方法是否适合作为新手默认推荐。"""
    return get_method_level(method_id) == "default"


def list_methods_by_level() -> dict[MethodLevel, list[str]]:
    """列出按级别分组的所有已知方法。"""
    result: dict[MethodLevel, list[str]] = {"default": [], "advanced": [], "experimental": []}
    for m in sorted(_CARD_BUILDER_METHODS):
        level = get_method_level(m)
        result[level].append(m)
    return result
