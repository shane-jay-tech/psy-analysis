# -*- coding: utf-8 -*-
"""src/ui/paper_writing_ui.py 渲染分支骨架＋写键面钉桩（s920-09）。

锚点复核（成立）：`:38 render_paper_writing_ui()`、`:606 _render_paper_mode_defense_qa()`——678 行仅 2 个顶层函数，
`tests/` 全树**零命中**，唯一调用方是 `app.py:2551-2554`。
脚手架仿 `tests/test_quick_entries_min.py` 的假 st 路子，但本页用到 27 种 `st.*` ⇒ 假 st 是**宽容记录型**；
外部动作（`PaperEngine`、`generate_defense_qa`、文件导入）下死桩 ⇒ 零网络、零 LLM、零真实会话。
"""
import os
import pathlib
import re
from types import SimpleNamespace

import pytest

import src.ui.paper_writing_ui as pwu

_CTX_ATTR = {"sidebar", "main"}            # `with st.sidebar:` —— 属性访问
_CTX_CALL = {"expander", "container", "spinner", "form", "popover", "status"}  # `with st.expander(...):` —— 调用


class RerunRequested(BaseException):
    """真实 `st.rerun()` 抛 `RerunException`，其基类是 **`BaseException`**（`streamlit/runtime/scriptrunner_utils/exceptions.py:22`）
    ⇒ 业务代码里的 `except Exception:` **吞不掉它**，重跑照样发生。
    假 st 若只返回、或派生自 Exception，就会把这条路径钉歪（本单第一版正是被页面的
    `try: import…/st.success/st.rerun() except Exception` 把重跑吞成了"导入失败"）。"""


