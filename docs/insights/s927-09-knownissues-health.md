# s927-09 — KNOWN_ISSUES.md 现行 P1／P2 条目健康度盘点（只读·零改动本体）

- 班次：`qoder-executor-20260927-1850-psy77`｜波次 24｜cwd `D:\code\psy-analysis`｜HEAD `c7b8623`
- 取证窗口：`date` 18:45 → 18:53:15 +0800
- 对象：`KNOWN_ISSUES.md`（157 行／15,565 B／mtime 2026-09-25 06:03）**§v5.10 后续硬化路线表 :99–:105**，即现行 P1×3 ＋ P2×2 共 **5 条**
- 三栏判据：已闭环待回写／仍开放／锚点过期。🔴 **判据③：本班未改 KNOWN_ISSUES.md 本体**，回写只列清单（§4）。

## 0. 锚点复核（卷宗锚点族 :101／:102／:103／:104／:105）

| 卷宗锚点 | 磁盘现值 | 判定 |
|---|---|---|
| `:101` P1 多实例项目写入 | 行号与内容全中 | **在世** |
| `:102` P1 大工作区快照 | 全中（`a02626c` 实存，2026-09-11「方案B 后台保存…531ms→0.9ms」） | **在世** |
| `:103` P1 浏览器 E2E | 全中，且其内部锚点 `tests/test_playwright_e2e.py:24`、`:138 行作废` 逐条复算通过 | **在世** |
| `:104` P2 交付入口收敛 | 全中 | **在世**（但语义已被在途件改写，见 §1 行 4） |
| `:105` P2 编排层拆分 | 全中 | **在世**（下方有重大孤儿态，见 §1 行 5） |
| 卷宗「:101 行锚点族…:104 重复出现」 | 看板另有 :92/:93（🟡 中优先级）与 :154–:157 跟进条目两条 | 按 5 条主口径，:154–:157 只在行 2 作相邻引用 |

⇒ 本批**没有**因行号搬家而失效的锚点；漂移全部发生在**单元格内容**层（下表逐条）。

## 1. 逐条三栏（判据①：5/5）

