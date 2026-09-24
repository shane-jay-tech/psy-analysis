"""s923-46：llm_gateway 流式/异步三出口的离线补面。

覆盖对象（src/llm_gateway/gateway.py）：
- ``llm_chat_stream``（:577）—— 块顺序、取消传播、异常吞并、缓存与 trace
- ``llm_chat_async_stream``（:647）—— callback 包装顺序、取消、异常吞并、回值类型
- ``llm_chat_async``（:696）—— 回值形状与一次性调用的一致性

全件零联网：
- 流式出口走 ``_install_fake_stream`` 把 ``ai_tutor.chat_with_tutor_stream`` 换成假上游；
- 一次性/异步出口走 ``register_llm_backend`` 注册的假后端；
- 外加 ``_block_real_network`` 的 socket 闸兜底（任何真实连接当场报错）。

实测钉（现状行为，与"应当如何"不同的地方在各用例 docstring 里点名，见 result 的证据节）：
- 流式出口 **不查** ``_BACKENDS`` 注册表（写死 import chat_with_tutor_stream）；
- 网关侧取消 **不抛** ``CancelledLLMError``（该类在 gateway.py 只定义、无 raise 站点）；
- 上游异常与流内异常一律被吞，只落 trace，不向消费者传播。
"""

from __future__ import annotations

import socket
import threading
import time

import pytest

from src.llm_gateway import (
    LLMResponse,
    LLMUnavailableError,
    cancel_request,
    clear_cache,
    clear_traces,
    get_trace_summary,
    llm_chat,
    llm_chat_async,
    llm_chat_async_stream,
    llm_chat_stream,
    register_llm_backend,
    set_cache_enabled,
)


# ---------------------------------------------------------------------------
# 夹具与助手
# ---------------------------------------------------------------------------

def _ok_config(model: str = "s92346-model") -> dict:
    """显式注入配置，绕开 _resolve_llm_config()（避免读 env/session 造成不确定性）。"""
    return {
        "provider": "openai", "base_url": "https://gateway.invalid/v1",
        "api_key": "sk-s92346-offline", "model": model, "timeout": 5,
    }


def _msgs(tag: str) -> list:
    """每个用例唯一 tag ⇒ 缓存键互不相同，用例之间不受执行顺序影响。"""
    return [{"role": "user", "content": f"s92346::{tag}"}]


def _last_trace() -> dict:
    import streamlit as st
    traces = st.session_state.get("llm_traces") or []
    assert traces, "trace 未落 session_state —— 本用例的断言前提失效，必须显式失败"
    return traces[-1]


@pytest.fixture(autouse=True)
def _block_real_network(monkeypatch):
    """socket 闸：本文件任何用例都不许摸真网络。

    先预热 streamlit / gateway 的惰性 import，再置闸，避免把"首次 import"误判成联网。
    """
    import streamlit as st  # noqa: F401  预热
    from src.llm_gateway import gateway as _gw  # noqa: F401  预热
    from src.paper_writer import ai_tutor as _tutor  # noqa: F401  预热

    class RealNetworkAttempt(RuntimeError):
        pass

    def _blocked(*args, **kwargs):
        raise RealNetworkAttempt("s923-46 用例禁止真实网络")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield


@pytest.fixture(autouse=True)
def _reset_gateway_state():
    """缓存/trace 是模块级全局，逐用例复位，避免顺序耦合与他串污染。"""
    clear_cache()
    set_cache_enabled(True)
    clear_traces()
    yield
    clear_cache()
    set_cache_enabled(True)


_cancel_ids_made: list = []


@pytest.fixture(autouse=True)
def _cleanup_cancel_flags():
    """用例里手工注册的 cancel_id 无论成败都从全局表摘掉，不污染兄弟用例。"""
    yield
    from src.llm_gateway.gateway import _cancel_flags, _cancel_lock
    with _cancel_lock:
        for cid in _cancel_ids_made:
            _cancel_flags.pop(cid, None)
    _cancel_ids_made.clear()


def _register_cancel_id(cid: str) -> str:
    """网关只在 ``_cancel_flags`` 里已有该 id 时才认取消（llm_chat_async_stream 会自己注册）。"""
    from src.llm_gateway.gateway import _cancel_flags, _cancel_lock
    with _cancel_lock:
        _cancel_flags[cid] = threading.Event()
    _cancel_ids_made.append(cid)
    return cid


