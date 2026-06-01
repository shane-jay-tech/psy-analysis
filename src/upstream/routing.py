"""上游/向导路由配置表（v3.3）。

设计目标：
- **显式优于隐式**：所有合法路由组合在 ROUTING_TABLE 中明确列出
- **防止组合爆炸**：增加新维度（如 v3.4 加入 phase="literature"）时强制更新表
- **未匹配明确报错**：而非静默 fallback 到默认行为

路由维度：
- undergrad_mode: bool — 是否在本科论文模式
- phase: str        — funnel | wizard | done（v3.3）；未来可扩展
- tier: str         — beginner | advanced

handler 标识符（字符串而非函数引用，避免循环 import）：
- "funnel_beginner"          → render_funnel
- "funnel_advanced"          → render_advanced_skip_form
- "wizard"                   — 现有 render_undergrad_wizard（不区分 tier）
- "non_undergrad"            — 走 app.py 主流程（数据分析/问卷/实验/论文）

调用方式（在 app.py）：
    handler_id = resolve_route(undergrad_mode, phase, tier)
    if handler_id == "funnel_beginner":
        from src.ui.upstream_panel import render_funnel
        render_funnel()
    elif ...
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# 路由配置表
# ---------------------------------------------------------------------------

# Key: (undergrad_mode, phase, tier)
# Value: handler_id (字符串)
ROUTING_TABLE: Dict[Tuple[bool, str, str], str] = {
    # 本科论文模式 + 漏斗 phase
    (True, "funnel", "beginner"):              "funnel_beginner",
    (True, "funnel", "advanced"):              "funnel_advanced",

    # v3.4 本科论文模式 + 文献综述工作台 phase
    (True, "literature_review", "beginner"):   "literature_review_beginner",
    (True, "literature_review", "advanced"):   "literature_review_advanced",

    # 本科论文模式 + wizard phase（不区分 tier，wizard 同一套）
    (True, "wizard", "beginner"):              "wizard",
    (True, "wizard", "advanced"):              "wizard",

    # 本科论文模式 + done phase（暂同 wizard 行为）
    (True, "done", "beginner"):                "wizard",
    (True, "done", "advanced"):                "wizard",
}


_VALID_PHASES = {"funnel", "literature_review", "wizard", "done"}
_VALID_TIERS = {"beginner", "advanced"}


# v3.4 phase 生命周期：funnel → literature_review（可选）→ wizard → done
_PHASE_LIFECYCLE = ["funnel", "literature_review", "wizard", "done"]


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------

class RouteNotFoundError(Exception):
    """无法解析的路由组合（防止静默 fallback）。"""
    pass


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def resolve_route(
    undergrad_mode: bool,
    phase: Optional[str],
    tier: Optional[str],
) -> str:
    """解析路由组合 → handler_id。

    Args:
        undergrad_mode: 是否在本科论文模式
        phase: funnel | wizard | done
        tier: beginner | advanced

    Returns:
        handler_id（字符串）

    Raises:
        RouteNotFoundError: 组合非法（未在 ROUTING_TABLE 中、缺失必需维度、无效值）
    """
    # 非本科模式：统一返回 non_undergrad（走主流程）
    if not undergrad_mode:
        return "non_undergrad"

    # 校验维度
    if not phase:
        raise RouteNotFoundError(
            "路由缺失维度 phase（必填）。当前 (undergrad_mode=True, phase=None)"
        )
    if not tier:
        raise RouteNotFoundError(
            f"路由缺失维度 tier（必填）。当前 (undergrad_mode=True, phase={phase!r}, tier=None)"
        )
    if phase not in _VALID_PHASES:
        raise RouteNotFoundError(
            f"未知 phase={phase!r}，合法值：{sorted(_VALID_PHASES)}"
        )
    if tier not in _VALID_TIERS:
        raise RouteNotFoundError(
            f"未知 tier={tier!r}，合法值：{sorted(_VALID_TIERS)}"
        )

    key = (bool(undergrad_mode), phase, tier)
    handler = ROUTING_TABLE.get(key)
    if handler is None:
        raise RouteNotFoundError(
            f"不支持的路由组合 {key}。"
            f"请在 src/upstream/routing.py 的 ROUTING_TABLE 中显式注册。"
        )
    return handler


def list_all_routes() -> Dict[Tuple[bool, str, str], str]:
    """返回所有合法路由组合（用于文档或测试）。"""
    return dict(ROUTING_TABLE)


def is_valid_route(
    undergrad_mode: bool,
    phase: Optional[str],
    tier: Optional[str],
) -> bool:
    """快速判断路由是否合法（不抛异常）。"""
    try:
        resolve_route(undergrad_mode, phase, tier)
        return True
    except RouteNotFoundError:
        return False


def get_phase_lifecycle() -> list:
    """返回 phase 生命周期顺序。"""
    return list(_PHASE_LIFECYCLE)


def next_phase(current_phase: str) -> Optional[str]:
    """返回生命周期中的下一个 phase；已是终点返回 None。"""
    try:
        idx = _PHASE_LIFECYCLE.index(current_phase)
        if idx + 1 < len(_PHASE_LIFECYCLE):
            return _PHASE_LIFECYCLE[idx + 1]
    except ValueError:
        pass
    return None


def validate_routing_table_at_startup() -> Dict[str, Any]:
    """v3.4 启动自检：遍历所有合法 (undergrad_mode, phase, tier) 组合，
    验证 ROUTING_TABLE 的完整性。

    Returns:
        {"ok": bool, "missing": [...], "errors": [...]}
    """
    missing: list = []
    errors: list = []
    # undergrad_mode=True 时，所有 (phase, tier) 组合必须显式注册
    for phase in _VALID_PHASES:
        for tier in _VALID_TIERS:
            key = (True, phase, tier)
            if key not in ROUTING_TABLE:
                missing.append(key)
    # ROUTING_TABLE 中不应有非法 phase/tier
    for key in ROUTING_TABLE.keys():
        mode, phase, tier = key
        if phase not in _VALID_PHASES:
            errors.append(f"路由表含未知 phase={phase!r}")
        if tier not in _VALID_TIERS:
            errors.append(f"路由表含未知 tier={tier!r}")
    return {
        "ok": (not missing and not errors),
        "missing": missing,
        "errors": errors,
    }
