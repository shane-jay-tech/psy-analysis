# literature_feed 数据面停摆下钻：调度器从未触发（A3 探针结论，2026-09-22）

> 来源：`docs/insights/psy-data-dirs-20260919.md` A3 留的口子——「到底是调度器从未被触发、还是触发了但拉取全失败，
> 要跑一次只读探针才知道；不在本单范围」。本档就是那次下钻的结果。
> 执行：`qoder-executor-20260922-0000-psy2b`（信箱单 `s922-17-psy-litfeed-probe`），2026-09-22 02:4x 本机实跑。
> **全程只读**：`data/literature_feed` 173 个在册文件跑前跑后 sha256 全等，零写入、零删除。

## 一、结论（一句话）

**「代码在动、数据不动」的成因是调度侧停摆，不是拉取失败。**
`PsyLiteratureFeed` 这个每日 09:00 的计划任务在本机**根本不存在**，`fetch_runs` 里 `trigger='scheduler'` 的行
自 **2026-06-27T01:00:02Z** 之后再没出现过；而只读探针 8 源全通、**7 源在 60 天窗口里抓到 73 篇增量**（rc=0），
所以 Crossref 链路、ISSN、免 key 通道都是好的。数据面最后一点动静（08-24）来自 `trigger='app_startup'` 的兜底路径。

停摆因此分两层，别混着说：

| 层 | 停摆时刻 | 判据 |
|---|---|---|
| 调度层（scheduler） | **2026-06-27 01:00Z** 之后归零 | `fetch_runs` group by trigger：scheduler 28 次全 completed，`max(started_at)=2026-06-27T01:00:02Z`；`schtasks /Query /TN "PsyLiteratureFeed"` rc=1「系统找不到指定的文件」 |
| 数据层（最后一次真跑） | **2026-08-24 04:34Z**（本地 12:34/12:42） | 最后一次 `app_startup` completed = run_id 41；`raw/` 末个日目录 `2026-08-24`；`feed.sqlite` mtime 08-24 12:42 |

## 二、探针读数（完成标准要求的「退出码＋逐源结果表」）

命令（`list` 子命令跳过 `seed()`，所以不 upsert；`--probe` 只 fetch 不抽取、不入库）：

```
./.venv/Scripts/python.exe scripts/seed_literature_sources.py list --probe
PROBE_RC=0
```

| source_id | ISSN | enabled | 探针实测（60 天窗口，每源上限 10） | sources 表在册 last_success_at |
|---|---|---|---|---|
| acta_psych_sinica | 0439-755X | 1 | **抓到 0 篇**（无样例） | 2026-08-24T04:33:59Z |
| adv_psych_science | 1671-3710 | 1 | 抓到 10 篇 | 2026-08-24T04:34:00Z |
| hrm | 0090-4848 | 1 | 抓到 9 篇 | 2026-08-24T04:34:06Z |
| jap | 0021-9010 | 1 | 抓到 10 篇 | 2026-08-24T04:34:12Z |
| job | 0894-3796 | 1 | 抓到 9 篇 | 2026-08-24T04:34:19Z |
| johp | 1076-8998 | 1 | 抓到 10 篇 | 2026-08-24T04:34:24Z |
| jvb | 0001-8791 | 1 | 抓到 10 篇 | 2026-08-24T04:34:31Z |
| personnel_psych | 0031-5826 | 1 | 抓到 5 篇 | 2026-08-24T04:34:39Z |

- **8/8 源查询成功，0 源抛错**（探针的 `[失败]` 分支一次都没走）⇒「拉取全失败」直接否证。
- 合计 73 篇可抓增量。若今晚真有一次触发，`raw/` 就会长出新日目录。
- 唯一零产出的是 `acta_psych_sinica`（心理学报，DOI 前缀 10.3724）——**它 60 天内一篇都没返回**，
  而另两本中文旗舰 `adv_psych_science` 拿满 10 篇。属源侧注册面问题，不是代码问题；**本档不改 ISSNs、不改源表**（红线：研究与统计结论面）。
- 八源的 `status` 全为 `ok`、`enabled` 全为 1 ⇒ 停摆与源健康度无关。

## 三、为什么 08-24 那次「触发成功」却没让数据动（A3 的第二半）

最后一次 completed 的 run 41 的 `summary_json`（现场读，未改）：

```
fetched 合计 29 | new_articles 全 0 | duplicates 全命中 29 | failed 0 | budget_exceeded false
extracted_articles 0 | extracted_constructs 0 | error null | status completed
```

⇒ 那几次**真的跑完了**，只是抓取游标（各源 `last_success_at`）之后 60 天窗口里的文章**全部已在库**
（`articles` 共 151 行），所以既不长 `raw/` 也不长库。这与「探针今天能抓到 73 篇」并不矛盾：
08-24 之后又过了 4 周，Crossref 侧确实攒出了新内容，只是**再没有人去触发**。

## 四、顺带证实/修正 A2、A4 的两处

1. **A2（锁墓碑）判据加强**：`locks/feed_fetch.lock` 里只有 08-24 的两条 acquire 记录
   （`pid=65436 acquired_at=2026-08-24T03:51:57+00:00`、`pid=72588 …T04:31:58+00:00`），
   4 周无任何新增 ⇒ 与 A3 同因（没进程走到抢锁那步）。**但同一次运行留下了两条僵尸行**：
   `run_id 39 / 40` 的 `status` 至今仍是 `'running'`、`ended_at` 为 NULL，而 run 41 已 completed。
   ⇒ 启动侧的 abandoned 对账（08-14 那 5 条被标 `abandoned` 就是它干的）在 08-24 这一批上没生效，
   原因未坐实（进程被强杀？对账只在别处跑？）。**登记，不顺手改。**
