# s927-08 — psy 脏树收口审计：12 枚在途件归属与提交清单（只读·零 git 操作）

- 班次：`qoder-executor-20260927-1850-psy77`｜波次 24｜cwd `D:\code\psy-analysis`
- 取证时点：`date` = 2026-09-27 18:32:43 +0800（开工）→ 18:38:54 +0800（收笔前）
- HEAD 现值：`c7b8623`（`git rev-parse --short HEAD`）
- 交付物性质：只出归类与清单；**本班未执行任何 git 写操作、未改任何在册代码件**（判据④自证见 §6）

## 0. 锚点复核（三处漂移，一律按磁盘实况修正并留痕）

| # | 卷宗／简报口径 | 磁盘现值 | 处置 |
|---|---|---|---|
| A1 | 背景锚点「8 修改件 + 3 未跟踪件＝11 件」 | `git status --porcelain` = **12 行＝8 ` M` + 4 `??`**；多出的第 4 枚未跟踪件是 `docs/insights/s924-36-a1-backport-draft-20260925.md`（前案交付物，未登记进本卷宗） | 按 12 件逐件归类，不裁表 |
| A2 | 派单横幅「那 15 枚 ` M` 在途件」 | ` M` 实测 **8 枚** | 本班无法复现 15 这一读数，按磁盘报；归因不判 |
| A3 | 简报 §5「psy HEAD `11e536d`／porcelain 12」 | HEAD 已到 `c7b8623`（其间 5 枚均为 `docs(psy): s927-02…06` 提交），porcelain 仍 12 行 | 只认磁盘（简报 §0） |
| A4 | 「触发 `--freeze` 重钉基线」类口径 | `git grep -in freeze -- '*.py'` → **0 命中**（本班复点，与 psy76 结论一致） | 本档不引该机制；等价闸＝硬编码全等快照 |
| A5 | `s924-36` 草案（09-26 00:12）自述「app.py mtime 09-22 04:29」 | `app.py` mtime 现值 **2026-09-26 11:47:36** | 该草案写完后 app.py 又被整批触碰过（见 §1 注①） |

## 1. 逐件归类表（判据①，12/12）

