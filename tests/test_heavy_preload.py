"""src/ui/heavy_preload.py 特征化测试（s918-20）。

仿 `tests/test_startup_checks.py` 的假件先例：假 session_state ＋ `threading.Thread` 打桩，
**不真起线程、不真导入 9 个重型依赖**。钉两条行为：会话门「只起一次」＋预热异常静默。
src 零改动。
"""
import sys

import pytest

from src.ui import heavy_preload as hp


class _FakeSessionState:
    """读用语义对齐 streamlit：`.get(key)` 缺键返回默认值，属性式写入。"""

    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getattr__(self, item):
        if item.startswith("_data"):
            raise AttributeError(item)
        return self._data[item]

    def __setattr__(self, key, value):
        if key == "_data":
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    def snapshot(self):
        return dict(self._data)


class ThreadSpy:
    started = []
    boom = False

    def __init__(self, target=None, daemon=None, name=None):
        self.target, self.daemon, self.name = target, daemon, name

    def start(self):
        if ThreadSpy.boom:
            raise RuntimeError("cannot spawn thread")
        ThreadSpy.started.append(self)


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    ThreadSpy.started = []
    ThreadSpy.boom = False
    monkeypatch.setattr(hp.threading, "Thread", ThreadSpy)
    state = _FakeSessionState()
    monkeypatch.setattr(hp, "st", type("FakeST", (), {"session_state": state}))
    return state


def test_first_call_spawns_one_daemon_thread_named_heavy_preload(reset):
    hp.start_heavy_preload_once()

    assert len(ThreadSpy.started) == 1
    spawned = ThreadSpy.started[0]
    assert spawned.daemon is True
    assert spawned.name == "heavy-preload"
    assert spawned.target is hp.preload_heavy_deps


def test_gate_flag_is_set_on_the_first_call(reset):
    hp.start_heavy_preload_once()

    assert reset.snapshot() == {"_heavy_preload_started": True}


def test_second_call_in_the_same_session_spawns_nothing(reset):
    hp.start_heavy_preload_once()
    hp.start_heavy_preload_once()
    hp.start_heavy_preload_once()

    assert len(ThreadSpy.started) == 1


def test_a_fresh_session_starts_again(reset, monkeypatch):
    hp.start_heavy_preload_once()

    fresh = _FakeSessionState()
    monkeypatch.setattr(hp, "st", type("FakeST", (), {"session_state": fresh}))
    hp.start_heavy_preload_once()

    assert len(ThreadSpy.started) == 2


def test_thread_spawn_failure_is_swallowed_and_the_session_stops_trying(reset):
    """起线程失败被吞，但门已经先落下 ⇒ 本会话**再也不会重试预热**（静默降级为无预热）。"""
    ThreadSpy.boom = True

    hp.start_heavy_preload_once()

    assert reset.snapshot() == {"_heavy_preload_started": True}
    assert ThreadSpy.started == []

    ThreadSpy.boom = False
    hp.start_heavy_preload_once()
    assert ThreadSpy.started == []


def test_preload_swallows_import_failure(monkeypatch):
    monkeypatch.setitem(sys.modules, "scipy.stats", None)  # 让首个 import 直接失败

    hp.preload_heavy_deps()  # 不抛即通过


HEAVY_ROOTS = {"semopy", "statsmodels", "pingouin", "factor_analyzer"}


def _loaded_heavy():
    return {m for m in sys.modules if m.split(".")[0] in HEAVY_ROOTS}


def test_the_warmup_body_never_runs_in_this_process(reset):
    """自证门：线程被桩化 ⇒ 预热线程体没跑，本次调用不该**新增**任何重型模块。
    用差分而非「不在 sys.modules」：合跑时前面的测试文件可能已载入这些库。"""
    before = _loaded_heavy()

    hp.start_heavy_preload_once()

    assert _loaded_heavy() == before


def test_all_nine_warmup_imports_share_one_try_block():
    """九条 import 同在一个 try 内 ⇒ **任一依赖挂了就整批不预热**（后面的模块白没暖）。
    静态钉结构：1 个 except、9 条 import。"""
    import inspect

    src = inspect.getsource(hp.preload_heavy_deps)

    assert src.count("except") == 1
    assert src.count("import ") == 9
