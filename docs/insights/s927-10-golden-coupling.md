# s927-10 —— `tests/test_cfa_sem_golden.py` × `src/analysis/cfa.py` 在途 diff 的耦合性质审计

- 班：`qoder-executor-20260928-0120-psy83`（波次 40，文档／裁决材料位）
- 仓／cwd：`D:\code\psy-analysis`｜取证时 HEAD＝`f0f3f73`（`git rev-parse --short HEAD` 现取）
- 取证时工作树：`git status --porcelain | wc -l` ＝ **12**（与波次 40 brief §5 表一致）
- 纪律：**零 git 写操作**（无 add／commit／stash／checkout／restore／clean）、**零码改动**、**只出材料**。
- 🔴 红线自持：本文**不判定任何统计量／效应量是否成立、不判定任何检验是否通过**。文中出现的数值一律标「取证读数」，其统计含义交人工裁决（见 §8）。

---

## 1. 判定结论（一句话）

**配套改动（test 与 impl 同窗、互为前提，必须一起提交）**——不是单边漂移。
但配套只覆盖到「拟合链跑通」这一层：**配套的质量是坏的**——在途测试把在册金标准带宽的比对**降级成恒真式并删除了四项 band 断言**，同时在途实现仍有 **4 个字段把 semopy 的缺列默认值当读数落 0.0**，其中 SRMR 会进 `card.effect_sizes` 与用户文案。

| 维度 | 结论 |
|---|---|
| 耦合性质 | 配套改动（双向互斥验证：A 红 8/9、B 红 8/9，见 §3） |
| 金标准基线是否同步改 | **基线文件零改动**（`tests/fixtures/golden_stats/` diffstat 为空）⇒ 无「改 json 凑绿」；但**测试对 json 的使用方向被翻转、比对被删**（§4，需人工裁） |
| 风险评级 | 🔴 **高**（提交动作本身低风险；风险在"绿了但保护变弱"+ 假 0 直达 UI／效应量出口） |
| 处置建议 | 可一起提交，**但先补 3 枚钉**（§6）；不接受「19 passed 即放行」的口径 |

---

## 2. 取证现场（全部命令＋原文输出留痕）

```
$ git rev-parse --short HEAD
f0f3f73

$ git status --porcelain
 M app.py
 M pytest.ini
 M requirements-lock.txt
 M src/analysis/__init__.py
 M src/analysis/cfa.py
 M src/analysis/result_card.py
 M src/output/interpretation.py
 M tests/test_cfa_sem_golden.py
?? docs/insights/s924-36-a1-backport-draft-20260925.md
?? node_modules/
?? scripts/research_release_gate.py
?? src/analysis/_sklearn_compat.py

$ git diff --stat
 src/analysis/cfa.py          | 218 +++++++++++++++++++-----
 tests/test_cfa_sem_golden.py | 108 ++++++++------
 （另 6 文件，合计 452 insertions / 151 deletions）

$ ls -l --time-style=full-iso tests/test_cfa_sem_golden.py src/analysis/cfa.py
-rw-r--r-- ... 30684 2026-09-26 11:47:36.327315700 +0800 src/analysis/cfa.py
-rw-r--r-- ... 19065 2026-09-26 11:47:36.327315700 +0800 tests/test_cfa_sem_golden.py

$ git diff -U0 -- src/analysis/cfa.py | grep -c '^@@'      → 16 hunks
$ git diff -U0 -- tests/test_cfa_sem_golden.py | grep -c '^@@' → 14 hunks

$ git diff --stat -- tests/fixtures/golden_stats/          → （空输出，rc=0）
$ git status --porcelain -- tests/fixtures/golden_stats/   → （空）
```

