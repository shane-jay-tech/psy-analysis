# v3.5 升级报告 — 巩固重构与质量提升（2026-05-18）

## 一句话

v3.5 不再横向扩展模块，而是偿还 v3.x 累积的架构债务（LLM 调用分散、session_state 命名空间散落、多 tab 无锁），同时把核心模块的交付质量推到产品级（降级透明、LLM-as-judge、完成度评分、矩阵 LLM 提取、跨 phase 反向修订、自审循环）。

## 核心数字

| 指标 | v3.4 | v3.5 | Δ |
|---|---|---|---|
| 测试 | 695 passed | **785 passed** | **+90** |
| 警告 | 0 | **0** | — |
| 失败 | 0 | **0** | — |
| 新增模块 | — | `llm_gateway` / `concurrency` / `workspace_state` / `socratic_benchmark` / `completeness` / `review_import` | +6 |
| Schema 版本 | v3.4 | v3.5 | — |

## 三阶段实现状态

### 阶段一：架构重构（最高优先级）✅

#### A1: 统一 LLM 调用网关 ✅
- **新模块** `src/llm_gateway/`（gateway.py + __init__.py，~270 行）
- API：`llm_chat()` / `llm_chat_async()` / `register_llm_backend()` / `cancel_request()` / `is_llm_available()` / `LLMUnavailableError` / `LLMResponse`
- 内部处理：模型解析、超时、重试、取消标志、降级异常
- 后端注册机制：默认后端委托 `chat_with_tutor`，可注册自定义后端
- **迁移调用点**：socratic_engine._safe_chat / feasibility_check.suggest_significance_reflection / themes._llm_identify_gaps / matrix._llm_extract_dimensions / socratic_benchmark.evaluate_with_judge
- 各模块降级逻辑保留（捕获 `LLMUnavailableError` 后切本地路径）
- **测试** `tests/test_llm_gateway.py` +12

#### A2: WorkspaceState 顶层 dataclass ✅
- **新模块** `src/utils/workspace_state.py`（~210 行）
- 6 个子状态：`FunnelState` / `LiteratureReviewState` / `WizardState` / `AnalysisState` / `AdvancedMeta` / `UIState`
- 顶层 `WorkspaceState` 提供 `to_dict` / `from_dict` / `from_legacy_session` / `sync_to_legacy_session`
- **不替换 session_state**——作为类型化视图，与底层 dict 字段双向同步
- workspace.py CURRENT_SCHEMA `v3.4 → v3.5`；新增 `_migrate_v3_3_to_v3_5` 占位（无字段变更）；VERSION_ORDER 加 v3.4
- build_workspace_snapshot 持久化 `workspace_state_v35` 字段；restore_workspace 自动重建
- 兼容路径：`get_workspace()` 优先读已存的 WorkspaceState，缺失时从 v3.4 散落字段自动重建
- **测试** `tests/test_workspace_state.py` +13

#### A3: 多 tab SessionLock ✅
- **新模块** `src/utils/concurrency.py`（~120 行）
- `SessionLock` 基于 `session_state["_lock_dict"]`：键=资源名，值=(holder_id, expire_at)
- API：`acquire(resource, holder_id, ttl=30)` / `release(...)` / `is_locked(resource, by_others)` / `get_holder(resource)`
- 上下文管理器 `with with_lock(resource): ...` 失败时返回 False（不抛）
- `ensure_tab_id()` 每个 tab 加载时生成持久 uuid4
- **测试** `tests/test_concurrency.py` +11（含过期 / 不同 holder / 续约 / 上下文退出释放）

### 阶段二：核心质量提升 ✅

#### B1: 文献综述降级路径全 UI 可见 ✅
- `LiteratureReviewState` 加 `last_search_method` / `last_cluster_method` / `last_gap_source` 三个字段
- `cluster_themes_with_meta` 返回 `{themes, method}`，UI 在主题 tab 顶部显示「🧠 KMeans / ⚠️ keyword_overlap / 📑 by_literature」
- Gap tab 显示「💡 LLM 深度分析 / ⚠️ 启发式检测可能遗漏」
- 搜索栏显示来源 source（crossref+s2 / chinese 等）
- 矩阵 cell 自动填充时返回 method（"llm" / "regex"），UI 显示总结

