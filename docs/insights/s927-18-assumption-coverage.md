# s927-18 方差分析前提覆盖缺口：「方法×前提」矩阵与补齐优先级（只读取证，零码改动）

- 班名：`qoder-executor-20260927-1940-psy79`（波次 28）；取证时刻 2026-09-27T19:49:34+08:00（`date` 现取）
- **开工 HEAD=`6cb3c96`；收口 HEAD=`37d0e69`**——19:43:36 由**他会话（署名 `psy-analysis <local@psy-analysis>`）**提交一笔 `docs(psy): s927-16 …`，内容正是本班 s927-16 产物（`git show --stat` 只含该 1 文件 123 行，`git diff 37d0e69 -- <该文件>` 为空⇒内容与本班落盘一致）。本班**未执行任何 git add/commit**，此笔为并发现场，按纪律只点名不介入。
- 本轮所有被引文件均未被本班改动（`git status --porcelain` 现值 14 项＝8 枚在途 ` M` ＋ s924-36／node_modules／research_release_gate／_sklearn_compat 四枚原有未跟踪 ＋ 本班 s927-17／s927-18 两份产物；s927-16 已随上笔进仓）
- 判据：卷宗「完成标准」①矩阵全方法覆盖 ②缺口清单带证据 ③优先级建议 ④零码改动
- 红线执行口径：**只出材料与优先级建议，不改计算码、不改 `assumptions` 键、不动 golden／期望数据；不签任何统计数值／效应量／检验结论**。本文所有"缺/有"都是**结构事实**（谁写了哪个键、谁读哪个键名），不是"该不该拒绝原假设"。

---

## 0 实况四句

1. **锚点的两项键集合复测通过（真跑，非引用）**：`one_way_anova → ['homogeneity']`、`mann_whitney → []`。
2. **覆盖面现值**：48 个在册 handler 里**只有 4 个**往 `output["assumptions"]` 写东西（`independent_ttest`／`one_way_anova`／`welch_anova`／`two_way_anova`）⇒ **44/48 方法的 assumptions 键集合为空**；其中**回归/SEM 之外的 30 个方法连注册表条目都没有**。
3. **两层互不相交**：假设注册表 `_METHOD_ASSUMPTIONS`（15 键）与 handler 实装集（4 键）**交集只有 1 个（`two_way_anova`）**；14 个在册方法有"假设清单文案"但 handler 不产任何键，3 个真产键的方法（含卷宗点名的 `one_way_anova`）**根本不在注册表**。⇒ 锚点 E2「独立组比较无一在册」在本轮以集合运算复算成立。
4. **新发现一条锚点未点名的机械盲区**（对方差分析族最致命）：`independent_ttest` 的 Levene 结果挂在 `result.assumption_equal_var`，而路由器 `_homogeneity_violated` 的旁路只读 `result.assumption_homogeneity`（`assumption_router.py:119`／`:133`）⇒ **键名不同即恒判"未违反"**。用替身对象实测：把 `{'passed': False}` 命名为 `assumption_equal_var` → 路由器返 False；同值改名 `assumption_homogeneity` → 返 True。

---

## 1 四层证据定义（矩阵怎么读）

| 层 | 含义 | 取证方式 |
|---|---|---|
| **L1 handler 写键** | `output["assumptions"][k] = …`，是 UI/结果卡可见的"前提读数"来源 | AST 扫 `src/analysis/runner.py` 48 个 `@_register` 函数体（沙盒 `scan_handlers.py`） |
| **L2 result 内嵌字段** | `result.assumption_*`（ANOVAResult／TT 结果 dataclass），路由器**旁路**可读，但不进 `output["assumptions"]` | 同上 + `assumption_router.py:117-121/131-135` |
| **L3 注册表在册** | `_METHOD_ASSUMPTIONS[tt]` 的 `MethodAssumption(name, kind=existing|placeholder, …)`，**描述性**，不参与计算 | 导入 `assumption_router` 现值 dump（`scan_registry.py`/`scan_matrix.py`） |
| **L4 路由出口** | 违反后有没有"建议改用哪个检验"：`_NORMALITY_FALLBACK`(5 键)／`_HOMOGENEITY_FALLBACK`(1 键)／`_SPHERICITY_NOTE`(1 键) | 同上 |

