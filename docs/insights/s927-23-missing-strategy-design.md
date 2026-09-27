# s927-23 设计稿：listwise 默认下 `missing_strategy` 的暴露形态（154310-2 案一）

- 单号：`s927-23` ／ 班名：`qoder-executor-20260927-2024-psy82` ／ 日期：2026-09-27
- 形状：**纯设计稿，零码改动**（本单只新增本文件，未触碰任何 `.py`／测试／`data/`）
- 判据映射：①暴露形态设计 → §3 §4；②默认值论证（维持 listwise）→ §6；③零码改动 → §0 末行 + §7（改动清单只登记、不执行）
- 案一原始口径（锚点 `zcode-bridge/done/20260925-154310-e00d.result.md:179-181`，原写 `outbox/`，已随 `--consume` 搬家）：
  「给 UI/plan 暴露 `missing_strategy` 选择并把 `missing_meta` 展示出来（`field_lineage.py:295` 已有 `S13_missing_meta` 血缘位），让用户看见"删了多少行"；**不改任何默认值**。」
  ⚠ 该句里同时含「暴露选择」与「不改默认值」两件事，本设计把它们拆开：**披露**（案 B，无风险）与**可选**（案 A，触数值面），选案留人工。

---

## 0. 现场复核（全部自跑，引前已复算；HEAD `3d6ca75`）

| # | 命令 | 读数 |
|---|---|---|
| 1 | `git grep -n missing_strategy HEAD` | 14 行：`src/analysis/field_lineage.py` 3、`src/analysis/runner.py` 4、`tests/test_analysis_result_schema.py` 1、docs 两档 6 |
| 2 | AST 数 `AnalysisPlan` 带注解字段（`intent_resolver.py:13-46`） | **29 个字段，`has missing_strategy = False`** |
| 3 | `grep -rn missing_strategy src/ui app.py` | **0 命中**（UI 无该选项，锚点这句仍成立） |
| 4 | `grep -rn missing_meta src/ui app.py src/output` | **0 命中**（引擎产出的元数据在展示面与交付面**一字未用**） |
| 5 | `src/analysis/runner.py:886` | `missing_strategy = getattr(plan, "missing_strategy", "listwise") or "listwise"` |
| 6 | `src/analysis/field_lineage.py:169` | `C5_missing_handling` 描述：「**按 plan.missing_strategy** 做行级剔除（默认 listwise）」 |
| 7 | `src/analysis/field_lineage.py:434` | `"missing_strategy": "S13_missing_meta"` |
| 8 | `grep -n "confidence" src/ui/undergrad_wizard.py` / `grep -n "plan.confidence_level\|confidence_level=" src/ui/undergrad_wizard.py` | 只有 `:2972` 滑条与 `:2983` 摘要文本；**第二条 grep rc=1（零命中）** ⇒ 向导"置信水平"控件从不写进 plan，是**同族第二枚空转件** |
| 9 | `src/utils/workspace.py:133-157 / :160-183` | plan 持久化白名单只 **13 键**（29 字段 ⇒ 16 枚 v3.7+ 专业字段恢复时静默丢）；Pipeline（`src/utils/pipeline_manager.py:22`）复用同一对函数 |
| 10 | `.venv/Scripts/python.exe -m pytest tests/test_analysis_field_lineage.py -q` | **64 passed in 1.63s**（S13／C5 锚点今天在世；改描述文案不触该门禁，见 §5.3） |
| 11 | `git status --porcelain \| wc -l` | 12 行（开工时读数；比派单横幅说的"约 15 行"少 3 行，主班已先行入库 3 枚 ⇒ 以盘为准） |

**缺陷的精确形状（四环，不是三环）**

```
声明环  AnalysisPlan 无 missing_strategy 字段（29 字段，实测无）      ← 空
执行环  runner.py:886 getattr(..., "listwise") ⇒ 恒取默认            ← 空转
披露环  missing_strategy / missing_meta 在 UI・交付面 0 命中          ← 用户看不见"删了多少行"
登记环  field_lineage.py:169 文案写成"按 plan.missing_strategy"      ← 血缘档指着一个不存在的字段
```

