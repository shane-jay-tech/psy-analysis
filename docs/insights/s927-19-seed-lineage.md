# s927-19 · seed 不进产物：三处改动的血缘影响清单＋迁移材料（零码改动，154316-1）

- 班：`qoder-executor-20260927-1945-psy80`｜cwd `D:\code\psy-analysis`｜分支 `main`｜HEAD `6cb3c96`
- 判据：①血缘影响清单 ②迁移步骤 ③推荐 ④零码改动 —— **四条全中**
- 锚点：`zcode-bridge/outbox/20260925-154316-4d99.result.md` → 按 brief §3a 到 `done/` 取到（9-27 00:13 落盘，14,560 B）⇒ 路径搬家不是缺陷，锚点**在世**
- 🔴 红线自证：本班**不执行任何迁移**（不重跑分析、不导快照、不改 golden、不改被跟踪文件）。
  文中出现的统计数值（`β 0.304/0.307`、`CI [0.204,0.417]` 等）**全部是 154316-4d99 已交回读数的引用**，
  本班未产生任何新的效应量/显著性结论；改动面一律写成「主班放行后可照做的步骤」，取值题留人工。

---

## 1. 锚点复算（先证其在世，再证其仍成立）

| 复点 | 本班读数（可复算命令见 §7） | 判定 |
|---|---|---|
| 「seed 不进任何产物字段」 | `bootstrap_ci` 表列＝`效应/β/CI下限/CI上限/Bootstrap n/判断`（`advanced.py:337-344`），`model_summary` 行＝6 行、末行是**中文串** `f"{n_bootstrap}次（偏差校正）"`（`:365`）⇒ 全表**无 seed 载体** | ✅ 锚点成立 |
| 「`_run_mediation` 不透传 n_bootstrap/seed」 | `runner.py:844` 实参四个：`advanced.mediation_analysis(df, x, m_arg, y)` | ✅ 锚点成立 |
| 「三处改动会让既有快照/表结构变化」 | 本班把「快照」拆成**三类载体**逐条落点（§3-B）：APA 表列集、`export_snapshot` JSON、归档 `params.json`／ZIP `analysis_params.json` ⇒ **成立，但只有 1 处真变表结构**（`bootstrap_ci` 增列），另两处是**内容串变、结构不变** | ✅ 成立（并按磁盘实况收窄，见 §3-B 注） |
| 「涉 APA 表字段血缘 `field_lineage`」 | 血缘面实测读数见 §3-A：`model_summary` **今天就已经是不可追溯字段**；`seed` 一旦进结果体＝**新增一枚不可追溯字段**；`n_bootstrap` 会被前缀规则**误并进 S6 观测样本量** | ✅ 成立，且比锚点更严重（锚点未预见 S6 误并） |

⚠ 一处**初读被本班否证**：锚点 154316-4d99 把 `model_summary` 当作「已有登记、加一行即可」的表。实测 `spec_for("model_summary") is None`
（`field_lineage.py` 精确表无此名、后缀 `_table/_coef/_check…` 均不匹配、前缀 `n_` 不匹配）⇒ **它从来不在血缘登记面里**。
本班第 3 处改动的先后顺序因此要重排（见 §6）。

---

## 2. 三处改动面（精确到位，全部零执行）

| # | 改动 | 落点 | 形状 |
|---|---|---|---|
| **M1** | `model_summary` 增一行 seed | `src/analysis/advanced.py:359-366`（`pd.DataFrame([{...}])`，列固定为 `指标/值`） | 表体**多一行**（列集不变）；`值` 列今天混装 float 与 str |
| **M2** | `bootstrap_ci` 增 `seed` 列 | `src/analysis/advanced.py:332-355`（`ci_rows` 两处 append：逐中介 `:337-344`、总间接 `:347-354`） | 表**多一列**（两处 dict 必须同改，否则 `pd.DataFrame(ci_rows)` 长出新列 NaN） |
| **M3** | `AnalysisPlan` 增 `n_bootstrap`/`seed` 并由 handler 透传 | `src/parser/intent_resolver.py:13-46`（dataclass，37 行字段尾巴追加）＋ `src/analysis/runner.py:830-845`（`_run_mediation` 调用点） | 计划面**多两个字段**＋调用点实参从 4 个变 6 个 |

