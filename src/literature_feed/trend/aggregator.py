"""关键词趋势聚合：article_keywords + 90 天半衰期指数衰减。

输入：article_keywords 表 + articles.issued_date
输出：[{keyword, canonical, domain, count, weighted_count, latest_issued_date}, ...]
- weighted_count = Σ decay(article.issued_date) × multiplier(canonical)
- 默认 180 天窗口，半衰期 90 天，TopN=30
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

from ..storage.feed_store import FeedStore
from .domain_weights import DomainWeights
from .scorer import compute_recency_decay

logger = logging.getLogger(__name__)


@dataclass
class TrendRow:
    keyword: str               # 展示名（canonical 或原始 keyword_norm）
    canonical: Optional[str]   # IO/HR/OB 词表里的 canonical（命中才有）
    domain: Optional[str]      # IO / HR / OB / None
    count: int
    weighted_count: float
    latest_issued_date: Optional[str]
    article_ids: List[int] = field(default_factory=list)


def compute_keyword_trends(
    store: FeedStore,
    *,
    weights: DomainWeights,
    window_days: int = 180,
    half_life_days: float = 90.0,
    top_n: int = 30,
    domain_only: bool = False,
    ref_date: Optional[date] = None,
) -> List[TrendRow]:
    """聚合 keyword_norm，按 weighted_count 降序返回 TopN。

    Args:
        window_days: 只算 issued_date >= ref_date - window_days 的文章
        half_life_days: 半衰期（90 天）
        top_n: 返回前 N 行（≤0 返回全部）
        domain_only: True 仅返回命中 IO/HR/OB 的关键词
    """
    if ref_date is None:
        ref_date = datetime.now(timezone.utc).date()
    since_iso = (ref_date - timedelta(days=max(0, int(window_days)))).isoformat() if window_days > 0 else None

    rows = store.list_keywords(since=since_iso, only_iohr=False, limit=200000)
    if not rows:
        return []

    bucket: Dict[str, TrendRow] = {}
    for r in rows:
        norm = (r.get("keyword_norm") or "").strip()
        if not norm:
            continue
        canonical = weights.canonical_for(norm)
        domain = weights.domain_for(canonical) if canonical else None
        if domain_only and domain is None:
            continue
        # 用 canonical 折叠同义词（"engagement" 和 "工作敬业度" 合并到 "员工敬业度"）；
        # 没有 canonical 的关键词按 keyword_norm 自己一组
        bucket_key = (canonical or norm).lower()
        display = canonical or (r.get("keyword_raw") or norm)

        decay = compute_recency_decay(
            r.get("issued_date"), ref_date=ref_date, half_life_days=half_life_days,
        )
        multiplier = weights.multiplier_for(canonical) if canonical else weights.default_weight
        weighted = decay * multiplier

        existing = bucket.get(bucket_key)
        if existing is None:
            bucket[bucket_key] = TrendRow(
                keyword=display,
                canonical=canonical,
                domain=domain,
                count=1,
                weighted_count=weighted,
                latest_issued_date=r.get("issued_date") or None,
                article_ids=[int(r["article_id"])] if r.get("article_id") else [],
            )
        else:
            existing.count += 1
            existing.weighted_count += weighted
            cur_date = r.get("issued_date") or None
            if cur_date and (existing.latest_issued_date is None or cur_date > existing.latest_issued_date):
                existing.latest_issued_date = cur_date
            if r.get("article_id"):
                aid = int(r["article_id"])
                if aid not in existing.article_ids:
                    existing.article_ids.append(aid)

    ordered = sorted(
        bucket.values(),
        key=lambda x: (x.weighted_count, x.count, x.latest_issued_date or ""),
        reverse=True,
    )
    if top_n > 0:
        ordered = ordered[:top_n]
    return ordered


def compute_domain_summary(
    rows: List[TrendRow],
) -> Dict[str, Dict[str, float]]:
    """把 TrendRow 列表按 domain 汇总，给 UI 顶部摘要用。

    Returns:
        {"IO": {"count": int, "weighted": float}, ...}
    """
    out: Dict[str, Dict[str, float]] = {
        "IO": {"count": 0, "weighted": 0.0},
        "HR": {"count": 0, "weighted": 0.0},
        "OB": {"count": 0, "weighted": 0.0},
        "其他": {"count": 0, "weighted": 0.0},
    }
    for r in rows:
        bucket = r.domain if r.domain in ("IO", "HR", "OB") else "其他"
        out[bucket]["count"] += r.count
        out[bucket]["weighted"] += r.weighted_count
    return out
