"""学术 meta 标签解析（``citation_*`` Highwire-Press / Dublin Core）。

心理科学官网详情页用 ``<meta name="citation_abstract">`` 等标签提供
摘要、作者、关键词，正文 DOM 反而经常空。这里只信 meta 标签。
"""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List


_META_TAG_RE = re.compile(
    r"""<meta\s+[^>]*?name=["']([^"']+)["'][^>]*?content=["']([^"']*)["']""",
    re.IGNORECASE | re.DOTALL,
)
_META_TAG_REVERSED_RE = re.compile(
    r"""<meta\s+[^>]*?content=["']([^"']*)["'][^>]*?name=["']([^"']+)["']""",
    re.IGNORECASE | re.DOTALL,
)


_KEYS_OF_INTEREST = {
    "citation_title",
    "citation_author",
    "citation_authors",
    "citation_abstract",
    "citation_doi",
    "citation_journal_title",
    "citation_publisher",
    "citation_publication_date",
    "citation_online_date",
    "citation_keywords",
    "citation_keyword",
    "citation_issue",
    "citation_volume",
    "dc.title",
    "dc.creator",
    "dc.description",
    "dc.identifier",
    "dc.publisher",
    "dc.date",
    "dc.subject",
}


def parse_citation_meta(html_text: str) -> Dict[str, List[str]]:
    """从 HTML 中抽 meta 标签 → ``{name_lower: [content, ...]}``。"""
    if not html_text:
        return {}
    out: Dict[str, List[str]] = {}
    for match in _META_TAG_RE.finditer(html_text):
        name = match.group(1).strip().lower()
        content = html.unescape(match.group(2)).strip()
        if name in _KEYS_OF_INTEREST and content:
            out.setdefault(name, []).append(content)
    for match in _META_TAG_REVERSED_RE.finditer(html_text):
        name = match.group(2).strip().lower()
        content = html.unescape(match.group(1)).strip()
        if name in _KEYS_OF_INTEREST and content:
            existing = out.setdefault(name, [])
            if content not in existing:
                existing.append(content)
    return out


def extract_keywords_from_meta(meta: Dict[str, List[str]]) -> List[str]:
    """合并 ``citation_keywords`` / ``dc.subject``，按 ``;`` ``,`` 切。"""
    raw_blocks: List[str] = []
    for key in ("citation_keywords", "citation_keyword", "dc.subject"):
        for chunk in meta.get(key, []):
            raw_blocks.append(chunk)
    out: List[str] = []
    seen = set()
    for chunk in raw_blocks:
        for kw in re.split(r"[;；、,，]", chunk):
            kw = kw.strip()
            if kw and kw not in seen:
                seen.add(kw)
                out.append(kw)
    return out