⚠ 对横幅初读的一处修正（写在下面以免后来者误判）：`field_lineage.py:434` 的**映射本身不空转**——`runner.py:901` 确实把 `missing_strategy` 写进了结果体，快照 `:1042-1043` 也落该键，所以"字段名 → S13"这条登记是有数据的。不诚实的只有 `:169` 那句里的 `plan.` 前缀（声明通道）与披露环。**别把"文案失实"当成"整条血缘登记作废"来改**，那是两处不同改动面。

---

## 1. 前置问题：要不要真的给 `AnalysisPlan` 加字段？（选案留人工）

这是本设计唯一必须先裁决的门。两案代价摆在一张表里，**推荐排布只是排序，不是放行**。

| 维度 | **案 B：不加字段**（披露-only） | **案 A：加字段**（真暴露选择） |
|---|---|---|
| 改动性质 | 语义诚实化 + 只读展示，**不动数据面** | **数据面改动**：plan 形状 +29→30，序列化面、写手面全要接 |
| runner | `:886` 的 getattr 换成模块级显式常量 `MISSING_STRATEGY_DEFAULT: MissingStrategy = "listwise"`（值不变，来源变诚实） | 保留 `:886` getattr（此时通道终于有写手），或改直读 `plan.missing_strategy` |
| 必须同步的写手面 | 0 处 | `intent_resolver.py:158/176/274`（靠默认值，可不改）、`src/ui/quick_entries.py:684`、`src/ui/undergrad_wizard.py:3021`（**该处 plan 由 `resolve_intent` 自然语言重建，控件值无处落地，必须新增显式赋值**）、`method_recommender.AnalysisRecipe.parameters`（recipe 预填面）、`workspace._serialize_plan/_deserialize_plan`（**不写进 13 键白名单 ⇒ 恢复工作区/Pipeline 复跑后静默回 listwise ⇒ 立刻再造一枚空转件**） |
| 缓存一致性 | 无新状态，天然无泄漏 | **免费收益**：`app.py:1113-1117` 缓存键 = `md5(f"{df内容哈希}\|{plan}")`，dataclass repr 覆盖全字段 ⇒ 加字段后换策略自动失效重算；反之若走 session_state 旁路而不进 plan，**必须手工把该值加进缓存键**，否则读到旧结果 |
| 统计口径风险 | 零（今天就是 listwise，明天还是） | **高**：4 枚枚举里只有 listwise 真落地（见 §6.1），放开选择＝把"估计量与有效样本 N 由用户改"的口子开到 UI，触本仓红线（统计数值结论＝人工闸） |
| 血缘档 | `:169` 文案改为指向常量与真实执行体；`:434` 映射保持不变即可 | 必须先解决 `:434` 的**同名撞位**（见 §5.2）：plan 侧与结果侧都叫 `missing_strategy`，而 `EXACT_FIELD_SPEC` 是 `字段名 → 单一 spec_id` 的一对一表，无法同时表达"S10 计划参数"与"S13 缺失元数据" |
| 回滚成本 | 低：一处常量 + 若干展示行，删掉即回到今天 | 中：字段进 plan 后 workspace/pipeline 落盘件里会多出键，旧件仍可读（`data.get` 白名单容错），但"已保存的工作区里带着用户选的非常量策略"这一状态需回归验证 |
| 对"案一"原文的贴合度 | 只做完"把 `missing_meta` 展示出来"这半，"暴露选择"半明确**不做并登记为出口** | 两半都做，但把 §6 的三枚假开关一并暴露在用户面前 |

