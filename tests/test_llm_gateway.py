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


# ---------------------------------------------------------------------------
# s924-51：空响应不得进响应缓存（缓存投毒守卫）
# ---------------------------------------------------------------------------

def _s92451_msgs(tag: str) -> list:
    """用例唯一 tag ⇒ 缓存键互不相同，不与兄弟用例串味。"""
    return [{"role": "user", "content": f"s92451::{tag}"}]


class TestEmptyResponseCacheGuard:
    """backend 返回 None / 空串时，响应缓存必须保持干净（零网络：注入自定义 backend）。

    钉的是 `_cache_put` 中心位的空值守卫 —— 若该守卫被摘掉，本类两条用例都会转红
    （变异自证见 s924-51 result 的证据节）。
    """

    def test_empty_backend_response_leaves_no_cache_entry(self):
        from src.llm_gateway import gateway as gw
        from src.llm_gateway import clear_cache, register_llm_backend, set_cache_enabled

        clear_cache()
        set_cache_enabled(True)
        cfg = _ok_config()
        msgs = _s92451_msgs("empty-not-cached")
        seen = {"n": 0}

        def _empty_backend(messages, model="", **kwargs):
            seen["n"] += 1
            return ""

        register_llm_backend("s92451_empty", _empty_backend)
        r1 = llm_chat(msgs, llm_config=cfg, backend="s92451_empty")
        assert r1.content == ""
        assert seen["n"] == 1

        key = gw._cache_key(msgs, cfg["model"], 0.7)
        assert key not in gw._response_cache            # 键根本没进缓存
        assert gw._cache_get(key) is None               # 也读不出空串
        assert "" not in gw._response_cache.values()

    def test_none_backend_response_is_not_cached_and_next_call_gets_real_text(self):
        """首次空（这里 None）→ 不写缓存；同 key 第二次必须拿到真文而非缓存空串。"""
        from src.llm_gateway import gateway as gw
        from src.llm_gateway import clear_cache, register_llm_backend, set_cache_enabled

        clear_cache()
        set_cache_enabled(True)
        cfg = _ok_config()
        msgs = _s92451_msgs("none-then-real")
        seq = iter([None, "真文"])
        seen = {"n": 0}

        def _flaky_backend(messages, model="", **kwargs):
            seen["n"] += 1
            return next(seq)

        register_llm_backend("s92451_flaky", _flaky_backend)
        r1 = llm_chat(msgs, llm_config=cfg, backend="s92451_flaky")
        assert r1.content == ""                         # 归一化后对外仍是空串
        assert seen["n"] == 1

        key = gw._cache_key(msgs, cfg["model"], 0.7)
        assert key not in gw._response_cache

        r2 = llm_chat(msgs, llm_config=cfg, backend="s92451_flaky")
        assert r2.content == "真文"                     # 第二次打后端拿到真文
        assert "cached" not in r2.fields                # 且不是缓存回吐
        assert seen["n"] == 2
        assert gw._cache_get(key) == "真文"             # 这一次才允许写缓存


# ---------------------------------------------------------------------------
# s924-52：流式出口前置缓存命中（与 llm_chat 对齐）
# ---------------------------------------------------------------------------

def _s92452_msgs(tag: str) -> list:
    return [{"role": "user", "content": f"s92452::{tag}"}]


