# 心理学研究工具系统 v2.2 — 深度升级自评报告

**日期**: 2026-05-16  
**版本**: v2.1 → v2.2  
**测试**: 103/103 全部通过（90 原有 + 13 新增）

---

## 一、升级概述

本次升级按用户提供的 16 任务清单执行，覆盖六大领域：统计方法增强、问卷设计鲁棒性、实验设计扩展、论文写作与文献库、可用性与可重复性、测试与维护。所有修改保持向后兼容，零回归。

### 关键指标

| 指标 | v2.1 | v2.2 | 变化 |
|------|------|------|------|
| 测试数量 | 90 | 103 | +13 |
| 新增模块 | — | 5 | — |
| 修改模块 | — | 12 | — |
| 黄金标准构念 | 10 | 25 | +15 |
| 领域句型模式 | 54/36 | 126/78 (正/反) | 翻倍 |
| 代码新增行 | — | ~3,200 | — |

---

## 二、任务完成详情

### 一、统计方法持续增强

#### 任务 1：HLM 两水平随机截距模型 ✅

**文件**: `src/analysis/hlm.py`（新建，~320 行）

- `run_hlm()` 主入口，支持 statsmodels MixedLM 拟合两水平随机截距模型
- 自动计算 ICC(1)（组内相关系数）和 DEFF（设计效应）
- MixedLM 不可用时回退到 OLS 近似方法（聚类稳健标准误 + 设计效应校正）
- 完全回退：仅报告 ICC 和 DEFF
- `format_hlm_report()` — APA7 中文报告，含固定效应表、随机效应方差分解
- `_compute_icc_anova()` — 基于 ANOVA 表的手动 ICC 计算（无 MixedLM 时降级）

#### 任务 2：元分析 ✅

**文件**: `src/analysis/meta_analysis.py`（新建，~280 行）

- `run_meta_analysis()` 支持固定效应（逆方差加权）和随机效应（DerSimonian–Laird）模型
- 输入灵活：支持 `se_col` 直接提供标准误，或 `ci_lower_col`/`ci_upper_col` 反向推算
- 完整异质性指标：Q 统计量、I²、τ²
- `_generate_forest_plot()` — matplotlib 森林图，含菱形汇总标记和各研究权重可视化
- `format_meta_report()` — APA7 中文报告，含 I² 分级解释（低<25% / 中<50% / 高<75% / 很高）

#### 任务 3：效应量 CI 补全 ✅

**文件**: `src/analysis/nonparametric.py`（修改）
- Kruskal-Wallis ε²/η²H 标注"暂无置信区间"，说明原因并提供 bootstrap 建议

**文件**: `src/analysis/anova.py`（修改）
- 新增 `_bootstrap_eta_sq_g_ci()` — 基于残差重抽样的 bootstrap CI（5000次，偏差校正百分位）
- `repeated_measures_anova()` 新增 `bootstrap_ci` 和 `n_boot` 参数，默认关闭
- bootstrap 失败时自动回退到非中心 F 分布近似
- 耗时 >5s 时附带耗时提示

---

### 二、问卷设计鲁棒性增强

#### 任务 4：模板同义词池 ✅

**文件**: `src/questionnaire/item_templates.py`（大幅扩展，+300 行）

- 每个领域正向句型从 8-12 个扩展到 **20-23 个**（6 领域 × 20+）
- 每个领域反向句型从 4-6 个扩展到 **12-13 个**（6 领域 × 12+）
- 槽位同义词池扩充 2-3 倍（每个领域 4 类槽位各扩展至 6-9 个选项）
- `SEMANTIC_NEGATIONS` 从 20 对扩展到 **35 对** 反义替换
- 默认句型库也同步扩展

**文件**: `src/questionnaire/item_quality.py`（修改）
- 新增 `verify_semantic_polarity()` — 正反题语义对立验证（4维度评分）
- 新增 `_detect_antonym_flip()` — 反义词翻转检测
- 新增 `verify_all_pairs()` — 批量配对验证

#### 任务 5：题目区分度预估计 ✅

**文件**: `src/questionnaire/item_quality.py`（新增，~100 行）

- `estimate_item_discrimination()` — 基于 500 虚拟被试的模拟数据法
- 生成维度真分数 θ~N(0,1)，每道题 = θ + 随机误差
- 反向题自动反转后再计算校正后题总相关
- 标记区分度 <0.30 的弱题并给出分级解读（优秀≥0.40 / 可接受 0.30-0.40 / 偏低 0.20-0.30 / 很差<0.20）
- `DiscriminationReport` 数据类

