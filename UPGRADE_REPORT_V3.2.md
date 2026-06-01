# v3.2 升级报告 — 选题漏斗 + AI 苏格拉底（2026-05-17）

## 一句话

把 AI 角色从下游的「替你做」（写论文、生成图表）扩展到上游的「逼你想清楚」（苏格拉底反问），让本科生在选题阶段就少踩坑。

## 核心成果

- **科研流程覆盖从下游扩展到上游**：v3.1 覆盖第 5-11 步（清洗→分析→写作→答辩），v3.2 新增第 1-4 步的「选题漏斗」（兴趣→现象→变量→可研究性→问题陈述）
- **新模块** `src/upstream/`（5 文件，~900 行）+ `src/ui/upstream_panel.py`（~400 行）
- **测试** 449 → 517（+68 tests），0 warnings, 0 failed
- **架构**：项目生命周期状态机（phase: funnel | wizard | done），数据贯通到下游 wizard 字段

## 已锁定的设计决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 用户分层 | BEGINNER + ADVANCED | 本科要兜得多，研究生要给空间 |
| 漏斗位置 | 前置独立入口（新建项目→漏斗→跳 wizard） | 职责清晰，wizard 文件不臃肿 |
| LLM 策略 | **强制 API key**（无 key 灰显） | 苏格拉底反问质量决定一切，模板化反问意义不大 |
| 范例库规模 | 6 大领域 × 1 例 = 6 条（v3.3 扩 18） | 范围控制：先把核心流程跑通 |
| 老项目处理 | 已有 research_q → 直接进 wizard，空白 → 进漏斗 | 最小惊讶，不强迫老用户回头走 |
| ADVANCED 模式 | v3.2 直接跳过漏斗（产物 schema 一致），完整折叠模式 v3.3 | 范围控制 |

## 7 项任务

### Step 1: 数据模型与 schema 迁移
- `src/utils/workspace.py`：CURRENT_SCHEMA `v2.9 → v3.2`，加 `_DEFAULT_UPSTREAM_STATE`、`get_upstream_state`、`set_upstream_state`、`_extract_vars_from_wizard`
- 新增迁移函数 `_migrate_v2_9_to_v3_2`：老项目从 wizard_data 反向填充 candidate_vars，已有 research_q 设 phase=wizard 跳过漏斗
- VERSION_ORDER 加 v2.9，MIGRATIONS["v2.9"] = [_migrate_v2_9_to_v3_2]
- build_workspace_snapshot/restore_workspace 处理 upstream_state（含 stages 中的 ChatMessage 序列化）
- **测试** +5（test_workspace.py：v3.2 默认 state、反向填充、wizard_results_context 优先、round-trip、自愈）

### Step 2: ResearchTier 系统
- `src/upstream/tier.py`：ResearchTier enum (BEGINNER/ADVANCED/AUTO)、`detect_tier_from_input`（关键词+长度启发式）、`get_active_tier`、`set_active_tier`、`tier_at_least`
- 参考 v8 SystemTier 模式（不依赖、不导入）
- **测试** +12（enum、detect、读写、tier_at_least、字符串容错）

### Step 3: AI 苏格拉底引擎
- `src/paper_writer/ai_tutor.py`：TutorContext 加 `phase` + `funnel_stage`；`build_tutor_system_prompt` 加 phase 分支；新增 `FUNNEL_BASE_PROMPT`（严格输出规则+5 阶段范例）
- `src/upstream/socratic_engine.py`：`ask_socratic`（注入「学生上一轮说」+ 校验 + 重试 1 次降温 + fallback）、`_validate_socratic_output`（含?/≤150 字/句数≤2）、`_truncate_to_first_questions`
- `src/upstream/topic_funnel_kb.py`：`FALLBACK_QUESTIONS`（每阶段 ≥5 条）、`FUNNEL_FEW_SHOT`（5 个对子）、`get_fallback_question`
- **测试** +13（phase 切换、校验、截断、正常响应、长输出截断、非问句 fallback、HTTP 错误 fallback、注入历史、温度=0.3、fallback 覆盖 5 阶段）

### Step 4: 5 阶段状态机 + 可研究性检查
- `src/upstream/topic_funnel.py`：FunnelStage、STAGES、get_stage、stage 读写、`advance_stage`（强制 force_save）、`go_to_stage`、`restart_funnel`（默认保留历史）、`complete_funnel`（写 wizard_data + phase→wizard）、`recognize_constructs`（接 IntentRecognitionChain）、`set_candidate_vars`（AnalysisPlan schema）
- `src/upstream/feasibility_check.py`：`check_falsifiability`（仅记录，不打分）、`check_measurability`（接 construct_kb established_scales）
- v3.2 简化：可研究性 4 项 → 2 项（可证伪 + 可测量），可操作/有意义留 v3.3
- **测试** +19（stage 数据、advance、restart、complete、set_candidate_vars、recognize_constructs、可证伪 3 例、可测量 3 例）

### Step 5: UI 面板 + 路由
- `src/ui/upstream_panel.py`：`render_funnel`（5 阶段步进器+苏格拉底对话）、`render_advanced_skip_form`（ADVANCED 跳过表单）、tier 切换器、LLM 强制提示卡片
- `app.py`：undergrad_mode 分支加 phase 路由（funnel/wizard）+ tier 路由（BEGINNER/ADVANCED）；版本字符串 → "v3.2 · 选题漏斗+AI 苏格拉底"
- **测试** 通过 e2e 测试覆盖（schema 版本号更新）