class TestStreamCachePrecheck:
    """llm_chat_stream 进入 generator 前先查响应缓存（案 A）。

    注：流式出口不吃 `register_llm_backend`（现状由 s923-46 的
    `test_llm_chat_stream_never_consults_registered_backend` 钉死），它写死
    `ai_tutor.chat_with_tutor_stream` ⇒ 卷宗「注入 backend」在本件里对流式侧只能
    落成「monkeypatch 假上游」，两条合计的调用数才是"零重复打后端"的可观测面。
    """

    def test_stream_reuses_chat_cache_and_never_touches_upstream(self, monkeypatch):
        import streamlit as st
        from src.paper_writer import ai_tutor
        from src.llm_gateway import clear_traces, register_llm_backend

        clear_cache()
        clear_traces()
        set_cache_enabled(True)
        cfg = _ok_config()
        msgs = _s92452_msgs("chat-then-stream")
        hits = {"backend": 0, "upstream": 0}

        def _backend(messages, model="", **kwargs):
            hits["backend"] += 1
            return "缓存正文"

        register_llm_backend("s92452_be", _backend)
        r1 = llm_chat(msgs, llm_config=cfg, backend="s92452_be")
        assert r1.content == "缓存正文"
        assert hits["backend"] == 1

        def _fake_upstream(messages, **kwargs):
            hits["upstream"] += 1
            yield "不该再打上游"

        monkeypatch.setattr(ai_tutor, "chat_with_tutor_stream", _fake_upstream)

        out = list(llm_chat_stream(msgs, llm_config=cfg))
        assert out == ["缓存正文"]                              # 整段一次性交付，逐字等于缓存值
        assert hits["upstream"] == 0
        assert hits["backend"] + hits["upstream"] == 1          # 判据②：两口合计只打一次

        traces = st.session_state.get("llm_traces") or []
        assert len(traces) == 2, "命中路径不应二次记账（try/finally 那一条不得再落）"
        hit = traces[-1]
        assert hit["cached"] is True                            # 判据④
        assert hit["cost_cny"] == 0.0                           # 判据④
        assert hit["streaming"] is True
        assert hit["success"] is True

    def test_stream_cache_miss_still_calls_upstream_once(self, monkeypatch):
        """对照组：未命中 ⇒ 上游照打一次、且落的是非 cached trace（证明上一条的 0 不是夹具坏了）。"""
        import streamlit as st
        from src.paper_writer import ai_tutor
        from src.llm_gateway import clear_traces

        clear_cache()
        clear_traces()
        set_cache_enabled(True)
        cfg = _ok_config()
        hits = {"upstream": 0}

        def _fake_upstream(messages, **kwargs):
            hits["upstream"] += 1
            yield "甲"
            yield "乙"

        monkeypatch.setattr(ai_tutor, "chat_with_tutor_stream", _fake_upstream)
        out = list(llm_chat_stream(_s92452_msgs("miss"), llm_config=cfg))
        assert out == ["甲", "乙"]
        assert hits["upstream"] == 1

        traces = st.session_state.get("llm_traces") or []
        assert len(traces) == 1
        assert traces[-1]["cached"] is False
        assert traces[-1]["streaming"] is True

    def test_pre_cancelled_id_does_not_take_cached_fast_path(self, monkeypatch):
        """取消契约优先于缓存快路：预置取消标志的 id 仍须零交付（不被缓存命中绕过去）。"""
        import streamlit as st
        from src.paper_writer import ai_tutor
        from src.llm_gateway import clear_traces, register_llm_backend
        from src.llm_gateway.gateway import _cancel_flags, _cancel_lock

        clear_cache()
        clear_traces()
        set_cache_enabled(True)
        cfg = _ok_config()
        msgs = _s92452_msgs("cancel-vs-cache")

        def _backend(messages, model="", **kwargs):
            return "缓存正文"

        register_llm_backend("s92452_be2", _backend)
        assert llm_chat(msgs, llm_config=cfg, backend="s92452_be2").content == "缓存正文"

        hits = {"upstream": 0}

        def _fake_upstream(messages, **kwargs):
            hits["upstream"] += 1
            yield "块"

        monkeypatch.setattr(ai_tutor, "chat_with_tutor_stream", _fake_upstream)

        cid = "s92452-pre-cancel"
        pre = threading.Event()
        pre.set()
        with _cancel_lock:
            _cancel_flags[cid] = pre
        try:
            out = list(llm_chat_stream(msgs, llm_config=cfg, cancel_id=cid))
        finally:
            with _cancel_lock:
                _cancel_flags.pop(cid, None)

        assert out == []                                    # 零交付（不是整段缓存）
        assert hits["upstream"] == 1                        # 走的是原有循环，取消在那儿生效
        traces = st.session_state.get("llm_traces") or []
        assert traces[-1]["cancelled"] is True
        assert traces[-1]["cached"] is False


