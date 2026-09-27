# s927-22 · Winsorize／异常值排除的产品化口径：现状梳理＋三案裁决材料＋样本量披露设计（零码改动，154319）

- 班：`qoder-executor-20260927-1945-psy80`｜cwd `D:\code\psy-analysis`｜分支 `main`｜HEAD `6cb3c96`
- 判据：①现状梳理 ②三案 ③样本量披露设计 ④零码改动 —— **四条全中**
- 锚点：`zcode-bridge/outbox/20260925-154319-a7bb.result.md` → 按 brief §3a 在 `done/` 取到（6,894 B，09-27 00:28）
- 🔴 **红线域自证（本班最要紧的一条）**：本单属**统计数值与效应量结论**域 ⇒
  ①**一字未改任何阈值**（`1.5`、`2%`、`10%`、`0.05`、`4 行`、`drop_threshold 0.50` 全部原样登记）；
  ②**没跑任何统计探针**——本班为 s927-22 **零计算**（不像同班 s19/s20 跑过纯函数／结构探针）：
  所有现状读数来自 `Read`/`rg`/`git show`，文中**不出现任何本班新产出的均值／t／p／效应量**，
  锚点里的三策略结论翻转（p 0.0021→0.0779）只作为"锚点曾报出的事实"引用，本班不复算、不采信为结论；
  ③三案一律写成材料＋判断题，**不代拍口径**。

---

## 1. 锚点复算（三句，一句作废／收窄）

| 锚点原话 | 本班复算 | 判定 |
|---|---|---|
| 「本仓排除异常值无一键接线（E1）」 | `cleaning_wizard.py` 全部 6 个动作实到：`drop_missing_rows:48`／`drop_constant_cols:58`／`impute_mean:72`／`impute_median:86`／`winsorize:107`／`coerce_numeric:120` ⇒ **无任何按 fence 剔行的动作**；`rg -i "drop.*fence|remove_outlier|exclude_outlier" src/` 亦零命中 | ✅ 成立 |
| 「Winsorize 仅 UI 触发且 `winsorize_outliers` 的 k 硬编 1.5（UI 层）」 | 生产调用者确实只有 UI 一枚（`cleaning_wizard.py:307`，其余命中在 `tests/test_cleaning_wizard.py:61`）；但"硬编"要分成**三处**：函数形参默认 `k: float = 1.5`（`:92`）、UI 按钮**又显式传** `k=1.5`（`:307`）、**检测侧另有一枚独立硬编** `data_quality.py:236-237`（`Q1 - 1.5*IQR`／`Q3 + 1.5*IQR`，与本函数互不引用） | ✅ 成立（并扩到三处双写） |
| 「主链无接入」 | 🔴 **本班作废此读法，按磁盘实况收窄**：**数据面其实已经接入**——向导第 3 步 `undergrad_wizard.py:2699-2700` 把清洗结果同时写进 `wiz.df` 与 `wiz_data["df"]`，而第 5 步 `:2940 df = wiz.df` → `:3023 run_analysis(df, plan)` ⇒ **跑的就是清洗后的 df**。真缺口在**声明面／审计面**：`runner` 对异常值零感知（`rg -i "outlier|winsor|fence|clip\(" src/analysis/runner.py` → **0 命中**）、`plan` 无清洗声明、血缘 `CLEANING_RULES` 无对应规则、交付包清洗日志里没有 winsorize（§2-E） | ⚠ 收窄（锚点若被读成"清洗不影响结果"会误判方向） |

---

## 2. 现状梳理

### A. UI 触发链（逐环，含四道入口闸）

