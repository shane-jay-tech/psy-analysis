# psy 根 `logs/` 现值画像 ＋ `junit_v59.xml` 陈旧产物处置建议（s923-53，只读）

- 任务：`zcode-bridge/inbox/s923-53.task.md`（cwd `D:\code\psy-analysis`）
- 执行班：`qoder-executor-20260924-0955-psy29`（psy **只读位**）
- 生成时间：2026-09-24T18:24+08:00
- 只读声明：本单**未删、未移、未改 `logs/` 下任何文件**，`data/` 与 `~/.psy_analysis` 一个字节未写；
  取证全程用 `os.path.getsize` / `glob` / `xml.etree` 只读解析，未打开任何写句柄。
- ⚠ 处置建议只是**建议**：`logs/` 被 `.gitignore:16` 忽略 ⇒ **git 没有还原点**，删错不可回滚，
  因此本单按纪律「只登记不删除」执行。

---

## 一、`ls -la logs/` 全清单贴档（判据点名）

```
$ cd D:\code\psy-analysis && ls -la logs/
total 458
drwxr-xr-x 1 31563 197609      0 Sep 23 12:15 .
drwxr-xr-x 1 31563 197609      0 Sep 24 18:15 ..
-rw-r--r-- 1 31563 197609    145 Sep 20 02:45 error_events_20260920.jsonl
-rw-r--r-- 1 31563 197609 326643 Aug 15 01:04 junit_v59.xml
-rw-r--r-- 1 31563 197609    706 Jul  5 16:08 startup_diagnosis.txt
-rw-r--r-- 1 31563 197609   2969 Sep 23 12:16 streamlit_run.log
-rw-r--r-- 1 31563 197609  46882 Jul  5 16:11 usage_events_20260705.jsonl
-rw-r--r-- 1 31563 197609    378 Jul 10 23:55 usage_events_20260710.jsonl
-rw-r--r-- 1 31563 197609     96 Jul 11 00:12 usage_events_20260711.jsonl
-rw-r--r-- 1 31563 197609   5691 Jul 14 12:59 usage_events_20260714.jsonl
-rw-r--r-- 1 31563 197609   1041 Jul 15 11:33 usage_events_20260715.jsonl
-rw-r--r-- 1 31563 197609    951 Aug 14 21:07 usage_events_20260814.jsonl
-rw-r--r-- 1 31563 197609  15186 Aug 15 01:02 usage_events_20260815.jsonl
-rw-r--r-- 1 31563 197609  13755 Aug 24 12:42 usage_events_20260824.jsonl
-rw-r--r-- 1 31563 197609    192 Sep 13 00:53 usage_events_20260913.jsonl
-rw-r--r-- 1 31563 197609    305 Sep 20 02:45 usage_events_20260920.jsonl
-rw-r--r-- 1 31563 197609     96 Sep 22 05:56 usage_events_20260922.jsonl
-rw-r--r-- 1 31563 197609    753 Sep 23 12:16 usage_events_20260923.jsonl
```

**16 个文件 / 415,789 字节**（`total 458` 是 512B 块口径，不是字节数）。git 侧：
`git ls-files logs` → **0 条**；`git check-ignore -v logs/junit_v59.xml` → `.gitignore:16:logs/`。

## 二、体积与时间线画像

| 类别 | 件数 | 字节 | 占比 | mtime 跨度 | 写方 |
|---|---|---|---|---|---|
| `junit_v59.xml` | 1 | **326,643** | **78.6%** | 2026-08-15 01:04 | pytest `--junitxml`（一次性手工产物） |
| `usage_events_*.jsonl` | 12 | 85,326 | 20.5% | 2026-07-05 → 09-23（**81 天**） | `src/utils/usage_logger.py:90` |
| `streamlit_run.log` | 1 | 2,969 | 0.7% | 2026-09-23 12:16（**目录里最新**） | `run.bat:38` / `start-bg.bat:4` 的 stdout 重定向 |
| `startup_diagnosis.txt` | 1 | 706 | 0.2% | 2026-07-05 16:08 | `run.bat:104`（仅启动失败分支） |
| `error_events_*.jsonl` | 1 | 145 | 0.0% | 2026-09-20 02:45 | `src/utils/usage_logger.py:114` |

