"""手动补录 fetcher：管理世界 + 兜底。

输入：DOI / URL / 引用文本（用户从 CNKI / 期刊官网粘贴）
输出：尽力解析的 ``RawArticle``（缺字段进 ``needs_review``）

不主动发网络请求。Crossref DOI 查询也只在用户显式调用 ``resolve_via_crossref``
时进行（避免在批量审核界面意外触发请求）。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..parsers.csl_normalizer import (
    coerce_authors,
    crossref_to_raw,
    normalize_iso_date,
)
from .base import FetchResult, RawArticle, SourceConfig, SourceFetcher


_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_YEAR_RE = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")
_URL_RE = re.compile(r"https?://[\w\-./?=&%#:+]+", re.IGNORECASE)


def detect_input_type(text: str) -> str:
    """从粘贴内容里判断 input_type：``doi`` / ``url`` / ``citation_text``。"""
    s = (text or "").strip()
    if not s:
        return "citation_text"
    if _DOI_RE.search(s) and len(s) <= 200 and "\n" not in s:
        return "doi"
    if _URL_RE.match(s) and "\n" not in s:
        return "url"
    return "citation_text"


def parse_citation_text(text: str, *, source_id: str) -> Optional[RawArticle]:
    """从一段中文/英文引用文本里尽力抽题目/作者/年份/期刊。

    用法举例：
        "张三, 李四. (2026). 变革型领导对工作绩效的影响. 管理世界, 42(3), 100-120."
    """
    s = (text or "").strip()
    if not s:
        return None

    # DOI
    doi_match = _DOI_RE.search(s)
    doi = doi_match.group(0) if doi_match else None

    # URL
    url_match = _URL_RE.search(s)
    url = url_match.group(0) if url_match else None

    # 年份
    year_match = _YEAR_RE.search(s)
    year = int(year_match.group(0)) if year_match else None

    # 标题：APA 风格里 (年份). 标题. 期刊...
    # 用 (年份). XXX. 锚定标题
    title: Optional[str] = None
    if year:
        m = re.search(r"\(\s*\d{4}[a-z]?\s*\)\s*\.?\s*(.+?)(?:\.|\?|\!)\s*", s)
        if m:
            title = m.group(1).strip()
    if not title:
        # 退而求其次：第一句句号前的部分
        first_sentence = re.split(r"[。.]", s, maxsplit=1)[0].strip()
        if first_sentence and len(first_sentence) > 5:
            title = first_sentence

    if not title:
        return None

    # 作者：在 (年份). 之前的 token
    authors: List[Dict[str, str]] = []
    if year:
        before = s.split(f"({year}", 1)[0]
        before = before.replace(f"{year}", "").strip().rstrip(",.，。")
        if before:
            authors = coerce_authors(before)

    # 期刊：标题之后到下一个句号
    container: Optional[str] = None
    if title:
        idx = s.find(title)
        if idx >= 0:
            tail = s[idx + len(title):].lstrip(" .。,，")
            container_match = re.match(r"([^.。,，]+)", tail)
            if container_match:
                container = container_match.group(1).strip()

    return RawArticle(
        title=title,
        source_id=source_id,
        provenance="manual",
        authors=authors,
        abstract=None,
        issued_date=f"{year:04d}-01-01" if year else None,
        doi=doi,
        container_title=container,
        keywords=[],
        metadata_status="needs_review",
        raw_payload={"raw_text": s, "url": url},
        source_url=url,
    )


class ManualIngestFetcher(SourceFetcher):
    """非自动 fetcher。不实现 ``fetch_since``（调用即抛 ``NotImplementedError``）。

    UI 调用 ``ingest_citation_text(...)`` / ``ingest_doi(...)`` / ``ingest_url(...)``
    走上层流程。
    """

    def fetch_since(self, since_date=None, *, limit: int = 20) -> FetchResult:
        # 手动补录不参与每日定时拉取
        return FetchResult(source_id=self.source_id, articles=[], raw_records=[])

    # ------------------------------------------------------------------ #
    # 入站方法（同步，UI 直接调用）
    # ------------------------------------------------------------------ #

    def ingest_citation_text(self, text: str) -> Optional[RawArticle]:
        return parse_citation_text(text, source_id=self.source_id)

    def ingest_doi(self, doi: str) -> Optional[RawArticle]:
        s = (doi or "").strip()
        if not s:
            return None
        m = _DOI_RE.search(s)
        if not m:
            return None
        return RawArticle(
            title="（待解析）",
            source_id=self.source_id,
            provenance="manual",
            doi=m.group(0),
            metadata_status="needs_review",
            raw_payload={"raw_input": s, "input_type": "doi"},
        )

    def ingest_url(self, url: str) -> Optional[RawArticle]:
        s = (url or "").strip()
        if not s or not _URL_RE.match(s):
            return None
        return RawArticle(
            title="（待解析）",
            source_id=self.source_id,
            provenance="manual",
            metadata_status="needs_review",
            source_url=s,
            raw_payload={"raw_input": s, "input_type": "url"},
        )

    def resolve_via_crossref(
        self,
        doi: str,
        *,
        requests_module: Any = None,
        timeout: int = 15,
    ) -> Optional[RawArticle]:
        """用 Crossref API 把 DOI 查成完整记录（用户显式触发，不参与定时跑）。"""
        rq = requests_module
        if rq is None:
            try:
                import requests  # type: ignore
            except ImportError:
                return None
            rq = requests
        s = (doi or "").strip()
        m = _DOI_RE.search(s)
        if not m:
            return None
        url = f"https://api.crossref.org/works/{m.group(0)}?mailto={self.config.contact_email}"
        try:
            resp = rq.get(url, headers={"User-Agent": self.config.user_agent}, timeout=timeout)
        except Exception:
            return None
        if getattr(resp, "status_code", 0) != 200:
            return None
        try:
            data = resp.json()
        except (ValueError, TypeError):
            return None
        message = (data or {}).get("message")
        if not message:
            return None
        ra = crossref_to_raw(message, source_id=self.source_id)
        if ra:
            ra.provenance = "manual"
            ra.metadata_status = "complete" if ra.abstract else "partial"
        return ra
