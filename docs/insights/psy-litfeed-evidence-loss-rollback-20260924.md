# psy `data/literature_feed/` 证据损失登记 ＋ 回滚可行性核对（pd05，2026-09-24，只读·零改动）

> 班：`qoder-executor-20260924-0126-psy20` · 单：`20260924-0045-pd05` · cwd `D:\code\psy-analysis`
> 用户裁决：**①5 呈报方选案 B —— 不回滚**。本档只做两件事：① 把已发生的证据损失登记在案；② 出「**若**日后要回滚」的可行性核对。
> 🔴 **本单数据零改动**：`data/literature_feed/` 全 181 件 sha256 开工＝收工逐件相同（见 §七）。未执行任何还原、未删任何文件、未对任何库发起写连接、未做 checkpoint。
> 上游：纪律档 §廿一（`D:\code\tmp\executor-drain-discipline-20260923.md:242`）、台账 #89 / #164 / #166（`D:\code\docs\insights\drain-20260923-pending-human.md:38/113/115`）、s923-12 档 `docs/insights/psy-feed-zombie-runs-20260923.md`。

---

## 〇、结论先说（五条）

1. **真正永久损失只有一项：`locks/feed_fetch.lock` 里 run 42 那条 acquire 记录（52 B 原件）的字节层证据。** 全仓盘上**不存在任何一份含该记录的副本**（逐件核过，见 §二.1）。它的数值内容仍以人工转述活在两份文档里，所以是**「降级为半机读」而非「全灭」**。
2. **回滚技术上可行、语义上不可取。** 快照 `tmp/s923-13/` 三件齐全、`PRAGMA integrity_check` = `ok`、当前无进程持库 ⇒ 能回。但回一次的代价是**不可逆地销毁真 app 会话（run 44）的全部产物**：24 篇 `articles` ＋ 2 行 `fetch_runs` ＋ 8 行 `sources` 的抓取水位，并**打断 s923-12 的核心取证链**。⇒ 与案 B 一致，**本单不执行**。
3. 🆕 **推翻一条在册论证方式（本单最重要的技术产出）**：`tmp/s923-10/feed.sqlite`（sha8 `167f6a81`）与写坏前快照 `tmp/s923-13/feed.sqlite`（sha8 `c9e6a208`）**逐表逐行完全相同**（9 张表全 `row-identical=True`，见 §三.①）。⇒ **db 文件 sha 变化无法区分「checkpoint 折叠」与「真写入」**。台账 #89 / §廿一 用「sha 变更早于 psy10」推导出的归因结论，**其证据基础不成立**（结论本身可能对，但这条论据无效）。
4. **在册现场已二次失效**：s923-12 档 §五.3 与 §七 两处把锁文件「52 B / mtime 09-22 04:16:23 / 只剩 run 42 一条记录」当作自证依据 —— 该现场已被覆盖（现 104 B 两条记录）。已在原档就地追加失效注（§二.1 末）。
5. **台账 #164 主班撤回的 `immutable=1` 口径，本单在同一份副本上独立复现**：`mode=ro&immutable=1` → `fetch_runs` **43/43**；纯 `mode=ro` → **44/44**。**缺的那一行恰是 run 44** —— 即「最新真 app 写入」。**用错读法的人会当场得出「run 44 不存在」这一假事实。**

---

## 一、三件套现值 vs 快照值对照表

| 件 | size | sha256（全 64 位） | mtime |
|---|---|---|---|
| **现态** `data/literature_feed/feed.sqlite` | 499,712 | `6bf5776b0cd927c89d0f6f0f7766ab7f87e220506f6b77516e55bc57e86215d6` | 2026-09-23 12:15:30 |
| **现态** `…/feed.sqlite-wal` | 741,632 | `4f9f07db98c190b7b06f0742b06ae01ede950c633d77decdb4365c388cebde2e` | 2026-09-23 12:16:18 |
| **现态** `…/feed.sqlite-shm` | 32,768 | `07f5299152687bb2fad833e5b07eaae4e2f6c1304dd3ed86638cc5a94db55349` | 2026-09-23 12:15:30 |
| **快照** `tmp/s923-13/feed.sqlite` | 499,712 | `c9e6a2080a89901e6c390870b2fa69fdb63b4b5773529d738892c02227d2c458` | 2026-08-24 12:42:25 |
| **快照** `tmp/s923-13/feed.sqlite-wal` | 20,632 | `5815d8c273e75a2dba4b27cf71c027f5dee0d2a213a9b4dc4074482b599c4962` | 2026-09-22 04:16:23 |
| **快照** `tmp/s923-13/feed.sqlite-shm` | 32,768 | `84725f8654bb94a45b1afa63c1ce6ce9810fcf9a4ac9091afdbd50a20da5139d` | 2026-09-23 11:04:49 |

