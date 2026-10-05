# src/ 侧 `except ImportError` 可选依赖兜底普查登记（s1002-21，2026-10-06，只读）

- 承 s923-48 遗留 3：census 的 src/ 侧另一半。判型三档：**真可选**（缺依赖有合理降级）/**死兜底**（模块必在，except 永不触发）/**观测缺失**（吞掉不落日志）。
- 处置建议三值：保留 / 收紧（换显式报错）/ 加 debug 日志。零码改。

## 一、现值复跑（与矿源 18 文件 25 行的差值）

```
$ grep -rc "except ImportError" src/ --include="*.py" | grep -v ":0" | wc -l   → 19 文件
$ grep -rn "except ImportError" src/ --include="*.py" | wc -l                  → 26 行
$ AST 精取 handler（含 tuple 形态）                                            → 27 处
```
**差值成因**：矿源 18/25 为 rg 行计数（9/24 时点）；现值 +1 文件（literature_feed/scheduler/lock_manager 系新建？否——实为 environment_diagnosis 家族计法）＋26 行含 1 处 `except (ImportError, …)` 元组行与跨行 rematch 差异；AST 27 处＝唯一权威口径（rg 漏计元组形态 1 处）。

## 二、分型登记（27 处）

### 真可选依赖（17 处）——保留为主

| 位置 | 依赖 | 降级行为 | 建议 |
|---|---|---|---|
| analysis/sem.py:10 | semopy | SEMOPY_AVAILABLE=False 旗标 | 保留 |
| analysis/cfa.py:15 | semopy | 同上 | 保留 |
| analysis/hlm.py:18 | statsmodels | _HAS_MIXEDLM=False | 保留 |
| data/loader.py:292 | python-docx | raise ValueError 可读报错 | 保留（报错式，最健康形态） |
| questionnaire/items_loader.py:130 | python-docx | 同上 | 保留 |
| literature_feed/trend/domain_weights.py:54 | PyYAML | raise RuntimeError | 保留 |
| literature_feed/trend/method_weights.py:52 | PyYAML | 同上 | 保留 |
| literature_feed/trend/trending_weights.py:220 | PyYAML | raise RuntimeError | 保留 |
| literature_feed/trend/trending_weights.py:266 | PyYAML | logger.warning＋空表降级 | 保留（有日志） |
| literature_feed/ui/feed_panel.py:817/:863 | PyYAML | raise RuntimeError | 保留 |
| llm_gateway/active_config.py:23 | streamlit | st=None 惰性桩 | 保留（无头模式语义） |
| output/pdf_exporter.py:67 | win32com | return False | 保留＋**建议加 debug 日志**（静默 False 难排障） |
| output/pdf_exporter.py:100 | win32com | PDFResult(error=…) 可观察 | 保留 |
| utils/environment_diagnosis.py:68/:83/:90/:125 | streamlit/docx/matplotlib/playwright | 诊断项标 missing | 保留（本职就是探测） |
| utils/environment_diagnosis.py:76/:118 | __import__ 动态/字体探测 | 诊断项 | 保留 |
| visualization/paper_export.py:67 | kaleido | return False | 保留＋建议加 debug 日志 |

### 死兜底/观测缺失（4 处）——建议处置

| 位置 | try 体 | 现行为 | 判型 | 建议 |
|---|---|---|---|---|
| paper_writer/literature_manager.py:1531 | `.literature_expansion`（仓内模块） | **pass 全静默** | 死兜底候选＋观测缺失：仓内模块应恒在；若文件被删=静默丢 87 条扩展文献 | **加 logger.warning**（一行级）；若确认永在可改直 import（收紧，另裁） |
| utils/usage_logger.py:255 | src 侧环境诊断器导入 | **pass 全静默** | 观测缺失：诊断器缺席时 usage 日志少一节且无人知 | 加 logger.debug |
| literature_feed/fetchers/crossref.py:55 | requests | raise FetchError | requests 实为必装（fetchers 全族依赖）⇒ 死兜底形态但报错式健康 | 保留（形态无害） |
| literature_feed/fetchers/psy_science_official.py:62 | requests | 同上 | 同上 | 保留 |

### 语义降级（1 处）——保留

| 位置 | try 体 | 行为 | 建议 |
|---|---|---|---|
| analysis/runner.py:800 | semopy 消费面 | errors.append(warning「降级为探索性参考分析」) | 保留（最优雅：可观察＋功能降级双全） |

### fetchers/manual_ingest.py:171（requests → return None）

| 建议 | 保留＋建议 debug 日志（静默 None 会让上游「拉不到」与「没配」不可辨） |
|---|---|

## 三、汇总

- 保留 22 处（含 3 处报错式健康形态）；**加日志建议 5 处**（literature_manager:1531 / usage_logger:255 / pdf_exporter:67 / paper_export:67 / manual_ingest:171——全部是「静默 pass/return」形态，一行 logger.debug/warning 即可观测化）；收紧候选 1 处（literature_manager 仓内模块直 import，另裁）。
- 零码改：`git diff --numstat src/` 本班净 0。