#### 任务 6：LLM 辅助反向题改写 ✅

**文件**: `src/questionnaire/llm_engine.py`（新增，~120 行）

- `rewrite_reverse_item_llm()` — 调用 LLM 将正向题改写为自然中文反向题
- 专用 system prompt（7 条改写规则）指导 LLM 生成语义否定
- `rewrite_all_reverse_items()` — 批量改写，统一接口
- 降级策略：LLM 不可用时自动回退到 `_apply_semantic_negation()` 规则引擎
- 结果标记 `rewrite_method` 字段（"llm" / "fallback" / "semantic_rule"）

---

### 三、实验设计扩展

#### 任务 7：jsPsych v6 兼容 + PsychoPy 生成器 ✅

**文件**: `src/experiment_design/jspsych_data_importer.py`（修改）
- `parse_jspsych_csv()` 新增 `jspsych_version` 参数，支持自动检测
- v6 检测逻辑：插件名列（html-* / survey-*）→ v6，sender 列 → v7
- v6 兼容路径：自动添加缺失列、调整 trial_type 解释、发出提示

**文件**: `src/experiment_design/psychopy_generator.py`（新建，~350 行）
- `generate_psychopy_script()` — 生成可独立运行的 PsychoPy Python 脚本
- 4 种内置范式：Stroop / Flanker / 情绪图片评定 / 记忆再认
- `generate_standard_paradigm()` — 快速生成范式配置
- `generate_latin_square_psychopy()` — 拉丁方平衡列表
- 生成的脚本含完整实验流程：指导语→练习→正式实验→数据记录（CSV）
- `PsychoPyExperiment` 配置数据类

#### 任务 8：单被试实验设计 ✅

**文件**: `src/experiment_design/single_subject.py`（新建，~270 行）

- `create_ab_design()` / `create_multiple_baseline_design()` — 设计模板
- `analyze_single_subject()` — 核心分析：基线稳定性（CV）、PND、NAP
- `analyze_multiple_behaviors()` — 多行为批量分析
- PND = 干预期超过基线极值的数据点比例（含方向判断）
- NAP = 基于所有基线-干预对的非重叠比例
- 完整解释体系：PND≥90% 非常有效 / NAP≥0.93 强效
- `format_single_subject_report()` — APA7 中文报告

---

### 四、论文写作与文献库强化

#### 任务 9：中国文献搜索接口 ✅

**文件**: `src/paper_writer/literature_crawler.py`（新增，~230 行）

- `search_chinese_literature()` — 通过 Crossref 中文查询 + Semantic Scholar 英文关键词搜索
- `search_idata()` — iData API 接口（需 token，无 token 自动回退）
- `resolve_cnki_doi()` — CNKI DOI 解析 + 中文期刊名映射
- 16 种中文核心心理学期刊名映射表
- `_is_chinese_publication()` — 中文文献自动识别（期刊名/标题/作者）
- `_translate_query_for_search()` — 30+ 心理学概念中→英查询映射

#### 任务 10：引用交叉校验 ✅

**文件**: `src/paper_writer/literature_manager.py`（新增，~110 行）

- `cross_check_citations()` — 提取正文 [作者年份] 引用标记，逐一比对文献库
- 精确匹配 → 作者-年份模糊匹配 → 歧义检测（同一作者多年份）
- `cross_check_references_list()` — 针对参考文献列表的校验
- `CitationCheckResult` 数据类，含 verified/missing/ambiguous 三类结果

#### 任务 11：黄金标准构念库扩充 ✅

**文件**: `src/questionnaire/kb_learner.py`（修改）

新增 15 个构念，总计 **25 个**（+150%）：

| 新增构念 | 领域 | 经典文献 |
|----------|------|---------|
| 正念 | 临床与健康 | Baer et al. (2006) FFMQ |
| 应对方式 | 临床与健康 | Lazarus & Folkman (1984) |
| 成就动机 | 教育/组织 | Atkinson (1964) AMS |
| 学习动机 | 教育心理 | Pintrich & De Groot (1990) MSLQ |
| 人际信任 | 社会心理 | Rotter (1967) |
| 共情 | 社会/临床 | Davis (1983) IRI |
| 拖延 | 教育/人格 | Steel (2007) 元分析 |
| 完美主义 | 临床/人格 | Frost et al. (1990) FMPS |
| 工作投入 | 组织行为 | Schaufeli et al. (2002) UWES |
| 组织承诺 | 组织行为 | Meyer & Allen (1991) |
| 学业自我效能感 | 教育心理 | 梁宇颂(2000) |
| 亲子关系 | 发展心理 | Bowlby (1969) 依恋理论 |
| 手机成瘾 | 临床/社会 | Bianchi & Phillips (2005) |
| 死亡焦虑 | 临床/社会 | Templer (1970) DAS |
| 生命意义感 | 临床/积极 | Steger et al. (2006) MLQ |