#### B2: LLM-as-judge 反问质量自动评估 ✅
- **新模块** `src/upstream/socratic_benchmark.py`（~250 行）
- `evaluate_with_judge(question, student_context, expected_dimensions)`：
  - 评分维度：启发性 1-5 + 跨阶段一致性 pass/fail + 触及核心维度 pass/fail
  - 连续 3 次取众数（启发性中位数 / 布尔字段多数票）
  - LLM 不可用 → 规则评估（字数/问号/启发词）
- `JudgeScore.total`（0-100）和 `grade`（优秀/合格/不足）
- `batch_evaluate_benchmark()` 对 30 案例 fixture 全跑
- `compare_judge_vs_human()` 与人工标注比对，consistency_rate < 80% → 标记需复核
- **测试** `tests/test_socratic_benchmark.py` +15

#### B3: 文献综述完成度评分 ✅
- **新模块** `src/literature_review/completeness.py`（~130 行）
- 6 项 × 20 分 = 100：文献量（≥15 满分）/ 高相关占比 / 笔记覆盖 / 矩阵填充 / Gap 存在 / 主题运行
- `CompletenessResult.grade`：优秀（≥80）/ 良好（≥60）/ 及格（≥40）/ 不足
- UI 顶部彩色徽章 + 子项展开详情
- 进入 wizard 前 < 60 分提示（不强制）
- **测试** `tests/test_completeness.py` +9

#### B4: 矩阵 LLM 提取 ✅
- `auto_fill_abstract_info(use_llm=True)`：调网关一次性传标题+摘要，要求 8 维度 JSON 输出
- `_safe_json_parse` 容错（去 markdown code block / 提取首尾 `{}`）
- 失败重试 1 次 → 正则兜底；返回 `{extracted, method}`
- UI 一键自动填充时显示 LLM/正则各处理多少篇

#### B5: 中文文献 + 文献→wizard 贯通 ✅（v3.4 漏的承接）
- `search_literature(include_chinese=True)` 同时调 `search_chinese_literature`
- 返回结构变更：`{items, method, sources, raw_count, deduped_count}`
- 兼容 `search_literature_legacy` 返回 List
- wizard step 7 加「来自文献综述工作台」专属区块：`reading_status="done"` + `relevance_score >= 0.4` 文献自动列出，复选框可勾选引用
- 持久化到 `wizard_data.lit_review_checked`
- **测试** `tests/test_literature_review_search.py::TestChineseSearchIntegration` +2

### 阶段三：体验闭环 ✅

#### C1: 跨 phase 反向修订 ✅
- 文献综述顶部新增「🔄 修订研究问题」按钮 + 二级确认对话框
- 两种模式：「微调现有」（回 stage 5）vs「重新选题」（回 stage 1）
- 设置 `_lr_pending_rescore` 标志位 → 漏斗修订完毕回到文献综述时自动触发
- `rescore_existing_items(items_dict, new_research_q, candidate_vars)` 重新打分所有已搜文献
- 显示成功提示：「📊 文献相关性已根据新研究问题重新计算」

#### C2: 自审循环（导出-批注-导回）✅
- **新模块** `src/literature_review/review_import.py`（~150 行）
- `export_for_review(items, notes, matrix)`：生成带 `[REVIEW:lit_id]` / `[REVIEW_NOTE:note_id]` / `[REVIEW_MATRIX:lit:dim]` 标记的 Markdown
- `import_review_comments(md_text)` 解析 `[COMMENT: ...]` 并按上下文关联
- `apply_review_comments_to_state(lr_state, parsed)` 写入 `LiteratureItem.review_comments` / `ReadingNote.review_comments`
- UI 导出 tab 加「🪞 自审循环」expander：下载 + 上传 + 自动应用
- 文献详情区显示「💬 自审批注」expander
- **测试** `tests/test_review_import.py` +9

