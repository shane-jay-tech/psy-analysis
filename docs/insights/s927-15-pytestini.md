# s927-15 `pytest.ini` 在途修改对收集面的影响核查

> 班：`qoder-executor-20260927-1930-psy78`（波次 27，只读采集）· cwd `D:\code\psy-analysis` · 2026-09-27 19:2x
> 性质：**只读、零回退**。对 `pytest.ini` 一行未动；HEAD 态读数全部用命令行 `-o addopts=…` 覆盖取得（不落盘）。

## 1. 判据① diff 全文

```
$ git diff HEAD -- pytest.ini
diff --git a/pytest.ini b/pytest.ini
index 934df60..6391715 100644
--- a/pytest.ini
+++ b/pytest.ini
@@ -11,4 +11,4 @@ markers =
     online: 需要外部网络的测试（CrossRef等）
     benchmark: LLM-as-judge 漂移基准测试
 
-addopts = --strict-markers -q
+addopts = --strict-markers
```

| 面 | 现值（本班现取） |
|---|---|
| 改动量 | `git diff --numstat HEAD -- pytest.ini` = **1 / 1**（一行，唯一改动项） |
| 工作树文件 | 430 B，mtime `2026-09-26 11:47:36.311596200 +0800` |
| HEAD 版本 | 419 B（`git show HEAD:pytest.ini \| wc -c`） |
| 其余配置 | `testpaths = tests`、`python_files/python_functions`、5 枚 markers（integration/ui/e2e/playwright/online/benchmark）、`--strict-markers` **全部未变** |
| 唯一 addoption（码侧） | `tests/conftest.py:57-63` 的 `--run-benchmark`（本仓**无** `--freeze`，与 `s927-04:154` 一致） |

⇒ **配置项语义层面：只动 verbosity 默认级，未动 `testpaths` / marker 注册 / `--strict-markers` 任何一项。**

📌 出处与在途时长：这一行不是新改动，是 **9/14 缺陷单 `d914-22-psy-pytest-summary-swallow` 的修复**（`zcode-bridge/done/d914-22-psy-pytest-summary-swallow.result.md`，GLM-5.3-Flash，2026-09-14T04:15），至今 **13 天未入库**。⚠️ 一处需登记的矛盾：源单时点 9/14，而工作树 mtime 是 9/26 11:47 ⇒ 内容 diff 与源单描述**逐字一致**，但落笔时间比源单晚 12 天，说明中途有人重写过（或另班二次应用）。本班不追人，只登记。

## 2. 判据② 收集计数对比（先命令后数字）

解释器一律 `D:\code\psy-analysis\.venv\Scripts\python.exe`（Python 3.12.9 / pytest 9.1.1）。HEAD 态用 `-o "addopts=--strict-markers -q"` 命令行覆盖复现，**不改文件**。

### 2a. 集合本身：**零变化，且逐字节同集**

| 命令（唯一差异＝addopts） | 收集数 | 输出字节 |
|---|---|---|
| `… -m pytest --collect-only -q`（**在途态** addopts＝无 `-q`，verbosity −1） | **5526 tests collected in 9.11s** | 509,066 B |
| `… -m pytest --collect-only -o "addopts=--strict-markers -q"`（**HEAD 态**，命令行不加 `-q`，同样落在 verbosity −1） | **5526 tests collected in 8.49s** | 509,066 B |

同层级两枚 nodeid 清单排序后比对：

```
$ sort collect_worktree_q.txt | grep '::' > set_new.txt      # 5526 行
$ sort f1_heademu_bare.txt    | grep '::' > set_old.txt      # 5526 行
$ cmp -s set_old.txt set_new.txt && echo NODEID_SETS_IDENTICAL
NODEID_SETS_IDENTICAL
```

⇒ **收集面（集合与计数）完全不受这行影响**：5526 枚，两个配置下 `::` 行逐字节相同。跑法零红零 collection error（两态 rc 均 0）。

### 2b. 输出形状：**这才是这行真正改的东西**（同一命令，形态互换）

