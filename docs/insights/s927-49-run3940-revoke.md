# s927-49 · run 39/40 僵尸态写库诉求：**撤销确认单**（2026-09-28）

> 结论先说（账目确认，非数值裁决）：**`s923-12` 提的「撤销清理 run 39/40 的写库诉求」这条建议成立，本班复核后确认**。
> 依据是四条现算读数：①run 39/40 现态仍是 `abandoned`（自愈态保持 7 天未回退）；②自愈机制仍在工作（run 42 之后也已被扫）；
> ③`ended_at` 咬合链 8/8 无一例外 ⇒ **自 09-23 至今没有任何人手工 UPDATE 过这张表**；④主库／`-wal` 字节读数与 09-24 主班独立复核值逐字相同。
> ⚠ 同时确认一条**必须写清的边界**：撤销的是「清 39/40」这一条具体诉求，**不等于**「库里已无 running 行」——
> 现仍有 **run 43／run 44 两枚 `running`**（各已挂约 125 小时，均已过 TTL），而处置正解仍是「跑一次让它自己被扫」，**属写库＋抓取动作＝人工闸，本班未跑**。
>
> 班：`qoder-executor-20260928-1700-psy95`（只读路）· HEAD `63d96c871a805516d889cf897213a62a53f446cf`（本班 `git log -1` 现取）
> · 探针：`D:\code\tmp\qoder-executor-20260928-1700-psy95\probe_runs.py`（源侧 `mode=ro`，零写）

---

## 1. 被撤销的诉求原文与它的两个「还活着的载体」

`s927-49` 卷宗锚点（`zcode-bridge/done/s923-12.result.md:53`，本班现点逐字）：

> **需要主班裁决的出口（重要）**：s922-17 §五.3 与原任务书都指向「清理 run 39/40 的 running 僵尸态」——**该写库诉求应撤销**（已自愈；再手工 UPDATE 会破坏 §二 的 7/7 取证链）。若仍要动库，唯一剩余对象是 **run 42**，而正解是「跑一次让它自己被扫」而不是手工标。

诉求本身（写库动作）在两处仍作为**待办**存在，且都**没有被追注撤销**（这是「防后续班再按旧任务书写库」的真实风险面）：

| 载体 | 位置 | 现文（未订正） | 性质 |
|---|---|---|---|
| 探针 result | `zcode-bridge/done/s922-17-psy-litfeed-probe.result.md:69` | 「`fetch_runs` 的 run 39 / 40 至今 `status='running'`、`ended_at` NULL…属写库修复，本单只读不做」 | 信箱归档件（主班写端，本班不动） |
| 在册探针档 | `docs/insights/psy-litfeed-data-plane-probe-20260922.md:84` 表第 3 行 | 「清理 `fetch_runs` 里 run 39/40 的 `'running'` 僵尸态、补 `.bat` 日志接线（A4）｜属写库动作＋生产码改动，本单只读不做｜**日间另派**」 | 已入库文档（tracked、工作树干净，本班不改） |
| 撤销建议（在册） | `docs/insights/psy-feed-zombie-runs-20260923.md:17`／`:109`（§六 出口 6） | 「现在**已无需手工清库**——建议撤销这条写库诉求…｜建议主班直接销案」 | s923-12 本人的建议，**但销案动作从未落**（见 §4） |

⇒ 注：锚点里写的「s922-17 §五.3」在盘上的实际形态是 **result 第 69 行的编号项 3**（`s922-17 result` 无「§七.1」一事台账 217 ⑦ 已登记为假锚点先例）；本班按磁盘实况定位，未判锚点失效。

## 2. 现态复算（本班 `mode=ro` 读数，逐条可复跑）

`SELECT run_id, trigger, status, started_at, ended_at, length(summary_json), length(error_json) FROM fetch_runs WHERE run_id IN (39,40)`：

```
(39, 'app_startup', 'abandoned', '2026-08-24T03:51:57Z', '2026-09-21T20:16:23Z', None, None)
(40, 'app_startup', 'abandoned', '2026-08-24T04:31:58Z', '2026-09-21T20:16:23Z', None, None)
```

⇒ 与 `s923-12` 在册读数**逐字相同**（`status='abandoned'`、`ended_at=2026-09-21T20:16:23Z`）：**「已自愈」这件事到今天仍然为真**，没有被回退、没有被改写。列名清单同步现取：`['run_id','trigger','started_at','ended_at','status','summary_json','error_json']`（**无 `id` 列**，与台账 89 的警告一致）。

