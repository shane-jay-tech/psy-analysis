# -*- coding: utf-8 -*-
"""src/ui/questionnaire_panel.py 分支头＋重入骨架钉桩（s920-10）。

按 `docs/insights/psy-questionnaire-panel-testdesign-20260918.md` 的口径做 B 类（假 st）与骨架普查，
**不做设计稿第 4 节的结构性抽取**（那是日间拍板的事）。

锚点复核（相对设计稿有一处漂移，按磁盘实况钉）：
- 设计稿 `st.rerun()` 记 **9 处**，磁盘实况 **8 处**（见 test_rerun_*）；`st.stop()` 仍 3 处（s920-10 时为 :43/:47/:517；s921-06/07 抽取后 :67/:71/:544；s922-02 加 anomaly 判据后 :80/:84/:564）。
- 本页确实零测试：`tests/test_app_routes_v6_panels.py:62` 那个同名用例 import 的是
  `src.ui.questionnaire_import_panel`（别的模块），不是本页。

假 `st` 的 `stop()` **抛异常**——真实 `st.stop()` 就是抛 `StopException` 结束脚本，
返回的话等于把"提前终止"钉成了"继续往下跑"。
"""
import ast
import inspect
import pathlib

import pytest

import src.ui.items_upload_panel as iup
import src.ui.questionnaire_import_panel as qip
import src.ui.questionnaire_panel as qp


class PageStopped(BaseException):
    """建模真实 `st.stop()`：它抛 `StopException`，基类是 **`BaseException`**
    （`streamlit/runtime/scriptrunner_utils/exceptions.py:22`）⇒ 业务侧 `except Exception` 吞不掉。
    假 st 的 stop 只返回等于把"提前终止"钉成"继续往下跑"。"""


class StrictSt:
    """只够跑分支头的假 st：多调一个方法就当场红。"""

    def __init__(self, radio_value, state=None):
        self.session_state = state if state is not None else {}
        self.radio_value = radio_value
        self.titles, self.captions = [], []
        self.radios, self.stops = [], 0
        self.anything_else = []

    def title(self, msg, **k):
        self.titles.append(msg)

    def caption(self, msg, **k):
        self.captions.append(msg)

    def radio(self, label, options, **k):
        self.radios.append((label, list(options), k))
        return self.radio_value

    def stop(self, **k):
        self.stops += 1
        raise PageStopped()

    def __getattr__(self, name):
        self.anything_else.append(name)
        raise AssertionError(f"分支头之后不该再碰 st.{name}（st.stop 没生效？）")


@pytest.fixture
def page(monkeypatch):
    """把两个外部子面板换成记录桩；返回 (记录本, 装 radio 值的工厂)。"""
    seen = {"upload": 0, "import": 0, "import_arg": None}

    def fake_upload():
        seen["upload"] += 1

    def fake_import(state):
        seen["import"] += 1
        seen["import_arg"] = state

    monkeypatch.setattr(iup, "render_items_upload_panel", fake_upload)
    monkeypatch.setattr(qip, "render_questionnaire_import_panel", fake_import)
    return seen, monkeypatch


def _run(st):
    qp.render_questionnaire_page()


# ─────────────────────────── A. 分支头（假 st） ───────────────────────────
def test_upload_branch_hands_off_to_items_panel_and_stops(page):
    seen, monkeypatch = page
    st = StrictSt("📤 上传现有题目（预审 + 排版导出）")
    monkeypatch.setattr(qp, "st", st)

    with pytest.raises(PageStopped):
        _run(st)

    assert seen["upload"] == 1 and seen["import"] == 0
    assert st.stops == 1
    assert st.titles == ["📋 问卷设计工具"]              # 只有页头，主页其余部分一帧都没渲染
    assert st.radios[0][1] == ["🆕 AI 设计新问卷", "📤 上传现有题目（预审 + 排版导出）", "📊 问卷数据导入与清洗"]
    assert st.radios[0][2]["key"] == "_q_sub_mode_radio" and st.radios[0][2]["horizontal"] is True


def test_import_branch_receives_the_live_session_state(page):
    seen, monkeypatch = page
    state = {"language": "zh"}
    st = StrictSt("📊 问卷数据导入与清洗", state=state)
    monkeypatch.setattr(qp, "st", st)

    with pytest.raises(PageStopped):
        _run(st)

    assert seen["import"] == 1 and seen["upload"] == 0
    assert seen["import_arg"] is state                   # 传的是**同一个** session_state 对象，不是副本
    assert st.stops == 1


