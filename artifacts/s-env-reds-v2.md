# 环境红名集处置后续单——三型分账现值 v2（s1025-06）

- 单号：s1025-06｜班次：shift-20261026-1845｜落盘：2026-10-26 19:5x
- 上版：`artifacts/s-env-reds.md`（s1023-08，28F+13E，基线 HEAD=9529f14）
- 复跑口径：**定向重跑上版 41 名红集**（36 唯一节点，tmp/s1025-06/red-nodes.txt），日志 `tmp/s1025-06/rerun-1923.log`；对 2 名疑似转绿做**文件级复核**（211.86s，18P/5F）。全量跑未做（软预算内不可容纳 645s 量级），全量确认留待主班下一次全量基线。

---

## 1. 现值读数（对 s1014-05 的 37F+13E 与 s1023-08 的 28F+13E）

| 读数 | F | E | 来源 |
|---|---|---|---|
| s1014-05（10-14 时代） | 37 | 13 | done/s1014-05.result.md |
| s1023-08（10-24，全量） | 28 | 13 | artifacts/s-env-reds.md |
| **本单 v2（10-26，定向+文件级）** | **27** | **13** | rerun-1923.log（节点级 26F+10P+13E）＋文件级复核 1 名假绿回红 |

- **转绿 1 名（真）**：test_seed_literature_sources::test_probe_reports_failure_per_source_without_raising——节点级、文件级双重绿；上版 monkeypatch 入口脱钩（0==8）现值不再复现，机制归属待主班对账（s1023-08 后仓内仅 218ec6c/36200b7 两笔码改，均不触 probe 链）。
- **假绿 1 名（更正）**：test_e2e_v52_paths::TestV52PrivacyPrecheck::test_sensitive_info_warning——36 节点定向跑绿，**文件级整跑复红**＝测试序依赖假绿，A 类现值仍记红。
- 其余 26F+13E 逐名零漂移（断言文本与上版同型）。

## 2. 环境安装态漂移（对上版 §3 清单的两笔重大变化）

| 项 | s1023-08 现值 | 本单实测 |
|---|---|---|
| kaleido | MISSING（import 失败） | **INSTALLED，import OK** |
| playwright chromium | 二进制安装态未验 | **在位**：D:\ms-playwright\chromium-1234\chrome-win64\chrome.exe（Chrome for Testing 151.0.7922.34） |
| streamlit | 1.58.0（无 download_button 访问器） | 1.58.0 未变（5 处 AttributeError 原样复现） |

- **归属待主班对账**：两笔安装均发生在 s1023-08（10-24）之后，非本班所为；按 jsdom 先例口径追认与否由主班裁决。
- **注记**：chromium 在位但 playwright 黄金流 5F+13E 原样红——证实上版判断「装浏览器消不了这面」（页面 0 元素＝服务渲染面；13E＝测试模块内钩子缺陷），该 18 名**不因安装转绿**。

## 3. 三型分账 v2（27F+13E 逐名）

### A｜环境缺依赖／工具链能力面（15F，较上版 15F 名次有动）
| 面 | 名单 | 现值证据 |
|---|---|---|
| streamlit AppTest 无 download_button（×5） | resultcard_paperpreview(1)、qimport_cleaned_key(1)、questionnaire_import_panel_render(3) | `AttributeError: 'AppTest' object has no attribute 'download_button'` ×5 原样；1.58.0 上游能力边界，**无可装依赖** |
| v52 路径面（×5） | privacy_disclaimer / **sensitive_info（假绿回红，记此）** / sidebar_cache / zip_tables ×2 | 页面 HTML 断言原样；sensitive_info 节点级绿不采信 |
| playwright golden 服务面（×5F） | sidebar_exists / file_upload / method_recommender / evidence_table / deliverable_export | assert 0 > 0 原样；chromium 已在位仍红＝服务渲染面实锤 |

### B｜真缺陷（6F＋13E）——与上版逐字一致，零收口
1. **src/ui/project_panel.py 三处 NameError**：banner 三测现值报错文本 `name 'e' is not defined`（exc/e 改名失配原样）＋变异验证 test 0/3 命中——4F 全红未动，修复单仍缺位。
2. **test_project_panel_ui 2F**：横幅文案「占用（...）」附加段与钉桩失配原样（434b6e6 遗留裁决待主班）。
3. **13E teardown**：`'Function' object has no attribute 'rep_call'` ×13 原样——钩子仍在测试模块内（非 conftest），属测试件结构缺陷。

### C｜路径漂移／登记失配（6F，上版 7F→6F：seed_literature 转绿）
| 名单 | 现值漂移点 |
|---|---|
| test_apptest_whitelist_drift | 白名单仍缺 ['test_project_panel_banner_s1002_16.py','test_qimport_cleaned_key_q1002_09.py'] 原样 |
| test_export_gate_global_scan | **漂移换名**：上版点名 questionnaire_import_panel.py，现值改点名 `src/ui/questionnaire_panel.py`——同域不同文件，门禁账面待复核 |
| test_lr_dirty_number_frozen_pins | assert 6 == 1 原样（「已翻正为 1；多于 1 枚说明有人加戏」） |
| test_questionnaire_panel_charac ×2 | 模块级名多 logger 等（['logger',...]==['CLOCK_ANOMALY_WARNING_TEXT']）＋触点钉现值 **883 == 881**（上版口径为 session_state 20 触点面，钉值已随码漂移） |
| test_skip_gates...::test_structure_based_gates_point_at_paths_that_exist | 扫描件数 352→**353**（普查器失配原样，基数+1 为仓内文件自然增长） |

## 4. 安装清单 v2（**零安装动作，仅供主班按 jsdom 先例裁决**）
1. ~~kaleido~~——**已装**（追认归属主班裁）；装后需在下一次全量跑复核导出族降级分叉不回归（降级链路 vs 真渲染分流点未验）。
2. ~~playwright chromium~~——**已在位**（同上追认）；黄金流 18 名不因之转绿（见 §2 注记）。
3. streamlit AppTest download_button——**维持「无可装」判**：1.58.0 上游边界，勿以升级 streamlit 为手段；走改测法/桩注入另单。
4. 其余 B/C 面＝代码与登记动作，不入安装清单。

## 5. 移交与复核建议
- 两笔安装的授权对账（谁装、何时、是否在 jsdom 先例授权范围内）——主班。
- seed_literature 转绿归属对账＋下一次全量基线时复核（防全量序下假绿反转）。
- B1 NameError 修复单、B2 钉桩语义裁决、B3 钩子迁 conftest——仍为待立项新单面（与上版移交一致，零推进）。
- 本单复跑日志与节点清单存档 tmp/s1025-06/，可复算。