三点画像结论：

1. **一个文件吃掉 78.6% 体积**，且它与其余全部文件的写入模型不同（一次性快照 vs 追加流）；
   清掉它目录立刻瘦 4/5，但它**不是运行时依赖**（第五节归因）。
2. **usage 事件高度集中在两天**：`20260705`(470 行) ＋ `20260815`(147 行) 占 856 行 usage 事件里的 617 行 ≈ **72%**，
   其余 10 个文件合计仅 239 行；单个事件名分布只取字段名未取字段值（隐私）：
   主要为 `page_visit`、`data_upload`、`analysis_execute`、`export`，
   另有 `error_events` 的 `export_failed` / `failure`。
   ⚠ `usage_hooks.py:64` 写的是 `export`、`tests` 侧写 `visit`/`failure` ⇒ 事件名词表**不统一**（第七节 E6）。
3. **卷宗清单漏了一个当下最活跃的文件**：`streamlit_run.log`（9/23 12:16，是目录里 mtime 最新的件）。
   卷宗写「混放 junit / startup_diagnosis / 按日 jsonl」——按磁盘实况补正为**四类**，其中 `streamlit_run.log`
   每次 `run.bat`/`start-bg.bat` 都会被 `>` **整体截断重写**（非追加），所以它天然自带「只留最后一次」的轮转。

## 三、锚点复核（卷宗两条，0 漂移）

| 锚点 | 原文 | 结论 |
|---|---|---|
| `README.md:55` | `PSY_ANALYSIS_LOG_DIR=logs                  # 运行日志目录；默认是「相对当前工作目录」的 logs/，换 cwd 就会换位置` | **逐字成立** |
| `src/utils/app_paths.py:27` | `LOG_DIR = _configured_path("PSY_ANALYSIS_LOG_DIR", Path("logs"))` | **逐字成立** |

## 四、逐类写方归因（`rg` 命中行号，判据点名）

```
$ rg -n 'usage_events|error_events' src -g '*.py'
src\utils\usage_logger.py:90    log_file = _log_dir() / f"usage_events_{date.today().strftime('%Y%m%d')}.jsonl"
src\utils\usage_logger.py:114   log_file = _log_dir() / f"error_events_{date.today().strftime('%Y%m%d')}.jsonl"
src\utils\usage_logger.py:130   files = sorted(_log_dir().glob("usage_events_*.jsonl"))[-days:]     # 读侧
src\utils\usage_logger.py:159   files = sorted(_log_dir().glob("error_events_*.jsonl"))[-days:]    # 读侧

$ rg -n "startup_diagnosis" -g '*.py' -g '*.bat' -g '*.ps1' .
run.bat:79    echo Writing diagnostic info to logs\startup_diagnosis.txt ...
run.bat:104   ) > logs\startup_diagnosis.txt 2>&1
docs\SYSTEM_REPORT.md:289  启动失败时自动写 logs/startup_diagnosis.txt（含 Python 版本、端口状态、错误日志）
```

| 文件类 | 写方（唯一定位） | 读方 | 判定 |
|---|---|---|---|
| `usage_events_*.jsonl` | `usage_logger.py:90`（`log_event`，`OSError` 静默吞） | `usage_logger.py:130 get_usage_summary`／`:196`（反馈包导出）／`scripts/analyze_usage_logs.py:25` | 活读写链路 |
| `error_events_*.jsonl` | `usage_logger.py:114`（`log_error`） | `usage_logger.py:159 get_error_summary` | 活读写链路 |
| `streamlit_run.log` | `run.bat:38`、`start-bg.bat:4`（`> ... 2>&1`，**截断式**） | 无代码读取（`run.bat:99-100` 只在失败时 `Get-Content -Tail 20`） | 人工排障件 |
| `startup_diagnosis.txt` | `run.bat:79-104`（失败分支） | 无 | 一次性，7/5 后再未更新 |
| `junit_v59.xml` | **pytest junitxml 插件**，由人手工带 `--junitxml=logs/junit_v59.xml` 跑全量时产出 | **0 个读取点**（`rg "junit_v59|logs/.*\.xml"` 在 `src`/`scripts`/`tests`/`app.py` 无命中） | 见第五节 |
| `install.log` / `verify.log` / `install_diagnosis.txt` | `install.bat:52 / :63 / :25` | 无 | **登记：logs/ 里今天这三个都不存在** ⇒ 7/5 后未跑过 `install.bat`，或跑成功未触发失败分支 |

