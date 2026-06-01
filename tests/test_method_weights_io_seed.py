"""method_weights.yaml + MethodWeights 回归（2026-05-30 Round 2）。

验证：
- 8 条种子方法 canonical 加载正确
- 同义词反查命中 canonical
- score_hits 数值校验（0.5 / canonical）
- compute_priority_score 接受 method_score 后，priority 严格上升
- update_candidate_scores 给 method_weights 后，命中方法关键词的候选 priority 高于不给时
- empty / 未配置词条保护：不传 method_weights 与传空 MethodWeights 等价
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from src.literature_feed.paths import METHOD_WEIGHTS_PATH
from src.literature_feed.storage.feed_store import ArticleRow, CandidateRow, FeedStore
from src.literature_feed.trend.method_weights import MethodWeights
from src.literature_feed.trend.scorer import (
    compute_method_score,
    compute_priority_score,
    update_candidate_scores,
)
from src.literature_feed.trend.domain_weights import DomainWeights


def _load() -> MethodWeights:
    return MethodWeights.from_yaml_path(METHOD_WEIGHTS_PATH)


# ---------------------------------------------------------------------------
# YAML 加载 + 词表完整性
# ---------------------------------------------------------------------------

class TestYamlLoading:
    def test_yaml_file_loads(self):
        mw = _load()
        assert mw.version == 1
        assert mw.default_weight == 1.0
        assert mw.method_multiplier == 1.5

    def test_seed_canonicals_present(self):
        mw = _load()
        canonicals = set(mw.all_canonical())
        # 至少 8 条种子方法
        for expected in [
            "纵向设计", "多层模型", "多源设计", "经验取样",
            "时间滞后设计", "配对分析", "元分析", "准实验",
        ]:
            assert expected in canonicals, f"method canonical 应包含「{expected}」"


# ---------------------------------------------------------------------------
# 同义词反查
# ---------------------------------------------------------------------------

class TestSynonymLookup:
    @pytest.mark.parametrize("term,expected_canonical", [
        ("longitudinal design", "纵向设计"),
        ("longitudinal study", "纵向设计"),
        ("纵向研究", "纵向设计"),
        ("HLM", "多层模型"),
        ("multilevel model", "多层模型"),
        ("hierarchical linear model", "多层模型"),
        ("ESM", "经验取样"),
        ("experience sampling", "经验取样"),
        ("APIM", "配对分析"),
        ("meta-analysis", "元分析"),
        ("quasi-experiment", "准实验"),
    ])
    def test_synonym_to_canonical(self, term, expected_canonical):
        mw = _load()
        assert mw.canonical_for(term) == expected_canonical
        assert mw.is_method(term)

    def test_unconfigured_term_returns_none(self):
        mw = _load()
        assert mw.canonical_for("xyz-not-a-real-method") is None
        assert mw.is_method("xyz-not-a-real-method") is False


# ---------------------------------------------------------------------------
# score_hits 数值校验
# ---------------------------------------------------------------------------

class TestScoreHits:
    def test_empty_hits_zero(self):
        mw = _load()
        assert mw.score_hits([]) == 0.0
        assert mw.score_hits(None) == 0.0  # type: ignore[arg-type]

    def test_single_canonical_half(self):
        mw = _load()
        assert abs(mw.score_hits(["纵向设计"]) - 0.5) < 1e-6

    def test_single_synonym_half(self):
        mw = _load()
        # 同义词应该等同于 canonical
        assert abs(mw.score_hits(["longitudinal design"]) - 0.5) < 1e-6

    def test_multiple_canonicals_accumulate(self):
        mw = _load()
        score = mw.score_hits(["纵向设计", "HLM", "ESM"])
        assert abs(score - 1.5) < 1e-6  # 3 × 0.5

    def test_canonical_synonym_dedupe(self):
        mw = _load()
        # 同 canonical 多形态命中只算一次
        score = mw.score_hits(["纵向设计", "longitudinal study", "longitudinal design"])
        assert abs(score - 0.5) < 1e-6

    def test_unconfigured_term_zero_contribution(self):
        mw = _load()
        score = mw.score_hits(["xyz-not-real", "another-fake"])
        assert score == 0.0


# ---------------------------------------------------------------------------
# compute_priority_score 集成 method_score
# ---------------------------------------------------------------------------

class TestPriorityScoreWithMethod:
    def test_default_method_score_zero_is_backward_compatible(self):
        # 不传 method_score → 与旧公式一致
        old = compute_priority_score(confidence=0.8, domain_score=0.5, decay=0.9)
        new = compute_priority_score(
            confidence=0.8, domain_score=0.5, decay=0.9, method_score=0.0,
        )
        assert abs(old - new) < 1e-9

    def test_positive_method_score_strictly_increases_priority(self):
        base = compute_priority_score(confidence=0.8, domain_score=0.5, decay=0.9)
        bumped = compute_priority_score(
            confidence=0.8, domain_score=0.5, decay=0.9, method_score=0.5,
        )
        assert bumped > base
        # 公式：base × (1 + 0.5) = base × 1.5
        assert abs(bumped - base * 1.5) < 1e-9

    def test_negative_method_score_clamped_to_zero(self):
        # 传负数等价于 0（防御性钳位）
        a = compute_priority_score(confidence=0.8, domain_score=0.5, decay=0.9, method_score=0.0)
        b = compute_priority_score(confidence=0.8, domain_score=0.5, decay=0.9, method_score=-1.0)
        assert abs(a - b) < 1e-9


# ---------------------------------------------------------------------------
# update_candidate_scores 端到端：方法加权确实抬高 priority
# ---------------------------------------------------------------------------

@pytest.fixture
def feed_store(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    db = tmp_path / "test_feed.sqlite"
    store = FeedStore(db)
    store.upsert_source(
        source_id="test_journal",
        journal_name="Test Journal",
        fetcher_type="manual",
    )
    yield store
    store.close()


class TestUpdateCandidateScoresEndToEnd:
    def _seed_two_articles(self, store: FeedStore) -> tuple[int, int]:
        """种 2 篇文章：A 命中纵向设计，B 不命中任何方法。"""
        with store.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO articles(
                    title, author_json, abstract, issued_date, doi,
                    container_title, publisher, keyword_json,
                    source_id, provenance, metadata_status, iohr_hits_json,
                    raw_hash, fetched_at, fetch_run_id, title_norm
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "A longitudinal study of leadership",
                    None,
                    "We use a longitudinal design with HLM to test ...",
                    "2026-01-15",
                    "10.1/test-a",
                    "Test J", None, None,
                    "test_journal", "manual", "complete",
                    json.dumps(["变革型领导"]),
                    "hashA", "2026-05-30T00:00:00Z", None,
                    "a longitudinal study of leadership",
                ),
            )
            article_a = cur.lastrowid
            cur = conn.execute(
                """
                INSERT INTO articles(
                    title, author_json, abstract, issued_date, doi,
                    container_title, publisher, keyword_json,
                    source_id, provenance, metadata_status, iohr_hits_json,
                    raw_hash, fetched_at, fetch_run_id, title_norm
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "Cross-sectional survey of leadership styles",
                    None,
                    "A single-wave questionnaire study covering leadership styles.",
                    "2026-01-15",
                    "10.1/test-b",
                    "Test J", None, None,
                    "test_journal", "manual", "complete",
                    json.dumps(["变革型领导"]),
                    "hashB", "2026-05-30T00:00:00Z", None,
                    "cross-sectional survey of leadership styles",
                ),
            )
            article_b = cur.lastrowid

            # 给两篇都加一个 pending 候选
            for aid, name in [(article_a, "candidate-a"), (article_b, "candidate-b")]:
                conn.execute(
                    """
                    INSERT INTO llm_candidates(
                        article_id, kind, name, normalized_name,
                        definition, method_category, evidence_quote, evidence_valid,
                        confidence, novelty_hint, domain_score, priority_score,
                        iohr_hits_json, llm_config_hash, prompt_version,
                        status, created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        aid, "construct", name, name,
                        "test", None, "evidence", 1,
                        0.8, "extension", 0, 0,
                        json.dumps(["变革型领导"]),
                        "h", "v1",
                        "pending", "2026-05-30T00:00:00Z",
                    ),
                )
        return article_a, article_b

    def test_method_weighted_candidate_outranks_unweighted(self, feed_store: FeedStore):
        self._seed_two_articles(feed_store)

        # 域权重一份（足够把变革型领导算进去；这里用空也行，只关心 method 增量）
        dw = DomainWeights.from_mapping({
            "version": 1,
            "default_weight": 1.0,
            "domain_multiplier": 1.5,
            "domains": {"IO": {"concepts": [
                {"canonical": "变革型领导", "synonyms": ["transformational leadership"]},
            ]}},
        })

        # 第一遍：不给 method_weights
        update_candidate_scores(feed_store, dw, ref_date=date(2026, 5, 30))
        rows1 = list(feed_store.connection.execute(
            "SELECT name, priority_score FROM llm_candidates ORDER BY name"
        ).fetchall())
        priority_a_no_method = next(r["priority_score"] for r in rows1 if r["name"] == "candidate-a")
        priority_b_no_method = next(r["priority_score"] for r in rows1 if r["name"] == "candidate-b")
        # 同样的 confidence/domain/decay → priority 相等
        assert abs(priority_a_no_method - priority_b_no_method) < 1e-6

        # 第二遍：给 method_weights → A 应严格高于 B
        mw = _load()
        update_candidate_scores(feed_store, dw, method_weights=mw, ref_date=date(2026, 5, 30))
        rows2 = list(feed_store.connection.execute(
            "SELECT name, priority_score FROM llm_candidates ORDER BY name"
        ).fetchall())
        priority_a_with_method = next(r["priority_score"] for r in rows2 if r["name"] == "candidate-a")
        priority_b_with_method = next(r["priority_score"] for r in rows2 if r["name"] == "candidate-b")

        assert priority_a_with_method > priority_b_with_method, (
            "命中纵向设计/HLM 的候选 priority 应高于纯横断研究"
        )
        # B 的 priority 应与"不给 method"时基本相同（B 文本里没有方法关键词）
        assert abs(priority_b_with_method - priority_b_no_method) < 1e-6

    def test_empty_method_weights_is_noop(self, feed_store: FeedStore):
        self._seed_two_articles(feed_store)
        dw = DomainWeights.empty()
        # 空方法词表 → 与不传 method_weights 等价
        update_candidate_scores(feed_store, dw, ref_date=date(2026, 5, 30))
        before = {r["name"]: r["priority_score"] for r in feed_store.connection.execute(
            "SELECT name, priority_score FROM llm_candidates"
        ).fetchall()}

        update_candidate_scores(
            feed_store, dw, method_weights=MethodWeights.empty(), ref_date=date(2026, 5, 30),
        )
        after = {r["name"]: r["priority_score"] for r in feed_store.connection.execute(
            "SELECT name, priority_score FROM llm_candidates"
        ).fetchall()}
        for k in before:
            assert abs(before[k] - after[k]) < 1e-6
