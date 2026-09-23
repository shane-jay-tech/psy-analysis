# psy literature_feed `trigger='scheduler'` 28 次触发的入口归因（只读取证，2026-09-23）

> 班：`qoder-executor-20260923-0022-psy8` · 单：`s923-10` · 全程只读（未注册/删除任何计划任务、未写库、未改生产码）。
> 取证时刻：2026-09-23 10:45–11:1x（本机时钟）。盘态读数一律标注取值时刻，引本档数值前请复跑。

## 〇、结论速览（先说要害）

1. **s922-17 探针的那句「那 28 次不是走 `run_daily_feed.bat` 来的」被否证。** 真实入口极可能就是 **一个已消失的 Windows 计划任务，动作 = `scripts\run_daily_feed.bat`，每日 09:00 起跑**。
   - 决定性证据：`data/literature_feed/logs/` 的 **NTFS 创建时间 = 2026-05-30 09:00:00**，与首条 scheduler 记录 `2026-05-30T01:00:01Z`（本地 09:00:01）**只差 1 秒**；而全仓（含未跟踪件）**只有 `scripts/run_daily_feed.bat:23` 的 `mkdir` 会创建这个目录**，Python 侧零命中。
   - 「目录里没有 `daily_runner.log`」不再构成「.bat 没跑过」的证据：同目录的 **LastWriteTime = 2026-09-14 08:00:47** 说明该目录**条目在 09-14 被动过**（现为空 ⇒ 最后一次动作是移除）。探针把「目录为空」当不变量，漏看了目录自己的两个时间戳。
2. **28 次触发的性质坐实**：25/28 落在本地 **09:00:01–09:00:03**（秒级抖动 ≤3s），缺口正好落在 06-10、06-11、06-22 三天（机器没开），这是**机器定时**而非人手的签名。3 条离群记录（01:51 / 06:00 / 09:39）另作解释，见 §五 候选 3。
3. **`trigger='scheduler'` 这个值本身不具归因力**：`src/literature_feed/scheduler/__main__.py:31` 的 `--trigger` **默认值就是 `scheduler`**，`daily_runner.py:209` 的 `run_daily(trigger="scheduler")` 同。⇒ 任何裸 `python -m src.literature_feed.scheduler` 都写 `scheduler`。**归因不能靠 trigger 字面值，只能靠文件/时间面** —— 本档因此走目录时间戳。
4. **任务消失的时间窗**：`2026-06-27 09:00:47`（最后一条 scheduler 结束）之后 → `2026-09-22 02:4x`（s922-17 那次 `schtasks` 查无）之前。本班复现「现查无任务」（见 §四），但**注册/删除的历史记录不可恢复**（计划任务操作日志为空）。
5. 统计/研究结论面零触碰；`data/` 本体零写入（`feed.sqlite` sha256 前缀 `c9e6a2080a89901e6c390870b2fa69fd`、499712 B，与 s922-17 记录逐字相同）。

## 一、任务书前提逐条实测（含 4 处否证）

