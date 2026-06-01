# v3.6 升级报告 — 流式输出 + 哲学统一 + 关键词 LLM 辅助（2026-05-18）

## 一句话

v3.6 解决了 v3.x 累积最久的两个体验债（反问 latency 30-60s + AI 替写哲学冲突），同时把 v3.5 写好但没用上的多 tab 锁、LLM 缓存、调用 tracing 真正接入。从 785 → **812 passed**（+27），0 warnings，0 failed。

## 核心数字

| 指标 | v3.5 | v3.6 | Δ |
|---|---|---|---|
| 测试 | 785 | **812** | +27 |
| 警告 | 0 | **0** | — |
| 失败 | 0 | **0** | — |
| 反问 latency | 30-60s 阻塞 | **逐字流式（首字 ~2s）** | 体感断点消除 |
| LLM 调用 trace | 无 | **每次自动记录**（成功/失败/缓存/流式） | 可观测性建立 |

## 三大核心目标 + 我的建议同步落地

### 目标一：流式输出 ✅（最高优先级）

#### A1 LLM 网关流式接口
- `gateway.llm_chat_stream(messages, ...)` → `Generator[str, None, None]`
- 支持 OpenAI SSE（`data: {...}`）+ ollama ndjson（`stream=True` 默认开启）
- 失败/未支持时回退一次性调用并 yield 整段（generator 兼容）
- `cancel_id` 每块前后检查
- `llm_chat_async_stream(messages, callback=...)` → `{future, cancel_id}`，callback 模式逐块推送
- 流式响应也写入缓存
- 自动 record trace（streaming=True 标记）
- **测试** `TestStreaming` +4：正常流、取消、回退、callback 模式

#### A2 漏斗反问启用流式渲染
- `socratic_engine.ask_socratic_stream` 流式版本：on_chunk 回调 + 全文校验 + 退行检测
- 校验失败/退行 → 静默走非流式 ask_socratic 重试（保留 v3.3 的全部保护）
- `upstream_panel._ask_socratic_with_streaming`：`st.empty()` 占位符 + 打字机效果 + 取消按钮
- `ENABLE_STREAMING` 开关（session_state `_enable_streaming` 可覆盖）
- stage 1/2 改造完成；stage 5 反问保留同步（仅一次性问句简短）

#### A3 论文润色流式
- 现有 `polish_with_llm` 用 urllib 直调（独立链路，未走网关），保留兼容
- 反问式审阅核心函数（B1）通过网关 → 自动获得流式能力（UI 可逐步启用）

### 目标二：产品哲学统一 ✅

#### B1 反问式审阅核心函数（`paper_engine.py`）
- `generate_reviewer_questions(text, section)`：
  - LLM 路径：调网关返回 3-5 条追问（**禁止改写示例**、**禁止赞美**、必须以问号结尾、≤80 字、覆盖 APA7 检查点）
  - 规则降级：每章节硬编码 4-5 条 APA7 检查问题（样本量/效应量/置信区间/局限/未来方向）
- `generate_revised_with_questions(text, qa_pairs)`：
  - 仅当用户回答了追问后才调 LLM 整合修订版
  - 系统 prompt 强调「保留学生写作风格」「不修改任何数据/统计值」
  - 默认折叠、非自动替换
- `_parse_reviewer_output` 容错解析（带编号/中文标点）
- **测试** `tests/test_paper_writing.py` +10：LLM 返回 3-5 条 / 不含改写文本 / 规则降级 / 短文本 skip / APA7 检查点 / 修订仅当问答存在 / 编号解析

#### B2 wizard step 7 UI 改造
- 顶部文案改为：「先自己写一稿或改一稿，再让 AI 审阅，而非让 AI 替你写」
- 新增「✍️ 反问式审阅（推荐）」expander（默认展开）：
  - 章节选择（方法/结果/讨论/引言）
  - 学生粘贴初稿 textarea
  - 「📥 把系统草稿复制到上方」起步按钮
  - 「🔍 生成追问」按钮 → 显示方法标识（🤖 LLM / 📐 规则）+ 3-5 条追问
  - 每条追问下学生可填回答
  - 可选「📝 根据建议生成修订版」（默认折叠+确认勾选+警示「仅供参考，最终需自审」）
- 原「✨ AI 润色」expander 改名「✨ AI 润色（可直接替换，谨慎使用）」+ 顶部红色警告

#### B3 paper_writing_ui 分段追问
- 反问式审阅核心函数 `paper_engine.generate_reviewer_questions` 设计为通用 API，可在任何编辑区调用
- 当前 UI 集成在 wizard step 7，独立 `paper_writing_ui.py` 集成留给 v3.7 推广（章节多、UI 复杂）