| # | 条目 | 三栏判定 | 本班实测（命令→读数） | 闭环／否证证据（result 出处） |
|---|---|---|---|---|
| 1 | **P1 :101 多实例项目写入** | 🔵 **仍开放** ＋ 🟠 **锚点过期（措辞级）** ＋ 🟢 **半条已闭环待回写** | ① `grep -i alert src/utils/instance_lock.py` → **0 命中** ⇒「未推进」仍成立；② `git ls-files tests/test_lock_alert_log.py` → **命中（已跟踪）**，`git log --diff-filter=A` → **`6243f0e`（2026-09-24）"test(psy): 入库 7 件「单据已结案、实物从未进过 git」的未跟踪测试件（68 例）"** ⇒ 单元格里的 **"untracked" 已过期 3 天**；③ 单元格未提到的在册镜像钉桩 `tests/test_instance_lock_alert_gap_pin.py`（tracked，docstring 自述「告警接线落地后本套件翻红＝预期信号，提醒回写 KNOWN_ISSUES:101」）→ **边界已有代码看护，看板未记** | `done/d914-08-psy-known-issues-line101-fix.result.md`（:101 单元格订正本体，行号实测未漂）；`done/d914-19-psy-lock-alert-log.result.md`（feed 侧 `lock_manager._alert_once`＋`_read_owner_pid` 落地，新增 3 例）；`done/s922-130-instancelock-alert-pin.result.md`（12 例静态钉桩＋防抵账边界，含变异自证）；`done/p912-30-psy-multiprocess-lock-design.result.md`（方案 A 设计稿）。`_alert_once` 现值：`src/literature_feed/scheduler/lock_manager.py:89`，调用点 :119/:151/:251 |
| 2 | **P1 :102 大工作区快照** | 🔵 **仍开放**（残留＝超阈值方案 A 增量资产化未评估）；锚点在世 | `git cat-file -t a02626c` → commit；`git log -1 a02626c` → 2026-09-11 方案 B 后台化 ⇒ 单元格引用有效。h912-06 的阈值语义与观测字段在 `src/utils/autosave_bg.py`（该班改动清单在册）。相邻 :156 跟进条目（s922-111 扩面）与 :102 同域，口径一致：快照键清单以 `src/utils/workspace.py:build_workspace_snapshot()` 为准 | `done/h912-06-psy-snapshot-b-close.result.md`（方案 B 收口＋阈值常量×2/消费点/观测字段）；`done/0912-02-08-psy-autosave-thread-audit.result.md`（审计源头，:156 的来源）；`docs/insights/psy-workspace-snapshot-pairing-gate-20260925.md`（09-25 后续对账） |
| 3 | **P1 :103 浏览器 E2E** | 🔵 **仍开放**；数字锚点**全部复算命中**（非过期） | ① `.venv` `importlib.util.find_spec('playwright')` → **None** ⇒ 前提未变；② 单元格自带复现命令原样跑：`-q -rs -m "playwright or e2e"` → **26 skipped, 5501 deselected（rc=0，14.85s）**；③ `--collect-only -q -m "playwright or e2e"` → **25/5526 collected**；④ 逐文件计数：`test_e2e_v52_paths.py` 12 ＋ `test_playwright_golden_research_flow.py` 13 ＝ 25，`tests/test_playwright_e2e.py` **0 item** ⇒ 与「整件 11 例连 collect 都不进」「补装后 36 例＝25＋11」自洽；⑤ 内锚 `tests/test_playwright_e2e.py:24` 实测正是 `pytest.importorskip("playwright", reason=…)`；⑥ 内锚「:138 行」实测＝`| Playwright 未安装 | E2E 测试跳过 |` 行 ⇒ 25/26/36 三口径与两处行内锚点零漂移 | `done/916p-a4-002-psy-known-issues-e2e-count.result.md`（25→26 订正本体，附时点与复现命令）；`done/d914-38-psy-e2e-skip-inventory.result.md`（另一轴：34 skip 含 benchmark 门限、真非绿 23 项＝playwright 13 errors＋e2e_v52 10 failures，勿与本行 26 混用）；`done/d913d-32-psy-known-issues-line-sync.result.md`（行号同步）；`done/d913d-24-psy-full-suite-baseline-rerun.result.md` |
| 4 | **P2 :104 交付入口收敛** | 🔵 **仍开放** ＋ 🟠 **单元格语义已被在途件改写** ＋ 🟢 **一条已闭环待回写** | ① 本班现测 `git grep -n on_export` → 全仓仅 3 处：`app.py:57`（只 import）、`src/utils/usage_hooks.py:62`（定义）、`tests/test_usage_hooks.py:89`（测试自调）⇒ **"导出有审计痕迹"至今零生产调用点**，s923-35 的结论未被推翻也未被收口；② `grep -n reports .gitignore` → **rc=1 无命中** ⇒ P5 的 CWD 相对写根 `reports/snapshots/` 风险仍潜伏；③ 新增发散因子（未跟踪在途）：`scripts/research_release_gate.py`（141 行，五环节三态门禁）与在册 `scripts/release_gate.py`（307 行）并存 ⇒ 交付入口由「草稿／作业包／正式交付」三形态扩成"三形态＋两套 gate 脚本"，本行"统一入口语义"的靶子变大；④ 门禁件 `tests/test_export_naming_global.py` 仍在册（M1 的"看得见"问题未在源码侧修） | `docs/insights/psy-delivery-entry-matrix-20260922.md`（s922-126，M1–M6／P1–P5 定名，P2 只读对账）；`docs/insights/psy-delivery-entry-m1-design-20260923.md`（s923-35 施工方案稿，**src 与 .gitignore 零改动**，含"真 AST 面 38 站点里 30 个非合规门禁看不见"）；`outbox/s927-06.result.md`＋`docs/insights/s927-06-conclusion-gate.md`（09-27 结论闸三闸口对照，并 definitive 否证本仓有 `--freeze`：`git grep -in freeze -- '*.py'`＝0 命中，本班复点同值）⇒ **可作为 :104 重写的输入，看板尚未引** |
| 5 | **P2 :105 编排层拆分** | 🔵 **仍开放** ＋ 🔴 **新发现：拆出的模块在 HEAD 上是"孤儿"，看板与实测都不知情** | ① `git log --diff-filter=A -- src/ui/startup_checks.py src/ui/heavy_preload.py` → 两枚模块由 **`8fa9708`「d914-23 配套入库：src/ui heavy_preload ＋ startup_checks」** 入仓；② 但 `git log -S "run_once_startup_cleanup" -- app.py` → **0 命中**，且 `git show HEAD:app.py` 实测 :144 仍是内联 `cleanup_literature_cache(older_than_days=7)`、:167 仍是内联 `def _preload_heavy_deps()`、:181–184 仍是内联线程启动 ⇒ **HEAD 的 app.py 从未调用过这两枚模块**；③ `git grep "startup_checks\|heavy_preload" HEAD -- '*.py'` → 命中面只有模块自身＋`tests/test_heavy_preload.py`／`tests/test_startup_checks.py` ⇒ 生产路径不跑、测试却在跑（12 passed，本班定向）＝典型"绿但不覆盖生产"；④ 在途 `app.py`（8 枚 ` M` 之一，mtime 09-26 11:47:36）正是补上调用点的那一步：`git diff --numstat -- app.py` → **12 增／40 删**，行数 **2433（HEAD）→2405（工作树）** | `done/d913a-43-psy-app-split-2.result.md`（09-14 同两块拆分的**第一次**落地，自报 app.py 2698→2686，末句「改动留工作树未提交（任务禁令）」⇒ 与本班"HEAD 无调用点"互证：那次实物随工作树蒸发）；`done/d914-19`／`8fa9708` 说明**模块本体入库、调用点两次入工作树**的分工错位；对照 `docs/insights/s927-08-dirty-audit.md` §1 行 1（本班上一单：该在途件判"应提交"，依赖两枚模块均在册） |

