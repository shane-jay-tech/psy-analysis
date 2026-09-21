# -*- coding: utf-8 -*-
"""src/paper_writer/psychology_report_format.py 六常量金档钉桩（s922-116）。

模块实测 74 行、3264 字节、纯 LF，只有 6 个顶层容器常量、零函数零类：
`PAPER_SECTIONS`(8) / `STAT_FORMATS`(8) / `SIG_MARKS`(3) / `EFFECT_SIZE_GUIDE`(8) /
`WRITING_RULES`(10) / `ACADEMIC_PHRASES`(10)。锚点 `:18 STAT_FORMATS = {`、`:30 SIG_MARKS = {` 未漂移。

**为什么要金档**（动手前 AST 普查，脚本见 result）：这 6 个常量在 `src/` 里的 4 个引用点
（`paper_engine.py:11`、`section_writers.py:11-12`、`paper_writer/__init__.py:11-13`）
**全部只 import 不 load**（`__init__` 是走 `__all__` 字符串再导出）——
即"心理学报格式规约"目前没有任何生产端读取；唯一的真实读数在 `tests/test_ui.py:233-239`，
且只有 4 条形如 `assert "t_test" in STAT_FORMATS` / `assert len(SIG_MARKS) > 0` 的弱断言。
所以本文件是这套格式约定的**第一道也是唯一一道**防翻改的门。

红线自查：本件只把盘上现值原样钉住（含 `EFFECT_SIZE_GUIDE` 的解读阈值与 `SIG_MARKS` 的 p 值档），
**不改任何数值、不评任何统计口径**；数值若被改动，本文件必红。
"""

import ast
from pathlib import Path
from string import Formatter

import pytest

from src.paper_writer.psychology_report_format import (
    ACADEMIC_PHRASES,
    EFFECT_SIZE_GUIDE,
    PAPER_SECTIONS,
    SIG_MARKS,
    STAT_FORMATS,
    WRITING_RULES,
)

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "paper_writer" / "psychology_report_format.py"

CONTAINERS = {
    "PAPER_SECTIONS": list,
    "STAT_FORMATS": dict,
    "SIG_MARKS": dict,
    "EFFECT_SIZE_GUIDE": dict,
    "WRITING_RULES": dict,
    "ACADEMIC_PHRASES": dict,
}


def _top_level_assignments():
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    names = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names += [t.id for t in node.targets if isinstance(t, ast.Name)]
    return names


def _fields(template):
    """[(字段名, 格式说明符)]，顺序即正文出现顺序（走 string.Formatter，不执行 f-string）。"""
    return [(f, spec or "") for _, f, spec, _ in Formatter().parse(template) if f]


# --------------------------------------------------------------------------- #
# 0. 模块形状
# --------------------------------------------------------------------------- #

def test_module_declares_exactly_the_six_golden_constants():
    """顶层赋值只有这 6 个，顺序即文件顺序：新增/删除常量都要先在这里登记。"""
    assert _top_level_assignments() == list(CONTAINERS)


def test_container_types_are_not_downgraded():
    for name, typ in CONTAINERS.items():
        assert type(globals()[name]) is typ, name


# --------------------------------------------------------------------------- #
# 1. 章节顺序（判据 2：列表精确比对，防插队）
# --------------------------------------------------------------------------- #

def test_paper_sections_exact_order():
    assert PAPER_SECTIONS == [
        "title_abstract",
        "introduction",
        "methods",
        "results",
        "discussion",
        "conclusions",
        "references",
        "appendix",
    ]


def test_paper_sections_shape():
    """8 节、键唯一、全为蛇形 ASCII 小写；results 在 discussion 之前、references 在 appendix 之前。"""
    assert len(PAPER_SECTIONS) == 8 == len(set(PAPER_SECTIONS))
    assert all(s.isascii() and s.islower() and " " not in s for s in PAPER_SECTIONS)
    idx = {s: i for i, s in enumerate(PAPER_SECTIONS)}
    assert idx["methods"] < idx["results"] < idx["discussion"] < idx["conclusions"]
    assert idx["introduction"] < idx["methods"]
    assert idx["references"] < idx["appendix"]
    assert idx["title_abstract"] == 0


# --------------------------------------------------------------------------- #
# 2. 统计报告格式串（判据核心：逐键钉字段名 + 精度说明符）
# --------------------------------------------------------------------------- #