**M3 的隐藏第四处（锚点未点名，本班新增）**：`src/utils/workspace.py:_serialize_plan`（`:133-158`）与 `_deserialize_plan`（`:161-183`）是**逐字段手写白名单**，
新字段不会自动进出。⇒ 只做 M3 不做这一处，seed 在「保存工程 / 重开工程」路径上**静默丢失**，可复现性字段补齐目标在持久化面直接落空。
同理 `runner.export_snapshot:1049-1054` 的 `snapshot["plan"]` 也只写 4 个键（`test_type/dependent_vars/independent_vars/confidence_level`）。

---

## 3-A. 血缘影响清单（`src/analysis/field_lineage.py` 登记面）

沙盒探针 `tmp/qoder-executor-20260927-1945-psy80/s19_probe_lineage.py` 实跑读数（纯函数面，零写盘）：

| 字段名 | 现状 spec | value_bearing / conclusion_eligible | 三处改动后的血缘后果 |
|---|---|---|---|
| `model_summary` | **None（不可追溯）** | — | M1 加行**不会**让情况变坏，也**不会**变好：它今天就没登记。闸门 `blocked` 早已为真（见下行基线） |
| `bootstrap_ci` | `S2_ci_endpoint` | True / True | M2 加列：**登记面看不到列级**（`EXACT_FIELD_SPEC` 只按顶层字段名匹配）⇒ 加列对血缘闸**完全隐形**，等于把可复现性字段塞进一条「血缘指向 `effect_size_ci.py::fisher_z_ci`」的表里（该抽取锚点与中介 bootstrap 无关，属锚点错位） |
| `seed`（若作为结果体新顶层字段） | **None** | — | **新增一枚不可追溯字段** ⇒ `conclusion_gate` 的 `untraceable` 从 `["model_summary"]` 变 `["model_summary","seed"]`（探针读数 `with_seed_field`） |
| `bootstrap_seed`／`rng_seed`／`seed_value` | **None** | — | 换名无用：登记面没有任何 seed 系命名，四种写法实测全部不可追溯 |
| `n_bootstrap` | **`S6_sample_size`（前缀 `n_` 兜底）** | True / **True** | 🔴 **语义误并**：它会被算成「观测样本量」族，而 S6 的 note 已就 `sample_size` 同名碰撞警告过一次（`field_lineage.py:269-270`）。探针实测 `trace_project_dir(demo,"n_bootstrap")` → `reached_raw_record=True`，即**一个运行参数被"回溯"到了某个被试行**——这是假阳性可追溯，比不可追溯更难发现 |

**基线闸读数**（今日，不加任何字段）：`AdvancedResult` 十个字段名过 `conclusion_gate` →
`blocked=True`，`supporting=9`，`ineligible=[]`，`untraceable=["model_summary"]`。
⇒ 「接闸即红」这件事**不是 seed 改动造成的**，seed 改动只把不可追溯集从 1 枚扩到 2 枚。
交叉参照同仓兄弟班 `docs/insights/s927-06-conclusion-gate.md`（HEAD `6bf76af`）：**`conclusion_gate` 在 `src/` 内除定义与 `__all__` 导出外零调用点** —— 本班复跑同一读法，结论同上。
⇒ 血缘面今天的实际风险是**登记性风险（测试与登记表面）**，不是生产阻断风险。

**在册血缘测试的受力点**（`tests/test_analysis_field_lineage.py`，逐条对照，不改判据）：