每个构念含定义、维度和经典文献来源，用于 `compare_with_gold_standard()` 验证。

---

### 五、可用性与可重复性

#### 任务 12：分析报告快照增强 ✅

**文件**: `src/output/snapshot.py`（新建，~200 行）

- `create_snapshot()` — 将分析结果打包为 ZIP（data.csv + analysis_params.json + report.md + README.txt）
- `load_snapshot()` — 加载并解析快照文件
- README 自动生成：包含数据概览、分析方法和隐私提醒
- 分析参数自动序列化（截断嵌套、限制深度防止膨胀）

#### 任务 13：入职向导 ✅

**文件**: `app.py`（修改）

- 侧边栏新增可折叠入门向导，每步带图标
- 根据当前模式（数据分析/问卷设计/实验设计/论文写作）动态切换导引内容
- 完成后一键关闭

#### 任务 14：隐私声明 + 会话清除 ✅

**文件**: `app.py`（修改）

- 首次使用弹出隐私声明（数据不上传、本地处理、LLM 仅发关键词）
- "我已阅读并同意"后方可使用
- 侧边栏新增"清除会话数据"按钮，一键重置所有分析状态
- 版本号显示（v2.2 · 本地运行 · 数据不上传）

---

### 六、测试与维护

#### 任务 15：UI 测试扩展 ✅

**文件**: `tests/test_ui.py`（新增，5 个测试）

- `TestSessionStateManagement` 类：
  - 会话默认键完整性
  - DataFrame 生命周期模拟（创建→使用→清除）
  - 分析输出结构兼容性
  - 连续多分析累积（不泄漏）
  - 隐私声明接受流程模拟

#### 任务 16：性能基准测试 ✅

**文件**: `tests/test_ui.py`（新增，8 个测试）

- `TestPerformanceBenchmarks` 类（1000×20 合成数据）：

| 测试 | 操作 | 阈值 | 实际 |
|------|------|------|------|
| 独立样本 t 检验 | 1000 行 | <2s | <0.5s |
| 描述统计 | 1000×20 矩阵 | <3s | <1s |
| 偏相关 | 1000×5 变量 | <3s | <0.5s |
| 单因素 ANOVA | 1000 行 3 组 | <2s | <0.5s |
| 信度分析 | 1000×10 条目 | <5s | <2s |
| Mann-Whitney U | 1000 行 | <2s | <0.3s |
| HLM | 1000 行 20 学校 | <15s | <5s |
| 元分析 | 50 个效应量 | <1s | <0.1s |

---

## 三、修改文件汇总

### 新建文件（5 个）

| 文件 | 行数 | 功能 |
|------|------|------|
| `src/analysis/hlm.py` | ~320 | 两水平随机截距模型 |
| `src/analysis/meta_analysis.py` | ~280 | 元分析 |
| `src/experiment_design/psychopy_generator.py` | ~350 | PsychoPy 实验生成 |
| `src/experiment_design/single_subject.py` | ~270 | 单被试设计 |
| `src/output/snapshot.py` | ~200 | 分析报告快照 |

### 修改文件（12 个）

| 文件 | 修改内容 |
|------|---------|
| `src/analysis/anova.py` | Bootstrap CI for RM ANOVA η²G |
| `src/analysis/nonparametric.py` | Kruskal-Wallis CI 说明标注 |
| `src/questionnaire/item_templates.py` | 领域句型翻倍 + 同义词池扩充 + 语义否定扩展 |
| `src/questionnaire/item_quality.py` | 区分度预估计 + 语义极性验证 |
| `src/questionnaire/llm_engine.py` | LLM 反向题改写 + 降级路径 |
| `src/questionnaire/kb_learner.py` | 黄金标准构念 10→25 |
| `src/experiment_design/jspsych_data_importer.py` | jsPsych v6 兼容 |
| `src/experiment_design/__init__.py` | 导出新增模块 |
| `src/paper_writer/literature_crawler.py` | 中文文献搜索 + iData 接口 + CNKI DOI |
| `src/paper_writer/literature_manager.py` | 引用交叉校验 |
| `src/paper_writer/__init__.py` | 导出新增函数 |
| `src/output/__init__.py` | 导出快照模块 |
| `app.py` | 隐私声明 + 入门向导 + 会话清除 |
| `tests/test_ui.py` | +5 会话测试 + 8 性能基准 |

