# psy-analysis docs/ 索引（INDEX）

- 生成：2026-10-26T19:54（s1023-12 汇编单；复跑脚本 tmp/s1023-12/build_index.py）
- 覆盖：docs/ 全树 **326** 文件（insights 284 / history 29 / 其他子目录 13）
- 字段：日期（文件名后缀>文中 ISO>git 首提）；关联 result＝文件名/标题/前 15 行中的单号；主题＝H1 标题（无则从略）。
- 维护口径：新 insights 件按「<主题>-<yyyymmdd>」命名落 docs/insights/ 后，重跑脚本刷新本档。

## 域分布总览

| 域 | 件数 |
|---|---|
| psy-其他 | 63 |
| s927 裁决批 | 55 |
| 其他 | 48 |
| census普查 | 29 |
| history升级报告 | 25 |
| s930 批 | 19 |
| feed/litfeed | 15 |
| thresholds/信度档位 | 15 |
| session/lock | 13 |
| app-split/交付 | 12 |
| snapshot/备份 | 9 |
| known-issues | 9 |
| e2e/playwright | 6 |
| bare-except/pass吞没 | 4 |
| dead-import/死码 | 4 |

## app-split/交付（12 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/DELIVERY_PACKAGE_GUIDE.md` | 2026-07-14 | — | 交付包使用指南 |
| `docs/architecture/app-split-blueprint.md` | 2026-09-04 | — | app.py 拆分蓝图（psy-E，2026-09-04 夜间产出） |
| `docs/decisions/2026-09-08-debate-paper-writing-dual-entry.md` | 2026-09-08 | — | 论文写作双入口重叠评估（KNOWN_ISSUES #L2 · 2026-09-08） |
| `docs/insights/psy-app-split-1-20260912.md` | 2026-09-12 | h912-12 | psy app.py 编排层拆分第一批报告（h912-12，2026-09-13 夜班）：隐私门搬入 src/ui/pages |
| `docs/insights/psy-app-split-2-20260913.md` | 2026-09-13 | — | psy app 拆分第二批（d913a-43，2026-09-13） |
| `docs/insights/psy-app-split-batch2-20260913.md` | 2026-09-13 | — | psy app 拆分第二批·行为等价断言补齐（d913b-48，2026-09-14） |
| `docs/insights/psy-app-split-batch3-20260914.md` | 2026-09-14 | — | psy app.py 第三批拆分（d914-23 / 20260913-181024-5993 后续，2026-09-14） |
| `docs/insights/psy-delivery-3form-matrix-20260918.md` | 2026-09-18 | s918-05 | psy 交付三形态入口现状矩阵（s918-05 / KNOWN_ISSUES :104 前置输入） |
| `docs/insights/psy-dualentry-overlap-20260918.md` | 2026-09-18 | s918-01 | psy 论文写作双入口重叠面对照报告（s918-01 / #L2 只读评估） |
| `docs/insights/psy-delivery-entry-matrix-20260922.md` | 2026-09-22 | s922-126 | psy 交付入口三形态语义对账矩阵（s922-126，2026-09-22，只读） |
| `docs/insights/psy-dualentry-instrumentation-design-20260922.md` | 2026-09-22 | s922-126 s922-127 | psy #L2 论文双入口埋点方案设计稿（s922-127，2026-09-22，纯设计不落码） |
| `docs/insights/psy-delivery-entry-m1-design-20260923.md` | 2026-09-23 | s922-126 s922-128 s923-35 | psy 交付入口矩阵 M1 / P5 施工方案稿（on_export 零调用）· 2026-09-23 |

## bare-except/pass吞没（4 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/bare-except-batch1-topfiles-20261008.md` | 2026-10-08 | s1007-61 | 批#1 Top 热点件裸 except 判定（s1007-61，含两在途件只读判定） |
| `docs/insights/bare-except-census-571-20261008.csv` | 2026-10-08 | — | — |
| `docs/insights/bare-except-tail-census-20261008.md` | 2026-10-08 | s1010-15 s1010-36 | psy 裸 except 长尾带分型清单（s1010-15 登记面，1-4 带 87 件 195 处） |
| `docs/insights/pass-swallow-census-20261008.md` | 2026-10-08 | s1007-61 s1010-01 s1010-15 s1010-38 s919-13 | pass 形真吞错全域索引（s1010-38，跨带先行面） |

## census普查（29 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/history/COVERAGE_AUDIT.md` | 2026-07-14 | — | 全仓测试覆盖率审查报告 |
| `docs/SYSTEM_OPTIMIZATION_COMPLETION_AUDIT.md` | 2026-08-24 | — | v5.10 系统级优化完成度审计 |
| `docs/insights/paper-writer-audit-20260904.md` | 2026-09-04 | — | 论文写作辅助模块质量审查（psy-C4，2026-09-04） |
| `docs/insights/questionnaire-engine-audit-20260904.md` | 2026-09-04 | — | 问卷设计引擎质量审查（psy-C2，2026-09-04） |
| `docs/insights/apa7-gate-escape-scan-20260905.md` | 2026-09-05 | — | APA7 门禁漏网案例全库扫描（合成边界输入，2026-09-05 夜 1020） |
| `docs/insights/psy-test-blindspot-audit-20260915.json` | 2026-09-15 | — | — |
| `docs/insights/psy-test-blindspot-audit-20260915.md` | 2026-09-15 | — | psy tests/ 覆盖盲区符号级审计（d914-75，只读） |
| `docs/insights/psy-test-naming-audit-20260916.md` | 2026-09-16 | s916-02 | psy 测试目录结构与命名规范审计（s916-02，2026-09-16，只读） |
| `docs/insights/psy-retired-model-scan-20260917.md` | 2026-09-17 | p917-22 | psy 退役模型名残留全仓扫描（r917-22，p917-22 重投） |
| `docs/insights/psy-df-inplace-audit-20260918.md` | 2026-09-18 | s918-09 | psy `session_state['df']` 就地变更风险审计（s918-09，只读） |
| `docs/insights/psy-quick-entries-audit-20260918.md` | 2026-09-18 | s918-27 | quick_entries 快捷分析入口审计（只读，s918-27 附表） |
| `docs/insights/psy-userhome-archive-census-20260922.md` | 2026-09-22 | s920-26 s922-128 | psy 用户主目录 / archive / demo_projects 三区面簿（s922-128，2026-09-22，只读） |
| `docs/insights/psy-alias-centralization-audit-20260923.md` | 2026-09-23 | s923-45 | psy：method_catalog「别名集中」声明 vs 各层私有别名表 —— 裁决材料 |
| `docs/insights/psy-census-values-recheck-20260923.md` | 2026-09-23 | s920-12 s922-11 s923-02 | psy 构念普查四数值只读复核（s923-02 · 2026-09-23） |
| `docs/insights/psy-docx-constants-dossier-20260923.md` | 2026-09-23 | s922-22 s923-18 | psy docx 两常量说谎裁决材料（`SPACE_AFTER_BODY_PT` / `TABLE_HEADER_FILL`）· s923-18 · 2026- |
| `docs/insights/psy-nextstep-heuristics-dossier-20260923.md` | 2026-09-23 | s923-31 | psy next_step 引擎三反直觉判据裁决材料（s923-31，只读） |
| `docs/insights/psy-pii-extension-dossier-20260923.md` | 2026-09-23 | s922-124 s923-33 | psy 座机分机号脱敏残留裁决材料（s923-33，只读设计稿） |
| `docs/insights/psy-qpanel-parallel-impl-census-20260923.md` | 2026-09-23 | s921-07 s922-02 s923-22 | psy 问卷设计页两份平行实现漂移普查（s923-22，只读） |
| `docs/insights/psy-power-sibling-fallback-census-20260924.md` | 2026-09-24 | s924-05 | psy post_hoc_power 四处同型兜底 census（只读落档 · 2026-09-25 实测） |
| `docs/insights/psy-untracked-tests-census-20260924.md` | 2026-09-24 | s922-134 s923-05 s924-06 s924-08 s924-29 s924-31 | psy「untracked 测试件」红用例普查（s924-31 · 只读） |
| `docs/insights/psy-exploratory-confirmatory-census-20260925.md` | 2026-09-25 | — | 探索性／确认性检验盘点与校正方式标注（信箱单 20260925-120703-44a0） |
| `docs/insights/psy-from-dict-census-adjudication-20260925.md` | 2026-09-25 | s924-64 | psy `def from_dict` 11 处散布 census 与收敛裁决材料（只读） |
| `docs/insights/psy-keyword-dual-source-census.md` | 2026-09-25 | s924-67 | psy 关键词双源 census：`parser/keyword_dict`（检验触发词）vs `questionnaire/construct_kb.CONS |
| `docs/insights/s927-08-dirty-audit.md` | 2026-09-27 | s924-36 s927-02 s927-08 | s927-08 — psy 脏树收口审计：12 枚在途件归属与提交清单（只读·零 git 操作） |
| `docs/insights/s930-26-logging-assembly-census.md` | 2026-10-02 | s927-44 s930-26 | 生产无 root 日志装配 105 处同族普查材料 |
| `docs/insights/psy-scripts-batps1-driveletter-census-20261006.md` | 2026-10-06 | s1002-20 s923-11 s924-14 | psy scripts/ .bat/.ps1 绝对盘符与 POSIX 重定向只读普查（s1002-20，2026-10-06） |
| `docs/insights/psy-src-importerror-census-20261006.md` | 2026-10-06 | s1002-21 s923-48 | src/ 侧 `except ImportError` 可选依赖兜底普查登记（s1002-21，2026-10-06，只读） |
| `docs/insights/fstring-ast-census-20261008.md` | 2026-10-08 | s1004-06 s1007-12 s1007-28 | f-string/隐式 str() 内嵌消费 AST 全量普查（s1007-28） |
| `docs/insights/llm-engine-twins-census-20261008.md` | 2026-10-08 | s1010-13 s1010-37 | llm_engine 双胞胎架构普查（s1010-37，只读材料零改码） |

## dead-import/死码（4 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/psy-dead-code-dossier-20260923.md` | 2026-09-23 | s922-15 s923-07 | psy 死码裁决材料包 · `generate_design_summary` ＋ `get_test_name_zh`（s923-07，2026-09-23） |
| `docs/insights/dead-import-batch-a-20261008.md` | 2026-10-08 | s1010-05 | psy 死 import 新矿批 A 三栏清单（s1010-05） |
| `docs/insights/dead-import-batch-b-20261008.md` | 2026-10-08 | s1010-06 | psy 死 import 新矿批 B 三栏清单（s1010-06） |
| `docs/insights/undergrad-wizard-dead-imports-20261008.md` | 2026-10-08 | s1007-20 s1010-07 | undergrad_wizard 死 import 人工定性材料＋heavy_preload 销案登记（s1010-07 降级腿，只读零删） |

