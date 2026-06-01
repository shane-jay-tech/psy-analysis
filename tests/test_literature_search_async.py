"""论文写作模块 — 异步文献搜索测试"""

import pytest
from unittest.mock import patch, MagicMock

from src.paper_writer.literature_search_async import (
    search_literature_with_online,
    search_literature_async,
    cancel_search_request,
    CancelledSearchError,
)


class TestLiteratureSearchAsync:
    def test_search_presets_only(self):
        results = search_literature_with_online(
            keywords=["中介效应"],
            include_online=False,
        )
        assert isinstance(results, list)
        assert len(results) > 0
        assert any("温忠麟" in str(r.get("authors", [])) for r in results)

    def test_cancel_search_request(self):
        from src.paper_writer.literature_search_async import _alloc_cancel_id
        cid = _alloc_cancel_id()
        assert cancel_search_request(cid) is True
        assert cancel_search_request(99999) is False

    def test_cancelled_during_search(self):
        from src.paper_writer.literature_search_async import _alloc_cancel_id
        cid = _alloc_cancel_id()
        cancel_search_request(cid)
        with pytest.raises(CancelledSearchError):
            search_literature_with_online(
                keywords=["中介效应"],
                include_online=False,
                cancel_id=cid,
            )

    def test_async_returns_future_and_cancel_id(self):
        result = search_literature_async(
            keywords=["自尊"],
            include_online=False,
        )
        assert "future" in result
        assert "cancel_id" in result
        assert isinstance(result["cancel_id"], int)
        # Wait for completion
        results = result["future"].result()
        assert isinstance(results, list)

    def test_online_search_mocked(self):
        mock_online = [
            {
                "construct": {
                    "authors": ["Smith, J."],
                    "year": "2020",
                    "title": "Test Title",
                    "journal": "Test Journal",
                    "reference": "Smith (2020). Test Title. Test Journal.",
                }
            }
        ]
        with patch(
            "src.paper_writer.literature_search_async.LiteratureManager.search_online",
            return_value=mock_online,
        ):
            results = search_literature_with_online(
                keywords=["test"],
                include_online=True,
            )
            online_entries = [r for r in results if r.get("source") == "crossref"]
            assert len(online_entries) >= 1
            assert online_entries[0]["title"] == "Test Title"
