"""文献综述搜索测试（mock crawler）。"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.literature_review.models import LiteratureItem
from src.literature_review.search import (
    deduplicate_by_doi,
    rank_by_relevance,
    search_literature,
)


def _mk_crawled(title, year, doi="", authors=None, journal="J Psy", abstract="",
                citation_count=0, source="crossref"):
    return SimpleNamespace(
        title=title, authors=authors or ["A"], year=year, journal=journal,
        doi=doi, abstract=abstract, citation_count=citation_count, source=source, url="",
    )


class TestSearchLiterature:
    def test_returns_empty_when_query_empty(self):
        result = search_literature("", None,
                                     crawler_search_all=lambda *a, **k: [],
                                     include_chinese=False)
        assert result["items"] == []
        assert result["method"] == "offline"

    def test_basic_search_returns_items(self):
        mock_crawler = lambda query, max_results, year_from: [
            _mk_crawled("X 与 Y 的关系", 2022, doi="10.1/a"),
            _mk_crawled("Z 研究", 2023, doi="10.2/b"),
        ]
        result = search_literature(
            "X 与 Y", {"dependent_vars": ["Y"]},
            max_results=10,
            crawler_search_all=mock_crawler,
            include_chinese=False,
        )
        assert len(result["items"]) == 2
        # 都是 LiteratureItem
        assert all(isinstance(it, LiteratureItem) for it in result["items"])
        assert result["method"] == "online"

    def test_year_filter_excludes_old(self):
        mock_crawler = lambda query, max_results, year_from: [
            _mk_crawled("旧文献", 2010, doi="10.1/a"),
            _mk_crawled("新文献", 2024, doi="10.2/b"),
        ]
        result = search_literature(
            "X", None, year_from=2020,
            crawler_search_all=mock_crawler,
            include_chinese=False,
        )
        titles = [it.title for it in result["items"]]
        assert "旧文献" not in titles
        assert "新文献" in titles

    def test_relevance_ranking(self):
        mock_crawler = lambda *a, **k: [
            _mk_crawled("无关研究", 2024, doi="10.1/x", citation_count=5),
            _mk_crawled("X 影响 Y 的研究", 2024, doi="10.2/x", citation_count=5,
                         abstract="本研究考察 X 对 Y 的影响"),
        ]
        result = search_literature(
            "X 影响 Y", None,
            crawler_search_all=mock_crawler,
            include_chinese=False,
        )
        # X 影响 Y 应排第一
        assert "X 影响" in result["items"][0].title

    def test_search_failure_returns_empty(self):
        def failing_crawler(*a, **k):
            raise RuntimeError("network error")
        result = search_literature("X", None, crawler_search_all=failing_crawler,
                                     include_chinese=False)
        assert result["items"] == []
        assert result["method"] == "offline"


class TestChineseSearchIntegration:
    """v3.5 中文文献库接通。"""

    def test_chinese_search_called_when_include_chinese_true(self):
        # mock 英文返回 1，中文返回 1
        mock_en = lambda *a, **k: [_mk_crawled("English Study", 2024, doi="10.1/en")]
        from types import SimpleNamespace
        mock_cn = lambda query, max_results, year_from: SimpleNamespace(
            references=[_mk_crawled("中文研究", 2024, doi="10.2/cn", journal="心理学报")]
        )
        result = search_literature(
            "焦虑", None, max_results=10,
            crawler_search_all=mock_en,
            chinese_search_fn=mock_cn,
            include_chinese=True,
        )
        titles = [it.title for it in result["items"]]
        assert "English Study" in titles
        assert "中文研究" in titles
        assert result["method"] == "online_with_chinese"
        assert "chinese" in result["sources"]

    def test_chinese_search_failure_falls_back(self):
        mock_en = lambda *a, **k: [_mk_crawled("EN Study", 2024, doi="10.1/en")]
        def failing_cn(*a, **k):
            raise RuntimeError("CNKI down")
        result = search_literature(
            "X", None,
            crawler_search_all=mock_en,
            chinese_search_fn=failing_cn,
            include_chinese=True,
        )
        # 中文失败但英文成功 → method="online"
        assert len(result["items"]) == 1
        assert result["method"] == "online"


class TestDeduplicate:
    def test_doi_dedup(self):
        items = [
            LiteratureItem(title="A", year=2024, doi="10.1/x"),
            LiteratureItem(title="A 重复", year=2024, doi="10.1/x"),
            LiteratureItem(title="B", year=2024, doi="10.2/y"),
        ]
        out = deduplicate_by_doi(items)
        assert len(out) == 2
        dois = [it.doi for it in out]
        assert "10.1/x" in dois
        assert "10.2/y" in dois

    def test_title_dedup_when_no_doi(self):
        items = [
            LiteratureItem(title="同名研究", year=2024),
            LiteratureItem(title="同名研究", year=2024),
            LiteratureItem(title="同名研究", year=2025),   # 年份不同算不同
        ]
        out = deduplicate_by_doi(items)
        assert len(out) == 2

    def test_doi_normalization(self):
        items = [
            LiteratureItem(title="A", doi="https://doi.org/10.1/x", year=2024),
            LiteratureItem(title="A", doi="10.1/x", year=2024),
        ]
        out = deduplicate_by_doi(items)
        assert len(out) == 1
