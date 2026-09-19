# -*- coding: utf-8 -*-
"""隐私门禁弹窗测试（s918-42，fake st）。

覆盖 `src/ui/pages/privacy_gate.py:11` `render_privacy_gate()`（任务书锚点写 :13，
实际 def 在第 11 行、:13 是 `if not st.session_state.privacy_accepted:` 守卫——按磁盘实况修正）。
生产由 `app.py:319` 调用（:317 是 import），此前 42 行零测试。

手法参考 `tests/test_export_gate_global_scan.py:118` 的 fake st，但本模块读写
`st.session_state.privacy_accepted` 是**属性式**访问（非 dict 下标），故 fake 用对象承载。
StopException / RerunException 均继承 BaseException，镜像真实 Streamlit——
否则 production 的 `except Exception`（:38）会误吞 rerun 信号。
可复跑：.venv/Scripts/python.exe -m pytest tests/test_privacy_gate.py -q
"""
from __future__ import annotations

from contextlib import contextmanager

import pytest

from src.ui.pages import privacy_gate


class StopGate(BaseException):
    """镜像 st.stop()：必须 BaseException 才不被 except Exception 吞。"""


class RerunSignal(BaseException):
    """镜像 st.rerun()。"""


class FakeState:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeCol:
    def __init__(self, label):
        self.label = label

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSt:
    def __init__(self, session_state, button_value=False):
        self.session_state = session_state
        self._button_value = button_value
        self.markdown_calls = []
        self.stop_called = False
        self.rerun_called = False

    @contextmanager
    def container(self):
        yield self

    def markdown(self, text, **kw):
        self.markdown_calls.append(text)

    def columns(self, spec):
        assert spec == [1, 4]
        return FakeCol("c1"), FakeCol("c2")

    def button(self, *a, **k):
        return self._button_value

    def stop(self):
        self.stop_called = True
        raise StopGate()

    def rerun(self):
        self.rerun_called = True
        raise RerunSignal()


# --- 未同意路径 ---------------------------------------------------------------


def test_not_accepted_renders_declaration_and_stops(monkeypatch):
    called = {"pref": False}
    monkeypatch.setattr("src.utils.user_prefs.update_pref",
                        lambda *a, **k: called.__setitem__("pref", True), raising=True)

    st = FakeSt(FakeState(privacy_accepted=False))
    monkeypatch.setattr(privacy_gate, "st", st)

    with pytest.raises(StopGate):
        privacy_gate.render_privacy_gate()

    assert len(st.markdown_calls) == 2
    assert "隐私声明" in st.markdown_calls[0]
    assert "数据隐私承诺" in st.markdown_calls[1]
    assert st.stop_called is True
    assert st.rerun_called is False
    assert called["pref"] is False  # 没点按钮不该落盘


# --- 已同意路径 ---------------------------------------------------------------


def test_accepted_renders_nothing_and_does_not_stop(monkeypatch):
    st = FakeSt(FakeState(privacy_accepted=True))
    monkeypatch.setattr(privacy_gate, "st", st)

    privacy_gate.render_privacy_gate()  # 不抛

    assert st.markdown_calls == []
    assert st.stop_called is False


# --- 点「同意」：写状态 + 落盘 + rerun ----------------------------------------


def test_agree_click_sets_state_persists_and_reruns(monkeypatch):
    prefs = []
    monkeypatch.setattr("src.utils.user_prefs.update_pref",
                        lambda k, v: prefs.append((k, v)), raising=True)

    st = FakeSt(FakeState(privacy_accepted=False), button_value=True)
    monkeypatch.setattr(privacy_gate, "st", st)

    # 点同意 → st.rerun() 抛 RerunSignal，先于外层 st.stop()
    with pytest.raises(RerunSignal):
        privacy_gate.render_privacy_gate()

    assert st.session_state.privacy_accepted is True
    assert prefs == [("privacy_accepted", True)]
    assert st.rerun_called is True


def test_agree_click_pref_failure_still_reruns(monkeypatch):
    """update_pref 落盘失败被 :38 `except Exception` 吞；会话内仍应同意并 rerun。"""
    def boom(*a, **k):
        raise OSError("prefs 文件被占用")

    monkeypatch.setattr("src.utils.user_prefs.update_pref", boom, raising=True)
    st = FakeSt(FakeState(privacy_accepted=False), button_value=True)
    monkeypatch.setattr(privacy_gate, "st", st)

    with pytest.raises(RerunSignal):
        privacy_gate.render_privacy_gate()

    assert st.session_state.privacy_accepted is True
    assert st.rerun_called is True


# --- 键缺失时的降级契约（超出任务书 3-4 条区间，见 result 遗留问题 1）-----------


def test_missing_key_raises_instead_of_showing_declaration(monkeypatch):
    """`st.session_state.privacy_accepted` 是属性式读取（:13）。键不存在时真实
    Streamlit 1.59.1 抛 AttributeError（已实测），即门禁**不降级为弹声明**而是崩红框。
    生产靠 `app.py:299-301` 的 _defaults 兜底先种 False，故门禁本身不自给自足。"""
    st = FakeSt(FakeState())  # 没有任何 session 键
    monkeypatch.setattr(privacy_gate, "st", st)

    with pytest.raises(AttributeError):
        privacy_gate.render_privacy_gate()

    assert st.markdown_calls == []  # 声明一行都没渲染出来
