"""文献审核队列 UI 辅助层测试。"""
import pytest

from src.literature_feed.review_queue_ui import (
    QueueItem,
    QueueSummary,
    ReviewAction,
    build_queue_items,
    compute_queue_summary,
    filter_queue,
    format_review_event,
)


class TestBuildQueueItems:
    def test_basic_conversion(self):
        rows = [
            {"candidate_id": 1, "title": "论文A", "status": "pending", "authors": "张三"},
            {"candidate_id": 2, "title": "论文B", "status": "approved", "year": 2024},
        ]
        items = build_queue_items(rows)
        assert len(items) == 2
        assert items[0].candidate_id == 1
        assert items[0].title == "论文A"
        assert items[0].authors == "张三"
        assert items[1].status == "approved"
        assert items[1].year == "2024"

    def test_empty_rows(self):
        assert build_queue_items([]) == []

    def test_missing_fields_default(self):
        rows = [{"candidate_id": 99}]
        items = build_queue_items(rows)
        assert items[0].title == "无标题"
        assert items[0].status == "pending"


class TestQueueItem:
    def test_status_label(self):
        item = QueueItem(candidate_id=1, title="X", status="approved")
        assert item.status_label == "已纳入"

    def test_status_icon(self):
        item = QueueItem(candidate_id=1, title="X", status="rejected")
        assert "❌" in item.status_icon

    def test_display_title(self):
        item = QueueItem(candidate_id=1, title="测试论文", status="pending")
        assert "🔵" in item.display_title
        assert "测试论文" in item.display_title


class TestComputeQueueSummary:
    def test_counts(self):
        items = [
            QueueItem(candidate_id=1, title="A", status="pending"),
            QueueItem(candidate_id=2, title="B", status="pending"),
            QueueItem(candidate_id=3, title="C", status="approved"),
            QueueItem(candidate_id=4, title="D", status="rejected"),
            QueueItem(candidate_id=5, title="E", status="deferred"),
        ]
        summary = compute_queue_summary(items)
        assert summary.total == 5
        assert summary.pending == 2
        assert summary.approved == 1
        assert summary.rejected == 1
        assert summary.deferred == 1

    def test_progress(self):
        items = [
            QueueItem(candidate_id=1, title="A", status="pending"),
            QueueItem(candidate_id=2, title="B", status="approved"),
            QueueItem(candidate_id=3, title="C", status="approved"),
            QueueItem(candidate_id=4, title="D", status="rejected"),
        ]
        summary = compute_queue_summary(items)
        assert summary.review_progress == 0.75

    def test_empty_progress(self):
        summary = compute_queue_summary([])
        assert summary.review_progress == 0.0


class TestFilterQueue:
    def setup_method(self):
        self.items = [
            QueueItem(candidate_id=1, title="A", status="pending", source="wos", year="2024", relevance_score=0.8),
            QueueItem(candidate_id=2, title="B", status="approved", source="cnki", year="2023", relevance_score=0.6),
            QueueItem(candidate_id=3, title="C", status="pending", source="wos", year="2024", relevance_score=0.3),
        ]

    def test_filter_by_status(self):
        result = filter_queue(self.items, status="pending")
        assert len(result) == 2

    def test_filter_by_source(self):
        result = filter_queue(self.items, source="cnki")
        assert len(result) == 1
        assert result[0].title == "B"

    def test_filter_by_year(self):
        result = filter_queue(self.items, year="2023")
        assert len(result) == 1

    def test_filter_by_relevance(self):
        result = filter_queue(self.items, min_relevance=0.5)
        assert len(result) == 2

    def test_combined_filters(self):
        result = filter_queue(self.items, status="pending", source="wos", min_relevance=0.5)
        assert len(result) == 1
        assert result[0].title == "A"