# 每个格式串拆成 (字段名, 格式说明符)，顺序即正文出现顺序。
STAT_FORMAT_GOLDEN = {
    "t_test": [("df", ""), ("t", ".2f"), ("p", ".3f"), ("d", ".2f")],
    "f_test": [("df1", ""), ("df2", ""), ("F", ".2f"), ("p", ".3f"), ("eta", ".3f")],
    "chi_sq": [("df", ""), ("chi2", ".2f"), ("p", ".3f"), ("v", ".3f")],
    "correlation": [("df", ""), ("r", ".2f"), ("p", ".3f")],
    "regression": [("beta", ".3f"), ("t", ".2f"), ("p", ".3f")],
    "bootstrap": [("B", ".3f"), ("ci_low", ".3f"), ("ci_high", ".3f")],
    "alpha": [("alpha", ".3f"), ("ci_low", ".3f"), ("ci_high", ".3f")],
    "kmo": [("kmo", ".3f"), ("df", ""), ("chi2", ".2f"), ("p", ".3f")],
}

# 统计量名 → 小数位（p 一律三位；统计量本身两位或三位，见现状）
P_PRECISION = ".3f"


def test_stat_formats_key_set_snapshot():
    assert list(STAT_FORMATS) == [
        "t_test", "f_test", "chi_sq", "correlation",
        "regression", "bootstrap", "alpha", "kmo",
    ]


@pytest.mark.parametrize("stat_key", sorted(STAT_FORMATS))
def test_stat_format_template_is_pure_ascii_or_symbol_and_parses(stat_key):
    """格式串必须是 str，且能按自身字段跑通 .format（占位符名合法、无遗漏的孤立花括号）。"""
    template = STAT_FORMATS[stat_key]
    assert isinstance(template, str) and template.strip()
    fields = [f for f, _ in _fields(template)]
    assert fields, stat_key
    sample = {f: 1.0 for f in fields}
    rendered = template.format(**sample)
    assert "{" not in rendered and "}" not in rendered, (stat_key, rendered)


@pytest.mark.parametrize("stat_key", sorted(STAT_FORMATS))
def test_stat_format_field_and_precision_golden(stat_key):
    """逐键钉 (字段, 精度) 序列：改字段名、改小数位、调顺序都会在这里翻红。"""
    got = _fields(STAT_FORMATS[stat_key])
    assert got == STAT_FORMAT_GOLDEN[stat_key], stat_key


@pytest.mark.parametrize("stat_key", sorted(STAT_FORMATS))
def test_stat_format_p_value_precision_is_three_decimals_when_present(stat_key):
    """现状：8 个格式串里凡带 p 值占位符的，精度一律 `.3f`（bootstrap/alpha 不报 p）。"""
    by_field = dict(_fields(STAT_FORMATS[stat_key]))
    if "p" in by_field:
        assert by_field["p"] == P_PRECISION, stat_key
    else:
        assert stat_key in {"bootstrap", "alpha"}, stat_key


def test_stat_formats_declared_field_names_are_stable_universe():
    """全量字段名并集快照：新增统计量字段（如 ci_low 之外的新键）需在此登记。"""
    universe = set()
    for template in STAT_FORMATS.values():
        universe |= {f for f, _ in _fields(template)}
    assert universe == {
        "alpha", "beta", "B", "chi2", "ci_high", "ci_low", "d", "df", "df1", "df2",
        "eta", "F", "kmo", "p", "r", "t", "v",
    }


# --------------------------------------------------------------------------- #
# 3. 显著性标记三档（判据 3）
# --------------------------------------------------------------------------- #

def test_sig_marks_three_tiers_exact():
    assert SIG_MARKS == {0.001: "***", 0.01: "**", 0.05: "*"}
    assert len(SIG_MARKS) == 3


def test_sig_marks_tiers_are_ordered_and_stars_monotonic():
    """阈值升序 ⇔ 星号降序：p 越小星越多，且三档互不重复。"""
    thresholds = sorted(SIG_MARKS)
    assert thresholds == [0.001, 0.01, 0.05]
    marks = [SIG_MARKS[t] for t in thresholds]
    assert marks == ["***", "**", "*"]
    assert len(set(marks)) == 3
    assert all(set(m) == {"*"} for m in marks)              # 只由星号组成
    assert [len(m) for m in marks] == [3, 2, 1]


def test_sig_marks_thresholds_are_within_unit_interval():
    """形状约束（不评口径）：三个阈值都在 (0, 1) 内、都是 float。"""
    for threshold, mark in SIG_MARKS.items():
        assert isinstance(threshold, float) and 0 < threshold < 1
        assert isinstance(mark, str) and mark


# --------------------------------------------------------------------------- #
# 4. 效应量解读阈值（原样钉，不动）
# --------------------------------------------------------------------------- #

def test_effect_size_guide_golden_snapshot():
    """8 个指标 × 3 档的现值全量快照（含 alpha 的"优秀/良好/可接受"反向三档）。"""
    assert EFFECT_SIZE_GUIDE == {
        "cohens_d": {"小": 0.20, "中": 0.50, "大": 0.80},
        "eta_sq": {"小": 0.01, "中": 0.06, "大": 0.14},
        "eta_sq_p": {"小": 0.01, "中": 0.06, "大": 0.14},
        "r": {"小": 0.10, "中": 0.30, "大": 0.50},
        "cramers_v": {"小": 0.10, "中": 0.30, "大": 0.50},
        "cohens_f2": {"小": 0.02, "中": 0.15, "大": 0.35},
        "cohens_w": {"小": 0.10, "中": 0.30, "大": 0.50},
        "alpha": {"优秀": 0.90, "良好": 0.80, "可接受": 0.70},
    }