| 命令 | HEAD 态（addopts 含 `-q`） | 在途态（addopts 无 `-q`） |
|---|---|---|
| `--collect-only -q` | verbosity **−2**：逐文件计数 `tests/test_yaml_config.py: 5`，**无 nodeid、无 "N tests collected" 总数行**，11,752 B | verbosity −1：nodeid 清单＋总数行，509,066 B |
| `--collect-only`（裸） | verbosity −1：nodeid 清单＋总数行 | verbosity **0**：Module/Class/Function 树，`grep -c '::'` = **0**，394,527 B |
| `pytest <件> -q`（真跑） | verbosity −2：**81 B / 1 行，只有进度点，汇总行被吞**（实测 `rc=0` 但屏幕上查不到 `passed`） | verbosity −1：100 B / 2 行，`2 passed in 0.06s` 完整 |
| `pytest <件>`（裸跑真跑） | −1：100 B（有汇总） | 0：**416 B**（多 316 B 的 session header，同样有汇总） |

### 2c. 房内既有跑法的计数（在途态现取，供后续班直接引）

```
$ … pytest --collect-only -q -m "not online"                                        → 5496/5526 collected (30 deselected) in 9.30s
$ … pytest --collect-only -q -m "not online and not benchmark and not e2e and not playwright"
                                                                                    → 5469/5526 collected (57 deselected) in 9.18s
```

同一条命令在 HEAD 态下**取不到这两个总数行**（见 2b 第 1 行）——`psy-test-baseline-20260921.md:31-33` 早已实测到同一现象并写明"本班第一次副本跑动就因此拿不到汇总"，其绕过法正是本班用的 `-o addopts=`（同档 `:64`）。

## 3. 判据③ 意图与影响判定 ＋ 建议：**保留（不签回退）**

### 意图（源单结论，本班独立复现成立）
`addopts` 里的 `-q` 与命令行 `-q` **叠加成 `-qq`**，pytest 9.1.1 的 terminal reporter 在该冗余级别下抑制最终汇总行 ⇒ 所有"命令行自带 `-q`"的跑法（房内夜间班主流写法）拿不到 `N passed / M failed` 汇总，只能靠 rc。最小修复＝配置侧删掉那枚 `-q`。本班 2b 第 3 行（81 B 无汇总 ⇄ 100 B 有汇总）就是该现象的一次现场复现。

### 影响面复核（两处消费方，结论不同，别混）

| 消费方 | 命令形状 | HEAD 态 | 在途态 | 判定 |
|---|---|---|---|---|
| `scripts/release_gate.py:53-56 check_unit_tests()` | `pytest --ignore=… --tb=no`（**命令行不带 `-q`**） | −1，汇总在 | 0，汇总在 | **两态都不坏** ⇒ s927-08 的"不破坏门禁解析"复核为真 |
| `scripts/research_release_gate.py:57 pytest_cmd()` | `pytest -q --tb=no <files>`（**带 `-q`**；该件此刻是 `??` 未跟踪在途件） | −2 ⇒ **五环节每条子跑的汇总被吞**，取证只剩 rc 与进度点 | −1 ⇒ 汇总完整 | 🔴 **回退会削弱一枚在册门禁脚本的取证面** |

其余同向证据：`h912-06-psy-snapshot-b-20260912.md:40`（早已警告"叠加 `-q` 会合成 `-qq` 吞掉汇总行"）、`psy-e2e-skip26-roster-20260922.md:7`、`psy-untracked-tests-census-20260924.md:73`（两班都写"本班命令自带 `-q`，不受在途差异影响"——**该自述只在在途态成立**；若回退，它们全部变 `-qq`）。

### 代价（如实，且已量化）
裸跑变长：同一 2 例文件 **100 B → 416 B（×4.2，固定 316 B header）**；`--collect-only` 裸跑 394,527 B 树形输出。⇒ 夜间班的 token 成本按"裸跑次数 × 316 B ＋ 输出行数"上升。
缓解（零改动）：命令一律自带 `-q` ⇒ 落到 −1 级，正是"点号＋汇总行"的最省形状；要清单则 `--collect-only -q`。