**排序建议（非放行）**：先落 **案 B**（披露 + 文案失实修正 + §8 的反空转断言），把**案 A 作为需要统计口径评审的独立写单**另行排队；理由不是省事，而是案 A 的"写手面"若不同时接完 5 处（尤其 workspace 白名单与向导重建点），**案 A 落地后的产品形态恰好就是本案要修的那个缺陷**——一个看起来能配、其实恒默认的开关。仓内已有两枚前例（`runner.py:886`、`undergrad_wizard.py:2972`），不应再造第三枚。

---

## 2. 数据面口径（两案共用，先钉死语义）

`src/analysis/data_quality.py:21` 的枚举：`MissingStrategy = Literal["listwise", "pairwise", "mean_imputation", "drop_column"]`。今天各分支**实际做的事**（逐条给行号，别靠名字猜）：

| 枚举值 | 代码位置 | 实际效果 | 对 UI 暴露的含义 |
|---|---|---|---|
| `listwise` | `:62-79` | 对 `_collect_numeric_vars` 选出的列 `dropna`，产 `rows_removed` / `n_after`，>15% 追加"检查缺失机制/考虑 MI·FIML"文案 | 唯一**真改变进入统计的行集**且被完整披露的策略 |
| `pairwise` | `:80-86`（docstring `:38` 自陈"**仅标记策略**"） | 原样返回 df，不删行；下游处理器无人读 `missing_strategy`（全仓命中仅 runner 4 处，无 handler 读者） | **假开关**：选了它，行不删、各检验各自按库内部 NaN 规则处理，N 由谁决定用户看不到 |
| `mean_imputation` | `:87-102` | 用列均值填充，`imputed_cols` 记账；`description_zh`（`:100`）自陈"会低估标准误，仅建议缺失 <5% 时使用" | **改数值不改行集**，直接落进统计数值红线面 |
| `drop_column` | `:103-120` | 缺失率 > `drop_threshold`（默认 0.50，`:28`）的列整体删除 | 可能**静默删掉用户点名的因变量**，属结构性副作用 |

⇒ 设计约束：**UI 上任何"策略"控件，能选项的集合必须等于"实际落地度 = 真生效"的集合**。今天这个集合只有 `{listwise}`。这条约束是 §3 两案形态的分水岭。

---

## 3. 暴露形态设计（选项 / 默认值 / 说明文案）

### 3.1 案 B 形态（披露，不加选择器）——推荐先做

- **控件**：不放 `selectbox`／`radio`（放了就等于暗示可配）。用只读徽标 + caption，位置：`app.py:1168` 那个已经 `expanded=True` 的「📋 分析计划」expander 内，紧跟 `cols[0..3]` 四枚 metric 之后、`parsed_keywords` caption（`:1174-1175`）之前。
- **默认值显示**：写死"列表删除（listwise）"，并把它标成**系统口径**而非**用户选择**——措辞不得用"当前选择/可切换"。
- **文案原文**（单行 caption）：
  > `🧮 缺失值处理：列表删除（listwise）— 本系统当前唯一生效策略，不可在界面更改。本次删除 12 行（8.6%），有效样本 128 / 140。逐行删留见下方「缺失处理明细」。`
  > （数值由 `missing_meta` 读出，非本设计拟定；`—` 兜底见 §4.3。）
- **说明文案（展开区，解释"为什么没有开关"）**：
  > `为什么这里改不了？引擎目前只落地 listwise：pairwise 在代码里只打标记不删行（data_quality.py:80），mean_imputation 会低估标准误，drop_column 可能整列删掉你点名的变量。把它们做成可点的下拉框，只会让你以为选了、实际跑的还是 listwise。需要 MI／FIML 请先与指导教师／评审确认口径，本系统在"数据清洗向导"里提供行级／列级的显式处理。`
