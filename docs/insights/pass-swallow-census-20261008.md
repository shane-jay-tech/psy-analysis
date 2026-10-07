# pass 形真吞错全域索引（s1010-38，跨带先行面）

- 日期：2026-10-08 ｜ 性质：**只读索引，零改码**——各带执行仍归各批（批#1=s1007-61 未出、批#3-#6=s1010-01/02/03/04、长尾=s1010-15 域）
- 口径：`except...:` 行的下一行以 `pass` 起始（两行形）；单行形 `except...: pass` 现值 **0**（唯一疑似=ui/quick_entries.py:609 注释提及，s919-13 已修非实码）
- **锚点漂移订正**：任务书口径 124（123＋1 单行形）→ 现值 **126**＝锚命令 123（pass 行尾无注释，`pass$` 过滤器可及）＋**3 注释形**（pass 行带行尾注释，被 `pass$` 漏掉：paper_writer/section_writers.py:1016、questionnaire/design_engine.py:228、ui/heavy_preload.py:23，三处注释均为理由注记=非高敏）；原「1 单行形」实为注释残留非实码
- 总账：**126 处 / 66 文件**；**高敏子集（pass 且无注释理由）＝123 处**；按批：长尾 80、批#4 15、批#6 8、批#5 3、批#3 15、批#1 5

## 索引表（file:line ｜ 批归属 ｜ 高敏）

### 长尾（80 处，高敏 77）

- src/analysis/_sklearn_compat.py:64 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/_sklearn_compat.py:83 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#4（15 处，高敏 15）

- src/analysis/anova.py:48 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/anova.py:397 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/anova.py:415 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/anova.py:452 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/anova.py:457 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/anova.py:578 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/anova.py:705 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/analysis/assumption_router.py:84 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/cfa.py:416 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#4（15 处，高敏 15）

- src/analysis/post_hoc_power.py:61 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/post_hoc_power.py:70 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/post_hoc_power.py:89 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/post_hoc_power.py:95 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/post_hoc_power.py:114 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/regression.py:136 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/analysis/result_card.py:308 ｜ 高敏 ｜ `except (TypeError, ValueError, IndexError):` → `pass`
- src/analysis/runner.py:661 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/runner.py:921 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/runner.py:1076 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#4（15 处，高敏 15）

- src/analysis/sem.py:202 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/analysis/sem.py:211 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/data/inspector.py:43 ｜ 高敏 ｜ `except (ValueError, TypeError):` → `pass`
- src/data/inspector.py:93 ｜ 高敏 ｜ `except (ValueError, TypeError):` → `pass`
### 批#6（8 处，高敏 8）

- src/data/loader.py:330 ｜ 高敏 ｜ `except (ValueError, TypeError):` → `pass`
- src/data/loader.py:414 ｜ 高敏 ｜ `except (ValueError, TypeError):` → `pass`
- src/data/loader.py:448 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/literature_feed/extract/grounding.py:52 ｜ 高敏 ｜ `except (json.JSONDecodeError, ValueError):` → `pass`
### 批#5（3 处，高敏 3）

- src/literature_feed/fetchers/crossref.py:151 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/literature_feed/fetchers/psy_science_official.py:250 ｜ 高敏 ｜ `except (TypeError, ValueError):` → `pass`
- src/literature_feed/scheduler/lock_manager.py:251 ｜ 高敏 ｜ `except OSError:` → `pass`
- src/literature_feed/scheduler/lock_manager.py:257 ｜ 高敏 ｜ `except OSError:` → `pass`
### 批#5（3 处，高敏 3）

- src/literature_feed/trend/scorer.py:173 ｜ 高敏 ｜ `except (TypeError, ValueError):` → `pass`
- src/literature_feed/trend/trending_weights.py:256 ｜ 高敏 ｜ `except OSError:` → `pass`
### 长尾（80 处，高敏 77）

- src/literature_feed/ui/feed_panel.py:554 ｜ 高敏 ｜ `except json.JSONDecodeError:` → `pass`
- src/literature_review/search.py:102 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/literature_review/search.py:121 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/literature_review/themes.py:111 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/literature_review/themes.py:353 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/llm_gateway/gateway.py:271 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/llm_gateway/gateway.py:309 ｜ 高敏 ｜ `except StopIteration:` → `pass`
### 批#6（8 处，高敏 8）

- src/output/docx_exporter.py:386 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/output/docx_exporter.py:1201 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/output/pdf_exporter.py:180 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/output/zip_exporter.py:53 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/output/zip_exporter.py:112 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/output/zip_exporter.py:147 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/paper_writer/literature_crawler.py:424 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/paper_writer/literature_crawler.py:451 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/paper_writer/literature_crawler.py:731 ｜ 高敏 ｜ `except OSError:` → `pass`
- src/paper_writer/literature_manager.py:1532 ｜ 高敏 ｜ `except ImportError:` → `pass`
- src/paper_writer/literature_manager.py:1671 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/paper_writer/literature_search_async.py:115 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/paper_writer/paper_engine.py:759 ｜ 高敏 ｜ `except (LLMUnavailableError, Exception):` → `pass`
- src/paper_writer/paper_engine.py:868 ｜ 高敏 ｜ `except (LLMUnavailableError, Exception):` → `pass`
- src/paper_writer/paper_engine.py:921 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/paper_writer/section_writers.py:602 ｜ 高敏 ｜ `except (ValueError, TypeError):` → `pass`
- src/paper_writer/section_writers.py:1016 ｜ 有注 ｜ `except Exception:` → `pass`
- src/parser/intent_resolver.py:108 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/questionnaire/academic_literature.py:91 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/questionnaire/academic_literature.py:374 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#3（15 处，高敏 15）

