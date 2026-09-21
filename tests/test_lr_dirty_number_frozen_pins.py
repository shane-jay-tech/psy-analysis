# -*- coding: utf-8 -*-
"""s922-105：文献面板「脏数字整页红」现状护栏钉桩（s922-05 §五 冻结项，A/B 方案未拍板前先锁死现状）。

冻结的是什么（口径来源：`docs/insights/psy-dirtynum-rescore-material-20260921.md` §五 与
`zcode-bridge/outbox/s922-05-psy-dirtynum-material.result.md`；本档**不重述其判据、不改任何数值**）：
① `src/literature_review/models.py:69/:73/:78` —— `LiteratureItem.from_dict` 的 year /
   citation_count / relevance_score 三处裸强转：`or 0` 只兜得住**空值**（''/None），非空脏串一律抛 ValueError；
② `src/ui/literature_review_panel.py:757` —— `_materialize_items` 的列表推导把单条脏值放大成
   「三条里一条脏 ⇒ 零条产出」（前置好条目一起被弃）；
③ `src/ui/literature_review_panel.py:121-123` —— rescore 打分器抛错时异常逃逸，且
   `_lr_pending_rescore = False` 在**同一 if 体内**位于调用之后 ⇒ 该行不执行 ⇒ 开关留在 True ⇒
   每次 rerun 重新调用打分器（s922-05 对 s920-13「永久静默」的订正：实为**永久重试**）。

每条用例 docstring 都写明「修复落地后应翻红成什么样」——A 案（助手侧跳过并告警）或 B 案
（主入口 try + finally 落开关）合入时，本档**必须主动变红**并按注释逐条翻正，禁止悄悄删桩。
本档只钉现状，不背书任何一种修法。零网络、零 LLM、零真实 session_state、零写盘。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import src.ui.literature_review_panel as lrp
from src.literature_review.models import LiteratureItem

_PANEL = Path(lrp.__file__).resolve()


# ─────────────────────────── ① models 层逐字段（现状钉桩） ───────────────────────────
@pytest.mark.parametrize("dirty", ["约 2019", "2019年", "n/a"])
def test_from_dict_year_nonempty_garbage_raises(dirty):
    """现状：year 非空脏串 ⇒ ValueError。修复（A 案跳过并告警 / C 案静默回退 0）后本用例应翻红。"""
    with pytest.raises(ValueError):
        LiteratureItem.from_dict({"key": "k", "title": "t", "year": dirty})


@pytest.mark.parametrize("dirty", ["约 12", "1,234"])
def test_from_dict_citation_count_garbage_raises_including_thousands_separator(dirty):
    """现状：citation_count 连千分位串 '1,234' 都抛（爬虫返回值常见形态）。修复后应翻红。"""
    with pytest.raises(ValueError):
        LiteratureItem.from_dict({"key": "k", "title": "t", "citation_count": dirty})


@pytest.mark.parametrize("dirty", ["约 0.75", "0.75 左右"])
def test_from_dict_relevance_score_garbage_raises(dirty):
    """现状：relevance_score 带中文修饰的浮点串抛 ValueError。修复后应翻红。"""
    with pytest.raises(ValueError):
        LiteratureItem.from_dict({"key": "k", "title": "t", "relevance_score": dirty})


@pytest.mark.parametrize("field,zero", [("year", 0), ("citation_count", 0), ("relevance_score", 0.0)])
@pytest.mark.parametrize("blank", ["", None])
def test_from_dict_blank_values_are_absorbed_not_raised(field, blank, zero):
    """现状：`or 0` / `or 0.0` 只兜空值 —— ''/None 落回默认，与上面三档脏串形成明确分界。

    这条是**分界护栏**：若有人把 `or 0` 改成 try/except 宽口径，本用例仍绿；
    若有人改成对 '' 也抛，本用例翻红（那是把伤害扩大，属改判据，需人工放行）。
    """
    item = LiteratureItem.from_dict({"key": "k", "title": "t", field: blank})
    assert getattr(item, field) == zero


@pytest.mark.parametrize(
    "field,text,expected",
    [("year", "2019", 2019), ("citation_count", "12", 12), ("relevance_score", "0.9", 0.9)],
)
def test_from_dict_numeric_strings_still_coerce_cleanly(field, text, expected):
    """现状对照（防恒红）：纯数字串正常转换 —— 抛错的只有非空脏串。"""
    item = LiteratureItem.from_dict({"key": "k", "title": "t", field: text})
    assert getattr(item, field) == expected


# ─────────────────────────── ② _materialize_items 整表弃（现状钉桩） ───────────────────────────
def test_materialize_one_dirty_row_drops_the_entire_table_including_leading_good_rows():
    """现状：[好, 脏, 好] ⇒ 抛 ValueError 且**零条产出**，前置好条目一起被弃（不是「跳过坏条」）。

    修复后应翻红：A 案会产出 2 条好条目 ＋ 1 条告警；C 案会产出 3 条（脏年变 0）。
    两种修法下本用例都不该再绿 —— 见到它红了就说明 §五 冻结项已有人施工。
    """
    rows = [
        {"key": "good-1", "title": "前置好条目", "year": "2019"},
        {"key": "dirty", "title": "脏年", "year": "约 2019"},
        {"key": "good-2", "title": "后置好条目", "year": "2020"},
    ]
    with pytest.raises(ValueError):
        lrp._materialize_items(rows)


def test_materialize_does_not_partially_mutate_the_session_list_when_it_raises():
    """现状：抛出是「整表弃」而非「写坏一半」—— 入参 dict 列表不被就地改写。

    这条修复后**仍应绿**（A/B/C 三案都不该在抛出前污染 session 列表），故不标翻正。
    """
    rows = [{"key": "a", "year": "2019"}, {"key": "b", "year": "约 2019"}]
    snapshot = [dict(r) for r in rows]
    with pytest.raises(ValueError):
        lrp._materialize_items(rows)
    assert rows == snapshot


def test_materialize_all_clean_rows_still_yields_every_item():
    """现状对照（防恒红）：全干净时逐条产出、顺序不变。"""
    rows = [{"key": "a", "year": "2019"}, {"key": "b", "year": "2020"}]
    items = lrp._materialize_items(rows)
    assert [i.key for i in items] == ["a", "b"] and all(isinstance(i, LiteratureItem) for i in items)


# ─────────────────────────── ③ rescore 逃逸 ＋ 开关留在 True（现状钉桩） ───────────────────────────
def test_rescore_helper_exception_escapes_without_writing_back(monkeypatch):
    """现状：`_do_relevance_rescore`(:198) 内无 try，打分器抛错直穿到调用方，且不落半成品。

    修复后（B 案在主入口包 try）从助手直调仍会抛 ⇒ 这条**保持绿**；
    若有人把 try 挪进助手并吞掉异常，本用例翻红（那是另一種语义，需人工放行）。
    """
    def boom(items, rq, vars_):
        raise RuntimeError("打分器炸了（模拟 LLM/网络失败）")

    monkeypatch.setattr(lrp, "rescore_existing_items", boom)
    old = [{"key": "a", "year": "2019"}]
    lr_state = {"literature_items": old}

    with pytest.raises(RuntimeError):
        lrp._do_relevance_rescore({"research_question": "新研究问题"}, lr_state)

    assert lr_state["literature_items"] is old  # 抛出前没有写回半成品


def _pending_rescore_block() -> ast.If:
    """从**磁盘上的真源码**取 `render_literature_review` 里那一条 `if _lr_pending_rescore` 节点。

    不写死行号：节点定位靠内容匹配，行号只用于断言它仍在主入口函数体内。
    """
    src = _PANEL.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "render_literature_review")
    hits = [n for n in ast.walk(fn)
            if isinstance(n, ast.If) and "_lr_pending_rescore" in (ast.get_source_segment(src, n) or "")]
    assert len(hits) == 1, f"锚点漂移：主入口里匹配到 {len(hits)} 条 pending_rescore 判断"
    return hits[0]


def test_main_entry_block_flag_stays_true_when_real_rescore_raises(monkeypatch):
    """现状：跑**真实源码语句**（ast 取 :121-123 后 exec），打分器抛错 ⇒ 开关仍为 True。

    这条就是 s922-05 对 s920-13 的订正点：不是「一次失败永久静默」，而是「每次 rerun 重新调用打分器」。
    修复后应翻红：B 案（try + finally 落 False）会让本用例读到 False。
    出口：翻正时把断言改成 `is False` 并注明放行单号，不要删用例。
    """
    def boom(items, rq, vars_):
        raise RuntimeError("打分器炸了（模拟 LLM/网络失败）")

    monkeypatch.setattr(lrp, "rescore_existing_items", boom)
    node = _pending_rescore_block()
    session = {"_lr_pending_rescore": True}
    fake_st = _SessionSt(session)

    globals_ = {
        "st": fake_st,
        "_do_relevance_rescore": lrp._do_relevance_rescore,  # 真助手，非复刻
        "upstream": {"research_question": "新研究问题"},
        "lr_state": {"literature_items": [{"key": "a", "year": "2019"}]},
    }
    with pytest.raises(RuntimeError):
        exec(compile(ast.get_source_segment(_PANEL.read_text(encoding="utf-8"), node),
                     f"{_PANEL.name}:pending-rescore-block", "exec"), globals_)

    assert session["_lr_pending_rescore"] is True, "开关被落了 False ⇒ §五 冻结项已被施工，本用例应翻正"
    assert fake_st.calls == [], "现状不该有 st.success（抛出发生在写回之前）"


def test_pending_flag_reset_is_second_statement_with_no_try_guard():
    """现状（结构冻结）：if 体 = [调用, 落 False]，两条**平铺**且外层 0 个 try ⇒ 抛出即跳过落开关。

    修复后应翻红：B 案会把两条包进 try/finally，本结构断言即失效。
    """
    node = _pending_rescore_block()
    assert [type(s).__name__ for s in node.body] == ["Expr", "Assign"], (
        "if 体结构漂移：现状是「调用 + 同体下一行落 False」，改动即说明 §五 冻结项已有人施工")
    assert isinstance(node.body[0].value, ast.Call)
    assert node.body[0].value.func.id == "_do_relevance_rescore"
    assert node.body[1].targets[0].slice.value == "_lr_pending_rescore"

    src = _PANEL.read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "render_literature_review")
    # 落开关这条语句外层没有任何 try/finally —— 这正是「异常逃逸 ⇒ 开关留 True」的结构原因。
    guarded = [t for t in ast.walk(fn) if isinstance(t, ast.Try) and node in t.body]
    assert guarded == [], "主入口已加 try ⇒ 本结构钉桩应随修复单翻正"
    assert sum(1 for n in ast.walk(fn) if isinstance(n, ast.Try)) == 0, (
        "render_literature_review 内 try 块数不再是 0（s922-05 证据 3 的现状读数）")


class _SessionSt:
    """最小假 st：只提供 session_state 读写，其余调用一律当场红（现状主入口这段不该触到别的 st API）。"""

    class _State(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    def __init__(self, initial):
        self.session_state = dict(initial)
        self.calls: list[str] = []

    def success(self, msg, **k):
        self.calls.append("success")

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
