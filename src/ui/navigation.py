"""主导航单一事实源。侧栏、跳转和路由测试均应复用这里的页面名。"""

from __future__ import annotations

# s924-38：回退槽页名的单一事实源。抽取前这条页名在 PAGE_MODES、MODE_DESCRIPTIONS 与
# get_mode_index 的回退分支里各写了一份字面量；删页或改名会让回退分支自己抛 ValueError
# （s922-141 登记的那处脆点）⇒ 现在只在下面写一次，其余三处一律引本常量。
DEFAULT_PAGE_MODE = "📈 数据分析"

PAGE_MODES = [
    "🗂️ 模板中心",
    "📚 文献与选题",
    "📋 问卷设计",
    "🧪 实验设计",
    DEFAULT_PAGE_MODE,          # 同时也是 get_mode_index 的回退槽
    "📝 论文写作",
    "📦 交付包导出",
]

MODE_DESCRIPTIONS = {
    "🗂️ 模板中心": "从研究模板快速开始新项目",
    "📚 文献与选题": "选题漏斗、文献雷达、文献审核",
    "📋 问卷设计": "设计研究用问卷",
    "🧪 实验设计": "设计实验范式、流程并估算样本量",
    DEFAULT_PAGE_MODE: "导入数据并执行统计分析",
    "📝 论文写作": "生成论文草稿、证据表",
    "📦 交付包导出": "导出研究交付包",
}


def get_mode_index(mode: str) -> int:
    """mode 的位置；不在 PAGE_MODES 里（含空串／None）时回退到 DEFAULT_PAGE_MODE 那一格。

    回退分支**故意**仍然 `PAGE_MODES.index(...)`：真删掉默认页就当场 ValueError，那是想要的
    信号——删页必须先在 `tests/test_navigation_pagemodes_snapshot.py` 撞红，不许被运行时静默兜住。
    """
    try:
        return PAGE_MODES.index(mode)
    except ValueError:
        return PAGE_MODES.index(DEFAULT_PAGE_MODE)