def _install_fake_stream(monkeypatch, chunks, *, raise_after_index: int | None = None,
                         delay_s: float = 0.0):
    """把 ``chat_with_tutor_stream`` 换成假上游（零联网）。

    Returns:
        (calls, pulled)：
        - ``calls``：每次被调用的 messages/kwargs 列表（验证参数透传）
        - ``pulled``：上游实际被取出的块（含网关因取消或异常而丢弃的"在途块"）
        生成器先 yield 第 i 块，再在 ``i == raise_after_index`` 时抛错。
    """
    calls: list = []
    pulled: list = []

    def fake_stream(messages, **kwargs):
        calls.append({"messages": messages, "kwargs": kwargs})
        for i, chunk in enumerate(chunks):
            if delay_s:
                time.sleep(delay_s)
            pulled.append(chunk)
            yield chunk
            if raise_after_index is not None and i == raise_after_index:
                raise RuntimeError(f"假上游在第 {i} 块后崩了")

    monkeypatch.setattr("src.paper_writer.ai_tutor.chat_with_tutor_stream", fake_stream)
    return calls, pulled


def _text_backend(name: str, text: str):
    """注册一个只回固定文本的假后端（一次性/异步出口用）。"""
    def _backend(messages, model="", temperature=0.7, max_tokens=None,
                 requests_module=None, llm_config=None):
        return text
    register_llm_backend(name, _backend)
    return name


# ---------------------------------------------------------------------------
# 一、流式出口：块顺序与参数透传
# ---------------------------------------------------------------------------

class TestStreamChunkOrder:
    def test_chunks_keep_upstream_order_and_concat(self, monkeypatch):
        calls, pulled = _install_fake_stream(monkeypatch, ["你", "好", "，", "世", "界"])
        out = list(llm_chat_stream(_msgs("order"), llm_config=_ok_config()))
        assert out == ["你", "好", "，", "世", "界"]
        assert "".join(out) == "你好，世界"
        assert pulled == out
        assert len(calls) == 1

    def test_empty_chunks_are_dropped_without_breaking_order(self, monkeypatch):
        """网关 `if chunk:` 过滤空块：空串不透给消费者，也不影响后续块次序。"""
        _install_fake_stream(monkeypatch, ["A", "", "B", "", "C"])
        out = list(llm_chat_stream(_msgs("empty"), llm_config=_ok_config()))
        assert out == ["A", "B", "C"]

    def test_upstream_receives_injected_config_verbatim(self, monkeypatch):
        """provider/base_url/api_key/model/temperature/timeout/requests_module 全量透传。"""
        cfg = _ok_config(model="s92346-passthrough")
        calls, _ = _install_fake_stream(monkeypatch, ["x"])
        sentinel = object()
        list(llm_chat_stream(_msgs("passthrough"), model=None, temperature=0.33,
                             llm_config=cfg, requests_module=sentinel))
        kw = calls[0]["kwargs"]
        assert kw["provider"] == "openai"
        assert kw["base_url"] == "https://gateway.invalid/v1"
        assert kw["api_key"] == "sk-s92346-offline"
        assert kw["model"] == "s92346-passthrough"          # model=None → 取 cfg["model"]
        assert kw["temperature"] == 0.33
        assert kw["timeout"] == 5
        assert kw["requests_module"] is sentinel
        assert calls[0]["messages"] == _msgs("passthrough")


# ---------------------------------------------------------------------------
# 二、流式出口：取消传播
# ---------------------------------------------------------------------------