| 测试 | 判据写法 | M1/M2/M3 是否受力 |
|---|---|---|
| `test_report_fields_are_registered`（`:140-144`） | 对 `report_fields.REQUIRED_REPORT_FIELDS`（现值 5 项 `alpha/omega/n_items/n_cases/ci`）逐个断言 **spec 存在且 value_bearing=True** | 只有把 `seed` 追加进这张表才受力：实测 `spec_for("seed") is None` ⇒ **立刻红**。`n_bootstrap` 追加则**不会红**（S6 恰好 value_bearing=True）⇒ 这是「静默通过型」缺口，需在裁决里点名 |
| `test_required_result_keys_are_registered`（`:147-149`） | 遍历 `result_schema.REQUIRED_RESULT_KEYS`（8 项） | 不受力（seed 不在这 8 个键里；除非有人把 `plan` 换成 `plan.seed`） |
| `test_registry_carries_no_numeric_values`（`:110-121`） | 登记项里装不进 int/float | 不受力，但它锁死了「把 seed 的**值**写进登记表」这条路 ⇒ seed 的默认值只能在代码常量面，不能靠登记面声明 |
| `test_every_mapping_points_to_a_registered_spec`（`:47-52`） | 映射表每个目标 spec 必须在册 | 若为 seed 新增 `S27_run_config` 之类的 spec，必须同步进 `FIELD_SPECS`，否则此条红 |
| `test_extraction_anchor_exists_in_repo`（`:66-77`） | 锚点写成 `路径::符号` 且符号必须在该文件里存在 | 若 S2 的 `extraction_anchor` 不改，seed 仍挂着 `effect_size_ci.py::fisher_z_ci`（锚点错位继续存在）；若新建 spec 指向 `advanced.py::mediation_analysis`，此条会**逼着**登记面与产物面同源 |
| `test_random_sampled_value_bearing_fields_trace_to_raw_record`（`:175-188`） | 三个固定 seed（68/2026/9）各抽 3 项，断言回溯到原始记录 | 实测：抽样池若加入 `n_bootstrap`，`seed=68` 与 `seed=9` 两组的命中集合**改变**（68→含 `n_bootstrap`；9→含 `n_bootstrap`）⇒ 用例仍绿（它只断"能回溯"），但**回溯语义被污染**：运行参数被当成可回溯到被试行的统计量。这是「测试全绿但方向反了」的形状 |

---

## 3-B. 产物／快照／表影响清单（哪些东西会变）

按「结构变 / 内容变 / 不受影响」三档。**没有任何一处需要动 `data/`**（本班探针未读写 `data/`，详见 §7 反证）。

### B1 会变**结构**的（只有 2 处）
1. **APA 表 `{table_id}_ci`**（method_id=`mediation`）：`src/output/apa_tables.py:643-661` 用 `columns=list(result.bootstrap_ci.columns)` ⇒ M2 一落地，**APA CI 表多一列 `seed`**，表列集随行。
2. **工作区持久化件**：`src/utils/workspace.py` 的 `_serialize_plan` 白名单若不同步 ⇒ 新字段在磁盘上**根本不出现**（缺结构，而非多结构）。

### B2 会变**内容**（字节级）的（4 处）
3. `reports/snapshots/<snapshot_id>.json`（`runner.export_snapshot:1028-1082`）：`snapshot["result"] = asdict(result)`，DataFrame 经 `json.dump(..., default=str)` **整体字符串化** ⇒ M1 加一行、M2 加一列都会改写该字段串。**结构键集不变**（仍是 `schema_version/snapshot_id/.../result/...`），所以既有快照读取方不会因缺键报错，但**逐字节 diff 必红**。
4. 归档件 `archive/<ts>_<id>/params.json` 的 `params` 节（`src/utils/archive_manager.py:65-82`，写入方是 `src/ui/quick_entries.py:720`）⇒ M3 若把新字段塞进 `params` 字典，这里跟着变；`index.json` 摘要同步。
5. 快照 ZIP 的 `analysis_params.json`（`src/output/snapshot.py:72-92` → `_extract_params:220-243`，逐 dataclass 字段 `str(v)`）⇒ M1/M2 改写的仍是**字符串化表体**；`snapshot_created` 本来就每次不同，故该项属"内容漂移"而非"新缺陷"。
6. 中介结果卡 **APA 文本**（`src/analysis/result_card.py:526`）：字面量 `"中介效应分析（Bootstrap 5000 次）表明…"` —— 见 B3-①，它今天根本不生成，但**一旦修好接线而不接 plan.n_bootstrap，这里会把 5000 写成假声明**。