| # | 任务书前提 | 实测命令 | 读数 | 判定 |
|---|---|---|---|---|
| 1 | `fetch_runs` 有 28 条 `trigger='scheduler'`，05-30～06-27 | §二 的 sqlite 查询 | 28 条，`run_id` 2..29 连续，`MIN(started_at)=2026-05-30T01:00:01Z`、`MAX=2026-06-27T01:00:02Z` | **成立** |
| 2 | 同探针「28 次全 completed」 | 同上 `GROUP BY trigger,status` | `scheduler/completed = 28`，无其它状态 | **成立** |
| 3 | `src/literature_feed/ui/feed_panel.py:541` 是 `FROM fetch_runs ORDER BY run_id DESC LIMIT 10` | `.venv/...python -X utf8 -c` 按行打印 :536-545 | :541 逐字符相同 | **成立**（无漂移） |
| 4 | `data/literature_feed/feed.sqlite` 在盘 | `ls -la data/literature_feed/` | 499712 B，主库 mtime 2026-08-24 12:42:25；旁有 `-shm`(32768) / `-wal`(20632)，二者 mtime **2026-09-22 04:16:23** | **成立**（边车另有权读，见 §六.3） |
| 5 | 「不是走 `run_daily_feed.bat` 来的」 | `powershell Get-Item ...logs \| Select CreationTime,LastWriteTime` ＋ `rg -n "logs" src/literature_feed --glob '*.py'`（**0 命中**）＋ `rg -n "mkdir" src scripts` | 目录 **创建即 05-30 09:00:00**；仓内唯一建该目录的写点是 `.bat:23` | **否证**（本档主结论） |
| 6 | 「`logs/daily_runner.log` 缺席」 | `ls data/literature_feed/logs/` → 空；`os.walk('D:/code')` 找 `daily_runner.log` → **0 命中** | 文件确实不存在 | 成立，但**推论失效**：目录 `LastWriteTime 09-14 08:00:47` 表明条目被移除过 |
| 7 | 「`schtasks` 查无相关任务」 | `schtasks /Query /FO CSV /V`（GBK 解码，366 行） | 无 `PsyLiteratureFeed`；名字含 `psy/feed/literature` 者为 0 | 成立（探针读数 262 任务，现 366 ⇒ 盘态已漂，两次都查无） |
| 8 | `run_daily_feed.bat:16` 是 `set "PY=python"` | 按行打印全 42 行 | :16 逐字相同；文件自初版 `ec45485`（2026-06-01）**零改动**（`git log --follow -p`） | **成立**（s923-11 的靶点有效） |
| 9 | （隐含）有别的代码会写 `scheduler` 标记 | `rg -n "run_daily\("` 全仓；`feed_panel.py:586-587` UI 子进程显式 `--trigger ui_manual`；`bootstrap_check.py:109` 显式 `app_startup` | 库里 `ui_manual` **0 行**、`manual` 0 行 ⇒ UI「立即抓取」按钮从未被真实点过；app 侧只产 `app_startup` | 成立 ⇒ 28 行只能来自**未显式传 `--trigger` 的入口**（.bat 或裸 CLI） |

## 二、sqlite 只读取证命令（可复算）

⚠️ **不要在原库上直接 `mode=ro` 打开**：本库是 WAL 模式且 `-shm`/`-wal` 现存（纪律档 §十三 的边车坑，`mode=ro` 也会碰边车 mtime）。本班正解 = **复制到 gitignore 的 `tmp/` 后查副本**（复制不改源 mtime）：

```bash
cd /d/code/psy-analysis && mkdir -p tmp/s923-10 && cp data/literature_feed/feed.sqlite* tmp/s923-10/
git check-ignore -v tmp/s923-10/x      # → .gitignore:29:tmp/
D:/code/psy-analysis/.venv/Scripts/python.exe -X utf8 - <<'PY'
import sqlite3
con=sqlite3.connect(r"tmp/s923-10/feed.sqlite"); con.row_factory=sqlite3.Row
# 触发面全貌
for r in con.execute("SELECT trigger,status,COUNT(*),MIN(started_at),MAX(started_at) "
                     "FROM fetch_runs GROUP BY trigger,status"): print(dict(r))
# 28 条清单
for r in con.execute("SELECT run_id,started_at,ended_at,status,summary_json "
                     "FROM fetch_runs WHERE trigger='scheduler' ORDER BY started_at"): print(dict(r))
PY
```

读数（`fetch_runs` 全表 42 行，`MAX(run_id)=42`）：

| trigger | status | 条数 | started_at 区间（UTC） |
|---|---|---|---|
| scheduler | completed | **28** | 2026-05-30T01:00:01Z → 2026-06-27T01:00:02Z |
| app_startup | completed | 5 | 2026-05-29T17:55:09Z → 2026-08-24T04:33:58Z |
| app_startup | abandoned | 7 | 2026-07-10T15:55:38Z → 2026-08-24T04:31:58Z |
| app_startup | failed | 1 | 2026-08-14T16:38:31Z |
| app_startup | running | 1 | **2026-09-21T20:16:23Z（=本地 09-22 04:16:23）** |

28 条逐行清单（本地时间 = UTC+8；`nsources` 取自 `summary_json.sources` 的键数）：

