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

✅ **s927-29（2026-09-28 写位施工单）已落 A＋B** ⇒ 上面点名的四条已按各自注释逐条翻正、**零删例**：
② 两条（整表弃 / 抛出前不污染入参）、③ 两条（真实语句读到开关 True / 结构冻结「0 个 try」）。
① `models.py` 的六处裸强转**没动**（那是 C 案，属改数据统计口径＝红线，仍未拍板）⇒ ① 全部保持原状绿，
其中「分界护栏」`test_from_dict_blank_values_are_absorbed_not_raised` 与两条「防恒红」对照继续生效。
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
def test_materialize_one_dirty_row_drops_the_entire_table_including_leading_good_rows(monkeypatch):
    """s927-29 放行 A 案后按本档注释翻正（原状：抛 ValueError 且零条产出，前置好条目一并被弃）。

    翻正依据＝本档文件头「A 案合入时本档必须主动变红并按注释逐条翻正，禁止悄悄删桩」＋
    `psy-dirtynum-rescore-material-20260921.md` §五 测试点 1。
    现判据：产出 2 条好条目（顺序不变）＋恰好 1 条告警；**用例不删，只改断言**。
    """
    recorder = _RecordingSt()
    monkeypatch.setattr(lrp, "st", recorder)
    rows = [
        {"key": "good-1", "title": "前置好条目", "year": "2019"},
        {"key": "dirty", "title": "脏年", "year": "约 2019"},
        {"key": "good-2", "title": "后置好条目", "year": "2020"},
    ]
    items = lrp._materialize_items(rows)

    assert [i.key for i in items] == ["good-1", "good-2"], "A 案应只弃坏条、保住好条目"
    assert len(recorder.warnings) == 1 and "脏年" in recorder.warnings[0]


def test_materialize_does_not_partially_mutate_the_session_list_when_it_raises(monkeypatch):
    """本档原注释说「修复后仍应绿」——**实况不成立**：旧断言用的是 `pytest.raises`，A 案后不再抛 ⇒ 会红。

    s927-29 按实况翻正：判据核心（入参 dict 列表不被就地改写）保留并加强，去掉「抛」这一形状。
    用例名留着 `raises` 字样是为台账断链可见，不改名。
    """
    monkeypatch.setattr(lrp, "st", _RecordingSt())
    rows = [{"key": "a", "year": "2019"}, {"key": "b", "year": "约 2019"}]
    snapshot = [dict(r) for r in rows]

    items = lrp._materialize_items(rows)

    assert rows == snapshot, "A 案只读不写：session 列表被就地改坏＝新病灶"
    assert [i.key for i in items] == ["a"], "好条目留下、脏条目被跳过"


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
    """s927-29 放行 B 案后按本档出口翻正：断言由 `is True` 改成 `is False`（放行单号 s927-29）。

    原状（s922-05 对 s920-13 的订正点）：开关留 True ⇒ 每次 rerun 重新调用打分器＝**永久重试**。
    现判据：跑磁盘上的真实语句，异常被主入口兜住不再外逃，开关**必定**落回 False。
    仍然 exec 真源码而非复刻逻辑 ⇒ 改的是断言，取证强度没降。用例不删。
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
    exec(compile(ast.get_source_segment(_PANEL.read_text(encoding="utf-8"), node),
                 f"{_PANEL.name}:pending-rescore-block", "exec"), globals_)  # 不再外逃＝B 案的降级面

    assert fake_st.session_state["_lr_pending_rescore"] is False, (
        "开关没落回 False ⇒ 会逐帧重烧打分器（永久重试复活）")
    # ⚠ 读 `fake_st.session_state` 而不是外面那份 `session`：`_SessionSt.__init__` 是 `dict(initial)` **拷贝**，
    #   旧钉桩断言的是拷贝前的 `session` ⇒ 那条「开关仍为 True」其实恒真（本班翻正时才发现，登记不扩大改动）。
    assert fake_st.calls == ["error"], f"应恰好一条用户可见的失败提示，实为 {fake_st.calls}"
    assert "打分器炸了" in fake_st.messages[0], "提示要带异常摘要，否则用户无从排查"


def test_pending_flag_reset_is_second_statement_with_no_try_guard():
    """结构冻结已随 s927-29 B 案失效 ⇒ 按本档注释翻正成「调用在 try 体、落开关在 finally」。

    结构断言的作用**没降级**：只加 `try` 不加 `finally` 的半修写法（s922-05 §一 点名的失败形态）
    在这里照样红 —— 落开关那条必须落在 `finalbody`，落在 try/except 体内都算没修。
    """
    src = _PANEL.read_text(encoding="utf-8")
    node = _pending_rescore_block()
    assert [type(s).__name__ for s in node.body] == ["Try"], (
        "if 体结构漂移：s927-29 之后应是单条 try/except/finally")

    block = node.body[0]
    assert [type(s).__name__ for s in block.body] == ["Expr"], "try 体只该有那一条调用"
    assert isinstance(block.body[0].value, ast.Call)
    assert block.body[0].value.func.id == "_do_relevance_rescore"
    assert len(block.handlers) == 1 and isinstance(block.handlers[0].type, ast.Name), (
        "兜异常的面漂移：打分器是 LLM/网络外部调用面，兜的不该只到 ValueError")
    assert block.handlers[0].type.id == "Exception"
    assert [type(s).__name__ for s in block.finalbody] == ["Assign"], "开关必须落在 finally 里"
    assert block.finalbody[0].targets[0].slice.value == "_lr_pending_rescore"
    for stmt in list(block.body) + list(block.handlers[0].body):
        seg = ast.get_source_segment(src, stmt) or ""
        assert "_lr_pending_rescore" not in seg, "落开关出现在 try/except 体内 ⇒ 抛出时仍会跳过，等于没修"

    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "render_literature_review")
    assert sum(1 for n in ast.walk(fn) if isinstance(n, ast.Try)) == 1, (
        "s922-05 证据 3 的现状读数「主入口 0 个 try」已翻正为 1；多于 1 枚说明有人加戏")


class _RecordingSt:
    """s927-29 翻正时补的最小假 st：记 warning（A 案的告警面），其余调用一律当场红。"""

    def __init__(self):
        self.warnings: list[str] = []

    def warning(self, msg, **k):
        self.warnings.append(msg)

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


class _SessionSt:
    """最小假 st：session_state 读写 ＋ success/error 两枚提示口（s927-29 后主入口这段会触 st.error）。

    success 在现状与 B 案后都**不该**出现（抛出发生在写回之前），故仍记进 `calls` 供断言逐字比对。
    """

    class _State(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    def __init__(self, initial):
        self.session_state = dict(initial)
        self.calls: list[str] = []
        self.messages: list[str] = []

    def success(self, msg, **k):
        self.calls.append("success")
        self.messages.append(msg)

    def error(self, msg, **k):
        self.calls.append("error")
        self.messages.append(msg)

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
