# -*- coding: utf-8 -*-
"""s922-106：lr「列表直转」同构点钉桩（notes / search 直转面，只钉现状＋登记孪生漂移，不合并实现）。

三处同构列表推导（s922-05 §三登记，本单首次给其中两处补测）：
1. `src/ui/literature_review_panel.py:757` `_materialize_items`
   `return [LiteratureItem.from_dict(d) for d in (items_dict_list or [])]`
2. `src/literature_review/notes.py:157` `notes_from_dict_list`
   `return [ReadingNote.from_dict(d) for d in data if isinstance(d, dict)]`（:155-156 先兜非 list ⇒ `[]`）
3. `src/literature_review/search.py:230` `rescore_existing_items`
   `items_obj = [LiteratureItem.from_dict(d) for d in items_dict]`（:227-228 先兜空 ⇒ `[]`）

**本单实测到的孪生漂移面（只登记、不合并，合并属人工裁决）**：
- 对「非 dict 元素」：只有 notes:157 有 `isinstance` 过滤（静默丢弃＝宽容），panel:757 与 search:230 **没有**
  ⇒ 同一份脏列表在笔记侧少几条、在文献侧直接抛（`AttributeError`/`TypeError` 形态，见真值表用例）。
- 对「脏数字」：任务书正文写的是「notes 侧脏数字仍抛 ValueError」，**磁盘实况不成立** ——
  `models.py:122-144` 的 `ReadingNote` 六个字段全是字符串型、**零个 int()/float() 强转点** ⇒ 脏数字不抛，
  而是把 `note_id=123`、`created_at=2026` 这类错类型静默留在实例上（类型泄漏）。抛错的只有文献两侧
  （`LiteratureItem.from_dict` 的 :69/:73/:78）。本单按实况钉桩并把这条不对称写进真值表，
  **不擅自把 notes 侧改成抛错**（那属对用户可见的数据取舍，且 s922-05 的 A/B/C 方案尚未拍板）。

同单登记（任务书完成标准 4）·本族**未测点**：
- `src/literature_review/review_import.py` 的批注写回面 `apply_review_comments_to_state`
  （函数体实测 **:134-177**；任务书锚点写的 :138-145 只覆盖到 docstring 与循环开头，按磁盘实况放宽）。
  三个写回循环 literature :145-153 ／ notes :156-164 ／ matrix :167-175 各自带一条
  `if not isinstance(x, dict): continue` —— 与上面第 2 点是**同一类宽容面**，但它写回的是 session 里的 dict 本体
  （`it["review_comments"] = existing` 就地变异），失败形态与直转面不同，本单未钉，留给后续单。

零网络、零 LLM、零写盘、不触真实 session_state；`rank_by_relevance` 是纯 bigram 计算（`search.py:203-218`），
本单只用它做「是否整表弃」的形态断言，**不钉任何 relevance_score 数值**（判分口径属红线）。
"""

from __future__ import annotations

import pytest

import src.ui.literature_review_panel as lrp
from src.literature_review.models import LiteratureItem, ReadingNote
from src.literature_review.notes import notes_from_dict_list
from src.literature_review.search import rescore_existing_items


def _good_note(i: int) -> dict:
    return {"note_id": f"n{i}", "literature_key": f"k{i}", "content": f"正文{i}", "type": "其他"}


def _good_lit(i: int, year: str = "2019") -> dict:
    return {"key": f"k{i}", "title": f"文献{i}", "year": year, "added_at": "2026-01-01T00:00:00"}


# ─────────────────────── notes 面①：非 dict 过滤的宽容（现状钉桩） ───────────────────────
def test_notes_non_dict_elements_are_silently_dropped_and_order_kept():
    """现状：非 dict 元素被 `isinstance` 静默过滤，好条目顺序不变、**不抛**。

    修复后（若 notes 侧改成「跳过并告警」）本例仍绿；若改成「整表弃」则翻红 —— 那属语义变更，需人工放行。
    """
    rows = [_good_note(1), "我不是 dict", 42, None, ["list 元素"], _good_note(2)]
    notes = notes_from_dict_list(rows)

    assert [n.note_id for n in notes] == ["n1", "n2"]
    assert all(isinstance(n, ReadingNote) for n in notes)


@pytest.mark.parametrize("not_a_list", [None, {}, "字符串", 7])
def test_notes_non_list_input_yields_empty_list(not_a_list):
    """现状：入参不是 list 时 `notes.py:155-156` 直接给 `[]`（不抛、不猜）。"""
    assert notes_from_dict_list(not_a_list) == []


# ─────────────────────── notes 面②：脏数字**不抛**（实况与任务书前提不一致，见文件头） ───────────────────────
def test_notes_dirty_numbers_do_not_raise_but_leak_wrong_types():
    """现状：`ReadingNote.from_dict`（models.py:135-144）零个数值强转 ⇒ 脏数字**不抛**，错类型留在实例上。

    这条钉的是「任务书前提在磁盘上不成立」的实况：note_id 拿到 int、created_at 拿到 int。
    若后续给 ReadingNote 加了 int()/float() 强转（把 notes 侧对齐文献侧），本例翻红 ——
    届时请连同下面的真值表用例一起翻正，别只删这一条。
    """
    dirty = {"note_id": 123, "literature_key": 456, "content": "正文", "created_at": 2026}
    good, note = notes_from_dict_list([_good_note(1), dirty])

    assert good.note_id == "n1" and isinstance(good.note_id, str)   # 对照：干净条目不受影响
    assert note.note_id == 123 and isinstance(note.note_id, int)   # 类型泄漏，无告警
    assert note.literature_key == 456
    assert note.created_at == 2026
    assert isinstance(note.updated_at, str)                        # 缺失键走 `or _now_iso()` 兜底


