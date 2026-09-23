"""src/experiment_design/experiment_templates.py 模板库现状钉桩（s922-113）。

动手前实测：`grep -rIn experiment_templates tests/` 命中 0 行 —— 这个 9 模板、551 行的
范式库此前完全无测试面。本文件只做**现状快照**（纯函数、离线、不桩任何外部服务），
不改任何评分权重、排序口径或模板内容。

钉桩面：
1. TEMPLATES 全量键集快照 + 每个模板的 dataclass schema 完整性；
2. 因子表（typical_ivs / typical_dvs）的条目形状与「因子数 vs 条件数口径」一致性；
3. get_template 命中 / 未命中；
4. list_templates 全量概要（含 description 的截断行为）；
5. recommend_template 的关键词命中排序、并列打破规则、零命中回退。

⚠ 与任务书措辞的差异（按磁盘实况修正，理由同时登记在 result）：
- 任务书写「每模板必含 id/name/paradigm 字段」——``DesignTemplate`` **没有 paradigm 字段**
  （实测 dataclass 字段共 15 个，见 SCHEMA_FIELDS 快照）。承担"范式"语义的是
  ``design_type``（between_subjects / within_subjects / mixed / survey）与 ``category``，
  故此处按真实 schema 钉，不虚构 paradigm 断言。
- 「因子数一致性」在现库上只**单向**成立：多因素模板都不写"个水平"（成立），
  但单因素模板也可能不写（iat 写的是「7个Block（5类任务）」）。故只钉成立的那个方向。
"""

import dataclasses
from dataclasses import fields

import pytest

from src.experiment_design import experiment_templates as et
from src.experiment_design.experiment_templates import (
    TEMPLATES,
    DesignTemplate,
    get_template,
    list_templates,
    recommend_template,
)

# --------------------------------------------------------------------------- #
# 现状快照（06:0x @HEAD e5850b0 实测取数，脚本见 result 的「证据」节）
# --------------------------------------------------------------------------- #

EXPECTED_TEMPLATE_IDS = [
    "between_subjects_single",
    "within_subjects_single",
    "factorial_between",
    "mixed_design",
    "survey_correlational",
    "emotion_induction",
    "intervention_study",
    "priming_experiment",
    "iat",
]

SCHEMA_FIELDS = [
    "id", "name", "category", "design_type", "description",
    "typical_ivs", "typical_dvs", "n_conditions_range", "duration_range",
    "sample_size_hint", "design_diagram", "key_considerations",
    "control_vars", "analysis_plan", "references",
]

STR_FIELDS = [f for f in SCHEMA_FIELDS if f not in {
    "typical_ivs", "typical_dvs", "key_considerations", "control_vars",
    "analysis_plan", "references",
}]
LIST_FIELDS = [f for f in SCHEMA_FIELDS if f not in STR_FIELDS]

# DesignTemplate 的 docstring/注释声明的四种设计类型（experiment_templates.py:16）
ALLOWED_DESIGN_TYPES = {"between_subjects", "within_subjects", "mixed", "survey"}

# 实测因子数（len(typical_ivs)）——新模板若与条件数口径冲突会被下方一致性用例拦下
FACTORS = {
    "between_subjects_single": 1, "within_subjects_single": 1, "iat": 1,
    "factorial_between": 2, "mixed_design": 2, "survey_correlational": 2,
    "emotion_induction": 2, "intervention_study": 2, "priming_experiment": 2,
}

TEMPLATE_IDS = list(TEMPLATES)          # 参数化用：新增模板自动进入逐模板用例


# --------------------------------------------------------------------------- #
# 1. 全量结构快照
# --------------------------------------------------------------------------- #

def test_templates_key_set_snapshot():
    """键集与键数都是现状：新增/删除模板必须显式更新快照（与参数化用例联动）。"""
    assert list(TEMPLATES) == EXPECTED_TEMPLATE_IDS
    assert len(TEMPLATES) == 9


def test_sweep_case_count_tracks_template_count():
    """「用例数与 TEMPLATES 键数联动」的自证：参数化表始终覆盖全量键。"""
    assert len(TEMPLATE_IDS) == len(TEMPLATES)
    assert set(TEMPLATE_IDS) == set(TEMPLATES)


