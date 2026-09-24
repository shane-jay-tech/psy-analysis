# psy `literature_feed/logs/` 死目录处置设计稿（s922-131，**只读：零删除、零建目录、零落码**）

- 班次：`qoder-executor-20260923-0022-psy1`（夜间 drain 子班）。取证时刻：2026-09-23 00:4x，HEAD `f6fc82d` ＋ 15 项脏工作树。
- 上游登记：`docs/insights/psy-data-dirs-20260919.md` §一表 :17 与 §二表 **A4**（:38）；
  再证：`docs/insights/psy-litfeed-data-plane-probe-20260922.md` §四.2（:69-75）。本稿是 A4 的**处置设计出口**，两篇均已在本稿 §六被引用。
> 勘误（2026-09-24）：本段判据已被 s923-10（zcode-bridge/done/s923-10.result.md）部分否证，成因以该 result 结论为准
> 现状（2026-09-25 复核 · qoder-executor-20260925-0630-psy49）：A4 的「死目录」判定不变（`logs/` 仍 0 条目、mtime 2026-09-14 08:00:47，复算 `stat data/literature_feed/logs`）；本稿 §〇 表所引 .bat 锚点 :23 / :25-27 / :37 已随 `1657af8` 漂为 :45 / :47 ⇒ 复算 `rg -n "mkdir|LOG=|VENV_PY" scripts/run_daily_feed.bat` 现取行号；上游那句「那 28 次不是走 .bat 来的」已被 s923-10 否证，成因以该 result 为准。另：本 2 行插注本身把上一条 :5 引的 probe §四.2 行区间由 `:69-75` 顺延成 `:69-76`（纪律档 §十.4 那类"注释行号被本次编辑自己推走"的形态，原文不复改）⇒ 认区间请用 `rg -n "A4（logs/ 死目录）" docs/insights/psy-litfeed-data-plane-probe-20260922.md` 现取。本稿原文零删改。
- 本机无 `rg`（不在 PATH）⇒ 凡任务书写 `rg` 的口径一律以 `git grep -n` / 定点 `grep -n` 复算，命令随附。

## 〇、锚点与前提复核（工单有两处要按磁盘实况改）

| 工单/台账前提 | 磁盘实况 | 判定 |
|---|---|---|
| `paths.py:33`「FETCH_LOCK_FILE: Path = LOCK_DIR / "feed_fetch.lock"」 | `sed -n '33p' src/literature_feed/paths.py` 逐字一致 | ✅ 零漂移 |
| `paths.py:38`「`for directory in (DATA_ROOT, JSONL_RAW_DIR, LOCK_DIR):`」 | 逐字一致，`ensure_dirs()`（:36-39）确实**不建** logs | ✅ 成立（A4 的那一半） |
| 「logs/ 在盘上存在」 | `find data -maxdepth 2 -type d` → 6 个目录，含 `data/literature_feed/logs`；`du -sk` → **0 KB**，`ls -a` 空，mtime **2026-09-14 08:00** | ✅ 成立（谁在 09-14 建/触它**未坐实**，见 §八.5） |
| 「**scheduler 零引用**／A4『无任何代码引用』」 | Python 侧真：`git grep -n "LOG_DIR" -- src/literature_feed` → **0 命中**；feed 包 64 处日志调用无一带文件路径。但 `scripts/run_daily_feed.bat` 有 **4 处**引用：`:8` 注释承诺、`:23` `mkdir`、`:25` `set "LOG=...logs\daily_runner.log"`、`:26-27/:37/:40` 追加写入（`grep -n "" scripts/run_daily_feed.bat`） | ⚠️ **半否证**：该目录**有消费方，只是不在 .py 里**。A4 的「无任何代码引用」只在 `--include=*.py` 口径下成立，probe §四.2 已独立发现同一件事 |
| 「死目录＝看着像有日志目录，实际永远为空」 | 空是事实，但**成因不是没接上**，而是 **`.bat` 从未成功跑过**（它会先 `mkdir` ＋ 写日志头再调 python；目录里连 `daily_runner.log` 都没有）| ⚠️ 归因要改：缺的不是「常量」，是「有人跑」 |
| 完成标准 3 用 `git status` 自证零删除 | `data/` 被 `.gitignore:42 data/` 整目录排除（`git check-ignore -v data/literature_feed/logs` → rc=0）⇒ git 对 `data/` **恒失明**，`git status` 不能证明「logs 未被动过」 | ⚠️ 口径补正：本稿 §七改用 `ls`＋`du`＋`find`＋mtime 四值前后对照 |

