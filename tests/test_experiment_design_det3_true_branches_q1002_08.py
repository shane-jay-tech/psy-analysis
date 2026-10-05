# -*- coding: utf-8 -*-
"""s1002-08：实验协议 det3 真分支覆盖补测（拉丁方/顺序平衡/LLM pending）。

矿源 s923-40 遗留 3：三面判据未点名未测——
① :327-335（现取）随机化 expander 的 latin_square 真分支（拉丁方矩阵行渲染）；
② :338-347（现取）顺序平衡方案真分支——被试间模板 counterbalancing 恒 None（既有件 :528
   钉的是假分支），本件用 within_subjects 引擎真实设计触发真分支；
③ :138-165（现取）LLM 增强 pending 状态机——future/cancel_id 全桩（concurrent Future 替身，
   零线程零 LLM）。

数值口径：拉丁方矩阵/时间线分钟数全部来自引擎真实产出（模板族参数化），断言只钉
结构存在性与行数/标签逐字，零统计结论。
复用兄弟件 _FakeST 手桩基建（import 复用，不复制第二份）。
"""
from __future__ import annotations

import pytest

from tests.test_experiment_design_ui_detail_branch import (  # 复用兄弟件手桩
    DESIGN_KWARGS, STATE_KEY, TAB_PROCEDURE,
    _FakeSessionState, _FakeST,
)

WITHIN_KWARGS = dict(DESIGN_KWARGS, design_type_hint="被试内")

BALANCE_EXPANDER_LABEL = "⚖ 顺序平衡方案"
LATIN_HEADER = "**拉丁方矩阵：**"


def _within_design():
    from src.experiment_design import ExperimentDesignEngine
    eng = ExperimentDesignEngine()
    d = eng.design_experiment(**WITHIN_KWARGS)
    assert d.procedure is not None
    return d


@pytest.fixture(scope="module")
def within_design():
    return _within_design()


class _PendingOkST(_FakeST):
    """pending 状态机真分支会 st.rerun（:165 :150），兄弟件手桩把 rerun 设为断言红——
    本件子类放开为记录（pending 语义本来就是要 rerun 刷新）。"""

    def rerun(self, *args, **kwargs):
        self._record("rerun", args, kwargs)
        return None


def _render_design(monkeypatch, design, extra_state=None, pressed=()):
    from src.ui import experiment_design_ui

    real_engine_cls = experiment_design_ui.ExperimentDesignEngine

    class _Engine(real_engine_cls):
        def __init__(self):
            super().__init__()
            self.design = design

    state = {STATE_KEY: None}
    state.update(extra_state or {})
    fake_st = _PendingOkST(session_state=_FakeSessionState(state), pressed=pressed)
    monkeypatch.setattr(experiment_design_ui, "st", fake_st)
    monkeypatch.setattr(experiment_design_ui, "ExperimentDesignEngine", _Engine)
    experiment_design_ui.render_experiment_design_ui()
    return fake_st


# ---------- ① 拉丁方矩阵真分支（随机化 expander 内） ----------

def test_latin_square_rows_render_inside_randomization_expander(monkeypatch, within_design):
    proc = within_design.procedure
    assert proc.randomization, "夹具退化：被试内设计的 randomization 不应为空"
    fake_st = _render_design(monkeypatch, within_design)
    body = fake_st.body(TAB_PROCEDURE)
    assert RANDOM_HEADER_OK(body, proc), "随机化 expander 方法/描述未渲染"
    # latin_square 真分支（:331-335 现取）：矩阵头部与每行 ' → ' 连接逐行在场
    ls = proc.randomization.get("latin_square")
    assert ls, "夹具退化：本设计应带 latin_square（真分支前提）"
    assert LATIN_HEADER in body
    for row in ls:
        assert f"- {' → '.join(row)}" in body


def RANDOM_HEADER_OK(body, proc):
    return (f"**方法：** {proc.randomization.get('method', '')}" in body
            and proc.randomization.get("description", "") in body)


# ---------- ② 顺序平衡方案真分支（被试内模板才触发） ----------

def test_counterbalancing_true_branch_renders_expander_with_latin(monkeypatch, within_design):
    proc = within_design.procedure
    assert proc.counterbalancing, (
        "夹具退化：被试内模板应产出 counterbalancing（procedure_builder:419-431 触发条件）")
    fake_st = _render_design(monkeypatch, within_design)
    labels = fake_st.labels_of("expander")
    assert BALANCE_EXPANDER_LABEL in labels, ":338 真分支未渲染顺序平衡 expander"
    body = fake_st.body(TAB_PROCEDURE)
    cb = proc.counterbalancing
    assert f"**方法：** {cb.get('method', '')}" in body
    assert cb.get("description", "") in body
    ls = cb.get("latin_square", [])
    assert ls and LATIN_HEADER in body
    for row in ls:
        assert f"- {' → '.join(row)}" in body
    for rec in cb.get("additional_recommendations", []):
        assert rec in body, "additional_recommendations 未渲染"


