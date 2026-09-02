"""v5.4 P1-3: 方法暴露分级策略。

公开发布版区分三档方法：
- DEFAULT: 有完整交付链（结果卡片 + APA 表格路由），新手默认推荐
- ADVANCED: 有结果卡片但缺 APA 表格路由，需手动处理表格
- EXPERIMENTAL: 无结果卡片或仅有基础输出，明确标注限制

判断依据：
1. 该方法是否在 _CARD_BUILDERS 注册
2. 该方法是否在 generate_tables_from_card 路由中有条目
"""
from src.analysis.method_catalog import (
    METHOD_CATALOG,
    MethodLevel,
    get_method_level as _catalog_method_level,
)

_CARD_BUILDER_METHODS: set[str] = {
    method_id
    for definition in METHOD_CATALOG if definition.card_id
    for method_id in definition.all_ids
}

_TABLE_ROUTER_METHODS: set[str] = {
    method_id
    for definition in METHOD_CATALOG if definition.table_group
    for method_id in definition.all_ids
}

_DEFAULT_METHODS: set[str] = {
    method_id
    for definition in METHOD_CATALOG if definition.level == "default"
    for method_id in definition.all_ids
}


def get_method_level(method_id: str) -> MethodLevel:
    """获取方法的暴露级别。"""
    return _catalog_method_level(method_id)


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
    known_methods = {method_id for d in METHOD_CATALOG for method_id in d.all_ids}
    for m in sorted(known_methods):
        level = get_method_level(m)
        result[level].append(m)
    return result