def test_all_values_are_design_template_instances():
    assert all(isinstance(t, DesignTemplate) for t in TEMPLATES.values())


def test_dataclass_field_snapshot():
    """schema 快照：动字段（增/删/改名）会红，防止悄悄改形状。"""
    assert [f.name for f in fields(DesignTemplate)] == SCHEMA_FIELDS


# --------------------------------------------------------------------------- #
# 2. 逐模板 schema 完整性（参数化遍历，新模板自动纳入）
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_template_id_matches_dict_key(tid):
    assert TEMPLATES[tid].id == tid


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_required_str_fields_non_empty(tid):
    """任务书要求的 id/name 必含；此处按盘上真实必填字段全量钉（无 paradigm 字段）。"""
    tmpl = TEMPLATES[tid]
    for name in SCHEMA_FIELDS:
        value = getattr(tmpl, name)
        if name in STR_FIELDS:
            assert isinstance(value, str), (tid, name)
            assert value.strip(), (tid, name)
    assert tmpl.name != tmpl.category


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_list_fields_are_non_empty_str_lists(tid):
    """四个"文字清单"字段必为非空字符串列表；两张因子表另见 shape 用例。"""
    tmpl = TEMPLATES[tid]
    for name in ("key_considerations", "control_vars", "analysis_plan", "references"):
        value = getattr(tmpl, name)
        assert isinstance(value, list) and value, (tid, name)
        assert all(isinstance(item, str) and item.strip() for item in value), (tid, name)
    for name in ("typical_ivs", "typical_dvs"):
        value = getattr(tmpl, name)
        assert isinstance(value, list) and value, (tid, name)
        assert all(isinstance(item, dict) and item for item in value), (tid, name)


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_design_type_in_declared_domain(tid):
    assert TEMPLATES[tid].design_type in ALLOWED_DESIGN_TYPES


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_factor_lists_shape(tid):
    """typical_ivs / typical_dvs 条目形状：name+levels+example 齐，DV 必带 measure。"""
    tmpl = TEMPLATES[tid]
    assert len(tmpl.typical_ivs) >= 1
    assert len(tmpl.typical_dvs) >= 1
    for iv in tmpl.typical_ivs:
        assert {"name", "levels", "example"} <= set(iv), (tid, iv)
        assert all(str(v).strip() for v in iv.values()), (tid, iv)
    for dv in tmpl.typical_dvs:
        assert set(dv) == {"name", "measure"}, (tid, dv)
        assert dv["name"].strip() and dv["measure"].strip(), (tid, dv)


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_iv_count_snapshot(tid):
    assert len(TEMPLATES[tid].typical_ivs) == FACTORS[tid]


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_single_factor_only_templates_declare_manipulation(tid):
    """现状：manipulation 这个 IV 子字段只有两个单因素模板写了（7/9 未写）。

    钉成「有 manipulation ⟺ 单因素」的方向，新模板漏写操作定义即红。
    """
    tmpl = TEMPLATES[tid]
    has_manip = all("manipulation" in iv for iv in tmpl.typical_ivs)
    if has_manip:
        assert len(tmpl.typical_ivs) == 1, tid
        assert all(str(iv["manipulation"]).strip() for iv in tmpl.typical_ivs), tid
    else:
        assert all("manipulation" not in iv for iv in tmpl.typical_ivs), tid


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_condition_range_consistent_with_factor_count(tid):
    """因子数一致性的**单向**口径（现库实测）：
    - 多因素（≥2 IV）模板的条件数绝不写成单因素"个水平"口径；
    - 条件数里出现"×"（交叉设计）的模板必为多因素。
    反向不成立（iat 是单因素但不写"个水平"），故不钉反向。
    """
    tmpl = TEMPLATES[tid]
    n_factors = len(tmpl.typical_ivs)
    if n_factors >= 2:
        assert "个水平" not in tmpl.n_conditions_range, (tid, tmpl.n_conditions_range)
    if "×" in tmpl.n_conditions_range:
        assert n_factors >= 2, (tid, tmpl.n_conditions_range)


