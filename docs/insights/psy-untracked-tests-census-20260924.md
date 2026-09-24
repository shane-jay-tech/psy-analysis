# psy「untracked 测试件」红用例普查（s924-31 · 只读）

- 班：`qoder-executor-20260925-0540-psy45`（波次 11 补派）· 2026-09-25 05:28 认领 · cwd `D:\code\psy-analysis`
- 前手锚：`zcode-bridge/done/s922-134-paperengine-lazyinit.result.md:47`「同族风险是**别的 untracked 测试件里可能还藏着红用例**（本班只查了自己名下这单，未替他班验件）」——:47 逐字在盘，锚点未漂。
- 性质：**只读出稿**。生产码／测试件／配置／在册档一字未动，未 `add` 未 `commit`；探针与全部 pytest 输出落 gitignored `tmp/qoder-executor-20260925-0540-psy45/`（`git check-ignore -v` 命中 `.gitignore:29 tmp/`）。零库接触（本单不 connect 任何 sqlite）。

## 0. 结论速览

1. **人群现值 1 件、且在收班时段漂到 2 件**（`git ls-files --others --exclude-standard` 在 `tests/` pathspec 下：05:28–05:38 读 **1**，05:39 读 **2**，新的一件是兄弟班 psy44 `s924-29` 刚落的在途件，见 §5 末与 §3 #8）——不是卷宗投料时（9/24 00:40）的多件形态：9/24 01:28 主班用 `6243f0e` 一次性入库了 7 件「单据已结案、实物从未进过 git」的未跟踪测试件（68 例），本波 `f3a9844`（05:17）又入库 1 件。⇒ **人群是活的，普查表按 claim 时点（05:28）钉桩**，任何"再跑一次对不上"先查 `claims.log` 尾部班名。
2. **那 1 件有主，不是无主债**：`tests/test_exporters_cjk_font_fallback_observability.py` ＝ psy35 的 `s924-08` 产出件（挂起三单 s924-06/07/08 的主因件，台账 210）。全仓唯一可判「无主」的未跟踪件是 `node_modules/.vite/vitest/…/results.json`（91 B、mtime 09-19 04:14 的 vitest 缓存孤儿；pytest 不收集）。
3. **该件本身是绿的**：单跑 `1 passed in 0.18s` rc=0，与 psy35 done 行「新建 observability 件 1 例 passed」逐位相合。
4. 🔴 **普查真正的红在这里，但它不在 untracked 人群里**：`tests/test_exporters_cjk_font_fallback.py`（**已跟踪、盘态未改**、mtime 9/23 02:21、sha8 `0b8cd9c5`）现值 **3 failed / 4 passed rc=1**，三条红全部是 s923-05 的「观测面为零」钉桩。归因＝工作树 `M src/questionnaire/exporters.py`（挂起三单叠加态）新增的 `logger.debug`——**psy35 在 s924-08 done 行已预告这条红**，属必然产物而非回归，更非无主债。按 §十一.2 该族禁 `checkout`/`restore`，本班只登记不修，甲/乙两出口仍交人工。
5. **外溢面已量化**：导出族（`-k "exporters or export_pdf or cjk or docx"`，collect 120/5217）红名集**恰等于**上述 3 条，其余全绿；门禁族（`-k "download_buttons or export_gate"`）1 红＝台账 81 在册红，**零新增**。
6. 卷宗完成标准①②③全达；否证/修正 2 条人群口径前提见 §2。

## 1. 锚点与前提复核（卷宗每句当待验命题）