| # | 路径 | 体量 | mtime | diff 摘要 | 判定 | 依据／风险 |
|---|---|---|---|---|---|---|
| 1 | `app.py` | 130,298 B | 09-26 11:47:36 | 52 行：启动清理／环境自检／重依赖预热三块内联逻辑改调 `src/ui/startup_checks.py`＋`src/ui/heavy_preload.py`（**两枚依赖均已跟踪且在册**，41／33 行），另补 d914-23 autosave 单点注释 | **应提交**（独立成组） | 行为声称零变更；`threading` 仍在 :9 导入并被 :1657 使用 ⇒ 无死导入。归属：d913a-43 拆分＋d914-23 注释两案混在一枚文件里，提交说明需并列点名 |
| 2 | `pytest.ini` | 430 B | 09-26 11:47:36 | 1 行：`addopts = --strict-markers -q` → 去掉 `-q` | **应提交（单列 chore）** | 纯 verbosity；`scripts/release_gate.py:39 _pytest_summary` 逆序扫 `passed|failed` 关键词，两种输出都取得到 ⇒ 不破坏门禁解析。副作用：夜间单每次裸跑 pytest 输出变长（token 成本），建议提交说明里写明取舍 |
| 3 | `requirements-lock.txt` | 955 B | 09-26 11:47:36 | 6 枚版本漂移：streamlit 1.57.0→1.58.0、numpy **2.4.4→2.3.5（降）**、scipy 1.17.1→1.18.0、plotly 6.7.0→6.8.0、pyreadstat 1.3.4→1.3.5、openai 2.36.0→2.44.0 | **暂不提交，先补一致性问题**（详见 `s927-12-deps-consistency.md`） | 改后仍与 `.venv` 实测不符（streamlit 1.59.1／numpy 2.5.1／plotly 6.9.0／openai 2.45.0），且 numpy 由「比实装低 0.1」改成「低 0.2」⇒ 该锁既非 `pip freeze` 产物也未验证可用；文件头「最后更新：2026-07-02」也未随改 |
| 4 | `src/analysis/__init__.py` | 598 B | 09-26 11:47:36 | 空文件 → 14 行包文档＋`try: from . import _sklearn_compat; _compat.install() except Exception: pass` | **应提交，但注释口径须先纠**（与 #11 同批） | 注释断言「本机 scikit-learn 已把 `check_array(force_all_finite=…)` 改名为 `ensure_all_finite`」——对 `.venv`（sklearn 1.5.2）**不成立**，见 §2.2 实测否证；且整块被 `except: pass` 包死 ⇒ 真坏不会红 |
| 5 | `src/analysis/cfa.py` | 30,684 B | 09-26 11:47:36 | 218 行（P16 取证修复）：默认估计量 `ML`→`MLW`＋`ML→MLW` 别名映射与告警、新增 `_stat_scalar`／`_round_or_nan`／`_resolve_objective`、`_assess_fit` 改标量取值并对越界指标判不通过、载荷表算符兼容 `=~`／`~` 方向区分、失败不再静默（写进 `warnings`）、新增字段 `requested_estimator`／`converged`、新常量 `FIT_RANGE_TOLERANCE = 1e-3` | 🔴 **人工放行后才可提交**（本班不签） | 命中统计红线域：改的是**拟合判据与阈值边界**（越界即判「未通过」）＋默认估计量语义（MLW 是 semopy 的 Wishart 形式 ML，非等价改名）。可复算入口：`tests/test_cfa_sem_golden.py`（19 passed，§3）。数值面本班未取用 |
| 6 | `src/analysis/result_card.py` | 75,705 B | 09-26 11:47:36 | 193 行：效应量补 95% CI 上卡（Cohen's d / η² / r）、新增 `_cohen_d_magnitude`、新增 `_build_corr_matrix_card` 逐对相关卡（Pearson／Spearman 分支前置）、APA 文案主谓纠偏（「X 对 Y 的影响」→「按 X 分组的两组在 Y 上的差异」）、Welch／配对 n／成对删除 n 的 `technical_notes` | 🔴 **人工放行后才可提交**（本班不签），但**结构面可先验** | 引用面已核：`effect_size_ci.fisher_z_ci`（tracked，返回二元组）、`ttest.effect_size_ci_lower/upper`、`correlation.corr_matrix/p_matrix/ci_low_matrix/n_matrix` **全部在册存在** ⇒ 无悬空属性。风险：Cohen 1988 分级（0.2/0.5/0.8、η² 0.01/0.06/0.14、\|r\| 0.1/0.3/0.5）与 p<0.05 措辞属**阈值文案**，是否入库要人拍。44 键快照闸 23 passed（§3） |
| 7 | `src/output/interpretation.py` | 29,087 B | 09-26 11:47:36 | 2 hunk／各 1 行：配对 t 结论文案去「处理后」改「第二次测量（相对第一次测量）」；Cohen's d 大效应句尾把「差异具有明显的实际意义」改成「通常对应较大的实际效应；实际意义仍需结合领域背景判断」 | **本班不裁决去留**（禁动件） | 波次 18 起在册禁动件（本派单横幅第 5 条）。本班仅读 diff 以完成归类，未做任何触碰；两条均为**效应量解释口径**，同样落人工闸 |
| 8 | `tests/test_cfa_sem_golden.py` | 19,065 B | 09-26 11:47:36 | 108 行：把「semopy 拟合必失败→指标全 0／loadings 恒 None／恰好 1 条拟合失败告警」的旧钉桩，改钉修复后现状（`estimator=="MLW"`、`converged is None`、`chi2>0`、载荷 12 行、越界判不通过），带宽仍全部读 `cfa_expected.json` | **应随 #5 同批提交**（含 1 处 cosmetic 前置修正） | 与 #5 是同一因果对，**不可拆开提交**（拆了必红）。在册缺陷：`:250` 与 `:251` 是**逐字重复的两行同一 import**（`from src.analysis.cfa import confirmatory_factor_analysis`），无害但应删一行；本班未动。口径前提「不调阈值、不发明数字」在 diff 内自查通过 |
| 9 | `node_modules/` | 1 枚文件 91 B | 09-19 04:14 | 仅 `node_modules/.vite/vitest/da39a3ee…/results.json`；**仓内无 `package.json`／`package-lock.json`**（`git ls-files` 0 命中） | 🔴 **应 gitignore**（不是「可忽略」，是必须） | 纯 vite/vitest 缓存落点，`.gitignore` 现 45 行无 `node_modules/` ⇒ `git check-ignore` rc=1（未被忽略）。建议 `.gitignore` 增 `node_modules/` 与 `**/.vite/`；**禁按路径 add 其内容**，也禁在无人认领前删除（唯一残留物，删了只是丢缓存） |
| 10 | `scripts/research_release_gate.py` | 5,341 B／141 行 | 09-26 11:52:00 | 全新：五环节（数据来源→统计→图表→主张→匿名化）**三态**门禁 pass/fail/blocked，统计结论**必须 `--confirm-review 姓名` 人工签收才 pass**，逐环节命令＋退出码＋输出尾部落 `tmp/gate-evidence/<时间戳>/<环节>.json` | **应提交（附两条前置）** | 功能定位与测试现状见 §2.1。前置：① 与在册 `scripts/release_gate.py`（307 行，二态）的并存关系要人拍（并轨／分名／谁作交付闸）；② 本脚本**不是只读探针**（开生产库＋写证据目录＋连跑 9 枚测试），本班**一次都没执行** |
| 11 | `src/analysis/_sklearn_compat.py` | 3,249 B／89 行 | 09-25 17:06:43 | 全新：`install()`／`uninstall()` 幂等垫片，`inspect.signature` 探测旧参数名，仅在目标函数**不接受** `force_all_finite` 时才 `functools.wraps` 转发到 `ensure_all_finite`（新名优先），不改数值语义 | **应提交为「前向兼容保险」，但注释须改口径 + 需补一枚最小测试** | §2.2 实测：在 `.venv` 下 `install()` 返回 **False**、`_PATCHED` False ⇒ 当前完全不生效；问题现场在**系统 python（sklearn 1.9.1）**。与 `run_daily_feed.bat:24-27`（s923-11）已选的「钉解释器到 .venv」处置方向相反 ⇒ 两条互斥口径并存，交人裁决 |
| 12 | `docs/insights/s924-36-a1-backport-draft-20260925.md` | 4,352 B／59 行 | 09-26 00:12 | 未跟踪新档：app.py 计时面回流草案（案 A1，6 hunk），正文自证「本档＋`tmp/s924-36-a1-backport.patch` 即全部交付物」 | **应提交**（前案唯一交付物，不提交即丢） | 属 docs 位、零代码风险。注意：正文引用的 `tmp/s924-36-a1-backport.patch` 在 `tmp/`（gitignore）⇒ 提交后档内该指针在仓外，需人确认是否把 patch 一并落 `docs/` 或 `scripts/`；本班未检查其是否仍在世（不在本单范围） |

