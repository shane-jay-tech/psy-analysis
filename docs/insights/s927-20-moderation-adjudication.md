# s927-20 · `_build_moderation` 恒落 else：字段缺失清单＋适配器缺口＋三案裁决材料（零码改动，154316-2）

- 班：`qoder-executor-20260927-1945-psy80`｜cwd `D:\code\psy-analysis`｜分支 `main`｜HEAD `6cb3c96`
- 判据：①缺口清单 ②三案＋依赖顺序 ③推荐 ④零码改动 —— **四条全中**
- 锚点：`zcode-bridge/outbox/20260925-154316-735d.result.md` → 按 brief §3a 在 `done/` 取到（9,642 B，mtime 09-27 00:25）⇒ 路径搬家，非锚点失效
- 🔴 红线自证：本班**不产生任何效应量／显著性结论**，不改任何阈值（仓内既有两处 `p<0.05` 硬阈一字未议，见 G9）；
  探针跑出的数值只用于回答**结构可得性**（"这个键在不在""这条线画不画得出"），一律标为演示量。零被跟踪文件改动。

---

## 1. 锚点复算

| 锚点原话 | 本班自跑读数（同夹具、同解释器） | 判定 |
|---|---|---|
| `_build_moderation` 因 `AdvancedResult` 无 `interaction_b/interaction_p/r2_change` 而恒落 else | `hasattr` 六键全 `False`（含别名 `interaction_coef/delta_r2/f_change`）；卡面 `apa_text=""`、`warnings=["调节效应分析结果缺少交互项统计量"]`、`effect_sizes=[]`、`plain_language_summary=""` | ✅ 成立（本班独立复算） |
| `generate_simple_slopes_figure` 需要的 `(intercept,slope)` dict **无任何生产适配器** | 成立：`rg '"simple_slopes":'` 全仓 0 处写入、`x_range` 0 处生产赋值 | ✅ 成立 |
| 「（截断，接线面在档）」——锚点被截断处 | 本班补齐：见 §2 G3～G6（卡丢表、`method` vs `method_id` 词表不通、分发器有 moderation 分支但取不到料、正文面守卫恒假） | ✅ 补齐 |
| （隐含）分发器 `generate_figures_from_card` 没有 moderation 分支 | 🔴 **本班作废此初读**：`apa_figures.py:681` 明确有 `elif method == "moderation":` 分支。本班第一版 grep 用 `^\s+(el)?if method in (` 漏掉了 `==` 写法 ⇒ 判为"无分支"是**读法缺陷**，不是事实 | ❌ 初读作废 |
| 锚点未预见：**在册契约测试用 mock 把缺陷遮住了** | `tests/test_result_card_runner_contract.py:71-74` 的 `MockModerationResult` 恰好定义了那三个键 ⇒ `test_moderation`（:184-193）断言 `"调节" in card.apa_text` 在 mock 上恒真 | 🆕 本班新增（G8） |

---

## 2. 缺口清单（G1～G10，全部带在世证据）

### G1 数据面：卡要的四组键在产物里不存在
`_build_moderation`（`src/analysis/result_card.py:547-579`）读：
`interaction_b` ∥ `interaction_coef`、`interaction_p`、`r2_change` ∥ `delta_r2`、`f_change`。
`AdvancedResult`（`src/analysis/advanced.py:9-20`）实有 10 个字段：`test_type/model_summary/coef_table/effect_size/effect_size_name/bootstrap_ci/simple_slopes/std_coef_table/missing_warning/warning` ⇒ **交集为空**。
真值在 `moderation_analysis` 的局部：`model.params["XM"]` 与 `model.pvalues["XM"]`（`:434/:437` 写进 `coef_table` 时已 round 到 3／4 位）、
`model.rsquared − model_no_interact.rsquared`（`:446-447`，**算完只用来推 f²，ΔR² 本身不落任何字段**）、
增量 F **产物零处**（`model.fvalue` 是整模型 F，不是交互项增量 F；需 `model.compare_f_test(model_no_interact)` 才有）。

