# s927-71 · psy tests 基线档现值刷新（3242 后漂移）（2026-09-29，只读取数＋本枚新档）

> 产出单：`s927-71`（执行班 `psy107`，只读位）。卷宗『做什么』原文＝跑全量 pytest 取现值（同解释器口径，见 `s927-27`）＋与 3242 对比给漂移表＋新增失败逐个归因。
> 取数窗口 **2026-09-29 09:41:40 → 09:46:39**（本地）。HEAD 全程 `0748a4a` 未动（跑前跑后各取一次，同值）。
> 本档**不改任何测试件、不改产品码、不改 `pytest.ini`／`KNOWN_ISSUES.md`**，不消红、不挂 `NEEDS_MIGRATION`、不写白名单。

## 0. 一句话结论（四条，全部现跑）

1. 现值＝**3 failed / 5509 passed / 29 skipped / 27 xfailed**（45 warnings，296.35 s，rc=1，`.venv` 解释器，无 `-m` 过滤）。
   与 s927-68 在 06:39 的那次读数**四计数逐位相同**——这不是巧：`cba266d..0748a4a` 只动了 3 枚 `docs/insights/*.md`，非文档件 **0** 枚。
2. 🔴 **对照物 3242 的身份要先纠正**：它不是任何一次实跑读数，是 n922-11 的**推导值**（`428406f` 副本收集面 3302 − 在册 skip 60）。
   本班用同一手法独立复算收集面＝**3301 items / 1 skipped**（rc=0，19.49 s）⇒ 汇总面 3302 可复算，3242 这个数因此可用；
   但引用时要写"推导"，别当"某次跑出来的 3242"。（卷宗『背景与锚点』把 n922-11 那句"3242 passed/60 skipped 可复现读数"当实读，属锚点表述滞后。）
3. 漂移 ＝ **passed +2267 / failed +3 / skipped −31 / xfailed +27 / 汇总面 +2266**；
   +2266 逐项归到 **86 枚测试件**（74 件净新增＋12 件既有改例数），**无一件例数减少**，最大单件 `tests/test_defense_qa_kb_data.py` +734（`a0173b0` s922-114）。
4. 三枚红的归因全部落地（**无一"归因不出"**）：2 枚＝夹具字节与 09-27 备份实现口径不同步（`6fb6b16`），1 枚＝在册 #81（原样留红）。
   本班**未修、未放宽、未挂名册**；处置建议见 §5 与 §8。

## 1. 现值（本班唯一一次全量的完整口径绑定）

| 口径要素 | 取值 |
|---|---|
| 解释器 | `D:\code\psy-analysis\.venv\Scripts\python.exe`（Python 3.12.9，`sys.prefix`＝`D:\code\psy-analysis\.venv`） |
| 命令 | `-m pytest -q --durations=10 -rs -rx -p no:cacheprovider`（**无 `-m` 过滤**＝全收集面；工作树 `addopts` 只有 `--strict-markers`，故 `-q` 必须显式给） |
| `LITERATURE_FEED_DATA_ROOT` | **未设**（＝与 3242 基线、与 s927-68 的 5509 同命令口径） |
| DB 路径现证 | 未设该变量时 `src.literature_feed.paths.DATA_ROOT` ＝ `D:\code\psy-analysis\data\literature_feed`（活库），`DB_PATH`＝ `...\feed.sqlite` 存在 ＝ 499,712 B |
| 时刻 | 2026-09-29 09:41:40 起 → 09:46:39 止（296.35 s / 0:04:56） |
| 树 | HEAD `0748a4a` ＋ 8 枚 ` M` 在途 ＋ 3 枚 `??` 在途；**tests/ 下无未跟踪件**（唯一在途测试件是已跟踪的 `tests/test_cfa_sem_golden.py`） |
| rc | **1**（`echo $?` 直读，未接管道） |

```
读数：3 failed, 5509 passed, 29 skipped, 27 xfailed, 45 warnings in 296.35s (0:04:56)
```

**形状自洽验算**：`5509 + 3 + 29 + 27 = 5568` ＝ 收集面 `5567 items + 1 条模块级 collection skip`（`tests/test_playwright_e2e.py:24` 的 `importorskip`）✓

三枚红（从 `full.log` 的 `FAILURES` 段逐字取，本班 `-rx` 把 `-rs` 顶掉 ⇒ 短摘要里只有 XFAIL 行，见 §8 第 3 条）：

