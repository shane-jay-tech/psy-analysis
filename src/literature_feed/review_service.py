"""文献雷达审核服务层 — 统一收口候选条目的审核操作。

所有审核动作（批准/拒绝/延迟/合并）必须走此层，不直接调 update_candidate_status。
每次审核自动写入 candidate_review_events 审计表。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from src.literature_feed.timestamps import utc_now

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

    now = utc_now()

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


@dataclass(frozen=True)
class BulkReviewOutcome:
    """批量审核的成败读数（s927-30：调用方从此分得清「0 成功」与「0 入参」）。

    `total`＝**入参候选条数**（N），`succeeded`＝真落库并写了审计事件的条数（x），
    `failures`＝被吞掉的那些 `(candidate_id, "异常类型: 原因")`。
    只读，不改任何审核语义；数值口径完全由 `bulk_review_candidates_detailed` 的循环实况给出。
    """

    total: int
    succeeded: int
    failures: tuple[tuple[int, str], ...] = ()

    @property
    def failed(self) -> int:
        return self.total - self.succeeded

    def echo(self) -> str:
        """「成功 x/N」回显；有失败时点名（最多 3 枚）并给出失败条数，全成功不带尾巴。"""
        if not self.failures:
            return f"成功 {self.succeeded}/{self.total}"
        who = "、".join(str(cid) for cid, _ in self.failures[:3])
        more = "…" if len(self.failures) > 3 else ""
        return (
            f"成功 {self.succeeded}/{self.total}"
            f"（失败 {self.failed} 条已跳过：{who}{more}，原因见日志）"
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
    """批量审核，返回成功处理条数。

    门面保持不变（int）；要拿「成功 x/N ＋ 失败计数」就调 `bulk_review_candidates_detailed`（s927-30）。
    """
    return bulk_review_candidates_detailed(
        store, candidate_ids, decision, reviewer, reason=reason, note=note,
    ).succeeded


def bulk_review_candidates_detailed(
    store,
    candidate_ids: Sequence[int],
    decision: str,
    reviewer: str,
    *,
    reason: str | None = None,
    note: str | None = None,
) -> BulkReviewOutcome:
    """批量审核并**透出成败计数**（s927-30：吞异常面不再只留在日志里）。

    语义前提一条没动（由 `tests/test_review_service_bulk_partial.py` 九条在册钉桩锁着）：
    部分成功仍是部分成功、每条失败仍**恰好一条 WARNING** 且文案骨架不变、审计表仍只为成功条目写。
    汇总只走 INFO ⇒ 不会把那条 WARNING 计数顶成两条。
    """
    ids = list(candidate_ids)
    succeeded, failures = 0, []
    for cid in ids:
        try:
            review_candidate(
                store, cid, decision, reviewer,
                rejection_reason=reason, note=note,
            )
            succeeded += 1
        except (ValueError, Exception) as e:  # noqa: BLE001 - 吞一切是现状，收窄属 s922-07 R2 的另一刀，本单不动
            logger.warning("bulk_review skip candidate %d: %s", cid, e)
            failures.append((cid, f"{type(e).__name__}: {e}"))
    outcome = BulkReviewOutcome(total=len(ids), succeeded=succeeded, failures=tuple(failures))
    if outcome.failed:
        logger.info("bulk_review %s", outcome.echo())
    return outcome


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
