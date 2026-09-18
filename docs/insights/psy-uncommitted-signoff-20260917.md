# psy 未提交改动签核清单（916p-a4-003，2026-09-17，只读盘点）

## 一、开工基线（命令与输出同段）

```
$ git status --porcelain        → 25 行（5 M ＋ 20 ??）
$ git diff --stat（尾部）        → requirements-lock.txt | 12 +++---；lock_manager.py | 38 ++++；5 files changed, 57 insertions(+), 49 deletions(-)
$ git diff --stat --cached      → 空（无已暂存）
$ ?? 行数                        → 20
```

## 二、已提交项（M 5 项）主表

| # | 路径 | 状态 | 改动摘要 | 来源单 | 回滚命令 | 签核 | 风险 |
|---|---|---|---|---|---|---|---|
| 1 | app.py | M | 面板路由与启动装配调整（9/13 UI 改造族） | psy-app-split 系列＋d913c-12 | git restore app.py | 是 | 中（入口装配） |
| 2 | docs/TESTING.md | M | pip install -e 不适用订正→venv 直跑口径 | d914-50-psy-testing-doc-cmd | git restore docs/TESTING.md | 否（一致性已核 ✓） | 低 |
| 3 | pytest.ini | M | addopts 去掉 -q（恢复汇总输出） | d914-22-pytest-summary-swallow | git restore pytest.ini | 否（diff↔来源单一致 ✓） | 低 |
| 4 | requirements-lock.txt | M | 六版本号对齐（streamlit 1.58/numpy 2.3.5/scipy 1.18 等） | d914-87-psy-lockfile-align | git restore requirements-lock.txt | 是（版本变更影响面） | 中 |
| 5 | src/literature_feed/scheduler/lock_manager.py | M | +38 行 d914-19 一次性告警守卫 | d914-19-psy-lock-alert-log | git restore src/literature_feed/scheduler/lock_manager.py | 是（配套测试 test_lock_alert_log.py 尚未入库，应同批） | 中 |

## 三、未跟踪文件清单（?? 20 项）

**报告类（docs/insights，12）**：psy-app-split-2-20260913、psy-app-split-batch2-20260913、psy-app-split-batch3-20260914、psy-autosave-timer-semantics-20260913、psy-benchmark-score-backfill-20260913、psy-e2e-skip-inventory-20260914、psy-e2e-subset-order-20260913、psy-interpreter-caliber-20260915、psy-known-issues-101-rewrite-20260913、psy-perf-smoke-contract-test-20260915、psy-test-blindspot-audit-20260915.md＋.json —— 建议：随下次签核批直接提交。
**脚本/源码类（4）**：src/ui/heavy_preload.py、src/ui/startup_checks.py（app-split 配套新源码，需单独复核）；tests/test_analysis_contracts.py、tests/test_perf_smoke_report.py、tests/test_startup_checks.py、tests/test_lock_alert_log.py（测试类，建议与对应实现同批提交）。
**其他（2）**：tmp/（噪声域，建议 .gitignore 补 tmp/）；**zcode-bridge/（psy 仓内嵌套目录，含 tmp/focus/20260912-0415 的 E01/E02 run.json——疑似 9/12 夜间任务 cwd 误指产生，建议日间确认后删除或迁移）**。

## 四、5 处已知归属一致性核对（来源单 ↔ 盘上 diff）

| 文件 | 来源单主张 | 盘上 diff 实际 | 一致 |
|---|---|---|---|
| pytest.ini | d914-22：去掉 -q | `-addopts = --strict-markers -q` → `+addopts = --strict-markers` | ✓ |
| docs/TESTING.md | d914-50：pip install -e 订正 | 改为「非安装包…venv 直跑 pytest…缺依赖再 install -r requirements.txt」 | ✓ |
| requirements-lock.txt | d914-87：六版本号 | streamlit 1.57→1.58、numpy 2.4.4→2.3.5、scipy 1.17.1→1.18.0 等 6 处 | ✓ |
| lock_manager.py | d914-19：告警守卫 | +38 行（logging/re import＋_alerted set＋一次性告警注释） | ✓ |
| KNOWN_ISSUES.md | 多实例锁行订正 | **已被本班 a4-001/a4-002 提交入库**（不再出现在 M 中） | ✓（状态更新） |

## 五、结论

- **建议随下次日间签核批直接提交**：pytest.ini、docs/TESTING.md、requirements-lock.txt、lock_manager.py＋tests/test_lock_alert_log.py（实现与测试同批）、tests/test_analysis_contracts.py、tests/test_perf_smoke_report.py、tests/test_startup_checks.py＋src/ui 两新源码、docs/insights 报告类 12 份。
- **建议单独复核**：app.py（入口装配改动面大）、tmp/（建议 .gitignore 补 tmp/）、zcode-bridge/ 嵌套目录（疑似误建）。

## 六、零改动自证

开工前/后 `git status --porcelain` 逐字一致（25 行）；`git diff --stat` 前后一致；本班零提交/零 add/零 stash/零 restore；不 push。
