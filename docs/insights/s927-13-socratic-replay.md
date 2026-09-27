# s927-13 psy 苏格拉底基准离线回放现状复测（B-098 链健康度）

> 班：`qoder-executor-20260927-1930-psy78`（波次 27，只读采集）· cwd `D:\code\psy-analysis` · 完成时间 2026-09-27 19:1x
> 性质：**只读复点**。零源码改动、零 golden 改动、零真实模型调用、零写库。

## 0. 环境锚点（全部本班现取，不引任何档里的旧读数）

| 项 | 现值 | 取法 |
|---|---|---|
| HEAD | `6f05d76`（2026-09-27 19:06:53 +0800，`docs(psy): s927-08/09/12 …`） | `git rev-parse HEAD` |
| 工作树 | `git status --porcelain` **12 行**，跑测试前后各取一次，逐行相同 | 见 §6 |
| 解释器 | `.venv\Scripts\python.exe` → Python 3.12.9 / pytest 9.1.1 / numpy 2.5.1 | `.venv/Scripts/python.exe -c "…"` |
| 模型凭据 | **环境里 `*API_KEY* / *BENCHMARK* / *DEEPSEEK* / *OPENAI* 命中 0 枚**（`KEY_VARS: []`） | `os.environ` 现扫 |

🔴 否证一处派单口径：波次 brief §5 表里写 psy `HEAD = 11e536d`，磁盘现值是 `6f05d76` —— 本班开工前 4 分钟（19:06:53）另有班次把 s927-08/09/12 三单提交了。**一切以现值为准**，下表比对用的是 `git log` 实测而非派单表。

## 1. 判据① 子集命令与结果

子集＝苏格拉底域 5 件（`git grep`/目录实测定位，无遗漏）：
`tests/test_socratic_quality.py`、`tests/test_socratic_benchmark.py`、`tests/test_socratic_drift_tracker.py`、`tests/test_socratic_benchmark_archive_infra.py`、`tests/test_upstream_socratic.py`

### 跑法 A：默认（不加 `--run-benchmark`，即常规 CI 口径）

```
$ .venv/Scripts/python.exe -m pytest tests/test_socratic_quality.py \
    tests/test_socratic_benchmark.py tests/test_socratic_drift_tracker.py \
    tests/test_socratic_benchmark_archive_infra.py tests/test_upstream_socratic.py -q
