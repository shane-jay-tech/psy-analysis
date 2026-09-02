"""LLM 网关核心实现：统一调用 + 取消 + 后端注册 + 降级异常 + v3.6 流式 + tracing + 缓存。"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Generator, List, Optional

from .active_config import get_active_llm_config, is_llm_active

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 异常 + 数据结构
# ---------------------------------------------------------------------------

class LLMUnavailableError(RuntimeError):
    """LLM 不可用（缺 API key、网络故障、配额耗尽等）。

    调用方应捕获此异常并切到本地降级路径。
    """
    def __init__(self, reason: str = "", cause: Optional[Exception] = None):
        super().__init__(reason or "LLM 调用失败")
        self.reason = reason
        self.cause = cause


class CancelledLLMError(RuntimeError):
    """用户主动取消了 LLM 请求。调用方应丢弃部分结果，不写入 UI。"""
    pass


@dataclass
class LLMResponse:
    """统一响应格式。"""
    content: str
    model: str = ""
    backend: str = ""             # 后端标识（chat_with_tutor / 自定义）
    raw: Any = None               # 原始响应（调试用）
    cancelled: bool = False
    error: Optional[str] = None
    fields: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.content) and not self.cancelled and not self.error


# ---------------------------------------------------------------------------
# v3.6 调用 tracing
# ---------------------------------------------------------------------------

@dataclass
class LLMTrace:
    """单次 LLM 调用的痕迹（用于成本统计与 debug）。"""
    timestamp: str = ""
    module: str = ""             # 调用方模块（"socratic" / "feasibility" / "themes" 等）
    model: str = ""
    backend: str = ""
    streaming: bool = False
    elapsed_ms: float = 0.0
    prompt_tokens_estimate: int = 0
    completion_tokens_estimate: int = 0
    cost_cny: float = 0.0        # v3.7: 估算成本（人民币元）
    success: bool = True
    cancelled: bool = False
    cached: bool = False
    error: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


_trace_lock = threading.Lock()


# ---------------------------------------------------------------------------
# v3.7 模型成本估算（人民币元 / 1M token）
# ---------------------------------------------------------------------------
# 价格快照截至 2026-05；价格变动时手动更新。本地 ollama 模型计 0；
# 未匹配的模型走 _DEFAULT_PRICING_CNY。
# 数据来源：各 provider 官方定价页 / OpenAI USD 价 × 7.2 汇率。
MODEL_PRICING_CNY: Dict[str, Dict[str, float]] = {
    # DeepSeek
    "deepseek-chat":          {"input": 1.0,  "output": 2.0},
    "deepseek-reasoner":      {"input": 1.0,  "output": 8.0},
    # 智谱 Zhipu
    "glm-4":                  {"input": 5.0,  "output": 5.0},
    "glm-4-plus":             {"input": 50.0, "output": 50.0},
    "glm-4-air":              {"input": 1.0,  "output": 1.0},
    "glm-4-flash":            {"input": 0.0,  "output": 0.0},
    # 通义 Qwen
    "qwen-plus":              {"input": 0.8,  "output": 2.0},
    "qwen-max":               {"input": 20.0, "output": 60.0},
    "qwen-turbo":             {"input": 0.3,  "output": 0.6},
    # OpenAI（USD × 7.2）
    "gpt-4o":                 {"input": 18.0, "output": 72.0},
    "gpt-4o-mini":            {"input": 1.1,  "output": 4.3},
    "gpt-4-turbo":            {"input": 72.0, "output": 216.0},
    "o1-preview":             {"input": 108.0,"output": 432.0},
    "o1-mini":                {"input": 21.6, "output": 86.4},
    # Anthropic Claude（USD × 7.2）
    "claude-opus-4-8":        {"input": 108.0,"output": 540.0},
    "claude-sonnet-4-6":      {"input": 21.6, "output": 108.0},
    "claude-haiku-4-5":       {"input": 7.2,  "output": 36.0},
}

_DEFAULT_PRICING_CNY = {"input": 5.0, "output": 15.0}


def estimate_cost_cny(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """估算单次调用成本（人民币元）。

    - 本地 ollama 模型（含 ":" 标识或以 ollama 开头）一律计 0
    - 未匹配的模型走 _DEFAULT_PRICING_CNY（中位价格）
    - 价格按 model 名前缀模糊匹配（如 "deepseek-chat-v2" → "deepseek-chat"）
    """
    if not model:
        return 0.0
    name = model.lower().strip()
    # 本地 ollama: llama3:8b、qwen2.5:7b 等
    if ":" in name or name.startswith("ollama"):
        return 0.0
    # 精确匹配
    pricing = MODEL_PRICING_CNY.get(name)
    if pricing is None:
        # 前缀模糊匹配（取最长匹配 key）
        candidates = [k for k in MODEL_PRICING_CNY.keys() if name.startswith(k)]
        if candidates:
            best = max(candidates, key=len)
            pricing = MODEL_PRICING_CNY[best]
        else:
            pricing = _DEFAULT_PRICING_CNY
    cost = (prompt_tokens / 1_000_000) * pricing["input"] + \
           (completion_tokens / 1_000_000) * pricing["output"]
    return round(cost, 6)


def _record_trace(trace: LLMTrace) -> None:
    """把 trace 推入 streamlit session_state.llm_traces（容错：无 streamlit 时无操作）。"""
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx

        # 并发 fallback 的工作线程没有 Streamlit ScriptRunContext；访问 session_state
        # 会产生警告，测试进程退出时还可能写入已关闭的捕获流。UI trace 只在主会话
        # 上下文记录，后台调用仍由 FallbackResult.attempts 完整返回。
        if (
            threading.current_thread() is not threading.main_thread()
            and get_script_run_ctx(suppress_warning=True) is None
        ):
            return
        with _trace_lock:
            traces = st.session_state.get("llm_traces")
            if not isinstance(traces, list):
                traces = []
            traces.append(trace.as_dict())
            # 保留最近 100 条避免内存膨胀
            if len(traces) > 100:
                traces = traces[-100:]
            st.session_state["llm_traces"] = traces
    except Exception:
        logger.debug("LLM trace 记录失败", exc_info=True)


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中文 1.5 字 = 1 token，英文 4 字符 = 1 token。"""
    if not text:
        return 0
    cn = sum(1 for c in text if "一" <= c <= "鿿")
    en_len = len(text) - cn
    return int(cn / 1.5) + int(en_len / 4) + 1