### G2 逐水平截距缺失（图面的硬阻塞）
`_simple_slopes`（`:474-507`）每条水平重拟合 `model_s`，取了 `params["X_c"]` 当斜率，**没取 `params["const"]`** ⇒
实测 `simple_slopes` 列＝`{m}的水平 / {m}实际值 / 简单斜率 / SE / t / p`，**无截距列**（`per_level_intercept_rows=0`）。
绘图面要 `dict[label → (intercept, slope)]`：`coef_table` 只有一枚 `截距`（整体模型在 `M_c=0` 处的常数，恰好＝均值水平那条线）⇒ **三条线里只有 1 条的截距可得**。

### G3 卡面丢弃全部表
全文件 `card.tables.append(...)` **只出现在 `_build_descriptive:146`**；`_build_moderation`/`_build_mediation` 一次都不写 ⇒ 实测 `card.tables=[]`、`card.figures=[]`。
即：调节的 `coef_table`／`simple_slopes` 从未进入结果卡，渲染面即便想桥接也无料。

### G4 卡 ↔ 图的词表不通（比"缺分支"更便宜的缺口）
`generate_figures_from_card(card: dict)` 首行 `method = card.get("method", "")`（`apa_figures.py:562`），
而 `AnalysisResultCard` 的字段名是 **`method_id`**（`result_card.py:26`）⇒ `asdict(card)` 后仍取不到 ⇒ 实测 `generate_figures_from_card(asdict(card))` 返回 **0 枚图**（不是报错，是静默空表）。
且 moderation 分支要的 `card["simple_slopes"]`（dict 形态）＋`card["x_range"]` 两个键**全仓零写入点**。

### G5 绘图函数自带假数据兜底（接通后新引入的风险面）
`generate_simple_slopes_figure()` 无参实测**能出图**（`figure_id="fig_simple_slopes"`，PNG 52,202 B），兜底线条是内置的
`{"High (+1SD)":(2.0,0.6),"Mean":(2.5,0.3),"Low (-1SD)":(3.0,0.05)}`（`:474-479`），`x_range` 默认 `(1.0,5.0)` 与数据无关。
⇒ 适配器若把 `slopes=None` 透传下去，会得到"成功出图"的**假图**；接线方案必须显式定义"无料即拒"（该行为变更属判据向，交人工）。

### G6 正文面两处错键（`reversed_interaction` 检测从不执行）
`src/paper_writer/section_writers.py:883` 守卫 `if "来源" in model_summary.columns:` —— 实测调节 `model_summary` 列＝`['指标','值']`、`指标` 行为 `R²/调整R²/F/p/Cohen's f² (交互项)` ⇒ 守卫**恒 False**，块内逻辑（含 :889 的交叉判定）从不进入；
退一步 :889 读 `simple_slopes["斜率"]`，实际列名是 `"简单斜率"`（`"斜率" in columns` → False）⇒ 即便上游放行也取空 list。两错叠加，**不是同一个键写错那么简单**。

### G7 调节变量名不同源（修好 G1 后立刻显形）
卡用 `card.variables.get("covariates", ["W"])` 取 `w`，而 `build_card_from_output:78-84` 只在 `plan.covariates` 非空时才写 `covariates` 键；
实测 `card.variables={"dependent":["y"],"independent":["x","m"]}`（**无 covariates**）⇒ `w` 落到缺省串 `"W"`。
而 `runner._run_moderation` 的实际调节列是 `plan.independent_vars[1]`（实测 `independent=["x","m"]`，真列名 `m`）。
⇒ 一旦 G1 补上、APA 文本生成，卡面会把调节变量叫成 "W"，与 APA 表／图注不同名。

### G8 在册契约测试被 mock 遮蔽（为何这缺陷能长期全绿）
`tests/test_result_card_runner_contract.py:71-74`：
`class MockModerationResult: interaction_b=0.24; interaction_p=0.03; r2_change=0.04` —— **逐字对齐 builder 的读取面，而非对齐 `AdvancedResult`**。
`test_moderation`（:184-193）因此断 `"调节" in card.apa_text` 与 `card.effect_sizes` 皆真。同文件 :62-67 `MockMediationResult` 对 `_build_mediation` 同形（其读的 `indirect_effect/direct_effect/total_effect/ci_lower/ci_upper` 在 `AdvancedResult` 里同样一枚不存，实测同链见同仓 154316-4d99）。
⇒ **闸全绿 ≠ 接线通**。补数据面之前先动这条 mock 属"改测试判据"，本班不碰（纪律 3）。