**汇总**：5 条 P1/P2 ⇒ 仍开放 **5／5**（无一闭环）、锚点过期 **2 处**（:101 的 "untracked" 定语；:104 的入口清单未含在途 gate）、已闭环待回写 **2 条半**（:101 的镜像钉桩未记、:104 的 s927-06 结论未引）、数字锚点复算全中 **1 条**（:103，25/26/36＋两处行内锚）。

## 2. 看板外相邻漂移（同族行锚点，顺手实测，不在三栏判据内）

| 位置 | 看板值 | 本班现值 | 后果 |
|---|---|---|---|
| `:38` 测试基线行 | 「v5.11 当前 **3306** 个离线收集项（复现：`-m "not online" --collect-only -q`，2026-09-21 复测）」 | 同一条命令 09-27 实测 → **5496/5526 tests collected (30 deselected)** | 落后 **2190 项**（＋66%）。命令与口径没错，只是六天里 s923/s924/s927 批测试单没回写；夜间单以 3306 为"应有量级"会误判收集面塌陷 |
| `:144` 假设路由 15 键注 | 现值 15 键，钉桩 `tests/test_assumption_route_count_pin.py` | 该钉桩文件在册（`ls tests/` 命中） | 无漂 |
| `:157` 「psy 测试一律走 .venv」 | 指向 `docs/TESTING.md` | 本仓 `.venv` 实装与 `requirements-lock.txt` 不符（详见 `s927-12-deps-consistency.md`） | 结论行不漂，但"已验证环境"的引用物在漂 |

## 3. 判据与实测台账（可直接复算）

