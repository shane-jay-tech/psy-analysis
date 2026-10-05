# -*- coding: utf-8 -*-
"""s923-23：文献综述（LR）`literature_items` 三处脏值入口的现状真值表钉桩。

补的是 `zcode-bridge/done/s922-105-lr-dirty-frozen-pins.result.md` 遗留 2 里点名未覆盖的三处：
① `src/utils/workspace.py:373`（`build_workspace_snapshot` 的快照采集面；任务书/s922-105 称「快照恢复」，
   本档按磁盘实况同时钉**采集**与**恢复**两条，见 `_RESTORE_*` 两例）；
② `src/ui/undergrad_wizard.py:3595-3602`（向导读「推荐参考文献」读侧；同一条 `literature_items` 列表）；
③ `src/literature_review/review_import.py:134`（`apply_review_comments_to_state` 写回面，
   含 `it["review_comments"]` 就地变异）。

口径（与 s922-105 一致）：**只钉现状，不背书任何一种修法**。每条用例的 docstring 写明
「宽容 vs 抛错」的现状是哪一侧、以及修复落地后本用例应翻红成什么样。禁止悄悄删桩。

⚠️ 本档**不导入 `app.py`、不跑 `AppTest`、不启动 Streamlit 应用**（纪律档 §廿一）。
它只用裸 `st.session_state`（与 `tests/test_workspace.py` 同口径）＋ AST 抽取的生产码片段，
零网络、零 LLM、零真实被试数据、零写盘。

防假绿设计（三处）：
- 读侧（入口 2）不重写一遍判据，而是用 AST 从 `undergrad_wizard.py` **抽出生产环**再 exec；
  `test_wizard_read_side_extraction_is_discriminating` 当场证明这条通道**有鉴别力**
  （同一通道喂一个"全宽容"的假实现必须红），否则整批读侧用例都是自证。
- 抽取锚点逐字钉（`_lr_items_raw = ...` 原文 + 环首行原文），生产码一改就**报错而不是静默测旧码**。
- 结构前提（`except Exception: pass`）单独钉一条，因为「抛错」在页面上的**表现**正是由它决定的。
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest
import streamlit as st

from src.literature_review.review_import import apply_review_comments_to_state
from src.utils.workspace import (
    LITERATURE_REVIEW_SESSION_KEY,
    build_workspace_snapshot,
    get_literature_review_state,
    restore_workspace,
)



# ───────────────────────── 脏值样本（三入口共用同一批） ─────────────────────────
FALSY_NON_LIST = {
    "none": None,
    "empty_list": [],
    "zero": 0,
    "empty_str": "",
    "false": False,
    "empty_dict": {},
}
ITERABLE_NON_LIST = {
    "nonempty_dict": {"keyA": 1, "keyB": 2},
    "bare_str": "abc",
}
NON_ITERABLE = {"int_5": 5, "bool_True": True}
LIST_WITH_DIRTY = [{"key": "k1", "title": "good"}, "junk", None, 7]
TUPLE_OF_DICTS = ({"key": "k1"}, {"key": "k2"})


@pytest.fixture(autouse=True)
def _clean_session_state():
    st.session_state.clear()
    yield
    st.session_state.clear()


# ═══════════════════════ 入口 1：workspace 快照采集面（:373） ═══════════════════════
def _build_lr(literature_items):
    """把脏 `literature_items` 塞进 session_state，跑一次真实 `build_workspace_snapshot`。"""
    st.session_state[LITERATURE_REVIEW_SESSION_KEY] = {"literature_items": literature_items}
    return build_workspace_snapshot()["literature_review_state"]["literature_items"]


def test_snapshot_capture_normalizes_all_falsy_non_list_to_empty_list():
    """现状（宽容侧）：`list(lr_state.get("literature_items") or [])` 的 `or []` 只兜得住**假值**。

    None / [] / 0 / "" / False / {} 六种都落回 `[]` —— 与 s922-105 对 `or 0` 的结论同构：
    `or` 是"空值兜底"，不是"类型兜底"。
    """
    for name, dirty in FALSY_NON_LIST.items():
        assert _build_lr(dirty) == [], name


@pytest.mark.parametrize(
    "dirty,expected",
    [
        pytest.param({"keyA": 1, "keyB": 2}, ["keyA", "keyB"], id="dict_静默变_keys"),
        pytest.param("abc", ["a", "b", "c"], id="str_静默逐字符拆"),
        pytest.param(TUPLE_OF_DICTS, [{"key": "k1"}, {"key": "k2"}], id="tuple_转_list_不报错"),
    ],
)
def test_snapshot_capture_silently_corrupts_iterable_non_list_without_raising(dirty, expected):
    """现状（**静默腐蚀**侧，比抛错更坏）：任何可迭代的非 list 都被 `list()` 吃成一个新 list。

    dict → **键列表**、str → **字符列表**：快照里 `literature_items` 变成一个"看起来像列表"的东西，
    条目全丢但零告警。修复（加 `isinstance(..., list)` 校验或告警）后本用例应翻红。
    """
    assert _build_lr(dirty) == expected


@pytest.mark.parametrize("dirty", [5, True], ids=["int", "bool_True"])
def test_snapshot_capture_raises_typeerror_on_non_iterable_non_list(dirty):
    """现状（抛错侧）：不可迭代的非假值 ⇒ `list(5)` TypeError，**整份工作区快照构建炸掉**。

    这不是"该条目丢了"，而是"整个保存动作失败"（`build_workspace_snapshot` 无本地 try）。
    修复后本用例应翻红成"降级为空列表 + 告警"。
    """
    with pytest.raises(TypeError):
        _build_lr(dirty)


def test_snapshot_capture_passes_dirty_entries_through_untouched():
    """现状：列表**内部**的脏条目（str/None/int 混在合法 dict 里）采集时**一律不筛不判**，原样进快照。

    ⇒ 采集面是"浅拷贝 + 零校验"。与 `undergrad_wizard` 读侧的 `isinstance` 过滤形成明确分工：
    脏条目由**每个消费方各自防**，快照本身不承担净化责任。
    """
    assert _build_lr(list(LIST_WITH_DIRTY)) == LIST_WITH_DIRTY


def test_snapshot_capture_drops_whole_section_when_lr_state_is_not_a_dict():
    """现状（静默丢失侧）：外层 `if isinstance(lr_state, dict)` ⇒ lr_state 是 str/list 时
    **整个 `literature_review_state` 键从快照里消失**（不是报错，也不是写空）。

    与 s922-105 ②「前置好条目一起被弃」同一形状：守卫在容器层，脏值在容器层就被整块吞掉。
    """
    st.session_state[LITERATURE_REVIEW_SESSION_KEY] = "not-a-dict"
    assert "literature_review_state" not in build_workspace_snapshot()


def test_snapshot_capture_key_absent_is_indistinguishable_from_empty_list():
    """现状：`literature_items` 键**缺失**与**为空 list**在快照里落回同一个 `[]` ⇒ 两态不可分。

    （对照 s921-07 在 `compute_pending_elapsed` 里刻意保留 None/0 两态可分的做法——采集面**没有**这层。）
    """
    st.session_state[LITERATURE_REVIEW_SESSION_KEY] = {"notes": []}
    got = build_workspace_snapshot()["literature_review_state"]
    assert got["literature_items"] == []


# ═══════════════════════ 入口 1'：workspace 快照恢复面（:685-690） ═══════════════════════
def _restore_lr(literature_items):
    n = restore_workspace({
        "_schema": "v3.5",
        LITERATURE_REVIEW_SESSION_KEY: {"literature_items": literature_items},
    })
    state = st.session_state.get(LITERATURE_REVIEW_SESSION_KEY)
    return n, state["literature_items"]


def test_snapshot_restore_writes_every_dirty_shape_back_verbatim():
    """现状（**全宽容＝零校验**）：恢复面对 12 种脏值**一种都不拦、一种都不改**。

    `lr.setdefault(k, v)` 只在键**缺失**时补默认值，脏值键**不被覆盖** ⇒
    采集面（`list()`）造成的腐蚀与恢复面造成的腐蚀叠加后，脏值可以跨"存盘→读盘"存活。
    修复（恢复面加类型校验）后本用例应翻红。
    """
    samples = {**FALSY_NON_LIST, **ITERABLE_NON_LIST, **NON_ITERABLE,
               "tuple": TUPLE_OF_DICTS, "list_with_dirty": LIST_WITH_DIRTY}
    for name, dirty in samples.items():
        st.session_state.clear()
        _, got = _restore_lr(dirty)
        assert got == dirty and type(got) is type(dirty), name


def test_snapshot_restore_never_raises_even_for_the_shapes_capture_would_reject():
    """现状对照：`int_5`/`bool_True` 在**采集**面抛 TypeError，在**恢复**面却安静地写回 session_state。

    ⇒ 三入口里只有采集面会因这条脏值当场炸；恢复面把同样的脏值**送进运行中的会话**，
    由下游（向导读/写回面）各自决定炸还是静默。这条差异是两案修复范围的关键读数。
    """
    for dirty in NON_ITERABLE.values():
        st.session_state.clear()
        n, got = _restore_lr(dirty)
        assert got == dirty and n >= 1


def test_get_literature_review_state_validates_only_the_outer_dict():
    """现状：读口 `get_literature_review_state` 只做两件事——外层非 dict 整体退回默认、缺失键 setdefault 补。

    `literature_items` 的实际类型**不校验**（int/str/dict 原样返回），
    所以「快照恢复后再经读口取出的东西」仍是脏的。修复应落在这里（一处覆盖三入口）。
    """
    st.session_state[LITERATURE_REVIEW_SESSION_KEY] = {"literature_items": 5}
    assert get_literature_review_state(st.session_state)["literature_items"] == 5

    st.session_state.clear()
    st.session_state[LITERATURE_REVIEW_SESSION_KEY] = {"literature_items": "abc"}
    assert get_literature_review_state(st.session_state)["literature_items"] == "abc"

    st.session_state.clear()
    st.session_state[LITERATURE_REVIEW_SESSION_KEY] = "not-a-dict"
    assert get_literature_review_state(st.session_state)["literature_items"] == []


# ═════════════════ 入口 2：undergrad_wizard 向导读侧（:3595-3602，AST 抽生产环） ═════════════════
_WIZ = Path(__file__).resolve().parents[1] / "src" / "ui" / "undergrad_wizard.py"
_wiz_src_text = _WIZ.read_text(encoding="utf-8")
_wiz_tree = ast.parse(_wiz_src_text)
_wiz_for = next(
    n for n in ast.walk(_wiz_tree)
    if isinstance(n, ast.For) and getattr(n.iter, "id", "") == "_lr_items_raw"
)
_ASSIGN_LINENO = next(
    i for i, ln in enumerate(_wiz_src_text.splitlines(), 1)
    if ln.strip() == '_lr_items_raw = _lr_state.get("literature_items") or []'
)
_wiz_region = textwrap.dedent(
    "\n".join(_wiz_src_text.splitlines()[_ASSIGN_LINENO - 1:_wiz_for.end_lineno])
)
_wiz_wrapped = (
    "def _lr_wizard_read(_lr_state):\n"
    + textwrap.indent(_wiz_region, "    ")
    + "\n    return _selected_lit\n"
)
_wiz_ns: dict = {}
exec(compile(_wiz_wrapped, "undergrad_wizard.py:3595-3602 (extracted)", "exec"), _wiz_ns)  # noqa: S102
_lr_wizard_read = _wiz_ns["_lr_wizard_read"]


def test_wizard_read_side_extraction_is_discriminating():
    """**鉴别力自证**（本文件最重要一条）：同一抽取通道喂"全宽容"的假实现必须红。

    若抽取静默退化（例如 dedent 把环吃成空函数、或 exec 的名字被改名后读到一个恒返回 []），
    下游所有 wizard 用例都会"绿着测空气"。这里正向断言抽出来的确实是对 `reading_status`/
    `relevance_score` 敏感的环：同一份输入，好条目→产出 1 条；把阈值字段抹成 0.1→产出 0 条。
    """
    good = [{"key": "g", "reading_status": "done", "relevance_score": "0.9"}]
    assert len(_lr_wizard_read({"literature_items": good})) == 1
    assert len(_lr_wizard_read({"literature_items": [
        {**good[0], "relevance_score": "0.1"}]})) == 0
    assert len(_lr_wizard_read({"literature_items": [
        {**good[0], "reading_status": "todo"}]})) == 0
    # 抽取区间必须逐字含生产判据原文（生产码一改就地报错，不静默测旧码）
    assert '_lr_items_raw = _lr_state.get("literature_items") or []' in _wiz_region
    assert "for _raw in _lr_items_raw:" in _wiz_region
    assert 'float(_raw.get("relevance_score") or 0) >= 0.4' in _wiz_region


def test_wizard_read_side_filters_non_dict_entries_tolerantly():
    """现状（**唯一真正宽容**的一侧）：读侧环自带 `if not isinstance(_raw, dict): continue`。

    脏条目混在合法条目里 ⇒ 脏的跳过、好的留下（`['g']`）。这与 s922-105 ② 里
    `_materialize_items` 的"一条脏 ⇒ 全丢"是**相反**的形状 ⇒ LR 各消费方对脏条目的态度并不一致。
    """
    good = {"key": "g", "reading_status": "done", "relevance_score": "0.9"}
    got = _lr_wizard_read({"literature_items": [good, "junk", None, 7]})
    assert [x["key"] for x in got] == ["g"]


@pytest.mark.parametrize("dirty", [None, [], 0, "", False, {}],
                         ids=["none", "empty_list", "zero", "empty_str", "false", "empty_dict"])
def test_wizard_read_side_absorbs_falsy_non_list_via_or_empty_list(dirty):
    """现状（宽容侧）：`or []` 在**环之前**兜住假值 ⇒ 0 条产出、零告警。

    注意与采集面的差异：这里 `None` 不抛（采集面 `list(None)` 抛）。同一个脏值在三个入口
    的**表现**可以完全不同，这正是任务书要"矩阵"而非"单点"的原因。
    """
    assert _lr_wizard_read({"literature_items": dirty}) == []


@pytest.mark.parametrize("dirty", [5, True], ids=["int", "bool_True"])
def test_wizard_read_side_raises_typeerror_then_vanishes_silently(dirty):
    """现状（抛错侧）：不可迭代的非假值 ⇒ `for` 当场 TypeError。

    单独看抽取环是"抛错"；配上下一条钉住的外层 `except Exception: pass`，
    页面上的**真实表现**是「📚 推荐参考文献」整块静默消失、连一条日志都不留。
    """
    with pytest.raises(TypeError):
        _lr_wizard_read({"literature_items": dirty})


@pytest.mark.parametrize("dirty", [{"keyA": 1, "keyB": 2}, "abc"],
                         ids=["dict_yields_keys", "str_yields_chars"])
def test_wizard_read_side_iterates_wrong_containers_and_produces_zero_items(dirty):
    """现状（静默零产出侧）：dict/str 可迭代 ⇒ 环跑得完，但每个元素都不是 dict ⇒ 全被 continue。

    不抛、不告警、产出 0 条。采集面已经把 dict 腐蚀成 keys（`['keyA','keyB']`），
    到这一层表现为"你的文献综述里没有一条已读高相关文献"——**因果链在这里闭环**。
    """
    assert _lr_wizard_read({"literature_items": dirty}) == []


def test_wizard_read_side_single_dirty_relevance_score_kills_the_whole_section():
    """现状（放大面，本文件最实质的一条）：**一条**脏 `relevance_score` ⇒ `float()` 抛 ValueError
    ⇒ 环中断 ⇒ 已进 `_selected_lit` 的前序好条目随局部量一起消失。

    实测顺序是「好条目在前、脏条目在后」：抽取环里好条目确实先被 append（见 `_lr_wizard_read`
    返回前的中间态），但抛错让函数没有返回值，外层 `except Exception: pass` 接住后
    **整块连"0 条"都不显示**。与 s922-105 ② 的 `_materialize_items`「前置好条目一起被弃」同型。
    """
    good = {"key": "g", "reading_status": "done", "relevance_score": "0.9"}
    bad = {"key": "b", "reading_status": "done", "relevance_score": "约 0.75"}
    with pytest.raises(ValueError):
        _lr_wizard_read({"literature_items": [good, bad]})
    # 对照：把脏条目挪到最前面，好条目同样救不回来（抛错点在环内，与顺序无关）
    with pytest.raises(ValueError):
        _lr_wizard_read({"literature_items": [bad, good]})


def test_wizard_read_side_handler_now_logs_warning(monkeypatch):
    """【s1002-19 翻正】s923-23 D3 / s924-39 遗留2 落地：读侧环的 handler 已从
    `except Exception: pass` 改为 `except Exception as exc:` ＋ `logger.warning(...)`——
    「整块推荐文献消失」时留观测日志（WARN 文案与 :129 既有格式同源）。

    原例（钉 pass 现状）按其自述「修复即红按注释翻正」执行：仍钉 handler 结构
    （type=Exception 恰 1 个），但主体断言改为 warning 调用在册。
    """
    outer = [n for n in ast.walk(_wiz_tree)
             if isinstance(n, ast.Try) and n.lineno <= _wiz_for.lineno <= n.end_lineno]
    assert outer, "读侧环之外找不到包裹它的 try ⇒ 结构前提已变，须重估全部读侧用例"
    innermost = min(outer, key=lambda n: n.end_lineno - n.lineno)
    assert len(innermost.handlers) == 1
    h = innermost.handlers[0]
    assert ast.unparse(h.type) == "Exception"
    body_src = [ast.unparse(stmt) for stmt in h.body]
    assert any("logger.warning" in b for b in body_src),         f"观测 WARN 丢失（回退成静默）：{body_src}"
    assert not any(b == "pass" for b in body_src), "handler 又变回裸 pass"


# ═════════════ 入口 3：review_import.apply_review_comments_to_state（:134 写回面） ═════════════
PARSED_ONE_HIT = {
    "literature": {"k1": [{"text": "c1", "imported_at": "2026-09-23 00:00:00"}]},
    "notes": {},
    "matrix": {},
}


def _apply(literature_items, parsed=PARSED_ONE_HIT):
    state = {"literature_items": literature_items, "notes": [], "matrix": {}}
    return apply_review_comments_to_state(state, parsed), state


@pytest.mark.parametrize("dirty", [None, [], 0, "", False, {}],
                         ids=["none", "empty_list", "zero", "empty_str", "false", "empty_dict"])
def test_review_import_writeback_absorbs_falsy_non_list(dirty):
    """现状（宽容侧）：`for it in (lr_state.get("literature_items") or [])` ⇒ 假值兜成 `[]`，计数 0。"""
    counts, _ = _apply(dirty)
    assert counts == {"literature": 0, "notes": 0, "matrix": 0}


@pytest.mark.parametrize("dirty", [5, True], ids=["int", "bool_True"])
def test_review_import_writeback_raises_typeerror_on_non_iterable(dirty):
    """现状（抛错侧）：不可迭代的非假值 ⇒ TypeError。

    与读侧的关键区别：**本函数没有 try** ⇒ 异常一路逃到调用方（导入向导的"应用批注"按钮），
    是「当场报错」而不是「静默不产出」。
    """
    with pytest.raises(TypeError):
        _apply(dirty)


def test_review_import_writeback_skips_dirty_entries_but_still_counts_hits():
    """现状（混合面）：脏条目被 `isinstance(it, dict)` 跳过，合法条目正常计数 ⇒ 计数**不**含脏条目。"""
    items = [{"key": "k1"}, "junk", None, 7]
    counts, state = _apply(items)
    assert counts["literature"] == 1
    assert state["literature_items"][1:] == ["junk", None, 7]


def test_review_import_writeback_mutates_items_in_place_and_leaks_to_caller():
    """现状（就地变异，任务书点名项）：`it["review_comments"] = existing` 改的是**调用方持有的同一个 dict**，
    而 `existing.extend(comments)` 改的甚至是 `it` 自己那个 list 对象。

    ⇒ 写回面**不返回新状态**（返回值只有计数），副作用全在原对象上。
    配合采集面的 `list(...)` 浅拷贝（`test_snapshot_capture_*`），同一批 dict 会同时存在于
    session_state 与快照里 ⇒ **导入一次批注，会话与快照一起被改**，回滚快照救不回来。
    """
    it = {"key": "k1"}
    counts, state = _apply([it, "junk", None, 7])
    assert counts["literature"] == 1
    assert it["review_comments"] == PARSED_ONE_HIT["literature"]["k1"]
    assert it is state["literature_items"][0]          # 原对象，不是副本
    assert it["review_comments"] is state["literature_items"][0]["review_comments"]


def test_review_import_writeback_on_tuple_keeps_container_type_and_still_mutates_members():
    """现状：容器是 tuple 时**不会**被换成 list（本函数不重绑容器），但元素 dict 仍被就地写。

    计数 literature=1 与容器实际不可变并存 ⇒ 若上层再对 `state["literature_items"]` 做 `append`，
    会在此之后另炸一次。钉这条是为记录"写回面默认容器可变"这个隐含前提。
    """
    counts, state = _apply(TUPLE_OF_DICTS)
    assert counts["literature"] == 1
    assert isinstance(state["literature_items"], tuple)
    assert state["literature_items"][0].get("review_comments")


@pytest.mark.parametrize("pre", ["pending", (1,)], ids=["str", "tuple"])
def test_review_import_writeback_raises_when_existing_comments_is_str_or_tuple(pre):
    """现状（抛错侧，就地变异的代价面）：`existing = it.get("review_comments") or []` 兜不住非空
    的 str/tuple ⇒ `existing.extend(...)` 当场 AttributeError。

    即"条目级脏值"在本函数里从**静默**（读侧）升级成**抛错**（写回侧），且抛点在循环中 ⇒
    第一条脏条目就让整次导入失败，后面的好条目一条都写不进去。
    """
    with pytest.raises(AttributeError):
        _apply([{"key": "k1", "review_comments": pre}])


@pytest.mark.parametrize("pre", [None, 0, {}], ids=["none", "int0", "empty_dict"])
def test_review_import_writeback_absorbs_falsy_existing_comments(pre):
    """现状（宽容侧）：假值 `review_comments` 被 `or []` 兜住 ⇒ 正常写入 1 条。"""
    counts, state = _apply([{"key": "k1", "review_comments": pre}])
    assert counts["literature"] == 1
    assert len(state["literature_items"][0]["review_comments"]) == 1


def test_review_import_writeback_expands_string_comment_list_into_characters():
    """现状（**静默腐蚀 + 计数虚高**，本文件最脏的一条）：
    `parsed_comments["literature"]["k1"]` 是**非空字符串**时，
    `if comments:` 判真 ⇒ `existing.extend("notalist")` ⇒ 逐字符写入，
    且 `counts["literature"] += len(comments)` 给出 **8**（字符串长度）。

    ⇒ 上游解析器（`parse_review_comments`）正常时永远给 list，所以这条今天"碰不到"；
    但本函数**不校验入参形状**，一旦上游改了输出契约（或有人手填批注 JSON），
    文献条目会被写成一串单字符"批注"，而计数报告说"成功导入 8 条"。
    修复（校验 comments 是 list）后本用例应翻红。
    """
    counts, state = _apply([{"key": "k1"}], {"literature": {"k1": "notalist"}, "notes": {}, "matrix": {}})
    assert counts["literature"] == 8
    assert state["literature_items"][0]["review_comments"] == list("notalist")


@pytest.mark.parametrize("bad_literature", [[], "x", 7], ids=["list", "str", "int"])
def test_review_import_writeback_raises_when_parsed_comments_is_wrong_type(bad_literature):
    """现状（抛错侧）：`parsed_comments.get("literature", {})` 的默认值**只在键缺失时生效**；
    键存在但类型不对 ⇒ 紧接着 `.get(it.get("key"))` 抛 AttributeError（int 则 AttributeError/TypeError）。

    与上一条同根：本函数把"入参形状"当既定事实。钉它是为记录**契约边界**在哪一侧。
    """
    parsed = {"literature": bad_literature, "notes": {}, "matrix": {}}
    with pytest.raises((AttributeError, TypeError)):
        _apply([{"key": "k1"}], parsed)


def test_review_import_writeback_matches_items_without_key_against_literal_none_key():
    """现状（串写风险）：条目**缺 `key`** 时 `it.get("key")` 是 None，
    于是 `parsed_comments["literature"].get(None)` 命中 ⇒ **ghost 批注写进每一个无 key 的条目**。

    上游 `parse_review_comments` 正常不会产生 `None` 键，但本函数不挡 ⇒ 一条无 key 的脏条目
    会被"实名批注"之外的通道拿到内容。修复（`if not it.get("key"): continue`）后本用例应翻红。
    """
    it_a, it_b = {"title": "no key A"}, {"title": "no key B"}
    counts, _ = _apply([it_a, it_b], {
        "literature": {None: [{"text": "ghost", "imported_at": "x"}]}, "notes": {}, "matrix": {}})
    assert counts["literature"] == 2
    assert it_a["review_comments"] == [{"text": "ghost", "imported_at": "x"}]
    assert it_b["review_comments"] == [{"text": "ghost", "imported_at": "x"}]


@pytest.mark.parametrize("matrix,raises", [
    pytest.param("x", True, id="matrix_str_抛"),
    pytest.param({"review_comments": "x"}, True, id="matrix_comments_str_抛"),
    pytest.param({"review_comments": "abc"}, True, id="matrix_comments_str_len3_抛"),
    pytest.param([], False, id="空list_被_or_兜住"),
    pytest.param({"review_comments": []}, False, id="空comments_被_or_兜住"),
])
def test_review_import_writeback_matrix_side_truth_table(matrix, raises):
    """现状：matrix 侧与 literature 侧同构——`or {}` 只兜假值；非空的错误类型一律 `.get` AttributeError。"""
    state = {"literature_items": [], "notes": [], "matrix": matrix}
    parsed = {"literature": {}, "notes": {},
              "matrix": {"c1": [{"text": "t", "imported_at": "x"}]}}
    if raises:
        with pytest.raises(AttributeError):
            apply_review_comments_to_state(state, parsed)
    else:
        assert apply_review_comments_to_state(state, parsed)["matrix"] == 1
