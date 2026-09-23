# psy 交付入口矩阵 M1 / P5 施工方案稿（on_export 零调用）· 2026-09-23

> 班：`qoder-executor-20260923-0022-psy16` ｜ 单：`s923-35` ｜ 性质：**只读施工方案**，`src/` 与 `.gitignore` **零改动**。
> 上游：`docs/insights/psy-delivery-entry-matrix-20260922.md`（s922-126 矩阵，M1–M6 / P1–P5 在此定名）＋ `docs/insights/psy-userhome-archive-census-20260922.md`（s922-128 落盘面簿，§3 已有 `reports/snapshots/` 一行）。
> 三案共同的定性：**都是"门禁/落盘/审计"三条声称与磁盘实况不符**的收口，不是新功能。

## 0. 一句话现状（三案各一条，全部本班现跑）

| 案 | 声称 | 实测 |
|---|---|---|
| **M1** | "导出命名有全局门禁守护" | 守护件 `tests/test_export_naming_global.py` **3 passed**，但它按行文本扫 `file_name="字面量"`、只走 `src/ui/*.py`（非递归）⇒ **真 AST 面 38 站点里 30 个非合规它一个都看不见**（探针复算见 §1.2） |
| **P5** | "交付入口都是浏览器下载、服务端零写入" | 半真：`export_snapshot` 的默认分支写 **CWD 相对** `reports/snapshots/`（`src/analysis/runner.py:1078-1080`），`reports/` **不在** `.gitignore`（全文 45 行无该条目），目录当前不存在 ⇒ 风险是**潜伏**而非已发生；同类 CWD 相对写根实测 **12 处**（§2.2） |
| **on_export** | "导出有审计痕迹" | **全仓无产者**：`on_export` 只有定义与一处 import（零调用），且没有任何旁路在写 `export` 事件 ⇒ 不是"接线漏了一处"，是"这条声称从未成立" |

---

## 1. M1：命名门禁扫描器改法

### 1.1 现状与"结构上不可能失败"的四个成因

被检件：`tests/test_export_naming_global.py`（3 例：`test_all_ui_files_parseable` / `test_download_buttons_use_export_filename` / `test_export_filename_handles_edge_cases`）。核心循环在 `:65-92`。

```
$ .venv/Scripts/python.exe -m pytest tests/test_export_naming_global.py -q
...                                                                      [100%]
3 passed in 1.30s
```

| 成因 | 落点 | 后果 |
|---|---|---|
| **D1 扫描根用 `UI_DIR.glob("*.py")`（非递归）** | `:57`、`:65` | `src/ui/` 的子目录（现 2 件）永不入眼；`src/output/`、`src/literature_feed/ui/` 整片不在范围内 |
| **D2 `app.py` 不在扫描根** | `:13`（`UI_DIR = src/ui`） | `app.py` 4 个 `download_button` 站点全盲（实测 `app.py:355/:2255/:2267/:2294` 均为 f-string 命名） |
| **D3 判据是"行文本"不是 AST** | `:69-77`（`"download_button" in line` ＋ `file_name` 同行或次行）＋ `:88`（只认 `file_name\s*=\s*["']…["']`） | **位置参数形态**（`deliverable_center_panel` 5 站点是第 3 位置参数，s922-126 已注明）与 **f-string 命名**（16 站点）在 `m is None` 处静默放过 ⇒ 唯一会红的只有"同行裸引号字面量"这一窄面 |
| **D4 豁免过宽** | `:84`（`"session_state" in line and "get" in line` 即放行） | `CALL_OTHER:get` 2 站点（`experiment_design_ui.py:404`、`undergrad_wizard.py:853`）靠这行免检；与 D3 叠加后「examined 0」 |

