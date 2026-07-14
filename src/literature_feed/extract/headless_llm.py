"""无头 / 调度模式下的 LLM 配置解析。

文献雷达的 LLM 抽取跑在 Windows 任务计划（``python -m
src.literature_feed.scheduler``）或 Streamlit 启动时的后台异步线程里——
这些上下文都**没有 UI 会话**。而 gateway 默认通过
``active_config.get_active_llm_config()`` → ``_get_quick_model_id()``
取激活模型，后者只读 ``streamlit session_state.quick_model_id``；
无头时返回 None → 无 api_key → ``llm_chat`` 抛
``LLMUnavailableError("未配置 API key…")``，抽取全失败。

本模块直接从 ``.env.local``（经 ``quick_models``）解析一个默认模型配置，
通过 ``gateway.llm_chat`` 的 ``llm_config=`` 注入口绕开 session_state。
**不改动** UI 的「模型激活」语义（get_active_llm_config / is_llm_active /
_get_quick_model_id 完全不动），UI 启动也不会被动激活。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# 默认模型 + 回退链。deepseek-v4-pro 便宜、稳、结构化抽取强，放首位；
# 其余按可用性回退。可用环境变量 PSY_FEED_MODEL_ID 覆盖首选。
DEFAULT_MODEL_ID = "deepseek"
_FALLBACK_ORDER: List[str] = ["deepseek", "gpt", "kimi", "claude"]


def resolve_headless_model() -> Optional[Dict[str, Any]]:
    """解析一个无头可用的 LLM 配置 dict（含 api_key / model），失败返回 None。

    顺序：环境变量 ``PSY_FEED_MODEL_ID``（默认 ``deepseek``）作为首选，
    配不齐则按 ``_FALLBACK_ORDER`` 依次回退。任一 id 拿到含
    ``api_key`` 与 ``model`` 的 cfg 即返回；四组全缺返回 None。
    """
    from src.llm_gateway.quick_models import get_quick_model_config, load_env_local

    try:
        load_env_local()
    except Exception as exc:  # noqa: BLE001 — .env.local 损坏不应让整轮崩
        # 只记异常类型，不记 exc 文本：异常消息可能裹挟密钥/路径（DeepSeek #1）
        logger.warning("load_env_local 失败：%s", type(exc).__name__)

    preferred = (os.environ.get("PSY_FEED_MODEL_ID") or DEFAULT_MODEL_ID).strip()

    # 首选 + 回退链，去重保持顺序
    order: List[str] = [mid for mid in dict.fromkeys([preferred, *_FALLBACK_ORDER]) if mid]

    for mid in order:
        try:
            cfg = get_quick_model_config(mid)
        except Exception as exc:  # noqa: BLE001
            # 同上：不记 exc 文本，防密钥泄漏进日志
            logger.warning("get_quick_model_config(%r) 失败：%s", mid, type(exc).__name__)
            continue
        if cfg and cfg.get("api_key") and cfg.get("model"):
            logger.info("headless LLM 解析到模型 id=%s model=%s", mid, cfg.get("model"))
            return dict(cfg)

    logger.warning("headless LLM 未解析到任何可用模型（.env.local 四组均缺）")
    return None


def make_headless_llm_chat(cfg: Dict[str, Any]) -> Callable[..., Any]:
    """返回一个签名兼容的 ``llm_chat`` 包装器。

    - 固定注入 ``llm_config=cfg`` → 绕开 session_state；
    - **忽略调用方传入的 model**，始终用 ``cfg['model']``，确保发往端点的
      模型名与该端点匹配（否则会把错模型名发到错后端）；
    - 透传 temperature（gateway 内部对 GPT/Kimi 的强制温度逻辑仍生效）。
    """
    model_name = cfg.get("model", "")

    # 默认低温：结构化 JSON 抽取偏好确定性输出（DeepSeek #4）。实际温度由
    # 抽取器显式传入（见 daily_runner 构造）；此默认仅为安全兜底。
    # 注：gateway 对 GPT/Kimi 会强制 temperature=1.0，此值仅对 deepseek/claude 生效。
    def _chat(messages: List[Dict[str, str]], *, model: Optional[str] = None,
              temperature: float = 0.3, **kwargs: Any) -> Any:
        from src.llm_gateway.gateway import llm_chat
        return llm_chat(
            messages,
            model=model_name,      # 忽略传入 model，强制用 cfg 的真实模型名
            temperature=temperature,
            llm_config=cfg,        # 注入配置 → 绕开 UI session_state
        )

    return _chat
