# -*- coding: utf-8 -*-
"""s918-41：LLM 激活配置兜底契约测试（active_config.py 95 行盲区）。

docstring 明示兜底契约：未选/未配/.env.local 损坏 → None 不抛异常。
测试以 monkeypatch 打桩 _get_quick_model_id / get_quick_model_config，
不读真实 .env.local、不联网。
"""
import pytest

from src.llm_gateway import active_config
from src.llm_gateway.active_config import (
    get_active_llm_config,
    is_llm_active,
)


def test_no_quick_model_id_returns_none(monkeypatch):
    """未选模型：_get_quick_model_id None → get_active_llm_config None。"""
    monkeypatch.setattr(active_config, "_get_quick_model_id", lambda: None)
    assert get_active_llm_config() is None
    assert is_llm_active() is False


def test_quick_model_config_oserror_returns_none(monkeypatch):
    """.env.local 损坏（OSError）→ None 不抛。"""
    monkeypatch.setattr(active_config, "_get_quick_model_id", lambda: "q99")

    def boom(_):
        raise OSError("disk error")

    monkeypatch.setattr(active_config, "get_quick_model_config", boom)
    assert get_active_llm_config() is None
    assert is_llm_active() is False


def test_quick_model_config_unicodeerror_returns_none(monkeypatch):
    """.env.local 编码错误（UnicodeDecodeError）→ None 不抛。"""
    monkeypatch.setattr(active_config, "_get_quick_model_id", lambda: "q99")

    def boom(_):
        raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

    monkeypatch.setattr(active_config, "get_quick_model_config", boom)
    assert get_active_llm_config() is None


def test_normal_config_contains_temperature(monkeypatch):
    """正常路径：返回 dict 含 temperature 字段。"""
    monkeypatch.setattr(active_config, "_get_quick_model_id", lambda: "q_ok")
    monkeypatch.setattr(active_config, "get_quick_model_config", lambda qid: {"model": "deepseek-v4-flash"})
    monkeypatch.setattr(active_config, "_resolve_temperature", lambda qid: 0.3)
    cfg = get_active_llm_config()
    assert cfg is not None
    assert cfg["model"] == "deepseek-v4-flash"
    assert "temperature" in cfg


def test_is_llm_active_equivalence(monkeypatch):
    """is_llm_active ≡ get_active_llm_config() is not None。"""
    monkeypatch.setattr(active_config, "_get_quick_model_id", lambda: None)
    assert is_llm_active() == (get_active_llm_config() is not None)
    monkeypatch.setattr(active_config, "_get_quick_model_id", lambda: "q_ok")
    monkeypatch.setattr(active_config, "get_quick_model_config", lambda qid: {"model": "m"})
    monkeypatch.setattr(active_config, "_resolve_temperature", lambda qid: 0.3)
    assert is_llm_active() == (get_active_llm_config() is not None)
