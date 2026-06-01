"""Tests for trending_weights module (~17 tests)."""

from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from src.literature_feed.trend.trending_weights import (
    TrendingEntry,
    TrendingWeights,
    compute_trending_weights,
    load_default_trending,
    load_trending_weights,
    write_trending_yaml,
)


# ---------------------------------------------------------------------------
# TrendingEntry / TrendingWeights dataclasses
# ---------------------------------------------------------------------------


class TestTrendingEntry:
    def test_fields(self):
        e = TrendingEntry(
            keyword="employee engagement",
            multiplier=1.15,
            spike_ratio=4.0,
            window_count=10,
            baseline_count=2,
        )
        assert e.keyword == "employee engagement"
        assert e.multiplier == 1.15
        assert e.spike_ratio == 4.0
        assert e.window_count == 10
        assert e.baseline_count == 2

    def test_frozen(self):
        e = TrendingEntry(keyword="x", multiplier=1.0, spike_ratio=1.0, window_count=1, baseline_count=1)
        with pytest.raises(Exception):
            e.keyword = "y"  # type: ignore[misc]


class TestTrendingWeights:
    def _make_entry(self, kw, mult=1.1, spike=2.0, wc=5, bc=2):
        return TrendingEntry(keyword=kw, multiplier=mult, spike_ratio=spike, window_count=wc, baseline_count=bc)

    def test_empty(self):
        tw = TrendingWeights.empty()
        assert tw.entries == ()
        assert tw.ignored == ()
        assert tw.promoted == ()

    def test_post_init_builds_index(self):
        e = self._make_entry("Employee Engagement")
        tw = TrendingWeights(entries=(e,))
        # index is keyed by lower-case
        assert "employee engagement" in tw._index

    def test_trending_score_single_hit(self):
        e = self._make_entry("employee engagement", mult=1.15)
        tw = TrendingWeights(entries=(e,))
        score = tw.trending_score(["employee engagement"])
        assert abs(score - 0.15) < 1e-9

    def test_trending_score_no_hit(self):
        tw = TrendingWeights.empty()
        assert tw.trending_score(["anything"]) == 0.0

    def test_trending_score_ignores_ignored_keyword(self):
        e = self._make_entry("burnout", mult=1.2)
        tw = TrendingWeights(entries=(e,), ignored=("burnout",))
        assert tw.trending_score(["burnout"]) == 0.0

    def test_trending_score_deduplicates_keywords(self):
        e = self._make_entry("burnout", mult=1.2)
        tw = TrendingWeights(entries=(e,))
        score = tw.trending_score(["burnout", "burnout", "Burnout"])
        assert abs(score - 0.2) < 1e-9  # counted once

    def test_is_ignored(self):
        tw = TrendingWeights(ignored=("burnout",))
        assert tw.is_ignored("Burnout") is True
        assert tw.is_ignored("engagement") is False

    def test_is_promoted(self):
        tw = TrendingWeights(promoted=("LMX",))
        assert tw.is_promoted("lmx") is True
        assert tw.is_promoted("other") is False

    def test_frozen(self):
        tw = TrendingWeights.empty()
        with pytest.raises(Exception):
            tw.window_days = 60  # type: ignore[misc]



# ---------------------------------------------------------------------------
# write_trending_yaml / load_trending_weights round-trip
# ---------------------------------------------------------------------------


class TestWriteLoadRoundTrip:
    def _make_tw(self):
        entries = (
            TrendingEntry(keyword="employee engagement", multiplier=1.15, spike_ratio=3.5, window_count=7, baseline_count=2),
            TrendingEntry(keyword="burnout", multiplier=1.05, spike_ratio=1.5, window_count=3, baseline_count=2),
        )
        return TrendingWeights(
            entries=entries,
            generated_at="2026-05-30T12:00:00+00:00",
            window_days=30,
            baseline_days=90,
            multiplier_cap=1.3,
            ignored=("stress",),
            promoted=("LMX",),
            promoted_log=("2026-05-30: promoted LMX",),
        )

    def test_round_trip(self, tmp_path):
        tw = self._make_tw()
        path = tmp_path / "trending_weights.yaml"
        write_trending_yaml(tw, path)
        assert path.exists()
        loaded = load_trending_weights(path)
        assert len(loaded.entries) == 2
        assert loaded.entries[0].keyword == "employee engagement"
        assert abs(loaded.entries[0].multiplier - 1.15) < 1e-6
        assert abs(loaded.entries[0].spike_ratio - 3.5) < 1e-6
        assert loaded.window_days == 30
        assert loaded.baseline_days == 90
        assert abs(loaded.multiplier_cap - 1.3) < 1e-6
        assert "stress" in loaded.ignored
        assert "LMX" in loaded.promoted
        assert len(loaded.promoted_log) == 1

    def test_write_atomic_tmp_file_removed(self, tmp_path):
        tw = self._make_tw()
        path = tmp_path / "tw.yaml"
        write_trending_yaml(tw, path)
        tmp = path.with_suffix(".yaml.tmp")
        assert not tmp.exists(), "tmp file should be removed after atomic replace"

    def test_load_missing_file_returns_empty(self, tmp_path):
        result = load_trending_weights(tmp_path / "nonexistent.yaml")
        assert result.entries == ()
        assert result.ignored == ()

    def test_load_corrupt_file_returns_empty(self, tmp_path):
        path = tmp_path / "corrupt.yaml"
        path.write_text("not valid yaml: [", encoding="utf-8")
        result = load_trending_weights(path)
        assert result.entries == ()

    def test_write_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "trending.yaml"
        tw = TrendingWeights.empty()
        write_trending_yaml(tw, nested)
        assert nested.exists()


