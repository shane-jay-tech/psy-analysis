# -*- coding: utf-8 -*-
"""「保存笔记」按钮分支可达性钉桩（s920-21，只读追踪＋钉桩，**不改生产码**）。

追的是 s919-06 收口时自己留的那句「真实来源未定位」。追踪结论分三层：

1. **折叠不是原因**。`st.expander(..., expanded=False)` 只是给前端一个初始展开态：
   `.venv/.../streamlit/elements/layouts.py:1253/1260` 把 `expanded` 写进 block proto／serde，
   `:1307` 照常 `self.dg._block(...)` 返回容器 ⇒ **容器内的小组件每轮都创建**，
   折叠只影响"看不看得见"，不影响"跑不跑"。所以"点保存笔记没反应"不能怪 expander。
2. **锁也不是原因**。`_check_lock_or_warn` 两条出口现在都会发 warning（s919-06 补了 acquire 那条）。
3. **真凶是内容判空那一层**：`if new_content.strip():`（`literature_review_panel.py:458`）
   没有 else ⇒ 内容为空／只有空格时：不建笔记、不提示、不 rerun ⇒ 用户视角就是"毫无反应"。
   下面 A/B 两条用例分别钉"可达"与"这条静默分支"。

隔离：假 `st`（不起 Streamlit 运行时）、`_check_lock_or_warn` 打桩 ⇒ **不碰 session_state 真实键、不写库**。
"""
from contextlib import contextmanager

import pytest

import src.ui.literature_review_panel as pnl
from src.literature_review.models import LiteratureItem


class FakeState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


class FakeSt:
    """只实现 `_render_literature_detail` 走得到的那几面；其余一律当场报错，免得悄悄多跑分支。"""

    def __init__(self, *, content, clicked):
        self.session_state = FakeState()
        self.content = content            # text_area("内容") 的返回值
        self.clicked = clicked            # 哪些按钮本帧返回 True
        self.warnings = []
        self.infos = []
        self.reruns = 0

    def markdown(self, *a, **k):
        pass

    def caption(self, *a, **k):
        pass

    def write(self, *a, **k):
        pass

    def info(self, msg, *a, **k):
        self.infos.append(msg)

    def warning(self, msg, *a, **k):
        self.warnings.append(msg)

    def selectbox(self, label, options=None, index=0, **k):
        return options[index] if options else None

    def text_input(self, label, **k):
        return ""

    def text_area(self, label, value="", **k):
        if label == "内容":
            return self.content
        return value

    def button(self, label, **k):
        return label in self.clicked

    @contextmanager
    def expander(self, label, expanded=False, **k):
        # 与真 Streamlit 同构：expanded 只影响前端初始态，块内代码无条件执行
        yield

    def rerun(self):
        self.reruns += 1
        raise _NoRerun()


class _NoRerun(Exception):
    """真 st.rerun() 以异常终止本轮。"""


def _render(monkeypatch, *, content, clicked, lock="allow"):
    """跑一次详情渲染。`lock`：allow=直接放行；denied=走**真**的 _check_lock_or_warn（假 SessionLock）。

    `create_note` 不打桩——它是纯内存函数（notes.py:16-30 只 append），
    让它真跑才能验到"笔记确实进了 lr_state"这一层。
    """
    item = LiteratureItem(key="k1", title="测试文献")
    fake = FakeSt(content=content, clicked=clicked)
    monkeypatch.setattr(pnl, "st", fake)
    if lock == "allow":
        monkeypatch.setattr(pnl, "_check_lock_or_warn", lambda resource: True)
    else:
        class LockedLock:
            def __init__(self, _state):
                pass

            def is_locked(self, resource, by_others=False):
                return True

            def get_holder(self, resource):
                return "other_tab"

            def acquire(self, resource, **kw):
                return False

        monkeypatch.setattr(pnl, "SessionLock", LockedLock)
    lr_state = {}
    try:
        pnl._render_literature_detail([item], "k1", lr_state)
    except _NoRerun:
        pass
    return fake, lr_state


def test_collapsed_expander_branch_is_reachable_and_creates_the_note(monkeypatch):
    """A｜可达现状：内容非空＋点了「保存笔记」⇒ 建笔记、写回 lr_state、rerun 一次。

    这条顺带把"折叠导致不可达"的猜测**证伪**：假 expander 与真实现同构（块内无条件执行），
    分支照样跑通 ⇒ 说明用户看不到提示不是因为 expander 折叠。
    """
    fake, lr_state = _render(monkeypatch, content="这是一条真笔记", clicked={"保存笔记"})

    notes = lr_state.get("notes") or []
    assert len(notes) == 1 and notes[0]["content"] == "这是一条真笔记"
    assert fake.reruns == 1
    assert lr_state.get("notes"), "笔记要写回 lr_state，否则渲染时列表仍是空的"
    assert fake.warnings == []          # 成功路径不该有提示


def test_empty_content_click_is_silently_ignored(monkeypatch):
    """B｜不可达现状（真凶）：内容只有空格 ⇒ 不建笔记、**不发任何提示**、不 rerun ⇒ 就是"毫无反应"。

    与 `quick_entries` 那条（warning 被同帧 rerun 冲掉，s920-23）不同：**这里连提示都没发过**，
    所以修法也不同——需要一个 else 分支给"内容不能为空"的反馈，而不是调 rerun 时序。
    """
    fake, lr_state = _render(monkeypatch, content="   \n ", clicked={"保存笔记"})

    assert not lr_state.get("notes"), "内容判空 ⇒ 一条笔记都不该建"
    assert fake.reruns == 0
    assert lr_state == {}          # 连键都不该出现（出现即说明走了写入分支）
    assert fake.warnings == [] and fake.infos == [], "现状：这条分支零反馈——钉住它，加提示时本用例应翻正"


def test_lock_denial_is_not_silent(monkeypatch):
    """C｜排除项：锁拒绝时一定有 warning（s919-06 的成果），所以"毫无反应"不可能是锁造成的。"""
    fake, lr_state = _render(monkeypatch, content="有内容", clicked={"保存笔记"}, lock="denied")

    assert not lr_state.get("notes") and fake.reruns == 0
    assert len(fake.warnings) == 1 and "🔒" in fake.warnings[0]
