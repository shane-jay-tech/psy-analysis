"""数据字典（codebook v1）测试：版本、唯一键、冲突清单、按字典拒绝未知字段。

对应信箱单 20260925-120655-d598。本件只读仓库内的字典载体文件，
不写 data/、不碰统计数值口径。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.questionnaire.data_dictionary import (
    CODEBOOK_VERSION,
    NO_VERSION_MARKER,
    Codebook,
    CodebookEntry,
    NonItemField,
    UnknownFieldError,
    codebook_from_items_doc,
    codebook_from_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_SCHEMA = REPO_ROOT / "demo_projects" / "psychology_questionnaire_demo" / "questionnaire_schema.json"


def _entry(var_name="Q1", **kw):
    return CodebookEntry(item_no=var_name, var_name=var_name, **kw)


def _codes(cb):
    return [c.code for c in cb.conflicts()]


# ---------------- 版本 ----------------

def test_dictionary_carries_version():
    assert CODEBOOK_VERSION == "psy-analysis/codebook/v1"
    assert Codebook().version == CODEBOOK_VERSION


def test_schema_without_version_is_not_fabricated():
    cb = codebook_from_schema({"dimensions": []})
    assert cb.version == NO_VERSION_MARKER
    assert "E_VERSION" in _codes(cb)


def test_explicit_version_silences_the_version_conflict():
    cb = codebook_from_schema({"dimensions": []}, version=CODEBOOK_VERSION)
    assert "E_VERSION" not in _codes(cb)


# ---------------- 唯一键 ----------------

def test_item_no_and_var_name_are_unique_keys():
    cb = Codebook(entries=[_entry("Q1"), _entry("Q1")])
    conflicts = cb.conflicts()
    dup = [c for c in conflicts if c.code == "E_DUP_KEY"]
    assert len(dup) == 2  # item_no 与 var_name 各报一次
    assert {c.keys[0] for c in dup} == {"Q1"}


def test_same_var_name_in_two_dimensions_is_a_conflict():
    cb = Codebook(entries=[
        _entry("Q3", dimension="焦虑"),
        _entry("Q3", dimension="自尊"),
    ])
    assert "E_MULTI_DIM" in _codes(cb)


def test_var_name_cannot_be_item_and_non_item_at_once():
    cb = Codebook(
        entries=[_entry("gender")],
        non_item_fields=[NonItemField("gender", "demographic")],
    )
    assert "E_ROLE_CLASH" in _codes(cb)


# ---------------- 量尺 / 反向题 / 缺失值编码 ----------------

def test_reversed_scale_order_is_a_conflict():
    cb = Codebook(entries=[_entry("Q1", scale_min=5, scale_max=1)])
    assert "E_SCALE_RANGE" in _codes(cb)


def test_missing_code_inside_scale_range_is_ambiguous():
    cb = Codebook(entries=[_entry("Q1", scale_min=1, scale_max=5, missing_codes=("3",))])
    assert "E_MISSING_AMBIGUOUS" in _codes(cb)


def test_missing_code_outside_scale_range_is_clean():
    cb = Codebook(entries=[_entry("Q1", scale_min=1, scale_max=5, missing_codes=("-999",))])
    assert cb.conflicts() == []


def test_missing_codes_are_reported_not_rewritten():
    cb = Codebook(entries=[_entry("Q1", scale_min=1, scale_max=5, missing_codes=("-999",))])
    df = pd.DataFrame({"Q1": ["1", "-999", "-999", "5"]})
    before = df.copy(deep=True)
    hits = cb.find_missing_code_hits(df)
    assert hits == {"Q1": {"-999": 2}}
    assert df.equals(before), "字典只报告缺失值编码命中，不得改写取值"


def test_reverse_item_written_as_bool_only():
    """反向题在字典里只有一种书写：bool（不再是"下标"或"列名"两套）。"""
    cb = Codebook(entries=[_entry("Q1", reverse=True), _entry("Q2")])
    assert [e.reverse for e in cb.entries] == [True, False]


# ---------------- 未知字段拒绝 ----------------

def test_unknown_fields_are_listed():
    cb = Codebook(entries=[_entry("Q1"), _entry("Q2")],
                  non_item_fields=[NonItemField("性别", "demographic")])
    assert cb.find_unknown_fields(["Q1", "Q2", "性别", "神秘列"]) == ["神秘列"]


def test_import_rejects_unknown_field_by_default():
    cb = Codebook(entries=[_entry("Q1")])
    df = pd.DataFrame({"Q1": [1, 2], "totally_unknown_field_xyz": ["a", "b"]})
    with pytest.raises(UnknownFieldError) as exc:
        cb.reject_unknown_fields(df)
    assert exc.value.unknown_fields == ["totally_unknown_field_xyz"]
    assert CODEBOOK_VERSION in str(exc.value)


def test_report_policy_keeps_row_count_and_lists_unknown():
    cb = Codebook(entries=[_entry("Q1")], unknown_field_policy="report")
    df = pd.DataFrame({"Q1": [1, 2, 3], "extra": [4, 5, 6]})
    kept, unknown = cb.reject_unknown_fields(df)
    assert unknown == ["extra"]
    assert list(kept.columns) == ["Q1"]
    assert len(kept) == len(df) == 3, "拒绝未知字段只作用于列面，不得改动行数"
    assert kept["Q1"].tolist() == [1, 2, 3]


def test_strict_flag_overrides_policy():
    cb = Codebook(entries=[_entry("Q1")], unknown_field_policy="report")
    df = pd.DataFrame({"Q1": [1], "extra": [2]})
    with pytest.raises(UnknownFieldError):
        cb.reject_unknown_fields(df, strict=True)


def test_clean_import_passes_without_error():
    cb = Codebook(entries=[_entry("Q1"), _entry("Q2")],
                  non_item_fields=[NonItemField("序号", "metadata")])
    df = pd.DataFrame({"序号": [1], "Q1": [4], "Q2": [2]})
    kept, unknown = cb.reject_unknown_fields(df)
    assert unknown == [] and list(kept.columns) == ["序号", "Q1", "Q2"]


# ---------------- 现存载体适配 ----------------

def test_existing_demo_schema_loads_and_is_conflict_free():
    """现存最像"字典"的载体：demo 的 questionnaire_schema.json（git 跟踪件，缺件即红）。"""
    assert DEMO_SCHEMA.exists(), f"字典载体被改名或删除：{DEMO_SCHEMA}"
    schema = json.loads(DEMO_SCHEMA.read_text(encoding="utf-8"))
    cb = codebook_from_schema(schema, version=CODEBOOK_VERSION)
    assert len(cb.entries) == 10
    assert [e.var_name for e in cb.entries][:2] == ["Q1", "Q2"]
    assert {e.var_name for e in cb.entries if e.reverse} == {"Q3", "Q8", "Q9"}
    assert cb.conflicts() == []
    df = pd.DataFrame({**{f"Q{i}": [1] for i in range(1, 11)},
                       "gender": ["男"], "grade": ["大一"], "id": [1],
                       "duration_seconds": [70]})
    assert cb.find_unknown_fields(df.columns) == []


def test_items_doc_reverse_indices_are_converted_to_var_names():
    """ItemsDoc 用 0 基下标、ScaleDimension 用列名 ⇒ 适配器负责换算，字典面只剩 bool。"""

    class _Doc:
        title = "探针卷"
        items = ["我很快乐", "我常常想哭"]
        reverse_indices = [1]

    cb = codebook_from_items_doc(_Doc())
    assert [(e.item_no, e.reverse) for e in cb.entries] == [("Q1", False), ("Q2", True)]
    assert cb.entries[1].label == "我常常想哭"