| 卷宗前提／锚 | 实测 | 判定 |
|---|---|---|
| 锚点 `s922-134.result.md:47`「别的 untracked 测试件里可能还藏着红用例」 | :47 逐字命中（`rg -n "untracked 测试件\|红用例"`） | 成立，且本班替前手补完「未替他班验件」那一半 |
| 「`git status --porcelain` 取 untracked `tests/*.py` 清单」（多件形态） | 现值 `??` 2 行，`tests/` 下仅 1 件 | **按实况收窄**：9/24 01:28 的 `6243f0e` 已入库 7 件、本波 `f3a9844` 入库 1 件 ⇒ 人群天然排空（不是"普查失效"） |
| 隐含前提「untracked 件里藏红」 | 那 1 件 `1 passed`；红在**已跟踪干净件**里 | **否证其形态、坐实其风险**：风险真实存在但载体不同——红由 untracked 件的**配套生产码改动**触发（同一笔挂起改动的两半分居 ?? 与 M 两态） |
| 派单横幅「人群口径二选一：`git ls-files --others --exclude-standard` vs `rg --hidden`（后者会把 `.git/objects/**` 拖进来）」 | `rg --hidden --files` 全仓 992 行，其中 **182 行以 `.git\` 开头** | **成立**（且差点被本班自己的字符类读成假零，见 §5 新坑）⇒ 人群口径只认 `git ls-files`，rg 系一律不可用作普查分母 |
| 「工作树里同时躺着 `node_modules/`」 | 在，且**只有 1 个文件**（`find node_modules -type f` = 1）；`.gitignore` 里**没有** `node_modules` 条目（`rg -c` rc=1） | 成立（体量与卷宗想象不同） |

## 2. 人群定义四档对拍（普查表按 P-git-tests 出）

| 档 | 取法 | 读数 | 用途判定 |
|---|---|---|---|
| **P-git** | `git ls-files --others --exclude-standard`（未跟踪∧未忽略） | 05:28 全仓 **2** ＝ `tests/…observability.py` ＋ `node_modules/.vite/…/results.json`；05:39 复读 **4**（＋本班 1 档＋psy44 在途 1 件） | ✅ **主口径**（按 claim 时点取 2） |
| P-git∩tests | 同上 pathspec `-- tests` | **1**（05:39 漂为 2，多的那件见 §3 #8） | ✅ 普查表人群 |
| P-status | `git status --porcelain` 的 `??` 行 | 2 行（`node_modules/` **目录折叠态**，非 1 文件） | ⚠ 只能当"有没有东西"，数文件会漏（折叠） |
| P-disk | 盘上 `tests/**/test_*.py`（= pytest `testpaths=tests`＋`python_files=test_*.py` 的真实收集面） | **290** 份（05:33 取）：已跟踪 289 ＋ 未跟踪 1；**被忽略的测试件 0**；`tests/` 外（排除 `.venv`/`tmp`/`node_modules`/`data`/`archive`）的 `test_*.py` **0**。🔴 该档**天生随兄弟班写位漂移**（05:39 已 291），复跑请认「忽略件 0／tests 外 0」这两条不变量，别认总份数 | ✅ 收集盲区自检：既无"忽略件偷偷被收集"，也无"tests 外没人收集" |
| P-rg | `rg --hidden --files` | 992 行（含 `.git\` 前缀 **182**）；`--hidden --no-ignore` 27,632 行 | ❌ 不可用作分母：它既看不见"跟踪态"（290 份 test 全进去），又把 `.git/**` 拖进来 |

全量收集面（非本单判据，仅解释分母用）：`pytest tests --collect-only -q` → **5217 tests collected rc=0**，本班窗口内三次读数同值。

## 3. 普查表（每件一行，pytest 摘要行原文；解释器 `.venv/Scripts/python.exe` 3.12.9，`PYTHONIOENCODING=utf-8`）

| # | 件 | 跟踪态 | sha8 | 命令（单件，`-q`） | 读数 | rc | 红例 |
|---|---|---|---|---|---|---|---|
| 1 | `tests/test_exporters_cjk_font_fallback_observability.py` | `??`（P-git 人群） | `6c71e142` | `pytest tests/test_exporters_cjk_font_fallback_observability.py -q` | `1 passed in 0.18s` | 0 | — |
| 2 | `node_modules/.vite/vitest/da39a3…/results.json` | `??` | 非件（JSON 缓存 91 B） | 不适用（`testpaths=tests`＋`python_files=test_*.py` 均不匹配） | 无 pytest 读数 | — | — |
| 3 | `tests/test_questionnaire_export_pdf_positive.py` | `M`（挂起单配套，**补充行**，非人群） | `fdc3d191` | `pytest tests/test_questionnaire_export_pdf_positive.py -q` | `4 passed in 1.67s` | 0 | — |
| 4 | `tests/test_exporters_cjk_font_fallback.py` | 已跟踪、盘态未改（**补充行**：红载体） | `0b8cd9c5` | `pytest tests/test_exporters_cjk_font_fallback.py -q` | `3 failed, 4 passed in 0.39s` | **1** | 见 §4 |
| 5 | 1＋4 同跑（污染自检） | — | — | `pytest tests/test_exporters_cjk_font_fallback.py tests/test_exporters_cjk_font_fallback_observability.py -q` | `3 failed, 5 passed in 0.53s` | 1 | 未跟踪那 1 例在合跑下仍绿 ⇒ 两份件的 `qn` 补丁互不泄漏（件内 docstring 声称"刻意 import 复制而非跨文件引用"实测成立） |
| 6 | 导出族 | — | — | `pytest tests -q -k "exporters or export_pdf or cjk or docx"` | `3 failed, 116 passed, 1 skipped, 5097 deselected, 1 xfailed in 27.49s` | 1 | 红名集 ⊆ #4 三条（**外溢为零**） |
| 7 | 门禁族 | — | — | `pytest tests -q -k "download_buttons or export_gate"` | `1 failed, 19 passed, 1 skipped, 5197 deselected in 14.01s` | 1 | 唯一红＝在册红 `test_export_gate_global_scan::test_all_download_buttons_accounted_for`（台账 81，非本批引入，按 §八 不消红） |
| 8 | `tests/test_feed_store_transaction_rollback.py` | `??`（**窗口内漂进来的兄弟班在途件**，mtime 05:39:03） | `11eed178` | `pytest tests/test_feed_store_transaction_rollback.py -q` | `6 passed in 0.30s` | 0 | — ｜**观察行、不入普查承重**：件属 psy44 `s924-30`（写位，05:36 claim 在册、本班收工时仍未 done），本班跑它只为量"人群漂了多少"，不据半成品读数定性；跑后复验 `data/` 10 分钟内被改文件 **0** 件、文献库 181 件／21,059,126 B 逐位不变（psy44 的 s924-29 done 行自报"feed 族连跑会**真写 yaml**"，故这条自证必做；下传口径＝只读位别跑兄弟班在途件，量漂移用 `git ls-files` 足够） |

**红件数／红例数**：人群内（#1–#2）红件 **0**、红例 **0**；工作树叠加态整体（#3–#7）红件 **2**（`test_exporters_cjk_font_fallback.py`、`test_export_gate_global_scan.py`）、红例 **4**，其中 1 条为 9/23 前在册、3 条为挂起三单必然产物；#8 属兄弟班在途件、另计不入本表。

## 4. 红例清单（只登记，不修）

`tests/test_exporters_cjk_font_fallback.py`（s923-05 的三条「观测面为零」钉桩）：

1. `test_structural_failure_leaves_no_log_record_and_no_return_signal` — :175 `assert caplog.records == []` 实得 5 条 `DEBUG src.questionnaire.exporters:exporters.py:255 docx 字体 … 设置失败（回退默认）: forced failure on w:rPr`
2. `test_exporters_module_itself_has_no_observability_surface`
3. `test_docx_ships_normally_while_cjk_mapping_silently_missing`

**归因链（只读证据，未做任何还原实验）**：工作树 `git diff -U0 src/questionnaire/exporters.py` 净加 `+import logging` / `+logger = logging.getLogger(__name__)` / `+logger.debug("docx 字体 %s 设置失败（回退默认）: %s", …)`（注释自署 s924-08 口径 A），另有 s924-07（删 `uni=True`）与 s924-06（`return bytes(pdf.output())`）两处 hunk ⇒ 三条红由 **logger.debug 那一处**单独充分造成，与 PDF 两 hunk 无关（#6 里 PDF 族 116 例全绿）。psy35 的 `s924-08` done 行（`claims.log:4999`）已预告「落地必让 s923-05 三条观测面钉桩转红」，主班 note（`:5017`）据此把三单整体挂起并出 `psy35-s924-060708-pending.patch`。

⚠ 一处计数观察未坐实（不猜）：#6 三桶合计 3＋116＋1＝120 与 collect 120 相合，但另报 `1 xfailed` ⇒ 121 > 120。本班判为「xfail 标记项在 `-k` 通道下的独立报告形态」，未做机理实验（要改选择器才能复现，超出只读必要面），**登记为观察、不影响红名集结论**。

## 5. 归属判定（判据＝`claims.log` × `git log --name-status` × mtime，三源同向）

| 件 | 归属 | 证据 |
|---|---|---|
| `tests/test_exporters_cjk_font_fallback_observability.py` `??` | **psy35 / `s924-08`**（挂起三单主因件） | `claims.log:4996`（01:27 claim，预告"新增 caplog 用例"）、`:4999`（01:35 done partial，「新建 observability 件 1 例 passed」）、`:5015-5017`（主班 02:15 note：三单同文件 hunk 不可拆、整体挂起、快照 `tmp/handover-snapshot-20260924/psy35-s924-08-observability-test.py`）；件 mtime 09-25 01:29:27；件内 docstring 自述「s924-08，口径 A 落地件」 |
| `tests/test_questionnaire_export_pdf_positive.py` `M` | **psy35 / `s924-06`**（第 3 例反向改写） | `claims.log:4987`（01:18 done）；mtime 09-25 01:15:13；`git diff --numstat` 该件 +22/-…属他班在途 |
| `src/questionnaire/exporters.py` `M` | **psy35 / `s924-06`＋`07`＋`08` 三单叠加态** | `claims.log:5015`「工作树 exporters.py 现为三单叠加态，下班禁 checkout/restore」 |
| `node_modules/.vite/vitest/…/results.json` `??` | **无主**（唯一一件） | 纯 Python 仓根目录无 `package.json`/`package-lock.json`；9/19 04:14 的 vitest 缓存；`claims.log` 无任一班车名指向它。**处置出口仅登记**：删（越界，本单禁止删范围外文件）或补 `.gitignore` 条目（改配置，超只读位）⇒ 交主班 |
| `app.py` / `pytest.ini` / `requirements-lock.txt` `M` | 他班在途在册项 | §七/§九 已登记；`pytest.ini` 现 diff＝`addopts` 去掉 `-q`（影响摘要行形态，本班全部读数按现状 `-q` 手加） |

**「本波刚入库的新件」不属 untracked 人群，别错记成无主债**：`f3a9844`（05:17，psy42 s924-20 新建 `tests/test_app_page_branch_pins.py` ＋ s924-22 改 `tests/test_i18n.py`）、`1657af8`／`2f08c60`／`dc1336a`／`5a8c9ce`／`c03d7a2` 各批测试件均已转跟踪态；`6243f0e`（9/24 01:28）是那批 7 件的历史清库笔。

**新坑（人群口径侧，下传）**：本班初用 `rg --hidden --files | rg -c '\.git[\\/]'` 读到 **0**，据此几乎写下"否证派单的 .git 说法"；改 python 直读同一集合得 **182/992**。真因两条叠加——① `rg --files` 在 Windows 打**反斜杠**路径（`.git\objects\…`），② Bash 工具链把命令里的 `\\` 吃成一个 `\`，字符类塌成 `[\/]`＝只剩斜杠 ⇒ **双重假零**。正解：人群计数用 python 直读，或至少 `rg -c '^\.git'`（该形态读数 183＝182＋`.gitignore`）。同族教训＝§九.3「数之前先验自己的字符类」。

## 6. 复算命令（判据①②③；🔴 普查档自己会漂人群，故一切全仓计数一律给"排除本档"形态）

```
$ git -C D:/code/psy-analysis ls-files --others --exclude-standard -- tests
tests/test_exporters_cjk_font_fallback_observability.py            # 05:28 人群 = 1 件；pathspec 天然免疫本班两档

$ git -C D:/code/psy-analysis ls-files --others --exclude-standard | wc -l
2                                                                  # 落档【前】读数；本班落 docs/insights 两档后此式读 4

$ git -C D:/code/psy-analysis ls-files --others --exclude-standard | rg -v '^docs/insights/psy-(untracked-tests|session-key-implicit)-census-20260924\.md$' | wc -l
2                                                                  # 基线时点读数；🔴 不给自命中数钉桩——05:39 同式读 3，差额 1 件是 psy44 的 tests/test_feed_store_transaction_rollback.py（他班在途，非本班产物），复跑式要判"人群"须再排 `-- tests/test_feed_store`

$ git -C D:/code/psy-analysis status --porcelain
# ?? 基线时点恰 2 行：node_modules/（目录折叠）、tests/test_exporters_cjk_font_fallback_observability.py；收工时该式仍含兄弟班 psy44 的在途 M/??，见 §7
```

$ cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_exporters_cjk_font_fallback_observability.py -q > tmp/qoder-executor-20260925-0540-psy45/r1.txt 2>&1; echo $?
0 / "1 passed in 0.18s"                                            # 取 rc 不接管道（§十一.3 更正）

$ cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_exporters_cjk_font_fallback.py -q > tmp/qoder-executor-20260925-0540-psy45/r3u.txt 2>&1; echo $?
1 / "3 failed, 4 passed in 0.39s"                                  # 不带 PYTHONIOENCODING 时同一 rc=1、中文全成乱码（§十三.1 同族：rc 对但细节丢）

$ git -C D:/code/psy-analysis diff -U0 src/questionnaire/exporters.py | rg -n "^[+-]"
# 净加 logging 两行＋except 分支 logger.debug ⇒ §4 归因链

$ cd D:/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/qoder-executor-20260925-0540-psy45/probe_untracked_pop.py
# P_GIT_TOTAL 2 / P_GIT_TESTS 1 / P_DISK_TESTS_COLLECTABLE 290 / TRACKED_TESTS 289 / P_DISK_TESTS_IGNORED 0 / TESTPY_OUTSIDE_TESTPATHS 0
```

## 7. 自证与边界

- **零仓库改动**：开工 05:28／收工 05:39 各跑一次 `git diff --numstat`，本班侧 0 行——收工多出的一行 `57 3 tests/test_feed_panel_trending_override.py` 与新 `?? tests/test_feed_store_transaction_rollback.py` **全部归因兄弟班 psy44（`M tests/test_feed_panel_trending_override.py` 属其 `s924-29`、05:36 done 未提交；`?? tests/test_feed_store_transaction_rollback.py` 属其 `s924-30`、05:36 claim 在途）**；本班四件被测件 sha8 收工复验逐位不变（`6c71e142`／`fdc3d191`／`0b8cd9c5`／`ce17c4dd`）；未 `add`、未 `commit`、未 `checkout`/`restore`；净新增只有本档 1 件（＋同班 `s924-33` 的 1 件），列路径交主班代提交。
- 🔴 **文献库不变量（因 §3 #8 跑过一件 feed 测试而必须自证）**：本班**未带** `LITERATURE_FEED_DATA_ROOT` 守卫跑了 `tests/test_feed_store_transaction_rollback.py`（件在 gitignored `tmp/` 外、属兄弟班在途件，跑前只判定"是否属人群漂移"）——跑后现场复验 `data/literature_feed` **181 件／21,059,126 B**（与 §九.2、psy41/psy43/psy44 各波同值），且 `data/**` 全树 10 分钟内被修改的文件数 **0**（python 直读 mtime，聚合摘要本班口径＝逐件 `relpath+size+mtime` 串接 sha256 前 16 位 `9e1259f8236325de`，与他班算法不同源不可互比）。⇒ 该件走的是 `tmp_path`/内存形态，无写库副作用；**但这仍是越界边缘动作，下传口径：只读位遇到"兄弟班在途件"不要跑，量人群漂移用 `git ls-files` 就够**。
- **只读位不跑全量**：破例口径未开——全量 399s 会把负载红算到同仓兄弟班头上；本单判据只要"每件一行读数"，故只跑单件与两个 `-k` 族（27.5s／14.0s）。
- **同仓并发**：收工时段出现 `?? tests/test_exporters_cjk_font_fallback_observability.py` 之外的 `M tests/test_feed_panel_trending_override.py`（psy44 `s924-29`，`claims.log:5192` 05:28 在册）＝兄弟班正常作业，本班零接触、未据此改判据（§十二）。
- **红线自查**：本单不涉鉴权／凭据／资金／统计结论／医疗数值——三条红全部是"是否留日志"的可观测性断言，无任何数值改动；`s924-08` 的甲/乙选案属人工闸，本班不代裁。
- 无库访问，故不涉 `data/kaoyan.db` 空库陷阱（台账 215④）与 literature_feed 不变量。