## 一、现有日志去向：三条链路（全部实测）

| 链路 | 触发方式 | 落点 | 盘上证据 |
|---|---|---|---|
| **A. 计划任务** | `schtasks` 调 `scripts/run_daily_feed.bat:37` | `data/literature_feed/logs/daily_runner.log`（cmd `>>` 重定向，**Python 完全不知道有这回事**） | ① 目录里连 `daily_runner.log` 都没有；② 本班复核 `schtasks /Query /TN "PsyLiteratureFeed"` → **rc=1「系统找不到指定的文件」**（任务根本没注册），与 probe §五.1 同读数；③ `fetch_runs` 里 28 次 `trigger='scheduler'` 与之矛盾，probe §四.2 判「那 28 次不是走 .bat 来的」 |
| **B. 直接 CLI** | `python -m src.literature_feed.scheduler` | `__main__.py:61-64` 唯一一处 `logging.basicConfig(...)` ⇒ **只有 StreamHandler(stderr)，无 FileHandler**（`git grep -n "FileHandler" -- '*.py'` 全仓 **0 命中**）→ 关终端即丢 | 复算即 §二表末行 |
| **C. app 内懒触发** | `src/literature_feed/ui/feed_panel.py:25,74` → `scheduler/bootstrap_check.maybe_trigger_async()` → 后台线程 `run_daily` | **什么都没配**：`app.py:12,18` 只有 `import logging` ＋ `getLogger`，全仓除 `__main__.py:61` 外再无 basicConfig | 实测读数见下 |

链路 C 的实测读数（这条决定了本单值不值得做）：

```bash
.venv/Scripts/python.exe -c "
import logging
lg=logging.getLogger('src.literature_feed.scheduler.bootstrap_check')
print(lg.handlers, logging.root.handlers, logging.getLevelName(lg.getEffectiveLevel()),
      lg.isEnabledFor(logging.INFO), lg.isEnabledFor(logging.WARNING))"
# → [] [] WARNING False True
```

⇒ app 进程里 root handlers 为空、有效级别停在默认 **WARNING**：
`bootstrap_check.py:82,92,110` 的三条 info（「已有后台线程跳过」「已后台触发 run_daily」「bootstrap async run done: status=…」）
**连 LogRecord 都不生成**（`isEnabledFor(INFO)=False`），`daily_runner.py` 的 5 条 info（:343,349 等）同理；
只有 WARNING+（:228 锁占用、:309/:369/:382 异常等）经 `logging.lastResort` 打到 Streamlit 控制台，用户看不见、会话一关即丢。
**「雷达为什么不更新」这个问题在生产里目前是不可回答的** —— 这正是 A4 说的"最误导人"的实质内容。

feed 侧日志写点清单（`git grep -c -E "logger\.(debug|info|warning|error|exception)|logging\.(warning|info|error|debug|exception)" -- src/literature_feed` ⇒ **64 处 / 14 文件**）：

