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
