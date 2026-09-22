# psy 浏览器 E2E「26 skipped」清单快照（s922-137，2026-09-23 实取）

> 只读快照，零安装、零改码。用途：`KNOWN_ISSUES.md:103` 那行「当前 `.venv` 未安装 Playwright，26 项明确跳过」
> 在册两年只有**计数**、没有**清单**；发布认证环境补装 Playwright 后要逐条勾销，缺的就是这份。
>
> - 取值时刻 **2026-09-23T01:24–01:28**，psy HEAD **`bcb21f4`**，解释器 `D:\code\psy-analysis\.venv\Scripts\python.exe`（Python 3.12.9）。
> - `pytest.ini` 此刻是他班 ` M` 在途件，现读 `addopts = --strict-markers`（他班把 `-q` 摘掉了）；本单所有命令**自带 `-q/-v`**，不受该在途差异影响。
> - **未跑全量**（并发约束）：只跑 `-m 'playwright or e2e'` 标记子集，该子集 26 项**全部在执行前即 skip，零用例体运行**。

## 〇、先读这节：与四份前档的关系（含对旧结论的一条订正）

`docs/insights/` 里**已有**四件 e2e 相关档案，本档不是从零起。逐件对账：

| 前档 | 它已经有什么 | 本档的增量 | 冲突处理 |
|---|---|---|---|
| `playwright-readiness-20260911.md`（p911r-36） | **文件级**跳过点定位表（`test_e2e_v52_paths.py:23-36`／`test_playwright_golden_research_flow.py:450`／`test_playwright_e2e.py:22`）＋一句关键环境读数：**`~/AppData/Local/ms-playwright` 里 chromium-1234 等浏览器二进制已在盘（703MB，含 INSTALLATION_COMPLETE），缺的只是 `.venv` 里的 playwright python 包** | ① 本档是**首份 nodeid 级**清单（25 条）；② 量出那条模块级 skip **遮住 11 例**（前档只记「11」在定位表的覆盖测试数列里，没说明它不进 skip 清单） | 无冲突。⚠️ 但前档「合计 72 个 def test 分布在 5 个 e2e/playwright 文件」一句里的 5 件，含 `test_e2e_rendering.py`／`test_e2e_ui.py` 等**今天不带 e2e 标记**的文件 ⇒ 见 §5.6，别把 72 当本清单分母 |
| `psy-e2e-count-caliber-20260917.md`（916p-a4-002） | 25（`-m e2e` collect）与 26（`-m 'playwright or e2e'` run）两个数**当时已实测**，并据此把台账 :103 从「25 项」改成「26 项」 | 本档给出口径差的**正确机制** | 🔴 **订正该档结论**：它写「并集实跑 26=25+1，说明 playwright-only 有 1 项不在 e2e 内」——今日三条实测把它否了：`-m playwright` collect **12**、`-m 'e2e and not playwright'` **13**、`-m 'playwright and not e2e'` **0 collected（4859 deselected）** ⇒ **`mark.playwright` 的 12 项全是 `mark.e2e` 的子集**，25/26 之差与标记域**毫无关系**，唯一来源就是 §三 的模块级 `importorskip`。⇒ 该旧档留痕不改，请主班在台账上追一行订正 |
| `psy-e2e-skip-inventory-20260914.md`（d914-38） | 当时同面读数是 **13 errors ＋ 10 failures＝23 非绿**，并断言「KNOWN_ISSUES 的 25 项跳过低估了 benchmark 域」 | — | **两档口径不可混用**：9-14 时这些用例**还没挂 skipif/importorskip**（是环境失败），今日同面 **0 error／26 skip** ⇒ 中间有人补了跳过标记。引用「23 非绿」时须注明那是 failures＋errors 域，不是 skip 域 |
| `psy-e2e-subset-order-20260913.md`（d913a-44/d913b-47） | 记的是 `tests/test_e2e_ui.py:52` 读 `at.session_state["_workspace_last_saved"]` 的**顺序依赖根因**，与全量基线「2586 passed/60 skipped」 | 无冲突 | 印证 §5.6：`test_e2e_ui.py` 这类**无标记的 `test_e2e_*` 件是真在跑的**（它们用 `AppTest`，不吃 Playwright），所以「e2e 命名面」与「e2e 标记面」必须分开记账 |