2. **A4（logs/ 死目录）要补一句**：`data/literature_feed/logs/` 实测仍为空，但**并非「无任何代码引用」**——
   `scripts/run_daily_feed.bat` 明确 `mkdir` 该目录并把 `daily_runner.log` 追加进去（.bat 第 8 行注释、:23 mkdir、:25-27 写日志头、:37 才调 python）。
   ⇒ 目录为空这件事本身就是**「.bat 从未成功跑过」**的证据（它会先写日志头再执行 python），
   与 `schtasks` 查无此任务互相印证。这也解释了为什么 28 次 `trigger='scheduler'` 却没有 .bat 日志——
   **那 28 次不是走 .bat 来的**（人或脚本直接 `python -m src.literature_feed.scheduler`，或一个已被删掉的任务）。
   这条归因尚未坐实，留给拍板的人。
> 勘误（2026-09-24）：本段判据已被 s923-10（zcode-bridge/done/s923-10.result.md）部分否证，成因以该 result 结论为准
> 现状（2026-09-25 复核 · qoder-executor-20260925-0630-psy49）：本段的**观测**仍在——`logs/` 现 0 条目、mtime 2026-09-14 08:00:47、目录 ctime 2026-05-30 09:00:00（复算 `stat data/literature_feed/logs`）；被否证的是「目录为空 ⇒ .bat 从未跑过」这一步**推论**（s923-10 归因到一个现已消失的计划任务）。另：本段所引 .bat 行号已随 `1657af8` 漂为 :45 mkdir / :47 LOG（§五 出口 1 的「先解决全局 python」前置也已由 :32/:38 的 `VENV_PY` 做掉）⇒ 复算一律 `rg -n "mkdir|LOG=|VENV_PY" scripts/run_daily_feed.bat` 现取。第三处同错判据在 `zcode-bridge/done/s922-17-psy-litfeed-probe.result.md`（该 result 只有五节、**无 §七**：派单沿用的"s922-17 result §七.1"是 s923-10 遗留 3 里的假锚点，实指其「证据」节 `:43` 那行「`ls data/literature_feed/logs/` → 空目录（.bat 一旦跑过必先写 daily_runner.log 头）」，复算 `rg -n "daily_runner.log 头" zcode-bridge/done/s922-17-psy-litfeed-probe.result.md`），属历史件不回改；本段原文零删改。

## 五、给 A3 拍板的可执行出口（本档一律未执行）

| # | 出口 | 代价/前置 | 谁该动 |
|---|---|---|---|
| 1 | 注册计划任务：`schtasks /Create /SC DAILY /TN "PsyLiteratureFeed" /TR "D:\code\psy-analysis\scripts\run_daily_feed.bat" /ST 09:00` | **先解决 .bat 里 `set "PY=python"` 用全局 python 的问题**：本仓依赖装在 `.venv`（semopy 2.3.11 在 `.venv/Scripts`），全局 python 未必有 ⇒ 不先确认就会从「不触发」变成「天天触发但全失败」，比现在更误导人 | 人工（改 .bat 属生产码） |
| 2 | 或放弃 .bat，接受 `bootstrap_check` 的 24h 阈值 + `trigger='app_startup'` 兜底 | 语义要写清：数据新鲜度 SLA 变成「你上次开 app 的时间」，不是每日 09:00 | 人工口径决定 |
| 3 | 清理 `fetch_runs` 里 run 39/40 的 `'running'` 僵尸态、补 `.bat` 日志接线（A4） | 属写库动作 + 生产码改动，本单只读不做 | 日间另派 |
| 4 | 核 `acta_psych_sinica` 的 ISSN/DOI 前缀注册面（60 天 0 篇） | 若确认该刊不进 Crossref，需人工决定是否从源表摘掉（改源＝改研究面簿） | 人工 |
| 5 | 若要把 `data/` 面簿做成可回归的机检 | `data/` 被 `.gitignore` 覆盖 ⇒ 探针与门禁对它是**失明**的（`git status --porcelain` 恒空），只能靠自算 sha256 清单，本档附的 before/after 法可复用 | 日间另派 |

## 六、本档的取证边界（照实说）

- 探针**确实发生了一次到 Crossref 的外呼**（8 源 × ≤10 篇，免 API key 的 polite 通道）。这是任务书点名的动作，
  不属「下载依赖」；但它是本仓本次收班唯一的出网动作，登记在此。
- `FeedStore()` 以 `ensure=True` 打开，会跑 `ensure_dirs()` + `_apply_schema()`；实测对 `data/` **零内容改动**
  （3 条 migration 全已 applied，schema 无变更），但**任何一次 sqlite 打开（含我用 `mode=ro` 的只读查询）都会临时生成
  `feed.sqlite-shm` / `feed.sqlite-wal` 两个 WAL 边车文件**，连接干净关闭后自动消失。跑前快照里它们存在（我先做的只读查询留下的），
  跑后消失——这是唯一被观察到的文件系统抖动，`feed.sqlite` 本体 sha256 前后同为 `c9e6a2080a89901e6c390870b2fa69fd…`（499 712 B，未变）。
- 结论只覆盖到「本机、本 `data/` 副本、09-22 02:4x 的读数」。06-27 那次 scheduler 断点的**触发方式变更原因**没有坐实
  （要翻 5-6 月的 shell 历史或任务计划改配记录），不属探针能力面。
