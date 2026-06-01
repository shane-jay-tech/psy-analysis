"""LLM 配置加载测试（v2.7 无 YAML 依赖版本）"""

import pytest
from config.llm_providers import LLM_PROVIDERS


class TestLLMProviders:
    def test_providers_dict(self):
        assert isinstance(LLM_PROVIDERS, dict)
        assert "deepseek" in LLM_PROVIDERS
        assert "zhipu" in LLM_PROVIDERS
        assert "openai" in LLM_PROVIDERS
        assert "ollama" in LLM_PROVIDERS
        assert "custom" in LLM_PROVIDERS
        assert "none" in LLM_PROVIDERS  # 新增：不使用 LLM 选项

    def test_none_provider_structure(self):
        none_cfg = LLM_PROVIDERS["none"]
        assert none_cfg["name"] == "不使用 LLM（纯本地模式）"
        assert none_cfg["models"] == []

    def test_deepseek_structure(self):
        ds = LLM_PROVIDERS["deepseek"]
        assert ds["name"] == "DeepSeek (国内可直接访问)"
        assert ds["base_url"] == "https://api.deepseek.com"
        assert "deepseek-chat" in ds["models"]

    def test_custom_structure(self):
        custom = LLM_PROVIDERS["custom"]
        assert "自定义端点" in custom["name"]
        assert custom["base_url"] == ""

    def test_all_providers_have_name(self):
        for key, cfg in LLM_PROVIDERS.items():
            assert "name" in cfg, f"{key} missing 'name'"
            assert "base_url" in cfg, f"{key} missing 'base_url'"
            assert "description" in cfg, f"{key} missing 'description'"