## 一、口径与命令原文（复现照此两条）

```bash
cd D:\code\psy-analysis
# 口径 A：跑一遍取 skip 原因（结果＝26 skipped, 4834 deselected）
.venv\Scripts\python.exe -m pytest -q -rs -m 'playwright or e2e'
# 口径 B：收集期计数（结果＝25/4856 tests collected (4831 deselected)）
.venv\Scripts\python.exe -m pytest -q -m 'playwright or e2e' --collect-only
```

两数之差＝**1**，来源见第三节。**「26」是 skip 条目数，「25」是收集到的 nodeid 数，两者不可互换**
（`KNOWN_ISSUES.md:103` 的「口径注」早已有同样的告警，本档给出处置现场）。

## 二、26 条逐条清单

### 2.1 收集到的 25 个 nodeid（口径 A 的 `-rs` 逐条读数）

| # | nodeid | skip 原因（原文） | 原因出处 |
|---|---|---|---|
| 1 | `tests/test_e2e_v52_paths.py::TestV52PageLoading::test_homepage_no_exception` | Playwright not installed or browsers not available | :35 类级 `pytest.mark.skipif(...)`（`pytestmark` 列表含 `mark.playwright`，:33） |
| 2 | `…::TestV52PageLoading::test_privacy_disclaimer_visible` | 同上 | 同上 |
| 3 | `…::TestV52PageLoading::test_no_streamlit_error_text` | 同上 | 同上 |
| 4 | `…::TestV52NextStepRecommendation::test_recommendation_cards_visible` | 同上 | 同上 |
| 5 | `…::TestV52PrivacyPrecheck::test_export_page_has_precheck` | 同上 | 同上 |
| 6 | `…::TestV52PrivacyPrecheck::test_sensitive_info_warning` | 同上 | 同上 |
| 7 | `…::TestV52ExportButtons::test_word_export_button_present` | 同上 | 同上 |
| 8 | `…::TestV52ExportButtons::test_zip_export_button_present` | 同上 | 同上 |
| 9 | `…::TestV52CacheManagement::test_sidebar_cache_button` | 同上 | 同上 |
| 10 | `…::TestV52ZipStructure::test_zip_contains_tables_directory` | 同上 | 同上 |
| 11 | `…::TestV52ZipStructure::test_zip_tables_have_csv_and_md` | 同上 | 同上 |
| 12 | `…::TestV52ConsistencyV3::test_consistency_includes_table_checks` | 同上 | 同上 |
| 13 | `tests/test_playwright_golden_research_flow.py::TestBrowserGoldenPath::test_app_launches_without_error` | Playwright not installed | :450 类级 `@pytest.mark.skipif(not E2E_AVAILABLE, …)` ＋ :451 `@pytest.mark.e2e` |
| 14 | `…::TestBrowserGoldenPath::test_health_endpoint` | 同上 | 同上 |
| 15 | `…::TestBrowserGoldenPath::test_sidebar_exists` | 同上 | 同上 |
| 16 | `…::TestBrowserGoldenPath::test_file_upload_visible` | 同上 | 同上 |
| 17 | `…::TestBrowserGoldenPath::test_upload_demo_csv` | 同上 | 同上 |
| 18 | `…::TestBrowserGoldenPath::test_no_network_dependency` | 同上 | 同上 |
| 19 | `…::TestBrowserGoldenPath::test_page_no_console_errors` | 同上 | 同上 |
| 20 | `…::TestBrowserGoldenPath::test_method_recommender_route_exists` | 同上 | 同上 |
| 21 | `…::TestBrowserGoldenPath::test_evidence_table_route_exists` | 同上 | 同上 |
| 22 | `…::TestBrowserGoldenPath::test_deliverable_export_route_exists` | 同上 | 同上 |
| 23 | `…::TestBrowserGoldenPath::test_method_recommender_panel_loads` | 同上 | 同上 |
| 24 | `…::TestBrowserGoldenPath::test_deliverable_center_panel_loads` | 同上 | 同上 |
| 25 | `…::TestBrowserGoldenPath::test_evidence_table_panel_loads` | 同上 | 同上 |

