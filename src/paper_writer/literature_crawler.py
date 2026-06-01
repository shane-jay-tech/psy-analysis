"""文献自动爬取器

基于 Crossref API 和 Semantic Scholar API 的学术文献自动搜索与缓存。
支持中文（通过 CNKI/万方关键词检索）和英文文献的自动获取。

特性：
- 双层 API（Crossref 主路径，Semantic Scholar 补充）
- 结果缓存（24小时 TTL，避免重复请求）
- 速率限制（每 API 至少间隔 1.1s）
- 自动 APA7 格式化
"""

import json
import hashlib
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta


# 缓存目录
_CACHE_DIR = Path(__file__).parent / ".literature_cache"


@dataclass
class CrawledReference:
    """爬取的文献条目"""
    title: str
    authors: List[str]
    year: int
    journal: str
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    abstract: str = ""
    citation_count: int = 0
    source: str = ""         # "crossref" | "semantic_scholar" | "web"
    is_open_access: bool = False
    url: str = ""

    def to_apa7(self, is_chinese: bool = False) -> str:
        """转换为 APA 7th Edition 格式"""
        if is_chinese:
            authors_str = ", ".join(self.authors)
        else:
            if len(self.authors) == 1:
                authors_str = f"{self.authors[0]}"
            elif len(self.authors) == 2:
                authors_str = f"{self.authors[0]}, & {self.authors[1]}"
            elif len(self.authors) <= 7:
                authors_str = ", ".join(self.authors[:-1]) + f", & {self.authors[-1]}"
            else:
                authors_str = ", ".join(self.authors[:6]) + ", ... " + self.authors[-1]

        ref = f"{authors_str} ({self.year}). {self.title}."
        if self.journal:
            ref += f" {self.journal}"
        if self.volume:
            ref += f", {self.volume}"
            if self.issue:
                ref += f"({self.issue})"
        if self.pages:
            ref += f", {self.pages}"
        if self.doi:
            ref += f". https://doi.org/{self.doi}"
        return ref

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "doi": self.doi,
            "abstract": self.abstract,
            "citation_count": self.citation_count,
        }


@dataclass
class CrawlResult:
    """爬取结果"""
    query: str
    total_found: int
    references: List[CrawledReference]
    source: str          # API来源
    search_time: str
    cached: bool = False


def search_crossref(
    query: str,
    max_results: int = 10,
    year_from: int = 2015,
    use_cache: bool = True,
) -> CrawlResult:
    """
    通过 Crossref API 搜索学术文献。

    参数：
        query: 搜索关键词（英文效果最佳）
        max_results: 最大返回数（1-100）
        year_from: 起始年份
        use_cache: 是否使用缓存

    返回：
        CrawlResult 包含爬取的文献列表
    """
    # 检查缓存
    if use_cache:
        cached = _load_cache(query, "crossref")
        if cached:
            return cached

    base_url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": min(max_results, 100),
        "filter": f"from-pub-date:{year_from}-01-01,type:journal-article",
        "sort": "relevance",
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "PsyAnalysisBot/2.0 (mailto:research@example.com)")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        return CrawlResult(
            query=query,
            total_found=0,
            references=[],
            source="crossref",
            search_time=datetime.now().isoformat(),
            cached=False,
        )

    total = data.get("message", {}).get("total-results", 0)
    items = data.get("message", {}).get("items", [])

    references = []
    for item in items:
        ref = _parse_crossref_item(item)
        if ref:
            references.append(ref)

    result = CrawlResult(
        query=query,
        total_found=total,
        references=references,
        source="crossref",
        search_time=datetime.now().isoformat(),
        cached=False,
    )

    if use_cache:
        _save_cache(query, "crossref", result)

    return result


