"""文献雷达审核服务层 — 统一收口候选条目的审核操作。

所有审核动作（批准/拒绝/延迟/合并）必须走此层，不直接调 update_candidate_status。
每次审核自动写入 candidate_review_events 审计表。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Sequence

logger = logging.getLogger(__name__)


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    MERGED = "merged"


class RejectionReason(str, Enum):
    IRRELEVANT_DOMAIN = "irrelevant_domain"
    WEAK_EVIDENCE = "weak_evidence"
    TOO_GENERIC = "too_generic"
    DUPLICATE = "duplicate"
    BAD_METADATA = "bad_metadata"
    LOW_QUALITY_SOURCE = "low_quality_source"
    OTHER = "other"


VALID_STATUSES = {"pending", "approved", "rejected", "deferred", "merged"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def review_candidate(
    store,
    candidate_id: int,
    decision: str,
    reviewer: str,
    *,
    rejection_reason: str | None = None,
    target_kb_id: str | None = None,
    note: str | None = None,
) -> None:
    """对单个候选执行审核决策，写入状态 + 事件。"""
    decision = decision.lower()
    if decision not in VALID_STATUSES or decision == "pending":
        raise ValueError(f"Invalid decision: {decision}")

    if decision == "rejected" and not rejection_reason:
        raise ValueError("Rejection requires a reason")
    if decision == "merged" and not target_kb_id:
        raise ValueError("Merge requires target_kb_id")

    conn = store.connection
    old_row = conn.execute(
        "SELECT status FROM llm_candidates WHERE candidate_id = ?", (candidate_id,)
    ).fetchone()
    old_status = dict(old_row)["status"] if old_row else None

    now = _utc_now()

    with store.transaction():
        conn.execute(
            """UPDATE llm_candidates
               SET status = ?, reviewer = ?, reviewed_at = ?,
                   rejection_reason = ?, target_kb_id = ?
             WHERE candidate_id = ?""",
            (decision, reviewer, now, rejection_reason, target_kb_id, candidate_id),
        )
        conn.execute(
            """INSERT INTO candidate_review_events
               (candidate_id, old_status, new_status, reviewer, reason, note, target_kb_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (candidate_id, old_status, decision, reviewer, rejection_reason, note, target_kb_id, now),
        )


def bulk_review_candidates(
    store,
    candidate_ids: Sequence[int],
    decision: str,
    reviewer: str,
    *,
    reason: str | None = None,
    note: str | None = None,
) -> int:
    """批量审核，返回成功处理条数。"""
    count = 0
    for cid in candidate_ids:
        try:
            review_candidate(
                store, cid, decision, reviewer,
                rejection_reason=reason, note=note,
            )
            count += 1
        except (ValueError, Exception) as e:
            logger.warning("bulk_review skip candidate %d: %s", cid, e)
    return count


def list_review_events(
    store,
    candidate_id: int | None = None,
    limit: int = 200,
) -> list[dict]:
    """查询审核历史事件。"""
    conn = store.connection
    if candidate_id is not None:
        rows = conn.execute(
            "SELECT * FROM candidate_review_events WHERE candidate_id = ? ORDER BY created_at DESC LIMIT ?",
            (candidate_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM candidate_review_events ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
