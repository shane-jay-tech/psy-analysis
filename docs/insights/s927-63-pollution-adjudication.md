# s927-63 · 044 文献推送生产数据污染：四件现状复核 ＋ 两案裁决材料（2026-09-29，只读·零回滚）

> 班：`qoder-executor-20260929-0532-psy104` · 单：`s927-63` · cwd `D:\code\psy-analysis` · 现取时间 `2026-09-29T05:32:24+08:00`
> 🔴 **本班零回滚、零写生产**：`data/literature_feed/` 全 181 件收工＝开工 sha256 逐件相同（§六）。
> 上游：`zcode-bridge/done/s923-17.result.md` §遗留 1（污染自报）· `docs/insights/psy-litfeed-evidence-loss-rollback-20260924.md`（pd05 前案，本档只更新现值与判据，不重复其配方）· 待人工台账 `D:\code\docs\insights\drain-20260923-pending-human.md` #89（L38）／#164（L113）／#166（L115）／#179（L128）。
> **与卷宗前提的两处不符已按磁盘实况收窄**，见 §〇.5。

---

## 〇、结论先说（六条）

1. **四件现状：全部不等于污染时（09-23 11:55）的指纹 ⇒「已被后续写入覆盖」成立。** 但覆盖者**不是探针、不是后续实验，而是一次真 app 会话**：`locks/feed_fetch.lock` 第 2 行 `pid=135684 acquired_at=2026-09-23T04:15:30+00:00`（北京 12:15:30）＝`fetch_runs.run_id=44`，同窗 `raw/2026-09-23/` 落下 6 支期刊 jsonl 共 345,459 B（`hrm/jap/job/johp/jvb/personnel_psych`，12:15:42→12:16:18 逐源 7 秒节拍，与在册 `raw/2026-08-24` 的抓取节律同形）。台账 #166 已把这次写入独立归因到 `start-bg.bat` 真 app 会话。
2. **覆盖发生在 09-23 12:15–12:16，此后六天生产字节再未变过**：本班 db `6bf5776b0cd927c8`／wal `4f9f07db98c190b7` 与 pd05 档 §一（09-24 读）及台账 #179 主班独立复核**逐位相同**；全目录 **181 件 / 21,059,126 B** 三处读数互证一致。⇒ 「污染现场」在字节层早已被"现态"取代，现态即最后一次真抓取的产物。
3. 🆕 **本班新读数（在册未记的一项）：`feed.sqlite-shm` 在今天 03:12:33 被刷新过**（sha16 由 09-24 的 `07f52991` 变 `144cf1db`），**db＋wal 字节未动 ⇒ 无提交、`max(run_id)` 仍是 44**。时窗与兄弟班 `qoder-executor-20260929-0307-psy98` 跑 `s927-58`（feed 域定向 184 例，claim 03:11／done 03:15）吻合 ⇒ **候选归因：该班定向测试连到了活库**（未坐实，本班不判）。这恰是 pd05 档 §五 纪律句要防的动作：**「禁止对 `data/literature_feed/` 原地开连接」——原地连接即使不写，也会改掉 `-shm`**。
4. **逻辑层「覆盖」并未发生：污染产物至今仍在库里。** 本班在沙盒副本上 `mode=ro` 复算（无 `immutable`，守台账 #164 口径）：`fetch_runs=44 / articles=175 / sources=8 / llm_candidates=122`，且 **`run_id=43`（11:55 那次探针会话，`trigger='app_startup'`、`started_at='2026-09-23T03:55:07Z'`、`ended_at=NULL`、`status='running'`）就是当前库里唯一残留的污染行**，它挂 **0 篇 `articles`**。⇒ 本案真正的"污染存量"不是四枚文件的字节，而是**一条僵尸 `running` 行 ＋ 锁文件里那一条 `pid=130036` 记录**。
5. ⚠️ **与卷宗／横幅前提的两处不符（据磁盘收窄，不判 failed）**：
   - 横幅写「psy 的 `data/` 被 .gitignore 覆盖 ⇒ 写坏了没有任何 git 还原点」——**git 侧成立**（本班实测 `git check-ignore -v data/literature_feed` → `.gitignore:42:data/`，`git status --porcelain data/` 空），**但「无任何还原点」不成立**：写坏前的**完整三件快照在 `tmp/s923-13/`（db `c9e6a2080a89901e`／wal `5815d8c273e75a2d` 20,632 B／shm）与 `tmp/20260924-0045-pd05/{snap_copy,s13}/` 各存一份**，pd05 已验 `PRAGMA integrity_check=ok`。⇒ **本班仍不推荐回滚，但推荐必须建在"能回而不该回"上，不能建在"回不去"上**。
   - 卷宗问「是否已被后续正常写入覆盖」预设了"覆盖＝污染消失"。实况是**字节被覆盖、逻辑残留仍在**（§〇.4），且台账 #179 已判定：**db 文件 sha 变化在这套 WAL 布局下不能区分「checkpoint 折叠」与「真写入」** ⇒ 单靠 sha/mtime 三条**不足以**答"污染是否还在"，必须逐表逐行差分。本班据此把取证方式从"三条指纹"扩到"三条指纹 ＋ 副本行级复算"。