> `-rs` 摘要里这些条的落点是**各测试函数自己的 def 行**（v52 侧 :136/:148/:163/:183/:205/:218/:246/:259/:280/:296/:341/:385；golden 侧 :455/:465/:471/:479/:487/:502/:510/:520/:528/:536/:544/:556/:568），
> 但**生效的是类级装饰器**（v52 `:35` 的 `pytestmark`、golden `:450` 的 `skipif`）——按 def 行去找守卫会找不到。
> golden 侧另有第二重保险：模块级 `browser` fixture（:398-402）在 `not E2E_AVAILABLE` 时 `pytest.skip`，
> 所以**摘掉类级 skipif 也不会真跑**，只会把 skip 从 setup 阶段挪到 fixture 阶段。

### 2.2 第 26 条：没有 nodeid 的那一条（＝口径差的正身）

| # | 落点 | skip 原因（原文） | 机制 |
|---|---|---|---|
| 26 | `tests/test_playwright_e2e.py:24` | `playwright 未安装，跳过浏览器 E2E 测试` | **`pytest.importorskip("playwright", reason=…)` 写在模块顶层**（import 段里，:23 `pytestmark = pytest.mark.e2e` 之后一行） |

## 三、口径差解释：collect 25 vs run 26

`pytest.importorskip` 在**模块导入期**就抛 `Skipped`，于是：

- **收集阶段**：`tests/test_playwright_e2e.py` 这个模块**一个 item 都产不出**（模块体没执行完，第 25 行 `from playwright.sync_api import …` 之前的 importorskip 已中断）⇒ `--collect-only` 只见另外两个文件（12＋13＝25）。
- **运行阶段**：该模块仍被 import 过一次，Skipped 异常被 pytest 收成**一条模块级 skip 报告**（`SKIPPED [1] tests\test_playwright_e2e.py:24`）⇒ 计数 **26**。

⇒ **「26 skipped」＝ 25 个用例 ＋ 1 条模块级 skip**，两者不是同一量纲。

## 四、⚠️ 最要紧的一条：补装 Playwright 后要重跑的是 **36 例**，不是 26 例

那条模块级 skip **遮住了 11 个真实用例**（它们从未出现在任何 skip 清单里，因为压根没被收集）：

| 类 | 用例数 | 用例名 |
|---|---|---|
| `TestPrivacyAndUpload` | 3 | `test_privacy_modal_dismissible` / `test_upload_csv_and_see_column_selector` / `test_sidebar_navigation` |
| `TestQuestionnaireLLM` | 2 | `test_questionnaire_mode_accessible` / `test_text_area_visible_in_questionnaire` |
| `TestWorkspaceSaveLoad` | 3 | `test_workspace_save_button_exists` / `test_workspace_load_button_exists` / `test_full_save_load_cycle` |
| `TestStreamlitHealth` | 3 | `test_health_endpoint` / `test_main_page_loads` / `test_no_critical_error` |

⇒ **勾销表模板（补装后逐条打勾，36 行）**：

- [ ] 口径 A 复跑：`.venv\Scripts\python.exe -m pytest -q -rs -m 'playwright or e2e'` → 期望 **26 skipped → 0 skipped**。
      补装路径按 `playwright-readiness-20260911.md` 的实测**只需装 python 包**：`~/AppData/Local/ms-playwright` 里 chromium-1234／chromium_headless_shell-1234／ffmpeg-1011 **已在盘（703MB，含 INSTALLATION_COMPLETE）**，缺的是 `.venv` 内的 `playwright` 包（本机 `import playwright` → `ModuleNotFoundError`，本档复测同值）。⇒ 先 `pip install playwright` ＋ `playwright install --dry-run` 核版本匹配，**不要盲目 `playwright install`（会重新下 703MB）**。
- [ ] §2.1 的 25 个 nodeid 全部转 PASS（其中 13 个 `TestBrowserGoldenPath` 依赖 `browser`/`page` fixture 起真实 chromium ＋ `streamlit_server` 模块级 fixture 拉起 `localhost:8501`）。
- [ ] §4 的 **11 个被遮住用例**首次进册（`test_playwright_e2e.py` 自带 `_start_streamlit()`，同样要 8501 端口空闲）。

- [ ] `KNOWN_ISSUES.md:103` 的「26 项」改写为**用例数＋机制**双口径（建议句式：「e2e∪playwright 标记面：25 个标记用例＋1 条模块级 importorskip（遮住 11 例）＝26 skip 条目；补装后待重跑 36 例」）。