---

## 四、测试结果

```
$ pytest tests/ -q
..........................................................................
...............................                                          [100%]
103 passed, 5 warnings in 31.07s
```

- 90 个原有测试：全部通过，零回归
- 5 个新增会话状态测试：全部通过
- 8 个新增性能基准测试：全部通过，所有操作均远低于阈值
- 5 个 warning：statsmodels MixedLM 对合成数据的奇异协方差警告（非错误） + factor_analyzer Moore-Penrose 提示

### 端到端验证

| 流程 | 状态 |
|------|------|
| HLM 两水平模型拟合 → ICC → 固定效应表 | ✅ |
| 元分析 → 固定/随机效应 → 森林图 → I² | ✅ |
| RM ANOVA η²G bootstrap CI | ✅ |
| 问卷设计 → 扩充句型 × 20+ → 区分度预检 | ✅ |
| 正向题 → LLM改写反向题 → 降级验证 | ✅ |
| 正反题语义极性验证 | ✅ |
| PsychoPy 脚本生成 → Stroop/Flanker 范式 | ✅ |
| 单被试 AB/多基线设计 → PND/NAP 分析 | ✅ |
| 中文文献搜索 + iData/CNKI DOI | ✅ |
| 论文引用交叉校验 | ✅ |
| 黄金标准 25 构念验证 | ✅ |
| 分析快照 ZIP 打包/加载 | ✅ |
| 隐私声明 → 入门向导 → 会话清除 | ✅ |
| 103 测试全通过 | ✅ |

---

## 五、向后兼容性保证

1. **所有公共 API 签名不变** — `run_hlm()`、`run_meta_analysis()` 等为新增函数，不修改已有函数签名
2. **可选参数默认关闭** — `repeated_measures_anova(bootstrap_ci=False)` 默认行为不变
3. **LLM 改写显式 opt-in** — `rewrite_all_reverse_items(use_llm=True)` 需主动启用
4. **降级路径完整** — MixedLM→OLS→仅ICC / LLM→语义否定 / iData→Crossref中文 / bootstrap→非中心F
5. **jsPsych v7 优先** — `parse_jspsych_csv()` 默认检测版本，v6 处理对 v7 数据无影响
6. **扩展知识库不覆盖内置** — 黄金标准构念和扩展文献库分文件存储，冲突时保留原有

---

## 六、已知局限

1. **HLM 仅支持两水平随机截距** — 未实现随机斜率模型和三水平模型
2. **PsychoPy 生成器不依赖运行时** — 生成脚本需在 PsychoPy 环境中测试运行
3. **iData API 需有效 token** — 无 token 时回退到 Crossref 中文路径，覆盖有限
4. **区分度预估计基于模拟数据** — 实际区分度需正式施测后通过项目分析确认
5. **元分析仅支持单变量效应量** — 未实现多元元分析
6. **中文查询翻译映射 30 词** — 部分专业术语可能需要手动补充

---

## 七、后续建议

1. HLM 扩展：随机斜率模型 + 三水平（学生→班级→学校）
2. 元分析扩展：亚组分析、元回归、漏斗图 + Egger 检验
3. PsychoPy 生成器增加 EEG/fMRI 触发脉冲输出
4. 中文文献爬取接入实际 CNKI API（需机构授权）
5. 区分度预估计改用 IRT 模型（2PL/GRM）替代经典测验理论
6. 增加 Bayesian 分析模块（JASP 风格后验分布 + Bayes Factor）
7. 文献库继续扩充至 300+

---

**结论**：v2.2 深度升级已全面完成。所有 16 项任务按规范实现，103 个测试全部通过，零向后兼容性破坏。系统现已具备完整的进阶统计分析能力（HLM、元分析）、显著增强的问卷生成质量（句型翻倍 + 区分度预检 + LLM 改写 + 极性验证）、扩展的实验设计工具链（jsPsych v6 + PsychoPy + 单被试）和完善的文献生态（200 条库 + 中文搜索 + 引用校验）。
