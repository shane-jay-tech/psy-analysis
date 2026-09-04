# v3.9 升级报告：UI 接入 + 隐私守门 + 依赖锁

**版本**：v3.8 → v3.9
**日期**：2026-05-23
**任务规模**：6 个产品力增强（U1–U6），17 个新增测试
**测试基线**：1123 → 1140（+17），0 失败 / 4 skipped

---

## 一句话总结

v3.8 把 N8/O1/O2/O3 四块核心模块铺好但没接进 UI，v3.9 把这三块新功能在向导里点亮，
并补上「上传期 PII 检测」「依赖版本锁」两个产品守门员；学生现在打开向导能直接用，
不用知道模块名。

---

## 一、U1 — O2 答辩 Q&A UI 接入

### 改动
- `src/ui/undergrad_wizard.py::_render_defense_qa_section` 加 checkbox：
  「📝 个性化生成（读你的论文 + 反问历史 + 选题决策）」
- 新增 helper `_generate_paper_aware_with_context(plan, output, ctx, max_items)`：
  - 收集论文 = `wiz_data["method_text"]` + `wiz_data["result_text"]` +
    `_reviewer_student_text` + `_reviewer_revised`
  - 收集 reviewer 历史 = `_reviewer_questions` × `_reviewer_qa` 配对
  - 收集漏斗决策 = `get_upstream_state()` 五键提取
- 调用 `generate_paper_aware_qa`（v3.8 已有），失败回退模板版
- UI badge：`📝 已读论文 · 💬 已用反问历史 · 🎯 已用选题决策`，让学生看到考官读了什么

### 关键修复
`method_text` / `result_text` 之前是步骤 7 的局部变量；现在在 tab_combined 渲染时
持久化到 `wiz_data["method_text"]` / `wiz_data["result_text"]`，paper-aware QA 才能拿到。

---

## 二、U2 — O3 AI 痕迹检测 UI 接入

### 改动
- `_render_ai_trace_check_section(default_draft)` 新 helper：
  - 文本框默认填入 `method+result` 完整草稿，可粘贴/编辑/清空
  - 「🔍 开始自检」调 `detect_ai_traces`，结果存 `_ai_trace_report`
  - 评分着色：≥50 红（重度）/ ≥20 黄（中度）/ <20 绿（轻度）
  - 4 个 metric：总命中 / 必删 / 建议改 / 提醒
  - 必删项默认展开 + 命中文本/原因/建议建议；建议改/轻度提醒折叠
- 步骤 7 tab_combined 调用：`_render_ai_trace_check_section(default_draft=full_draft)`

### 用户体验
学生写完不知道自己「太 AI」，规则层零成本（不调 LLM）秒回结果。

---

## 三、U3 — N8 多模型 fallback UI 接入

### 改动
**侧边栏 LLM 配置**（app.py，主 LLM 配置块下方）：
- checkbox「启用备用模型」
- 提供商 + 模型 dropdown（与主模型独立可选）
- 同 provider 自动复用主 Key；异 provider 单独输入
- slider「主模型领跑时间（ms）」200–3000，默认 800
- 状态字段：`llm_fallback_enabled / provider / model / api_key / head_start_ms`

**Gateway 加 helper**（`src/llm_gateway/gateway.py`）：
- `_resolve_fallback_candidates()` 从 session_state 读配置；未启用/缺字段返回 None
- `chat_with_smart_fallback(messages, **)` 自动决定：
  - 无 fallback → 走 `llm_chat`（与之前完全一致，零成本）
  - 有 fallback → 走 `llm_chat_with_fallback` 主备并发
- `__init__.py` 导出 `chat_with_smart_fallback`

### 默认行为
关闭 fallback 时与 v3.8 完全一致；学生可在卡顿时一键打开。

---

## 四、U4 — N9 jsPsych 长→宽 auto-pivot

### 改动
**新核心函数**（`src/data/loader.py`）：
- `pivot_jspsych_to_wide(df, *, subject_col, condition_col, value_col, agg)`
- 自动嗅探变体：`subject` / `subj_id` / `participant`，`condition` / `trial_type`，
  `rt` / `反应时` / `反应时_ms` / `RT` / `response_time`
- 校准：单向子串匹配 + 别名 ≥3 字符（防止 `rt` 误匹配 `participant`）
- `agg`: `"mean"` / `"median"`
- 返回 `(wide_df, meta)`，meta 含 `n_subjects / n_conditions / pivoted_from`

