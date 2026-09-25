# 分析字段血缘登记表 v1（信箱单 20260925-120653-3298）

- 取数班：`qoder-executor-20260925-1630-psy68`，2026-09-25 16:2x～16:5x（A 档／data 型）
- 本体件：`src/analysis/field_lineage.py`（`LINEAGE_VERSION = "psy-analysis/field-lineage/v1"`）
- 测试件：`tests/test_analysis_field_lineage.py`（64 例）
- **红线复点**：本档与本体件**不含任何统计数值结论**——登记的只有「字段 ← 原始文件／抽取步骤／清洗规则／版本」
  的**溯源映射**，α／ω／效应量／置信区间／p 值／样本量的数值一律不经此处（结构断言见测试
  `test_registry_carries_no_numeric_values`）。

---

## 一、为什么"字段名叫 provenance 不等于它是血缘"（否证任务书的一处前提）

任务书的假设是"分析字段已有某种来源记录，登记即可"。实测否证：

| # | 前提 | 实测 | 结论 |
|---|---|---|---|
| ① | 结果侧已有来源记录 | `src/analysis/result_card.py:120` 的 `card.provenance` 只有两项：`method_id` 与 `generated_by="AnalysisResultCard"` | 来源记录=**方法标签**，不含原始文件／抽取步骤／清洗规则／版本 |
| ② | 结果能回溯到用户上传的原件 | 全仓把"原件叫什么"落进结果侧的只有一处：`archive_analysis(file_name=...)` → `params.json`；它**只记文件名**，无内容哈希、无路径 | 名字可记，**内容不可比对**；`data.csv` 是脱敏后的副本（`redact_dataframe_for_storage`），与原件不逐字节等同 |
| ③ | `snapshot_id` 能定位原始数据 | `runner.py::_generate_snapshot_id` = `df` 行哈希前 12 位 + 参数哈希 + 秒级时间戳 | 它是**数据指纹**，不是**指针**：拿它找不到任何一个文件 |
| ④ | 结果体字段都有血缘 | AST 普查 `src/analysis/*.py` 的 dataclass 字段（去掉本模块自身）：**230 个**，登记表当前覆盖 **172**，余 **58 个登记不到** | 缺的是**契约面**（与同批 d598/c36e/7575 同一形状），不是判据太严 |

所以本单做的是**从零立登记表**，不是"整理既有"。

## 二、原始文件载体登记（`RAW_SOURCES`）

| id | 载体 | 定位符 | 随仓？ | 可回溯到一条原始记录？ |
|---|---|---|---|---|
| R1_archive_copy | 归档副本（脱敏后） | `archive/<ts>_<id>/data.csv` ＋ `params.json` | 否（gitignore） | 是 |
| R2_workspace_upload | 会话内上传件 | `workspace['meta']`／`workspace['file_name']` | 否 | 是 |
| R3_demo_fixture | 演示数据集 | `demo_projects/psychology_questionnaire_demo/data.csv` | **是** | 是（唯一跨机可复算面） |
| R4_items_file | 题目文件 | `items_loader.parse_items_file` 入参 | 是 | 是 |
| R5_registry | 仓内注册表／映射表 | `method_catalog.py`／`contracts.py` | 是 | **否**（不来自用户数据） |
| R6_runtime_only | 运行期派生物 | `charts_data`／`snapshot_id`／`created_at`／`provenance` | — | **否** |
| R7_plan_input | 分析计划 | 归档件 `params.json` 的 `params` 节 | 否 | 是（参数记录） |

⚠ R1／R2 都在 gitignore 域：**血缘登记不写它们**，探针全程只读。

## 三、清洗规则登记（`CLEANING_RULES`）

| id | 锚点 | 对字段做什么 | 改单元格取值 | 只报告 |
|---|---|---|---|---|
| C1_column_bucketing | `import_cleaning.py::classify_columns` | 决定列进题目桶／人口学桶 | 否 | 否 |
| C2_reverse_scoring | `import_cleaning.py::reverse_score` | 反向题翻尺 | **是** | 否 |
| C3_invalid_detection | `import_cleaning.py::detect_invalid_responses` | 标越界作答 | 否 | **是** |
| C4_dimension_scoring | `import_cleaning.py::compute_dimension_scores` | 题目→维度分（派生列） | **是** | 否 |
| C5_missing_handling | `data_quality.py::handle_missing` | 行级剔除（默认 listwise） | 否 | 否 |
| C6_quality_screening | `data_quality.py::data_quality_check` | 恒定列／零方差／缺失率／离群／正态 | 否 | **是** |
| C7_privacy_redaction | `guardrails.py::redact_dataframe_for_storage` | 删高敏感列、身份列哈希 | **是** | 否 |
| C0_none_declared | （无） | 不经清洗 | 否 | 是 |