### 1.2 存量债（本班 AST 探针实测；M1 收紧后会一次性变红的就是这一张表）

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/s923-35/naming_gate_probe.py
SCANNED_FILES_WITH_BUTTONS 14
TOTAL_DOWNLOAD_BUTTON_SITES 38
  FSTRING                16
  LITERAL                9
  CALL:_efn              5
  CALL_OTHER:get         2
  CALL_OTHER:_safe_filename 2
  CALL:export_filename   2
  NAME_OR_ATTR           1
  NO_FILE_NAME_AT_ALL    1
COMPLIANT 7 NON_COMPLIANT 30
```

明细（30 处，逐条带 `file:line`，留存 `tmp/s923-35/naming_gate_probe.out`）：`app.py` 4（全 FSTRING）· `deliverable_center_panel.py` 5（4 FSTRING＋1 LITERAL，**都是 positional#3**）· `evidence_table_panel.py` 4（全 LITERAL positional#3）· `questionnaire_panel.py` 3（全 FSTRING）· `undergrad_wizard.py` 5（`NO_FILE_NAME_AT_ALL:69`／FSTRING:625／get:853／LITERAL:2398、:2410）· `items_upload_panel.py` 2（`_safe_filename`）· `paper_preview_panel.py` 2 · `result_card_panel.py` 2 · `experiment_design_ui.py:404` · `renderers.py:661` · `app_pages_text.py:154` · `questionnaire_import_panel.py:192`。

**与 s922-126 的对账（一次同时钉住两件事）**：该档记「35 站点 = 7 合规 ＋ 23 硬编码（LITERAL 9＋FSTRING 13＋EXPR 1）」。本班探针在同口径下得 38 站点 = 7 合规 ＋ 26 硬编码（LITERAL **9** 一致／FSTRING **16**＝13＋3／EXPR 1 一致）＋ 4 处"另有清洗器但非 `export_filename`"＋ 1 处无名可取 ⇒ **总数 +3 与硬编码 +3 全部来自 `src/ui/questionnaire_panel.py`**，即 §十五 那笔（主班 `f8ca14e`，s922-138/139/140）。**LITERAL 9 逐位复现＝两班探针同型可比**，不是各说各话。

### 1.3 施工步骤（两步走，禁止一步"修扫描器＋改 30 站点"）

1. **S1 只修扫描器、不判红**：把 `_find_download_buttons` 与 `test_download_buttons_use_export_filename` 换成 **AST 版**——递归 `rglob("*.py")`、扫描根 = `src/` ＋ `app.py`、`file_name` 取 **keyword 或第 3 位置参数**、分类为 `{CALL:export_filename|_efn} / 其它表达式 / 字面量 / 缺名`。此笔**只加一条"计数可见"断言**（`assert examined >= 30`，防"examined 0"复发），**先不加严判定**。
2. **S2 存量显式入表**：给 26/30 处一个**带理由的账**，形制照同仓已有的三表制 `tests/test_export_gate_global_scan.py:18-38`（`WHITELIST_EXPORTS` / `GATED_EXPORTS` / `NEEDS_MIGRATION`）。🔴 注意该件的 `NEEDS_MIGRATION` **有"必须为空"断言＝不是收容所**（台账 81 同族教训），M1 若要建表，**必须另建一张显式带理由的债务表**，别把 30 条塞进现有白名单。
3. **S3 逐面迁移**（可分多笔）：优先级＝用户可感知最强者先，即 `app.py:355/:2255/:2267/:2294`（主分析页四出口）→ `deliverable_center_panel` 五出口（正式交付面）→ 中间产物类（`renderers`/`evidence_table`/`result_card`）。
4. **S4 清洗器收口**（与 S3 同笔，见风险 R3）：现 **4 套命名实现并存**——`src/utils/export_naming.py:11 export_filename`（统一 `{项目名}_{模块}_{日期}.{ext}`＋`_sanitize` 截 30 字）· `src/ui/items_upload_panel.py:375 _safe_filename` · `src/ui/app_pages_text.py:153` 内联字符白名单串（`isalnum() or "._-（）()"`，截 20）· `deliverable_center_panel.py` 的裸 f-string。M1 的"统一命名"若不点名这四处，扫描器绿了也是假绿。

### 1.4 受影响测试名单（改到哪一步要跑哪一族）

- `tests/test_export_naming_global.py`（3 例）——S1 直接重写对象。
- `tests/test_export_gate_global_scan.py`（11 例，现 **1 failed**＝在册红 `test_all_download_buttons_accounted_for`，缺账文件 `src/ui/questionnaire_panel.py`，台账 81）——同仓"全局账本门"的形制模板；🔴 **M1 不得顺手消这 1 红**（加白名单＝替隐私分类签字，挂 NEEDS_MIGRATION＝绕"必须为空"断言）。
- 全仓 `export_filename` 的**唯一**测试引用就是 `test_export_naming_global.py`（`rg -l 'export_filename|export_naming' tests/` → 1 件）⇒ M1 的回归面**窄**，但也意味着 `export_filename` 本身除 3 例外无守卫（中文/特殊字符/空标题那例在 `:99-115`）。
- S3 若改到 `deliverable_center_panel.py` / `undergrad_wizard.py` / `paper_preview_panel.py`，按纪律档 §十五 加跑 `pytest tests -q -k "download_buttons or export_gate"`。

### 1.5 风险

- **R1（最高）"扫描器一修好就 30 红"**：这会让"零新增红"验收当场不可满足。⇒ S1 与 S2 **必须同笔或 S2 先行**；且**改计数口径**（新增 30 例债务）属纪律档 §五-4 的停手项，需主班拍板债务表形制。
- **R2 白名单＝签字权**：给某个 `file_name` 写"这条不需要统一命名"的理由，实质是替产品与隐私口径背书（colony 静默消毒器先例，台账 153 同型）。执行班只出候选清单与理由草案，**不签**。
- **R3 迁移会改用户可见文件名**：`export_filename` 会**加日期、加项目名、截断 30 字符**（`export_naming.py:22-26`），而现状 26 处里含 `作业包_{name}_{now}.zip` 这类**已自带日期**的串 ⇒ 直接换函数会得到"双日期""项目名重复"的新文件名。⇒ 这不是纯重构，是**行为改动**，S3 每一笔要带"改前/改后文件名逐字对照"。
- **R4 `NO_FILE_NAME_AT_ALL:1`（`undergrad_wizard.py:69`）**：该行 `download_button` 连 `file_name` 都没有 ⇒ 浏览器落地名由 Streamlit 默认值决定。S1 之后它属于"缺名"类，要单独定性（是缺陷还是有意）。

---

## 2. P5：`reports/` 落盘根迁移到 `app_paths`

### 2.1 现状（全部现跑，目录与忽略态是本案关键）

```
$ grep -n "snap_dir" src/analysis/runner.py
1078:        snap_dir = Path("reports/snapshots")
1079:        snap_dir.mkdir(parents=True, exist_ok=True)