| 文件 | 处数 | 与调度日志直接相关的关键行（实测锚） |
|---|---:|---|
| `scheduler/daily_runner.py` | 20 | `:228` 锁占用跳过（warning）、`:287` abandon_stale_runs 失败、`:309/:475/:493/:610` 逐源与逐文异常、`:343/:345/:349/:351/:360` trending 链、`:369` 打分回填失败、`:382/:393` 顶层异常与 finish_run 也失败、`:483` JSONL 归档失败、`:510` 状态写入失败、`:591/:595/:602` budget/LLM 未配置、`:606` 抽取失败 |
| `scheduler/bootstrap_check.py` | 4 | `:82`（info，已有线程跳过）、`:92`（info，已触发）、`:110`（info，async done: status/sources 计数）、`:123`（exception） |
| `scheduler/lock_manager.py` | 1 | `:94` `logging.warning("[lock-alert] %s %s", …)`（d914-19 已落地的**一次性**告警，与本单要补的"落盘"是两件事）、`:43` 另有一处 `print("已在运行中")` |
| `scheduler/__main__.py` | 1 | `:61` basicConfig、`:78` 顶层 `logging.exception`、`:82` `--json-summary` 往 **stdout** 打一行 JSON（`>> "%LOG%"` 时会被 .bat 收走） |
| `extract/extractor.py` | 19 | 抽取阶段（LLM 调用）的逐文异常 |
| `extract/headless_llm.py` `trend/trending_weights.py` `storage/migrations.py` `ui/feed_panel.py` 等 | 4/5/3/2 ＋ 其余 6 处 | 非调度主干，落盘后自动同源受益 |

## 二、两方案对比

| 判据 | **方案 A：补 `LOG_DIR` 常量＋调度日志落此** | **方案 B：删目录** |
|---|---|---|
| 消除 A4 矛盾 | ✅ 目录有了代码侧主人，"永远为空"变成"有内容/有轮转" | ✅ 面簿少一项，但**问题本身（不可观测）原样留着** |
| 与既有事实的一致性 | ✅ `.bat` 已经在把它当日志目录用，A 是**追认现状** | ❌ 要同时改 `.bat` 的 :8/:23/:25/:37 四处，否则 `mkdir` 会把它**当场重建** ⇒ B 单独执行是**不成立的**（这点是硬否证：删完下次跑 .bat 就长回来） |
| 排查收益 | 高：链路 B/C 的 64 个写点从"丢 stderr"变成"可回溯 30 天" | 无 |
| 改动面 | Python 3 处 ＋ .bat 1 处 ＋ prune 1 处 ＋ 测试 1 件（见 §三） | 1 次删除 ＋ .bat 4 处 |
| 测试隔离 | 需顺 `LITERATURE_FEED_DATA_ROOT`（`paths.py:19-25`）⇒ `LOG_DIR` 必须**派生自 DATA_ROOT**，否则测试会在真仓库里造 logs/ | 需改 `psy-data-dirs` 台账两行 |
| 回滚成本 | 低（删常量＋一行元组） | 中（目录不受 git 管，删了没历史，重建靠 `mkdir`/`.bat`） |
| 隐私/红线面 | 需明确"只写调度元数据"（§五.3） | 无 |
| 是否需新依赖 | 否（标准库 `logging` ＋ 现有 `prune_archive.py` 框架） | 否 |
| **结论** | **推荐（收窄为 A-）** | 不推荐，且**单做不成立** |

## 三、推荐：A-（补环，但把落盘范围收窄到 CLI 入口）

三条收窄口径，是本稿与"顺手全都写文件"的区别：

1. **只在 `__main__.py` 挂 FileHandler**；**app 进程（链路 C）不落盘**。
   理由：① Streamlit 多会话/多实例并发写同一文件，Windows 上会与 `.bat` 的 `>>` 句柄抢；② app 是用户面，不该在 `data/` 里持续长文件；③ 真正需要回溯的是**无人值守的每日跑批**。
   代价要说清：链路 C 的 `:82/:92/:110` 依然不可见 ⇒ 若主班要连 app 侧一起钉，就得再设计"按 pid 分文件"，那是另一单（§八.1）。
2. **不要与 `.bat` 的 `>>` 共用同一个文件名**。cmd 重定向与 Python FileHandler 各有各的缓冲，同文件双写者会把行序打乱。
   推荐双文件：Python 写 `LOG_DIR / "scheduler_YYYYMMDD.log"`（按天，§四#4），`.bat` 的 stdout 兜底改写 `daily_runner.out.log`（含 `--json-summary` 那一行与 exit 标记），:26-27/:40 的手写日志头保留在 .out 侧。
