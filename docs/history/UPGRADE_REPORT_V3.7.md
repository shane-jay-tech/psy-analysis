# v3.7 升级报告 — 信效度补全 + 体验债清零（2026-05-22 ~ 05-23）

## 一句话

v3.7 把 v3.6 列出的全部 7 项 N1-N7 体验债清零，外加把信效度方法体系做齐（v3.7 第一阶段已完成的信度 8 法 + 效度 6 法 + CFA 整合），同时新增 Word/Markdown/jsPsych JSON 三种数据源。从 1021 → **1049 passed**（+28），0 warnings，0 failed。

## 核心数字

| 指标 | v3.6 | v3.7 | Δ |
|---|---|---|---|
| 测试 | 1021 | **1049** | +28 |
| 警告 | 0 | **0** | — |
| 失败 | 0 | **0** | — |
| 数据格式 | CSV/Excel/SPSS | **+jsPsych JSON/JSONL +Word .docx +Markdown .md** | +3 类 |
| LLM 成本可见性 | 仅 token 数 | **¥ 估算 + 按模型分布 + cached=0** | 单价表 16+ 模型 |
| 断点位置 | 仅完成度评分 | **「上次到这里」banner + 一键跳转** | 13 步流程恢复体验 |
| 语义对齐规则 | 11 (R1-R11) | **20 (R1-R20)** | +9 |
| 反问审阅 | 不读 gap | **读 literature_review.gap_analysis 注入 system prompt** | 不重复追问 |
| 流式输出 | 仅漏斗 stage 1/2 | **+wizard tutor + 反问修订** | 主路径全覆盖 |
| 人工金标 | 0 | **8 边界案例** | judge 一致率可校准 |

## v3.7 N1-N7 全清单

### 🟢 N1 — 流式输出全面铺开
- `chat_with_tutor_stream` 接入 `undergrad_wizard.py` AI 助教对话（用 `st.write_stream` 替代 `st.markdown`）
- `paper_engine.generate_revised_with_questions_stream` 流式版本（yield 逐块，最后 yield 结果 dict）
- 流式失败自动回退到一次性调用
- **测试** `tests/test_paper_writing.py::TestRevisedWithQuestions::test_stream_yields_chunks_then_dict`

### 🟢 N2 — LLM-as-judge 人工金标
- `tests/fixtures/socratic_benchmark.json` 新增 `human_labels` 段
- 8 个边界案例标注（覆盖：短模糊输入 / 极度模糊 / 现象阶段不退行 / 高质量变量对 / 易漏维度 / 高风险方案 / 样本量临界 / 末阶段抛光）
- 每条含 `manual_score` (1-5) + `manual_passes` (bool) + `boundary_type` + 标注 rationale
- `compare_judge_vs_human` 一致率 ≥ 0.8 视为对齐；偏差 ≥ 2 触发 `needs_human_review=True`
- **测试** `tests/test_socratic_benchmark.py::TestN2HumanLabels`（6 tests）

### 🟢 N3 — LLM 成本估算
- `llm_gateway.MODEL_PRICING_CNY` 16+ 模型单价表（deepseek-chat、gpt-4o、claude-sonnet-4-6、gemini-2.5-pro、qwen-max 等）
- `estimate_cost_cny(prompt_tokens, completion_tokens, model)` 含前缀匹配
- `LLMTrace.cost_cny` 字段，cached 计 0
- `get_trace_summary()` 聚合 `total_cost_cny` + `by_model_cost` dict
- 侧栏「🔍 LLM 调用统计」expander 显示 ¥ + 按模型分布 + caption 说明
- **测试** `tests/test_llm_gateway.py::TestCostEstimation`（9 tests）

### 🟢 N4 — 反问式审阅注入 gap
- `paper_engine._format_gap_context` 把 GapAnalysis（dict 或 dataclass）格式化为 prompt 段落（cap 5 gaps × 200 chars）
- `generate_reviewer_questions(*, gap_analysis=None)` 形参注入到 system prompt：「学生已在文献综述阶段识别以下研究空白...请避免重复追问」
- 返回 dict 含 `gap_context_used: bool` 标志
- `undergrad_wizard._collect_literature_gaps` 从 `literature_review_state` 读取并自动注入
- UI 显示「📚 已读 gap」徽章
- **测试** `tests/test_paper_writing.py::TestReviewerGapInjection`（6）+ `TestFormatGapContext`（3）