全表形状（`run_id >= 30`）：`completed 33 / abandoned 8 / running 2 / failed 1`，`max(run_id)=44`、`max(started_at)=2026-09-23T04:15:30Z`
⇒ **09-23 之后再没有 run 发生过**（这是 run 43/44 至今仍是 `running` 的唯一原因，也是 `s923-12` 根因③「无人来扫」的第 2 次复现）。

## 3. 自愈证据（比 s923-12 更硬的一条：机制仍在自证）

`s923-12` 当时写「当前唯一僵尸是 run 42」。本班现算：**run 42 也已被扫掉**——

```
(42, 'app_startup', 'abandoned', '2026-09-21T20:16:23Z', '2026-09-23T03:55:07Z')
(43, 'app_startup', 'running',   '2026-09-23T03:55:07Z', None)
(44, 'app_startup', 'running',   '2026-09-23T04:15:30Z', None)
```

`run 42 的 ended_at == run 43 的 started_at` ⇒ **是 run 43 起跑时 `abandon_stale_runs()` 扫掉了 42**，与 `s923-12` §四 的算术根因**完全同型**，证明：机制健在、且这 7 天里没被人工干预替代。

`ended_at` 咬合链两口径（本班自校脚本，全 8 条 abandoned）：

| 口径 | 定义 | 闭合 |
|---|---|---|
| 甲（`s923-12` 原文的朴素写法） | `ended_at` == **紧邻下一条 run** 的 `started_at` | **4/8**（32→33、34→35、38→39、42→43 命中；36/37/39/40 落空） |
| 乙（本班订正） | `ended_at` == **当次 sweep 的起跑行**（其后可匹配到的任一条 `started_at`） | **8/8，零例外**：36/37/38 三条同指 run 39；39/40 两条同指 run 42 |

⇒ 落空的四条**全是「一次 sweep 同时扫掉多条」**（36/37/38 与 39/40 各自的 `ended_at` 完全相同），所以甲口径本身不适用于批量场景。
`s923-12` 说的「7/7 逐秒算术」在乙口径下今天扩到 **8/8 且零例外**——**这条链是「谁标的、何时标的」的唯一凭据，手工 UPDATE 会就地销毁它**（这正是撤销诉求的核心理由，且本班复核后它**仍然未被销毁**）。

## 4. 撤销建议为何成立（＋为什么它一直没被登记）

1. **对象已不存在**：39/40 不再是 `running`（§2）⇒ 诉求的宾语消失，执行它无从下手。
2. **执行它有害**：会把两条 `ended_at` 从 `2026-09-21T20:16:23Z`（＝run 42 起跑时刻，链上一环）改成人工时刻，直接破坏 §3 的 8/8 咬合证据。
3. **机制自己会做完剩下的事**：`feed_store.py:321 abandon_stale_runs(ttl_seconds=3600)` 的 SQL 是
   `UPDATE fetch_runs SET status='abandoned', ended_at=? WHERE status='running' AND started_at < ?`，
   唯一调用点 `daily_runner.py:291`（在 `_run_locked()` 内、`start_run()` 之前）。
   run 43/44 的 `started_at` 距本班现算 UTC 时刻（`2026-09-28T09:09:01Z`）已 **125.2 h / 124.9 h**，**双双越过 3600 s TTL**
   ⇒ 下一次 run 一起跑就会把它们标掉，**无需手工**。
4. **未落账实为流程缺口**：`psy-feed-zombie-runs-20260923.md:109` 写明「建议主班直接销案」，但待人工台账
   `D:\code\docs\insights\drain-20260923-pending-human.md` 的 `s923-12` 相关行（第 38 行 #89／第 128 行 #179）
   讨论的是**回滚配方与写坏归因**，**没有一条是「撤销清 39/40 诉求」的销案条目** ⇒ 该建议至今处于「有建议、无账」状态。
   本单就是把这笔账落清（**账目确认，不改任何在册件**）。

⚠ 顺带闭合一条：`s923-12` 遗留问题 2（sweep 返回值被丢弃 ⇒ 现场无法回答「对账到底做没做」）**已由前人入库闭合**，非本班改动。
证据：`git log -S"abandon_stale_runs 清理"` → `1657af8 2026-09-25 04:18:48 +0800 fix(psy): s924-14＋s924-15 两单同归本笔（… 调度器 stale 弃单计数可观测）`，
`git show --stat 1657af8` 列 `src/literature_feed/scheduler/daily_runner.py | 16 +++++++++--`、`tests/test_literature_feed_scheduler.py | 39 +++`；
现读 `daily_runner.py:291-296` 已是 `n = self.store.abandon_stale_runs() or 0` ＋ `logger.info("abandon_stale_runs 清理 %d 条 running 僵尸", n)`。
⇒ 行号已自 `s923-12` 的 `:283-287` 漂到 `:291-296`，后续引该链的行号以现值为准。