```
git rev-parse --short HEAD                                   # c7b8623
wc -l KNOWN_ISSUES.md                                        # 157（P1/P2 表在 :99–:105）
grep -in alert src/utils/instance_lock.py                    # 0 命中
git ls-files tests/test_lock_alert_log.py                    # 命中（已跟踪）
git log --diff-filter=A --format="%h %ad %s" --date=short -- tests/test_lock_alert_log.py
                                                             # 6243f0e 2026-09-24
git cat-file -t a02626c; git log -1 --date=short --format="%h %ad %s" a02626c
.venv/Scripts/python.exe -c "import importlib.util as u; print(u.find_spec('playwright'))"   # None
.venv/Scripts/python.exe -m pytest -q -rs -m "playwright or e2e"          # 26 skipped, 5501 deselected, rc=0
.venv/Scripts/python.exe -m pytest --collect-only -q -m "playwright or e2e"   # 25/5526 collected
.venv/Scripts/python.exe -m pytest --collect-only -q -m "not online"      # 5496/5526 collected (30 deselected)
.venv/Scripts/python.exe -m pytest tests/test_heavy_preload.py tests/test_startup_checks.py -q   # 12 passed
git grep -n on_export -- '*.py'                              # 3 处，零生产调用点
grep -n reports .gitignore                                   # rc=1
git log -S "run_once_startup_cleanup" -- app.py              # 0 命中（HEAD 从未接线）
git diff --numstat -- app.py                                 # 12  40  app.py
```
（一律带 `-p no:cacheprovider`；collect-only／marker 跑不执行用例。**data/ 零写自证**：跑前跑后 `feed.sqlite 499,712 B @09-23 12:15:30`、`feed.sqlite-shm 32,768 B @09-27 09:30:01` 逐项相等；**全树** `.venv` `pathlib.rglob` 复核＝**187 枚／21,103,172 B**，与在册基线逐位相符，且全树最大 mtime 仍是 `feed.sqlite-shm @09-27 09:30:01`（早于本班开窗）；`git status --porcelain` 全程 12 行未变。）

## 4. 回写清单（🔴 判据③：本班一律未执行，交主班或人工）

| # | 位置 | 建议改法（最小面） | 类型 | 回滚成本 |
|---|---|---|---|---|
| R1 | `:101` 单元格末 | 删 "untracked " 定语 → `tests/test_lock_alert_log.py（已于 6243f0e，2026-09-24 入库）`；并补一句"镜像钉桩＝`tests/test_instance_lock_alert_gap_pin.py`，其翻红即本行回写信号" | 措辞过期订正 | 单行，1 分钟 |
| R2 | `:38` | 3306 → 5496（2026-09-27 复测，命令原样），或按 :157 的精神改为"数字只在 TESTING.md 维护" | 数字刷新 | 单行 |
| R3 | `:104` | 把"三形态"扩为"三形态＋`scripts/release_gate.py`／`scripts/research_release_gate.py` 两套 gate（后者当前未跟踪）"，并记 `on_export` 零生产调用点（09-27 实测）与 `reports/` 未入 `.gitignore` 两条待收 | 语义扩面 | 单行改写 |
| R4 | `:105` | 补记孤儿态：「模块 `src/ui/{startup_checks,heavy_preload}.py` 已由 `8fa9708` 入仓，但 **HEAD 的 app.py 无调用点**（`git log -S run_once_startup_cleanup -- app.py`＝0 命中）；接线现挂在工作树（12+/40−）」＋"d913a-43 已做过一次、随工作树丢失"的教训句 | 新事实登记 | 单行 |
| R5 | `:103` | **不必改**（三口径复算全中）；可选：在行尾追加"2026-09-27 复算 26/25/36 全中"的时戳，便于下批省一次 marker 跑（≈35 s） | 时戳增补 | 可选，纯增行 |

⚠ R1–R5 全为 `KNOWN_ISSUES.md` 单文件单行级改动，但**执行位归主班／人工**（本班授权＝只读＋出 insights）。统计口径类内容（:102 的 10MB／2s／52MB 阈值、:38 之外的一切数值结论）本班未复核也未签。

## 5. 本班未做／边界

- 未改 `KNOWN_ISSUES.md` 及任何在册件；未 add／commit／stash／checkout／restore／clean。
- 未跑全量套件（只跑 marker 选择与 collect-only，二者不执行用例）；未复跑在册红 `test_export_gate_global_scan`（psy76 在册 1 failed，非本班所致）。
- 未开生产 `data/` 库、未执行 `scripts/research_release_gate.py`（它开 `data/literature_feed/feed.sqlite` 并写 `tmp/gate-evidence/`）。
- 卷宗锚点里"历史多次被夜间单引用 :101/:102/:103/:104/:105"一族**逐条复核完**，无"查无此行"的失效锚点（与 brief §3a 的 outbox→done 搬家缺陷无关：本单引用的 result 出处**实测全部在 `zcode-bridge/done/`**，唯 s927 本批自身的 01–06 结果件在 `outbox/`，见 result 证据节）。