## 五、`junit_v59.xml` 归因结论（生成方与命令推断，判据点名）

三方独立对账全部吻合：

| 凭据 | 读数 |
|---|---|
| XML 头 | `<testsuites name="pytest tests"><testsuite errors="0" failures="0" skipped="59" tests="2507" time="208.391" timestamp="2026-08-15T01:01:02.882793+08:00" hostname="本机中文计算机名（不外抄）"` |
| XML 体（`xml.etree` 解析） | `<testcase>` 元素 **2507 个**、`failure`/`error` 子节点 **0 个**、末条用例 `tests.test_yaml_config.TestLLMProviders::test_all_providers_have_name` |
| 文档旁证 | `docs/history/UPGRADE_REPORT_V5.9.md:107`「全量回归 **2507 passed, 59 skipped, 0 失败**（208.4s），`logs/junit_v59.xml` 可查」 |

⇒ **归因结论**：它是 **2026-08-15 01:01 那次 v5.9 发版全量回归**的 pytest junit-xml 报告，
推断命令为 `.venv\Scripts\python.exe -m pytest … --junitxml=logs/junit_v59.xml`
（`testsuites name="pytest tests"` ＋ `hostname` 为 pytest junitxml 固定形状；文件名 `v59` = 版本 5.9 标记，非 pytest 自动生成名）。
**不是任何脚本/CI/测试套件的产物**——全仓无 `--junitxml` 的自动化写点（只有 `docs/insights/*` 里各班手工配方，
且它们把 junit 写到 `tmp/`，如 `psy-e2e-skip-inventory-20260914.md:3` 的 `tmp/junit-skip.xml`）。
**陈旧度**：距今 **40 天**，且其 2507 例 / 208.4s 基线已被后续读数彻底取代
（对比 `docs/insights/psy-app-split-2-20260913.md:20` 的 2663 例 / 631s、纪律档 §七 的 4633 例 / 399s 口径）——
即：**同一名额上已有三份互不相同的全量读数并存，`junit_v59.xml` 是最旧的那一份**。

## 六、`LOG_DIR` 随 cwd 漂移的实测后果

```
$ cd D:\code && D:/code/psy-analysis/.venv/Scripts/python.exe -c "from src.utils.app_paths import LOG_DIR; ..."
LOG_DIR = 'logs'   绝对化后 = D:\code\logs
$ cd D:\code && ls -d logs
ls: cannot access 'logs': No such file or directory
```

