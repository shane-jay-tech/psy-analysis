"""ResearchTier：用户分层（本科/研究生/auto）。

设计参考 D:\\my-quant-system-v8\\core\\config.py 的 SystemTier 模式（不依赖、不导入）。

BEGINNER  → 走完整 5 阶段漏斗
ADVANCED  → 直接跳过漏斗（v3.2），完整折叠模式 v3.3 实现
AUTO      → 根据首次输入文本启发式判断
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------

class ResearchTier(str, Enum):
    BEGINNER = "beginner"
    ADVANCED = "advanced"
    AUTO = "auto"


_TIER_ORDER = [ResearchTier.BEGINNER, ResearchTier.ADVANCED]


# ---------------------------------------------------------------------------
# 启发式分层检测
# ---------------------------------------------------------------------------

# ADVANCED 触发关键词：本科生通常不会熟练使用这些术语
_ADVANCED_KEYWORDS = {
    "假设", "中介", "调节", "操作化", "构念", "潜变量",
    "效应量", "信度", "效度", "结构方程", "SEM", "CFA",
    "层级回归", "多层线性", "HLM", "纵向数据",
    "预注册", "OSF", "样本量计算", "power analysis", "效力",
    "理论框架", "文献综述", "gap", "实证研究",
}

# 文本长度阈值：超过此长度视为详细描述
_ADVANCED_LENGTH_THRESHOLD = 150


def detect_tier_from_input(text: str) -> ResearchTier:
    """根据首次输入文本启发式判断 tier。

    规则：
    - 长度 ≥ 150 字 且 含 ≥1 个 ADVANCED 关键词 → ADVANCED
    - 含 ≥2 个 ADVANCED 关键词（不限长度）→ ADVANCED
    - 否则 → BEGINNER
    """
    if not isinstance(text, str) or not text.strip():
        return ResearchTier.BEGINNER

    matched = sum(1 for kw in _ADVANCED_KEYWORDS if kw.lower() in text.lower())
    if matched >= 2:
        return ResearchTier.ADVANCED
    if len(text) >= _ADVANCED_LENGTH_THRESHOLD and matched >= 1:
        return ResearchTier.ADVANCED
    return ResearchTier.BEGINNER


# ---------------------------------------------------------------------------
# Session / workspace 读写
# ---------------------------------------------------------------------------

def get_active_tier(session_state: Any = None) -> ResearchTier:
    """从 session_state 中读取当前 tier。缺失时返回 BEGINNER。"""
    if session_state is None:
        try:
            import streamlit as st
            session_state = st.session_state
        except Exception:
            return ResearchTier.BEGINNER

    # 优先从 upstream_state 读
    try:
        from src.utils.workspace import get_upstream_state
        upstream = get_upstream_state(session_state)
        raw = upstream.get("tier", "beginner")
    except Exception:
        raw = session_state.get("upstream_state", {}).get("tier", "beginner") \
            if isinstance(session_state.get("upstream_state"), dict) else "beginner"

    return _coerce_tier(raw)


def set_active_tier(session_state: Any, tier: ResearchTier | str) -> None:
    """写入 tier 到 upstream_state。"""
    coerced = _coerce_tier(tier)
    try:
        from src.utils.workspace import get_upstream_state
        state = get_upstream_state(session_state)
        state["tier"] = coerced.value
    except Exception:
        # 兜底：直接写
        if not isinstance(session_state.get("upstream_state"), dict):
            session_state["upstream_state"] = {}
        session_state["upstream_state"]["tier"] = coerced.value


def _coerce_tier(value: Any) -> ResearchTier:
    """容错地把任意值转成 ResearchTier（默认 BEGINNER）。"""
    if isinstance(value, ResearchTier):
        return value
    if isinstance(value, str):
        v = value.lower().strip()
        for tier in ResearchTier:
            if tier.value == v:
                return tier
    return ResearchTier.BEGINNER


# ---------------------------------------------------------------------------
# 比较
# ---------------------------------------------------------------------------

def tier_at_least(min_tier: ResearchTier | str, current: ResearchTier | str) -> bool:
    """current >= min_tier？AUTO 视为 BEGINNER 等级。"""
    cur = _coerce_tier(current)
    minimum = _coerce_tier(min_tier)
    if cur == ResearchTier.AUTO:
        cur = ResearchTier.BEGINNER
    if minimum == ResearchTier.AUTO:
        minimum = ResearchTier.BEGINNER
    return _TIER_ORDER.index(cur) >= _TIER_ORDER.index(minimum)