3. **命名与格式沿既有先例**：按天命名对齐 `src/utils/usage_logger.py:90,114`
   （`usage_events_%Y%m%d.jsonl` / `error_events_%Y%m%d.jsonl`），格式串直接用 `__main__.py:62` 现成的
   `%(asctime)s [%(levelname)s] %(name)s: %(message)s`；`FileHandler(..., encoding="utf-8", delay=True)`
   —— `delay=True` 防"只 `--help` 也建了个空日志"，`utf-8` 与 `.bat:13 chcp 65001`、`:29 PYTHONIOENCODING=utf-8` 同口径。

## 四、实施改动点清单（每点带实测锚；**本单一律未执行**）

| # | 文件:行（现状锚） | 改法 | 风险/归属 |
|---|---|---|---|
| 1 | `src/literature_feed/paths.py:25-33`（常量区，`LOCK_DIR` 定义在 :28、`FETCH_LOCK_FILE` :33） | 增 `LOG_DIR: Path = DATA_ROOT / "logs"`（**必须在 `FETCH_LOCK_FILE` 之后、`ensure_dirs` 之前**，保持 DATA_ROOT 派生链） | 低；派生错根会污染真仓 |
| 2 | `src/literature_feed/paths.py:36-39` `ensure_dirs()` | 元组改 `(DATA_ROOT, JSONL_RAW_DIR, LOCK_DIR, LOG_DIR)` | 低；幂等语义不变（:37 docstring 已声明） |
| 3 | `src/literature_feed/__init__.py:10-18` 的 `from .paths import (...)` ＋ `:20-28` `__all__` | 两处各加 `LOG_DIR` | 低；漏加则外部按 `src.literature_feed.LOG_DIR` 取不到（现有 7 个常量都在导出面上） |
| 4 | `src/literature_feed/scheduler/__main__.py:59-64`（现 `logging.basicConfig(level=…, format=…)`） | ① 新增 CLI 开关 `--log-file PATH`（默认 `LOG_DIR / f"scheduler_{date.today():%Y%m%d}.log"`）与 `--no-log-file`；② `ensure_dirs()` 后 `basicConfig(handlers=[logging.StreamHandler(), logging.FileHandler(path, encoding="utf-8", delay=True)], …)`；③ `:78` 的顶层 `logging.exception` 之前先 `ensure_dirs()`（现状：`ensure_dirs()` 只被 `storage/feed_store.py`（`ensure=True`）与 `storage/jsonl_archive.py:41` 间接调用，入口层没有 ⇒ 目录不存在时 FileHandler 会直接抛） | 中；**这是 A- 的唯一实质编码点**，须带 §五#9 的用例 |
| 5 | `scripts/run_daily_feed.bat:23`（`mkdir`）＋ `:25`（LOG 名）＋ `:26-27`、`:37`、`:40` | 删 `:23`（目录由 `ensure_dirs()` 建，**单一主人原则**）；`:25` 改 `daily_runner.out.log`；`:37` 加 `--log-file` 或靠默认 | 中：**属生产码**，且 `:16 set "PY=python"` 必须先换 `.venv\Scripts\python.exe`（见 §八.3 前置条件），否则接线后每天写一条 `ModuleNotFoundError` 进新日志，比现在更误导 |
| 6 | `src/literature_feed/scheduler/daily_runner.py:70` `logger = logging.getLogger(__name__)` | **不改**（命名空间 `src.literature_feed.scheduler.daily_runner` 已能被入口 handler 全量收到，包内 14 个模块同构 ⇒ 挂 1 个 handler 就覆盖 64 个写点） | 无 |
| 7 | `src/literature_feed/scheduler/bootstrap_check.py:82,92,110` | **不改**，但 app 侧可见性若要做，另单评估"按 pid 分文件"或写 `data/literature_feed/logs/app_bootstrap_*.log` | 需裁决（§八.1） |
| 8 | `scripts/prune_archive.py:23-24`（`RAW_DIR`/`RAW_KEEP_DAYS = 90`）＋ `:51-69 rule_raw` ＋ `:71-79 main` | 加 `LOGS_DIR = REPO/"data"/"literature_feed"/"logs"`、`LOG_KEEP_DAYS = 30`、`rule_logs(apply)`（照 `:55-58` 的 cutoff 与 `:63-67` 的「文件只 `unlink`、目录只 `rmtree` 于 archive 规则」分支），并在 `:77-78` 两条规则后 `rule_logs(args.apply)` | 低；**默认 dry-run 语义必须保持**（`:72` 的 `--apply`） |
| 9 | 测试：新增 `tests/test_feed_logs_dir.py`（≥4 例） | ① `ensure_dirs()` 建出 logs（打 `LITERATURE_FEED_DATA_ROOT` 到 tmp_path，参照 `tests/test_lock_alert_log.py:14-20` 的 env＋`sys.modules` 清理夹具）；② `--no-log-file` 时**不创建任何 .log**；③ 默认时 `scheduler_%Y%m%d.log` 出现且含 `[INFO] src.literature_feed.scheduler` 行；④ `rule_logs(apply=False)` 不删文件、`apply=True` 只删 cutoff 前的 `*.log` 且目录仍在 | 低；纯本地 IO，无网络 |
| 10 | 台账回写：`docs/insights/psy-data-dirs-20260919.md:17,38` 两行 ＋ `KNOWN_ISSUES.md` 是否需要一行 | A4 判定改「已定方案 A-，待实施（见本稿）」并**删除"无任何代码引用"这句**（不实，§〇） | 低 |

