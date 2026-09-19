# -*- coding: utf-8 -*-
"""快捷入口归档 warning 与 st.rerun() 的**同帧时序**钉桩（s920-23，**不改生产码**）。

起因：`src/ui/quick_entries.py:724` 发 `st.warning("⚠️ 结果已生成，但归档失败…")`，
而同一函数末尾 `:729` 就是 `st.rerun()`（s919-13 收口时自己留的话："提示可能一闪而过"）。
本文件只把这份时序现状钉成可复跑的断言，供日间决定"要不要改成先落 pending 提示再 rerun"。
红线：不断言任何统计量、不判显著性；归档函数打桩，**绝不往真实归档目录写**。
"""
from contextlib import contextmanager

import pandas as pd
import pytest

import src.ui.quick_entries as qe
import src.utils.archive_manager as archive_manager


class RerunRequested(Exception):
    """真实 `st.rerun()` 以异常终止本轮脚本运行，这里同构模拟。"""


class FakeState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        self.pop(key, None)


class EventSt:
    """按**发生顺序**记录 UI 事件的假 st —— 本单的全部价值都在这条流水账上。"""

    def __init__(self):
        self.session_state = FakeState()
        self.events = []

    @contextmanager
    def spinner(self, *args, **kwargs):
        self.events.append(("spinner-enter", args[0] if args else ""))
        yield
        self.events.append(("spinner-exit", args[0] if args else ""))

    def rerun(self):
        self.events.append(("rerun", None))
        raise RerunRequested()

    def warning(self, msg):
        self.events.append(("warning", msg))

    def success(self, msg):
        self.events.append(("success", msg))

    def info(self, msg):
        self.events.append(("info", msg))

    def __getattr__(self, name):
        raise AssertionError(f"本单不该触发页面渲染: st.{name}")


DF = pd.DataFrame({"分数": [3, 4, 5, 6, 7, 8, 3, 4, 5, 6, 7, 8],
                   "组别": ["A"] * 6 + ["B"] * 6})


@pytest.fixture
def st_env(monkeypatch):
    fake = EventSt()
    monkeypatch.setattr(qe, "st", fake)
    return fake


def _run_events(stub):
    """跑一次快捷分析（吞掉 rerun 抛出的控制流异常），返回 UI 事件流水。"""
    try:
        qe._run_quick_analysis(DF, "independent_ttest", dv="分数", iv="组别")
    except RerunRequested:
        pass
    return stub.events


def test_archive_failure_warning_is_immediately_followed_by_rerun(st_env, monkeypatch):
    """现状：warning 发出后**同一帧**立刻 rerun ⇒ 中间没有任何让 Streamlit 把提示画出来的机会。

    断言用的是"warning 之后的事件序"，不是"有没有 warning"——后者 s919-13 已钉过，本单钉的是**时序**。
    现状序是 `warning → spinner-exit → rerun`（warning 发在 `with st.spinner(...)` 内），
    全程没有渲染点 ⇒ "一闪而过"有实证。
    """
    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(archive_manager, "archive_analysis", boom)

    events = _run_events(st_env)
    kinds = [e[0] for e in events]
    idx = kinds.index("warning")

    assert events[idx][1].startswith("⚠️ 结果已生成，但归档失败")
    # 实测中间只夹一个 spinner-exit：warning 是在 `with st.spinner(...)` 里发的，
    # 退出 spinner 之后就是 rerun ⇒ 两者之间没有任何"让 Streamlit 把提示画出来"的渲染点。
    assert kinds[idx + 1:] == ["spinner-exit", "rerun"], f"warning 后的事件序变了：{kinds[idx + 1:]}"
    assert kinds.count("warning") == 1 and kinds.count("rerun") == 1


def test_no_rerun_happens_before_the_analysis_is_written(st_env, monkeypatch):
    """反向对照：rerun 一定发生在结果落进 session_state **之后**（这条决定"改不改"的边界）。

    若哪天有人为了保住 warning 把 rerun 提前，结果就没了——本断言让那种改法当场红。
    """
    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(archive_manager, "archive_analysis", boom)

    _run_events(st_env)
    kinds = [e[0] for e in st_env.events]
    assert "analysis_output" in st_env.session_state, "rerun 前结果必须已写入，否则用户连结果都看不到"
    assert kinds[-1] == "rerun"


def test_successful_archive_still_reruns_without_warning(st_env, monkeypatch):
    """归档成功时：零 warning、一次 rerun ⇒ 说明"一闪而过"只发生在失败分支，别把它当全局问题修。"""
    monkeypatch.setattr(archive_manager, "archive_analysis", lambda *a, **k: None)

    kinds = [e[0] for e in _run_events(st_env)]

    assert "warning" not in kinds
    assert kinds.count("rerun") == 1


def test_kb_failure_warning_has_no_rerun_in_its_frame():
    """另一条 s919-13 补的 warning（KB 查询失败）**不受此影响**：它所在函数里没有 rerun。

    用源码静态判：`_render_ai_item_review_form`（`quick_entries.py:518`）从 warning 到函数结尾
    不含 `st.rerun(` ⇒ 日间只需处理归档那一条，别顺手改两处。
    """
    import inspect

    src = inspect.getsource(qe._render_ai_item_review_form)
    at = src.index("st.warning")

    assert "KB 查询失败" in src[at:at + 120]
    assert "st.rerun(" not in src[at:], "KB 分支所在函数出现了 rerun，本断言的前提（同帧不冲掉）已失效"
