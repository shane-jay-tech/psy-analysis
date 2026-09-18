# psy tests/ 覆盖盲区符号级审计（d914-75，只读）

- 实测时间：2026-09-15 04:1x
- 产物：本报告 ＋ `psy-test-blindspot-audit-20260915.json`（机器可读）
- 扫描脚本：`tmp/blindspot_scan.py`（项目内 tmp/，未污染 src/、tests/）

## ① 方法与判定口径

- 枚举 `src/**/*.py`（排除 `__pycache__`）：**244 个模块**；
- 对每模块用 `ast` 取**顶层公开符号**（ClassDef/FunctionDef，去掉下划线开头、长度≥5）；
- 符号在 `tests/**` 全文做词边界匹配（`re.search(r"\b"+name+r"\b", tests_corpus)`）；
- 模块点分路径与文件名主干另做一次精确匹配；
- 判定：任一符号命中 → `covered`；仅模块名命中 → `covered_by_module_name`；全不命中 → `blind`。
- 结果：**covered 178 ／ covered_by_module_name 40 ／ blind 26**（合计 244 ✓）。

## ② 盲区清单（blind 26 条，按行数降序，含二次核实结论）

二次核实＝在 src/ 语料内检索该模块的被 import 情况：有上层 import 者 →「疑似盲区（可能经上层间接执行）」；无任何 import 者 →「真盲区（UI 入口/工具，测试与生产调用双缺）」。

| 行数 | 模块 | 二次核实结论 |
|---|---|---|
| 1556 | paper_writer.literature_expansion | 疑似盲区：被 literature_manager import（其有直接测试，可能间接触达） |
| 790 | ui.questionnaire_panel | 真盲区：importers=0，Streamlit 页面入口 |
| 733 | questionnaire.item_templates | 疑似盲区：被 design_engine / llm_engine import |
| 727 | ui.quick_entries | 真盲区：importers=0 |
| 678 | ui.paper_writing_ui | 真盲区：importers=0 |
| 664 | output.reasoning | 疑似盲区：被 analysis.runner import |
| 552 | questionnaire.intent_recognizer | 疑似盲区：被 design_engine / topic_funnel import |
| 513 | experiment_design.psychopy_generator | 疑似盲区：被 experiment_design.__init__ re-export |
| 424 | experiment_design.single_subject | 疑似盲区：同上 |
| 289 | parser.keyword_dict | 疑似盲区：被 intent_resolver / tokenizer import |
| 236 | paper_writer.interactive_qa | 疑似盲区：被 paper_engine import |
| 219 | ui.literature_review_queue_panel | 真盲区：importers=0 |
| 160 | utils.error_messages | 真盲区：importers=0 |
| 139 | ui.health_panel | 真盲区：importers=0 |
| 120 | paper_writer.workflow_service | 疑似盲区：被 __init__ / undergrad_wizard import |
| 110 | questionnaire.scale_guidance | 疑似盲区：被 design_engine import |
| 104 | utils.llm_timer | 疑似盲区：被 3 个 UI 模块 import（但 UI 层整体无测试，弱间接） |
| 95 | llm_gateway.active_config | 疑似盲区：被 gateway import |
| 92 | utils.usage_hooks | 真盲区：importers=0 |
| 90 | literature_feed.scheduler.__main__ | 真盲区：`__main__` 入口，仅命令行触达 |
| 77 | ui.project_status_panel | 真盲区：importers=0 |
| 63 | visualization.fonts | 疑似盲区：被 charts / exporters import |
| 42 | ui.pages.privacy_gate | 真盲区（测试零引用；生产由根仓 app.py:317 使用，属「生产在用但无测试」） |
| 40 | output.docx_styles | 疑似盲区：被 docx_exporter import |
| 33 | ui.heavy_preload | 真盲区（生产由根仓 app.py:336 使用，无测试） |
| 26 | output.reasoning 之外的 25 行以下条目（含 utils.method_exposure 等） | 逐条同口径：有 import 者=疑似盲区，无=真盲区（完整清单见 JSON） |

## ③ 误报排查

- **反例（模块名粗筛的误报）**：`tests/test_literature_feed_storage.py:260` 的 `class TestJsonlArchive` —— `literature_feed.storage.jsonl_archive` 模块名不出现在 tests 任何文本里，但其类 `JsonlArchive` 被直接引用；只按「模块名/文件名」粗筛会把已覆盖模块误判为盲区。本审计用**符号级词边界匹配**规避该误报（`jsonl_archive` 因此判 covered 而非 blind）。
- **反向误报（本口径的残余风险）**：符号名是常见词时词边界匹配会命中无关文本（如 `Problem`），倾向把盲区误判为 covered——即本清单的 blind 判定偏保守（宁少报不误报），实际盲区只会更多不会更少。
- **动态 import / 字符串拼接模块名**：本仓 tests/ 无该形态（抽查无 `import_module` 调用）；如未来出现，符号级匹配会漏检——属口径已知边界。

## ④ 边界声明

- 本报告只记录**覆盖事实**，不对任何模块的功能正确性、统计方法或研究结论做判断。
- `git diff --stat -- src/ tests/`：src/tests 零新改动（本班只新增两份 docs/insights 产物与 tmp/ 扫描脚本）；开工前既有的 `M src/literature_feed/scheduler/lock_manager.py`（9/14 03:39）与本班无关，如实披露。