⚠ L3 的 `kind="existing"` 只代表"注册名指向 `assumptions.py` 既有 check 函数"，白名单只有 4 个 check（`_EXISTING_CHECK_NAMES = {check_normality, check_homogeneity, check_sphericity, check_normality_groups}`）；**它不等于 L1 真的在该 handler 里被调用**（见 G2）。

---

## 2 判据①：「方法 × 前提」矩阵

四前提取卷宗口径（独立性／分布／方差／样本量），另立「球形」列（重复测量族需要，锚点已计入）。
图例：`L1✓键名`＝handler 真写该键；`L2✓`＝result 内嵌该字段且路由器有读路径；`L3 E/P`＝注册表在册（existing/placeholder）；`L4✓`＝有建议出口；`✗`＝三层全无；`—`＝不适用。

### 2.A 方差分析族（卷宗主问对象）

| 方法 | 独立性 | 分布（正态） | 方差（齐性） | 球形 | 样本量 | L4 出口 |
|---|---|---|---|---|---|---|
| `one_way_anova` | ✗ 全仓无实现（锚点前提一，引它别重查） | **✗ 不查**（实测键集合 `['homogeneity']`，无 normality） | L1✓ `homogeneity`（`runner.py:122` ← `anova.py:74→131`）；L3 **不在册** | ✗ | 通用层（见 2.C） | L4✓ 唯一在册的 homogeneity 出口（→`welch_anova`） |
| `welch_anova` | ✗ | ✗ | L1✓ `homogeneity`（`runner.py:137` ← `anova.py:587`）；L3 不在册 | ✗ | 通用 | **L4✗：`_HOMOGENEITY_FALLBACK` 只有 `one_way_anova`** ⇒ 有读数、无建议 |
| `two_way_anova` | ✗ L3 P（placeholder） | L3 E（但 handler 不查，实测无 normality 键） | L1✓ `homogeneity`（`runner.py:152`，且有 `is not None` 守卫 ← `anova.py:227`）；L3 E/P 在册（**唯一两层相交者**） | ✗ | L3 P ＋通用 | **L4✗（映射无 two_way_anova）** |
| `repeated_anova` | ✗ L3 不在册 | ✗ | ✗ | **L2✓**（`anova.py:392/465` 产 `assumption_sphericity`，handler 不写 L1 键）；L3 不在册 | 通用 | L4✓（`_SPHERICITY_NOTE` 仅 `repeated_anova`）——但本班端到端用例**未跑通**（见 E4），可达性只由静态行号支撑 |
| `mixed_anova` | L3 P | L3 E | L3 E | **L2✓**（`anova.py:672/717`）＋ L3 E；handler 不写 L1 键 | L3 P | **L4✗（映射只有 repeated_anova）** |
| `ancova` | ✗ | ✗ | ✗ | ✗ | 通用 | ✗（`ancova` handler 无任何 assumption 写入，AST hits＝'-'） |
| `manova` | L3 ✗/P | L3 P | L3 E/P | ✗ | L3 — | **L1–L4 全断**（handler 不写键；14 个"在册不产键"方法之一） |

### 2.B 相邻比较族（锚点点名的对照组）

| 方法 | 独立性 | 分布 | 方差 | 样本量 | 备注 |
|---|---|---|---|---|---|
| `independent_ttest` | ✗ | **L1✓ `normality`**（`runner.py:79` 逐组 Shapiro） | **L2 有、但路由盲区**：`result.assumption_equal_var`（`ttest.py:99`）≠ 路由器读的 `assumption_homogeneity` ⇒ §0.4 实测恒 False | 通用 | ttest 内部另做 Levene 并**同族静默切 Welch**（锚点主干读数 1，属"绕过前提登记"的另一条路） |
| `paired_ttest` / `one_sample_ttest` | ✗ | **✗ handler 不查**（AST 无命中），但两者**在 L4 映射里在册**（`_NORMALITY_FALLBACK`）⇒ 永远不可能触发的死映射 | ✗ | 通用 | |
| `mann_whitney` | ✗ | ✗ | ✗ | ✗ | 实测键集合 `[]`（锚点 K 段复测通过）；**非参目的地自身不查任何前提** |
| `kruskal_wallis` | ✗ | ✗（实测键集合 `[]`，E3） | ✗ | ✗ | 同上：`one_way_anova` 的正态建议落点，自身零前提 |
| `wilcoxon` / `friedman` | ✗ | ✗ | ✗ | ✗ | handler 无命中 |
| `pearson_corr` | ✗ | L4✓ 在映射（→`spearman_corr`）／L1✗ handler 不查 | — | 通用 | 死映射同 `paired_ttest` |