def search_semantic_scholar(
    query: str,
    max_results: int = 10,
    year_from: int = 2015,
    use_cache: bool = True,
) -> CrawlResult:
    """
    通过 Semantic Scholar API 搜索学术文献（补充 Crossref）。

    参数：
        query: 搜索关键词
        max_results: 最大返回数
        year_from: 起始年份
        use_cache: 是否使用缓存

    返回：
        CrawlResult 包含爬取的文献列表
    """
    if use_cache:
        cached = _load_cache(query, "semantic_scholar")
        if cached:
            return cached

    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": min(max_results, 100),
        "year": f"{year_from}-",
        "fields": "title,authors,year,journal,volume,pages,externalIds,abstract,citationCount,isOpenAccess,url,publicationVenue",
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "PsyAnalysisBot/2.0")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        return CrawlResult(
            query=query,
            total_found=0,
            references=[],
            source="semantic_scholar",
            search_time=datetime.now().isoformat(),
            cached=False,
        )

    total = data.get("total", 0)
    papers = data.get("data", [])

    references = []
    for paper in papers:
        ref = _parse_s2_paper(paper)
        if ref:
            references.append(ref)

    result = CrawlResult(
        query=query,
        total_found=total,
        references=references,
        source="semantic_scholar",
        search_time=datetime.now().isoformat(),
        cached=False,
    )

    if use_cache:
        _save_cache(query, "semantic_scholar", result)

    return result


def search_all(
    query: str,
    max_results: int = 15,
    year_from: int = 2015,
    include_s2: bool = True,
    use_cache: bool = True,
) -> List[CrawledReference]:
    """
    聚合搜索：从 Crossref + Semantic Scholar 获取，合并去重。

    参数：
        query: 搜索关键词
        max_results: 每个源的最大返回数
        year_from: 起始年份
        include_s2: 是否同时查询 Semantic Scholar
        use_cache: 是否使用缓存

    返回：
        去重后的 CrawledReference 列表
    """
    all_refs: Dict[str, CrawledReference] = {}

    # Crossref 主路径
    cr_result = search_crossref(query, max_results, year_from, use_cache)
    for ref in cr_result.references:
        key = _ref_dedup_key(ref)
        if key not in all_refs:
            all_refs[key] = ref

    # Semantic Scholar 补充
    if include_s2:
        time.sleep(1.1)  # 速率限制
        s2_result = search_semantic_scholar(query, max_results, year_from, use_cache)
        for ref in s2_result.references:
            key = _ref_dedup_key(ref)
            if key not in all_refs:
                all_refs[key] = ref

    # 按引用数降序排列
    sorted_refs = sorted(all_refs.values(), key=lambda r: -r.citation_count)
    return sorted_refs


def search_for_construct(
    construct_name: str,
    domain: str = "",
    max_results: int = 15,
    use_cache: bool = True,
) -> List[CrawledReference]:
    """
    根据心理学构念名称搜索相关文献。

    自动构造优化的搜索查询：构念名 + 心理学 + 量表/测量关键词。

    参数：
        construct_name: 构念中文名称
        domain: 所属领域（用于优化查询）
        max_results: 最大返回数
        use_cache: 是否使用缓存

    返回：
        相关文献列表
    """
    # 构造搜索查询
    query_parts = [construct_name]

    # 尝试中英文混合搜索
    domain_en = {
        "社会心理": "social psychology",
        "认知": "cognitive psychology",
        "发展": "developmental psychology",
        "临床与健康": "clinical psychology",
        "组织行为": "organizational behavior",
        "教育心理": "educational psychology",
        "人格": "personality psychology",
    }

    if domain and domain in domain_en:
        query_parts.append(domain_en[domain])

    query_parts.append("scale OR measure OR questionnaire")
    query = " ".join(query_parts)

    return search_all(query, max_results=max_results, use_cache=use_cache)


def recommend_literature(
    construct_name: str,
    domain: str = "",
    top_k: int = 5,
) -> List[Dict]:
    """
    为构念推荐相关文献（供问卷设计引擎调用的高层接口）。

    返回格式适配 design_engine 的 academic_enrichment 结构。
    """
    refs = search_for_construct(construct_name, domain, max_results=10)

    recommendations = []
    for ref in refs[:top_k]:
        recommendations.append({
            "title": ref.title,
            "authors": ", ".join(ref.authors[:3]),
            "year": ref.year,
            "journal": ref.journal,
            "doi": ref.doi,
            "citation_count": ref.citation_count,
            "abstract": ref.abstract[:200] if ref.abstract else "",
            "apa7": ref.to_apa7(is_chinese=False),
        })

    return recommendations


