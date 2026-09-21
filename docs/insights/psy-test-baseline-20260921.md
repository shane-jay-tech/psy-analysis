# psy-analysis 全量测试基线快照（2026-09-22 凌晨实跑，s921-12 的 3250 口径复核）

> 产出单：`n922-11-psy-baseline-file`（执行班 `qoder-executor-20260922-0000-psy` 子班）
> 全部数字 = 本机 `.venv` 实跑，逐条附命令。档内文件名写 20260921 是任务书指定的产出名，
> **实跑时刻跨到 09-22 凌晨**（起 00:09 / 收 00:47），以下每个快照都单独标了时刻。

## 0. 一句话结论

- 3277 / 3250 的差异**可以逐条对上**：+35 项是真实新增用例（其中 **18 项来自 4 个未跟踪的在途测试文件，
  不在任何 commit 里**），剩下 **8 项对不上**——因为 `s921-12` 记的「3250 passed」本身比同一棵树的
  可复现读数高 8，**没有任何树差异能解释这 8**。
- 所以：`3250` 不该继续当对照基线用；`KNOWN_ISSUES.md:38` 那条「当前 3306 个离线收集项」是
  **另一种口径**（`-m "not online"` 收集数），两者不可互换。
- 另发现一处**在册长期红项之外的第二红**：`test_output_snapshot_roundtrip`（时钟粒度，非本班造成，见 §5）。

## 1. 快照 A —— 本班开工时点（不含本班任何改动）

```
命令  ./.venv/Scripts/python.exe -m pytest -q --durations=15 -p no:cacheprovider
时刻  2026-09-22 00:09 起，耗时 187.68s (0:03:07)
工作树 HEAD=eec95c3(main) + 他人在途 M app.py(12+/40-) M pytest.ini(1+/1-) M requirements-lock.txt(6+/6-)
        + 4 个未跟踪 tests/*.py（见 §3 的 18 项）
结果  3277 passed, 60 skipped, 0 failed, 43 warnings
收集  collected 3336 items / 1 skipped（1 = 模块级 collection skip，故汇总口径 3337 = 3277+60）
日志  tmp/n922-11-baseline.log（tmp/ 已 gitignore，本单收尾删除）
```

> 注 1：与班单给的「9/21 实测 3277 passed / 60 skipped（约 321 秒）」**计数逐项相同**，
> 墙钟 187.68s 而非 321s——同一台机器上墙钟不可复现（首跑冷 `__pycache__`、并发负载都会动它），
> 所以本档把「时长」和「计数」分成两栏，不拿时长当结论。
> 注 2：`pytest.ini` 的在途改动把 `addopts` 从 `--strict-markers -q` 改成 `--strict-markers`。
> 这一条直接改变命令行 quiet 层级：在 `428406f` 的检出副本里 `-q` 会与 addopts 的 `-q` 叠成 `-qq`，
> 而 `-qq` **不打最终计数行**——本班第一次副本跑动就因此拿不到汇总（实测留痕，见 §4）。

### durations Top5（快照 A，`--durations=15` 的头部五条）

| # | 秒 | 用例 |
|---|-----|------|
| 1 | 19.94 | `tests/test_golden_stats.py::TestGoldenMediation::test_mediation_runs` |
| 2 | 17.89 | `tests/test_paper_export.py::test_export_zip_smoke` |
| 3 | 5.87 | `tests/test_delivery_package.py::test_zip_has_correct_structure_with_all_components` |
| 4 | 4.00 | `tests/test_ai_content_review.py::test_ai_content_review_all_fail_raises` |
| 5 | 3.88 | `tests/test_robustness.py::test_mediation_weak_effect` |

Top2 合计 37.83s = 全量墙钟 187.68s 的 **20.2%**，Top5 合计 51.58s = **27.5%**。
第 6-15 名全部落在 2.3-3.4s 且九条来自 `test_questionnaire_design.py` / `test_ui.py` 的同一族
（该族单例最慢 3.00s，共 10 条上榜）⇒ 想压门禁时长，只有前两条值得动，且都是统计计算本体（红线域，未碰）。

## 2. 快照 B —— 本班收班时点（含本班 +80 例）

```
命令  ./.venv/Scripts/python.exe -m pytest -q -rs --durations=5 -p no:cacheprovider
时刻  2026-09-22 00:41 起，耗时 180.34s (0:03:00)
结果  3356 passed, 1 failed, 60 skipped, 43 warnings
本班净增  +3 (s922-10) +55 (s922-12) +22 (s922-13) = +80 例，3356 = 3277 + 80 - 1(红) 全部转绿
唯一红项  tests/test_output_snapshot_roundtrip.py::test_returned_bytes_equal_the_file_written_in_the_same_call
          ——非本班造成，见 §5；本班三个新文件在该次全量里 80 例全绿
```