## 五、轮转与清理策略（含与 `prune_archive` 的衔接）

1. **轮转靠按天命名，不用 `RotatingFileHandler`**。全仓 `Rotating`/`TimedRotating` 零命中（§一表 B 的 grep），且多进程下 `Rotating` 的 rename 会与 `.bat` 的重定向句柄打架；`usage_logger.py:90` 已经用过按天路线，沿袭即可。
2. **保留期**：建议 `LOG_KEEP_DAYS = 30`（比 `RAW_KEEP_DAYS = 90`（`prune_archive.py:24`）短，理由：日志只服务排障，一个"抓取停摆"周期最迟 2 周内必须被发现）。取 90 与取 30 只影响 §五.4 的体积上界，不影响正确性 ⇒ 交主班定值（§八.4）。
3. **隐私与红线口径**：日志内容面 = 时间戳/级别/模块名/source_id/article_id/run_id/pid/异常文本。**不含**文献正文、不含 `PROJECTS_DIR` 下的用户项目数据（daily_runner 的 20 个写点实测都只打 id 与计数，见 §一表 :343「%d entries」、:510 等）。仍在 `data/`（`.gitignore:42`）⇒ 不入库。
   ⚠️ 一处已核对的导出面：`usage_logger.export_feedback_package`（:181-196）与 `clear_logs`（:229-236）只作用于**app 级 `logs/`**（`src/utils/app_paths.py:27` 的 `LOG_DIR = _configured_path("PSY_ANALYSIS_LOG_DIR", Path("logs"))`）并只 glob `*.jsonl` ⇒ 本稿的 feed 侧 `data/literature_feed/logs/*.log` 不会被导出、也不会被"清除日志"按钮顺带删掉。**两件事，别混**（与 KNOWN_ISSUES:101 对"另一把锁"的同款提醒一个性质）。
4. **体积上界（静态推算，不是实测）**：一次 `run_daily` 能产生的行数上界 ≈ 固定写点 64 条 ＋ 循环内写点（`daily_runner.py:475,493,510` 每源 3 条 × 8 源，`:606,610` 每文 ≤2 条 × `MAX_EXTRACT_ARTICLES_PER_RUN`）≈ 百量级；按 200 B/行 ⇒ **单日志 ≤ ~100 KB/天，30 天 ≤ ~3 MB**。
   ⚠️ 之所以是推算：本单是只读设计稿，**不得**真跑 `run_daily`（它会写 `feed.sqlite` 与 `raw/`，属数据面簿动作）。要实测读数请走 §八.3 的前置条件修好后，一次人工观察。
5. 与 `prune_archive` 的衔接口径：`rule_logs` 只处理 `*.log`、只 `unlink` 文件；**绝不 `rmtree(LOGS_DIR)`**（否则 A4 会以新形态复发）；保持"默认 dry-run、`--apply` 才动"的两段式（`prune_archive.py:72`）。

## 六、互相引用与需要回写的上游条目