def _module_from_messages(messages: List[Dict[str, str]]) -> str:
    """从 system prompt 启发式判断调用模块（用于 trace 显示）。"""
    if not messages:
        return "unknown"
    sys_content = ""
    for m in messages:
        if m.get("role") == "system":
            sys_content = m.get("content", "")
            break
    if "苏格拉底" in sys_content or "反问" in sys_content or "FUNNEL" in sys_content.upper():
        return "socratic"
    if "反思" in sys_content or "意义性" in sys_content:
        return "feasibility_reflection"
    if "gap" in sys_content.lower() or "研究空白" in sys_content:
        return "literature_gap"
    if "提取" in sys_content and "JSON" in sys_content.upper():
        return "matrix_extract"
    if "judge" in sys_content.lower() or "评估" in sys_content:
        return "socratic_judge"
    if "审阅" in sys_content or "追问" in sys_content:
        return "paper_reviewer"
    if "高门槛" in sys_content or "可操作" in sys_content:
        return "operability_check"
    if "导师" in sys_content:
        return "ai_tutor"
    return "unknown"


def get_trace_summary() -> Dict[str, Any]:
    """返回当前 session 的 LLM 调用统计（v3.7：含成本聚合）。"""
    try:
        import streamlit as st
        traces = st.session_state.get("llm_traces") or []
    except Exception:
        traces = []
    if not traces:
        return {
            "total_calls": 0, "total_tokens": 0, "total_cost_cny": 0.0,
            "by_module": {}, "by_status": {}, "by_model_cost": {},
        }
    total = len(traces)
    total_tokens = sum(
        (t.get("prompt_tokens_estimate", 0) + t.get("completion_tokens_estimate", 0))
        for t in traces
    )
    by_module: Dict[str, int] = {}
    by_status: Dict[str, int] = {"success": 0, "cancelled": 0, "error": 0, "cached": 0}
    by_model_cost: Dict[str, float] = {}
    total_elapsed = 0.0
    total_cost = 0.0
    for t in traces:
        mod = t.get("module") or "unknown"
        by_module[mod] = by_module.get(mod, 0) + 1
        if t.get("cached"):
            by_status["cached"] += 1
        elif t.get("cancelled"):
            by_status["cancelled"] += 1
        elif t.get("success"):
            by_status["success"] += 1
        else:
            by_status["error"] += 1
        total_elapsed += float(t.get("elapsed_ms") or 0)
        # v3.7: 缓存命中不计成本
        if not t.get("cached"):
            cost = float(t.get("cost_cny") or 0.0)
            total_cost += cost
            mdl = t.get("model") or "unknown"
            by_model_cost[mdl] = by_model_cost.get(mdl, 0.0) + cost
    return {
        "total_calls": total,
        "total_tokens": total_tokens,
        "total_cost_cny": round(total_cost, 4),
        "total_elapsed_ms": round(total_elapsed, 1),
        "avg_elapsed_ms": round(total_elapsed / total, 1) if total else 0,
        "by_module": by_module,
        "by_status": by_status,
        "by_model_cost": {k: round(v, 4) for k, v in by_model_cost.items()},
    }