## 3. 与「3250」的逐条归因

对照物：`428406f`（s921-12，2026-09-21 19:24）提交原文末句「全量 3250 passed 0 failed」。
方法：把该 commit `git archive` 到 `tmp/` 检出副本，两棵树各跑一次
`pytest --collect-only -o addopts= -p no:cacheprovider -q`，**对 node-id 全集做排序 diff**（不靠人记数）。

```
428406f 副本：collected 3301 items / 1 skipped（= 3302）
快照 A  本树：collected 3336 items / 1 skipped（= 3337）
diff：+37 个 id 新增，-2 个 id 消失，净 +35
```

| 项 | 来源 | 净增 id | 归因（≥1 行/项） |
|---|---|---|---|
| 1 | `0fd0333` s921-15 | +6 | 新建 `tests/test_e2e_qimport_upload.py`（AppTest 真上传路径 6 例） |
| 2 | `e02df5a` s921-13 | +2 | `test_lock_manager.py`：删 1 条裕量式断言、加 3 条精确边界/接缝例（`+3/-1`） |
| 3 | `350acdb` s922-02 | +9 | `test_questionnaire_panel_logic.py`：pending 负秒 3 条 + 1 条 parametrize（9 行）；该文件原已含 3 条 pending 相关 id，故「12 条含 pending_elapsed」里有 9 条是净新 |
| 4 | `0a450dd` s922-06 | 0 | `test_feed_panel_charac.py` 那条是**改名翻正**（`is_swallowed`→`warns_like_weights`），diff 里正好一删一加 |
| 5 | **未跟踪在途** | **+18** | `test_analysis_contracts.py` 6 + `test_lock_alert_log.py` 3 + `test_perf_smoke_report.py` 5 + `test_startup_checks.py` 4。实测 18 例全绿（`pytest -q` 四文件 1.21s）。**这 18 项不在任何 commit 里 ⇒ 快照 A 的 3277 不是「干净树」读数**，`git clone` 出来的同 HEAD 只有 3259 |
| 6 | 合计 | **+35** | 3302 + 35 = 3337 ✓ 与快照 A 汇总逐项对齐 |
| 7 | 残差 | **−8 无法归因于树差异** | 若 3250 成立，则 3250 + 35 = 3285 应等于 3277……差 8。反推 428406f 隐含 skipped = 3302 − 3250 = 52，而快照 A 是 60。两棵树的 skip 门族实测**同为 74 collected + 1 模块级 skip**（6 个文件：playwright 三件 + socratic 三件，见 §4 命令），且这 6 个文件在 `428406f..eec95c3` 之间 tests/ 零改动 ⇒ skip 集合不可能少 8 条 ⇒ **唯一自洽解：同一棵树在同机可复现的是 3242 passed / 60 skipped，`3250` 那一次读数比它高 8，且没有任何差异可解释**（不是 `-m "not online"` 造成的——那种过滤只会让数变小） |

**结论**：引用基线数时必须同时给「命令 + 时刻 + 工作树 SHA + 是否含未跟踪文件」。
`3250 / 3277 / 3297 / 3306 / 2644` 这五个在册数字**分属四种口径**，见下表，不可互相印证：

| 数字 | 出处 | 口径 | 是否含未跟踪 |
|---|---|---|---|
| 2644 | `KNOWN_ISSUES.md:38` 旧值（09-17） | 未注明 | 不明 |
| 3250 | `428406f` s921-12 提交语 | 全量 passed（本机不可复现，比可复现读数高 8） | 当时不明 |
| 3242 | 本档 §3 第 7 行推导 | `428406f` 树 + 本机环境的可复现 passed | 否（干净检出） |
| 3277 | 本档快照 A | 全量 passed，无 marker 过滤 | **是（+18）** |
| 3297 | `62b1981` s921-17 | `--collect-only -q -m "not online"` | 否 |
| 3306 | `d7553a6` s922-08 / `KNOWN_ISSUES.md:38` | `--collect-only -q -m "not online"` | 否 |
| 3337 / 3417 | 本档快照 A / B | collected 汇总口径（含 1 条模块级 collection skip） | 是 |

> 交叉校验：`3306 − 3297 = 9` 恰等于 s922-02 在 `test_questionnaire_panel_logic.py` 净增的 9 条 id
> （两者之间只有 s922-02(+9) 与 s922-06(净 0) 动过 tests/）⇒ 本档的 node-id 计数法与仓里已记的两个
> 数字**在「收集 + not online」这一口径下逐位对得上**，本档第 1-6 行因此可信；只有第 7 行的 3250 不可复现。

