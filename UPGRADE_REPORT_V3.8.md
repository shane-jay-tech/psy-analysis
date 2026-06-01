# v3.8 升级报告：产品力打磨 — Fallback / 痕迹检测 / 个性化答辩 / E2E 测试

**版本**：v3.7 → v3.8
**日期**：2026-05-23
**任务规模**：4 个产品力增强（O1 / O2 / O3 / N8），74 个新增测试
**测试基线**：1049 → 1123（+74），0 失败 / 4 skipped

---

## 一句话总结

v3.7 把数据/写作/答辩三条线产品级铺完，v3.8 在三条线上各打一锤增强：
- **答辩**：从模板化变成「读你论文的考官」（O2）
- **写作**：交稿前自检 AI 八股，规则层零成本（O3）
- **数据/LLM**：deepseek 卡顿时另一家直接接上（N8）
- **质量**：完整黄金路径有了端到端回归（O1）

---

## 一、N8 — 多模型并发 fallback

### 痛点
v3.7 已有取消按钮 + cancel_id，但 deepseek 远程偶尔第一个 token 等 5-10s，体验依然有瑕。

### 方案
`src/llm_gateway/gateway.py::llm_chat_with_fallback`：把多个候选模型（不同家/不同 model）扔到 `ThreadPoolExecutor`，`FIRST_COMPLETED` 等谁先回包。

```python
result = llm_chat_with_fallback(
    messages,
    candidates=[
        {"model": "deepseek-chat", "llm_config": {...}, "backend": "deepseek"},
        {"model": "qwen-plus",     "llm_config": {...}, "backend": "qwen"},
    ],
    head_start_ms=300,  # 主模型领跑 300ms（避免无谓烧 token）
)
print(result.winner_model, result.total_elapsed_ms)
```

关键设计：
- **单候选自动降级到 `llm_chat`**（不引入并发开销）
- **`head_start_ms`**：主模型先跑一段时间，超时未回才启动备用 → 大部分情况只跑一家
- **自动 cancel 落败者**（用内部 cancel_ids，避免幽灵请求继续烧 token）
- **`FallbackResult` 留痕**：winner_model + attempts（每个候选的耗时/error）+ total_elapsed_ms

### 测试覆盖（8 tests）
- `TestN8FallbackBasic`：单候选退化、双候选都成功取最快的
- `TestN8FallbackFailover`：主挂掉 → 备用接上、所有挂掉返回失败
- `TestN8FallbackHeadStart`：主先回不启动备、主超时启动备
- `TestN8FallbackTrace`：attempts 完整 / 落败者标记 cancelled

---

## 二、O3 — 中文学术写作 AI 痕迹检测

### 痛点
学生用 deepseek/gpt 一通生成后，论文里全是「首先...其次...综上所述...具有重要意义...值得深入探讨...未来研究可以进一步...」一眼可见的 AI 烙印，老师反感。

### 方案
`src/output/ai_trace_detector.py` 规则层（零 LLM 成本）：

15 条 PATTERNS 覆盖 5 大类：
1. **开场八股**：首先/其次/最后 + 然而句首滥用 + 不仅...而且并列连用
2. **总结套话**：综上所述/总而言之/由此可见/不难看出/本文得出以下结论
3. **AI 高频空话**：值得深入探讨 / 具有重要意义 / 为...提供参考 / 日新月异 / ...必要性
4. **模板化结构**：本研究表明 / 研究结果显示 / 未来研究可以进一步
5. **翻译腔**：作出贡献（'contribute to' 直译）

每条规则：`(label, severity, pattern, why, suggestion)`

```python
report = detect_ai_traces(paper_text)
# report.score ∈ [0, 100]，越高越像 AI
# report.has_high_severity → 是否有「必删」级命中
# report.hits 每条带 line_no / matched_text / suggestion
```

评分：`weighted_sum / max(total_chars/1000, 1.0) * 10`，high=5/med=2/low=0.5。
经验阈值：≤20 轻度，20-50 中度，≥50 重度。