class TestReviewAction:
    def test_valid_approve(self):
        action = ReviewAction(candidate_id=1, decision="approved")
        assert action.validate() == []

    def test_reject_without_reason(self):
        action = ReviewAction(candidate_id=1, decision="rejected")
        errors = action.validate()
        assert len(errors) == 1
        assert "原因" in errors[0]

    def test_reject_with_reason(self):
        action = ReviewAction(candidate_id=1, decision="rejected", rejection_reason="duplicate")
        assert action.validate() == []

    def test_merge_without_target(self):
        action = ReviewAction(candidate_id=1, decision="merged")
        errors = action.validate()
        assert "目标文献" in errors[0]

    def test_merge_with_target(self):
        action = ReviewAction(candidate_id=1, decision="merged", target_kb_id="kb_123")
        assert action.validate() == []

    def test_invalid_decision(self):
        action = ReviewAction(candidate_id=1, decision="invalid")
        errors = action.validate()
        assert any("无效" in e for e in errors)


class TestFormatReviewEvent:
    def test_format(self):
        event = {
            "created_at": "2026-07-01T10:00:00Z",
            "reviewer": "user",
            "new_status": "approved",
            "old_status": "pending",
            "reason": None,
            "note": "质量不错",
        }
        formatted = format_review_event(event)
        assert formatted["审核人"] == "user"
        assert formatted["操作"] == "已纳入"
        assert formatted["原状态"] == "待审核"
        assert formatted["备注"] == "质量不错"


# ─────────── s920-03：状态表合口（一张表派生 icon/label，加状态只改一行） ───────────
def test_status_table_is_the_only_source_for_both_views():
    from src.literature_feed.review_queue_ui import (
        REVIEW_STATUSES,
        status_icon,
        status_keys,
        status_label,
    )

    assert status_keys() == list(REVIEW_STATUSES) == ["pending", "approved", "rejected", "deferred", "merged"]
    assert all(len(v) == 2 and v[0] and v[1] for v in REVIEW_STATUSES.values())
    for key, (icon, label) in REVIEW_STATUSES.items():
        assert (status_icon(key), status_label(key)) == (icon, label)     # 两个视图同源，不可能再分叉


def test_unknown_status_keeps_the_two_legacy_fallbacks_apart():
    from src.literature_feed.review_queue_ui import status_icon, status_label

    assert status_label("全部") == "全部"       # 标签：原样回显（下拉哨兵值靠这个）
    assert status_icon("全部") == ""           # 图标：给空串（不硬造一个表情）


def test_queue_item_views_and_history_formatting_all_read_the_same_table():
    from src.literature_feed.review_queue_ui import (
        QueueItem,
        format_review_event,
        status_icon,
        status_label,
    )

    item = QueueItem(candidate_id=1, title="T", source="arxiv", status="merged", relevance_score=0.5)

    assert item.status_label == status_label("merged") == "已合并"
    assert item.status_icon == status_icon("merged") == "🔗"
    assert item.display_title == "🔗 T"                        # 图标＋标题的组合方式没变

    evt = {"created_at": "2026-09-20T03:00:00Z", "reviewer": "user", "new_status": "approved",
           "old_status": "pending", "rejection_reason": None, "candidate_id": 1}
    out = format_review_event(evt)

    assert out["操作"] == "已纳入" and out["原状态"] == "待审核"


def test_queue_panel_has_no_dead_bulk_import():
    """s930-03 防回流钉：literature_review_queue_panel 不得 import 未使用的
    bulk_review_candidates（s927-30 遗留点名件；AST 口径，import 与使用双向核对）。

    口径收窄说明：该面板另有 4 枚历史死 import（Optional/QueueSummary/ReviewDecision/
    annotations）**不在本单点名面**，钉只锁 bulk_review_candidates——全文件死 import
    普查属另单（登记于 s930-03 result 遗留）。
    """
    import ast
    from pathlib import Path

    src = Path("src/ui/literature_review_queue_panel.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if (a.asname or a.name) == "bulk_review_candidates":
                    imported.add("bulk_review_candidates")
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    dead = imported - used
    assert not dead, f"bulk_review_candidates 死 import 回流（未使用不得 import）"
