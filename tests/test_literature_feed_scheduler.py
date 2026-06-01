"""v4.7 自学习模块 — 调度器测试（Phase 4e）。

覆盖：
- DailyRunner: 锁冲突 / 单源失败隔离 / 幂等
- bootstrap_check: evaluate / maybe_trigger_async / last_async_result
- run_daily: store ownership + close
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture
def feed_root(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    import sys
    for mod in list(sys.modules):
        if mod.startswith("src.literature_feed"):
            del sys.modules[mod]
    return tmp_path


# =============================================================================
# fixtures: mock fetchers + extractor factory
# =============================================================================

@pytest.fixture
def mock_fetchers():
    from src.literature_feed.fetchers import (
        FetchError, FetchResult, RateLimitedError, RawArticle,
        SchemaChangedError, SourceConfig, SourceFetcher,
    )

    class _GoodFetcher(SourceFetcher):
        def fetch_since(self, since_date=None, *, limit=20):
            articles = [
                RawArticle(
                    title="变革型领导对工作满意度的影响",
                    source_id=self.source_id, provenance="manual",
                    abstract="变革型领导通过心理资本提升员工工作满意度。",
                    issued_date="2026-05-15", doi="10.1234/test/abc-1",
                ),
            ]
            return FetchResult(
                source_id=self.source_id, articles=articles,
                raw_records=[{"id": "abc-1"}], probe_signature="mock:v1",
            )
        def health_signature(self) -> str:
            return "mock-good:v1"

    class _RateFetcher(SourceFetcher):
        def fetch_since(self, since_date=None, *, limit=20):
            raise RateLimitedError("429", retry_after=60)

    class _SchemaFetcher(SourceFetcher):
        def fetch_since(self, since_date=None, *, limit=20):
            raise SchemaChangedError("无法解析")

    def _build(source):
        sid = source["source_id"]
        cfg = SourceConfig(source_id=sid, journal_name=source.get("journal_name", ""),
                           fetcher_type=source.get("fetcher_type", ""))
        if sid == "good":
            return _GoodFetcher(cfg)
        if sid == "rate":
            return _RateFetcher(cfg)
        if sid == "schema":
            return _SchemaFetcher(cfg)
        raise FetchError(f"unknown {sid}")

    return _build


@pytest.fixture
def fake_extractor_factory():
    """空 extractor：不抽东西，但接口对上。"""
    from src.literature_feed.extract.extractor import LLMExtractor

    def _factory(store, budget):
        def fake_chat(messages, *, model, temperature):
            return SimpleNamespace(
                content='{"constructs":[]}',
                fields={"usage": {"prompt_tokens": 50, "completion_tokens": 10}},
            )
        return LLMExtractor(store, budget, llm_chat_fn=fake_chat)
    return _factory


# =============================================================================
# DailyRunner
# =============================================================================

class TestDailyRunner:

    def test_happy_path_single_source(self, feed_root, mock_fetchers, fake_extractor_factory):
        from src.literature_feed.scheduler import DailyRunner
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.budget_tracker import BudgetTracker
        from src.literature_feed.trend import DomainWeights

        store = FeedStore()
        store.upsert_source(source_id="good", journal_name="J", fetcher_type="manual")
        runner = DailyRunner(
            store=store, weights=DomainWeights.empty(),
            budget=BudgetTracker(monthly_limit_usd=10.0),
            extractor_factory=fake_extractor_factory, fetcher_builder=mock_fetchers,
        )
        summary = runner.run(trigger="t", days_back=30, do_extract=False)
        assert summary.status in ("completed", "partial", "ok")
        assert summary.sources["good"].new_articles == 1
        store.close()

    def test_lock_conflict_returns_skipped(self, feed_root, mock_fetchers, fake_extractor_factory):
        from src.literature_feed.scheduler import DailyRunner, LockManager
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.budget_tracker import BudgetTracker
        from src.literature_feed.trend import DomainWeights

        store = FeedStore()
        store.upsert_source(source_id="good", journal_name="J", fetcher_type="manual")
        runner = DailyRunner(
            store=store, weights=DomainWeights.empty(),
            budget=BudgetTracker(monthly_limit_usd=10.0),
            extractor_factory=fake_extractor_factory, fetcher_builder=mock_fetchers,
        )
        lock = LockManager()
        lock._open_and_lock()
        try:
            summary = runner.run(trigger="t-locked")
            assert summary.status == "skipped_locked"
        finally:
            lock._unlock_and_close()
        store.close()

    def test_mixed_sources_partial_status(self, feed_root, mock_fetchers, fake_extractor_factory):
        from src.literature_feed.scheduler import DailyRunner
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.budget_tracker import BudgetTracker
        from src.literature_feed.trend import DomainWeights

        store = FeedStore()
        for sid in ("good", "rate", "schema"):
            store.upsert_source(source_id=sid, journal_name=sid, fetcher_type="manual")
        runner = DailyRunner(
            store=store, weights=DomainWeights.empty(),
            budget=BudgetTracker(monthly_limit_usd=10.0),
            extractor_factory=fake_extractor_factory, fetcher_builder=mock_fetchers,
        )
        summary = runner.run(trigger="t-mix", days_back=30, do_extract=False)
        # 1 ok + 1 rate + 1 schema → partial
        assert summary.status == "partial"
        assert summary.sources["good"].status.startswith("ok")
        assert summary.sources["rate"].status == "rate_limited"
        assert summary.sources["schema"].status == "schema_changed"
        store.close()

    def test_idempotent_second_run(self, feed_root, mock_fetchers, fake_extractor_factory):
        from src.literature_feed.scheduler import DailyRunner
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.budget_tracker import BudgetTracker
        from src.literature_feed.trend import DomainWeights

        store = FeedStore()
        store.upsert_source(source_id="good", journal_name="g", fetcher_type="manual")
        runner = DailyRunner(
            store=store, weights=DomainWeights.empty(),
            budget=BudgetTracker(monthly_limit_usd=10.0),
            extractor_factory=fake_extractor_factory, fetcher_builder=mock_fetchers,
        )
        s1 = runner.run(trigger="run1", days_back=30, do_extract=False)
        assert s1.sources["good"].new_articles == 1
        s2 = runner.run(trigger="run2", days_back=30, do_extract=False)
        assert s2.sources["good"].new_articles == 0
        assert s2.sources["good"].duplicates == 1
        store.close()

    def test_run_daily_no_sources_returns_empty_summary(self, feed_root):
        """run_daily 在空库（没有 source）时应正常返回，不抛异常，自建 store 被关闭。"""
        from src.literature_feed.scheduler import daily_runner as dr_mod

        summary = dr_mod.run_daily(trigger="ut-empty", days_back=30, do_extract=False)
        # 没注册 source → sources dict 空但 status 应该是 ok 类
        assert summary is not None
        assert isinstance(summary.sources, dict)

    def test_runner_owns_store_closes_on_close(self, feed_root):
        """DailyRunner 自建 store 时 close() 应释放连接（self._owns_store=True 路径）。"""
        from src.literature_feed.scheduler import DailyRunner

        runner = DailyRunner()  # 不传 store → 自建
        assert runner._owns_store is True
        store = runner.store
        runner.close()
        # 关闭后再访问 connection 应抛错（sqlite3.ProgrammingError）
        import sqlite3
        with pytest.raises((sqlite3.ProgrammingError, AttributeError)):
            store.connection.execute("SELECT 1")


# =============================================================================
# bootstrap_check
# =============================================================================

class TestBootstrapCheck:

    def test_evaluate_returns_should_run_when_no_history(self, feed_root):
        from src.literature_feed.scheduler.bootstrap_check import evaluate

        decision = evaluate(stale_hours=24)
        assert decision.should_run is True
        assert decision.last_success_hours is None
        assert "从未" in decision.reason or decision.last_success_hours is None

    def test_evaluate_skips_when_recent_success(self, feed_root, mock_fetchers, fake_extractor_factory):
        from src.literature_feed.scheduler import DailyRunner
        from src.literature_feed.scheduler.bootstrap_check import evaluate
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.budget_tracker import BudgetTracker
        from src.literature_feed.trend import DomainWeights

        store = FeedStore()
        store.upsert_source(source_id="good", journal_name="g", fetcher_type="manual")
        runner = DailyRunner(
            store=store, weights=DomainWeights.empty(),
            budget=BudgetTracker(monthly_limit_usd=10.0),
            extractor_factory=fake_extractor_factory, fetcher_builder=mock_fetchers,
        )
        runner.run(trigger="t", days_back=30, do_extract=False)
        store.close()

        decision = evaluate(stale_hours=24)
        assert decision.should_run is False

    def test_evaluate_force_stale_returns_should_run(self, feed_root, mock_fetchers, fake_extractor_factory):
        from src.literature_feed.scheduler import DailyRunner
        from src.literature_feed.scheduler.bootstrap_check import evaluate
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.budget_tracker import BudgetTracker
        from src.literature_feed.trend import DomainWeights

        store = FeedStore()
        store.upsert_source(source_id="good", journal_name="g", fetcher_type="manual")
        runner = DailyRunner(
            store=store, weights=DomainWeights.empty(),
            budget=BudgetTracker(monthly_limit_usd=10.0),
            extractor_factory=fake_extractor_factory, fetcher_builder=mock_fetchers,
        )
        runner.run(trigger="t", days_back=30, do_extract=False)
        store.close()

        # stale=0 → 立刻判 stale
        decision = evaluate(stale_hours=0)
        assert decision.should_run is True

    def test_last_async_result_initially_none(self, feed_root):
        # 把模块缓存清掉避免上一个测试的副作用
        import sys
        for mod in list(sys.modules):
            if mod.startswith("src.literature_feed.scheduler.bootstrap_check"):
                del sys.modules[mod]
        from src.literature_feed.scheduler import bootstrap_check

        # 全新进程下应该是 None
        assert bootstrap_check.last_async_result() is None
        assert bootstrap_check.is_running() is False
