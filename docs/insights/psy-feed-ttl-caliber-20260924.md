# psy feed 双 TTL 口径裁决档：3600 判活 vs 21600 判抢（s924-16 · 只读）

> **性质：只读普查 + 口径推演，不改任何生产码/数据。** 取证时刻 2026-09-25T04:0x，HEAD 见文末自证。
> 来账：`zcode-bridge/done/s923-12.result.md:56`「TTL(3600) 与锁 TTL(21600) 两套口径互不指认
> （一个判'死透'、一个判'可强抢'），且 3600 < 21600 意味着僵尸行会比墓碑锁更早被判活……
> 两者谁该更严没有文档。」
> 本班按纪律把两条链全部实测复核，**结论比来账更细：来账那句时间轴推演在两种故障形态下都不成立**（见 §3）。

## 1. 两条判定链的实况（含复跑命令）

**链 A · 僵尸行判定（判"死透"）** — `abandon_stale_runs`：

- 锚点：`src/literature_feed/storage/feed_store.py:321` `def abandon_stale_runs(self, *, ttl_seconds: int = 3600) -> int:`
  （⚠ 卷宗写 `feed_store.py:321`，磁盘实况在 **storage/ 子包**；行号零漂移，路径按实况修正）
- 行为：把 `fetch_runs` 中 `status='running'` 且 `started_at < now-3600s` 的行改标 `abandoned`。
- **触发点唯一**：`src/literature_feed/scheduler/daily_runner.py:285`（`_run_locked` 内，即**必须先抢到互斥锁才会执行**）。
- 时间格式同型（可比较性自证）：`started_at` 与 cutoff 都是秒精度 `...Z`（`feed_store.py:132-133`），字典序=时序。

**链 B · 锁强抢判定（判"可强抢"）** — `LockManager`：

- 锚点：`src/literature_feed/scheduler/lock_manager.py:54` `ttl_seconds: int = 21600,  # 6h`
- 判据：`is_stale()`（`lock_manager.py:128-155`）按**锁文件 mtime** 距今 `> ttl` 判陈旧；
  `_open_and_lock()`（`:170-196`）抢锁前先 `is_stale → break_stale`（`:157-164`，unlink 删文件）。
- 构造点无 TTL 覆盖：`daily_runner.py:182` 与 `feed_panel.py:632` 都用缺省 21600。

两处锚点的 rg 复跑命令（读数见 s924-16 result 证据节）：

```
$ cd /d/code/psy-analysis && rg -n "ttl_seconds: int = 21600" src/literature_feed/scheduler/lock_manager.py
$ cd /d/code/psy-analysis && rg -n "def abandon_stale_runs" src/literature_feed/storage/feed_store.py
```

**关键实测（本班新增，来账未验证的前提）**——Windows `msvcrt` 字节锁**跟随进程生命周期**：

- 持锁期间第二方 `LK_NBLCK` → `PermissionError`（互斥有效）；
- **owner 句柄关闭/进程退出 ⇒ 锁自动消失**，文件虽在、壳不挡人（实测可立即重取）；
- **owner 活着持锁时 `unlink` 失败**：`PermissionError winerror=32` ⇒ `break_stale()` 对"活着的悬挂进程"**永远删不动**，
  其后果是继续走 `_do_lock` 失败 → `LockBusyError`，所谓「>6h 强抢」在该形态下是**纸面语义**。
- 复跑命令（本班在 `tmp/` 隔离探针跑，不触真锁）：
  `$ .venv/Scripts/python.exe - <<'EOF'`（msvcrt 上锁→二取→unlink→释放重取四步探针，全文见 s924-16 result 证据节）

⇒ 修正 s923-12 的表述：**「僵尸行比墓碑锁更早被判活」只在 TTL 数值轴上成立，在真实时序上不成立**——
进程死亡时墓碑锁根本不会"被判活"（OS 锁随进程消失，任何时刻都能重新 acquire，与 21600 无关）；
进程悬挂时两条判定又都失效（abandon 进不了锁、break_stale 删不动文件）。**两条 TTL 不是"谁更严"的关系，
是一个管 DB 行账、一个管文件壳，唯一共同的执行载体都是"下一次 `run()`"。**

## 2. 时间轴推演（T0 崩溃/悬挂；行内读数 = 该刻两个判定的状态）

### 场景甲：owner 进程死亡（崩溃/断电）

| 时刻 | 僵尸行（链 A，3600） | 墓碑锁（链 B，21600） | 实际发生什么 |
|---|---|---|---|
| T+0min | `running`，age=0 → 不判 | mtime=acquire 时刻，age=0 → 非 stale | OS 锁已随进程释放，仅 DB 行挂着 |
| T+60min | age>3600 → **已满足判死条件** | 非 stale | 但**没有任何执行体**会去跑判定 |
| T+6h | 同上 | age>21600 → stale，break_stale **成功**（无活句柄）+ 一条 `[lock-alert] stale_lock` 告警 | 删除的只是文件壳；不删也不挡新 run |
| T+下一次 run()（daily/手动） | `_run_locked` 第一句 abandon → 行标 `abandoned` | 与 stale 与否无关，锁秒得 | **两条判定在这一刻同时兑现** |

### 场景乙：owner 进程活着但悬挂（网络卡死/死循环）