行号定位的关键坑：用 `(?<=[\n。！？])` 而不是 `(?:^|[\n。！？])`，因为后者会让 `m.start()` 指向 `\n`，行号反而错到上一行。`\s*` 也得改成 `[ \t　]*` 避免吃换行。

### 测试覆盖（25 tests）
- `TestBasicDetection`：空文本/干净文本/AI 文本/长文本归一化（每千字加权）
- `TestPatternCoverage`：15 条规则各覆盖一个测试
- `TestLineContext`：行号正确、按位置排序
- `TestCustomization`：severity_filter、extra_patterns
- `TestRewriteSuggestion`：单句替换建议
- `TestRealisticParagraph`：完整 AI 段评分 ≥ 50；学生手写段 < 20

---

## 三、O2 — 答辩 Q&A 个性化生成

### 痛点
v3.7 的 `generate_defense_qa` 是基于检验类型的模板（cronbach 配 6 题、t 检验配 6 题...）。所有 N=120 t 检验的学生看到的题都一样，没有读过他的论文，没结合他的反问历史。

### 方案
`src/paper_writer/defense_qa.py::generate_paper_aware_qa`：把学生论文 + reviewer 反问历史 + 漏斗决策都注入 system prompt，LLM 返回个性化 JSON 数组。

输入侧上下文格式化：
- `_format_paper_context(text)`：论文 ≤2500 字，超长居中截断 + 「中间内容省略」标记
- `_format_reviewer_history(history)`：cap 8 条 Q&A，每条问/答 ≤200 字
- `_format_funnel_decisions(funnel)`：从 funnel_state 提取 research_question / variables / design / sample_size / hypothesis 五个键

输出侧：
- LLM 返回严格 JSON 数组：`[{question, answer_outline, category, difficulty, rationale}]`
- 解析容错：直接 JSON、```json``` 包裹、混杂文本中提取数组三种都接得住
- `_build_paper_aware_item` 校验 question/answer_outline 必填，category 非法回落 method，difficulty 非法回落 常问
- `rationale` 拼到 answer 末尾的「为什么问这题：...」段（学生看到题目就知道考官在盯什么）
- 难度排序：必问 > 常问 > 刁钻

降级策略：LLM 调用失败 / 返回非法 JSON → `fallback_to_template=True` 调老版 `generate_defense_qa`，永远有内容。

`PaperAwareQAResult` 标记每个上下文来源是否实际用到（used_paper / used_reviewer_history / used_funnel），UI 可以显示「读了你论文 / 用了反问历史」徽章。

### 测试覆盖（27 tests）
- `TestPaperContext`：短/长/空文本格式化
- `TestReviewerHistory`：空/dict/cap 8/截断长 Q&A
- `TestFunnelDecisions`：空/全键/部分键
- `TestParseResponse`：纯 JSON / 代码块 / 混杂文本 / 非法
- `TestBuildItem`：缺字段/非法 category/非法 difficulty
- `TestGeneratePaperAwareQA`：happy path / LLM 失败回退 / 解析失败回退 / max_items / 排序

---

## 四、O1 — 黄金路径端到端测试

### 痛点
单元测试覆盖 1049 个点，但**业务链组装 bug** 单测看不到：load_data 的 metadata 用什么 key？run_analysis 对 cronbach 读 dependent_vars 还是 scale_items？jsPsych loader 给 rt 列改成什么名？这些只有真跑一遍才知道。

### 方案
`tests/test_golden_path_e2e.py` 真实模块串完整业务链（不依赖 streamlit server，LLM 全 mock 可 CI 离线）：

**路径 1（信效度路径）— 焦虑量表 N=120 5 题**
1. CSV 写盘 → `load_data` 嗅探编码 → `meta["source_type"] == "csv"`
2. 描述统计：`descriptive_stats` 返回 5 行（每题一行），列含 M/SD
3. `run_analysis(plan=cronbach_alpha, dependent_vars=[sa1..sa5])` → α 计算
4. `generate_defense_qa(plan, out, ctx)` → 至少含 method 类
5. `build_thesis_docx(meta, method_md, result_md, descriptive_table=...)` → bytes ≥ 1KB

