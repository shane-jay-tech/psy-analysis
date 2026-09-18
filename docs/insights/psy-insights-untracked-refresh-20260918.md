# psy docs/insights 未入库清单刷新＋精确入库命令（s918-19，只读）

生成：2026-09-19 01:05｜执行：Qoder 会话（班次 `qoder-rev-20260919-0006`，倒序尾部接手）
**本单只出报告，不 `git add`、不 commit、不 push。**

**结论：`docs/insights` 磁盘 43 份（42 `.md` ＋ 1 `.json`）、git 已跟踪 21 份、未跟踪 22 份。
逐份定性＝22 份全部「保留待入库」，0 份弃置。** 与 9/16 旧清单（n916x-30）相比净增 7 份：
6 份新执行报告 ＋ **1 份旧报告口径漏掉的 `.json` 机读件**。本单自身（本报告）计入清单。

## 一、集合比对（命令与数字同段）

```
$ git ls-files docs/insights | wc -l                          → 21（已跟踪）
$ ls docs/insights | wc -l                                    → 43（磁盘全量）
$ ls docs/insights/*.md | wc -l                               → 42（仅 .md）
$ git status --porcelain docs/insights/ | grep -c '^??'       → 22（未跟踪：21 .md + 1 .json）
```

对账：`42 (.md) − 21 (跟踪) = 21 未跟踪 .md`，加 1 份 `.json` ＝ **22 行** ✓（与旧报告的
「磁盘 35 − 跟踪 21 = 14」同口径可比：`.md` 未跟踪 14 → 21，**净增 7**，其中含旧报告自计的那 1 份）。

锚点复核：`docs/insights/psy-insights-untracked-20260916.md:41` 原文
「日间收口建议：精确路径 `git add docs/insights/<15 份>`（含本报告）一次入库；入库前快速抽验即可，无需逐份重读。」
**逐字命中** ✓；任务书「现值已漂移：`?? docs/insights` 已 21 份（旧清单 14 份）」中的 **21 与 14 均复核成立**
（21 指 `.md`；本单实测的 22 是含 `.json` 的全口径）。

## 二、旧清单未覆盖的 7 份逐份定性

| 文件 | mtime | 任务 id | 终态 | 定性 |
|---|---|---|---|---|
| psy-baseline-recheck-20260917.md | 09-18 04:58 | 917-34 | collect 2701／一次通过实测已记 | **保留待入库**（⚠️ 数字已被今晚推进，见第四节） |
| psy-benchmark-sidecar-edges-20260916.md | 09-18 01:21 | n916x-32 | side-car 追加 4 边界用例 → `-k sidecar` 7 passed | **保留待入库** |
| psy-known-104-105-20260916.md | 09-18 01:14 | n916x-31 | :104/:105 三要素仍成立，处置方向判「需日间拍板」，零改码 | **保留待入库** |
| psy-prune-archive-fix-20260917.md | 09-18 04:52 | 917-33 | 择一收敛＝改 docstring＋补 `is_dir` 守卫 | **保留待入库** |
| psy-questionnaire-panel-testdesign-20260918.md | 09-19 00:39 | s918-28 | 只读设计稿；结论「A 类纯逻辑现实为空集」 | **保留待入库**（本夜班产物） |
| psy-quick-entries-audit-20260918.md | 09-19 00:43 | s918-27 | 只读审计＋配套测试 6 例 | **保留待入库**（本夜班产物） |
| psy-test-blindspot-audit-20260915.json | 09-15 01:49 | d914-75 | 符号级 AST 审计的**机读产物**（`total_src_modules: 244`） | **保留待入库**——旧报告只数 `.md`，把它整份漏掉了（`grep -c json` 旧报告 → 0） |

旧清单已登记的 15 份（含 n916x-30 自身）**全部仍在未跟踪状态**，定性不变，本单不重复裁决。

## 三、可直接粘贴的精确入库命令（22 份，逐路径，无 `-A`/`.`）