class TestStreamCancellation:
    def test_cancel_stops_emitting_and_drops_inflight_chunk(self, monkeypatch):
        """取消检查在 yield 之前 ⇒ 在途那块被取出但永不交付消费者。"""
        _, pulled = _install_fake_stream(monkeypatch, ["A", "B", "C", "D", "E"])
        cid = _register_cancel_id("s92346-stream-cancel")
        gen = llm_chat_stream(_msgs("cancel"), llm_config=_ok_config(), cancel_id=cid)
        got = []
        for chunk in gen:
            got.append(chunk)
            if len(got) == 2:
                assert cancel_request(cid) is True
        assert got == ["A", "B"]
        assert pulled == ["A", "B", "C"]          # C 是"取出即丢弃"的在途块
        assert "C" not in got

    def test_cancel_never_raises_cancelled_llm_error(self, monkeypatch):
        """否证卷宗前提：网关流式取消是静默收尾，不抛 CancelledLLMError。"""
        _install_fake_stream(monkeypatch, ["A", "B", "C", "D"])
        cid = _register_cancel_id("s92346-cancel-noraise")
        cancel_request(cid)                        # 消费前就取消
        out = list(llm_chat_stream(_msgs("cancel-noraise"), llm_config=_ok_config(),
                                   cancel_id=cid))
        assert out == []                           # 未抛异常，generator 正常结束

    def test_cancelled_llm_error_is_never_raised_by_gateway(self):
        """CancelledLLMError 在 gateway.py 只有 class 定义、全模块零 raise 站点。"""
        import inspect
        import re

        from src.llm_gateway import gateway as gw
        src = inspect.getsource(gw)
        assert re.search(r"raise\s+CancelledLLMError", src) is None
        assert "class CancelledLLMError" in src

    def test_cancelled_stream_records_cancelled_trace(self, monkeypatch):
        _install_fake_stream(monkeypatch, ["A", "B", "C", "D", "E"])
        cid = _register_cancel_id("s92346-cancel-trace")
        gen = llm_chat_stream(_msgs("cancel-trace"), llm_config=_ok_config(), cancel_id=cid)
        got = []
        for chunk in gen:
            got.append(chunk)
            if len(got) == 1:
                cancel_request(cid)
        trace = _last_trace()
        assert trace["streaming"] is True
        assert trace["cancelled"] is True
        assert trace["success"] is False
        assert trace["error"] == ""                # "cancelled" 不当错误上报
        assert trace["cost_cny"] == 0.0            # 取消不计费
        assert get_trace_summary()["by_status"]["cancelled"] >= 1

    def test_cancelled_partial_result_is_not_cached(self, monkeypatch):
        """取消的部分文本不得进缓存（否则下次拿到残缺答案）。"""
        _install_fake_stream(monkeypatch, ["部分", "结果", "丢弃"])
        cid = _register_cancel_id("s92346-cancel-cache")
        gen = llm_chat_stream(_msgs("cancel-cache"), llm_config=_ok_config(), cancel_id=cid)
        got = []
        for chunk in gen:
            got.append(chunk)
            if len(got) == 1:
                cancel_request(cid)
        assert "".join(got) == "部分"

        backend = _text_backend("s92346_after_cancel", "完整答案")
        resp = llm_chat(_msgs("cancel-cache"), llm_config=_ok_config(), backend=backend)
        assert resp.content == "完整答案"
        assert "cached" not in resp.fields         # 未命中缓存 ⇒ 取消确实没写缓存

    def test_unregistered_cancel_id_is_silently_ignored(self, monkeypatch):
        """取消依赖 _cancel_flags 先注册；裸 id 调 cancel_request 返回 False、流照跑完。"""
        _install_fake_stream(monkeypatch, ["A", "B", "C", "D"])
        assert cancel_request("s92346-never-registered") is False
        out = list(llm_chat_stream(_msgs("unregistered"), llm_config=_ok_config(),
                                   cancel_id="s92346-never-registered"))
        assert out == ["A", "B", "C", "D"]


# ---------------------------------------------------------------------------
# 三、流式出口：异常与不可用路径
# ---------------------------------------------------------------------------

class TestStreamErrorPaths:
    def test_upstream_exception_is_swallowed_after_partial_output(self, monkeypatch):
        """上游中途抛错 ⇒ 消费者只看到流自然结束（异常被 except 吞掉并入 trace）。"""
        _, pulled = _install_fake_stream(monkeypatch, ["A", "B", "C"], raise_after_index=1)
        out = list(llm_chat_stream(_msgs("boom"), llm_config=_ok_config()))
        assert out == ["A", "B"]
        assert pulled == ["A", "B"]               # 抛在 B 之后 ⇒ C 根本没被取出
        trace = _last_trace()
        assert trace["success"] is False
        assert "假上游在第 1 块后崩了" in trace["error"]
        assert trace["cancelled"] is False

    def test_failed_stream_does_not_poison_cache(self, monkeypatch):
        _install_fake_stream(monkeypatch, ["残", "缺"], raise_after_index=0)
        assert list(llm_chat_stream(_msgs("nocache"), llm_config=_ok_config())) == ["残"]
        backend = _text_backend("s92346_err_cache", "正常全文")
        resp = llm_chat(_msgs("nocache"), llm_config=_ok_config(), backend=backend)
        assert resp.content == "正常全文"
        assert "cached" not in resp.fields

    def test_unavailable_config_raises_llm_unavailable_on_iteration(self):
        """generator 特性：调用点不抛，首次 next 才抛 LLMUnavailableError。"""
        cfg = _ok_config()
        cfg["api_key"] = ""
        gen = llm_chat_stream(_msgs("nokey"), llm_config=cfg)
        with pytest.raises(LLMUnavailableError, match="未配置 API key"):
            next(gen)

    def test_unavailable_config_raises_inside_async_stream_future(self, monkeypatch):
        """异步包装把异常吞在 _runner 里 ⇒ future 不抛、回值是空串。"""
        cfg = _ok_config()
        cfg["api_key"] = ""
        result = llm_chat_async_stream(_msgs("async-nokey"), llm_config=cfg)
        assert set(result) == {"future", "cancel_id"}
        assert result["future"].result(timeout=10) == ""