```
tests/test_backup_user_data.py::test_create_backup_packs_projects_tree_and_feed_db
tests/test_backup_user_data.py::test_verify_accepts_archive_right_after_create
tests/test_export_gate_global_scan.py::TestExportGateGlobalScan::test_all_download_buttons_accounted_for
```

## 2. 漂移表（现值 vs 3242）

| 计数项 | 3242 基线（`428406f` 树，n922-11 推导） | 本班现值 | 差 |
|---|---|---|---|
| passed | 3242（＝3302 − 60，**非实读**） | **5509** | **+2267** |
| failed | 0 | **3** | **+3** |
| skipped | 60 | **29** | **−31** |
| xfailed | 0 | **27** | **+27** |
| 汇总面（四项之和） | 3302 | **5568** | **+2266** |
| collected（class 行） | 3301 items / 1 skipped（**本班在副本上独立复算，与 n922-11 逐位同**） | 5567 items / 1 skipped | +2266 |
| 墙钟 | 187.68 s（n922-11 快照 A，另一棵树） | 296.35 s | 不可复现，不列结论 |

**四个差项自洽**：`+2267（passed） − 31（skipped） + 27（xfailed） + 3（failed） = +2266` ＝ 汇总面差 ✓

### 2.1 在册各数字的口径归属（补全 n922-11 §3 的表，本班新增两行现值）

| 数字 | 出处 | 口径 | 是否含未跟踪件 |
|---|---|---|---|
| 3242 | n922-11 §3 第 7 行**推导** | `428406f` 树 passed | 否 |
| 3250 | `428406f` 提交语 | 全量 passed（同机不可复现，比可复现读数高 8） | 当时不明 |
| 3277 / 3356 | n922-11 快照 A / B | 全量 passed | 是（+18） |
| 5509 | s927-68（09-29 06:39，HEAD `cba266d`） | 全量 passed，venv 无过滤 | 否（tests 全跟踪） |
| **5509** | **本班（09-29 09:41，HEAD `0748a4a`）** | 同上 | 否 |

⇒ **3242 → 5509 这一段是"跨 7 天、跨 105 枚动过 tests/ 的提交"的漂移**，不是回归；s927-68 已主张 `3250/3242` 停止当数值锚点，本班用同一解释器同一命令复算，**支持该主张**（差 2267 项，量级问题）。

## 3. 漂移归因（node-id diff，逐族）

方法（沿用 n922-11 的手法，不靠人记数）：两棵树各跑一次 `--collect-only -q`（**只收集、不执行**），
得 `tmp\psy107\nodes-428406f.txt`（3301 行）与 `tmp\psy107\nodes-worktree.txt`（5567 行），
按**文件**计数求差；净新增文件再按"引入它的提交"归批（`git log --diff-filter=A`）。

```
基线树副本收集：3301 tests collected in 19.49s        rc=0
工作树收集：    5567 tests collected in 11.62s        rc=0
逐文件差分：    86 行（74 件净新增 ＋ 12 件既有改例数），合计 delta = +2266，负 delta 0 行
```

| 族（按引入提交的任务号） | 件数 | 净增例数 | 说明 |
|---|---|---|---|
| `s922-*` 批 | 27 | **+1467** | 含最大单件 `tests/test_defense_qa_kb_data.py` +734（`a0173b0` s922-114）、`test_experiment_templates.py` +111（`04e5dc0` s922-113）、`test_guardrails_pii_probes.py` +87（`4a33a88` s922-124）、`test_power_analysis.py` +67（`8545b66` s922-12）、`test_psychology_report_format_golden.py` +58（`6497cf3` s922-116） |
| 提交语无任务号（主班代提交／合笔） | 21 | **+382** | 含 `f1a903f`（字段血缘＋边界值，+64 与 +47）、`500e492`（结果字典 v1，+43／+24／+18）、`6243f0e`（入库 7 件从未进过 git 的未跟踪测试件，68 例）、`b85b084`（pd01 题名注入面，+40）、`13e7e52`（psy7 主班代提交，+19／+13／+9）、`cedb00e`（+12）、`fe763a4`（+9） |
| `s923-*` 批 | 14 | **+244** | 含 `test_lr_dirty_entry_matrix.py` +52（`ac1e7f6` s923-23）、`test_questionnaire_import_panel_render.py` +21（`6dcae95` s923-01..06）、`test_truncate_twins.py` +28（`bc6398a` s923-42）、`test_cfa_sem_golden.py` +19（`d37e156` s922-16 之后入库） |
| 既有文件改例数 | 12 | **+72** | 全部为增项，最大 `test_questionnaire_panel_logic.py` 27→64（+37）、`test_usage_hooks.py` 23→27（+4） |
| `s924-*` 批 | 7 | **+69** | 含 `test_undergrad_wizard_gap_warning_observability.py` +27（`ac396fb` s924-39）、`test_socratic_benchmark_archive_infra.py` +17（`7f97243` s922-125 之后） |
| `s927-*` 批 | 4 | **+23** | 09-2x 本会话批次的钉桩单 |
| `s921-*` 批 | 1 | **+9** | 基线提交之后落地的 s921 尾部件 |
| **合计** | **86** | **+2266** | 与汇总面差逐项闭合 ✓（逐件明细 `tmp\psy107\drift-per-file-sorted.txt`） |

