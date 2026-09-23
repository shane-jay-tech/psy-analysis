# psy `fetch_runs` run 39/40「僵尸 running」根因（只读，2026-09-23）

> 班：`qoder-executor-20260923-0022-psy8` · 单：`s923-12` · 全程只读（零写库、零删除、未跑取数）。
> 读数时刻：2026-09-23 11:2x。库副本取自 `tmp/s923-10/feed.sqlite(+‑wal/‑shm)`（复制于 10:5x，sha256 前缀 `c9e6a2080a89901e6c390870b2fa69fd` 与 s922-17 在册值逐字相同）。
> ⚠️ 必须在副本上查：本库是 **WAL** 且 `-shm/-wal` 现存，纪律档 §十三 的 `mode=ro` 边车坑在这里同样成立；且 run 39/40 的现值就**写在 WAL 里**，只读主库会读到旧态。

## 〇、结论速览

1. **任务书的核心前提已被现实否证：run 39/40 不再是 `running`。** 现值 `status='abandoned'`、`ended_at='2026-09-21T20:16:23Z'`。s922-17 探针读数没错（它跑在 09-22 02:4x 本地 = 09-21 **18:4xZ**），但探针落地后约 **1.5 小时**，`run 42` 起跑并把 39/40 扫掉了。⇒ **「启动侧对账在这一批没生效」不成立**，它生效了，只是**迟到了 28 天**。
2. **根因不是对账逻辑坏，而是对账的触发面太窄 ＋ TTL 卡了 42 分钟。** 三条独立事实拼起来：
   - `abandon_stale_runs()` **全仓只有一个调用点**：`daily_runner.py:285`（在 `_run_locked()` 内、`start_run()` 之前）⇒ **只有「下一次 run 起跑」才会扫上一次**，没有定时器、没有 app 打开时扫。
   - 默认 `ttl_seconds=3600`（`feed_store.py:321`）。08-24 那批里，run 41 起跑时（`04:33:58Z`）run 39 才 **42 分钟**、run 40 才 **2 分钟** ⇒ 两条都**没到 TTL，合规地不标**。
   - 之后再没有下一次 run —— **08-24 04:34 → 09-21 20:16，空窗 28 天 15 小时** ⇒ 无人来扫，僵尸态就一直挂着。
3. **7/7 逐秒咬合的算术验证**：库里**每一条** `abandoned` 行的 `ended_at` 都精确等于**下一次 run 的 `started_at`**（见 §二表），这把「谁标的、什么时候标的」钉成可复算事实，无需推测。
4. **现在的唯一僵尸换成了 run 42**（`app_startup`，`started_at=2026-09-21T20:16:23Z`，`ended_at`/`summary_json`/`error_json` 全 NULL），它同时留下两枚化石：`feed.sqlite-wal`/`-shm` 的 mtime = **2026-09-22 04:16:23**（本地，与 `started_at` 同一秒），以及 `locks/feed_fetch.lock` 里的 `pid=111228 acquired_at=2026-09-21T20:16:23+00:00`。⇒ **同一个缺陷在自传**：扫别人的那次 run 自己死了，而下一次 run 至今没来。
5. **腰斩机制坐实（且能解释「为什么僵尸全在 `app_startup` 面」**：`bootstrap_check.py:84-91` 用 **`daemon=True` 后台线程**跑 `run_daily(trigger="app_startup")`。关 Streamlit / 关终端 / 重启解释器时，daemon 线程被**直接掐死**，`finally`/`finish_run` 不执行 ⇒ 行停在 `running`。旁证：`.bat` 时代的 **28 条 scheduler 行零 abandoned、零 running（全 completed）**，而全部 7 条 abandoned ＋ 1 条 running 都出自 `app_startup`。`_safe_run` 本身 catch `Exception`（:122），所以**普通异常会落成 `failed` 行而不是僵尸**（run 35 就是 `failed` 且有 summary）⇒ 僵尸专门对应「进程被终止」。
6. **裁决输入**：原任务书暗示要「清理 39/40」。现在**已无需手工清库**——建议撤销这条写库诉求，最多只剩「给 run 42 收尾」，而它会**在下一次 run 起跑时被自动标 `abandoned`**（已验证 7/7 次都是这个行为）。真正值得修的是**触发面**，见 §六。