def test_notes_face_swaps_in_a_literature_dict_without_complaining():
    """现状：把带脏 year 的**文献** dict 混进笔记列表 ⇒ ReadingNote 照造、`year` 静默丢弃、不抛。

    即「列表里混错类型条目」这条失败路径在笔记侧隐形，在文献侧（panel:757 / search:230）却会抛。
    """
    notes = notes_from_dict_list([{"key": "k9", "title": "串台的文献", "year": "约 2019"}])

    assert len(notes) == 1 and isinstance(notes[0], ReadingNote)
    assert not hasattr(notes[0], "year")                           # 字段被丢弃而非报错


# ─────────────────────── search 面：一条脏 year 整表弃（现状钉桩） ───────────────────────
def test_search_rescore_one_dirty_year_drops_entire_table():
    """现状：`search.py:230` 的直转对 [好, 脏, 好] 抛 ValueError ⇒ 三条全弃（完成标准 3）。

    修复后（A 案跳过并告警）本例应翻红成「产出 2 条」。
    """
    rows = [_good_lit(1, "2019"), _good_lit(2, "约 2019"), _good_lit(3, "2020")]
    with pytest.raises(ValueError):
        rescore_existing_items(rows, "压力与绩效", None)


@pytest.mark.parametrize("empty", [[], None])
def test_search_rescore_empty_input_short_circuits_to_empty_list(empty):
    """现状：`search.py:227-228` 对 []/None 直接 return []，打分链路零调用。"""
    assert rescore_existing_items(empty, "任意研究问题", None) == []


def test_search_rescore_all_clean_rows_round_trip_in_order():
    """现状对照（防恒红）：全干净时逐条转出，`to_dict` 回写后条目数与 key 都在。

    只断言条数与 key 集合，**不断言 relevance_score 数值**（判分口径属红线）。
    """
    rows = [_good_lit(1, "2019"), _good_lit(2, "2020")]
    out = rescore_existing_items(rows, "", None)  # research_q 为空 ⇒ rank_by_relevance 原样返回

    assert [d["key"] for d in out] == ["k1", "k2"]
    assert all(isinstance(d, dict) for d in out)


def test_search_rescore_non_dict_element_raises_too():
    """现状：search:230 **没有** isinstance 过滤 ⇒ 非 dict 元素直接抛（与 notes:157 的宽容相反）。"""
    with pytest.raises((AttributeError, TypeError, ValueError)):
        rescore_existing_items([_good_lit(1), "我不是 dict"], "", None)


# ─────────────────────── 孪生漂移面真值表（登记用，不合并实现） ───────────────────────
@pytest.mark.parametrize(
    "face,call_non_dict,expect_non_dict_raises,call_dirty,expect_dirty_raises",
    [
        ("panel.py:757 _materialize_items", lambda: lrp._materialize_items(["非dict"]), True,
         lambda: lrp._materialize_items([_good_lit(1), _good_lit(2, "约 2019")]), True),
        ("search.py:230 rescore_existing_items", lambda: rescore_existing_items(["非dict"], "", None), True,
         lambda: rescore_existing_items([_good_lit(1), _good_lit(2, "约 2019")], "", None), True),
        ("notes.py:157 notes_from_dict_list", lambda: notes_from_dict_list(["非dict"]), False,
         lambda: notes_from_dict_list([{"note_id": 123, "content": "脏数字"}]), False),
    ],
)
def test_twin_faces_are_not_yet_consistent(face, call_non_dict, expect_non_dict_raises,
                                          call_dirty, expect_dirty_raises):
    """三处同构直转对「非 dict」与「脏数字」的反应**逐格实测不一致** ⇒ 本单登记漂移，不擅自合并。

    合并（例如给文献两侧也加 isinstance，或给笔记侧也加数值强转）都会改变用户可见的数据取舍，
    属 s922-05 A/B/C 方案范围＝人工裁决。本用例的意义是：**任何人单方面统一其中一侧，这里立刻红**。
    """
    def raises(fn) -> bool:
        try:
            fn()
        except Exception:  # noqa: BLE001 - 现状登记要收所有异常形态
            return True
        return False

    assert raises(call_non_dict) is expect_non_dict_raises, f"{face} 的非 dict 反应漂移"
    assert raises(call_dirty) is expect_dirty_raises, f"{face} 的脏数字反应漂移"


def test_literature_item_from_dict_is_the_common_raise_source():
    """两侧抛错的**同源性**：panel:757 与 search:230 的失败都来自 `LiteratureItem.from_dict`（models.py:69）。

    ⇒ 若要「先合一处再改」，收敛点在这一处强转，而不是三个列表推导（口径交人工，本单不动）。
    """
    with pytest.raises(ValueError):
        LiteratureItem.from_dict({"key": "k", "year": "约 2019"})
    with pytest.raises(ValueError):
        rescore_existing_items([{"key": "k", "year": "约 2019"}], "", None)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
