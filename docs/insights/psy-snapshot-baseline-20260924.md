# psy `-k snapshot` 族基线（s924-28 · 复跑读数 ＋ 机理更正）

> 班名 `qoder-executor-20260925-0510-psy43` · 取数 2026-09-25 05:1x · cwd `D:\code\psy-analysis` · **只读出稿**（未改任何 `src/`／`tests/` 件）
> 解释器：`D:\code\psy-analysis\.venv\Scripts\python.exe -m pytest`（纪律档 §七：裸 `python` 会走全局 sklearn 造假红）
> 本档**不回改**历史件 `docs/insights/psy-test-baseline-20260921.md`（卷宗明令，档内 §五）。所有计数现取，命令内联，可直接对拍。

---

## 〇、结论先行（5 条，含 2 条对上游表述的否证）

1. ✅ **`-k snapshot` 全族新基线：`111 passed, 1 skipped, 5105 deselected`，`rc=0`**（15.85s / 13.81s 两次连跑读数逐字相同）。唯一 skip 与快照无关＝`tests/test_playwright_e2e.py:24` 模块级 skip（playwright 未装）。
2. ✅ **单件 `tests/test_output_snapshot_roundtrip.py` 连跑 3 次：`10 passed` ×3、`rc=0` ×3**（1.89/1.66/1.77s）。⇒ `s923-21.result.md:78` 遗留问题 3 要求主班复核的那句（"全量那 1 failed ＝ `test_output_snapshot_roundtrip` 自本单后应消失，按 `10 passed` 复核"）**本单正式复核通过**，该在册红项可从口径里删除。卷宗的"预期 10 passed 量级"＝**命中**。
3. 🔴 **否证卷宗的机理表述**：卷宗写"跨秒红须连跑两次（**DOS zip 时间戳 2s 量化机制**）"。实测该机制**不是这条红的成因**，且"跨秒"也不相关：
   - 该件断言只读成员内容（`zf.read(name)`），**从不比较 zip 头**。探针里两次 `create_snapshot` 的 4 个成员头 `date_time` **逐位相等**（`(2026, 9, 25, 5, 18, 6)` 两读相同），成员却仍差 `analysis_params.json` ⇒ 头粒度进不了断言。
   - 测试件自己的 docstring 已写明："**真因不是 zip 头**，而是 `analysis_params.json` 里嵌了 `snapshot_created`"（`tests/test_output_snapshot_roundtrip.py:58`）。
   - 真因＝**Windows 粗墙钟**：`time.get_clock_info('time')` → `implementation='GetSystemTimeAsFileTime()', monotonic=False, adjustable=True, resolution=0.015625`；本班 5000 次相邻 `datetime.now().isoformat()` 采样**同值率 99.940%**。
   - "跨秒"不相关：探针里相邻两次调用相差 **965µs、同在一秒内**，墙钟段却已不同（`.958943` vs `.959909`）；反之跨秒也可能落同一 tick。⇒ 判据要按 tick 表述，不能按"跨秒"表述（§三 R1 给了更正版）。
4. ⚠ **机理细化（本班新测，与 `s923-21`／生产码注释的两处描述不同）**：
   - 墙钟**实际步进约 1ms**（末 6 位在采样窗内只有 4 种取值、相邻差 995/998/999µs），而 `get_clock_info('time').resolution` 仍报 `0.015625` ⇒ `src/output/snapshot.py:76-79` 与测试注释里的"**15.625ms 槽**"数值层面不准（**结论不受影响**：粗墙钟撑不住"相邻两次必不同"）。本班只登记，不改注释（该件属导出/快照生产码，不在本班产出面）。
   - `perf_counter_ns()` 的"同值率 0.000%"（`s923-21` 读数）**只在 `create_snapshot` 调用间距（ms 级）下成立**：本班纯循环紧采 5000 次，同值率 **43.329%** ⇒ 那个 `+mono` 尾数提供的是"调用开销 ≫ 计数器分辨率 100ns 时的区分度"，**不是"永不重复"**。这条决定了 §三 R1 的判定顺序必须先看时钟来源、再看尾数，而不是"有尾数就永久免检"。