### 3.1 在途件对分母的影响（本班实测，给 s927-68 遗留 ② 的答复）

`git archive HEAD` 另建副本 `tmp\psy107\at-HEAD`，收集面＝**5567 items / 1 skipped** ⇒
**与含 11 枚在途件的工作树收集面同值**，但 node-id 全集 diff **不为空**：差异恰 **4 条**，全在
`tests/test_cfa_sem_golden.py::TestCfaGoldenOnFourFactorFixture`（在途版把 4 条改名，
`test_golden_bands_currently_unmet` → `test_golden_bands_now_comparable_to_real_values` 等）。

⇒ 结论两条：① **分母等价**（在途件不改变例数），本班 5509 与"commit 基线的收集面"不矛盾；
② 🔴 **名集不等价** ⇒ 判"零新增红"必须比**红名集**，只比四计数会漏掉这种"同名族改判据"的形态。
本班**未**在 HEAD 副本上真跑全量（只收集），故"HEAD 树上这 4 条是否绿"**不主张**。

## 4. skip／xfail 两条口径的漂移（60→29、0→27）

| 项 | 基线构成（n922-11 `-rs` 普查） | 本班构成 | 取数手段 |
|---|---|---|---|
| `--run-benchmark` 门 | **34** | **2** | `-m benchmark --collect-only`：基线副本 **34/3301**、工作树 **2/5567**；这 2 条定向复跑确认抛在 `tests/test_socratic_quality.py:57` 与 `:156`（reason 需要 `--run-benchmark`） |
| 浏览器／Playwright 族 | **26** | **26** | 定向三件（`test_playwright_e2e.py`／`test_e2e_v52_paths.py`／`test_playwright_golden_research_flow.py`）实跑 `15 passed, 26 skipped in 3.74s`；SKIPPED 行按文件普查＝12＋13＋1（那 1 是 `test_playwright_e2e.py:24` 的模块级 `importorskip` 记账） |
| 残差 | 0 | **1** | 🔴 **归因不出**（见 §8 第 3 条），本班不作推断 |
| 合计 skipped | **60** ✓ | **29** ✓（28 已定位＋1 未定位） | — |
| xfailed | **0** | **27** | `-rx` 普查：`test_guardrails_pii_probes.py` **26**（`4a33a88` s922-124，`xfail(strict=False)`，KNOWN_ISSUES.md:150 假阴性面）＋ `test_experiment_design_ui_detail_branch.py` **1**（`:652` `xfail(strict=True)`，s923-40 登记的 docx_exporter 类型漂移）。两件在 `428406f` 副本里**都不存在** ⇒ xfailed 0→27 完全属 §3 的"净新增文件"，不是既有断言被改判 |

⚠ xfail 侧一条要点名给主班：那 **1 条是 `strict=True`**（`test_experiment_design_ui_detail_branch.py:652`，
`docx_exporter.py` 把 `List[str]` 喂给 `str` 形参）。它**命中集合清空即 XPASS 当场转红**，属人工域桩，
后续班次不许为了让基线好看去动它（同 learning 仓那两条同族桩的在册口径）。

## 5. 新增失败逐个归因（相对 3242 基线，3 枚全为新增）