### G9 阈值面（只登记，不议）
既有两处硬阈：`result_card.py:568`（`interaction_p < 0.05` 决定"显著"字样）、`advanced.py:450`（`interact_p < 0.05` 决定 warning 文案）。
本班**不改、不建议改、不新设**；只提示：G1 修好后 :568 这条**从未被执行过**的分支会第一次真正上线（文案由"缺少交互项统计量"变为"显著／不显著"）——属行为变化，走人工闸。

### G10 第四名消费者在途（只点名不定性）
`src/output/interpretation.py:587-589` 也读 `r.simple_slopes`（grep 命中行号，本班**未打开该件**：它在 §23.3 禁读／归属未坐实清单内，且 `git status` 现为 `M`）。
⇒ 任何补数据面／补列名的方案都要主班在该件归属坐实后一并核，本班不替它下结论。

---

## 3. 三案＋依赖顺序

### 案A 补字段（数据面：`advanced.py` 内部，不动渲染）
| 子项 | 改法形状 | 落点 | 影响面 |
|---|---|---|---|
A-1 | `interaction_b=float(model.params["XM"])`、`interaction_p=float(model.pvalues["XM"])`（未舍入原值，**别复用已 round 的 coef 行**） | `AdvancedResult` 新增 2 个带默认值的可选字段 | 3 处 `AdvancedResult(` 构造点全在 `advanced.py`（:77/:374/:463）且**全用关键字** ⇒ 源码兼容 |
A-2 | `r2_change=float(model.rsquared − model_no_interact.rsquared)`（局部已算过，只是没留） | `:446-447` 旁 | 产物新增字段 ⇒ `export_snapshot` 的 `result` 串变（键集是 `asdict` 派生，非固定） |
A-3 | `f_change` 需新算（`model.compare_f_test(model_no_interact)`） | `:447` 后 | **新增一次统计量计算**：属数值面新增，须人工确认口径（本班只标位置） |
A-4 | `_simple_slopes` 每水平并取 `model_s.params["const"]` ⇒ 表加截距列（或另返 dict） | `:498-505` | 🔴 列名会变 ⇒ `apa_tables.py:697-716` 的 `columns=list(simple_slopes.columns)` **APA 表列集直接变**（同 s927-19 B1-1 形状） |
A-5 | 血缘同步登记（否则见 §4） | `field_lineage.py` | 登记面 |

- **收益**：G1 直接消 `else` ⇒ 卡面出 APA 文本；A-4 之后图才有料。
- **代价**：A-4 触 APA 表结构；A-3 触新统计量；**卡→图的词表桥（G4）与 G3 丢表不解决 ⇒ 光做案 A 图仍旧没有**。

### 案B 补适配器（渲染面：只吃既有产物）
| 子项 | 改法形状 | 能否达标 |
|---|---|---|
B-1 | 在 `_build_moderation` 里从 `coef_table` 按行找 `"{x} × {m}"` 取 `B`/`p` | ⚠ 可用但是**舍入后的值**（3／4 位），且行名随变量名漂移（实测改列名后行名变 `"x × W1"`）⇒ 只能按位置或后缀匹配，脆 |
B-2 | `interaction_p` 另一条源：`warning` 串里已含 `p=0.0000`（`:451/:453`） | ❌ 解析中文提示串取数＝反模式，不建议 |
B-3 | ΔR² 用恒等式 `f²(1−R²)` 反推 | ⚠ 可反推但**两个入参都已 round 到 3 位**（演示量：以展示的 R²=0.933、f²=1.069 反推得 0.072，仅作可得性证据）⇒ 精度有界、不可作报告值 |
B-4 | `f_change` | ❌ **产物里根本没有**，渲染面无源 |
B-5 | 逐水平 `(intercept, slope)` | ❌ 见 G2：只有均值水平 1/3 条线可拼 ⇒ **图面单独走案 B 画不全** |
B-6 | `asdict(card)` 的 `method_id` → `method` 词表桥 ＋ 把 dict 料（`simple_slopes`/`x_range`）塞进卡 | ✅ 纯渲染面，最便宜（G4） |
B-7 | `section_writers.py:883` 守卫键与 :889 列名（`简单斜率`） | ✅ 纯渲染面，独立（G6） |
B-8 | 绘图兜底改"无料即拒" | ⚠ 属行为／判据变更 ⇒ 人工闸（G5） |