5. ✅ **本班读数可归因**：`-k snapshot` 收集到的 **17 件（合计 111 例）与当时 porcelain 脏件（`app.py`／`pytest.ini`／`requirements-lock.txt`／`src/questionnaire/exporters.py`／`tests/test_questionnaire_export_pdf_positive.py`／`tests/test_exporters_cjk_font_fallback_observability.py`）交集＝0** ⇒ 上列读数是 **HEAD 等价读数**，不掺兄弟班在途改动。⚠ 且**跨主班一笔代提交仍稳定**：HEAD 在本班窗口内由 `1144427d`（05:03）推进到 `f3a9844f`（05:17:55，s924-20＋s924-22 入账＝兄弟班 psy42 的两件测试），本班 run1/run2 在前、run3 在后，三跑读数**逐字相同**（`111 passed, 1 skipped, 5105 deselected`）⇒ 本基线对这两笔 HEAD 同时成立。

---

## 一、全族读数（判据①）

```
$ .venv/Scripts/python.exe -m pytest tests -q -k snapshot          # run1
111 passed, 1 skipped, 5105 deselected in 15.85s                   # rc=0（>file 取码，未接管道）
$ .venv/Scripts/python.exe -m pytest tests -q -k snapshot -rs      # run2
SKIPPED [1] tests\test_playwright_e2e.py:24: playwright 未安装，跳过浏览器 E2E 复核
111 passed, 1 skipped, 5105 deselected in 13.81s                   # rc=0
$ .venv/Scripts/python.exe -m pytest tests -q -k snapshot          # run3（本档落盘、且主班已代提交 psy42 两单、HEAD=f3a9844f 之后）
111 passed, 1 skipped, 5105 deselected in 13.27s                   # rc=0 ⇒ 三跑同值，读数不随 HEAD/新档变化
```
`0 failed` ⇒ **判据① 成立**。收集面分解（`--collect-only -q`，17 件合计 **111**，与 run 读数闭合；模块级 skip 的 `test_playwright_e2e.py` 不在分组列表内，故收集表 111＝通过数 111、选定数 112）：

| 收集文件 | 例数 | 是否"快照族"本名 |
|---|---|---|
| `tests/test_output_snapshot_roundtrip.py` | 10 | ✅ 族（s923-21 修的那件） |
| `tests/test_result_card_registry_snapshot.py` | 23 | ✅ 族 |
| `tests/test_navigation_pagemodes_snapshot.py` | 15 | ✅ 族 |
| `tests/test_app_defaults_keys_snapshot.py` | 4 | ✅ 族 |
| `tests/test_experiment_templates.py` | 25 | ✗ 邻接（函数名含 snapshot） |
| `tests/test_lr_dirty_entry_matrix.py` | 11 | ✗ 邻接 |
| `tests/test_defense_qa_kb_data.py` | 6 | ✗ 邻接 |
| `tests/test_assumption_route_count_pin.py` | 4 | ✗ 邻接 |
| `tests/test_psychology_report_format_golden.py` | 3 | ✗ 邻接 |
| `tests/test_power_analysis.py` / `test_template_center_workspace.py` | 2 / 2 | ✗ 邻接 |
| `tests/test_environment_diagnosis.py` / `test_exporters_docx_geometry.py` / `test_method_contract_gate.py` / `test_project_panel_ui.py` / `test_workspace.py` / `test_workspace_restore_pairing_pins.py` | 各 1 | ✗ 邻接 |

⇒ 族本名 4 件＝**52 例**，邻接 **59 例**。⚠ **`-k` 是子串选择器**（纪律档 §十一.3）："111 全绿"≠"快照族 52 例全绿"的两倍信息，也别把 `-k snapshot` 当全量代理。`5105 deselected` ⇒ 本仓现收集总数 ≈ **5217**（**现取**、含他班未跟踪新件；别按 numstat 推）。

## 二、单件读数（判据②）

