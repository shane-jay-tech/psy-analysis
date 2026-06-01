# LLM 配置单轨化 + 侧栏精简（v4.6）

**日期**：2026-05-25
**触发原因**：用户报告"上面 AI 模型选了之后，问卷设计还是走本地知识库；要在下面 LLM 配置好了才会调 LLM"

---

## 根本原因

双轨写入、单轨读取的 bug：
- 顶部「🤖 AI 模型」selectbox 只写 `st.session_state.quick_model_id`
- 但问卷设计 / 实验设计 / AI 助教 / AI 润色 等老代码都直接读 `st.session_state.llm_provider / llm_api_key / llm_model / llm_temperature`，绕过 quick_model
- 结果：选了顶部预设也没用，必须再去填底部 panel

之前架构上有两套 UI（顶部 4 预设 + 底部手填），心智成本和维护成本都高。

---

## 决策

砍底部「🤖 LLM 配置」整段（含「备用模型 fallback」）。所有 LLM 调用统一从 `quick_model_id` → `D:\code\.env.local` 读。
温度按预设强制（GPT/Kimi=1.0，DeepSeek=0.3，Claude=0.7），用户不调。
侧栏 9 个 expander 整合成 4 块（顶部决策区 + 📁 项目·工作区 + 💡 帮助·入门 + ⚙️ 设置·状态）。

用户问卷答案：
- "把两个合并成为一个就可以了，只保留快速模型那个就行"
- "按预设强制，别让我调（推荐）"
- "明确报错：请去填 .env.local，指到模板文件"
- "目前的面板也有点繁杂了，你精简优化一下" → 选「中度：4 块」

---

## 改了什么

### 新增
- `src/llm_gateway/active_config.py` — 唯一 LLM 配置入口（`get_active_llm_config()` / `is_llm_active()` / `get_active_temperature()`）
- `D:\code\.env.local.example` — 三件套模板（GPT_/DEEPSEEK_/KIMI_/CLAUDE_ × BASE_URL/API_KEY/MODEL）

### 删除
- 底部「🤖 LLM 配置」expander（旧 631-890 行）
- 「备用模型 fallback」整块（含 `llm_fallback_*` session 字段）
- `app.py` 的 `from config.llm_providers import LLM_PROVIDERS` 和 `from src.utils.api_key_store import ...`（运行时不再用）
- `gateway._resolve_fallback_candidates()` / `chat_with_smart_fallback` 退化为单调用

### 改动
- `app.py`：
  - 侧栏 491-991 重构为 4 块（顶部决策区 + 📁/💡/⚙️ 三个 expander）
  - LLM 状态 panel（~1530）改读 `get_active_llm_config()`
  - 问卷 design_btn 主路径（~1770）改读 active_config
  - premium 失败降级（~1720）改读 active_config
  - regenerate-with-override（~1960）改读 active_config
  - 400 错误信息指向 `D:\code\.env.local`（不再提"侧栏 LLM 配置"）
  - 版本 caption：v3.7 → v4.6
- `src/llm_gateway/gateway.py`：
  - `_resolve_llm_config()` 简化为转发 active_config
  - `is_llm_available()` 默认走 `is_llm_active()`
  - `chat_with_smart_fallback()` 单调用化
- `src/ui/undergrad_wizard.py`：
  - 删 `LLM_PROVIDERS` import
  - AI tutor / 答辩 / AI 润色 三处共 5 个站点改读 active_config
- `src/ui/experiment_design_ui.py`：
  - 删 `LLM_PROVIDERS` import
  - LLM 增强路径改读 active_config
- `src/utils/env_check.py`：`check_llm_api()` 改用 `list_available_quick_models()`，启动检查直接报"快速模型已配置：GPT-5.5、DeepSeek V4 Pro…等 N 个"
- `src/utils/workspace.py`：snapshot 键从 `["llm_provider", "llm_model", "llm_temperature", "app_mode"]` 改为 `["app_mode", "quick_model_id"]`；旧版 JSON 加载时 `llm_*` 键静默忽略（向后兼容）
- `tests/test_ui.py:test_session_defaults_structure`：旧 LLM 字段断言更新为 `quick_model_id`

---

## 仲裁

DeepSeek 审查派遣阶段被用户中断，跳过独立审查。回归保护依靠：
1. **测试套件 1260 passed / 4 skipped**（运行时间 171.88s）— 覆盖 active_config / gateway / 问卷引擎 / 工作区往返 / UI session 默认结构
2. **AST 语法验证**全部 7 个改动文件 — 都过
3. **向后兼容**：workspace.py 加载旧 JSON 静默忽略 `llm_*`，不会炸用户存档

剩余风险（如果出现回头修）：
- 真实点过的 UI 路径只能让用户上线后说话；测试套件无法覆盖 streamlit 运行时
- `quick_model_id` 切换时 gateway 缓存可能 stale；如发现选了模型但回了旧响应，加 `clear_cache()` 即可
- 用户首次启动若没填 `.env.local`，顶部 selectbox 显示「⚠️未配置」，需要看 caption 才知道指 `.env.local.example`

---

## 用户视角

- 侧栏从 9 个折叠面板缩成 4 块，第一眼能看到所有功能入口
- 选 AI 模型只看顶部一个 selectbox，不再有"上面选了下面又要填"的双轨困惑
- 没填 `.env.local` 时报错明确指向模板路径
- 模型温度按预设强制，不再需要懂"温度是什么"