## 一、任务书前提逐条实测

| 前提 | 实测命令 | 读数 | 判定 |
|---|---|---|---|
| run 39/40 至今 `status='running'`、`ended_at` NULL | `SELECT run_id,status,started_at,ended_at FROM fetch_runs WHERE run_id IN (39,40)` | 两条均 **`abandoned`**，`ended_at=2026-09-21T20:16:23Z`（副本上另有 WAL，见开头警告） | **否证（前提过期）** |
| 08-14 那 5 次同类有被标 `abandoned` 的痕迹 | 同表 `WHERE started_at LIKE '2026-08-14%'` | 08-14 共 **5 行**（34..38），其中 **4 行 abandoned ＋ 1 行 failed**（run 35）；「5 次都被标 abandoned」表述偏松 | 基本成立，**收窄** |
| 启动侧对账在 08-24 这批没生效 | §四 算术 | 生效了，只是**迟到 28 天**；08-24 当时**不该生效**（未过 TTL） | **否证**（改判为「触发面太窄」） |
| 「同一次运行留下了两条僵尸行 39/40」 | 两条 `started_at` 相差 **40 分 1 秒**；`raw/` 父目录 mtime = 本地 11:52:06 = **03:52:06Z**（run 39 建日目录），`raw/2026-08-24/` 子目录 mtime = **04:32:36Z**（run 40 起跑后 38 秒建最后一个 raw 文件），6 个 `.jsonl` 自身 mtime = **04:34:06–39Z**（run 41 追加） | **两次独立运行、各自抓过 raw 才被腰斩**，不是一次运行留两行 | **否证** |
| `src/literature_feed/ui/feed_panel.py:541` 是那条 `FROM fetch_runs ORDER BY run_id DESC LIMIT 10` | 按行打印 :536-545 | 逐字相同 ⇒ **UI「最近抓取审计」正好会把僵尸行显示成「running」**（`ORDER BY run_id DESC LIMIT 10` 覆盖 33..42） | 成立（且是用户可见面） |
| `data/` 下文件 mtime 零变化 | 跑前/跑后 181 件 mtime＋size 快照比对（`tmp/data-mtime-snapshot-psy8.json`） | added 0 / removed 0 / changed 0 | **通过** |
| abandoned 写入点存在（要求「按 result 定位」） | `rg -n "abandoned" src tests` | 生产码**唯一**一处命中：`feed_store.py:322`（docstring）＋ `:329`（`SET status = 'abandoned'`）；全仓唯一调用者 `daily_runner.py:285`；测试唯一命中 `test_literature_feed_storage.py:188` | **通过**（单点，无第二条路径） |

## 二、两批 run 字段全貌对照（`run_id ≥ 30`，sqlite 副本实测）

| run_id | trigger | started_at (UTC) | ended_at (UTC) | status | summary_json | error_json | 与下一条的间隔 | 谁把它收尾的 |
|---|---|---|---|---|---|---|---|---|
| 30 | app_startup | 2026-06-28T17:02:39Z | 2026-06-28T17:03:26Z | completed | 1358 B | NULL | 7d | 自己 |
| 31 | app_startup | 2026-07-05T08:09:22Z | 2026-07-05T08:11:17Z | completed | 1358 B | NULL | 5d | 自己 |
| **32** | app_startup | 2026-07-10T15:55:38Z | **2026-07-15T03:29:42Z** | **abandoned** | **NULL** | NULL | 4.5d | **run 33 起跑时扫**（间隔 >TTL ✓） |
| 33 | app_startup | 2026-07-15T03:29:42Z | 2026-07-15T03:31:30Z | completed | 1361 B | NULL | 30d | 自己 |
| **34** | app_startup | 2026-08-14T09:17:08Z | **2026-08-14T16:38:31Z** | **abandoned** | NULL | NULL | 7.4h | **run 35**（>TTL ✓） |
| 35 | app_startup | 2026-08-14T16:38:31Z | 2026-08-14T16:38:34Z | **failed** | 2257 B（含 `Crossref` 报错原文） | NULL | 7 分 | 自己（异常被 `_safe_run` 接住 ⇒ **不是僵尸**） |
| **36** | app_startup | 2026-08-14T16:45:33Z | **2026-08-24T03:51:57Z** | **abandoned** | NULL | NULL | 13 秒 | **run 39**（9d 后） |
| **37** | app_startup | 2026-08-14T16:45:46Z | 同上 | **abandoned** | NULL | NULL | 10 分 | 同上 |
| **38** | app_startup | 2026-08-14T16:56:06Z | 同上 | **abandoned** | NULL | NULL | 9d | 同上 |
| **39** | app_startup | 2026-08-24T03:51:57Z | **2026-09-21T20:16:23Z** | **abandoned** | NULL | NULL | 40 分 | **run 41 没扫（未过 TTL）→ run 42 才扫** |
| **40** | app_startup | 2026-08-24T04:31:58Z | **2026-09-21T20:16:23Z** | **abandoned** | NULL | NULL | 2 分 | 同上 |
| 41 | app_startup | 2026-08-24T04:33:58Z | 2026-08-24T04:34:39Z | completed | 1356 B | NULL | **28d 15h** | 自己（**它扫过 36/37/38，没扫 39/40**） |
| **42** | app_startup | **2026-09-21T20:16:23Z** | **NULL** | **running** | **NULL** | **NULL** | — | **当前唯一僵尸；它自己把 39/40 扫了** |