注①（批量触点）：8 枚 ` M` 的 mtime 全落在 **09-26 11:47:36**（.311／.327 两簇），`research_release_gate.py` 在 11:52:00 ⇒ 存在一次跨 8 件的整批写。**mtime 因此不能用来区分各件作者**，只能证明「09-26 11:47 这批被一起碰过」；#11／#12 的时间戳（09-25 17:06／09-26 00:12）在该批之前，属另两次会话。

## 2. 两枚未跟踪件的功能定位与测试现状（卷宗「做什么」点名项）

### 2.1 `scripts/research_release_gate.py`

- **定位**：与 `release_gate.py` 的差别在它自己 docstring 里写了两条（三态 + 证据落盘），实测相符：
  - 三态判定（`:116-136`）：任一环节 FAIL → 退出码 1；全绿但无 `--confirm-review` → **BLOCKED／退出码 2**；全绿且有人签收 → PASS／0，并把 `{"reviewer","at"}` 写进 `HUMAN_REVIEW.json`。
  - ⚠ 一处**语义缝隙**（值得提交前定口径）：`HUMAN_REVIEW.json` 只在 PASS 分支写；`--fail-probe` 与「环节失败」时签收记录不落盘 ⇒ 「先签收后修好」的复跑顺序无法留痕。本班不改。
- **在册引用**：`git grep -rn research_release_gate` 全域命中只有 ①自身用法注释 3 行 ②`docs/insights/s927-03-star-caliber.md:248/:266`、`s927-04-n-and-ci-design.md:155/:179`（均为**引述**，其中 `:266` 还专门否证过一串把 `--freeze`/`correlation` 记到该件的错误读数）。⇒ **门禁本体零测试覆盖**，且它自己点名的 9 枚测试全部在世：
  `test_golden_stats_v2.py`(17,583 B)、`test_effect_size_ci.py`(3,849)、`test_golden_delivery.py`(5,847)、`test_visualization_charts.py`(4,059)、`test_apa_figures_v2.py`(12,360)、`test_figure_collection.py`(4,510)、`test_evidence_quality.py`(4,460)、`test_guardrails_pii.py`(4,504)、`test_guardrails_pii_probes.py`(22,206)。