81 passed, 2 skipped in 3.57s        ← 复跑第二次 3.52s，计数一致
```

逐件拆分（同口径分别单跑，rc 均 0）：

| 文件 | 结果 |
|---|---|
| test_socratic_quality.py | **1 passed, 2 skipped** |
| test_socratic_benchmark.py | 21 passed |
| test_socratic_drift_tracker.py | 10 passed |
| test_socratic_benchmark_archive_infra.py | 17 passed |
| test_upstream_socratic.py | 32 passed |

2 枚 skip 的来源＝`tests/conftest.py:57` 的 `--run-benchmark` 门禁（未传旗标 ⇒ 凡 `benchmark` 关键字逐例加 skip），落在 `test_socratic_quality.py:57` 与 `:156` 两例上。

### 跑法 B：9/11 锚点原命令

```
$ .venv/Scripts/python.exe -m pytest tests/test_socratic_quality.py --run-benchmark -v
tests/test_socratic_quality.py::test_socratic_quality_benchmark SKIPPED  [ 33%]
tests/test_socratic_quality.py::test_benchmark_fixture_loadable PASSED   [ 66%]
tests/test_socratic_quality.py::test_socratic_quality_replay_offline PASSED [100%]
======================== 2 passed, 1 skipped in 1.00s =========================
```

SKIPPED 原因实测为 `tests\test_socratic_quality.py:62: 未设置 BENCHMARK_LLM_API_KEY 环境变量`（`-rs` 取）。
⇒ 该例**被门禁跳过**，不是通过；本班未设任何 key、未联网去"让它跑起来"。

### 门禁面普查

```
$ … pytest <5件> -m benchmark --collect-only -q
tests/test_socratic_quality.py::test_socratic_quality_benchmark
tests/test_socratic_quality.py::test_socratic_quality_replay_offline
2/83 tests collected (81 deselected) in 1.06s
```

## 2. 判据② 漂移表（对 9/11 落地基线）

基线出处（按 brief §3a，卷宗写的 `outbox/` 路径实际已搬到 `done/`）：
- `zcode-bridge/done/20260910-212204-c448.result.md`（B-098 落地单）
- `psy-analysis/docs/insights/replay-mark-eval-20260911.md`（9/11 夜间 p911r-32 评估档，含当时的两组实测数字）

| # | 观测量 | 9/11 基线（档载） | 本班现值（实测） | 漂移判定 | 归因 |
|---|---|---|---|---|---|
| 1 | `test_socratic_quality.py --run-benchmark -v` | 2 passed, 1 skipped / 1.18s | 2 passed, 1 skipped / 1.00s | **计数零漂移**，耗时 −15% | 环境侧（机器负载），非期望值变化 |
| 2 | `test_socratic_quality.py` 默认跑 | **3 skipped** / 0.07s | **1 passed, 2 skipped** | **+1 例进默认跑**（`test_benchmark_fixture_loadable` 解除连坐） | 码侧真变化：`fe763a4`(9/25) 摘文件级 `pytestmark`、改逐例标记 |
| 3 | `test_socratic_quality_replay_offline` 默认跑是否执行 | 否（连坐跳过） | **仍然否** | ⚠️ **零漂移＝缺陷原地存活** | 见 §3，唯一未闭的一枚 |
| 4 | 漂移观测面 `test_socratic_drift_tracker.py` | （当时整件 benchmark 连坐，10 skipped） | 10 passed | 10→0 skip | `92bfdca`(9/23, s923-34) 拆门禁 |
| 5 | judge 面 `test_socratic_benchmark.py` | 文件级 benchmark 连坐 | 21 passed（件内 docstring 自述"21 例全部离线"） | 静默失明→默认执行 | `fe763a4`(9/25) |
| 6 | 归档基建 `test_socratic_benchmark_archive_infra.py` | s922-125 落地时 15 passed | 17 passed | **+2 例** | `4443b3e`(9/25, s924-65) 修同秒撞名/大写后缀/侧车件，随修补钉 |
| 7 | golden 快照枚数 | 1（`benchmark_20260910_031938.json`） | **仍是 1** | 零进展 | c448 遗留第 1 条：第二 golden 需联网首跑 ⇒ 属人工放行，本班不产 |
| 8 | 引擎测试 `test_upstream_socratic.py` | 无档载基线 | 32 passed | 无基线可比，只登记现值 | — |

**"7 日健康度"口径落法**：链上 4 次提交全落在 9/22–9/25（`7f97243`→`92bfdca`→`4443b3e`/`fe763a4`），最近 7 日（9/21–9/27）该域**零新失败、零 golden 变更、零回归**；链的健康度现值是"绿"，但绿的成色分两种——#2/#4/#5/#6 是真扩容，#3 是**扩容后仍留在门禁里的漏项**。

## 3. 唯一实质发现（属测试面读数，不属统计结论）

`tests/test_socratic_quality.py:156` 的 `test_socratic_quality_replay_offline` **带着 `@pytest.mark.benchmark`，但它本身是零联网设计**（`:159` 主动 `monkeypatch.delenv("BENCHMARK_LLM_API_KEY")`、`:166-172` 用计数 spy 包住 `ask_socratic`、`:184` 断言 `calls["real"] == 0`）。后果：

- 默认跑法（＝常规 CI 口径）下，这枚**恰恰是为"消除联网依赖"而写的回放例从不执行**；
- 同文件 `:22-25` 的 s924 口径注释写的是"现在只在**真打 LLM** 的用例上逐例挂 benchmark（见下面两处函数级标记）"——**注释与代码不符**：两处函数级标记里只有 `:57` 真打 LLM，`:156` 不打。

这正是 9/11 评估档 `replay-mark-eval-20260911.md` 已推荐、但**至今未采纳**的"方案 A（独立 `replay` mark）"：当时原文写"影响面：全量 pytest 通过数 +1；无网络、无付费"，并点名方案 B 的风险为"CI 永不执行离线回放 → 回放测试的回归保护为零"。9/25 的 `fe763a4` 做了"摘文件级、改逐例"这一步，**但没有将 `:156` 移出 benchmark 门禁**，所以那条风险原地成立。

⇒ **本班不改**：改测试标记＝改门禁语义，超出只读采集授权；且它属"要不要重钉基线/门禁"一类判断。原文交给主班／人工拍：最小改动面＝把 `:156` 的 `@pytest.mark.benchmark` 换成 `replay`（需在 `pytest.ini:markers` 或 `tests/conftest.py:79` 注册一行），回滚成本＝单行 revert，复算入口＝本文 §1 跑法 A/B 两条命令＋`-m benchmark --collect-only` 计数（改后应从 2 降到 1）。
⚠️ 该处另需注意：`pytest.ini` 此刻是在途脏件（见 s927-15），任何 marker 注册改动都别落在它上面而不留痕。

## 4. 判据③ golden 的 mtime 与内容 hash（只读记录，未做任何写入/重钉）

```
tests/fixtures/socratic_benchmark.json              size 8944 B  mtime_ns 1779464093099120700  (2026-05-22 23:34:53.099 +0800)
  sha256 7e72bce26c46ba4cd69fdb576326143880e33ea4b612ef3afaf04c5b0b8cefb1