**逻辑差集（现态 − 快照，逐表 count 复算）**：

| 表 | 快照 | 现态 | 差 | 回滚后果 |
|---|---|---|---|---|
| `fetch_runs` | 42 | 44 | **+2** | 删 run 43/44 ＋ **改** run 42（见 §三.②） |
| `articles` | 151 | 175 | **+24** | 删 24 行（全部 `fetch_run_id=44`） |
| `sources` | 8 | 8 | 0（**8 行各 2 列被改**） | 16 个时间戳格退回 8-24 |
| `llm_candidates` | 122 | 122 | 0 | 无变化，**且 0 行引用那 24 篇** ⇒ 回滚不造外键孤儿 |
| `llm_extraction_cache` / `schema_migrations` / `article_keywords` / `candidate_review_events` / `manual_submissions` | 24 / 3 / 0 / 0 / 0 | 同 | 0 | 无变化 |
| `sqlite_sequence` | `fetch_runs=42, articles=151, llm_candidates=122` | `44 / 175 / 122` | — | 🔴 **计数器回退 ⇒ ID 复用串号**（见 §四 R1） |

**现态的其他两份冗余副本（可用于「回滚到现态」而非「回滚到快照」）**：
- `tmp/s923-36/`（12:15 复制）：db sha8 `6bf5776b` ＋ wal sha8 `4f9f07db` ⇒ **与现态逐字节相同**（`-shm` 不同，属瞬态边车，无取证价值）。
- `tmp/s923-24/feed.sqlite`（13:14，540,672 B，sha8 `4ffb6598`，db-only 无边车）：逻辑同现态（44 runs / 175 articles），字节形态不同 ⇒ 是一次 checkpoint 后的折叠像。

---

## 二、证据损失登记（逐条）

### 2.1 🔴 损失项 L1：`locks/feed_fetch.lock` 的 run-42 记录 —— 字节层证据永久丢失

- **时点**：2026-09-23 **11:55:07**（`2026-09-23T03:55:07+00:00`，北京 11:55）。
- **被谁覆盖**：`start-bg.bat` 链路上的锁获取动作（`lock_manager.break_stale()` 在 mtime > 21600 s 时**连文件一起删掉重建**）。run 42 的锁记录 mtime 为 09-22 04:16:23，距 11:55 已 **31 小时 39 分 > 6 小时** ⇒ 触发 stale 清理，旧记录随文件删除消失。
- **原值（机读原件，已不存在）**：52 B 单记录 —— `pid=111228` / `acquired_at=2026-09-21T20:16:23+00:00`（转述自 s923-12 档 §〇.4 / §五.3、s923-10 档，以及纪律档 §廿一）。
- **现值（内容摘要，本单实测）**：104 B **两条**记录，sha8 `d9c6c878`，mtime 2026-09-23 12:15:30：
  ```
  \r\npid=130036 acquired_at=2026-09-23T03:55:07+00:00\r\n\r\npid=135684 acquired_at=2026-09-23T04:15:30+00:00\r\n
  ```
  两条分别对应 run 43（11:55）与 run 44（12:15），**都不含 run 42**。
- **残余证据（还剩什么）**：
  1. `fetch_runs` 里 run 42 的行本体（`started_at='2026-09-21T20:16:23Z'`）仍在库 ⇒ **主证未丢**。
  2. 写坏前的边车 mtime 在 `tmp/s923-13/feed.sqlite-wal` 里**存活**：mtime = **2026-09-22 04:16:23**（本地），与 run 42 `started_at=2026-09-21T20:16:23Z` 同一秒（UTC+8）⇒ 逐秒互证仍可在快照上复算。
  3. 🔴 但**现态**库的 `-wal`/`-shm` mtime 已被改写为 09-23 12:15:30 / 12:16:18 ⇒ 「在活库上当场复算」这条路已死，只能靠 `tmp/s923-13/` 副本 ⇒ **可复核性从「活体」降级为「依赖一份未被 git 管的副本」**。
  4. 锁记录本身只剩**三份文档里的转述**（s923-12 / s923-10 / 纪律档 §廿一），无任何字节副本。