$ rg -n "export_snapshot" src/ app.py tests/
src/analysis/runner.py:1028:def export_snapshot(output: Dict[str, Any], file_path: str = None) -> str:
src/analysis/runner.py:1078:        snap_dir = Path("reports/snapshots")
app.py:1503:                    from src.analysis.runner import export_snapshot
app.py:1504:                    snap_path = export_snapshot(output)
src/ui/undergrad_wizard.py:3201:                    from src.analysis.runner import export_snapshot
src/ui/undergrad_wizard.py:3202:                    snap_path = export_snapshot(output)

$ git check-ignore -v reports feedback_package logs data
reports           （rc=1 未忽略）
feedback_package  （rc=1 未忽略）
logs              .gitignore:16:logs/
data              .gitignore:42:data/
```

四条要点：① 生产**两个调用点都不传 `file_path`** ⇒ 必走 CWD 相对默认分支；② 两处都包在 `try/except Exception → st.error("快照保存失败…")`（`app.py:1509-1510`、`undergrad_wizard.py:3204-3205`）⇒ **写坏/写偏是静默降级**，用户只看到一行红字；③ `tests/` 对 `export_snapshot` **零引用** ⇒ 默认分支**零测试覆盖**（与 §1.4 的"窄回归面＋零守卫"同型）；④ 仓根当前无 `reports/`（`ls reports` → No such file）⇒ **s922-128 的"从未写"仍成立**，P5 是排雷不是救灾。

### 2.2 🔴 同类面普查（新，别只改一处）

按"字面相对路径构造"扫 `src/**/*.py` ＋ `app.py`，得 **12 处 CWD 相对写根**：

| # | 落点 | 目标目录 | 是否被 gitignore |
|---|---|---|---|
| 1 | `src/analysis/runner.py:1078` | `reports/snapshots/` | ❌ 未忽略（本案） |
| 2 | `src/utils/usage_logger.py:192` | `feedback_package/` | ❌ 未忽略（**同罪，本案应并案**） |
| 3 | `src/utils/app_paths.py:27` | `LOG_DIR = Path("logs")` | ✅ `.gitignore:16` |
| 4 | `src/utils/usage_logger.py:33` | `logs`（`_log_dir()` 兜底） | ✅ |
| 5-9 | `src/utils/cache_manager.py:39-43` | `data/temp_figures`／`pdf_temp`／`zip_cache`／`feedback_logs`／`data` | ✅ `.gitignore:42` |
| 10 | `src/utils/feedback_logger.py:23` | `data/feedback_logs` | ✅ |
| 11 | `src/utils/perf_logger.py:18` | `data/perf_log.jsonl` | ✅ |
| 12 | `src/experiment_design/psychopy_generator.py:469` | 生成到**产出的脚本里**的 `Path('{exp.data_dir}')` | 不适用（模板串） |

（另有 `app.py:634` 把 `Path(".")` 当 `run_full_diagnosis(project_root=…)` 实参——那是**读**侧 CWD 依赖，属 `4b0d667` 修过的诊断族，不在本案。）

⇒ **P5 的真实范围是"未忽略的那两处"（#1 #2），不是"runner 一处"**；已被 gitignore 遮蔽的 9 处虽然脏树看不见，但**换 CWD 启动就散落到别处**，属同根病、可另单。

### 2.3 施工步骤（照仓内现成三级解析，勿另发明）

1. **T0 先拍板落点语义**（见风险 R1，这是本案唯一的"需裁决"）：快照该落
   (a) `APP_HOME`（`~/.psy_analysis`，与用户数据同根，跨 CWD 稳定，便携部署友好），还是
   (b) `REPOSITORY_ROOT / "reports"`（与 `archive/` 同根，历史读数位置不变）。
   s922-126 §P5 已写明「**是否把快照收进 `APP_HOME` 需拍板**（涉及历史数据位置，不能由执行班挪）」。
2. **T1 在 `src/utils/app_paths.py` 增常量**：`REPORTS_DIR` / `SNAPSHOT_DIR = REPORTS_DIR / "snapshots"`，**默认值按 T0 结论**。⚠️ `app_paths.py:24` 有一条在册注释「这两项历史上位于仓库/当前工作目录，**默认值不可改变**；仅允许显式重定向」⇒ 若 T0 选 (a)/(b) 任一"改默认"方案，**必须同笔改这条注释**，否则注释与代码互相打脸（三处一体：常量＋注释＋调用侧）。
3. **T2 解析口照 `usage_logger._log_dir()` 的三级式**（`src/utils/usage_logger.py:29-38`，仓内**已入库的正解样板**）：显式打桩 > 环境变量（新名建议 `PSY_ANALYSIS_REPORTS_DIR`）> `app_paths` 默认，且**调用期**解析、不在模块顶部一次性绑定。该函数自己的 docstring 就记着这个教训：「早先是模块顶部 `_LOG_DIR = LOG_DIR` 一次性绑定——`.env`/测试在 import 之后才设环境变量就不认了」。
4. **T3 改 `runner.export_snapshot`**：`:1078` 的 `Path("reports/snapshots")` 换成 T1/T2 的解析口；`mkdir` 保持 `parents=True, exist_ok=True`；🔴 顺手把 `app.py:1509-1510`／`undergrad_wizard.py:3204-3205` 的 `except Exception` 收窄成 `except OSError` 并把路径写进 `st.error`（否则新缺陷继续静默）。**这一条属生产码行为改动，可拆独立一笔。**
5. **T4 `.gitignore` 追加 `reports/` 与 `feedback_package/`**：🔴 **只能追加在 EOF**（纪律档 §十四：多份入库文档按行号锚 `.gitignore:16/:29/:41/:42`，插中段会集体失真；现全文 45 行）。⚠️ 顺序要想清：若 T1 已把落点挪出仓根，加 `reports/` 是**兜底**（防回退或旧 CWD 启动）；若决定不迁移，加忽略＝**把脏目录永久藏起来**，是更坏的选择 ⇒ **别单独走 T4**。
6. **T5 补契约测试**（本案唯一"必须新增测试"的点）：
   - 默认分支落点可被环境变量重定向（新 `PSY_ANALYSIS_REPORTS_DIR` 生效、无需重导入）；
   - **`tests/test_app_paths.py:5-17` 同族**的"默认值不许被带跑"例（照 `tests/test_usage_hooks.py:193-199` 那句断言的形状）；
   - "跑一次 export_snapshot 不新增任何仓根未忽略目录"的自证（`tmp_path` 起沙盒）。
7. **T6 文档同批**：`docs/insights/psy-delivery-entry-matrix-20260922.md:109`（P5 行）、`psy-userhome-archive-census-20260922.md:53`（面簿行）要随迁改口径，否则"落盘根三岔"的在册描述失真。

### 2.4 受影响测试名单

- `tests/test_app_paths.py`（路径等值与 `_configured_path` 覆盖，5 例族）——T1 加常量即触面。
- `tests/test_usage_hooks.py:190-200`（`_log_dir()` 优先级三例：显式桩 > env > 默认）——T2 若偏离这个形状，会被这三例的**同族新增例**打回；也是本案的**规格来源**。
- `tests/test_privacy_archive_usage.py:231-242`（`export_feedback_package(tmp_path/…)` 显式目录；默认分支未测）——并案 #2 时改这里。
- `tests/conftest.py:41-52`（`isolate_streamlit_app_test_storage` 给 `PSY_ANALYSIS_*` 与 `ARCHIVE_ROOT`/`_LOG_DIR` 打桩）⇒ **新增的 REPORTS 覆盖点要一并进这个夹具**，否则 `AppTest` 类测试一旦点"保存快照"就会往真仓根写（🔴 且属 §廿一 文献库沙盒之外**另一个**真写面）。
- `tests/test_output_snapshot_roundtrip.py`（`src/output/snapshot.py:create_snapshot` 的往返件）——**同名不同物**，本案不动它，但引用"快照"二字时要点名区分（§2.5 R4）。
- 若 T3 收窄了 `except Exception`，`pytest tests -q -k "snapshot"` ＋ §十五 的导出门禁族一并跑。

### 2.5 风险

- **R1（唯一需裁决）"改默认值 vs 注释/历史位置"**：`app_paths.py:24` 明写默认不可变；而**不改默认就治不了"仓根冒未忽略目录"**。二者只能选一，且涉及"用户已有快照文件的位置"⇒ 执行班不得自行选。附带一个不显眼的口径分裂：若落点改成 `APP_HOME`，`data/benchmark_history`、`archive/` 仍在仓根 ⇒ "三个根"变"四个根"，**除非同批改 ARCHIVE_ROOT**。
- **R2 静默降级会掩盖迁移失败**：现状两处 `except Exception` 让"写不进去"变成一行红字，迁移期新路径不可写（只读盘、便携目录、OneDrive 同步盘）时会**看着像老毛病**。T3 的收窄建议是为这个服务的。
- **R3 便携部署语义**：`app_paths` 的立模块初衷就是"测试、便携部署或受管环境可重定向"（`:3-4`）⇒ 新常量必须走 `_configured_path`，别新开一套 `os.environ` 读法。
- **R4 同名快照三处**：`runner.export_snapshot`（JSON，落盘）／`src/output/snapshot.create_snapshot`（ZIP，**生产零调用**、只回 bytes）／`project_panel.py` 的"项目快照导出"（在 §1 门禁白名单里）。写方案或改码前先点名是哪一个。

---

## 3. on_export 接线点清单

### 3.1 零调用与"无旁路"的双重证据

```
$ rg -n "on_export" src/ app.py
app.py:57:    on_privacy_precheck, on_export, on_error_display, on_diagnosis_run,
src/utils/usage_hooks.py:62:def on_export(format: str, success: bool, duration_ms: int):

