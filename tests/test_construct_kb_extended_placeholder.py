# -*- coding: utf-8 -*-
"""src/questionnaire/construct_kb_extended.py 空占位钉桩（s922-115）。

锚点实测未漂移：该模块 7 行、347 字节、纯 LF，`:7 EXTENDED_CONSTRUCTS = {}` 是全文件唯一语句。
动手前 `grep -rIn construct_kb_extended tests/` 在 tests/ 里零命中。

**为什么钉一个空 dict**（不是凑数用例）：

1. 它是**活的**合并面，不是死码。`academic_literature.py:65`、`design_engine.py:213`、`design_engine.py:232`
   三处都在做 `{**CONSTRUCTS, **EXTENDED_CONSTRUCTS}`——EXTENDED 侧在**合并方向上赢**，
   所以一旦有人往里塞与内置 51 条同名的键，就是**静默覆盖内置构念**。本件用
   `test_no_key_collision_with_builtin_constructs` 把这条挡住。
2. `upstream/topic_funnel.py:245-254` 把这个模块的 import 包在 `except Exception` 里，
   失败只吐一句「构念库加载失败」的降级文案 ⇒ 模块**语法/导入一旦坏掉是静默退化，不是报错**。
   本件因此显式钉可导入性（含 AST 读盘不执行的两项快照）。
3. 扩充它必须同步 **`tests/test_construct_kb_census.py`** 的普查口径：那边钉的是
   「51 条 × 8 字段（name_zh / name_en / domain / definition / dimensions / typical_scale /
   established_scales / references）+ 维度四键（name / desc / item_count / example）」，
   并明写「新增/删改构念会让这些数字变红，这是刻意的门禁」。
   本件的 `test_future_entries_match_census_schema` 就是这条口径在扩展侧的镜像：
   **今天空跑（0 例）＝真空通过**，故另有一条"必须为空"的守卫用例把空态钉住；
   真有人填条目时该参数化会自动开始逐条校验形状。

只数形状，不评内容：不判断任何构念定义的学术正确性，不碰统计数值与研究结论。
"""

import ast
import importlib
from pathlib import Path

import pytest

from src.questionnaire.construct_kb import CONSTRUCTS
from src.questionnaire.construct_kb_extended import EXTENDED_CONSTRUCTS

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "questionnaire" / "construct_kb_extended.py"

# 与 tests/test_construct_kb_census.py 的 FIELD_SET / DIM_FIELD_SET 同一口径（抄，不另造）
CENSUS_FIELD_SET = {"name_zh", "name_en", "domain", "definition", "dimensions",
                    "typical_scale", "established_scales", "references"}
CENSUS_DIM_FIELD_SET = {"name", "desc", "item_count", "example"}
CENSUS_TOTAL = 51          # CONSTRUCTS 现值，由 census 那侧负责把它钉红


def _module():
    return importlib.import_module("src.questionnaire.construct_kb_extended")


def _tree():
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


# --------------------------------------------------------------------------- #
# 1. 可导入性 + 模块形状
# --------------------------------------------------------------------------- #

def test_module_is_importable_and_binding_is_the_shared_dict():
    """可导入性：模块能按顶层名导入，且 `from ... import` 拿到的就是模块级同一个 dict。

    注册表是可变模块级对象（与 census 的 :101 同一口径），本用例**只读**、就地不改。
    """
    mod = _module()
    assert mod.EXTENDED_CONSTRUCTS is EXTENDED_CONSTRUCTS
    assert MODULE_PATH.exists() and MODULE_PATH.suffix == ".py"


def test_module_top_level_ast_is_docstring_plus_single_assignment():
    """AST 读盘不执行：顶层只有「module docstring + 一条赋值」，没有 import / 函数 / 条件分支。

    挡两种漂移：① 悄悄往占位模块里塞代码（它会经由 try/except 的降级面变成静默失效）；
    ② 把赋值换成别的容器类型。
    """
    body = _tree().body
    assert len(body) == 2, [type(s).__name__ for s in body]
    assert isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
    assign = body[1]
    assert isinstance(assign, ast.Assign)
    assert [t.id for t in assign.targets if isinstance(t, ast.Name)] == ["EXTENDED_CONSTRUCTS"]
    assert isinstance(assign.value, ast.Dict) and assign.value.keys == []   # 字面量空 dict
    assert not [n for n in ast.walk(_tree())
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom))]


def test_public_namespace_has_exactly_the_placeholder_binding():
    """模块公开命名空间只有 EXTENDED_CONSTRUCTS（不含 __all__、不再有别的常量）。"""
    public = {n for n in vars(_module()) if not n.startswith("_")}
    assert public == {"EXTENDED_CONSTRUCTS"}


# --------------------------------------------------------------------------- #
# 2. 空态本身
# --------------------------------------------------------------------------- #

def test_extended_constructs_is_an_empty_plain_dict():
    """现状：类型是 dict（不是 Mapping/None/空 list），且 len == 0。"""
    assert type(EXTENDED_CONSTRUCTS) is dict
    assert EXTENDED_CONSTRUCTS == {}
    assert len(EXTENDED_CONSTRUCTS) == 0


def test_merging_with_builtin_constructs_changes_nothing():
    """三处消费端的合并式 `{**CONSTRUCTS, **EXTENDED_CONSTRUCTS}` 现状等价于 CONSTRUCTS 本身。"""
    merged = {**CONSTRUCTS, **EXTENDED_CONSTRUCTS}
    assert len(CONSTRUCTS) == CENSUS_TOTAL
    assert merged == CONSTRUCTS
    assert list(merged) == list(CONSTRUCTS)          # 空扩展不改顺序（下游按序遍历时会可见）


def test_no_key_collision_with_builtin_constructs():
    """扩充时的覆盖守卫：EXTENDED 与 CONSTRUCTS 键集必须互斥。

    键同名即静默覆盖内置构念（`academic_literature.py:65` 等处是 EXTENDED 侧赢），
    所以这条即便今天恒真（空集），明天就是闸门。
    """
    assert set(EXTENDED_CONSTRUCTS) & set(CONSTRUCTS) == set()


@pytest.mark.parametrize("construct_name", sorted(EXTENDED_CONSTRUCTS))
def test_future_entries_match_census_schema(construct_name):
    """任何未来条目都须与 `test_construct_kb_census.py` 的形状口径一致（键 == name_zh、8 字段齐、维度四键）。"""
    entry = EXTENDED_CONSTRUCTS[construct_name]
    assert construct_name == entry["name_zh"]
    assert set(entry) == CENSUS_FIELD_SET
    assert isinstance(entry["dimensions"], list) and entry["dimensions"]
    for dim in entry["dimensions"]:
        assert set(dim) == CENSUS_DIM_FIELD_SET
        assert isinstance(dim["item_count"], int) and dim["item_count"] > 0
    for field in ("established_scales", "references"):
        assert isinstance(entry[field], list)
        assert all(isinstance(x, str) and x.strip() for x in entry[field])


def test_census_schema_case_is_currently_vacuous_by_design():
    """上一条今天是 **1 例 skipped（reason: got empty parameter set）**，不是静默消失。

    这个显式跳过就是"扩展库仍为空"的读数额外证据；真有人填条目而没同步 census 口径时，
    上一条会自动开始逐条校验形状，同时 `tests/test_construct_kb_census.py` 那边的
    TOTAL / DIM_TOTAL 等计数仍是独立的对账面。
    """
    assert sorted(EXTENDED_CONSTRUCTS) == []