- **副本穷举（证明「原件无处可寻」）**：全 `tmp/` 下只有两枚 `.lock` 文件 —— `tmp/psy12-feed-sandbox/literature_feed/locks/feed_fetch.lock` 与 `tmp/s923-19/litfeed_sandbox/locks/feed_fetch.lock`，二者 sha8 **均为 `d9c6c878`、均为 104 B 两条**，即**都是覆盖之后态的沙盒副本**，不含 run 42 记录。`grep -rl "111228" tmp/ docs/ logs/` 仅命中两份 `.md`（文档转述），**零字节级副本**。
- **该链降级判定**：s923-12 档 §五.3 的原论证结构是**三源互证**（库行 `started_at` ＋ WAL/SHM mtime ＋ 锁记录）。现在第三源字节丢失、第二源在活体上被覆盖（仅存快照副本）⇒ **该链降级为半机读**：结论仍可复算，但复算依赖「快照副本＋文档转述」而非现场活体，**副本一旦丢失即不可恢复**（`data/` 被 `.gitignore:42` 整层覆盖，`tmp/` 同样不受 git 管 ⇒ **无任何 git 还原点**）。

### 2.2 损失项 L2：s923-12 档的两处「现场自证」已失效（在册结论失效）

s923-12 档以下两句引用的是**当时**的锁文件现场，现已不复存在：
- **§五.3**（第 97 行）：「**现存文件只剩 run 42 一条记录**（52 B，mtime 09-22 04:16:23）」—— 现值 104 B 两条，mtime 09-23 12:15:30。
- **§七**（第 113 行）：「`locks/feed_fetch.lock`（52 B，mtime 2026-09-22 04:16:23）只读不写」—— 该「只读不写」自证对**psy8 本班当次**成立，但其**锚点值**已被后续会话改写，故此后任何班**不能再用「现场看到 52 B」来复核 s923-12**。

⇒ 已在原档就地追加失效注（见 §六）。

### 2.3 损失项 L3：10:49 那一刻的字节态不可复现

`tmp/s923-10/` 目录现只剩 `feed.sqlite` ＋ 三支 `q*.py`，**`-wal`/`-shm` 边车已不在盘上**（实测目录清单）。⇒ psy8 那次「10:49 的 db 字节像」只剩主文件、缺 WAL，**该时点的完整字节态永久不可复现**；只剩逻辑态可用（而逻辑态恰与 `tmp/s923-13/` 全等，见 §三.① —— 所以这次损失未造成结论损伤）。

### 2.4 🔴 损失项 L4（结论层）：台账 #89 / §廿一 的归因论证被证伪为无效判据

- **在册说法**（纪律档 §廿一、台账 #89）：「`tmp/s923-10/feed.sqlite`（10:49 复制）已是 `167f6a81` ⇒ **sha 变更早于 psy10** ⇒ 子班自报的归因不成立」。
- **本单实测**：把 `tmp/s923-10/feed.sqlite` 与 `tmp/s923-13/feed.sqlite` 各自 copy2 进沙盒、纯 `mode=ro` 打开、对 9 张表逐行比对 ⇒ **全表 `row-identical=True`**，两库逻辑零差异（同 42 runs / 151 articles，run 42 同为 `status='running'` / `ended_at=NULL`）。
- **判定**：二者 sha8 不同（`167f6a81` vs `c9e6a208`）但逻辑全等 ⇒ **该 sha 差异是 WAL→主文件的 checkpoint 折叠造成的字节变化，不是数据写入**。
- ⇒ **「db 文件 sha 变了」在这套 WAL 布局下不能当「有人写了数据」的判据**。据其做的归因（无论指向 psy10 还是排除 psy10）**都缺证据力**。
- ⚠️ **本单不据此改判责任归属**（那是人工裁决面）；本单只登记「**这条在册论据无效**」这一事实，并把「谁在 11:55 之前打开过库」列为遗留项交人工（另注：台账 #166 已把 12:15 那次写入独立归因到 `start-bg.bat` 真 app 会话，**那条归因不依赖 sha 论证**，不受本条影响）。

---

## 三、回滚可行性核对（只读；逐条给「能不能回／回什么／代价／命令」）

### ① 前置判据复核