- **收益**：零表结构变化、零新统计量、可并行推进 B-6/B-7。
- **代价**：**消不掉 G2/G4 的硬阻塞 ⇒ 图面画不全；ΔR² 只能带舍入反推；f_change 永久缺位。**

### 案C 双补（数据面给源、渲染面给线）
A-1＋A-2（＋血缘登记）→ 卡面消 `else` 并写 `card.tables` → B-6 词表桥 → A-4 截距列 → `x_range` 由数据给（B-6 配套）→ B-7 正文键名 →（A-3、B-8 各自单列人工题）。

### 依赖顺序（三案共同的最短链，含"必须先谁"的理由）

```
① 数据面键 A-1/A-2      ←  一切的前提；G1 不解决，卡面与正文面都拿不到数
② 血缘登记 A-5          ←  必须与 ① 同笔（见 §4：四个新键里两枚今天会落"不可追溯"）
③ 卡面写 apa_text+tables ←  消 else ＋ 补 G3；④ 的料从这里来
④ 卡→图 dict 词表桥 B-6  ←  依赖 ③（要卡里有 simple_slopes 的 dict 形态）＋依赖 ⑤（要有截距）
⑤ 逐水平截距 A-4         ←  依赖 ① 之后单独评估：它改 APA 表列集，代价最高，可押后
⑥ 正文键名 B-7           ←  与 ①–⑤ 正交，可并行；但它修的是一条从不执行的死分支，改完即"新行为上线"
⑦ mock 对齐（G8）        ←  最后做，且属人工闸：改 mock＝改测试判据
```
**顺序论点**：⑤ 押后不影响 ①②③④⑥ 交付（均值水平那条线＋APA 表已能出全部数字）；
⑥ 与 ③ 不要同一笔（③ 改的是卡、⑥ 改的是正文装配，回滚半径不同）；
⑦ 必须在 ① 之后（先有真字段，mock 对齐真字段才有意义，否则改完仍红）。

---

## 4. 血缘面读数（案A 新字段名的归类，附探针证据）

`conclusion_gate` 对 14 枚拟新增字段名的实测：`blocked=True`，`supporting=4`，`untraceable=10`。

| 拟用名 | spec | 备注 |
|---|---|---|
`interaction_p` | **S3_p_value**（`_p` 后缀兜底） | 语义**恰好正确**（就是 p 值）——巧合可用，但仍建议显式登记，别靠后缀 |
`interaction_coef` | S7_descriptive_table（`_coef` 后缀） | 🔴 误并：交互系数被归进"描述统计表"族（`value_bearing=True, eligible=True`） |
`interaction_b` | **None** | 不可追溯（`_b` 无规则） |
`r2_change`／`delta_r2`／`f_change`／`interaction_se` | **None ×4** | 全部不可追溯 ⇒ 案 A 若一次上四键，血缘面净增 4 枚不可追溯字段 |
`intercept`／`intercepts`／`level_intercept` | **None ×3** | 同上（A-4 会新增这类名） |
`x_range`／`moderator`／`moderator_name` | **None ×3** | 渲染面/卡面的定位参数，也无登记 |
`simple_slopes` | S25_derived_table | 在世登记，`value_bearing=True` |
`n_bootstrap` | S6_sample_size | ⚠ 与 s927-19 §3-A 同一枚坑（前缀 `n_` 误并观测样本量），交叉引用 |

⇒ 结论：**任何补字段方案都要与 `field_lineage` 登记同笔**，否则等于把 4~10 枚新字段挂在"登记不到"上；
但按 s927-06／s927-19 同证（`conclusion_gate` 在 `src/` 内零调用点），这是**登记面债**，不是今天会拦你的生产闸。

---

## 5. 推荐

**推荐案C（双补），但拆两笔、且第 ⑤ 步押后。**

- **C-1（止血笔，最小改动面）**：A-1＋A-2 ＋ 血缘登记（A-5 只登记这两枚）＋ ③ 卡面写 `apa_text`/`card.tables`。
  收益＝恒落 else 消失、ΔR² 效应量进卡、调节变量名同源（顺手把 G7 的 `w` 改读 `independent_vars[1]`）；
  代价＝**零表结构变化**（不动 `_simple_slopes` 列）、零新增统计量（不算 `f_change`）；回滚＝revert 一笔。