C2／C4／C7 会改取值 ⇒ 凡下游字段（α、维度分、归档件）的血缘链**必须**含它们，
否则"回溯到原始记录"回去的不是同一份数。

## 四、字段族登记（26 条 spec，节选）

| spec | 字段族 | 抽取锚点 | 清洗链 | 载体 | 承载数值 | 可作结论 |
|---|---|---|---|---|---|---|
| S1 | 信度点值 α／ω／CR／ICC／κ | `reliability.py::cronbach_alpha` | C1→C2→C5 | R2 | 是 | 是 |
| S2 | 置信区间端点 | `effect_size_ci.py::fisher_z_ci` | C5 | R2 | 是 | 是 |
| S3 | p 值 | `ttest.py::independent_ttest` | C5 | R2 | 是 | 是 |
| S4 | 统计量／自由度 | 同上 | C5 | R2 | 是 | 是 |
| S5 | 效应量 | `effect_size_ci.py::fisher_z_ci` | C5 | R2 | 是 | 是 |
| S6 | 观测样本量与计数 | `data_quality.py::data_quality_check` | C5→C6 | R2 | 是 | 是 |
| S7 | 描述统计表 | `descriptive.py::descriptive_stats` | C5 | R2 | 是 | 是 |
| S8 | 题目／变量列 | `items_loader.py::parse_items_file` | C1→C4 | R4 | 否 | 是 |
| S9 | 方法标识 | `method_catalog.py::resolve_method_id` | C0 | R5 | 否 | 是 |
| S10 | 计划参数 | `intent_resolver.py::AnalysisPlan` | C0 | R7 | 否 | 是 |
| S11 | 版本标记 | `contracts.py::ANALYSIS_RESULT_SCHEMA` | C0 | R5 | 否 | 是 |
| S12 | 警告／错误面 | `runner.py::run_analysis` | C6 | R2 | 否 | 是 |
| S13 | 缺失值元数据 | `data_quality.py::handle_missing` | C5 | R2 | 是 | 是 |
| S14 | 假设判定面 | `assumptions.py::check_normality` | C5→C6 | R2 | 是 | 是 |
| S15 | 图表负载 | `runner.py::run_analysis` | C0 | **R6** | 否 | **否** |
| S16 | 快照 id | `runner.py::_generate_snapshot_id` | C0 | **R6** | 否 | **否** |
| S17 | 生成时间 | `result_card.py::__post_init__` | C0 | **R6** | 否 | **否** |
| S18 | 卡片 provenance | `result_card.py::build_card_from_output` | C0 | **R6** | 否 | **否** |
| S19 | 脱敏报告面 | `guardrails.py::redact_dataframe_for_storage` | C7 | R1 | 否 | 是 |
| S20 | 方法切换建议 | `assumption_router.py::check_route` | C5 | R2 | 否 | **否**（runner 自述"仅建议，不切换"） |
| S21 | 建议样本量 | `post_hoc_power.py::estimate_post_hoc` | C5 | R2 | 是 | **否** |
| S22 | 文献库记录 | `feed_store.py::ArticleRow` | C0 | R5 | 否 | 是 |
| S23 | 原件名定位符 | `archive_manager.py::archive_analysis` | C7 | R2 | 否 | 是 |
| S24 | 拟合指数／信息量 | `cfa.py::CFAResult` | C5 | R2 | 是 | 是 |
| S25 | 派生表与逐研究数组 | `regression.py::multiple_regression` | C5 | R2 | 是 | 是 |
| S26 | 模型与判定标记 | `sem.py::structural_equation_model` | C0 | R7 | 否 | 是 |