- **判定键（任务书点名要答的）**：`fetch_runs` **确实没有 `id` 列**。实际结构：
  `run_id INTEGER PRIMARY KEY AUTOINCREMENT, trigger TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT, status TEXT NOT NULL DEFAULT 'running', summary_json TEXT, error_json TEXT`
  ⇒ **回滚/比对用什么键判定**：主键 **`run_id`**（现值 44/44 distinct）＋ 时间锚 **`started_at`**（实测 **44/44 distinct ⇒ 可作候选唯一键**）。
  ⚠️ §廿一 说「探针要按 `started_at` 取」—— `started_at` 可用，但**它是 UTC 带 `Z` 的文本**（如 `2026-09-23T04:15:30Z`＝北京 12:15:30），比对时别按本地时刻取。
  文章侧归因键是 **`articles.fetch_run_id`**，它**是**真外键：`FOREIGN KEY(fetch_run_id) REFERENCES fetch_runs(run_id)`（`schema.sql:7` 有 `PRAGMA foreign_keys = ON`）。⇒ **外科式删行会撞外键**，整文件回滚则不会（快照自身自洽）。
- **快照可复用性**：`tmp/s923-13/` copy2 副本 `PRAGMA integrity_check` = **`ok`**，10 张表齐、`page_count=122` `freelist=0`；现态副本亦 `ok`（`page_count=132`）。⇒ **还原源没有损坏**。
- **持锁情况**：实测无任何 python/streamlit 进程在跑（`Get-CimInstance Win32_Process` 无 `app.py`/`streamlit` 命中）⇒ **回滚窗口现在是开的**，但**一次 app 启动即会追加 run 45**（43/44 全为 `trigger='app_startup'`），窗口会自己变脏。
- **git 能不能救**：**不能**。`git check-ignore -v` 实证 `.gitignore:42:data/` 同时命中 `feed.sqlite` 与 `locks/feed_fetch.lock`；`git status --porcelain data/` 输出为空。⇒ 唯一还原点就是 §一 那三份**不受版本管**的 `tmp/` 副本。

### ② 回滚到底会改什么（逐行实测，非推演）

```
[回滚即删] run_id=43 -> (43,'app_startup','2026-09-23T03:55:07Z',None,'running',None,None)
[回滚即删] run_id=44 -> (44,'app_startup','2026-09-23T04:15:30Z',None,'running',None,None)
[回滚即改] run_id=42
    快照: (42,'app_startup','2026-09-21T20:16:23Z', None,                  'running',   None,None)
    现态: (42,'app_startup','2026-09-21T20:16:23Z','2026-09-23T03:55:07Z','abandoned', None,None)
[回滚即删] articles 24 行（fetch_run_id=44，fetched_at 2026-09-23T04:15:42Z..04:16:18Z）
    源分布：hrm 3 / jap 12 / job 2 / johp 3 / jvb 3 / personnel_psych 1
[回滚即改] sources 8 行 × 2 列（last_attempt_at / last_success_at）
    例 hrm：'2026-08-24T04:34:06Z' <- 现态 '2026-09-23T04:15:42Z'
```

🔴 **最重的代价（在册文档未记的一项）**：回滚会把 run 42 从 `abandoned` 退回 `running` 并**清空 `ended_at='2026-09-23T03:55:07Z'`**。而这个值恰是 s923-12 全档赖以立论的「**每条 abandoned 行的 `ended_at` 精确等于下一条 run 的 `started_at`**」逐秒算术链的**最新一环（42→43，即 s923-12 的 7/7 链被延长到 8/8 的那一环）**。⇒ **回滚三件套不只是「丢新数据」，它会主动抹掉一条在册取证链的最后一环**，且抹掉后无法从活库复原（须再靠 `tmp/s923-36/` 那份副本反查）。

---

## 四、可行性逐条结论表

