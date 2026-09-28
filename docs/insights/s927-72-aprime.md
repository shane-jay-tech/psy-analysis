# s927-72 · A′ 哨兵的调用方识别（design_engine 出口形态收口）

- 班：`qoder-executor-20260929-0415-psy101`（写位路），日期 2026-09-29，盘面 HEAD 实测 `73ed50f`。
- 卷宗：`zcode-bridge/inbox/s927-72.task.md`（正文「按 A′（solved 哨兵）落地：实现哨兵值返回＋调用方识别，补 3 例」）。
- 上游：`done/s923-03.result.md`（三案判决设计稿）→ 出口 A′ 由 `2f08c60`（s924-04）落了**哨兵本体**。
- 本单补的是**台账 215① 点名的那一格**：`docs/insights/drain-20260923-pending-human.md` 第 215 行①——
  「`design_engine.py:159` 在 `solved=False` 时仍把 `n_subjects=0` 往下送 ⇒ medium 效应的设计稿会写"每组 0 人"
  （改前是"每组 4000 人"的假数，A′ 只是把假数换成显式拒答，**不是本批新引入**，但"0 人"同样不可用）；
  **engine 侧必须读 `solved` 改为不出数** ⇒ 另单」。
- 红线自证：本单**只改出口形态与调用方取数**，未动任何公式、求解调用、阈值或区间；
  效应量／p 值／样本量的**数值判定一律不签**（数值断言全部用「引擎字段 == 同一真实求解器返回字段」的同源比较）。

## 1 哨兵本体早在 HEAD，缺的只是调用方（实测）

```
$ git --no-pager log --oneline -2 -- src/analysis/post_hoc_power.py
2f08c60 feat(psy): s924-04＋s924-16 两单同归本笔（power 求解 A′ 拒答口径落地 ＋ feed TTL 口径普查）
$ grep -n "solved" src/experiment_design/power_analysis.py | head -3
35:    solved: bool = True                 # False ⇒ 本结果是未解哨兵，数值字段不可引用
```
`src/analysis/post_hoc_power.py` 的调用侧已闭合（`:307` 先查 `res_080.solved` 才走 `:314` 的
`int(res_080.required_n)`）⇒ **本单对它零改动**。唯一没读哨兵的调用方是 `design_engine.py`。

## 2 改前实测：一个假数从引擎流到五张出口（HEAD 版直出，可复算）

探针 `tmp/s927-72/probe_head_baseline.py` 用 `git show HEAD:src/experiment_design/design_engine.py`
取出的 HEAD 副本（`tmp/s927-72/head_design_engine.py`）跑默认 medium（d=0.5，被试间模板）：

```
== HEAD 版 design_engine（改动前）实测读数，d=0.5 medium 默认路径
power_result.solved = False
n_subjects / n_per_group / n_groups = 0 0 2
报告样本量行 = ['**计划样本量：** N = 0']
报告分组行   = ['**分组：** 共2组，每组0人']
随机化描述   = 将被试随机分配至2个实验条件，每组0人（剩余0人随机分配）。使用随机数生成器确保分配的无偏性。
预算被试费行 = ['| 被试费 | 30元/人 | 0人 | 0元 |']
含『效力分析完成』的日志 = ['效力分析完成: N=0, 效力=nan']
泄漏点计数 = 5
```
⇒ 台账记的是「报告那一格」，实测泄漏面是 **5 格**：报告样本量行、报告分组行、程序随机化文案、
预算费用表、引擎日志（`效力分析完成: N=0, 效力=nan` 是一句**假完成宣告**，比"0 人"更值得记）。
默认路径就中招：`effect_size_expected` 的缺省值是 `"medium"`（`:91`）⇒ 不传参的用户拿到的设计稿
写的就是「N = 0／每组 0 人」。

## 3 改动（只一个文件，四处出口 + 一个状态字段）

`src/experiment_design/design_engine.py`：