6. **推荐：案乙「维持并登记」**（与 pd05 档抬头的用户裁决"选案 B——不回滚"、台账 #166 的改判建议同向）。理由与代价见 §四、§五。

---

## 一、四件现状（本班 05:3x 现读，逐条可复算）

| 件 | 污染前（s923-17 记） | 污染后 11:55（s923-17 记） | **本班现读 sha16 / size / mtime** | 判定 |
|---|---|---|---|---|
| `feed.sqlite` | `c9e6a2080a89901e` 499,712 | `167f6a8123150a47` 499,712 | **`6bf5776b0cd927c8` / 499,712 / 2026-09-23 12:15:30.421** | 已被覆盖（≠两态） |
| `feed.sqlite-wal` | `5815d8c273e75a2d` 20,632 | `2d2e386b129f4aa0` 28,872 | **`4f9f07db98c190b7` / 741,632 / 2026-09-23 12:16:18.817** | 已被覆盖 |
| `feed.sqlite-shm` | `db7e00e87820c793` | `35d020ba5ff41a53` | **`144cf1dbf7bb0e7c` / 32,768 / 2026-09-29 03:12:33.220** | 已被覆盖**两次**（09-23 12:15 ＋ 本班开工当天 03:12） |
| `locks/feed_fetch.lock` | `4e0139f407c7b59e`（52 B，run 42 单条） | `010c4852e603e282` | **`d9c6c8783c8a8de1` / 104 / 2026-09-23 12:15:30.493** | 已被覆盖；内容见下 |

现锁文件逐字（`cat` 实测，104 B 两条）：

```
\r\npid=130036 acquired_at=2026-09-23T03:55:07+00:00\r\n\r\npid=135684 acquired_at=2026-09-23T04:15:30+00:00\r\n
```

⇒ 第 1 条＝污染会话（run 43，**探针残留仍在字节层**）；第 2 条＝真 app 会话（run 44）。原 run 42 那条 52 B 记录**字节层永久无副本**（pd05 §二.1 穷举全 `tmp/` 仅两枚 `.lock`，皆为覆盖后态；本班复核 `tmp/psy12-feed-sandbox/…/feed_fetch.lock` 与 `tmp/s923-19/litfeed_sandbox/…/feed_fetch.lock` sha16 **均＝`d9c6c8783c8a8de1`**，与现态同 ⇒ 前案穷举仍成立）。

**污染前快照在世（横幅前提的否证件）**——本班实测 `find tmp -name 'feed.sqlite*'` 全量枚举后的三组关键值：

