"""SQLite 幂等 schema 迁移 — 启动时自动补齐缺失列和新表。

设计原则：
- 每条迁移有唯一 ID，执行一次后不再重复。
- 全部用 ALTER TABLE ... ADD COLUMN（SQLite 不支持 DROP/RENAME）。
- 失败不中断应用启动，仅 log warning。
"""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Sequence

logger = logging.getLogger(__name__)


def _get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cursor = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cursor.fetchone() is not None


def _ensure_migration_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id TEXT PRIMARY KEY,
            applied_at   TEXT NOT NULL
        )
    """)


def _is_applied(conn: sqlite3.Connection, migration_id: str) -> bool:
    cursor = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE migration_id = ?", (migration_id,)
    )
    return cursor.fetchone() is not None


def _mark_applied(conn: sqlite3.Connection, migration_id: str):
    conn.execute(
        "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
        (migration_id, datetime.now(timezone.utc).isoformat()),
    )


# ---------------------------------------------------------------------------
# Migration definitions
# ---------------------------------------------------------------------------

def _m_20260703_candidate_review_fields(conn: sqlite3.Connection):
    """补齐 llm_candidates 审核相关列（老库可能缺失）。"""
    if not _table_exists(conn, "llm_candidates"):
        return
    cols = _get_table_columns(conn, "llm_candidates")
    additions = [
        ("rejection_reason", "TEXT"),
        ("reviewer", "TEXT"),
        ("reviewed_at", "TEXT"),
        ("target_kb_id", "TEXT"),
    ]
    for col, dtype in additions:
        if col not in cols:
            conn.execute(f"ALTER TABLE llm_candidates ADD COLUMN {col} {dtype}")


def _m_20260703_candidate_deferred_status(conn: sqlite3.Connection):
    """确保 status 索引覆盖 deferred 状态（文档化，无 DDL 变更）。"""
    pass


def _m_20260703_review_audit_log(conn: sqlite3.Connection):
    """新建审核事件表。"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candidate_review_events (
            event_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id  INTEGER NOT NULL,
            old_status    TEXT,
            new_status    TEXT NOT NULL,
            reviewer      TEXT,
            reason        TEXT,
            note          TEXT,
            target_kb_id  TEXT,
            created_at    TEXT NOT NULL,
            FOREIGN KEY(candidate_id) REFERENCES llm_candidates(candidate_id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_review_events_candidate
        ON candidate_review_events(candidate_id, created_at DESC)
    """)


MIGRATIONS: Sequence[tuple[str, callable]] = [
    ("20260703_candidate_review_fields", _m_20260703_candidate_review_fields),
    ("20260703_candidate_deferred_status", _m_20260703_candidate_deferred_status),
    ("20260703_review_audit_log", _m_20260703_review_audit_log),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_migrations(conn: sqlite3.Connection) -> list[str]:
    """执行所有未应用的迁移。返回本次执行的迁移 ID 列表。"""
    applied = []
    try:
        _ensure_migration_table(conn)
        for mid, fn in MIGRATIONS:
            if _is_applied(conn, mid):
                continue
            try:
                fn(conn)
                _mark_applied(conn, mid)
                conn.commit()
                applied.append(mid)
                logger.info("Migration applied: %s", mid)
            except Exception as e:
                conn.rollback()
                logger.warning("Migration failed: %s — %s", mid, e)
    except Exception as e:
        logger.warning("Migration system init failed: %s", e)
    return applied