- src/questionnaire/ai_content_review.py:322 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/questionnaire/design_engine.py:228 ｜ 有注 ｜ `except Exception:` → `pass`
### 批#3（15 处，高敏 15）

- src/questionnaire/items_loader.py:105 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/questionnaire/items_loader.py:137 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/questionnaire/items_loader.py:153 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/questionnaire/kb_search.py:70 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/questionnaire/kb_search.py:101 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/questionnaire/kb_search.py:227 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/questionnaire/kb_search.py:304 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/questionnaire/llm_engine.py:583 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/questionnaire/llm_engine.py:739 ｜ 高敏 ｜ `except StopIteration:` → `pass`
- src/questionnaire/llm_engine.py:773 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#3（15 处，高敏 15）

- src/questionnaire/llm_engine_premium.py:1244 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/questionnaire/llm_engine_premium.py:1424 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/experiment_design_ui.py:149 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/experiment_design_ui.py:389 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/ui/export_gate.py:42 ｜ 高敏 ｜ `except (TypeError, IndexError):` → `pass`
- src/ui/heavy_preload.py:23 ｜ 有注 ｜ `except Exception:` → `pass`
- src/ui/heavy_preload.py:33 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#1（5 处，高敏 5）

- src/ui/literature_review_panel.py:244 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/literature_review_panel.py:771 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/ui/onboarding.py:44 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/onboarding.py:56 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/onboarding.py:70 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/pages/privacy_gate.py:39 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#3（15 处，高敏 15）

- src/ui/paper_writing_ui.py:316 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#1（5 处，高敏 5）

- src/ui/project_panel.py:43 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#3（15 处，高敏 15）

- src/ui/questionnaire_panel.py:260 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/renderers.py:627 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/ui/session_reset.py:148 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/session_reset.py:154 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/startup_checks.py:26 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#1（5 处，高敏 5）

- src/ui/undergrad_wizard.py:2102 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/undergrad_wizard.py:3042 ｜ 高敏 ｜ `except Exception:` → `pass`
### 长尾（80 处，高敏 77）

- src/ui/upstream_panel.py:138 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/ui/upstream_panel.py:649 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/upstream/feasibility_check.py:520 ｜ 高敏 ｜ `except (LLMUnavailableError, Exception):` → `pass`
- src/upstream/routing.py:158 ｜ 高敏 ｜ `except ValueError:` → `pass`
- src/upstream/socratic_engine.py:288 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/upstream/topic_funnel.py:328 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/evidence_quality.py:316 ｜ 高敏 ｜ `except (ValueError, TypeError):` → `pass`
- src/utils/friendly_errors.py:298 ｜ 高敏 ｜ `except Exception:` → `pass`
### 批#6（8 处，高敏 8）

- src/utils/instance_lock.py:127 ｜ 高敏 ｜ `except OSError:` → `pass`
- src/utils/instance_lock.py:147 ｜ 高敏 ｜ `except OSError:` → `pass`
### 长尾（80 处，高敏 77）

- src/utils/llm_timer.py:30 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/memory_manager.py:160 ｜ 高敏 ｜ `except OSError:` → `pass`
- src/utils/memory_manager.py:190 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/next_step_engine.py:69 ｜ 高敏 ｜ `except (AttributeError, TypeError):` → `pass`
- src/utils/perf_logger.py:64 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/privacy_ethics.py:194 ｜ 高敏 ｜ `except OSError:` → `pass`
- src/utils/project_manager.py:165 ｜ 高敏 ｜ `except OSError:` → `pass`
- src/utils/project_manager.py:400 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/usage_logger.py:256 ｜ 高敏 ｜ `except ImportError:` → `pass`
- src/utils/user_prefs.py:92 ｜ 高敏 ｜ `except OSError:` → `pass`
- src/utils/workspace.py:251 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/workspace.py:329 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/workspace.py:407 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/workspace.py:550 ｜ 高敏 ｜ `except (ValueError, TypeError):` → `pass`
- src/utils/workspace.py:558 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/workspace.py:652 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/workspace.py:704 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/workspace.py:733 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/workspace.py:752 ｜ 高敏 ｜ `except Exception:` → `pass`
- src/utils/workspace.py:777 ｜ 高敏 ｜ `except Exception:` → `pass`

## 复现

```
$ grep -rA1 -n -E "except[^:]*: *$" src --include=*.py | grep -E "pass *$"   # =123（无注释形）
$ python 全量扫（except 行下一行 re ^\s*pass）                            # =126（含 3 注释形）
```