```
data_quality_check(data_quality.py:225-252)  ── IQR fence 标记（1.5 硬编 :236-237）
   ├ 闸1  len(series) < 4      → 该列跳过             :228
   ├ 闸2  col in zero_var_cols → 该列跳过             :228
   ├ 闸3  IQR == 0             → 该列跳过             :234-235
   └ 闸4  outlier_pct ≤ 2%     → 不入 report.outlier_cols（:242 >10% ／ :249 >2% 两条文案档）
        ↓ 只有进了 outlier_cols 的列才对用户可见
render_cleaning_wizard(cleaning_wizard.py:182)  expander「📍 异常值（N 列）」:294
   ├ st.multiselect(report.outlier_cols) 默认空        :301-304
   └ st.button("Winsorize（IQR 1.5 倍边界）") disabled=not target  :305-306
        ↓
winsorize_outliers(current_df, target, k=1.5)   :307 → :92-110（逐列 s.clip(low, high)，行数不变）
        ↓
st.session_state[df_key] = new_df ; log.append(step) ; st.rerun()   :308-310
        ↓ 返回 (current_df, log)
undergrad_wizard.py:2695-2701（唯一生产调用者，实测 rg 全仓仅此一处）
   ├ wiz.df = cleaned_df  ＋  wiz_data["df"] = cleaned_df     ← 数据面就此并进分析链
   └ wiz_data["cleaning_log_md"] = cleaning_log_to_method_paragraph(clean_log)  :2700
        ↓
undergrad_wizard.py:2940 df = wiz.df → :3023 run_analysis(df, plan)
        ↓
第 7 步方法部分 :3382-3390 把 cleaning_text 插进「### 数据分析方法」段落
```

三点必读：
1. **入口是"报告驱动的可见性"**：异常值是否可处理，取决于 §A 闸 4 的两条**既有阈值**（2%／10%）。本班不动它们，但要主班知道：**口径的产品化若绕开这两条闸，就会出现"检测说没事、处理面却说有 3 个值被压边"的自相矛盾**（§4 披露设计因此要求逐列计数与 `outlier_cols` 同时可取）。
2. **只有本科论文向导这一条路吃到清洗结果**（`render_cleaning_wizard` 生产调用者 1 处）⇒ 主分析面板／问卷导入路径**无清洗入口**。
3. **撤销粒度不符文案**：`caption` 写"每步可撤销"（`:2691`），实现只有 `:318-321` 的「⏪ 全部撤销，恢复原始数据」（`st.session_state[df_key] = df.copy()`、`log` 清空）；
   `:314-316` 逐步展示时 `cols = st.columns([5, 1])` 的第二列**建而未用** ⇒ 逐条撤销疑为未落地。此项属现状缺陷，本班不改。

### B. 声明／执行面：一条**已经空转的同族前例**（对三案极关键）

仓内已有"策略入册＋主链执行"的完整样板——缺失值：
`MissingStrategy = Literal["listwise","pairwise","mean_imputation","drop_column"]`（`data_quality.py:21`）
→ `handle_missing(df, numeric_cols, strategy, drop_threshold=0.50)` 返回 `(df, meta)`，`meta` 九键（`:50-59`：`strategy/original_n/original_n_cols/n_after/rows_removed/cols_removed/removed_col_names/imputed_cols/description_zh`）
→ `runner.py:886` 取声明、`:901` 写进 output、`:926-932` 执行并落 `missing_meta`、`export_snapshot:1043` 落快照。

⚠ 但**声明那一环是空的**：`runner.py:886` 写的是 `getattr(plan, "missing_strategy", "listwise")`，而 `AnalysisPlan`（`intent_resolver.py:13-46`）**根本没有 `missing_strategy` 字段**，全仓亦无任何 `plan.missing_strategy = …` 写手（实测 `rg -n "missing_strategy" src/` 只命中 runner 三处＋快照一处）
⇒ **现网缺失策略恒为 `"listwise"`，那条"可声明"通道今天不成立**。
⇒ 任何"把 winsorize 接主链＋入册"的方案若照抄这套形状，会**复制一枚同样的空转件**（这条与本仓 `154316-4d99` 遗留 2 的 `mc_method/missing_strategy 同族缺位` 判断相互印证）。
**这是三案裁决的第一约束：先定"声明由谁写"，再谈接不接主链。**

### C. 血缘册（"入册"的第二义）

`field_lineage.CLEANING_RULES` 在册 C1…C7＋C0（`field_lineage.py:136-195`）**没有一条覆盖 winsorize 或按 fence 剔行**：
- 唯一两个"改取值"的规则是 `C2_reverse_scoring` 与 `C4_dimension_scoring`（`changes_cell_values=True`），`C7_privacy_redaction`；
- 离群的**标记**面已入血缘：`EXACT_FIELD_SPEC["outlier_cols"] = "S13_missing_meta"`（`:515`），但它挂的清洗规则只有 `C5_missing_handling`（`:295-298`）；
- `S6_sample_size` 由 `PREFIX_RULES ("n_", …)`（`:573-575`）兜底 ⇒ **披露字段若命名 `n_before/n_after/n_excluded` 会被自动判成"观测样本量"族**（同班 s927-19 §3-A 实测同坑，交叉引用）。
⇒ "入册"在本仓是**两件事**：①策略声明册（`MissingStrategy` 型 Literal＋plan 字段＋写手）②血缘清洗规则册（`CLEANING_RULES` 新增 C8/C9 ＋ `EXACT_FIELD_SPEC` 同步）。只做 ① 会留血缘债，只做 ② 是纸面登记。