def clear_traces() -> None:
    """清空 trace（用于会话重置或测试）。"""
    try:
        import streamlit as st
        st.session_state["llm_traces"] = []
    except Exception:
        pass


# ---------------------------------------------------------------------------
# v3.6 LLM 响应缓存（同 prompt 复用）
# ---------------------------------------------------------------------------

_response_cache: Dict[str, str] = {}
_cache_lock = threading.Lock()
_CACHE_ENABLED = True
_CACHE_MAX = 200


def _cache_key(messages: List[Dict[str, str]], model: str, temperature: float) -> str:
    blob = json.dumps(
        {"m": messages, "model": model, "t": round(temperature, 2)},
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.md5(blob.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> Optional[str]:
    if not _CACHE_ENABLED:
        return None
    with _cache_lock:
        return _response_cache.get(key)


def _cache_put(key: str, value: str) -> None:
    if not _CACHE_ENABLED or not value:
        return
    with _cache_lock:
        if len(_response_cache) >= _CACHE_MAX:
            # 简单 FIFO：删最早一条
            try:
                first = next(iter(_response_cache))
                _response_cache.pop(first, None)
            except StopIteration:
                pass
        _response_cache[key] = value


def set_cache_enabled(enabled: bool) -> None:
    global _CACHE_ENABLED
    _CACHE_ENABLED = bool(enabled)


def clear_cache() -> None:
    with _cache_lock:
        _response_cache.clear()


# ---------------------------------------------------------------------------
# 后端注册
# ---------------------------------------------------------------------------

# 后端：name → callable(messages, model, temperature, max_tokens, requests_module) → str
_BACKENDS: Dict[str, Callable] = {}
_DEFAULT_BACKEND = "chat_with_tutor"


def register_llm_backend(name: str, callable_obj: Callable) -> None:
    """注册自定义 LLM 后端。"""
    _BACKENDS[name] = callable_obj


def _get_default_backend() -> Callable:
    """返回默认后端（基于 ai_tutor.chat_with_tutor）。"""
    if _DEFAULT_BACKEND in _BACKENDS:
        return _BACKENDS[_DEFAULT_BACKEND]
    # 注册默认后端
    from src.paper_writer.ai_tutor import chat_with_tutor as _chat

    def _backend(messages, model="", temperature=0.7, max_tokens=None,
                  requests_module=None, llm_config=None):
        cfg = llm_config or _resolve_llm_config()
        # v4.3: 快捷模型可能强制 temperature（GPT/Kimi 仅支持 1.0）
        quick_id = cfg.get("_quick_model_id")
        if quick_id:
            try:
                from src.llm_gateway.quick_models import get_forced_temperature
                forced = get_forced_temperature(quick_id)
                if forced is not None:
                    temperature = forced
            except Exception:
                logger.debug("quick_model temperature 查询失败", exc_info=True)
        return _chat(
            messages,
            provider=cfg.get("provider", ""),
            base_url=cfg.get("base_url", ""),
            api_key=cfg.get("api_key", ""),
            model=model or cfg.get("model", ""),
            temperature=temperature,
            timeout=cfg.get("timeout", 60),
            requests_module=requests_module,
        )
    register_llm_backend(_DEFAULT_BACKEND, _backend)
    return _BACKENDS[_DEFAULT_BACKEND]


# ---------------------------------------------------------------------------
# LLM 配置解析
# ---------------------------------------------------------------------------

def _resolve_llm_config() -> Dict[str, Any]:
    """v4.4: 仅从顶部「🤖 AI 模型」selectbox 读配置。

    旧的 llm_provider/llm_api_key/llm_model/llm_custom_* session_state 已全部移除。
    未选模型 / env 未配 → 返回空 dict。
    """
    active = get_active_llm_config()
    return dict(active) if active else {}


def is_llm_available(llm_config: Optional[Dict[str, Any]] = None) -> bool:
    """快速判断 LLM 是否可用。

    v4.4：默认走 ``is_llm_active()``（顶部 selectbox + .env.local）。
    显式传 llm_config 时仍按原逻辑判断（测试用）。
    """
    if llm_config is None:
        return is_llm_active()
    if llm_config.get("provider") == "ollama":
        return True
    return bool(llm_config.get("api_key"))


def chat_with_smart_fallback(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    cancel_id: Optional[str] = None,
) -> "LLMResponse":
    """v4.6: 单轨化后退化为单调用，但保留 2 次重试以扛瞬时网络抖动。

    符号保留供旧调用站点不变。retries=2 → 总计最多 3 次尝试；
    business 错误（4xx）和瞬时错误（连接/超时/5xx）一视同仁地交由
    llm_chat 内部捕获，避免在网关层引入多套异常分类。
    """
    return llm_chat(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        cancel_id=cancel_id,
        retries=2,
    )


# ---------------------------------------------------------------------------
# 取消机制
# ---------------------------------------------------------------------------

_cancel_flags: Dict[str, threading.Event] = {}
_cancel_lock = threading.Lock()


def _new_cancel_id() -> str:
    return uuid.uuid4().hex[:12]


def cancel_request(cancel_id: str) -> bool:
    """请求取消某个进行中的 LLM 调用；返回是否找到该 id。"""
    with _cancel_lock:
        evt = _cancel_flags.get(cancel_id)
    if evt is None:
        return False
    evt.set()
    return True


def _is_cancelled(cancel_id: Optional[str]) -> bool:
    if not cancel_id:
        return False
    with _cancel_lock:
        evt = _cancel_flags.get(cancel_id)
    return bool(evt and evt.is_set())


# ---------------------------------------------------------------------------
# 同步调用
# ---------------------------------------------------------------------------

def llm_chat(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    cancel_id: Optional[str] = None,
    backend: Optional[str] = None,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
    retries: int = 1,
) -> LLMResponse:
    """统一 LLM 同步调用入口。

    Args:
        messages: OpenAI 兼容的 messages 列表
        model: 模型名（None 则用 active_config.get_active_llm_config()["model"]）
        temperature: 温度
        max_tokens: 最大 token（暂未传给后端，未来扩展用）
        cancel_id: 取消标志 ID（提前调 cancel_request 可中断）
        backend: 指定后端名（None 则用默认 chat_with_tutor）
        llm_config: 注入用配置（测试用）
        requests_module: 注入 requests（测试 mock）
        retries: 失败重试次数

    Returns:
        LLMResponse

    Raises:
        LLMUnavailableError: LLM 不可用、调用全失败、取消
    """
    if _is_cancelled(cancel_id):
        return LLMResponse(content="", cancelled=True)

    cfg = llm_config or _resolve_llm_config()
    if not is_llm_available(cfg):
        raise LLMUnavailableError("未配置 API key（或非 ollama 提供方）")

    backend_fn = _BACKENDS.get(backend) if backend else _get_default_backend()
    if backend_fn is None:
        raise LLMUnavailableError(f"未知后端：{backend!r}")

    used_model = model or cfg.get("model", "")
    used_backend = backend or _DEFAULT_BACKEND
    module_name = _module_from_messages(messages)

    # v3.6 缓存检查
    cache_k = _cache_key(messages, used_model, temperature)
    cached = _cache_get(cache_k)
    if cached:
        prompt_tok = sum(_estimate_tokens(m.get("content", "")) for m in messages)
        comp_tok = _estimate_tokens(cached)
        _record_trace(LLMTrace(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            module=module_name, model=used_model, backend=used_backend,
            elapsed_ms=0.0, cached=True, success=True,
            prompt_tokens_estimate=prompt_tok,
            completion_tokens_estimate=comp_tok,
            cost_cny=0.0,  # 缓存命中不计费
        ))
        return LLMResponse(content=cached, model=used_model, backend=used_backend,
                            fields={"cached": True})

    last_err: Optional[Exception] = None
    start = time.time()
    for attempt in range(max(1, retries + 1)):
        if _is_cancelled(cancel_id):
            elapsed = (time.time() - start) * 1000
            _record_trace(LLMTrace(
                timestamp=datetime.now().isoformat(timespec="seconds"),
                module=module_name, model=used_model, backend=used_backend,
                elapsed_ms=elapsed, cancelled=True, success=False,
            ))
            return LLMResponse(content="", cancelled=True)
        try:
            content = backend_fn(
                messages,
                model=used_model,
                temperature=temperature,
                max_tokens=max_tokens,
                requests_module=requests_module,
                llm_config=cfg,
            )
            elapsed = (time.time() - start) * 1000
            content = content or ""
            _cache_put(cache_k, content)
            prompt_tok = sum(_estimate_tokens(m.get("content", "")) for m in messages)
            comp_tok = _estimate_tokens(content)
            _record_trace(LLMTrace(
                timestamp=datetime.now().isoformat(timespec="seconds"),
                module=module_name, model=used_model, backend=used_backend,
                elapsed_ms=elapsed, success=bool(content),
                prompt_tokens_estimate=prompt_tok,
                completion_tokens_estimate=comp_tok,
                cost_cny=estimate_cost_cny(prompt_tok, comp_tok, used_model),
            ))
            return LLMResponse(
                content=content,
                model=used_model,
                backend=used_backend,
            )
        except Exception as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(min(2 ** attempt, 8))
            continue

    elapsed = (time.time() - start) * 1000
    _record_trace(LLMTrace(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        module=module_name, model=used_model, backend=used_backend,
        elapsed_ms=elapsed, success=False, error=str(last_err)[:120],
    ))
    raise LLMUnavailableError(
        reason=f"调用全部失败（重试 {retries} 次）：{last_err}",
        cause=last_err,
    )


# ---------------------------------------------------------------------------
# v3.6 流式调用
# ---------------------------------------------------------------------------

def llm_chat_stream(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.7,
    cancel_id: Optional[str] = None,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
) -> Generator[str, None, None]:
    """流式 LLM 调用：逐块 yield 文本片段。

    - 不支持流式时，自动回退一次性调用并 yield 整段
    - 取消标志在每块前后检查
    - 自动累积内容并记录 trace（在 generator 关闭时 record）
    - 若 LLM 不可用，抛 LLMUnavailableError
    """
    cfg = llm_config or _resolve_llm_config()
    if not is_llm_available(cfg):
        raise LLMUnavailableError("未配置 API key（或非 ollama 提供方）")

    used_model = model or cfg.get("model", "")
    module_name = _module_from_messages(messages)
    accumulated = []
    start = time.time()
    error_msg = ""

    try:
        from src.paper_writer.ai_tutor import chat_with_tutor_stream
        for chunk in chat_with_tutor_stream(
            messages,
            provider=cfg.get("provider", ""),
            base_url=cfg.get("base_url", ""),
            api_key=cfg.get("api_key", ""),
            model=used_model,
            temperature=temperature,
            timeout=cfg.get("timeout", 60),
            requests_module=requests_module,
        ):
            if _is_cancelled(cancel_id):
                error_msg = "cancelled"
                break
            if chunk:
                accumulated.append(chunk)
                yield chunk
    except Exception as exc:
        error_msg = str(exc)[:120]
    finally:
        elapsed = (time.time() - start) * 1000
        full = "".join(accumulated)
        # 流式成功时也写缓存（避免下次重复调用）
        if full and not error_msg:
            cache_k = _cache_key(messages, used_model, temperature)
            _cache_put(cache_k, full)
        prompt_tok = sum(_estimate_tokens(m.get("content", "")) for m in messages)
        comp_tok = _estimate_tokens(full)
        success = bool(full) and not error_msg
        _record_trace(LLMTrace(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            module=module_name, model=used_model, backend=_DEFAULT_BACKEND,
            streaming=True,
            elapsed_ms=elapsed,
            success=success,
            cancelled=(error_msg == "cancelled"),
            error=error_msg if error_msg and error_msg != "cancelled" else "",
            prompt_tokens_estimate=prompt_tok,
            completion_tokens_estimate=comp_tok,
            cost_cny=estimate_cost_cny(prompt_tok, comp_tok, used_model) if success else 0.0,
        ))


def llm_chat_async_stream(
    messages: List[Dict[str, str]],
    callback: Optional[Callable[[str], None]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """异步流式调用。callback 模式：每块 yield 后调用 callback(chunk)。

    Returns: {"future": Future, "cancel_id": str}
        future.result() 返回累积的完整文本字符串。
    """
    cancel_id = kwargs.pop("cancel_id", None) or _new_cancel_id()
    with _cancel_lock:
        _cancel_flags[cancel_id] = threading.Event()

    def _runner() -> str:
        accumulated = []
        try:
            for chunk in llm_chat_stream(messages, cancel_id=cancel_id, **kwargs):
                accumulated.append(chunk)
                if callback:
                    try:
                        callback(chunk)
                    except Exception:
                        logger.debug("stream callback 异常", exc_info=True)
        except Exception:
            logger.debug("LLM stream 中断", exc_info=True)
        finally:
            with _cancel_lock:
                _cancel_flags.pop(cancel_id, None)
        return "".join(accumulated)

    future = _get_executor().submit(_runner)
    return {"future": future, "cancel_id": cancel_id}


# ---------------------------------------------------------------------------
# 异步调用
# ---------------------------------------------------------------------------

_executor: Optional[ThreadPoolExecutor] = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm-gw")
    return _executor


def llm_chat_async(
    messages: List[Dict[str, str]],
    **kwargs: Any,
) -> Dict[str, Any]:
    """异步 LLM 调用。返回 {"future": Future, "cancel_id": str}。

    用法：
        result = llm_chat_async(messages)
        # 后续...
        cancel_request(result["cancel_id"])      # 中途取消
        # 或
        response: LLMResponse = result["future"].result(timeout=60)
    """
    cancel_id = kwargs.pop("cancel_id", None) or _new_cancel_id()
    with _cancel_lock:
        _cancel_flags[cancel_id] = threading.Event()

    def _runner() -> LLMResponse:
        try:
            return llm_chat(messages, cancel_id=cancel_id, **kwargs)
        except Exception as exc:
            return LLMResponse(content="", error=str(exc))
        finally:
            with _cancel_lock:
                _cancel_flags.pop(cancel_id, None)

    future = _get_executor().submit(_runner)
    return {"future": future, "cancel_id": cancel_id}


# ---------------------------------------------------------------------------
# v3.8 N8: 多模型并发 fallback —— 谁先返回用谁
# ---------------------------------------------------------------------------

@dataclass
class FallbackResult:
    """竞速调用的最终结果。

    Attributes:
        response: 胜出的 LLMResponse
        winner_model: 实际拿到结果的模型名
        winner_index: 胜出者在 candidates 中的下标
        elapsed_ms: 从启动到拿到第一个完整响应的耗时
        attempts: 每个候选的简要状态（[{"model", "ok", "cancelled", "error", "elapsed_ms"}, ...]）
    """
    response: LLMResponse
    winner_model: str = ""
    winner_index: int = -1
    elapsed_ms: float = 0.0
    attempts: List[Dict[str, Any]] = field(default_factory=list)


def llm_chat_with_fallback(
    messages: List[Dict[str, str]],
    candidates: List[Dict[str, Any]],
    *,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    cancel_id: Optional[str] = None,
    requests_module: Any = None,
    timeout: float = 60.0,
    head_start_ms: float = 0.0,
) -> FallbackResult:
    """并发跑多个候选模型，先到先用，其他自动取消（竞速 fallback）。

    适用场景：deepseek 远程偶尔卡 5-10s 才出第一个 token —— 同时打 qwen，
    哪个先返回就用哪个，体验稳定。

    Args:
        messages: OpenAI 兼容 messages
        candidates: [{"model": str, "llm_config": dict, "backend"?: str}, ...]
            - model: 模型名（必填）
            - llm_config: 该模型对应的 provider/base_url/api_key/timeout（必填）
            - backend: 可选自定义后端，默认走 chat_with_tutor
        temperature: 共用温度
        max_tokens: 共用 max_tokens
        cancel_id: 外层取消 ID（用户点「取消」时传入），传入后任一已 set 立即停止竞速
        requests_module: 测试 mock
        timeout: 总超时（秒），超时后所有候选返回 None 时抛 LLMUnavailableError
        head_start_ms: 给第一个候选先跑 N 毫秒再启动其他（默认 0=纯并发）。
            >0 时实现"主模型优先，备用兜底"语义。

    Returns:
        FallbackResult，包含 response 与 winner 信息。

    Raises:
        LLMUnavailableError: 所有候选都失败或全部取消。
        ValueError: candidates 为空。
    """
    if not candidates:
        raise ValueError("candidates 不能为空")

    # 单候选退化：直接走 llm_chat
    if len(candidates) == 1:
        c = candidates[0]
        start = time.time()
        try:
            resp = llm_chat(
                messages,
                model=c.get("model"),
                temperature=temperature,
                max_tokens=max_tokens,
                cancel_id=cancel_id,
                backend=c.get("backend"),
                llm_config=c.get("llm_config"),
                requests_module=requests_module,
            )
        except LLMUnavailableError as exc:
            elapsed = (time.time() - start) * 1000
            return FallbackResult(
                response=LLMResponse(content="", error=str(exc)),
                winner_model=c.get("model", ""),
                winner_index=-1,
                elapsed_ms=elapsed,
                attempts=[{"model": c.get("model", ""), "ok": False,
                           "error": str(exc)[:100], "elapsed_ms": elapsed}],
            )
        elapsed = (time.time() - start) * 1000
        return FallbackResult(
            response=resp,
            winner_model=c.get("model", ""),
            winner_index=0 if resp.ok else -1,
            elapsed_ms=elapsed,
            attempts=[{"model": c.get("model", ""), "ok": resp.ok,
                       "cancelled": resp.cancelled,
                       "error": resp.error or "", "elapsed_ms": elapsed}],
        )

    # 为每个候选分配独立 cancel_id；外层 cancel_id 触发时同步置位所有内层
    inner_cancel_ids: List[str] = []
    for _ in candidates:
        cid = _new_cancel_id()
        with _cancel_lock:
            _cancel_flags[cid] = threading.Event()
        inner_cancel_ids.append(cid)

    futures: List[Future] = []
    start_times: List[float] = []
    executor = _get_executor()

    def _run_one(idx: int, cand: Dict[str, Any], inner_cid: str) -> tuple[int, LLMResponse, float]:
        t0 = time.time()
        try:
            resp = llm_chat(
                messages,
                model=cand.get("model"),
                temperature=temperature,
                max_tokens=max_tokens,
                cancel_id=inner_cid,
                backend=cand.get("backend"),
                llm_config=cand.get("llm_config"),
                requests_module=requests_module,
            )
        except LLMUnavailableError as exc:
            return idx, LLMResponse(content="", error=str(exc)), (time.time() - t0) * 1000
        return idx, resp, (time.time() - t0) * 1000

    overall_start = time.time()

    # 启动第一个候选
    futures.append(executor.submit(_run_one, 0, candidates[0], inner_cancel_ids[0]))
    start_times.append(time.time())

    # head_start_ms > 0：等一段再启动其他候选（主优先策略）
    if head_start_ms > 0 and not _is_cancelled(cancel_id):
        # 边等边监听外层 cancel
        deadline = time.time() + head_start_ms / 1000
        while time.time() < deadline:
            if _is_cancelled(cancel_id):
                break
            # 主模型已完成则跳过启动备用
            if futures[0].done():
                break
            time.sleep(0.05)

    # 主模型还没好（或没启用 head_start）→ 启动其他候选
    if not futures[0].done():
        for idx in range(1, len(candidates)):
            if _is_cancelled(cancel_id):
                break
            futures.append(executor.submit(_run_one, idx, candidates[idx], inner_cancel_ids[idx]))
            start_times.append(time.time())

    # 等任一 future 返回 ok 的结果，或全部失败
    attempts: List[Dict[str, Any]] = [None] * len(candidates)  # type: ignore[list-item]
    winner: Optional[tuple[int, LLMResponse, float]] = None
    deadline = overall_start + timeout

    pending = list(futures)
    while pending and time.time() < deadline:
        # 外层取消：传播到所有 inner cancel
        if _is_cancelled(cancel_id):
            for cid in inner_cancel_ids:
                with _cancel_lock:
                    evt = _cancel_flags.get(cid)
                if evt:
                    evt.set()
            break

        from concurrent.futures import wait, FIRST_COMPLETED
        remaining = max(0.05, deadline - time.time())
        done_set, _not_done = wait(pending, timeout=min(remaining, 0.2),
                                    return_when=FIRST_COMPLETED)
        if not done_set:
            continue
        for fut in done_set:
            try:
                idx, resp, elapsed = fut.result()
            except Exception as exc:
                # 不应该到这里——_run_one 已 catch
                continue
            attempts[idx] = {
                "model": candidates[idx].get("model", ""),
                "ok": resp.ok,
                "cancelled": resp.cancelled,
                "error": resp.error or "",
                "elapsed_ms": round(elapsed, 1),
            }
            if resp.ok and winner is None:
                winner = (idx, resp, elapsed)
            pending.remove(fut)
        if winner is not None:
            # 取消未完成的候选
            for j, cid in enumerate(inner_cancel_ids):
                if attempts[j] is None:
                    with _cancel_lock:
                        evt = _cancel_flags.get(cid)
                    if evt:
                        evt.set()
            break

    # 清理 cancel flags
    for cid in inner_cancel_ids:
        with _cancel_lock:
            _cancel_flags.pop(cid, None)

    overall_elapsed = (time.time() - overall_start) * 1000

    # 填充未启动/未完成的 attempt 占位
    for j in range(len(candidates)):
        if attempts[j] is None:
            attempts[j] = {
                "model": candidates[j].get("model", ""),
                "ok": False,
                "cancelled": True,
                "error": "未完成（被取消或超时）",
                "elapsed_ms": 0.0,
            }

    if winner is not None:
        idx, resp, elapsed = winner
        return FallbackResult(
            response=resp,
            winner_model=candidates[idx].get("model", ""),
            winner_index=idx,
            elapsed_ms=round(overall_elapsed, 1),
            attempts=attempts,
        )

    # 所有候选都失败/取消
    errs = [a.get("error", "") for a in attempts if a.get("error")]
    raise LLMUnavailableError(
        reason=f"所有 {len(candidates)} 个候选模型均失败：{'; '.join(errs[:3])}",
    )
