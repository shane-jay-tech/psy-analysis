"""Crossref API fetcher（心理学报 + 心理科学进展）。

按 ISSN 抓增量。带 ``mailto`` 进 Polite Pool（合规 + 限流更宽松）。
请求间 ``rate_limit_seconds`` 节流，遇 429/503 读 ``Retry-After`` 抛
``RateLimitedError``。

DOI 前缀 ``10.3724`` 由心理所主办两刊共用，靠 ISSN 区分 source。
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any, Dict, List, Optional

from ..parsers.csl_normalizer import crossref_to_raw
from .base import (
    FetchError,
    FetchResult,
    RawArticle,
    RateLimitedError,
    SchemaChangedError,
    SourceConfig,
    SourceFetcher,
)


_BASE_URL = "https://api.crossref.org/works"


class CrossrefFetcher(SourceFetcher):
    """通用 Crossref ISSN fetcher。

    ``config.extra`` 必须含 ``issn``（或顶层 ``config.issn``）。
    """

    def __init__(
        self,
        config: SourceConfig,
        *,
        requests_module: Any = None,
        sleep_fn: Any = None,
    ) -> None:
        super().__init__(config)
        self._requests = requests_module          # 测试注入
        self._sleep = sleep_fn or time.sleep

    # ------------------------------------------------------------------ #

    def _get_requests(self):
        if self._requests is not None:
            return self._requests
        try:
            import requests  # type: ignore
        except ImportError as exc:
            raise FetchError("requests 库未安装") from exc
        return requests

    def fetch_since(
        self,
        since_date: Optional[str] = None,
        *,
        limit: int = 20,
    ) -> FetchResult:
        issn = self.config.issn or self.config.extra.get("issn")
        if not issn:
            raise FetchError(f"source {self.source_id} 未配置 ISSN")

        since = since_date or _default_since()
        params = [
            ("filter", f"issn:{issn},from-issued-date:{since}"),
            ("sort", "issued"),
            ("order", "desc"),
            ("rows", str(int(max(1, min(100, limit))))),
            ("mailto", self.config.contact_email),
        ]

        rq = self._get_requests()
        url = _BASE_URL
        try:
            resp = rq.get(
                url,
                params=params,
                headers={"User-Agent": self.config.user_agent},
                timeout=30,
            )
        except Exception as exc:
            raise FetchError(f"Crossref 请求失败：{exc}") from exc

        status = getattr(resp, "status_code", 0)
        if status in (429, 503):
            retry_after = None
            try:
                retry_after = int(resp.headers.get("Retry-After", "60"))
            except (TypeError, ValueError):
                retry_after = 60
            raise RateLimitedError(
                f"Crossref 限流 ({status})", retry_after=retry_after,
            )
        if status != 200:
            raise FetchError(f"Crossref 返回 {status}: {getattr(resp, 'text', '')[:200]}")

        try:
            data = resp.json()
        except (ValueError, TypeError) as exc:
            raise FetchError(f"Crossref 响应非 JSON：{exc}") from exc

        message = (data or {}).get("message") or {}
        items: List[Dict[str, Any]] = list(message.get("items") or [])

        if not items:
            # 不抛 SchemaChangedError；可能就是没新文章
            return FetchResult(
                source_id=self.source_id,
                articles=[],
                raw_records=[],
                probe_signature=self.health_signature(),
                notes="empty result",
            )

        articles: List[RawArticle] = []
        raw_records: List[Dict[str, Any]] = []
        bad = 0
        for item in items:
            ra = crossref_to_raw(item, source_id=self.source_id)
            if ra is None:
                bad += 1
                continue
            # ISSN 双刊共享 DOI 前缀，确保 container_title 落地为 source 配的期刊名
            if not ra.container_title:
                ra.container_title = self.config.journal_name
            articles.append(ra)
            raw_records.append({
                "fetched_at": _utc_now(),
                "source_id": self.source_id,
                "issn": issn,
                "url": _build_request_url(url, params),
                "item": item,
            })

        # 全数据无效 → schema 可能改了
        if items and not articles:
            raise SchemaChangedError(
                f"Crossref 返回 {len(items)} 条但全无法解析（possible schema change）",
            )

        # 节流：只为防止下一次连续调用过快；本调用已结束
        try:
            self._sleep(self.config.rate_limit_seconds)
        except Exception:
            pass

        return FetchResult(
            source_id=self.source_id,
            articles=articles,
            raw_records=raw_records,
            probe_signature=self.health_signature(),
            notes=f"got={len(articles)} bad={bad}",
        )


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _default_since(days_back: int = 60) -> str:
    """默认从 60 天前开始抓。"""
    today = date.today()
    earlier = date.fromordinal(max(1, today.toordinal() - days_back))
    return earlier.isoformat()


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_request_url(base: str, params: List[tuple]) -> str:
    from urllib.parse import urlencode
    return f"{base}?{urlencode(params)}"