- **运行副作用（本班未执行，逐条为静态读码所得）**：
  1. `:44-53` `check_data_sources()` 以 `file:…?mode=ro` 打开**生产库** `data/literature_feed/feed.sqlite` 跑 `pragma integrity_check` + `select count(*) from sources`。按波次 24 已定机理，WAL 库上 `mode=ro` 仍会回写 `-shm` 头，而 `data/` 整层 gitignore ⇒ **无还原点**。⇒ 该脚本不可在并发窗当「只读探测」用。
  2. `:87-89` 写 `tmp/gate-evidence/<stamp>/`（`tmp/` 已 gitignore，可接受，但会无界堆积）。
  3. `:56-57` 拼 `pytest -q --tb=no <files>`，一次跑满 9 枚文件 ⇒ 并发窗内等同半量级套件。
- **归类倾向**：功能面是有价值的发布闸（三态＝把「统计结论须人签」编码进了退出码，与本次波次的红线同构），**建议提交**；但「是否取代 `release_gate.py`」与「是否在 `run_daily_feed.bat`／计划任务里挂上」两项属排定任务变更＝人工闸，本班只列不改。

### 2.2 `src/analysis/_sklearn_compat.py`（含 `src/analysis/__init__.py` 的挂钩）

- **定位**：把 sklearn ≥1.6 的 `check_array(ensure_all_finite=…)` 改名，向前兼容仍按旧名调用的 `factor_analyzer`；只做参数改名转发，不碰数值。设计约束写得很克制（signature 探测／`functools.wraps`／新名优先／可 `uninstall()`）。
- 🔴 **实测否证其「本机」前提**（`.venv` 是 psy 唯一授权解释器，brief §6）：
  - `.venv` `scikit-learn == 1.5.2`；`inspect.signature(check_array)` 参数表含 `force_all_finite`、**无** `ensure_all_finite`、**无 `**kwargs`** ⇒ `_supports_legacy_kwarg()` 判 True ⇒ **`install()` 实测返回 False、`_PATCHED` 保持 False、`check_array` 未被 wrap**。
  - 对照：**系统 python** `scikit-learn == 1.9.1`，同一签名探测给出 `force_all_finite: False | ensure_all_finite: True` ⇒ 垫片描述的断裂现场**只在系统解释器成立**。
  - 结论：这不是「垫片写坏」，而是**它治的病不在被指派的解释器里**；`__init__.py` 的注释把「全局 PATH 解释器」写成「本机」，会把下一班引向错误因果。
- **与在册既有处置冲突**：`scripts/run_daily_feed.bat:24-27`（s923-11，2026-09-23）已记录同一事实并选了相反处方——「pin the interpreter to THIS repo's .venv …(sklearn 1.5.2 in .venv vs 1.9.1 globally)」。⇒ 现在仓内并存两种口径：**改解释器**（已入库）vs **改 API 名转发**（未跟踪在途）。交人裁决：留一套，或明写「垫片只服务非 .venv 的误跑路径」并把它标注为诊断件而非修复件。
- **测试现状**：`grep` 全域（排 `.venv`/`node_modules`）无任何测试引用 `_sklearn_compat`／`force_all_finite`／`ensure_all_finite`；`tests/` 里 `factor_analyzer` 仅出现在 `conftest.py:6/:103/:108`（filterwarnings 的第三方归因白名单）与 `test_heavy_preload.py`／`test_env_check.py`（依赖名清单）。⇒ 该垫片**无 install/uninstall 断言、无幂等断言**，且挂钩整体被 `except Exception: pass` 吞掉 ⇒ 它失效时测试仍全绿（「绿但零覆盖」的又一形态）。
- **归类倾向**：可提交，但**前置两件事**（改注释口径 + 补 ≥1 枚「在 1.5.2 上 install() 返回 False / 在 ≥1.6 上正确转发」的可复算用例）；否则就是把一条被磁盘否证的因果叙述钉进包导入链。

## 3. pytest 现值（判据②：定向，未跑全量）

解释器一律 `D:\code\psy-analysis\.venv\Scripts\python.exe`，一律带 `-p no:cacheprovider`（不落 `.pytest_cache`）。

