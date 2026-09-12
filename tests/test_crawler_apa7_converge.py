# -*- coding: utf-8 -*-
"""p911r-31：crawler to_apa7 收敛到 format_reference 的回归测试。

覆盖 publisher 缺失分支（期刊类条目）与中文无斜体口径（ecdb 已定）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper_writer.literature_crawler import CrawledReference
from src.paper_writer.literature_manager import LiteratureEntry


def _entry(**kw):
    base = dict(key="probe", authors=["A. One"], year="2020", title="T",
                journal="J of Testing", volume="", issue="", pages="", doi="",
                is_chinese=False)
    base.update(kw)
    return LiteratureEntry(**base)


def test_publisher_missing_journal_branch():
    """期刊类条目（publisher 缺失）：走期刊分支，无出版社尾巴，与 LiteratureEntry 等价。"""
    r = CrawledReference(title="T", authors=["A. One"], year=2020,
                         journal="J of Testing", volume="12", issue="3", pages="10-20",
                         doi="10.1234/abc")
    out = r.to_apa7(is_chinese=False)
    expected = _entry(journal="J of Testing", volume="12", issue="3", pages="10-20",
                      doi="10.1234/abc").format_reference()
    assert out == expected
    assert "出版社" not in out and "Press" not in out
    assert "https://doi.org/10.1234/abc" in out


def test_chinese_branch_keeps_no_italic():
    """中文分支（ecdb 口径：中文无斜体）：输出不含 * 斜体标记。"""
    r = CrawledReference(title="中介效应分析", authors=["温忠麟", "叶宝娟"], year=2014,
                         journal="心理科学进展", volume="22", issue="5", pages="731-745")
    out = r.to_apa7(is_chinese=True)
    assert "*" not in out
    assert "心理科学进展" in out


def test_delegation_uses_format_reference_semantics():
    """委托收敛：crawler 输出与「同字段 LiteratureEntry.format_reference」完全一致（含 >20 作者 APA7 省略）。"""
    many = [f"Author {chr(65 + i)}." for i in range(25)]
    r = CrawledReference(title="Big survey", authors=many, year=2023, journal="Big J")
    expected = _entry(authors=many, year="2023", title="Big survey", journal="Big J").format_reference()
    assert r.to_apa7(is_chinese=False) == expected