`raw/` 面同批互证（三枚 mtime 各自落在谁的窗口里）：`raw/` 父目录 = 本地 11:52:06 = **03:52:06Z**（run 39 建出 `2026-08-24/` 日目录）；`raw/2026-08-24/` 子目录 = 本地 12:32:36 = **04:32:36Z**（run 40 起跑后 38 秒建出最后一个 raw 文件 ⇒ 它确实抓过才死）；里面 6 个 `.jsonl` 自身 mtime = **04:34:06–04:34:39Z**（run 41 的写入；向已存在文件追加不 bump 父目录 mtime，故三者不矛盾）。

对照要点（08-14 批 vs 08-24 批）：两批**字段形状完全同构**（`summary_json`/`error_json` 皆 NULL、`ended_at` 全等于下一次 run 的 `started_at`）⇒ **不是两种病，是同一种病的两个阶段**。08-14 批之所以"看起来被正常处理了"，只是因为**下一次 run 恰好隔了 9 天**（>TTL）；08-24 批的下一次 run 只隔了 **2 分钟**（<TTL）。

**abandoned 全表校验（7/7）**：`SELECT run_id,started_at,ended_at FROM fetch_runs WHERE status='abandoned'` 的 `ended_at` 与"下一条 run 的 `started_at`"**逐秒相同**，零例外。

## 三、abandoned 写入点与调用链（行号均为本机 `rg`/按行打印实测）

| 环节 | 位置 | 关键内容 |
|---|---|---|
| 写入 SQL | `src/literature_feed/storage/feed_store.py:321-334` | `def abandon_stale_runs(self, *, ttl_seconds: int = 3600)`；`UPDATE fetch_runs SET status='abandoned', ended_at=? WHERE status='running' AND started_at < ?`；返回 `cur.rowcount` |
| 唯一调用点 | `src/literature_feed/scheduler/daily_runner.py:283-287` | `_run_locked()` 第一件事就是 `self.store.abandon_stale_runs()`（**不传 ttl ⇒ 用默认 3600**），且整块被 `try/except Exception → logger.warning("…（忽略继续）")` 包着 ⇒ 扫失败也不响 |
| 时序 | `daily_runner.py:220-240`、`:289` | `run()` → 抢锁（**锁忙则 `status=skipped_locked` 且 `run_id=0`，根本不写行**）→ `_run_locked()` → 扫别人 → `start_run()` 插自己的 `running` 行 → … → `finish_run()` |
| 收尾 | `feed_store.py:297-319` | `finish_run()` 是唯一把 `ended_at`/`status` 写齐的地方；进程被掐 ⇒ 永不执行 |
| 腰斩源 | `src/literature_feed/scheduler/bootstrap_check.py:84-91` | `threading.Thread(..., name="literature-feed-bootstrap", daemon=True)` ⇒ 解释器退出即被杀 |
| 兜底捕获 | `bootstrap_check.py:106-125` | `_safe_run` catch `Exception` ⇒ 普通异常落 `failed`（有 summary），**僵尸只可能是进程级死亡** |
| 读表面 | `src/literature_feed/ui/feed_panel.py:539-541` | `ORDER BY run_id DESC LIMIT 10` ⇒ 僵尸行会长期显示在「最近抓取审计」里，触发条件是"打开面板"而不是"跑一次" |
| 成功判定 | `feed_store.py:336-343` | `latest_successful_run()` 只认 `('completed','partial')` ⇒ 僵尸行**不影响** bootstrap 的 24h 阈值判定，但也不产生任何告警 |
| 锁面 | `src/literature_feed/scheduler/lock_manager.py:47-57`、`:128-155`、`:170-176` | 锁 TTL **21600s（6h）**、按**锁文件 mtime** 判 stale；`msvcrt.locking` 是**OS 级字节锁**，进程死了自动释放 ⇒ run 41 能在 run 40 死后 2 分钟抢到锁（现存记录 `pid=111228 acquired_at=2026-09-21T20:16:23+00:00` 只是化石，不阻塞） |
| 测试面 | `tests/test_literature_feed_storage.py:173-190` | 只钉了「手工把 `started_at` 改成 2020 年再扫 ⇒ n==1」这一条 SQL 语义；**未钉**「只有下一次 run 才扫」「TTL 与真实 run 间隔的竞争」「UI 显示态」三件事 |

