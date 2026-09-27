# s927-14 psy 文献工具链（literature_manager / format_reference）回归子集复测

> 班：`qoder-executor-20260927-1930-psy78`（波次 27，只读采集）· cwd `D:\code\psy-analysis` · 2026-09-27 19:1x
> 性质：**只读复点**。零码改动、零写库、零联网、零真实模型调用。

## 0. 锚点复核（brief §3a：卷宗写 `outbox/` 的先去 `done/` 取）

| 卷宗锚点 | 实取 | 状态 |
|---|---|---|
| `docs/night-plans/BACKLOG.md` B-097/B-090/B-108 行 | 该档**不在 psy 仓**，在根仓 `D:\code\docs\night-plans\BACKLOG.md:62,66,67,82` | 三行均 `done` ＋ `[archived 2026-09-20]`；B-097＝ecdb、B-090＝dab0、B-108＝4acb、B-098＝c448 |
| 9/11 闭环时点读数 | `zcode-bridge/done/20260910-212204-ecdb.result.md`、`done/20260910-211946-dab0.result.md`、`done/20260911-053211-4acb.result.md` | 三枚均在世（outbox 内 0 命中＝路径搬家，非缺陷） |

## 1. 判据① 子集清单与结果

### 定位口径
`rg`/`git grep` 命中文献域测试件共 26 枚（`ls tests/ | grep -i literature|bibtex`）＋ 5 枚含 `format_reference`、9 枚含 `literature_manager`。
🔴 但**卷宗 scope 是工具链（literature_manager / format_reference）**，不是"全部 literature* 文件"：`literature_feed_*`（抓取/存储/UI，10 枚）属文献**订阅feed**域，其中两枚带 `pytestmark = pytest.mark.online`（真联网）⇒ 按卷宗"禁止联网"红线**排除**；`literature_review_*`（7 枚）属综述工作台域，同理不入本单。

### 跑法与现值（默认跑法，无 `--run-benchmark`）

```
$ .venv/Scripts/python.exe -m pytest tests/test_apa7_gate_and_citation.py tests/test_literature_format.py \
    tests/test_literature_library_offline.py tests/test_literature_manager_expansion.py \
    tests/test_literature_manager_network.py tests/test_apa7_manual_string_pin.py \
    tests/test_crawler_apa7_converge.py tests/test_citation_in_text.py tests/test_lock_prompt.py -q
85 passed in 2.25s            ← rc=0，0 failed / 0 skipped
```

| 文件 | 现值 | 入库出处 |
|---|---|---|
| tests/test_apa7_gate_and_citation.py | 12 passed | `e20d1db`(9/11, ecdb 入库) |
| tests/test_literature_format.py | 5 passed | `08edad6`(9/5)，9/11 后**未再改动** |
| tests/test_literature_library_offline.py | 22 passed | `63d42fe`(9/22, s922-120)＋`d0142d4`(9/23, s923-32) |
| tests/test_literature_manager_expansion.py | 6 passed | `815ac64`(9/16, 916-04) |
| tests/test_literature_manager_network.py | 13 passed | `90b4d60`(9/19, s918-11) |
| tests/test_apa7_manual_string_pin.py | 7 passed | `1fb88e8`(9/19, s918-10) |
| tests/test_crawler_apa7_converge.py | 3 passed | `p911r-31`→`e20d1db` |
| tests/test_citation_in_text.py | 15 passed | `acd0b33`(9/5) |
| tests/test_lock_prompt.py | 2 passed | `e20d1db`(9/11, dab0) |
| **合计** | **85 passed / 0 skipped / 0 failed** | 逐件相加＝85，与合并跑一致 |

B-090/B-108 锁同源化的 9/11 基线子集（4acb 原文口径）另跑一次：

```
$ .venv/Scripts/python.exe -m pytest tests/test_instance_lock.py tests/test_project_manager.py tests/test_lock_prompt.py -q
28 passed in 3.76s        ← 与 done/20260911-053211-4acb.result.md 记的 "28 passed" 逐字相同
```

（该件起子进程持锁，但 `tests/test_instance_lock.py:39-40` 的 `lock_dir = tmp_path / "projects"` ⇒ 全程 tmp 沙盒，未碰生产 `data/`，见 §4。）

## 2. 判据② 差异归因

| # | 观测量 | 9/11 基线（档载） | 现值（实测） | 判定 | 归因 |
|---|---|---|---|---|---|
| 1 | ecdb 的格式子集 `apa7_gate + literature_format` | **17 passed（11＋6）** | **17 passed（12＋5）** | 总数**零漂移**，**枚次分配漂 +1/−1** | 见下方"记账差"一段 |
| 2 | 工具链覆盖面 | ecdb 时点 17 | **85** | ×5 扩容，零红 | 9/11–9/23 五次入库：`e20d1db`/`815ac64`/`1fb88e8`/`90b4d60`/`63d42fe`/`d0142d4` |
| 3 | B-090/B-108 锁子集 | 28 passed（4acb） | 28 passed | **零漂移** | — |
| 4 | tuple 路径是否仍走 `format_reference` | 收敛完成 | **仍收敛**：`src/paper_writer/literature_library.py:671-682` 现值 `return entry_obj.format_reference()`，改前的裸斜体 `f"{head} … *{source}*."` 在该文件 grep **0 命中** | **B-097 判据仍绿** | 未回退 |
| 5 | tuple 路径的钉测强度 | ecdb 新增 2 例 | `tests/test_apa7_gate_and_citation.py` 现**9 处**调用 `format_citation_apa7`（4 元/5 元两形态齐），含 `test_ecdb_publisher_present_goes_into_output:82`／`test_ecdb_publisher_absent_still_clean:88` | 仍被真钉，非只跑一次 | — |
| 6 | 锁文案同源面 | 面板＋项目横幅共用 formatter | `src/ui/literature_review_panel.py:84,92`、`src/ui/project_panel.py:25` 三处现值仍调 `locked_user_prompt` | 零漂移 | — |

