"""v4.7 自学习模块 — 存储层测试。

覆盖：
- FeedStore: schema 应用 / source CRUD / fetch_runs / articles 三层去重 / candidates / 缓存
- JsonlArchive: append + iter + 路径安全
- BudgetTracker: 记账 / 月分桶 / 警告 / 硬阻断 / 缓存 hit
- 标题/DOI 归一化
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def feed_root(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    # 强制 reload paths 让覆盖生效
    import sys
    for mod in list(sys.modules):
        if mod.startswith("src.literature_feed"):
            del sys.modules[mod]
    return tmp_path


# ---------------------------------------------------------------------------
# FeedStore
# ---------------------------------------------------------------------------

class TestFeedStore:

    def test_schema_creates_all_tables(self, feed_root):
        from src.literature_feed.storage import FeedStore

        store = FeedStore()
        cur = store.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r["name"] for r in cur.fetchall()}
        for expected in (
            "sources", "fetch_runs", "articles", "article_keywords",
            "llm_candidates", "manual_submissions", "llm_extraction_cache",
        ):
            assert expected in tables
        store.close()

    def test_wal_mode_enabled(self, feed_root):
        from src.literature_feed.storage import FeedStore

        store = FeedStore()
        mode = store.connection.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
        store.close()

    def test_upsert_source_idempotent(self, feed_root):
        from src.literature_feed.storage import FeedStore

        store = FeedStore()
        store.upsert_source(
            source_id="acta_psych", journal_name="心理学报",
            issn="0439-755X", doi_prefix="10.3724", fetcher_type="crossref",
        )
        store.upsert_source(
            source_id="acta_psych", journal_name="心理学报（升级）",
            issn="0439-755X", doi_prefix="10.3724", fetcher_type="crossref",
        )
        srcs = store.list_sources()
        assert len(srcs) == 1
        assert srcs[0]["journal_name"] == "心理学报（升级）"
        store.close()

    def test_article_dedup_by_doi(self, feed_root):
        from src.literature_feed.storage import FeedStore, ArticleRow

        store = FeedStore()
        store.upsert_source(
            source_id="s1", journal_name="A", fetcher_type="crossref",
        )
        a1 = ArticleRow(
            title="Title One", source_id="s1", provenance="crossref",
            fetched_at="2026-05-28T00:00:00Z",
            doi="https://doi.org/10.3724/SP.J.1041.2026.00500",
            issued_date="2026-05-01",
        )
        id1 = store.upsert_article(a1)

        # 不同标题，但 DOI 相同 → 还是返回 id1
        a2 = ArticleRow(
            title="Different title", source_id="s1", provenance="crossref",
            fetched_at="2026-05-28T00:00:00Z",
            doi="10.3724/SP.J.1041.2026.00500",  # 没有 https 前缀，归一化后相同
            issued_date="2026-05-01",
        )
        id2 = store.upsert_article(a2)
        assert id1 == id2
        store.close()

    def test_article_dedup_by_source_title_date(self, feed_root):
        from src.literature_feed.storage import FeedStore, ArticleRow

        store = FeedStore()
        store.upsert_source(source_id="s1", journal_name="A", fetcher_type="crossref")

        # 没 DOI 的中文文章去重靠 (source_id, title_norm, issued_date)
        a1 = ArticleRow(
            title="组织公民行为研究综述",
            source_id="s1", provenance="manual",
            fetched_at="2026-05-28T00:00:00Z",
            issued_date="2026-04-01",
        )
        id1 = store.upsert_article(a1)

        # 标题加标点（正常化后相同）
        a2 = ArticleRow(
            title="组织公民行为：研究综述",
            source_id="s1", provenance="manual",
            fetched_at="2026-05-28T00:00:00Z",
            issued_date="2026-04-01",
        )
        id2 = store.upsert_article(a2)
        assert id1 == id2
        store.close()

    def test_keywords_unique_per_article(self, feed_root):
        from src.literature_feed.storage import FeedStore, ArticleRow

        store = FeedStore()
        store.upsert_source(source_id="s1", journal_name="A", fetcher_type="crossref")
        aid = store.upsert_article(ArticleRow(
            title="X", source_id="s1", provenance="crossref",
            fetched_at="2026-05-28T00:00:00Z",
        ))
        added = store.add_keywords(aid, ["敬业度", "敬业度", "工作满意度"], iohr_hits=["敬业度"])
        assert added == 2

        kws = store.list_keywords()
        norms = sorted(k["keyword_norm"] for k in kws)
        assert norms == ["工作满意度", "敬业度"]
        iohr = [k for k in kws if k["is_iohr_hit"]]
        assert len(iohr) == 1 and iohr[0]["keyword_norm"] == "敬业度"
        store.close()

    def test_candidates_pending_count_and_status(self, feed_root):
        from src.literature_feed.storage import FeedStore, ArticleRow, CandidateRow

        store = FeedStore()
        store.upsert_source(source_id="s1", journal_name="A", fetcher_type="crossref")
        aid = store.upsert_article(ArticleRow(
            title="X", source_id="s1", provenance="crossref",
            fetched_at="2026-05-28T00:00:00Z",
        ))
        c1 = store.insert_candidate(CandidateRow(
            article_id=aid, kind="construct", name="变革型领导",
            evidence_quote="变革型领导", evidence_valid=True, priority_score=2.0,
        ))
        c2 = store.insert_candidate(CandidateRow(
            article_id=aid, kind="method", name="层次回归",
            evidence_quote="层次回归", evidence_valid=True, priority_score=1.0,
        ))
        assert store.count_candidates() == 2

        store.update_candidate_status(c1, status="approved", reviewer="user", target_kb_id="kb-001")
        assert store.count_candidates(status="pending") == 1
        assert store.count_candidates(status="approved") == 1

        pending = store.list_candidates(status="pending")
        assert len(pending) == 1 and pending[0]["candidate_id"] == c2
        store.close()

    def test_fetch_runs_lifecycle_and_stale(self, feed_root):
        from src.literature_feed.storage import FeedStore

        store = FeedStore()
        run_id = store.start_run("scheduler")
        store.finish_run(run_id, status="completed", summary={"acta": {"new": 3}})
        latest = store.latest_successful_run()
        assert latest["run_id"] == run_id
        assert json.loads(latest["summary_json"])["acta"]["new"] == 3

        # stale 任务
        store.connection.execute(
            "UPDATE fetch_runs SET status='running', started_at='2020-01-01T00:00:00Z' WHERE run_id=?",
            (run_id,),
        )
        n = store.abandon_stale_runs(ttl_seconds=3600)
        assert n == 1
        store.close()

    def test_extraction_cache_roundtrip(self, feed_root):
        from src.literature_feed.storage import FeedStore

        store = FeedStore()
        store.cache_extraction(
            abstract_hash="h1", prompt_version="v1", model="m1",
            response={"constructs": [{"name": "x"}]},
        )
        got = store.get_cached_extraction(abstract_hash="h1", prompt_version="v1", model="m1")
        assert got and got["constructs"][0]["name"] == "x"
        miss = store.get_cached_extraction(abstract_hash="other", prompt_version="v1", model="m1")
        assert miss is None
        store.close()

    def test_manual_submission_lifecycle(self, feed_root):
        from src.literature_feed.storage import FeedStore, ArticleRow

        store = FeedStore()
        store.upsert_source(source_id="mw", journal_name="管理世界", fetcher_type="manual")
        sub_id = store.insert_manual_submission(input_type="doi", raw_input="10.3389/x")
        aid = store.upsert_article(ArticleRow(
            title="管理学新论", source_id="mw", provenance="manual",
            fetched_at="2026-05-28T00:00:00Z",
        ))
        store.attach_submission_article(sub_id, aid)
        row = store.connection.execute(
            "SELECT * FROM manual_submissions WHERE submission_id=?", (sub_id,)
        ).fetchone()
        assert row["status"] == "parsed" and row["parsed_article_id"] == aid

        sub2 = store.insert_manual_submission(input_type="url", raw_input="https://x")
        store.fail_submission(sub2, "解析超时")
        row2 = store.connection.execute(
            "SELECT * FROM manual_submissions WHERE submission_id=?", (sub2,)
        ).fetchone()
        assert row2["status"] == "failed" and row2["error"] == "解析超时"
        store.close()


# ---------------------------------------------------------------------------
# Normalize helpers
# ---------------------------------------------------------------------------

class TestNormalize:

    def test_normalize_title_drops_punct(self, feed_root):
        from src.literature_feed.storage.feed_store import normalize_title

        assert normalize_title("AAA：BBB（CCC）") == normalize_title("AAA, BBB CCC")
        assert normalize_title("  Hello World!  ") == "helloworld"

    def test_normalize_doi_strips_prefix(self, feed_root):
        from src.literature_feed.storage.feed_store import normalize_doi

        cases = [
            "https://doi.org/10.3724/X",
            "http://doi.org/10.3724/x",
            "DOI:10.3724/X",
            "10.3724/X",
        ]
        norms = {normalize_doi(c) for c in cases}
        assert norms == {"10.3724/x"}


# ---------------------------------------------------------------------------
# JsonlArchive
# ---------------------------------------------------------------------------

class TestJsonlArchive:

    def test_append_and_iter(self, feed_root):
        from src.literature_feed.storage import JsonlArchive

        arch = JsonlArchive()
        arch.append("acta_psych", {"doi": "10.x/1", "title": "A"}, date="2026-05-28")
        arch.append("acta_psych", {"doi": "10.x/2", "title": "B"}, date="2026-05-28")
        records = list(arch.iter_day("acta_psych", "2026-05-28"))
        assert [r["title"] for r in records] == ["A", "B"]

    def test_path_safety_strips_traversal(self, feed_root):
        from src.literature_feed.storage import JsonlArchive

        arch = JsonlArchive()
        evil = "../../etc/passwd"
        p = arch.append(evil, {"x": 1}, date="2026-05-28")
        # 文件名应被 sanitize；不允许跑出 root
        assert str(arch.root) in str(p.resolve())
        assert ".." not in p.name

    def test_append_many_writes_all(self, feed_root):
        from src.literature_feed.storage import JsonlArchive

        arch = JsonlArchive()
        arch.append_many("s1", [{"i": i} for i in range(5)], date="2026-05-28")
        recs = list(arch.iter_day("s1", "2026-05-28"))
        assert [r["i"] for r in recs] == [0, 1, 2, 3, 4]


# ---------------------------------------------------------------------------
# BudgetTracker
# ---------------------------------------------------------------------------

class TestBudgetTracker:

    def test_first_call_records_cost(self, feed_root):
        from src.literature_feed.storage import BudgetTracker

        b = BudgetTracker(monthly_limit_usd=10.0)
        b.record(model="deepseek-v4", prompt_tokens=1000, completion_tokens=500, caller="test")
        u = b.current_usage()
        assert u["calls"] == 1
        assert u["total_tokens"] == 1500
        assert u["total_usd"] > 0
        assert u["limit_usd"] == 10.0

    def test_warn_threshold(self, feed_root):
        from src.literature_feed.storage import BudgetTracker

        b = BudgetTracker(monthly_limit_usd=0.001, warn_ratio=0.5)
        b.record(model="gpt-5.5", prompt_tokens=100, completion_tokens=100, caller="test")
        u = b.current_usage()
        assert u["warn"] is True

    def test_hard_block_raises(self, feed_root):
        from src.literature_feed.storage import BudgetTracker, BudgetExceededError

        b = BudgetTracker(monthly_limit_usd=0.0001)
        b.record(model="claude-opus-4-8", prompt_tokens=100, completion_tokens=100, caller="test")
        with pytest.raises(BudgetExceededError):
            b.precheck()

    def test_essential_call_bypasses_block(self, feed_root):
        from src.literature_feed.storage import BudgetTracker

        b = BudgetTracker(monthly_limit_usd=0.0001)
        b.record(model="claude-opus-4-8", prompt_tokens=100, completion_tokens=100, caller="test")
        # essential 调用不抛
        b.precheck(essential=True)
        assert b.can_call(essential=True) is True
        assert b.can_call(essential=False) is False

    def test_cache_hit_does_not_charge(self, feed_root):
        from src.literature_feed.storage import BudgetTracker

        b = BudgetTracker(monthly_limit_usd=10.0)
        b.record(model="deepseek-v4", prompt_tokens=1000, completion_tokens=500, caller="test")
        before = b.current_usage()["total_usd"]
        b.record(model="deepseek-v4", prompt_tokens=0, completion_tokens=0, caller="test", cache_hit=True)
        after = b.current_usage()
        assert after["total_usd"] == pytest.approx(before)
        assert after["cache_hits"] == 1

    def test_by_caller_attribution(self, feed_root):
        from src.literature_feed.storage import BudgetTracker

        b = BudgetTracker(monthly_limit_usd=10.0)
        b.record(model="deepseek-v4", prompt_tokens=100, completion_tokens=50, caller="construct")
        b.record(model="deepseek-v4", prompt_tokens=100, completion_tokens=50, caller="method")
        b.record(model="deepseek-v4", prompt_tokens=100, completion_tokens=50, caller="construct")
        u = b.current_usage()
        assert u["by_caller"]["construct"]["calls"] == 2
        assert u["by_caller"]["method"]["calls"] == 1

    def test_persistence_across_instances(self, feed_root):
        from src.literature_feed.storage import BudgetTracker

        b1 = BudgetTracker(monthly_limit_usd=10.0)
        b1.record(model="kimi-k2", prompt_tokens=200, completion_tokens=100, caller="x")
        # 新实例读同一个 path
        b2 = BudgetTracker(monthly_limit_usd=10.0)
        u = b2.current_usage()
        assert u["calls"] == 1
        assert u["total_tokens"] == 300
