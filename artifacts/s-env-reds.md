# 环境红名集处置单——全量红名集现值对比＋三型分账（s1023-08）

- 单号：s1023-08｜班次：shift-20261023-2340｜落盘：2026-10-24 04:56
- T0 基线日志：`tmp/s1023-08/baseline-0434.log`（HEAD=9529f14，全量 645.97s，EXIT=1）
- 对照基：`tmp/s1008-01/s1014-05-full.log`（s1014-05 时代读数），逐名清单 `tmp/s1023-08/prior-reds-s1014-05.txt` vs `tmp/s1023-08/current-reds-0434.txt`
- 性质：**只读归因单**——零安装、零改码、零写库；安装清单仅供主班

---

## 1. 现值对比（37F+13E 是否漂移：**漂移**）

| 读数 | F | P | S | X | E | 来源 |
|---|---|---|---|---|---|---|
| s1014-05（2026-10-14 时代） | 37 | 5715 | 4 | 28 | 13 | done/s1014-05.result.md |
| **本单 T0（2026-10-24 04:34，HEAD=9529f14）** | **28** | **5732** | 4 | 28 | **13** | baseline-0434.log |

- **E 侧 13 名逐名零漂移**（全部 test_playwright_golden_research_flow.py，与 s1008-01→s1014-05 一脉）。
- **F 侧 37→28：11 名转绿＋2 名新增红**（37−11+2=28），逐名 diff 见 tmp/s1023-08/ 两清单。
- 转绿 11 名：test_docx_export::test_plotly_figs_to_figure_items_smoke、test_export_all_figures_zip_smoke_s1004_08、test_fig_to_image_runtime_s93010 ×2、test_figure_export_degradation_keeps_statistics ×4、test_paper_export ×2、test_skip_gates...::test_capability_gate_agrees_with_independent_probe[kaleido]。
  - 机制注记（实测定性＋推断标注）：实测 `import kaleido` **仍失败**（依赖未装），[kaleido] 门测转绿＝门与独立探针**一致判缺**；图形导出族 10 名在缺 kaleido 下通过，**推断**为降级链路（degradation 族即其名）已由他班在途件收口——**转绿属代码侧收口，非依赖安装所致**。归属请主班对账（对应 s1008-01 遗留 3 的点名在途件）。
- 新增红 2 名：test_project_panel_ui.py::test_lock_on_empty_state_create_shows_the_banner_and_writes_nothing、::test_banner_has_no_holder_because_the_exception_carries_only_one_arg（归因见 §2-B2，指向当日 commit 434b6e6）。

## 2. 三型分账（现值 28F+13E 逐名）

### A｜环境缺依赖／工具链能力面（15F）
| 面 | 名单 | 证据要点 |
|---|---|---|
| streamlit AppTest 无 download_button 访问器（×5） | test_e2e_resultcard_paperpreview(1)、test_qimport_cleaned_key_q1002_09(1)、test_questionnaire_import_panel_render(3) | `AttributeError: 'AppTest' object has no attribute 'download_button'`；实测 streamlit **1.58.0**（较新线仍无此访问器）→ 属上游 AppTest 能力边界，**非版本陈旧、装包不可解** |
| v52 路径面（×5） | test_e2e_v52_paths：privacy_disclaimer / sensitive_info / sidebar_cache / zip_tables ×2 | 页面 HTML 不含「本系统/隐私/缓存清理」、zip 内 0 表（assert 0 > 0）——登记在册 v52 服务渲染面 |
| playwright golden 服务面（×5F） | test_playwright_golden_research_flow：sidebar_exists / file_upload_visible / method_recommender_route_exists / evidence_table_route_exists / deliverable_export_route_exists | assert 0 > 0（页面 0 元素）；playwright 包 import 正常，浏览器二进制安装态未验 |

### B｜真缺陷（6F＋13E）——点名
1. **src/ui/project_panel.py 三处 NameError（:73 / :98 / :116）**：`except Exception as exc:` 配 `st.error(f"...{type(e).__name__}...")` —— 变量已改名 exc 而横幅串仍引用 `e`，横幅一触发即 NameError。命中 test_project_panel_banner_s1002_16.py 3 例（NameError 实锤）＋同文件 test_mutation_revert_to_pass_turns_banner_assertions_red（assert 0 == 3，变异验证零命中，同根）。**s1014-05 将该 4 例总括进「环境面」，本单逐名归因后更正为真缺陷**（留痕）。修复另单（本单零改码）。
2. **test_project_panel_ui.py 2 例（新增红，当日 434b6e6 遗留）**：434b6e6「2a 统一提示补持有起始时间（holder+since）」落地后横幅文案含附加段，两钉桩仍钉旧文案／钉死「无 holder」（后者测试名即断言异常单参）——改码未同步测试预期，语义谁对待主班裁（更新钉桩 or 收窄提示）。
3. **13E teardown 面（test_playwright_golden_research_flow.py，逐名零漂移）**：`AttributeError: 'Function' object has no attribute 'rep_call'`（:417）。根因是 `pytest_runtest_makereport` 钩子定义在**测试模块内**（:431）——pytest 不从测试模块收集钩子，rep_call 永不落位 ⇒ 13 名全数 teardown 红。**属测试件结构缺陷，非缺依赖**（装 playwright 依赖不消此红）。

### C｜路径漂移／登记失配（7F）
| 名单 | 漂移点 |
|---|---|
| test_apptest_whitelist_drift::test_every_apptest_constructor_file_is_registered | 白名单缺 ['test_project_panel_banner_s1002_16.py','test_qimport_cleaned_key_q1002_09.py']（两者自身亦在红名集，连带登记漂移） |
| test_export_gate_global_scan::test_all_download_buttons_accounted_for | src/ui/questionnaire_import_panel.py 下载钮未入账（与 A-download_button 面同域） |
| test_lr_dirty_number_frozen_pins::test_pending_flag_reset_is_second_statement_with_no_try_guard | 结构钉漂移（assert 6 == 1） |
| test_questionnaire_panel_charac ×2 | monster-function 模块级名（多出 logger 等）、session_state 触点计数双漂移 |
| test_seed_literature_sources::test_probe_reports_failure_per_source_without_raising | monkeypatch 入口 dr.build_fetcher 脱钩（probe 零「[失败]」行，0==8）——入口路径漂移候选，需复核 probe 现实现 |
| test_skip_gates...::test_structure_based_gates_point_at_paths_that_exist | 普查器扫 352 份件返回空 ⇒ 普查器与现存结构型门禁写法失配 |

## 3. 安装清单（**零安装动作，仅供主班**）
1. `pip install kaleido`——解锁图形导出全链；**注**：当前降级路径已接且门测绿，装后需重验导出族与降级分叉不回归。
2. `python -m playwright install chromium`——浏览器二进制补装（playwright 包已在）；可试消 A-黄金流 5F 的服务面，**消不了 13E**（B3 测试件缺陷）。
3. streamlit AppTest download_button：**无依赖可装**——1.58.0 已较新，属上游能力边界；建议主班走改测法/桩注入，勿以升级 streamlit 为手段。
4. 其余 B/C 类均为代码与登记面动作，不属于安装清单。

## 4. 移交与复核建议
- 转绿 11 名的归属对账（他班在途件收口）——对应 s1008-01 遗留 3、s1014-05 遗留 2 的点名闭合。
- B1 三处 NameError 修复单、B2 两钉桩语义裁决、B3 钩子迁 conftest——均为新单面。
- 本单基线日志与两份逐名清单存档 tmp/s1023-08/，可复算。
