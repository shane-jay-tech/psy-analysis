# 接入 4 个常用模型为快捷预设（v4.3）

- **日期**：2026-05-23
- **范围**：新增 `src/llm_gateway/quick_models.py`；改 `gateway._resolve_llm_config` 与默认 backend；`app.py` 侧边栏顶部加 selectbox
- **协作模式**：单架构师直写（well-bounded scope；4 行配置 + 1 处 gateway hook + 1 处 UI）
- **关联**：[v4.1 上传题目](2026-05-23-impl-questionnaire-upload.md) · [v4.2 维度评分](2026-05-23-impl-ai-review-dimensions.md)

## 起因

用户长期在 `D:\code` 同时维护 4 个 OpenAI 兼容渠道（GPT-5.5 / DeepSeek V4 Pro / Kimi K2.6 / Claude Opus 4.7），密钥早就写在 `D:\code\.env.local` 里。但心理系统的 LLM 配置走的是 Streamlit 侧边栏手填 provider/api_key/model——和 `D:\code\scripts\llm_call.py` 完全是两套。

需求原话：
> 你直接把我现在使用的几个模型接入到心理分析系统，我只用到时候选择我要用哪一个就行了。

## 决策

**单一选择器（id 字符串）驱动一切**，密钥读 `.env.local` 不进 UI。

### 1. 新模块 `src/llm_gateway/quick_models.py`

```python
QUICK_MODELS = [
    QuickModel(id="gpt",      env_prefix="GPT",      provider="openai"),
    QuickModel(id="deepseek", env_prefix="DEEPSEEK", provider="deepseek"),
    QuickModel(id="kimi",     env_prefix="KIMI",     provider="moonshot"),
    QuickModel(id="claude",   env_prefix="CLAUDE",   provider="claude"),
]

def get_quick_model_config(model_id, *, timeout=600) -> Optional[Dict]:
    ...  # 返回 {provider, base_url, api_key, model, timeout, _quick_model_id}
```

- 启动时按 `_candidate_env_paths()` 找 `.env.local`（优先模块所在目录向上扫，兜底 `D:/code/.env.local` 写死路径）
- `load_env_local(force=False)`：把 `KEY=VALUE` 行装进 `os.environ`，**默认不覆盖**已有 env（与 `llm_call.py` 行为一致）
- 关键 env 缺一个 → `get_quick_model_config` 返回 `None`，UI 端可灰掉条目
- `_FORCED_TEMPERATURE = {"gpt": 1.0, "kimi": 1.0}` 与 `llm_call.py` 同步

### 2. gateway hook（`src/llm_gateway/gateway.py`）

```python
def _resolve_llm_config():
    quick_id = st.session_state.get("quick_model_id", "")
    if quick_id:
        cfg = get_quick_model_config(quick_id)
        if cfg is not None:
            return cfg  # 提前返回，绕过手填
    # ... 原 provider/api_key/model 路径不变
```

并在默认 backend wrapper 里读 `cfg["_quick_model_id"]`，对 GPT/Kimi 强制 `temperature=1.0`，覆盖上层 caller 写死的 0.3/0.7。

### 3. UI（`app.py` 侧边栏顶部）

```python
🤖 AI 模型: [📌 默认（手动设置） / GPT-5.5 / DeepSeek V4 Pro / Kimi K2.6 / Claude Opus 4.7]
```

- 未配置 env 的条目显示 `⚠️未配置`
- 选中后下方 caption 展示 `✅ <model>` + 角色描述（"主程序员/评审官/调研员/架构师"）
- 旧的「LLM 设置」面板继续存在；选「📌 默认」即回到手填模式（向后兼容）

## 安全

- 4 组 env 只在 `D:\code\.env.local` 中（已 gitignore：`.env.local` + `.env.*.local` 两条规则）
- 密钥不进 session_state、不进任何归档、不进日志
- session_state 只存 6 字符的 id（"gpt" 等）

## 测试

`tests/test_quick_models.py` 14 个测试：

1. `QUICK_MODELS` 4 条目 + provider 路由正确
2. 完整 env → config dict 形状正确（含 `_quick_model_id`）
3. 缺 API_KEY → None
4. 4 个模型同配齐时各返回独立 config
5. `_FORCED_TEMPERATURE` GPT/Kimi=1.0，DeepSeek/Claude=None
6. `list_available_quick_models` 按 env 标记 `available` 字段
7. `load_env_local` 从临时文件读 + 引号剥离 + 默认不覆盖已有 env

测试 fixture 把 `_candidate_env_paths` 改成空列表，避免误读真实 `D:\code\.env.local`。

全量回归：**1222 passed / 4 skipped**（baseline 1208，0 新失败）。

## 风险与权衡

- **session_state 一旦设了 quick_model_id，后续手填的 provider/api_key/model 就被忽略**——这是设计目的（"只选一次"），但用户清掉选择需要回选「📌 默认」
- 强制温度只在默认 backend wrapper 生效；如果别处直接读 `cfg["model"]` 自己拼 LLM 调用，温度需要 caller 自己处理（目前 `paper_writer/ai_tutor.py` 是统一入口，已覆盖）
- `D:\code\.env.local` 文件需要存在；若用户清掉文件，4 个条目都灰掉，UI 仍可用「📌 默认」走手填
- 不支持运行时改 `.env.local`（启动时一次性读入）；需要刷新页面 / 重启

## 不在本期

- 在 UI 里编辑 `.env.local` 内容（安全考虑：明文密钥不进 UI）
- 模型间路由（如 "调研走 Kimi、写作走 Claude" 自动分派）——目前一次只能选一个