# ---------------------------------------------------------------------------
# compute_trending_weights (mocked)
# ---------------------------------------------------------------------------


class TestComputeTrendingWeights:
    def _make_row(self, canonical, count, weighted_count):
        from src.literature_feed.trend.aggregator import TrendRow
        return TrendRow(keyword=canonical, canonical=canonical, domain="IO",
                        count=count, weighted_count=float(weighted_count),
                        latest_issued_date="2026-05-01")

    def _run(self, window_rows, baseline_rows, existing=None, multiplier_cap=1.3):
        from unittest.mock import MagicMock, patch
        store = MagicMock()
        dw = MagicMock()
        with patch("src.literature_feed.trend.aggregator.compute_keyword_trends") as mock_ckw:
            mock_ckw.side_effect = [window_rows, baseline_rows]
            return compute_trending_weights(store, domain_weights=dw,
                                           multiplier_cap=multiplier_cap, existing=existing)

    def test_spike_ratio_and_multiplier(self):
        r = self._make_row("employee engagement", 10, 8.0)
        b = self._make_row("employee engagement", 4, 4.0)
        tw = self._run([r], [b])
        assert len(tw.entries) == 1
        assert abs(tw.entries[0].spike_ratio - 2.0) < 1e-3
        assert abs(tw.entries[0].multiplier - 1.05) < 1e-3

    def test_no_spike_excluded(self):
        r = self._make_row("burnout", 2, 2.0)
        b = self._make_row("burnout", 10, 4.0)
        tw = self._run([r], [b])
        assert len(tw.entries) == 0

    def test_ignored_keyword_excluded(self):
        existing = TrendingWeights(ignored=("employee engagement",))
        r = self._make_row("employee engagement", 10, 10.0)
        b = self._make_row("employee engagement", 2, 2.0)
        tw = self._run([r], [b], existing=existing)
        assert len(tw.entries) == 0

    def test_multiplier_cap_respected(self):
        r = self._make_row("lmx", 100, 100.0)
        b = self._make_row("lmx", 1, 1.0)
        tw = self._run([r], [b], multiplier_cap=1.3)
        assert len(tw.entries) == 1
        assert tw.entries[0].multiplier <= 1.3

    def test_promoted_entry_included_without_spike(self):
        existing = TrendingWeights(promoted=("special topic",))
        r = self._make_row("special topic", 2, 2.0)
        b = self._make_row("special topic", 10, 4.0)
        tw = self._run([r], [b], existing=existing)
        assert len(tw.entries) == 1
        assert tw.entries[0].keyword == "special topic"

    def test_carries_over_ignored_promoted(self):
        existing = TrendingWeights(ignored=("x",), promoted=("y",), promoted_log=("log",))
        tw = self._run([], [], existing=existing)
        assert "x" in tw.ignored
        assert "y" in tw.promoted
        assert "log" in tw.promoted_log

    def test_entries_sorted_desc(self):
        r1 = self._make_row("a", 10, 10.0)
        r2 = self._make_row("b", 20, 20.0)
        b1 = self._make_row("a", 2, 2.0)
        b2 = self._make_row("b", 2, 4.0)
        tw = self._run([r1, r2], [b1, b2])
        if len(tw.entries) >= 2:
            assert tw.entries[0].spike_ratio >= tw.entries[1].spike_ratio


# ---------------------------------------------------------------------------
# Scorer integration: backward compat
# ---------------------------------------------------------------------------


class TestScorerTrendingIntegration:
    def test_backward_compat_no_trending_param(self):
        from src.literature_feed.trend.scorer import compute_priority_score
        r1 = compute_priority_score(confidence=0.8, domain_score=0.5, decay=0.9)
        r2 = compute_priority_score(confidence=0.8, domain_score=0.5, decay=0.9, trending_score=0.0)
        assert abs(r1 - r2) < 1e-12

    def test_trending_score_increases_priority(self):
        from src.literature_feed.trend.scorer import compute_priority_score
        base = compute_priority_score(confidence=0.8, domain_score=0.5, decay=0.9)
        boosted = compute_priority_score(confidence=0.8, domain_score=0.5, decay=0.9, trending_score=0.1)
        assert boosted > base

    def test_trending_zero_no_effect(self):
        from src.literature_feed.trend.scorer import compute_priority_score
        r1 = compute_priority_score(confidence=0.8, domain_score=0.0, decay=1.0)
        r2 = compute_priority_score(confidence=0.8, domain_score=0.0, decay=1.0, trending_score=0.0)
        assert abs(r1 - r2) < 1e-12


# ---------------------------------------------------------------------------
# load_default_trending convenience
# ---------------------------------------------------------------------------


class TestLoadDefaultTrending:
    def test_missing_path_returns_empty(self, tmp_path):
        result = load_default_trending(path=tmp_path / "trending.yaml")
        assert isinstance(result, TrendingWeights)
        assert result.entries == ()

    def test_existing_file_loaded(self, tmp_path):
        tw = TrendingWeights(
            entries=(TrendingEntry(keyword="test", multiplier=1.05, spike_ratio=2.0, window_count=5, baseline_count=2),),
            generated_at="2026-05-30T00:00:00+00:00",
        )
        path = tmp_path / "trending.yaml"
        write_trending_yaml(tw, path)
        result = load_default_trending(path=path)
        assert len(result.entries) == 1
        assert result.entries[0].keyword == "test"
