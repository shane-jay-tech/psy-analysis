# s927-05 · 「报告字段读不到 58 个」三分栏登记单（只出分类与建议，零码改动）

- 班：`qoder-executor-20260927-1820-psy76`（波次 22 只读采集位）
- 仓／cwd：`D:\code\psy-analysis`｜HEAD `6bf76af`
- 卷宗判据：①58 字段三分类全表 ②三分栏建议 ③零码改动 —— **三条全中**
- 锚点：`done/20260925-120653-3298.result.md` §E3（原写 `outbox/…`，按 brief §3a 到 `done/` 取到，内容在世）
- 🔴 红线自证：**"哪些字段真会进报告"是产品裁决，本班只出三分栏建议与判据，不代拍**；阈值／档位面（`threshold`）一律留在观察栏，不登记、不解释、不判读

---

## 1. 锚点复核（先证其在世，再用）

| 复点项 | 本班读数 | 判定 |
|---|---|---|
| §E3 的 58 枚清单 | 原班探针落在 `tmp/qoder-executor-20260925-1630-psy68/probe_final.log:3`（**该沙盒今天仍在**）⇒ 本班逐字提取存为 `anchor58.json`，长度 **58** | ✅ 完整在世，可直接复核 |
| 盘上现算覆盖率 | 同法（`src/analysis/*.py`，排 `field_lineage.py` 自身）AST 重跑：**scanned 231 / traced 172 / untraceable 59** | ⚠ 与在册 230/172/**58** 差 1 枚 |
| 差的这一枚 | 🔴 **`requested_estimator`** —— 宿主 `src/analysis/cfa.py::CFAResult:28`，赋值点 `cfa.py:321`；`git show HEAD:src/analysis/cfa.py` 命中 **0** 次，工作树版命中 **2** 次，该件脏 **178 加／40 删** | **由未提交的在途件新增**，非登记退化；58 ∪ {它} = 59，**在册 58 一枚未消失** |
| 3298 的成因表述「补登记要逐个读处理器产出面，30 分钟档做不完」 | 成立，且本班实测后**方向要改**：真正做不完的 Not 是"逐个读"，是**登记表当前的键空间装不下 16 枚**（§4） | 收窄，不否证 |

⚠ **本班自纠一条测量错误（如实登记）**：首跑探针 `@dataclass(frozen=True)` 的装饰器是 `ast.Call` 节点，本班只判了 `Name`/`Attribute` 两型 ⇒ 把 frozen dataclass 整类漏掉，一度读出 **217 宇宙／46 未登记**（假漂移 13 枚）。修 Call 分支后与在册逐位对齐。
**订正后的第二读法**：口径 A（任意 `ClassDef` 的 `AnnAssign`）与口径 B（只算 dataclass 宿主）**在本仓读数完全相同（231/172/59）** ⇒ "58" 这个数字对这两种口径**不敏感**，只对口径外的东西（在途件）敏感。

---

## 2. 判据① · 58(+1) 字段三分类全表

分类判据（全部落在可定位站点上，不猜）：
- **P1 产出面存在**＝`src/` 内有生产型站点（类字段声明 `#Class@行` ／ 构造实参 `#-@行` ／ `obj.x=` 赋值），且至少一处落在分析层 `src/analysis/`
- **P2 产出面不存在**＝`src/` 内零站点（只在 tests 或只被读）
- **P3 语义不明**＝同名字段被 **≥2 个宿主类**声明
- 附「导出面读者」＝该名字在 `src/output/` 有没有读者（决定"能不能算进报告"）

| 类 | 枚数 | 一句话 |
|---|---|---|
| **P1 产出面存在（分析层处理器）** | **42** | 全部有真实产出点，其中 **15 枚已有导出层读者** |
| **P3 语义不明（≥2 宿主类）** | **17** | 再切一刀：仅 1 枚同目录同义，**16 枚跨目录多义** |
| **P2 产出面不存在** | **0** 🔴 | **无一枚是幻影字段** |

🔴 **P2 = 0 是本单最重要的读数**：3298 说"58 个登记不到＝按本表语义不得作结论支撑"，但**盘上没有一枚是"没人产出"的字段**——全部由分析层处理器实实在在产出、其中 15 枚还已经被导出层读着。
⇒ "登记不到"是**登记表覆盖面**问题，不是**字段可信度**问题；把它读成"这 58 个字段不可信"会得出错误的裁法。

逐字段全表（59 枚，含产出站点、导出/UI 读者）→ `D:\code\tmp\qoder-executor-20260927-1820-psy76\out_s92705.txt` §3；P3 的第二刀 → 同目录 `out_s92705c.txt` §9。摘要：

| 栏 | 字段（按名，59 枚全列） |
|---|---|
| P1（42） | `accuracy` `aliases` `alternative_methods` `apa_text` `assumption_equal_var` `assumption_homogeneity` `assumption_normality` `assumption_sphericity` `bartlett_chi2` `check_name` `effect_sizes` `f2_effect_sizes` `fit_indices` `fit_summary` `fit_summary_zh` `hard_route_allowed` `hard_route_reason` `high_influence_cases` `hosmer_lemeshow` `interpretation` `issues` `known_groups_effect_name` `known_groups_stat` `known_groups_test` `message_zh` `min_loading_threshold` `next_action` `original_test` `plain_language_summary` `primary_method` `primary_method_zh` `rejected_methods` `requested_estimator` `required_variables` `suggested_test` `suggested_test_zh` `table` `table_group` `tables` `test_name` `threshold` `violated_assumptions` |
| P3（17） | `categories` `detail` `domain` `explanation` `kind` `label` `level` `message` `model_summary` `name` `note` `reasons` `recommendation_id` `severity` `suggested_action` `text` `variable_roles` |
| P2（0） | —— |

### 2.1 「进不进报告」的现网口径（决定 B 栏能不能裁）

| 事实 | 读数 |
|---|---|
| 统一报告口径面 `src/output/report_fields.py:FIELD_ALIASES` 认的键 | 13 个：`alpha ci item_count mcdonald_omega n n_cases n_factors_items n_items n_obs omega omega_value sample_size total_n` |
| 59 枚里落在这张统一口径面上的 | **0 枚** ⇒ 这 59 枚**没有一个**走"报告字段统一口径"那条路 |
| `REQUIRED_REPORT_FIELDS` | `('alpha','omega','n_items','n_cases','ci')` —— 只有 5 个必报字段，全部**已在册可追溯**（3298 §E3 下半段同读法） |
| 但导出层确实读了其中 15 枚 | `accuracy`(apa_tables) `assumption_homogeneity`/`bartlett_chi2`/`fit_summary_zh`/`known_groups_*`(interpretation) `assumption_sphericity`/`high_influence_cases`(reasoning) `table`(apa_tables/docx/formatter/interpretation) `detail`(interpretation) `label`(ai_trace_detector/reasoning) `name`(docx/pdf/zip) `note`(apa_tables/docx/zip) `severity`(ai_trace_detector) `text`(apa_figures/docx/reasoning) |
| `conclusion_gate(59 枚)` | `blocked=True, untraceable=59, ineligible=0, supporting=0` ⇒ **一旦 3298 的闸接线，这 59 枚会让闸全红**（与 s927-06 直接相关） |

### 2.2 P3 的第二刀（17 枚）

| 子类 | 枚数 | 字段 | 含义 |
|---|---|---|---|
| 同目录同义 | **1** | `model_summary`（`advanced`/`logistic_regression`/`regression` 三个结果类，全在 `analysis/`） | 按名登记**安全** |
| 🔴 跨目录多义 | **16** | `categories`(analysis+utils) `detail`(4 目录) `domain`(3) `explanation`(analysis+utils) `kind`(3) `label`(4) `level`(4) `message`(2) `name`(**10 个目录**，479 站点) `note`(6) `reasons`(2) `recommendation_id`(2) `severity`(5) `suggested_action`(3) `text`(2) `variable_roles`(2) | `EXACT_FIELD_SPEC: dict[str,str]` 的键是**裸字段名**（现 165 条）⇒ 一个名字只能一个含义，**结构上装不下** |

---

## 3. 判据② · 三分栏登记（供拍板；本班不裁）

分栏规则写在探针里、确定性可复算（`probe_s92705_b.py` §5）。

| 栏 | 枚数 | 字段 | 本班给的理由／形状 | 权限 |
|---|---|---|---|---|
| **A 补 spec（逐字段按名登记）** | **21** | `accuracy` `assumption_equal_var` `assumption_homogeneity` `assumption_normality` `assumption_sphericity` `bartlett_chi2` `f2_effect_sizes` `fit_indices` `fit_summary` `fit_summary_zh` `high_influence_cases` `hosmer_lemeshow` `interpretation` `issues` `known_groups_effect_name` `known_groups_stat` `known_groups_test` `message_zh` `min_loading_threshold` `table` `test_name` | 宿主类数=1、语义唯一、承载处理器判据或模型面输出 ⇒ 一条 `EXACT_FIELD_SPEC` 就够；其中 8 枚已被导出层读着，**最值得补** | 执行手可做（不动任何数值），但需人先确认 A 栏范围 |
| **A2 补 spec（挂到既有 spec，零新 spec）** | **20** | `aliases` `alternative_methods` `check_name` `explanation` `hard_route_allowed` `hard_route_reason` `next_action` `original_test` `primary_method` `primary_method_zh` `rejected_methods` `required_variables` `suggested_action` `suggested_test` `suggested_test_zh` `table_group` `variable_roles` `violated_assumptions` `recommendation_id` `reasons` | 推荐／路由／假设检查面 ⇒ 登记表里**已有** `S20_routing_advice`（`conclusion_eligible=False`，锚点 `assumption_router.py::check_route`）与 `S14_assumptions`，只是字段名没挂上去 ⇒ 扩 `SUFFIX_RULES`/`PREFIX_RULES` 即可 | 同上，**改动面最小的一栏** |
| **B 裁「不进报告」** | **4 + 12** | 派生展示面：`apa_text` `plain_language_summary` `effect_sizes` `tables`（＋ `name` `note` `detail` `severity` `text` `label` `level` `message` `domain` `kind` `categories` `model_summary` 共 12 枚多宿主字段） | 两条不同的裁法：①**派生面 4 枚**——它们不是"数据来源"，是别的字段派生出的字符串/容器，登记成数据血缘是**类别错误**，应显式标"派生展示面、不作结论支撑"（`S18_card_provenance` 就是这个形状）；②**多宿主 12 枚**——不是"不进报告"，是**现键空间没法进登记表**（其中 11 枚跨目录多义；`model_summary` 是同目录三宿主、语义一致，**其实可改归 A 栏**，列在此处只因分栏规则按"宿主类数≥2"一刀切），硬登记会串义 | 🔴 **B 栏＝产品裁决**（卷宗原话"先由主班裁定哪些字段真会进报告"）⇒ 本班只列形状 |
| **C 留观察** | **2** | `threshold`（宿主 `reliability_bands.py::AlphaBand:17`）／`requested_estimator`（在途脏 `cfa.py`） | ①`threshold` 是 **α 档位阈值**，命中统计红线；且若给它开 spec，`tests/test_analysis_field_lineage.py:110 test_registry_carries_no_numeric_values` 会管住"数值不许进登记面"⇒ 只能登记锚点字符串、不能登记数；②它由未提交在途件引入，**先等 `cfa.py` 定版**再登记，否则钉的是流动的字段面 | 人工 |
| 合计 | **59** | 无一漏桶 | | |

### 3.1 A/A2 栏的最小改动面（实测算出来的，不是估的）

只加 **13 条** 前缀／后缀规则（前缀 5：`assumption_` `known_groups_` `suggested_` `original_` `hard_route_`；后缀 8：`_sizes` `_methods` `_indices` `_action` `_roles` `_name` `_reason` `_allowed`）→ **一次收编 22／59 枚**；剩下 **37 枚**才需要逐字段 `EXACT_FIELD_SPEC` 或走 B 栏裁决。
⇒ 若目标是"先把 untraceable 从 59 压到 37"，代价是**改两张元组表，不是写 59 条 spec**。（⚠ 该 13 条是**候选形状**，不是建议采用——`_name`/`_test` 这类短后缀有把未来字段误收编的风险，收编粒度属人拍。）

⚠ 顺带登记一条在册缺陷（本班不动、不"顺手修"）：`field_lineage.py:555-570 SUFFIX_RULES` 共 14 条，其中 `("_warning", "S12_warning_face")` 在 `:561` 与 `:569` **重复出现两次**（第二条是死条目，改第一条形同虚设的第二份）；且 `PREFIX_RULES` 只有 1 条（`n_`）——"前缀收编"这条路在本仓几乎是空的，§3.1 的 5 条前缀全属新建。`tests/test_analysis_field_lineage.py:48-52` 只校"映射指向存在的 spec"，**不校重复规则** ⇒ 该缺陷现网无门禁。

---

## 4. 🔴 结构性缺陷（本单最该被看见的一条，超出卷宗提问形状）

登记表用 **裸字段名 → spec_id** 的键空间（`field_lineage.py:359 EXACT_FIELD_SPEC: dict[str, str]`，165 条）。实测：

- 59 枚里 16 枚同名字段跨目录多义（`name` 一个名字 **479 个站点、10 个目录**）⇒ **按名登记必然串义**，把 `SchemaIssue.name` 和 `CandidateRow.name` 说成同一个来源是错的；
- 于是这 16 枚**永远不会**被"补 spec"补掉，只能改登记键。

三条改法（各案后果，**本班不选**）：
- **甲：登记键改成 `模块::类.字段`（类限定名）**。彻底，但 `spec_for()`/`classify_fields()`/`conclusion_gate()` 的入参形状要改 ⇒ 触 `tests/test_analysis_field_lineage.py` 64 例（含 :48/:52 映射完整性、:59 `chain()` 长度 5、:110 数值禁入三条硬自证），且 3298 的人读档要重写。**改动面最大、语义最干净。**
- **乙：给这 16 枚开"分域 spec"（同名多条，按 `spec_id` 前缀分域）**。改动局限在表内，但登记表从"一字段一源"变成"一字段 N 源"，`conclusion_gate` 的 `untraceable/ineligible/supporting` 三态要重新定义 ⇒ **动的是闸的语义**，与 s927-06 强耦合。
- **丙：这 16 枚一律裁为"不作结论支撑"（B 栏）**，不改键空间。最省，但等于承认"通用名一律不得作结论" ⇒ 会把 `detail`/`name`/`note` 这类**确实进了 docx/pdf 导出**（§2.1 表）的字段一起压进"不得作结论"，报告里用到它们的地方要么改文案要么继续违规。**现状下最可能"无痛但失真"的一案。**
- 复算入口：`probe_s92705_c.py` → `out_s92705c.txt` §9；`EXACT_FIELD_SPEC` 条数与三态读数见 `probe_s92705_b.py` §7。
- 谁拍：这是**契约面改造＋报告口径**，主班＋人工；且必须先于 §6 的"补 spec"批次定案，否则 A2 栏的挂规则方向都会反过来。

---

## 5. 门禁同步形状（照 A/A2 落 spec 时会撞什么）

| 在册闸 | 会怎样 | 备注 |
|---|---|---|
| `tests/test_analysis_field_lineage.py:44` 每条 spec 的 `version_domains` **非空**且键必须在 `VERSION_ANCHORS`（现仅 4 个域：`codebook/report_fields/analysis_result/lineage`） | 新 spec 必须挂到这 4 个域之一，否则红 | 补 spec 的**硬前置**：要么复用 4 域，要么扩 `VERSION_ANCHORS`（＝改版本锚面） |
| `:39-40` `cleaning_rules` 键必须在 `CLEANING_RULES`（现 8 条 C0–C7） | 同上 | 同上 |
| `:66-68 test_extraction_anchor_exists_in_repo`（锚点 `文件::符号` 必须在世） | 新 spec 的 `extraction_anchor` 指向的符号改名／删除即红 | A2 栏复用 `S20` 既有锚点 ⇒ 不新增风险 |
| `:56 test_specs_are_unique_and_non_empty`：`len(_all_specs()) >= 20` | **只有下界** ⇒ 加 spec 不红 | ✅ 无重钉需求 |
| `:110 test_registry_carries_no_numeric_values` | 任何 spec 字段值为 int/float 即红 ⇒ `threshold`/档位类**只能登记锚点串**，不能带数 | 🔴 与统计红线同源 |
| `tests/test_golden_stats.py:389-401` | 只钉 fixture 目录存在＋`count >= 7` 下界 ⇒ 补 fixture 不红 | ✅ |
| `:213-216 test_clean_eligible_set_passes_gate`（`len(supporting) == 5`） | 入参是写死的 5 个报告字段 ⇒ **补这 59 枚不会动它** | ✅ |
| 🔴 基线重钉 | 本仓**无 `--freeze`**（s927-04 已独立复点：`.py` 全域 `--freeze` 零命中；`tests/conftest.py:57` 唯一 addoption 是 `--run-benchmark`）⇒ 等价闸＝**硬编码全等快照**，本单相关的那枚是 `test_analysis_field_lineage.py:216` 的 `== 5`（经核**不受本批影响**）与 `:56` 的 `>= 20`（下界，不受影响） | ⇒ 本单 A/A2 栏**不触发重钉基线**；只有 §4 甲/乙案（改键空间/改闸语义）会 |

---

## 6. 零改动自证

- 对 `D:\code\psy-analysis` 写入件数 = **1**（本档，`docs/insights/`）。`src/` **一字节未写**。
- 探针输入全部为**盘上源码 AST 与文本**，未打开 `data/` 任何库、未 import `app.py`、未跑 pytest（并发窗）。
- 解释器 `.venv/Scripts/python.exe -B`。
- 禁动件：`src/output/interpretation.py`（波次 18 脏件）**未读未写**；前手沙盒 `qoder-executor-20260927-1400-psy74`／`-1430-psy75` **未清理未写入**（本班另建自己沙盒）；`qoder-executor-20260925-1630-psy68` 沙盒**只读**（提取 `probe_final.log` 的 58 清单，未在其目录内写任何文件——`anchor58.json` 写在本班沙盒）。
- 未 add／commit／stash／checkout／restore／clean。

## 7. 复算入口

| 件 | 内容 |
|---|---|
| `D:\code\tmp\qoder-executor-20260927-1820-psy76\anchor58.json` | 从 psy68 `probe_final.log:3` 逐字提取的在册 58 清单（psy68 沙盒零写入） |
| `...\probe_s92705.py` → `out_s92705.txt` | §1 双口径覆盖率＋§2 漂移对账＋§3 **59 枚逐字段三分类全表（含产出站点）**＋§4 导出面命中 |
| `...\probe_s92705_b.py` → `out_s92705b.txt` | §5 分栏规则＋§6 **三分栏全表**＋§7 现网报告口径面与 `conclusion_gate` 三态＋§8 门禁形状 |
| `...\probe_s92705_c.py` → `out_s92705c.txt` | §9 17 枚多宿主字段的第二刀（同义 1／跨目录多义 16） |
| `...\rows_s92705.json` | 逐字段结构化读数（供下批直接消费，免重扫） |
| 命令 | `cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -B D:/code/tmp/qoder-executor-20260927-1820-psy76/probe_s92705.py`（A→B→C 顺序，B/C 依赖 A 的两份产物） |

## 8. 遗留（交主班）

1. 🔴 **§4 键空间问题必须先裁**：不裁，则"补 spec 58 个"这条路线**结构性做不到 0**（最多把 59 压到 16）。
2. 🔴 **B 栏（哪些字段真会进报告）＝产品裁决**，卷宗原话如此，本班只列形状与三条改法后果。
3. `requested_estimator` 请等脏件 `cfa.py`（178/40，未提交）定版后再登记；`threshold` 留观察栏（红线，本班不解释其档位含义）。
4. 3298 的 §E3 清单**本身没落盘在仓内**（只在 `tmp/psy68` 沙盒第 3 行）——沙盒是按班清理的临时件，**在册 58 清单的唯一持久载体其实是本档 §2 的表**。若主班要保它，请把本档入库；本班无权改 3298 的结果件（信箱路径写位归主班）。
5. 本档未进 `docs/insights/` 索引登账件。