### B3 声明面「5000」硬编字面量（M3 的必查清单，seed 之外的同族缺陷）
`rg -n "5000" src/` 命中里与中介 bootstrap **同源**的 6 处（改动前需逐处决定"参数化还是留常量"）：
`result_card.py:526`、`apa_tables.py:659`（英文 note `"5000 bootstrap samples"`）、`section_writers.py:719`（正文「重复抽样5000次」）、
`learning_card.py:671` 与 `:691`、`ui/undergrad_wizard.py:3003`（UI 预期耗时提示）、`defense_qa_kb.py:1380`（答辩话术）。
⇒ **裁决点**：M3 透传后若允许 `n_bootstrap≠5000`，这 6 处里任何一处不改，产物就会出现「写的次数 ≠ 跑的次数」的**虚假可复现声明**；
反过来说，**只做 M1/M2（把默认值写死进产物）而不做 M3（透传）**，则 seed/n 声明与实跑恒等，风险面最小 —— 这是本班推荐排序的依据（§6）。

### B4 明确**不受影响**的（防过度施工）
- `sem.indirect_effects` 的列全等钉（`tests/test_characterization_redline_sem.py:59`、`tests/test_cfa_sem_golden.py:342`）＝另一张表，seed 三处不碰它。
- `bootstrap_ci` 的数值钉（`test_characterization_redline_sem.py:79-85` 与 `:92-98`）＝**按键取值**（`ci["β"]`／`summary["总间接效应"]`），加列/加行都**不会**让它们红；实测也无 `list(bootstrap_ci.columns) ==` 这类全等钉（`rg "columns\) =="` 20 命中里 0 枚中介表）。
- 金样件 `tests/fixtures/golden_stats/advanced/mediation_expected.json`：只含 a/b/c'/间接/总效应＋容差，**无 CI、无 seed 字段**（154316-4d99 E5 已逐字读数，本班复核文件仍在）⇒ M1/M2/M3 都不需要改它，但也**侦测不到**配置漂移。

---

## 4. 在册测试影响面（放行后该跑什么，逐条给判据）

| 档 | 测试 | 预期 | 依据 |
|---|---|---|---|
| **会红（真信号）** | 若把 `seed` 追加进 `REQUIRED_REPORT_FIELDS` 而不登记 spec | `test_report_fields_are_registered[seed]` 红 | §3-A 探针读数 `would_break_if_seed_in_report_fields=True` |
| **会红（真信号）** | 新增 spec 但 `EXACT_FIELD_SPEC`/`FIELD_SPECS` 不同步 | `test_every_mapping_points_to_a_registered_spec` 红 | `tests/test_analysis_field_lineage.py:47-52` |
| **逐字节 diff（不算红，但要留痕）** | `export_snapshot` / ZIP / `params.json` 的一切对比件 | 内容串变 | §3-B B2 |
| **静默不改判据** | `test_random_sampled_value_bearing_fields_trace_to_raw_record` | 仍绿，抽样集合漂移 | §3-A 末行 |
| **静默不改判据** | `n_bootstrap` 若被登记为 value_bearing | 仍绿但血缘错并 | `would_break_if_nbootstrap_in_report_fields=False` |

跑法口径（同仓纪律）：**只跑定向文件、不跑全量**（并发只读），且本仓**无 `--freeze`**
（`git grep -in freeze -- '*.py' | wc -l` → **0**，本班复算；等价闸是上面的硬编码全等/按键钉）。
解释器一律 `.venv/Scripts/python.exe`。

---

## 5. 迁移步骤（**材料，一步都不执行**）

> 人工闸：写库/迁移/改被跟踪文件/重钉基线都要主班＋用户放行（brief §4）。以下是放行后可照做的最小序。

**阶段 0 前置（改码前）**
1. 冻结一份对照件：`export_snapshot` 在改动前后各出一份，落 `tmp/<班名>/`（**不进 `reports/snapshots/`**），差异写进交班件。
2. 确认 `data/` 不在改动面内（`rg` 三处改动全在 `src/`），并复述"本仓 `data/` 无 git 还原点"。
3. 与 `s927-06-conclusion-gate.md` 的接线裁决对表：血缘闸**尚未接生产**，因此 seed 登记的收益是登记面的，不是阻断面的 —— 别把两件事排成同一优先级。

**阶段 1 声明面（M1＋M2，先只写不读）**
4. `advanced.py` 的 `model_summary` 增行、`bootstrap_ci` 两处 `ci_rows.append` 同步增列；
   ⚠ 命名即血缘：`seed` 走前缀/后缀规则都落不进任何 spec（§3-A），要么新建 spec（如 `S27_run_config`，`value_bearing=False`、`raw_source=R7_plan_input`），要么并入 `S10_plan_parameter` 语义。
   ⚠ **不要**用 `n_bootstrap` 作字段名进结果体（`n_` 前缀会把它并进 S6 观测样本量）。