```
$ .venv/Scripts/python.exe -m pytest tests/test_output_snapshot_roundtrip.py -q
run1 rc=0 :: 10 passed in 1.89s
run2 rc=0 :: 10 passed in 1.66s
run3 rc=0 :: 10 passed in 1.77s
```
`10 passed` ×3 三连跑 ⇒ 复刻并追上 `s923-21.result.md:33-38` 的"3 连跑 rc=0"验收形态，且该件锚点 `:25 def test_roundtrip_restores_the_dataframe_exactly(out):` **零漂移**（本班 `sed -n '20,30p'` 复点）。

## 三、复跑判据（更正版；卷宗要的"连跑两次"这条按机理重写）

- **R1 何时必须连跑（判据表述更正）**：凡用例前提含"两次调用／两份产物的时间戳必不同"者，**一次绿不足以定性**。判定顺序：
  ① 先看该键的时钟来源——`datetime.now()`／`time.time()` 都走 `GetSystemTimeAsFileTime`（本班实测同值率 99.940%，`s923-21` 20 万次测 99.998%）⇒ **不可用作区分**，`time.time_ns()` 同源于粗时钟、换了等于没换；
  ② 再看有没有单调尾数（现解＝`src/output/snapshot.py:80` 的 `+mono{time.perf_counter_ns()}`，`QueryPerformanceCounter`、`monotonic=True`、`resolution=1e-07`）⇒ **有尾数且调用间距 ≫ 100ns 时，一次绿即可信**；
  ③ 无尾数而红了 ⇒ 连跑 5 次（历史配方 `psy-test-baseline-20260921.md:126` 的 `for i in 1..5`），若红在**约 82.5%～99.9% 概率**上复现、且红名固定指向"两产物必须不同"那一条，按**时钟红**定性、不要记成回归红。
  🔴 **别再用"跨秒"作触发条件**：实测红与秒边界无关（965µs 差、同秒内也能分开；同 tick 内跨秒也无用），触发条件是"两次调用落进同一个墙钟 tick"。
- **R2 免改码的鉴别力自证（本班采用，只读）**：`tmp/psy43/clock_probe.py`（`create_snapshot(..., output_path=None)` 走 `io.BytesIO`、**不落盘**，见 `src/output/snapshot.py:57-61`）输出四行决定性读数：粗墙钟同值率 99.940%／`perf_counter_ns` 紧采同值率 43.329%／**zip 头 `date_time` 两次相等**／**成员差异键＝`analysis_params.json`、params 差异键＝`snapshot_created`**。后两条正是"机理在内容不在 zip 头"的直读证据。
- **R3 变异刀（本班未执行，超只读位授权）**：摘掉 `snapshot.py:80` 的 `+mono{…}` 尾数（或换成 `time.time_ns()`）⇒ `test_returned_bytes_equal_the_file_written_in_the_same_call` 应按 R1① 概率转红。该刀改生产码，纪律档 §四.3／派单硬闸 3 ⇒ 需主班排窗，且**该件的防回归注释（`tests/test_output_snapshot_roundtrip.py:78-84`）已把这条因果钉在文字里**。

## 四、在册基线更新（给主班直接抄）

| 项 | 旧口径 | 现值（本班 05:1x 现取） |
|---|---|---|
| 全量里的 `1 failed ＝ test_output_snapshot_roundtrip` | 纪律档 §八在册 | 🔴 **删除**（s923-21 修复＋本单 3 连跑复核） |
| 单件 `test_output_snapshot_roundtrip.py` | 改前 `1 failed, 9 passed`（`s923-21:18`） | **10 passed、rc=0（×3）** |
| `-k snapshot` 族 | 无在册值 | **111 passed / 1 skipped / 5105 deselected / rc=0**（15.85s、13.81s 两跑一致） |
| psy 全量 | 纪律档 §七"4633/61/26/1 传闻级" | **本班未跑**（只读位，纪律档 §四.2 禁止并发跑全量）⇒ 该项仍属待主班收班统一取 |
| 在册红 `test_export_gate_global_scan::test_all_download_buttons_accounted_for` | 台账 81 | 本班未复跑、**不宣布变化**（`-k snapshot` 不覆盖它；纪律档 §八：撞红不自行消红） |
| 快照生产码 | `src/output/snapshot.py:74` 写 `datetime.now()` | 现值 `:80` 带 `+mono` 尾数；**锚点行号漂移 +6**（历史件的 `:74` 已过期，本档现取） |