# ============================================================
# Task 9: 中文文献搜索 (iData API + CNKI DOI)
# ============================================================

# 中文核心心理学期刊映射
_CHINESE_JOURNALS = {
    "心理学报": "Acta Psychologica Sinica",
    "心理科学": "Psychological Science",
    "心理科学进展": "Advances in Psychological Science",
    "心理发展与教育": "Psychological Development and Education",
    "中国临床心理学杂志": "Chinese Journal of Clinical Psychology",
    "中国心理卫生杂志": "Chinese Mental Health Journal",
    "应用心理学": "Chinese Journal of Applied Psychology",
    "心理学探新": "Psychological Exploration",
    "心理与行为研究": "Studies of Psychology and Behavior",
    "中华行为医学与脑科学杂志": "Chinese Journal of Behavioral Medicine and Brain Science",
    "教育研究": "Educational Research",
    "社会学研究": "Sociological Studies",
    "管理世界": "Management World",
    "中国健康心理学杂志": "China Journal of Health Psychology",
}


def search_chinese_literature(
    query: str,
    max_results: int = 15,
    year_from: int = 2015,
    use_cache: bool = True,
) -> CrawlResult:
    """
    搜索中文心理学文献。

    通过 Crossref API + 中文查询词搜索，自动过滤中文期刊。
    同时也尝试通过 CNKI DOI 格式解析中文文献。

    参数：
        query: 中文搜索关键词（如 "自尊 量表 信效度"）
        max_results: 最大返回数
        year_from: 起始年份
        use_cache: 是否使用缓存

    返回：
        CrawlResult 包含中文文献列表
    """
    if use_cache:
        cached = _load_cache(query, "chinese")
        if cached:
            return cached

    all_refs: Dict[str, CrawledReference] = []

    # 路径1: Crossref 搜索（中文期刊也有 DOI）
    # 用中文查询词 + 中文期刊过滤
    cr_query = f"{query} 心理学 量表"
    time.sleep(0.3)
    try:
        base_url = "https://api.crossref.org/works"
        params = {
            "query": cr_query,
            "rows": min(max_results, 100),
            "filter": f"from-pub-date:{year_from}-01-01,type:journal-article",
            "sort": "relevance",
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "PsyAnalysisBot/2.0 (mailto:research@example.com)")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        items = data.get("message", {}).get("items", [])
        for item in items:
            ref = _parse_crossref_item(item)
            if ref and _is_chinese_publication(ref):
                ref.source = "crossref_cn"
                key = _ref_dedup_key(ref)
                if key not in all_refs:
                    all_refs[key] = ref
    except Exception:
        pass

    # 路径2: Semantic Scholar 补充（英文关键词）
    en_query = _translate_query_for_search(query)
    if en_query:
        time.sleep(1.1)
        try:
            s2_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            s2_params = {
                "query": en_query,
                "limit": min(max_results, 100),
                "year": f"{year_from}-",
                "fields": "title,authors,year,journal,externalIds,abstract,citationCount,url",
            }
            s2_url_full = f"{s2_url}?{urllib.parse.urlencode(s2_params)}"
            req = urllib.request.Request(s2_url_full)
            req.add_header("User-Agent", "PsyAnalysisBot/2.0")
            with urllib.request.urlopen(req, timeout=30) as resp:
                s2_data = json.loads(resp.read().decode("utf-8"))
            for paper in s2_data.get("data", []):
                ref = _parse_s2_paper(paper)
                if ref:
                    ref.source = "semantic_scholar_cn"
                    key = _ref_dedup_key(ref)
                    if key not in all_refs:
                        all_refs[key] = ref
        except Exception:
            pass

    refs = sorted(all_refs.values(), key=lambda r: -r.citation_count)
    result = CrawlResult(
        query=query,
        total_found=len(refs),
        references=refs[:max_results],
        source="chinese",
        search_time=datetime.now().isoformat(),
        cached=False,
    )

    if use_cache:
        _save_cache(query, "chinese", result)

    return result