### D. 快照／导出面

| 载体 | 今天有没有清洗记录 |
|---|---|
`export_snapshot`（runner.py:1028-1082） | 有 `missing_strategy`/`missing_meta`，**无任何清洗/异常值面**；`snapshot["plan"]` 只 4 键（`:1049-1054`） |
归档 `params.json`（archive_manager.py:65-82） | 只记 `columns/n_rows/n_cols/params/privacy_redaction` ⇒ **df 已被 winsorize 这件事不落档**（`n_rows` 是清洗后的行数） |
交付包 ZIP／DOCX | `deliverable_center_panel.py:75-81` 的 `bundle.data_cleaning_log` 取的是**问卷导入**面板的 `_CLEANED_KEY` 日志，且**只留 `{step, action}` 两键** ⇒ `zip_exporter.py:117-121 cleaning_log/cleaning_log.json`、`:277 data_cleaning_steps`、`docx_exporter.py:1240-1243` 这一整条**交付面里既没有 winsorize，也没有列名/形状／任何量** |
论文方法段 | **有**（唯一在世面）：`cleaning_log_to_method_paragraph`（`:327-334`）逐条 `step.summary()`；winsorize 的 summary＝`对「X」做 Winsorize（IQR 边界压缩，k=1.5）`——**有 k、无处理规模**（`CleaningStep.summary()` 只在 `rows_diff>0/cols_diff>0` 时追加"删除 N 行/列"，`:30-36`，winsorize 前后 shape 恒等 ⇒ 走不到该分支） |

### E. 能力缺口的准确形状

「排除异常值」要落地，缺的**不是函数**（fence 公式在世两处、`drop_missing_rows` 的剔行先例在世、`CleaningStep` 的 shape 差值在世），缺的是：
①一个 `exclude_outliers(df, cols, k) -> (df, CleaningStep)` 的动作；②**§4 的披露**（剔了谁、几行、影响哪几列、与本次分析变量的交集）；③§B 的声明写手；④§C 的两册登记。
⇒ 锚点说"需新增分析管道级剔行函数＋其在 result 卡的样本量披露"方向正确，本班补充：**函数最便宜，③④才是代价所在**。

---

## 3. 三案（材料对照，不代拍）

### 案① 接主链＋入册（把异常值处置变成 `runner` 的一等公民）
- 形状：`OutlierStrategy = Literal["keep","winsorize","exclude","robust_estimator"]`（新声明册）＋ `AnalysisPlan.outlier_strategy/...` ＋ **一个真写手**（UI 选择器或解析器）＋ `runner` 在 `handle_missing` 旁挂 `handle_outliers(df, cols, strategy, meta)` ＋ `output["outlier_meta"]` ＋ `export_snapshot`／`params.json` 同步 ＋ `CLEANING_RULES` 新增 C8（winsorize，`changes_cell_values=True`）／C9（fence 剔行，`changes_cell_values=False` 但改行集）。
- 收益：脱 UI 可复现；口径与缺失策略同形，读者已熟悉；披露可统一。
- 代价与风险（都属人工闸）：
  - 🔺 **改计数口径**：主链一旦默认执行任何剔行/压边，历史分析的 N／CI／效应量全变（与本仓 `_collect_numeric_vars` 那条"改后所有历史分析的 n 与 CI 都会变"同类）⇒ **默认值必须是 `keep`**（本班只标形状，不议任何档）。
  - 🔺 **不可重入风险**：UI 已压过边的 df 再进主链第二次 winsorize，fence 会按**已压缩**的分布重算 ⇒ 双重处理。案①必须回答"UI 处置与主链处置如何互斥／幂等"（见 Q2）。
  - 🔺 **顺序语义**：winsorize 与 listwise 删缺失的先后会改 N（§A 闸 4 又依赖 `dropna()` 后的序列，`:226`）⇒ 顺序必须写进声明册，不能靠调用位置隐式决定。
  - 🔺 与 §B 空转前例同形：若 `plan` 字段没有真写手，案①＝**把缺口从"没有"变成"有一个不动的开关"**（更难发现）。