## e2e/playwright（6 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/playwright-readiness-20260911.md` | 2026-09-11 | — | psy Playwright 离线就绪盘点 + 日间执行清单（2026-09-12 夜间执行班，任务 p911r-36） |
| `docs/insights/psy-e2e-subset-order-20260913.md` | 2026-09-13 | — | psy e2e 子集顺序依赖：根因定位与最小修复（2026-09-13，d913a-44 材料 + d913b-47 修复） |
| `docs/insights/psy-e2e-skip-inventory-20260914.md` | 2026-09-14 | — | psy 浏览器 E2E 跳过项清点（d914-38，2026-09-14，只读） |
| `docs/insights/psy-e2e-skip26-roster-20260922.md` | 2026-09-22 | s922-137 | psy 浏览器 E2E「26 skipped」清单快照（s922-137，2026-09-23 实取） |
| `docs/insights/s930-21-playwright-pin.md` | 2026-10-02 | s927-27 s930-21 | playwright 钉法与浏览器族 36 例现状材料 |
| `docs/insights/psy-apptest-download-assert-design-20261006.md` | 2026-10-06 | s1002-25 s921-12 s924-01 | AppTest download_button 载荷断言口设计（s1002-25，2026-10-06） |

## feed/litfeed（15 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/psy-litfeed-assets-20260918.md` | 2026-09-18 | s918-55 | psy `data/literature_feed` 本地资产与陈旧锁盘点（s918-55，只读） |
| `docs/insights/psy-feed-logs-dir-design-20260922.md` | 2026-09-22 | s922-131 s923-10 | psy `literature_feed/logs/` 死目录处置设计稿（s922-131，**只读：零删除、零建目录、零落码**） |
| `docs/insights/psy-litfeed-data-plane-probe-20260922.md` | 2026-09-22 | s922-17 s927-49 s930-51 | literature_feed 数据面停摆下钻：调度器从未触发（A3 探针结论，2026-09-22） |
| `docs/insights/psy-feed-predicate-dossier-20260923.md` | 2026-09-23 | s922-107 s923-24 | psy 文献雷达「徽章 vs 一键批准」双谓词不一致裁决材料（s923-24，只读） |
| `docs/insights/psy-feed-scheduler-attribution-20260923.md` | 2026-09-23 | s922-17 s923-10 | psy literature_feed `trigger='scheduler'` 28 次触发的入口归因（只读取证，2026-09-23） |
| `docs/insights/psy-feed-source-census-20260923.md` | 2026-09-23 | s922-17 s923-13 | psy 文献雷达源侧普查：`acta_psych_sinica` 为何 0 篇（2026-09-23，只读核查） |
| `docs/insights/psy-feed-zombie-runs-20260923.md` | 2026-09-23 | s922-17 s923-10 s923-12 | psy `fetch_runs` run 39/40「僵尸 running」根因（只读，2026-09-23） |
| `docs/insights/psy-feed-doi-prefix-verdict-20260924.md` | 2026-09-24 | s922-17 s923-13 s924-19 | psy feed `doi_prefix` 死配置处置裁决材料（s924-19 · 只读复核） |
| `docs/insights/psy-feed-empty-raw-observability-20260924.md` | 2026-09-24 | s923-13 s924-14 s924-18 | psy feed 空响应 raw 可观测性设计稿（s924-18 · 2026-09-25 · 只读出稿） |
| `docs/insights/psy-feed-run-fingerprint-design-20260924.md` | 2026-09-24 | s923-10 s923-13 s924-15 s924-17 | psy feed run 进程指纹字段设计稿（s924-17 · 2026-09-25 · 只读出稿） |
| `docs/insights/psy-feed-ttl-caliber-20260924.md` | 2026-09-24 | s923-12 s924-16 | psy feed 双 TTL 口径裁决档：3600 判活 vs 21600 判抢（s924-16 · 只读） |
| `docs/insights/psy-litfeed-evidence-loss-rollback-20260924.md` | 2026-09-24 | s923-10 s923-12 s923-13 | psy `data/literature_feed/` 证据损失登记 ＋ 回滚可行性核对（pd05，2026-09-24，只读·零改动） |
| `docs/insights/s927-50-feed-strategy.md` | 2026-09-28 | s923-13 s924-36 s927-50 | 文献推送 `from-issued-date` 策略三选裁决材料：三案的抓取覆盖差异与成本（2026-09-28，只读登记） |
| `docs/insights/feed-st-harness-summary-shape-20261005.md` | 2026-10-05 | s1004-49 s930-15 | exporters panel／summary 件 st-harness 同形冗余核对（s930-15 遗留，备用）——s1004-49 |
| `docs/insights/feedback-package-reachability-20261005.md` | 2026-10-05 | s1004-46 | export_feedback_package UI 不可达 × 交付入口矩阵 并案裁决材料（1b5e 遗留）——s1004-46 |

