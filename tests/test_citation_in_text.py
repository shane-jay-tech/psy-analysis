# -*- coding: utf-8 -*-
"""citation_in_text.replace_inline_citations 的边界用例。

覆盖：1/2/3/20+ 作者、中文作者、未知 key、多 key 分号（全/半角）、
嵌套方括号不误伤、空白容错、LiteratureManager 真实对象接入、无引用原文原样。
"""
from src.paper_writer.citation_in_text import (
    InTextCitationResult,
    replace_inline_citations,
)
from src.paper_writer.literature_manager import LiteratureEntry, LiteratureManager


def _en(key, authors, year=2020, **kw):
    base = dict(key=key, authors=authors, year=year, title="T", journal="J",
                is_chinese=False)
    base.update(kw)
    return LiteratureEntry(**base)


def _cn(key, authors, year=2014, **kw):
    base = dict(key=key, authors=authors, year=year, title="题", journal="刊",
                is_chinese=True)
    base.update(kw)
    return LiteratureEntry(**base)


def test_single_key_one_author():
    lib = {"smith2020": _en("smith2020", ["Smith, J. A."])}
    r = replace_inline_citations("如 [smith2020] 所示。", lib)
    assert r.text == "如 (Smith, 2020) 所示。"
    assert r.replaced_groups == 1 and r.unknown_keys == []


def test_single_key_two_authors_english():
    lib = {"sj2021": _en("sj2021", ["Smith, J. A.", "Jones, B."], year=2021)}
    r = replace_inline_citations("[sj2021]", lib)
    assert r.text == "(Smith & Jones, 2021)"


def test_single_key_three_authors_et_al():
    lib = {"abc2022": _en("abc2022", ["Smith, J.", "Jones, B.", "Lee, C."], year=2022)}
    r = replace_inline_citations("[abc2022]", lib)
    assert r.text == "(Smith et al., 2022)"


def test_twentyone_authors_in_text_uses_first_et_al():
    lib = {"big2023": _en("big2023", [f"Author{i}, X." for i in range(1, 22)], year=2023)}
    r = replace_inline_citations("[big2023]", lib)
    # 正文内引用：>20 作者同样是 First et al.（省略号规则仅用于参考文献表）
    assert r.text == "(Author1 et al., 2023)"


def test_chinese_two_authors():
    lib = {"温忠麟2014": _cn("温忠麟2014", ["温忠麟", "叶宝娟"])}
    r = replace_inline_citations("该方法 [温忠麟2014] 提出。", lib)
    assert r.text == "该方法 (温忠麟与叶宝娟, 2014) 提出。"


def test_chinese_three_authors_deng():
    lib = {"hz2018": _cn("hz2018", ["张三", "李四", "王五"], year=2018)}
    r = replace_inline_citations("[hz2018]", lib)
    assert r.text == "(张三等, 2018)"


def test_multi_key_semicolon_preserves_order():
    lib = {"a2020": _en("a2020", ["Alpha, A."], year=2020),
           "b2021": _en("b2021", ["Beta, B."], year=2021)}
    r = replace_inline_citations("对比 [b2021; a2020] 两个研究。", lib)
    assert r.text == "对比 (Beta, 2021; Alpha, 2020) 两个研究。"


def test_multi_key_fullwidth_semicolon_and_spaces():
    lib = {"a2020": _en("a2020", ["Alpha, A."], year=2020),
           "b2021": _en("b2021", ["Beta, B."], year=2021)}
    r = replace_inline_citations("[ a2020　； b2021 ]", lib)
    assert r.text == "(Alpha, 2020; Beta, 2021)"


def test_unknown_key_kept_and_collected():
    lib = {"known2020": _en("known2020", ["Smith, J."])}
    r = replace_inline_citations("[ghost2099] 与 [known2020]", lib)
    assert "[ghost2099]" in r.text
    assert "(Smith, 2020)" in r.text
    assert r.unknown_keys == ["ghost2099"]


def test_mixed_known_unknown_group_untouched():
    lib = {"a2020": _en("a2020", ["Alpha, A."], year=2020)}
    r = replace_inline_citations("[a2020; ghost2099]", lib)
    assert r.text == "[a2020; ghost2099]"
    assert r.unknown_keys == ["ghost2099"] and r.replaced_groups == 0


def test_nested_brackets_not_harmed():
    lib = {"x2020": _en("x2020", ["Xu, X."], year=2020)}
    r = replace_inline_citations("嵌套 [[x2020]] 与普通 [x2020]。", lib)
    assert "[[x2020]]" in r.text          # 嵌套组不替换
    assert "(Xu, 2020)" in r.text     # 普通组正常替换


def test_markdown_link_text_untouched_when_unknown():
    lib = {"k2020": _en("k2020", ["Kay, K."], year=2020)}
    r = replace_inline_citations("见 [官方文档](https://example.com) 与 [k2020]。", lib)
    assert "[官方文档](https://example.com)" in r.text
    assert "(Kay, 2020)" in r.text


def test_literature_manager_object_supported():
    m = LiteratureManager()
    m.add_entry(_cn("温忠麟2014", ["温忠麟", "叶宝娟"]))
    m.add_entry(_en("smith2020", ["Smith, J. A."], year=2020))
    r = replace_inline_citations("[温忠麟2014; smith2020]", m)
    assert r.text == "(温忠麟与叶宝娟, 2014; Smith, 2020)"


def test_text_without_citations_unchanged():
    lib = {"k2020": _en("k2020", ["Kay, K."], year=2020)}
    src = "没有任何引用的正文，含 (括号) 与 [脚注] 样式。"
    r = replace_inline_citations(src, lib)
    assert r.text == src and r.replaced_groups == 0 and r.unknown_keys == ["脚注"]


def test_result_is_dataclass_with_diagnostics():
    lib = {}
    r = replace_inline_citations("[ghost]", lib)
    assert isinstance(r, InTextCitationResult)
    assert r.text == "[ghost]" and r.replaced_groups == 0 and "ghost" in r.unknown_keys