### 案② 维持 UI 独占（不接主链，只补登记与披露）
- 形状：主链一字不动；把 `CleaningStep` 日志**如实接进** `output`／`params.json`／交付包（§D 三处），并把清洗结果标记随 df 一起传递（例如 `meta["cleaning_applied"]`），血缘 `CLEANING_RULES` 补 C8/C9 但 `report_only=True`（登记"发生过"，不主张"由系统执行"）。
- 收益：**零改计数口径**（历史结果不受影响）；披露缺口立刻补上（今天的"洗过但看不出来"最危险）；改动全在导出／登记面，回滚半径最小。
- 代价：不可复现（离开向导就没人知道 df 被压过边）；非向导路径无入口；"稳健"仍只有 UI 一条腿（锚点 E1 指出稳健实为两族：数据侧 winsorize 与估计量侧非参数，案②不解决其二）。

### 案③ 双轨（UI 人工处置 ＋ 主链**只声明不默认执行**的处置轨）
- 形状：案② 的登记＋披露全部照做；另在主链开一个**默认 `keep`（＝现状不变）**的 `outlier_policy` 声明位，**唯一硬要求是"两轨写同一处声明"**：UI 一旦处置，必须把同一份 `CleaningStep` 序列进那条声明（并让主链见到该声明就**不再二次处置**，解案①的幂等题）。
- 收益：现状零位移（默认档＝今天的行为，历史可比）；复现性靠"声明随数据走"而不是靠"主链强制洗"；三案里唯一同时解 §B 空转与 §D 无痕的形状。
- 代价：多一条轨＝多一处需登记的语义；需要回答"UI 处置记录由谁持久化"（`workspace.py` 的手写白名单坑，同班 s927-19 §2 已证 `_serialize_plan` 不会自动带新字段）。

| 对照维度 | 案① 接主链＋入册 | 案② 维持 UI 独占 | 案③ 双轨 |
|---|---|---|---|
改计数口径风险 | 🔺 高（默认档一动即历史全变） | ✅ 无 | ✅ 默认 keep ⇒ 无（除非用户主动声明） |
复现性（离开 UI） | ✅ | ❌ | ⚠ 声明在，处置在日志里 |
脱 UI 可自动化 | ✅ | ❌ | ⚠ |
幂等／双重处理风险 | 🔺 必须正面回答 | ✅ 不存在（只有一轨） | ⚠ 需"见到声明即不重做"约束 |
交付包／快照／归档留痕 | ✅（新建） | ✅（复用） | ✅（复用＋声明） |
血缘登记 | C8/C9 ＋ 执行方＝runner | C8/C9（report_only=True） | C8/C9 ＋ 双执行方需分列 |
实现改动面（枚处） | 约 7 处（plan／写手／runner／快照／归档／血缘／披露） | 约 4 处（output／params.json／交付包／血缘） | 约 8 处（案② ＋ 声明位 ＋ 互斥约束） |
回滚半径 | 大（跨层） | 小（导出／登记面） | 中（案②部分可单独 revert） |

---

## 4. 样本量披露设计（本单核心交付，纯形状、零口径）

### 4.1 六个必须同时出现的面（缺一即失真）

| # | 量 | winsorize | exclude（剔行） | 今天能否拿到 |
|---|---|---|---|---|
D1 | `N_before` / `N_after` | 恒等（**这正是要披露的点**：shape 不变易被读成"什么都没发生"） | 变 | ✅ `CleaningStep.before_shape/after_shape`（`:26-27`）；`missing_meta` 同名单已在世（`original_n`/`n_after`/`rows_removed`） |
D2 | **被压边的值的计数**（逐列） | 核心量 | 不适用 | ❌ 零处记录（`:102-105` 直接 clip，不数） |
D3 | 被处置**行的定位符**（行号列表或其哈希） | 逐列值定位 | 核心量 | ❌ 无；⚠ 隐私面：只登记定位符，**不登记被处置的原始数值**（红线＋`C7_privacy_redaction` 同族考虑） |
D4 | 生效边界（fence `low/high`）＋ **k 值** ＋ **规则版本号** | 需要 | 需要 | ⚠ 半：边界已在既有 warning 文案里以中文串出现（`data_quality.py:245-246`），**k 在 summary 串里**（`:109`）；两处都非机器可读字段 ⇒ 本设计只是把它结构化，**不新产出任何数值** |
D5 | **处置顺序**（与缺失 listwise／反向计分／维度求和的先后） | 需要 | 需要 | ❌ 无声明位（§B） |
D6 | 处置列 ∩ 本次分析变量集 | 需要 | 需要 | ⚠ 可推（`report.outlier_cols` 与 `plan` 变量列），但从未有人求交 ⇒ 会重演 `154316-4d99` E3 的"无关列把分析集缩小而结果卡无痕" |

