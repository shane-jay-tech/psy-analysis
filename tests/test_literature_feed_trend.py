"""v4.7 自学习模块 — 趋势聚合 + IO/HR/OB 加权测试（Phase 4d）。

覆盖：
- DomainWeights: from_yaml_path / from_mapping / empty / 反查 / score_hits / flat_synonyms
- scorer: compute_recency_decay / compute_priority_score / compute_domain_score / update_candidate_scores
- aggregator: compute_keyword_trends / compute_domain_summary
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest


@pytest.fixture
def feed_root(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    import sys
    for mod in list(sys.modules):
        if mod.startswith("src.literature_feed"):
            del sys.modules[mod]
    return tmp_path


@pytest.fixture
def sample_yaml(tmp_path: Path) -> Path:
    p = tmp_path / "weights.yaml"
    p.write_text(
        """
version: 1
default_weight: 1.0
domain_multiplier: 2.0
domains:
  IO:
    concepts:
      - canonical: 变革型领导
        synonyms: [transformational leadership, 变革型]
      - canonical: 工作满意度
        synonyms: [job satisfaction]
  HR:
    concepts:
      - canonical: 员工敬业度
        synonyms: [employee engagement, work engagement, 敬业度]
  OB:
    concepts:
      - canonical: 组织承诺
        synonyms: [organizational commitment]
