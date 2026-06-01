"""心理科学官网 fetcher（``https://www.psysci.net``）。

策略：
1. 抓最新一期目录页（SSR），得到文章详情页 URL 列表
2. 对每篇详情页抓 HTML，从 ``<meta name="citation_*">`` 标签里读元数据
3. 摘要 / 作者 / 关键词通常在 meta 而非可见 DOM

风险：官网历史上有改版（2019 / 2022），probe 失败时抛
``SchemaChangedError``，调度器记 ``schema_changed`` + 保留 raw HTML 快照。
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..parsers.csl_normalizer import coerce_authors, normalize_iso_date
from ..parsers.meta_tag_parser import extract_keywords_from_meta, parse_citation_meta
from .base import (
    FetchError,
    FetchResult,
    RawArticle,
    RateLimitedError,
    SchemaChangedError,
    SourceConfig,
    SourceFetcher,
)


_DEFAULT_BASE = "https://www.psysci.net"
_LIST_PATH = "/CN/volumn/current.shtml"
# 详情链接通常是 /CN/Y2026/V49/I3/100 这样的路径
_ARTICLE_LINK_RE = re.compile(
    r"""href=["'](/CN/(?:Y\d{4}|abstract)/[^"']+?)["']""",
    re.IGNORECASE,
)


class PsyScienceOfficialFetcher(SourceFetcher):
    """心理科学官网（华东师大）SSR + meta 标签解析。"""

    def __init__(
        self,
        config: SourceConfig,
        *,
        requests_module: Any = None,
        sleep_fn: Any = None,
    ) -> None:
        super().__init__(config)
        self._requests = requests_module
        self._sleep = sleep_fn or time.sleep
        self.base_url = (config.base_url or _DEFAULT_BASE).rstrip("/")

    def _get_requests(self):
        if self._requests is not None:
            return self._requests
        try:
            import requests  # type: ignore
        except ImportError as exc:
            raise FetchError("requests 库未安装") from exc
        return requests

    # ------------------------------------------------------------------ #

    def fetch_since(
        self,
        since_date: Optional[str] = None,
        *,
        limit: int = 20,
    ) -> FetchResult:
        list_url = f"{self.base_url}{_LIST_PATH}"
        rq = self._get_requests()

        # 1. 拉目录页
        try:
            resp = rq.get(
                list_url,
                headers={"User-Agent": self.config.user_agent},
                timeout=30,
            )
        except Exception as exc:
            raise FetchError(f"目录页请求失败：{exc}") from exc

        self._raise_for_rate_limit(resp)
        status = getattr(resp, "status_code", 0)
        if status != 200:
            raise FetchError(f"目录页返回 {status}")

        list_html = getattr(resp, "text", "") or ""
        if not list_html:
            raise SchemaChangedError("目录页 HTML 为空")

        article_paths = _extract_article_links(list_html)
        if not article_paths:
            raise SchemaChangedError("目录页未匹配到任何文章链接（schema 可能变更）")

        # 限制 + 去重
        seen = set()
        unique_paths: List[str] = []
        for p in article_paths:
            if p in seen:
                continue
            seen.add(p)
            unique_paths.append(p)
            if len(unique_paths) >= limit:
                break

        # 2. 对每篇抓详情页
        articles: List[RawArticle] = []
        raw_records: List[Dict[str, Any]] = []
        consecutive_fails = 0
        parse_attempts = 0     # 详情页拿到 HTML 的次数
        parse_successes = 0    # _parse_detail 返回非 None 的次数（含被 since 过滤前）

        for path in unique_paths:
            url = f"{self.base_url}{path}" if path.startswith("/") else path
            try:
                detail_resp = rq.get(
                    url,
                    headers={"User-Agent": self.config.user_agent},
                    timeout=30,
                )
            except Exception:
                consecutive_fails += 1
                if consecutive_fails >= 3:
                    raise FetchError("连续 3 篇详情请求失败")
                self._sleep(self.config.rate_limit_seconds)
                continue

            self._raise_for_rate_limit(detail_resp)
            if getattr(detail_resp, "status_code", 0) != 200:
                consecutive_fails += 1
                if consecutive_fails >= 3:
                    raise SchemaChangedError("连续 3 篇详情返回非 200")
                self._sleep(self.config.rate_limit_seconds)
                continue

            html_text = getattr(detail_resp, "text", "") or ""
            consecutive_fails = 0  # reset on HTTP success

            # 解析阶段拆两步：(1) 结构能否解析 (2) since_date 是否要丢
            parse_attempts += 1
            ra, parsable = self._parse_detail_with_flag(html_text, url=url, since_date=since_date)
            if parsable:
                parse_successes += 1
            if ra:
                articles.append(ra)
                raw_records.append({
                    "fetched_at": _utc_now(),
                    "source_id": self.source_id,
                    "url": url,
                    "html_hash": hashlib.sha256(html_text.encode("utf-8")).hexdigest(),
                    "meta": parse_citation_meta(html_text),
                })
            self._sleep(self.config.rate_limit_seconds)

        # 抓到 HTML 但 0 篇能结构性解析 → schema 可能改了
        if parse_attempts > 0 and parse_successes == 0:
            raise SchemaChangedError(
                f"目录页有 {len(unique_paths)} 个链接，{parse_attempts} 篇拿到 HTML 但 0 篇能解析"
            )

        return FetchResult(
            source_id=self.source_id,
            articles=articles,
            raw_records=raw_records,
            probe_signature=self.health_signature(),
            notes=f"links={len(unique_paths)} parsed={len(articles)}",
        )

    # ------------------------------------------------------------------ #

    def _parse_detail_with_flag(
        self,
        html_text: str,
        *,
        url: str,
        since_date: Optional[str],
    ) -> Tuple[Optional[RawArticle], bool]:
        """返回 (article, parsable)。

        - parsable=False: meta 缺失或 title 抽不到 → 结构性失败（schema 嫌疑）
        - parsable=True, article=None: 结构能解析，但 since_date 过滤掉
        - parsable=True, article=RawArticle: 正常拿到
        """
        meta = parse_citation_meta(html_text)
        if not meta:
            return None, False

        title = _first(meta.get("citation_title")) or _first(meta.get("dc.title"))
        if not title:
            return None, False

        # 作者：citation_author 可能多次出现
        author_list = meta.get("citation_author") or meta.get("citation_authors") or meta.get("dc.creator") or []
        if len(author_list) == 1 and ("," in author_list[0] or ";" in author_list[0]):
            authors = coerce_authors(author_list[0])
        else:
            authors = coerce_authors(author_list)

        abstract = _first(meta.get("citation_abstract")) or _first(meta.get("dc.description"))
        doi = _first(meta.get("citation_doi")) or _first(meta.get("dc.identifier"))
        publisher = _first(meta.get("citation_publisher")) or _first(meta.get("dc.publisher"))
        container = _first(meta.get("citation_journal_title")) or self.config.journal_name

        date_str = (
            _first(meta.get("citation_publication_date"))
            or _first(meta.get("citation_online_date"))
            or _first(meta.get("dc.date"))
        )
        issued_date = normalize_iso_date(date_str)

        if since_date and issued_date and issued_date < since_date:
            return None, True  # 结构 OK，只是被时间过滤

        keywords = extract_keywords_from_meta(meta)

        raw_hash = hashlib.sha256(html_text.encode("utf-8")).hexdigest()

        article = RawArticle(
            title=title,
            source_id=self.source_id,
            provenance="official_site",
            authors=authors,
            abstract=abstract or None,
            issued_date=issued_date,
            doi=doi,
            container_title=container,
            publisher=publisher,
            keywords=keywords,
            metadata_status="complete" if abstract else "partial",
            raw_payload={"meta": meta},
            raw_hash=raw_hash,
            source_url=url,
        )
        return article, True

    # ------------------------------------------------------------------ #

    def _raise_for_rate_limit(self, resp: Any) -> None:
        status = getattr(resp, "status_code", 0)
        if status in (429, 503):
            retry_after = 60
            try:
                retry_after = int(getattr(resp, "headers", {}).get("Retry-After", "60"))
            except (TypeError, ValueError):
                pass
            raise RateLimitedError(f"官网限流 ({status})", retry_after=retry_after)


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _extract_article_links(html_text: str) -> List[str]:
    return [m.group(1) for m in _ARTICLE_LINK_RE.finditer(html_text or "")]


def _first(values: Optional[List[str]]) -> Optional[str]:
    if not values:
        return None
    for v in values:
        if v:
            return v.strip()
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