## 四、根因（算术版，可复算）

**为什么 run 41（08-24 04:33:58Z）没扫掉 39/40：**

```
cutoff = now - 3600s = 04:33:58Z - 1h = 03:33:58Z
run 39 started_at = 03:51:57Z  >  cutoff  ⇒ 不满足 `started_at < cutoff` ⇒ 不标
run 40 started_at = 04:31:58Z  >  cutoff  ⇒ 同上
```

**为什么之后 28 天没人扫：** 库里 `run_id>41` 的下一条是 `42`，`started_at=2026-09-21T20:16:23Z`。中间**零行**（`skipped_locked` 不写行，所以「锁忙被跳过」也留不下痕迹）。⇒ 扫的动作只能等下一次真跑。

**为什么 run 42 扫掉了：**

```
cutoff = 2026-09-21T20:16:23Z - 1h = 2026-09-21T19:16:23Z
run 39 (2026-08-24T03:51:57Z) < cutoff ⇒ 标，ended_at = utc_now = 20:16:23Z ✓
run 40 (2026-08-24T04:31:58Z) < cutoff ⇒ 标，同上 ✓
```
两条的 `ended_at` 实测正是 `2026-09-21T20:16:23Z`（= run 42 自己的 `started_at`），**逐秒对上**，与 §二 的 7/7 校验同构。

⇒ **结论：根因 = 「对账只有下一次 run 会做」×「默认 TTL 1h」×「触发面（app 打开 / .bat）本来就可能 28 天不跑」三者相乘**；`abandon_stale_runs()` 本身的 SQL 与字符串时间比较（全库 `started_at` 同型 `YYYY-MM-DDTHH:MM:SSZ`，定长 ⇒ 字典序＝时间序，无比较风险）**没有缺陷**。所以任务书里「启动侧对账没生效，根因未查」这一格可以**结掉**：它生效了，缺的是"谁来触发它"。

## 五、顺带否证/修正的三处在册说法