tests/fixtures/_benchmark_reports/benchmark_20260910_031938.json
  size 14643 B  mtime_ns 1788981578268982700  (2026-09-10 03:19:38.268 +0800)
  sha256 909b479962e3fe0ec53c23a875c58241976bc32a4f86be08efcb060ec8c09c78
```

枚数：`_benchmark_reports/` 下 `benchmark_*.json` **共 1 枚**，即 `_load_golden_replay()`（`:149-151` 取 `sorted()[-1]`）永远命中这一枚 ⇒ 所谓"回归对比"目前是**单快照自证**，没有第二个快照可对。

golden 内容读数（读，不改）：`n_cases=30`、`version="v3.7"`、`generated_at=2026-09-10T03:19:38.267505`、`llm={"provider":"relay","model":"gpt-5.6-sol"}`、空回复 0 例、带 error 0 例。
🔴 该 golden 是**经 711ev 中转 gpt-5.6-sol 产出的**（非 deepseek），与 c448 档/测试 docstring 里"provider 默认 deepseek"的叙述不同源——登记为口径不一致，**属给人看的事实，不构成任何数值结论**；要重录第二快照＝联网＋真模型调用＝人工闸，本班未做。

顺带登记：`socratic_benchmark.json` docstring 头写 `version v3.3`（`test_socratic_quality.py:5` 语境），golden 内记 `v3.7`，两者不一致，同样不改。

## 5. 判据④ 零真实模型调用（三重证据）

1. **前置无凭据**：`os.environ` 现扫，`API_KEY/BENCHMARK/DEEPSEEK/OPENAI` 关键字命中 0 枚；本班全程未设任何 key（`KEY_VARS: []`）。
2. **测试内自证**：真打 LLM 的 `test_socratic_quality_benchmark` 两次跑法都停在 `test_socratic_quality.py:62` 的 skip；`test_socratic_quality_replay_offline` 自带 spy 断言 `calls["real"] == 0`，且 `:159` 显式删 key 后才起跑。
3. **离线面被别的用例钉住**：`test_socratic_benchmark_archive_infra.py::test_evaluate_module_imports_no_outbound_network_stack_in_a_fresh_process`（起新子进程实测出站模块零加载）与 `::test_this_test_file_starts_no_network_stack_and_never_runs_the_main_flow` 两例均在本次子集里 PASSED。
4. 未装任何依赖、未联网、未跑 `--run-benchmark` 之外的真后端。

## 6. 证据 / 现场未动声明

- 跑测试**前**与**后**各取一次 `git status --porcelain`：均 12 行、逐行相同（含 `M pytest.ini`、`M src/output/interpretation.py` 等在途脏件），本班未 add/commit/restore/stash/checkout。
- 生产目录零写：`data/benchmark_history/` 下最新 mtime 仍是 `2026-09-16 01:21:06`（`benchmark_backfill_draft.json`），早于本班窗口 11 天 ⇒ 侧车无变化。（注：`data/` 整层 gitignore、无还原点，本班探针只落 `D:\code\tmp\qoder-executor-20260927-1930-psy78\`。）
- **在册红未触碰**：`test_export_gate_global_scan::test_all_download_buttons_accounted_for`（offender `questionnaire_panel.py`）不在本班 5 件子集里，两次跑法输出中**都未被带出**（81+2 / 83 计数可反证）；本班未消红、未复跑归因、未加白名单。
- 并发保护：未跑全量套件，只跑点名的 5 个文件；取 rc 一律用 `PIPESTATUS[0]`；psy 侧带 `PYTHONIOENCODING=utf-8`。
- 本仓**无 `--freeze` 机制**（等价闸＝`test_result_card_registry_snapshot.py` 的 44 键硬编码全等快照）。本文所有"基线"字样指 golden 快照文件，不是 freeze 基线；不存在"要不要重钉基线"的门禁动作。

## 7. 遗留（交人工／主班）

1. §3 的门禁漏项（`:156` 移出 benchmark）——要不要采纳 9/11 方案 A，交人工拍；本班未动一行。
2. 第二枚 golden 快照缺失 ⇒ 漂移表 #7 零进展；产它需联网真模型调用＝人工闸。
3. golden 内 `provider=relay / model=gpt-5.6-sol` 与 docstring 的 deepseek 叙述、`v3.7` 与 `v3.3` 两处口径不一致，只登记不修。
4. 派单表 HEAD 值（`11e536d`）与磁盘（`6f05d76`）已漂一次，主班收班时按现值取。