# ---------------------------------------------------------------------------
# 四、流式成功写缓存 + 与一次性调用同源
# ---------------------------------------------------------------------------

class TestStreamCacheConsistency:
    def test_successful_stream_writes_cache_that_llm_chat_hits(self, monkeypatch):
        """流式全文写缓存 ⇒ 同 prompt 的一次性调用零成本复用，且文本逐字相同。"""
        _install_fake_stream(monkeypatch, ["逐", "字", "相同"])
        msgs = _msgs("cache-hit")
        streamed = "".join(list(llm_chat_stream(msgs, llm_config=_ok_config(),
                                                temperature=0.42)))
        assert streamed == "逐字相同"

        def _explode(*args, **kwargs):
            raise AssertionError("命中缓存后不应再碰后端")

        register_llm_backend("s92346_boom", _explode)
        resp = llm_chat(msgs, llm_config=_ok_config(), temperature=0.42,
                        backend="s92346_boom")
        assert resp.content == streamed
        assert resp.fields.get("cached") is True


# ---------------------------------------------------------------------------
# 五、注册后端与流式出口的分工（现状钉：流式不查注册表）
# ---------------------------------------------------------------------------

class TestBackendRegistryAsymmetry:
    def test_llm_chat_stream_never_consults_registered_backend(self, monkeypatch):
        """现状：流式出口写死 chat_with_tutor_stream，register_llm_backend 对它无效。

        生产调用方（socratic_engine:277 / paper_engine:907）若指望自定义后端接管流式，
        实际接管不到 —— 本用例把这条分歧钉住，改生产码时需同步翻它。
        """
        seen = {"n": 0}

        def _never(messages, model="", **kwargs):
            seen["n"] += 1
            return ["后端块"]

        register_llm_backend("s92346_stream_unseen", _never)
        _install_fake_stream(monkeypatch, ["网", "关"])
        out = list(llm_chat_stream(_msgs("asym"), llm_config=_ok_config()))
        assert out == ["网", "关"]
        assert seen["n"] == 0

    def test_llm_chat_does_consult_registered_backend(self):
        """对照组：一次性出口认注册表（证明不对称是流式侧的行为，而非夹具失灵）。"""
        backend = _text_backend("s92346_sync_seen", "后端答案")
        resp = llm_chat(_msgs("ctrl"), llm_config=_ok_config(), backend=backend)
        assert isinstance(resp, LLMResponse)
        assert resp.content == "后端答案"
        assert resp.backend == "s92346_sync_seen"

    def test_unknown_backend_raises_on_sync_path(self):
        with pytest.raises(LLMUnavailableError, match="未知后端"):
            llm_chat(_msgs("unknown-be"), llm_config=_ok_config(),
                     backend="s92346_does_not_exist")


# ---------------------------------------------------------------------------
# 六、llm_chat_async_stream：callback 顺序 / 取消 / 异常
# ---------------------------------------------------------------------------

