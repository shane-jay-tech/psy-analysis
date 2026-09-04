# -*- coding: utf-8 -*-
"""literature_manager.format_reference 的 APA7 边界用例（psy-C4 缺陷修复回归）。

覆盖：>20 作者省略规则、20 作者边界、书籍 publisher、中文两作者回归、DOI 清洗回归。
"""
from src.paper_writer.literature_manager import LiteratureEntry


def _en(**kw):
    base = dict(key="k", authors=["Author1, X."], year=2020, title="A study", journal="J of Tests",
                is_chinese=False)
    base.update(kw)
    return LiteratureEntry(**base)


def test_twentyone_authors_ellipsized():
    """21 位作者：前 19 位 + … + 末位（APA 7 省略规则）。"""
    e = _en(authors=[f"Author{i}, X." for i in range(1, 22)])
    ref = e.format_reference()
    assert "Author19, X." in ref
    assert "…, & Author21, X." in ref
    assert "Author20" not in ref


def test_twenty_authors_no_ellipsis():
    """20 位作者为边界：不省略，末位用 & 连接。"""
    e = _en(authors=[f"Author{i}, X." for i in range(1, 21)])
    ref = e.format_reference()
    assert "Author20, X." in ref
    assert "…" not in ref
    assert ", & Author20, X." in ref


def test_book_publisher_appended():
    """书籍条目（无期刊）携带出版社：追加出版社且以句号收尾。"""
    e = _en(title="Coefficient alpha", journal="", publisher="Psychometrika Press", year=1951)
    ref = e.format_reference()
    assert "Psychometrika Press." in ref
    assert ref.endswith(".")


def test_chinese_two_authors_regression():
    """中文两作者：格式回归（作者. (年). 标题. 期刊, 卷(期), 页码.）。"""
    e = LiteratureEntry(key="温忠麟2014", authors=["温忠麟", "叶宝娟"], year=2014,
                        title="中介效应分析", journal="心理科学进展", volume="22",
                        issue="5", pages="731-745", is_chinese=True)
    ref = e.format_reference()
    assert ref == "温忠麟, 叶宝娟. (2014). 中介效应分析. 心理科学进展, 22(5), 731-745."


def test_doi_cleaning_regression():
    """DOI 前缀清洗回归（带 https://doi.org/ 前缀也能正确输出）。"""
    e = _en(doi="https://doi.org/10.3758/s13428", volume="46", pages="1-10")
    ref = e.format_reference()
    assert "https://doi.org/10.3758/s13428" in ref
    assert "doi:" not in ref