**mtime 同秒（`11:47:36.327315700`）逐位相同** ⇒ 两件是在同一次批量写入里落盘的，符合「一次修复同时改实现与测试」的形态，不符合「两个不同时间各自漂」的形态。
两件均为**工作树版**（非 HEAD）；HEAD 对照件已取到 `D:\code\tmp\qoder-executor-20260928-0120-psy83\`（HEAD cfa.py 535 行、HEAD 测试 365 行；**交班时随临时件自清**，重建法见 §9）。

环境实测（`.venv` 解释器，非系统 python）：`semopy 2.3.11 | pandas 3.0.3`。

在途定向测试（非全量，2.22 s）：

```
$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_cfa_sem_golden.py -p no:cacheprovider
collected 19 items
tests\test_cfa_sem_golden.py ...................                 [100%]
============================== 19 passed in 2.22s ==============================
```

⇒ **在当前工作树里 test 与 impl 自洽（绿）**。这是「配套」的必要证据，不是「正确」的证据（§4／§5 说明为何绿了仍高风险）。

---

## 3. 双向 diff 对照表（完成标准 ①）

### 3.1 逐主题配对（实现 hunk ↔ 测试 hunk）

| # | 主题 | `src/analysis/cfa.py`（在途） | `tests/test_cfa_sem_golden.py`（在途） | 配对性 |
|---|---|---|---|---|
| C1 | 默认估计量改名 | `estimator: str = "ML"` → `"MLW"`（dataclass 默认＋函数签名默认＋docstring 三处）；新增 `SEMOPY_OBJECTIVES`／`_SEMOPY_OBJECTIVE_ALIASES = {"ML": "MLW"}`／`_resolve_objective()` | `assert cfa_result.estimator == "ML"` → `== "MLW"`（`test_result_identity_fields`） | ✅ 严格 1:1 |
| C2 | 收敛状态入库 | `CFAResult` 新增 `converged: Optional[bool] = None`；`model.inspect(mode="converged")` 结果不再算完即丢，None 视为「该版本不提供」 | 新增 `assert cfa_result.converged is None` | ✅ 配套，但钉成**版本特定值**（§5-R2） |
| C3 | 调用方意图留痕 | `CFAResult` 新增 `requested_estimator: str = ""`，`_resolve_objective` 前赋值 | **无任何断言**、无任何下游消费方（全仓 grep 只见 cfa.py 自身） | ⚠️ 单边（新增面未钉，见 §5-R4） |
| C4 | pandas 3.x Series 取值 | 新增 `_stat_scalar()`；`_assess_fit` 的 4 处 `getattr(...) or 0` → `_stat_scalar(...)`；`SEMOPY_FIT_MAP` 循环改走 `_stat_scalar` ＋ `coerced` 计数告警 | 测试侧无对应新钉（Series 归一化属内部实现，不可从结果对象观测） | ➖ 中性（无可钉点） |
| C5 | 越界指标判据 | 新增 `FIT_RANGE_TOLERANCE = 1e-3`；`_assess_fit` 尾部：CFI/TLI>1+tol 或 RMSEA<−tol ⇒ 覆写 `fit_summary_zh` 为「⚠ 拟合指标越界…」并强制 `is_good=is_acceptable=False`；1e-3 内属浮点误差则 clamp 到 1.0 | `assert fit_summary_zh.startswith("模型拟合出错")` → `assert "越界" in ... or "不理想" in ...`；`fit_good is False` 保留 | ✅ 严格 1:1（文案锚随判据一起改） |
| C6 | 载荷算符兼容 | `estimates['op'] == '=~'` → `ops.isin(("=~","~"))`，并按算符方向决定 `lval/rval` 谁是因子；新增 `'op' in estimates.columns` 守卫 | `assert cfa_result.loadings is None` → `assert loadings is not None` ＋ `len == 12` ＋ 列名集合 `{"潜在变量","观测变量","标准载荷"}` | ✅ 严格 1:1 |
| C7 | 载荷占位符 `-` | 新增 `_round_or_nan()`（`float("-")` 不再抛） | 测试只断行数与列名，**未断 SE/z/p 的 NaN 语义**（4 行首指标 NaN 无钉） | ⚠️ 半配套（NaN 契约未钉） |
| C8 | 失败不再静默 | `except Exception: pass` → `except Exception as exc: warnings.append("⚠ 载荷表提取失败…")`；载荷空 → append 告警 | `test_failure_is_surfaced_as_exactly_one_semopy_warning` → `test_no_semopy_failure_warning_after_fix`（改为 `is_fallback is False`／`fallback_note == ""`／无「semopy模型拟合失败」） | ✅ 配套（断言语境整体反转），两态覆盖口径保留 |
| C9 | 带宽比对 | —（实现无涉） | `test_golden_bands_currently_unmet` → `test_golden_bands_now_comparable_to_real_values`：**删** `cfi<CFI_min`／`tli<TLI_min`／`chi2<chi2_range[0]`／`chi2_df != df`／`rmsea == RMSEA_max*0`／`srmr == SRMR_max*0`；**改**为 `cfi > CFI_min`、`chi2 > chi2_range[0]*0`、`rmsea>=0 and srmr>=0` | 🔴 **单向：只动测试、实现无对应改动** ⇒ 这是全表唯一一处「测试改了但没有任何实现改动要求它这么改」（§4 专节） |

### 3.2 交叉探针（决定性证据：证明是「配套」而非「单边」）

方法：`git show HEAD:src/analysis/cfa.py` 取到 tmp，用 `importlib` 分别加载 HEAD 实现与在途实现（`cfa.py` 只依赖 pandas/numpy/semopy，可独立加载），把两版测试的**关键断言原文**分别套到两版实现上。**不改动仓内任何文件。**

脚本：`D:\code\tmp\qoder-executor-20260928-0120-psy83\probe_coupling.py`（临时件，用完自清）

```
### A) 在途测试断言 × HEAD 实现（HEAD cfa.py）
  [FAIL] estimator == 'MLW'   实得='ML'
  [FAIL] converged is None (字段存在)   实得='<无此字段>'
  [FAIL] chi2 > 0   实得=0.0
  [FAIL] is_fallback is False   实得=True
  [FAIL] loadings is not None   实得='None'
  [FAIL] len(loadings) == 12   实得='None'
  [FAIL] cfi > CFI_min   实得=0.0
  [PASS] fit_acceptable is False and fit_good is False   实得=(False, False)
  [FAIL] 无 'semopy模型拟合失败' 告警   实得=["⚠ semopy模型拟合失败：'ML is unknown objective function.'", ...]