## 五、历史件不回改（卷宗明令）

`docs/insights/psy-test-baseline-20260921.md`（153 行、跟踪且干净）的 §5 用"时钟粒度／同一 tick"描述该红，`:126` 给了 `for i in 1..5` 配方，`:133-135` 列了三条出口（冻结时钟接缝／注入不同值／降级断言）——**均留在原处不改**；实况是 s923-21 走了"第二条的变体（单调尾数注入）"。本档只承担"新基线＋机理更正"两件事，两处口径差异以本档现取读数为准、历史件按惯例保留。

## 六、零改动与副作用自证（判据③）

```
$ git status --porcelain           # 本班净新增恰 1 件：本档（?? docs/insights/psy-snapshot-baseline-20260924.md）
$ git diff --numstat               # 收工 5 行：app.py 12/40、pytest.ini 1/1、requirements-lock.txt 6/6、src/questionnaire/exporters.py 14/6、tests/test_questionnaire_export_pdf_positive.py 12/10 —— 全属他班在途，本班一行未动
$ python -c "…os.walk('data/literature_feed')…"     # 跑前：files 181 bytes 21059126 ／ 跑后：files 181 bytes 21059126 —— 逐位不变
```
porcelain 现读 9 行里，`?? docs/insights/psy-font-family-stacks-20260924.md` 是**本班前一单 s924-27** 的产出，`?? node_modules/` 与 3 件 ` M`／1 件 `??` 属他班；其余（含兄弟班 psy42 的测试件）已由主班在 05:17:55 以 `f3a9844f` 代提交转干净 ⇒ **本单在两笔 HEAD 下净新增都是恰好 1 件**。
- 未带 `LITERATURE_FEED_DATA_ROOT` 守卫的理由（现场复核而非默认）：`--collect-only` 表内 **17 件零命中 `literature|feed`**（`rg -c` rc=1／无匹配），`-k snapshot` 选定面不含文献族 ⇒ 不触发 `§十.2` 那条"旧形态会把 `trending_weights.yaml` 写进真库"的路径；真库仍以"件数／总字节"两读数自证未变。
- `data/literature_feed/feed.sqlite` 侧车现读：主文件 **499,712 B**、`-shm` 32,768 B、`-wal` **741,632 B**（派单 05:0x 观察值 741,632 B ⇒ 本班读数同值、未增长）。本班**未打开该库**（无 `sqlite3.connect`、无快照、无 `backup()`）⇒ 不产生"两路互不可比摘要"问题（派单硬闸 4：本班**不报任何库内不变量**，只报件数／字节两个文件系统读数）。`-wal` 增长的来源**非信箱班可判**，此处只登记现象。
- 兄弟班 psy42（`s924-20`／`s924-22`）在途件全程未碰；porcelain 里它的件**不写入本单"改动清单"**。

## 七、复算配方

```
cd D:/code/psy-analysis
.venv/Scripts/python.exe -m pytest tests -q -k snapshot                 > r1.txt 2>&1; echo $?
.venv/Scripts/python.exe -m pytest tests -q -k snapshot -rs             > r2.txt 2>&1; echo $?
.venv/Scripts/python.exe -m pytest tests/test_output_snapshot_roundtrip.py -q   # 连跑 3 次，取 rc
.venv/Scripts/python.exe -m pytest tests -q -k snapshot --collect-only -q       # 17 件分解表（合计 111）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe tmp/psy43/clock_probe.py        # R2 机理四读数（需 tmp/ 探针件在位）
```
⚠ 取 rc 一律 `>file 2>&1; echo $?`，**别接管道**（`| tail` 会把 rc 换成 `tail` 的 0；`-k` 空集是真 rc=5，纪律档 §十一.3 更正）。本档引用自身计数时不含"0 命中式判据"⇒ 无 §十.4 自命中问题（本档虽含 `snapshot` 字样，但 `--collect-only` 只看 `tests/` 下 `.py`，`docs/` 不参与）。
