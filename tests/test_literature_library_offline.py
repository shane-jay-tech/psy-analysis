"""s922-120：内置文献库（src/paper_writer/literature_library.py）离线检索钉桩。

零联网：只用模块内的静态 dict，不触碰任何外部服务，也不使用测试替身。

基线数字来自开工前实测（先跑后写死，命令原文见各用例注释）：
    .venv/Scripts/python.exe -c "from src.paper_writer.literature_library import \\
        LITERATURE_LIBRARY as L, get_total_entry_count as G; \\
        print(G(), len(L), len({(e[0], e[1]) for v in L.values() for e in v}))"
    -> 112 91 112

覆盖三块：
1) get_total_entry_count 的非零基线（判据 2 要求固化实测值）；
2) match_references 的精确优先排序 / top_n 截断 / 签名去重 / 空输入回退；
3) format_citation_apa7 对全部唯一条目的 APA7 排版形态（判据 4：正则比对，
   容忍 "C.." 这类双句点标点微调）。

与既有测试的分工（开工前实测）：
- tests/test_ui.py::TestLiteratureRecommendation 只断言 count > 100 与 len(refs) >= 1
  ——本件把「非零基线」收紧为精确值，并补排序/截断/去重面；
- tests/test_apa7_gate_and_citation.py 逐条覆盖 B1/B3/B5/B8/B11 边界——
  本件不重复边界，改为对**库内真实条目**做整体形态回归。
"""
import re

import pytest

from src.paper_writer.literature_library import (
    LITERATURE_LIBRARY,
    format_citation_apa7,
    get_total_entry_count,
    match_references,
)

# ---- 实测基线（改动文献库会翻红，属设计意图：倒逼同步回写边界表）----
BASELINE_UNIQUE_ENTRIES = 112
BASELINE_LIBRARY_KEYS = 91

APA7_SHAPE = re.compile(
    r"^(?P<authors>.+?)\.?\s*"
    r"\((?P<year>\d{4}(?:/\d{4})?|n\.d\.)\)\.\s*"
    r"(?P<title>.+?)\.\s*"
    r"(?P<source>.+)$"
)


def _unique_entries():
    """按 (作者, 年份) 签名去重后的条目列表——与 get_total_entry_count 同口径。"""
    return {(e[0], e[1]): e for entries in LITERATURE_LIBRARY.values() for e in entries}


# ---------------------------------------------------------------- 基线计数

class TestEntryCountBaseline:

    def test_count_is_non_zero(self):
        assert get_total_entry_count() >= 1

    def test_count_matches_measured_baseline(self):
        # 固化自 python -c 实测（判据 2）
        assert get_total_entry_count() == BASELINE_UNIQUE_ENTRIES

    def test_count_equals_deduplicated_signature_count(self):
        # 计数口径自证：去重签名数 == 返回值
        assert get_total_entry_count() == len(_unique_entries())

    def test_key_count_matches_measured_baseline(self):
        assert len(LITERATURE_LIBRARY) == BASELINE_LIBRARY_KEYS

    def test_every_entry_is_four_field_tuple_with_str_year(self):
        lens = {len(e) for e in _unique_entries().values()}
        years = {type(e[1]).__name__ for e in _unique_entries().values()}
        assert lens == {4}, lens
        assert years == {"str"}, years


# ---------------------------------------------------------------- 关键词匹配

class TestMatchReferencesOrdering:

    def test_exact_hits_sort_before_fuzzy_hits(self):
        # '焦虑' 既是库键（精确路径），又是 '社交焦虑' 的子串（模糊路径）
        keys = [k for k, _ in match_references(["焦虑"], top_n=50)]
        assert keys.count("焦虑") >= 5
        first_fuzzy = next(i for i, k in enumerate(keys) if k != "焦虑")
        assert set(keys[:first_fuzzy]) == {"焦虑"}
        assert "社交焦虑" in keys[first_fuzzy:]

    def test_top_n_truncates_and_preserves_prefix(self):
        three = match_references(["社交焦虑"], top_n=3)
        five = match_references(["社交焦虑"], top_n=5)
        assert len(three) == 3
        assert len(five) == 5
        assert five[:3] == three

    def test_default_top_n_is_five(self):
        assert len(match_references(["自尊"])) == 5

    def test_top_n_zero_returns_empty(self):
        assert match_references(["自尊"], top_n=0) == []

    def test_results_are_signature_deduplicated(self):
        # '焦虑' 同时命中 焦虑/社交焦虑 两键，别名键共享同一 list 实例
        refs = match_references(["焦虑"], top_n=50)
        sigs = [(e[0], e[1]) for _, e in refs]
        assert len(sigs) == len(set(sigs)) == 10

    def test_unknown_keyword_returns_empty_list(self):
        assert match_references(["完全不存在的关键词xyz"], top_n=5) == []

    def test_empty_keyword_list_returns_empty(self):
        assert match_references([], top_n=5) == []

    def test_english_alias_key_matches_same_entries(self):
        zh = [e for _, e in match_references(["自尊"], top_n=3)]
        en = [e for _, e in match_references(["self esteem"], top_n=3)]
        assert zh == en

    def test_mixed_case_keyword_keeps_content_but_echoes_raw_keyword(self):
        # 现状钉桩：精确分支写入的是未降纲的 kw 本身，故返回键回显原样大小写，
        # 且因排序键只比对小写化后的关键词，这类输入的条目落到排序后段。
        refs = match_references(["Self Esteem"], top_n=3)
        assert [k for k, _ in refs] == ["Self Esteem"] * 3
        assert len(refs) == len(match_references(["self esteem"], top_n=3))

    def test_multiple_keywords_merge_matches(self):
        keys = {k for k, _ in match_references(["自尊", "社交焦虑"], top_n=10)}
        assert len(match_references(["自尊", "社交焦虑"], top_n=10)) > 5
        assert keys & {"自尊", "社交焦虑"}


# ---------------------------------------------------------------- APA7 排版

class TestApa7FormattingOfLibraryEntries:

    def test_all_unique_entries_follow_apa7_shape(self):
        # 判据 4：正则而非全串比对（作者缩写后的 "C.." 双句点属标点微调）
        bad = []
        for sig, entry in _unique_entries().items():
            out = format_citation_apa7(entry)
            if not APA7_SHAPE.match(out):
                bad.append((sig, out[:80]))
        assert not bad, f"{len(bad)} 条目不符 APA7 形态：{bad[:3]}"

    @pytest.mark.parametrize("keyword", ["社交焦虑", "自尊", "抑郁", "大五人格"])
    def test_top_hit_fields_land_in_expected_slots(self, keyword):
        entry = match_references([keyword], top_n=1)[0][1]
        out = format_citation_apa7(entry)
        m = APA7_SHAPE.match(out)
        assert m, out
        assert m.group("authors").strip().rstrip(".") == entry[0].strip().rstrip(".")
        assert m.group("year") == entry[1]
        assert entry[2][:20] in m.group("title")
        assert m.group("source").strip()

    def test_apa7_output_is_single_line_string(self):
        for _, entry in match_references(["睡眠"], top_n=3):
            out = format_citation_apa7(entry)
            assert isinstance(out, str)
            assert "\n" not in out and "\r" not in out
            assert out.endswith(".")