| run_id | started_at（UTC） | 本地 | 星期 | 时长(s) | nsources | fetched | new | dup | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 2026-05-30T01:00:01Z | 05-30 09:00:01 | Sat | 0 | 0 | 0 | 0 | 0 | 与 `logs/` 目录创建 09:00:00 相差 1s |
| 3 | 2026-05-31T01:00:02Z | 05-31 09:00:02 | Sun | 0 | 0 | 0 | 0 | 0 | 空转 |
| 4 | 2026-06-01T01:00:02Z | 06-01 09:00:02 | Mon | 0 | 0 | 0 | 0 | 0 | 空转（仓初始化同日） |
| 5 | 2026-06-02T01:00:02Z | 06-02 09:00:02 | Tue | 0 | 0 | 0 | 0 | 0 | 空转 |
| 6 | 2026-06-03T01:00:02Z | 06-03 09:00:02 | Wed | 0 | 0 | 0 | 0 | 0 | 空转 |
| **7** | 2026-06-03T17:51:10Z | **06-04 01:51:10** | Thu | 42 | 8 | 45 | 45 | 0 | **离群 ①**：seed 后首次实抓，全新 |
| 8 | 2026-06-04T01:00:02Z | 06-04 09:00:02 | Thu | 49 | 8 | 32 | 0 | 32 | |
| 9 | 2026-06-05T01:00:02Z | 06-05 09:00:02 | Fri | 44 | 8 | 33 | 2 | 31 | |
| 10 | 2026-06-06T01:00:02Z | 06-06 09:00:02 | Sat | 46 | 8 | 33 | 0 | 33 | |
| 11 | 2026-06-07T01:00:02Z | 06-07 09:00:02 | Sun | 47 | 8 | 34 | 1 | 33 | |
| 12 | 2026-06-08T01:00:03Z | 06-08 09:00:03 | Mon | 44 | 8 | 34 | 0 | 34 | |
| 13 | 2026-06-09T01:00:02Z | 06-09 09:00:02 | Tue | 175 | 8 | 37 | 5 | 32 | |
| 14 | 2026-06-12T01:00:02Z | 06-12 09:00:02 | Fri | 226 | 8 | 43 | 8 | 35 | **缺 06-10、06-11** |
| 15 | 2026-06-13T01:00:02Z | 06-13 09:00:02 | Sat | 69 | 8 | 44 | 1 | 43 | |
| 16 | 2026-06-14T01:00:02Z | 06-14 09:00:02 | Sun | 42 | 8 | 44 | 0 | 44 | |
| 17 | 2026-06-15T01:00:02Z | 06-15 09:00:02 | Mon | 116 | 8 | 45 | 2 | 43 | |
| 18 | 2026-06-16T01:00:02Z | 06-16 09:00:02 | Tue | 54 | 8 | 27 | 4 | 23 | |
| 19 | 2026-06-17T01:00:02Z | 06-17 09:00:02 | Wed | 54 | 8 | 27 | 1 | 26 | |
| 20 | 2026-06-18T01:00:03Z | 06-18 09:00:03 | Thu | 75 | 8 | 28 | 1 | 27 | |
| 21 | 2026-06-19T01:00:01Z | 06-19 09:00:01 | Fri | 72 | 8 | 36 | 10 | 26 | |
| 22 | 2026-06-20T01:00:01Z | 06-20 09:00:01 | Sat | 102 | 8 | 38 | 2 | 36 | |
| 23 | 2026-06-21T01:00:02Z | 06-21 09:00:02 | Sun | 73 | 8 | 40 | 2 | 38 | |
| **24** | 2026-06-22T22:00:37Z | **06-23 06:00:37** | Tue | 44 | 8 | 41 | 3 | 38 | **离群 ②**：补跑形态（06-22 09:00 那次缺席） |
| **25** | 2026-06-23T01:39:36Z | **06-23 09:39:36** | Tue | 50 | 8 | 39 | 0 | 39 | **离群 ③**：同日第二条，非整点 |
| 26 | 2026-06-24T01:00:02Z | 06-24 09:00:02 | Wed | 47 | 8 | 38 | 0 | 38 | |
| 27 | 2026-06-25T01:00:02Z | 06-25 09:00:02 | Thu | 62 | 8 | 38 | 1 | 37 | |
| 28 | 2026-06-26T01:00:02Z | 06-26 09:00:02 | Fri | 70 | 8 | 36 | 1 | 35 | |
| 29 | 2026-06-27T01:00:02Z | 06-27 09:00:02 | Sat | 45 | 8 | 35 | 0 | 35 | **最后一条 scheduler** |

派生统计（同一份副本上算，命令见上）：