| # | 方案 | 能不能回 | 回什么 | 代价 | 命令（**本单未执行**） |
|---|---|---|---|---|---|
| **R1** | 三件套整体回滚到 `tmp/s923-13/`（§廿一 原配方） | ✅ **技术上能**（源齐・`integrity_check=ok`・当前无人持库）；❌ **语义上不该**（案 B 已判不回） | 整库退回 42 runs / 151 articles / sources(8-24 水位) 态 | 🔴 删 run 43＋**run 44（真 app 抓取）**；🔴 删 24 篇 `articles`；🔴 run 42 退回 `running`、**断 8/8 算术链第 8 环**；`sources` 16 格水位退回；🔴 `sqlite_sequence` 回退到 42/151 ⇒ **下次抓取会复用 `run_id=43`、`article_id=152…`，与在册文档已引用的 43/44 撞号**；`raw/2026-09-23/` 345,459 B **不在还原集内 ⇒ 成孤儿**（db 无行、raw 有文件） | `copy2 tmp/s923-13/{feed.sqlite,feed.sqlite-wal,feed.sqlite-shm} → data/literature_feed/`（**三件同批**；回滚前后各取一次 sha256；app 必须先停） |
| **R2** | 只回滚 `feed.sqlite`、不回 `-wal` | ⚠️ **能执行但得到假态** —— 禁 | 主文件回旧，WAL 仍在 | WAL 重放会把新态带回来 ⇒ **产出「既不是快照也不是现态」的第三态**。本单实证其数量级：错误读法下 `fetch_runs` 少 1 行（43 vs 44） | — （不建议，仅记录） |
| **R3** | **不回滚，接受现态 ＋ 只清僵尸行/锁**（台账 #166 建议方向） | ✅ 能，且**与案 B 一致** | 不动历史数据，只把 run 43/44 收尾、清 104 B 锁 | 属**写库**，需人工授权；🔴 手工 `UPDATE` 会毁 `ended_at` 算术链（s923-12 §六.6 同判）⇒ **正解是「跑一次真 app 让它自己被 `abandon_stale_runs` 扫」**，而非手工改 | 由 app 侧 `daily_runner` 触发；不建议任何手写 SQL |
| **R4** | 外科式部分回滚（只删 run 43、保 run 44＋24 篇） | ❌ **不建议** | 单删探针产物、留真数据 | 键是明确的（`run_id`/`started_at`），但：① `articles.fetch_run_id` 有**外键**、`PRAGMA foreign_keys=ON`，删 43 需谨慎；② run 43 的 `started_at` 是 run 42 `ended_at` 的算术锚，删它即**自毁 8/8 链**；③ 制造出库里从未存在过的中间态，后续无法用「谁写的」复算 | — |
| **R5** | 恢复 `locks/feed_fetch.lock` 的 run-42 原件 | ❌ **不能回** | — | 全仓无字节副本（§二.1 穷举）。只能手写一个「看起来对」的 52 B 文件 ⇒ **那是造证据，禁止** | — |
| **R6** | 连带回滚 `raw/`（让 raw 与 db 一致） | ✅ 能（文件层） | 删 `raw/2026-09-23/` 6 件 | **删属破坏性操作**且不可逆（`data/` 无 git）；不做则留 345,459 B 孤儿 | 不执行（本单零删除） |
| **R7** | 回到 09-23 10:49 那一刻的字节态 | ❌ **不能** | — | 该时点的 `-wal`/`-shm` 边车已不在盘上（§二.3）⇒ 只剩逻辑态，字节态永久不可复现 | — |
| **R8** | 回滚到「现态」以防我操作失手（**取证性**回滚） | ✅ **能，且已具备** | 现态 db＋wal | 仅 1 处：`-shm` 与现态不同（`144cf1db` vs 现 `07f52991`），但 shm 是可从 db＋wal 重建的瞬态边车 ⇒ 无实质损失 | 源：`tmp/s923-36/{feed.sqlite,feed.sqlite-wal}`（sha 与现态**逐字节相同**，本单实测） |

---

## 五、给后续只读探针的纪律句（任务书第 3 项）

> 🔴 **涉 WAL 活库取证，一律先 `shutil.copy2` 三件套进 `tmp/` 沙盒、再只读取；禁止对 `data/literature_feed/` 原地开连接、禁止原地 `integrity_check`／checkpoint／`VACUUM`。**
> 三条硬细则：
> 1. **后缀是 `-wal` / `-shm`，不是 `.sqlite-wal`** —— 拼错会「只复制了主文件」，于是两种读法读数相同、反证自毁（台账 #164 主班自曝踩过）。**复制后必须核对 WAL 字节数非零**再取数（本单实证：`feed.sqlite-wal = 741,632 B`）。
> 2. **读副本一律 `?mode=ro`，绝不加 `immutable=1`**。带活 WAL 时 `immutable=1` 会让 SQLite 跳过 WAL 重放、只读主文件旧镜像 ⇒ **不报错、直接得出「最新一行不存在」的假事实**。本单在同一份副本上独立复现：`mode=ro&immutable=1` → `fetch_runs` **43/43**；纯 `mode=ro` → **44/44**，差的恰是 run 44（12:15 真 app 会话）。出处口径＝**台账 #164（主班撤回「`immutable=1` 在 python 侧可用」这条已下发全夜的取证口径）**。
> 3. **别用 db 文件 sha 变化判「谁写了库」**（本单新增，见 §二.4）：WAL checkpoint 会在**逻辑零变化**的前提下改掉主文件 sha。判写入要**逐表逐行差分**，不能只看 sha8/size。

