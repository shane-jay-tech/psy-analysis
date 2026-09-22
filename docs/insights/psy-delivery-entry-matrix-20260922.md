# psy 交付入口三形态语义对账矩阵（s922-126，2026-09-22，只读）

> 班：`qoder-executor-20260922-0000-psy13`｜仓：`D:/code/psy-analysis`｜基线 HEAD `7f97243`
> 性质：P2 只读对账。**零生产码改动**、`data/` 未写、`git status` 收班仍 10 项。
> 所有 `file:line` 均为本班实测（工具：`rg` / `ast.parse` / `sed -n`），探针脚本见 §7。

---

## 0. 任务书锚点复核（先证伪）

| 任务书锚点 | 实测 | 结论 |
|---|---|---|
| `KNOWN_ISSUES.md:104`「\| P2 \| 交付入口收敛 \| …」 | `rg -n '交付入口收敛' KNOWN_ISSUES.md` → **104** | ✅ 未漂移 |
| `src/ui/export_gate.py:54` `def run_export_gate(...)` | `rg -n` → **54** | ✅ 未漂移 |
| `app.py:1700` `_build_homework_package(output, df, ...)` | 实测在 **`app.py:1517`**；`app.py:1700` 现内容是问卷设计异步回调的 `except CancelledLLMError` 分支（`sed -n '1690,1712p'`） | ❌ **漂移 −183 行**，按磁盘实况修正 |

补充：任务书说「三入口」，`rg -n '_build_homework_package|run_export_gate' app.py src/` 的**全部**命中（10 行）指向的实际可达出口不止 3 个——门禁被 4 处复用、作业包 1 处、另有一族"分析页直出"按钮**根本不进门禁**。§1 逐点入表，矩阵按 4 列展开（含任务书点名的三列）。

---

## 1. 调用点全量入表（完成标准 2：`rg -n '_build_homework_package|run_export_gate' app.py src/` 全命中）

| # | 命中位置 | 性质 | 归属入口 |
|---|---|---|---|
| 1 | `app.py:82` `    _build_homework_package,` | import（自 `src/ui/app_pages_text.py`） | B 作业包 |
| 2 | `app.py:1517` `_build_homework_package(output, df, st.session_state.get("archive_tag", ""))` | 唯一调用点 | B 作业包 |
| 3 | `src/ui/export_gate.py:54` `def run_export_gate(session_state)` | 定义 | — |
| 4 | `src/ui/export_gate.py:113` `allowed, reasons, issues = run_export_gate(session_state)` | `render_export_gate` 内部唯一调用（定义 `export_gate.py:105`） | C 草稿 |
| 5 | `src/ui/deliverable_center_panel.py:14` `from src.ui.export_gate import run_export_gate` | import | A 正式交付 |
| 6 | `src/ui/deliverable_center_panel.py:170` `gate_result = run_export_gate(session_state)` | 「导出前检查」tab — **仅展示，不 return**（`:172-175` 后函数即结束） | A 展示位 |
| 7 | `src/ui/deliverable_center_panel.py:182` `gate_allowed, gate_reasons, _ = run_export_gate(session_state)` | 「导出」tab — **真阻断**（`:187 return`） | A 硬门禁 |
| 8 | `src/ui/app_pages_text.py:4` 注释、`:94` `def _build_homework_package(output, df, tag="")` | 定义＋迁移说明 | B 作业包 |
| 9 | `src/ui/undergrad_wizard.py:53` `from src.ui.export_gate import run_export_gate` | import | D 向导正式出口 |
| 10 | `src/ui/undergrad_wizard.py:63` `allowed, gate_reasons, _ = run_export_gate(st.session_state)` | `_render_official_download`（定义 `:56`）— 门禁失败**清除产物**（`:66 st.session_state.pop`）且不渲染按钮 | D 硬门禁 |

`render_export_gate`（`export_gate.py:105`）的上游只有 **1 个**：`app.py:2323` import → `app.py:2329` 调用 → 通过才 `app.py:2330 render_export_panel(_bundle)`。
`_render_official_download` 的调用点 **4 个**：`undergrad_wizard.py:455`（论文交付包 ZIP）／`:777`（图表集 ZIP）／`:1538`（Word）／`:1658`（图表 ZIP）。

---

## 2. 入口 × 维度矩阵（完成标准 1：≥3 入口 × ≥5 维度，每格实测锚）