## history升级报告（25 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/history/SELF_ASSESSMENT_REPORT.md` | 2026-05-16 | — | 心理学研究工具系统 v2.0 — 完整自评报告（历史快照） |
| `docs/history/UPGRADE_REPORT.md` | 2026-05-16 | — | 心理学研究工具系统 v2.1 — 深度升级自评报告 |
| `docs/history/UPGRADE_REPORT_V2.2.md` | 2026-05-16 | — | 心理学研究工具系统 v2.2 — 深度升级自评报告 |
| `docs/history/UPGRADE_REPORT_V2.3.md` | 2026-05-16 | — | 心理学研究工具系统 v2.3 — 本科使用体验优化自评报告 |
| `docs/history/UPGRADE_REPORT_V2.4.md` | 2026-05-16 | — | 心理学研究工具系统 v2.4 — 本科体验深化自评报告 |
| `docs/history/UPGRADE_REPORT_V2.5.md` | 2026-05-17 | — | 心理学研究工具系统 v2.5 — 体验断层修补自评报告 |
| `docs/history/UPGRADE_REPORT_V2.7.md` | 2026-05-17 | — | Psy Analysis v2.7 升级报告 |
| `docs/history/UPGRADE_REPORT_V2.8.md` | 2026-05-17 | — | Psy Analysis v2.8 升级报告 |
| `docs/history/UPGRADE_REPORT_V2.9.md` | 2026-05-17 | — | Psy Analysis v2.9 升级报告 |
| `docs/history/UPGRADE_REPORT_V3.0.md` | 2026-05-17 | — | Psy Analysis v3.0 升级报告 |
| `docs/history/UPGRADE_REPORT_V3.1.md` | 2026-05-17 | — | Psy Analysis v3.1 升级报告 |
| `docs/history/UPGRADE_REPORT_V3.2.md` | 2026-05-17 | — | v3.2 升级报告 — 选题漏斗 + AI 苏格拉底（2026-05-17） |
| `docs/history/UPGRADE_REPORT_V3.3.md` | 2026-05-17 | — | v3.3 升级报告 — 巩固 v3.2 上游成果（2026-05-17） |
| `docs/history/UPGRADE_REPORT_V3.4.md` | 2026-05-17 | — | v3.4 升级报告 — 启动文献综述工作台（2026-05-17） |
| `docs/history/UPGRADE_REPORT_V3.5.md` | 2026-05-18 | — | v3.5 升级报告 — 巩固重构与质量提升（2026-05-18） |
| `docs/history/UPGRADE_REPORT_V3.6.md` | 2026-05-18 | — | v3.6 升级报告 — 流式输出 + 哲学统一 + 关键词 LLM 辅助（2026-05-18） |
| `docs/history/UPGRADE_REPORT_V3.7.md` | 2026-05-22 | — | v3.7 升级报告 — 信效度补全 + 体验债清零（2026-05-22 ~ 05-23） |
| `docs/history/UPGRADE_REPORT_V3.8.md` | 2026-05-23 | — | v3.8 升级报告：产品力打磨 — Fallback / 痕迹检测 / 个性化答辩 / E2E 测试 |
| `docs/history/UPGRADE_REPORT_V3.9.md` | 2026-05-23 | — | v3.9 升级报告：UI 接入 + 隐私守门 + 依赖锁 |
| `docs/history/UPGRADE_REPORT_V5.8.md` | 2026-08-15 | — | v5.8 升级报告：启动/加载性能优化 + 关键 Bug 修复 |
| `docs/history/UPGRADE_REPORT_V5.9.md` | 2026-08-15 | — | v5.9 升级报告：交互性能深化 + 图表崩溃修复 + 误触防护 |
| `docs/SYSTEM_REPORT.md` | 2026-08-24 | — | Psy-Analysis 系统报告 |
| `docs/history/UPGRADE_REPORT_V5.10.md` | 2026-08-24 | — | v5.10 升级报告：研究路径接通 + 安全工作区 + 新手体验恢复 |
| `docs/insights/generate-missing-report-dead-20261005.md` | 2026-10-05 | s1004-39 | generate_missing_report 零调用方判死与处置裁决材料（ae49 遗留）——s1004-39 |
| `docs/insights/health-report-wiring-20261008.md` | 2026-10-08 | s1007-11 s1007-33 | health_report 生产-消费接线取证（s1007-33） |

## known-issues（9 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/known-issues-doc-alignment-20260905.md` | 2026-09-05 | — | KNOWN_ISSUES 与 KNOWN_LIMITATIONS 双文档漂移核对（只读评审，2026-09-05 夜 1021） |
| `docs/KNOWN_LIMITATIONS.md` | 2026-09-09 | — | 已知限制与降级策略 |
| `docs/insights/psy-known-issues-101-rewrite-20260913.md` | 2026-09-13 | p912-30 | psy KNOWN_ISSUES.md:101 行文订正（d913c-33，2026-09-13）——已被同任务族完成，本单按冲突条款出比对 |
| `docs/insights/psy-known-104-105-20260916.md` | 2026-09-16 | — | psy KNOWN_ISSUES.md:104/:105 现状核验与处置方向（n916x-31，零改码） |
| `docs/insights/psy-knownissues-reorg-20260918.md` | 2026-09-18 | s918-01 s918-02 s918-08 | psy KNOWN_ISSUES「仍未修复」章节状态漂移审计＋重组稿（s918-08） |
| `docs/insights/psy-knownissues-v512-20260920.md` | 2026-09-20 | s918-08 s919-15 s921-17 | psy KNOWN_ISSUES「仍未修复」节状态刷新 v2（s921-17，只读复核稿·留日间放行） |
| `docs/insights/psy-known-issues-boundary-rows-audit-20260923.md` | 2026-09-23 | s923-43 | psy KNOWN_ISSUES「已知功能边界」表逐行核销取证（2026-09-24 执行，单号 s923-43） |
| `docs/insights/s927-09-knownissues-health.md` | 2026-09-25 | s927-09 | s927-09 — KNOWN_ISSUES.md 现行 P1／P2 条目健康度盘点（只读·零改动本体） |
| `docs/insights/s927-66-knownreds-ledger.md` | 2026-09-29 | s927-66 | s927-66 · psy 台账在册红归因汇编（一页清单，供主班排消红单） |

