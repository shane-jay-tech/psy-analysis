"""方法推荐向导 — 规则引擎根据研究设计推荐统计方法。

推荐逻辑由规则产生（可测试、可追溯），LLM 仅用于解释。
覆盖 12+ 高频心理学研究场景。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MethodRecommendation:
    """方法推荐结果。"""
    primary_method: str
    primary_method_zh: str
    alternative_methods: list[dict[str, str]] = field(default_factory=list)
    rejected_methods: list[dict[str, str]] = field(default_factory=list)
    required_variables: list[str] = field(default_factory=list)
    assumption_checks: list[str] = field(default_factory=list)
    explanation: str = ""
    next_action: str = ""
    confidence: str = "high"
    warnings: list[str] = field(default_factory=list)


@dataclass
class ResearchDesignInput:
    """用户输入的研究设计信息。"""
    purpose: str = ""  # difference / correlation / prediction / mediation / moderation / reliability
    dv_type: str = ""  # continuous / binary / ordinal / count
    iv_type: str = ""  # categorical / continuous / multi_factor
    sample_relation: str = ""  # independent / paired / repeated
    time_points: int = 1  # 1 / 2 / 3+
    n_groups: int = 2
    has_covariate: bool = False
    n_covariates: int = 0
    sample_size: int = 0
    dv_count: int = 1
    assumptions_met: str = "unknown"  # met / partial / violated / unknown


def recommend_method(design: ResearchDesignInput) -> MethodRecommendation:
    """根据研究设计推荐统计方法。"""
    for rule in _RULES:
        if rule["match"](design):
            rec = rule["recommend"](design)
            _add_sample_size_warnings(rec, design)
            return rec

    return MethodRecommendation(
        primary_method="descriptive",
        primary_method_zh="描述统计",
        explanation="未能匹配到具体统计方法，建议先进行描述统计探索数据。",
        next_action="运行描述统计",
        confidence="low",
        warnings=["当前研究设计信息不足以精确推荐，建议补充研究目的和变量信息"],
    )


def _add_sample_size_warnings(rec: MethodRecommendation, design: ResearchDesignInput):
    if design.sample_size > 0:
        if design.sample_size < 30:
            rec.warnings.append(f"样本量 N={design.sample_size} 偏小，统计检验力可能不足")
        if design.sample_size < 20 and rec.primary_method in ("mediation", "moderation", "multiple_regression"):
            rec.warnings.append("样本量不足以支持该方法，建议至少 50 人以上")
            rec.confidence = "low"


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

def _match_two_group_diff(d: ResearchDesignInput) -> bool:
    return (d.purpose == "difference" and d.dv_type == "continuous"
            and d.iv_type == "categorical" and d.sample_relation == "independent"
            and d.n_groups == 2)


def _rec_two_group_diff(d: ResearchDesignInput) -> MethodRecommendation:
    primary = "independent_ttest" if d.assumptions_met != "violated" else "mann_whitney"
    primary_zh = "独立样本 t 检验" if primary == "independent_ttest" else "Mann-Whitney U 检验"
    return MethodRecommendation(
        primary_method=primary,
        primary_method_zh=primary_zh,
        alternative_methods=[
            {"method": "mann_whitney", "reason": "正态性假设不满足时的非参数替代"},
            {"method": "welch_ttest", "reason": "方差不齐时使用 Welch 校正"},
        ],
        rejected_methods=[
            {"method": "one_way_anova", "reason": "仅有两组时 t 检验更直接"},
            {"method": "chi_square", "reason": "因变量为连续变量，非分类变量"},
        ],
        required_variables=["一个分组变量（二分类）", "一个连续因变量"],
        assumption_checks=["正态性（Shapiro-Wilk）", "方差齐性（Levene）"],
        explanation="两个独立组别在一个连续变量上的均值差异比较，经典选择是独立样本 t 检验。",
        next_action="进入独立样本 t 检验",
    )


def _match_paired_diff(d: ResearchDesignInput) -> bool:
    return (d.purpose == "difference" and d.dv_type == "continuous"
            and d.sample_relation == "paired" and d.time_points <= 2)


def _rec_paired_diff(d: ResearchDesignInput) -> MethodRecommendation:
    primary = "paired_ttest" if d.assumptions_met != "violated" else "wilcoxon"
    primary_zh = "配对样本 t 检验" if primary == "paired_ttest" else "Wilcoxon 符号秩检验"
    return MethodRecommendation(
        primary_method=primary,
        primary_method_zh=primary_zh,
        alternative_methods=[
            {"method": "wilcoxon", "reason": "差值分正态性不满足时的非参数替代"},
        ],
        rejected_methods=[
            {"method": "independent_ttest", "reason": "样本为配对/重复测量，非独立样本"},
        ],
        required_variables=["同一被试的两次测量"],
        assumption_checks=["差值分的正态性"],
        explanation="同一组被试在前后两个时间点的测量差异比较，使用配对样本 t 检验。",
        next_action="进入配对样本 t 检验",
    )


def _match_multi_group_diff(d: ResearchDesignInput) -> bool:
    return (d.purpose == "difference" and d.dv_type == "continuous"
            and d.iv_type == "categorical" and d.sample_relation == "independent"
            and d.n_groups >= 3)


def _rec_multi_group_diff(d: ResearchDesignInput) -> MethodRecommendation:
    primary = "one_way_anova" if d.assumptions_met != "violated" else "kruskal_wallis"
    primary_zh = "单因素方差分析" if primary == "one_way_anova" else "Kruskal-Wallis H 检验"
    return MethodRecommendation(
        primary_method=primary,
        primary_method_zh=primary_zh,
        alternative_methods=[
            {"method": "kruskal_wallis", "reason": "正态性假设不满足时的非参数替代"},
            {"method": "welch_anova", "reason": "方差不齐时使用 Welch 校正"},
        ],
        rejected_methods=[
            {"method": "independent_ttest", "reason": "三组及以上不能使用两两 t 检验（累积一类错误）"},
        ],
        required_variables=["一个分组变量（≥3 水平）", "一个连续因变量"],
        assumption_checks=["正态性", "方差齐性（Levene）"],
        explanation=f"比较 {d.n_groups} 个独立组在一个连续变量上的均值差异，使用单因素方差分析。",
        next_action="进入单因素方差分析",
    )


def _match_repeated_measures(d: ResearchDesignInput) -> bool:
    return (d.purpose == "difference" and d.dv_type == "continuous"
            and d.sample_relation == "repeated" and d.time_points >= 3)


def _rec_repeated_measures(d: ResearchDesignInput) -> MethodRecommendation:
    return MethodRecommendation(
        primary_method="repeated_anova",
        primary_method_zh="重复测量方差分析",
        alternative_methods=[
            {"method": "friedman", "reason": "正态性假设不满足时的非参数替代"},
            {"method": "mixed_anova", "reason": "同时有组间和组内因素时使用"},
        ],
        rejected_methods=[
            {"method": "one_way_anova", "reason": "样本为重复测量，非独立样本"},
            {"method": "paired_ttest", "reason": "三个及以上时间点不能两两配对检验"},
        ],
        required_variables=[f"同一被试的 {d.time_points} 次测量"],
        assumption_checks=["球形性（Mauchly）", "正态性"],
        explanation=f"同一组被试在 {d.time_points} 个时间点/条件下的重复测量差异比较。",
        next_action="进入重复测量方差分析",
    )


def _match_correlation(d: ResearchDesignInput) -> bool:
    return d.purpose == "correlation" and d.dv_type == "continuous"


def _rec_correlation(d: ResearchDesignInput) -> MethodRecommendation:
    primary = "pearson_corr" if d.assumptions_met != "violated" else "spearman_corr"
    primary_zh = "Pearson 相关" if primary == "pearson_corr" else "Spearman 秩相关"
    return MethodRecommendation(
        primary_method=primary,
        primary_method_zh=primary_zh,
        alternative_methods=[
            {"method": "spearman_corr", "reason": "正态性不满足或有序变量时使用"},
            {"method": "partial_corr", "reason": "需要控制第三变量时使用偏相关"},
        ],
        rejected_methods=[
            {"method": "chi_square", "reason": "两个变量均为连续变量，非分类变量"},
        ],
        required_variables=["两个连续变量"],
        assumption_checks=["正态性", "线性关系（散点图）", "无极端异常值"],
        explanation="探索两个连续变量之间的线性关系强度和方向。",
        next_action="进入 Pearson 相关分析",
    )


def _match_prediction(d: ResearchDesignInput) -> bool:
    return d.purpose == "prediction" and d.dv_type == "continuous"


def _rec_prediction(d: ResearchDesignInput) -> MethodRecommendation:
    return MethodRecommendation(
        primary_method="multiple_regression",
        primary_method_zh="多元线性回归",
        alternative_methods=[
            {"method": "hierarchical_regression", "reason": "需要分步检验预测贡献时使用"},
            {"method": "stepwise_regression", "reason": "探索性选择最优预测组合（谨慎使用）"},
        ],
        rejected_methods=[
            {"method": "pearson_corr", "reason": "相关只能描述关系，不能建立预测模型"},
        ],
        required_variables=["一个连续因变量", "多个预测变量"],
        assumption_checks=["线性关系", "残差正态性", "同方差性", "多重共线性（VIF）"],
        explanation="用多个预测变量联合预测一个连续结果变量。",
        next_action="进入多元线性回归",
    )


def _match_mediation(d: ResearchDesignInput) -> bool:
    return d.purpose == "mediation"


def _rec_mediation(d: ResearchDesignInput) -> MethodRecommendation:
    return MethodRecommendation(
        primary_method="mediation",
        primary_method_zh="中介效应分析",
        alternative_methods=[
            {"method": "sem", "reason": "多个中介变量或复杂路径时使用结构方程模型"},
        ],
        rejected_methods=[
            {"method": "multiple_regression", "reason": "回归不能检验间接效应的显著性"},
            {"method": "pearson_corr", "reason": "相关不能建立因果路径"},
        ],
        required_variables=["自变量 X", "中介变量 M", "因变量 Y"],
        assumption_checks=["变量间线性关系", "无多重共线性", "残差正态性"],
        explanation="检验 X 对 Y 的影响是否通过中介变量 M 传递（间接效应）。",
        next_action="进入中介效应分析",
        warnings=["中介分析需要理论支持因果方向，横断面数据结论需谨慎解释"],
    )


def _match_moderation(d: ResearchDesignInput) -> bool:
    return d.purpose == "moderation"


def _rec_moderation(d: ResearchDesignInput) -> MethodRecommendation:
    return MethodRecommendation(
        primary_method="moderation",
        primary_method_zh="调节效应分析",
        alternative_methods=[
            {"method": "hierarchical_regression", "reason": "用分层回归手动构建交互项"},
        ],
        rejected_methods=[
            {"method": "mediation", "reason": "调节是改变关系强度，中介是传递效应，概念不同"},
        ],
        required_variables=["自变量 X", "调节变量 W", "因变量 Y"],
        assumption_checks=["变量间线性关系", "交互项多重共线性（建议中心化）"],
        explanation="检验 W 是否改变了 X 对 Y 影响的强度或方向。",
        next_action="进入调节效应分析",
    )


def _match_reliability(d: ResearchDesignInput) -> bool:
    return d.purpose == "reliability"


def _rec_reliability(d: ResearchDesignInput) -> MethodRecommendation:
    return MethodRecommendation(
        primary_method="cronbach_alpha",
        primary_method_zh="Cronbach's α 信度分析",
        alternative_methods=[
            {"method": "mcdonald_omega", "reason": "因子载荷不等时 omega 比 alpha 更准确"},
            {"method": "split_half", "reason": "仅有两半时使用分半信度"},
        ],
        rejected_methods=[
            {"method": "pearson_corr", "reason": "相关系数不能替代信度系数"},
        ],
        required_variables=["同一量表的全部题项"],
        assumption_checks=["题项为同一维度", "使用 Likert 等距量表"],
        explanation="评估量表各题项测量同一构念的一致性程度。",
        next_action="进入信度分析",
    )


def _match_prediction_binary(d: ResearchDesignInput) -> bool:
    return d.purpose == "prediction" and d.dv_type == "binary"


def _rec_prediction_binary(d: ResearchDesignInput) -> MethodRecommendation:
    return MethodRecommendation(
        primary_method="binary_logistic",
        primary_method_zh="二元 Logistic 回归",
        alternative_methods=[
            {"method": "discriminant_analysis", "reason": "预测变量满足多元正态时可用"},
        ],
        rejected_methods=[
            {"method": "multiple_regression", "reason": "因变量为二分类，不适用线性回归"},
        ],
        required_variables=["一个二分类因变量", "多个预测变量"],
        assumption_checks=["无多重共线性", "样本量充足（每个预测变量至少 10-20 例）"],
        explanation="预测一个二分类结果（如：是否/通过否）的概率。",
        next_action="进入 Logistic 回归",
    )


def _match_chi_square(d: ResearchDesignInput) -> bool:
    return (d.purpose == "difference" and d.dv_type in ("binary", "ordinal")
            and d.iv_type == "categorical")


def _rec_chi_square(d: ResearchDesignInput) -> MethodRecommendation:
    return MethodRecommendation(
        primary_method="chi_square_independence",
        primary_method_zh="卡方独立性检验",
        alternative_methods=[
            {"method": "fisher_exact", "reason": "期望频数 < 5 的格子超过 20% 时使用"},
        ],
        rejected_methods=[
            {"method": "independent_ttest", "reason": "因变量非连续变量"},
        ],
        required_variables=["两个分类变量"],
        assumption_checks=["每格期望频数 ≥ 5", "独立观测"],
        explanation="检验两个分类变量之间是否存在关联。",
        next_action="进入卡方检验",
    )


def _match_covariate_diff(d: ResearchDesignInput) -> bool:
    return (d.purpose == "difference" and d.dv_type == "continuous"
            and d.has_covariate and d.sample_relation == "independent")


def _rec_covariate_diff(d: ResearchDesignInput) -> MethodRecommendation:
    return MethodRecommendation(
        primary_method="ancova",
        primary_method_zh="协方差分析 (ANCOVA)",
        alternative_methods=[
            {"method": "one_way_anova", "reason": "无需控制协变量时直接使用 ANOVA"},
            {"method": "multiple_regression", "reason": "用回归框架同时检验分组和协变量"},
        ],
        rejected_methods=[
            {"method": "independent_ttest", "reason": "无法控制协变量的影响"},
        ],
        required_variables=["一个分组变量", "一个连续因变量", "一个或多个协变量"],
        assumption_checks=["协变量与因变量线性关系", "协变量与自变量独立", "方差齐性", "回归斜率同质性"],
        explanation="在控制协变量后比较组间差异。",
        next_action="进入协方差分析",
    )


# Rule registry (order matters: more specific first)
_RULES = [
    {"match": _match_covariate_diff, "recommend": _rec_covariate_diff},
    {"match": _match_mediation, "recommend": _rec_mediation},
    {"match": _match_moderation, "recommend": _rec_moderation},
    {"match": _match_reliability, "recommend": _rec_reliability},
    {"match": _match_prediction_binary, "recommend": _rec_prediction_binary},
    {"match": _match_prediction, "recommend": _rec_prediction},
    {"match": _match_repeated_measures, "recommend": _rec_repeated_measures},
    {"match": _match_paired_diff, "recommend": _rec_paired_diff},
    {"match": _match_multi_group_diff, "recommend": _rec_multi_group_diff},
    {"match": _match_two_group_diff, "recommend": _rec_two_group_diff},
    {"match": _match_chi_square, "recommend": _rec_chi_square},
    {"match": _match_correlation, "recommend": _rec_correlation},
]


# ─── AnalysisRecipe: 从推荐到执行的桥梁 ─────────────────────────


_METHOD_TO_VARIABLE_ROLES: dict[str, dict[str, str]] = {
    "independent_ttest": {"dv": "连续因变量", "iv": "分组变量（2 组）"},
    "paired_ttest": {"dv": "连续因变量", "iv": "配对标识"},
    "one_way_anova": {"dv": "连续因变量", "iv": "分组变量（≥3 组）"},
    "repeated_anova": {"dv": "连续因变量", "iv": "时间/条件"},
    "pearson_corr": {"x": "连续变量 1", "y": "连续变量 2"},
    "spearman_corr": {"x": "变量 1", "y": "变量 2"},
    "multiple_regression": {"dv": "连续因变量", "predictors": "预测变量（可多个）"},
    "binary_logistic": {"dv": "二分因变量", "predictors": "预测变量"},
    "mediation": {"x": "自变量", "m": "中介变量", "y": "因变量"},
    "moderation": {"x": "自变量", "w": "调节变量", "y": "因变量"},
    "cronbach_alpha": {"items": "量表题项"},
    "chi_square": {"var1": "分类变量 1", "var2": "分类变量 2"},
    "chi_square_independence": {"var1": "分类变量 1", "var2": "分类变量 2"},
    "ancova": {"dv": "连续因变量", "iv": "分组变量", "covariate": "协变量"},
    "mann_whitney": {"dv": "因变量", "iv": "分组变量（2 组）"},
    "wilcoxon": {"dv": "因变量", "iv": "配对标识"},
    "kruskal_wallis": {"dv": "因变量", "iv": "分组变量（≥3 组）"},
    "descriptive": {"vars": "待描述变量"},
}


@dataclass
class AnalysisRecipe:
    """从方法推荐生成的可执行分析方案。"""
    method_id: str
    method_zh: str
    variable_roles: dict[str, str] = field(default_factory=dict)
    parameters: dict = field(default_factory=dict)
    assumption_checks: list[str] = field(default_factory=list)
    recommendation_id: str = ""
    confidence: str = "high"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "method_id": self.method_id,
            "method_zh": self.method_zh,
            "variable_roles": self.variable_roles,
            "parameters": self.parameters,
            "assumption_checks": self.assumption_checks,
            "recommendation_id": self.recommendation_id,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


def recommendation_to_recipe(
    rec: MethodRecommendation,
    design: ResearchDesignInput,
    recommendation_id: str = "",
) -> AnalysisRecipe:
    """将方法推荐转换为可执行分析方案。"""
    method = rec.primary_method
    roles = _METHOD_TO_VARIABLE_ROLES.get(method, {})

    params: dict = {}
    if design.n_groups > 0:
        params["n_groups"] = design.n_groups
    if design.time_points > 1:
        params["time_points"] = design.time_points
    if design.has_covariate:
        params["n_covariates"] = design.n_covariates
    if design.sample_size > 0:
        params["sample_size"] = design.sample_size

    return AnalysisRecipe(
        method_id=method,
        method_zh=rec.primary_method_zh,
        variable_roles=dict(roles),
        parameters=params,
        assumption_checks=list(rec.assumption_checks),
        recommendation_id=recommendation_id,
        confidence=rec.confidence,
        warnings=list(rec.warnings),
    )
