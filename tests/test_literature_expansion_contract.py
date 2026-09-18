# -*- coding: utf-8 -*-
"""s918-36：文献扩展库数据契约钉桩（87→107 漂移）。

docstring 漂移记录：literature_expansion.py:1 声称「87 条新增 APA 7th Edition
格式参考文献」，但 get_expansion_entries() 实测返回 107 条
（zh48 + zh_extra10 + en39 + en_extra10；与预设库重叠 9 键）。
docstring 未随数据扩批更新——本契约按实测现状钉住，修订 docstring 留日间。
"""
import pytest

from src.paper_writer.literature_expansion import get_expansion_entries


def test_total_count_is_107():
    """总数钉桩：实测 107（docstring 的 87 已漂移）。返回为 {key: entry} 字典。"""
    entries = get_expansion_entries()
    assert len(entries) == 107
    assert isinstance(entries, dict)


def test_all_entries_are_literature_entry():
    """全部为 LiteratureEntry 实例（类型契约）。"""
    entries = get_expansion_entries()
    assert len(entries) > 0
    for e in entries.values():
        assert type(e).__name__ == 'LiteratureEntry', f"{e} 非 LiteratureEntry"


def test_keys_unique():
    """键唯一：dict 天然唯一；再验 entry.key 与字典键一致。"""
    entries = get_expansion_entries()
    for k, e in entries.items():
        assert e.key == k, f"字典键 {k} 与 entry.key {e.key} 不一致"


def test_each_entry_has_bibliography_fields():
    """每条至少具备作者/年份/标题三要素（APA 7th 最小可渲染集）。"""
    entries = get_expansion_entries()
    for e in entries.values():
        assert getattr(e, "authors", None), f"{e.key} 缺 authors"
        assert getattr(e, "year", None), f"{e.key} 缺 year"
        assert getattr(e, "title", None), f"{e.key} 缺 title"


def test_language_split_matches_known_census():
    """中英分段：is_chinese 字段分层，两类都非空。"""
    entries = get_expansion_entries()
    zh = [e for e in entries.values() if getattr(e, "is_chinese", False)]
    en = [e for e in entries.values() if not getattr(e, "is_chinese", False)]
    assert len(zh) > 0 and len(en) > 0
    assert len(zh) + len(en) == len(entries)
