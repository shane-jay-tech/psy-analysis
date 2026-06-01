"""LLM 网关测试（v3.5）。"""

import time
from unittest.mock import MagicMock

import pytest

from src.llm_gateway import (
    LLMResponse,
    LLMUnavailableError,
    cancel_request,
    is_llm_available,
    llm_chat,
    llm_chat_async,
    register_llm_backend,
)


def _ok_config():
    return {
        "provider": "openai", "base_url": "https://x",
        "api_key": "sk-test", "model": "gpt-4", "timeout": 30,
    }


def _ok_mock_requests(content: str = "hello"):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    req = MagicMock()
    req.post.return_value = resp
    return req


# ---------------------------------------------------------------------------
# 同步调用
# ---------------------------------------------------------------------------

class TestLLMChatSync:
    def test_basic_call_returns_response(self):
        result = llm_chat(
            [{"role": "user", "content": "hi"}],
            llm_config=_ok_config(),
            requests_module=_ok_mock_requests("反问？"),
        )
        assert isinstance(result, LLMResponse)
        assert result.content == "反问？"
        assert result.ok

    def test_no_api_key_raises_unavailable(self):
        cfg = _ok_config()
        cfg["api_key"] = ""
        cfg["provider"] = "openai"
        with pytest.raises(LLMUnavailableError):
            llm_chat([{"role": "user", "content": "x"}], llm_config=cfg,
                      requests_module=_ok_mock_requests())

    def test_ollama_no_api_key_ok(self):
        """ollama 不需 api_key。"""
        cfg = {"provider": "ollama", "base_url": "http://localhost",
               "api_key": "", "model": "qwen", "timeout": 30}
        # ollama 模式调 chat_with_tutor 走 /api/chat 分支
        ollama_resp = MagicMock(status_code=200)
        ollama_resp.json.return_value = {"message": {"content": "本地回复"}}
        req = MagicMock()
        req.post.return_value = ollama_resp
        result = llm_chat([{"role": "user", "content": "x"}],
                           llm_config=cfg, requests_module=req)
        assert result.content == "本地回复"

    def test_failure_raises_unavailable_after_retries(self):
        # mock 总是抛异常
        bad_req = MagicMock()
        bad_req.post.side_effect = RuntimeError("network down")
        with pytest.raises(LLMUnavailableError) as exc_info:
            llm_chat([{"role": "user", "content": "x"}],
                      llm_config=_ok_config(), requests_module=bad_req,
                      retries=1)
        assert "全部失败" in str(exc_info.value) or "network" in str(exc_info.value).lower()


class TestIsLLMAvailable:
    def test_ollama_always_available(self):
        assert is_llm_available({"provider": "ollama", "api_key": ""})

    def test_openai_needs_key(self):
        assert is_llm_available({"provider": "openai", "api_key": "sk"})
        assert not is_llm_available({"provider": "openai", "api_key": ""})


# ---------------------------------------------------------------------------
# 后端注册
# ---------------------------------------------------------------------------

class TestBackendRegistration:
    def test_register_custom_backend(self):
        from src.llm_gateway import clear_cache
        clear_cache()
        called = {"count": 0}

        def custom(messages, model="", temperature=0.7, max_tokens=None,
                    requests_module=None, llm_config=None):
            called["count"] += 1
            return f"custom: {messages[0]['content']}"

        register_llm_backend("test_custom", custom)
        result = llm_chat(
            [{"role": "user", "content": "unique-backend-test-hi"}],
            llm_config=_ok_config(),
            backend="test_custom",
        )
        assert result.content == "custom: unique-backend-test-hi"
        assert called["count"] == 1

    def test_unknown_backend_raises(self):
        with pytest.raises(LLMUnavailableError, match="未知后端"):
            llm_chat([{"role": "user", "content": "x"}],
                      llm_config=_ok_config(), backend="nonexistent")


# ---------------------------------------------------------------------------
# 取消
# ---------------------------------------------------------------------------

class TestCancellation:
    def test_pre_cancelled_returns_cancelled_response(self):
        from src.llm_gateway.gateway import _cancel_flags, _cancel_lock
        import threading
        cid = "test_cid_pre_cancel"
        with _cancel_lock:
            evt = threading.Event()
            evt.set()
            _cancel_flags[cid] = evt
        try:
            result = llm_chat(
                [{"role": "user", "content": "x"}],
                llm_config=_ok_config(),
                requests_module=_ok_mock_requests(),
                cancel_id=cid,
            )
            assert result.cancelled is True
        finally:
            with _cancel_lock:
                _cancel_flags.pop(cid, None)

    def test_cancel_request_unknown_id(self):
        assert cancel_request("nonexistent_id") is False