| 位置 | 改动 | 性质 |
|---|---|---|
| `ExperimentDesign` 字段表 | 新增 `power_solved: bool = True`、`power_failure_reason: str = ""` | 调用方状态记账（默认值保证旧构造点零改动） |
| 效力分析取数处（HEAD `:156-162`） | 读 `power_result.solved`：真才取 `required_n`/`required_per_group`；假则置 0 并记 `power_solved=False`，日志改「效力分析未求解」 | 取数口径 |
| 程序出口（build_full_procedure 之后） | 新增 `_suppress_unsolved_subject_counts()`：只替换 `randomization` 的 `description`/`note` 文案并钉空 `assignments`，`method`／拉丁方等非数值字段原样保留 | 出口形态 |
| 报告出口 `format_design_report` | 样本量行/分组行按 `power_solved` 分流，未解时写「未给出 ⛔ …A′ 拒答」＋透出诊断文本 | 出口形态 |
| 预算出口 `_estimate_budget` | 未解时整表不出（新增 `_budget_refusal()`），改判为「无法估算」 | 出口形态 |

刻意**保留**的两条：
- `n_groups` 在哨兵态仍照取（`power_result.n_groups=2`）——它是模板决定的**设计结构**，不是求解产物；
  置 0 会把 `tests/test_experiment_design_ui_detail_branch.py:435` 的 `d.n_groups > 1` 夹具钉桩打红。
- `n_subjects`/`n_per_group` 仍为 int 0（不改成 `None`）——`procedure_builder.py:198` 的
  `n_subjects // n_conditions` 与 UI 侧算术会当场 TypeError；拒答靠 `power_solved` 分流，不靠类型游戏。

## 4 补的三例（欠解／无解/正常解）＋一条回归对照

新增 `tests/test_design_engine_aprime_caller.py`（纯新文件，未碰任何在册钉桩件）：

| 例 | 真实求解器状态（实测 failure_reason） | 引擎出口断言 |
|---|---|---|
| 正常解 | d=0.2 独立 t ⇒ `solved=True`，`required_n=788`／每组 394 | 报告出 `N = 788`、分组行在场、随机化含「每组394人」、预算表在场；引擎字段与 `PowerResult` 字段**同源相等** |
| 无解（求解器不可解） | d=0.8 ⇒ `solved=False`，「数值求解失败（迭代进入 NaN 发散区，scipy 非中心 t 已知数值不稳定）」 | 报告无 `N = 0`／无「每组0人」，拒答文案＋诊断透出；随机化文案不含「每组0人」且 `method` 未被清空；预算无被试费行；日志不再出现「效力分析完成」 |
| 欠解（区间内无变号点） | d=0.05 ⇒ `solved=False`，「目标样本量超出搜索区间上界 4000（欠配）」 | 同无解口径；`n_groups` 仍为结构值 2 |
| 回归对照 | `n_subjects_hint=60`（HEAD `:150-155`，`power_result=None`） | `power_solved` 恒真、照常出数、预算照常 |

「欠解」那一态在引擎的字符串 API 上不可达（`effect_map` 只有 small/medium/large，`:147`），
故用 `monkeypatch` 把**真实** `calculate_sample_size(...)` 的哨兵产物注进 `_auto_power_analysis`
的返回位——注的是真哨兵，不是手搓假对象。

## 5 定向读数（改前 / 改后对照）

