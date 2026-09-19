# psy `data/literature_feed` 本地资产与陈旧锁盘点（s918-55，只读）

生成：2026-09-19 11:36｜执行：Qoder 会话（班次 `qoder-rev-20260919-1020`，倒序尾部续班）
未删锁、未清 raw、未改任何配置；sqlite 走 `mode=ro` URI 只读连接。
⚠️ 但「零文件变更」并不彻底：只读连接仍会在这个 WAL 库上生出 `-shm`/`-wal` 边车文件，
本单已在核实主库完好后删除复原（详见 §六 第三行与遗留 5）。零金额估算。

## 一句话结论

**20M 资产里只有 0.5M 是活的（sqlite），19M 的 `raw/` 从 6/3 起没有任何保留策略、也没有任何删除代码**；
那颗 26 天前的陈旧锁**不阻塞抓取**（`acquire()` 会自动 `break_stale` 接管），
但**它只有在"下次真的有人来抢锁"时才会消失**——全模块没有任何巡检/清理责任方。
另外锁文件本身是**追加式历史**，`_read_owner_pid()` 用 `re.search` 只会拿到**最旧那条** pid。

## 二、目录盘点（`ls -la data/literature_feed/`，原始输出）

```
drwxr-xr-x  -            .            (父 data/ mtime 09-19 05:41)
-rw-r--r--  3222  May 30 00:34  domain_weights.yaml
-rw-r--r--  499712 Aug 24 12:42 feed.sqlite
-rw-r--r--  719   Jul 15 11:31  llm_budget.json
drwxr-xr-x  -     Aug 24 11:51  locks
drwxr-xr-x  -     Sep 14 08:00  logs
-rw-r--r--  1715  May 30 01:05  method_weights.yaml
drwxr-xr-x  -     Aug 24 11:52  raw
-rw-r--r--  248   Aug 24 12:34  trending_weights.yaml
```

| 项 | 体积（`du -sk`） | 最后活动 | 备注 |
|---|---|---|---|
| `raw/` | **19332 KB（≈18.9 M）** | 2026-08-24 | **29 个日期目录，2026-06-03 → 08-24**，日均 ≈0.9 MB；占全目录 97% |
| `feed.sqlite` | 488 KB | 2026-08-24 12:42 | 122 页 × 4096 B ＝ 499,712 B，**与文件实际大小逐字相等 ⇒ 无空闲页/无碎片** |
| 三个 `*_weights.yaml` ＋ `llm_budget.json` | 各 1–4 KB | 5/30 – 8/24 | 配置类，均在版本库外（`data/` 被 .gitignore 排除） |
| `logs/` | **0** | 目录 mtime 09-14 08:00 | **空目录**——抓取日志目前不落地（或已被清） |
| 合计 | ≈20 M | — | 与任务书锚点「实测 du=20M」一致 ✓ |

## 三、sqlite 表行数（只读连接实测）

复现：`cd /d/code/psy-analysis && .venv/Scripts/python.exe -c "import sqlite3,pathlib; p=pathlib.Path('data/literature_feed/feed.sqlite').resolve(); c=sqlite3.connect(f'file:{p.as_posix()}?mode=ro',uri=True); [print(t[0], c.execute('select count(*) from \"%s\"'%t[0]).fetchone()[0]) for t in c.execute(\"select name from sqlite_master where type='table' order by name\")]"`

| 表 | 行数 | | 表 | 行数 |
|---|---|---|---|---|
| `articles` | **151** | | `manual_submissions` | **0** |
| `llm_candidates` | **122** | | `article_keywords` | **0** |
| `fetch_runs` | 41 | | `candidate_review_events` | **0** ⚠ |
| `llm_extraction_cache` | 24 | | `schema_migrations` | 3 |
| `sources` | 8 | | `sqlite_sequence` | 3（索引 15 个） |

⚠ 交叉印证 `s918-26`（审核队列面板测试）：面板读 `llm_candidates`（**122 条待审**），
审核历史读 `candidate_review_events`（**0 行**）⇒ **审核动作从未落库**，
队列面板的「📜 审核历史」区在当前数据下恒显示「暂无审核记录」。
另有 3 张空表（含 `article_keywords`、`manual_submissions`）说明相关链路建了表未启用。

## 四、陈旧锁：现状与责任归属

`ls -la data/literature_feed/locks/` 原始输出：

```
total 5
drwxr-xr-x 1 31563 197609 0 Aug 24 11:51 .
drwxr-xr-x 1 31563 197609 0 Aug 24 12:42 ..
-rw-r--r-- 1 31563 197609 153 Aug 24 12:33 feed_fetch.lock
```

`cat` 内容（**三条追加记录**）：

```
pid=65436 acquired_at=2026-08-24T03:51:57+00:00
pid=72588 acquired_at=2026-08-24T04:31:58+00:00
pid=63596 acquired_at=2026-08-24T04:33:58+00:00
```

