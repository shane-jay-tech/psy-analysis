# -*- coding: utf-8 -*-
"""startup_checks 行为等价断言（d913b-48，拆分第二批）。

验证 src/ui/startup_checks.py 两函数与原 app.py 内联块行为逐字等价：
- run_once_env_check：每会话首跑执行自检+toast，重跑不再执行（startup_check_done 门）；
  自检异常吞掉并置 env_status=None（v5.8 白屏保护语义）。
- run_once_startup_cleanup：每会话首跑清理一次（has_auto_cleaned 门），重跑不再执行；
  异常静默。

st 以假件替换（_FakeSessionState 支持 in/属性两种语义，对齐 streamlit 行为），
env_check / memory_manager 依赖走 monkeypatch，零真实副作用。
"""
import sys
import types
from pathlib import Path

import pytest

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui import startup_checks  # noqa: E402


class _FakeSessionState:
    """属性语义对齐 streamlit：未设键读取即 AttributeError；支持 `in` 判存。"""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, key):
        return key in self.__dict__


@pytest.fixture()
def fake_st(monkeypatch):
    st = types.SimpleNamespace(session_state=_FakeSessionState(startup_check_done=False, env_status=None))
    monkeypatch.setattr(startup_checks, "st", st)
    return st


def test_env_check_runs_once_then_gated(fake_st, monkeypatch):
    """首跑：自检+toast 按序各一次；重跑：门生效零调用（调用序列等价断言）。"""
    calls = []

    def fake_run_check():
        calls.append("check")
        return {"python": "ok"}

    def fake_toasts(status):
        calls.append(f"toast:{status}")

    import src.utils.env_check as env_check
    monkeypatch.setattr(env_check, "run_startup_check", fake_run_check)
    monkeypatch.setattr(env_check, "render_env_status_toasts", fake_toasts)

    startup_checks.run_once_env_check()
    startup_checks.run_once_env_check()

    assert calls == ["check", "toast:{'python': 'ok'}"], "首跑一次自检+一次 toast，重跑零调用"
    assert fake_st.session_state.startup_check_done is True
    assert fake_st.session_state.env_status == {"python": "ok"}


def test_env_check_swallows_failure_and_keeps_none(fake_st, monkeypatch):
    """自检异常 → env_status=None 且不外抛（v5.8 白屏保护等价断言）。"""
    import src.utils.env_check as env_check

    def boom():
        raise RuntimeError("check failed")

    monkeypatch.setattr(env_check, "run_startup_check", boom)
    startup_checks.run_once_env_check()
    assert fake_st.session_state.env_status is None
    assert fake_st.session_state.startup_check_done is True


def test_cleanup_runs_once_then_gated(fake_st, monkeypatch):
    """首跑清理一次；重跑门生效（has_auto_cleaned）。"""
    calls = []

    def fake_cleanup(older_than_days=7):
        calls.append(older_than_days)
        return {"cleaned": 3}

    import src.utils.memory_manager as memory_manager
    monkeypatch.setattr(memory_manager, "cleanup_literature_cache", fake_cleanup)

    startup_checks.run_once_startup_cleanup()
    startup_checks.run_once_startup_cleanup()

    assert calls == [7], "首跑一次清理（7 天口径），重跑零调用"
    assert fake_st.session_state.has_auto_cleaned is True


def test_cleanup_swallows_exception(fake_st, monkeypatch):
    """清理异常 → 静默吞掉（与原内联块 except: pass 等价）。"""
    import src.utils.memory_manager as memory_manager

    def boom(older_than_days=7):
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(memory_manager, "cleanup_literature_cache", boom)
    startup_checks.run_once_startup_cleanup()  # 不应抛出
    assert fake_st.session_state.has_auto_cleaned is True