## psy-其他（63 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/psy-autosave-timer-semantics-20260913.md` | 2026-09-13 | — | autosave 节流计时语义核对与测试（d913b-49） |
| `docs/insights/psy-benchmark-score-backfill-20260913.md` | 2026-09-13 | — | psy 基准首跑分数档位补记＋调用台账与 cost_log 对账（b-50，2026-09-13，只读） |
| `docs/insights/psy-perf-smoke-contract-test-20260915.md` | 2026-09-15 | — | perf_smoke --json 契约回归测试补记（d914-73，2026-09-15） |
| `docs/insights/psy-benchmark-sidecar-edges-20260916.md` | 2026-09-16 | — | psy benchmark side-car 补评落盘契约补测扩展（n916x-32） |
| `docs/insights/psy-insights-untracked-20260916.md` | 2026-09-16 | — | psy docs/insights 未入库报告盘点与收口清单（n916x-30，只读） |
| `docs/insights/psy-apa7-manual-string-converge-20260917.md` | 2026-09-17 | — | questionnaire 侧手工拼 APA7 串收敛核验＋现状钉测（916p-a4-005，2026-09-17） |
| `docs/insights/psy-baseline-number-reconcile-20260917.md` | 2026-09-17 | — | psy 测试基线数字「2544」三文档对账（916p-a4-001，2026-09-17） |
| `docs/insights/psy-baseline-recheck-20260917.md` | 2026-09-17 | — | psy 测试基线数字复核（917-34） |
| `docs/insights/psy-error-messages-tests-20260917.md` | 2026-09-17 | — | error_messages.py 特征化测试（916p-a4-004，2026-09-17，只增测试） |
| `docs/insights/psy-literature-tests-impl-20260917.md` | 2026-09-17 | — | psy literature_manager 盲区测试实现报告（916-04，2026-09-17） |
| `docs/insights/psy-prune-archive-fix-20260917.md` | 2026-09-17 | — | psy prune_archive docstring/实现不符收敛＋is_dir 守卫（917-33） |
| `docs/insights/psy-prune-archive-guard-20260917.md` | 2026-09-17 | — | prune_archive.py 保留策略取证＋tmp 隔离安全测试（916p-a4-007，2026-09-17） |
| `docs/insights/psy-readme-env-drift-20260917.md` | 2026-09-17 | — | psy README 环境变量与命令声明对账（916p-a4-006，2026-09-17） |
| `docs/insights/psy-uncommitted-signoff-20260917.md` | 2026-09-17 | — | psy 未提交改动签核清单（916p-a4-003，2026-09-17，只读盘点） |
| `docs/insights/psy-untracked-triage-20260917.md` | 2026-09-17 | p917-37 | psy 全仓未跟踪文件盘点（r917-37，p917-37 重投） |
| `docs/insights/psy-apppy-split-roadmap-20260918.md` | 2026-09-18 | s918-06 s922-103 s922-18 s922-23 s923-14 | psy app.py 页面控制器拆分路线图（s918-06 只读前置） |
| `docs/insights/psy-baseline-recount-20260918.md` | 2026-09-18 | s918-07 | psy 测试基线数字复核＋:38 订正稿（s918-07） |
| `docs/insights/psy-benchmark-history-recheck-20260918.md` | 2026-09-18 | s918-56 | psy `data/benchmark_history` 台账现状复核（s918-56，只读） |
| `docs/insights/psy-deepseek-baseurl-trace-20260918.md` | 2026-09-18 | s918-15 | psy `DEEPSEEK_BASE_URL` 读取链取证（s918-15，只读） |
| `docs/insights/psy-insights-untracked-refresh-20260918.md` | 2026-09-18 | s918-19 | psy docs/insights 未入库清单刷新＋精确入库命令（s918-19，只读） |
| `docs/insights/psy-l3-drift-verify-20260918.md` | 2026-09-18 | s918-02 | psy #L3 漂移观测真实状态核验＋KNOWN_ISSUES 订正稿（s918-02） |
| `docs/insights/psy-nested-zcodebridge-triage-20260918.md` | 2026-09-18 | s918-17 | psy 仓内嵌套 zcode-bridge 目录定性（s918-17，只读） |
| `docs/insights/psy-pytest-swallow-diagnosis-20260918.md` | 2026-09-18 | s918-51 | psy「pytest 终端汇总行被吞」诊断（s918-51，只读） |
| `docs/insights/psy-questionnaire-panel-testdesign-20260918.md` | 2026-09-18 | s918-28 | questionnaire_panel 渲染页测试设计稿（只读，s918-28） |
| `docs/insights/psy-sidecar-makedirs-design-20260918.md` | 2026-09-18 | s918-13 | psy side-car 落盘「目录不存在自动创建」增强设计稿（s918-13，只读不落码） |
| `docs/insights/psy-data-dirs-20260919.md` | 2026-09-19 | s920-26 | psy `data/` 全子目录面簿普查（s920-26，**只读，零删除**） |
| `docs/insights/psy-dfinplace-blindspot-20260919.md` | 2026-09-19 | s918-09 s919-10 | psy df in-place 审计盲区扩展（s919-10，只读审计，零代码改动） |
| `docs/insights/psy-psychopy-reforder-20260919.md` | 2026-09-19 | s919-01 s920-02 | PsychoPy 生成脚本「引用-定义序」静态审计（s920-02，只读） |
| `docs/insights/psy-timesensitive-20260919.md` | 2026-09-19 | s919-21 s920-24 | psy 时敏断言专项清点（s920-24，wall clock 现算值做相等断言） |
| `docs/insights/psy-dirtynum-rescore-material-20260921.md` | 2026-09-21 | s920-13 s921-09 s922-05 | psy 脏数字整页红 ＋ rescore 无 try：复现与最小防御草案（s922-05 材料单，2026-09-21） |
| `docs/insights/psy-test-baseline-20260921.md` | 2026-09-21 | n922-11 s921-12 | psy-analysis 全量测试基线快照（2026-09-22 凌晨实跑，s921-12 的 3250 口径复核） |
| `docs/insights/psy-benchmark-observe-20260922.md` | 2026-09-22 | s922-19 | psy #L3 benchmark 观测面对账事实表（s922-19，2026-09-22 只读） |
| `docs/insights/psy-cfa-obj-fix-design-20260923.md` | 2026-09-23 | s923-08 | psy CFA `obj=` 缺陷修复设计稿（s923-08 · 2026-09-23） |
| `docs/insights/psy-docx-style-unify-design-20260923.md` | 2026-09-23 | s922-22 s923-19 | psy 两路 docx 样式统一样式源设计稿（exporters vs docx_exporter） |
| `docs/insights/psy-i18n-runtime-probe-20260923.md` | 2026-09-23 | s922-21 s923-17 | psy i18n `t()` 运行期 key 直方图探针（24 悬置键取证）· s923-17 · 2026-09-23 |
| `docs/insights/psy-logs-dir-portrait-20260923.md` | 2026-09-23 | s923-53 | psy 根 `logs/` 现值画像 ＋ `junit_v59.xml` 陈旧产物处置建议（s923-53，只读） |
| `docs/insights/psy-power-solver-redesign-20260923.md` | 2026-09-23 | s923-03 | psy power_analysis 求解器缺陷修复设计稿（s923-03 · 2026-09-23） |
| `docs/insights/psy-quick-models-retired-drift-20260923.md` | 2026-09-23 | s923-52 | psy `quick_models` 快捷预设 vs 退役阵容漂移 · 裁决材料（s923-52） |
| `docs/insights/psy-relay-log-schema-20260923.md` | 2026-09-23 | s922-09 s922-19 s923-16 | psy relay 日志扩字段设计稿（case_id / 耗时 / 错误体）· s923-16 · 2026-09-23 |
| `docs/insights/psy-smart-fallback-twin-verdict-20260923.md` | 2026-09-23 | s923-51 | psy `chat_with_smart_fallback` 零调用孪生出口 · 三案裁决材料 |
| `docs/insights/psy-userhome-write-attribution-20260923.md` | 2026-09-23 | s922-128 s923-36 | psy userhome `index.json` 重写与 feed WAL 触点归因（H1／H5）· 2026-09-23 |
| `docs/insights/psy-data-hygiene-20260924.md` | 2026-09-24 | s924-70 | psy `data/` 治理对账单：kaoyan.db 孤儿归因＋raw 轮转＋wal 体检＋benchmark 草稿件裁决 |
| `docs/insights/psy-dup-method-text-tables-20260924.md` | 2026-09-24 | s923-07 s924-11 | psy 检验方法「名称／文案」多表盘点：`get_test_name_zh` vs `app_pages_text` 单一来源裁决材料 |
| `docs/insights/psy-font-family-stacks-20260924.md` | 2026-09-24 | s923-19 s924-27 | psy 字体族栈普查与并轨裁决材料（s924-27 · 只读） |
| `docs/insights/psy-skipif-reality-20260924.md` | 2026-09-24 | s924-71 | psy `skipif` 依赖实况对账：kaleido／playwright 已装画像＋`socratic_quality` 死件裁决 |
| `docs/insights/psy-data-dictionary-20260925.md` | 2026-09-25 | — | psy 数据字典 v1 · 题号／变量名／量表／维度／量尺／反向题／缺失值编码 |
| `docs/insights/psy-defense-qa-duplicate-question-adjudication-20260925.md` | 2026-09-25 | s922-114 s924-56 s924-58 | psy 答辩题库「同题 4 组 9 条」冗余合并裁决材料（只读） |
| `docs/insights/psy-field-lineage-20260925.md` | 2026-09-25 | — | 分析字段血缘登记表 v1（信箱单 20260925-120653-3298） |
| `docs/insights/psy-report-fields-unification-20260925.md` | 2026-09-25 | — | psy 报告字段统一 v1 · alpha／omega／项目数／样本量／置信区间 |
| `docs/insights/psy-archive-warning-rerun-verdict-20261006.md` | 2026-10-06 | s1002-40 s920-23 | 归档警告 × st.rerun 时序三案裁决材料（s1002-40，只读） |
| `docs/insights/psy-consistency-issues-wiring-verdict-20261006.md` | 2026-10-06 | s1002-47 s923-31 | consistency_issues 就绪评分死链接线裁决材料（s1002-47，三处一体，只读） |
| `docs/insights/psy-constructkb-dup-domain-verdict-20261006.md` | 2026-10-06 | s1002-38 s920-12 | 构念库 name_en 撞车与域标签两写法数据口径裁决材料（s1002-38，只读） |
| `docs/insights/psy-defenseqa-categories-placeholders-verdict-20261006.md` | 2026-10-06 | s1002-41 s924-56 s924-57 | defense_qa REQUIRED_CATEGORIES 4→6 与 placeholders 双口径裁决材料（s1002-41，只读） |
| `docs/insights/psy-get-title-by-kbid-verdict-20261006.md` | 2026-10-06 | s1002-35 s920-04 | merged 回显目标标题：FeedStore get_title_by_kb_id 接口裁决材料（s1002-35，只读） |
| `docs/insights/psy-groupvar-ternary-verdict-20261006.md` | 2026-10-06 | s1002-42 s922-122 | result_card :1412 三元式吞 group_var 裁决材料（s1002-42，2026-10-06，只读） |
| `docs/insights/psy-logistic-tableroute-verdict-20261006.md` | 2026-10-06 | s1002-16 s1002-46 s923-43 | result_card Logistic 族异常静默与 table_group 路由不同源裁决材料（s1002-46，只读） |
| `docs/insights/psy-matrix-heuristics-verdict-20261006.md` | 2026-10-06 | s1002-45 s922-121 | matrix 切句与局限关键词两启发式裁决材料（s1002-45，只读） |
| `docs/insights/psy-recommend-wordbound-verdict-20261006.md` | 2026-10-06 | s1002-43 s922-113 s923-27 | recommend_template 子串收紧乙案裁决材料（s1002-43，只读） |
| `docs/insights/psy-report-format-batch2-verdict-20261006.md` | 2026-10-06 | s1002-44 s922-116 s922-117 s924-60 | 心理学报规约接入第二批与 write_keywords 窗口裁决材料（s1002-44，只读） |
| `docs/insights/psy-review-status-sourcesync-verdict-20261006.md` | 2026-10-06 | s1002-34 s920-03 | review 状态表 × 决策白名单同源化裁决材料（s1002-34，2026-10-06，只读） |
| `docs/insights/psy-usagelogger-alert-gaps-20261006.md` | 2026-10-06 | s1002-33 s920-07 s924-66 | usage_logger 告警面余留三缺口裁决材料（s1002-33，2026-10-06，只读） |
| `docs/insights/psy-wizard-afg-1819-verdict-20261006.md` | 2026-10-06 | s1002-39 s920-15 | 向导假设检验 ⑱/⑲ 两缺陷裁决材料（s1002-39，2026-10-06，只读） |
| `docs/insights/psy-schtasks-recheck-20261008.md` | 2026-10-08 | s1007-01 s1007-38 | psy schtasks 盘点快照复核（s1007-38 追加时点节） |