### 建议（交人工拍，本班不执行）
1. **保留这行并提交，单列 chore 一笔**（与 s927-08 判定同向，但本班把它从"纯 verbosity、无害"升级为"**该留**"——理由＝上表第二行的在册依赖）。回滚成本：单行 revert，且**收集面零变化**（5526 同集）⇒ revert 不会改变任何覆盖面，只把汇总行重新吞掉。
2. 提交说明里必须一并写明两件事：① 房内所有"裸跑 pytest"的读数从此多一段 header；② 谁若将来想把 `-q` 加回 `addopts`，等价于把 `research_release_gate.py` 的五环节取证改回"只有 rc"。
3. ⚠️ **别把两件事混成一刀**：`s927-14 §3b` 提的"往 `addopts` 加 `-m "not online`"会**真的改变收集集合**（5526 → **5496**，见 2c），与本单的"零集合影响"完全不同性质 ⇒ 那一刀必须单独走人工闸，不能搭这行提交。

## 4. 判据④ 零回退／零写自证

- `pytest.ini` 本班**只读**：跑完再取 `ls -la --time-style=full-iso pytest.ini` 仍是 `430 B / 2026-09-26 11:47:36.311596200`，`git diff --numstat HEAD -- pytest.ini` 仍是 `1 1`；未 restore／checkout／edit／stash。
- HEAD 态一律用命令行 `-o "addopts=…"` 复现（pytest 的 ini override，不落盘）。实测该法**确实生效**：`--collect-only -q -o "addopts=--strict-markers -q"` 与 `--collect-only -qq -o "addopts=--strict-markers"` 输出逐字节同（均 11,752 B、同为 `file: N` 形态）⇒ 覆盖通道可用，比对结论不依赖"假设它生效"。
- `git status --porcelain` 从 12 行增至 14 行，增量＝本班两枚产物（`s927-13-socratic-replay.md`／`s927-14-literature-regression.md`），无其它新增脏件。
- 生产 `data/` 全树（含 `literature_feed/feed.sqlite` 与其 `-wal`/`-shm` 侧车）**零写**：187 文件 / 21,103,172 B，跑全部 collect 与 4 次微型跑测试前后 `cmp -s` = **IDENTICAL**（快照 `D:\code\tmp\qoder-executor-20260927-1930-psy78\data_before.txt` / `data_after_collect.txt`）。本班只 `os.stat` 遍历，**未打开任何 sqlite**。
  ⚠️ 顺带登记（非本班所致）：`feed.sqlite-shm` mtime 为 `2026-09-27 09:30:01`、大小 32,768 B 不变——早于本班窗口 10 小时，符合"`mode=ro` 打开也会刷 `-shm` mtime 而不写库"的已知机理，**不得当作写库证据**。
- 并发保护：**未跑全量测试**，只有 `--collect-only`（导入期动作，实测 8.5–9.3s/次）与 `tests/test_lock_prompt.py`（2 例）4 次微型跑；取 rc 用 `PIPESTATUS[0]`；psy 侧带 `PYTHONIOENCODING=utf-8`。
- 在册红：`test_export_gate_global_scan::test_all_download_buttons_accounted_for`（offender `questionnaire_panel.py`）本班**未执行**任何测试文件集合外的跑动，`--collect-only` 仅收集不执行故不产出红／绿；未消、未归因、未加白名单。

## 5. 引用本档时必须同时标的口径

- **5526 ＝ `.venv` 解释器口径的收集面**。🔴 本仓 `.venv` 与全局 python 的包集不同（`s927-12-deps-consistency.md` 实测：一侧有包另一侧 MISSING；`requirements-lock.txt` 那 6 行在途改动值 100% 取自**全局**解释器、对 `.venv` 仍 4 处不符，含 numpy 锁定 2.3.5 ⇄ 实装 2.5.1）。⇒ 换解释器收集数可能因 collection error 而变小，**引这个数不标解释器＝无效读数**。本班未测全局侧（不越权、不装依赖），只点名该风险。
- 本仓**无 `--freeze`**：本文所有"基线"指档载读数与配置现值，不存在"重钉基线"这扇门。