**#1 的记账差（本班否证掉的一处锚点内部不一致）**：ecdb 档同一页写了"17 passed"又写了"11＋6"。git 实测两处都对不上入库版本：
`git show e20d1db^:tests/test_literature_format.py` 与 `git show HEAD:…` 均 **5 例**、`git diff e20d1db^ HEAD -- tests/test_literature_format.py` **空**（该件自 9/5 `08edad6` 未动一行）⇒ **档载的"6"在任何入库版本都复现不出来**；
`test_apa7_gate_and_citation.py` 在 `e20d1db` 由 10 例 → 12 例（＋2＝两条 `test_ecdb_publisher_*`），而档载跑法是 11。
⇒ 结论：差 1 全在 apa7_gate 侧，属**执行中态与入库态之间的记账漂移**（ecdb 明写"未 commit，改动留日间签核"），**不是用例丢失**：现值 17 例里 B1/B2/B3-B4/B5/B8/B11/normal＋2 条 publisher 全部在册可点名。本班不改档、不补数。

## 3. 本域新发现（测试面读数，交人工拍，本班未动一行）

### 3a. 🔴 一枚**未标记**的联网用例，且房的反选口径挡不住它

`tests/test_paper_writer.py::TestLiteratureManager::test_online_search_graceful`（`:65-68`）→
`src/paper_writer/literature_manager.py:1553-1560 search_online()` → `src/questionnaire/kb_search._search_crossref()`
＝**真打 CrossRef**，且该例**不带任何 pytest 标记**。实测：

```
$ .venv/Scripts/python.exe -m pytest tests/test_paper_writer.py --collect-only -q -m "not online"
…::test_online_search_graceful        ← 仍在收集清单里
```

⇒ 房内约定的 `-m "not online"`（见 `docs/history/ARCHITECTURE_PHASE1_PLAN.md:41`、`docs/history/COVERAGE_AUDIT.md:68` 的跑法）**排除不了它**：任何默认全量跑都会真打外网。
⚠️ 本班因卷宗"禁止联网"红线**未执行 `test_paper_writer.py` 一件**，所以这条**只是静态取证＋collect-only 佐证，没有真打**；也因此**没有**该件其它用例的现值（登记为口径缺口，交主班收班时决定是否补跑）。
修法＝给它补 `@pytest.mark.online`（或改 mock）＝改测试语义，超本班授权，交人工。

### 3b. `online` marker 只注册、无反选，注释与配置不符

`pytest.ini` 现值：`addopts = --strict-markers`（**无** `-m "not online"`）。而
`tests/test_literature_feed_fetchers.py:4` 自述"``@pytest.mark.online``，CI 默认排除"、
`tests/test_literature_search_async.py:6` 同形 ⇒ 默认跑法**并不排除**这两件（它们会真联网）。
本班未跑它们，故**无法给出其现值**；只登记"注释所述门禁在本仓当前配置下不存在"。
（注：改 `addopts` 属在途脏件 `pytest.ini` 的写域，见 s927-15，本班一行不碰。）

## 4. 判据③ 零码改动／零写库自证

- `git status --porcelain` 跑前跑后均**同一集合**（本班开工时 12 行，产物落盘后 13 行，唯一增量＝本班自己的 `?? docs/insights/s927-13-socratic-replay.md` 与本档）。
- `git diff --name-only HEAD -- tests/` 输出只有 `tests/test_cfa_sem_golden.py`（他班在途件）⇒ **本班 9＋3 枚在册件全部与 HEAD 逐字一致**，所引数字皆为入库版而非工作树版。
- 生产 `data/` 三层自证（`data/` 整层 gitignore ⇒ 无 git 还原点，故按 size＋mtime_ns 全树指纹对比，**不打开任何 sqlite**）：

```
跑测试前：187 个文件 / 21,103,172 B
跑测试后（文献子集后、锁子集后各取一次）：187 个文件 / 21,103,172 B，逐行 diff **0 差异**
快照：D:\code\tmp\qoder-executor-20260927-1930-psy78\data_before.txt / data_after.txt
```

- 未 add／commit／stash／restore／checkout／clean；未装依赖；未联网；未设任何模型 key。
- 在册红未触碰：`test_export_gate_global_scan::test_all_download_buttons_accounted_for` 不在本班任何一次跑法的文件清单内，输出中也未被带出（85／28 全 passed、0 skipped 可反证）。
- 本仓**无 `--freeze` 机制**（等价闸＝硬编码全等快照），本文"基线"一律指档载读数与 golden 文件，不涉及重钉动作。

## 5. 遗留（交人工／主班）

1. §3a 未标记联网例：补 `online` marker 或改 mock，二选一，均＝改测试语义＝人工闸。
2. §3b `online` 门禁在配置层不存在：要么把反选写进 `addopts`（碰在途脏件 `pytest.ini`，与 s927-15 交叉）、要么在跑法文档里把 `-m "not online"` 定为强制口径。本班未选案。
3. `test_paper_writer.py` 整件现值缺失（本班禁联网未跑）⇒ 文献链"全量口径"数字交主班收班时取。
4. ecdb 档载"11＋6"与入库版"10→12 ＋ 5"不符，只登记不订正（改的是别人的已入库 result，超授权）。