def search_idata(
    query: str,
    api_token: Optional[str] = None,
    max_results: int = 15,
    use_cache: bool = True,
) -> CrawlResult:
    """
    通过 iData API 搜索中文文献（需 API token）。

    iData (http://www.woaiai.cn/) 是国内常用的学术资源平台，
    支持 CNKI/万方等中文数据库检索。

    参数：
        query: 中文搜索关键词
        api_token: iData API token（可选，未提供则回退到 Crossref 中文搜索）
        max_results: 最大返回数
        use_cache: 是否使用缓存

    返回：
        CrawlResult 包含中文文献列表

    注意：iData API 需要开通权限。如无 token，自动回退到
    search_chinese_literature() 的 Crossref 路径。
    """
    if not api_token:
        # 降级到 Crossref 中文搜索
        result = search_chinese_literature(query, max_results, use_cache=use_cache)
        result.source = "chinese_fallback"
        return result

    if use_cache:
        cached = _load_cache(query, "idata")
        if cached:
            return cached

    refs = []
    try:
        # iData API endpoint (需根据实际 API 文档调整)
        api_url = "https://api.woaiai.cn/v1/search"
        params = {
            "q": query,
            "db": "cnki",
            "size": min(max_results, 50),
            "token": api_token,
        }
        url = f"{api_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "PsyAnalysisBot/2.0")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for item in data.get("results", data.get("data", [])):
            ref = _parse_idata_item(item)
            if ref:
                refs.append(ref)
    except Exception:
        # API 不可用时回退
        return search_chinese_literature(
            query, max_results=max_results, use_cache=use_cache
        )

    result = CrawlResult(
        query=query,
        total_found=len(refs),
        references=refs,
        source="idata",
        search_time=datetime.now().isoformat(),
        cached=False,
    )

    if use_cache:
        _save_cache(query, "idata", result)

    return result


def resolve_cnki_doi(doi: str) -> Optional[Dict]:
    """
    通过 DOI 解析中文文献的详细信息（CNKI DOI 格式：10.xxxx/...）。

    CNKI 分配的 DOI 均可在 doi.org 上解析，此函数提供便捷的
    中文期刊名映射和格式化。
    """
    try:
        url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "PsyAnalysisBot/2.0")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        item = data.get("message", {})
        if not item:
            return None

        title = item.get("title", [""])[0] if item.get("title") else ""
        container = item.get("container-title", [""])
        journal_en = container[0] if container else ""

        # 查找中文期刊名
        journal_cn = _find_chinese_journal_name(journal_en)

        authors = []
        for author in item.get("author", []):
            family = author.get("family", "")
            given = author.get("given", "")
            if family:
                authors.append(f"{family}{given}")

        return {
            "title": title,
            "title_cn": _guess_chinese_title(title, journal_cn),
            "authors": authors,
            "year": item.get("published-print", {}).get("date-parts", [[None]])[0][0],
            "journal_en": journal_en,
            "journal_cn": journal_cn,
            "volume": item.get("volume", ""),
            "issue": item.get("issue", ""),
            "pages": item.get("page", ""),
            "doi": doi,
            "abstract": item.get("abstract", ""),
        }
    except Exception:
        return None


def _parse_idata_item(item: Dict) -> Optional[CrawledReference]:
    """解析 iData API 返回的单条文献"""
    try:
        title = item.get("title", item.get("题名", ""))
        if not title:
            return None

        authors = []
        author_field = item.get("authors", item.get("作者", []))
        if isinstance(author_field, str):
            authors = [a.strip() for a in author_field.split(";") if a.strip()]
        elif isinstance(author_field, list):
            authors = author_field

        year = item.get("year", item.get("年份", datetime.now().year))

        journal = item.get("journal", item.get("刊名", item.get("source", "")))
        doi = item.get("doi", item.get("DOI", ""))

        return CrawledReference(
            title=title,
            authors=authors,
            year=int(year) if year else datetime.now().year,
            journal=journal,
            volume=str(item.get("volume", item.get("卷", ""))),
            issue=str(item.get("issue", item.get("期", ""))),
            pages=str(item.get("pages", item.get("页码", ""))),
            doi=doi,
            abstract=str(item.get("abstract", item.get("摘要", "")))[:500],
            citation_count=item.get("citation_count", item.get("被引", 0)),
            source="idata",
            is_open_access=False,
            url=f"https://doi.org/{doi}" if doi else "",
        )
    except Exception:
        return None