### 2.C 全方法通用层（不分方法，故矩阵只列一次）

| 维度 | 在世实现 | 覆盖面 | 关键限制（只报事实） |
|---|---|---|---|
| 样本量 | `data_quality_check` 的 `n_complete<30` 文案（`runner.py:909-932` 调用，**包在 `try/except: pass` 里**，锚点 E6 已证静默降级） | 名义上全 48 方法 | DQ 抛错时 `output["data_quality"]=None` 且不留错误行 ⇒ "跑没跑"外部无从判分 |
| 样本量（闸） | `assumption_router.py:150-154` 的 `n<20`／`n>5000` → `hard_route_allowed=False` | 全 48 方法（`check_route` 在 `runner.py:958` 无条件调） | 只闸"一键切换"，不闸分析本身 |
| 样本量（护栏） | `guardrails.check_sample_size` | **仅 Streamlit 主分析按钮一条路**（`app.py:1081`，本班 s927-16 实测：另 6 个 `run_analysis` 调用点零护栏） | 只出 `warn` 态，不阻断 |
| 独立性 | **全仓无实现**（锚点 154314 前提一：`rg` 12 命中全是"卡方独立性检验"与 SPSS 教学文案） | 0/48 | 引它别重查 |
| 分布（正态，另一口径） | `data_quality.py:279` 的整列 Shapiro | 全方法（DQ 层） | 与逐组 Shapiro **同 output 内两套口径**（锚点 A 段实测：逐组通过、合并违反） |

---

## 3 判据②：缺口清单（每条带证据，按"是否要造统计计算"分性）

| # | 缺口 | 证据（可复算） | 性质 |
|---|---|---|---|
| **G1** | 多组路径不查正态：`one_way_anova`／`welch_anova`／`two_way_anova` 的键集合只有 `homogeneity` | 真跑：`probe_keys.py` → `one_way_anova keys=['homogeneity']`、`welch_anova keys=['homogeneity']`；AST：三 handler 均无 `check_normality*` | **需造计算**（红线） |
| **G2** | 注册表 `kind="existing"` 与 handler 实装互不相交：14/15 在册方法 handler 不产任何键 | 集合运算（E2，见 §5.3）：`_METHOD_ASSUMPTIONS`(15) ∩ handler-writes(4) = `{two_way_anova}` | 结构（登记与实装两侧二选一） |
| **G3** | 反向：真产键的 3 个方法（`independent_ttest`/`one_way_anova`/`welch_anova`）**不在注册表** | 同上，`写了键但不在注册表: ['independent_ttest','one_way_anova','welch_anova']` | 结构（扩 `_METHOD_ASSUMPTIONS` 需同时过 `test_assumption_route_count_pin.py` 的钉桩，见 G7） |
| **G4** | **键名盲区**：`independent_ttest` 的 Levene 挂在 `assumption_equal_var`，路由器只读 `assumption_homogeneity` | 替身实测：`{'passed': False}` 命名 `assumption_equal_var` → `_homogeneity_violated`=False；改名 → True（E5，见 §5.3） | 结构（改名或加读路径，非造计算） |
| **G5** | **有键无出口**：`welch_anova`／`two_way_anova`／`mixed_anova` 产或可读 `homogeneity`/`sphericity`，但三张映射表键集只含 `one_way_anova`（方差）与 `repeated_anova`（球形） | dump：`_HOMOGENEITY_FALLBACK=['one_way_anova']`、`_SPHERICITY_NOTE=['repeated_anova']`、`_NORMALITY_FALLBACK` 5 键 | 结构（映射表加键即可，但会新增建议＝行为变化） |
| **G6** | **死映射**：`paired_ttest`／`one_sample_ttest`／`pearson_corr` 在 `_NORMALITY_FALLBACK` 在册，其 handler **不产 normality 键** ⇒ 永不可能触发 | AST：三 handler hits 均为 '-'；映射键集合含三者 | 结构 |
| **G7** | 44/48 方法 assumptions 键集合为空；30 个方法三层全无（含 `mediation`/`moderation`/`efa`/`cfa`/`hlm`/`sem`/信度族/非参族） | AST 全集扫描（E1：48 handler 中 4 个写键，见 §5.3 脚本） | 混合（补前提＝造计算＝红线；只登记＝结构） |
| **G8** | 建议链**上游已被吞**：即使补了键，`assumption_router.py` 的 9 处 `is False` 身份比较仍会把 `np.bool_` 违反读成"未违反"（s927-17 实测：真实 `check_normality` 违反→`is False` 为 False） | s927-17 §2 真值表＋E3；生产者 `assumptions.py:47/93/150`、`anova.py:74/392`、`data_quality.py:279` 均产 `numpy.bool` | **依赖项**（不修它，G1/G4/G5 的补齐对用户不可见） |