```
$ .venv/Scripts/python.exe -m pytest tests/test_experiment_design_ui_detail_branch.py tests/test_power_analysis.py \
      tests/test_post_hoc_power.py tests/test_experiment_engine_lazy_init.py -q
97 passed, 1 xfailed in 7.61s          ← 改动前基线（绿）

$ .venv/Scripts/python.exe -m pytest tests/test_design_engine_aprime_caller.py -q
4 passed in 2.54s                       ← 新增三例＋对照（改前这 4 例的断言对象 power_solved 属性不存在）

$ .venv/Scripts/python.exe -m pytest tests/test_design_engine_aprime_caller.py tests/test_experiment_design.py \
      tests/test_experiment_design_ui_detail_branch.py tests/test_experiment_design_ui_reset_pin.py \
      tests/test_experiment_engine_lazy_init.py tests/test_power_analysis.py tests/test_post_hoc_power.py \
      tests/test_questionnaire_design.py tests/test_ui.py tests/test_llm_engine.py -q
272 passed, 1 xfailed, 2 warnings in 38.57s                   ← 改动后（绿，零翻红）
```

公式本体零改动自证：

```
$ git --no-pager diff --name-only
src/experiment_design/design_engine.py                         ← 生产码只这一枚
$ git --no-pager diff --stat -- src/experiment_design/power_analysis.py src/analysis/post_hoc_power.py \
      src/experiment_design/procedure_builder.py src/experiment_design/preregistration.py
（空）
$ git --no-pager diff -U0 -- src/experiment_design/design_engine.py \
      | grep -E "^[+-].*(brentq|power_at_n|nct\.|ncf\.|ncx2|np\.|effect_map|calculate_sample_size\()"
（空）   ← 求解调用、公式参数、效应量映射一个都没碰
```

## 6 未接的调用方与未落 A′ 的族（不在本单授权面，逐条留证据）

1. 🔴 **UI 显示面未接**：`src/ui/experiment_design_ui.py:235` 的 `metric("样本量", f"N = {d.n_subjects}")`、
   `:283` 的 `**总样本量：N = {d.n_subjects}**`、`:284-285` 的分组行仍会把哨兵渲染成「N = 0／每组0人」。
   本次**没碰**：波次 58 共通指示 §E 已把 `s927-61`（统计显示面＋同域三件在途）停派，且该件的在册钉桩
   `tests/test_experiment_design_ui_detail_branch.py:436` 正钉着这行文案 ⇒ 属**另单同批**处置。
2. ⚠ **非 t 族仍未落 A′**（s924-04 只改了 t 族）：`power_analysis.py:204/247/278/324` 四处仍是
   `except ValueError: n = n_hi`。实测 `quick_sample_size('correlation', 0.05)` 仍返回
   `{'n_total': 3000, 'solved': True, 'actual_power': 0.782}` ⇒ 假数仍在，哨兵位用不上。
   引擎路径**够不到**它（`effect_map` 最小 0.2 ⇒ 相关族给 194，实测），所以本单不受影响，
   但直接调 `calculate_sample_size`/`quick_sample_size` 的下游仍在险。属 B 案/后续单。
3. ℹ **preregistration 的键名对不上**（既有缺陷，非本单引入）：`preregistration.py:347`/`:464`
   取 `pw.get('required_n', …)`，而 `quick_sample_size` 给的键是 `n_total`（`power_analysis.py:459`）
   ⇒ 恒落 `sample_n or '?'` 兜底，即"因错而对"。要真接线得统一键名，另单。
4. ℹ 目标件清洁度：开工时 `design_engine.py`/`power_analysis.py`/`post_hoc_power.py` 三枚均不在
   `git status --porcelain` 内（现点 11 枚脏件全属 §C 在途名单，一律未碰）；收口时仍如此。

## 7 必须同笔入库的件（主班合提口径）

一笔之内必须同时入库，缺一即红：

1. `src/experiment_design/design_engine.py`（改）
2. `tests/test_design_engine_aprime_caller.py`（新增，`??`）
3. `docs/insights/s927-72-aprime.md`（本档，新增，`??`）

分笔风险：只提交 ① ⇒ 新增三例无处跑、判据②不可复算；只提交 ② ⇒ 4 例全红
（`ExperimentDesign` 无 `power_solved` 属性，`AttributeError`）。二者无第三方依赖，
**不涉及** §C 的 11 枚在途件，可与它们无关地独立成笔。