## s927 裁决批（55 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/s927-04-n-and-ci-design.md` | 2026-09-26 | s927-04 | s927-04 · 逐对 n 输出契约 与 非参数效应量 CI 补齐路径（设计稿，零码改动） |
| `docs/insights/s927-01-invalid-values-adjudication.md` | 2026-09-27 | s927-01 | s927-01 · 问卷导入三条非法值静默计分缺陷：裁决材料（现网已改版，本单收窄为「已付成本核对＋未决剩余项」） |
| `docs/insights/s927-02-posthoc-p-adjudication.md` | 2026-09-27 | s927-01 s927-02 | s927-02 · 事后多重比较 p 值显示规则：裁决材料（44a0 卷宗三条） |
| `docs/insights/s927-05-field58-triage.md` | 2026-09-27 | s927-05 | s927-05 · 「报告字段读不到 58 个」三分栏登记单（只出分类与建议，零码改动） |
| `docs/insights/s927-06-conclusion-gate.md` | 2026-09-27 | s927-06 | s927-06 · conclusion_gate 接线窗口裁决材料（三闸口对照＋门禁同步草案＋推荐形状，零码改动） |
| `docs/insights/s927-12-deps-consistency.md` | 2026-09-27 | s927-12 | s927-12 — requirements-lock.txt 在途变更 × `_sklearn_compat.py` 依赖一致性核查（只读·零码改动） |
| `docs/insights/s927-13-socratic-replay.md` | 2026-09-27 | s927-08 s927-13 | s927-13 psy 苏格拉底基准离线回放现状复测（B-098 链健康度） |
| `docs/insights/s927-14-literature-regression.md` | 2026-09-27 | s927-14 | s927-14 psy 文献工具链（literature_manager / format_reference）回归子集复测 |
| `docs/insights/s927-15-pytestini.md` | 2026-09-27 | s927-15 | s927-15 `pytest.ini` 在途修改对收集面的影响核查 |
| `docs/insights/s927-16-guardrails-adjudication.md` | 2026-09-27 | s927-16 | s927-16 四道统计护栏零调用：接线裁决材料（只读取证，零码改动） |
| `docs/insights/s927-17-isfalse-adjudication.md` | 2026-09-27 | s927-17 | s927-17 `assumption_router` 的 `is False` 身份比较：修法裁决材料（只读取证，零码改动） |
| `docs/insights/s927-18-assumption-coverage.md` | 2026-09-27 | s924-36 s927-16 s927-17 s927-18 | s927-18 方差分析前提覆盖缺口：「方法×前提」矩阵与补齐优先级（只读取证，零码改动） |
| `docs/insights/s927-19-seed-lineage.md` | 2026-09-27 | s927-19 | s927-19 · seed 不进产物：三处改动的血缘影响清单＋迁移材料（零码改动，154316-1） |
| `docs/insights/s927-20-moderation-adjudication.md` | 2026-09-27 | s927-20 | s927-20 · `_build_moderation` 恒落 else：字段缺失清单＋适配器缺口＋三案裁决材料（零码改动，154316-2） |
| `docs/insights/s927-22-winsorize-adjudication.md` | 2026-09-27 | s927-22 | s927-22 · Winsorize／异常值排除的产品化口径：现状梳理＋三案裁决材料＋样本量披露设计（零码改动，154319） |
| `docs/insights/s927-23-missing-strategy-design.md` | 2026-09-27 | s927-23 | s927-23 设计稿：listwise 默认下 `missing_strategy` 的暴露形态（154310-2 案一） |
| `docs/insights/s927-10-golden-coupling.md` | 2026-09-28 | s927-10 | s927-10 —— `tests/test_cfa_sem_golden.py` × `src/analysis/cfa.py` 在途 diff 的耦合性质审 |
| `docs/insights/s927-21-missing-spec.md` | 2026-09-28 | s927-21 | s927-21 —— 缺失机制判定（MCAR／MAR／MNAR）三组件实现规格 |
| `docs/insights/s927-24-placeholder-debt.md` | 2026-09-28 | s927-24 | s927-24 —— `_METHOD_ASSUMPTIONS` placeholder 债清单（两类）＋登记修正草案 |
| `docs/insights/s927-26-note.md` | 2026-09-28 | s922-02 s922-138 s922-139 s924-37 s927-26 s927-33 | s927-26 · Premium 链时钟回拨 anomaly 接线（复核结论：已由 s922-139 提前闭合，本班零生产码改动） |
| `docs/insights/s927-28-guard13.md` | 2026-09-28 | s922-04 s922-108 s927-28 | s927-28 · 恢复路径按案 a 收口「他键守卫」点位（含 13→11 的复数与逐点表） |
| `docs/insights/s927-29-dirtynum-ab.md` | 2026-09-28 | s922-05 s927-29 | s927-29 · dirtynum A＋B 施工记录（波次 43 写位班，2026-09-28） |
| `docs/insights/s927-30-note.md` | 2026-09-28 | s922-07 s927-30 | s927-30 · bulk_review「成功 x/N」回显＋异常计数透出（波次 43 写位班，2026-09-28） |
| `docs/insights/s927-33-relaylog-schema.md` | 2026-09-28 | s922-104 s922-19 s923-16 s927-33 | `_relay_calls.jsonl` 日志粒度补齐 · 裁决材料（s927-33 · 2026-09-28） |
| `docs/insights/s927-34-note.md` | 2026-09-28 | s922-07 s922-105 s922-107 s927-34 | s927-34 · s922-105/107 判据翻正接线核查（波次 43，2026-09-28）＝**blocked：R1/R2 未放行落地** |
| `docs/insights/s927-36-endore-adjudication.md` | 2026-09-28 | s920-0 s920-01 s920-1 s920-15 s922-11 s927-36 | `s920-01…14` 终态补记 · 裁决材料（s927-36 · 2026-09-28） |
| `docs/insights/s927-37-note.md` | 2026-09-28 | s922-04 s922-112 s927-37 | s927-37 · 快照 27 键人工回写（s922-112 遗留 2 的落地） |
| `docs/insights/s927-39-nextstep3.md` | 2026-09-28 | s922-119 s927-39 | nextstep 三处反直觉行为 · 逐处治理/文档化裁决材料（s927-39 · 2026-09-28） |
| `docs/insights/s927-40-solven-adjudication.md` | 2026-09-28 | s927-40 | s927-40 · `power_analysis` 异常吞掉缺陷裁决材料（只读出材料 · 2026-09-28） |
| `docs/insights/s927-42-boundary-tighten.md` | 2026-09-28 | s924-03 s927-42 | s927-42 · 构念数下界收紧裁决材料（只读落档 · 2026-09-28） |
| `docs/insights/s927-43-bytes-contract.md` | 2026-09-28 | s923-04 s927-43 | s927-43 exporters bytes/bytearray 契约归一 —— 裁决材料（零码改动） |
| `docs/insights/s927-46-summary-adjudication.md` | 2026-09-28 | s923-07 s924-41 s927-46 | s927-46 `generate_design_summary` 接线裁决材料（三问逐问，只出材料不选案） |
| `docs/insights/s927-47-chi2-review-request.md` | 2026-09-28 | s927-47 | s927-47 · chi2 区间 [60,120] vs 实测 44.511：多模型复核请求材料（2026-09-28） |
| `docs/insights/s927-48-note.md` | 2026-09-28 | s927-48 | s927-48 · `run_daily_feed.bat` chcp 重定向目检结论（不坏，登记） |
| `docs/insights/s927-49-run3940-revoke.md` | 2026-09-28 | s923-12 s927-49 | s927-49 · run 39/40 僵尸态写库诉求：**撤销确认单**（2026-09-28） |
| `docs/insights/s927-51-space-after-body.md` | 2026-09-28 | s923-18 s927-51 | SPACE_AFTER_BODY_PT 三案裁决材料（s927-51·B′ 论证复核，前后输出对照实测版） |
| `docs/insights/s927-55-note.md` | 2026-09-28 | s924-06 s927-55 | s927-55 · `build_questionnaire_pdf` 尾部恒真死分支清理（1 语句行归一） |
| `docs/insights/s927-31-merge-adjudication.md` | 2026-09-29 | s922-102 s924-37 s927-31 | s927-31 · 问卷设计重复建设并单裁决材料 |
| `docs/insights/s927-38-note.md` | 2026-09-29 | s923-30 s927-38 | s927-38 environment_diagnosis 中文字体分支的裸 except 收窄（写位落档 · 2026-09-29 实测） |
| `docs/insights/s927-41-note.md` | 2026-09-29 | s924-01 s927-41 | s927-41 `_APP_TEST_FILES` 追加升级单 → 实况收窄为白名单漂移守门（写位落档 · 2026-09-29 实测） |
| `docs/insights/s927-52-p3p4-decisions.md` | 2026-09-29 | s923-19 s924-09 s924-26 s927-52 | s927-52 · P3/P4 版式改值项人工拍板决策清单（承 s923-19） |
| `docs/insights/s927-53-buttons3-paths.md` | 2026-09-29 | s923-15 s923-22 s927-53 | s927-53 · panel 三枚下载按钮：四路出口的成本与后果（承 s923-22 裁决 81） |
| `docs/insights/s927-56-drift22-decisions.md` | 2026-09-29 | s924-11 s927-56 | s927-56｜22 处跨表措辞漂移「取哪侧」裁决清单（一次可勾选） |
| `docs/insights/s927-58-note.md` | 2026-09-29 | s924-17 s927-58 | feed_panel 读写键名失配修复（s927-58·读侧对齐生产者 extracted_* 族） |
| `docs/insights/s927-60-key-ownership.md` | 2026-09-29 | s924-22 s927-60 | s927-60｜`mean` / `reliability` 两键归属裁决材料（消费路径实测＋两案＋推荐＋diff 草案） |
| `docs/insights/s927-62-note.md` | 2026-09-29 | s924-05 s927-62 | s927-62｜`s924-05` §9 待订正 6 条落实记录（勘误追加单 · 2026-09-29） |
| `docs/insights/s927-63-pollution-adjudication.md` | 2026-09-29 | s923-17 s927-58 s927-63 | s927-63 · 044 文献推送生产数据污染：四件现状复核 ＋ 两案裁决材料（2026-09-29，只读·零回滚） |
| `docs/insights/s927-65-redline-ledger.md` | 2026-09-29 | k920-86 s923-08 s927-65 | s927-65 · 本批心理统计红线待裁项总清单（一页版，2026-09-29 · 只汇编·不裁决·不算数） |
| `docs/insights/s927-68-baseline3250.md` | 2026-09-29 | n922-11 s927-27 s927-68 | s927-68 · 「3250 基线」口径复测现值与 KNOWN_ISSUES 注记草案（2026-09-29，只读＋登记单） |
| `docs/insights/s927-70-note.md` | 2026-09-29 | s927-08 s927-58 s927-70 | psy 脏树 `?? node_modules/` 入 .gitignore（s927-70·s927-08 后续处置） |
| `docs/insights/s927-71-baseline-refresh.md` | 2026-09-29 | n922-11 s922-114 s927-27 s927-68 s927-71 | s927-71 · psy tests 基线档现值刷新（3242 后漂移）（2026-09-29，只读取数＋本枚新档） |
| `docs/insights/s927-72-aprime.md` | 2026-09-29 | s923-03 s924-04 s927-72 | s927-72 · A′ 哨兵的调用方识别（design_engine 出口形态收口） |
| `docs/insights/s927-11-releasegate.md` | 2026-09-30 | s927-11 | s927-11 — scripts/research_release_gate.py 功能测绘与测试补位 |
| `docs/insights/s927-32-slice-order.md` | 2026-09-30 | s922-103 s927-32 | s927-32 · slice 6a／片 4 搬迁顺序可行性现值与推荐执行序（只读裁决材料） |
| `docs/insights/s927-54-note.md` | 2026-10-01 | s923-05 s924-08 s927-54 | s927-54 收口记录（2026-10-01） |