- **入口指引（避免"这里不能改＝无路可走"）**：在文案尾部保留一条指路到 `src/ui/cleaning_wizard.py`（该处已有 `:272` "删除含缺失的行"按钮与 `:290` 的"<5% 删行 / 5–15% 中位数填补"建议），并明确写出**分工差异**：清洗向导改的是**送进分析的那份 df**（用户亲手、有 before/after 形状账），本节披露的是**分析引擎自己做的删除**。不写清就会变成两处各说各话。
- **runner 侧配套（案 B 唯一代码语义改动）**：`:886` 改为显式常量，注释同步改掉"可从plan传入"这句失实描述（`:885`），并留一条 `TODO(s927-23 案 A)` 指针，防止后来人把常量当"漏接的 bug"顺手改回 getattr 而不接写手面。

### 3.2 案 A 形态（真选择器）——必须带三道闸

- **控件位置（两处，同键同源）**：
  1. `app.py:1168`「📋 分析计划」expander 内（主页面路径）；
  2. `src/ui/undergrad_wizard.py:2971`「⚙ 高级分析选项」expander 内，与"置信水平"并列——**注意该处的 plan 是在 `:3021` 由 `resolve_intent`（真名 `src/parser/intent_resolver.py:128 def resolve(df, request, col_info=None)`，UI 侧以别名导入）从自然语言重建的**，所以控件值必须在重建之后显式回写；或给 `resolve()` 加一个 `missing_strategy: MissingStrategy = "listwise"` 形参——**加形参的爆炸半径要一起算**：调用方含 `app.py:1052`、`undergrad_wizard.py:1938`（第二处重建点，连 `col_info` 都没传）与 `:3021`、`quick_entries.py` 等，改签名即跨文件改动面 ⇒ 设计**首选"重建后显式回写"**这条窄路。若只加控件不回写，正好复制"置信水平滑条"那枚空转件（§0 第 8 行实测）。
- **选项与默认值**：`selectbox("缺失值处理策略", ["listwise"], index=0)` 起步——**是，案 A 第一期也只给一个可选项**；其余三枚在用户显式知晓前不出现。给出后必须按下表分级：

  | 选项 | 默认可见 | 选它时的强制附加件 |
  |---|---|---|
  | `listwise` | ✅ 且为默认 | 无 |
  | `pairwise` | ❌ 需案 A 二期，且**前提是先把 pairwise 真接进下游处理器** | 逐检验 N 差异表（否则"不同分析基于不同样本量"只是文案） |
  | `mean_imputation` | ❌ | 高风险确认对话框 + 必填理由 + 结果卡打"插补后估计，标准误偏小"徽标 |
  | `drop_column` | ❌ | 删除前列清单预览；若命中 `plan.dependent_vars` ⇒ **禁止提交**，改为报错并让用户先改变量选择 |
- **持久化**：字段必须同时进 `workspace._serialize_plan/_deserialize_plan`（`src/utils/workspace.py:133-157/:160-183`）的白名单，并在 §8 的反空转断言里测往返；**不接白名单就等于没做案 A**。
- **缓存**：走 plan 字段即自动生效（`app.py:1113-1117` 的 `|{plan}` repr）；禁止用 session_state 旁路传策略。

---

## 4. `missing_meta` 的展示位设计

### 4.1 载体形状（实测 `data_quality.py:50-59` 九键 ＋ `:121-141` 追加的 `warnings` ⇒ **落地时共十键**）

`strategy`／`original_n`／`original_n_cols`／`n_after`／`rows_removed`／`cols_removed`／`removed_col_names`／`imputed_cols`／`description_zh`，**再追加** `warnings`（`:121-141`：listwise 且损失 >15% 时给"偏误警告"一条，`mean_imputation` 时给一条定性警告，其余分支置空列表）；出错兜底 `{"strategy": "none", "description_zh": "缺失值处理未执行（出错）。"}`（`runner.py:932`，**注意兜底件里没有 `warnings` 键** ⇒ 渲染必须逐键 `get` 兜底）。

### 4.2 三个展示位（各司其职，不做第四处）