| 命令（省略公共前缀 `.venv/Scripts/python.exe -m pytest`） | 结果 | 用时 |
|---|---|---|
| `tests/test_cfa_sem_golden.py -p no:cacheprovider --tb=short` | **19 passed**（脏 #5＋#8 自洽；rc=0） | 2.93 s |
| `tests/test_result_card_registry_snapshot.py -p no:cacheprovider --tb=line` | **23 passed**（44 键全等快照闸未被 #6 触发） | 1.62 s |
| `tests/test_analysis_result_card.py tests/test_result_card_runner_contract.py tests/test_effect_size_ci.py -p no:cacheprovider --tb=line` | **37 passed** | 1.91 s |
| 合计 | **79 passed / 0 failed / 0 error**（4 枚在册件，12/12 件均已归类） | ≈6.5 s |

- **未跑全量**（并发窗纪律）。在册红 `test_export_gate_global_scan::test_all_download_buttons_accounted_for`（psy76 一手：现仍 1 failed，offender `questionnaire_panel.py`）**本班未复跑、未触碰、未挂白名单**；本班三组定向均未与之相交，故未被其挡住。
- **零写副作用自证**（跑前／跑后各取一次，均不回滚）：`data/` **浅层（`-maxdepth 2`）13 枚**文件 size+mtime 逐项相等——`feed.sqlite 499,712 B @09-23 12:15:30`、`feed.sqlite-wal 741,632 B @09-23 12:16:18`、`feed.sqlite-shm 32,768 B @09-27 09:30:01`（本班开窗前已是此值，跑后未变）、`perf_history.jsonl 1,528 B @08-24`；**全树复核**（`.venv` `pathlib.rglob`）＝ **187 枚／21,103,172 B**，与在册基线读数逐位相符，且**全树最大 mtime 仍是 `feed.sqlite-shm @09-27 09:30:01`**（早于本班开窗）⇒ 187 枚无一枚被本班触碰；`logs/` 最新仍是 `usage_events_20260925.jsonl`；`git status --porcelain` 跑前／跑后同为 **12 行**、无新增条目。

## 4. 提交清单（判据③：精确路径，交主班或人工执行；本班零执行）

顺序即建议提交顺序；🔴 者须人工放行后才动手。

1. **C1 `chore(gitignore)`** — 写位：`.gitignore`（新增两行 `node_modules/`、`**/.vite/`）。效果：#9 从 porcelain 消失。**不 add #9 内容、不删目录**。
2. **C2 `docs(insights)`** — 精确路径：`docs/insights/s924-36-a1-backport-draft-20260925.md`（#12）＋本档 `docs/insights/s927-08-dirty-audit.md`＋`docs/insights/s927-09-knownissues-health.md`＋`docs/insights/s927-12-deps-consistency.md`（本班三件产物）。
3. **C3 `refactor(app)`** — 精确路径：`app.py`（#1）。依赖 `src/ui/startup_checks.py`／`src/ui/heavy_preload.py` 均在册 ⇒ 可独立提交。
4. **C4 `chore(pytest)`** — 精确路径：`pytest.ini`（#2）。
5. 🔴 **C5 `fix(cfa)`（人工闸）** — 精确路径：`src/analysis/cfa.py`＋`tests/test_cfa_sem_golden.py`（#5＋#8，**成对，不可拆**）。前置：① 人工对「默认估计量 ML→MLW」「越界指标判不通过」「`FIT_RANGE_TOLERANCE=1e-3`」三处判据签认；② 删 `tests/test_cfa_sem_golden.py:250-251` 重复 import 之一（cosmetic）。
6. 🔴 **C6 `feat(result_card)`（人工闸）** — 精确路径：`src/analysis/result_card.py`（#6）。前置：效应量 CI 与 Cohen/η²/\|r\| 分级文案是否入库由人拍；`tests/test_result_card_registry_snapshot.py` 23 passed 只证明**键面未变**，不背书文案数值。
7. **C7 `chore(compat)`（建议拆两枚）** — 精确路径：`src/analysis/_sklearn_compat.py`（#11）＋`src/analysis/__init__.py`（#4）。前置（§2.2）：改注释口径（「本机」→「≥1.6 / 非 .venv 解释器」）、与 `run_daily_feed.bat:24-27` 的「钉解释器」处置择一、补最小用例。**未满足前置则本组整体挂起**，不要为清 porcelain 而先提交。
8. **C8 `feat(gate)`** — 精确路径：`scripts/research_release_gate.py`（#10）。前置：与 `scripts/release_gate.py` 的并存关系拍定；**不得**把它登记成只读探针。
9. 🔴 **C9（人工裁决，本班不建议提交现状版）** — 精确路径：`requirements-lock.txt`（#3）。见 §1#3 与 `s927-12`。
10. **不列入任何提交组**：`src/output/interpretation.py`（#7，禁动件，去留由主班／人工按波次 18 口径裁决）。