**UI 集成**（`undergrad_wizard.py::_render_jspsych_pivot_panel`）：
- 仅在 `meta["source_type"] == "jspsych_json"` 显示
- 4 列 dropdown（被试/条件/数值/聚合）+「转为宽表」+「↩️ 回退到长表」
- 转换后保留长表副本（`wiz._jspsych_long_df`），可一键回退
- 转换后清掉 `analysis_output / plan` 强制重选分析

### 测试覆盖（8 tests, `tests/test_data_loader.py::TestPivotJspsychToWide`）
- 显式列 / 中文列 / subj_id 变体 / mean / median / 缺列 raise / 空 df raise / pivoted_from 标记

---

## 五、U5 — PII 列检测 + 依赖锁

### PII 检测
**`src/utils/guardrails.py::detect_pii_columns(df)`**：按风险三级：
- **high**（必删）：身份证 / 护照 / 手机号 / 电话 / email / 微信 / QQ / 家庭住址
- **medium**（哈希）：姓名 / 学号 / 工号 / 员工号
- **low**（提醒）：被试 / 学生 / 编号 / subject / participant / id

同列归到最高 severity（去重）。

**UI 集成**（`undergrad_wizard.py::_render_pii_warning`）：
- 步骤 2 数据上传后自动展示
- high → `st.error` 红色硬警告 + 列出列名
- medium → `st.warning` + **「🔐 一键脱敏（哈希这些列）」按钮**
- low → 折叠展开，提醒为虚拟编号

### 依赖锁
- `requirements.txt` 校准上界（pandas <4 / numpy <3 / openai <3 / plotly <7 等
  匹配 2026 验证可工作版本）
- 新增 `requirements-lock.txt` 用 `pip freeze` 锁死直接依赖（streamlit==1.57.0
  / pandas==3.0.3 / numpy==2.4.4 / openai==2.36.0 等 17 行）
- 顶部注释说明：requirements.txt 软约束（开发）/ requirements-lock.txt 精确锁
  （交付/CI）

### 测试覆盖（9 tests, `tests/test_guardrails_pii.py::TestDetectPIIColumns`）

---

## 六、U6 — 收口

- `app.py` v3.8 → v3.9
- `KNOWN_ISSUES.md` 标记 N9 ✅；剩余 N10/N11 推到 v4.0
- `UPGRADE_REPORT_V3.9.md`（本文）
- 全量回归：1140 passed / 4 skipped / 0 warnings

---

## 七、回归基线

```
1140 passed, 4 skipped in 116.19s
```

| 阶段 | 测试数 | 增量 |
|---|---|---|
| v3.8 基线 | 1123 | — |
| + U4 jsPsych pivot | 1131 | +8 |
| + U5 PII | 1140 | +9 |

**整 v3.9 升级 +17 tests**（U1/U2/U3 是 UI 集成，复用 v3.8 核心模块测试，
未新增单测；UI 行为靠手测）。

---

## 八、文件清单

### 新增
- `tests/test_guardrails_pii.py`（9 tests）
- `requirements-lock.txt`
- `UPGRADE_REPORT_V3.9.md`（本文）

### 修改
- `app.py` — v3.8 → v3.9 / 加 fallback 状态 5 字段 / 侧边栏 fallback UI 块
- `src/ui/undergrad_wizard.py` — 4 个新 helper：`_generate_paper_aware_with_context` /
  `_render_ai_trace_check_section` / `_render_jspsych_pivot_panel` / `_render_pii_warning`；
  step 2 加 PII + pivot 调用；step 7 加 trace + paper-aware checkbox；
  `method_text`/`result_text` 持久化
- `src/llm_gateway/gateway.py` — `_resolve_fallback_candidates` + `chat_with_smart_fallback`
- `src/llm_gateway/__init__.py` — 导出新 helper
- `src/data/loader.py` — `pivot_jspsych_to_wide`
- `src/utils/guardrails.py` — `detect_pii_columns` + `_PII_PATTERNS`
- `tests/test_data_loader.py` — `TestPivotJspsychToWide`（8 tests）
- `requirements.txt` — 校准上界
- `KNOWN_ISSUES.md` — N9 标记 ✅；新增 v3.9 已修复段

---

## 九、留给 v4.0 的事

| 严重度 | 局限 | 备注 |
|---|---|---|
| 🟢 低 | #N10 judge 漂移连续观测 | CI 跑 benchmark + 历史趋势 |
| 🟢 低 | #N11 团队版成本预算 | 实验室共享 key + 月度预算 |

下一波合理的方向是 v4.0 的「教师视角」：
- 老师批阅多份学生论文的批量入口
- 课程级仪表盘（哪些学生卡在第几步、批次质量分布）
- 答辩 Q&A 题库的结构化导出（让老师抽查）
