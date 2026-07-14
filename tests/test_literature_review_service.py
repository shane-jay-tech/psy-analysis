"""文献雷达审核服务层测试。"""
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.literature_feed.storage.feed_store import FeedStore, CandidateRow
from src.literature_feed.storage.migrations import run_migrations
from src.literature_feed.review_service import (
    review_candidate,
    bulk_review_candidates,
    list_review_events,
    RejectionReason,
)


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test.db"
    s = FeedStore(db_path=db_path, ensure=True)
    yield s
    s.close()


def _insert_candidate(store, name="test_construct") -> int:
    row = CandidateRow(
        article_id=1,
        kind="construct",
        name=name,
        normalized_name=name.lower(),
        evidence_quote="evidence text",
        confidence=0.8,
        status="pending",
        created_at="2026-07-03T00:00:00Z",
    )
    # Insert a dummy article first
    store.connection.execute(
        "INSERT OR IGNORE INTO sources (source_id, journal_name, fetcher_type) VALUES (?, ?, ?)",
        ("test_source", "Test Journal", "manual"),
    )
    store.connection.execute(
        """INSERT OR IGNORE INTO articles
           (article_id, title, source_id, provenance, fetched_at, title_norm)
           VALUES (1, 'Test Article', 'test_source', 'manual', '2026-07-03', 'test article')"""
    )
    store.connection.commit()
    return store.insert_candidate(row)


class TestReviewCandidate:
    def test_reject_requires_reason(self, store):
        cid = _insert_candidate(store)
        with pytest.raises(ValueError, match="reason"):
            review_candidate(store, cid, "rejected", "user1")

    def test_reject_with_reason(self, store):
        cid = _insert_candidate(store)
        review_candidate(
            store, cid, "rejected", "user1",
            rejection_reason=RejectionReason.WEAK_EVIDENCE,
        )
        row = store.connection.execute(
            "SELECT status, rejection_reason FROM llm_candidates WHERE candidate_id=?", (cid,)
        ).fetchone()
        assert dict(row)["status"] == "rejected"
        assert dict(row)["rejection_reason"] == "weak_evidence"

    def test_defer_candidate(self, store):
        cid = _insert_candidate(store)
        review_candidate(store, cid, "deferred", "user1")
        row = store.connection.execute(
            "SELECT status FROM llm_candidates WHERE candidate_id=?", (cid,)
        ).fetchone()
        assert dict(row)["status"] == "deferred"

    def test_deferred_hidden_from_pending(self, store):
        cid = _insert_candidate(store)
        review_candidate(store, cid, "deferred", "user1")
        pending = store.list_candidates(status="pending")
        assert not any(c["candidate_id"] == cid for c in pending)

    def test_merge_requires_target(self, store):
        cid = _insert_candidate(store)
        with pytest.raises(ValueError, match="target_kb_id"):
            review_candidate(store, cid, "merged", "user1")

    def test_merge_with_target(self, store):
        cid = _insert_candidate(store)
        review_candidate(store, cid, "merged", "user1", target_kb_id="kb_001")
        row = store.connection.execute(
            "SELECT status, target_kb_id FROM llm_candidates WHERE candidate_id=?", (cid,)
        ).fetchone()
        assert dict(row)["status"] == "merged"
        assert dict(row)["target_kb_id"] == "kb_001"

    def test_review_event_written(self, store):
        cid = _insert_candidate(store)
        review_candidate(store, cid, "approved", "reviewer_x")
        events = list_review_events(store, candidate_id=cid)
        assert len(events) == 1
        assert events[0]["old_status"] == "pending"
        assert events[0]["new_status"] == "approved"
        assert events[0]["reviewer"] == "reviewer_x"


class TestBulkReview:
    def test_batch_reject_writes_same_reason(self, store):
        ids = [_insert_candidate(store, f"c_{i}") for i in range(3)]
        count = bulk_review_candidates(
            store, ids, "rejected", "batch_user",
            reason=RejectionReason.IRRELEVANT_DOMAIN,
        )
        assert count == 3
        events = list_review_events(store)
        assert len(events) == 3
        assert all(e["reason"] == "irrelevant_domain" for e in events)


class TestMigrations:
    def test_old_db_migrates_candidate_review_fields(self, tmp_path):
        """模拟旧库（缺列），打开后自动补齐。"""
        db_path = tmp_path / "old.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("""
            CREATE TABLE llm_candidates (
                candidate_id INTEGER PRIMARY KEY,
                article_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

        applied = run_migrations(conn)
        assert "20260703_candidate_review_fields" in applied
        assert "20260703_review_audit_log" in applied

        cols = {row[1] for row in conn.execute("PRAGMA table_info(llm_candidates)").fetchall()}
        assert "rejection_reason" in cols
        assert "reviewer" in cols
        assert "reviewed_at" in cols
        assert "target_kb_id" in cols

        # review events table exists
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "candidate_review_events" in tables
        conn.close()

    def test_migrations_idempotent(self, tmp_path):
        """重复执行不报错。"""
        db_path = tmp_path / "idem.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE llm_candidates (
                candidate_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        run_migrations(conn)
        run_migrations(conn)  # second run should be no-op
        conn.close()
