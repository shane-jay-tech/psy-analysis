# psy KNOWN_ISSUES「仍未修复」节状态刷新 v2（s921-17，只读复核稿·留日间放行）

> 2026-09-21｜Qoder 执行班 s921 子班 2｜**KNOWN_ISSUES.md 零改动**（`git status --porcelain KNOWN_ISSUES.md` 空、该文件末次提交仍是 `d1f99ab 09-19T17:42` s919-15，其后 s920 批 24 单与 s921 批（截至本单在册 15 份 result）全未回写本文件 ⇒ 状态又漂移）。
> 上一版：`docs/insights/psy-knownissues-reorg-20260918.md`（s918-08，9/18 出稿）——**它的重组建议至今未落地**（两个 ✅ 小节仍挂在「仍未修复」节下，见 §三第 6 行），故本稿既刷状态也重述位置问题。
> 本稿每一行都给**可复跑命令**，不给裸行号：v1 稿写的锚点 `:91 表头 / :92-95 数据行` 到今天已位移到 `:89 / :91-95`（v1 的 `sed -n '91p'` 今天取到的是 #L1 数据行，不是表头）——这正是"只写行号"的失效样本。

## 一、锚点附卷（完成标准要求的复跑口径）

```bash
cd /d/code/psy-analysis
sed -n '42p'  KNOWN_ISSUES.md          # → ## 仍未修复（v4.7+ 路线）      ✅ 锚点仍有效
grep -n "严重度\|^| 🟡\|^| 🔴\|^| 🟢" KNOWN_ISSUES.md
#  89:| 严重度 | 局限 | 目标版本 | 状态 |        ← 看板表头（v1 记作 :91）
#  91:| 🔴 高 | #L1 自学习模块 | v4.7 主线 | 已落地 |
#  92:| 🟡 中 | #L2 F1 论文写作合并 | v4.7 | 待评估 |
#  93:| 🟡 中 | #L3 N10 评分趋势观测 | v4.7 | 待开 |
#  94:| 🟢 低 | #L4 自评报告刷新 | — | 已关闭（…4add02e…） |
#  95:| 🟢 低 | #L5 socratic_engine 类型 lie | v5.8 | 已完成 |
```
任务书写的「`:89-95` 看板」按磁盘实况＝表头 :89 + 数据行 :91-95（:90 是分隔行）。

## 二、逐行新旧对照（旧＝盘中现状，新＝v2 订正建议）

| # | 位置 | 旧（盘上原文） | 新（建议改法） | 依据（今日实测） |
|---|---|---|---|---|
| 1 | `:38` 测试基线 | 「v5.11 当前 **2644** 个离线收集项（…2026-09-17）」 | 数字 → **3297**，复现日期 → 2026-09-21 | `pytest --collect-only -q -m "not online"` → `3297/3327 tests collected (30 deselected) in 11.54s`。四天内 +653，主要是 s920/s921 两批纯测试单 |
| 2 | `:42` 节名 | 「仍未修复（v4.7+ 路线）」 | 「路线与状态（v4.7+）」（＝v1 建议第 1 条，仍未放行） | 节内含两个 ✅ 小节（见第 6 行），节名与内容矛盾 |
| 3 | `:91` #L1 | 「已落地」 | **不改** | `ls src/literature_feed` → fetchers/parsers/extract/scheduler/storage/trend/ui 全在；`:52` 正文口径一致 |
| 4 | `:92` #L2 | 「待评估」 | 「已出对照材料（`docs/insights/psy-dualentry-overlap-20260918.md`，s918-01），**待用户拍板**；正文引用的 594 行已漂到 678 行」 | `wc -l src/ui/paper_writing_ui.py` → **678**（盘上 `:56` 仍写「(594 行独立 mode)」）；对照报告在册（27 行） |
| 5 | `:93` #L3 + 正文 `:63` | 「待开」／正文「**计划**：CI 跑 … ＋记录趋势到 …」 | 「**基建已建、观测未连续**」；正文「计划」改「现状＋缺口」 | ① 脚本已有归档与自动对比：`scripts/evaluate_socratic_benchmark.py:29`（`HISTORY_DIR`）、`:128`（`_last_history_entry`）、`:136`（`_archive_to_history`）⇒ "计划"两字已陈旧；② 末次真归档 `data/benchmark_history/socratic_benchmark_20260909T192139Z.json`（mtime 9/10 03:19），此后**断档 11 天**；③ 只有 `benchmark_backfill_draft.json`（9/16 01:21，18 KB）**草稿未入库**；④ 无 CI：`ls .github/workflows` → 目录不存在；⑤ 已知 bug 未修：`scripts/benchmark_relay_shim.py:20` 的 `LOG_PATH = Path(__file__).resolve().parent / "data" / "benchmark_history"` 少一层（`ls -d scripts/data` → 不存在），出自 `docs/insights/psy-data-dirs-20260919.md` A5 |
| 6 | `:94` `:95` #L4/#L5 | 「已关闭」／「已完成」 | 状态**正确**，但两条目（`:65`、`:71`）应迁出「仍未修复」节 ⇒ v1 建议第 2/3 条，至今未放行 | 归档证据可复跑：`git log --oneline --diff-filter=A -- docs/history/SELF_ASSESSMENT_REPORT.md` → `4add02e` |
| 7 | `:101` P1 多实例写入 | 「余留＝可选告警日志与锁粒度/回退策略」 | **不改**（行仍准确），但补一句限定防混淆 | `grep -n "alert" src/utils/instance_lock.py` → **零命中** ⇒ 告警日志确实未做；注意 feed 侧 `lock_manager._alert_once`（d914-19）是**另一把锁**，不抵消本行；今日另有他人在途 untracked `tests/test_lock_alert_log.py`（测的是 feed 锁），放行时别当成这条已推进 |
| 8 | `:103` P1 浏览器 E2E | 「未安装 Playwright，26 项明确跳过（…2026-09-17）」 | 数字**仍成立**，建议把复现日期补成「2026-09-21 复核」 | `python -c "import playwright"` → ModuleNotFoundError；`pytest -q -rs -m "playwright or e2e"` → **26 skipped, 3302 deselected**，与 `d1a6bc2 09-17 订正 25→26` 一致。⚠ 口径注：同标记**收集**只有 25 项（`--collect-only -m "playwright or e2e"` → `25/3327`）⇒ 第 26 项来自模块级 skip 而非标记收集，两个数不可互换 |
| 9 | `:107` 📌 9/13 状态注 | 「已落地两级互斥…待实施＝仅可选告警日志」 | 与第 7 行同源，建议合并表述以免两处各写一遍（同一文件里已出现两个口径） | 现状无变化，但 `:101` 与 `:107` 重复描述同一件事＝下次漂移点 |

## 三、放行方式建议

- 第 1/4/5/8 行是**数字与状态**订正，可整段替换，零代码风险。
- 第 2/6/9 行是**位置与重复表述**订正（＝s918-08 v1 建议 1/2/3 的原样重述），已拖 3 天，放行一次即可同时结掉 v1、v2 两稿。
- 第 7 行与第 5 行的 ⑤（`benchmark_relay_shim.py:20` 一行路径修法）**属生产码/代码改动**，按各自原单处置，本稿只登记不动。

## 四、红线自证

本单只读：未改 `KNOWN_ISSUES.md`、未改任何 `src/`、未改任何阈值或统计口径（α/ω 档位、信度判据、benchmark 金标一律未动），未跑统计结论类脚本；新增文件仅本稿。`data/benchmark_history/` 与 `data/` 全域只列目录未写入。