### B) HEAD 测试断言 × 在途实现（worktree cfa.py）
  [FAIL] estimator == 'ML'   实得='MLW'
  [FAIL] chi2 == 0.0（全 0 降级）   实得=44.511
  [FAIL] cfi == 0.0   实得=1.005
  [FAIL] loadings is None   实得=12
  [FAIL] warnings 恰好 1 条且为拟合失败   实得=['效度指标附加失败：attempted relative import ...']
  [FAIL] is_fallback is True   实得=False
  [FAIL] fit_summary_zh 以 '模型拟合出错' 开头   实得='⚠ 拟合指标越界（CFI=1.005>1；TLI'
  [FAIL] cfi < CFI_min（钉未达标）   实得=1.005
  [PASS] chi2 < chi2_range[0]   实得=44.511
### 汇总：A 红 8/9 ；B 红 8/9
```

⇒ **两个方向都红**（9 枚里各红 8 枚，且两个 PASS 都是巧合而非语义相符）。这排除了「只改了测试没改实现」与「只改了实现没改测试」两种单边形态：**任一侧单独提交都会立刻红**。

> 探针自留瑕疵（照实报）：A/B 里那条 `效度指标附加失败：attempted relative import with no known parent package` 是**我的探针产物**（用 importlib 单文件加载时相对导入失败），不是仓内缺陷；真实 pytest 下 `warnings == []`（§3.3）。因此探针里的「warnings 恰好 1 条」类判读只用于形状对比，不作结论。

### 3.3 在途实现的取证读数（**不是**统计结论）

```
estimator= MLW  requested= 'MLW'  converged= None
chi2= 44.511  df= 48.0  p= 0.0  cfi= 1.005  tli= 1.007  rmsea= 0.0  srmr= 0.0  aic= 59.555  bic= 158.504
rmsea_ci_lower= 0.0  rmsea_ci_upper= 0.0
fit_acceptable= False  fit_good= False  is_fallback= False
summary= ⚠ 拟合指标越界（CFI=1.005>1；TLI=1.007>1），已按「未通过」处理：数值不可信，请核对估计量/样本量/模型识别。
warnings= []
loadings rows= 12   NaN 计数= {'潜在变量':0,'观测变量':0,'标准载荷':0,'SE':4,'z值':4,'p值':4}
```

---

## 4. 最重要的一处：带宽比对在测试侧被无声降级（完成标准 ②③ 的核心）

在册基线 `tests/fixtures/golden_stats/psychometrics/cfa_expected.json`（**在途零改动**，HEAD 同文件同字节）：

```json
"chi2_range": [60, 120], "df": 48, "CFI_min": 0.92, "TLI_min": 0.90,
"RMSEA_max": 0.08, "SRMR_max": 0.08, "loadings_min": 0.50, "loadings_max": 0.95
```

测试文件头部红线原文（两版都在，**未被同步修订**）：

> 「不调阈值：所有带宽一律从在册 `*_expected.json` 现场读取，测试里一个新数字都不发明；**带宽失守时把「失守」本身钉成断言**（见 `test_cfa_golden_bands_currently_unmet`），而不是去改 json、不是把断言写松。」

在途版的实际做法与这句话的差距（**逐条对照，取证读数只用于说明覆盖面，不作达标判定**）：

| 在册带宽 | HEAD 测试怎么钉 | 在途测试怎么钉 | 覆盖面变化 |
|---|---|---|---|
| `chi2_range [60,120]` | `assert chi2 < expected["chi2_range"][0]`（钉未达标） | `assert chi2 > expected["chi2_range"][0] * 0` | 🔴 **`* 0` 把下界变成 0 ⇒ 恒真式**。数字 60 留在源码里"看着像在读带宽"，实际不再与区间比较；上界 120 从不参与。取证读数 44.511 落在区间**下方**，这一层关系现在无人钉 |
| `df = 48` | `assert chi2_df != expected["df"]` | **删除** | ⚠ 删除本身合理（读数 df=48 与基线一致，旧的"不等"钉的是坏状态），但**没有换成"相等"钉** ⇒ df 现在无人守 |
| `CFI_min 0.92` | `assert cfi < CFI_min`（钉未达标） | `assert cfi > CFI_min` | ⚠ 方向翻转。越界值 1.005 同样 `> 0.92` ⇒ **该断言无法区分「真达标」与「数值不可信的越界值」**（配套的另一枚 `fit_acceptable is False` 才是不通过的实际来源） |
| `TLI_min 0.90` | `assert tli < TLI_min` | **删除** | 🔴 TLI 带宽完全无人钉（只在越界 clamp 逻辑里出现） |
| `RMSEA_max 0.08` | `assert rmsea == RMSEA_max * 0`（钉「假 0」） | `assert rmsea >= 0` | 🔴 「RMSEA=0 属降级假值」这条**专门防假达标**的钉被换成"非负"恒真式 |
| `SRMR_max 0.08` | `assert srmr == SRMR_max * 0`（钉「假 0」） | `assert ... srmr >= 0`（同行合并） | 🔴 同上，且 **SRMR 现在是"缺列默认 0"（§5-R1），假达标风险比 HEAD 更实** |
| `loadings_min/max 0.50/0.95` | 从未钉 | 仍未钉 | ➖ 无变化（既存缺口，非本次引入） |

净结论：**基线 json 一个数没改（纪律上正确），但测试从"钉住失守"变成"不与基线比较"**。这在语义上等同于把该类的金标准保护撤下来，而文件的 docstring 仍在声称「零放宽、带宽失守钉成断言」，同时新函数名 `test_golden_bands_now_comparable_to_real_values` 与注释「真值可比：既有量级也有界」都指向"在比"——**文与实不符**。这处不属于「配套改动」，是本审计唯一的**测试侧单边漂移**。

> 注：`*_expected.json` 里 `tolerance` 段（CFI/TLI 0.05、RMSEA/SRMR 0.03）两版测试都没用过 —— 既存缺口，登记不展开。

---

## 5. 风险评级与依据（完成标准 ③）

**总评级：🔴 高**（改动性质＝低风险／落地质量＝高风险，二者要分开看）

| ID | 风险 | 证据 | 评级 |
|---|---|---|---|
| R1 | **缺列默认值被当读数**：`SEMOPY_FIT_MAP` 的 4 个 key 在 semopy 2.3.11 的 `calc_stats` 输出里不存在，`stats.get(key, 0)` 静默落 `0.0` | 实测 `calc_stats` 列名＝`['DoF','DoF Baseline','chi2','chi2 p-value','chi2 Baseline','CFI','GFI','AGFI','NFI','TLI','RMSEA','AIC','BIC','LogLik']`；map 要的 `"p-value"`／`"SRMR"`／`"RMSEA 90% CI (LB)"`／`"RMSEA 90% CI (UB)"` 全 `MISSING`。真名应为 `chi2 p-value`（SRMR 该版本**根本不输出**） | 🔴 高 |
| R1a | ⇒ 直达**效应量出口**与用户文案 | `src/analysis/result_card.py:1162-1164`（在途件，只读）：`SRMR = {srmr:.3f}` 并 `card.effect_sizes.append({"name":"SRMR","value":float(srmr)})`；`src/output/interpretation.py:416-418`（在途件）：`p = {r.chi2_p} … [{r.rmsea_ci_lower}, {r.rmsea_ci_upper}], SRMR = {r.srmr}` | 🔴 高（方向恰好相反的两个假信号：p=0 读作"拟合被拒绝"、SRMR=0 读作"完美拟合"。**是否构成误导属统计口径，交人工**） |
| R1b | 在途修复自称"失败不再静默"，但 `coerced` 计数器只统计 `None` 或多值，**缺列（默认 0）不计** ⇒ 这 4 个假 0 不产生任何 warning，测试也照不出（守卫写成 `not all(4 项==0)`，cfi/tli 非 0 即放行） | cfa.py:344-353（在途版）＋ §3.3 `warnings= []` | 🔴 高 |
| R2 | 测试钉 `converged is None` ＝**版本特定钉**（本机 semopy 2.3.11 `inspect(mode="converged")` 返回 None）。换 semopy 版本（返回布尔）即红，且无 skip／xfail／版本守卫；同文件对 numpy/pandas 版本漂移有显式出口注释，唯独这枚没有 | test_cfa_sem_golden.py:204-206（在途版） | 🟠 中高 |
| R3 | **带宽比对降级**（§4）：6 条 band 断言删／翻，`* 0` 恒真式 2 处 | §4 全表 | 🔴 高（保护强度）／🟢 低（提交风险） |
| R4 | 新增字段 `requested_estimator` 零断言、零下游消费（全仓 grep 除 cfa.py 自身无命中）；`field_lineage.py` 的字段谱系（`"chi2_p": "S3_p_value"`／`"srmr": "S24_fit_index"`）**未登记这两个新字段** | grep 结果 §5 取证 | 🟠 中 |
| R5 | 载荷 NaN 契约未钉：12 行里 SE/z/p 各 4 个 NaN（首指标固定占位），而 `interpretation.py:421-424` 用 `(r.loadings["p值"] < 0.05).sum()` 数显著载荷，NaN 比较恒 False ⇒ 分母 12／分子按非 NaN 计。**该计数是否成立交人工** | §3.3 NaN 计数 + interpretation.py:419-424 | 🟠 中 |
| R6 | 提交集合边界：`src/analysis/__init__.py`（在途 M）新增 `from . import _sklearn_compat` ＋ `_compat.install()`，而 `_sklearn_compat.py` 是 **untracked（`??`）** ⇒ 只 add 在册件会让子包静默失去垫片（try/except 吞掉），EFA/ω/CFA 回退支路按注释所述会 TypeError | `git status --porcelain` + `git diff -- src/analysis/__init__.py` 原文 | 🟠 中（同窗提交的必要条件） |
| R7 | 同窗脏件混装：`app.py` 在途 diff 与 CFA 无关（`d913a-43`／`d914-23` UI 拆分，落到 `src/ui/startup_checks.py`／`heavy_preload.py`）；`pytest.ini` 只把 `-q` 去掉；`requirements-lock.txt` 在途改 streamlit/numpy/scipy/plotly/pyreadstat/openai 版本（**其中 numpy 2.4.4→2.3.5 是降级**，与本仓测试文件自称的「版本漂移请查 numpy/pandas」口径直接相关） | `git diff -- app.py pytest.ini requirements-lock.txt` 原文 | 🟠 中（CFA 这一组**不应**与它们捆成一次提交） |
| R8 | 旁证（利好）：`src/analysis/sem.py:91`（HEAD，未在途）早已是 `obj = "MLW" if estimator == "ML" else estimator` ⇒ 在途 cfa.py 改法与仓内既有实现**同型**，属"补齐漏改的姊妹模块"，不是发明新口径 | grep sem.py:35/91 | 🟢 低（性质佐证：修复方向可信） |

---

## 6. 处置建议（给主班的「可直接批的形状」，不含任何代我决策的数值口径）

按可批顺序，**均为建议，不代执行**：

1. **提交集合切一刀**（低风险、高收益）：把 `src/analysis/cfa.py` ＋ `tests/test_cfa_sem_golden.py` ＋ `src/analysis/__init__.py` ＋ `src/analysis/_sklearn_compat.py`（🔴 必须显式精确路径 add 这个 untracked 件，否则 R6）作为**一枚**「CFA/SEM 拟合链修复＋配套钉桩」；`app.py`／`result_card.py`／`interpretation.py`／`pytest.ini`／`requirements-lock.txt` 各自另立集合（R7）。回滚成本：这一枚是纯源码＋测试文件，`git revert` 单提交即可；无迁移、无数据写、`data/` 不涉。
2. **放行前补 3 枚钉**（把 §4 撤掉的保护换回可比形式，**不新增任何数字**，全部读在册 json）：
   - ① 反恒真式：`chi2` 改成与 `expected["chi2_range"]` 的**双端**比较（落区间内／外都要显式表态，若失守就按文件头部纪律把"失守"钉成断言并写明出口，而不是写 `* 0`）。
   - ② 假 0 拦截：把 `RMSEA`／`SRMR`／`chi2_p` 的"来自 semopy 还是来自缺列默认"变成可观测——实现侧给 `_stat_scalar`／map 循环加「key 不在 `stats.columns` 就 append warning（或置 NaN）」，测试侧钉「不得出现无 warning 的 0」。这一枚是 R1／R1b 的正解。
   - ③ 版本耦合钉：`converged is None` 加 semopy 版本前置条件或改钉类型（`is None or isinstance(bool)`），避免 R2 的环境性假红。
3. **不要**用「19 passed」当验收：那 19 枚绿恰恰是 §4 降级之后才绿的。验收判据建议改成「在途测试对 json 的每个带宽 key 至少有一条非恒真比较」＋「R1 四个字段无静默 0」。
4. **人工裁决项**（我不碰，见 §8）：越界 CFI/TLI 的处置口径（clamp 1e-3 容差、判"未通过"）是否符合本仓统计规范；semopy 2.3.11 是否输出 SRMR（若否，字段应落 NaN 并显式标"不提供"，而不是 0.0）；`chi2 p-value` 与 `chi2`／`DoF` 的同源性。
5. 若主班要在收班前拿到「这两件之外还有谁依赖 CFA 结果形状」的边界：调用方 3 处在 `src/analysis/runner.py:535/561/797`、`cfa.py:635/658` 内部、注册表 `result_card.py:1559`；测试面另有 `tests/test_validity.py:245`、`tests/test_result_card_registry_snapshot.py`、`tests/test_error_messages.py`（后者只把 `"ML"` 当字符串模板入参，与改名无关）。

---

## 7. 与其它在途件的边界（避免误读我的结论）

- 本审计**只判 `cfa.py` × `test_cfa_sem_golden.py` 的耦合性质**。`result_card.py`（193 行在途）与 `interpretation.py`（4 行在途）我只**引用**其行号作为 blast-radius 证据，**未审**其自身配套性（那是别的单／主班的活）。
- 横幅与 brief 的「这些是早先信箱班留在盘上未收编的半成品，归属未逐枚坐实」——本文按"取证对象"处理，**未对作者归属作任何定性**。
- 文中提到的既有事实：`app.py`／`cfa.py`／`result_card.py`／`interpretation.py`／`pytest.ini`／`requirements-lock.txt`／`test_cfa_sem_golden.py` 七件的在途状态我已现复核（§2 `git status` 原文），与 brief §5 表一致。

## 8. 红线声明

本单的卷宗判据（完成标准 ①②③④）是**改动性质审计**，不要求我判定任何统计量或效应量是否成立，故未触红线、状态 `done`。
以下三类结论我**明确不作**，全部标 `交人工`：

1. 任何「拟合达标／不达标」「模型可接受／不可接受」的判定（§3.3、§4 的读数只用于说明断言覆盖面）；
2. 任何「效应量成立／载荷显著个数对不对」的判定（R1a、R5）；
3. 任何校正口径（Holm／FDR／临界值）相关的取舍（本单无涉，s927-21 才有）。

## 9. 复核指令（他人可原样重跑，全部只读）

```bash
cd /d/code/psy-analysis
git rev-parse --short HEAD; git status --porcelain
git diff --stat -- tests/fixtures/golden_stats/          # 期望：空
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_cfa_sem_golden.py -p no:cacheprovider
# 交叉探针：交班时临时件已自清（tmp/<班名>/ 不留），重建法＝
#   git show HEAD:src/analysis/cfa.py > /tmp/cfa_head.py
#   再用 importlib.util.spec_from_file_location 分别加载该件与工作树 src/analysis/cfa.py（cfa.py 只依赖
#   pandas/numpy/semopy，可独立加载），把 §3.2 列出的断言互套。注意单文件加载会使
#   效度附加支路的相对导入失败并多出一条 warning（探针产物，非仓内缺陷）。
```

零写主证：`find data -maxdepth 1 -type f -printf '%T@ %s %p\n'` 跑前跑后一致（`data/` 仅 `perf_history.jsonl` 1528 B、`kaoyan.db` 0 B，两枚 mtime 未变）。
