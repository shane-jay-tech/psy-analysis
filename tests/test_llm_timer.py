"""src/utils/llm_timer.py 取消机制与等待提示特征化测试（s918-21）。

纯状态函数＋上下文管理器：假 `st`、假时钟、`cancel_request` 打桩，**零 LLM、零网络、零等待**。
只钉状态机与文案，不评价提示语措辞。
锚点：src/utils/llm_timer.py:33，104 行。
"""
import pytest

import src.utils.llm_timer as lt


class Container:
    def __init__(self, sink):
        self.sink = sink

    def info(self, msg):
        self.sink.append(("info", msg))

    def error(self, msg):
        self.sink.append(("error", msg))

    def success(self, msg):
        self.sink.append(("success", msg))

    def empty(self, *a):
        self.sink.append(("empty", None))


class FakeStreamlit:
    def __init__(self, sink):
        self.session_state = {}
        self.sink = sink

    def empty(self):
        return Container(self.sink)


@pytest.fixture
def ui(monkeypatch):
    sink = []
    monkeypatch.setattr(lt, "st", FakeStreamlit(sink))
    return sink


@pytest.fixture
def clock(monkeypatch):
    ticks = {"t": 1_000.0}
    monkeypatch.setattr(lt.time, "time", lambda: ticks["t"])
    return ticks


def _state():
    return lt.st.session_state


def test_fresh_state_reports_no_cancel(ui):
    assert lt.is_cancel_requested() is False


def test_request_cancel_sets_the_flag_without_an_active_id(ui, monkeypatch):
    calls = []
    import src.llm_gateway.gateway as gw
    monkeypatch.setattr(gw, "cancel_request", lambda cid: calls.append(cid), raising=False)

    lt.request_cancel()

    assert lt.is_cancel_requested() is True
    assert calls == []


def test_set_active_cancel_id_then_cancel_notifies_the_gateway(ui, monkeypatch):
    calls = []
    import src.llm_gateway.gateway as gw
    monkeypatch.setattr(gw, "cancel_request", lambda cid: calls.append(cid), raising=False)

    lt.set_active_cancel_id("req-77")
    lt.request_cancel()

    assert calls == ["req-77"]
    assert _state()[lt._ACTIVE_CANCEL_ID_KEY] == "req-77"


def test_gateway_cancel_failure_is_swallowed_but_flag_survives(ui, monkeypatch):
    def boom(cid):
        raise RuntimeError("gateway gone")

    import src.llm_gateway.gateway as gw
    monkeypatch.setattr(gw, "cancel_request", boom, raising=False)
    lt.set_active_cancel_id("req-1")

    lt.request_cancel()

    assert lt.is_cancel_requested() is True


def test_clear_cancel_removes_both_keys(ui):
    lt.set_active_cancel_id("req-2")
    lt.request_cancel()

    lt.clear_cancel()

    assert lt.is_cancel_requested() is False
    assert lt._CANCEL_KEY not in _state() and lt._ACTIVE_CANCEL_ID_KEY not in _state()


def test_clear_cancel_is_idempotent_when_nothing_is_set(ui):
    lt.clear_cancel()
    lt.clear_cancel()

    assert lt.is_cancel_requested() is False


def test_llm_status_fast_success_blanks_the_container(ui, clock):
    with lt.llm_status("生成中") as container:
        clock["t"] += 1.0
        container.info("tick")

    kinds = [k for k, _ in ui]
    assert "success" not in kinds
    assert kinds[-1] == "empty"


def test_llm_status_slow_success_reports_elapsed_seconds(ui, clock):
    with lt.llm_status("生成中"):
        clock["t"] += 9.0

    successes = [m for k, m in ui if k == "success"]
    assert successes == ["✅ 生成中 — 完成 (9s)"]


def test_llm_status_failure_shows_model_and_elapsed_then_reraises(ui, clock):
    with pytest.raises(ValueError):
        with lt.llm_status("生成中", model_name="deepseek-v4-flash"):
            clock["t"] += 3.5
            raise ValueError("boom")

    errors = [m for k, m in ui if k == "error"]
    assert len(errors) == 1
    assert "生成中 — 失败 (4s)" in errors[0]
    assert "（模型: deepseek-v4-flash）" in errors[0]
    assert "建议：检查网络连接" in errors[0]


def test_llm_status_without_model_name_omits_the_parenthesis(ui, clock):
    with pytest.raises(KeyError):
        with lt.llm_status("生成中"):
            raise KeyError("k")

    errors = [m for k, m in ui if k == "error"]
    assert "（模型:" not in errors[0]


def test_entering_llm_status_clears_a_pending_cancel(ui, clock):
    lt.request_cancel()
    assert lt.is_cancel_requested() is True

    with lt.llm_status("再来一次"):
        assert lt.is_cancel_requested() is False


def test_timeout_hint_is_a_dead_parameter(ui):
    """`timeout_hint` 只出现在函数签名里，函数体从不读它——60s 阈值是写死的文案。
    调用方（如 quick_entries 的 `llm_status(..., timeout_hint=60)`）改这个值不会有任何效果。"""
    import inspect

    src = inspect.getsource(lt.llm_status.__wrapped__)

    assert src.count("timeout_hint") == 1
    assert "超过1分钟" in src
