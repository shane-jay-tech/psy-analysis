"""上游科研流程模块（v3.2）：选题漏斗 + AI 苏格拉底 + ResearchTier。

`tier`         — 用户分层（BEGINNER/ADVANCED）
`topic_funnel` — 5 阶段状态机（兴趣→现象→变量→可研究性→问题陈述）
`socratic_engine` — 反问引擎（基于 ai_tutor 扩展）
`feasibility_check` — 可证伪 + 可测量检查
`topic_funnel_kb` — 范例库 + Fallback 模板 + Few-shot
"""

from .tier import (
    ResearchTier,
    detect_tier_from_input,
    get_active_tier,
    set_active_tier,
    tier_at_least,
)

__all__ = [
    "ResearchTier",
    "detect_tier_from_input",
    "get_active_tier",
    "set_active_tier",
    "tier_at_least",
]