- **C-2（图与正文笔）**：B-6 词表桥 ＋ A-4 截距列 ＋ `x_range` 由数据给 ＋ B-7 正文键名。
  代价＝APA 表列集变（`simple_slopes` 多一列）⇒ 与 s927-19 的"结构变化面"同族，需要主班一并收；
  ⚠ 这一笔若不做 B-8，会引入"传 None 出假图"的风险，所以 **B-8 与 C-2 必须同笔或 C-2 不启动**。
- **不推荐单独走案 B**：G2/G4 两道硬阻塞决定案 B 画不全图，且 B-3 的 ΔR² 只能带舍入反推——把可复现性建立在一个恒等式残差上，方向不对。
- **不推荐单独走案 A**：不动 ③④ 就还是"数据有了但卡里没有表、图里没有料"，G3/G4 不解决则收益只覆盖 APA 文本一行。
- **A-3（增量 F）与 ⑦（mock 对齐）单列**：前者是新增统计量计算、后者是改测试判据，两条都超出租位权限，一律**只给位置不给结论**，交主班＋人工。

## 6. 判断题（数值／取值题不代拍）

- Q1 `interaction_b/interaction_p` 用**未舍入原值**还是与 `coef_table` 一致的 3／4 位舍入值？（两者会让卡面与表面对不上号）
- Q2 `f_change` 到底要不要（增量 F 需新算一次 `compare_f_test`）？不要则从 `_build_moderation` 删这条死读取，还是留着恒 None？
- Q3 截距列（A-4）是进 `simple_slopes` 表（改 APA 表列集），还是另返一个 dict 只给图用？
- Q4 `x_range` 取数据的实际 x 全距，还是保留 (1.0,5.0) 默认并把它记成"未声明"？
- Q5 G5 的兜底假数据：改成"无料即拒"（行为变更）还是保留但强制适配器永不传 None？
- Q6 G8 的 mock：对齐 `AdvancedResult`（＝改测试判据）还是新增一条用真 `moderation_analysis` 返回值的用例（＝加判据，不改旧判据）？

---

## 7. 证据

前置：HEAD=`6cb3c96`、分支 `main`（未切、未 add、未 commit）；`git status --porcelain` 开收口两次同为 **14 行**（brief §5 的 12 系主班 13:4x 读数，已漂移）；
`src/analysis/advanced.py`、`src/output/apa_figures.py`、`src/paper_writer/section_writers.py`、`src/analysis/result_card.py`、`src/output/apa_tables.py` 逐件 `git status --porcelain <件>` 复核：
**只有 `src/analysis/result_card.py` 是在途脏件（` M`）** ⇒ 本班引用其 `_build_moderation` 时同时用 `git show HEAD:` 对照（HEAD 版位于 :385-417，`interaction_b = getattr(...)` 与 `else:` 两行与在工作树逐字同）⇒ 本班结论对 HEAD 同样成立，非脏件引入。
`src/output/interpretation.py` 为脏件＋§23.3 归属未坐实 ⇒ 只 grep 行号、未打开（G10）。

**E1 沙盒三证（本班两个探针同一护栏）**
```
$ .venv/Scripts/python.exe tmp/qoder-executor-20260927-1945-psy80/s20_probe_gap.py   → 拒跑：未设置 PSY_SANDBOX_ROOT  RC_NO_ENV=3
$ .venv/Scripts/python.exe tmp/qoder-executor-20260927-1945-psy80/s20_probe_names.py → 同上                             RC_NO_ENV=3
$ PSY_SANDBOX_ROOT=D:/code/psy-analysis/tmp/qoder-executor-20260927-1945-psy80 \
  PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe .../s20_probe_gap.py                RC=0
```
→ 沙盒生效反证：探针在 **import 前**把 `PSY_ANALYSIS_ARCHIVE_DIR` 指进本班沙盒，打印 `app_paths.ARCHIVE_ROOT` 解析值为
`...\tmp\qoder-executor-20260927-1945-psy80\fake_archive`（同件 s19 探针另证：import **后**改 env 常量不动 ⇒ `paths` 是 import 期常量、monkeypatch 无效）。
→ 夹具：`tests/fixtures/golden_stats/advanced/moderation.csv`（git 跟踪件，实测 30 行 × `x,m,y` 三列），第二组用**内存改列名**（`m`→`W1`）验漂移，不落盘。
→ 中文输出必须 `PYTHONIOENCODING=utf-8`（首次未设 ⇒ `UnicodeEncodeError: 'gbk' codec can't encode '\xb2'`，rc=1 但计算已完成；本班按 brief §6 补该变量后 rc=0，此坑与 kaoyan 的"禁设"口径不冲突，psy 该设）。