def test_ai_design_branch_falls_through_without_stopping(page):
    seen, monkeypatch = page
    st = StrictSt("🆕 AI 设计新问卷")
    monkeypatch.setattr(qp, "st", st)

    with pytest.raises(AssertionError) as exc:          # 主页继续 ⇒ 撞到假 st 的未预期调用
        _run(st)

    assert "st.sidebar" in str(exc.value)               # 第一个未预期调用就是侧栏 ⇒ 确实往下走了
    assert seen["upload"] == 0 and seen["import"] == 0 and st.stops == 0


def test_branch_dispatch_is_emoji_prefix_only_so_label_edits_silently_fall_through(page):
    """现状风险钉桩：判据是 `startswith("📤")`。文案丢表情 ⇒ **不转交、悄悄回到 AI 设计页**。只钉不改。"""
    seen, monkeypatch = page
    for label in ("上传现有题目（预审 + 排版导出）", "", "📥 上传现有题目"):
        st = StrictSt(label)
        monkeypatch.setattr(qp, "st", st)
        with pytest.raises(AssertionError):
            _run(st)
        assert seen["upload"] == 0 and st.stops == 0


def test_sub_mode_radio_is_rendered_before_any_side_effect(page):
    """顺序契约：radio 必须先于转交（否则切换工作流要点两次）。"""
    _, monkeypatch = page
    st = StrictSt("📤 上传现有题目（预审 + 排版导出）")
    monkeypatch.setattr(qp, "st", st)

    with pytest.raises(PageStopped):
        _run(st)

    assert st.captions and st.radios and len(st.radios) == 1  # 页头两条文案＋一次 radio，然后立刻转交


# ─────────────────────── B. 重入骨架（源码普查） ───────────────────────
SRC = pathlib.Path(inspect.getsourcefile(qp))
BODY = SRC.read_text(encoding="utf-8")


def _call_names(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            yield sub.func.value, sub.func.attr


def test_page_is_still_one_monster_function():
    """抽取一旦发生，本用例红——那是好事，届时把普查数一起改掉（设计稿第 4 节的三个签名）。
    s921-06 已抽 classify_questionnaire_sub_mode ⇒ 按注释同步普查数。"""
    tree = ast.parse(BODY)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]

    assert [f.name for f in funcs] == ["classify_questionnaire_sub_mode", "compute_pending_elapsed", "pending_clock_anomaly", "render_questionnaire_page"]
    assert [c.name for c in classes] == ["_DummyContext"]
    fn = funcs[-1]
    assert fn.lineno == 64 and (fn.end_lineno - fn.lineno + 1) == 774   # s921-07 后 51/767；s922-02 加 pending_clock_anomaly 后 64/774


def test_reentry_is_all_via_rerun_with_zero_callbacks():
    """本页没有 on_click/on_change，全部交互靠 `st.rerun()` 重入 ⇒ 加回调属于骨架换范式，须先过这条。"""
    reruns = BODY.count("st.rerun()")
    stops = BODY.count("st.stop()")

    assert reruns == 8                                   # 设计稿记 9，磁盘实况 8（已留痕）
    assert stops == 3
    assert "on_click" not in BODY and "on_change" not in BODY


def test_stop_sites_are_the_two_branch_heads_plus_one_deep_in_report():
    lines = [(i, ln.strip()) for i, ln in enumerate(BODY.splitlines(), 1) if "st.stop()" in ln]

    assert [i for i, _ in lines] == [80, 84, 564]        # s921-06 后 58/62/532；s921-07 后 67/71/544；s922-02 加 anomaly 后 80/84/564
    assert lines[0][1].startswith("st.stop()") and lines[1][1].startswith("st.stop()")


def test_session_state_touches_are_20_and_three_keys_dominate():
    """20 处 `st.session_state.` 引用（设计稿口径），其中 language/questionnaire_design/_q_design_pending 是主写键。"""
    n = sum(1 for _ in BODY.splitlines() if "st.session_state" in _)

    assert len(BODY.splitlines()) == 837                 # s921-06 后 805；s921-07 后 817；s922-02 加 anomaly 与负秒钉后 837
    assert BODY.count("st.session_state.") >= 20
    for key in ("language", "questionnaire_design", "_q_design_pending", "_q_premium_mode"):
        assert key in BODY


def test_branch_head_prefixes_live_on_the_expected_lines():
    """s921-06 抽取后翻正：页面判据行变成对纯函数的调用（钉调用原文+行位），
    emoji 前缀串比较原文整体搬进 classify 体内（钉函数体原文）——两处判据仍逐字在钉。"""
    lines = BODY.splitlines()

    assert "    _q_sub_class = classify_questionnaire_sub_mode(_q_sub_mode)" == lines[75]
    assert 'if _q_sub_class == "upload_items":' == lines[76].strip()
    assert 'elif _q_sub_class == "import_clean":' == lines[80].strip()
    assert 'if choice.startswith("📤"):' == lines[34].strip()
    assert 'elif choice.startswith("📊"):' == lines[36].strip()