| 快照 | db sha16 | wal sha16 / B | 意义 |
|---|---|---|---|
| `tmp/s923-13/` | `c9e6a2080a89901e` | `5815d8c273e75a2d` / 20,632 | **写坏前完整态**（copy2 保 mtime：db 08-24 12:42:25／wal 09-22 04:16:23） |
| `tmp/20260924-0045-pd05/snap_copy/`（＝`s13/`） | `c9e6a2080a89901e` | `5815d8c273e75a2d` / 20,632 | 同上的第二份独立副本 |
| `tmp/s923-10/feed.sqlite` | `167f6a8123150a47` | wal 0 B | **mtime 09-23 10:49:33＝早于污染 66 分钟** ⇒ 该 sha 是纯 checkpoint 折叠像，非写入证据（台账 #179） |

---

## 二、覆盖归因链（三源互证，本班现取）

1. **锁层**：`pid=135684 / acquired_at 04:15:30Z`（＝北京 12:15:30）。
2. **库层**：`fetch_runs.run_id=44 = ('app_startup','2026-09-23T04:15:30Z',NULL,'running')`（本班副本复算；run 44 亦 `status='running'`＝另一个僵尸，属 s923-12 同族问题）。
3. **文件层**：`raw/2026-09-23/` 6 支 jsonl 12:15:42→12:16:18，与 wal 末次 mtime 12:16:18.817 同秒收尾。

⇒ 四件的覆盖动作＝**同一次真 app 抓取会话**，不是探针复跑、不是本班。台账 #166 另记一条读数陷阱：`held_by_other` 告警的 pid 取锁文件**第一条** acquire，故既往"held by pid=130036"只能当**历史 acquire** 读，不代表当时持有者。

---

## 三、案甲：回滚到污染前（材料）

- **能不能回**：**能**。还原源齐（§一 末表，db＋wal＋shm 三件），pd05 §三.① 已验 `integrity_check=ok`；本班 `Get-Process python*,streamlit` 实测**当前无进程持库** ⇒ 窗口仍开着。
- **回什么**：db 退回 42 runs / 151 articles、wal 退回 20,632 B 态、锁退回"只含 run 42"（**但锁的 run-42 原件字节已灭，回出来的只能是"重写的一份"＝造证据，pd05 R5 已禁**）。
- **代价（台账 #179 已登记两条 ＋ 本班新增一条）**：
  1. 删 `run_id=44` ＋ 其 24 篇 `articles`（`fetch_run_id=44`）＋ `sources` 8 行 × 2 列水位退回 08-24 ⇒ **抹掉库里最后一次真 app 抓取**。本班补测：`articles` 中 `fetch_run_id=44` **恰 24 行、run 43 挂 0 行** ⇒ 回滚的净损失全落在真数据上，**换不回任何污染清除收益**（污染行 run 43 会被一起删，但它是 0 行数据的空壳）。
  2. run 42 由 `abandoned` 退回 `running`、`ended_at='2026-09-23T03:55:07Z'` 被清空 ⇒ **主动抹掉 s923-12 逐秒算术链的最新一环（42→43）**。本班在现态副本复算该锚仍在：`run 42 = (42,'app_startup','2026-09-21T20:16:23Z','2026-09-23T03:55:07Z','abandoned')`。
  3. `sqlite_sequence` 由 `44/175/122` 回退到 `42/151/122`（本班实测现态＝`fetch_runs 44 / articles 175 / llm_candidates 122`）⇒ **下次抓取复用 `run_id=43`、`article_id=152`，与已入库文档（pd05 档、台账 #89/#166、s923-17 result）引用的 43/44 撞号串案**。
  4. 🆕 **本班新增代价**：`raw/2026-09-23/` 345,459 B 不在三件套还原集内 ⇒ 回滚后"库无行、raw 有文件"成孤儿（pd05 R6 已列，本班现值复核 raw 仍在）；且**六天来 db/wal 字节未变＝回滚的"回退量"已完全等于真抓取数据量，没有任何中间态可保**。
