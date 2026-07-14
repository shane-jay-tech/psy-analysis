"""SQLite 主库 CRUD（WAL 模式）。

设计原则：
- 一个 ``FeedStore`` 实例 = 一个 SQLite 连接，线程不安全；调用方按需各开各的。
  WAL 多 reader + 单 writer 由 SQLite 自己保证。
- 所有写操作走显式事务；外部传 ``with store.transaction():`` 控制一组操作。
- 文章去重三层：DOI 唯一约束 → (source_id, title_norm, issued_date) 唯一约束 →
  应用层先 lookup 再 INSERT（失败时返回已有 article_id）。

行对象 ``ArticleRow`` / ``CandidateRow`` 是轻量 dataclass，用作输入/输出 DTO。
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

logger = logging.getLogger(__name__)

from ..paths import DB_PATH, ensure_dirs


SCHEMA_PATH: Path = Path(__file__).parent / "schema.sql"


# ---------------------------------------------------------------------------
# DTO
# ---------------------------------------------------------------------------

@dataclass
class ArticleRow:
    title: str
    source_id: str
    provenance: str
    fetched_at: str
    title_norm: str = ""               # 自动派生
    article_id: Optional[int] = None
    authors: List[Dict[str, str]] = field(default_factory=list)
    abstract: Optional[str] = None
    issued_date: Optional[str] = None  # ISO 8601 (YYYY-MM-DD)
    doi: Optional[str] = None
    container_title: Optional[str] = None
    publisher: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    metadata_status: str = "complete"
    iohr_hits: List[str] = field(default_factory=list)
    raw_hash: Optional[str] = None
    fetch_run_id: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.title_norm:
            self.title_norm = normalize_title(self.title)
        if self.doi:
            self.doi = normalize_doi(self.doi)


@dataclass
class CandidateRow:
    article_id: int
    kind: str                         # "construct" / "method"
    name: str
    evidence_quote: str
    evidence_valid: bool = False
    candidate_id: Optional[int] = None
    normalized_name: str = ""
    definition: Optional[str] = None
    method_category: Optional[str] = None
    confidence: Optional[float] = None
    novelty_hint: Optional[str] = None
    domain_score: float = 0.0
    priority_score: float = 0.0
    iohr_hits: List[str] = field(default_factory=list)
    llm_config_hash: Optional[str] = None
    prompt_version: Optional[str] = None
    status: str = "pending"
    rejection_reason: Optional[str] = None
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None
    target_kb_id: Optional[str] = None
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.normalized_name:
            self.normalized_name = normalize_keyword(self.name)
        if not self.created_at:
            self.created_at = utc_now_iso()


# ---------------------------------------------------------------------------
# 归一化工具
# ---------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[\s　\.,;:!?\"'\[\]{}()<>，。；：！？“”‘’【】《》（）\-—_/\\]+")


def normalize_title(raw: str) -> str:
    """去标点 + 折叠空白 + 小写 + Unicode NFKC。用于去重 key。"""
    if not raw:
        return ""
    text = unicodedata.normalize("NFKC", raw).strip().lower()
    text = _PUNCT_RE.sub("", text)
    return text


def normalize_doi(raw: str) -> str:
    """归一化 DOI：去 https://doi.org/ 前缀 + 小写。"""
    if not raw:
        return ""
    s = raw.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s


def normalize_keyword(raw: str) -> str:
    if not raw:
        return ""
    return unicodedata.normalize("NFKC", raw).strip().lower()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def hash_abstract(text: str) -> str:
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# FeedStore
# ---------------------------------------------------------------------------