#### C3: UI 单元测试补全 ✅
- **新文件** `tests/test_literature_review_ui.py` +18
- 覆盖：矩阵维度增删、笔记类型过滤、完成度阈值（优秀/良好/及格/不足）、UI 状态键管理、tab 切换状态保持、漏斗→文献综述转换可见性
- 注：仅测试纯逻辑函数（不渲染 streamlit），UI 渲染本身靠手动验证

### 阶段四：维护性 ✅

#### D1: 启动缓存
- `topic_funnel_kb.list_all_examples()` 用 `@st.cache_resource` 装饰
- 18 条范例只构建一次，rerun 复用
- 测试环境（无 streamlit 上下文）直接走原函数无缓存

#### D2: KNOWN_ISSUES 更新
- 9 项已修复标记 ✅
- 7 项未修复（按 🟡 中 / 🟢 低 排优先级）
- v3.6 计划列入：流式输出、关键词库 LLM 辅助、LLM 哲学一致性

## 文件改动清单

### 新增（13 文件）
```
src/llm_gateway/__init__.py
src/llm_gateway/gateway.py
src/utils/workspace_state.py
src/utils/concurrency.py
src/upstream/socratic_benchmark.py
src/literature_review/completeness.py
src/literature_review/review_import.py

tests/test_llm_gateway.py             (12)
tests/test_workspace_state.py         (13)
tests/test_concurrency.py             (11)
tests/test_socratic_benchmark.py      (15)
tests/test_completeness.py            (9)
tests/test_review_import.py           (9)
tests/test_literature_review_ui.py    (18)
```

### 修改（11 文件）
```
src/upstream/socratic_engine.py        — _safe_chat 走 LLM 网关
src/upstream/feasibility_check.py      — suggest_significance_reflection 走网关
src/literature_review/themes.py        — _llm_identify_gaps 走网关；新增 cluster_themes_with_meta
src/literature_review/search.py        — include_chinese=True；返回 dict 含 method/sources；新增 rescore_existing_items
src/literature_review/matrix.py        — auto_fill_abstract_info 加 use_llm；新增 _llm_extract_dimensions / _safe_json_parse
src/upstream/topic_funnel_kb.py        — list_all_examples 加 @st.cache_resource

src/ui/literature_review_panel.py      — 完成度徽章 + 修订入口 + 降级提示 + 自审循环 + LLM 矩阵填充
src/ui/undergrad_wizard.py             — wizard step 7 注入 lit_review_checked

src/utils/workspace.py                 — CURRENT_SCHEMA v3.5 + workspace_state_v35 持久化 + 迁移链
app.py                                 — 版本字符串 v3.5

KNOWN_ISSUES.md                        — 9 项已修复标记 + 7 项 v3.6 计划
```

## 测试覆盖统计

| 文件 | 增量 |
|---|---|
| test_llm_gateway.py | +12 |
| test_workspace_state.py | +13 |
| test_concurrency.py | +11 |
| test_socratic_benchmark.py | +15 |
| test_completeness.py | +9 |
| test_review_import.py | +9 |
| test_literature_review_ui.py | +18 |
| test_literature_review_search.py | +2（中文路径） |
| test_workspace.py / test_e2e_rendering.py | schema 断言更新 |
| **总计** | **+90**（695 → 785） |

## 架构债务偿还情况

| 债务 | v3.4 状态 | v3.5 状态 |
|---|---|---|
| LLM 调用分散 | 5+ 模块直接调 chat_with_tutor | ✅ 统一走 `llm_gateway.llm_chat` |
| session_state 命名空间散落 | ~60 个 key 散落 | ✅ `WorkspaceState` 6 分组类型化视图（兼容旧字段） |
| 多 tab 编辑无锁 | 🔴 高优先级未做 | ✅ `SessionLock` + `with_lock` 上下文 |
| 降级路径不可见 | UI 静默降级 | ✅ 顶部状态条 + cell 标注 |
| 反问质量评估靠人工 | 30 fixture 不动 | ✅ LLM-as-judge + 与人工对比 |
| 文献综述无完成度反馈 | 用户不知离"够用"多远 | ✅ 6 项 × 20 分实时评分 + UI 徽章 |
| 矩阵填充靠正则 | 表述变体漏检 | ✅ LLM 一次性提取 + 正则兜底 |