- 本地时分直方图：`[('01:51',1), ('06:00',1), ('09:00',25), ('09:39',1)]` ⇒ **25/28 命中 09:00:01–09:00:03**。
- 跨度 05-30 → 06-27 共 29 天，实到 26 个本地日期，缺 06-10、06-11、06-22（3 天，均工作日）。
- run 2..6 的 `sources` 为空 dict ⇒ 前 5 次是**零源空转**。`scripts/seed_literature_sources.py:3-5` 的自述正对上：「自学习调度（**PsyLiteratureFeed 每日 09:00**）一直在跑，但 `sources` 表为空，导致每天空转、抓 0 篇」——**这是仓内对「任务确实存在且按 09:00 跑」的独立人证**（该文件首入库 097a657，2026-07-14）。
- 28 行 `run_id` 连续无洞 ⇒ 期间无「跑失败到连行都没插」的情况；而 06-27 之后**行都没了**（不是插了失败行）⇒ 调度侧被摘，与「数据抓取失败」不是一回事（与探针一致）。

## 三、`.bat` 是不是入口：三面向交叉

| 面向 | 证据 | 命令 |
|---|---|---|
| 目录时间戳（**决定性**） | `data/literature_feed/logs/` CreationTime **2026/5/30 9:00:00**、LastWriteTime **2026/9/14 8:00:47**、现空。对照 `locks`/`raw`/根目录 CreationTime 均为 2026/5/28 22:14:21（⇒ 时间戳没被统一抹过，读数可信） | `powershell -NoProfile "Get-Item 'data\literature_feed\logs',... \| Select Name,CreationTime,LastWriteTime"` |
| 代码唯一写点 | 建目录/写日志只存在于 `.bat:23,25,26-27,37,40`；`src/literature_feed/**/*.py` 里 `logs` **0 命中**；`paths.py:36-39` 的 `ensure_dirs()` 只建 `DATA_ROOT/raw/locks` 三个目录 | `rg -n "logs" src/literature_feed --glob '*.py'`；`rg -n "mkdir" src scripts` |
| 调度惯例 | 本机确有「每日 09:00 跑 .bat/脚本」的注册面：`\kaoyan-news-daily`(9:00:01，动作是 .bat)、`\WorkspaceBackupGuard`(9:00:01)、`\QuantMorningPipeline`(9:15)、`\PsyWeeklyBackup`(9:30:01)、`\TrainingReminder-早`(9:30) | `schtasks /Query /FO CSV /V`（366 行，取「要运行的任务」列正则 `python\|\.bat\|\.ps1\|psy\|feed` ⇒ 13 命中，**无 feed 相关**） |
| 外部脚本排除 | `D:/code/scripts`、`D:/Program` 下所有 `.bat/.ps1/.cmd` 中提及 `literature_feed` 或 `run_daily_feed` 者：**0**（⇒ 不是仓外包装脚本建的目录） | python 扫描 |
| `.bat` 未被改过 | `git log --follow -p -- scripts/run_daily_feed.bat` 只有初版 `ec45485`；日志路径从未变 ⇒ 探针「也许以前写的是别的路径」这条退路也排除 | 同左 |

## 四、任务删除痕迹（都扑空，如实登记）

- `schtasks /Query /FO CSV /V`：**无 `PsyLiteratureFeed`、无任何名字含 psy/feed/literature 且动作相关者**（366 任务，取值 10:5x）。
- `Get-WinEvent -FilterHashtable @{logname='Microsoft-Windows-TaskScheduler/Operational'}` → **「找不到任何匹配的记录」**（该日志为空或被禁用）⇒ 任务的注册/删除事件不可恢复。
- 全盘（`D:\code`，跳过 `.git/.venv/node_modules/__pycache__/.pytest_cache`）找不到任何 `daily_runner.log`；周备 `D:\code\backups\psy-analysis\psy-*.zip`（4 个，09-04/06/13/20）**包内只有 3 个条目**（`projects/*.json`、`literature_feed/feed.sqlite`）⇒ 日志**未入备份，内容不可恢复**。
- `D:\$Recycle.Bin` 递归按名匹配 `daily*`/`*.log`：0 命中（该目录常受 ACL 遮蔽，**未见不等于没有**，不作否证用）。

⇒ 结论只能到「任务曾存在、现不存在、消失于 06-27 之后 09-22 之前」；**谁删的、哪一天删的未坐实**（不拿「重装/清理」凑结论）。

## 五、候选入口按证据强度排序