| 位 | 锚点 | 渲染什么 | 为什么放这儿 |
|---|---|---|---|
| **P1 摘要位**（一行） | `app.py:1168-1177` 分析计划 expander | `description_zh` 之外只给 4 个数：`rows_removed`／`original_n`→`n_after`／占比／`strategy` | 与"检验方法・因变量・自变量・置信度"四枚 metric 同级——**样本缩减本就是分析计划的一部分**，这是本案的正面答案 |
| **P2 明细位**（折叠） | 紧随 P1，新 `st.expander("🧾 缺失处理明细", expanded=False)` | 九键全表（`st.dataframe`）；`cols_removed>0` 时列 `removed_col_names`；`imputed_cols` 在 listwise 下**显式渲染成空列表并注明"本次未做任何插补"** | 空列表要显示出来才有证明力："没插补"是结论而不是缺件 |
| **P3 交付位** | `src/output/snapshot.py:72-90`（`analysis_params.json` 由 `_extract_params` 全键转出，`missing_meta` 今天已会随 ZIP 落盘，只是没人渲染）与 `runner.py:1042-1043`（快照 JSON 已有两键） | README／报告里加一句策略与 N 变化；不改 JSON 形状 | 快照与 ZIP **已有数据面**，缺的只是人读得懂的句子 ⇒ 属文案层，零结构风险 |

- 结果卡（`src/ui/result_card_panel.py:40` `_render_card_content`）**不加第四处**：卡片是"效应量+APA 句式"面，重复披露 N 会与 `result.n` 打架；改为在 P1/P2 与卡片之间放一条**一致性提示**（见 4.4）。

### 4.3 兜底与三态

展示必须区分三态，缺态即说明缺失：
1. **正常**：`missing_meta` 有键 → 渲染 P1+P2；
2. **未执行**：`strategy == "none"`（`runner.py:932`）→ P1 直接显示"缺失值处理未执行（出错）"，并把该行升级为 `st.warning`，**不得静默显示 0**；
3. **件缺**（历史工作区／旧快照恢复来的 output 无该键）→ 显示"（旧结果，无缺失处理记录）"并禁用"重新出报告"之外的派生动作提示。
> 取数一律 `output.get("missing_meta") or {}` + `dict.get` 逐键兜底，禁止 `meta["rows_removed"]` 直取——旧件恢复路径上这枚键未必存在。

### 4.4 必须顺手消除的双账（本案最重要的"衔接"副作用）

`src/ui/undergrad_wizard.py:1787-1800` 现在**自己另算一套缺失数**：`df.isna().sum().sum()` 与 `total_missing / (df.shape[0]*df.shape[1])`，口径是**全列全格**；而引擎的删除只发生在 `_collect_numeric_vars` 选出的**数值列**上（`runner.py:927`）。⇒ 同一个数据集，向导说的百分比和引擎的 `rows_removed` **天然不等**，今天已经不等，只是没人并排显示。
⇒ 设计裁定：**P1/P2 上线时，向导 1787 段改为读 `missing_meta`（读不到才退回自算，并标注"估算，非引擎口径"）**；否则新展示位的出现会让两本账第一次被用户并排看见，比现状更可疑。这条属案 A/B 共同的前置整改，改动面仅文案与取数来源。

---

## 5. 与 `field_lineage` 的衔接

### 5.1 血缘档今天的读者只有测试（先说清，否则会设计出一个不存在的接口）

