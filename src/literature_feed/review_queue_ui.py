"""文献审核队列 UI 辅助层 — 从 review_service 到 Streamlit 组件的桥接。

提供数据转换和状态管理函数，Streamlit 页面只需调用这些函数
而不直接操作数据库。所有审核操作走 review_service，不可绕过。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence


# 状态 → 展示映射
STATUS_LABELS = {
    "pending": "待审核",
    "approved": "已纳入",
    "rejected": "已排除",
    "deferred": "待定",
    "merged": "已合并",
}

STATUS_ICONS = {
    "pending": "🔵",
    "approved": "✅",
    "rejected": "❌",
    "deferred": "⏸️",
    "merged": "🔗",
}

REJECTION_REASON_LABELS = {
    "irrelevant_domain": "领域不相关",
    "weak_evidence": "证据薄弱",
    "too_generic": "过于泛化",
    "duplicate": "重复条目",
    "bad_metadata": "元数据问题",
    "low_quality_source": "来源质量低",
    "other": "其他",
}


@dataclass
class QueueItem:
    """审核队列中的单条文献。"""
    candidate_id: int
    title: str
    authors: str = ""
    year: str = ""
    source: str = ""
    abstract: str = ""
    status: str = "pending"
    reviewer: str = ""
    reviewed_at: str = ""
    rejection_reason: str = ""
    relevance_score: float = 0.0

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def status_icon(self) -> str:
        return STATUS_ICONS.get(self.status, "")

    @property
    def display_title(self) -> str:
        return f"{self.status_icon} {self.title}"


@dataclass
class QueueSummary:
    """审核队列统计摘要。"""
    total: int = 0
    pending: int = 0
    approved: int = 0
    rejected: int = 0
    deferred: int = 0
    merged: int = 0

    @property
    def review_progress(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.total - self.pending) / self.total


@dataclass
class ReviewAction:
    """一次审核操作的参数包。"""
    candidate_id: int
    decision: str
    reviewer: str = "user"
    rejection_reason: str | None = None
    target_kb_id: str | None = None
    note: str | None = None

    def validate(self) -> list[str]:
        """校验操作参数，返回错误列表（空=合法）。"""
        errors = []
        if self.decision == "rejected" and not self.rejection_reason:
            errors.append("排除操作必须选择原因")
        if self.decision == "merged" and not self.target_kb_id:
            errors.append("合并操作必须选择目标文献")
        if self.decision not in ("approved", "rejected", "deferred", "merged"):
            errors.append(f"无效的审核决策: {self.decision}")
        return errors


def build_queue_items(rows: Sequence[dict]) -> list[QueueItem]:
    """从数据库行转换为 QueueItem 列表。"""
    items = []
    for row in rows:
        items.append(QueueItem(
            candidate_id=row.get("candidate_id", 0),
            title=row.get("title", "无标题"),
            authors=row.get("authors", ""),
            year=str(row.get("year", "")),
            source=row.get("source", ""),
            abstract=row.get("abstract", ""),
            status=row.get("status", "pending"),
            reviewer=row.get("reviewer", ""),
            reviewed_at=row.get("reviewed_at", ""),
            rejection_reason=row.get("rejection_reason", ""),
            relevance_score=row.get("relevance_score", 0.0),
        ))
    return items


def compute_queue_summary(items: list[QueueItem]) -> QueueSummary:
    """计算队列统计摘要。"""
    summary = QueueSummary(total=len(items))
    for item in items:
        if item.status == "pending":
            summary.pending += 1
        elif item.status == "approved":
            summary.approved += 1
        elif item.status == "rejected":
            summary.rejected += 1
        elif item.status == "deferred":
            summary.deferred += 1
        elif item.status == "merged":
            summary.merged += 1
    return summary


def filter_queue(
    items: list[QueueItem],
    *,
    status: str | None = None,
    source: str | None = None,
    year: str | None = None,
    min_relevance: float = 0.0,
) -> list[QueueItem]:
    """筛选队列条目。"""
    result = items
    if status:
        result = [i for i in result if i.status == status]
    if source:
        result = [i for i in result if i.source == source]
    if year:
        result = [i for i in result if i.year == year]
    if min_relevance > 0:
        result = [i for i in result if i.relevance_score >= min_relevance]
    return result


def format_review_event(event: dict) -> dict[str, str]:
    """把审核事件转换为展示友好的字典。"""
    return {
        "时间": event.get("created_at", ""),
        "审核人": event.get("reviewer", ""),
        "操作": STATUS_LABELS.get(event.get("new_status", ""), event.get("new_status", "")),
        "原状态": STATUS_LABELS.get(event.get("old_status", ""), event.get("old_status", "")),
        "原因": REJECTION_REASON_LABELS.get(
            event.get("reason", ""), event.get("reason", "")
        ),
        "备注": event.get("note", "") or "",
    }