**路径 2（实验路径）— jsPsych 反应时 30 被试 × 2 条件**
1. JSON 数组写盘 → `load_data` 识别 jspsych_json，列名归一（rt → 反应时_ms）
2. 长→宽 pivot：`groupby(["subject","condition"])["rt"].mean().unstack()`
3. `run_analysis(paired_ttest, dependent_vars=["congruent","incongruent"])` → 配对 t
4. `generate_defense_qa` 对 paired_ttest 不崩

**路径 3（写作 + 反问路径）— 问卷相关 N=80**
1. `run_analysis(pearson_corr, dependent_vars=["焦虑","抑郁","学业满意"])`
2. 学生手写结果段
3. `detect_ai_traces` 检测：手写段 score < 30
4. `generate_defense_qa` + `render_qa_as_markdown`
5. `build_thesis_docx(defense_qa_md=...)` ≥ 2KB

**跨路径 v3.8 集成**：fallback 拿 AI 草稿 → trace 检测（≥30）→ paper_aware QA mock LLM → 完整链不崩。

修了 4 个集成 bug：
- `cronbach_alpha` 用 `dependent_vars` 不是 `scale_items`
- 相关分析 test_type 是 `pearson_corr` 不是 `correlation`
- `descriptive_stats` 列是 `M / SD`（中文 + 单字母）不是 `Mean / 均值`
- jsPsych loader 把 `rt` 改成 `反应时_ms`

这些 bug 单测看不见 —— 各模块自己测自己用对了 key，但模块之间的契约靠人脑记。

### 测试覆盖（14 tests）
- `TestGoldenPath1_AnxietyScale`（5）
- `TestGoldenPath2_RTExperiment`（3）
- `TestGoldenPath3_QuestionnaireWritingAndReview`（5）
- `TestV38Integration`（1）

---

## 五、回归基线

```
1123 passed, 4 skipped in 125.34s
```

| 阶段 | 测试数 | 增量 |
|---|---|---|
| v3.7 验收 | 1049 | — |
| + N8 fallback | 1057 | +8 |
| + O3 trace | 1082 | +25 |
| + O2 paper-aware | 1109 | +27 |
| + O1 e2e | 1123 | +14 |

0 warning（v3.7 已清零，v3.8 维持）。

---

## 六、文件清单

### 新增
- `src/output/ai_trace_detector.py`（O3，~330 LOC）
- `tests/test_ai_trace_detector.py`（25 tests）
- `tests/test_defense_qa_paper_aware.py`（27 tests）
- `tests/test_golden_path_e2e.py`（14 tests）
- `UPGRADE_REPORT_V3.8.md`（本文）

### 修改
- `src/llm_gateway/gateway.py` — 加 `FallbackResult` + `llm_chat_with_fallback`
- `src/llm_gateway/__init__.py` — 导出
- `src/paper_writer/defense_qa.py` — 加 `generate_paper_aware_qa` 等 7 个新函数 / 数据类
- `tests/test_llm_gateway.py` — 加 N8 4 个测试类
- `app.py` — 顶部 docstring v3.1 → v3.8
- `KNOWN_ISSUES.md` — N8 标记 ✅；新增 v3.8 已修复段；剩余 N9-N11 推到 v3.9

---

## 七、留给 v3.9 的事

| 严重度 | 局限 | 备注 |
|---|---|---|
| 🟢 低 | #N9 jsPsych 长→宽 auto-pivot | O1 e2e 已示范代码，提到 loader 后置层 |
| 🟢 低 | #N10 judge 漂移连续观测 | CI 跑 benchmark + 历史趋势 |
| 🟢 低 | #N11 团队版成本预算 | 实验室共享 key + 月度预算 |

UI 接入 v3.8 三个新功能（answer_aware QA / trace report 显示位 / fallback 模型 dropdown）也是 v3.9 范畴 —— 当前 v3.8 是把模块和测试层扎好，UI 集成下个版本再做。