## 4. 「干净检出能不能复现基线」——实测：不能

```
git archive 428406f | tar -x -C tmp/n922-11-at428406f
(cd 该副本 && PYTHONPATH=. <repo>/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider)
→ 第一轮：26 项红/错，全部因缺 gitignore 的 data/ 夹具（如
  data/benchmark_history/socratic_benchmark_20260909T192139Z.json、权重 seed YAML）
→ 补 cp -rn data/. 副本/data/ 之后第二轮：3 failed（下表），最终计数行被 -qq 吞掉
```

| 残留红项 | 根因（实测报错） | 说明 |
|---|---|---|
| `test_instance_lock.py::test_foreign_holder_blocks_with_pid` | `FileNotFoundError [WinError 2]` | `tests/test_instance_lock.py:110` 直用 `REPO/.venv/Scripts/python.exe` 起子进程——`.venv` 是 gitignore，干净检出根本没有 |
| `test_instance_lock.py::test_concurrent_subprocesses_exactly_one_wins` | 同上（`:134` 同一写法） | 同上 |
| `test_output_snapshot_roundtrip.py::test_returned_bytes_equal_...` | `assert set() == {'analysis_params.json'}` | 见 §5，与检出无关，是时钟粒度 |

⇒ 本仓全量基线**结构上绑定"本机这份工作树"**：未跟踪的 `.venv/`、`data/` 夹具、以及 §3 第 5 行的 18 条在途用例。
任何"复现基线"的尝试都必须在工作树里跑，或至少补 `.venv` 联接 + `data/` 覆盖，并接受那 18 条的存在。

## 5. 在册红项复核 + 新点名的第二红

- 班单在册的长期红项 `test_report_import_cwd`（GBK 编码族，主班在册 n922-01）：**两次全量均未复现红**
  （快照 A 0 failed、快照 B 该条也不在红项里）⇒ 与「偶发」定性一致，本档不改判。
- 新点名（**非本班造成，本档只登记不修**）：
  `tests/test_output_snapshot_roundtrip.py::test_returned_bytes_equal_the_file_written_in_the_same_call`
  在**干净工作树**下独立连跑 5 次：**3 红 2 绿**。
  ```
  for i in 1..5: pytest -q tests/test_output_snapshot_roundtrip.py
  → 10 passed / 1 failed / 1 failed / 10 passed / 1 failed
  ```
  根因（源码级）：`src/output/snapshot.py:74` 用 `datetime.now().isoformat()` 写 `snapshot_created`，
  该用例 :77-79 要求「同一进程内两次 `create_snapshot` 的 `analysis_params.json` 必不相同」；
  Windows 时钟粒度让两次调用落在同一 tick ⇒ 集合相同 ⇒ `assert set() == {'analysis_params.json'}` 红。
  用例自己的 docstring（s919-21）已声明它是「拿两次调用的时间戳差当断言前提」——这个前提在本机不总成立。
  可执行出口（三条，任选，均属改测试口径不属改产出）：①冻结时钟接缝（同仓 `s921-13` 给 `is_stale` 加
  `now=` 的同款手法）；②两次调用之间显式推进/注入不同 `snapshot_created`；③把该断言降级为
  「除 `snapshot_created` 外逐字节相同」而不再要求它必变。**本单一律未改。**

## 6. 以后引用本档的方式（建议主班采纳为口径）

```
基线命令  ./.venv/Scripts/python.exe -m pytest -q --durations=15 -p no:cacheprovider
须附三件  ①时刻 ②git rev-parse HEAD ③git status --porcelain（未跟踪 tests/*.py 必须列出）
skip 口径 60 = 34（`--run-benchmark` 门）+ 26（Playwright 未装）⇒ 装了就掉、加旗标就掉，别当趋势看
红项口径  「0 failed」只在快照 A 成立；快照 B 有 §5 那条偶发红 ⇒ 报「偶发 1 红」时必附独立复跑次数
```

## 7. 本档未做的事

- 未改任何生产码、未改任何测试、未改 `KNOWN_ISSUES.md:38` 那条 3306（它是收集口径，本身没错，
  只是常被当成全量 passed 用——要不要在该行补一句「收集口径」请主班拍板）。
- 未做 §3 第 7 行那 8 项的直接实验（需 `428406f` 副本再跑一次全量 `-rs` 并与本档 §2 的 skip 清单对 diff；
  副本要先补 `.venv` 联接才与真树等价）。软预算 40 分钟已到，按「超预算先落 partial」的纪律，
  这里选择**把已实测的部分交足、把这一项标成可执行出口**，整体判 done（完成标准两条都已满足）。
- 未 push，未动 `000-QUEUE.md`。