**「应回退」栏：一件都不成立**。12 件里没有任何一枚带「与本仓在册档冲突到必须丢弃」的证据；最低成本的搁置方式是 #3/#4/#11 三件**不提交也不回退、继续挂工作树**（`requirements-lock.txt` 是 12 行纯文本、shim 是未跟踪单文件，回滚成本近零，但回退同样是写动作 ⇒ 仍归主班）。

## 5. 本班新发现（提交前值得人看一眼，均为只读所得）

1. **垫片治错解释器**（§2.2，实测定量）：`.venv` sklearn 1.5.2 上 `install()` 返回 False；1.9.1 只在系统 python 里。
2. **`__init__.py` 挂钩全包 `except: pass`** ⇒ 兼容层失效不可能变红（在册测试零覆盖，「绿但零覆盖」新形态）。
3. **`tests/test_cfa_sem_golden.py:250/251` 逐字重复 import**（提交前删一行）。
4. **`research_release_gate.py` 的签收记录只在 PASS 分支落盘**（`:116-136`）⇒ 失败态无签收留痕，且 `tmp/gate-evidence/` 无界堆积。
5. **mtime 同瞬批量**（8 枚 ` M` 全为 09-26 11:47:36）⇒ 用 mtime 反推「哪件属于哪一案」在本仓不成立；本档的归属全部靠 diff 内的案号自述（d913a-43／d914-23／P16／s924-12／s923-11）。
6. **本仓 `--freeze` 0 命中**（§0 A4）⇒ 提交说明与后续 KNOWN_ISSUES 回写都不该再引「重钉基线」。

## 6. 零 git 操作自证（判据④）

- 本班用过的 git 命令**全部只读**：`rev-parse`／`status --porcelain`（含 `-uall -- node_modules`）／`diff`（逐件与 `--stat`）／`show HEAD:<file>`／`ls-files`／`grep`／`check-ignore -v`／`log --oneline`。
- **未执行**：`git add`／`commit`／`stash`／`checkout`／`restore`／`clean`／`push`／任何 `--freeze` 类基线动作，也**未尝试**（故无「被权限门拦下」记录）。
- 写位只有两处：`docs/insights/s927-08-dirty-audit.md`（本档，卷宗点名产物）与沙盒 `D:\code\tmp\qoder-executor-20260927-1850-psy77\`（探针脚本，见 §7）。工作树 12 枚在途件**逐件字节数／mtime 未变**（§3 表后自证）。
- `src/output/interpretation.py` 与 8 枚 ` M`：仅 `git diff` 读取，未写入、未 add、未判去留（#7 明列「不提交组」）。

## 7. 复算入口（本班留档，故不清理）

- 沙盒 `D:\code\tmp\qoder-executor-20260927-1850-psy77\sk_probe.py`：一次输出两枚解释器的 `check_array` 签名与垫片状态，即 §2.2 全部读数。**须以 `.venv` 解释器起脚本**（脚本自己再分头调全局 `D:\Program\python.exe`；用 `sys.executable` 当"系统 python"会得到 .venv 自己——本班第一次就踩了）。子进程显式 `encoding='utf-8'`、标签全 ASCII（GBK 控制台下中文标签会变乱码，读数虽不错但不可核对）。18:4x 实跑 rc=0，输出与该班结论逐行一致。
- pytest 读数复算：§3 表内三条命令原样可跑，总用时 <10 s。
- data/ 无写主证复算：`stat -c "%n %s %y" data/literature_feed/feed.sqlite*` 与 §3 数值对比。
- ⚠ 前手三座沙盒 `tmp/qoder-executor-20260927-1400-psy74/`、`-1430-psy75/`、`-1820-psy76/` 本班未触碰（被 s927-02…06 点名为复算入口）。

## 8. 本班未做／交出去的事

- 未裁决 `interpretation.py` 去留（禁动件）；未消在册红（超授权）；未改 `requirements-lock.txt` 或任何计算码／快照／期望数据；未拍任何统计数值或阈值（#5/#6/#7 全部标人工闸）。
- `#12` 里指针 `tmp/s924-36-a1-backport.patch` 是否仍在世：未查（不在本单范围）。
- `research_release_gate.py` 是否在计划任务／`run_daily_feed.bat` 里挂上：未查未改（改计划任务＝人工闸）。
