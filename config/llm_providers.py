"""LLM 提供商预设配置（无需外部配置文件）

v3.7 更新：
- 静态默认列表升级到 2026-05 已知最新
- 新增 Kimi (Moonshot) + Claude 两个 provider
- 实际使用时建议点 sidebar「🔄 获取最新模型」从 /v1/models 端点拉取实时列表

支持的提供商：
- deepseek: DeepSeek (国内可直接访问，OpenAI 兼容)
- zhipu: 智谱 GLM (国内可直接访问，OpenAI 兼容)
- moonshot: Kimi/月之暗面 (国内可直接访问，OpenAI 兼容)
- openai: OpenAI (需要 VPN)
- claude: Anthropic Claude（需要 OneAPI/硅基流动等中转代理）
- ollama: Ollama (本地免费)
- custom: 自定义端点（OpenAI 兼容）
- none: 不使用 LLM（纯本地模式）
"""

from typing import Dict, Any


def _build_providers() -> Dict[str, Any]:
    """内置默认提供商。models 字段为静态默认列表；运行时可调 fetch_models 覆盖。"""
    return {
        "none": {
            "name": "不使用 LLM（纯本地模式）",
            "base_url": "",
            "default_model": "",
            "models": [],
            "supports_fetch_models": False,
            "description": "完全离线，使用内置关键词匹配引擎。问卷设计等功能不受影响。",
        },
        "deepseek": {
            "name": "DeepSeek (国内可直接访问)",
            "base_url": "https://api.deepseek.com",
            # 默认用稳定可用的 model ID（API 实际接受值）
            "default_model": "deepseek-chat",
            "models": [
                "deepseek-chat",         # ✅ 稳定可用：V3 通用
                "deepseek-reasoner",     # ✅ 稳定可用：R1 推理
                # ⚠️ 以下为可能更新的版本，不一定被 API 接受，建议点 🔄 验证
                "deepseek-v3.2-exp",
                "deepseek-v3.1",
            ],
            "supports_fetch_models": True,
            "description": (
                "⚠️ 默认 `deepseek-chat` 是 API 已知接受的稳定 ID。其他名称（如 v3.2-exp）"
                "可能不被 API 接受 → 报 400 错。建议先点「🔄 获取最新模型」拉取你账号实际可用列表。"
            ),
        },
        "zhipu": {
            "name": "智谱 GLM (国内可直接访问)",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "default_model": "glm-4-plus",
            # 精简：保留当代 plus/flash/air，删除特殊变体
            "models": [
                "glm-4-plus",       # 当代旗舰
                "glm-4-air",        # 平衡
                "glm-4-flash",      # 免费快速
            ],
            "supports_fetch_models": True,
            "description": "国产模型，flash 免费额度充足，plus 旗舰能力强。完整列表点「🔄」联网获取。",
        },
        "moonshot": {
            "name": "Kimi / Moonshot (国内可直接访问)",
            "base_url": "https://api.moonshot.cn/v1",
            # 默认用稳定 API ID
            "default_model": "kimi-latest",
            "models": [
                "kimi-latest",              # ✅ 稳定：自动追踪
                "kimi-thinking-preview",    # ✅ 推理变体
                "moonshot-v1-128k",         # ✅ 稳定：长文本
                "moonshot-v1-32k",
                # ⚠️ 以下为可能的新版命名，不一定被 API 接受
                "kimi-k2-0905-preview",
                "kimi-k2-turbo-preview",
            ],
            "supports_fetch_models": True,
            "description": (
                "⚠️ 默认 `kimi-latest` 自动追踪最新稳定版（最保险）。其他名称可能不被 API 接受。"
                "建议点「🔄」拉取你账号实际可用列表。"
            ),
        },
        "openai": {
            "name": "OpenAI (需要 VPN)",
            "base_url": "https://api.openai.com/v1",
            # 默认用众所周知稳定的 ID
            "default_model": "gpt-4o-mini",
            "models": [
                "gpt-4o-mini",         # ✅ 稳定：便宜快速
                "gpt-4o",              # ✅ 稳定：通用旗舰
                "o4-mini",             # ✅ 推理小模型
                # ⚠️ 以下为可能的新版命名，不一定被 API 接受
                "gpt-5",
                "gpt-5-mini",
                "gpt-5-pro",
            ],
            "supports_fetch_models": True,
            "description": (
                "⚠️ 默认 `gpt-4o-mini` 是 API 已知接受的稳定 ID。GPT-5 系列等较新名称需要"
                "你账号实际订阅且模型 ID 拼写正确。建议点「🔄」拉取实际可用列表。"
            ),
        },
        "claude": {
            "name": "Anthropic Claude (需中转代理)",
            "base_url": "https://api.anthropic.com",
            # Anthropic 实际 API model ID 通常含日期版本号，这里只放最稳的
            "default_model": "claude-3-5-sonnet-20241022",
            "models": [
                # ✅ 已知稳定的 API model ID（含日期版本号）
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229",
                # ⚠️ 以下为简短别名，可能需要带日期后缀才被 API 接受
                "claude-opus-4-8",
                "claude-sonnet-4-6",
                "claude-haiku-4-5",
            ],
            "supports_fetch_models": True,
            "description": (
                "⚠️ 直连 Anthropic API 的 model ID **通常需要带日期后缀**（如 "
                "`claude-3-5-sonnet-20241022`）。简短别名（如 `claude-opus-4-8`）通过中转代理"
                "可能可用，直连不一定。强烈建议点「🔄」获取你账号实际可用列表。"
                "另外：Anthropic API 协议路径与 OpenAI 不同，建议通过 OneAPI/硅基流动 中转。"
            ),
        },
        "ollama": {
            "name": "Ollama (本地，免费)",
            "base_url": "http://localhost:11434/v1",
            "default_model": "qwen2.5:7b",
            "models": [],   # ollama 模型由本地部署决定，从 /api/tags 获取
            "supports_fetch_models": True,    # 走 /api/tags 而非 /v1/models
            "description": "完全免费，无需网络。需先安装 Ollama 并拉取模型。建议 ≥7B 获得反问质量。",
        },
        "custom": {
            "name": "自定义端点 (OpenAI 兼容)",
            "base_url": "",
            "default_model": "",
            "models": [],
            "supports_fetch_models": True,
            "description": (
                "接入任意 OpenAI 兼容 API（硅基流动 / 阿里百炼 / OneAPI 等）。"
                "Claude/Gemini 通过此入口使用代理服务。"
            ),
        },
    }


LLM_PROVIDERS = _build_providers()