| 判据 | 实测 |
|---|---|
| 锁龄 | mtime 2026-08-24 12:33（本地）＝`04:33:58Z` → 距 09-19 11:36 约 **25.9 天 ≈ 622 小时** |
| TTL | `lock_manager.py:54 ttl_seconds: int = 21600`（6h）✓ 锚点命中 ⇒ **超 TTL 约 103 倍** |
| 是否阻塞 | **不阻塞**：`_open_and_lock()` 先 `is_stale()` → `break_stale()` 删除后接管（`s918-57` 已用 `test_acquire_steals_a_stale_lock` 钉过这条路径） |
| 谁负责清 | **只有"下一个来抢锁的人"会顺手清**；`is_stale()` 不主动清理，也没有任何巡检任务/启动自检调用 `break_stale()`。若抓取链不再运行，它会**永久留盘** |
| pid 归属可靠性 | **不可靠**：`_write_owner_info` 用 `seek(0,2)` 追加、从不清空 ⇒ 文件是历史流水；而 `_read_owner_pid()` 用 `re.search(r"pid=(\d+)")` 取**第一个匹配**，即**最早那次持锁者的 pid（65436）**，不是最后持锁者（63596）。本例三个 pid 全不同，错读可验 |

⇒ 两个待判项（本单都不动手）：① 是否要在 `daily_runner` 启动时加一次 `break_stale()` 巡检；
② `_read_owner_pid()` 应改为取**最后一个**匹配（`re.findall(...)[-1]`）或写前截断。
②与 `s918-57` 遗留 1（Windows 上持锁期根本读不到 pid，告警恒 `pid=unknown`）是同一处代码的两个缺陷面，建议并一单修。

## 五、保留策略现状（raw / logs）

- **`raw/` 无任何保留策略**：`grep -rn "retention\|keep_days\|prune\|max_age" src/literature_feed --include=*.py`
  命中的全是 trending 计算窗口（`window_days`/`days_back`），**没有一处是删除语义**；
  全模块唯一 `os.unlink` 在 `storage/budget_tracker.py:118`，删的是自己的临时文件。
  ⇒ 83 天累积 19M、日均 +0.9MB、**只增不减**。
- **`logs/` 是空目录**（mtime 09-14 08:00）：既没有日志文件也没有轮转代码 ⇒ 与 `s918-08`/`n918-09` 那条
  「桥日志编码族/留痕」不同源，这里是**抓取侧根本没有文件日志**。
- 三个 `*.yaml` 权重与 `llm_budget.json` 合计 <5 KB，属配置不是资产；但它们**全部在 `.gitignore` 的 `data/` 段内**
  ⇒ 与备份链的关系见 `s918-31` 遗留 3（`backup_user_data.py` 只备 `~/.psy_analysis/projects` ＋ `feed.sqlite`，
  **不备 `raw/` 与这几个 yaml**）。

## 六、验收情况

| 完成标准 | 实测 | 复现命令 |
|---|---|---|
| 报告含各表行数表 | 第三节 10 表逐行（含 3 张空表与 `candidate_review_events=0` 的交叉印证） | 第三节末复现命令行 |
| 含 `ls -la data/literature_feed/locks/` 原始输出 | 第四节原文粘贴（1 个文件，153 B，mtime 08-24 12:33） | `cd /d/code/psy-analysis && ls -la data/literature_feed/locks/` |
| 全仓零文件变更 | **此条一度被本单写成"成立"，实为不成立——已纠正**：`mode=ro` 只读连接在这个库上仍会生出 `feed.sqlite-shm`(32768 B) ＋ `feed.sqlite-wal`(0 B) 两个边车文件（时间戳 11:36＝本单盘点时刻），目录由 8 项变 10 项。确认 `journal_mode=wal`、`pragma quick_check=ok`（主库未受损）后**已删除复原至 8 项**。主库与锁文件全程未变（`feed.sqlite` 499712 B／08-24 12:42；`feed_fetch.lock` 153 B／08-24 12:33） | `cd /d/code/psy-analysis && ls data/literature_feed \| wc -l` → 8；`ls -l data/literature_feed/feed.sqlite data/literature_feed/locks/feed_fetch.lock` |

## 遗留问题

1. 未读任何文献正文/摘要内容（只取行数与体积），因此「122 条 `llm_candidates` 里有多少是重复/低质」不在本单结论内。
2. `fetch_runs` 41 次、最后一次时间未取（需读表内字段，属内容面）；若要判"抓取是否已停摆"，
   现在只能说 **sqlite mtime 与 raw 最新目录都停在 08-24**，是一条间接证据。
3. 锁的三个 pid 现在是否还活着未查（`psutil` 级核对属运行期动作，只读单不做）。
4. 执行身份非 glmflash：Qoder 会话直执，扣费为 0 桥积分。