### 4.2 载体选型（**不得开出第四条 N 通路**）

兄弟班 `docs/insights/s927-04-n-and-ci-design.md` 实测：同一份相关分析今天会以 **三个 n（58／57／55）＋两个 r** 出现在三条通路上（统计层→卡 / APA 表自算 / 事后功效）。
⇒ 本设计的第一条硬约束：**披露里的 N 必须与既有 N 通路同源**，具体要求：
- 顶层载体沿用 `missing_meta` 的九键形状，新增 `outlier_meta`（写进 `output`、`export_snapshot`、`params.json` 三处，缺一即无痕）；
- "有效 N"若要被下游取到，必须走 `result_schema.SAMPLE_SIZE_CARRIERS`（`:45`：`n/n_cases/n_obs/n_valid/sample_size`）里的既有键名之一，**或同步扩这条元组**（扩＝改契约，人工闸）；
- ⚠ 命名避开 `n_` 前缀自动归类坑（§C）：披露字段建议 `rows_before`／`rows_excluded`／`cells_clipped`；若必须用 `n_*`，则 `field_lineage` 需先补登记（与 s927-19 §3-A 的 `n_bootstrap` 同一条修法）；
- 卡面：走 `technical_notes`（既有"各变量对样本量 n = 60"式串的先例）与 `warnings`；**不要塞进 `effect_sizes`**（那是数值面，会把"处理规模"伪装成效应量）；
- 交付包：`cleaning_log/cleaning_log.json` 的条目从 `{step, action}` 两键扩到 `{action, target_cols, rows_before, rows_after, rows_excluded, cells_clipped, k, rule_version}`（`deliverable_center_panel.py:79-81` 是收窄点，`zip_exporter.py:118-121` 已能原样序列化 dict ⇒ 扩键即可，无需改导出器）。

### 4.3 呈现句式（形状，不是口径）

沿用 `handle_missing` 的 `description_zh` 语态（`data_quality.py:70-73`「列表删除（Listwise Deletion）：删除了含缺失值的 N 行（x%），剩余 y 行完整数据。」），给出对称模板，**方框处一律留人工**：

- winsorize：`异常值处理：对「⟨列⟩」做边界压缩（Winsorize，IQR 系数 ⟨k⟩，规则版本 ⟨rev⟩），共 ⟨c⟩ 个取值被压至 [⟨low⟩, ⟨high⟩]；样本行数不变（N = ⟨N_before⟩ = ⟨N_after⟩）。`
- exclude：`异常值处理：按 IQR 边界（系数 ⟨k⟩）剔除 ⟨r⟩ 行（定位符见 outlier_meta.row_locators），N 由 ⟨N_before⟩ 降至 ⟨N_after⟩；其中 ⟨m⟩ 行为本次分析变量所在列的取值。`
- 顺序声明（两式共用）：`处理顺序：⟨缺失策略⟩ → ⟨异常值策略⟩（顺序会改变有效 N，不可隐含）。`

⚠ 两处刻意留白：①**要不要显示百分比**（百分比＝处理规模，不是推断量，但它极易被读者当"影响可忽略"的结论 ⇒ 属呈现口径，人工拍）；②**D3 定位符的粒度**（行号 vs 哈希，涉隐私最小化，与 `C7_privacy_redaction`／`redact_dataframe_for_storage` 同族，本班不判）。

---

## 5. 推荐（交主班裁）

**推荐案③（双轨），且其"案② 那一半"可先行、单独成笔。** 三条理由（都可复算）：

