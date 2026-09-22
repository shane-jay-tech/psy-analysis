# psy `data/` 全子目录面簿普查（s920-26，**只读，零删除**）

- 普查：2026-09-20 00:2x（班次 `qoder-rev-20260919-1020`）。口径：**只做文件级聚合**（计数/体积/mtime/写方推断），
  未读任何数据文件正文，未开 `feed.sqlite`，未列可能含个人信息的样本文件名。
- 锚点复核：`.gitignore:42` 确为 `data/`（整目录不入库）⇒ 面簿只能从磁盘做，git 里没有这些行的历史。
  「已知子目录只有 literature_feed／benchmark_history」成立：`find data -maxdepth 2 -type d` 共 **5 个目录**，
  其中 `literature_feed` 的三个子目录（raw／locks／logs）此前从未被面簿过。

## 一、面簿（目录级）

| 目录 | 文件数 | 体积 | 最早 mtime | 最后写入 | 写方（代码位置实测） |
|---|---:|---:|---|---|---|
| `data/benchmark_history/` | 4 | 49 KB | 2026-09-10 03:19 | **2026-09-16 01:21** | `scripts/evaluate_socratic_benchmark.py:29`（`REPO_ROOT/data/benchmark_history`，路径正确） |
| `data/literature_feed/`（含子目录合计） | 173 | 19 838 KB | 2026-05-30 00:34 | **2026-08-24 12:42** | 根常量 `src/literature_feed/paths.py:22-33` |
| ├ `literature_feed/raw/` | 167 | 19 332 KB | 2026-06-04 01:51 | **2026-08-24 12:34** | `src/literature_feed/storage/jsonl_archive.py:40`（`JSONL_RAW_DIR`） |
| ├ `literature_feed/locks/` | 1 | 1 KB | 2026-08-24 12:33 | 2026-08-24 12:33 | `paths.py:33 FETCH_LOCK_FILE = LOCK_DIR/"feed_fetch.lock"` |
| └ `literature_feed/logs/` | **0** | 0 | — | 从未写过 | **无写方**：`ensure_dirs()`（`paths.py:38`）只建 `DATA_ROOT/JSONL_RAW_DIR/LOCK_DIR`，不含 `logs` |
| `data/` 顶层散落文件 | 2 | 1.5 KB | 2026-08-24 01:20 | **2026-09-19 05:41** | 见下表 |

顶层文件逐个：

| 文件 | 体积 | mtime | 写方 |
|---|---:|---|---|
| `data/perf_history.jsonl` | 1528 B | 2026-08-24 01:20 | `scripts/perf_smoke.py:22`（`PROJECT_ROOT/data/perf_history.jsonl`） |
| `data/kaoyan.db` | **0 B** | **2026-09-19 05:41** | **psy 全仓零引用**（`kaoyan` 在 `*.py` 里无命中，含 src/app.py/scripts） |

`literature_feed` 扩展名构成：`jsonl 167／yaml 3／sqlite 1／lock 1`；三个 yaml 是 `domain_weights`、
`method_weights`（均 5-30）、`trending_weights`（8-24 12:34）；`feed.sqlite` 499 712 B，最后写 8-24 12:42。
`raw/` 的日分布尾部（按天计数）：`07-05:5｜07-10:1｜07-15:6｜08-14:4｜08-15:1｜08-24:6`，**8-24 之后零新增**。

## 二、异常与陈旧项清单（全部只登记，未删未改）