def test_categories_grouping_snapshot():
    """5 个 category 取值与每模板归属为现状（category 是 CATEGORIES 之外的自由标签）。"""
    assert {t.category for t in TEMPLATES.values()} == {
        "基础实验设计", "进阶实验设计", "非实验设计", "特定范式", "应用研究",
    }
    assert {tid: TEMPLATES[tid].category for tid in TEMPLATE_IDS} == {
        "between_subjects_single": "基础实验设计",
        "within_subjects_single": "基础实验设计",
        "factorial_between": "进阶实验设计",
        "mixed_design": "进阶实验设计",
        "survey_correlational": "非实验设计",
        "emotion_induction": "特定范式",
        "intervention_study": "应用研究",
        "priming_experiment": "特定范式",
        "iat": "特定范式",
    }


def test_design_type_distribution_snapshot():
    dist = {}
    for t in TEMPLATES.values():
        dist[t.design_type] = dist.get(t.design_type, 0) + 1
    assert dist == {
        "between_subjects": 3, "within_subjects": 3, "mixed": 2, "survey": 1,
    }


# --------------------------------------------------------------------------- #
# 3. get_template
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_get_template_hit(tid):
    got = get_template(tid)
    assert got is TEMPLATES[tid]


def test_get_template_miss_returns_none():
    assert get_template("no_such_template") is None
    assert get_template("") is None
    # 大小写敏感（现状）：键都是小写蛇形，传大写形态取不到
    assert get_template("IAT") is None


# --------------------------------------------------------------------------- #
# 4. list_templates
# --------------------------------------------------------------------------- #

def test_list_templates_covers_all():
    rows = list_templates()
    assert isinstance(rows, list)
    assert [r["id"] for r in rows] == EXPECTED_TEMPLATE_IDS     # 保序，非排序


def test_list_templates_row_shape():
    rows = list_templates()
    for tid, row in zip(TEMPLATE_IDS, rows):
        tmpl = TEMPLATES[tid]
        assert set(row) == {"id", "name", "category", "design_type", "description"}
        assert row["name"] == tmpl.name
        assert row["category"] == tmpl.category
        assert row["design_type"] == tmpl.design_type
        # 现状：恒为「前 80 字 + 省略号」，短描述（现库 9 个里 6 个 <80 字）也被加省略号
        assert row["description"] == tmpl.description[:80] + "..."
        assert row["description"].endswith("...")


def test_list_templates_returns_fresh_objects():
    a, b = list_templates(), list_templates()
    assert a == b and a is not b


# --------------------------------------------------------------------------- #
# 5. recommend_template：排序 / 回退（实测取数，权重未动）
# --------------------------------------------------------------------------- #

# (topic, keywords, 期望返回的模板 id 序列) —— 全部来自 HEAD e5850b0 的真实运行读数
# 例外：索引 4（"IAT 效应"）于 2026-09-23 由 s923-27 重新取数——
# 该行的旧读数钉的是 recommend_template 里 `"IAT"` 字面量与 all_text 降纲不同源的**死码现状**，
# 字面量对齐为小写后读数由 ["between_subjects_single"] 变为 ["iat"]，属**预期翻正**而非回归。
RECOMMEND_CASES = [
    ("", [], ["between_subjects_single"]),
    ("压力与情绪", [], ["emotion_induction"]),
    ("情绪诱发", ["情绪"], ["emotion_induction"]),
    ("内隐联想", ["IAT"], ["iat"]),
    ("IAT 效应", [], ["iat"]),
    ("问卷调查研究", ["问卷"], ["survey_correlational"]),
    ("认知干预效果", ["干预"], ["intervention_study"]),
    ("启动", ["启动"], ["priming_experiment"]),
    ("两因素交互作用", ["交互"], ["factorial_between", "mixed_design"]),
    ("被试内反应时", ["被试内"], ["within_subjects_single", "mixed_design"]),
    ("中介作用问卷", ["中介"], ["survey_correlational", "factorial_between", "mixed_design"]),
    ("情绪", ["情绪", "问卷", "干预"], ["survey_correlational", "emotion_induction", "intervention_study"]),
]


@pytest.mark.parametrize("topic,keywords,expected", RECOMMEND_CASES)
def test_recommend_snapshot(topic, keywords, expected):
    got = recommend_template(topic, keywords)
    assert [t.id for t in got] == expected