## s930 批（19 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/s930-17-cfa-golden-gaps.md` | 2026-10-02 | s927-10 s930-17 | CFA golden 钉桩缺口与四条裁决项对照材料 |
| `docs/insights/s930-20-userlib-index-dangle.md` | 2026-10-02 | s927-21 s930-20 | 用户库索引悬空处置选项材料 |
| `docs/insights/s930-22-coerce-zero-adjudication.md` | 2026-10-02 | s927-29 s930-02 s930-22 | models.py 六处裸强转静默回退 0 裁决材料 |
| `docs/insights/s930-23-usage-logger-fallback.md` | 2026-10-02 | s927-38 s930-23 | usage_logger 字体诊断兜底裁决材料 |
| `docs/insights/s930-24-asset-predicate-unify.md` | 2026-10-02 | s927-39 s930-01 s930-06 s930-22 s930-24 | 资产谓词四处写法单源化方案材料 |
| `docs/insights/s930-25-two-gates-adjudication.md` | 2026-10-02 | s924-04 s927-40 s930-25 | 坏 design 串退 2x2 与 −0.02 缓冲带阈值材料 |
| `docs/insights/s930-27-fake-zero-export-map.md` | 2026-10-02 | s927-47 s930-17 s930-27 | 假 0 族与 result_card 效应量出口对照材料 |
| `docs/insights/s930-29-gated-exports-granularity.md` | 2026-10-02 | s927-53 s930-29 | GATED_EXPORTS 文件级粒度归因材料 |
| `docs/insights/s930-30-exporters-str-degrade.md` | 2026-10-02 | s927-55 s930-12 s930-30 | exporters str 出口显式降级选项材料 |
| `docs/insights/s930-31-stats-labels-signoff.md` | 2026-10-02 | s927-56 s930-31 | 7 处统计标签实现实况签字材料 |
| `docs/insights/s930-32-i18n-settings-decision-matrix.md` | 2026-10-02 | s924-11 s927-56 s927-60 s930-32 | i18n×settings 键位并轨与归类矛盾：一页决策矩阵 |
| `docs/insights/s930-34-198-4-numeric-semantics.md` | 2026-10-02 | s927-66 s930-34 | 台账 #198④ 数值语义对照材料 |
| `docs/insights/s930-35-rotate-sort-key.md` | 2026-10-02 | s927-67 s930-35 | 备份 rotate 排序键材料＋沙盒双分隔符实验 |
| `docs/insights/s930-42-lr-panel-blast-radius.md` | 2026-10-02 | s927-29 s930-02 s930-42 | 文献面板外部调用面整页红风险普查 |
| `docs/insights/s930-44-bundle-reachability.md` | 2026-10-02 | s927-39 s930-43 s930-44 | paper_bundle 四格可达性 AppTest 走查材料 |
| `docs/insights/s930-45-s923-924-legacy-sweep.md` | 2026-10-02 | s923-02 s923-04 s923-11 s923-15 s923-924 s924-03 s924-06 s92 | s923/s924 遗留是否已被提交吃掉普查（销案表） |
| `docs/insights/s930-46-trending-sandbox-retest.md` | 2026-10-02 | s927-66 s930-46 | 台账 #194① trending_weights 沙盒复测报告 |
| `docs/insights/s930-49-errbody-privacy.md` | 2026-10-02 | s923-16 s927-33 s930-49 | err_body 隐私脱敏口径材料（备用） |
| `docs/insights/s930-01-legacy2-retracted-20261008.md` | 2026-10-08 | k1007-145 s1004-01 s927-28 s930-01 | s930-01 遗留 2 误判销案登记（2026-10-08，s1004-01 遗留 2） |

