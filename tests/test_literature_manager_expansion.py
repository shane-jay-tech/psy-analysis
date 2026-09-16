"""literature_manager 盲区测试实现（916-04，按设计稿 n916c-08 ≥6 条）。

纯合成数据，零联网：validate_doi 的 Crossref 请求经 monkeypatch 离线伪造。
可复跑：python -m pytest tests/test_literature_manager_expansion.py -q
"""
import io
import json

import pytest

from src.paper_writer.literature_manager import (
    CitationCheckResult,
    LiteratureEntry,
    LiteratureManager,
    cross_check_citations,
    validate_doi,
)


def _entry(**overrides) -> LiteratureEntry:
    base = dict(
        key="温忠麟2014",
        authors=["温忠麟", "叶宝娟"],
        year="2014",
        title="中介效应分析: 方法和模型发展",
        journal="心理科学进展",
        volume="22",
        issue="5",
        pages="731-745",
        doi="10.3724/SP.J.1042.2014.00731",
        is_chinese=True,
    )
    base.update(overrides)
    return LiteratureEntry(**base)


# 1. LiteratureEntry 数据类：构造后引用标记与文献条目含作者/年份/标题
def test_literature_entry_roundtrip_and_citation():
    e = _entry()
    assert e.format_citation() == "[温忠麟2014]"
    ref = e.format_reference()
    assert "温忠麟" in ref and "2014" in ref and "中介效应分析" in ref


# 2. APA 参考文献格式（设计稿条目2 的 APA 断言落在 format_reference——
#    format_citation 实现为 [key] 标记，APA 职责在 format_reference，见实现报告）
def test_format_reference_apa():
    cn = _entry().format_reference()
    assert cn.startswith("温忠麟, 叶宝娟. (2014). 中介效应分析: 方法和模型发展.")
    assert "心理科学进展, 22(5), 731-745." in cn
    assert cn.endswith("https://doi.org/10.3724/SP.J.1042.2014.00731")

    en = _entry(
        key="smith2020",
        authors=["Smith, J.", "Jones, K."],
        year="2020",
        title="Latent growth modeling",
        journal="Structural Equation Modeling",
        volume="12",
        issue="3",
        pages="1-10",
        doi="10.1080/10705511.2020.1",
        is_chinese=False,
    ).format_reference()
    assert en.startswith("Smith, J., & Jones, K. (2020). Latent growth modeling.")
    assert "*Structural Equation Modeling*, *12*(3), 1-10." in en


# 3. validate_doi：非法输入 → None（离线路径）；合法 DOI 经 mock Crossref 解析元数据
def test_validate_doi_shape_and_offline_mock(monkeypatch):
    assert validate_doi("") is None
    assert validate_doi("not-a-doi") is None  # 无斜杠，不发请求直接 None

    class _FakeResp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    payload = json.dumps({
        "message": {
            "title": ["Latent growth modeling"],
            "author": [{"family": "Smith", "given": "J."}],
            "container-title": ["Structural Equation Modeling"],
            "published-print": {"date-parts": [[2020]]},
            "volume": "12", "issue": "3", "page": "1-10",
            "publisher": "Taylor & Francis", "type": "journal-article",
        }
    }).encode("utf-8")

    def fake_urlopen(req, timeout=0):
        assert "api.crossref.org/works/" in req.full_url
        return _FakeResp(payload)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    meta = validate_doi("https://doi.org/10.1080/10705511.2020.1")
    assert meta is not None and meta["verified"] is True
    assert meta["title"] == "Latent growth modeling"
    assert meta["authors"] == ["Smith, J."]
    assert meta["year"] == "2020" and meta["volume"] == "12" and meta["pages"] == "1-10"


# 4. cross_check_citations：缺失引用被标记＋作者-年份备选匹配
def test_cross_check_citations():
    entries = [
        _entry(),
        _entry(key="tiaoji2020", authors=["李四"], year="2020", title="调节效应"),
    ]
    # 引用标记须含「文字+4位年份」才会被当作引用（[张三2001] 缺库 → missing；
    # [李四2020] 与 key 不符但命中「第一作者+年份」备选键 → verified）。
    text = "方法上采用中介效应检验[温忠麟2014]，并结合调节效应[李四2020]与未知文献[张三2001]。"
    res = cross_check_citations(text, entries)
    assert isinstance(res, CitationCheckResult)
    assert res.total_citations == 3
    assert res.verified == 2
    assert res.missing == 1
    assert res.missing_citations == ["张三2001"]


# 5. LiteratureManager roundtrip：add_entry 后 get_entry 查回；重复 key 不覆盖
def test_literature_manager_roundtrip():
    mgr = LiteratureManager()
    before = len(mgr.entries)
    e = _entry(key="newkey2024")
    mgr.add_entry(e)
    assert mgr.get_entry("newkey2024") is e
    duplicate = _entry(key="newkey2024", title="另一篇同名 key 的文章")
    mgr.add_entry(duplicate)
    assert mgr.get_entry("newkey2024") is e  # 首入为准
    assert mgr.get_entry("不存在的key") is None
    assert len(mgr.entries) == before + 1


# 6. search_presets：关键词命中预置库
def test_search_presets():
    mgr = LiteratureManager()
    hits = mgr.search_presets(["中介效应"], n=5)
    assert hits and any(h.key == "温忠麟2014" for h in hits)
    assert mgr.search_presets(["量子纠缠暗物质绝对不存在词"], n=5) == []