`field_lineage` 的运行时消费者实测为 **0**：`grep -rn "field_lineage\|EXACT_FIELD_SPEC" --include=*.py src app.py tests` 除模块自身外只命中 `tests/test_analysis_field_lineage.py`。所以"UI 与血缘的衔接"**不是接一条现成管道**，而是要在两条路里选一条：
- **L1（轻，推荐）**：血缘保持登记件身份不变，UI 只做**文本一致性**衔接——P2 明细区底部一行小字，用 `fl.spec_for("missing_strategy").chain()`（`field_lineage.py:610/:219-229` 已提供，输出五段人读链、不含任何数值）渲染"这一族字段的来源链"。**收益**：血缘档第一次有了真实读者，`:434` 那条登记从"只在测试里自洽"变成"用户看得见"；**约束**：`chain()` 结构是 5 段（`tests/test_analysis_field_lineage.py` 有 `len(spec.chain()) == 5` 断言），**不得为了 UI 好看去改 `_spec` 签名或段数**，那会撞测试判据（禁区）。
- **L2（重）**：把 S13 挂进 `conclusion_gate`／交付前闸口做门禁。**本案不建议**：门禁会改变导出行为，属另一条链的功能改动，应另开单。

### 5.2 案 A 必须解决的同名撞位（登记面的真缺陷）

`EXACT_FIELD_SPEC`（`field_lineage.py:359`）是 `字段名 → 单一 spec_id`。案 A 之后 `missing_strategy` 同时存在于两处语义：plan 上的**用户参数**（同族 `plan`/`confidence_level` 都归 `S10_plan_parameter`，`:426-433`）与结果/快照上的**执行回显**（现归 `S13_missing_meta`，`:434`）。一张表一个名字只能落一格 ⇒ 设计裁定：
- 结果侧继续 `missing_strategy → S13_missing_meta`（**不动 `:434`**，它承载统计数值，`value_bearing=True`）；
- plan 侧新增**别名登记** `plan_missing_strategy → S10_plan_parameter`（`SUFFIX_RULES`/`PREFIX_RULES` 也能承载，但同名字段靠前后缀区分比让一条映射两头飞更清楚），并在快照 `snapshot["plan"]`（今天只有 4 键，`runner.py:1049-1054`）里用该别名；
- ⚠ 案 B 不涉及撞位：**不要为案 B 引入这个别名**，那会给一张只有测试读者的表加一行无用登记。

### 5.3 描述文案的失实修正（两案都要，一处措辞）

`field_lineage.py:169`（`C5_missing_handling.reason_zh`）现文：
> 「按 plan.missing_strategy 做行级剔除（默认 listwise），决定进入统计的有效行集」

- 案 B 改为：「按 `src/analysis/runner.py::MISSING_STRATEGY_DEFAULT`（当前恒为 listwise）对数值分析变量做行级剔除，决定进入统计的有效行集」——把"plan 上有字段"这句假前提摘掉。
- 案 A 改为：「按 plan.missing_strategy（用户可选，默认 listwise）…」，此时原文反而变正确。
- **门禁安全性（实测）**：`tests/test_analysis_field_lineage.py` 的锚点校验只对 `extraction_anchor`（`路径::符号`）在文件文本里做词边界搜索（`ANCHOR_RE` `:27`，校验体 `:67-79`），`reason_zh` 不在校验面；`C5_missing_handling` 的 anchor 是 `src/analysis/data_quality.py::handle_missing`，本设计不改函数名 ⇒ 文案改动不触红。定向实测：`pytest tests/test_analysis_field_lineage.py -q` = **64 passed**。
- ⚠ 该文案里含 `MISSING_STRATEGY_DEFAULT` 字样时，务必确认测试没有把 `reason_zh` 当锚点解析（今天没有，`ANCHOR_RE` 只作用于 `extraction_anchor` 与 RAW_SOURCES/params 类锚点）；若有变化即红，属**门禁在保护真链路**，不要改判据。

---

## 6. 默认值论证：维持 `listwise`（判据②）

**"维持"的操作性定义**（免得论证滑成口号）：`runner.py:886` 求出的值、`output["missing_strategy"]`（`:901`）、快照两键（`:1042-1043`）、`tests/test_analysis_result_schema.py:40` 的 `"missing_strategy": "listwise"` 判据，四者今天都是 `"listwise"`，改动后仍全部为 `"listwise"`，且**判据一字不改**。

论据（全部指向仓内可复核的行号，不引入任何我方统计结论）：