- **不可回项**：锁文件 run-42 原件（R5）、09-23 10:49 那一刻的完整字节态（R7，其 `-wal/-shm` 已不在盘）。
- **执行风险**：`data/` 无 git 还原点（`git check-ignore` 实证）⇒ 回滚**失手即不可逆**；且 `articles.fetch_run_id` 有真外键，外科式删行会撞约束（pd05 §三.①）。

## 四、案乙：维持并登记（材料）

- **维持的是什么**：一条 0 数据的僵尸行 `run_id=43` ＋ 锁文件里一条 `pid=130036` 历史 acquire ＋ 已改判无效的"sha 变更"归因论据（#179）。
- **风险清单（如实登记）**：
  1. `run 43/44` 双双 `status='running'`＝僵尸，会持续触发 `stale_lock`／`held_by_other` 类告警，且 `abandon_stale_runs` 只在**下一次 run** 才扫（s923-12 在册结论）⇒ 不跑真 app 就永远挂着。
  2. 可复核性依赖**不受 git 管的 `tmp/` 副本**：`tmp/s923-13/` 一旦清理即彻底断源（本案唯一还原点＋唯一"污染前"证据同在一处，单点）。
  3. 🆕 `-shm` 会被任何原地连接改掉（本班 §〇.3 现证）⇒ "三件套指纹不变"这类自证有天然噪声，登记类结论应以 **db＋wal 两件**为准、shm 只作旁证。
- **正解方向（属写库，需人工授权，本班不执行）**：台账 #166 建议的"**接受现态 ＋ 只清僵尸行与锁**"；pd05 R3 进一步给出**非手写 SQL 的口径**——跑一次真 app 让它自己被 `abandon_stale_runs` 扫，从而保住 `ended_at` 算术链。
- **已裁决状态的对账缺口（要人工看一眼）**：pd05 档抬头写「用户裁决：呈报方选案 B——不回滚」，但台账 **#89 处置列仍是"待人工（涉数据回滚，主班未自主执行）"**，#166 又以"改判建议"形式并存。⇒ **分册状态不同步**，本班按"仍开放"出材料并推荐案乙，不代人工宣布结案。

---

## 五、推荐（一案）：案乙「维持并登记」

三条决定性理由，全部落在本班可复算的读数上：

1. **回滚换不到任何收益**：污染在字节层已被真 app 会话覆盖（§一／§二），逻辑层只剩 `run_id=43` 这个**挂 0 篇文章的空壳**；案甲删掉的却是 24 篇真文章＋8 源水位＋算术链一环。
2. **案甲会自造新的、更贵的证据损失**：撞号（R1 之 `sqlite_sequence`）＋ 断链（run 42）＋ 孤儿 raw，三项都是"回滚后无法用活库复原"的类型，性质上比本案要修的"锁文件 52 B"更重。
3. **案甲的失败模式不可逆**：`data/` 整层无 git（本班实证），唯一还原点在 `tmp/`；同一天（03:12）已出现"原地连接改 `-shm`"的现证 ⇒ 在这个目录上做覆盖式操作，容错为零。

配套三条（都不需回滚，都不属本班授权）：① 把 `tmp/s923-13/` 三件快照**登记为"本案唯一还原点"**并纳入清理白名单（人工定：是否受版外备份）；② 授权一次真 app 会话收僵尸行（#166 方向）；③ 把"涉文献推送域一律先 copy2 三件套到沙盒、禁原地开连接（含只读）"写进纪律档 §廿一／§五（pd05 已起草，本班 §〇.3 给出它仍在被违反的现证）。

---

## 六、零改动自证 ＋ 写类实验生效反证

