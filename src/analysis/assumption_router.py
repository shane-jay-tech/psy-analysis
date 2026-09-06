"""假设违反路由仲裁器。

行业共识（R afex / pingouin / JASP / jamovi / SPSS）：
跨检验族不做静默切换。本模块只**计算建议**，不修改 effective test_type。
UI 渲染层负责显示横幅 + 一键切换按钮。

Hoenig & Heisey 2001：post-hoc observed power 是循环论证 anti-pattern；
本模块输出的 RouteDecision 不参与 power 决策。

n<20 / n>5000 时 hard_route_allowed=False：Shapiro-Wilk 在小样本检测力低、
在大样本会拒鸡毛蒜皮，此时假设检验本身不可信，禁止用户一键切换。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

import pandas as pd

from .assumptions import AssumptionResult


# 跨族切换映射：当原检验的核心假设违反时，建议改用的非参数 / Welch 等价
# 仅在 hard_route_allowed=True 时让 UI 显示切换按钮
_NORMALITY_FALLBACK = {
    "independent_ttest": ("mann_whitney", "Mann-Whitney U（独立两组非参数）"),
    "paired_ttest": ("wilcoxon", "Wilcoxon 符号秩（配对非参数）"),
    "one_sample_ttest": ("wilcoxon", "Wilcoxon 单样本符号秩"),
    "one_way_anova": ("kruskal_wallis", "Kruskal-Wallis（多组非参数）"),
    "pearson_corr": ("spearman_corr", "Spearman 等级相关"),
}

_HOMOGENEITY_FALLBACK = {
    "one_way_anova": ("welch_anova", "Welch ANOVA（不假设方差齐性）"),
}

_SPHERICITY_NOTE = {
    "repeated_anova": (
        "friedman",
        "Friedman 检验（球形假设违反且严重时；通常 GG 校正已足够）",
    ),
}


@dataclass
class RouteDecision:
    """路由决策（仅建议，不修改 effective test_type）。

    Attributes:
        original_test: 原始 test_type。
        suggested_test: 建议改用的 test_type（None 表示无建议）。
        suggested_test_zh: 建议检验的中文标签。
        reasons: 触发建议的原因列表（每项是一句中文）。
        violated_assumptions: 违反的假设名（"normality" / "homogeneity" / "sphericity"）。
        hard_route_allowed: 是否允许 UI 提供一键切换。
            False 时 UI 仅显示警告，禁用切换按钮（小/大样本假设检验不可信）。
        hard_route_reason: hard_route_allowed=False 的原因（"小样本检测力不足"等）。
        sample_size: 用于决策的样本量 n。
    """

    original_test: str
    suggested_test: Optional[str] = None
    suggested_test_zh: str = ""
    reasons: List[str] = field(default_factory=list)
    violated_assumptions: List[str] = field(default_factory=list)
    hard_route_allowed: bool = True
    hard_route_reason: str = ""
    sample_size: int = 0

    @property
    def has_suggestion(self) -> bool:
        return self.suggested_test is not None and self.suggested_test != self.original_test


def _extract_n(df: pd.DataFrame, plan, output: Dict[str, Any]) -> int:
    """从 plan / df / output 中估计样本量。"""
    # 1) 优先用 descriptive 表中已计算的 N
    desc = output.get("descriptive")
    if isinstance(desc, pd.DataFrame) and "N" in desc.columns:
        try:
            return int(desc["N"].sum())
        except Exception:
            pass
    # 2) 用 plan 涉及的列在 df 中的非空行数
    cols = []
    cols += list(getattr(plan, "dependent_vars", []) or [])
    cols += list(getattr(plan, "independent_vars", []) or [])
    cols = [c for c in cols if c and c in df.columns]
    if cols:
        return int(df[cols].dropna().shape[0])
    return int(df.shape[0])


def _normality_violated(output: Dict[str, Any]) -> bool:
    """检查 output["assumptions"]["normality"] 中是否有任意一组拒绝正态。"""
    norm = output.get("assumptions", {}).get("normality")
    if isinstance(norm, AssumptionResult):
        return norm.passed is False
    if isinstance(norm, dict):
        # check_normality_groups 返回的是 {group_name: AssumptionResult}
        for v in norm.values():
            if isinstance(v, AssumptionResult) and v.passed is False:
                return True
            if isinstance(v, dict) and v.get("passed") is False:
                return True
    return False


def _homogeneity_violated(output: Dict[str, Any]) -> bool:
    homo = output.get("assumptions", {}).get("homogeneity")
    if isinstance(homo, AssumptionResult):
        return homo.passed is False
    if isinstance(homo, dict):
        return homo.get("passed") is False
    # 也可能藏在 result 里
    result = output.get("result")
    if result is not None:
        ah = getattr(result, "assumption_homogeneity", None)
        if isinstance(ah, dict):
            return ah.get("passed") is False
    return False


def _sphericity_violated(output: Dict[str, Any]) -> bool:
    sph = output.get("assumptions", {}).get("sphericity")
    if isinstance(sph, AssumptionResult):
        return sph.passed is False
    if isinstance(sph, dict):
        return sph.get("passed") is False
    result = output.get("result")
    if result is not None:
        asph = getattr(result, "assumption_sphericity", None)
        if isinstance(asph, dict):
            return asph.get("passed") is False
    return False


def check_route(df: pd.DataFrame, plan, output: Dict[str, Any]) -> RouteDecision:
    """检查 output 中的假设结果，返回路由建议（不修改 output 内任何字段）。

    调用约定：必须在 handler 跑完之后调用，因为 assumption 字段是 handler 填的。
    """
    test_type = getattr(plan, "test_type", "") or output.get("test_type", "")
    n = _extract_n(df, plan, output)

    decision = RouteDecision(original_test=test_type, sample_size=n)

    # n 边界：Shapiro 在小样本检测力不足、在大样本拒鸡毛蒜皮
    if n < 20:
        decision.hard_route_allowed = False
        decision.hard_route_reason = (
            f"样本量过小 (n={n})，正态性检验检测力不足，建议结果不可靠，禁止一键切换。"
        )
    elif n > 5000:
        decision.hard_route_allowed = False
        decision.hard_route_reason = (
            f"样本量过大 (n={n})，正态性检验对鸡毛蒜皮的偏差过敏感，建议结果不可靠，"
            "禁止一键切换。"
        )

    # 球形违反（重复测量）
    if _sphericity_violated(output) and test_type in _SPHERICITY_NOTE:
        sugg, zh = _SPHERICITY_NOTE[test_type]
        decision.suggested_test = sugg
        decision.suggested_test_zh = zh
        decision.violated_assumptions.append("sphericity")
        decision.reasons.append(
            "球形假设违反；本系统已自动应用 Greenhouse-Geisser 校正，"
            "如校正后仍不放心可改用非参数 Friedman 检验。"
        )

    # 方差齐性违反
    if _homogeneity_violated(output) and test_type in _HOMOGENEITY_FALLBACK:
        sugg, zh = _HOMOGENEITY_FALLBACK[test_type]
        decision.suggested_test = sugg
        decision.suggested_test_zh = zh
        decision.violated_assumptions.append("homogeneity")
        decision.reasons.append(
            "Levene 检验显示方差不齐；建议改用 Welch ANOVA（独立 t 检验已自动 Welch 校正，无需切换）。"
        )

    # 正态性违反
    if _normality_violated(output) and test_type in _NORMALITY_FALLBACK:
        sugg, zh = _NORMALITY_FALLBACK[test_type]
        # 正态优先级低于方差齐性建议（如果两者都违反，UI 优先显示方差齐性）
        if decision.suggested_test is None:
            decision.suggested_test = sugg
            decision.suggested_test_zh = zh
        decision.violated_assumptions.append("normality")
        decision.reasons.append(
            f"Shapiro-Wilk / KS 检验显示数据不服从正态分布；如样本量足够，"
            f"建议改用非参数检验「{zh}」。注意：非参数检验的零假设与参数检验不完全等价。"
        )

    return decision


def to_dict(decision: RouteDecision) -> Dict[str, Any]:
    """RouteDecision → 可 JSON 序列化的 dict（用于快照导出）。"""
    return {
        "original_test": decision.original_test,
        "suggested_test": decision.suggested_test,
        "suggested_test_zh": decision.suggested_test_zh,
        "reasons": list(decision.reasons),
        "violated_assumptions": list(decision.violated_assumptions),
        "hard_route_allowed": decision.hard_route_allowed,
        "hard_route_reason": decision.hard_route_reason,
        "sample_size": decision.sample_size,
        "has_suggestion": decision.has_suggestion,
    }


# ---------------------------------------------------------------------------
# 方法假设集注册表（覆盖面补齐：回归 / logistic / 多变量 / SEM 族）
#
# 约束：每条假设只允许两种 kind——
#   "existing"     指向 assumptions.py 既有 check 实现（check_name 为函数名）；
#   "placeholder"  系统尚无对应实现，路由到通用提示（note），绝不新造统计计算。
# 注册名与 runner.py @_register 完全对齐。
# ---------------------------------------------------------------------------

from .assumptions import (  # noqa: E402  (就近引用，便于核对既有实现清单)
    check_homogeneity,
    check_normality,
    check_normality_groups,
    check_sphericity,
)

_EXISTING = "existing"
_PLACEHOLDER = "placeholder"

_EXISTING_CHECK_NAMES = frozenset({
    "check_normality", "check_normality_groups", "check_homogeneity", "check_sphericity",
})

_GEN_NOTE = "通用提示：请结合数据背景人工核查该假设；系统暂无自动检验实现。"


@dataclass(frozen=True)
class MethodAssumption:
    """单个方法学假设的路由条目。"""
    name: str                 # 假设名（中文，可含英文术语）
    kind: str                 # _EXISTING | _PLACEHOLDER
    check_name: str = ""      # kind=_EXISTING 时为既有函数名；占位为空
    note: str = ""            # 应用说明 / 通用提示


@dataclass(frozen=True)
class MethodAssumptionSet:
    """一个 test_type 的完整假设集合（只读）。"""
    test_type: str
    assumptions: tuple

    @property
    def existing_checks(self) -> tuple:
        return tuple(a for a in self.assumptions if a.kind == _EXISTING)

    @property
    def placeholders(self) -> tuple:
        return tuple(a for a in self.assumptions if a.kind == _PLACEHOLDER)


def _ex(name: str, check_name: str, note: str = "") -> MethodAssumption:
    return MethodAssumption(name=name, kind=_EXISTING, check_name=check_name, note=note)


def _ph(name: str, note: str = _GEN_NOTE) -> MethodAssumption:
    return MethodAssumption(name=name, kind=_PLACEHOLDER, note=note)


_METHOD_ASSUMPTIONS: Dict[str, tuple] = {
    # ---- 回归族 ----
    "linear_regression": (
        _ex("残差正态性", "check_normality", "应用于回归残差而非原始因变量"),
        _ph("因变量与自变量的线性关系"),
        _ph("残差同方差性（异方差诊断）"),
        _ph("观测间相互独立"),
    ),
    "multiple_regression": (
        _ex("残差正态性", "check_normality", "应用于回归残差而非原始因变量"),
        _ph("自变量间无严重多重共线性（VIF）"),
        _ph("残差同方差性（异方差诊断）"),
        _ph("观测间相互独立"),
        _ph("样本量充足（常见口径每预测变量 ≥10–20 例）"),
    ),
    "hierarchical_regression": (
        _ex("残差正态性", "check_normality", "应用于回归残差而非原始因变量"),
        _ph("自变量间无严重多重共线性（VIF）"),
        _ph("嵌套模型间可比（逐层增变量，其余设定不变）"),
        _ph("残差同方差性（异方差诊断）"),
    ),
    # ---- logistic 族（注意：不假设因变量或残差正态）----
    "binary_logistic": (
        _ph("连续自变量与 logit 线性（Box-Tidwell）"),
        _ph("自变量间无严重多重共线性"),
        _ph("观测间相互独立"),
        _ph("因变量为真二分类"),
    ),
    "multinomial_logistic": (
        _ph("连续自变量与 logit 线性"),
        _ph("自变量间无严重多重共线性"),
        _ph("观测间相互独立"),
        _ph("因变量类别互斥且穷尽"),
    ),
    "ordinal_logistic": (
        _ph("比例优势（平行线）假设"),
        _ph("自变量间无严重多重共线性"),
        _ph("观测间相互独立"),
    ),
    # ---- 多变量 / 混合族 ----
    "manova": (
        _ph("多元正态性（各因变量联合正态）"),
        _ph("组间协方差矩阵齐性（Box's M）"),
        _ex("各组方差齐性（逐因变量）", "check_homogeneity", "对每个因变量分别核查"),
        _ph("因变量间存在线性相关"),
        _ph("无极端多元异常值（如 Mahalanobis 距离）"),
    ),
    "mixed_anova": (
        _ex("正态性", "check_normality", "组内水平上逐组核查"),
        _ex("组间方差齐性", "check_homogeneity"),
        _ex("球形假设", "check_sphericity", "违反时系统自动 Greenhouse-Geisser 校正"),
        _ph("观测间相互独立（被试间）"),
    ),
    "two_way_anova": (
        _ex("正态性", "check_normality", "逐单元格（iv1×iv2 组合）核查"),
        _ex("单元格方差齐性", "check_homogeneity", "逐单元格核查；双因素无非参数等价，违反时建议谨慎解读或考虑数据变换"),
        _ph("观测间相互独立（被试间）"),
        _ph("各单元格样本量充足且无空单元格"),
    ),
    "hlm": (
        _ex("残差正态性", "check_normality", "应用于固定效应残差"),
        _ph("随机效应近似正态"),
        _ph("各层级样本量充足（每层效应 ≥ 合理观测数）"),
        _ph("残差同方差性（按层级分别核查）"),
    ),
    # ---- SEM 族 ----
    "sem": (
        _ph("观测变量多元正态性"),
        _ph("样本量充足（常见口径 ≥ 10–20 × 自由参数）"),
        _ph("模型可识别"),
        _ph("指标间无严重多重共线性"),
    ),
    # ---- 相关族补充 ----
    "partial_corr": (
        _ex("双变量正态性", "check_normality", "控制变量后残差化的两变量"),
        _ph("变量间线性关系"),
        _ph("样本量充足"),
    ),
    "point_biserial": (
        _ph("二分变量为真二分（非人为切分）"),
        _ex("连续变量正态性", "check_normality"),
        _ph("两组方差齐性与线性关系"),
    ),
    # ---- 卡方族 ----
    "chi_square_gof": (
        _ph("期望频数充足（各单元格期望 ≥ 5）"),
        _ph("观测间相互独立"),
        _ph("类别互斥且穷尽"),
    ),
    "chi_square_independence": (
        _ph("期望频数充足（各单元格期望 ≥ 5）"),
        _ph("观测间相互独立"),
        _ph("类别互斥且穷尽"),
    ),
}


def get_assumption_set(test_type: str) -> Optional[MethodAssumptionSet]:
    """返回该 test_type 的方法学假设集合；未注册的方法返回 None（默认分支不变）。"""
    assumptions = _METHOD_ASSUMPTIONS.get(test_type)
    if assumptions is None:
        return None
    return MethodAssumptionSet(test_type=test_type, assumptions=assumptions)


def describe_assumption_routes() -> Dict[str, Dict[str, int]]:
    """注册表覆盖画像：每法 existing/placeholder 计数（供覆盖报告使用）。"""
    return {
        name: {
            "existing": sum(1 for a in assumptions if a.kind == _EXISTING),
            "placeholder": sum(1 for a in assumptions if a.kind == _PLACEHOLDER),
        }
        for name, assumptions in _METHOD_ASSUMPTIONS.items()
    }