1. **落地度**：四枚枚举里只有 listwise 完整实现"删除 + 记账 + 警告"三段（`data_quality.py:62-79` ＋ 记账 `:50-59` ＋ 警告 `:122-131`）；`pairwise` 分支被文件自己的 docstring 判为"仅标记策略"（`:38`、`:80-86`），`mean_imputation`/`drop_column` 各自改变数值或变量集合（`:87-102` / `:103-120`）。默认值一旦改到这三位，等于把默认口径交给**未落地或改变估计量的分支**。
2. **可披露性**：listwise 的代价（样本缩减）是**可完全量化披露**的——`original_n`/`n_after`/`rows_removed` 三个整数就够，用户一眼看到"N 变成了多少"。而 `mean_imputation` 的代价只有**一条定性警告文案**（`:132-140`，"低估标准误并扭曲变量间相关结构"），现有结果面上**没有任何量化位可披露其影响幅度**（`imputed_cols` 只列名不给幅度）⇒ 一个代价无法被核对的默认值不该被选中。
3. **红线归属**：改默认值 = 改变估计量族，属本仓/工作区纪律里的"统计口径变更"，**必须人工（统计评审）放行**，不由 UI/工程设计单顺带决定。本案形状是"只出设计"，故只登记、不动。
4. **锚点原文就是"不改"**：案一的定义末句即「不改任何默认值」（`done/20260925-154310-e00d.result.md:181`）。本案若改了默认值，就不再是案一。
5. **没有"顺手改也白改"的顾虑，但也没有理由**：本班当场复算 `git grep -in freeze -- '*.py'` = **0 行**（本仓确无 `--freeze`／基线重钉，与 `c7b8623` 提交名"并 definitive 否证本仓有 --freeze"同向）；磁盘上也没有落盘件带 `missing_strategy`（`grep -rl missing_strategy data` **rc=1（0 命中）**，`reports/` 目录今天**不存在**）⇒ 改默认值**不会**撞任何既有基线，因此这条不构成"不能改"的技术障碍；真正的障碍是第 1–4 条。**如实区分：不拦路的是技术，拦路的是口径与可披露性。**
6. **反向确认**：维持 listwise 不代表"UI 不该说清代价"。本案的披露设计（§4）正是把"隐式完全案例删除"从隐式变显式——这是案一"补证据面"的全部收益，零数值改动即可拿到。

⇒ 结论：**默认值维持 `listwise`**；任何非常量默认（含"把 pairwise 做成默认"）必须走统计口径人工闸，且以 §3.2 的三道闸与 §5.2 的别名登记为前置。

---

## 7. 落地改动清单（只登记，本单不执行；交主班放行）

### 案 B（推荐先做，最小改动面 5 处）

| # | 文件:行 | 改什么 | 面 |
|---|---|---|---|
| B1 | `src/analysis/runner.py:885-886` | getattr 换 `MISSING_STRATEGY_DEFAULT` 常量；注释"可从plan传入"改诚实 | 语义（值不变） |
| B2 | `src/analysis/data_quality.py`（模块级，紧邻 `:21` 枚举） | 定义 `MISSING_STRATEGY_DEFAULT: MissingStrategy = "listwise"` 供 runner 引用 | 新增常量 |
| B3 | `app.py:1168-1177` | P1 摘要 caption + P2 明细 expander（含 §4.3 三态兜底） | UI 展示 |
| B4 | `src/ui/undergrad_wizard.py:1787-1800` | 改读 `missing_meta`（取不到才回退自算并标"估算，非引擎口径"） | UI 取数 |
| B5 | `src/analysis/field_lineage.py:169` | `reason_zh` 措辞去 `plan.` 假前提 | 字符串 |
| B6（可选） | `src/output/snapshot.py` README / `src/analysis/runner.py::export_snapshot` | 交付文案补一句策略与 N 变化（不动 JSON 键形状） | 文案 |

