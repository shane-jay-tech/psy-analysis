# psy 死 import 新矿批 A 三栏清单（s1010-05）

- 日期：2026-10-08 ｜ 口径：AST usage＋词边界＋文件内引号引用面＋精确再输出链（仅认「from 本模块 import」与「setattr(本模块,名)」，跨文件同名/他文件字符串注解一律不保护）
- 总账：**删 47 名/27 件 ／ 陷阱留 5 名 ／ 在途顺延 4 名 ／ 判定外保守留若干（假引号组已全部重裁转删）**

## 删栏（47 名/27 件）

| 件 | 删名 |
|---|---|
| data/transforms.py | Union |
| experiment_design/llm_engine.py | OpenAI、AuthenticationError、RateLimitError、APITimeoutError、APIStatusError、APIConnectionError（六连） |
| questionnaire/llm_engine.py | 同上六连 |
| questionnaire/llm_engine_premium.py | re、as_completed、LLMEngineError |
| questionnaire/exporters.py | os、Inches、WD_STYLE_TYPE |
| questionnaire/item_templates.py | random、Optional |
| questionnaire/kb_search.py | Tuple |
| questionnaire/design_engine.py | Any |
| questionnaire/academic_literature.py | Tuple |
| experiment_design/jspsych_data_importer.py | StringIO、Tuple、Any |
| experiment_design/design_engine.py | get_template |
| experiment_design/psychopy_generator.py | Tuple |
| analysis/assumptions.py | List、Optional |
| analysis/hlm.py | Dict、Optional |
| analysis/logistic_regression.py | Any |
| analysis/meta_analysis.py | field |
| analysis/method_recommender.py | Optional |
| analysis/reliability.py | field |
| analysis/runner.py | Optional |
| analysis/validity.py | field |
| analysis/field_lineage.py | Any |
| analysis/factor_analysis.py | stats（from scipy） |
| analysis/sem.py | numpy as np |
| data/inspector.py | numpy as np |
| experiment_design/experiment_templates.py | field |
| experiment_design/power_analysis.py | field、Optional |
| experiment_design/procedure_builder.py | field |

## 留栏——陷阱与例外

- **在途顺延（4 名）**：data/loader.py Optional＋BinaryIO（porcelain M）、analysis/result_card.py Optional（porcelain M，s1010 批在途 +193 行）——零叠改留待后续微单。
- **假引号重裁记录（21 名初裁 KEEP→重裁 DELETE）**：初版跨文件引号匹配把 data_quality 'scipy.stats'、ai_tutor docstring「OpenAI 兼容」、test_fonts docstring、field_lineage 文档串、themes "List[ThemeCluster]" 等他文件字符串当保护证据——重裁口径只认两类真陷阱（本模块 re-export/setattr），21 名全部转删；其中 5 名曾现「re-export 假证行」（descriptive_stats/ai_content_review/kb_search/field_lineage as fl 等同行异名导入）逐行人工核伪。
- 本批真陷阱零命中：无 monkeypatch.setattr 指 A 面件；无 __init__ 从 A 面件转输出被删名（get_template 经查 __init__ 直从 experiment_templates 取，design_engine 自身导入判死）。

## 测试与门

py_compile 27 件全过；导入门 27/27；触及域 13 件 226 passed（含 test_llm_engine/premium——两 engine 六连摘除后消费面绿、test_questionnaire_export_docx 在途件亦绿）；删后 47 名逐名零残留。
