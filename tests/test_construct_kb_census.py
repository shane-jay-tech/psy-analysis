# -*- coding: utf-8 -*-
"""src/questionnaire/construct_kb.py::CONSTRUCTS 全量普查钉桩（s920-12）。

锚点（实测仍成立）：`:13 CONSTRUCTS = {`，模块 1199 行数据。现测只查到 5 个构念
（`test_construct_kb_io_seed.py` 点组织承诺/工作-家庭冲突/组织公民行为/家长式领导，
`test_demo_datasets_hr.py` 点工作满意度）⇒ 其余 46 个的结构从未被钉过。

**只数形状，不评内容**：条数、字段完备率、维度结构、量表/文献条数区间——全部按 2026-09-20 磁盘实况精确计数。
不判断任何构念定义的学术正确性、不碰统计数值结论；新增/删改构念会让这些数字变红，这是刻意的门禁。
"""
import collections

from src.questionnaire.construct_kb import CONSTRUCTS

TOTAL = 51
FIELD_SET = {"name_zh", "name_en", "domain", "definition", "dimensions",
             "typical_scale", "established_scales", "references"}
DIM_FIELD_SET = {"name", "desc", "item_count", "example"}
DIM_TOTAL = 155
ITEM_COUNT_TOTAL = 732
SCALE_TOTAL = 98
REFERENCE_TOTAL = 80


def test_registry_has_exactly_51_constructs_keyed_by_their_own_chinese_name():
    assert len(CONSTRUCTS) == TOTAL
    assert len(set(CONSTRUCTS)) == TOTAL                      # 键不重复（dict 天然，但顺序/命名靠这条兜）
    assert all(k == v["name_zh"] for k, v in CONSTRUCTS.items())  # 键 == name_zh，没有别名键


def test_every_construct_carries_all_eight_fields_no_partial_entry():
    shapes = {frozenset(v) for v in CONSTRUCTS.values()}

    assert shapes == {frozenset(FIELD_SET)}                   # 完备率 51/51 = 100%，无缺键也无自造键


def test_domain_labels_are_nine_including_two_near_duplicate_pairs():
    """现状：域标签 9 个，其中「社会心理学/社会心理」「认知心理学/认知」是同一域的两种写法。只钉不改。"""
    counts = collections.Counter(v["domain"] for v in CONSTRUCTS.values())

    assert dict(counts) == {
        "组织行为": 16, "临床与健康": 8, "发展心理学": 8, "社会心理学": 7, "认知心理学": 5,
        "人格": 2, "社会心理": 2, "教育心理": 2, "认知": 1,
    }
    assert sum(counts.values()) == TOTAL
    assert {"社会心理", "认知"} <= set(counts)                 # 短标签还在，别顺手"规范化"掉


def test_dimension_structure_is_uniform_four_key_dicts():
    dims = [d for v in CONSTRUCTS.values() for d in v["dimensions"]]

    assert len(dims) == DIM_TOTAL
    assert {frozenset(d) for d in dims} == {frozenset(DIM_FIELD_SET)}
    assert all(isinstance(d["item_count"], int) and d["item_count"] > 0 for d in dims)
    assert sum(d["item_count"] for d in dims) == ITEM_COUNT_TOTAL
    assert all(str(d["desc"]).strip() and str(d["example"]).strip() and str(d["name"]).strip() for d in dims)
    per = [len(v["dimensions"]) for v in CONSTRUCTS.values()]
    assert (min(per), max(per)) == (2, 6) and 0 not in per    # 没有零维度构念


def test_module_docstring_still_admits_only_three_dimension_keys():
    """文档漂移钉桩：`dimensions` 实为四键（多 `example`），模块 docstring 还写三键。"""
    import src.questionnaire.construct_kb as kb_mod

    assert "{name, desc, item_count}" in kb_mod.__doc__
    assert "example" not in kb_mod.__doc__


def test_established_scales_and_references_are_non_empty_string_lists():
    scales = [s for v in CONSTRUCTS.values() for s in v["established_scales"]]
    refs = [r for v in CONSTRUCTS.values() for r in v["references"]]

    assert (len(scales), len(refs)) == (SCALE_TOTAL, REFERENCE_TOTAL)
    assert all(isinstance(s, str) and s.strip() for s in scales + refs)
    n_scale = [len(v["established_scales"]) for v in CONSTRUCTS.values()]
    n_ref = [len(v["references"]) for v in CONSTRUCTS.values()]
    assert (min(n_scale), max(n_scale)) == (1, 4)
    assert (min(n_ref), max(n_ref)) == (1, 3)                # 没有"零文献"构念


def test_typical_scale_and_definition_are_all_filled_prose():
    assert all(isinstance(v["typical_scale"], str) and v["typical_scale"].strip() for v in CONSTRUCTS.values())
    lens = [len(v["definition"]) for v in CONSTRUCTS.values()]

    assert min(lens) >= 78                                    # 最短一条 78 字，不是占位符
    assert max(lens) <= 174


def test_english_name_work_engagement_is_shared_by_exactly_two_constructs():
    """现状：`工作投入` 与 `员工敬业度` 共用 name_en="Work Engagement"（两条不同构念，都引 UWES）。
    按英文名反查会撞车——只钉不改。"""
    by_en = collections.Counter(v["name_en"] for v in CONSTRUCTS.values())
    dupes = {k for k, c in by_en.items() if c > 1}

    assert dupes == {"Work Engagement"}
    assert sorted(k for k, v in CONSTRUCTS.items() if v["name_en"] == "Work Engagement") == sorted(
        ["工作投入", "员工敬业度"])
    assert len(by_en) == TOTAL - 1                            # 唯一重复就这一处


def test_registry_is_a_plain_module_dict_shared_with_every_importer():
    """普查口径说明：`CONSTRUCTS` 是模块级可变 dict，`from ... import` 拿到的是同一个对象。
    本文件因此**只读**——任何就地改写都会串到同一次 pytest 会话里的其它测（不在此处演示破坏）。"""
    import src.questionnaire.construct_kb as kb_mod

    assert CONSTRUCTS is kb_mod.CONSTRUCTS and type(CONSTRUCTS) is dict