| # | 项 | 证据 | 判定 |
|---|---|---|---|
| **A1** | `data/kaoyan.db` 0 字节、今天 05:41 出现 | `ls -l data/kaoyan.db`；`grep kaoyan --include=*.py` 全仓 0 命中 | **外来落错目录**。0 字节＝只被 `sqlite3`/`open(w)` 碰过、没写进任何内容；psy 自己没有一句代码会建它 ⇒ 写入方在本仓之外（同族病灶见 s918-17 面簿：脚本路径/`cwd` 指错时会往不该写的目录落文件）。**处置需人拍板**（删除属跨判断动作，本单没动） |
| **A2** | `literature_feed/locks/feed_fetch.lock` 遗留 27 天（8-24 12:33） | 文件在盘；TTL 由 `scheduler/lock_manager.py:54 ttl_seconds=21600`＝6h 决定 | **不是活锁**：Windows 侧锁是 `msvcrt` 句柄锁，进程一死句柄即释放，文件只是"墓碑"。但 `is_stale()` 早该判陈旧，说明**8-24 之后再没有进程跑到过抢锁那一步** ⇒ 与 A3 同因 |
| **A3** | 整个 `literature_feed` 数据面自 **2026-08-24 12:42** 停摆 | `raw/` 最后写入 8-24 12:34；`feed.sqlite` 8-24 12:42；`git log -- src/literature_feed` 在 8-24 之后只有两笔：`17faa95`（09-02 公开发布准备）与 `5a9e46f`（09-19，本会话夹带的 d914-19 告警接线＋pid 读取修复） | **代码在动、数据不动**。面簿能坐实的到这一层为止：到底是调度器从未被触发、还是触发了但拉取全失败（网络/键失效），要跑一次只读探针才知道——`scripts/seed_literature_sources.py list --probe`（s919-20 刚加的只读子命令，不写库）是下家最省事的入口。**不在本单范围** |
| **A4** | `literature_feed/logs/` 空目录且**无任何代码引用** | `ensure_dirs()` 只建三个目录（`paths.py:38`）；`grep -rn "LOG" src/literature_feed/scheduler/` 0 命中 | **死目录**。要么补一个 `LOG_DIR` 常量把调度日志落进来（`paths.py:4-6` 的"所有自学习数据落 data/literature_feed 之下"原则正缺这一环），要么删目录。当前状态是"看着像有日志目录，实际永远为空"，排查时最误导人。**处置设计已出稿（s922-131，2026-09-23）：见 `docs/insights/psy-feed-logs-dir-design-20260922.md`，并先读该稿 §〇 对本行两处判据的修正** |
| **A5** | `scripts/benchmark_relay_shim.py:20` 的 `LOG_PATH = Path(__file__).parent / "data" / "benchmark_history"` 少一层 | 该式指向 `scripts/data/benchmark_history/`，而 `ls -d scripts/data` → **不存在**；同族正确写法是 `evaluate_socratic_benchmark.py:29` 的 `REPO_ROOT/…` | **路径 bug（尚未造成脏数据）**。因为该 shim 一旦被调用就会去建/写 `scripts/data/…`，与文档承诺的 `data/benchmark_history/` 分家 ⇒ 面簿口径会对不上。修法一行（`.parents[1]`），但属生产码改动，交日间 |
| **A6** | `perf_history.jsonl` 与 `trending_weights.yaml` 停在 8-24 | 见 §一表 | 正常老化，非异常；记在这里是为了让下次面簿能分辨"8-24 那天的批量动作"是同一批（性能冒烟＋雷达同日跑过） |

## 三、体积口径的说明（免得下次读错）

`du -sk` 给的是**磁盘占用**，不是字节和：`raw/` 167 个 jsonl 占 19 332 KB ≈ 每个约 116 KB，
而 `data/` 总量里 `literature_feed` 占 **99.7%**（19 838 / 19 891 KB）⇒ `data/` 面簿实际≈`literature_feed` 面簿，
其余三项（benchmark_history／perf_history／kaoyan.db）加起来不到 60 KB。
另：`data/` 整体被 `.gitignore:42` 排除 ⇒ **这些体积不进仓库、不进备份口径**，但也意味着**没有任何版本历史**，
误删不可恢复（这也是本单坚持零删除的理由）。

## 四、零改动自证与复现

- 本文件是唯一新增；`data/` 下**未写未删未改名**（面簿全程只读）。复现：
```bash
cd /d/code/psy-analysis
find data -maxdepth 2 -type d | sort                                  # 目录全集（5 个）
du -sk data/* data/literature_feed/*                                   # 体积
for d in data/benchmark_history data/literature_feed data/literature_feed/raw \
         data/literature_feed/locks data/literature_feed/logs; do
  printf "%s files=%s KB=%s newest=%s\n" "$d" "$(find $d -type f|wc -l)" "$(du -sk $d|cut -f1)" \
    "$(find $d -type f -printf '%TY-%Tm-%Td %TH:%TM\n'|sort|tail -1)"
done
ls -l --time-style=+%Y-%m-%d_%H:%M data/*.db data/*.jsonl data/literature_feed/locks/*   # A1/A2
sed -n '22,40p' src/literature_feed/paths.py                                            # A4：ensure_dirs 不含 logs
ls -d scripts/data 2>&1                                                                 # A5：No such file
grep -rn "LOG_PATH" scripts/benchmark_relay_shim.py                                     # A5
```
- 交叉核对：`git status --porcelain --untracked-files=no` 在普查期间无 `data/` 相关行（`data/` 本就不入库）。

## 五、未覆盖面（如实）

1. **未读任何正文**：`feed.sqlite` 未开库（里面是文献条目，属自学习数据）、`raw/*.jsonl` 未抽样、
   `benchmark_history` 的报告 md 未打开。凡"里面是什么内容/质量如何"的问题本单不答（隐私与数值双红线）。
2. **未做写入方进程级归因**：A1/A3 只到"代码里没有/数据面停摆"这一层，
   要坐实"谁在 05:41 建了 kaoyan.db""调度为何停摆"需要看进程计划任务（`schtasks`）与运行日志——那是跨仓动作。
3. `data/` 之外还有 `archive/`（`.gitignore:41`）与用户数据根 `~/.psy_analysis`（`app_paths.py:17-21`，
   projects/ 与 autosave 都在那儿）**未纳入本面簿** ⇒ 若目标是"全部落盘面簿"，那是另外的单。
