"""论文写作系统 — 心理学报格式论文初稿生成"""

from .paper_engine import PaperEngine, PaperState
from .literature_manager import (
    LiteratureManager, LiteratureEntry, smart_search_literature,
    CitationCheckResult, cross_check_citations, cross_check_references_list,
)
from .interactive_qa import InteractiveQA, Question, QUESTION_TEMPLATES
from .section_writers import PaperContext
from .psychology_report_format import (
    PAPER_SECTIONS, STAT_FORMATS, SIG_MARKS,
    EFFECT_SIZE_GUIDE, WRITING_RULES, ACADEMIC_PHRASES,
)
from .literature_crawler import (
    CrawledReference, CrawlResult,
    search_crossref, search_semantic_scholar, search_all,
    search_for_construct, recommend_literature, clear_cache,
    search_chinese_literature, search_idata, resolve_cnki_doi,
)

__all__ = [
    "PaperEngine", "PaperState",
    "LiteratureManager", "LiteratureEntry", "smart_search_literature",
    "CitationCheckResult", "cross_check_citations",
    "cross_check_references_list",
    "InteractiveQA", "Question", "QUESTION_TEMPLATES",
    "PaperContext",
    "PAPER_SECTIONS", "STAT_FORMATS", "SIG_MARKS",
    "EFFECT_SIZE_GUIDE", "WRITING_RULES", "ACADEMIC_PHRASES",
    "CrawledReference", "CrawlResult",
    "search_crossref", "search_semantic_scholar", "search_all",
    "search_for_construct", "recommend_literature", "clear_cache",
    "search_chinese_literature", "search_idata", "resolve_cnki_doi",
]
