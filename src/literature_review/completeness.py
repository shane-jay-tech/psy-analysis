"""文献综述完成度评分（v3.5）。

6 项 × 20 分 = 100 分总分
- 文献量：≥15 篇为满分
- 高相关占比：relevance ≥0.5 的文献占比
- 笔记覆盖率：有笔记的文献占比
- 矩阵填充率：非空单元格占比
- gap 是否存在
- 主题聚类是否运行
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .models import LiteratureItem, ReadingNote


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class CompletenessSubScore:
    name: str
    score: float                # 0-20
    weight: float = 20.0
    suggestion: str = ""


@dataclass
class CompletenessResult:
    total: float = 0.0          # 0-100
    sub_scores: List[CompletenessSubScore] = field(default_factory=list)

    @property
    def grade(self) -> str:
        """字面分级。"""
        if self.total >= 80:
            return "优秀"
        if self.total >= 60:
            return "良好"
        if self.total >= 40:
            return "及格"
        return "不足"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total": round(self.total, 1),
            "grade": self.grade,
            "sub_scores": [asdict(s) for s in self.sub_scores],
        }


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def calculate_completeness(state: Dict[str, Any]) -> CompletenessResult:
    """根据 LiteratureReviewState dict 计算完成度。

    state 期望含：literature_items、notes、matrix、themes、gaps（与 workspace 持久化结构一致）。
    """
    items_raw = state.get("literature_items") or []
    notes_raw = state.get("notes") or []
    matrix = state.get("matrix") or {}
    themes = state.get("themes") or []
    gaps = state.get("gaps") or []

    # 1) 文献量 (≥15 满分)
    n_items = len(items_raw)
    item_score = min(20.0, (n_items / 15.0) * 20.0)
    item_sug = "" if n_items >= 15 else f"仅 {n_items} 篇文献，建议补到 15 篇以上"

    # 2) 高相关占比（relevance ≥0.5）
    if items_raw:
        high = sum(
            1 for it in items_raw
            if isinstance(it, dict) and float(it.get("relevance_score") or 0) >= 0.5
        )
        ratio = high / len(items_raw)
        rel_score = ratio * 20.0
        rel_sug = "" if ratio >= 0.5 else f"高相关文献占比仅 {ratio:.0%}，建议筛选关键词或精读核心文献"
    else:
        rel_score, rel_sug = 0.0, "尚未搜索文献"

    # 3) 笔记覆盖率（有笔记的文献占比）
    if items_raw:
        keys_with_notes = {
            n.get("literature_key") for n in notes_raw if isinstance(n, dict)
        }
        covered = sum(
            1 for it in items_raw
            if isinstance(it, dict) and it.get("key") in keys_with_notes
        )
        ratio = covered / len(items_raw)
        note_score = ratio * 20.0
        note_sug = "" if ratio >= 0.4 else f"仅 {ratio:.0%} 文献有笔记，建议至少为高相关文献加笔记"
    else:
        note_score, note_sug = 0.0, ""

    # 4) 矩阵填充率
    if items_raw and matrix.get("dimensions"):
        dims = matrix.get("dimensions") or []
        cells = matrix.get("cells") or {}
        total_cells = max(1, len(items_raw) * len(dims))
        filled = 0
        for k, row in cells.items():
            if not isinstance(row, dict):
                continue
            for d in dims:
                if str(row.get(d, "")).strip():
                    filled += 1
        ratio = filled / total_cells
        matrix_score = ratio * 20.0
        matrix_sug = "" if ratio >= 0.4 else f"矩阵填充率 {ratio:.0%}，建议为关键文献至少填关键维度"
    else:
        matrix_score, matrix_sug = 0.0, "矩阵尚未配置或无文献"

    # 5) 是否有 gap
    if gaps:
        gap_score = 20.0
        gap_sug = ""
    else:
        gap_score = 0.0
        gap_sug = "尚未运行 Gap 分析"

    # 6) 是否运行主题聚类
    if themes:
        theme_score = 20.0
        theme_sug = ""
    else:
        theme_score = 0.0
        theme_sug = "尚未运行主题聚类"

    sub_scores = [
        CompletenessSubScore("文献量", round(item_score, 1), 20.0, item_sug),
        CompletenessSubScore("高相关占比", round(rel_score, 1), 20.0, rel_sug),
        CompletenessSubScore("笔记覆盖", round(note_score, 1), 20.0, note_sug),
        CompletenessSubScore("矩阵填充", round(matrix_score, 1), 20.0, matrix_sug),
        CompletenessSubScore("Gap 分析", round(gap_score, 1), 20.0, gap_sug),
        CompletenessSubScore("主题聚类", round(theme_score, 1), 20.0, theme_sug),
    ]
    total = sum(s.score for s in sub_scores)

    return CompletenessResult(total=round(total, 1), sub_scores=sub_scores)
