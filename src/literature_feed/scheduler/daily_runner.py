"""每日自动抓取 + LLM 抽取 + 打分回填的总入口。

调度路径（双触发，文件锁去重）：
1. Windows Task Scheduler 通过 ``scripts/run_daily_feed.bat`` 调用
   ``python -m src.literature_feed.scheduler``
2. Streamlit 应用启动时 ``bootstrap_check.maybe_trigger_async()`` 懒触发

运行流程：
1. ``LockManager.acquire()`` 拿独占锁；冲突即退出（另一个进程在跑）
2. ``store.abandon_stale_runs()`` 清掉卡住的旧 run
3. ``store.start_run()`` 记 fetch_run_id
4. 遍历 enabled sources，按 source 隔离失败：
   - 调 fetcher.fetch_since(since_date)
   - JSONL 原始归档
   - upsert_article + add_keywords（命中 IO/HR/OB 自动标记）
   - 更新 sources.last_attempt / status
5. 可选：对本轮新文章触发 LLM 抽取（受 BudgetTracker 守门）
6. 全量回填 priority_score（IO/HR/OB 词表 + 半衰期）
7. ``store.finish_run(status='completed' | 'failed', summary=…)``

幂等性来自 (DOI / source_id+title_norm+issued_date) 的 upsert 与
(article_id, kind, normalized_name, prompt_version) 的候选去重；同一天多次触发
不会产生重复行。

错误隔离：单 source 抛 FetchError → 记 sources.status，整体 run 仍标 completed
（partial）。LockBusyError 是预期分支不算失败。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..extract.extractor import ExtractionError, LLMExtractor
from ..fetchers import (
    FetchError,
    FetchResult,
    RateLimitedError,
    SchemaChangedError,
    SourceConfig,
    SourceFetcher,
)
from ..fetchers.crossref import CrossrefFetcher
from ..fetchers.manual_ingest import ManualIngestFetcher
from ..fetchers.psy_science_official import PsyScienceOfficialFetcher
from ..parsers.csl_normalizer import extract_iohr_hits
from ..storage.budget_tracker import BudgetExceededError, BudgetTracker
from ..storage.feed_store import ArticleRow, FeedStore
from ..storage.jsonl_archive import JsonlArchive, sha256_text
from ..trend import (
    DEFAULT_HALF_LIFE_DAYS,
    DomainWeights,
    MethodWeights,
    TrendingWeights,
    compute_trending_weights,
    load_default_method_weights,
    load_default_trending,
    load_default_weights,
    update_candidate_scores,
    write_trending_yaml,
)
from ..paths import TRENDING_WEIGHTS_PATH
from .lock_manager import LockBusyError, LockManager

logger = logging.getLogger(__name__)

DEFAULT_DAYS_BACK = 14
DEFAULT_FETCH_LIMIT = 20
MAX_EXTRACT_ARTICLES_PER_RUN = 12  # 即使预算够也不一次跑太多，留给后续每日增量


# ---------------------------------------------------------------------------
# Fetcher registry
# ---------------------------------------------------------------------------

def build_fetcher(source: Dict[str, Any]) -> SourceFetcher:
    """从 sources 表行构造 fetcher 实例。"""
    fetcher_type = (source.get("fetcher_type") or "").strip().lower()
    extra = {}
    notes_json = source.get("notes")
    if notes_json:
        try:
            extra = json.loads(notes_json)
        except (TypeError, ValueError):
            extra = {}
    base_url = extra.get("base_url") if isinstance(extra, dict) else None
    config = SourceConfig(
        source_id=source["source_id"],
        journal_name=source.get("journal_name", ""),
        fetcher_type=fetcher_type,
        issn=source.get("issn"),
        doi_prefix=source.get("doi_prefix"),
        base_url=base_url,
        extra=extra if isinstance(extra, dict) else {},
    )
    if fetcher_type == "crossref":
        return CrossrefFetcher(config)
    if fetcher_type == "official_site":
        return PsyScienceOfficialFetcher(config)
    if fetcher_type == "manual":
        return ManualIngestFetcher(config)
    raise FetchError(f"未知 fetcher_type={fetcher_type!r}（source={source['source_id']}）")


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class SourceSummary:
    source_id: str
    fetched: int = 0
    new_articles: int = 0
    duplicates: int = 0
    failed: int = 0
    status: str = "ok"
    error: Optional[str] = None


@dataclass
class RunSummary:
    run_id: int
    trigger: str
    started_at: str
    ended_at: Optional[str] = None
    status: str = "completed"  # completed / partial / failed / skipped_locked
    sources: Dict[str, SourceSummary] = field(default_factory=dict)
    extracted_articles: int = 0
    extracted_constructs: int = 0
    extracted_methods: int = 0
    extracted_failed: int = 0
    budget_exceeded: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "trigger": self.trigger,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "sources": {k: v.__dict__ for k, v in self.sources.items()},
            "extracted_articles": self.extracted_articles,
            "extracted_constructs": self.extracted_constructs,
            "extracted_methods": self.extracted_methods,
            "extracted_failed": self.extracted_failed,
            "budget_exceeded": self.budget_exceeded,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

class DailyRunner:
    """组合 lock + store + fetchers + extractor + scorer 的总编排。"""

    def __init__(
        self,
        *,
        store: Optional[FeedStore] = None,
        lock: Optional[LockManager] = None,
        archive: Optional[JsonlArchive] = None,
        budget: Optional[BudgetTracker] = None,
        weights: Optional[DomainWeights] = None,
        method_weights: Optional[MethodWeights] = None,
        compute_trending: bool = True,
        trending_window: int = 30,
        trending_cap: float = 1.3,
        extractor_factory=None,           # 测试注入
        fetcher_builder=build_fetcher,    # 测试注入
        clock=None,                       # 测试注入：返回 utc datetime
    ) -> None:
        self._owns_store = store is None
        self.store = store or FeedStore()
        self.lock = lock or LockManager()
        self.archive = archive or JsonlArchive()
        self.budget = budget or BudgetTracker()
        self.weights = weights if weights is not None else load_default_weights()
        self.method_weights = (
            method_weights if method_weights is not None else load_default_method_weights()
        )
        self.compute_trending = compute_trending
        self.trending_window = trending_window
        self.trending_cap = trending_cap
        self._extractor_factory = extractor_factory
        self._fetcher_builder = fetcher_builder
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def close(self) -> None:
        """关闭 runner 自建的 store。外部传入的 store 不动。"""
        if self._owns_store and self.store is not None:
            try:
                self.store.close()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------ #

    def run(
        self,
        *,
        trigger: str = "scheduler",
        sources: Optional[Sequence[str]] = None,
        days_back: int = DEFAULT_DAYS_BACK,
        fetch_limit: int = DEFAULT_FETCH_LIMIT,
        do_extract: bool = True,
        max_extract: int = MAX_EXTRACT_ARTICLES_PER_RUN,
        compute_trending: Optional[bool] = None,
        trending_window: Optional[int] = None,
        trending_cap: Optional[float] = None,
    ) -> RunSummary:
        """主入口。锁冲突返回 status=skipped_locked 而非抛异常。"""
        with self._with_lock() as locked:
            if not locked:
                summary = RunSummary(
                    run_id=0, trigger=trigger,
                    started_at=self._iso_now(),
                    ended_at=self._iso_now(),
                    status="skipped_locked",
                )
                logger.warning("daily_runner: 锁被占用，本次跳过")
                return summary
            return self._run_locked(
                trigger=trigger,
                source_filter=set(sources) if sources else None,
                days_back=days_back,
                fetch_limit=fetch_limit,
                do_extract=do_extract,
                max_extract=max_extract,
                compute_trending=compute_trending if compute_trending is not None else self.compute_trending,
                trending_window=trending_window if trending_window is not None else self.trending_window,
                trending_cap=trending_cap if trending_cap is not None else self.trending_cap,
            )

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #

    class _LockedCtx:
        def __init__(self, runner: "DailyRunner") -> None:
            self.runner = runner
            self.acquired = False

        def __enter__(self) -> bool:
            try:
                self.runner.lock._open_and_lock()  # noqa: SLF001
                self.runner.lock._write_owner_info()  # noqa: SLF001
                self.acquired = True
                return True
            except LockBusyError:
                return False

        def __exit__(self, *exc: Any) -> None:
            if self.acquired:
                self.runner.lock._unlock_and_close()  # noqa: SLF001

    def _with_lock(self):
        return DailyRunner._LockedCtx(self)

    def _iso_now(self) -> str:
        return self._clock().replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _run_locked(
        self,
        *,
        trigger: str,
        source_filter: Optional[set],
        days_back: int,
        fetch_limit: int,
        do_extract: bool,
        max_extract: int,
        compute_trending: bool = True,
        trending_window: int = 30,
        trending_cap: float = 1.3,
    ) -> RunSummary:
        # 清理别的进程留下的 stale running 记录
        try:
            self.store.abandon_stale_runs()
        except Exception as exc:  # noqa: BLE001
            logger.warning("abandon_stale_runs 失败（忽略继续）：%s", exc)

        run_id = self.store.start_run(trigger)
        started = self._iso_now()
        summary = RunSummary(run_id=run_id, trigger=trigger, started_at=started)
        any_failed = False
        any_ok = False

        try:
            since_iso = self._compute_since(days_back)
            fetched_articles_for_extract: List[int] = []

            for src in self.store.list_sources(enabled_only=True):
                src_id = src["source_id"]
                if source_filter and src_id not in source_filter:
                    continue
                # 顶层兜底：任何 source 抛飞了都不该影响其他 source（DeepSeek #3）
                try:
                    src_summary, new_ids = self._fetch_one_source(
                        src, since_iso=since_iso, run_id=run_id, fetch_limit=fetch_limit,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception("source %s 处理时未捕获异常", src_id)
                    src_summary = SourceSummary(
                        source_id=src_id, status="failed",
                        error=f"{type(exc).__name__}: {exc}", failed=1,
                    )
                    new_ids = []
                summary.sources[src_id] = src_summary
                if src_summary.status.startswith("ok"):  # ok / ok_status_unwritten
                    any_ok = True
                else:
                    any_failed = True
                fetched_articles_for_extract.extend(new_ids)

            # LLM 抽取（受预算守门 + 单次上限）
            if do_extract and fetched_articles_for_extract:
                self._run_extraction(
                    summary,
                    article_ids=fetched_articles_for_extract[:max_extract],
                )

            # 不论是否新增候选，回填一次 priority_score
            # First compute trending if needed, so scores include trending boost
            trending = None
            if compute_trending and self._should_compute_trending():
                try:
                    existing = load_default_trending()
                    trending = compute_trending_weights(
                        self.store,
                        domain_weights=self.weights,
                        window_days=trending_window,
                        multiplier_cap=trending_cap,
                        existing=existing,
                    )
                    write_trending_yaml(trending, TRENDING_WEIGHTS_PATH)
                    logger.info("trending weights computed: %d entries", len(trending.entries))
                except Exception as exc:  # noqa: BLE001 — trending failure must not fail the run
                    logger.warning("compute_trending_weights failed (non-fatal): %s", exc)
                    # fallback to last-good cached YAML so this run still benefits from prior trending
                    try:
                        trending = load_default_trending()
                        logger.info("trending fallback to cached yaml (entries=%d)", len(trending.entries))
                    except Exception as inner:  # noqa: BLE001
                        logger.debug("cached trending also unavailable: %s", inner)
                        trending = None
            elif not compute_trending:
                pass  # skip trending by design
            else:
                # not time to recompute; load cached file if present
                try:
                    trending = load_default_trending()
                except Exception as exc:  # noqa: BLE001
                    logger.debug("load_default_trending failed: %s", exc)

            try:
                update_candidate_scores(
                    self.store, self.weights,
                    method_weights=self.method_weights,
                    trending=trending,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("update_candidate_scores 失败（不致命）：%s", exc)

            if any_failed and any_ok:
                summary.status = "partial"
            elif any_failed and not any_ok:
                summary.status = "failed"
            else:
                summary.status = "completed"
            summary.ended_at = self._iso_now()
            self.store.finish_run(
                run_id, status=summary.status, summary=summary.to_dict(),
            )
        except Exception as exc:  # noqa: BLE001 — 顶层兜底
            logger.exception("daily_runner 顶层异常：%s", exc)
            summary.status = "failed"
            summary.error = f"{type(exc).__name__}: {exc}"
            summary.ended_at = self._iso_now()
            try:
                self.store.finish_run(
                    run_id, status="failed",
                    summary=summary.to_dict(),
                    error={"message": summary.error},
                )
            except Exception:  # noqa: BLE001
                logger.exception("finish_run 也失败了")
        return summary

    def _should_compute_trending(self) -> bool:
        """True if trending_weights.yaml is missing, stale (>7d), or today is Monday."""
        path = TRENDING_WEIGHTS_PATH
        if not path.exists():
            return True
        try:
            mtime = path.stat().st_mtime
            age_days = (self._clock().timestamp() - mtime) / 86400
            if age_days > 7:
                return True
        except Exception:  # noqa: BLE001
            return True
        # recompute every Monday to keep baseline rolling
        return self._clock().weekday() == 0

    def _compute_since(self, days_back: int) -> str:
        days_back = max(0, int(days_back))
        cutoff = self._clock().date() - timedelta(days=days_back)
        return cutoff.isoformat()

    # ------------------------------------------------------------------ #

    def _fetch_one_source(
        self,
        source: Dict[str, Any],
        *,
        since_iso: str,
        run_id: int,
        fetch_limit: int,
    ) -> tuple:
        src_id = source["source_id"]
        src_summary = SourceSummary(source_id=src_id)

        try:
            fetcher = self._fetcher_builder(source)
        except FetchError as exc:
            src_summary.status = "failed"
            src_summary.error = str(exc)
            src_summary.failed = 1
            self.store.update_source_status(src_id, status="failed", success=False)
            return src_summary, []

        # 抓取
        try:
            result: FetchResult = fetcher.fetch_since(since_iso, limit=fetch_limit)
        except RateLimitedError as exc:
            src_summary.status = "rate_limited"
            src_summary.error = str(exc)
            self.store.update_source_status(
                src_id, status="rate_limited", success=False,
                probe_signature=fetcher.health_signature(),
            )
            return src_summary, []
        except SchemaChangedError as exc:
            src_summary.status = "schema_changed"
            src_summary.error = str(exc)
            src_summary.failed = 1
            self.store.update_source_status(
                src_id, status="schema_changed", success=False,
                probe_signature=fetcher.health_signature(),
            )
            return src_summary, []
        except FetchError as exc:
            src_summary.status = "failed"
            src_summary.error = str(exc)
            src_summary.failed = 1
            self.store.update_source_status(
                src_id, status="failed", success=False,
                probe_signature=fetcher.health_signature(),
            )
            return src_summary, []
        except Exception as exc:  # noqa: BLE001 — 网络/解析意外
            src_summary.status = "failed"
            src_summary.error = f"{type(exc).__name__}: {exc}"
            src_summary.failed = 1
            self.store.update_source_status(
                src_id, status="failed", success=False,
                probe_signature=fetcher.health_signature(),
            )
            logger.exception("source %s 抓取异常", src_id)
            return src_summary, []

        # JSONL 归档（即使后续入库失败也保住原始数据）
        try:
            if result.raw_records:
                self.archive.append_many(src_id, result.raw_records)
        except Exception as exc:  # noqa: BLE001
            logger.warning("source %s JSONL 归档失败（忽略继续）：%s", src_id, exc)

        # 入库 + IOHR 命中
        new_ids: List[int] = []
        weights_dict = self.weights.flat_synonyms()
        for raw in result.articles:
            try:
                aid, was_new = self._upsert_article(raw, run_id=run_id, weights=weights_dict)
            except Exception as exc:  # noqa: BLE001
                src_summary.failed += 1
                logger.exception("source %s 文章入库失败：%s", src_id, exc)
                continue
            src_summary.fetched += 1
            if was_new:
                src_summary.new_articles += 1
                new_ids.append(aid)
            else:
                src_summary.duplicates += 1

        src_summary.status = "ok"
        sig = result.probe_signature or fetcher.health_signature()
        # DeepSeek #3：单点 status 更新失败不能毁掉整个 run；包起来 + 降级标记
        try:
            self.store.update_source_status(
                src_id, status="ok", success=True, probe_signature=sig,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("source %s 状态写入失败（文章已入库，忽略）：%s", src_id, exc)
            src_summary.status = "ok_status_unwritten"
        return src_summary, new_ids

    def _upsert_article(
        self, raw, *, run_id: int, weights: Dict[str, Any],
    ) -> tuple:
        # 计算 IOHR 命中
        text_blobs = [
            raw.title or "",
            raw.abstract or "",
            " ".join(raw.keywords or []),
        ]
        iohr_hits = extract_iohr_hits(text_blobs, weights) if weights else []

        # raw_hash：用归一化 dict 算（payload 可能是 None）
        raw_hash = raw.raw_hash
        if not raw_hash:
            raw_hash = sha256_text(json.dumps(raw.to_dict(), ensure_ascii=False, sort_keys=True))

        # 先查重，确定 was_new；upsert 后再 add_keywords
        existing_id = self._lookup_existing_id(raw)

        article_row = ArticleRow(
            title=raw.title,
            authors=list(raw.authors or []),
            abstract=raw.abstract,
            issued_date=raw.issued_date,
            doi=raw.doi,
            container_title=raw.container_title,
            publisher=raw.publisher,
            keywords=list(raw.keywords or []),
            source_id=raw.source_id,
            provenance=raw.provenance,
            metadata_status=raw.metadata_status or "complete",
            iohr_hits=iohr_hits,
            raw_hash=raw_hash,
            fetched_at=self._iso_now(),
            fetch_run_id=run_id,
        )
        aid = self.store.upsert_article(article_row)
        was_new = existing_id is None

        # 关键词入表（重复忽略）
        if raw.keywords:
            self.store.add_keywords(aid, raw.keywords, source="author", iohr_hits=iohr_hits)

        return aid, bool(was_new)

    def _lookup_existing_id(self, raw) -> Optional[int]:
        """先查 DOI / (source_id + title_norm + issued_date)，没有就返回 None。"""
        from ..storage.feed_store import normalize_doi, normalize_title
        conn = self.store.connection
        if raw.doi:
            row = conn.execute(
                "SELECT article_id FROM articles WHERE doi = ?",
                (normalize_doi(raw.doi),),
            ).fetchone()
            if row:
                return int(row["article_id"])
        title_norm = normalize_title(raw.title)
        row = conn.execute(
            "SELECT article_id FROM articles "
            "WHERE source_id = ? AND title_norm = ? "
            "  AND COALESCE(issued_date,'') = COALESCE(?, '')",
            (raw.source_id, title_norm, raw.issued_date),
        ).fetchone()
        return int(row["article_id"]) if row else None

    # ------------------------------------------------------------------ #

    def _run_extraction(
        self,
        summary: RunSummary,
        *,
        article_ids: List[int],
    ) -> None:
        if not article_ids:
            return
        if not self.budget.can_call(essential=False):
            summary.budget_exceeded = True
            logger.info("budget 已耗尽，跳过 LLM 抽取")
            return
        extractor = self._build_extractor()
        for aid in article_ids:
            try:
                stats = extractor.extract_for_article(aid)
            except BudgetExceededError:
                summary.budget_exceeded = True
                logger.warning("BudgetExceededError，停止本轮抽取")
                break
            except ExtractionError as exc:
                summary.extracted_failed += 1
                logger.error("article %d 抽取失败：%s", aid, exc)
                continue
            except Exception as exc:  # noqa: BLE001
                summary.extracted_failed += 1
                logger.exception("article %d 抽取异常：%s", aid, exc)
                continue
            summary.extracted_articles += 1
            summary.extracted_constructs += stats.constructs_kept
            summary.extracted_methods += stats.methods_kept

    def _build_extractor(self) -> LLMExtractor:
        if self._extractor_factory is not None:
            return self._extractor_factory(self.store, self.budget)
        return LLMExtractor(self.store, self.budget)


# ---------------------------------------------------------------------------
# 顶层便捷函数（CLI / Streamlit 都可调用）
# ---------------------------------------------------------------------------

def run_daily(
    *,
    trigger: str = "scheduler",
    sources: Optional[Sequence[str]] = None,
    days_back: int = DEFAULT_DAYS_BACK,
    fetch_limit: int = DEFAULT_FETCH_LIMIT,
    do_extract: bool = True,
    max_extract: int = MAX_EXTRACT_ARTICLES_PER_RUN,
    compute_trending: bool = True,
    trending_window: int = 30,
    trending_cap: float = 1.3,
    db_path: Optional[Path] = None,
) -> RunSummary:
    """便捷入口。runner 拥有的 store 由 runner.close() 关闭（DeepSeek #2）。"""
    store = FeedStore(db_path=db_path) if db_path else None
    runner = DailyRunner(store=store)
    try:
        return runner.run(
            trigger=trigger,
            sources=sources,
            days_back=days_back,
            fetch_limit=fetch_limit,
            do_extract=do_extract,
            max_extract=max_extract,
            compute_trending=compute_trending,
            trending_window=trending_window,
            trending_cap=trending_cap,
        )
    finally:
        runner.close()  # 关闭 runner 自建的 store（如果是从外部传入的则跳过）
        if store is not None:
            try:
                store.close()
            except Exception:  # noqa: BLE001
                pass