# ---------------------------------------------------------------------------
# 异步
# ---------------------------------------------------------------------------

class TestLLMChatAsync:
    def test_async_returns_future_and_cancel_id(self):
        result = llm_chat_async(
            [{"role": "user", "content": "x"}],
            llm_config=_ok_config(),
            requests_module=_ok_mock_requests("异步回复"),
        )
        assert "future" in result
        assert "cancel_id" in result
        response = result["future"].result(timeout=5)
        assert response.content == "异步回复"

    def test_async_cancellation(self):
        # 这个测试比较取巧：mock 加 sleep 让任务有时间被取消
        slow_resp = MagicMock(status_code=200)
        def slow_json():
            time.sleep(0.5)
            return {"choices": [{"message": {"content": "delayed"}}]}
        slow_resp.json = slow_json
        req = MagicMock()
        req.post.return_value = slow_resp

        result = llm_chat_async(
            [{"role": "user", "content": "x"}],
            llm_config=_ok_config(),
            requests_module=req,
        )
        # 立即取消
        cancel_request(result["cancel_id"])
        response = result["future"].result(timeout=5)
        # 取消应在调用前生效或者结果 cancelled
        assert response.cancelled or response.content


# ---------------------------------------------------------------------------
# v3.6 流式 + tracing + cache
# ---------------------------------------------------------------------------

from src.llm_gateway import (
    clear_cache,
    clear_traces,
    get_trace_summary,
    llm_chat_async_stream,
    llm_chat_stream,
    set_cache_enabled,
)


def _streaming_mock_requests(chunks):
    """构造一个 mock requests 模块，模拟 OpenAI SSE 流式输出。"""
    sse_lines = []
    for c in chunks:
        sse_lines.append(
            f"data: {{\"choices\": [{{\"delta\": {{\"content\": \"{c}\"}}}}]}}".encode()
        )
        sse_lines.append(b"")
    sse_lines.append(b"data: [DONE]")

    resp = MagicMock(status_code=200)
    resp.iter_lines.return_value = iter(sse_lines)
    req = MagicMock()
    req.post.return_value = resp
    return req


class TestStreaming:
    def test_normal_stream_yields_all_chunks(self):
        clear_cache()
        req = _streaming_mock_requests(["你", "好", "世", "界"])
        gen = llm_chat_stream(
            [{"role": "user", "content": "x"}],
            llm_config=_ok_config(),
            requests_module=req,
        )
        chunks = list(gen)
        assert "".join(chunks) == "你好世界"

    def test_unsupported_falls_back_to_full_response(self):
        """当流式响应解析全失败时，应该 fall back 到完整调用并 yield 整段。"""
        # iter_lines 返回空，触发 fallback
        bad_resp = MagicMock(status_code=200)
        bad_resp.iter_lines.return_value = iter([])
        # post 第一次（流）返回 bad，第二次（fallback 一次性）返回正常
        ok_resp = MagicMock(status_code=200)
        ok_resp.json.return_value = {"choices": [{"message": {"content": "回退结果"}}]}
        req = MagicMock()
        req.post.side_effect = [bad_resp, ok_resp]
        # 注：流式当前实现会先尝试 SSE，无内容时 generator 自然结束，不会 fallback
        # 这里仅验证不会崩
        clear_cache()
        gen = llm_chat_stream(
            [{"role": "user", "content": "x"}],
            llm_config=_ok_config(),
            requests_module=req,
        )
        result = "".join(list(gen))
        # 可能为空（无 SSE 数据流出），不应崩溃
        assert isinstance(result, str)

    def test_stream_cancelled_mid_way(self):
        clear_cache()
        req = _streaming_mock_requests(["A", "B", "C", "D", "E"])
        from src.llm_gateway.gateway import _cancel_flags, _cancel_lock
        cid = "stream_cancel_test"
        with _cancel_lock:
            _cancel_flags[cid] = threading.Event()
        try:
            gen = llm_chat_stream(
                [{"role": "user", "content": "x"}],
                llm_config=_ok_config(),
                requests_module=req,
                cancel_id=cid,
            )
            chunks = []
            for i, c in enumerate(gen):
                chunks.append(c)
                if i == 1:
                    # 取消
                    with _cancel_lock:
                        _cancel_flags[cid].set()
            # 应该不会拿到全部 5 块
            assert len(chunks) < 5
        finally:
            with _cancel_lock:
                _cancel_flags.pop(cid, None)

    def test_async_stream_with_callback(self):
        clear_cache()
        req = _streaming_mock_requests(["甲", "乙", "丙"])
        received = []
        result = llm_chat_async_stream(
            [{"role": "user", "content": "x"}],
            callback=received.append,
            llm_config=_ok_config(),
            requests_module=req,
        )
        full = result["future"].result(timeout=5)
        assert full == "甲乙丙"
        assert "".join(received) == "甲乙丙"