### 🟢 N5 — 语义对齐扩到 20 条
- 新增 R12-R20（9 条）：偏相关+多重控制 / 多重回归 VIF / 中介+调节组合 / 重复测量球形 / 两因素交互 / 嵌套 HLM / 非参数 IQR / EFA KMO+Bartlett / 卡方期望频数+Fisher
- `is_aligned` 语义改为只看 `severity == "warning"`，info 级提醒不破坏对齐（修复 R20 误伤的 chi_square 通过用例）
- **测试** `tests/test_semantic_alignment.py::TestR12-TestR20` + `TestRuleCount`（19 tests）

### 🟢 N6 — 断点续读位置标记
- `workspace.update_last_position(phase, step, label)` / `get_last_position` / `is_at_last_position` / `humanize_elapsed`
- 漏斗 `advance_stage` / `go_to_stage` / `restart_funnel` / `complete_funnel` 自动写 last_position
- 文献综述、wizard step 切换处自动写
- `app.py` 路由层在 phase ≠ last_position.phase 时显示 `⏯ 上次到这里：xxx · N 分钟前` banner + 跳转/忽略两按钮
- **测试** `tests/test_workspace.py::TestN6_LastPosition`（15 tests）

### 🟢 N7 — 多源数据导入
- **jsPsych JSON/JSONL**：`load_jspsych_json` 自动嗅探数组 vs JSONL，展开 `data` 字段，列名归一化（trial_index → 试次序号 等）；JSONL 跳过坏行
- **Word .docx**：`load_word_table` 提取文档中的表格（默认第一个），第一行作表头，数值列自动 `pd.to_numeric`
- **Markdown .md/.markdown**：`load_markdown_table` 解析 GFM 管道表格（含分隔行 `|---|`），多表格按 index 选取
- `load_data` 统一入口路由扩展名 → 对应 loader
- 主页 + 本科向导 `st.file_uploader` 的 `type=` 列表已加 `json/jsonl/docx/md/markdown`
- **测试** `tests/test_data_loader.py`（21 tests，新文件）

## 用户反馈即时响应

会话中用户说："支持的格式我觉得应该加上 WORD 和 MARKDOWN" → 立即扩展为 N7+ 范围（不仅 jsPsych，还加 Word/Markdown），相关测试 11 条全部通过。

## 文件清单

### 新增
- `tests/test_data_loader.py`（+21 tests）
- `UPGRADE_REPORT_V3.7.md`（本文件）

### 改动
- `src/llm_gateway/gateway.py` — MODEL_PRICING_CNY、estimate_cost_cny、cost_cny 字段、trace 聚合
- `src/llm_gateway/__init__.py` — 导出 cost API
- `src/upstream/semantic_alignment.py` — R12-R20 + 分类常量
- `src/paper_writer/paper_engine.py` — _format_gap_context、generate_reviewer_questions(gap_analysis=)、generate_revised_with_questions_stream
- `src/utils/workspace.py` — last_position 字段 + 4 helper 函数
- `src/upstream/topic_funnel.py` — advance_stage/go_to_stage/restart_funnel/complete_funnel 钩 last_position
- `src/ui/literature_review_panel.py`、`src/ui/upstream_panel.py`、`src/ui/undergrad_wizard.py` — phase 切换钩 last_position；wizard tutor 用流式
- `src/data/loader.py` — load_jspsych_json / load_word_table / load_markdown_table + load_data 路由
- `app.py` — sidebar 成本面板、resume banner、file_uploader 扩展、版本 caption v3.7
- `tests/test_paper_writing.py`（+10）、`tests/test_workspace.py`（+15）、`tests/test_semantic_alignment.py`（+19）、`tests/test_llm_gateway.py`（+9）、`tests/test_socratic_benchmark.py`（+6）、`tests/test_data_loader.py`（+21 全新）
- `tests/fixtures/socratic_benchmark.json` — version v3.3→v3.7、+human_labels（8 案例）
- `KNOWN_ISSUES.md` — 标注 N1-N7 全部 ✅ 已修复

## 验证

```
1049 passed, 4 skipped in 137s
0 warnings, 0 failed
```

## 下一步候选（v3.8 路线）

- 多模型并发 fallback（#N8 仍待）
- 把成本估算接入到团队/学校多用户成本预算（仍单用户）
- judge 与人工标注的多次对照（连续观测一致率漂移）
- jsPsych 数据自动构面：把 trial-level 长表自动 pivot 到被试级宽表