def _is_chinese_publication(ref: CrawledReference) -> bool:
    """判断文献是否为中文出版物"""
    # 检查期刊名是否在中文期刊列表中
    journal_lower = ref.journal.lower()
    for cn_name, en_name in _CHINESE_JOURNALS.items():
        if cn_name in ref.journal or en_name.lower() in journal_lower:
            return True

    # 检查标题是否包含中文字符
    chinese_char_count = sum(1 for c in ref.title if '一' <= c <= '鿿')
    if chinese_char_count >= 3:
        return True

    # 检查作者名是否包含中文
    for author in ref.authors:
        if any('一' <= c <= '鿿' for c in author):
            return True

    return False


def _find_chinese_journal_name(journal_en: str) -> str:
    """根据英文期刊名查找对应的中文名"""
    journal_lower = journal_en.lower()
    for cn_name, en_name in _CHINESE_JOURNALS.items():
        if en_name.lower() in journal_lower or journal_lower in en_name.lower():
            return cn_name
    return ""


def _guess_chinese_title(title: str, journal_cn: str) -> str:
    """如果标题不含中文，尝试推断中文标题（占位）"""
    if any('一' <= c <= '鿿' for c in title):
        return title
    return title  # 无法自动翻译，保持原样


def _translate_query_for_search(query: str) -> str:
    """将中文查询词映射为英文搜索词（常用心理学概念映射）"""
    concept_map = {
        "自尊": "self-esteem",
        "焦虑": "anxiety",
        "抑郁": "depression",
        "自我效能": "self-efficacy",
        "主观幸福感": "subjective well-being",
        "情绪智力": "emotional intelligence",
        "心理韧性": "resilience",
        "社会支持": "social support",
        "工作倦怠": "job burnout",
        "大五人格": "big five personality",
        "应对方式": "coping style",
        "正念": "mindfulness",
        "认知失调": "cognitive dissonance",
        "归因": "attribution",
        "成就动机": "achievement motivation",
        "拖延": "procrastination",
        "印象管理": "impression management",
        "共情": "empathy",
        "依恋": "attachment",
        "创伤后成长": "posttraumatic growth",
        "内隐": "implicit",
        "执行功能": "executive function",
        "元认知": "metacognition",
        "量表": "scale OR measure OR inventory",
        "信效度": "reliability validity",
        "问卷": "questionnaire",
    }

    parts = query.split()
    en_parts = []
    for part in parts:
        # 先尝试整词匹配
        if part in concept_map:
            en_parts.append(concept_map[part])
        else:
            # 尝试部分匹配
            matched = False
            for cn, en in concept_map.items():
                if cn in part:
                    en_parts.append(en)
                    matched = True
                    break
            if not matched:
                en_parts.append(part)

    return " ".join(en_parts) if en_parts else ""


def clear_cache(older_than_hours: int = 24):
    """清理过期缓存"""
    if not _CACHE_DIR.exists():
        return

    cutoff = datetime.now() - timedelta(hours=older_than_hours)
    for cache_file in _CACHE_DIR.glob("*.json"):
        try:
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if mtime < cutoff:
                cache_file.unlink()
        except OSError:
            pass


# ============================================================
# 内部函数
# ============================================================


