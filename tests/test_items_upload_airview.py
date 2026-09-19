# -*- coding: utf-8 -*-
"""src/ui/items_upload_panel.py::_run_ai_review 钉桩（s920-16）。

现测（`test_items_upload_panel.py`）只覆盖 `_safe_filename`，本函数零命中。
**全程 mock，零网络、零 LLM 调用**：`ai_content_review` 与 `CONSTRUCTS` 都在被测函数内部
`from ... import`，所以打桩打在**源模块属性**上（`from X import Y` 每次执行都重读 X.Y）。

钉的是"哪条路径 + 落什么副作用"，不判断任何评分内容、不背书 AI 给分：
  ① KB 命中 ⇒ 把 kb_definition 透传给评审；结果写进 session_state；成功提示一条。
  ② KB 未命中 ⇒ kb_definition 传 None（不是空串——下游据此区分"没查到"与"查到但定义为空"）。
  ③ 评审抛异常 ⇒ st.error，并且**把上一次的结果从 session_state 摘掉**（不然是拿旧结果冒充本轮）。
  ④ 现状：CONSTRUCTS 查表自身抛异常被 `except Exception: pass` 静默 ⇒ 与"未命中"长得一样
     （与 s918-27/s919-13 在 quick_entries 里修掉的是同一族病灶；本单只钉不改）。
  ⑤ spinner 文案随 dimensions 有/无切换 ⇒ 用户等的时长提示与实际跑的 mode 一致。
"""
import pytest

import src.questionnaire.ai_content_review as acr
import src.questionnaire.construct_kb as kb
import src.ui.items_upload_panel as iup
from src.questionnaire.items_loader import ItemsDoc


class FakeState(dict):
    pass


class FakeSt:
    def __init__(self):
        self.session_state = FakeState()
        self.errors, self.successes, self.spinners = [], [], []

    def error(self, msg, **k):
        self.errors.append(msg)

    def success(self, msg, **k):
        self.successes.append(msg)

    def __getattr__(self, name):
        if name == "spinner":
            return self._spinner
        raise AssertionError(f"未预期调用 st.{name}")

    class _spinner_ctx:
        def __init__(self, host, msg):
            self.host, self.msg = host, msg

        def __enter__(self):
            self.host.spinners.append(self.msg)
            return None

        def __exit__(self, *exc):
            return False

    def _spinner(self, msg, **k):
        return FakeSt._spinner_ctx(self, msg)


class Spy:
    def __init__(self, result=None, error=None):
        self.calls, self.result, self.error = [], result, error

    def __call__(self, **kw):
        self.calls.append(kw)
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def env(monkeypatch):
    st = FakeSt()
    monkeypatch.setattr(iup, "st", st)
    monkeypatch.setattr(kb, "CONSTRUCTS", {
        "社交焦虑": {"definition": "稳定的社交场合紧张倾向"},
        "空定义构念": {"definition": ""},
    })
    return st, monkeypatch


def _run(st, monkeypatch, spy, *, name="社交焦虑", dimensions=None):
    monkeypatch.setattr(acr, "ai_content_review", spy)
    doc = ItemsDoc(items=["我在群体面前会紧张", "我担心别人评价我"])
    iup._run_ai_review(doc, f"  {name}  ", "  用户自己的定义  ", dimensions=dimensions)
    return spy


def test_kb_hit_passes_definition_and_stores_result(env):
    """①＋②对照：KB 命中时 kb_definition 原样透传，strip 掉的是入参两侧空白。"""
    st, monkeypatch = env
    spy = _run(st, monkeypatch, Spy(result={"score": 4}), name="社交焦虑")

    kw = spy.calls[0]
    assert kw["kb_definition"] == "稳定的社交场合紧张倾向"
    assert kw["construct_name"] == "社交焦虑" and kw["construct_definition"] == "用户自己的定义"
    assert kw["n_personas"] == 4 and len(kw["items"]) == 2
    assert st.session_state.get("_items_ai_review_result") == {"score": 4}
    assert st.successes == ["✅ AI 预审完成"] and st.errors == []


def test_kb_miss_sends_none_not_empty_string(env):
    st, monkeypatch = env
    spy = _run(st, monkeypatch, Spy(result={}), name="查无此构念")

    assert spy.calls[0]["kb_definition"] is None
    assert st.successes == ["✅ AI 预审完成"], "未命中不算失败：照常完成预审"


def test_kb_entry_with_empty_definition_passes_empty_string(env):
    """命中但 definition 为空 ⇒ 传空串（与"未命中传 None"可区分，别顺手合并成一种）。"""
    st, monkeypatch = env
    spy = _run(st, monkeypatch, Spy(result={}), name="空定义构念")

    assert spy.calls[0]["kb_definition"] == ""


def test_review_failure_reports_and_clears_stale_result(env):
    """③：评审抛错 ⇒ 有 error，且**上一轮结果必须被摘掉**，否则界面会拿旧结果冒充本轮。"""
    st, monkeypatch = env
    st.session_state["_items_ai_review_result"] = {"score": "上一次的结果"}

    _run(st, monkeypatch, Spy(error=RuntimeError("quota exceeded")))

    assert st.errors == ["AI 预审失败：quota exceeded"]
    assert "_items_ai_review_result" not in st.session_state
    assert st.successes == []


def test_lookup_blowup_is_currently_indistinguishable_from_miss(env):
    """④现状：查表本身抛异常 ⇒ 被 `except Exception: pass` 吞掉，结果与"未命中"完全一样。

    钉住它，是为了让"要不要像 quick_entries 那样补一行提示"（s918-27→s919-13 那条路）
    有个可核对的现场；真要改时这条会红，按注释翻正即可。
    """
    st, monkeypatch = env

    class Boom(dict):
        def get(self, *a, **k):
            raise RuntimeError("注册表读不动")

    monkeypatch.setattr(kb, "CONSTRUCTS", Boom())
    spy = _run(st, monkeypatch, Spy(result={}))

    assert spy.calls[0]["kb_definition"] is None
    assert st.errors == [] and st.successes == ["✅ AI 预审完成"], "现状：异常被吞，用户无从得知"


def test_spinner_text_follows_dimensions_mode(env):
    """⑤：有 dimensions 走"分维度评分"，没有走"串行评分"；文案与实际 mode 必须同步。"""
    st, monkeypatch = env
    spy = _run(st, monkeypatch, Spy(result={}))
    assert st.spinners == ["4 位 AI 专家串行评分（约 30-60 秒）..."]

    st2 = FakeSt()
    monkeypatch.setattr(iup, "st", st2)          # 换成第二个假 st 再跑一次
    _run(st2, monkeypatch, Spy(result={}), dimensions=[{"name": "维度1"}])
    assert st2.spinners == ["4 位 AI 专家分维度评分（约 30-60 秒）..."]