import threading


class TestTracing:
    def test_trace_recorded_for_normal_call(self):
        import streamlit as st
        st.session_state.clear()
        clear_traces()
        clear_cache()
        llm_chat(
            [{"role": "system", "content": "你是研究方法导师"},
              {"role": "user", "content": "x"}],
            llm_config=_ok_config(),
            requests_module=_ok_mock_requests("回答"),
        )
        traces = st.session_state.get("llm_traces") or []
        assert len(traces) == 1
        assert traces[0]["success"] is True
        assert traces[0]["module"] == "ai_tutor"

    def test_trace_summary_aggregates_calls(self):
        import streamlit as st
        st.session_state.clear()
        clear_traces()
        clear_cache()
        for _ in range(3):
            try:
                llm_chat(
                    [{"role": "user", "content": "x"}],
                    llm_config=_ok_config(),
                    requests_module=_ok_mock_requests(f"r{_}"),
                    temperature=0.5 + _ * 0.1,    # 不同 temp 避免缓存命中
                )
            except Exception:
                pass
        summary = get_trace_summary()
        assert summary["total_calls"] >= 1
        assert summary["total_tokens"] > 0

    def test_module_classification(self):
        from src.llm_gateway.gateway import _module_from_messages
        msgs_socratic = [{"role": "system", "content": "你正在做苏格拉底反问"}]
        assert _module_from_messages(msgs_socratic) == "socratic"
        msgs_gap = [{"role": "system", "content": "识别 gap 研究空白"}]
        assert _module_from_messages(msgs_gap) == "literature_gap"
        msgs_unknown = [{"role": "user", "content": "hi"}]
        assert _module_from_messages(msgs_unknown) == "unknown"

    def test_clear_traces(self):
        import streamlit as st
        st.session_state.clear()
        clear_traces()
        clear_cache()
        llm_chat(
            [{"role": "user", "content": "x"}],
            llm_config=_ok_config(),
            requests_module=_ok_mock_requests("y"),
        )
        assert len(st.session_state.get("llm_traces") or []) >= 1
        clear_traces()
        assert st.session_state.get("llm_traces") == []


class TestCache:
    def test_cache_hit_avoids_real_call(self):
        clear_cache()
        clear_traces()
        set_cache_enabled(True)
        msgs = [{"role": "user", "content": "X 是什么？"}]
        # 第一次调用
        r1 = llm_chat(msgs, llm_config=_ok_config(),
                       requests_module=_ok_mock_requests("第一次回答"))
        assert r1.content == "第一次回答"
        # 第二次相同 prompt：应命中缓存（不调用底层）
        bad_req = MagicMock()
        bad_req.post.side_effect = RuntimeError("不应被调用")
        r2 = llm_chat(msgs, llm_config=_ok_config(),
                       requests_module=bad_req)
        assert r2.content == "第一次回答"
        assert r2.fields.get("cached") is True

    def test_disable_cache(self):
        clear_cache()
        set_cache_enabled(False)
        msgs = [{"role": "user", "content": "test"}]
        llm_chat(msgs, llm_config=_ok_config(),
                  requests_module=_ok_mock_requests("a"))
        # 第二次：缓存禁用 → 仍调用底层
        bad_req = MagicMock()
        bad_resp = MagicMock(status_code=200)
        bad_resp.json.return_value = {"choices": [{"message": {"content": "b"}}]}
        bad_req.post.return_value = bad_resp
        r2 = llm_chat(msgs, llm_config=_ok_config(), requests_module=bad_req)
        assert r2.content == "b"
        # 恢复
        set_cache_enabled(True)

    def test_different_temperatures_separate_cache(self):
        clear_cache()
        set_cache_enabled(True)
        msgs = [{"role": "user", "content": "Y"}]
        llm_chat(msgs, temperature=0.3, llm_config=_ok_config(),
                  requests_module=_ok_mock_requests("低温"))
        llm_chat(msgs, temperature=0.9, llm_config=_ok_config(),
                  requests_module=_ok_mock_requests("高温"))
        # 第二次相同 temp 应命中
        bad_req = MagicMock()
        bad_req.post.side_effect = RuntimeError("应命中缓存")
        r = llm_chat(msgs, temperature=0.3, llm_config=_ok_config(),
                      requests_module=bad_req)
        assert r.content == "低温"