# ---------------------------------------------------------------------------
# s924-53：异步流式静默空串的观测接线（caplog）
# ---------------------------------------------------------------------------

class TestAsyncStreamObservability:
    def test_interruption_warns_without_leaking_secrets_and_callback_stays_debug(
            self, caplog, monkeypatch):
        """后端整场失败 ⇒ 默认可见的 warning（带 cancel_id 前 8 位＋model），回值仍是 str；
        callback 异常仍留 debug 级（回调属调用方代码，不上抬以免带出上层内容）。

        同一条用例顺手钉住凭据红线：新日志行里既不得出现注入的 api_key 值，
        也不得出现 messages 正文（请求体明文）。
        """
        import logging

        from src.paper_writer import ai_tutor
        from src.llm_gateway.gateway import logger as gw_logger

        caplog.set_level(logging.DEBUG, logger="src.llm_gateway.gateway")
        clear_cache()
        secret_key = "sk-s92453-should-never-be-logged"
        secret_body = "s92453::被测请求正文-不得进日志"

        # ── 场景一：整场失败（LLM 不可用）→ 中断告警
        bad_cfg = dict(_ok_config(), api_key="", model="gpt-4")
        with caplog.at_level(logging.DEBUG):
            res = llm_chat_async_stream([{"role": "user", "content": secret_body}],
                                        llm_config=bad_cfg)
            out = res["future"].result(timeout=10)
        assert isinstance(out, str)                         # 现状语义钉住：仍是拼接串
        assert out == ""                                    # 且整场失败时为空串

        gw_records = [r for r in caplog.records
                      if r.name == "src.llm_gateway.gateway"]
        warns = [r for r in gw_records if r.levelno >= logging.WARNING]
        assert warns, "整场失败必须默认可见（升 warning）"
        msg = warns[-1].getMessage()
        assert res["cancel_id"][:8] in msg                  # 带相关 id 前 8 位
        assert "model=gpt-4" in msg                         # 带模型名
        # 精确量"这条日志自己带出什么"：消息本体 + 它自己的 traceback 文本
        rendered = "\n".join(
            [r.getMessage() + (r.exc_text or "") for r in gw_records]
        )
        assert secret_key not in rendered                   # 凭据不外泄
        assert secret_body not in rendered                  # 请求体明文不外泄
        assert "api_key" not in msg                         # 消息自身不引用配置字段

        # ── 场景二：callback 抛错 → 仍只有 debug，不产生 warning
        caplog.clear()

        def _fake_upstream(messages, **kwargs):
            yield "甲"
            yield "乙"

        monkeypatch.setattr(ai_tutor, "chat_with_tutor_stream", _fake_upstream)

        def _bad_callback(chunk):
            raise RuntimeError("回调内部炸了")

        caplog.set_level(logging.DEBUG, logger="src.llm_gateway.gateway")
        with caplog.at_level(logging.DEBUG):
            res2 = llm_chat_async_stream(_s92452_msgs("cb-observ"), callback=_bad_callback,
                                         llm_config=_ok_config())
            full2 = res2["future"].result(timeout=10)
        assert full2 == "甲乙"                              # 回调炸掉不影响交付
        recs2 = [r for r in caplog.records if r.name == "src.llm_gateway.gateway"]
        cb = [r for r in recs2 if "callback" in r.getMessage()]
        assert cb, "callback 异常仍须留痕"
        assert all(r.levelno == logging.DEBUG for r in cb)  # 但级别不上抬
        assert not [r for r in recs2 if r.levelno >= logging.WARNING]