1. **s922-17 探针 §四.1**「08-14 那 5 条被标 abandoned 就是它（启动侧对账）干的」——**部分修正**：08-14 的 5 条里只有 4 条 abandoned，run 35 是 `failed`（自己收尾）；且 34 由 run 35 扫、36/37/38 由 **run 39** 扫（不是 08-14 当场处理完的）。
2. **同段**「同一次运行留下了两条僵尸行」——否证：39 与 40 相差 **40 分 1 秒**，是两次独立腰斩。旁证三条：① 探针 §四.1 自己引过 `locks/feed_fetch.lock` 里是**两条 acquire 记录**（03:51:57 与 04:31:58，两个 pid 65436/72588）；② `lock_manager.py:236-248` 的 `_write_owner_info` 是 `seek(0,2)` **追加**写 ⇒ 多条记录＝多次 acquire，不是一次写两行；③ `raw/2026-08-24/` 子目录 mtime 落在 run 40 起跑后 38 秒（§二）。⇒ 一条 run 只留一行僵尸。
3. **A2「锁墓碑」**——修正为**不阻塞，且旧记录已被机制自清**：锁是 `msvcrt.locking` 字节锁（进程死即由 OS 释放），文件里的 owner 记录只在 **mtime > 21600s（6h）** 时被 `break_stale()` 连文件一起删掉重建（`lock_manager.py:157-176`）。run 41 能在 run 40 死后 2 分钟起跑即是反证。**现存文件只剩 run 42 一条记录**（52 B，mtime 09-22 04:16:23）⇒ 恰说明 run 42 起跑时把 28 天前的旧锁文件当 stale 清了，探针见过的那两条 08-24 记录已随之消失。⇒ 墓碑"读起来吓人"而非功能缺陷；但记录里的 `pid` 早已不存在、无人回收，属可观测性问题。
   > ⚠️ **失效注（pd05 `20260924-0045-pd05`，2026-09-24 01:3x 追加）**：本条引用的**现场锚点已不存在**。`locks/feed_fetch.lock` 现值 **104 B / 两条记录**（`pid=130036 acquired_at=2026-09-23T03:55:07+00:00` ＋ `pid=135684 acquired_at=2026-09-23T04:15:30+00:00`，sha8 `d9c6c878`，mtime 2026-09-23 12:15:30）——**本条赖以立论的「只剩 run 42 一条记录（52 B，mtime 09-22 04:16:23）」那条记录已被 `break_stale()` 连文件删掉覆盖，全仓无任何字节副本**（`tmp/` 下仅存的两枚 `.lock` 均为覆盖后态）。⇒ 本条「三源互证」中「锁记录」这一源降级为**文档转述**，**该链自此半机读**：run 42 的 `started_at` 仍可由 ① `fetch_runs` 行本体 ＋ ② `tmp/s923-13/feed.sqlite-wal` 的 mtime（09-22 04:16:23，逐秒对齐）两源复算，但**活库边车的 mtime 现场亦已失效**，复核只能依赖那份不受 git 管的快照。本注不改本条结论，只登记证据损失。详见 `psy-litfeed-evidence-loss-rollback-20260924.md` §二。

## 六、修复设计（本单一律不落码、不写库；按代价从低到高）

| # | 动作 | 落点 | 代价/风险 | 是否需授权 |
|---|---|---|---|---|
| 1 | **把 `abandon_stale_runs()` 的调用点从"仅 `_run_locked`"扩到"UI 面板渲染时 ＋ `bootstrap_check.evaluate()` 之前"**（只扫不改语义，TTL 沿用） | `feed_panel.py` 读表前、`bootstrap_check.py` 判阈值前 | 打开 app 即自愈，28 天空窗被压成"下次开 app"；但把写库动作搬进了**读路径**（app 打开即写库，`data/` 快照/审计类断言会受影响） | **是**（写库面） |
| 2 | **僵尸显示态收窄（零写库）**：UI 里 `status='running' 且 started_at 距今 > ttl` 显示为「疑似中断」，并把 `is_running()`（进程内线程存活）作为第二判据 | `feed_panel.py:539-560` | 纯读侧，最低风险，**不动数据**；治标（库里仍是 `running`） | 否（只读展示） |
| 3 | **`start_run()` 即写 pid/host 进 `summary_json`（或新增 `pid` 列）**，让腰斩行至少可归因 | `feed_store.py:289-295` ＋ `schema.sql:32` 一带 | 现在僵尸行三个 JSON 字段全 NULL，什么都不知道；加列属 schema 迁移 | **是**（schema） |
| 4 | **TTL 与锁 TTL 对齐口径**：`abandon_stale_runs` 默认 3600s 与 `lock_manager` 的 21600s 语义不同（一个是"死透了"，一个是"可以强抢"），应在两处 docstring 互相指认并考虑由 `--json-summary` 暴露实际扫掉的条数（现返回值被 `daily_runner.py:285` **丢弃**，日志里也没有） | `feed_store.py:321`、`daily_runner.py:284-287` | 纯可观测性；不改行为 | 小改，建议与 #1 并单 |
| 5 | **`daemon=True` 改子进程**：app 侧兜底改走 `feed_panel.py:579 _spawn_scheduler_subprocess()` 那套（`DETACHED_PROCESS`），进程与 app 生命周期解耦 ⇒ 腰斩概率骤降；代价是 trigger 会从 `app_startup` 变成显式传入的值，**历史序列会出现新的断层**（口径要先定） | `bootstrap_check.py:84-91` | 行为改动 ＋ 口径变更 | **是**（需裁决） |
| 6 | 撤销「手工清 39/40」的写库诉求 | — | 已自愈；再手工 UPDATE 等于**污染那条 `ended_at` 的取证价值**（它是 7/7 咬合链的一环） | 建议主班直接销案 |