class FakeState(dict):
    """`st.session_state` 既有属性式读写也有 get/pop/setdefault ⇒ 两种都得支持。"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        self.pop(name, None)


class _Ctx:
    def __init__(self, host, name):
        self.host, self.name = host, name

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __getattr__(self, item):
        return self.host._make(f"{self.name}.{item}")


class RecordingSt:
    """记录型假 st：控件按 `values` 给值，容器返回 ctx，`button` 按 `clicked` 给真。"""

    def __init__(self, values=None, clicked=()):
        self.calls = []
        self.values = dict(values or {})
        self.clicked = set(clicked)
        self.session_state = FakeState()

    def _make(self, name):
        def fn(*a, **k):
            self.calls.append((name, a, k))
            return self._default(name, a, k)

        return fn

    def _default(self, name, a, k):
        if name in self.values:
            v = self.values[name]
            return v(a, k) if callable(v) else v     # 可按 label 分派（同名控件在多个 tab 里出现）
        leaf = name.rsplit(".", 1)[-1]
        if leaf == "rerun":
            raise RerunRequested()
        if leaf == "button":
            label = a[0] if a else k.get("label")
            return label in self.clicked or k.get("key") in self.clicked
        if leaf == "tabs":
            return [_Ctx(self, f"tab{i}") for i in range(len(a[0] if a else k.get("labels", [])))]
        if leaf == "columns":
            spec = a[0] if a else k.get("spec", 1)
            n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
            return [_Ctx(self, f"col{i}") for i in range(n)]
        if leaf in _CTX_CALL:
            return _Ctx(self, leaf)
        if leaf == "checkbox":
            return k.get("value", False)          # 回显默认值：勾选态是**从状态读出来**的
        if leaf in ("text_input", "text_area", "slider", "number_input", "selectbox"):
            return k.get("value")
        return None

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name in _CTX_ATTR:
            return _Ctx(self, name)
        return self._make(name)

    @property
    def names(self):
        return [c[0] for c in self.calls]

    def msgs(self, kind):
        return [str(a[0]) for n, a, k in self.calls if (n == kind or n.endswith("." + kind)) and a]

    def kwargs_of(self, kind):
        return [k for n, a, k in self.calls if n == kind or n.endswith("." + kind)]


from src.paper_writer import PaperEngine as RealPaperEngine


@pytest.fixture
def engines(monkeypatch):
    """用**真** PaperEngine（init 0.7s、纯内存，不碰网络），只挂个计数器看渲染调了几遍。"""
    made = []

    def factory():
        eng = RealPaperEngine()
        eng.gaps_calls, eng.imported = 0, []
        orig = eng.get_gaps_summary

        def counted(*a, **k):
            eng.gaps_calls += 1
            return orig(*a, **k)

        monkeypatch.setattr(eng, "get_gaps_summary", counted)
        made.append(eng)
        return eng

    monkeypatch.setattr(pwu, "PaperEngine", factory)
    return made


class FakeUpload:
    name = "methods.json"

    def getvalue(self):
        return b"{}"


def _prime(st):
    """按 app.py 的预置口径把三个属性式读的键建出来。"""
    for key in ("paper_engine", "analysis_output", "plan"):
        setattr(st.session_state, key, None)


def _qa_item(i=0, diff="常问"):
    return SimpleNamespace(question_id=f"q{i}", question=f"问题{i}", answer=f"答{i}",
                           category_label="方法", difficulty=diff)


# ─────────────────────────── 入口与骨架 ───────────────────────────
def test_entry_builds_engine_once_then_reuses_the_same_object(engines, monkeypatch):
    st = RecordingSt()
    monkeypatch.setattr(pwu, "st", st)
    _prime(st)

    pwu.render_paper_writing_ui()
    first = st.session_state.paper_engine
    pwu.render_paper_writing_ui()

    assert len(engines) == 1                    # 第二次 render **不重建**引擎
    assert st.session_state.paper_engine is first
    assert first.gaps_calls > 0


@pytest.mark.parametrize("missing", ["paper_engine", "analysis_output"])
def test_three_keys_are_assumed_present_by_the_page(engines, monkeypatch, missing):
    """现状耦合：本页用**属性式**读 `paper_engine / analysis_output / plan`，键不存在就 AttributeError。
    预置这两个键是 app.py 的责任（值是 None 才走到懒建/判空分支）。
    `plan` 不走属性式读取（它在答辩分支里是 `.get("plan")`），故不在本清单内。"""
    st = RecordingSt()
    monkeypatch.setattr(pwu, "st", st)
    for key in ("paper_engine", "analysis_output", "plan"):
        if key != missing:
            setattr(st.session_state, key, None)

    with pytest.raises(AttributeError):
        pwu.render_paper_writing_ui()


def test_missing_engine_is_the_only_bootstrap_path_and_reset_rebuilds_it(engines, monkeypatch):
    st = RecordingSt(clicked={"🔄 重置论文"})
    monkeypatch.setattr(pwu, "st", st)
    _prime(st)

    with pytest.raises(RerunRequested):         # 重置 ⇒ 必须重进本页
        pwu.render_paper_writing_ui()

    assert len(engines) == 2                    # 懒建一个 + 重置再建一个
    assert st.session_state.paper_engine is engines[1]
    assert engines[1].gaps_calls == 0           # 关键现状：新引擎本轮**还没渲染过**
    assert engines[0].gaps_calls == 2           # 旧实例只走到第 2 次取缺口就被 rerun 打断；
    # 第 3 次调用在 tab4 深处（整页渲染完才有 3）⇒ 少这次 rerun 的话，界面停在半个新状态上

    st2 = RecordingSt()
    monkeypatch.setattr(pwu, "st", st2)
    _prime(st2)
    st2.session_state.paper_engine = engines[1]
    pwu.render_paper_writing_ui()
    assert len(engines) == 2                    # 键已存在且非 None ⇒ 不再新建
    assert st2.session_state.paper_engine is engines[1]


def test_five_tabs_are_the_skeleton_and_the_page_runs_start_to_finish(engines, monkeypatch):
    st = RecordingSt()
    monkeypatch.setattr(pwu, "st", st)
    _prime(st)

    pwu.render_paper_writing_ui()               # 不抛 = 冒烟通过

    tab_calls = [c for c in st.calls if c[0] == "tabs"]
    assert len(tab_calls) == 1
    assert tab_calls[0][1][0] == ["1️⃣ 研究信息", "2️⃣ 文献管理", "3️⃣ 确认问题", "4️⃣ 生成论文", "5️⃣ 答辩模拟"]
    assert any("论文写作" in m for m in st.msgs("title"))
    assert any("填写研究信息" in c for c in st.msgs("caption"))
    assert st.session_state.paper_engine.gaps_calls == 3   # 现状：一次渲染里 get_gaps_summary 被调 3 遍，只钉不改


def test_methods_file_import_failure_is_a_visible_error_not_a_crash(engines, monkeypatch):
    def boom_import(self, path):
        self.imported.append(path)
        raise ValueError("JSON 字段缺失")

    st = RecordingSt(values={"file_uploader": lambda a, k: FakeUpload()
                             if a and a[0] == "上传方法信息文件" else None})
    monkeypatch.setattr(RealPaperEngine, "import_methods_from_file", boom_import, raising=False)
    monkeypatch.setattr(pwu, "st", st)
    _prime(st)

    try:
        pwu.render_paper_writing_ui()
        assert any("导入失败" in e for e in st.msgs("error")), st.msgs("error")
        assert "已导入方法信息" not in "".join(st.msgs("success"))
        assert "rerun" not in st.names          # 失败不许重跑（一跑就把错误提示刷没了）
    finally:
        leaked = engines[0].imported
        assert leaked                            # 确实把上传内容落成临时文件了
        for path in leaked:                      # 现状：delete=False，文件留在盘上，本用例顺手清掉
            if os.path.exists(path):
                os.remove(path)


def test_methods_file_import_success_reports_and_reruns(engines, monkeypatch):
    st = RecordingSt(values={"file_uploader": lambda a, k: FakeUpload()
                             if a and a[0] == "上传方法信息文件" else None})
    monkeypatch.setattr(RealPaperEngine, "import_methods_from_file",
                        lambda self, path: self.imported.append(path), raising=False)
    monkeypatch.setattr(pwu, "st", st)
    _prime(st)

    try:
        with pytest.raises(RerunRequested):     # 导入成功 ⇒ 立刻重跑，让新数据回灌界面
            pwu.render_paper_writing_ui()
        assert any("已导入方法信息" in m for m in st.msgs("success"))
        assert "rerun" in st.names
        assert st.msgs("error") == []
    finally:
        for path in engines[0].imported:
            if os.path.exists(path):
                os.remove(path)


# ──────────────────── 答辩模拟分支 ────────────────────
@pytest.mark.parametrize("state", [
    {},
    {"plan": SimpleNamespace()},
    {"analysis_output": {"test_type": "t"}},
])
def test_defense_branch_needs_both_plan_and_output(state, monkeypatch):
    st = RecordingSt()
    st.session_state.update(state)
    monkeypatch.setattr(pwu, "st", st)
    called = []
    monkeypatch.setattr(pwu, "generate_defense_qa", lambda **k: called.append(k))

    pwu._render_paper_mode_defense_qa()

    assert any("数据分析" in i for i in st.msgs("info"))       # 缺件时给的是去路，不是空白页
    assert called == [] and "_paper_defense_qa_items" not in st.session_state


def test_defense_generation_waits_for_the_click_then_writes_one_key(monkeypatch):
    st = RecordingSt()
    st.session_state.update({"plan": SimpleNamespace(),
                             "analysis_output": {"test_type": "pearson_corr", "test_name_zh": "Pearson相关"}})
    seen = {}
    monkeypatch.setattr(pwu, "generate_defense_qa",
                        lambda **k: seen.update(k) or [_qa_item(0), _qa_item(1)])
    monkeypatch.setattr(pwu, "group_qa_by_difficulty", lambda items: {"常问": items})
    monkeypatch.setattr(pwu, "render_qa_as_markdown", lambda items: "# md")
    monkeypatch.setattr(pwu, "st", st)

    pwu._render_paper_mode_defense_qa()
    assert seen == {} and "_paper_defense_qa_items" not in st.session_state   # 没点按钮绝不偷跑 LLM

    st2 = RecordingSt(clicked={"paper_defense_qa_gen"})
    st2.session_state.update(st.session_state)
    monkeypatch.setattr(pwu, "st", st2)
    pwu._render_paper_mode_defense_qa()

    assert seen["max_items"] == 7 and seen["ctx"]["test_name_zh"] == "Pearson相关"
    assert len(st2.session_state["_paper_defense_qa_items"]) == 2
    assert any(n.endswith("spinner") or n == "spinner" for n in st2.names)   # 生成期有等待反馈


def test_rendering_existing_questions_writes_mastered_state_without_any_click(monkeypatch):
    """现状：问答一渲染就把每题勾选值写回 `paper_defense_qa_mastered`（`setdefault` 拿的是同一个 dict），
    不需要任何点击。只钉不改。"""
    st = RecordingSt()
    st.session_state.update({"plan": SimpleNamespace(),
                             "analysis_output": {"test_type": "t", "test_name_zh": "方法"},
                             "_paper_defense_qa_items": [_qa_item(0)]})
    monkeypatch.setattr(pwu, "group_qa_by_difficulty", lambda items: {"常问": items})
    monkeypatch.setattr(pwu, "render_qa_as_markdown", lambda items: "# md")
    monkeypatch.setattr(pwu, "st", st)

    pwu._render_paper_mode_defense_qa()

    assert st.session_state["paper_defense_qa_mastered"] == {"q0": False}
    assert any("已生成 1 个问题" in m for m in st.msgs("markdown"))
    assert "🟡 常问" in "".join(st.msgs("markdown"))


def test_write_surface_is_exactly_six_session_keys():
    """写键清单（源码普查）：本页只碰这 6 个键，多一个就算越界。"""
    text = pathlib.Path(pwu.__file__).read_text(encoding="utf-8")
    keys = set(re.findall(r'st\.session_state\.(?:get|pop|setdefault)\(\s*["\']([_a-zA-Z]+)["\']', text))
    keys |= set(re.findall(r"st\.session_state\.([a-zA-Z_]+)", text)) - {"get", "pop", "setdefault"}
    keys |= set(re.findall(r'st\.session_state\[\s*["\']([_a-zA-Z]+)["\']\s*\]', text))

    assert keys == {"paper_engine", "analysis_output", "plan", "_lit_search_pending",
                    "_paper_defense_qa_items", "paper_defense_qa_mastered"}
    assert text.count("st.session_state.pop(") == 2          # _lit_search_pending 用后即摘
    assert "on_click" not in text and "on_change" not in text  # 与 questionnaire_panel 同构：全靠 rerun 重入
