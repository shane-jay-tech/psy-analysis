"""图表收藏夹 — 跨会话累积本科生分析过程中产出的所有图表。

核心数据流：
- 用户在 renderers 渲染图表后点击"📌 加入论文图表集" → add()
- 第 7 步管理 expander 列出所有收藏 → list_all()
- 工作区保存时 to_serializable() → JSON 可存
- 工作区恢复时 from_serializable() → 重建对象（plotly fig 用 JSON 还原）

序列化策略：
- Plotly Figure 用 fig.to_json() 序列化为 JSON 字符串（无损保留交互性）
- 反序列化用 plotly.io.from_json() 还原
- 不用 pickle（跨版本不稳定）；不用 base64 PNG（丢失交互能力，无法重新调色）
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import plotly.graph_objects as go


@dataclass
class FigureEntry:
    """单条图表收藏。"""
    figure_id: str
    title: str
    test_type: str
    variables: List[str]
    fig_object: Any  # plotly.graph_objects.Figure
    created_at: str
    note: str = ""
    chart_type: str = ""  # 如 "箱线图" / "热力图" / "散点图"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为可 JSON 的 dict。"""
        return {
            "figure_id": self.figure_id,
            "title": self.title,
            "test_type": self.test_type,
            "variables": list(self.variables),
            "fig_json": (
                self.fig_object.to_json() if isinstance(self.fig_object, go.Figure)
                else None
            ),
            "created_at": self.created_at,
            "note": self.note,
            "chart_type": self.chart_type,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FigureEntry":
        """从序列化 dict 重建。"""
        import plotly.io as pio
        fig_json = d.get("fig_json")
        fig = pio.from_json(fig_json) if fig_json else None
        return cls(
            figure_id=d.get("figure_id", str(uuid.uuid4())),
            title=d.get("title", "未命名图表"),
            test_type=d.get("test_type", "unknown"),
            variables=list(d.get("variables", [])),
            fig_object=fig,
            created_at=d.get("created_at", ""),
            note=d.get("note", ""),
            chart_type=d.get("chart_type", ""),
        )


@dataclass
class FigureCollection:
    """图表收藏夹（持久化容器）。"""
    entries: List[FigureEntry] = field(default_factory=list)

    # ----------------------------------------------------------------- #
    # 增删改查
    # ----------------------------------------------------------------- #

    def add(
        self,
        *,
        title: str,
        test_type: str,
        variables: List[str],
        fig_object: go.Figure,
        note: str = "",
        chart_type: str = "",
    ) -> str:
        """加入新图表，返回 figure_id。"""
        entry = FigureEntry(
            figure_id=str(uuid.uuid4()),
            title=title,
            test_type=test_type,
            variables=list(variables),
            fig_object=fig_object,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            note=note,
            chart_type=chart_type,
        )
        self.entries.append(entry)
        return entry.figure_id

    def remove(self, figure_id: str) -> bool:
        """删除指定图表。返回是否删除成功。"""
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.figure_id != figure_id]
        return len(self.entries) < before

    def update_note(self, figure_id: str, note: str) -> bool:
        """更新备注。"""
        for e in self.entries:
            if e.figure_id == figure_id:
                e.note = note
                return True
        return False

    def update_title(self, figure_id: str, title: str) -> bool:
        for e in self.entries:
            if e.figure_id == figure_id:
                e.title = title
                return True
        return False

    def get(self, figure_id: str) -> Optional[FigureEntry]:
        for e in self.entries:
            if e.figure_id == figure_id:
                return e
        return None

    def list_all(self) -> List[FigureEntry]:
        """返回所有收藏（按加入顺序）。"""
        return list(self.entries)

    def clear_all(self) -> int:
        """清空，返回清除条数。"""
        n = len(self.entries)
        self.entries.clear()
        return n

    def __len__(self) -> int:
        return len(self.entries)

    # ----------------------------------------------------------------- #
    # 重复检测（防同一分析图表二次加入）
    # ----------------------------------------------------------------- #

    def find_duplicate(
        self, *, test_type: str, variables: List[str], chart_type: str
    ) -> Optional[FigureEntry]:
        """根据 test_type + variables + chart_type 查找已存在的图表。"""
        var_set = tuple(sorted(variables))
        for e in self.entries:
            if (
                e.test_type == test_type
                and tuple(sorted(e.variables)) == var_set
                and e.chart_type == chart_type
            ):
                return e
        return None

    # ----------------------------------------------------------------- #
    # 序列化（工作区集成）
    # ----------------------------------------------------------------- #

    def to_serializable(self) -> List[Dict[str, Any]]:
        """转为工作区可保存的 list[dict]。"""
        return [e.to_dict() for e in self.entries]

    @classmethod
    def from_serializable(cls, data: List[Dict[str, Any]]) -> "FigureCollection":
        """从工作区恢复。"""
        coll = cls()
        if not data:
            return coll
        for d in data:
            try:
                coll.entries.append(FigureEntry.from_dict(d))
            except Exception:
                # 单条恢复失败不影响其他
                continue
        return coll


# --------------------------------------------------------------------------- #
# Streamlit session_state 集成
# --------------------------------------------------------------------------- #

SESSION_KEY = "figure_collection"


def get_collection_from_session(session_state: Any) -> FigureCollection:
    """从 Streamlit session_state 读取（不存在则初始化空）。"""
    if SESSION_KEY not in session_state or not isinstance(
        session_state.get(SESSION_KEY), FigureCollection
    ):
        session_state[SESSION_KEY] = FigureCollection()
    return session_state[SESSION_KEY]


def set_collection_to_session(session_state: Any, coll: FigureCollection):
    session_state[SESSION_KEY] = coll