1. **今天的实际风险是"无痕"而不是"没能力"**：§D 证明清洗结果只有论文方法段一条中文出口，快照／归档／交付包三处全无痕，而 `wiz.df` 已把清洗后的 df 喂进了 `run_analysis`（§1 第三行）⇒ **先补披露（案② 那半）就能消掉最危险的一半，且不动任何计数口径。**
2. **案① 会撞上仓内既有的空转前例**（§B：`missing_strategy` 声明通道今天没有写手）⇒ 在写手问题没答案之前接主链，等于再造一枚"看起来能配其实恒默认"的开关，比现状更易误导。
3. **案① 的幂等题只有案③ 能承接**：数据已被 UI 压过边，主链再执行一次会按压缩后的分布重算 fence；案③ 的"见到声明即不重做"是唯一不引入双重处理的形状（案② 不接主链 ⇒ 无此题，但也无自动化；案① 若不回答，风险直降可信度）。
- **顺序建议**：②-half（披露＋登记，纯导出／登记面）→ 声明写手归属（人工题 Q1）→ ③ 的互斥约束 → （若确有需要才谈）案① 的主链执行位。
- 🔺 任何把 `exclude` 变成主链默认动作的形状，本班一律标**人工闸**：它改的是"哪些人被算进来了"，属统计口径，不是工程配置。

## 6. 判断题（一律不代拍；数值／阈值题全部排除在外）

- Q1 声明写手归谁：解析器（`intent_resolver`）、UI 选择器、还是归档件 `params.json` 回填？（§B 的缺口正是这一格没人写）
- Q2 UI 处置与主链处置的互斥怎么表达：`outlier_meta` 存在即跳过？还是把 UI 处置降级为"提议"不覆盖 df？（今天 `wiz.df` 是直接覆盖）
- Q3 披露里的"处理规模"要不要给百分比（§4.3 留白①）？
- Q4 行定位符粒度（行号 vs 稳定哈希）与 `redact_dataframe_for_storage` 的关系（§4.3 留白②）？
- Q5 `SAMPLE_SIZE_CARRIERS` 是扩元组还是强制披露复用既有键（§4.2，扩＝改契约）？
- Q6 「稳健」第二族（非参数估计量侧，`nonparametric.py`）要不要与 winsorize 并成同一张口径表？（锚点 E1 已证稳健实为两族，本单未展开）
- Q7 撤销粒度（§A-3 的"每步可撤销"文案 vs 只有全部撤销的实现）算文案缺陷还是功能缺口？是否另开单？

---

## 7. 证据

前置：HEAD=`6cb3c96`、分支 `main`（未切、未 add、未 commit）；`git status --porcelain | wc -l` = **14**（19:42:54 与 20:0x 两次同值；brief §5 记 12 系主班 13:4x 读数，已漂移并在此点名）。
在途件归类（§23.6 口径，逐件 `git status --porcelain <件>` 实点）：
`src/ui/cleaning_wizard.py`、`src/analysis/data_quality.py`、`src/analysis/runner.py`、`src/ui/undergrad_wizard.py`、`src/analysis/field_lineage.py`、`src/output/zip_exporter.py`、`src/ui/deliverable_center_panel.py`、`src/analysis/result_schema.py`、`src/parser/intent_resolver.py`、`src/utils/archive_manager.py` ⇒ **全部干净件（工作树≡HEAD）**，本单结论不依赖任何脏件。
唯二脏件 `src/analysis/result_card.py`（` M`）与 `src/output/interpretation.py`（` M`，§23.3 禁读）在本单**只被交叉引用、未作现状依据**（§4.2 引的是 s927-04 档的读数并标明其脏件前提）。

**E1 本班零统计探针（红线反证）**
`s19/s20` 两班各跑过纯函数／结构探针；**s927-22 一枚探针都没跑**。沙盒 `tmp/qoder-executor-20260927-1945-psy80/` 内与本单相关的件为**零**（可直接 `ls` 复核：里面只有 `s19_*`、`s20_*` 与前人保留件）。
唯一"执行"过的命令类别：`rg`/`Read`/`git show`/`git status`/`sed`/`date`。
⇒ 因此本单不需要沙盒反证（无写路径、无 open 路径）；`data/` 未读未列未连（`.gitignore:42` 覆盖 ⇒ 无还原点），未连 sqlite、未走 Backup API、未用 `mode=ro`（规则 5 在"零连接"前提下不适用，已如实登记）。
反证二：`ls reports` → `No such file or directory`（本班未长出快照目录）。