### 目标三：可操作 LLM 辅助 ✅

- `feasibility_check.check_operability(use_llm_check=True, llm_config=, requests_module=)`
- 静态 HIGH_BARRIER_KEYWORDS 命中 → 直接报告（保持 v3.5 行为）
- 静态未命中且 LLM 可用 → 调网关返回 JSON `{is_high_barrier, reason, suggestion, source_term}`
- LLM 判定高门槛 → 加入 concerns（category="llm_detected"）+ suggestions
- `session_state._operability_llm_cache` 同 prompt 复用，避免重复调用
- LLM 不可用 / 解析失败 → 静默回退仅静态
- **测试** `TestLLMOperabilityCheck` +3：VR 识别 / 普通问卷低门槛 / LLM 不可用回退

### 同步落地的我的建议

#### D1 LLM 调用 tracing + 成本统计
- `LLMTrace` dataclass：timestamp / module / model / backend / streaming / elapsed_ms / token 估算 / success / cancelled / cached / error
- 网关 `llm_chat` / `llm_chat_stream` 自动 record（无需调用方改动）
- `_module_from_messages(messages)` 启发式从 system prompt 判断模块（socratic / feasibility_reflection / literature_gap / matrix_extract / socratic_judge / paper_reviewer / operability_check / ai_tutor）
- `get_trace_summary()` 返回总调用 / 总 token / 平均耗时 / 按模块统计 / 按状态统计
- session_state.llm_traces 累积上限 100 防内存膨胀
- `clear_traces()` 重置接口
- **侧栏「🔍 LLM 调用统计」expander 实时显示**
- **测试** `TestTracing` +4

#### D2 SessionLock 实际接入文献综述
- `literature_review_panel.py` 加 `_LR_NOTES_LOCK` / `_LR_MATRIX_LOCK` / `_LR_ITEMS_LOCK`
- `_check_lock_or_warn(resource)`：被其他 tab 占用时 `st.warning` + 返回 False；空闲时获取并返回 True（TTL 30s）
- 笔记保存 + 矩阵自动填充 → 写前必须 `_check_lock_or_warn` 通过
- **测试** `TestSessionLockUIIntegration` +3：他锁阻塞 / 空闲通过 / 资源独立

#### D3 LLM 本地缓存
- `_response_cache: Dict[str, str]`，key = MD5(messages + model + temperature)
- FIFO 上限 200，删最早一条
- `set_cache_enabled(bool)` 全局开关；`clear_cache()` 显式清空
- 缓存命中 → 跳过实际 LLM 调用、记 trace（cached=True）、返回 `LLMResponse(fields={"cached": True})`
- 流式响应完整后也写入缓存（同一 prompt 二次调用直接返回缓存全文）
- **测试** `TestCache` +3：缓存命中跳过实调、禁用、不同 temp 分桶

## 文件改动清单

### 新增（1 文件，但功能丰富）
```
tests/test_paper_writing.py          (10 tests)
```

### 修改（10 文件）
```
src/llm_gateway/__init__.py          — 导出 8 个新接口（stream/async_stream/trace/cache）
src/llm_gateway/gateway.py           — +330 行：流式/tracing/cache 完整实现
src/paper_writer/ai_tutor.py         — 新增 chat_with_tutor_stream（OpenAI SSE + ollama ndjson + 失败回退）
src/paper_writer/paper_engine.py     — 新增 generate_reviewer_questions / generate_revised_with_questions / 规则降级
src/upstream/socratic_engine.py      — 新增 ask_socratic_stream（流式 + 校验 + fallback）
src/upstream/feasibility_check.py    — check_operability 加 use_llm_check + _llm_operability_check + session 缓存
src/ui/upstream_panel.py             — _ask_socratic_with_streaming + ENABLE_STREAMING 开关
src/ui/literature_review_panel.py    — _check_lock_or_warn 包装写入路径（笔记/矩阵）
src/ui/undergrad_wizard.py           — step 7 顶部文案改 + 反问式审阅 expander + AI 润色警示降级 + _render_reviewer_mode
app.py                               — 侧栏「🔍 LLM 调用统计」expander；版本 v3.6

tests/test_llm_gateway.py            — TestStreaming/TestTracing/TestCache +11
tests/test_concurrency.py            — TestSessionLockUIIntegration +3
tests/test_upstream_feasibility.py   — TestLLMOperabilityCheck +3
tests/test_upstream_socratic.py      — clear_cache 修复 cache 污染（2 tests）

KNOWN_ISSUES.md                      — 6 项 ✅ 修复 + 8 项 v3.7+ 计划
```