class TestAsyncStreamWrapper:
    def test_callback_order_matches_chunks_and_future_is_concat(self, monkeypatch):
        _install_fake_stream(monkeypatch, ["甲", "乙", "丙"])
        received: list = []
        result = llm_chat_async_stream(_msgs("cb-order"), callback=received.append,
                                       llm_config=_ok_config())
        full = result["future"].result(timeout=10)
        assert received == ["甲", "乙", "丙"]
        assert isinstance(full, str)
        assert full == "".join(received) == "甲乙丙"

    def test_cancel_inside_callback_stops_wrapper_and_pops_flag(self, monkeypatch):
        """callback 在 runner 线程里取消 ⇒ 出口只交付取消前的块，且用完摘掉标志。"""
        _install_fake_stream(monkeypatch, ["A", "B", "C", "D", "E"], delay_s=0.01)
        received: list = []
        holder: dict = {}

        def _cb(chunk):
            received.append(chunk)
            if len(received) == 2:
                holder["cancelled"] = cancel_request(holder["cancel_id"])

        result = llm_chat_async_stream(_msgs("cb-cancel"), callback=_cb,
                                       llm_config=_ok_config())
        holder["cancel_id"] = result["cancel_id"]
        full = result["future"].result(timeout=10)
        assert received == ["A", "B"]
        assert holder["cancelled"] is True
        assert full == "AB"

        from src.llm_gateway.gateway import _cancel_flags, _cancel_lock
        with _cancel_lock:
            assert result["cancel_id"] not in _cancel_flags   # finally 里已 pop

    def test_callback_exception_does_not_break_stream(self, monkeypatch):
        _install_fake_stream(monkeypatch, ["A", "B", "C"])
        seen: list = []

        def _bad_cb(chunk):
            seen.append(chunk)
            raise ValueError("callback 自己炸了")

        result = llm_chat_async_stream(_msgs("cb-raises"), callback=_bad_cb,
                                       llm_config=_ok_config())
        assert result["future"].result(timeout=10) == "ABC"
        assert seen == ["A", "B", "C"]

    def test_upstream_exception_returns_partial_without_failing_future(self, monkeypatch):
        _install_fake_stream(monkeypatch, ["A", "B", "C"], raise_after_index=0)
        result = llm_chat_async_stream(_msgs("partial"), llm_config=_ok_config())
        assert result["future"].result(timeout=10) == "A"      # 不抛，回部分串

    def test_future_and_cancel_id_keys_and_result_type(self, monkeypatch):
        _install_fake_stream(monkeypatch, ["单", "块"])
        result = llm_chat_async_stream(_msgs("shape"), llm_config=_ok_config())
        assert set(result) == {"future", "cancel_id"}
        assert isinstance(result["cancel_id"], str) and result["cancel_id"]
        assert type(result["future"].result(timeout=10)) is str


# ---------------------------------------------------------------------------
# 七、llm_chat_async：回值一致性与错误形状
# ---------------------------------------------------------------------------

class TestAsyncConsistency:
    def test_async_response_matches_sync_backend_output(self):
        backend = _text_backend("s92346_async_ok", "同一答案")
        msgs = _msgs("async-sync")
        cfg = _ok_config()
        future_pack = llm_chat_async(msgs, llm_config=cfg, backend=backend,
                                     temperature=0.55, retries=0)
        async_resp = future_pack["future"].result(timeout=10)
        sync_resp = llm_chat(msgs, llm_config=cfg, backend=backend,
                             temperature=0.55, retries=0)
        assert isinstance(async_resp, LLMResponse)
        assert async_resp.content == sync_resp.content == "同一答案"
        assert async_resp.model == sync_resp.model == "s92346-model"

    def test_async_backend_failure_becomes_error_response_not_exception(self):
        """一次性路径同步会抛 LLMUnavailableError，异步路径把它折进 LLMResponse.error。"""
        def _bad(messages, model="", **kwargs):
            raise RuntimeError("后端离线")

        register_llm_backend("s92346_async_bad", _bad)
        cfg = _ok_config()
        pack = llm_chat_async(_msgs("async-bad"), llm_config=cfg,
                              backend="s92346_async_bad", retries=0)
        resp = pack["future"].result(timeout=10)
        assert isinstance(resp, LLMResponse)
        assert resp.content == ""
        assert resp.ok is False
        assert "后端离线" in (resp.error or "")

        with pytest.raises(LLMUnavailableError):
            llm_chat(_msgs("sync-bad"), llm_config=cfg,
                     backend="s92346_async_bad", retries=0)

    def test_async_pops_cancel_flag_after_completion(self):
        backend = _text_backend("s92346_async_pop", "done")
        pack = llm_chat_async(_msgs("pop"), llm_config=_ok_config(), backend=backend,
                              retries=0)
        pack["future"].result(timeout=10)
        from src.llm_gateway.gateway import _cancel_flags, _cancel_lock
        deadline = time.time() + 2
        while time.time() < deadline:
            with _cancel_lock:
                if pack["cancel_id"] not in _cancel_flags:
                    break
            time.sleep(0.01)
        with _cancel_lock:
            assert pack["cancel_id"] not in _cancel_flags

    def test_async_stream_and_async_share_concat_semantics(self, monkeypatch):
        """两条异步出口的"最终全文"对同一份上游产出必须逐字一致。"""
        _install_fake_stream(monkeypatch, ["同", "一", "份", "全文"])
        stream_pack = llm_chat_async_stream(_msgs("both"), llm_config=_ok_config())
        streamed = stream_pack["future"].result(timeout=10)

        msgs = _msgs("both")
        cfg = _ok_config()
        # 流式已把全文写缓存 ⇒ 一次性异步走缓存，内容即流式全文
        resp_pack = llm_chat_async(msgs, llm_config=cfg, temperature=0.7, retries=0)
        resp = resp_pack["future"].result(timeout=10)
        assert streamed == "同一份全文"
        assert resp.content == streamed
        assert resp.fields.get("cached") is True
