"""候选打分：recency decay × confidence × (1 + domain_score) × (1 + method_score)。

- recency decay：90 天半衰期指数衰减，无 issued_date → 1.0
- domain_score：来自 DomainWeights.score_hits（IO/HR/OB 命中加分）
- method_score：来自 MethodWeights.score_hits（研究方法命中加分，可选）
- priority_score：用于 候选审阅 / 趋势排序

回填工具 update_candidate_scores() 在 YAML 改动或全量回灌时一次扫所有候选。
"""

from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Iterable, Optional

from ..parsers.csl_normalizer import extract_iohr_hits
from ..storage.feed_store import FeedStore
from .domain_weights import DomainWeights
from .method_weights import MethodWeights

if TYPE_CHECKING:
    from .trending_weights import TrendingWeights

logger = logging.getLogger(__name__)

DEFAULT_HALF_LIFE_DAYS = 90.0


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    """ISO 8601 日期字符串 → date；无法解析返回 None。"""
    if not value:
        return None
    s = value.strip()
    if not s:
        return None
    # 接受 "YYYY-MM-DD" / "YYYY-MM-DDTHH:MM:SS..." / "YYYY-MM"
    try:
        if "T" in s:
            s = s.split("T", 1)[0]
        if len(s) == 7:  # YYYY-MM
            s = s + "-01"
        return date.fromisoformat(s)
    except ValueError:
        return None


def compute_recency_decay(
    issued_date: Optional[str],
    *,
    ref_date: Optional[date] = None,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """0.5 ** (days / half_life)。无 issued_date → 1.0。未来日期 → 1.0（防钟差）。"""
    if half_life_days <= 0:
        return 1.0
    parsed = _parse_iso_date(issued_date)
    if parsed is None:
        return 1.0
    if ref_date is None:
        ref_date = datetime.now(timezone.utc).date()
    delta = (ref_date - parsed).days
    if delta <= 0:
        return 1.0
    return 0.5 ** (delta / half_life_days)


def compute_domain_score(hits: Iterable[str], weights: DomainWeights) -> float:
    """委托给 DomainWeights.score_hits。"""
    return weights.score_hits(hits)


def compute_method_score(hits: Iterable[str], weights: MethodWeights) -> float:
    """委托给 MethodWeights.score_hits。"""
    return weights.score_hits(hits)


def compute_priority_score(
    *,
    confidence: Optional[float],
    domain_score: float,
    decay: float,
    method_score: float = 0.0,
    trending_score: float = 0.0,
) -> float:
    """priority = decay × confidence × (1 + domain_score) × (1 + method_score)。

    - confidence None 或 NaN → 视作 0（明确未知就不应该排前）
    - method_score 默认 0（向后兼容；不传 method_weights 的旧调用与本次改动前完全等价）
    - 越接近 1 越应该被先看
    """
    if confidence is None:
        conf = 0.0
    else:
        try:
            conf = float(confidence)
        except (TypeError, ValueError):
            conf = 0.0
        if math.isnan(conf):
            conf = 0.0
    conf = max(0.0, min(1.0, conf))
    decay = max(0.0, float(decay))
    domain_score = max(0.0, float(domain_score))
    method_score = max(0.0, float(method_score))
    trending_score = max(0.0, float(trending_score))
    return decay * conf * (1.0 + domain_score) * (1.0 + method_score) * (1.0 + trending_score)


def update_candidate_scores(
    store: FeedStore,
    weights: DomainWeights,
    *,
    method_weights: Optional[MethodWeights] = None,
    trending: Optional["TrendingWeights"] = None,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    ref_date: Optional[date] = None,
    only_status: Optional[str] = "pending",
) -> int:
    """为候选回填 domain_score / priority_score。返回被更新的行数。

    - 默认只刷 pending（已审过的不动，避免改写人工记录的 priority）
    - YAML 改动 / 全量回灌 时调用一次
    - method_weights 给入时，priority 多乘 (1 + method_score)；不给时退化为旧公式
    """
    if ref_date is None:
        ref_date = datetime.now(timezone.utc).date()

    use_methods = method_weights is not None and bool(method_weights.methods)
    method_syn = method_weights.flat_synonyms() if use_methods else None

    sql = """
    SELECT c.candidate_id, c.confidence, c.iohr_hits_json,
           a.issued_date, a.title, a.abstract, a.keyword_json
      FROM llm_candidates c
      LEFT JOIN articles a ON a.article_id = c.article_id
    """
    params: list = []
    if only_status:
        sql += " WHERE c.status = ?"
        params.append(only_status)

    rows = store.connection.execute(sql, params).fetchall()
    updated = 0
    with store.transaction() as conn:
        for row in rows:
            try:
                hits = json.loads(row["iohr_hits_json"]) if row["iohr_hits_json"] else []
            except (TypeError, ValueError):
                hits = []
            if not isinstance(hits, list):
                hits = []
            decay = compute_recency_decay(
                row["issued_date"], ref_date=ref_date, half_life_days=half_life_days,
            )
            domain_score = compute_domain_score(hits, weights)

            method_score = 0.0
            if use_methods:
                blobs = []
                for col in ("title", "abstract"):
                    val = row[col] if col in row.keys() else None
                    if val:
                        blobs.append(val)
                kw_json = row["keyword_json"] if "keyword_json" in row.keys() else None
                if kw_json:
                    try:
                        kws = json.loads(kw_json)
                        if isinstance(kws, list):
                            blobs.extend(str(k) for k in kws if k)
                    except (TypeError, ValueError):
                        pass
                m_hits = extract_iohr_hits(blobs, method_syn) if blobs else []
                method_score = compute_method_score(m_hits, method_weights)

            # compute trending score from article keywords if trending weights provided
            t_score = 0.0
            if trending is not None:
                kw_json_t = row["keyword_json"] if "keyword_json" in row.keys() else None
                kw_list: list = []
                if kw_json_t:
                    try:
                        kw_list = json.loads(kw_json_t) or []
                        if not isinstance(kw_list, list):
                            kw_list = []
                    except (TypeError, ValueError):
                        kw_list = []
                # canonicalize all sources before trending lookup; trending._index is keyed by canonical name
                canonical_terms: list = []
                for raw in list(kw_list) + list(hits):
                    if not raw:
                        continue
                    canon = weights.canonical_for(str(raw))
                    if canon:
                        canonical_terms.append(canon)
                t_score = trending.trending_score(canonical_terms)

            priority = compute_priority_score(
                confidence=row["confidence"],
                domain_score=domain_score,
                decay=decay,
                method_score=method_score,
                trending_score=t_score,
            )
            conn.execute(
                "UPDATE llm_candidates SET domain_score = ?, priority_score = ? WHERE candidate_id = ?",
                (domain_score, priority, row["candidate_id"]),
            )
            updated += 1
    use_trending = trending is not None
    logger.info("update_candidate_scores: 回填 %d 行（method=%s, trending=%s）", updated, use_methods, use_trending)
    return updated