## 5. 零写自证（本单完成标准 ③）

- 连接方式：`sqlite3.connect("file:...feed.sqlite?mode=ro", uri=True)`（源侧只读，规避台账 217 ⑳ 的「读写打开末连触发 checkpoint」自伤）。
- 当场试写两发均被拒：`UPDATE fetch_runs SET status='running' WHERE run_id=39` 与 `DELETE FROM fetch_runs WHERE run_id=0`
  ⇒ 均回 `OperationalError: attempt to write a readonly database`；随后 `rollback()` 并 `close()`。
- 三点取样不变：主库 `size=499712 sha8=6bf5776b mtime=1790136930` 取数前后逐位相同；`-wal` `741632 B sha8=4f9f07db`、`-shm 32768 B` 同值。
  ⚠ 只读连接仍可能刷新 `-shm` 头（w40 §6 口径），故主证以**主库 size／sha 不变**为准。
- **跨班互证**：本班 `db 6bf5776b`／`wal 4f9f07db(741,632 B)` 与台账 #179 主班 09-24 独立复核读数**逐字相同**
  ⇒ `data/literature_feed/`（被 `.gitignore` 覆盖、无还原点）**自 09-24 起数据面未动**，「有人已按旧任务书写库」的担心在字节层被否证。
- 未跑 `.bat`、未跑抓取、未注册/删除计划任务、未动 `src/`、未动 `zcode-bridge/**` 写端、未 `git add`／`commit`。

## 6. 交回主班／人工的三个出口（本班一律不代执行）

1. **账**：把「撤销清理 run 39/40 的写库诉求」正式销案（建议挂到待人工台账新增行的「已处置」侧，或按 §7 note 文本落 claims）。
2. **文**：给 §1 表里两枚仍在世的载体加**失效注**（不改历史正文，只加一行「该诉求已由 s927-49 确认撤销」），建议文本见 §7。
3. **库**：若要清 run 43/44，唯一正解是**跑一次日更**让 `abandon_stale_runs()` 自扫（＝写库＋真实抓取，人工闸）；
   在跑之前请一并决定是否清 `locks/feed_fetch.lock`（现读 104 B，两条 acquire 记录
   `pid=130036 acquired_at=2026-09-23T03:55:07+00:00`／`pid=135684 acquired_at=2026-09-23T04:15:30+00:00`，
   与 run 43/44 一一对应；台账 #166 已钉「读侧取首条 ⇒ 这类 pid 只能当**历史 acquire** 读」，本班复点仍成立）。

## 7. 建议文本（只出文本，本班不代落）

- claims note 建议（主班代登时可用）：
  `s923-12 遗留 1 的「撤销清理 run 39/40 写库诉求」经 s927-49 现算复核成立并销案；库里另有 run 43/44 两枚 running（各挂 125 h，已过 TTL），清它们走「跑一次自扫」＝人工闸，勿手工 UPDATE（ended_at 咬合链 8/8 是唯一的归因凭据）。`
- `psy-litfeed-data-plane-probe-20260922.md:84` 建议加注：
  `【2026-09-28 s927-49 订正】本行「清理 run 39/40」诉求**已撤销**：两条自 2026-09-21T20:16:23Z 起即为 abandoned（由 run 42 起跑时自动扫出），手工 UPDATE 会销毁 ended_at 咬合链取证。`
- `s922-17 result` 第 69 行的处理**不动**（信箱归档件，append-only 纪律；要否证就在 s927-49 侧写，本班已做）。

## 8. 本单未做（红线自陈）

未连生产库做任何写入；未跑抓取／`.bat`／计划任务；未移动信箱件（除卷宗按三步收口外）；
未改 `zcode-bridge/**` 任何写端与 `claims.log`（除经 `claims_writer.py` 落本班 claim/done 行）；
未对「僵尸态是否属缺陷」「TTL/锁 TTL 谁该更严」等口径下判断（`s923-12` 遗留 3/4 仍挂账）；
未消红、未挂 NEEDS_MIGRATION、未写白名单。
