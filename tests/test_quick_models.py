"""测试 v4.3 快捷模型预设：load_env_local + get_quick_model_config + 强制温度。

不打真 API；用临时 .env 文件 + monkeypatch 隔离 os.environ。
"""
from __future__ import annotations

import importlib
import os

import pytest

from src.llm_gateway import quick_models as qm


_ENV_KEYS = [
    "GPT_BASE_URL", "GPT_API_KEY", "GPT_MODEL",
    "DEEPSEEK_BASE_URL", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL",
    "KIMI_BASE_URL", "KIMI_API_KEY", "KIMI_MODEL",
    "CLAUDE_BASE_URL", "CLAUDE_API_KEY", "CLAUDE_MODEL",
]


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """每个测试前清空 4 组 env，并屏蔽真实 .env.local 的读取。"""
    for k in _ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    # 默认 _candidate_env_paths 返回空 → load_env_local 成 no-op
    monkeypatch.setattr(qm, "_candidate_env_paths", lambda: [])
    yield


def _set_full_env(monkeypatch, prefix: str, model_name: str = "test-model"):
    monkeypatch.setenv(f"{prefix}_BASE_URL", f"https://example.com/{prefix.lower()}/v1")
    monkeypatch.setenv(f"{prefix}_API_KEY", f"sk-{prefix.lower()}-fake")
    monkeypatch.setenv(f"{prefix}_MODEL", model_name)


# ---------------------------------------------------------------------------
# QUICK_MODELS 元数据
# ---------------------------------------------------------------------------

def test_quick_models_list_has_four_entries():
    ids = [m.id for m in qm.QUICK_MODELS]
    assert ids == ["gpt", "deepseek", "kimi", "claude"]


def test_quick_models_provider_routing():
    """每个 id 路由到 gateway 已支持的 provider。"""
    pmap = {m.id: m.provider for m in qm.QUICK_MODELS}
    assert pmap["gpt"] == "openai"
    assert pmap["deepseek"] == "deepseek"
    assert pmap["kimi"] == "moonshot"
    assert pmap["claude"] == "claude"


def test_get_quick_model_by_id_unknown_returns_none():
    assert qm.get_quick_model_by_id("unknown") is None


# ---------------------------------------------------------------------------
# get_quick_model_config
# ---------------------------------------------------------------------------

def test_get_config_with_full_env(monkeypatch):
    """4 组 env 都配齐 → 返回 gateway 形状的 dict。"""
    _set_full_env(monkeypatch, "GPT", "gpt-5.5")
    cfg = qm.get_quick_model_config("gpt")
    assert cfg is not None
    assert cfg["provider"] == "openai"
    assert cfg["base_url"] == "https://example.com/gpt/v1"
    assert cfg["api_key"] == "sk-gpt-fake"
    assert cfg["model"] == "gpt-5.5"
    assert cfg["timeout"] == 600
    assert cfg["_quick_model_id"] == "gpt"


def test_get_config_missing_key_returns_none(monkeypatch):
    """缺 API_KEY → None（UI 端可灰掉选项）。"""
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://x")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4")
    # 不设 API_KEY
    assert qm.get_quick_model_config("deepseek") is None


def test_get_config_unknown_id_returns_none():
    assert qm.get_quick_model_config("unknown") is None


def test_get_config_custom_timeout(monkeypatch):
    _set_full_env(monkeypatch, "KIMI")
    cfg = qm.get_quick_model_config("kimi", timeout=120)
    assert cfg is not None
    assert cfg["timeout"] == 120


def test_get_config_for_all_four(monkeypatch):
    """4 个模型同时配齐时都能各自返回一份 config。"""
    _set_full_env(monkeypatch, "GPT", "gpt-5.5")
    _set_full_env(monkeypatch, "DEEPSEEK", "deepseek-v4-pro")
    _set_full_env(monkeypatch, "KIMI", "kimi-k2.6")
    _set_full_env(monkeypatch, "CLAUDE", "claude-opus-4-8")
    for mid, expected_model in [
        ("gpt", "gpt-5.5"),
        ("deepseek", "deepseek-v4-pro"),
        ("kimi", "kimi-k2.6"),
        ("claude", "claude-opus-4-8"),
    ]:
        cfg = qm.get_quick_model_config(mid)
        assert cfg is not None, f"{mid} 应可解析"
        assert cfg["model"] == expected_model
        assert cfg["_quick_model_id"] == mid


# ---------------------------------------------------------------------------
# 强制温度
# ---------------------------------------------------------------------------

def test_forced_temperature_gpt_kimi():
    assert qm.get_forced_temperature("gpt") == 1.0
    assert qm.get_forced_temperature("kimi") == 1.0


def test_forced_temperature_others_none():
    """DeepSeek / Claude 不强制温度。"""
    assert qm.get_forced_temperature("deepseek") is None
    assert qm.get_forced_temperature("claude") is None
    assert qm.get_forced_temperature("unknown") is None


# ---------------------------------------------------------------------------
# list_available_quick_models（UI 渲染用）
# ---------------------------------------------------------------------------

def test_list_marks_unavailable_when_env_missing(monkeypatch):
    """所有 env 都没配 → 4 个条目都 available=False。"""
    rows = qm.list_available_quick_models()
    assert len(rows) == 4
    for r in rows:
        assert r["available"] is False
        assert r["model"] == ""
        assert r["id"] in {"gpt", "deepseek", "kimi", "claude"}
        assert r["label"]


def test_list_marks_available_when_env_present(monkeypatch):
    _set_full_env(monkeypatch, "CLAUDE", "claude-opus-4-8")
    rows = qm.list_available_quick_models()
    by_id = {r["id"]: r for r in rows}
    assert by_id["claude"]["available"] is True
    assert by_id["claude"]["model"] == "claude-opus-4-8"
    # 其他三个仍未配置
    assert by_id["gpt"]["available"] is False
    assert by_id["deepseek"]["available"] is False
    assert by_id["kimi"]["available"] is False


# ---------------------------------------------------------------------------
# load_env_local：从临时 .env.local 文件读
# ---------------------------------------------------------------------------

def test_load_env_local_from_tempfile(monkeypatch, tmp_path):
    """临时 .env.local 中的 KIMI_* 三件套被读入 os.environ。"""
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "# 注释行\n"
        "KIMI_BASE_URL=https://kimi.test/v1\n"
        'KIMI_API_KEY="sk-kimi-tmp"\n'
        "KIMI_MODEL=kimi-k2.6\n"
        "\n",
        encoding="utf-8",
    )
    # 让 _candidate_env_paths 返回我们的临时文件
    monkeypatch.setattr(qm, "_candidate_env_paths", lambda: [env_file])
    qm.load_env_local(force=True)
    assert os.environ.get("KIMI_BASE_URL") == "https://kimi.test/v1"
    # 引号被剥离
    assert os.environ.get("KIMI_API_KEY") == "sk-kimi-tmp"
    assert os.environ.get("KIMI_MODEL") == "kimi-k2.6"


def test_load_env_local_does_not_overwrite_by_default(monkeypatch, tmp_path):
    """默认 force=False，已存在的 os.environ 不会被覆盖。"""
    env_file = tmp_path / ".env.local"
    env_file.write_text("GPT_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("GPT_API_KEY", "from-os")
    monkeypatch.setattr(qm, "_candidate_env_paths", lambda: [env_file])
    qm.load_env_local()  # force=False
    assert os.environ.get("GPT_API_KEY") == "from-os"
