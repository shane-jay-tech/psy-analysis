"""方法 ID 单一事实源。

所有方法 ID 的规范名称和别名映射集中于此。
系统中任何需要解析方法 ID 的地方应使用 resolve_method_id()。
"""

from __future__ import annotations

CANONICAL_IDS: dict[str, str] = {
    "pearson_corr": "pearson_corr",
    "pearson_correlation": "pearson_corr",
    "spearman_corr": "spearman_corr",
    "spearman_correlation": "spearman_corr",
    "partial_corr": "partial_corr",
    "partial_correlation": "partial_corr",
    "point_biserial": "point_biserial",
    "independent_ttest": "independent_ttest",
    "independent_t_test": "independent_ttest",
    "paired_ttest": "paired_ttest",
    "paired_t_test": "paired_ttest",
    "one_sample_ttest": "one_sample_ttest",
    "one_way_anova": "one_way_anova",
    "two_way_anova": "two_way_anova",
    "repeated_measures_anova": "repeated_measures_anova",
    "rm_anova": "repeated_measures_anova",
    "mixed_anova": "mixed_anova",
    "mann_whitney": "mann_whitney",
    "wilcoxon": "wilcoxon",
    "kruskal_wallis": "kruskal_wallis",
    "friedman": "friedman",
    "chi_square": "chi_square",
    "chi_square_test": "chi_square",
    "fisher_exact": "fisher_exact",
    "linear_regression": "linear_regression",
    "multiple_regression": "multiple_regression",
    "hierarchical_regression": "hierarchical_regression",
    "logistic_regression": "logistic_regression",
    "cronbach_alpha": "cronbach_alpha",
    "mcdonalds_omega": "mcdonalds_omega",
    "efa": "efa",
    "cfa": "cfa",
    "sem": "sem",
    "mediation": "mediation",
    "moderation": "moderation",
    "moderated_mediation": "moderated_mediation",
    "hlm": "hlm",
    "hierarchical_linear_model": "hlm",
    "mixed_effects": "hlm",
    "descriptive": "descriptive",
    "descriptive_statistics": "descriptive",
    "normality_test": "normality_test",
    "levene_test": "levene_test",
    "ave_cr": "ave_cr",
    "discriminant_validity": "discriminant_validity",
}

_TABLE_ROUTE_ALIASES: dict[str, list[str]] = {
    "pearson_corr": ["pearson_corr", "pearson_correlation", "spearman_corr"],
    "descriptive": ["descriptive", "descriptive_statistics"],
    "independent_ttest": ["independent_ttest", "independent_t_test"],
    "paired_ttest": ["paired_ttest", "paired_t_test"],
    "one_sample_ttest": ["one_sample_ttest"],
    "mann_whitney": ["mann_whitney"],
    "wilcoxon": ["wilcoxon"],
    "kruskal_wallis": ["kruskal_wallis"],
    "chi_square": ["chi_square", "chi_square_test", "chi_square_independence", "chi_square_gof"],
    "one_way_anova": ["one_way_anova"],
    "two_way_anova": ["two_way_anova"],
    "repeated_measures_anova": ["repeated_measures_anova", "rm_anova"],
    "mixed_anova": ["mixed_anova"],
    "multiple_regression": ["multiple_regression", "hierarchical_regression", "linear_regression"],
    "cronbach_alpha": ["cronbach_alpha", "mcdonalds_omega"],
    "efa": ["efa"],
    "cfa": ["cfa", "sem"],
    "hlm": ["hlm", "hierarchical_linear_model", "mixed_effects"],
    "mediation": ["mediation"],
    "moderation": ["moderation"],
    "logistic_regression": ["logistic_regression", "binary_logistic"],
}


def resolve_method_id(raw_id: str) -> str:
    """将任意方法 ID（含别名）解析为规范 ID。未知 ID 原样返回。"""
    return CANONICAL_IDS.get(raw_id, raw_id)


def get_table_route_group(method_id: str) -> str | None:
    """查找某方法 ID 属于哪个表格路由组。返回路由组 key 或 None。"""
    canonical = resolve_method_id(method_id)
    for group, members in _TABLE_ROUTE_ALIASES.items():
        if canonical in members or method_id in members:
            return group
    return None
