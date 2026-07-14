"""统一 LLM 调用网关（v3.5）。

设计：
- 所有模块通过 `llm_chat(messages, ...)` 调用 LLM，不直接接 chat_with_tutor
- 网关内部处理：模型选择、超时、重试、取消标志、降级异常
- 不可用时抛 LLMUnavailableError，调用方捕获后切到本地降级路径
- 后端可注册（register_llm_backend），便于未来扩展（Gemini/Claude/...）
"""

from .gateway import (
    CancelledLLMError,
    FallbackResult,
    LLMResponse,
    LLMTrace,
    LLMUnavailableError,
    MODEL_PRICING_CNY,
    cancel_request,
    chat_with_smart_fallback,
    clear_cache,
    clear_traces,
    estimate_cost_cny,
    get_trace_summary,
    is_llm_available,
    llm_chat,
    llm_chat_async,
    llm_chat_async_stream,
    llm_chat_stream,
    llm_chat_with_fallback,
    register_llm_backend,
    set_cache_enabled,
)

__all__ = [
    "CancelledLLMError",
    "FallbackResult",
    "LLMResponse",
    "LLMTrace",
    "LLMUnavailableError",
    "MODEL_PRICING_CNY",
    "cancel_request",
    "chat_with_smart_fallback",
    "clear_cache",
    "clear_traces",
    "estimate_cost_cny",
    "get_trace_summary",
    "is_llm_available",
    "llm_chat",
    "llm_chat_async",
    "llm_chat_async_stream",
    "llm_chat_stream",
    "llm_chat_with_fallback",
    "register_llm_backend",
    "set_cache_enabled",
]