### Step 6: wizard 集成
- `src/ui/undergrad_wizard.py`：path 选择初始化保留 funnel 已填字段（不再重置）；顶部加「🔄 回到选题漏斗」按钮（保留 stages 历史）
- 集成测试 +6（端到端 BEGINNER、ADVANCED schema 一致、老项目 phase=wizard、空白项目 phase=funnel、restart 保留历史、跨保存-加载完整恢复）

### Step 7: 范例库 + 回归
- `src/upstream/topic_funnel_kb.py`：6 大领域好/差选题对比填充（社会/临床/教育/发展/认知/组织行为）
- 每条含 `vague`/`bad_q`/`good_q`/`transformation`（5 阶段）/`why_better`
- 完整回归：449 → **517 passed**（+68 tests），0 warnings，0 failed

## 文件改动清单

### 新增（8 文件）
```
src/upstream/__init__.py
src/upstream/tier.py
src/upstream/socratic_engine.py
src/upstream/topic_funnel.py
src/upstream/feasibility_check.py
src/upstream/topic_funnel_kb.py
src/ui/upstream_panel.py
tests/test_upstream_tier.py
tests/test_upstream_socratic.py
tests/test_upstream_funnel.py
tests/test_upstream_feasibility.py
tests/test_upstream_integration.py
```

### 修改（5 文件）
```
src/paper_writer/ai_tutor.py        — TutorContext 加 phase/funnel_stage；build_tutor_system_prompt 加 phase 分支
src/utils/workspace.py              — CURRENT_SCHEMA v3.2；upstream_state 序列化；迁移；helpers
src/ui/undergrad_wizard.py          — 保留 funnel 已填字段；顶部「回到漏斗」按钮
app.py                              — phase 路由；版本字符串 v3.2
tests/test_workspace.py             — 旧版本断言更新；新增 5 个 v3.2 迁移测试
tests/test_e2e_rendering.py         — schema 断言 v2.9 → v3.2
```

## 关键复用资产（验证有效）

| 资产 | 位置 | 用途 |
|---|---|---|
| `IntentRecognitionChain.recognize()` | `src/questionnaire/intent_recognizer.py:380` | 阶段 3 变量识别（自动 keyword/TFIDF/LLM 三层） |
| `AnalysisPlan` schema | `src/parser/intent_resolver.py` | candidate_vars 数据结构（避免重造） |
| `chat_with_tutor()` | `src/paper_writer/ai_tutor.py:185` | 苏格拉底对话调用（mock 测试模式照常用） |
| workspace MIGRATIONS dict | `src/utils/workspace.py` | schema 迁移链 |
| autosave `force=True` | `src/utils/autosave.py:47` | 阶段切换绕过 30s 节流 |
| construct_kb established_scales | `src/questionnaire/construct_kb.py` | 阶段 4 可测量检查 |

## 推迟到 v3.3 的项

- 范例库扩到 18 条（每域 3 例）
- ADVANCED 完整折叠模式（5→2 阶段，目前直接跳过）
- 可研究性 4 项检查（目前只 2 项：可操作、有意义）
- **文献综述工作台**（独立模块，含 Crossref + 笔记 + 主题矩阵 + gap 识别）
- 多 tab 编辑锁
- 决策留痕系统（每个关键决策的理由+引用文献）

## 测试统计

| 文件 | 新增 tests | 关键覆盖 |
|---|---|---|
| test_workspace.py | +5 | v3.2 默认 state；wizard_data 反向填充；upstream round-trip；自愈 |
| test_upstream_tier.py | +12 | enum；启发式检测；session 读写；tier_at_least |
| test_upstream_socratic.py | +13 | phase 切换；校验；截断；fallback 链；mock LLM |
| test_upstream_funnel.py | +13 | stage 数据；advance/restart/complete；recognize；set_candidate_vars |
| test_upstream_feasibility.py | +6 | 可证伪 3 例；可测量 3 例 |
| test_upstream_integration.py | +6 | 端到端 BEGINNER；ADVANCED 等价；老项目；保留历史；保存-加载 |
| test_e2e_rendering.py | 修改 3 | schema 断言更新 |

**总计：+68 tests（449 → 517 passed），0 warnings，0 failed，3 skipped（kaleido）**

## 验证方式

1. `pytest tests/ -q` → 517 passed, 3 skipped, 0 failed, 0 warnings ✓
2. `run.bat` 启动 → http://localhost:8501
3. 新项目「测试漏斗」→ 本科论文模式 → 应进入漏斗 stage 1
4. 老项目（v3.1 创建）→ 升级 v3.2 → 直接进 wizard，不被漏斗拦
5. ADVANCED tier → 跳过表单 → 直接进 wizard
6. 漏斗中切换项目 → 数据完整恢复

## 反思

> 我之前在 v3.0 把"问题构建陪练"判为"边际价值低"——错了。下游是执行（规则清晰），上游是判断（没有标准答案）。AI 角色必须从「替你做」转为「逼你想清楚」，这是质变不是量变。
> 
> v3.2 第一次让本科生在**选题阶段**就被严肃对待——不是被 ChatGPT 给一个题目，而是被反问「你最不爽的现象是什么？」「如果你的假设错了会观察到什么？」。这种工具罕见。

## 下一步建议

- v3.3：文献综述工作台（最难、最有价值，差异化最大）
- v3.4：研究设计向导（接 questionnaire/experiment 模块）+ 预注册导出（OSF/中文开题报告）
- v3.5：项目生命周期反向追溯（下游分析结果可回写修订上游笔记）