```
$ PYTHONUTF8=1 .venv/Scripts/python.exe tmp/qoder-executor-20260929-0532-psy104/s927-63_probe.py   → PROBE_RC=0
开工基线 files=181 total_bytes=21059126   （与 pd05 §七、台账 #179 主班复核逐位相同）
收工基线 only-in-start=[] only-in-end=[] SHA-CHANGED=[] MTIME-CHANGED=[]  VERDICT: ZERO-DIFF ✅
```

- **写类实验的落点反证**（`LITERATURE_FEED_DATA_ROOT` 官方覆盖口，`src/literature_feed/paths.py:17`）：

```
$ LITERATURE_FEED_DATA_ROOT=<本沙盒>/writetest/literature_feed python -c "from src.literature_feed import paths; paths.ensure_dirs(); paths.FETCH_LOCK_FILE.write_text(...)"
  rc=0
  DATA_ROOT= D:\code\psy-analysis\tmp\qoder-executor-20260929-0532-psy104\writetest\literature_feed
  LOCK=    …\writetest\literature_feed\locks\feed_fetch.lock  exists=True (28 B)
  同一时刻生产目录 181 件 sha256/mtime 全等（ZERO-DIFF）
```

  ⇒ **生产模块在设了该环境变量后确实不碰生产目录**，后续任何涉库探针照此办理即安全。
- **本班对活库零开连接**：全部 sqlite 连接 URI 带 `mode=ro`、**不带 `immutable=1`**（守 #164），且只打在 `tmp/qoder-executor-20260929-0532-psy104/readcopy/` 的 copy2 副本上；复制后核对 WAL 字节数 **741,632 ≠ 0**（守 #164 拼错后缀那条坑）。
- 未执行：任何 `INSERT/UPDATE/DELETE/DROP/VACUUM`、任何 checkpoint、任何 `.bat`、任何抓取、任何删除、任何 `git add`/`commit`、任何还原。
- 红线：本档全部数值是**文件字节数／sha／行数／时间戳**，无一条统计或经济结论；未碰医疗／PII／鉴权／凭据；未挂白名单、未标 `NEEDS_MIGRATION`。

## 七、复算命令（主班可独立跑；⚠ 其局限一并写死）

```
$ git check-ignore -v data/literature_feed                                   → .gitignore:42:data/
$ stat -c '%y %s' data/literature_feed/feed.sqlite{,-wal,-shm} data/literature_feed/locks/feed_fetch.lock
$ sha256sum <上述四件> | cut -c1-16
$ cat data/literature_feed/locks/feed_fetch.lock
$ find tmp -type f \( -name 'feed.sqlite' -o -name 'feed.sqlite-wal' -o -name 'feed.sqlite-shm' \) -exec sha256sum {} \;
$ PYTHONUTF8=1 .venv/Scripts/python.exe tmp/qoder-executor-20260929-0532-psy104/s927-63_probe.py
```

⚠ **局限**：① 探针的"收工 ZERO-DIFF"只覆盖本班窗口（±数分钟），不是六天连续监控；② 行级复算打的是 05:3x 的 copy2 副本，若主班复跑时真 app 已启动过一次，`max(run_id)` 会变成 45——**那属于正常追加，不是本班读数错**；③ §〇.3 的 `-shm` 归因只是时窗吻合，**本班未坐实**，主班若要定责需自己取 `logs/sweep-*.log` 与 psy98 的 result 对时。

## 八、遗留（交人工／主班）

1. 台账 **#89 与 pd05 抬头的"已选案 B"状态不同步**（§四末）——要人工点头才闭合，本班不代宣。
2. `run_id=44`（真 app 会话）**同为 `status='running'` 僵尸**：清它属写库，需授权；且它比 run 43 更该清（它有 24 篇下游文章）。
3. 唯一还原点 `tmp/s923-13/` 无版本管、无第二份异地副本 ⇒ 是否入备份白名单交人工。
4. 纪律档 §廿一／§五 待补两条：「原地只读连接也会改 `-shm`」（本班现证）与「涉库单开工基线应以 db＋wal 两件为准」。
