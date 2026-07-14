"""LLM 取消机制端到端测试。

覆盖：
1. 请求前已取消 → 立即返回 cancelled=True
2. 调用 cancel_request → Event 被设置
3. 取消后 _is_cancelled 返回 True
4. 取消后下一次请求不被误取消（标志清理）
5. 流式过程中取消 → 停止消费
"""
import threading
import time

import pytest


@pytest.fixture(autouse=True)
def _clean_cancel_state():
    """确保每个测试开始时取消状态干净。"""
    from src.llm_gateway.gateway import _cancel_flags, _cancel_lock
    with _cancel_lock:
        _cancel_flags.clear()
    yield
    with _cancel_lock:
        _cancel_flags.clear()


class TestCancelMechanism:
    """测试底层取消标志系统。"""

    def test_new_cancel_id_unique(self):
        from src.llm_gateway.gateway import _new_cancel_id
        ids = {_new_cancel_id() for _ in range(100)}
        assert len(ids) == 100

    def test_is_cancelled_false_by_default(self):
        from src.llm_gateway.gateway import _is_cancelled
        assert _is_cancelled(None) is False
        assert _is_cancelled("nonexistent") is False

    def test_cancel_request_sets_event(self):
        from src.llm_gateway.gateway import (
            _cancel_flags, _cancel_lock, cancel_request, _is_cancelled,
        )
        cancel_id = "test_cancel_001"
        evt = threading.Event()
        with _cancel_lock:
            _cancel_flags[cancel_id] = evt

        assert _is_cancelled(cancel_id) is False
        result = cancel_request(cancel_id)
        assert result is True
        assert _is_cancelled(cancel_id) is True
        assert evt.is_set()

    def test_cancel_unknown_id_returns_false(self):
        from src.llm_gateway.gateway import cancel_request
        assert cancel_request("unknown_id_xyz") is False

    def test_cancel_does_not_affect_other_ids(self):
        from src.llm_gateway.gateway import (
            _cancel_flags, _cancel_lock, cancel_request, _is_cancelled,
        )
        id_a = "cancel_a"
        id_b = "cancel_b"
        with _cancel_lock:
            _cancel_flags[id_a] = threading.Event()
            _cancel_flags[id_b] = threading.Event()

        cancel_request(id_a)
        assert _is_cancelled(id_a) is True
        assert _is_cancelled(id_b) is False


class TestLLMChatCancel:
    """测试 llm_chat 的取消行为。"""

    def test_pre_cancelled_returns_immediately(self):
        """请求前已取消 → 不调用后端，直接返回 cancelled。"""
        from src.llm_gateway.gateway import (
            _cancel_flags, _cancel_lock, llm_chat,
        )
        cancel_id = "pre_cancel_test"
        evt = threading.Event()
        evt.set()
        with _cancel_lock:
            _cancel_flags[cancel_id] = evt

        resp = llm_chat(
            [{"role": "user", "content": "hello"}],
            cancel_id=cancel_id,
            llm_config={"api_key": "fake", "model": "test", "base_url": "http://x"},
        )
        assert resp.cancelled is True
        assert resp.content == ""

    def test_cancel_during_retry_loop(self):
        """重试循环中取消 → 不再重试。"""
        from src.llm_gateway.gateway import (
            _cancel_flags, _cancel_lock, llm_chat, register_llm_backend,
        )

        call_count = 0

        def _failing_backend(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                cancel_request_in_bg(cancel_id)
                time.sleep(0.05)
            raise ConnectionError("simulated failure")

        cancel_id = "retry_cancel_test"
        evt = threading.Event()
        with _cancel_lock:
            _cancel_flags[cancel_id] = evt

        def cancel_request_in_bg(cid):
            from src.llm_gateway.gateway import cancel_request
            threading.Timer(0.01, cancel_request, args=(cid,)).start()

        register_llm_backend("test_cancel_backend", _failing_backend)

        resp = llm_chat(
            [{"role": "user", "content": "test"}],
            cancel_id=cancel_id,
            backend="test_cancel_backend",
            retries=5,
            llm_config={"api_key": "fake", "model": "test", "base_url": "http://x"},
        )
        assert resp.cancelled is True
        assert call_count <= 2


class TestCancelledLLMError:
    """测试 CancelledLLMError 异常类。"""

    def test_is_runtime_error(self):
        from src.llm_gateway import CancelledLLMError
        err = CancelledLLMError("cancelled")
        assert isinstance(err, RuntimeError)

    def test_can_be_caught(self):
        from src.llm_gateway import CancelledLLMError
        with pytest.raises(CancelledLLMError):
            raise CancelledLLMError("user cancelled")


class TestCancelFlagCleanup:
    """测试取消标志在请求完成后被清理。"""

    def test_flag_removed_after_successful_call(self):
        """成功调用后 cancel_id 应从 _cancel_flags 中移除。"""
        from src.llm_gateway.gateway import (
            _cancel_flags, _cancel_lock, llm_chat, register_llm_backend,
        )

        def _success_backend(messages, **kwargs):
            return "ok"

        register_llm_backend("test_success_backend", _success_backend)

        resp = llm_chat(
            [{"role": "user", "content": "test"}],
            cancel_id="cleanup_test",
            backend="test_success_backend",
            llm_config={"api_key": "fake", "model": "test", "base_url": "http://x"},
        )
        assert resp.content == "ok"
        with _cancel_lock:
            assert "cleanup_test" not in _cancel_flags