## 已知局限（v3.6 计划）

详见 `KNOWN_ISSUES.md`：

| 严重度 | 局限 | 计划版本 |
|---|---|---|
| 🟡 中 | 反问 latency 30-60s（未启用流式） | v3.6（启用 llm_chat_async + SSE） |
| 🟡 中 | 可操作关键词库手维护（VR/AR 漏检） | v3.6 LLM 辅助识别 |
| 🟡 中 | LLM 哲学一致性（漏斗反问 vs wizard 润色） | v3.6 改为「先你写一稿，AI 反问」 |
| 🟢 低 | 语义对齐覆盖（中介调节组合） | v3.6-v3.7 |
| 🟢 低 | 断点续读可视化 | v3.6 |
| 🟢 低 | 实验数据导入链路（jsPsych） | v3.6 |

## 部署验证清单

| # | 验证点 | 状态 |
|---|---|---|
| 1 | 启动 → 侧栏显示 v3.5 | ✅ |
| 2 | 漏斗 → 文献综述 → 完成度评分顶部显示 | ✅ |
| 3 | 文献综述搜索默认含中文（CNKI） | ✅ search_chinese_literature 已接入 |
| 4 | wizard step 7「📚 来自文献综述工作台」区块自动列出 done 文献 | ✅ |
| 5 | 修订研究问题 → 二级确认 → 漏斗 → 回综述自动 rescore | ✅ |
| 6 | 自审循环：导出 .md → 加 [COMMENT:...] → 上传导回 → 显示在文献详情 | ✅ |
| 7 | 主题聚类 tab 顶部显示「🧠 KMeans」/「⚠️ keyword_overlap」 | ✅ |
| 8 | Gap 分析 tab 显示「💡 LLM」/「⚠️ heuristic」 | ✅ |
| 9 | 矩阵一键填充：LLM/正则 各处理 N 篇 | ✅ |
| 10 | 多 tab 同时编辑笔记 → 后到的 tab 提示「另一标签页正在编辑」 | ✅ SessionLock |
| 11 | 关闭浏览器 → 重新打开 → workspace_state_v35 完整恢复 | ✅ |
| 12 | 老 v3.4 项目升 v3.5 → 自动迁移 + WorkspaceState 重建 | ✅ from_legacy_session |
| 13 | 全量测试 785 passed, 0 warnings, 0 failed | ✅ |

## 复用资产

| 资产 | 位置 | 用途 |
|---|---|---|
| `llm_gateway.llm_chat` | `src/llm_gateway/gateway.py` | 全局 LLM 入口 |
| `WorkspaceState.from_legacy_session` | `src/utils/workspace_state.py` | v3.4 旧 session 兼容 |
| `SessionLock + with_lock` | `src/utils/concurrency.py` | 多 tab 编辑保护 |
| `calculate_completeness` | `src/literature_review/completeness.py` | 文献综述质量度量 |
| `evaluate_with_judge` | `src/upstream/socratic_benchmark.py` | 反问质量自动评估 |
| `import_review_comments` | `src/literature_review/review_import.py` | 自审批注解析 |
| `search_chinese_literature` | `src/paper_writer/literature_crawler.py` | v3.4 已有，v3.5 接通 |

## 下一步建议（v3.6）

按 KNOWN_ISSUES 优先级：

1. **反问流式输出**（🟡）—— 启用 `llm_chat_async`，UI 改 SSE 流式渲染。前置工作 v3.5 已就绪
2. **LLM 哲学一致性**（🟡）—— wizard 第 7 步改为「先你写一稿，AI 反问」，统一漏斗与下游的产品哲学
3. **可操作关键词库 LLM 辅助**（🟡）—— LLM 兜底识别新型高门槛设计
4. **语义对齐 ~20 条**（🟢）—— 覆盖中介调节组合
5. **实验数据导入**（🟢）—— jsPsych JSON 直接导入