| 时刻 | 僵尸行 | 墓碑锁 | 实际发生什么 |
|---|---|---|---|
| T+0min ~ 6h+ | 不判（进不了锁） | <6h 非 stale | 第二方 `run()` → `skipped_locked`（`daily_runner.py:219-227`），abandon 永远轮不到 |
| T+6h 起 | 不判 | stale=True，但 **unlink 失败（winerror=32）→ break_stale 返回 False** | 依旧 `LockBusyError → skipped_locked`；UI 文案「下一次 acquire 会强抢」（`feed_panel.py:641-642`）**与实测不符** |

### 场景丙：正常长任务（LLM 抽取慢）

`_write_owner_info` 只在 acquire 时写一次（mtime 不续租），>6h 的正常运行同样落进场景乙的"stale 删不动"分支——
21600 注释「daily run + LLM 抽取最坏情况也用不到」是这条隐性假设的文档替身，**无代码强制**。
（真库副本实读：`fetch_runs` 现存两条 `running` 僵尸行 run 43/44，`app_startup` 触发、started 于 09-23，
说明判死链在本机已连续两天未获执行窗口——`bootstrap_check` 的后台 `run_daily` 同样被锁弹回时，abandon 不会跑。）

## 3. 三方案利弊（裁决交主班＋owner，本档不代拍板）

| 维度 | 方案一：abandon 对齐 21600 | 方案二：锁 TTL 对齐 3600 | 方案三：维持现状 + 启动告警 |
|---|---|---|---|
| 改动 | `feed_store.py:321` 缺省 3600→21600 | `lock_manager.py:54` 缺省 21600→3600 | 零数值改动，`run()` 入口把 stale/僵尸行数打日志或 UI 横幅 |
| 对场景甲 | 中性（判定都发生在下一次 run，60min→6h 的窗口差在本节奏下无感） | 中性（同左） | 中性，但**可见性立刻改善** |
| 对场景乙 | 无差别（两判都失效） | **恶化**：正常 >1h 的 run 的锁频繁进 stale 分支；Windows 删不动尚存一线，**POSIX 下 unlink 打开中的文件会成功**（推断，本机不可实测）→ 删走后第二 worker 锁新文件 = 双开抓取 | 无变化 |
| 对误判风险 | daily 节奏（≥24h）下等于放弃"1h 判死"的早发现 | 把"锁文件壳可清"与"进程该被抢"混为一谈，且引入 POSIX 双开窗口 | 零风险 |
| 触及"改计数口径"红线 | 判据变更会使既有 abandoned 计数分布漂移 ⇒ 按纪律需人工闸 | 同左 | 不触数值 |
| 结论建议 | ❌ 不建议单做 | ❌ 不建议（实测语义下它是**假保护**，还有 POSIX 反效果） | ✅ 建议主走此路，并附两条**只读**修正：① UI `feed_panel.py:641-642` 文案改为「stale 仅在 owner 进程已退出时可清壳；活锁悬挂删不动」；② 把「僵尸行存在且 age>3600」作为启动横幅数据源（`fetch_runs` 直读，无新计数口径） |

真正值得修的暴露面（超出本卷授权，全部只登记不动手）：
1. **僵尸行判死没有独立执行体**——abandon 寄生在 `_run_locked` 里，被锁弹回的 `run()` 不执行它；
   `skipped_locked` 分支（`daily_runner.py:226`）前调用一次 `abandon_stale_runs()` 即可闭环（改行为，需派单）。
2. **POSIX 双开窗口**：`break_stale` 在类 Unix 上删得掉活句柄的文件（推断），若部署到 Linux 需在
   删除前校验 owner pid 存活（锁文件已存 pid：`_write_owner_info :236-248`，`_read_owner_pid :68-82` 现成可用）。
3. 两条 TTL 与「谁该更严」的口径说明**至今无文档**——本档即补这块，建议 owner 拍板后把结论回写进
   `lock_manager.py:47` docstring（当前那句"超了视为 stale 强抢"需按 §1 实测语义收窄）。

## 4. 自证（只读门）

- 未跑文献库/feed 写路径以外的任何面；复跑的定向族（带沙盒）：
  `$ LITERATURE_FEED_DATA_ROOT="D:/code/psy-analysis/tmp/qoder-executor-20260925-0340-psy37/feed-data" .venv/Scripts/python.exe -m pytest tests/test_literature_feed_lock.py tests/test_literature_feed_storage.py tests/test_literature_feed_scheduler.py tests/test_lock_manager.py tests/test_lock_stale_boundary.py tests/test_instance_lock.py tests/test_instance_lock_alert_gap_pin.py tests/test_instance_lock_oserror_branch.py tests/test_lock_alert_log.py -q`
  → **107 passed**（全部通过，零红 ⇒ 无在册红被本单惊动）
- 真库三项逐位不变（跑测试前后各取一次）：
  files=181 / bytes=21059126 / agg(sha256 of sorted path|len|sha12 lines)=`46b7204bd8d96416f7ed9ea333374136b49cf8f5110159187177082a9f0eabf0` ×2 ⇒ **UNCHANGED-OK**
- `$ git log -1 --format='%h %s'` → `9d7df82 docs(psy): s924-11 方法 id 文案表重复面盘点（实况是 10 张表＋2 处硬编码，不是"两表"）`
- 本档是 cwd 内唯一新增件；`git status --porcelain` 除本档（与 s924-04 的 4 件、以及**非本班的 CFA 三件在途改动**）外零改动。