## 七、取证边界与自证

- 只读：未执行任何 `UPDATE/DELETE`、未跑 `.bat`、未跑抓取、未注册/删除计划任务、未改任何生产码或测试。
- `data/` **零变化**：181 件 mtime＋size 跑前/跑后逐项相等（`tmp/data-mtime-snapshot-psy8.json`）；`feed.sqlite` 本体 sha256 前缀与 s922-17 在册值逐字相同；`locks/feed_fetch.lock`（52 B，mtime 2026-09-22 04:16:23）只读不写。
  > ⚠️ **失效注（pd05，2026-09-24 追加）**：本行「只读不写」对 **psy8 本班当次成立**（本班未写，收工复核 181 件 sha256 与开工逐件相同 ⇒ 本班未参与写坏），但**它引用的现场锚点已失效**：该锁文件现为 104 B／两条记录（`pid=130036`／`pid=135684`，mtime 2026-09-23 12:15:30），run 42 那条 52 B 原件已被 `break_stale()` 覆盖且**无任何字节副本**。⇒ **后续班不得再用「现场能看到 52 B 的 run 42 锁记录」来复核本档**；该值只存在于本文档及 s923-10／纪律档 §廿一 的转述中。
  > 🔴 **下传纪律句（涉 WAL 活库取证，pd05 复述并加严）**：本档「必须在副本上查」的要求继续成立，但要补两条 —— ① **先 `shutil.copy2` 三件套（`feed.sqlite` ＋ `-wal` ＋ `-shm`，注意后缀不是 `.sqlite-wal`）再取数，复制后核对 WAL 字节数非零**；② **读副本一律 `?mode=ro`，禁止加 `immutable=1`** —— 带活 WAL 时它会跳过重放、只读主文件旧镜像，**不报错而是直接得出「最新一行不存在」的假事实**（台账 **#164** 主班已就此撤回旧口径；pd05 在同一副本上复现：`immutable=1` → `fetch_runs` 43/43，纯 `mode=ro` → 44/44，差的正是 12:15 真 app 那行 run 44）。另加一条：**判「有没有人写了库」不能看 db 文件 sha**，WAL checkpoint 会在逻辑零变化的前提下改掉主文件字节像（pd05 实测 `tmp/s923-10` 与写坏前快照 `tmp/s923-13` **9 张表逐行全等而 sha8 不同**）。

- 所有 SQL 只打在 `tmp/s923-10/` 的库副本上（含 `-wal`/`-shm` 同批复制，故 run 42 写在 WAL 里的 39/40 变更可见）。**这是本单能看到「39/40 已被扫」的前提** —— 若当初用 `mode=ro` 只读主库，会看到与探针相同的旧态并再次误判。
- 时钟：本机时钟本夜双向跳过，故判据不依赖绝对时刻，全部用**同一进程留下的两源互证**（`ended_at` vs 下一条 `started_at`、库行 vs 锁文件/WAL mtime）。
- 未坐实项：**run 42 具体死于什么**（用户关 app / 关机 / 崩溃皆与证据相容，进程级死亡之外无法区分）；`run 36/37/38` 为何 13 秒内连开两次（形似人工连点"立即抓取"，但 `ui_manual` 在库里 0 行 ⇒ 该按钮路径当时未用或代码更晚，**不强行解释**）；08-14 与 08-24 两天的原始终端输出不可恢复（`daily_runner.log` 已于 09-14 08:00:47 被移出目录，见 s923-10 §四）。
