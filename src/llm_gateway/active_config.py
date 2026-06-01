"""v4.6 单轨 LLM 配置入口。

哲学：所有 LLM 调用都从这里读配置。session_state 里只有一个标志位
``quick_model_id``（来自侧栏顶部「🤖 AI 模型」selectbox），实际 base_url /
api_key / model 一律来自 ``D:\\code\\.env.local``，由 quick_models 解析。

旧版的 ``llm_provider / llm_api_key / llm_model / llm_custom_* /
llm_temperature / llm_fallback_*`` session_state 字段已全部废弃。

温度模型：
- API 强制温度（GPT/Kimi=1.0）由 ``quick_models.get_forced_temperature`` 提供，
  唯一真值；改了那里这里自动跟进。
- 没有 API 强制的模型（DeepSeek、Claude）按 v4.6 UI 决策固定预设温度。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    import streamlit as st
except ImportError:  # pragma: no cover - 非 UI 上下文（测试 / CLI）
    st = None  # type: ignore[assignment]

from .quick_models import get_forced_temperature, get_quick_model_config

_logger = logging.getLogger(__name__)


# 没有 API 强制的模型，按 v4.6 决策固定的 UI 预设温度
_UI_DEFAULT_TEMPERATURES: Dict[str, float] = {
    "deepseek": 0.3,   # 评审官走严谨
    "claude": 0.7,     # 综合判断
}
_FALLBACK_TEMPERATURE = 0.7


def _get_quick_model_id() -> Optional[str]:
    """读 streamlit session_state.quick_model_id；非 UI 上下文返回 None。"""
    if st is None:
        return None
    try:
        value = st.session_state.get("quick_model_id")
    except (AttributeError, KeyError):
        return None
    if value is None:
        return None
    qid = str(value).strip()
    return qid or None


def _resolve_temperature(qid: str) -> float:
    """API 强制优先，否则用 UI 预设。"""
    forced = get_forced_temperature(qid)
    if forced is not None:
        return forced
    return _UI_DEFAULT_TEMPERATURES.get(qid, _FALLBACK_TEMPERATURE)


def get_active_temperature() -> float:
    """返回当前选中的快速模型对应的强制温度；默认 0.7。"""
    qid = _get_quick_model_id()
    if not qid:
        return _FALLBACK_TEMPERATURE
    return _resolve_temperature(qid)


def get_active_llm_config() -> Optional[Dict[str, Any]]:
    """返回当前激活的 LLM 配置 dict，或 None（未选 / env 未配 / .env.local 损坏）。

    形状与 ``quick_models.get_quick_model_config`` 一致，并加入
    ``temperature`` 字段。

    .env.local 损坏（编码错误、IO 错误）会记 warning 并返回 None；
    不抛异常，让 UI 层用「未激活」走兜底路径。
    """
    qid = _get_quick_model_id()
    if not qid:
        return None
    try:
        cfg = get_quick_model_config(qid)
    except (OSError, KeyError, UnicodeDecodeError) as exc:
        _logger.warning("get_quick_model_config(%r) failed: %s", qid, exc)
        return None
    if not cfg:
        return None
    out = dict(cfg)
    out["temperature"] = _resolve_temperature(qid)
    return out


def is_llm_active() -> bool:
    """有没有激活的 LLM。等价于 ``get_active_llm_config() is not None``。"""
    return get_active_llm_config() is not None