```bash
cd /d/code/psy-analysis && git add \
  docs/insights/psy-apa7-manual-string-converge-20260917.md \
  docs/insights/psy-app-split-2-20260913.md \
  docs/insights/psy-app-split-batch2-20260913.md \
  docs/insights/psy-app-split-batch3-20260914.md \
  docs/insights/psy-autosave-timer-semantics-20260913.md \
  docs/insights/psy-baseline-recheck-20260917.md \
  docs/insights/psy-benchmark-score-backfill-20260913.md \
  docs/insights/psy-benchmark-sidecar-edges-20260916.md \
  docs/insights/psy-e2e-skip-inventory-20260914.md \
  docs/insights/psy-e2e-subset-order-20260913.md \
  docs/insights/psy-insights-untracked-20260916.md \
  docs/insights/psy-interpreter-caliber-20260915.md \
  docs/insights/psy-known-104-105-20260916.md \
  docs/insights/psy-known-issues-101-rewrite-20260913.md \
  docs/insights/psy-perf-smoke-contract-test-20260915.md \
  docs/insights/psy-prune-archive-fix-20260917.md \
  docs/insights/psy-questionnaire-panel-testdesign-20260918.md \
  docs/insights/psy-quick-entries-audit-20260918.md \
  docs/insights/psy-readme-env-drift-20260917.md \
  docs/insights/psy-test-blindspot-audit-20260915.json \
  docs/insights/psy-test-blindspot-audit-20260915.md \
  docs/insights/psy-uncommitted-signoff-20260917.md
```

命令正文由 `git status --porcelain docs/insights/ | grep '^??' | sed 's/^?? //' | sort` 直接生成，
**逐字对照磁盘、非手抄**；重跑本单前先复跑该命令，若行数≠22 说明又有新份落盘。

## 四、入库前需要知道的三件事

1. **基线数字已再漂移**：`psy-baseline-recheck-20260917.md` 记 collect **2701**；本会话（9/19 夜）在
   psy 补测后实测 **2766**（`s918-35` 四单前为 2709）。该份报告的数字现在只能当历史节点，不能当现值引用。
   复现：`cd /d/code/psy-analysis && .venv/Scripts/python.exe -m pytest tests/ -q --collect-only | tail -1`
2. **今晚 3 份产物钉的是未提交代码**：`psy-quick-entries-audit` 与 `tests/test_quick_entries_min.py` 的被测对象
   `src/ui/heavy_preload.py`、`src/ui/startup_checks.py`、改动的 `app.py` 目前仍是 untracked/modified。
   若日间回滚那批，报告与配套测试会一起失真——建议**同批入库**或同批回滚，别只回滚代码。
3. **`.json` 与 `.md` 同名同源**：入库时务必成对，只入 `.md` 会让机读审计数据失去出处。
   旧报告正是这个漏法（其口径明写「磁盘 .md 35 份」）。

## 五、验收情况

| 完成标准 | 实测 | 复现命令 |
|---|---|---|
| 报告含现值差集数（实测） | **22 行**（21 `.md` ＋ 1 `.json`），并与旧清单 14 份做增量对照（净增 7） | `git status --porcelain docs/insights/ \| grep -c '^??'` |
| 命令可整段复制执行 | 第三节为单条 `git add` ＋ 22 个逐路径续行，无 `-A`/`-u`/`.` | `grep -c "docs/insights/" <<<"<第三节正文>"` → 22 |
| 只读、不 commit | 本单产出仅 `?? docs/insights/psy-insights-untracked-refresh-20260918.md`，未执行任何 `git add`/`commit` | `cd /d/code/psy-analysis && git status --porcelain docs/insights \| grep -c '^??'` → 23（含本报告） |

## 遗留问题

1. **本单发现旧报告的口径缺陷**：它用「磁盘 `.md` 数 − 跟踪数」算未跟踪，天然漏掉非 `.md` 产物
   （此次即漏 1 份 `.json`）。建议后续同类单改用 `git status --porcelain <目录>` 的 `??` 行计数为准（本单已用）。
2. 未跟踪 22 份里 15 份 mtime 早于 9/17，已在 n916x-30 挂「待日间入库」**两天没动**——堆积本身是风险
   （`git clean -fd` 一发就全没）。本报告不越权代为入库。
3. 本单未逐份重读旧 15 份的正文（沿用旧报告定性与任务书「同一条不重复裁决」纪律），
   只核对了它们的**仍在未跟踪状态**这一事实。
4. 执行身份非 glmflash：Qoder 会话直执，扣费为 0 桥积分。