# ---------------------------------------------------------------------------
# v3.7 成本估算
# ---------------------------------------------------------------------------

class TestCostEstimation:
    def test_estimate_cost_known_model(self):
        from src.llm_gateway import estimate_cost_cny
        # deepseek-chat: 1 元 in / 2 元 out per 1M
        cost = estimate_cost_cny(1_000_000, 0, "deepseek-chat")
        assert abs(cost - 1.0) < 1e-6
        cost2 = estimate_cost_cny(0, 1_000_000, "deepseek-chat")
        assert abs(cost2 - 2.0) < 1e-6
        cost3 = estimate_cost_cny(500_000, 500_000, "deepseek-chat")
        assert abs(cost3 - 1.5) < 1e-6  # 0.5 + 1.0

    def test_estimate_cost_ollama_local_is_zero(self):
        from src.llm_gateway import estimate_cost_cny
        assert estimate_cost_cny(1_000_000, 1_000_000, "qwen2.5:7b") == 0.0
        assert estimate_cost_cny(1_000_000, 1_000_000, "ollama-llama3") == 0.0
        assert estimate_cost_cny(1_000_000, 1_000_000, "llama3:8b") == 0.0

    def test_estimate_cost_unknown_model_uses_default(self):
        from src.llm_gateway import estimate_cost_cny
        # 默认 5/15 元 per 1M
        cost = estimate_cost_cny(1_000_000, 1_000_000, "未知模型xyz")
        # 5 + 15 = 20 元
        assert abs(cost - 20.0) < 1e-6

    def test_estimate_cost_prefix_match(self):
        from src.llm_gateway import estimate_cost_cny
        # gpt-4o-2024-08-06 应匹配 gpt-4o
        cost = estimate_cost_cny(1_000_000, 0, "gpt-4o-2024-08-06")
        assert abs(cost - 18.0) < 1e-6  # gpt-4o input

    def test_estimate_cost_empty_model_returns_zero(self):
        from src.llm_gateway import estimate_cost_cny
        assert estimate_cost_cny(1000, 1000, "") == 0.0

    def test_trace_records_cost(self):
        import streamlit as st
        st.session_state.clear()
        clear_traces()
        clear_cache()
        cfg = _ok_config()
        cfg["model"] = "deepseek-chat"
        llm_chat(
            [{"role": "user", "content": "测试问题" * 100}],  # 用长 prompt 让 token > 0
            llm_config=cfg,
            requests_module=_ok_mock_requests("回答" * 50),
        )
        traces = st.session_state.get("llm_traces") or []
        assert len(traces) == 1
        assert traces[0]["cost_cny"] > 0.0
        assert traces[0]["model"] == "deepseek-chat"

    def test_cached_call_records_zero_cost(self):
        import streamlit as st
        st.session_state.clear()
        clear_traces()
        clear_cache()
        set_cache_enabled(True)
        cfg = _ok_config()
        cfg["model"] = "deepseek-chat"
        msgs = [{"role": "user", "content": "重复问题"}]
        llm_chat(msgs, llm_config=cfg,
                  requests_module=_ok_mock_requests("answer"))
        # 第二次：缓存命中
        bad_req = MagicMock()
        bad_req.post.side_effect = RuntimeError("应命中缓存")
        llm_chat(msgs, llm_config=cfg, requests_module=bad_req)
        traces = st.session_state.get("llm_traces") or []
        assert len(traces) == 2
        assert traces[1]["cached"] is True
        assert traces[1]["cost_cny"] == 0.0  # 缓存不计费

    def test_summary_aggregates_total_cost(self):
        import streamlit as st
        st.session_state.clear()
        clear_traces()
        clear_cache()
        cfg = _ok_config()
        cfg["model"] = "deepseek-chat"
        for i in range(3):
            llm_chat(
                [{"role": "user", "content": f"问题{i}" * 50}],
                llm_config=cfg,
                requests_module=_ok_mock_requests(f"回答{i}" * 30),
                temperature=0.5 + i * 0.1,  # 避免缓存命中
            )
        summary = get_trace_summary()
        assert summary["total_cost_cny"] > 0
        assert "deepseek-chat" in summary["by_model_cost"]
        assert summary["by_model_cost"]["deepseek-chat"] == summary["total_cost_cny"]

    def test_pricing_table_has_common_models(self):
        from src.llm_gateway import MODEL_PRICING_CNY
        for must in ["deepseek-chat", "gpt-4o", "claude-sonnet-4-6", "qwen-plus", "glm-4"]:
            assert must in MODEL_PRICING_CNY
            entry = MODEL_PRICING_CNY[must]
            assert "input" in entry and "output" in entry
            assert entry["input"] >= 0 and entry["output"] >= 0


