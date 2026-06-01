"""Trending weights layer: detects keyword spikes over a rolling window.

Derived from recent article keywords; does NOT modify domain_weights.yaml.
Influence is bounded by multiplier_cap (default 1.2 = +20% at most).
Human-in-the-loop: ignored / promoted lists are carried over across recomputes.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
)

if TYPE_CHECKING:
    from ..storage.feed_store import FeedStore
    from .domain_weights import DomainWeights

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrendingEntry:
    keyword: str
    multiplier: float
    spike_ratio: float
    window_count: int
    baseline_count: int


@dataclass(frozen=True)
class TrendingWeights:
    entries: Tuple[TrendingEntry, ...] = ()
    generated_at: str = ""
    window_days: int = 30
    baseline_days: int = 90
    multiplier_cap: float = 1.2
    ignored: Tuple[str, ...] = ()
    promoted: Tuple[str, ...] = ()
    promoted_log: Tuple[str, ...] = ()
    _index: Mapping[str, TrendingEntry] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        idx: Dict[str, TrendingEntry] = {}
        for entry in self.entries:
            idx[entry.keyword.lower()] = entry
        object.__setattr__(self, "_index", idx)

    def trending_score(self, keywords: Iterable[str]) -> float:
        seen: set = set()
        total = 0.0
        ignored_lower = {k.lower() for k in self.ignored}
        for kw in keywords:
            key = kw.strip().lower()
            if not key or key in seen or key in ignored_lower:
                continue
            seen.add(key)
            entry = self._index.get(key)
            if entry is not None:
                total += max(0.0, entry.multiplier - 1.0)
        return total

    def is_ignored(self, keyword: str) -> bool:
        return keyword.strip().lower() in {k.lower() for k in self.ignored}

    def is_promoted(self, keyword: str) -> bool:
        return keyword.strip().lower() in {k.lower() for k in self.promoted}

    @classmethod
    def empty(cls) -> TrendingWeights:
        return cls()



# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------


def compute_trending_weights(
    store,
    *,
    domain_weights,
    window_days: int = 30,
    baseline_days: int = 90,
    multiplier_cap: float = 1.2,
    ref_date=None,
    existing=None,
) -> TrendingWeights:
    """Compute a fresh TrendingWeights from recent article keywords.

    Spike ratio = window_weighted / max(baseline_weighted, 1e-9).
    Multiplier  = 1.0 + min(cap-1, max(0, (spike_ratio-1) * 0.05)).
    Promoted entries are floored at half-cap so manual promotion is not a no-op.
    """
    from .aggregator import compute_keyword_trends

    if ref_date is None:
        ref_date = datetime.now(timezone.utc).date()

    window_rows = compute_keyword_trends(
        store,
        weights=domain_weights,
        window_days=window_days,
        top_n=0,
        ref_date=ref_date,
    )

    baseline_ref = ref_date - timedelta(days=window_days)
    baseline_rows = compute_keyword_trends(
        store,
        weights=domain_weights,
        window_days=baseline_days,
        top_n=0,
        ref_date=baseline_ref,
    )

    baseline_weighted_map: Dict[str, float] = {}
    baseline_count_map: Dict[str, int] = {}
    for r in baseline_rows:
        if r.canonical:
            key = r.canonical.lower()
            baseline_weighted_map[key] = float(r.weighted_count)
            baseline_count_map[key] = int(r.count)

    ignored_lower = {k.lower() for k in (existing.ignored if existing else ())}
    promoted_lower = {k.lower() for k in (existing.promoted if existing else ())}

    entries: List[TrendingEntry] = []
    for r in window_rows:
        if not r.canonical:
            continue
        keyword = r.canonical
        key = keyword.lower()

        if key in ignored_lower:
            continue

        window_weighted = float(r.weighted_count)
        baseline_weighted = baseline_weighted_map.get(key, 0.0)
        spike_ratio = window_weighted / max(baseline_weighted, 1e-9)
        spike_ratio = round(spike_ratio, 4)

        multiplier = 1.0 + min(
            multiplier_cap - 1.0,
            max(0.0, (spike_ratio - 1.0) * 0.05),
        )
        # Promoted entries are floored at half-cap so manual promotion is not a no-op.
        if key in promoted_lower:
            promoted_floor = 1.0 + (multiplier_cap - 1.0) * 0.5
            multiplier = max(multiplier, promoted_floor)
        multiplier = round(multiplier, 4)

        window_count = int(r.count)
        baseline_count = baseline_count_map.get(key, 0)

        if spike_ratio > 1.0 or key in promoted_lower:
            entries.append(TrendingEntry(
                keyword=keyword,
                multiplier=multiplier,
                spike_ratio=spike_ratio,
                window_count=window_count,
                baseline_count=baseline_count,
            ))

    # Add promoted entries that did not appear in window_rows at all
    if existing:
        window_keys = {e.keyword.lower() for e in entries}
        promoted_floor = 1.0 + (multiplier_cap - 1.0) * 0.5
        for promoted_kw in existing.promoted:
            pk = promoted_kw.lower()
            if pk not in window_keys and pk not in ignored_lower:
                entries.append(TrendingEntry(
                    keyword=promoted_kw,
                    multiplier=round(promoted_floor, 4),
                    spike_ratio=0.0,
                    window_count=0,
                    baseline_count=baseline_count_map.get(pk, 0),
                ))

    entries.sort(key=lambda e: e.spike_ratio, reverse=True)

    return TrendingWeights(
        entries=tuple(entries),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        window_days=window_days,
        baseline_days=baseline_days,
        multiplier_cap=multiplier_cap,
        ignored=existing.ignored if existing else (),
        promoted=existing.promoted if existing else (),
        promoted_log=existing.promoted_log if existing else (),
    )



# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def write_trending_yaml(tw: TrendingWeights, path) -> None:
    """Atomically write TrendingWeights to YAML (tmp + os.replace)."""
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML required to write trending_weights.yaml") from exc

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")

    payload = {
        "version": 1,
        "generated_at": tw.generated_at,
        "window_days": tw.window_days,
        "baseline_days": tw.baseline_days,
        "multiplier_cap": float(tw.multiplier_cap),
        "ignored": list(tw.ignored),
        "promoted": list(tw.promoted),
        "promoted_log": list(tw.promoted_log),
        "trends": [
            {
                "keyword": e.keyword,
                "multiplier": float(e.multiplier),
                "spike_ratio": float(e.spike_ratio),
                "window_count": int(e.window_count),
                "baseline_count": int(e.baseline_count),
            }
            for e in tw.entries
        ],
    }

    with open(tmp, "w", encoding="utf-8") as f:
        f.write("# trending weights - auto-generated" + chr(10))
        f.write("# generated: " + tw.generated_at + chr(10) + chr(10))
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass

    os.replace(tmp, path)
    logger.info("write_trending_yaml: wrote %d entries to %s", len(tw.entries), path)


def load_trending_weights(path) -> TrendingWeights:
    """Load TrendingWeights from YAML; returns empty on missing/parse error."""
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not available; returning empty TrendingWeights")
        return TrendingWeights.empty()

    path = Path(path)
    if not path.exists():
        logger.debug("trending_weights.yaml not found at %s", path)
        return TrendingWeights.empty()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.warning("Failed to load trending_weights.yaml: %s", exc)
        return TrendingWeights.empty()

    try:
        ignored = tuple(str(x) for x in (data.get("ignored") or []))
        promoted = tuple(str(x) for x in (data.get("promoted") or []))
        promoted_log = tuple(str(x) for x in (data.get("promoted_log") or []))
        window_days_raw = data.get("window_days")
        window_days = int(window_days_raw) if window_days_raw is not None else 30
        baseline_days_raw = data.get("baseline_days")
        baseline_days = int(baseline_days_raw) if baseline_days_raw is not None else 90
        cap_raw = data.get("multiplier_cap")
        multiplier_cap = float(cap_raw) if cap_raw is not None else 1.2
        generated_at = str(data.get("generated_at") or "")

        entries = []
        for item in (data.get("trends") or []):
            if not isinstance(item, dict):
                continue
            keyword = str(item.get("keyword") or "").strip()
            if not keyword:
                continue
            entries.append(TrendingEntry(
                keyword=keyword,
                multiplier=float(item.get("multiplier") or 1.0),
                spike_ratio=float(item.get("spike_ratio") or 0.0),
                window_count=int(item.get("window_count") or 0),
                baseline_count=int(item.get("baseline_count") or 0),
            ))

        return TrendingWeights(
            entries=tuple(entries),
            generated_at=generated_at,
            window_days=window_days,
            baseline_days=baseline_days,
            multiplier_cap=multiplier_cap,
            ignored=ignored,
            promoted=promoted,
            promoted_log=promoted_log,
        )
    except Exception as exc:
        logger.warning("Failed to parse trending_weights.yaml: %s", exc)
        return TrendingWeights.empty()


def load_default_trending(path=None) -> TrendingWeights:
    """Load from TRENDING_WEIGHTS_PATH (D drive); lazy import avoids circular imports."""
    if path is None:
        from ..paths import TRENDING_WEIGHTS_PATH
        path = TRENDING_WEIGHTS_PATH
    return load_trending_weights(path)
