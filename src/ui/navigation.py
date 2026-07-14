"""导航与路由 v5.7 — 精简为 6 个主入口。"""

from __future__ import annotations


PAGE_MODES = [
    "🗂️ 模板中心",
    "📚 文献与选题",
    "📋 问卷设计",
    "📈 数据分析",
    "📝 论文写作",
    "📦 交付包导出",
]

MODE_DESCRIPTIONS = {
    "🗂️ 模板中心": "从研究模板快速开始新项目",
    "📚 文献与选题": "选题漏斗、文献雷达、文献审核",
    "📋 问卷设计": "设计研究用问卷",
    "📈 数据分析": "导入数据并执行统计分析",
    "📝 论文写作": "生成论文草稿、证据表",
    "📦 交付包导出": "导出研究交付包",
}


def get_mode_index(mode: str) -> int:
    try:
        return PAGE_MODES.index(mode)
    except ValueError:
        return 3  # default to 数据分析