$ rg -n 'log_event\("export' src/ app.py
src/utils/usage_hooks.py:64:    log_event("export", format=format, success=success, duration_ms=duration_ms)
```

⇒ `app.py:57` 只 import 不调（`from src.utils.usage_hooks import …`），全仓**唯一**产出 `export` 事件的地方就是钩子自己 ⇒ s922-126 的"导出有审计痕迹不成立"**不是接线遗漏，是这条声称从未落地**。姊妹面 `on_privacy_precheck` 反倒是**接了但接错位置**（`app.py:2371` 埋在被展示的那次页级扫描上，s922-126 已记）。

其余钩子的实际接线率（本班全量普查，`rg -o 'on_(…)\(' app.py src/ --glob '!src/utils/usage_hooks.py'`）：`usage_hooks.py` 共 **13 个 `on_*` 定义**（`:12/:17/:22/:27/:32/:37/:42/:47/:52/:57/:62/:67/:72`），生产侧调用点只有 **6 处、去重 5 个钩子**——`app.py:310 on_page_visit`、`:834 on_data_upload`、`:839`＋`:2403 on_error_display`、`:637 on_diagnosis_run`、`:2371 on_privacy_precheck`；第 6 个在产钩子是**间接**的：`app.py:1125 with AnalysisTimer(plan.test_type)` → `usage_hooks.py:91 on_analysis_execute`。

⇒ **7 个钩子零调用**：`on_export`、`on_template_select`、`on_next_step_show`、`on_next_step_click`、`on_method_recommend`、`on_table_generate`、`on_consistency_check`。其中 `on_next_step_show/on_next_step_click` 与 `on_template_select` **已在 `app.py:57-58` 被 import 却零调用**（死 import），且这两枚"下一步推荐"钩子的失配与 `74e0717` 登记的在册缺陷同源（推荐引擎的两枚 `session_state` 键全仓零写方，台账 156——**本班不动、不"顺手修好"**）。`on_export` 属同一死码族（与 `src/output/snapshot.py:create_snapshot` 生产零调用同型）。

### 3.2 该埋的位置（推荐 3 点，不推荐 38 点）

`on_export(format, success, duration_ms)` 的三字段要求"知道结果与耗时"，而浏览器下载（`st.download_button`）**服务端不知道用户是否真的点了保存** ⇒ 38 个 `download_button` 站点逐个埋**必然产出假 `success=True`**。所以：

| 优先级 | 位置 | 理由 | 需要的改动形状 |
|---|---|---|---|
| **P0** | `src/ui/renderers.py:675 export_html` ／ `:701 export_csv` | 真在服务端生成字节的两处；`app.py:1496/:1499`、`undergrad_wizard.py:3194/:3197` 共 4 个调用点自动覆盖 | 函数首尾包计时＋try/except（成功/异常各一次 `on_export`） |
| **P0** | `src/analysis/runner.py:1028 export_snapshot` | 唯一真写盘出口；覆盖 `app.py:1504`、`undergrad_wizard.py:3202`；`format="json"` | 同上，且与 P5 的 T3 **同一笔**做（同函数） |
| **P1** | 交付中心／作业包 zip 生成点（`deliverable_center_panel.py:207-264` 5 出口、`app_pages_text.py:154` 作业包） | 正式交付面，审计价值最高；`format` 逐出口取 `md/docx/pdf/zip` | 在生成 bytes 处埋，**不在按钮处埋** |
| **P2（不建议）** | 38 个 `st.download_button` 站点 | 只能记"渲染了几次出口"，语义上等于新增一个 `export_offered` 事件而非 `export` | 若真要，先改名再埋，别占用 `success` 字段 |

复用形状（仓内已有，别另发明）：`src/utils/usage_hooks.py:84-93 class AnalysisTimer` 就是"计时＋成功位＋裸调用"的现成模式 ⇒ 建议加一个同型 `ExportTimer(fmt)`，`__exit__` 里 `on_export(fmt, exc_type is None, ms)`。

### 3.3 接线不破什么、会破什么

- **不破**在册特征化测试：`tests/test_usage_hooks.py:89` 用 `uh.on_export("docx", True, 120)` 当"钩子层不吞异常"的载体（`test_hooks_do_not_swallow_exceptions_themselves`，`log_event` 已打桩）⇒ 接线不动钩子本体，该例恒绿。
- 会新增**写盘面**：`log_event` 落 `usage_events_YYYYMMDD.jsonl` 于 `_log_dir()`（默认 `app_paths.LOG_DIR = Path("logs")`，被 `.gitignore:16` 遮蔽）。写失败 `except OSError: pass` **静默丢弃**（`usage_logger.py:93-95`）⇒ 🔴 **"导出有审计痕迹"这条永远不能当合规证据**，只能当产品分析用。
- 🔴 **红线（本班不越）**：`on_export` 的字段是 `format/success/duration_ms`，而 `usage_logger` 模块级承诺「不得包含原始数据或敏感信息」（`:78` 注释）。接线时**顺手加 `filename=` / `title=` / `project=` 就是把用户文档标题写进遥测**——属隐私分级域，需人工签。本清单只给三字段口径的位置，不给扩字段方案。

---

## 4. 本单自证（零改动）

```
$ git diff --numstat src/ .gitignore        ← 无输出（生产码与 .gitignore 零改动）
$ git status --porcelain src/ .gitignore    ← 无输出
$ rg -n "on_export" src/ app.py             ← 2 命中（import 与 def），已内联 §3.1
```

- 探针留存（`tmp/` 被 `.gitignore:29` 覆盖，不进 git）：`tmp/s923-35/naming_gate_probe.py`、`tmp/s923-35/naming_gate_probe.out`。
- 未启动 app、未跑 `AppTest` ⇒ 未建文献库沙盒副本；开工／收工各取一次 `data/literature_feed` 三件 sha256 前 8 位自证未变（读数见结果件）。
- `locks/feed_fetch.lock` 未碰。

## 5. 需主班裁决（三案各一条，按急度排）

1. **P5-T0 落点语义**（`APP_HOME` vs `REPOSITORY_ROOT/reports` vs 只加 env 覆盖不动默认）——牵动 `app_paths.py:24` 注释与"三根/四根"分裂，**涉历史数据位置**，执行班不得自行选。
2. **M1-S1/S2 的债务表形制**（30 条存量走"另建带理由债务表"还是"扩现有 WHITELIST 并逐条签字"）——后者等于让执行班替命名与隐私口径背书，**本班拒绝**。
3. **on_export 是否要接**（P0 三点）＋**是否允许扩字段**（当前只许三字段）——不接就请把"导出有审计痕迹"这条声称从 KNOWN_ISSUES／交付文案里删掉，两案都比"埋个假 success"诚实。
