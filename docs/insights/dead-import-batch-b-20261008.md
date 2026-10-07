# psy 死 import 新矿批 B 三栏清单（s1010-06）

- 日期：2026-10-08 ｜ 口径：AST usage＋词边界＋文件内引号引用面＋全仓（src+tests 单趟）再输出链/字符串引用排除
- 总账：**删 38 名/28 件 ／ 留（陷阱）10 名 ／ 顺延（在途 M）3 名 ／ 留（假引号保守）14 名**

## 删栏（38 名/28 件，commit 见 result）

| 件 | 删名 |
|---|---|
| utils/archive_manager.py | os、shutil |
| utils/memory_manager.py | os |
| utils/cache_manager.py | shutil、Optional |
| utils/environment_diagnosis.py | sync_playwright |
| utils/privacy_ethics.py | glob as glob_module（别名体删除） |
| utils/autosave.py | Path |
| output/formatter.py | pandas as pd |
| output/plotly_renderers.py | numpy as np、_base_layout、CHART_HEIGHT |
| output/snapshot.py | List |
| visualization/charts.py | plotly.express as px、make_subplots |
| templates/registry.py | json |
| upstream/tier.py | Optional |
| upstream/topic_funnel_kb.py | Optional |
| paper_writer/literature_manager.py | Path |
| paper_writer/defense_qa.py | field as _field |
| paper_writer/interactive_qa.py | Callable |
| paper_writer/bundle_export.py | io、Optional |
| paper_writer/section_diff.py | Optional |
| paper_writer/draft_bundle.py | Optional |
| paper_writer/adapters.py | Any、Optional |
| literature_feed/parsers/meta_tag_parser.py | Any |
| literature_feed/parsers/csl_normalizer.py | Iterable |
| literature_feed/fetchers/base.py | Sequence |
| literature_feed/trend/domain_weights.py | Sequence |
| literature_feed/review_queue_ui.py | Any、Optional |
| literature_feed/review_service.py | Optional |
| literature_review/completeness.py | Optional |
| literature_feed/trend/trending_weights.py | Optional |

## 留栏——陷阱排除记录（两陷阱各一行依据）

- **陷阱①再输出链（9 名留）**：PAPER_SECTIONS/STAT_FORMATS/SIG_MARKS/EFFECT_SIZE_GUIDE/ACADEMIC_PHRASES/smart_search_literature（paper_engine/section_writers）被 `paper_writer/__init__.py` 转输出（`__init__` 导出行与 `__all__` 串双证）且测试消费；LLMUnavailableError（section_writers）被 `llm_gateway/__init__.py` 转输出。
- **陷阱②monkeypatch 字符串引用（1 名留）**：autosave.py LEGACY_META_FILE——tests/conftest.py:52 `monkeypatch.setattr(autosave, "LEGACY_META_FILE", ...)` 依赖模块属性存在，删之破 conftest（本批 test_autosave 系 202 passed 内含该面）。
- **消费面留（1 名）**：defense_qa DIFFICULTY_LEVELS——test_defense_qa_kb_data 等测试件 import 消费。

## 顺延栏（在途 M 整文件避让，3 名）

- utils/workspace.py json＋ExperimentDesign、output/delivery_package.py export_all_figures_zip、output/docx_exporter.py APATable——三件在途（s1010-06 任务书在途锚），留后续微单。

## 假引号保守留（14 名，供后续人工核）

daily_runner（DEFAULT_HALF_LIFE_DAYS/TrendingWeights/date/time）、feed_panel（MethodWeights/TrendingEntry）、completeness（LiteratureItem/ReadingNote）、themes（LiteratureItem）、trending_weights（DomainWeights/FeedStore）、manual_ingest（SourceConfig/normalize_iso_date）、review_queue_ui/interactive_qa（field）、csl_normalizer（datetime）——初裁引号匹配疑为跨文件同名噪音（如 test_fonts docstring、"Path Coefficients" 标题），不在本批点名锚内，保守留待人工。
