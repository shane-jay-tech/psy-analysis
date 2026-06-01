"""文献综述工作台（v3.4）：搜索 → 筛选 → 笔记 → 矩阵 → 主题 → Gap。

模块组成：
- models     — LiteratureItem / ReadingNote / ThemeCluster / GapAnalysis / LiteratureMatrix
- search     — 调 literature_crawler 聚合搜索 + 去重 + 相关性排序
- notes      — 阅读笔记 CRUD + 按文献/主题聚合 + Markdown 导出
- matrix     — 文献矩阵构建 + 摘要自动填充 + CSV 导出
- themes     — KMeans/层次聚类主题 + LLM/启发式 gap 识别
"""

from .models import (
    GapAnalysis,
    LiteratureItem,
    LiteratureMatrix,
    ReadingNote,
    ThemeCluster,
)

__all__ = [
    "LiteratureItem",
    "ReadingNote",
    "ThemeCluster",
    "GapAnalysis",
    "LiteratureMatrix",
]