> 与锚点冲突处：锚点前提四称"专职护栏 `guardrails.check_sample_size` 零调用者"。本班 s927-16 复算否证其范围——它在 `app.py:1081` 在世接线（Streamlit 主分析路径），只是**不覆盖另外 6 个 `run_analysis` 入口**。矩阵 2.C 按实况写。

---

## 4 判据③：补齐优先级建议（排序＝材料，不是放行）

排序原则（可驳）：① 是否被既有缺陷吞住收益 → ② 改动性质（结构登记/映射 vs 造统计计算＝红线距离）→ ③ 用户主用路径的暴露面。

- **P-1（前置，非本单范围但决定其余各项的可见性）＝ 先修 G8 的 9 处身份比较**。
  理由：G1/G4/G5 任何补齐产出的都是 `numpy.bool` 型 `passed`，在现写法下一律读成"未违反"⇒ **补了也不产出建议**。若跳过这步先补前提，会造出"有新键、无新行为"的空转改动，且测试仍全绿（假绿成因同 s927-17 §2.3）。
- **P0＝G4（键名盲区）与 G5/G6（映射表与实装对齐）**：三条都是"改名/加键/删死映射"级别，**不新增任何统计计算**，风险面最小、可测性最强。其中 G6（死映射）也可选择"给 `paired_ttest`/`one_sample_ttest` 补逐组 Shapiro"，但那已属 G1 性质的造计算，需拆成两案分别裁。
- **P1＝G3（把真产键的 3 个方法登记进注册表）**：收益是覆盖面画像（`describe_assumption_routes()` 的 existing/placeholder 计数）不再漏主用族；**注意它会撞在册钉桩** `tests/test_assumption_route_count_pin.py`（该件专钉"注记数↔实现现值"三向一致，改注册表必须同步改注记，且禁"自证式快照"——见其 `:160-171` 的活对象守卫）。
- **P2＝G1（多组路径补正态）与 G7 的方法级子集**：**这是造统计计算＝红线**，须另派带人工裁的班，并要求逐条回答：用逐组还是合并 Shapiro（2.C 已实测两口径在同 output 内分叉）、`one_way_anova` 的 k 组多重比较下 Shapiro 的 α 如何定、效应量缺失时的建议目的地（`kruskal_wallis` 自身零前提，G7）。**本班一律不代答。**
- **P3＝G2（注册表 existing 白名单与实装的一致性）**：属长期债，涉及"placeholder 是设计使然"的在册解释（锚点 E4：`_EXISTING_CHECK_NAMES` 只 4 个 check ⇒ 线性类假设在当前设计下无法登记为 existing）。排在最后是因为它牵动"占位是否算缺陷"的口径本身。
- **不建议现在动的**：`mann_whitney`/`kruskal_wallis`/`wilcoxon`/`friedman` 的"非参方法自己的前提"。它们当前是**建议的目的地**；给目的地补前提检查会形成"建议 A→A 也被闸"的闭环风险，属设计决策（交人）。

---

## 5 判据④：零码改动自证 + 交人工／遗留

