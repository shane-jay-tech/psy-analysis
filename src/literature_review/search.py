"""文献搜索：调 literature_crawler.search_all 聚合 Crossref + Semantic Scholar，
按相关性 / 年份 / 期刊类型筛选去重。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .models import LiteratureItem


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _char_bigrams(text: str) -> set:
    if not text:
        return set()
    text = text.lower()
    return {text[i:i+2] for i in range(max(0, len(text) - 1))}


def _bigram_overlap_ratio(query: str, target: str) -> float:
    """目标文本被查询覆盖的比例（max-coverage，0-1）。"""
    a = _char_bigrams(query)
    b = _char_bigrams(target)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return max(inter / len(a), inter / len(b))


def _normalize_doi(doi: str) -> str:
    if not doi:
        return ""
    return doi.strip().lower().rstrip("/").replace("https://doi.org/", "").replace("http://doi.org/", "")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def search_literature(
    research_q: str,
    candidate_vars: Optional[Dict[str, Any]] = None,
    *,
    max_results: int = 20,
    year_from: Optional[int] = None,
    exclude_non_journal: bool = True,
    include_chinese: bool = True,
    crawler_search_all: Optional[Callable] = None,
    chinese_search_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """根据漏斗产出的 research_q + candidate_vars 搜索文献（v3.5 含中文）。

    Args:
        research_q: 研究问题文本
        candidate_vars: 候选变量
        max_results: 单源最大返回数
        year_from: 起始年份；None 默认为 (今年 - 10)
        exclude_non_journal: True 时过滤非期刊文献
        include_chinese: v3.5 是否同时搜中文文献库
        crawler_search_all: 注入英文搜索（测试用）
        chinese_search_fn: 注入中文搜索（测试用）

    Returns:
        {
            "items": List[LiteratureItem]（合并去重，按 relevance 排序）,
            "method": "online" | "online_with_chinese" | "offline",
            "sources": ["crossref", "semantic_scholar", "chinese"],
            "raw_count": int,
            "deduped_count": int,
        }
    """
    if crawler_search_all is None:
        from src.paper_writer.literature_crawler import search_all
        crawler_search_all = search_all

    if year_from is None:
        year_from = datetime.now().year - 10

    query = _build_search_query(research_q, candidate_vars)
    if not query.strip():
        return {"items": [], "method": "offline", "sources": [], "raw_count": 0, "deduped_count": 0}

    items: List[LiteratureItem] = []
    sources: List[str] = []

    # 英文路径
    try:
        crawled_en = crawler_search_all(query, max_results=max_results, year_from=year_from)
        if crawled_en:
            items.extend(LiteratureItem.from_crawled(c) for c in crawled_en)
            sources.append("crossref+s2")
    except Exception:
        pass

    # v3.5 中文路径
    if include_chinese:
        if chinese_search_fn is None:
            try:
                from src.paper_writer.literature_crawler import search_chinese_literature
                chinese_search_fn = search_chinese_literature
            except Exception:
                chinese_search_fn = None
        if chinese_search_fn is not None:
            try:
                cn_result = chinese_search_fn(query, max_results=max(10, max_results // 2),
                                                year_from=year_from)
                cn_refs = getattr(cn_result, "references", None) or []
                if cn_refs:
                    items.extend(LiteratureItem.from_crawled(c) for c in cn_refs)
                    sources.append("chinese")
            except Exception:
                pass

    raw_count = len(items)

    if not items:
        return {"items": [], "method": "offline", "sources": [], "raw_count": 0, "deduped_count": 0}

    # 年份过滤
    items = [it for it in items if it.year >= year_from or it.year == 0]

    # 非期刊过滤
    if exclude_non_journal:
        items = _filter_non_journal(items)

    # 去重
    items = deduplicate_by_doi(items)

    # 相关性排序
    items = rank_by_relevance(items, research_q, candidate_vars)

    items = items[:max_results]

    method = "online_with_chinese" if "chinese" in sources else (
        "online" if sources else "offline"
    )

    return {
        "items": items,
        "method": method,
        "sources": sources,
        "raw_count": raw_count,
        "deduped_count": len(items),
    }


def _build_search_query(research_q: str, candidate_vars: Optional[Dict[str, Any]]) -> str:
    """合并 research_q + candidate_vars 生成搜索关键词。"""
    parts: List[str] = []
    if research_q and research_q.strip():
        parts.append(research_q.strip())
    if isinstance(candidate_vars, dict):
        for key in ("dependent_vars", "independent_vars"):
            for v in candidate_vars.get(key) or []:
                if v and isinstance(v, str):
                    parts.append(v.strip())
    return " ".join(parts)


def _filter_non_journal(items: List[LiteratureItem]) -> List[LiteratureItem]:
    """启发式：journal 字段空或含「Conference / Proceedings / Thesis / Dissertation」→ 排除。"""
    out: List[LiteratureItem] = []
    blacklist = ["conference", "proceedings", "thesis", "dissertation", "preprint"]
    for it in items:
        j = (it.journal or "").lower()
        if not j:
            # journal 为空但有 doi 通常仍是期刊，保留
            if it.doi:
                out.append(it)
            continue
        if any(kw in j for kw in blacklist):
            continue
        out.append(it)
    return out


def deduplicate_by_doi(items: List[LiteratureItem]) -> List[LiteratureItem]:
    """按 DOI 去重；DOI 缺失时按 (title.lower(), year) 去重。"""
    seen_doi: set = set()
    seen_title: set = set()
    out: List[LiteratureItem] = []
    for it in items:
        norm_doi = _normalize_doi(it.doi)
        if norm_doi:
            if norm_doi in seen_doi:
                continue
            seen_doi.add(norm_doi)
            out.append(it)
        else:
            tkey = (it.title.strip().lower(), it.year)
            if tkey in seen_title or not it.title:
                continue
            seen_title.add(tkey)
            out.append(it)
    return out


def rank_by_relevance(
    items: List[LiteratureItem],
    research_q: str,
    candidate_vars: Optional[Dict[str, Any]] = None,
) -> List[LiteratureItem]:
    """按 (题目+摘要 与 research_q+vars 的 bigram 覆盖率) 排序，写入 relevance_score。"""
    query = _build_search_query(research_q, candidate_vars)
    if not query:
        return items
    for it in items:
        target = (it.title or "") + " " + (it.abstract or "")
        score = _bigram_overlap_ratio(query, target)
        # 引用数加权（避免冷门高相关被排到前面）
        cite_bonus = min(0.1, it.citation_count / 1000.0)
        it.relevance_score = round(min(1.0, score + cite_bonus), 4)
    return sorted(items, key=lambda x: -x.relevance_score)


def rescore_existing_items(
    items_dict: List[Dict[str, Any]],
    research_q: str,
    candidate_vars: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """v3.5 跨 phase 修订后重新打分（保留所有元数据，只更新 relevance_score）。"""
    if not items_dict:
        return []
    # 转 LiteratureItem，重排，再转回 dict
    items_obj = [LiteratureItem.from_dict(d) for d in items_dict]
    items_obj = rank_by_relevance(items_obj, research_q, candidate_vars)
    return [it.to_dict() for it in items_obj]


# ---------------------------------------------------------------------------
# 摘要数据（用于 UI 展示搜索结果元数据）
# ---------------------------------------------------------------------------

def search_summary(
    items_before_dedup: List[LiteratureItem],
    items_after: List[LiteratureItem],
    query: str,
) -> Dict[str, Any]:
    return {
        "query": query,
        "raw_count": len(items_before_dedup),
        "deduped_count": len(items_after),
        "dropped": len(items_before_dedup) - len(items_after),
    }