def test_counterbalancing_branch_is_skipped_for_between_design(monkeypatch):
    """负对照：被试间设计（counterbalancing=None）真分支不渲染（与既有件 :528 相邻面）。"""
    from src.experiment_design import ExperimentDesignEngine
    eng = ExperimentDesignEngine()
    d = eng.design_experiment(**DESIGN_KWARGS)
    assert d.procedure.counterbalancing is None
    fake_st = _render_design(monkeypatch, d)
    assert BALANCE_EXPANDER_LABEL not in fake_st.labels_of("expander")


# ---------- ③ LLM pending 状态机（future/cancel_id 全桩） ----------

class _FakeFuture:
    """concurrent.futures.Future 替身：done/result 可编程，零线程。"""

    def __init__(self, done=True, result=None, exc=None):
        self._done = done
        self._result = result
        self._exc = exc
        self.cancelled = False
        self.cancel_called = 0

    def done(self):
        return self._done

    def result(self):
        if self._exc is not None:
            raise self._exc
        return self._result

    def cancel(self):
        self.cancel_called += 1
        self.cancelled = True
        return True


def test_llm_pending_done_branch_applies_and_clears(monkeypatch, within_design):
    """done=True ⇒ 弹出 pending、_apply_llm_enhancement 被调、success 文案在。"""
    from src.ui import experiment_design_ui

    applied = []
    monkeypatch.setattr(experiment_design_ui, "_apply_llm_enhancement",
                        lambda eng, res: applied.append(res))
    fut = _FakeFuture(done=True, result={"ok": 1})
    state = {STATE_KEY: None,
             "_exp_design_pending": {"cancel_id": 7, "future": fut}}
    fake_st = _render_design(monkeypatch, within_design, extra_state=state)
    assert applied == [{"ok": 1}]
    assert "_exp_design_pending" not in fake_st.session_state
    assert any("LLM 增强完成" in str(x) for x in _all_success(fake_st))


def _all_success(fake_st):
    return [w.args[0] for w in fake_st.widgets if w.api == "success"]


def test_llm_pending_not_done_renders_info_and_cancel(monkeypatch, within_design):
    """done=False ⇒ info 文案＋取消按钮在、future.result 不被调。"""
    fut = _FakeFuture(done=False)
    calls = []
    fut.result = lambda: calls.append(1)  # 不应被调
    state = {STATE_KEY: None, "_exp_design_pending": {"cancel_id": 9, "future": fut}}
    fake_st = _render_design(monkeypatch, within_design, extra_state=state)
    assert calls == []
    assert any("正在通过大语言模型增强" in str(w.args[0])
               for w in fake_st.widgets if w.api == "info")
    assert "❌ 取消增强" in fake_st.labels_of("button")


def test_llm_pending_cancel_button_pops_and_warns(monkeypatch, within_design):
    """点取消 ⇒ cancel_design_request 被调＋pending 弹出＋warning 文案。"""
    from src.ui import experiment_design_ui

    cancelled = []
    monkeypatch.setattr(experiment_design_ui, "cancel_design_request",
                        lambda cid: cancelled.append(cid) or True)
    fut = _FakeFuture(done=False)
    state = {STATE_KEY: None,
             "_exp_design_pending": {"cancel_id": 11, "future": fut}}
    fake_st = _render_design(monkeypatch, within_design,
                             extra_state=state, pressed=("❌ 取消增强",))
    assert cancelled == [11]
    assert fut.cancel_called == 1
    assert "_exp_design_pending" not in fake_st.session_state
    assert any("已取消" in str(w.args[0]) for w in fake_st.widgets if w.api == "warning")


# ---------- 变异刀：counterbalancing 置恒 None 至少一条转红 ----------

def test_mutation_counterbalancing_always_none_turns_red(monkeypatch, within_design):
    proc = within_design.procedure
    original = proc.counterbalancing
    try:
        proc.counterbalancing = None  # 模拟「被试间恒 None」回归
        fake_st = _render_design(monkeypatch, within_design)
        assert BALANCE_EXPANDER_LABEL not in fake_st.labels_of("expander"), (
            "变异未生效：置 None 后 expander 仍渲染，本套件对 ② 无判别力")
    finally:
        proc.counterbalancing = original
    # 还原后复渲：真分支恢复在场（变异已还原、生产码零残留）
    fake_st2 = _render_design(monkeypatch, within_design)
    assert BALANCE_EXPANDER_LABEL in fake_st2.labels_of("expander")
