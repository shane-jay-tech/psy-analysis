"""跨模块语义对齐：检查研究问题 ↔ 候选变量 ↔ 分析方法是否匹配。

设计原则：
- **不阻塞**：仅返回警告 + 建议，不强制修改
- **可证伪**：每条规则触发条件明确（不依赖 LLM 判断）
- **建议导向**：警告必含替代方法建议

调用：wizard 第 4 步（方法推荐）显示橙色警告卡片。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class AlignmentWarning:
    severity: str       # "warning" | "info"
    issue: str
    suggestion: str
    rule_id: str        # 规则编号，便于测试与文档

    def as_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "issue": self.issue,
            "suggestion": self.suggestion,
            "rule_id": self.rule_id,
        }


@dataclass
class AlignmentResult:
    is_aligned: bool
    warnings: List[AlignmentWarning] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "is_aligned": self.is_aligned,
            "warnings": [w.as_dict() for w in self.warnings],
        }


# ---------------------------------------------------------------------------
# 关键词库
# ---------------------------------------------------------------------------

_CAUSAL_WORDS = ["预测", "影响", "导致", "决定", "驱动", "因果", "效应"]
_DIFF_WORDS = ["差异", "比较", "对比", "高于", "低于"]
_RELATION_WORDS = ["相关", "关联", "联系", "关系"]

# 方法分类（基于 wizard 推荐的 12 种方法）
_T_TEST_METHODS = {
    "independent_ttest", "paired_ttest", "one_sample_ttest",
    "t检验", "独立样本t检验", "配对样本t检验",
}
_ANOVA_METHODS = {
    "one_way_anova", "two_way_anova", "repeated_measures_anova", "ancova",
    "anova", "方差分析",
}
_CORR_METHODS = {
    "pearson_corr", "spearman_corr", "partial_corr", "point_biserial",
    "pearson相关", "spearman相关", "相关分析",
}
_REGRESSION_METHODS = {
    "linear_regression", "multiple_regression", "hierarchical_regression",
    "regression", "回归", "回归分析",
}
_CHI_SQUARE_METHODS = {
    "chi_square", "chi_square_independence", "chi_square_gof",
    "卡方", "卡方检验",
}
_NONPARAM_METHODS = {
    "mann_whitney", "wilcoxon", "kruskal_wallis", "friedman",
    "mann-whitney u", "wilcoxon符号秩",
}
# v3.4 高级方法分类
_PARTIAL_CORR_METHODS = {
    "partial_corr", "partial_correlation", "偏相关",
}
_MEDIATION_METHODS = {
    "mediation", "中介", "中介分析", "中介效应",
}
_MODERATION_METHODS = {
    "moderation", "调节", "调节分析", "调节效应",
}
# v3.7 R15-R20 细分类（独立于 _classify_method 大类）
_REPEATED_METHODS = {
    "repeated_measures_anova", "rm_anova", "repeated", "重复测量", "重复测量anova",
}
_TWO_WAY_METHODS = {
    "two_way_anova", "factorial_anova", "二因素anova", "两因素anova", "两因素方差分析",
}
_MULTI_REGRESSION_METHODS = {
    "multiple_regression", "hierarchical_regression", "多元回归", "层次回归",
}
_FACTOR_METHODS = {
    "efa", "exploratory_factor_analysis", "factor_analysis", "探索性因子分析", "因子分析",
}


def _classify_method(method: str) -> str:
    """返回方法所属大类。"""
    if not method:
        return "unknown"
    m = method.strip().lower()
    if m in _PARTIAL_CORR_METHODS:
        return "partial_corr"
    if m in _MEDIATION_METHODS:
        return "mediation"
    if m in _MODERATION_METHODS:
        return "moderation"
    if m in _T_TEST_METHODS:
        return "t_test"
    if m in _ANOVA_METHODS:
        return "anova"
    if m in _CORR_METHODS:
        return "corr"
    if m in _REGRESSION_METHODS:
        return "regression"
    if m in _CHI_SQUARE_METHODS:
        return "chi_square"
    if m in _NONPARAM_METHODS:
        return "nonparam"
    return "unknown"


def _classify_var(var_name: str, hint_categorical: bool = False) -> str:
    """根据变量名启发式判断类型：categorical | continuous。

    简单规则：含「组别/性别/类型/水平/X 类」等词 → categorical；
            否则视为 continuous（保守假设）。
    """
    if not var_name:
        return "unknown"
    cat_keywords = ["组别", "性别", "类型", "水平", "类别", "分组", "条件",
                     "level", "group", "category", "type"]
    for kw in cat_keywords:
        if kw in var_name.lower():
            return "categorical"
    return "continuous"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def check_alignment(
    research_q: str,
    candidate_vars: Optional[Dict[str, Any]],
    planned_method: str,
) -> AlignmentResult:
    """检查研究问题、候选变量、分析方法三者是否对齐。

    返回 AlignmentResult.warnings 列表（可能为空）。
    """
    warnings: List[AlignmentWarning] = []

    rq = (research_q or "").strip()
    method_kind = _classify_method(planned_method)
    cv = candidate_vars or {}
    dvs = cv.get("dependent_vars") or []
    ivs = cv.get("independent_vars") or []
    n_dv = len([v for v in dvs if v])
    n_iv = len([v for v in ivs if v])

    # 变量类型识别（启发式）
    iv_types = [_classify_var(v) for v in ivs if v]
    dv_types = [_classify_var(v) for v in dvs if v]
    n_iv_categorical = sum(1 for t in iv_types if t == "categorical")
    n_iv_continuous = sum(1 for t in iv_types if t == "continuous")
    n_dv_continuous = sum(1 for t in dv_types if t == "continuous")
    n_dv_categorical = sum(1 for t in dv_types if t == "categorical")

    # ----- 规则 1：方法 vs 变量类型 -----
    # R1: 多个连续变量但选 t 检验 → 应考虑相关
    if method_kind == "t_test" and n_iv_continuous >= 1 and n_dv_continuous >= 1 \
            and n_iv_categorical == 0:
        warnings.append(AlignmentWarning(
            severity="warning",
            issue="变量都是连续型（无分组变量），但选择了 t 检验。",
            suggestion="t 检验需要一个分类分组变量。建议改为「相关分析（Pearson/Spearman）」。",
            rule_id="R1_TTEST_NO_CATEGORICAL",
        ))

    # R2: 一个分类 + 一个连续，但选相关分析 → 应考虑 t 检验/ANOVA
    if method_kind == "corr" and n_iv_categorical >= 1 and n_dv_continuous >= 1:
        warnings.append(AlignmentWarning(
            severity="warning",
            issue="自变量含分类变量，但选择了相关分析。",
            suggestion="相关分析适合两个连续变量。建议改为「t 检验（2 组）」或「ANOVA（3 组以上）」。",
            rule_id="R2_CORR_WITH_CATEGORICAL_IV",
        ))

    # R3: 两个分类变量但选 t 检验 → 应考虑卡方
    if method_kind == "t_test" and n_iv_categorical >= 1 and n_dv_categorical >= 1:
        warnings.append(AlignmentWarning(
            severity="warning",
            issue="DV 和 IV 都是分类变量，但选择了 t 检验。",
            suggestion="比较两个分类变量的关联，应使用「卡方检验」。",
            rule_id="R3_TTEST_BOTH_CATEGORICAL",
        ))

    # ----- 规则 2：方向性词与方法的匹配 -----
    has_causal = any(w in rq for w in _CAUSAL_WORDS)
    has_diff = any(w in rq for w in _DIFF_WORDS)
    has_relation = any(w in rq for w in _RELATION_WORDS)

    # R4: 因果词 + 相关分析 → 警告"相关无法支持因果"
    if has_causal and method_kind == "corr":
        warnings.append(AlignmentWarning(
            severity="warning",
            issue="研究问题含「预测/影响」等因果词，但方法是相关分析。",
            suggestion="相关分析仅显示关联，无法支持因果推论。讨论时应避免用因果语言；如需因果证据，"
                        "考虑实验设计（操纵 IV）或回归分析（控制混淆）。",
            rule_id="R4_CAUSAL_WORD_WITH_CORR",
        ))

    # R5: 差异词 + 回归 → 提示
    if has_diff and method_kind == "regression":
        warnings.append(AlignmentWarning(
            severity="info",
            issue="研究问题含「差异/比较」等词，但方法是回归。",
            suggestion="差异分析建议用 t 检验（2 组）或 ANOVA（≥3 组）；如确需控制混淆变量，"
                        "可保留回归但说明 IV 已编码为分类变量（哑变量）。",
            rule_id="R5_DIFF_WORD_WITH_REGRESSION",
        ))

    # R6: 关系词 + t 检验 → 提示
    if has_relation and method_kind == "t_test" and n_iv_categorical == 0:
        warnings.append(AlignmentWarning(
            severity="info",
            issue="研究问题含「相关/关系」等词，但方法是 t 检验。",
            suggestion="探究关系建议用相关或回归分析；t 检验适合比较两组均值差异。",
            rule_id="R6_RELATION_WORD_WITH_TTEST",
        ))

    # ----- 规则 3：变量数量 vs 方法 -----
    # R7: 选 ANOVA 但只有 1 个 IV 且 IV 不是分类 → 警告
    if method_kind == "anova" and n_iv == 1 and iv_types and iv_types[0] != "categorical":
        warnings.append(AlignmentWarning(
            severity="warning",
            issue="ANOVA 需要分类型自变量，当前 IV 似乎是连续变量。",
            suggestion="若 IV 为连续变量，建议用相关或回归；若 IV 实为分类变量，请明确变量名（如「组别」）。",
            rule_id="R7_ANOVA_CONTINUOUS_IV",
        ))

    # R8: 卡方 但变量不全是分类 → 警告
    if method_kind == "chi_square" and (n_iv_continuous + n_dv_continuous) > 0:
        warnings.append(AlignmentWarning(
            severity="warning",
            issue="卡方检验要求所有变量为分类变量，但你的变量列表中含连续变量。",
            suggestion="若 DV 为连续变量，应改用 t 检验/ANOVA；若 IV 为连续变量，应改用回归。",
            rule_id="R8_CHISQUARE_WITH_CONTINUOUS",
        ))

    # ----- v3.4 规则 4：高级方法的变量结构校验 -----
    covariates = cv.get("covariates") or []
    n_cov = len([c for c in covariates if c])
    grouping_var = cv.get("grouping_var") or ""
    moderator = cv.get("moderator") or ""    # 可选：UI 可让用户填
    mediator = cv.get("mediator") or ""      # 可选

    # R9: 偏相关分析需指定控制变量
    if method_kind == "partial_corr" and n_cov == 0:
        warnings.append(AlignmentWarning(
            severity="warning",
            issue="偏相关分析需要指定一个或多个控制变量（covariates），但当前未填写。",
            suggestion="请在「候选变量」中明确控制变量；若无控制变量需求，应改用普通相关分析。",
            rule_id="R9_PARTIAL_CORR_NO_CONTROL",
        ))

    # R10: 中介分析需 X、M、Y 三个不同的变量
    if method_kind == "mediation":
        all_vars = (
            [v for v in dvs if v]
            + [v for v in ivs if v]
            + ([mediator] if mediator else [])
        )
        unique_vars = {v.strip().lower() for v in all_vars if v}
        # 至少需要 3 个不同变量；或 IV/DV 与中介相同
        x_eq_y = bool(ivs and dvs and ivs[0].strip().lower() == dvs[0].strip().lower())
        x_eq_m = bool(ivs and mediator and ivs[0].strip().lower() == mediator.strip().lower())
        if x_eq_y or x_eq_m or len(unique_vars) < 3:
            warnings.append(AlignmentWarning(
                severity="warning",
                issue="中介分析需要 X（自变量）、M（中介变量）、Y（因变量）三个不同的变量。",
                suggestion="请确认你已选择三个不同的变量；若仅有两个变量，应改用相关或回归分析。",
                rule_id="R10_MEDIATION_NEEDS_THREE_VARS",
            ))

    # R11: 调节分析中调节变量为二分变量时提示
    if method_kind == "moderation":
        # 调节变量优先看 grouping_var；若无，看 moderator 字段
        mod_var = moderator or grouping_var
        # 简单启发式：变量名含"二分/dichotomous/性别/真假"等 → 视为二分
        is_dichotomous = bool(mod_var) and any(
            kw in mod_var.lower()
            for kw in ["二分", "dichotomous", "性别", "真假", "yes/no", "0/1"]
        )
        if is_dichotomous:
            warnings.append(AlignmentWarning(
                severity="info",
                issue=f"调节变量「{mod_var}」似乎是二分变量。",
                suggestion="调节变量为二分时，等同于分组分析；如确为分组检查，也可使用分组回归（按组别分别跑回归）。",
                rule_id="R11_MODERATION_DICHOTOMOUS_W",
            ))

    # ----- v3.7 规则 5：高级统计方法的报告完整性提示 -----
    raw_m = (planned_method or "").strip().lower()

    # R12: 偏相关 + 控制变量 ≥ 3 → 多重比较问题提示
    if method_kind == "partial_corr" and n_cov >= 3:
        warnings.append(AlignmentWarning(
            severity="info",
            issue=f"偏相关分析使用了 {n_cov} 个控制变量，可能存在多重控制带来的不稳定。",
            suggestion="控制变量越多越损失自由度；建议仅保留理论上必须控制的变量；"
                        "若做多组偏相关比较，请用 Bonferroni / FDR 校正 p 值。",
            rule_id="R12_PARTIAL_CORR_MANY_CONTROLS",
        ))

    # R13: 多重回归（IV ≥ 3）→ 必报 VIF（共线性诊断）
    if (method_kind == "regression" and (n_iv >= 3 or raw_m in _MULTI_REGRESSION_METHODS)):
        warnings.append(AlignmentWarning(
            severity="info",
            issue=f"多重回归含 {max(n_iv, 2)} 个自变量，需检查多重共线性。",
            suggestion="必报 VIF（方差膨胀因子）；VIF > 10 提示严重共线性，"
                        "考虑剔除变量或使用岭回归 / Lasso。",
            rule_id="R13_MULTI_REGRESSION_VIF",
        ))

    # R14: 同时填 mediator 和 moderator → 有调节的中介
    if mediator and moderator:
        warnings.append(AlignmentWarning(
            severity="info",
            issue="同时存在中介变量 M 和调节变量 W，可能是「有调节的中介」(moderated mediation)。",
            suggestion="若 M 仅在某些 W 水平下中介，应使用 PROCESS Model 7/14/58 等组合模型；"
                        "需报告条件间接效应及其 95% bootstrap CI。",
            rule_id="R14_MED_MOD_COMBO",
        ))

    # R15: 重复测量 ANOVA → 球形检验提示
    if raw_m in _REPEATED_METHODS or "repeated" in raw_m or "重复测量" in raw_m:
        warnings.append(AlignmentWarning(
            severity="info",
            issue="重复测量 ANOVA 假设球形性 (sphericity)，违反时 F 统计量偏高。",
            suggestion="必报 Mauchly's W；若 p < .05，使用 Greenhouse-Geisser 或 Huynh-Feldt 校正。",
            rule_id="R15_REPEATED_SPHERICITY",
        ))

    # R16: 两因素 / 析因 ANOVA → 必报交互效应
    is_two_way = (raw_m in _TWO_WAY_METHODS) or \
                  (method_kind == "anova" and n_iv_categorical >= 2)
    if is_two_way:
        warnings.append(AlignmentWarning(
            severity="info",
            issue="两因素 ANOVA 设计：交互效应是核心假设。",
            suggestion="必报 A × B 交互的 F 与 p；交互显著时不要单独解释主效应；"
                        "建议绘制交互效应图（estimated marginal means）便于解读。",
            rule_id="R16_TWOWAY_INTERACTION",
        ))

    # R17: 嵌套数据提示（IV/DV 名含「学校/班级/团队/医院/教师/班主任」）
    nested_keywords = ["学校", "班级", "团队", "医院", "教师", "班主任", "校区", "school", "class"]
    nested_hits = [v for v in (ivs + dvs + covariates)
                    if v and any(kw in v.lower() for kw in nested_keywords)]
    if nested_hits and method_kind in ("regression", "t_test", "anova", "corr"):
        warnings.append(AlignmentWarning(
            severity="info",
            issue=f"变量「{nested_hits[0]}」可能是组别层数据，存在数据嵌套结构（学生在班级内、班级在学校内）。",
            suggestion="嵌套数据违反独立性假设，建议使用多层线性模型 (HLM/MLM) "
                        "或在回归中加入聚类稳健标准误（cluster-robust SE）。",
            rule_id="R17_NESTED_DATA",
        ))

    # R18: 非参数检验 → 描述统计应用中位数 + IQR
    if method_kind == "nonparam":
        warnings.append(AlignmentWarning(
            severity="info",
            issue="非参数检验不假设正态分布，对应的描述统计也应换。",
            suggestion="不要用 M ± SD（均值 ± 标准差）；改用 Mdn (中位数) 与 IQR (四分位距) "
                        "或 Q1-Q3。报告效应量也用 r = Z/√N 而非 Cohen's d。",
            rule_id="R18_NONPARAM_DESCRIPTIVE",
        ))

    # R19: 因子分析 → 必报 KMO + Bartlett 球形检验前提
    if raw_m in _FACTOR_METHODS or "factor" in raw_m or "因子分析" in raw_m:
        warnings.append(AlignmentWarning(
            severity="info",
            issue="探索性因子分析 (EFA) 有适用性前提。",
            suggestion="必报 KMO ≥ .60（< .50 不适合做 EFA）+ Bartlett 球形检验 p < .05；"
                        "因子载荷一般 ≥ .40 才纳入；旋转方法（varimax / promax）需说明理由。",
            rule_id="R19_FACTOR_PRECONDITION",
        ))

    # R20: 卡方检验 → 提示期望频数检查
    if method_kind == "chi_square":
        warnings.append(AlignmentWarning(
            severity="info",
            issue="卡方检验要求期望频数 ≥ 5（2×2 表中 ≥ 5；其他表 ≥ 80% 单元格 ≥ 5）。",
            suggestion="若期望频数过小，2×2 表用 Fisher 精确检验；"
                        "更大的表用 Monte Carlo 模拟 p 值或合并相邻类别。报告效应量 φ / Cramer's V。",
            rule_id="R20_CHISQUARE_LOW_EXPECTED",
        ))

    # v3.7: is_aligned 仅看 warning 级（info 是报告完整性提醒，不算"不对齐"）
    has_warning_severity = any(w.severity == "warning" for w in warnings)
    return AlignmentResult(
        is_aligned=(not has_warning_severity),
        warnings=warnings,
    )