### 5.1 零写与零改动
- 本班未改任何被跟踪文件；未 add／commit／checkout／restore／stash／clean。三份产物只新增 `docs/insights/s927-1[678]-*.md`（待主班代提交）。
- `data/` 零写自证：探针为纯内存（demo 数据由 `src/data/demo_datasets.py` 现算，不落盘），全程未连 sqlite、未开生产库；`find data -type f -printf '%p %s\n'` 跑前（19:30）／跑后（收口前）两份快照 `cmp -s` rc=0，**187 文件／21,103,172 B** 与在册基线逐字符相符。
- **跑过 `run_analysis` 的副作用面已核**：`runner.py` 的写盘点仅 `export_snapshot()`（`:1079/:1081/:1082`），本班未调用；`reports/snapshots/` 未生成（收工 `git status` 无该路径）。
- **未跑 pytest**：并发窗禁全量；定向跑亦未必要（矩阵全部由 AST＋导入 dump＋两次内存探针闭合）。因此：未复跑、未归因在册红 `test_export_gate_global_scan::test_all_download_buttons_accounted_for`；未触 `tests/test_paper_writer.py::TestLiteratureManager::test_online_search_graceful`（无 `online` 标记的 CrossRef 外呼件，硬交底④）。

### 5.2 交人工／遗留
1. `repeated_anova`／`mixed_anova` 的**球形旁路可达性只到静态行号级**（`:117-121/131-135` 读 `result.assumption_sphericity`）：本班端到端用例 `result` 为 `None`（`AnalysisPlan` 的 blocks/时间列字段组合未凑对，见 E4），**未取得活体证据**（E4）⇒ 矩阵里该行标 L2✓ 属"生产者存在＋读路径存在"，不含"实测触发"。放行前建议补一次真跑。
2. G8 与 s927-17 是同一件事的两端：本文按"依赖项"引用，**修法与语义（None 三态）不在本文选案**，交主班在 s927-17 上裁。
3. 优先级排序里的 P0/P1 都伴随**运行时行为变化**（新增建议、改注册表计数），属"改生产码"人工闸；本文只给最小改动面，未给 diff。
4. 全量套件读数缺位（并发窗），收班由主班统一取数并附时刻与 HEAD。
5. 在册钉桩提示（E3 的键集合复测即经真跑取证）：任何扩 `_METHOD_ASSUMPTIONS` 的动作要先读 `tests/test_assumption_route_count_pin.py`（专钉注记↔实现三向一致＋反自证守卫），否则会撞既有红。

### 5.3 取证脚本与 E 编号（全在沙盒 `D:/code/tmp/qoder-executor-20260927-1940-psy79/`，仓根零残留）

| E | 命令 | 关键读数 |
|---|---|---|
| E1 | `PYTHONIOENCODING=utf-8 .venv\Scripts\python.exe <沙盒>/scan_handlers.py` | `registered handlers: 48`；仅 `independent_ttest`(69-83,`check_normality_groups`+`output["assumptions"]`)、`one_way_anova`(113-124)、`welch_anova`(128-139)、`two_way_anova`(143-153) 有 hits，其余 44 个为 `-` |
| E2 | 同上目录 `scan_matrix.py`（集合运算） | handler 写键集 (4) ∩ 注册表 (15) = `['two_way_anova']`；`写了键但不在注册表: [independent_ttest, one_way_anova, welch_anova]`；`在注册表但 handler 不写键: 14`；`48 中两者皆无: 30` |
| E3 | `<沙盒>/scan_registry.py` | 注册表逐条 name/kind（含 `manova` 方差条目 `E/P` 并存、`chi_square_*` 全 P）；`_NORMALITY_FALLBACK`=5 键、`_HOMOGENEITY_FALLBACK`=`['one_way_anova']`、`_SPHERICITY_NOTE`=`['repeated_anova']`、`_EXISTING_CHECK_NAMES`=4 个 check |
| E4 | `<沙盒>/probe_keys.py`、`probe_keys2.py`（真跑 `run_analysis`，纯内存 demo 数据） | `one_way_anova`/`welch_anova` → `['homogeneity']`；`mann_whitney`/`kruskal_wallis`/`repeated_anova` → `[]`；`independent_ttest` → `['normality']` 且 result 内嵌 `['assumption_equal_var','assumption_normality']`；`repeated_anova` 用例 `result` 为 `None`（计划字段未凑对）⇒ 球形可达性未取活体证据 |
| E5 | 内联替身对象（`class Fake: assumption_equal_var={'passed': False}`） | `_homogeneity_violated` 读 `assumption_homogeneity` ⇒ 对 `assumption_equal_var` **恒 False**；同值改名即 True。纯查找路径验证，不含任何真实统计量 |