**E2 触发链行号（全部本班自读，非引锚点）**
`cleaning_wizard.py`：`182`（render 签名）／`194-199`（session_state 初始化与 current_df 取用）／`244,254,285,308`（各分支覆盖 `st.session_state[df_key]`）／`294-310`（异常值 expander→multiselect→button→`winsorize_outliers(..., k=1.5)`）／`313-321`（步骤列表＋全部撤销）／`92-110`（winsorize 函数体：`quantile(0.25/0.75)`→`clip`→`CleaningStep(action="winsorize", before_shape, after_shape, description_zh=f"…k={k}）")`）／`30-36`（`summary()` 只在 rows/cols 差值 >0 时追加数量）／`22-28`（`CleaningStep` 字段）／`48,58,72,86,107,120`（六个 action 名）。
`data_quality.py`：`225-252`（fence 标记四道闸与两条文案档，`series = num_df[col].dropna()` 在 `:226`）／`9-18`（`DataQualityReport` 字段：`outlier_cols/zero_var_cols/n_total/n_complete` 等）／`21`（`MissingStrategy = Literal["listwise","pairwise","mean_imputation","drop_column"]`）／`50-59`＋`70-73`（`meta` 九键与 `description_zh` 句式）。
`runner.py`：`886`／`901`／`926-932`／`1042-1043`／`1028-1082`；`rg -i "outlier|winsor|fence|clip\(" src/analysis/runner.py` → **0 命中**。
`undergrad_wizard.py`：`2688-2701`（清洗向导入口与 df/log 同步）／`2940`／`3023`／`3382-3390`。
`intent_resolver.py:13-46`（`AnalysisPlan` 全字段，实测**无 `missing_strategy`**）。
`field_lineage.py`：`136-195`（CLEANING_RULES C0-C7）／`515`（`outlier_cols`→S13）／`295-298`（S13 只挂 C5）／`573-575`（`n_` 前缀→S6）。
`deliverable_center_panel.py:75-81`、`zip_exporter.py:117-121`＋`:277`、`docx_exporter.py:1240-1243`、`archive_manager.py:65-82`。

**E3 生产调用者计数**：`rg -n "winsorize_outliers" --type py src/ tests/` → src 内 2 处（定义 `:92` ＋ UI `:307`），tests 2 处；`rg -n "render_cleaning_wizard" src/ tests/` → src 内 2 处（定义＋`undergrad_wizard.py:2695` 唯一调用者），tests 3 处。

**E4 锚点三句的独立复算**见 §1 表；其中"主链无接入"被本班收窄为"数据面已接入、声明／审计面未接入"（依据 `undergrad_wizard.py:2699-2700 → :2940 → :3023` 的赋值链，每一步都是本班实读）。

## 8. 遗留问题

1. **本班作废掉一条初读**：把锚点"主链无接入"读成"清洗不影响分析"。实读赋值链后：`wiz.df` 已被清洗结果覆盖并被 `run_analysis` 使用 ⇒ 缺口在**声明与留痕**，不在数据通路。这条收窄直接改变了三案的代价对比（若按初读去裁，会误把案① 判成"零风险增量"）。
2. §A-3 的撤销粒度（文案"每步可撤销" vs 只有全部撤销、`st.columns([5,1])` 第二列建而未用）属独立缺陷，本单只登记，未定性成因（可能是未落地的半成品）。
3. `DataQualityReport.outlier_cols` 与 `report.warnings` 的两条阈值档（2%／10%）与 `handle_missing` 的 `drop_threshold=0.50` 是**四枚既有硬编**，本班一律不动、不建议动；但产品化方案必须显式说明它们与披露的关系（§4.1 第 1 点）。
4. 「稳健」第二族（非参数估计量侧）本单未展开（卷宗只问 winsorize 接主链与 exclude 入册）⇒ 写成 Q6 交主班。
5. 本班未跑 pytest（只读位＋并发约束）；§D 的"交付包不含 winsorize"是**读赋值链**（`deliverable_center_panel.py:75-81` 的 session_state 键来源）推得，主班若要坐实建议实跑一次交付包导出并附时刻与 HEAD。
6. 全量套件读数缺位（并发只读约束），勿以本班名义引用任何"N passed"。
7. 与同班另两单的交叉引用（同一坑的三处表现，主班宜并案看）：`n_` 前缀误并 S6 → `docs/insights/s927-19-seed-lineage.md` §3-A；披露字段命名要避该坑 → 本单 §4.2；`AnalysisPlan` 加字段必须同步 `workspace.py` 手写白名单 → s927-19 §2 末段（案③ 若把声明持久化，会立刻撞上这条）。