---

## 六、已就地的失效注（s923-12 档，本单唯一的既有档改动）

失效注以**追加**形式落在 `docs/insights/psy-feed-zombie-runs-20260923.md` 的 §五.3 与 §七 两处之后，指向本档。原文两句**未删未改**（改前／改后对照见 result 与本档 §二.2）。纪律档 §廿一 在 `D:\code\tmp\`（**本单 cwd 之外**）⇒ 未碰，其订正转登台账 #89／#164，交人工。

---

## 七、零改动自证

- **全量清单**：`tmp/20260924-0045-pd05/manifest.py` 走 `data/literature_feed/` **每件** sha256＋size＋mtime。
  开工 `lf-sha-start.json` @ `2026-09-24T01:30:49+0800`，收工 `lf-sha-end.json` @ `2026-09-24T01:36:28+0800`。
  ⇒ **181 件 / 21,059,126 B 两端相等；only-in-start `[]`、only-in-end `[]`、CHANGED `[]` ＝ ZERO-DIFF**。
- **三件套开工＝收工**：`feed.sqlite 6bf5776b…` / `-wal 4f9f07db…` / `-shm 07f52991…`（全值见 §一）。
- **取证源原件亦未被改**（本单从这些目录 copy 出数据，须自证没碰原件）：`tmp/s923-13/` 三件（`c9e6a208`/`5815d8c2`/`84725f86`）、`tmp/s923-10/feed.sqlite`（`167f6a81`）、`tmp/s923-36/` db＋wal（`6bf5776b`/`4f9f07db`）、`locks/feed_fetch.lock`（`d9c6c878`）—— 七个原件收工 sha8 与开工**逐一相符**。
- **未执行**：任何 `INSERT/UPDATE/DELETE/DROP/VACUUM`、任何 checkpoint、任何 `.bat`、任何抓取、任何删除、任何 `git commit`/`git add`。所有 sqlite 连接 URI 均带 `mode=ro`，且全部打在 `tmp/20260924-0045-pd05/` 下的副本上。
- **红线遵守**：未碰统计方法／SEM／CFA／效力分析结论、学术诚信、PII 脱敏、导出门禁隐私分级、鉴权／凭据／密钥、资金与统计数值结论。本档出现的数值全部是**文件字节数／sha／行数／时间戳**，无一条是统计或经济结论。

### 复算命令

```
$ .venv/Scripts/python.exe tmp/20260924-0045-pd05/manifest.py tmp/20260924-0045-pd05/lf-sha-start.json
$ .venv/Scripts/python.exe tmp/20260924-0045-pd05/probe_ro.py
$ .venv/Scripts/python.exe tmp/20260924-0045-pd05/rowdiff.py
$ .venv/Scripts/python.exe tmp/20260924-0045-pd05/manifest.py tmp/20260924-0045-pd05/lf-sha-end.json
$ git check-ignore -v data/literature_feed/feed.sqlite data/literature_feed/locks/feed_fetch.lock
```

---

## 八、遗留问题（交人工／主班）

1. 🔴 **§廿一／台账 #89 的归因论证要不要正式作废**：本单已证「sha 变更」不具证据力（§二.4）。**11:55 之前是谁/什么进程打开过库**仍未坐实。本单**未改判责任**，只登记论证无效。
2. **纪律档 §廿一 的两处待订正**（档在 cwd 之外，本单未碰）：① 还原配方应补「**回滚会断 8/8 算术链**」与「**`sqlite_sequence` 回退致 ID 复用串号**」两条代价（本档 §四 R1）；② 「探针按 `started_at` 取」应补明该列是 UTC 带 `Z` 文本。
3. **`raw/` 与 db 的一致性口径未定**：现态里 raw 与 db 一致；一旦按 R1 回滚即产生 345,459 B 孤儿（R6）。**要不要把 `raw/` 纳入三件套之外的「第四件」**，需人工定。
4. **回滚窗口是会自己关的**：下次 app 启动必追加 run 45，现态 sha 随即变化。若人工仍要走 R1，**需先约定「停 app」的执行窗口**。
5. s923-12 档 §五.3 的失效注只做了「现场锚点失效」的标注；该档其余结论（abandoned 算术、daemon 腰斩机制）**不受本次覆盖影响**，无需返工。