图例：✅ 有／⚠️ 形式上有但不阻断／❌ 无。

| 维度 | **A 正式交付**<br>「📦 交付包导出」模式 | **B 作业包**<br>「📈 数据分析」结果页按钮 | **C 草稿导出**<br>「📝 论文写作 → 预览与导出」 | **D 向导正式出口**<br>本科论文向导（参考列） |
|---|---|---|---|---|
| **1 触发点（页面/按钮）** | 模式分派 `app.py:2353`；面板 `app.py:2390`→`deliverable_center_panel.py:32`；tab3 按钮 `deliverable_center_panel.py:204` `st.button("📥 生成{mode_label}交付包")`；格式四选一 `:202` | `app.py:1511` `st.button("📦 导出作业包", type="primary")`；同排还有 `:1490` HTML／`:1498` CSV／`:1501` 快照 | `app.py:2317` tab「📄 预览与导出」→ `app.py:2330 render_export_panel`；定义 `paper_preview_panel.py:97`；两个 `st.download_button` 在 `:121`／`:130` | `app.py`（wizard 模式）→ `undergrad_wizard.py:455/777/1538/1658`，经 `:56 _render_official_download` |
| **2 硬门禁** | ✅ `run_export_gate` @`deliverable_center_panel.py:182`（阻断 `:187`） | ❌ **不经 `run_export_gate`**；唯一前置＝`app.py:1513 check_effect_size_required`（定义 `src/output/formatter.py:181`，仅查效应量非空） | ✅ `render_export_gate` @`app.py:2329`→`export_gate.py:113` | ✅ `run_export_gate` @`undergrad_wizard.py:63`，失败时**主动清产物**（`:66`） |
| **3 门禁项细目** | 4 类全过：健康检查 `export_gate.py:61`、Bundle 校验 `:74`、未确认 AI 差异 `:78-83`、隐私 `:94-99`；另加面板侧 `bundle.is_exportable()`（`deliverable_center_panel.py:180`，定义 `src/paper_writer/research_deliverable.py:37`）与 `check_consistency`（`:154-168`，tab2） | 1 类：效应量（`formatter.py:181-199`）。健康检查／Bundle 校验／AI 差异／隐私文本扫描 **全不经** | 4 类全过（同 A，走同一函数）＋**Bundle 校验重复一次**：`paper_preview_panel.py:103` 与 `export_gate.py:74` 是同一 `validate_bundle_for_export`（定义 `src/paper_writer/bundle_export.py:165`） | 4 类全过（同 A）；无 `is_exportable`、无 `check_consistency` |
| **4 隐私预检** | ⚠️→✅ 双层：页级 `app.py:2370 export_pre_check(..., source="交付包")` **只 `st.error` 不阻断**（`:2376-2380`，面板照样在 `:2389` 渲染）；真阻断在门禁层 `export_gate.py:95 source="正式交付物"`。埋点 `app.py:2371 on_privacy_precheck`（定义 `src/utils/usage_hooks.py:57`） | ❌ 无文本级预检。仅**列级**脱敏：`app_pages_text.py:104-105 redact_dataframe_for_storage`（`src/utils/guardrails.py`），作用于 ZIP 内 `data.csv`；`report.md`／`params.json` **不过扫描** | ✅ 仅经 `export_gate.py:95` 一处（页级不重复）；`on_privacy_precheck` **0 次** | ✅ 仅经 `export_gate.py:95`；`on_privacy_precheck` 0 次 |
| **5 命名（export_naming）** | ❌ 全部**位置参数硬编码**：`research_deliverable_{mode}.md/.docx/.pdf/.zip` @`deliverable_center_panel.py:210/220/240/257`＋`export_meta.json` @`:264`。**无项目名、无日期** ⇒ 跨项目/跨日同名 | ❌ 自造规则：`app_pages_text.py:157 f"作业包_{safe_name}_{now}.zip"`，`safe_name` 由**局部**清洗器 `:153`（保留 `._-（）()`、截 20 字）生成，时间戳 `%Y%m%d_%H%M%S` `:99`。**不调 `export_filename`** | ⚠️ 半走：`:124 file_name=md_result.filename` ← `bundle_export.py:142 f"{bundle.title}_论文.md"`（**裸 title，无 sanitize**，`:153` docx 同）；`:133 f"{bundle.title}_论文.md"` 与 md 按钮**同名**（标签写「Word（参数包）」实为 md） | ✅ 唯一整族合规：`undergrad_wizard.py:448/1531/1662` 用 `export_filename`（定义 `src/utils/export_naming.py:12`，清洗器 `:37`）；例外 `:781 "论文图表集.zip"`、`:2398/2410` 模板 CSV |
| **6 落盘方式/目录** | 浏览器下载，服务端**零写入**（`st.download_button` 全 5 处，`deliverable_center_panel.py:207/217/237/254/264`） | 浏览器下载，ZIP 在内存 `io.BytesIO`（`app_pages_text.py:101-102`），服务端零写入 | 浏览器下载（`paper_preview_panel.py:121/130`），服务端零写入 | 浏览器下载；ZIP/DOCX 先落 `st.session_state`（`undergrad_wizard.py:446/1529`）——**会话内存，非盘** |
| **7 审计痕迹** | 仅隐私计数：`usage_events_*.jsonl` 的 `privacy_precheck`（`app.py:2371`）。**无 export 事件**：`on_export` 定义 `usage_hooks.py:62`，生产调用点 **0**（`rg -n 'on_export' app.py src/` 仅命中 import `app.py:57`） | ❌ 无。`download_history` 亦不写（只有 wizard 写，见 D） | ❌ 无 | ⚠️ `undergrad_wizard.py:866 _record_download` 写 `st.session_state["download_history"]`（`:876` 上限 30 条）——**进程内、不落盘、rerun 依赖 session** |
| **8 失败/降级语义** | 4 种格式各自 `try/except` → `st.error`（`:223-224/248-249/260-261`）；PDF 不可用走 `st.warning` 引导手动另存（`:230-231`） | 单一 `st.success`（`:161`），ZIP 构建无 try/except ⇒ 异常直穿 Streamlit | 阻断时 `st.error("存在阻断性问题…")` 后 `return`（`:113-114`）；判定靠**中文字符串匹配**（`:111 "为空" in i or "标题" in i or "无任何章节" in i`） | 阻断时清产物＋`st.error("导出被阻止：" + …[:2])`（`:67-68`，**只报前 2 条原因**） |