字段名 → spec 的判定顺序：**精确表 `EXACT_FIELD_SPEC`（165 键）→ `SUFFIX_RULES`（14 条）→ `PREFIX_RULES`（1 条）**；
三级都不中 ⇒ `spec_for()` 返回 `None`，即"登记不到"。**不兜一个通用规范**（兜了就等于假装可追溯）。

⚠ 已登记的语义碰撞（写进 S6 的 note）：`sample_size` 在 `TTestResult` 族里是**观测 N**（S6），
在 `RouteDecision`／`SchemaReport` 里是**建议样本量**（S21 语义）——同名不同血缘，
把 S21 当 S6 用就会出现"结论说 N 够，血缘指的是 power 建议"。

## 五、验收判据的实测读数（可复算）

探针：`D:\code\tmp\qoder-executor-20260925-1630-psy68\lineage_probe.py`（`$` 行见 result 的「证据」节）

1. **随机抽样可回溯**：`sample_fields(..., seed=68／2026／9)` 抽到的**承载数值且载体可回溯**字段，
   逐个用 `trace_project_dir()` 落到 `demo_projects/.../data.csv`（表头 14 列 × 30 行）的具体行 ⇒ 全部 `reached=True`。
2. **不可回溯者不判通过**：同一抽样里的 `canonical_method_id`（R5）／`charts_data`（R6）
   ⇒ `reached=False`，理由逐字为「登记的载体是 R5_registry／R6_runtime_only……不对应任何一条原始记录」。
3. **本地归档面（只读）**：`archive/` 现读 **17** 个 `params.json`，seed=68 抽到
   `20260815_005008_a215bab9a3add5cc`，`n_cases` 回溯链：
   结果字段 ← 归档目录 ← 原件名 `multi.csv`（登记列 7／原始行数 150）← 第 3 行，行键 `[抑郁得分, 焦虑得分, 组别, 题1..题4]`。
4. **阻断判据**：`conclusion_gate(["alpha","totally_unknown_field_xyz"])` ⇒ `blocked=True`；
   `conclusion_gate(["alpha","snapshot_id"])` ⇒ 同样 `blocked=True`（有登记但不得作结论也阻断）。

## 六、未闭合面（交主班／后续单）

0. **S22（文献库记录）是 26 条 spec 里唯一没有字段名指向它的一条**：
   它登记的是 feed 侧字段（`ArticleRow.provenance` 等），不在 `src/analysis` 的 dataclass 普查面内。
   留着是为了把「feed 属 gitignore 只读域、任何血缘登记都不写它」这条约束钉在代码里；
   接 feed 字段名映射时补，不在本单范围。
1. **58 个字段登记不到**（全清单见 `probe_final.log` 第 3 行）。按本登记表语义，它们**一律不得作为结论支撑字段**；
   其中 `tables`／`model_summary`／`fit_indices`／`accuracy`／`post_hoc` 属"报告里真会出现"的面，
   补登记需在下一批做（要读各处理器的产出面才能定锚点，30 分钟档做不动）。
2. **未接生产入口**：`conclusion_gate` 没有任何调用点，现网报告不会因为字段不可追溯而被拦下 ⇒
   与同批 d598／c36e／7575 同形，**本单只到契约面本体**，故判 `partial`。
   接线要挑闸口（导出前？渲染前？），属新单，且会碰到在册的导出面账本门禁（新增 `st.download_button`／导出面
   必须同批改账），本班**未新增任何入口**。
3. **原件级回溯不可能**：`file_name` 只存名字、无哈希无路径，且 `data.csv` 是脱敏副本 ⇒
   "从结果回溯到**用户那份原件的某一行**"在当前盘上做不到。要真闭合，需要归档时同记
   原件 sha256 ＋ 行列定位符——那是**写盘格式变更**（触 gitignore 域），必须走人工闸，不由执行手拍。
4. **归档件被读写打开过**（非本单引入）：`archive/` 只读探针未改任何文件（收工读数见 result）。

## 七、术语澄清

- 本仓**没有**「数据血缘服务／lineage store／ETL 调度」这类东西：`rg -i "lineage|血缘"` 在 `src/` 下
  除本单新建件外，只命中 `provenance`（文献库抓取来源标签，`feed_store.py::ArticleRow.provenance`）
  与论文导出侧的同名注释。本表的 R5／S22 与之相连但不混用：feed 的 `provenance` 记的是**文献条目**来源，
  本表记的是**分析字段**来源。