| 排名 | 候选 | 能解释什么 | 不能解释什么 | 强度 |
|---|---|---|---|---|
| 1 | **Windows 计划任务（名很可能就是 `.bat` 注释教的 `PsyLiteratureFeed`），动作 = `D:\code\psy-analysis\scripts\run_daily_feed.bat`，Daily 09:00** | 25/28 的 09:00:01–03 秒级命中；缺 3 个工作日（机器关机即跳过，`.bat` 无补跑或补跑被电源管理拦）；`logs/` 目录在 05-30 09:00:00 被创建（**只有 .bat 会建它**）；`trigger='scheduler'`（`.bat:37` 不传 `--trigger`，落 `__main__.py:31` 默认值）；06-27 后行数为零（任务被摘） | 日志文件为何不在（由 09-14 08:00:47 的目录条目移除解释，非候选缺陷） | **★★★★☆** |
| 2 | 同型计划任务但动作 = 裸 `python -m src.literature_feed.scheduler`（不经 .bat） | 时间签名、trigger 默认值、无日志 | **无法解释 09:00:00 那次 `mkdir`**（Python 侧无该写点） | ★☆☆☆☆（基本排除） |
| 3 | 离群 3 条（run 7 的 01:51、run 24 的 06:00、run 25 的 09:39）来自**人工补跑**或 **Task Scheduler「错过计划后尽快启动」补跑** | 三者都带 `trigger='scheduler'`（两条路径同默认值），run 7 恰好是 seed 完成后的首次实抓（new=45 全新） | 无法区分「人按下」与「补跑策略」；本机已无任务对象可读 `/Settings`（`StartWhenAvailable`） | 单列，不改变主排序 |
| 4 | 「任务被删掉」 | 与现查无任务相容 | **它不是解释日志缺席所必需的**（探针把它当必需假设，本档撤掉）；删除时间/执行者不可恢复 | 未坐实 |
| 5 | app / Streamlit 侧（`bootstrap_check` 懒触发、UI「立即抓取」按钮） | — | `bootstrap_check.py:109` 显式 `app_startup`、`feed_panel.py:586-587` 显式 `ui_manual`；库里 `ui_manual` **0 行** ⇒ **排除** | 排除 |

## 六、边界与自证

1. **只读**：未 `schtasks /Create`/`/Delete`/`/Change`，未跑 `.bat`，未跑取数，未写库。全仓受版件只新增本文件一件（见 result 改动清单）。
2. **零写库自证**：`data/literature_feed/feed.sqlite` sha256 前缀 `c9e6a2080a89901e6c390870b2fa69fd`、499712 B，与 s922-17 记录的读数逐字相同；本班所有 SQL 只打在 `tmp/s923-10/` 的副本上。
3. **WAL 边车读数另有一层含义（供 s923-12 用）**：`-shm`/`-wal` 的 mtime **2026-09-22 04:16:23** 与库里 `run 42 started_at=2026-09-21T20:16:23Z`（本地同一时刻）**秒级对齐** ⇒ 边车是那次 `app_startup` 崩跑留下的化石，而 `run 42` 至今 `status='running'`。s923-10 只登记，不在此下结论。
4. **同时否证他档两处**：`zcode-bridge/done/s922-17-psy-litfeed-probe.result.md` §七.1 与 `docs/insights/psy-litfeed-data-plane-probe-20260922.md:69-74`（A4 那一节），以及 `docs/insights/psy-feed-logs-dir-design-20260922.md:23` 表格里「.bat 从未跑过／那 28 次不是走 .bat 来的」三处同源判据。**他档文本一律未改**，更正集中在本档。
5. **时钟风险**：本机时钟本夜双向跳过，故本档时间戳一律注明取值时刻，判据用「同一记录的两源互相咬合」（09:00:00 目录 vs 09:00:01 行）而非绝对时刻。

## 七、留给拍板的人（本班一律未执行）

1. 若要恢复日更：**先做 s923-11（`.bat` 解释器锚定 `.venv`）再注册任务**，否则从「不触发」变「天天触发但全失败」（探针 §七.2 的坑仍有效）。注册动作属人工。
2. 若要坐实「谁建的目录／谁删的日志」：唯一还活着的机读源是 **NTFS USN journal**（`fsutil usn readjournal D:`，需管理员），本班未读；除此之外不可复算。
3. 若想让「入口归因」以后不再靠猜：`docs/insights/psy-feed-logs-dir-design-20260922.md` §六 #4 的 `--log-file` 设计（把 Python 侧日志也落到 `LOG_DIR`）是正解，落码属另一单。
4. 建议在 `fetch_runs.summary_json` 或新增列里落 `pid/host/executable`（现 `summary_json` 只有 12 个键：run_id/trigger/started_at/ended_at/status/sources/extracted_*/budget_exceeded/error，**零进程指纹** ⇒ 这是本次归因只能退到文件时间戳的根因）。属写库/schema 改动，待授权。
