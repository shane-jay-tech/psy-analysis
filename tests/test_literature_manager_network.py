"""src/paper_writer/literature_manager.py 三个网络函数离线 mock 单测（s918-11）。

仿 815ac64（`tests/test_literature_manager_expansion.py`）的 urlopen monkeypatch 先例：
**零联网、零真实 Crossref 请求、src/ 零改动**。覆盖 happy／异常／空结果三态。
覆盖函数：`smart_search_literature`(:1621)、`autofill_from_doi`(:1758)、`enrich_reference`(:1794)。
"""
import asyncio
import io
import json

from src.paper_writer.literature_manager import (
    LiteratureEntry,
    LiteratureManager,
    autofill_from_doi,
    enrich_reference,
    smart_search_literature,
)


class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _crossref_bytes(**over):
    msg = {
        "title": ["Latent growth modeling"],
        "author": [{"family": "Smith", "given": "J."}],
        "container-title": ["Structural Equation Modeling"],
        "published-print": {"date-parts": [[2020]]},
        "volume": "12", "issue": "3", "page": "1-10",
        "publisher": "Taylor & Francis", "type": "journal-article",
    }
    msg.update(over)
    return json.dumps({"message": msg}).encode("utf-8")


def _patch_crossref(monkeypatch, payload=None, raises=None):
    calls = []

    def fake_urlopen(req, timeout=0):
        calls.append(req.full_url)
        if raises is not None:
            raise raises
        return _FakeResp(payload if payload is not None else _crossref_bytes())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return calls


def _preset(**over):
    base = dict(key="张三2019", authors=["张三"], year="2019", title="中文心理学研究",
                journal="心理学报", volume="51", issue="1", pages="1-12", doi="")
    base.update(over)
    return LiteratureEntry(**base)


def _patch_presets(monkeypatch, entries):
    monkeypatch.setattr(LiteratureManager, "search_presets",
                        lambda self, keywords, n=10: list(entries))


# ---------- smart_search_literature ----------

def _search(topic="成长模型", keywords=("LGM", "growth"), prefer_chinese=True):
    return asyncio.run(smart_search_literature(topic, list(keywords), prefer_chinese))


def test_smart_search_returns_presets_and_skips_online_when_not_chinese(monkeypatch):
    _patch_presets(monkeypatch, [_preset()])
    hits = []
    monkeypatch.setattr(LiteratureManager, "search_online",
                        lambda self, query, n=5: hits.append(query) or [])

    got = _search(prefer_chinese=False)
    assert [r["key"] for r in got] == ["张三2019"]
    assert hits == []


def test_smart_search_merges_online_hits_with_hash_keys_and_review_flag(monkeypatch):
    _patch_presets(monkeypatch, [_preset()])
    online = [{"construct": {"reference": "Smith 2020 xxx", "authors": ["Smith, J."],
                             "year": "2020", "title": "Latent growth modeling",
                             "journal": "SEM"}}]
    seen = {}

    def fake_online(self, query, n=5):
        seen["query"] = query
        seen["n"] = n
        return online

    monkeypatch.setattr(LiteratureManager, "search_online", fake_online)

    got = _search()

    assert seen["query"] == "成长模型 LGM growth 心理学" and seen["n"] == 3
    assert len(got) == 2
    merged = got[-1]
    assert merged["key"].startswith("online_") and len(merged["key"]) == len("online_") + 8
    assert merged["source"] == "crossref"
    assert merged["title"] == "Latent growth modeling" and merged["is_chinese"] is False
    assert merged["relevance"] == "在线检索文献，需人工审核"


def test_smart_search_marks_chinese_titles_from_online(monkeypatch):
    _patch_presets(monkeypatch, [])
    monkeypatch.setattr(LiteratureManager, "search_online",
                        lambda self, query, n=5: [{"construct": {"reference": "r",
                                                                 "title": "中文标题"}}])

    got = _search()

    assert got[0]["is_chinese"] is True


def test_smart_search_swallows_online_failure(monkeypatch):
    _patch_presets(monkeypatch, [_preset()])

    def boom(self, query, n=5):
        raise RuntimeError("network down")

    monkeypatch.setattr(LiteratureManager, "search_online", boom)

    got = _search()

    assert [r["key"] for r in got] == ["张三2019"]


def test_smart_search_returns_empty_list_when_both_sources_empty(monkeypatch):
    _patch_presets(monkeypatch, [])
    monkeypatch.setattr(LiteratureManager, "search_online", lambda self, query, n=5: [])

    assert _search() == []


# ---------- autofill_from_doi ----------

def test_autofill_skips_request_for_unparsable_doi(monkeypatch):
    calls = _patch_crossref(monkeypatch)

    assert autofill_from_doi("") is None
    assert autofill_from_doi("not-a-doi") is None
    assert calls == []


def test_autofill_builds_apa_key_and_marks_review_needed(monkeypatch):
    _patch_crossref(monkeypatch)

    entry = autofill_from_doi("https://doi.org/10.1080/10705511.2020.1")

    assert entry.key == "Smith2020"
    assert entry.authors == ["Smith, J."] and entry.year == "2020"
    assert entry.journal == "Structural Equation Modeling"
    assert entry.volume == "12" and entry.issue == "3" and entry.pages == "1-10"
    assert entry.doi == "10.1080/10705511.2020.1"
    assert entry.is_chinese is False and entry.source == "crossref_autofill"
    assert "需人工审核" in entry.relevance_note


def test_autofill_key_for_chinese_title_drops_comma_and_space(monkeypatch):
    _patch_crossref(monkeypatch, payload=_crossref_bytes(
        title="中文标题", author=[{"family": "王", "given": "五"}]))

    entry = autofill_from_doi("10.1/中文")

    assert entry.is_chinese is True
    assert entry.key == "王五2020"


def test_autofill_returns_none_when_crossref_fails(monkeypatch):
    _patch_crossref(monkeypatch, raises=OSError("timeout"))

    assert autofill_from_doi("10.1080/10705511.2020.1") is None


def test_autofill_returns_none_on_empty_crossref_message(monkeypatch):
    _patch_crossref(monkeypatch, payload=json.dumps({"message": {}}).encode("utf-8"))

    assert autofill_from_doi("10.1080/10705511.2020.1") is None


# ---------- enrich_reference ----------

def test_enrich_without_doi_returns_same_object_without_requesting(monkeypatch):
    calls = _patch_crossref(monkeypatch)
    entry = _preset(doi="")

    assert enrich_reference(entry) is entry
    assert calls == []


def test_enrich_fills_only_the_missing_fields(monkeypatch):
    _patch_crossref(monkeypatch)
    entry = _preset(doi="10.1080/10705511.2020.1", volume="99", issue="", pages="")

    out = enrich_reference(entry)

    assert out.volume == "99"          # 用户已填 → 保留
    assert out.issue == "3"            # 空 → 由 Crossref 补
    assert out.pages == "1-10"


def test_enrich_leaves_entry_unchanged_when_lookup_fails(monkeypatch):
    _patch_crossref(monkeypatch, raises=OSError("503"))
    entry = _preset(doi="10.1080/10705511.2020.1", volume="", issue="", pages="")

    out = enrich_reference(entry)

    assert (out.volume, out.issue, out.pages) == ("", "", "")