⇒ 默认值是**相对路径 `logs`**，一旦被以 `D:\code` 为 cwd 的方式启动（例如有人从工作区根跑 `python -m streamlit`、
或计划任务的「起始于」填错），首个埋点事件就会经 `usage_logger._ensure_log_dir()`（`:48-58`，
`target.mkdir(parents=True, exist_ok=True)`）**在工作区根凭空建一个 `D:\code\logs\`** 并把事件写进去——
仓内 `logs/` 从此不再收全，且根仓 `D:\code` 的 porcelain 会多出一个未跟踪目录。
今天的 16 个文件全在仓内 `logs/` ⇒ **本机当前会话的 cwd 是仓根**（`start-bg.bat` 里有 `cd /d` 兜住，
旁证见 `docs/insights/psy-userhome-write-attribution-20260923.md:76`）。

另外发现**日志根不止一个**（画像补正）：
`scripts/run_daily_feed.bat:37-39` 把文献雷达的日志写 `data/literature_feed/logs/daily_runner.log`
（第三个 sink，**当前该目录为空**）；`.gitignore:16` 只忽略了根 `logs/`。

## 七、读侧口径缺陷（只登记，不改）

`usage_logger.py:130`／`:159` 用 `sorted(glob)[-days:]` 取的是**最近 N 个文件**，不是最近 N 天；
文件间有空洞时窗口会拉长，而返回体里的 `"period_days": days`（`:146`）仍写声明值。实测：

```
$ .venv\Scripts\python.exe -c "files=sorted(Path('logs').glob('usage_events_*.jsonl')); ..."
usage 文件总数 = 12
days=7 : 实取 7 个文件 = 20260814..20260923，跨 39 天，返回体 period_days 仍写 7
days=30: 实取 12 个文件 = 20260705..20260923，跨 78+ 天，返回体 period_days 仍写 30
days=7 口径下聚合事件条数 = 313
```

⇒ `get_usage_summary(days=30)` 被 `export_feedback_package`（`:196`）用于**打包外发**，
按现值它实际会带出约 81 天的事件而非 30 天。这条属**隐私导出面**（红线域），本单**只出只读报告、不动数值**。

## 八、清理与固定 `LOG_DIR` 的建议稿

### A 档 · 可直接做（0 运行时依赖、0 在册红；仍需用户点头，因 `logs/` 无 git 还原点）

| # | 动作 | 依据 | 影响面 |
|---|---|---|---|
| A1 | 把 `junit_v59.xml` **移出 `logs/` 归档**（如 `docs/history/artifacts/junit_v59.xml`，或 `tmp/` 下保命名），**不删** | 第五节：0 读取点；唯一引用是 `UPGRADE_REPORT_V5.9.md:107` 的「可查」 | 该文档需同步把「可查」改指向新路径，否则留悬空指针 |
| A2 | 在 `README.md` 的环境变量段（`:55` 附近）**加一行事实说明**：`logs/` 无轮转、`streamlit_run.log` 每次启动被截断、`junit_*.xml` 属手工产物 | 第二、四节实测 | 纯文档 |
| A3 | 给 `logs/` 定一条**明确边界**：只允许 `usage_events_*`／`error_events_*`／`streamlit_run.log`／`startup_diagnosis.txt` 四类命名，其余（含任意 `*.xml`）不进仓根 | 第四节表 | 纯约定 |
| A4 | 若要清体积：A1 一步即从 415,789B 降到 89,146B（−78.6%），**其余 15 个文件加起来不到 junit 的 1/4**，收益不值得引入删除逻辑 | 第二节表 | 纯测算 |

> ⚠ A1 的执行**不能**用 `scripts/backup_user_data.py`（该脚本 `:42 prune()` 会**裁剪别人的旧备份**，
> 纪律档 §五.5 明令执行班禁跑仓内 backup 脚本），也不能用 `scripts/prune_archive.py`（只管 `archive/` 与 `raw/`）。

### B 档 · 需用户拍板（本单不动）

| # | 议题 | 为什么不能直接做 |
|---|---|---|
| B1 | **给 `LOG_DIR` 换默认根**：从相对 `Path("logs")` 改为绝对（`REPOSITORY_ROOT/"logs"` 或 `APP_HOME/"logs"`） | `app_paths.py:26` 注释自陈「默认值不可改变；仅允许显式重定向」，且 `README.md:55` 已把「随 cwd 漂移」写成**公开契约**；改默认＝改契约，会连带影响便携部署与在册测试（`tests/test_usage_hooks.py:164`、`test_privacy_archive_usage.py:212-227` 均按可重定向口径钉桩）。**建议方向**：不改默认，改为启动时告警（`env_check.py` 侧提示「cwd 不在仓根」）。 |
| B2 | **是否给 `logs/` 装轮转/retention**（对齐 `prune_archive.py` 的 dry-run 默认风格） | 需要用户定窗口（留多少天）；且第七节读侧口径不修，加轮转反而会让 `[-days:]` 窗口更失真。 |
| B3 | `get_usage_summary` 的「最近 N 文件 → 最近 N 天」修法（`:130/:159`） | 属**统计口径变更**且下游是隐私导出包 ⇒ 红线域，只登记（第七节实测）。 |
| B4 | 事件名词表统一（`page_visit` vs `visit`、`export` vs `export_failed`） | 会让 `analyze_usage_logs.py` 与历史 jsonl 的分布对比断裂（在册 81 天数据不可重算）。 |
| B5 | 补装 `.env.example`/文档里 `PSY_ANALYSIS_LOG_DIR` 的**推荐绝对值**示例 | 与 B1 绑定裁决。 |

## 九、仓库零文件改动自证

```
$ git status --porcelain      # 18:05 接班
 M app.py
 M pytest.ini
 M requirements-lock.txt
