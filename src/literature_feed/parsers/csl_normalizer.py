"""把异构源（Crossref / 官网 / 手动）归一化成统一的 ``RawArticle``。

内部以 CSL-JSON 兼容字段为 canonical 表达：
- title / author (数组) / abstract / issued (date-parts) / DOI /
  container-title / publisher / keyword
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from ..fetchers.base import RawArticle


# ---------------------------------------------------------------------------
# 日期归一化：Crossref date-parts / ISO 字符串 / 中文日期
# ---------------------------------------------------------------------------

_ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")
_YEAR_MONTH_RE = re.compile(r"^(\d{4})-(\d{1,2})$")
_YEAR_RE = re.compile(r"^(\d{4})$")
_CN_DATE_RE = re.compile(r"^(\d{4})年(\d{1,2})月(?:(\d{1,2})日)?")


def normalize_iso_date(value: Any) -> Optional[str]:
    """把各种日期表达统一成 ``YYYY-MM-DD``（缺省日补 01，缺月补 01）。"""
    if value is None:
        return None

    # Crossref 的 date-parts: {"date-parts": [[2026, 5, 1]]}
    if isinstance(value, dict) and "date-parts" in value:
        parts = value.get("date-parts") or [[]]
        if parts and parts[0]:
            arr = parts[0]
            year = int(arr[0]) if len(arr) >= 1 else None
            month = int(arr[1]) if len(arr) >= 2 else 1
            day = int(arr[2]) if len(arr) >= 3 else 1
            if year:
                try:
                    return date(year, max(1, month), max(1, day)).isoformat()
                except ValueError:
                    return f"{year:04d}-{max(1,month):02d}-01"
        return None

    if isinstance(value, (int, float)):
        try:
            return date(int(value), 1, 1).isoformat()
        except ValueError:
            return None

    if isinstance(value, (list, tuple)):
        return normalize_iso_date({"date-parts": [list(value)]})

    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    m = _ISO_DATE_RE.match(s)
    if m:
        y, mo, d = (int(g) for g in m.groups())
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return f"{y:04d}-{mo:02d}-01"

    m = _YEAR_MONTH_RE.match(s)
    if m:
        y, mo = (int(g) for g in m.groups())
        return f"{y:04d}-{mo:02d}-01"

    m = _YEAR_RE.match(s)
    if m:
        return f"{int(m.group(1)):04d}-01-01"

    m = _CN_DATE_RE.match(s)
    if m:
        y = int(m.group(1))
        mo = int(m.group(2))
        d = int(m.group(3)) if m.group(3) else 1
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return f"{y:04d}-{mo:02d}-01"

    return None


# ---------------------------------------------------------------------------
# 作者归一化：Crossref author array / 中文姓名串
# ---------------------------------------------------------------------------

def coerce_authors(value: Any) -> List[Dict[str, str]]:
    """把作者表达统一成 ``[{family, given}, ...]``。"""
    if not value:
        return []

    if isinstance(value, list):
        out: List[Dict[str, str]] = []
        for item in value:
            if isinstance(item, dict):
                family = (item.get("family") or item.get("last") or "").strip()
                given = (item.get("given") or item.get("first") or "").strip()
                if not family and not given and item.get("name"):
                    name = str(item["name"]).strip()
                    family, given = _split_name(name)
                if family or given:
                    out.append({"family": family, "given": given})
            elif isinstance(item, str):
                family, given = _split_name(item)
                if family or given:
                    out.append({"family": family, "given": given})
        return out

    if isinstance(value, str):
        # 用常见分隔符切：; / 、 / , / 空格（中文常用）
        parts = re.split(r"[;；、,，]", value)
        out = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            family, given = _split_name(part)
            if family or given:
                out.append({"family": family, "given": given})
        return out

    return []


def _split_name(name: str) -> tuple:
    """把单个姓名切成 (family, given)。中文：姓在前；英文：以空格切，最后一段为 family。"""
    name = unicodedata.normalize("NFKC", name).strip()
    if not name:
        return "", ""
    if " " in name and re.search(r"[A-Za-z]", name):
        parts = name.split()
        return parts[-1], " ".join(parts[:-1])
    # 中文姓名：默认 1-2 字姓
    if re.match(r"^[一-鿿]+$", name):
        if len(name) <= 1:
            return name, ""
        # 复姓简化处理：常见复姓
        compound_surnames = {"欧阳", "司马", "诸葛", "上官", "夏侯", "东方", "皇甫", "尉迟", "公孙"}
        if len(name) >= 3 and name[:2] in compound_surnames:
            return name[:2], name[2:]
        return name[:1], name[1:]
    return name, ""


# ---------------------------------------------------------------------------
# IO/HR/OB 词表命中
# ---------------------------------------------------------------------------

def extract_iohr_hits(
    text_blobs: Sequence[str],
    weights_dict: Dict[str, Sequence[str]],
) -> List[str]:
    """在文本里命中 IO/HR/OB 词表中的任何同义词，返回命中的词条名（去重保序）。

    Args:
        text_blobs: 待匹配文本（标题/摘要/关键词均可）
        weights_dict: {词条名: [同义词...]}，词条名也算同义词

    Returns:
        命中的词条名列表
    """
    if not text_blobs or not weights_dict:
        return []
    # 把文本拼一起做单趟扫描
    blob = " ".join(t for t in text_blobs if t).lower()
    if not blob:
        return []
    hits: List[str] = []
    seen: Set[str] = set()
    for canonical, synonyms in weights_dict.items():
        all_syn = [canonical] + list(synonyms or [])
        for syn in all_syn:
            if not syn:
                continue
            if syn.lower() in blob:
                if canonical not in seen:
                    hits.append(canonical)
                    seen.add(canonical)
                break
    return hits


# ---------------------------------------------------------------------------
# Crossref → RawArticle
# ---------------------------------------------------------------------------

def crossref_to_raw(
    item: Dict[str, Any],
    *,
    source_id: str,
    keep_jats: bool = False,
) -> Optional[RawArticle]:
    """单条 Crossref ``item`` 转 ``RawArticle``。无标题或结构异常返回 None。"""
    if not isinstance(item, dict):
        return None

    title_arr = item.get("title") or []
    title = ""
    if isinstance(title_arr, list) and title_arr:
        title = str(title_arr[0]).strip()
    elif isinstance(title_arr, str):
        title = title_arr.strip()

    if not title:
        return None

    # 摘要可能带 JATS 标签 <jats:p>
    abstract = item.get("abstract")
    if isinstance(abstract, str) and not keep_jats:
        abstract = re.sub(r"<[^>]+>", " ", abstract)
        abstract = re.sub(r"\s+", " ", abstract).strip()

    # 日期：优先 issued，其次 published-print / published-online
    issued = (
        item.get("issued")
        or item.get("published-print")
        or item.get("published-online")
        or item.get("created")
    )
    issued_date = normalize_iso_date(issued)

    container = item.get("container-title")
    if isinstance(container, list) and container:
        container = container[0]
    elif not isinstance(container, str):
        container = None

    keywords = item.get("subject") or item.get("keyword") or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in re.split(r"[;；、,，]", keywords) if k.strip()]
    elif isinstance(keywords, list):
        keywords = [str(k).strip() for k in keywords if k]
    else:
        keywords = []

    raw_hash = hashlib.sha256(
        json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return RawArticle(
        title=title,
        source_id=source_id,
        provenance="crossref",
        authors=coerce_authors(item.get("author")),
        abstract=abstract or None,
        issued_date=issued_date,
        doi=item.get("DOI"),
        container_title=container,
        publisher=item.get("publisher"),
        keywords=keywords,
        metadata_status="complete" if abstract else "partial",
        raw_payload=item,
        raw_hash=raw_hash,
        source_url=item.get("URL") or item.get("resource", {}).get("primary", {}).get("URL"),
    )