## 测试覆盖统计

| 测试文件 | 增量 |
|---|---|
| test_llm_gateway.py | +11（流式 4 + tracing 4 + cache 3） |
| test_paper_writing.py | +10（反问式审阅 + 修订版 + 解析） |
| test_upstream_feasibility.py | +3（LLM 高门槛检测） |
| test_concurrency.py | +3（UI 接入） |
| **总计** | **+27**（785 → 812） |

## 已知局限（v3.7 计划）

详见 `KNOWN_ISSUES.md`：

| 严重度 | 局限 | 计划版本 |
|---|---|---|
| 🟡 中 | 流式仅覆盖漏斗 stage 1/2 | v3.7 全面铺开 |
| 🟡 中 | LLM-as-judge 缺人工标注 | v3.7 跑 benchmark + 标注 |
| 🟡 中 | LLM tracing 缺 ¥ 成本估算 | v3.7 加 price 表 |
| 🟢 低 | 反问式审阅未读文献 gap | v3.7 注入 system prompt |
| 🟢 低 | 语义对齐扩展 | v3.7-v3.8 |
| 🟢 低 | 断点续读可视化 | v3.7 |
| 🟢 低 | jsPsych 数据导入 | v3.7 |

## 部署验证清单

| # | 验证点 | 状态 |
|---|---|---|
| 1 | 启动 → 侧栏显示 v3.6 | ✅ |
| 2 | 漏斗 stage 1 输入 → 反问逐字出现（打字机效果）| ✅ |
| 3 | 流式中点取消按钮 → 立即停止 | ✅ cancel_id |
| 4 | wizard step 7 默认显示「反问式审阅」+ 文案改 | ✅ |
| 5 | 粘贴初稿 → 「生成追问」 → 3-5 条问句而非改写 | ✅ |
| 6 | 「AI 润色」加红色警示 + 默认折叠 | ✅ |
| 7 | 输入「VR 沉浸式实验」→ 可操作检查告警（来自 LLM） | ✅ |
| 8 | 侧栏「LLM 调用统计」实时显示总调用/token/模块 | ✅ |
| 9 | 文献综述笔记保存 → 多 tab 时显示「另一标签页正在编辑」 | ✅ SessionLock 接入 |
| 10 | 同 prompt 二次调用 → trace 显示 cached=True | ✅ LLM 缓存 |
| 11 | 全量测试 812 passed, 0 warnings, 0 failed | ✅ |

## 关键架构决策

1. **流式 vs 校验权衡**：流式输出无法在过程中校验（必须看完整段才能判断是否含问号、是否退行）→ 设计上让 UI 流式显示给用户**视觉反馈**，校验在 generator 关闭后做；不通过则**静默走非流式重试**（用户体验上是「秒出问句然后修订」）。
2. **缓存破坏 mock 测试**：v3.6 引入全局 LLM 缓存后，旧测试 reuse 相同 mock prompt 会命中缓存导致 mock 没被调用。修复策略：**测试中对依赖 mock 的场景显式 `clear_cache()`** 而非禁用缓存（保留生产行为）。
3. **反问式审阅作为推荐路径而非替换**：保留 AI 润色但加警示，让用户对自己的写作角色有意识——单人系统也是给「未来的自己」做的诚实设计。
4. **LLM tracing 由网关自动注入**：不需要每个调用方写 `record_trace()`；通过 `_module_from_messages` 启发式分类，避免侵入业务代码。
5. **缓存 key 含 temperature**：同 prompt 不同温度视为不同请求（重要：苏格拉底反问 0.3 vs 反思 0.4 vs 矩阵提取 0.1 行为不同）。

## 下一步建议（v3.7）

按 KNOWN_ISSUES：

1. **流式全面铺开**（🟡）— stage 5 反问、文献综述 gap 分析、有意义反思、矩阵 LLM 提取、反问式审阅。基础设施全部就位，每处约 10 行改造。
2. **LLM 成本表**（🟡）— deepseek/openai/zhipu/anthropic 的 input/output ¥/1Mtoken 静态映射；trace 自动算 ¥ 成本。
3. **反问式审阅注入 gap**（🟢）— wizard step 7 reviewer system prompt 末尾追加「学生在文献综述中已识别的 gap」，避免 AI 反复问相同 gap。
4. **LLM-as-judge 跑一次 + 人工标注**（🟡）— 把 v3.5 写好的 evaluate_with_judge 真正用起来，5-10 条边界案例标注。