回滚成本：逐条独立可 revert；B1/B2 是一对（要么同 revert 要么同留），其余互不依赖。

### 案 A（后续独立写单；缺任何一项即等于没做）

A1 `AnalysisPlan` +1 字段（默认 `"listwise"`，附 docstring 说明落地度）；A2 runner 接回 plan 值；A3 向导 `:3021` 重建后显式回写（首选窄路，见 §3.2）；A4 `quick_entries.py:684`／recipe 预填面；A5 `workspace.py:133-157/:160-183` 白名单 +1（**这是案 A 的生死线**）；A6 UI 选择器与三道闸（§3.2）；A7 血缘别名 `plan_missing_strategy → S10`（§5.2）；A8 §8 反空转断言；A9 缓存键验证（`app.py:1113-1117` 自动覆盖，写断言防回归）。

---

## 8. 反空转验收断言设计（新增测试建议；不改任何既有判据）

> 目的：本案的缺陷本质是"声明通道空转"，所以**任何一案的验收都必须包含一条"通道真被读"的断言**，否则改完只是把空转移了个位置。

- **案 B 断言**
  1. `run_analysis(df, plan)` 后 `output["missing_strategy"] == "listwise"` 且 `output["missing_meta"]["strategy"] == "listwise"`；
  2. `hasattr(plan, "missing_strategy") is False` 且 runner 源码不再出现 `"missing_strategy", "listwise"` 的 getattr 三元兜底（可用 AST／文本搜索断言，防止"常量+getattr 并存"的半吊子态）；
  3. UI 披露断言（若仓内已有 Streamlit 渲染层测试范式则挂同处）：文案里出现"当前唯一生效策略"字样 ⇒ 把"不给选择"变成**被测试保护的决策**，而不是被后人当 bug 修好。
- **案 A 断言**
  1. 通道真生效：夹具 `plan.missing_strategy = "drop_column"` + 一列缺失率 >50% ⇒ `output["missing_meta"]["cols_removed"] == 1`（**若声明通道仍空转，这条必红**）；
  2. 持久化往返：`_deserialize_plan(_serialize_plan(plan))` 后策略值不变（专治 §1 白名单静默丢）；
  3. 缓存不脏：同 df 不同策略 ⇒ `_cache_key` 不同（`app.py:1113-1117` 公式可在测试内复算）；
  4. 默认不漂移：未显式设置时恒 `listwise`，与 `tests/test_analysis_result_schema.py:40` 同向。
- **夹具与沙盒纪律**（本仓硬规则）：`data/` 被 `.gitignore` 覆盖 ⇒ 无还原点；上述断言一律用**自带内存夹具**（`pd.DataFrame` 造缺失），不读真库；若必须触路径面，注意 `paths` 是 import 期常量、`monkeypatch` 无效 ⇒ 用沙盒 env 并在测试里加"沙盒真生效"反证。

---

## 9. 遗留问题与出口

1. **`pairwise` 的真实现**是独立缺口（`data_quality.py:80` 只打标记）。在它接进下游处理器之前，UI 不得出现该选项——本设计把它登记为**案 A 二期前置**，不在本案范围。
2. **向导置信水平滑条空转**（§0 第 8 行实测）是本案的同族缺陷，形状完全相同（控件 → 不写进 plan → runner 取默认）。建议另开一单，判据可复用 §8 案 A 第 1、2 条。本单**未修改**它。
3. **16 枚 plan 字段不在持久化白名单**（29 vs 13）：本案只就 `missing_strategy` 发言，全量核对属独立审计。
4. **`field_lineage` 无运行时读者**：L1 衔接（§5.1）落地后它才有第一个读者；若人工不批 L1，血缘与数据面的"脱节"只修了文案环，登记环仍只在测试里自洽。
5. 判据③"零码改动"在本单的达成 = 本文件是唯一产物；§7 全部是**交人工放行的待办**，不是已发生改动。