三件红所在文件在基线树**都存在**（`tmp\psy107\at-428406f\tests\` 下 `ls` 命中），且本班逐件差分为 0
（例数没变）⇒ **基线树上它们是绿的**（n922-11 快照 A＝0 failed），三枚全部是"基线之后落下的改动把绿翻红"。

| 红项 | 抛点与原文 | 归因（族＋机理） | 本班处置 |
|---|---|---|---|
| `test_backup_user_data.py::test_create_backup_packs_projects_tree_and_feed_db` | `sqlite3.DatabaseError: file is not a database`，抛在 `scripts\backup_user_data.py:57` 的 `con.backup(out)`；日志 `:95` 给出 `src` ＝ `C:\Users\...\pytest-649\test_create_backup_packs_proje0\repo\data\literature_feed\feed.sqlite` | **测试件夹具与实现口径不同步**（属"命令/夹具口径红"，不是生产回归）：夹具 `tests\test_backup_user_data.py:24` 往 FEED_DB 路径写 `b"fake-sqlite"` 假字节；09-27 `6fb6b16`（r5 A1，2026-09-27 00:43:07）把 `_snapshot_sqlite` 从 `zf.write` 改成 SQLite backup API（该笔只动 `scripts\backup_user_data.py`／`src\ui\literature_review_panel.py`／`tests\test_lr_rerun_apptest.py` 三件，**未动本测试件**）⇒ 假字节首次被当库打开即拒。日志里的 `src` 是 tmp 沙盒路径 ⇒ **活库零接触**（与 §6 四点快照互证） | **未修**（改夹具＝改判据方向、改实现＝动备份语义，两条都在闸后）。台账 250 ⓑ 已在问"是否登记为在册红"，本班给到机理级归因，定性交主班/人工 |
| `test_backup_user_data.py::test_verify_accepts_archive_right_after_create` | 同抛点（`full.log:155-158`），同一 `DatabaseError` | 同族同因（共用 `sandbox` 夹具那条 `write_bytes(b"fake-sqlite")`） | 同上，未修 |
| `test_export_gate_global_scan.py::TestExportGateGlobalScan::test_all_download_buttons_accounted_for` | `AssertionError: ... ['src/ui/questionnaire_panel.py']`，`tests\test_export_gate_global_scan.py:88` | **在册唯一真红 #81**（`D:\code\docs\insights\drain-20260923-pending-human.md` 第 30 行）：红源＝主班代提交 `f8ca14e`（2026-09-23 01:44:58，s922-138/139/140）给 `src\ui\questionnaire_panel.py` 加了 3 枚 `st.download_button` 而未接 export_gate；`git merge-base --is-ancestor f8ca14e HEAD` rc=0（在 HEAD 链上） | **原样留红**：未挂 `NEEDS_MIGRATION`、未写白名单、未改判据（两条都是越权） |

## 6. 零写与零码改动自证

前提：`data/` 在 `.gitignore` 第 42 行（`git check-ignore -v data` 命中 `.gitignore:42:data/`）⇒ `git status` 对它结构性失明，
所以零写只能靠**逐件 size／mtime_ns／sha8 多点快照**（本班取了四点）。探针＝本班自建 `tmp\psy107\snap.py`（全文件 sha256 前 8 位，非 s927-68 那份"前 1 MB"口径，故 AGG12 与其 `fa318fd4a4db` **不可互比**）。

```
$ ./.venv/Scripts/python.exe tmp/psy107/snap.py tmp/psy107/data-before.txt  data   # 09:41:33 开跑前
data-before.txt:  files=187 total_bytes=21103172 AGG12=80aeeb03061a
$ ...（09:41:40→09:46:39 全量一次）
$ ... snap.py tmp/psy107/data-after.txt   data                                       # 09:46:56 全量后
data-after.txt:   files=187 total_bytes=21103172 AGG12=80aeeb03061a
$ ... snap.py tmp/psy107/data-after2.txt  data                                       # 09:54:30 定向复跑之后
data-after2.txt:  files=187 total_bytes=21103172 AGG12=80aeeb03061a
$ ... snap.py tmp/psy107/data-final.txt   data                                       # 10:01:54 收口第四点
data-final.txt:   files=187 total_bytes=21103172 AGG12=80aeeb03061a
$ diff tmp/psy107/data-before.txt tmp/psy107/data-after.txt   → DIFF_RC=0（0 行）
$ diff tmp/psy107/data-before.txt tmp/psy107/data-after2.txt  → DIFF_RC=0（0 行）
$ diff tmp/psy107/data-before.txt tmp/psy107/data-final.txt   → DIFF_RC=0（0 行）
$ find data -newermt "2026-09-29 09:41:00" | wc -l           → 0
```

**活库三件单点复算**（与台账 220 记的三枚 sha8 **逐位相同**）：
`feed.sqlite 499712 B 6bf5776b`／`feed.sqlite-wal 741632 B 4f9f07db`／`feed.sqlite-shm 32768 B 144cf1db`
⇒ 含 `-wal`/`-shm` 侧车在内整层零写入（本班全程未设 `LITERATURE_FEED_DATA_ROOT`，即"最危险"的口径下仍零写）。

**cwd 外写入自查**：

```
$ find "D:/code/backups/psy-analysis" -newermt "2026-09-29 09:41:00" | wc -l   → 0（5 枚 psy-*.zip ＋ README-RESTORE.md，最新仍 09-27 09:30）
$ find "$USERPROFILE/.psy_analysis" -newermt "2026-09-29 09:41:00" | wc -l     → 0（项目用户目录零新增）
$ ls -d tmp/s923-13                                                            → 还原点目录未删未覆
```

**根目录产物**：跑前后各点一次根目录清单，`diff` rc=0（32 条目集合不变）；`.coverage` **跑前不存在、跑后仍不存在**（本仓 `addopts` 无 coverage 插件）。
`.pytest_cache/`、`__pycache__/`、`logs/`、`tmp/` 均在 `.gitignore` 里，本班全程带 `-p no:cacheprovider`。

**零码改动**：`git status --porcelain` 收工＝开工同一集合（8 枚 ` M` ＋ 3 枚 `??`，本班未 add／未 commit／未 stash／未 checkout／未 restore），
HEAD 跑前跑后同值 `0748a4a`；本班新增件只有两类——本档（`docs\insights\s927-71-baseline-refresh.md`，`??`，待主班按精确路径代提交）
与 `tmp\psy107\`（gitignore 区，非交付物）。

## 7. 引用口径建议（与 s927-27／s927-68 对平，材料不是裁决）

1. **解释器**固定 `.venv`（`D:\Program` 那把会多 11 条、且包集不同：sklearn 1.9.1 vs 1.5.2、numpy 2.3.5 vs 2.5.1，见 s927-27 §4）。
2. **显式带 `-q`**：工作树 `pytest.ini` 的 `addopts` 是 `--strict-markers`（HEAD 是 `--strict-markers -q`），历史读数与现读数之间多一个"`-q` 谁带的"差异项（s927-68 §1 新点名的漂移源，本班复现）。
3. **引用"总数"必写是哪一型**：本班未测 `-m` 各型（s927-68 已给同刻四型 5567／5542／5537／5578，本班与之不互比、直接引）。
4. **基线四要素同笔**：解释器／命令（含 `-q` 与 `-m`）／时刻＋HEAD／是否含在途件——四缺一即不可与别的数互证。
5. 报"偶发 1 红"必附独立复跑次数：n922-11 点名的 `test_output_snapshot_roundtrip` 那条偶发红本次**在全量里为绿**（不在三枚红名集内），s927-68 亦然 ⇒ 它属"名集可换人"的形态，别把"psy 全量常态 1 红"当判据。

## 8. 本班归因不出／未做的事

1. 🔴 **skip 残差 1 条归因不出**：29 skipped 里 28 条已逐条定位（§4），余 1 条本班未定位、不作推断。
   根因是**本班自己的命令错**：同时写了 `-rs -rx`，pytest 的 `-r` 后者覆盖前者 ⇒ 只留下 XFAIL 行，
   SKIPPED 名集没进日志（s927-68 同命令口径读到的也是 29，故该残差不属"3242 之后新漂"的项）。
   下一次取数请把 `-r` 写成**单个** `-ra`（或 `-rs` 与 `--tb=no -q` 分开），一次跑齐四计数＋两个名集。
2. **未取"commit 基线"全量读数**：本班只在工作树上跑了这一次全量（禁碰在途件 ⇒ 不能在 HEAD 干净树上跑）。
   §3.1 给的是"HEAD 副本收集面 5567 ＝ 工作树 5567、node 名差 4 条"，**不等于** HEAD 树全量读数。s927-68 遗留 ② 仍未闭合。
3. **未跑 `-m` 各型与系统解释器对照**（s927-68 已在同刻取过，本班不复跑以免烧窗）；本班唯一一次全量＝§1 那行。
4. `tests\test_cfa_sem_golden.py` 在途版（`+59/−49` 行）的 4 条改名是否把"现状断言"换成了"修好后断言"——**属统计域裁决，本班未读其 diff 语义、未判性**。
5. 是否把 §5 前两枚登记为在册红、以及"改夹具还是改备份实现"的选路，**交主班/人工**（台账 250 ⓑ 原问未闭）。本班零改判据、零 skip／xfail 增删。