def test_recommend_empty_falls_back_to_between_subjects():
    """空关键词 + 空主题 → 回退默认模板（单元素）。"""
    got = recommend_template("", [])
    assert [t.id for t in got] == ["between_subjects_single"]


def test_recommend_no_hit_falls_back_too():
    got = recommend_template("完全无关的topic", ["不存在的关键词xyz"])
    assert [t.id for t in got] == ["between_subjects_single"]


def test_recommend_never_exceeds_three_and_is_unique():
    probes = [
        ("", []), ("情绪", ["情绪", "问卷", "干预", "内隐", "启动", "交互", "被试内"]),
        ("问卷", ["问卷"]), ("脑电", ["脑电"]), ("态度", ["态度"]),
    ]
    for topic, kws in probes:
        got = recommend_template(topic, kws)
        assert 1 <= len(got) <= 3, (topic, kws)
        assert len({t.id for t in got}) == len(got), (topic, kws)
        assert all(isinstance(t, DesignTemplate) for t in got)


def test_recommend_ties_broken_by_template_insertion_order():
    """并列时按 TEMPLATES 的插入顺序（sorted 稳定性）打破——现库 factorial 插在 mixed 之前。"""
    got = recommend_template("两因素交互作用", ["交互"])
    assert [t.id for t in got] == ["factorial_between", "mixed_design"]
    assert TEMPLATE_IDS.index("factorial_between") < TEMPLATE_IDS.index("mixed_design")


def test_recommend_keyword_match_is_case_insensitive():
    """关键词与模板正文都 lower() 后再比：大小写两种写法同解。"""
    assert [t.id for t in recommend_template("内隐联想", ["IAT"])] == \
           [t.id for t in recommend_template("内隐联想", ["iat"])]


def test_recommend_uppercase_iat_topic_gets_iat_boost():
    """正断言（s923-27 翻正，此前该用例钉的是**在册死码现状**）：纯大写 IAT 主题能拿到 iat 加分。

    背景：`recommend_template` 在 :503-505 把 all_text 统一 `lower()` 降纲，而 :531 的
    关键词表原样写的是大写 `"IAT"` ⇒ 那枚字面量**永不命中**，分支只能被 "内隐" / "态度"
    触发，纯大写 IAT 主题（无中文线索）会掉进默认回退。s923-27 把字面量改为小写 `"iat"`
    对齐降纲口径后，本用例从「钉现状」翻正为「钉设计意图」：

    - 纯大写 IAT 主题 → `["iat"]`（此前是 `["between_subjects_single"]`）；
    - 大小写两种写法结果相同 ⇒ 加分不依赖主题恰好写成小写；
    - 中文线索那条路径行为不变（保留原用例的第二条断言）。

    与 `src/experiment_design/experiment_templates.py:531` 那一枚字面量是**一体两笔**，
    拆开提交则本文件必红。
    """
    assert [t.id for t in recommend_template("IAT 效应", [])] == ["iat"]
    assert [t.id for t in recommend_template("iat 效应", [])] == ["iat"]
    assert [t.id for t in recommend_template("IAT效应", ["IAT"])] == ["iat"]
    # 中文线索分支未受影响
    assert recommend_template("内隐 IAT 效应", [])[0].id == "iat"


def test_recommend_topic_substring_can_trigger_survey_boost():
    """在册现状（只钉不改）：主题里的**任意子串**都能触发类别加分。

    "毫不相关的量子隧穿" 命中 "相关" ⇒ survey_correlational +5，与"量子"这个关键词无关。
    """
    assert recommend_template("毫不相关的量子隧穿", ["量子"])[0].id == "survey_correlational"
    assert recommend_template("毫不相关", [])[0].id == "survey_correlational"


def test_recommend_does_not_mutate_template_lib():
    asdict = dataclasses.asdict
    before = {tid: asdict(t) for tid, t in TEMPLATES.items()}
    recommend_template("情绪与干预", ["情绪", "干预", "问卷"])
    list_templates()
    get_template("iat")
    assert {tid: asdict(t) for tid, t in TEMPLATES.items()} == before