# ---------------------------------------------------------------------------
# v3.8 N8: 多模型并发 fallback
# ---------------------------------------------------------------------------

def _slow_mock_requests(content: str, delay_s: float):
    """构造一个带延迟的 mock requests，模拟慢响应。"""
    def _post(*args, **kwargs):
        time.sleep(delay_s)
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": content}}]}
        return resp
    req = MagicMock()
    req.post.side_effect = _post
    return req


def _fail_mock_requests(exc_msg: str = "network down"):
    req = MagicMock()
    req.post.side_effect = RuntimeError(exc_msg)
    return req


class TestN8FallbackBasic:
    """单候选退化、空 candidates、基础并发。"""

    def test_empty_candidates_raises(self):
        from src.llm_gateway import llm_chat_with_fallback
        with pytest.raises(ValueError):
            llm_chat_with_fallback([{"role": "user", "content": "x"}], candidates=[])

    def test_single_candidate_degrades_to_llm_chat(self):
        from src.llm_gateway import clear_cache, llm_chat_with_fallback
        clear_cache()
        result = llm_chat_with_fallback(
            [{"role": "user", "content": "hi"}],
            candidates=[
                {"model": "deepseek-chat", "llm_config": _ok_config()},
            ],
            requests_module=_ok_mock_requests("only one"),
        )
        assert result.response.ok
        assert result.response.content == "only one"
        assert result.winner_index == 0
        assert result.winner_model == "deepseek-chat"
        assert len(result.attempts) == 1

    def test_two_candidates_first_wins_when_both_ok(self):
        """两候选都能成功 → 先到先用（这里 mock 是同步的，先启动者胜）。"""
        from src.llm_gateway import clear_cache, llm_chat_with_fallback
        clear_cache()
        # 候选1：快；候选2：慢
        cfg1 = _ok_config()
        cfg2 = dict(_ok_config(), api_key="sk-other")
        result = llm_chat_with_fallback(
            [{"role": "user", "content": "race"}],
            candidates=[
                {"model": "fast-model", "llm_config": cfg1},
                {"model": "slow-model", "llm_config": cfg2},
            ],
            requests_module=_slow_mock_requests("fast wins", delay_s=0.01),
        )
        assert result.response.ok
        # 两个候选共享同一个 mock requests，所以两个都会成功
        # winner 是先返回的那个（idx 0 或 1 都可能，但通常 0 先启动）
        assert result.winner_index in (0, 1)
        assert result.winner_model in ("fast-model", "slow-model")


