# -*- coding: utf-8 -*-
"""questionnaire 侧 APA7 手工串**收敛后**的相等钉测（s918-10 改写 916p-a4-005 的钉测）。

原文件钉的是「两处手工 f-string 与 `format_reference` 不一致」；本单把
`academic_literature.py:417` 与 `kb_search.py:190` 两处都改为委托 `LiteratureEntry.format_reference()`，
故钉3 从**不等断言改写为相等断言**，钉1/2/4 更新为收敛后的新形态。
全程离线：Crossref 响应经 monkeypatch 伪造，零联网、零真实抓取。
可复跑：.venv/Scripts/python.exe -m pytest tests/test_apa7_manual_string_pin.py -q
"""
import io
import json
from pathlib import Path

import pytest

from src.paper_writer.literature_manager import LiteratureEntry
from src.questionnaire.academic_literature import _parse_crossref_item
from src.questionnaire.kb_search import _search_crossref

ITEM = {
    "title": ["Latent Growth Modeling Scale"],
    "author": [{"family": "Smith", "given": "J."}, {"family": "Lee", "given": "K."}],
    "container-title": ["Structural Equation Modeling"],
    "published-print": {"date-parts": [[2020]]},
    "DOI": "10.1080/10705511.2020.1",
    "abstract": "A scale for measuring latent growth.",
    "publisher": "Taylor & Francis",
}

CONVERGED = ("Smith, J., & Lee, K. (2020). Latent Growth Modeling Scale. "
             "*Structural Equation Modeling*. https://doi.org/10.1080/10705511.2020.1")


class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _mock_search_response(monkeypatch, items):
    payload = json.dumps({"message": {"items": items}}).encode("utf-8")

    def fake_urlopen(req, timeout=0):
        assert "api.crossref.org/works" in req.full_url
        return _FakeResp(payload)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)


def test_academic_literature_site_emits_the_converged_string(monkeypatch):
    got = _parse_crossref_item(ITEM)["reference_apa7"]

    assert got == CONVERGED
    assert "*Structural Equation Modeling*" in got     # 斜体标记：原手工串没有
    assert "doi:10.1080" not in got                    # 不再出现 doi: 前缀形态


def test_kb_search_site_emits_the_converged_string(monkeypatch):
    _mock_search_response(monkeypatch, [ITEM])

    results = _search_crossref("成长模型")

    assert len(results) == 1
    assert results[0]["construct"]["reference"] == CONVERGED


def test_the_two_sites_now_agree_on_identical_input(monkeypatch):
    """钉3：原「不一致断言」改写为**相等断言**——同一条 Crossref 记录，两站点产出逐字相同。"""
    _mock_search_response(monkeypatch, [ITEM])

    from_academic = _parse_crossref_item(ITEM)["reference_apa7"]
    from_kb = _search_crossref("成长模型")[0]["construct"]["reference"]

    assert from_academic == from_kb == CONVERGED


def test_converged_output_matches_the_single_source_of_truth():
    """钉4：收敛面基线＝`LiteratureEntry.format_reference()` 本身（两站点不再各自造轮子）。"""
    baseline = LiteratureEntry(
        key="Smith2020", authors=["Smith, J.", "Lee, K."], year="2020",
        title="Latent Growth Modeling Scale", journal="Structural Equation Modeling",
        doi=ITEM["DOI"], is_chinese=False,
    ).format_reference()

    assert baseline == CONVERGED


def test_manual_fstrings_are_gone_from_both_sites():
    """反回退钉：两处旧手工拼串（含 kb_search 的 ' doi:' 形态）不得复活。"""
    root = Path(__file__).resolve().parents[1]
    academic = (root / "src/questionnaire/academic_literature.py").read_text(encoding="utf-8")
    kb = (root / "src/questionnaire/kb_search.py").read_text(encoding="utf-8")

    assert 'f" doi:{doi}"' not in kb
    assert 'ref_apa7 = f"{first_author} ({year}). {title}. {container}."' not in academic
    assert academic.count("format_reference()") == 1
    assert kb.count("format_reference()") == 1


def test_chinese_title_takes_the_chinese_branch_without_italics(monkeypatch):
    """is_chinese 由标题实际判定（非硬编码 False）：中文条目不加 Markdown 星号。"""
    zh = dict(ITEM, title=["中介效应分析量表"],
              author=[{"family": "温", "given": "忠麟"}, {"family": "叶", "given": "宝娟"}])

    got = _parse_crossref_item(zh)["reference_apa7"]

    assert got == ("温, 忠麟, 叶, 宝娟. (2020). 中介效应分析量表. "
                   "Structural Equation Modeling. https://doi.org/10.1080/10705511.2020.1")
    assert "*" not in got


def test_items_without_scale_keyword_still_return_none():
    """收敛未改变 _parse_crossref_item 的过滤语义：非量表标题照旧丢弃。"""
    assert _parse_crossref_item(dict(ITEM, title=["Something Else"])) is None
