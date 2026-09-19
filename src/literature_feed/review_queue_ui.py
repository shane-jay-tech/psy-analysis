"""文献审核队列 UI 辅助层 — 从 review_service 到 Streamlit 组件的桥接。

提供数据转换和状态管理函数，Streamlit 页面只需调用这些函数
而不直接操作数据库。所有审核操作走 review_service，不可绕过。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence


# 状态 → (图标, 标签)。**单一表**：加一个决策只改这一行。
# 改前是 label 表与 icon 表两张平行字典靠手工对齐，加一个决策要改两处（`done(s919-02)` 遗留 1）。
REVIEW_STATUSES: dict[str, tuple[str, str]] = {
    "pending": ("🔵", "待审核"),
    "approved": ("✅", "已纳入"),
    "rejected": ("❌", "已排除"),
    "deferred": ("⏸️", "待定"),
    "merged": ("🔗", "已合并"),
}


def status_label(status: str) -> str:
    """未知状态**原样回显**（下拉框里的"全部"这类哨兵值就走这条，改前是 `label 表.get(x, x)`）。"""
    return REVIEW_STATUSES.get(status, ("", status))[1]


def status_icon(status: str) -> str:
    """未知状态给空串（改前是 `icon 表.get(x, "")`）。"""
    return REVIEW_STATUSES.get(status, ("", ""))[0]


def status_keys() -> list[str]:
    """状态枚举的展示顺序 = 表定义顺序。"""
    return list(REVIEW_STATUSES)

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
        return status_label(self.status)

    @property
    def status_icon(self) -> str:
        return status_icon(self.status)

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


def review_success_message(
    decision: str,
    *,
    title: str | None = None,
    target_kb_id: str | None = None,
    rejection_reason: str | None = None,
) -> str:
    """审核成功后的回显文案（s920-04：四种决策不再共用一句光秃秃的状态词）。

    只做展示：决策白名单、落库参数、`ReviewAction.validate` 一概不经过这里。
    标题拿不到（空/None）就退回 `status_label` 的原短句，**不渲染空的《》**。
    """
    label = status_label(decision)
    name = (title or "").strip()
    if not name:
        return label
    if decision == "approved":
        return f"已纳入《{name}》"
    if decision == "rejected":
        reason = REJECTION_REASON_LABELS.get(rejection_reason or "", rejection_reason or "")
        return f"已排除《{name}》（原因：{reason}）" if reason else f"已排除《{name}》"
    if decision == "deferred":
        return f"已标记《{name}》为待定"
    if decision == "merged":
        return f"已合并《{name}》→ 目标 {target_kb_id}"
    return label


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
        "操作": status_label(event.get("new_status", "")),
        "原状态": status_label(event.get("old_status", "")),
        "原因": REJECTION_REASON_LABELS.get(
            event.get("reason", ""), event.get("reason", "")
        ),
        "备注": event.get("note", "") or "",
    }