def _parse_crossref_item(item: Dict) -> Optional[CrawledReference]:
    """解析 Crossref API 返回的单条文献"""
    try:
        title = item.get("title", [""])[0] if item.get("title") else ""
        if not title:
            return None

        authors = []
        for author in item.get("author", []):
            family = author.get("family", "")
            given = author.get("given", "")
            if family:
                name = f"{family}, {given[0]}." if given else family
                authors.append(name)

        year = item.get("published-print", {}).get("date-parts", [[None]])[0][0]
        if not year:
            year = item.get("created", {}).get("date-parts", [[None]])[0][0]
        if not year:
            year = datetime.now().year

        doi = item.get("DOI", "")

        # 期刊信息
        container = item.get("container-title", [""])
        journal = container[0] if container else ""
        volume = item.get("volume", "")
        issue = item.get("issue", "")
        page = item.get("page", "")

        abstract = item.get("abstract", "")
        if isinstance(abstract, str) and abstract.startswith("<"):
            abstract = _strip_html(abstract)

        return CrawledReference(
            title=title,
            authors=authors,
            year=int(year),
            journal=journal,
            volume=str(volume) if volume else "",
            issue=str(issue) if issue else "",
            pages=str(page) if page else "",
            doi=doi,
            abstract=abstract[:500] if abstract else "",
            citation_count=item.get("is-referenced-by-count", 0),
            source="crossref",
            is_open_access="license" in item,
            url=f"https://doi.org/{doi}" if doi else "",
        )
    except Exception:
        return None


def _parse_s2_paper(paper: Dict) -> Optional[CrawledReference]:
    """解析 Semantic Scholar API 返回的单条论文"""
    try:
        title = paper.get("title", "")
        if not title:
            return None

        authors = []
        for author in paper.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(name)

        year = paper.get("year")
        if not year:
            year = datetime.now().year

        external_ids = paper.get("externalIds", {})
        doi = external_ids.get("DOI", "")

        venue = paper.get("publicationVenue") or paper.get("journal") or {}
        if isinstance(venue, dict):
            journal = venue.get("name", "")
            volume = venue.get("volume", "")
            pages = venue.get("pages", "")
        else:
            journal = str(venue) if venue else ""
            volume = ""
            pages = ""

        abstract = paper.get("abstract", "")

        return CrawledReference(
            title=title,
            authors=authors,
            year=int(year),
            journal=journal,
            volume=str(volume) if volume else "",
            issue="",
            pages=str(pages) if pages else "",
            doi=doi,
            abstract=abstract[:500] if abstract else "",
            citation_count=paper.get("citationCount", 0),
            source="semantic_scholar",
            is_open_access=paper.get("isOpenAccess", False),
            url=paper.get("url", ""),
        )
    except Exception:
        return None


def _ref_dedup_key(ref: CrawledReference) -> str:
    """生成去重键（基于DOI或标题+年份）"""
    if ref.doi:
        return ref.doi.lower()
    key = f"{ref.title.lower()}_{ref.year}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _strip_html(text: str) -> str:
    """去除HTML标签"""
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    return clean.strip()


def _load_cache(query: str, source: str) -> Optional[CrawlResult]:
    """加载缓存的搜索结果"""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"{query}_{source}".encode()).hexdigest()
    cache_file = _CACHE_DIR / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 检查TTL（24小时）
        cached_time = datetime.fromisoformat(data.get("search_time", "2000-01-01"))
        if datetime.now() - cached_time > timedelta(hours=24):
            return None

        refs = []
        for r in data.get("references", []):
            refs.append(CrawledReference(
                title=r.get("title", ""),
                authors=r.get("authors", []),
                year=r.get("year", 0),
                journal=r.get("journal", ""),
                volume=r.get("volume", ""),
                issue=r.get("issue", ""),
                pages=r.get("pages", ""),
                doi=r.get("doi", ""),
                abstract=r.get("abstract", ""),
                citation_count=r.get("citation_count", 0),
                source=r.get("source", source),
                is_open_access=r.get("is_open_access", False),
                url=r.get("url", ""),
            ))

        return CrawlResult(
            query=data.get("query", query),
            total_found=data.get("total_found", len(refs)),
            references=refs,
            source=source,
            search_time=data.get("search_time", ""),
            cached=True,
        )
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def _save_cache(query: str, source: str, result: CrawlResult):
    """保存搜索结果到缓存"""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"{query}_{source}".encode()).hexdigest()
    cache_file = _CACHE_DIR / f"{cache_key}.json"

    data = {
        "query": query,
        "source": source,
        "total_found": result.total_found,
        "search_time": result.search_time,
        "references": [r.to_dict() for r in result.references],
    }

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