维度数＝8（触发点/硬门禁/门禁项/隐私预检/命名/落盘/审计痕迹/失败语义），入口列＝4，均 ≥ 完成标准要求的 5×3。

---

## 3. 「命名统一」前提的实测否证（完成标准 1 的最硬一格）

`docs/TESTING.md:133` 声称：`test_export_naming` 失败 → 「检查新加的 `st.download_button` 是否用了 `export_filename()`」。实测该门禁**恒真**：

| 口径 | 读数 | 证据 |
|---|---|---|
| 门禁测试自身 | `3 passed in 0.83s`（全绿） | `.venv/Scripts/python.exe -m pytest tests/test_export_naming_global.py -q` |
| 门禁**实际检查到**的 `file_name` 站点数 | **0** | 复刻 `tests/test_export_naming_global.py:69-77` 的正文逻辑跑一遍，`test_examined = 0` |
| 独立口径交叉验证 | `rg -c 'download_button.*file_name\|file_name.*download_button' src/ui/*.py` → **零命中（rg exit 1）**；awk「同行或次行含 file_name」→ **0** | 探针 `tmp/psy13/naming_gate_probe2.py` §A |
| AST 真值面：全仓 `st.download_button` 站点 | **35**（`src/ui` 31／`app.py` 4） | 同上 §B |
| 其中直接调用 `export_filename`／`_efn` | **7**（`CALL:export_filename` 2 ＋ `CALL:_efn` 5）；另有 2 处经 `st.session_state.get(...)` 间接（值由 `export_filename` 生成） | 同上 §B kinds 表 |
| 其中硬编码（FSTRING 13＋LITERAL 9＋EXPR 1） | **23** | 同上 §B/§D |
| 扫描器覆盖面 | `UI_DIR.glob("*.py")` **非递归** 38 文件；`rglob` 40 文件 ⇒ **2 个子目录文件永远不被看**；`app.py` 4 站点**完全在扫描范围外**（`tests/test_export_naming_global.py:13 UI_DIR = src/ui`） | §A |

**根因**：启发式只认「`file_name` 与 `download_button` 同行，或在其下一行」（`tests/test_export_naming_global.py:71-77`），而全仓 Streamlit 调用一律写成多行具名/位置参数；且 A 列 5 处**把文件名当第 3 个位置参数**传（如 `deliverable_center_panel.py:207-210`），行内**连 `file_name` 字样都没有**。⇒ 该测试**结构上不可能失败**，「命名已统一」这条在册前提不成立。