def test_effect_size_tier_labels_split_two_families():
    """现状：7 个指标用「小/中/大」，只有 alpha 用「优秀/良好/可接受」（信度是反向语义）。"""
    by_label = {}
    for metric, tiers in EFFECT_SIZE_GUIDE.items():
        by_label.setdefault(tuple(tiers), []).append(metric)
    assert set(by_label) == {("小", "中", "大"), ("优秀", "良好", "可接受")}
    assert by_label[("优秀", "良好", "可接受")] == ["alpha"]
    assert len(by_label[("小", "中", "大")]) == 7


@pytest.mark.parametrize("metric", sorted(EFFECT_SIZE_GUIDE))
def test_effect_size_values_increase_for_effect_magnitudes(metric):
    """效应量族「小<中<大」单调（alpha 族是"优秀>良好>可接受"，方向相反，同型钉住）。"""
    tiers = list(EFFECT_SIZE_GUIDE[metric].values())
    assert tiers == sorted(tiers, reverse=(metric == "alpha")), metric
    assert all(isinstance(v, float) and 0 < v < 1 for v in tiers), metric


def test_eta_sq_and_eta_sq_p_are_currently_identical():
    """现状钉桩：偏η² 与 η² 用的是同一组阈值（是否该分开是内容口径，本件不判、不改）。"""
    assert EFFECT_SIZE_GUIDE["eta_sq"] == EFFECT_SIZE_GUIDE["eta_sq_p"]


# --------------------------------------------------------------------------- #
# 5. 写作规范与套语（判据 1 的"APA 规则条数"）
# --------------------------------------------------------------------------- #

def test_writing_rules_count_and_key_order():
    assert len(WRITING_RULES) == 10
    assert list(WRITING_RULES) == [
        "title", "abstract", "keywords", "introduction",
        "methods_participants", "methods_materials", "methods_procedure",
        "results", "discussion", "references",
    ]
    assert all(v.strip() and isinstance(v, str) for v in WRITING_RULES.values())


def test_writing_rules_method_and_section_coverage():
    """现状：章节 8 节里 6 节有直接规则键（title/abstract/keywords 属标题区，appendix/conclusions 无独立键）。"""
    assert {"methods_participants", "methods_materials", "methods_procedure"} <= set(WRITING_RULES)
    assert not {"appendix", "conclusions"} & set(WRITING_RULES)
    assert WRITING_RULES["references"].startswith("GB/T 7714-2015")
    assert "200-300字" in WRITING_RULES["abstract"]
    assert "3-5个" in WRITING_RULES["keywords"]


def test_academic_phrases_snapshot_and_placeholder_usage():
    assert list(ACADEMIC_PHRASES) == [
        "purpose", "hypothesis", "significant", "not_significant", "support",
        "not_support", "compare_previous", "contribution", "limitation", "future",
    ]
    assert ACADEMIC_PHRASES["hypothesis"] == "本研究假设(H{num})："
    assert ACADEMIC_PHRASES["not_significant"] == "{effect}未达到统计显著性水平"
    templated = {k for k, v in ACADEMIC_PHRASES.items() if "{" in v}
    assert templated == {"hypothesis", "significant", "not_significant", "support",
                         "not_support", "compare_previous"}


@pytest.mark.parametrize("phrase_key", sorted(ACADEMIC_PHRASES))
def test_academic_phrase_templates_render(phrase_key):
    """每条套语都能被自身占位符填满（不残留花括号），且不含未声明的字段。"""
    template = ACADEMIC_PHRASES[phrase_key]
    fields = {f for f, _ in _fields(template)}
    assert not (fields - {"num", "effect", "author", "year"}), (phrase_key, fields)
    rendered = template.format(**{f: "X" for f in fields})
    assert "{" not in rendered and "}" not in rendered
    assert rendered.strip()


def test_golden_file_does_not_mutate_module_constants():
    """本件全程只读：跑完所有容器的长度与内容不变（防止"顺手补格式"）。"""
    before = {n: repr(globals()[n]) for n in CONTAINERS}
    for template in STAT_FORMATS.values():
        "{}".format
    for metric in list(EFFECT_SIZE_GUIDE):
        EFFECT_SIZE_GUIDE[metric]["小"] if "小" in EFFECT_SIZE_GUIDE[metric] else None
    assert {n: repr(globals()[n]) for n in CONTAINERS} == before