""".strip(),
        encoding="utf-8",
    )
    return p


# =============================================================================
# DomainWeights
# =============================================================================

class TestDomainWeights:

    def test_from_yaml_path_loads_all(self, sample_yaml):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.from_yaml_path(sample_yaml)
        assert w.version == 1
        assert w.default_weight == 1.0
        assert w.domain_multiplier == 2.0
        # 2+1+1 canonical
        assert len(w.flat_synonyms()) == 4

    def test_from_yaml_path_missing_returns_empty(self, tmp_path):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.from_yaml_path(tmp_path / "doesnotexist.yaml")
        assert len(w.flat_synonyms()) == 0
        assert w.default_weight == 1.0

    def test_empty_factory(self):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.empty()
        assert w.flat_synonyms() == {}
        assert w.domain_for("anything") is None

    def test_domain_for_canonical_hit(self, sample_yaml):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.from_yaml_path(sample_yaml)
        assert w.domain_for("变革型领导") == "IO"
        assert w.domain_for("员工敬业度") == "HR"
        assert w.domain_for("组织承诺") == "OB"

    def test_domain_for_synonym_routes_to_canonical_domain(self, sample_yaml):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.from_yaml_path(sample_yaml)
        assert w.domain_for("transformational leadership") == "IO"
        assert w.domain_for("employee engagement") == "HR"
        # 大小写无关
        assert w.domain_for("WORK ENGAGEMENT") == "HR"

    def test_domain_for_unknown_returns_none(self, sample_yaml):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.from_yaml_path(sample_yaml)
        assert w.domain_for("某个完全没收录的术语") is None
        assert w.domain_for("") is None
        assert w.domain_for("   ") is None

    def test_canonical_for_synonym(self, sample_yaml):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.from_yaml_path(sample_yaml)
        assert w.canonical_for("敬业度") == "员工敬业度"
        assert w.canonical_for("transformational leadership") == "变革型领导"
        # canonical 自身映射到自己
        assert w.canonical_for("变革型领导") == "变革型领导"

    def test_multiplier_for(self, sample_yaml):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.from_yaml_path(sample_yaml)
        assert w.multiplier_for("变革型领导") == 2.0
        assert w.multiplier_for("没收录") == 1.0

    def test_score_hits_dedups(self, sample_yaml):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.from_yaml_path(sample_yaml)
        # canonical + synonym 同一概念，去重后只算一次
        s1 = w.score_hits(["变革型领导", "transformational leadership"])
        s2 = w.score_hits(["变革型领导"])
        assert s1 == s2 == pytest.approx(1.0)  # mult(2) - default(1) = 1
        # 两个不同概念
        s3 = w.score_hits(["变革型领导", "员工敬业度"])
        assert s3 == pytest.approx(2.0)

    def test_score_hits_empty(self, sample_yaml):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.from_yaml_path(sample_yaml)
        assert w.score_hits([]) == 0.0
        assert w.score_hits(None) == 0.0

    def test_all_canonical_filter_by_domain(self, sample_yaml):
        from src.literature_feed.trend import DomainWeights

        w = DomainWeights.from_yaml_path(sample_yaml)
        io_only = w.all_canonical(domain="IO")
        assert set(io_only) == {"变革型领导", "工作满意度"}
        all_ = w.all_canonical()
        assert len(all_) == 4


# =============================================================================
# scorer
# =============================================================================

class TestScorer:

    def test_recency_decay_today_returns_one(self):
        from src.literature_feed.trend import compute_recency_decay

        today = date.today()
        assert compute_recency_decay(today.isoformat(), ref_date=today) == 1.0

    def test_recency_decay_half_life_at_90(self):
        from src.literature_feed.trend import compute_recency_decay

        ref = date(2026, 5, 1)
        old = (ref - timedelta(days=90)).isoformat()
        v = compute_recency_decay(old, ref_date=ref, half_life_days=90)
        assert v == pytest.approx(0.5, abs=1e-6)

    def test_recency_decay_invalid_returns_one(self):
        from src.literature_feed.trend import compute_recency_decay

        assert compute_recency_decay(None) == 1.0
        assert compute_recency_decay("") == 1.0
        assert compute_recency_decay("not-a-date") == 1.0

    def test_recency_decay_future_clipped_to_one(self):
        from src.literature_feed.trend import compute_recency_decay

        ref = date(2026, 5, 1)
        future = (ref + timedelta(days=10)).isoformat()
        assert compute_recency_decay(future, ref_date=ref) == 1.0

    def test_recency_decay_yyyy_mm_format(self):
        from src.literature_feed.trend import compute_recency_decay

        ref = date(2026, 5, 1)
        # YYYY-MM 自动补 -01
        v = compute_recency_decay("2026-02", ref_date=ref, half_life_days=90)
        assert 0 < v < 1

    def test_priority_score_basic(self):
        from src.literature_feed.trend import compute_priority_score

        # decay=1 conf=0.8 domain=1.0 → 1*0.8*(1+1)=1.6
        v = compute_priority_score(confidence=0.8, domain_score=1.0, decay=1.0)
        assert v == pytest.approx(1.6)

    def test_priority_score_clamps_confidence(self):
        from src.literature_feed.trend import compute_priority_score

        v_over = compute_priority_score(confidence=1.5, domain_score=0.0, decay=1.0)
        assert v_over == pytest.approx(1.0)
        v_neg = compute_priority_score(confidence=-0.3, domain_score=0.0, decay=1.0)
        assert v_neg == pytest.approx(0.0)

    def test_priority_score_handles_nan(self):
        from src.literature_feed.trend import compute_priority_score

        v = compute_priority_score(confidence=float("nan"), domain_score=1.0, decay=1.0)
        assert v == 0.0

    def test_priority_score_none_confidence_zero(self):
        from src.literature_feed.trend import compute_priority_score

        v = compute_priority_score(confidence=None, domain_score=1.0, decay=1.0)
        assert v == 0.0

    def test_update_candidate_scores_backfills(self, feed_root, sample_yaml):
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.feed_store import ArticleRow, CandidateRow
        from src.literature_feed.trend import DomainWeights, update_candidate_scores

        store = FeedStore()
        store.upsert_source(source_id="X", journal_name="x", fetcher_type="manual")
        aid = store.upsert_article(ArticleRow(
            title="t1", source_id="X", provenance="manual", title_norm="t1",
            issued_date=(date.today() - timedelta(days=30)).isoformat(),
            fetched_at=datetime.now(timezone.utc).isoformat(),
        ))
        cid = store.insert_candidate(CandidateRow(
            article_id=aid, kind="construct", name="变革型领导",
            normalized_name="变革型领导", confidence=0.9,
            evidence_quote="这是 evidence", evidence_valid=True,
            iohr_hits=["变革型领导"],
            llm_config_hash="x", prompt_version="v1", status="pending",
        ))
        assert cid > 0
        w = DomainWeights.from_yaml_path(sample_yaml)
        n = update_candidate_scores(store, w)
        assert n == 1
        row = store.connection.execute(
            "SELECT priority_score, domain_score FROM llm_candidates WHERE candidate_id=?",
            (cid,),
        ).fetchone()
        # domain_score = mult(2) - default(1) = 1
        assert row["domain_score"] == pytest.approx(1.0)
        assert row["priority_score"] > 0.5
        store.close()


# =============================================================================
# aggregator
# =============================================================================

class TestAggregator:

    def _seed_articles_and_keywords(self, store, *, n_old: int = 2, n_new: int = 3):
        """种几篇文章 + 关键词。返回 article_ids 列表。"""
        from src.literature_feed.storage.feed_store import ArticleRow

        store.upsert_source(source_id="J", journal_name="j", fetcher_type="manual")
        ids = []
        today = date.today()
        for i in range(n_old):
            aid = store.upsert_article(ArticleRow(
                title=f"old-{i}", source_id="J", provenance="manual", title_norm=f"old-{i}",
                issued_date=(today - timedelta(days=200 + i)).isoformat(),
                fetched_at=datetime.now(timezone.utc).isoformat(),
            ))
            store.add_keywords(aid, ["旧关键词"])
            ids.append(aid)
        for i in range(n_new):
            aid = store.upsert_article(ArticleRow(
                title=f"new-{i}", source_id="J", provenance="manual", title_norm=f"new-{i}",
                issued_date=(today - timedelta(days=10 + i)).isoformat(),
                fetched_at=datetime.now(timezone.utc).isoformat(),
            ))
            store.add_keywords(aid, ["变革型领导", "未收录词"])
            ids.append(aid)
        return ids

    def test_compute_keyword_trends_filters_window(self, feed_root, sample_yaml):
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.trend import DomainWeights, compute_keyword_trends

        store = FeedStore()
        self._seed_articles_and_keywords(store, n_old=2, n_new=3)
        w = DomainWeights.from_yaml_path(sample_yaml)

        rows = compute_keyword_trends(store, weights=w, window_days=30, top_n=10)
        # 30 天窗口里只有 new-* (3 篇)，旧关键词不应出现
        keywords = {r.keyword for r in rows}
        assert "旧关键词" not in keywords
        # 变革型领导（命中 IO）+ 未收录词
        assert "变革型领导" in keywords
        store.close()

    def test_compute_keyword_trends_domain_only(self, feed_root, sample_yaml):
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.trend import DomainWeights, compute_keyword_trends

        store = FeedStore()
        self._seed_articles_and_keywords(store, n_old=0, n_new=3)
        w = DomainWeights.from_yaml_path(sample_yaml)

        rows = compute_keyword_trends(store, weights=w, window_days=30,
                                      top_n=10, domain_only=True)
        for r in rows:
            assert r.domain in ("IO", "HR", "OB")
        # 未收录词被过滤
        assert all(r.keyword != "未收录词" for r in rows)
        store.close()

    def test_compute_keyword_trends_top_n_limit(self, feed_root, sample_yaml):
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.trend import DomainWeights, compute_keyword_trends

        store = FeedStore()
        self._seed_articles_and_keywords(store, n_old=0, n_new=3)
        w = DomainWeights.from_yaml_path(sample_yaml)

        rows = compute_keyword_trends(store, weights=w, window_days=30, top_n=1)
        assert len(rows) == 1
        store.close()

    def test_compute_keyword_trends_empty_store(self, feed_root, sample_yaml):
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.trend import DomainWeights, compute_keyword_trends

        store = FeedStore()
        w = DomainWeights.from_yaml_path(sample_yaml)
        rows = compute_keyword_trends(store, weights=w)
        assert rows == []
        store.close()

    def test_compute_keyword_trends_synonym_folding(self, feed_root, sample_yaml):
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.feed_store import ArticleRow
        from src.literature_feed.trend import DomainWeights, compute_keyword_trends

        store = FeedStore()
        store.upsert_source(source_id="J", journal_name="j", fetcher_type="manual")
        today = date.today()
        # 一篇用 canonical，一篇用 synonym → 应折叠到同一行
        aid1 = store.upsert_article(ArticleRow(
            title="a", source_id="J", provenance="manual", title_norm="a",
            issued_date=(today - timedelta(days=5)).isoformat(),
            fetched_at=datetime.now(timezone.utc).isoformat(),
        ))
        store.add_keywords(aid1, ["员工敬业度"])
        aid2 = store.upsert_article(ArticleRow(
            title="b", source_id="J", provenance="manual", title_norm="b",
            issued_date=(today - timedelta(days=3)).isoformat(),
            fetched_at=datetime.now(timezone.utc).isoformat(),
        ))
        store.add_keywords(aid2, ["work engagement"])

        w = DomainWeights.from_yaml_path(sample_yaml)
        rows = compute_keyword_trends(store, weights=w, window_days=30, top_n=10)
        engage = [r for r in rows if r.canonical == "员工敬业度"]
        assert len(engage) == 1, "synonym should fold to canonical"
        assert engage[0].count == 2  # 两篇都计数
        store.close()

    def test_compute_domain_summary_buckets(self):
        from src.literature_feed.trend import TrendRow, compute_domain_summary

        rows = [
            TrendRow("a", "变革型领导", "IO", 3, 5.0, "2026-05-01"),
            TrendRow("b", "员工敬业度", "HR", 2, 4.0, "2026-04-01"),
            TrendRow("c", "组织承诺", "OB", 1, 1.5, "2026-03-01"),
            TrendRow("d", None, None, 4, 2.0, "2026-02-01"),  # 其他
        ]
        out = compute_domain_summary(rows)
        assert out["IO"]["count"] == 3
        assert out["HR"]["count"] == 2
        assert out["OB"]["count"] == 1
        assert out["其他"]["count"] == 4
        assert out["IO"]["weighted"] == pytest.approx(5.0)

    def test_compute_domain_summary_empty(self):
        from src.literature_feed.trend import compute_domain_summary

        out = compute_domain_summary([])
        for dom in ("IO", "HR", "OB", "其他"):
            assert out[dom] == {"count": 0, "weighted": 0.0}