## session/lock（13 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/literature-panel-locked-contract-20260911.md` | 2026-09-11 | — | 文献面板抛 ProjectLockedError 契约材料（2026-09-12 夜间执行班，任务 p911r-34，零实现） |
| `docs/insights/psy-litlocked-design-20260918.md` | 2026-09-18 | s918-04 s918-52 | 文献面板锁异常语义核验＋`LiteratureLockedError` 方案（s918-52，只读） |
| `docs/insights/psy-lock-granularity-design-20260918.md` | 2026-09-18 | s918-04 | psy 项目锁粒度与回退策略设计稿（s918-04 / P1 余留） |
| `docs/insights/psy-session-state-attr-read-census-20260921.md` | 2026-09-21 | s921-01 s922-04 | psy session_state 属性式读取普查（s922-04，2026-09-21） |
| `docs/insights/psy-session-subscript-read-census-20260922.md` | 2026-09-22 | s922-136 | psy session_state 下标式裸读面普查（s922-136，2026-09-23 夜班实取） |
| `docs/insights/psy-session-key-implicit-census-20260924.md` | 2026-09-24 | s922-136 s924-21 s924-33 | psy `key=` 隐式注册面并入 session_state census（s924-33 · 只读） |
| `docs/insights/psy-session-state-ast-census-20260924.md` | 2026-09-24 | s923-14 s924-21 | psy `session_state` 去重键 AST 级复算：26 vs 30 口径归一（s924-21 · 只读） |
| `docs/insights/psy-instance-lock-clock-seam-20260925.md` | 2026-09-25 | s924-63 | psy `instance_lock` 时钟接缝裁决：epoch `st_mtime` 判龄 vs 墙钟内容戳 |
| `docs/insights/s927-35-locknow.md` | 2026-09-28 | s921-13 s922-109 s927-35 | s927-35 · `break_stale()` / `acquire()` 的 `now` 时钟接缝统一（s922-109 遗留 1 落地） |
| `docs/insights/s930-19-tri-axis-lock-drift.md` | 2026-10-02 | s927-21 s930-19 | lock/venv/HEAD 三向依赖漂移对账与重建方案材料 |
| `docs/insights/s930-28-sweep-lock-ttl.md` | 2026-10-02 | s923-12 s927-49 s930-28 | sweep 抢锁顺序与双 TTL 口径对照材料 |
| `docs/insights/lock-alert-bark-20261005.md` | 2026-10-05 | s1004-24 s1004-36 s930-09 | 锁域告警 bark 化裁决材料（s930-09 遗留：_alert_once 只进 logging）——s1004-24 |
| `docs/insights/block-closure-precise-20261008.md` | 2026-10-08 | s1004-07 s1007-29 | 块级依赖闭包精确化（s1007-29，AST 作用域分析） |

## snapshot/备份（9 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/h912-06-psy-snapshot-b-20260912.md` | 2026-09-12 | h912-06 | psy 快照方案 B 收尾报告（h912-06，2026-09-12 夜班）：受理语义入码＋换案阈值实测 |
| `docs/insights/psy-snapshot-plana-design-20260918.md` | 2026-09-18 | s918-03 | psy 大快照超阈值方案 A 增量资产化设计稿（s918-03） |
| `docs/insights/psy-snapshot-planA-incremental-design-20260922.md` | 2026-09-22 | h912-06 s918-03 s922-129 | psy 大快照超阈值方案 A 增量资产化设计稿（s922-129） |
| `docs/insights/psy-snapshot-key-sizing-20260923.md` | 2026-09-23 | s922-129 s923-38 | psy workspace 快照逐键体量运行时实测 + v35 同源重复度（s923-38，2026-09-24） |
| `docs/insights/psy-snapshot-baseline-20260924.md` | 2026-09-24 | s923-21 s924-28 | psy `-k snapshot` 族基线（s924-28 · 复跑读数 ＋ 机理更正） |
| `docs/insights/psy-workspace-snapshot-pairing-gate-20260925.md` | 2026-09-25 | s923-38 s924-62 | psy workspace 快照「四键成对性」门禁设计稿（含 restore 缺键实测） |
| `docs/insights/s927-64-snapshot-order.md` | 2026-09-29 | s923-21 s924-28 s927-64 | s927-64 · `perf_counter_ns` 快照排序语义债：三案材料 ＋ 推荐（2026-09-29，登记档·零码改动） |
| `docs/insights/s927-67-backup-naming.md` | 2026-09-29 | k921-52 s927-67 | s927-67 · psy 备份目录命名口径普查与统一方案材料（2026-09-29 现值，只读单） |
| `docs/insights/s930-47-backup-two-reds.md` | 2026-10-02 | s927-68 s930-47 | test_backup_user_data 两枚红归因材料 |

## thresholds/信度档位（15 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/insights/psy-thread-threshold-20260911.md` | 2026-09-11 | — | psy 快照方案B session_state 跨线程验证 + df_b64 阈值校准（2026-09-12 夜间执行班，任务 p911r-33） |
| `docs/insights/psy-interpreter-caliber-20260915.md` | 2026-09-15 | n915-79 p914-19 | psy 测试解释器口径说明（n915-79，只读起草） |
| `docs/insights/psy-e2e-count-caliber-20260917.md` | 2026-09-17 | — | psy KNOWN_ISSUES E2E 跳过口径取证（916p-a4-002，2026-09-17） |
| `docs/insights/psy-eta-threshold-caliber.md` | 2026-09-25 | s924-61 | psy Cohen η² 阈值复写点 census 与收敛裁决材料（只读） |
| `docs/insights/s927-03-star-caliber.md` | 2026-09-27 | s927-03 | 相关矩阵星标规则标准化裁决材料（correlation.py 三处） |
| `docs/insights/s927-44-caliber-ab.md` | 2026-09-28 | s923-05 s924-08 s927-44 | s927-44 `export_to_docx` CJK 补齐失败面 口径 A／B —— 裁决材料（零码改动） |
| `docs/insights/s927-45-format-caliber-note.md` | 2026-09-28 | s923-06 s927-45 | s927-45 版式数值判据「逐位等于」口径订正单（ psy 分区纪律补文草稿，零改纪律本体） |
| `docs/insights/s927-27-interp-caliber.md` | 2026-09-29 | s922-03 s927-27 | s927-27 · 全量套件解释器口径基线档（钉桩） |
| `docs/insights/s927-69-caliber-note.md` | 2026-09-29 | s927-69 | s927-69 · 派单模板补文草案：writer 覆盖类判据的前置核查口径（2026-09-29，登记单） |
| `docs/insights/s930-18-assumption-router-caliber.md` | 2026-10-02 | s927-21 s927-24 s930-18 | assumption_router 口径冲突与登记实况对拍材料 |
| `docs/insights/s930-33-cramer-w-caliber.md` | 2026-10-02 | s927-62 s930-33 | Cramér's V/Cohen's w 口径分叉裁决材料 |
| `docs/insights/missing-pct-caliber-20261005.md` | 2026-10-05 | s1004-41 | missing_pct 双阈值（15 vs 10）与双分母口径统一裁决材料（0b52 遗留）——s1004-41 |
| `docs/insights/reliability-rounding-20261005.md` | 2026-10-05 | s1004-29 | reliability.py 30 处 round() 舍入规则统一裁决材料（c36e 遗留）——s1004-29 |
| `docs/insights/psy-reliability-template-gaps-20261006.md` | 2026-10-06 | s1002-37 s920-06 | ReliabilityResult 指南模板缺口裁决材料（s1002-37，2026-10-06，报告型零文案落码） |
| `docs/insights/psy-thresholds-module-design-20261006.md` | 2026-10-06 | s1002-36 s920-05 | psychometrics 效度/信度阈值族集中常量化设计稿（s1002-36，2026-10-06，零数值改动） |

## 其他（48 件）