class FeedStore:
    """SQLite 主库门面。

    Args:
        db_path: 数据库文件路径。``None`` 用 ``paths.DB_PATH`` 默认。
        ensure: 首次打开时建库 + 跑 schema（幂等）。
    """

    def __init__(self, db_path: Optional[Path] = None, *, ensure: bool = True) -> None:
        self._db_path: Path = Path(db_path) if db_path else DB_PATH
        if ensure:
            ensure_dirs()
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = sqlite3.connect(
            str(self._db_path),
            timeout=10,
            isolation_level=None,            # 我们手动管理事务
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        if ensure:
            self._apply_schema()

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        with contextlib.suppress(sqlite3.Error):
            self._conn.close()

    def __enter__(self) -> "FeedStore":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # 事务
    # ------------------------------------------------------------------ #

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """显式事务（BEGIN IMMEDIATE，避免 WAL 下读升写竞争）。"""
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            logger.debug("feed_store: transaction 失败，回滚", exc_info=True)
            with contextlib.suppress(sqlite3.Error):
                self._conn.rollback()
            raise

    def _apply_schema(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        # PRAGMA 必须在事务外；executescript 自动 commit
        self._conn.executescript(sql)
        # 幂等迁移：补齐老库缺失的新列/新表
        from .migrations import run_migrations
        run_migrations(self._conn)

    # ------------------------------------------------------------------ #
    # sources
    # ------------------------------------------------------------------ #

    def upsert_source(
        self,
        source_id: str,
        *,
        journal_name: str,
        issn: Optional[str] = None,
        doi_prefix: Optional[str] = None,
        fetcher_type: str,
        enabled: bool = True,
        notes: Optional[str] = None,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO sources(source_id, journal_name, issn, doi_prefix, fetcher_type, enabled, notes)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    journal_name = excluded.journal_name,
                    issn         = excluded.issn,
                    doi_prefix   = excluded.doi_prefix,
                    fetcher_type = excluded.fetcher_type,
                    enabled      = excluded.enabled,
                    notes        = excluded.notes
                """,
                (source_id, journal_name, issn, doi_prefix, fetcher_type, int(bool(enabled)), notes),
            )

    def update_source_status(
        self,
        source_id: str,
        *,
        status: str,
        success: bool,
        probe_signature: Optional[str] = None,
    ) -> None:
        now = utc_now_iso()
        with self.transaction() as conn:
            if success:
                conn.execute(
                    """
                    UPDATE sources
                       SET status = ?, last_attempt_at = ?, last_success_at = ?,
                           probe_signature = COALESCE(?, probe_signature)
                     WHERE source_id = ?
                    """,
                    (status, now, now, probe_signature, source_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE sources
                       SET status = ?, last_attempt_at = ?,
                           probe_signature = COALESCE(?, probe_signature)
                     WHERE source_id = ?
                    """,
                    (status, now, probe_signature, source_id),
                )

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_sources(self, *, enabled_only: bool = False) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM sources"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY source_id"
        return [dict(r) for r in self._conn.execute(sql).fetchall()]

    # ------------------------------------------------------------------ #
    # fetch_runs
    # ------------------------------------------------------------------ #

    def start_run(self, trigger: str) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO fetch_runs(trigger, started_at, status) VALUES(?, ?, 'running')",
                (trigger, utc_now_iso()),
            )
            return int(cur.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        summary: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE fetch_runs
                   SET ended_at = ?, status = ?, summary_json = ?, error_json = ?
                 WHERE run_id = ?
                """,
                (
                    utc_now_iso(),
                    status,
                    json.dumps(summary, ensure_ascii=False) if summary else None,
                    json.dumps(error, ensure_ascii=False) if error else None,
                    run_id,
                ),
            )

    def abandon_stale_runs(self, *, ttl_seconds: int = 3600) -> int:
        """把卡住的 running 任务标 abandoned。返回标记数。"""
        cutoff = datetime.now(timezone.utc).timestamp() - ttl_seconds
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        with self.transaction() as conn:
            cur = conn.execute(
                """
                UPDATE fetch_runs
                   SET status = 'abandoned', ended_at = ?
                 WHERE status = 'running' AND started_at < ?
                """,
                (utc_now_iso(), cutoff_iso),
            )
            return cur.rowcount

    def latest_successful_run(self) -> Optional[Dict[str, Any]]:
        # 'partial' 也算成功——只要至少有一家 source 抓到东西，就够 bootstrap_check 用
        cur = self._conn.execute(
            "SELECT * FROM fetch_runs WHERE status IN ('completed', 'partial') "
            "ORDER BY ended_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def hours_since_last_success(self) -> Optional[float]:
        run = self.latest_successful_run()
        if not run or not run.get("ended_at"):
            return None
        try:
            ended = datetime.fromisoformat(run["ended_at"].replace("Z", "+00:00"))
        except ValueError:
            return None
        delta = datetime.now(timezone.utc) - ended
        return delta.total_seconds() / 3600.0

    # ------------------------------------------------------------------ #
    # articles
    # ------------------------------------------------------------------ #

    def upsert_article(self, row: ArticleRow) -> int:
        """插入文章，重复返回已有 article_id（不报错）。"""
        if not row.title:
            raise ValueError("article title required")
        if not row.title_norm:
            row.title_norm = normalize_title(row.title)
        if row.doi:
            row.doi = normalize_doi(row.doi)

        # 1) DOI 命中已有
        if row.doi:
            existing = self._conn.execute(
                "SELECT article_id FROM articles WHERE doi = ?", (row.doi,)
            ).fetchone()
            if existing:
                return int(existing["article_id"])

        # 2) (source_id, title_norm, issued_date) 命中已有
        existing = self._conn.execute(
            "SELECT article_id FROM articles WHERE source_id = ? AND title_norm = ? AND COALESCE(issued_date,'') = COALESCE(?, '')",
            (row.source_id, row.title_norm, row.issued_date),
        ).fetchone()
        if existing:
            return int(existing["article_id"])

        with self.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO articles(
                    title, author_json, abstract, issued_date, doi,
                    container_title, publisher, keyword_json,
                    source_id, provenance, metadata_status, iohr_hits_json,
                    raw_hash, fetched_at, fetch_run_id, title_norm
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.title,
                    json.dumps(row.authors, ensure_ascii=False) if row.authors else None,
                    row.abstract,
                    row.issued_date,
                    row.doi or None,
                    row.container_title,
                    row.publisher,
                    json.dumps(row.keywords, ensure_ascii=False) if row.keywords else None,
                    row.source_id,
                    row.provenance,
                    row.metadata_status,
                    json.dumps(row.iohr_hits, ensure_ascii=False) if row.iohr_hits else None,
                    row.raw_hash,
                    row.fetched_at or utc_now_iso(),
                    row.fetch_run_id,
                    row.title_norm,
                ),
            )
            return int(cur.lastrowid)

    def get_article(self, article_id: int) -> Optional[Dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM articles WHERE article_id = ?", (article_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_articles(
        self,
        *,
        source_id: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM articles"
        clauses: List[str] = []
        params: List[Any] = []
        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)
        if since:
            clauses.append("issued_date >= ?")
            params.append(since)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY issued_date DESC NULLS LAST, article_id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    # ------------------------------------------------------------------ #
    # article_keywords
    # ------------------------------------------------------------------ #

    def add_keywords(
        self,
        article_id: int,
        keywords: Sequence[str],
        *,
        source: str = "author",
        iohr_hits: Optional[Iterable[str]] = None,
    ) -> int:
        if not keywords:
            return 0
        iohr_set = {normalize_keyword(k) for k in (iohr_hits or [])}
        added = 0
        with self.transaction() as conn:
            for raw in keywords:
                if not raw:
                    continue
                norm = normalize_keyword(raw)
                if not norm:
                    continue
                is_iohr = 1 if norm in iohr_set else 0
                try:
                    conn.execute(
                        """
                        INSERT INTO article_keywords(article_id, keyword_raw, keyword_norm, keyword_source, is_iohr_hit)
                        VALUES(?, ?, ?, ?, ?)
                        """,
                        (article_id, raw.strip(), norm, source, is_iohr),
                    )
                    added += 1
                except sqlite3.IntegrityError:
                    # UNIQUE(article_id, keyword_norm) 冲突，已存在
                    continue
        return added

    def list_keywords(
        self,
        *,
        since: Optional[str] = None,
        only_iohr: bool = False,
        limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        """关联 articles 表查 keyword + issued_date，给趋势聚合用。"""
        sql = """
        SELECT ak.keyword_norm, ak.keyword_raw, ak.is_iohr_hit, a.issued_date, a.article_id
          FROM article_keywords ak
          JOIN articles a ON a.article_id = ak.article_id
        """
        clauses: List[str] = []
        params: List[Any] = []
        if since:
            clauses.append("a.issued_date >= ?")
            params.append(since)
        if only_iohr:
            clauses.append("ak.is_iohr_hit = 1")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    # ------------------------------------------------------------------ #
    # llm_candidates
    # ------------------------------------------------------------------ #

    def insert_candidate(self, row: CandidateRow) -> int:
        """插入候选。重复（同 article+kind+name+prompt_version）返回 0，否则返回 candidate_id。"""
        if not row.created_at:
            row.created_at = utc_now_iso()
        with self.transaction() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO llm_candidates(
                    article_id, kind, name, normalized_name, definition,
                    method_category, evidence_quote, evidence_valid,
                    confidence, novelty_hint, domain_score, priority_score,
                    iohr_hits_json, llm_config_hash, prompt_version,
                    status, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.article_id,
                    row.kind,
                    row.name,
                    row.normalized_name,
                    row.definition,
                    row.method_category,
                    row.evidence_quote,
                    1 if row.evidence_valid else 0,
                    row.confidence,
                    row.novelty_hint,
                    row.domain_score,
                    row.priority_score,
                    json.dumps(row.iohr_hits, ensure_ascii=False) if row.iohr_hits else None,
                    row.llm_config_hash,
                    row.prompt_version,
                    row.status,
                    row.created_at,
                ),
            )
            # INSERT OR IGNORE: rowcount=1 表示插入成功，=0 表示命中唯一约束被跳过
            if cur.rowcount == 0:
                return 0
            return int(cur.lastrowid)

    def update_candidate_status(
        self,
        candidate_id: int,
        *,
        status: str,
        reviewer: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        target_kb_id: Optional[str] = None,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE llm_candidates
                   SET status = ?, reviewer = ?, reviewed_at = ?,
                       rejection_reason = ?, target_kb_id = ?
                 WHERE candidate_id = ?
                """,
                (status, reviewer, utc_now_iso(), rejection_reason, target_kb_id, candidate_id),
            )

    def list_candidates(
        self,
        *,
        status: str = "pending",
        kind: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM llm_candidates WHERE status = ?"
        params: List[Any] = [status]
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        sql += " ORDER BY priority_score DESC, candidate_id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def count_candidates(self, *, status: str = "pending") -> int:
        cur = self._conn.execute("SELECT COUNT(*) AS n FROM llm_candidates WHERE status = ?", (status,))
        return int(cur.fetchone()["n"])

    # ------------------------------------------------------------------ #
    # manual submissions
    # ------------------------------------------------------------------ #

    def insert_manual_submission(
        self,
        *,
        input_type: str,
        raw_input: str,
    ) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO manual_submissions(input_type, raw_input, status, created_at)
                VALUES(?, ?, 'pending', ?)
                """,
                (input_type, raw_input, utc_now_iso()),
            )
            return int(cur.lastrowid)

    def attach_submission_article(self, submission_id: int, article_id: int) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE manual_submissions SET parsed_article_id = ?, status = 'parsed' WHERE submission_id = ?",
                (article_id, submission_id),
            )

    def fail_submission(self, submission_id: int, error: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE manual_submissions SET status = 'failed', error = ? WHERE submission_id = ?",
                (error, submission_id),
            )

    # ------------------------------------------------------------------ #
    # LLM 摘要 hash 缓存
    # ------------------------------------------------------------------ #

    def cache_extraction(
        self,
        *,
        abstract_hash: str,
        prompt_version: str,
        model: str,
        response: Dict[str, Any],
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO llm_extraction_cache(abstract_hash, prompt_version, model, response_json, cached_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(abstract_hash, prompt_version, model) DO UPDATE SET
                    response_json = excluded.response_json,
                    cached_at     = excluded.cached_at
                """,
                (abstract_hash, prompt_version, model, json.dumps(response, ensure_ascii=False), utc_now_iso()),
            )

    def get_cached_extraction(
        self,
        *,
        abstract_hash: str,
        prompt_version: str,
        model: str,
    ) -> Optional[Dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT response_json FROM llm_extraction_cache WHERE abstract_hash = ? AND prompt_version = ? AND model = ?",
            (abstract_hash, prompt_version, model),
        )
        row = cur.fetchone()
        if not row:
            return None
        try:
            return json.loads(row["response_json"])
        except (TypeError, ValueError):
            return None