**E2 主读数原件**：`tmp/qoder-executor-20260927-1945-psy80/s20_gap.json`（30 项结构读数）＋ `s20_names.txt`（血缘归类）。
关键值：`card_key_presence` 六键全 false；`card`＝`{apa_text:"", warnings:["调节效应分析结果缺少交互项统计量"], effect_sizes:[], tables_len:0, figures:[], plain_language_summary:"", variables:{dependent:[y],independent:[x,m]}}`；
`simple_slopes_columns`＝`["m的水平","m实际值","简单斜率","SE","t","p"]`；`rename_drift.simple_slopes_columns`＝`["W1的水平","W1实际值",…]`；
`figures_from_card={n:0, ids:[]}`；`figure_default_slopes={ok:true, png_bytes:52202, uses_builtin_dummy_lines:true}`；
`delta_r2_availability={in_result_attrs:false, as_model_summary_row:[], algebraic_reconstruction_possible_from_displayed:true, recon_value_3dp:0.072 ← 演示量，非结论}`。

**E3 在世性 grep（全部 `--no-ignore` 口径已用于 src/）**：
`rg -n "AdvancedResult\(" src/ tests/` → 仅 `advanced.py:77/374/463`，三处均关键字构造；
`rg -n "card.tables.append" src/analysis/result_card.py` → 唯一命中 `:146`；
`rg -n 'card.get("method"' src/output/apa_figures.py` → `:562`（对比 `result_card.py:26 method_id`）；
`rg -n "simple_slopes" src/` → 消费者 4 名：`apa_tables.py:697-716`（**这条是通的**，按列迭代）、`apa_figures.py:681-693`、`section_writers.py:886-889`、`interpretation.py:587`（禁读，未打开）；
`rg '"simple_slopes":' src/` 与 `rg "x_range" src/` 生产写入 0 处。

**E4 零写库／零 data 触碰**：本班未连任何 sqlite、未走 Backup API（无重查需求）、未读 `data/`；
`ls reports` → `No such file or directory`（未长出快照目录）；探针只 `print` 与写沙盒内 `s20_gap.json`（带越界 assert）。
班中系统侧通报他方对 `data/kaoyan.db` 持锁，本班与该写入无关、未参与、未打开该件（`.gitignore:42` 覆盖 `data/` ⇒ 无还原点，故一律不碰）。

## 8. 遗留问题

1. **本班作废掉两条初读**：①「分发器无 moderation 分支」——错在 grep 只匹 `method in (...)`，`apa_figures.py:681` 实有 `elif method == "moderation"`（G4 的真实缺口是 `method` vs `method_id` 词表不通＋卡不带料）；②探针里 `dispatcher_branches_have_moderation` 用了"全文件子串命中"当判据，命中过宽（`generate_simple_slopes_figure` 本身就在文件里），该布尔**不采信**，改以 `figures_from_card.n=0` ＋ 分支行号实证。
2. `f_change`（A-3）与 mock 对齐（G8/⑦）两条本班只给位置与风险，未给方案：前者触新增统计量、后者触测试判据，均超只读位权限。
3. `_build_mediation` 与 `_build_moderation` 同根（`AdvancedResult` 无对应字段、mock 同形遮蔽），本单按卷宗只裁 moderation；**建议主班把两枚并成一笔**，否则 C-1 只把一半的 else 消掉。
4. 本班**未跑任何 pytest**（只读位＋同仓并发）⇒ §2 的在册测试状态是读码＋真对象探针推得，主班收班请定向跑
   `tests/test_result_card_runner_contract.py tests/test_result_card_registry_snapshot.py tests/test_golden_stats_v2.py -k Moderation tests/test_apa_figures_v2.py` 并附时刻与 HEAD。
5. G10（`interpretation.py`）与 `_build_moderation` 的在途定性需主班在归属坐实后统一核；本班不替禁读件下结论。
6. 全量套件读数缺位（并发只读约束），勿以本班名义引用任何"N passed"。