- 本稿 ← **A4**（`psy-data-dirs-20260919.md` §一 :17 ＋ §二 :38）＝问题登记处；本稿给的是处置方案与改动点清单。
- 本稿 ← **probe §四.2**（`psy-litfeed-data-plane-probe-20260922.md:69-75`）＝本稿「.bat 是唯一既有消费方」结论的**独立再证**；两档互证后，"死目录"三字的正确表述应是「**未接通且无人跑**的目录」。
- 回写方向（本稿不代改台账正文之外的判据，仅列清单）：§四#10。

## 七、零改动自证（本单新增 1 个文件 ＋ 改 1 处台账指针，`data/` 全程未动）

```bash
cd /d/code/psy-analysis
ls -a -l --time-style=+%Y-%m-%d_%H:%M data/literature_feed/logs/  # 前＝后：total 4，仅 . 与 ..，目录 mtime 仍是 2026-09-14_08:00
du -sk data/literature_feed/logs                                  # 前＝后＝0 KB
find data -maxdepth 2 -type d | sort                              # 前＝后＝6 行（data / benchmark_history / literature_feed / locks / logs / raw）⇒ 未建任何新目录
git status --porcelain | wc -l                                    # 前 16 行 → 后 18 行（差额只有两处，且都是新增）
git status --porcelain | grep "^ M"                               # 后 4 行：app.py / pytest.ini / requirements-lock.txt（他班在途，未碰）＋ docs/insights/psy-data-dirs-20260919.md（本单为完成标准 4 加的回写指针，见 §六）
```

- ⚠️ 口径提醒：`data/` 被 `.gitignore:42` 整目录排除 ⇒ **"零删除"不可能靠 `git status` 自证**（§〇末行），以上面 `ls`／`du`／`find` 三值前后一致为准。

- 本单**未**调用 `run_daily` / `FeedStore(ensure=True)` / `prune_archive --apply` 中的任何一个（前两者会写 `data/`，后者是删除动作）。
- 未删任何文件；未改 `paths.py` / `__main__.py` / `run_daily_feed.bat` / `prune_archive.py`；他班在途的 ` M` 三件（`app.py`、`pytest.ini`、`requirements-lock.txt`）**未碰**——` M` 现在多出的第 4 行是本单 §六 的台账指针。
- §一链路 C 的读数与 §〇的锚点复核全部由 `.venv/Scripts/python.exe` 与只读 grep 取得（唯一一次解释器执行是 `logging` 内省，零 IO）。

## 八、未决与需裁决出口（交主班/人工）

1. **app 进程要不要也落盘**（§三.1 收窄后仍留盲区）：若要，需先定"按 pid 分文件"还是"写进 `fetch_runs` 表取代日志"。后者更贴本仓风格（`daily_runner` 已有 run 记录与 `abandon_stale_runs`），可能比补 FileHandler 更省事 —— **值得主班先判这条再决定是否实施 §四#4**。
2. `.bat` 改动是否与本接线同批（属生产码；不同批会出现「Python 写 scheduler_*.log、.bat 仍写 daily_runner.log」的双写窗口）。
3. **前置条件（硬）**：`run_daily_feed.bat:16 set "PY=python"` 走全局解释器，而本仓依赖装在 `.venv`（纪律档 line 57：全局 sklearn 1.9.1 vs `.venv` 1.5.2）。⚠️ 换解释器属生产码＋环境判断，本单未动；**在 A- 实施时必须一并换**，否则新日志只会记录每天一条 ImportError。
4. `LOG_KEEP_DAYS` 取 30 还是 90（§五.2）。
5. `data/literature_feed/logs` 的 mtime 是 **2026-09-14 08:00**，而 .bat 若真跑过必留下 `daily_runner.log` ⇒ "谁在 09-14 建的这个空目录"归因**未坐实**（本单不猜）。下次面簿可顺带看一眼是否再被重建 —— 若重建，说明有个我们没找到的第三方脚本在 `mkdir`。
6. 若主班拍板 **B（删目录）**：§二表已给出否证（`.bat:23` 的 `mkdir` 会当场重建），必须先同批改 .bat 四处，否则 B 不可执行。