---

## 4. 前提否证清单（本单 4 处）

1. ❌ **`app.py:1700` 锚点失效** → 实调在 `app.py:1517`（−183 行）。
2. ❌ **「三入口」计数** → 同一 `rg` 命中集实际指向 **4 类可达出口**（A/B/C/D），另有 `app.py:1490/1498/1501` 三个分析页直出（HTML/CSV 走 `renderers.py:675/701`，HTML 甚至是裸 `<a download="分析报告.html">` base64 链接 @`renderers.py:697`，连 `download_button` 都不是，命名门禁与 AST 门禁同时看不见）。
3. ❌ **「草稿入口缺门禁」**（读 `KNOWN_ISSUES.md:104` 的自然理解）→ **C 入口 4 类门禁一项不缺**，走的就是 `run_export_gate`；它的真实偏差是**门禁过严侧的冗余**（`validate_bundle_for_export` 跑两次，§2 维度 3）与**命名裸 title**，不是缺门。真正缺门的是 **B 作业包**和**分析页直出**（只有效应量检查）。
4. ❌ **「命名走 export_naming」**（`docs/TESTING.md:133` 的既成口径）→ 35 站点仅 7 处直调，守护测试恒真（§3 全套读数）。
5. ⚠️ 附带：`on_privacy_precheck` 只在 A 入口的**页级装饰性扫描**里被调（`app.py:2371`），而**真阻断**的门禁级扫描（`export_gate.py:95`）**不埋点** ⇒ 日志里的 `privacy_precheck.safe` 记录的是"被展示的那次"，与"是否放行"不是同一件事；且 `export_pre_check` 的 `safe = len(high_severity)==0`（`src/utils/privacy_ethics.py:190`，`_PATTERNS` 定义 `:59`）——**在册缺陷，本单不修**（email/password 检出不拦）。

---

## 5. 统一语义建议稿（完成标准 3：两级）

### 5.1 最小改动（不动门禁语义、不动统计/医疗内容，纯补齐）

| # | 建议 | 落点（实测锚） | 为什么算最小 |
|---|---|---|---|
| M1 | **先修命名门禁的可观测性，再谈统一命名**：把扫描器从「文本启发式」换成 `ast` 取 `file_name` 关键字＋第 3 位置参数，并把 `app.py` 纳入扫描根 | `tests/test_export_naming_global.py:13,69-77` | 现在的绿是假绿；不先修它，M2 做完也无人守 |
| M2 | B 作业包文件名改用 `export_filename("课程作业", "zip", title=test_name)`，局部清洗器 `app_pages_text.py:153` 只保留 ZIP 内 `README.txt` 的展示名 | `src/ui/app_pages_text.py:153-157` | 只换命名，ZIP 内容与脱敏逻辑一字不动 |
| M3 | C 草稿两处文件名补 sanitize 并**互不重名**：`:130` 那个按钮标签写「Word（参数包）」却给 `.md`，建议同时改标签或改扩展名 | `src/ui/paper_preview_panel.py:124,130-133`、`src/paper_writer/bundle_export.py:142,153` | 裸 `bundle.title` 可含 `\ / : * ? " < >` （即 `export_naming.py:40` 要清洗的那一组）⇒ Windows 下载名可能被浏览器截断 |
| M4 | A 入口 5 处 `research_deliverable_{mode}.ext` 改走 `export_filename`（带项目名＋日期），消除跨项目同名 | `deliverable_center_panel.py:210,220,240,257,264` | 语义不变，仅命名；`export_meta.json` 可保留原名 |
| M5 | 把**门禁级**隐私扫描也埋一次（复用 `on_privacy_precheck`），与页级那次用 `source` 字段区分 | `src/ui/export_gate.py:95-99` | 只加一条事件，不改判定；`on_export` 已有定义无调用（`usage_hooks.py:62`），与 s922-127 的埋点设计合并做 |
| M6 | D 入口 `st.error` 别只报前 2 条原因（`[:2]` 截断会让人以为只有 2 个问题） | `src/ui/undergrad_wizard.py:67` | 文案级 |

### 5.2 需拍板（改的是语义，不该由执行班决定）