5. 表体 dtype 护栏：`model_summary["值"]` 今天混装 float 与 str；seed 若以 int 进列，`apa_tables.py:646-653` 的 `isinstance(val, float)` 分支会把它走 `str()` ⇒ 记录渲染口径，别顺手 `_fmt_num`。

**阶段 2 登记面（与阶段 1 同一笔提交，别分两笔）**
6. `EXACT_FIELD_SPEC` 增 `seed`／`bootstrap_n`／`ci_method` 三项映射；`FIELD_SPECS` 增对应 spec 且 `extraction_anchor` 必须指向**真正产出它的函数**（`advanced.py::mediation_analysis`），以便 `test_extraction_anchor_exists_in_repo` 继续逼同源。
7. `S2_ci_endpoint` 的锚点错位单独立项：`bootstrap_ci` 现在挂 `effect_size_ci.py::fisher_z_ci`，与中介 bootstrap 无关（本单只点名，不同笔修）。

**阶段 3 计划面（M3，风险最高，最后做）**
8. `AnalysisPlan` 增字段**必须带默认值**（`src/`＋`tests/` 内 `AnalysisPlan(` 构造点 **27** 处，实测 `rg -c` 计数，不会被强制补齐）。默认值取 `None` 还是 `42`／`5000` 是**语义题**：
   `None` ⇒ 「用户未声明」与「声明为默认」可分（推荐形状，但要求 handler 在 None 时回落到函数默认，产物里 seed 显示"未声明"）；
   数值 ⇒ 产物永远有值，但会**把默认值伪装成用户选择**。⚠ 本班不代拍。
9. 同步第四处：`workspace.py:_serialize_plan`/`_deserialize_plan` 白名单 ＋ `export_snapshot` 的 `snapshot["plan"]` 四键 —— 漏一处＝持久化面静默丢 seed（§2 末）。
10. `runner._run_mediation` 调用点透传；`_run_moderation` 无 bootstrap，不涉及。
11. B3 的 6 处「5000」字面量逐处决定参数化或保留（同笔提交，否则出现虚假声明）。

**阶段 4 回归（定向，不跑全量）**
12. `tests/test_analysis_field_lineage.py`、`tests/test_characterization_redline_sem.py`、`tests/test_golden_stats.py -k Mediation`、`tests/test_robustness.py`、`tests/test_result_card*`、`tests/test_output_snapshot_roundtrip.py`；
13. 若某钉因新列变红：**按判据变化更新钉值属重钉基线＝人工闸**，执行手不得自改（本班即按此停手）。

**回滚成本**：阶段 1＋2 是**纯增行/增列**，回滚＝删两处 append 与登记项，产物侧无历史件受影响（`data/` 零触碰）。
阶段 3 触及 dataclass 与持久化白名单：回滚要把已写有新键的 `params.json`/工作区件当**在读旧件兼容**问题处理（`data.get(...)` 回落即可，不必迁移历史件）。⇒ 建议**阶段 3 单独一笔提交、单独可 revert**。

---

## 6. 推荐（交主班裁，不代拍）

**推荐序：M1 → M2 → 登记（阶段 2）→ M3，且 M1/M2 与登记必须同笔。**

- **第一档（低风险、直接闭合"seed 不进产物"）**：**只做 M1**——`model_summary` 增一行 seed。
  理由：它是**唯一一处既不改表结构、又不触碰血缘登记面**的改动（`model_summary` 今天已是不可追溯字段，加行不改变闸态），
  却把「第三方能否复跑」这个验收缺口从"零载体"变成"有载体"。产物侧只改 §3-B B2-3/5 两处的字符串。
- **第二档（结构变更，收益是机器可读）**：M2 加 `seed` 列。代价＝B1-1 的 APA 表列集变化（下游 docx/pdf 表宽、`_fmt_num` 分支要复看）。
  ⚠ **命名警告**：列名建议 `bootstrap_seed` 之外的**非 `n_` 前缀**，但无论叫什么，登记面都必须先补 spec，否则只是把不可追溯字段从 1 枚变 2 枚。