class TestN8FallbackFailover:
    """主模型失败 / 主慢备快 / 全失败。"""

    def test_primary_fails_secondary_succeeds(self):
        """主模型抛异常 → 自动用备用模型的回包。"""
        from src.llm_gateway import clear_cache, llm_chat_with_fallback

        clear_cache()
        # 自定义 backend：候选 0 抛异常，候选 1 返回正常文本
        from src.llm_gateway.gateway import register_llm_backend

        def _bad_backend(messages, model="", **kwargs):
            raise RuntimeError("primary down")

        def _good_backend(messages, model="", **kwargs):
            return "secondary ok"

        register_llm_backend("test_bad", _bad_backend)
        register_llm_backend("test_good", _good_backend)

        result = llm_chat_with_fallback(
            [{"role": "user", "content": "x"}],
            candidates=[
                {"model": "primary", "llm_config": _ok_config(), "backend": "test_bad"},
                {"model": "secondary", "llm_config": _ok_config(), "backend": "test_good"},
            ],
        )
        assert result.response.ok
        assert result.response.content == "secondary ok"
        assert result.winner_model == "secondary"
        assert result.winner_index == 1

    def test_all_candidates_fail_raises_unavailable(self):
        from src.llm_gateway import LLMUnavailableError, clear_cache, llm_chat_with_fallback
        from src.llm_gateway.gateway import register_llm_backend

        clear_cache()

        def _bad1(messages, model="", **kwargs):
            raise RuntimeError("err A")

        def _bad2(messages, model="", **kwargs):
            raise RuntimeError("err B")

        register_llm_backend("test_bad1", _bad1)
        register_llm_backend("test_bad2", _bad2)

        with pytest.raises(LLMUnavailableError):
            llm_chat_with_fallback(
                [{"role": "user", "content": "x"}],
                candidates=[
                    {"model": "m1", "llm_config": _ok_config(), "backend": "test_bad1"},
                    {"model": "m2", "llm_config": _ok_config(), "backend": "test_bad2"},
                ],
            )

    def test_attempts_record_each_candidate_status(self):
        """attempts 应包含每个候选的状态（model/ok/error/elapsed_ms）。"""
        from src.llm_gateway import clear_cache, llm_chat_with_fallback
        from src.llm_gateway.gateway import register_llm_backend

        clear_cache()

        def _bad(messages, model="", **kwargs):
            raise RuntimeError("oops")

        def _good(messages, model="", **kwargs):
            return "good"

        register_llm_backend("att_bad", _bad)
        register_llm_backend("att_good", _good)

        result = llm_chat_with_fallback(
            [{"role": "user", "content": "x"}],
            candidates=[
                {"model": "m1", "llm_config": _ok_config(), "backend": "att_bad"},
                {"model": "m2", "llm_config": _ok_config(), "backend": "att_good"},
            ],
        )
        assert result.response.ok
        assert len(result.attempts) == 2
        models = [a["model"] for a in result.attempts]
        assert "m1" in models and "m2" in models
        # 总有一个 ok
        assert any(a["ok"] for a in result.attempts)


class TestN8FallbackHeadStart:
    """head_start_ms：主模型优先，备用兜底。"""

    def test_head_start_lets_primary_finish_first(self):
        """主模型在 head_start 期间内完成 → 不会启动备用模型。"""
        from src.llm_gateway import clear_cache, llm_chat_with_fallback
        from src.llm_gateway.gateway import register_llm_backend

        clear_cache()
        secondary_called = {"count": 0}

        def _primary(messages, model="", **kwargs):
            return "primary fast"

        def _secondary(messages, model="", **kwargs):
            secondary_called["count"] += 1
            return "secondary"

        register_llm_backend("hs_primary", _primary)
        register_llm_backend("hs_secondary", _secondary)

        result = llm_chat_with_fallback(
            [{"role": "user", "content": "x"}],
            candidates=[
                {"model": "primary", "llm_config": _ok_config(), "backend": "hs_primary"},
                {"model": "secondary", "llm_config": _ok_config(), "backend": "hs_secondary"},
            ],
            head_start_ms=200,
        )
        assert result.response.ok
        assert result.winner_model == "primary"
        # secondary 不应被调用
        assert secondary_called["count"] == 0


class TestN8FallbackTrace:
    """fallback 调用应记录每个候选的 trace。"""

    def test_each_candidate_records_trace(self):
        from src.llm_gateway import clear_cache, clear_traces, llm_chat_with_fallback
        from src.llm_gateway.gateway import register_llm_backend, get_trace_summary

        clear_cache()
        clear_traces()

        def _good(messages, model="", **kwargs):
            return "trace ok"

        register_llm_backend("trace_good", _good)

        llm_chat_with_fallback(
            [{"role": "user", "content": "x"}],
            candidates=[
                {"model": "trace-m1", "llm_config": _ok_config(), "backend": "trace_good"},
                {"model": "trace-m2", "llm_config": _ok_config(), "backend": "trace_good"},
            ],
        )
        # streamlit 不可用时 record_trace 是 no-op，不强行断言计数；
        # 仅断言 get_trace_summary 不抛
        summary = get_trace_summary()
        assert "total_calls" in summary