## 五、附带发现（都在口径位内，只登记不改）

1. **同文件里 15 个用例根本不吃 Playwright，别误勾销**：`tests/test_playwright_golden_research_flow.py::TestDemoProjectOffline` 有 15 个 `test_`，**零装饰器、零浏览器 fixture**（`test_demo_project_exists`、`test_demo_data_valid`…），它们在全量里照常跑。
   该文件 `test_` 定义共 **28**，其中只有 13 个在 e2e 标记面 ⇒ **按文件名/按文件勾销会多勾 15 行**。
2. **三个在册 e2e 件都要活的 Streamlit 服务**（`BASE_URL = http://localhost:8501`、`_start_streamlit()` / `streamlit_server` fixture）⇒ 发布认证环境若禁本地端口，这 36 例**装完 Playwright 也过不了**，属第二道门。
3. **两标记是包含关系，不是并集两半**：`-m playwright` collect **12**、`-m e2e` collect **25**、`-m 'e2e and not playwright'` **13**、`-m 'playwright and not e2e'` **0**。
   ⇒ `mark.playwright` 的 12 项（全在 `test_e2e_v52_paths.py:33` 的 `pytestmark` 列表里）是 `mark.e2e` 的**真子集**，`'playwright or e2e'` 的并集恒等于 `e2e` 单标记的 25。两标记在 `pytest.ini` 都已登记，`--strict-markers` 不翻红。
   ⚠️ 这条同时订正了 `psy-e2e-count-caliber-20260917.md` 的「playwright-only 有 1 项不在 e2e 内」——见 §〇 表第二行。
6. **文件名带 e2e ≠ 在 26 条目里**（这是最容易勾销勾错的一处）：`tests/` 下另有 **5 件名字含 e2e 但零 e2e/playwright 标记**的用例件，它们**吃 `streamlit.testing.v1.AppTest`、不吃 Playwright**，因此**不在本清单、也不该进勾销表**：
   `test_e2e_rendering.py`（15 个 `def test_`）／`test_e2e_ui.py`（6）／`test_e2e_qimport_upload.py`（9）／`test_e2e_resultcard_paperpreview.py`（5）＝ **35 例**，另有 `test_golden_path_e2e.py`（14 例，标的是 `mark.integration`）。
   ⇒ 这 5 件同时都在 `tests/conftest.py:20-29` 的 `_APP_TEST_FILES` 隔离名单里（前 4 件＋3 件非 e2e 名）。**按文件名 glob 取「e2e 面」会得 37＋14 例，与标记面的 25＋11＝36 例完全不是一回事**。本单只读位未跑它们（属全量口径）。

4. **零安装自证**：`.venv\Scripts\python.exe -c "import playwright"` → `ModuleNotFoundError: No module named 'playwright'`（本单全程未执行任何 `pip install`；`requirements-lock.txt` 是他班 ` M` 在途件，未触碰）。
5. **`KNOWN_ISSUES.md:103` 锚点逐字命中**，且其「口径注」早已声明「收集仅 25 项，第 26 项来自模块级 skip，两数不可互换」——本单**没有否证它**，只是把「模块级 skip」具体定位到 `test_playwright_e2e.py:24` 的 `importorskip`，并量出它遮住 11 例。

## 六、本档未覆盖

1. 未验「补装 Playwright 后这 36 例是否真能过」（禁安装，且需活服务）——表是**待勾销清单**，不是通过证明。
2. §5.6 那 49 例（35＋14）**本班未跑**：它们属全量口径，且本班受并发约束不跑全量。它们「现在是否绿」未知，勿由本档推定。
3. 全量 61 skipped 的其余 35 项（非 e2e 面）不在本档，属另一普查；`benchmark` 域 33 项 skip 见 `psy-e2e-skip-inventory-20260914.md`（该档口径混了 benchmark 与 e2e，引用时注意）。
4. `archive/`、`tmp/` 下的历史 e2e 件不在 `testpaths` 内，未计。
5. 三条 skip 机制的**版本起点**未查（9-14 时这些用例是 error/failure、今日是 skip ⇒ 中间某笔提交补了标记）。要追责到 commit 需 `git log -S "importorskip" -- tests/`，本单未做。