- **第三档（M3 透传）**：**排最后，且必须与"第四处"（workspace 白名单）＋ B3 六枚字面量同笔**。
  单独做 M3 而不做 8/9/11 条＝把「用户可声明」做成假接口（声明了也不进持久化，也不进正文），比现状更易误导。
- **默认推荐形状（若用户只要"报告可复跑"）**：M1 ＋ 阶段 2 登记 ＋ B3 中 `result_card.py:526`／`apa_tables.py:659`／`section_writers.py:719` 三处字面量参数化 = **四处一笔画**，
  不动 `AnalysisPlan`、不动 `bootstrap_ci` 列集 ⇒ 表结构零变化、快照键集零变化，血缘面新增 0 枚不可追溯字段。

## 7. 判断题（数值／取值题一律留人工，本班不选案）

- Q1 `AnalysisPlan.n_bootstrap/seed` 的默认值取 `None`（未声明可分）还是 `42/5000`（与函数默认同值）？
- Q2 seed 是否进 `REQUIRED_REPORT_FIELDS`？进＝`test_report_fields_are_registered` 要求它 `value_bearing=True`，但 seed 是**运行参数不是统计量**，登记为 value_bearing 是否可接受？
- Q3 新建 `S27_run_config` spec，还是把 seed 归进 `S10_plan_parameter`？（S10 的载体是 `R7_plan_input`，`raw_backable=True` ⇒ 回溯指向 `params.json` 而非被试行，语义更贴）
- Q4 `n_bootstrap` 若必须用这个名字，是否给 `PREFIX_RULES` 加一条**先于 `n_` 的显式例外**？（改前缀规则会波及全部 `n_*` 字段的判类，属登记面重钉）
- Q5 B3 的 6 枚「5000」字面量：参数化，还是在 `n_bootstrap≠5000` 时**拒绝生成**该措辞（改判据向）？

---

## 8. 证据

前置：HEAD=`6cb3c96`（`git rev-parse --short HEAD`，开工 19:42:54 至收口未变）；
`git status --porcelain | wc -l` = **14**（开工 19:42 现取；brief §5 记的 12 是主班 13:4x 读数，已漂移，按磁盘现值）。
⚠ 并发提示：班中有他方对 `data/kaoyan.db` 的活动迹象（系统侧锁通报，本班未参与），收口复点该锁已不在盘、侧车为零 ⇒ 本班与该写入无关（见 E2）。

**E1 沙盒真生效的反证（含拒跑证据）**

```
$ .venv/Scripts/python.exe tmp/qoder-executor-20260927-1945-psy80/s19_probe_lineage.py
拒跑：未设置 PSY_SANDBOX_ROOT。本探针按班次纪律只在沙盒内运行。
RC_NO_ENV=3
$ PSY_SANDBOX_ROOT=D:/code/psy-analysis/tmp/qoder-executor-20260927-1945-psy80 \
  PSY_PROBE_EMIT=.../s19_lineage.json .venv/Scripts/python.exe .../s19_probe_lineage.py
RC_WITH_ENV=0
```
→ 探针内反证三条（打印在同一 stdout）：
① `PSY_ANALYSIS_ARCHIVE_DIR` 在 **import 之前**设进沙盒 ⇒ `app_paths.ARCHIVE_ROOT` 解析为本班沙盒下的 `fake_archive`（`archive_root_inside_sandbox=True`）；
② import **之后**再改该 env（等价 `monkeypatch` 时点）⇒ `ARCHIVE_ROOT` **不变**（`archive_root_after_late_env` 仍指 `fake_archive`，不是 `late_env_should_not_matter`）—— 这就是「paths 是 import 期常量、monkeypatch 无效」的一手复算；
③ 产出物写位经 `assert str(path).startswith(sandbox)` 护栏，越出沙盒即抛。