| # | 议题 | 两难 |
|---|---|---|
| P1 | **作业包要不要进 `run_export_gate`** | 进了＝"课程作业"场景被健康检查/文献待审卡死（学生场景可能本就不该卡）；不进＝一份未过隐私扫描的 ZIP 可被"作业"名义带走。**建议方向：至少先只加 `export_pre_check` 文本扫描**，别一步到位上全门 |
| P2 | 页级预检（`app.py:2370-2386`）与门禁级预检（`export_gate.py:94-99`）**保留哪一个** | 现状两层扫描**不同 `source`、不同数据面**（页级只看 `analysis_output`＋`paper_bundle`；门禁级多一个 `research_deliverable_bundle`），且页级不阻断。要么页级降级为纯提示并写明"不阻断"，要么删页级避免"报错但还能导"的错觉 |
| P3 | `validate_bundle_for_export` 在 C 入口跑两次（`paper_preview_panel.py:103` ＋ `export_gate.py:74`）是否收敛 | 收敛＝少一次校验但**错误文案分级会变**（`:111` 靠中文字符串 `"为空"/"标题"` 判阻断），涉及 UI 语义；先拍「以门禁为单一事实源」再改 |
| P4 | A 入口 tab2「导出前检查」只展示不阻断（`deliverable_center_panel.py:170-175` 无 `return`）是否要改成阻断预览 | 改了＝tab2 与 tab3 语义一致；不改＝tab2 是"体检报告"。现状易被读成"它把关了" |
| P5 | **落盘根不统一**：三条交付入口全是浏览器下载（服务端零写入），而 `export_snapshot` 写 **CWD 相对**的 `reports/snapshots/`（`src/analysis/runner.py:1078,1081`）、归档写 `ARCHIVE_ROOT = 仓库/archive`（`src/utils/app_paths.py:26`）、用户数据写 `~/.psy_analysis`（`:18`）——三个根、三种可移植性。快照未走 `app_paths`，换 CWD 启动就散落 | 属 s922-128 面簿范围；**是否把快照收进 `APP_HOME` 需拍板**（涉及历史数据位置，不能由执行班挪） |

---

## 6. 边界声明

- 未改任何生产码；未写 `data/`；未触发任何导出（只静态取证＋跑 1 个既有测试文件的只读验证）。
- 红线自查：未改统计结论、未碰医疗内容与被试数据；`_PATTERNS` 相关只引用行号，未读任何用户正文。
- 在册缺陷只登记不修（`export_pre_check.safe` 只看 high、快照时间戳粒度、win32 大小写不敏感 glob 等）——见 psy12 待人工台账。
- **测试件引用口径**（按主班 08:33 补记执行）：本单唯一整读过的测试件是 `tests/test_export_naming_global.py`，引用前已核 `git status --short` 与 `git diff --stat HEAD` 双路**对该路径均零输出** ⇒ 本班所读＝HEAD `7f97243` 版本，非他班在途态；§3 的全部行号（`:13/:69-77/:71-77`）为**本班实测**，不引他处二手行号。`tests/test_v163_acceptance.py` **本单未读、未引**（不属本批范围）。

---

## 7. 复算附录（全部只读，可整段粘贴）

```bash
cd /d/code/psy-analysis
# 锚点
rg -n '交付入口收敛' KNOWN_ISSUES.md
rg -n 'def run_export_gate' src/ui/export_gate.py
rg -n '_build_homework_package|run_export_gate' app.py src/
# 调用点上游
rg -n 'render_export_gate|_render_official_download' app.py src/
rg -n 'def export_html|def export_csv|def export_snapshot|def check_effect_size_required' app.py src/
# 命名门禁恒真（三种独立口径互证）
PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest tests/test_export_naming_global.py -q
rg -c 'download_button.*file_name|file_name.*download_button' src/ui/*.py   # 预期：零命中，exit 1
# 埋点面
rg -n 'on_export' app.py src/ tests/          # 预期：生产零调用（仅 import + 定义 + 测试直调）
# 落盘根
rg -n 'APP_HOME|ARCHIVE_ROOT|LOG_DIR' src/utils/app_paths.py
rg -n 'reports/snapshots' src/analysis/runner.py
```

AST/复刻双口径探针（本单留存，未删，供下一班复算）：
`tmp/psy13/naming_gate_probe.py`、`tmp/psy13/naming_gate_probe2.py`（`tmp/` 已在 `.gitignore` 层，`git status` 不显）。