| 文件 | 日期 | 关联 result | 主题（H1） |
|---|---|---|---|
| `docs/history/自评报告_系统升级.md` | 2026-05-14 | — | 心理学分析与问卷系统 — 升级自评报告 |
| `docs/ACADEMIC_INTEGRITY_GUIDE.md` | 2026-07-14 | — | 学术诚信与 AI 辅助使用指南 |
| `docs/INSTALLATION_TROUBLESHOOTING.md` | 2026-07-14 | — | 安装与故障排除指南 |
| `docs/PRIVACY_AND_AI_USAGE.md` | 2026-07-14 | — | 隐私保护与 AI 使用说明 |
| `docs/TESTING.md` | 2026-07-14 | — | 测试体系说明 |
| `docs/USER_QUICKSTART.md` | 2026-07-14 | — | Psy-Analysis 快速开始指南 |
| `docs/decisions/2026-08-24-impl-system-optimization-v510.md` | 2026-09-02 | s923-49 | v5.10 系统级优化实施与评审归档 |
| `docs/history/ARCHITECTURE_PHASE1_PLAN.md` | 2026-09-04 | — | Architecture Phase 1 Work Order |
| `docs/history/FRONTEND_ERGONOMICS_PLAN.md` | 2026-09-04 | — | 前端人体工学优化实施计划 |
| `docs/history/PLAN-REVIEW-LOG.md` | 2026-09-04 | — | Plan review log |
| `docs/history/PLAN.md` | 2026-09-04 | — | Repository-wide test coverage audit |
| `docs/history/SYSTEM_OPTIMIZATION_PLAN.md` | 2026-09-04 | — | 系统级优化实施计划 |
| `docs/insights/method-explanation-matrix-20260904.md` | 2026-09-04 | — | 全部统计方法解释质量矩阵（psy-C3，2026-09-04） |
| `docs/insights/method-explanations-drafts-batch1-20260905.md` | 2026-09-05 | — | 方法解释文案草稿·第一批 top10（staging，2026-09-05/06 夜） |
| `docs/insights/questionnaire-gap2-wiring-design-20260905.md` | 2026-09-05 | — | 问卷引擎 Gap 2 接线设计稿（2026-09-06 凌晨，方案文档不实施） |
| `docs/insights/triple-registry-consistency-20260905.md` | 2026-09-05 | — | runner × interpretation × router 三方一致性核对（2026-09-06 凌晨，只读） |
| `docs/insights/crawler-apa7-converge-20260911.md` | 2026-09-11 | — | literature_crawler.to_apa7 收敛到 format_reference（2026-09-12 夜间执行班，任务 p911r-31） |
| `docs/insights/replay-mark-eval-20260911.md` | 2026-09-11 | — | psy golden 回放测试 mark 语义与 CI 接入评估（2026-09-11/12 夜间执行班，任务 p911r-32，零写库） |
| `docs/insights/s922-07-batchapprove-two-stage-material.md` | 2026-09-21 | s921-10 s921-11 s922-06 s922-07 | s922-07 材料单：「⚡ 一键批准高置信」分支两段式确认评估（只读，零代码 diff） |
| `docs/insights/s924-36-a1-backport-draft-20260925.md` | 2026-09-25 | s922-139 s924-36 | s924-36 落码草案 — app.py 计时面回流（案 A1，六 hunk patch 已生成） |
| `docs/insights/s928-01-space-after-bprime.md` | 2026-09-29 | s927-51 s928-01 | s928-01 · SPACE_AFTER_BODY_PT 案 B′ 接线实施（两笔落地记录） |
| `docs/insights/gh-label-corr-stars-20261004.md` | 2026-10-04 | s1004-56 s923-08 | gh-label-corr-stars-20261004 —— s1004 批合卷（psy 裁决材料） |
| `docs/insights/invalid-score-3options-20261004.md` | 2026-10-04 | s1004-54 | 非法值静默计分三案裁决材料（c47f 遗留）——s1004-54 |
| `docs/insights/causal-wording-gate-design-20261005.md` | 2026-10-05 | s1004-45 | 因果措辞自动门禁设计稿（「影响/机制」动词面扫描器）——s1004-45 |
| `docs/insights/codebook-scale-template-mapping-20261005.md` | 2026-10-05 | s1004-48 | codebook `scale` 字段与 ALL_TEMPLATES 五套模板名映射裁决材料（d598 遗留）——s1004-48 |
| `docs/insights/collect-numeric-vars-scope-20261005.md` | 2026-10-05 | s1004-40 | _collect_numeric_vars 作用域过宽影响面裁决材料（a7a1 E2＋4d99 E3）——s1004-40 |
| `docs/insights/errors-form-contract-20261005.md` | 2026-10-05 | s1004-35 | result errors 警告面 str/dict 双形态契约统一裁决材料（7575 遗留）——s1004-35 |
| `docs/insights/fetch-runs-zombie-attribution-20261005.md` | 2026-10-05 | s1004-36 | fetch_runs 僵尸 running（TTL 未生效）与 daily_runner 运行面归因材料——s1004-36 |
| `docs/insights/learning-card-colloquial-copy-20261005.md` | 2026-10-05 | s1004-51 | learning_card 教学口语化文案分桶清单（fe47 遗留，备用）——s1004-51 |
| `docs/insights/legacy-inspection-batch2-s925-927-20261005.md` | 2026-10-05 | s1004-50 s923-924 s925-927 s927-27 s927-47 s927-49 s930-45 | result 遗留节滚动目检第二批（s925–s927 批）目检表——s1004-50 |
| `docs/insights/mc-correction-failopen-20261005.md` | 2026-10-05 | s1004-38 | _apply_mc_correction 未知方法名 fail-open 修法裁决材料（ae49 遗留）——s1004-38 |
| `docs/insights/mc-method-mediation-control-surface-20261005.md` | 2026-10-05 | s1004-37 s927-23 | mc_method 与 _run_mediation 默认配置控制面缺位设计稿（ae49 遗留 3＋4d99 E2）——s1004-37 |
| `docs/insights/method-weights-20red-attribution-20261005.md` | 2026-10-05 | s1004-22 s930-48 | method_weights_io_seed 20 红独立族归因（s930-48 遗留：canonicals 空集）——s1004-22 |
| `docs/insights/mixed-anova-diagnosability-20261005.md` | 2026-10-05 | s1004-44 | mixed_anova 小样本/畸形面板崩溃 定向报错裁决材料（a7a1 遗留）——s1004-44 |
| `docs/insights/nonparam-ci-design-20261005.md` | 2026-10-05 | s1004-30 s927-61 | 非参数族效应量 CI 补齐统计层设计稿（b040 遗留，dataclass 先行）——s1004-30 |
| `docs/insights/qpanel-v4-parity-20261005.md` | 2026-10-05 | s1004-20 s930-43 s930-44 | app.py 内联 vs panel 问卷分支对拍 v4 路径——差异表与三归类（s930-43/44 遗留）——s1004-20 |
| `docs/insights/repeated-anova-subjectcol-design-20261005.md` | 2026-10-05 | s1004-43 s927-18 | repeated_anova subject_col 透传设计稿（plan 增字段前置）——s1004-43 |
| `docs/insights/skip-record-track-design-20261005.md` | 2026-10-05 | s1004-52 s930-07 | 运行期 skip 记录轨（-rs 反查无因 skip）设计稿（备用）——s1004-52 |
| `docs/insights/spss-missing-codes-20261005.md` | 2026-10-05 | s1004-28 | SPSS 用户缺失范围（missing_codes）归一判据单（d598 遗留 C4）——s1004-28 |
| `docs/insights/cancel-registry-triplets-20261008.md` | 2026-10-08 | s1010-13 | cancel-id 注册表三胞胎归一裁决材料（s1010-13，只读零改码） |
| `docs/insights/error-type-whitelist-draft-20261008.md` | 2026-10-08 | s1004-46 s1007-12 s1007-31 | error_type 白名单草案（s1007-31，案①未落→草案分支） |
| `docs/insights/export-gate-coverage-20261008.md` | 2026-10-08 | s1010-08 | export_gate「所有导出入口必须经此检查」全称命题抽验矩阵（s1010-08，零改码材料） |
| `docs/insights/restore-branch-guard-20261008.md` | 2026-10-08 | s1007-03 s1007-22 | 恢复流程两分支无兜底——补齐裁决材料（s1007-22，零改码） |
| `docs/insights/s1002-32-count-erratum-20261008.md` | 2026-10-08 | s1002-32 s1007-05 s1007-34 | s1002-32 计数口径勘误行（s1007-34） |
| `docs/insights/switch-2options-final-20261008.md` | 2026-10-08 | s1004-05 s1007-36 s930-05 | required_n→n_total 彻底切两案材料·终版（s1007-36，零改码） |
| `docs/insights/variables-families-collision-registry-20261008.md` | 2026-10-08 | s1007-02 s1007-27 s924-64 | variables 字段族分案防撞登记（s1007-27） |
| `docs/insights/p-sample-table-holm-bh-20261009.md` | 2026-10-09 | s1008-01 s1014-03 | p-sample-table-holm-bh-20261009 —— 校正前后 p 样例表（决议#21） |
| `docs/INDEX.md` | 2026-10-24 | s1023-12 | psy-analysis docs/ 索引（INDEX） |