**E2 零写库／零 data 触碰**：探针只 `print` ＋（可选）写沙盒内 `s19_lineage.json`；
夹具是 git 跟踪件 `demo_projects/psychology_questionnaire_demo/data.csv`（表头 14 列 × 30 行，探针仅 `csv.DictReader` 读一行）；
未调用 `export_snapshot`/`create_snapshot`/`archive_analysis`，未连任何 sqlite；`ls reports` → **`No such file or directory`**（本仓今天没有 `reports/snapshots/`，本班未长出它）。
`data/` 现值（收口 19:52:42 复点）：`find data -type f | wc -l` = **187**（同口径 `rg --files data/` 回 **184**，差 3 枚实测为 `feed.sqlite-shm`／`feed.sqlite-wal`／`locks/feed_fetch.lock` —— rg 吃 gitignore 侧车规则，find 不吃 ⇒ 盘上盘点一律以 find 为准），顶层只有 `benchmark_history/ kaoyan.db literature_feed/ perf_history.jsonl` 四条目；
`find data -maxdepth 1 -name '*.db*'` 只回 `data/kaoyan.db` 一枚（**无 `-wal`/`-shm`/`.lock` 侧车**）；`git check-ignore -v data/kaoyan.db` → **`.gitignore:42:data/`**（⇒ 写坏了 git 里没有还原点，本班零触碰）。
⇒ 本班"未写库"的主证是**没有 open 路径 ＋ 没有侧车长出**，不拿 size/mtime 当主证（brief §6：侧车 mtime 会被 `mode=ro` 打开刷新，是弱证）。

**E3 血缘读数原件**：`tmp/qoder-executor-20260927-1945-psy80/s19_probe_lineage.py`（探针本体）＋ 同名 `s19_stdout.txt`（完整 JSON 输出）。
关键取值：`baseline_result_body.untraceable=["model_summary"]` → `with_seed_field.untraceable=["model_summary","seed"]`；
`classify.traced.n_bootstrap = ["S6_sample_size", true, true]`；
`sampled["68"]=["n_bootstrap","result","assumptions"]`、`sampled["9"]=["n_bootstrap","ci","n_items"]`、`sampled["2026"]` 不含新字段。

**E4 三处改动面与第四处**：`advanced.py:332-366`（两处 append＋一处 model_summary）、`runner.py:844`（四实参调用点）、
`intent_resolver.py:13-46`（dataclass 尾）、`workspace.py:133-183`（手写白名单双向）、`runner.py:1049-1054`（快照 plan 只 4 键）。
`rg`：`AnalysisPlan(` 在 `src/`＋`tests/` 内 **27** 处、全仓 **30** 处（多出的 3 处在 `scripts/perf_smoke.py`）。

**E5 在册钉对照**：`rg "columns\) =="` 20 命中、0 枚中介表；`test_characterization_redline_sem.py:79-98` 为按键取值；
`tests/fixtures/golden_stats/advanced/mediation_expected.json` 全文（本班 `cat` 复算）无 seed／CI 字段，tolerance 最小 0.10。

**E6 未越界**：无 git 写操作；未碰主班独占件（`.executor.lock`/`000-QUEUE.md`/`claims.log` 仅经 `claims_writer.py`/`consumed.jsonl`/`zcode-bridge/scripts/*.py`/待人工台账）；
未删他人沙盒（`tmp/qoder-executor-20260927-1400-psy74/` 等保留件未触碰）；产物只写本文件与 `outbox/s927-19.result.md`。

## 9. 遗留问题

1. **本班作废掉的一条初读**：锚点把 `model_summary` 当作「已在血缘登记面内的表」—— 实测它在登记面**从来是零 spec**（E3），
   因此「三处改动会牵动血缘」这句话对 M1 而言是**不成立**的（闸态基线已 blocked，M1 不改变它）；真正新增血缘债的是 M2 之后的 seed 字段与 M3 的 `n_bootstrap` 前缀误并。
2. `bootstrap_ci` 的血缘锚点错位（挂 `effect_size_ci.py::fisher_z_ci`）本单只点名，建议另开登记面小单。
3. `n_bootstrap` 的 `n_` 前缀误并 S6 属**登记面结构性风险**，任何以 `n_` 命名的运行参数都会中招（同族还有 `n_iter`、`n_rep` 之类，本单未穷举）。
4. 血缘闸无生产调用点（E1 of s927-06 同证）⇒ seed 登记的收益止于登记面；是否接闸、接哪个闸属 `s927-06` 的裁决题，本单不重裁。
5. 未跑任何测试套件（只读位＋并发约束）；§4 的"会红/不会红"是**读码＋纯函数探针**推得，非实跑套件读数，主班收班时请补定向跑一次。
6. 全量套件读数缺位（并行只读约束），收班统一取数请附时刻与 HEAD。
