# psy docs/insights 未入库报告盘点与收口清单（n916x-30，只读）

**结论：docs/insights 磁盘 .md 35 份、git 已跟踪 21 份、未跟踪 14 份。逐条定性＝14 份全部「保留待入库」（0 份弃置）——均为夜/日班执行结果报告（有任务 id 锚点、内容为终态结论非草稿），弃置将丢失可追溯验收证据。本报告自身归入清单待日间入库。**

## 一、集合比对（命令与数字同段）

```
$ git ls-files docs/insights | wc -l   → 21（已跟踪）
$ ls docs/insights/*.md | wc -l        → 35（磁盘）
未跟踪＝35 − 21 ＝ 14
```

## 二、未跟踪清单（文件名＋文件系统 mtime＋定性）

| 文件 | mtime | 定性 | 理由（非时间判定） |
|---|---|---|---|
| psy-app-split-2-20260913.md | 09-14 00:39 | 保留待入库 | psy 拆分第二批执行报告（d913a-43 66min 重单的产物），方案 B 收尾链证据 |
| psy-app-split-batch2-20260913.md | 09-14 01:53 | 保留待入库 | 拆分 batch2 执行报告，同族链 |
| psy-app-split-batch3-20260914.md | 09-14 05:23 | 保留待入库 | 拆分 batch3 执行报告，同族链收官 |
| psy-autosave-timer-semantics-20260913.md | 09-13 16:19 | 保留待入库 | 自动保存计时器语义核验报告（h913 执行件） |
| psy-benchmark-score-backfill-20260913.md | 09-13 16:08 | 保留待入库 | 基准分回补执行件（psy-benchmark-scoring 链） |
| psy-e2e-skip-inventory-20260914.md | 09-14 06:17 | 保留待入库 | 25 项 E2E 跳过清点＝BACKLOG B-114（Playwright 补装）的锚点文件 |
| psy-e2e-subset-order-20260913.md | 09-13 14:36 | 保留待入库 | e2e 子集顺序依赖教训单（教训已入台账，报告本体未入库） |
| psy-interpreter-caliber-20260915.md | 09-16 03:16 | 保留待入库 | 测试解释器口径（.venv pytest）推荐稿——n915-79 产物，口径被后续班引用 |
| psy-known-issues-101-rewrite-20260913.md | 09-14 00:52 | 保留待入库 | 防撞条款合规留档（d913c-33 零编辑出比对文件，KNOWN_ISSUES 101 行改写依据） |
| psy-perf-smoke-contract-test-20260915.md | 09-15 01:43 | 保留待入库 | 性能冒烟契约测试执行报告 |
| psy-test-blindspot-audit-20260915.md | 09-15 01:51 | 保留待入库 | 测试盲区审计报告 |
| psy-uncommitted-signoff-20260917.md | 09-17 03:33 | 保留待入库 | 未提交改动签核清单（916p-a4-003，日间签核依据） |
| psy-apa7-manual-string-converge-20260917.md | 09-17 03:40 | 保留待入库 | APA7 手工串收敛核验＋钉测（916p-a4-005） |
| psy-readme-env-drift-20260917.md | 09-17 03:43 | 保留待入库 | README 环境变量/命令对账（916p-a4-006） |
| （本报告）psy-insights-untracked-20260916.md | 本班 | 保留待入库 | 本单产物 |

弃置判定＝0：14 份均为「任务 id＋终态结论」形态的执行报告，无草稿/半成品/重复副本（抽验 4 份头部均为成稿结论段）。

## 三、验收情况

- ✅ 未跟踪清单行数 14＝磁盘 35−跟踪 21（两数并列、命令同段）；✅ 每条含文件系统 mtime；✅ 只读未 git add/commit 未 push。

## 遗留问题

日间收口建议：精确路径 `git add docs/insights/<15 份>`（含本报告）一次入库；入库前快速抽验即可，无需逐份重读。