?? node_modules/

$ git status --porcelain      # 18:25 收班（并发兄弟班期间变了）
 M KNOWN_ISSUES.md
 M app.py
 M pytest.ini
 M requirements-lock.txt
?? docs/insights/psy-logs-dir-portrait-20260923.md
?? docs/insights/psy-quick-models-retired-drift-20260923.md
?? node_modules/
?? tests/test_assumption_route_count_pin.py
```

⚠ **收班读数与接班不同，但差额里没有一项出自本单的写动作**：
`M KNOWN_ISSUES.md` 与 `?? tests/test_assumption_route_count_pin.py` 是并发班（`psy30` 的 s923-55 等）在途件，
本班全程未打开任何写句柄碰它们；`?? docs/insights/psy-quick-models-retired-drift-20260923.md` 是本班 s923-52 的产出。
本单（s923-53）唯一新增文件＝**本文自身**。
`M app.py`/`M pytest.ini`/`M requirements-lock.txt` 三项纪律档 §七/§九 点名的他班在途件，**只读过、未写**。


## 十、复算配方（命令原文）

```
cd D:\code\psy-analysis
ls -la logs/                                   # 第一节清单
git ls-files logs                              # → 0 条
git check-ignore -v logs/junit_v59.xml         # → .gitignore:16:logs/
rg -n 'usage_events|error_events' src -g '*.py'
rg -n "startup_diagnosis" -g '*.py' -g '*.bat' -g '*.ps1' .
rg -n 'streamlit_run' -g '*.bat' .
rg -n "junit" -g '*.md' docs/history docs/insights
.venv\Scripts\python.exe -c "import xml.etree.ElementTree as ET,os; ..."   # 第五节三方对账
.venv\Scripts\python.exe -c "... getsize/glob ..."                        # 第二、七节画像
cd D:\code && .venv\Scripts\python.exe -c "from src.utils.app_paths import LOG_DIR; ..."   # 第六节
ls -d data/literature_feed/logs                # 第三 sink（当前空）
```

## 十一、遗留问题

1. `junit_v59.xml` 的处置（A1）与 `UPGRADE_REPORT_V5.9.md:107`「可查」指针的连带改写，需用户点头后才能做——**本单未删未移**。
2. 第七节的「最近 N 文件」读侧口径 ＋ 反馈包实际外发 81 天事件：隐私导出面，**未量化到条目级**（只给了行数/天数），
   要精确到「外发集会带哪些字段」需另开只读单。
3. 事件名词表分叉（`visit`/`page_visit`、`export`/`export_failed`）来源未逐条追到 emit 点，只定位到 `usage_hooks.py:64` 一例。
4. `install.bat` 的 `install.log`/`verify.log`/`install_diagnosis.txt` 三件在 `logs/` 全部缺席：
   无法区分「从未跑过」与「跑成功且不写成功日志」（`install.bat:52/:63` 只把 **stderr** 重定向，成功时也只会留下空文件）——需一次实测才能定论，本单不跑安装脚本。
5. ~~`.gitignore:16` 是否覆盖 `data/literature_feed/logs/`~~ → **本单已闭合**：
   `git check-ignore -v data/literature_feed/logs/daily_runner.log` → `.gitignore:42:data/`（**靠 `data/` 整条被忽略，不是 `logs/` 那条**）。
   顺带：`.gitignore` 另有 `*.log`（`:17` 区段），⇒ 第六节的 cwd 漂移若真在 `D:\code` 建出 `logs\`，
   根仓也**不会**把它报成未跟踪脏项（`usage_events_*.jsonl` 不匹配 `*.log`，会以 `?? logs/` 出现一次后被人当噪音）。
   遗留收窄为：**两个 sink 的分工没有文档说明**（`README.md:55` 只讲根 `logs/`）。
6. 本单未跑全量套件（psy 全量 399s／并发不可归因），判据无一项要求全量数；所有读数来自 16 个日志文件的直接取证。
