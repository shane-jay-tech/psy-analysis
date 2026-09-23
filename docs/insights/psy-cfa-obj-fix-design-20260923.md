# psy CFA `obj=` 缺陷修复设计稿（s923-08 · 2026-09-23）

> 班：`qoder-executor-20260923-0022-psy7` · **统计红线单：只出稿，`src/analysis/cfa.py` 与 `tests/fixtures/golden_stats/` 零改动**。
> 取证环境：HEAD `6dcae95` · `.venv/Scripts/python.exe` · **semopy 2.3.11** · pandas 见下 · 全部实测走 `-c` 内存沙箱，**未 exec 生成器、未落任何盘**。
> `data/benchmark_history/` 四件 sha256_8 收班复验：`3d83f7e9 / dff47515 / 092d61b0 / 909b4799`（逐位不变）。

## 0. 结论先说（三句话）

1. **上游对根因的诊断是错的**（"semopy 的 `obj` 位要求可调用目标函数"）。实测：`obj` 是**按名字查表的字符串位**，合法值只有 `MLW/FIML/GLS/WLS/ULS/DWLS`；**传可调用对象同样 `KeyError`**。真因是**值取错了**：`"ML"` 不在名字集里 —— 那是 lavaan 的估计器名，被原样搬进了 semopy 的形参位。
2. **上游给的两个"可执行出口①"都不成立**：`Model.fit` 签名里**既没有 `algo=` 也没有 `estimator=`**，硬传会 `TypeError: minimize() got an unexpected keyword argument`，仍被 cfa.py 的 `except` 吞成同一种降级。
3. **只改 `obj="MLW"` 修不好**：本单实测出**四处独立断点**（§2）。上游说"改好后两条测试会主动红"也偏少 —— 现读该测试件 **19 例全绿**，案 A 会翻 **3 例**，案 C 会翻 **4 例**（§5）。而"两案都会改动金标准 JSON 的 8 个期望值"这句**要收窄**：8 项里**只有 `chi2_range` 一项必须重估**，`df` 不用动，`loadings_min/max` 两项**实测已在带内**（§3）。

## 1. 锚点与签名读数（现场复算）

```
rg -n "model.fit\(clean_df, obj=estimator\)" src/analysis/cfa.py   →  212:（任务书给 212 ✓；done 卷宗给 209/:264 已过期）
rg -n "except Exception as e:" src/analysis/cfa.py                  →  280:  result.warnings.append("⚠ semopy模型拟合失败：…")
```

`.venv` 内 `inspect.signature(semopy.Model.fit)`：

```
(self, data=None, cov=None, obj='MLW', solver='SLSQP', groups=None,
 clean_slate=False, regularization=None, n_samples=None, **kwargs)
```

- `semopy.__version__` → **2.3.11**；`semopy.__file__` → `D:\code\psy-analysis\.venv\Lib\site-packages\semopy\__init__.py`
- 名字集：`sorted(semopy.Model('').objectives.keys())` → **`['DWLS','FIML','GLS','MLW','ULS','WLS']`**（无 `ML`）
- `Model.get_objective` 源码：`return self.objectives[name]` / `except KeyError: raise KeyError(f'{name} is unknown objective function.')`

传参语义实测（同一份 4 因子/12 题/200 行金标准夹具 `tests/fixtures/golden_stats/psychometrics/cfa.csv`，`clean rows 200`）：

| 调用 | 结果 |
|---|---|
| `fit(df, obj='ML')` | **`KeyError: 'ML is unknown objective function.'`** ← 现状，与 `test_cfa_sem_golden.py:223` 钉的串逐字一致 |
| `fit(df, obj=<lambda>)` | **`KeyError: '<function <lambda> at 0x…> is unknown objective function.'`** ⇒ **否证"obj 位要可调用"** |
| `fit(df, estimator='ML')` | `TypeError: minimize() got an unexpected keyword argument 'estimator'`（`**kwargs` 直通 scipy 求解器）⇒ done 卷宗出口①的两个写法都不可用，且失败形态与现状**一模一样**（被 `except` 吞成全 0）＝换出口不解决问题的假象 |
| `fit(df, algo='ml')` | 同上 `TypeError: … 'algo'` |
| `fit(df, obj='MLW')` | **拟合成功**（chi2 44.511 / DoF 48 / CFI 1.004933 / TLI 1.006783 / RMSEA 0 / AIC 59.55489 / BIC 158.504411 / chi2 p-value 0.616606） |
| `fit(df, obj='ULS')`／`'DWLS'` | 拟合本身不报错，但 `float(calc_stats(m).get('chi2'))` → **`TypeError: float() argument … not 'Series'`** ⇒ 换非 MLW 目标函数会**连带打断 cfa.py 的读数路径**，不是免费开关 |

**同仓已存在的正确写法（最重要的现成出口）**：`src/analysis/sem.py:91-92`

```python
obj = "MLW" if estimator == "ML" else estimator
model.fit(clean, obj=obj)
```

⇒ 案 A 不必新设计：**把 sem.py 那两行搬到 cfa.py** 即可，且**公开形参 `estimator="ML"` 的默认值不动**，`test_cfa_sem_golden.py:197 assert cfa_result.estimator == "ML"` 保持绿（若改成把默认值换成 `"MLW"`，那例当场红 —— 这是本案唯一真正的"计数/语义口径"分歧点）。

## 2. 四处独立断点（只修 #1 修不好）

| # | 位置 | 断点 | 实测证据 | 修法（本单**未做**） |
|---|---|---|---|---|
| 1 | `cfa.py:212` | `obj=estimator` 值 `"ML"` 非法 | `KeyError: 'ML is unknown objective function.'` | 照 `sem.py:91` 做 `ML→MLW` 映射 |
| 2 | `cfa.py:74-86 SEMOPY_FIT_MAP` | **4/11 个 stat 键名不存在**：`p-value`（真名 `chi2 p-value`）、`SRMR`、`RMSEA 90% CI (LB)`、`RMSEA 90% CI (UB)` | `calc_stats` 实际键：`DoF, DoF Baseline, chi2, chi2 p-value, chi2 Baseline, CFI, GFI, AGFI, NFI, TLI, RMSEA, AIC, BIC, LogLik` | `chi2_p` 改键名可修；**SRMR 与 RMSEA 双 CI 在 semopy 2.3.11 里根本拿不到** ⇒ 只能自算或从 `CFAResult` 契约里摘掉（属**改对外结构**，待裁决） |
| 3 | `cfa.py:240`（含 `:261` 同型） | 载荷筛选 `estimates['op'] == '=~'` **恒 0 行** | `inspect(mode='list', std_est=True)` 的 `op` 唯一取值是 **`'~'` 与 `'~~'`**；`=~` 只出现在**模型语法**里（`_build_model_syntax` 用的正是 `=~`）⇒ 语法记号被误当成回读记号。`op=='~'` 命中 **12 行**（＝旧任务书说的"载荷行数=12"） | 改判 `== "~"`；`~~`（因子协方差）那条**本来就是对的**，别一起改 |
| 4 | `cfa.py:246-251` | 每因子第一条（标记变量）的 `Std. Err / z值 / p值` 是**字符串 `'-'`**，`float('-')` → ValueError → 被 `:254 except Exception: pass` **整块吞掉** ⇒ 即便 #3 修好，`loadings` 仍是 `None`（静默） | 实测首行：`q1 ~ F1, Estimate 1.0, Est. Std 0.714615, Std.Err '-'` | 用 `pd.to_numeric(errors="coerce")` 或先判 `'-'`；`except Exception: pass` 本身就是本缺陷的**遮蔽器**（同一模式在 `:278` 又有一次） |

⇒ 结论：**案 A ≠ 一行修复**。案 A 只做 #1 的话，拟合链半通（11 个指标里 7 个有值、4 个仍 0），载荷仍 `None`，用户仍然拿到一个"看着像结果"的对象。

附带两处小坑（不改也无人受害，登记）：`cfa.py:215-217` 的 `converged` 是**死变量**（`inspect(mode='converged')` 在 2.3.11 返回 `None`，全函数再没读过它）；`result.estimator` 在 `:199`（try 之前）就已写 `"ML"`，**拟合失败后该字段仍声称"ML"** ⇒ 光看结果对象无法区分"用 ML 拟合过"与"从未拟合"。

## 3. 金标准 8 期望值受影响清单（`cfa_expected.json`，reference_tool: R lavaan 0.6-18）

夹具：4 因子 × 3 题、n=200、`model_spec "F1 =~ q1+q2+q3; …; F4 =~ q10+q11+q12"`。实测列＝案 C 全修后 `obj='MLW'` 的读数。

| # | expected 键 | 在册值 | 修后实测 | 是否要动 JSON |
|---|---|---|---|---|
| 1 | `chi2_range` | [60, 120] | **44.511** | **要重估**（破下界）。⚠ 为何 semopy 的 chi2 落在 lavaan ML 带外**属统计结论，本单不下判断**（`chi2/df=0.927<1` 是线索之一），交多模型评审 |
| 2 | `df` | 48 | **48** | **不动**（模型自由度与估计器无关，实测逐字相同） |
| 3 | `CFI_min` | 0.92 | **1.004933** | 数值"达标"但 **CFI>1 非法** ⇒ 带宽建议加**上界/合法性**检查，不是改 0.92 这个数 |
| 4 | `TLI_min` | 0.90 | **1.006783** | 同上 |
| 5 | `RMSEA_max` | 0.08 | **0**（int） | 因 chi2<df 恒 0 ⇒ "越小越好"档**失去判别力**；数不用改，**判据形状**要改 |
| 6 | `SRMR_max` | 0.08 | **算不出来**（`calc_stats` 无 `SRMR` 键；经 cfa.py 现写法落为 `0.0`） | **要么自算 SRMR，要么摘掉这一档**。危险点：`_assess_fit` 把 srmr=0 当"极好"，**假达标**（与 §2#2 同源） |
| 7 | `loadings_min` | 0.50 | **0.5334** | **不动**（须先修 §2#3/#4 才拿得到载荷；`Est. Std` 12 行的极小值） |
| 8 | `loadings_max` | 0.95 | **0.8172** | **不动**（极大值，带内） |

**净口径**：8 项里 **1 项必须重估（chi2_range）＋ 1 项结构失效（SRMR）＋ 2 项判据形状要改（CFI/TLI/RMSEA 的"恒 0 / >1"）＋ 4 项完全不用动（df、loadings×2、以及带宽本身）**。
⇒ done 卷宗"两案都会改动金标准 JSON 的 8 个期望值＝改统计结论"**证据上不成立**（过强）；真正的统计结论风险不在 JSON，而在 §4 的 AVE/CR 换轨。

`tolerance` 块（CFI 0.05 / TLI 0.05 / RMSEA 0.03 / SRMR 0.03）在 cfa 侧**未被任何断言消费**（`test_golden_bands_currently_unmet` 只用 `expected`），别顺手当"已用容差"。

## 4. 比 JSON 更危险的一面（务必进裁决）：AVE/CR 换轨

`cfa.py:365-368 _attach_validity_metrics` 是按 `result.loadings is not None` **分支**的：

- 现状（断点全在）→ `loadings is None` → 走 `_fallback_loadings_per_factor`（**factor_analyzer 逐因子单因子 FA**，`:421-430`）算 AVE/CR/HTMT/Fornell-Larcker。
- 案 C 修好 → `loadings` 有值 → **改用 semopy 标准化载荷**算 AVE/CR ⇒ **同一份数据下这些效度指标数值全部变化**，而它们正是论文里"收敛效度/区分效度"的结论来源。

⇒ **"改统计结论"的真实发生地在 AVE/CR/HTMT，不在金标准 8 项**。现成在册断言多为集合/带宽形（`test_cfa_sem_golden.py:244-247`、`test_validity.py:250`、`test_reliability_extended.py:61-62 all(v>0.7)`）—— 集合类不会红，**但 `>0.7` 这类带宽容差可能因换轨而失守**。裁决前置动作（人工/评审做，本单不做）：
```
# 只读比对：同一夹具下「FA 兜底载荷」与「semopy 标准化载荷」的 AVE/CR 差
# 建议在评审沙箱里跑，不在生产码里加开关
```

## 5. 两案（＋第三案）对比与"翻正步骤"

| | 案 A 改估计器入口（只做 §2#1） | 案 B 显式判失败 `is_fallback` | **案 C 完整修链（#1+#2+#3+#4）** |
|---|---|---|---|
| 改动 | 2 行（照搬 `sem.py:91-92`） | `except` 里 `result.is_fallback=True` ＋ `fallback_note`；`renderers.py:245`/`interpretation.py:409` 已消费 `is_fallback`，**UI 侧零改** | §2 四处，含 1 处对外契约抉择（SRMR/RMSEA-CI 摘或自算） |
| 用户拿到 | 7 个真指标＋4 个 0＋**载荷仍 None**，且 `fit_acceptable` 因 srmr=0 可能**假达标** | 数值仍全 0，但**降级被明说**（当前 `test:225/226` 钉的正是 `is_fallback is False`，会红） | 12 行真载荷＋AVE/CR **换轨**（§4） |
| 是否触统计红线 | 半触（指标从"无"变"有"） | **不触**（零数值变化，只加透出） | **全触**（效度结论变） |
| 工时 | 0.5h ＋ 3 例测试同步 | 0.5h ＋ 1 例测试同步 | 2h ＋ 4 例测试同步 ＋ 多模型评审 ＋ AVE/CR 对照报告 |
| 建议排序 | — | **推荐先做**：它单独可交付、不动任何数值、把"全 0 的像样对象"变成"明说的降级"，是止血 | 之后作为独立裁决单推进 |

案 B 的额外收益：现状 `warnings` 只 1 条、`fit_summary_zh` 有"模型拟合出错"字样，但 **`src/analysis/runner.py:535/561/797`（done 卷宗点名的调用方）读的是数值字段**，没有分支 ⇒ 案 B 才是"下游不再拿假 0"的最小修复。（这三处行号**本单未复核**，属 done 卷宗引数，推进前现取。）

### 翻正测试的步骤（现读基线：`19 passed in 2.03s`，`tests/test_cfa_sem_golden.py`）

⚠ **上游说只有两条会红，实测不止**：

| 测试 | 例 | 案 A 后 | 案 B 后 | 案 C 后 |
|---|---|---|---|---|
| `test_fit_attributes_exist_but_currently_zeroed` | :199 | **红**（9 个里 7 个非 0；`chi2_p`/`srmr` 因 §2#2 仍 0） | 绿 | **红且无法全绿**——除非同时改 §2#2；`chi2_p` 可转绿，`srmr` **仍 0** |
| `test_golden_bands_currently_unmet` | :228 | **红**（`cfi<0.92` 与 `chi2_df!=48` 两句失守） | 绿 | **红**（须按 §3 重写为"逐项实测 vs 带宽"的达标例，并处理 SRMR 不可得） |
| `test_failure_is_surfaced_as_exactly_one_semopy_warning` | :220 | **红**（`len(warnings)==1` → 0） | 绿（但 `is_fallback` 断言要按案 B 新语义改） | **红** |
| `test_loadings_are_none_so_row_count_12_premise_fails` | :210 | 绿（载荷仍 None） | 绿 | **红**（`loadings` 变 12 行 DataFrame；**该例 docstring 说的"前提不成立"在案 C 下反转为成立**，须改名重写，别只删断言） |
| `test_result_identity_fields` | :192 | 绿（前提是 `estimator` 默认值不动） | 绿 | 绿；**若把默认值改成 `"MLW"` 则红** |
| `test_validity_metrics_are_still_produced_after_the_failure` | :242 | 绿 | 绿 | 绿（集合/带宽形断言）但**语义作废**：它钉的是"失败之后"，案 C 后"失败"没了，例名与 docstring 都要改 |

步骤（交人工/评审执行，本单不执行）：
1. 先跑 `pytest tests -q -k "cfa or sem_golden or validity or reliability"` 取**案前基线**（别拿全量，psy 全量失败集不稳定）。
2. 案 B 单独一笔：`cfa.py:280` except 内加 `is_fallback=True` ＋ `fallback_note`，同步 `test:220/225/226` 三句 → 期望 `19 passed`。
3. 案 A 单独一笔（2 行）→ 按 §3 实测数**先出对照表**给评审，再决定 JSON 动哪几项。
4. 案 C 只在 AVE/CR 换轨评审**放行后**推进；同步 §5 表中 4 例（其中 :210 是**改名重写**，:242 是**改语义**）。
5. 每步都要跑 psy 的**全局清单型门禁族** `pytest tests -q -k "download_buttons or export_gate"`（HEAD 上已有 1 条主班造成的在册红 `test_all_download_buttons_accounted_for`，见待人工 81，**不计入本案**）。

## 6. 否证清单（本单全部推翻/收窄的上游前提）

| 上游前提（`done/s922-16-psy-cfasem-golden.result.md:84` 与任务书） | 实测 | 判定 |
|---|---|---|
| "semopy 2.3.11 的 `obj` 位要求**可调用目标函数**" | `obj` 是名字位（`self.objectives[name]`），合法值 `MLW/FIML/GLS/WLS/ULS/DWLS`；**传 callable 同样 KeyError**（读数见 §1） | **否证**（结论"恒降级"成立，机制说反了） |
| "出口①：改成 semopy 2.3.x 认可的估计器入口（`algo='ml'` 或 `estimator='ML'`）" | `Model.fit` 签名无此二位，`**kwargs` 直通 scipy：`TypeError: minimize() got an unexpected keyword argument 'estimator' / 'algo'` | **否证**（两个写法都不可用，且失败形态与现状同形＝假修复温床） |
| "CFA 在**所有数据**上恒降级" | `obj='ML'` 在 `get_objective` 第一次查表就抛，**与数据无关**；本单只在金标准夹具上实测 | **成立**（机制上必然，非经验概括） |
| "**两案都会改动金标准 JSON 的 8 个期望值**＝改统计结论" | §3：1 项必改（chi2_range）、1 项不动（df）、2 项实测已在带内（loadings）、3 项是判据形状问题、1 项算不出来 | **过强 → 收窄**。真正的统计结论风险是 §4 的 **AVE/CR 换轨**，上游未提及 |
| "改好后 `test_fit_attributes_exist_but_currently_zeroed` 与 `test_golden_bands_currently_unmet` 会主动红" | 案 A 红 3 例、案 C 红 4 例（:220 那条也会；:210 案 C 下会） | **不完整**（少报 1–2 条） |
| 锚点 `cfa.py:212` | 212 正是 `model.fit(clean_df, obj=estimator)` | **成立**（任务书比 done 卷宗的 :209/:264 更新，磁盘以任务书为准） |
| `SEMOPY_FIT_MAP` 的键是 semopy 输出的键 | 11 键中 **4 个不存在/名字不符**（§2#2） | **否证新发现的第三处缺陷**（上游未记） |

## 7. 遗留 / 需裁决（本单落 partial 的原因）

1. `chi2_range [60,120]` 与 semopy MLW 的 44.511 差异**如何定论**属统计结论 → 交多模型评审，本单不判。
2. `SRMR` / `RMSEA 90% CI` 在 semopy 2.3.11 拿不到：是**自算**、**摘字段**（改对外契约）还是**只留 note**？三选一都超出执行班授权。
3. AVE/CR 换轨（§4）需先出对照数并人工复核，才能放行案 C。
4. 是否接受"`estimator` 默认值保持 `"ML"` ＋ 内部映射"（sem.py 现写法）而不是"把默认值改成 `MLW`"——后者会让 `test:197` 与所有调用方文案变口径。
5. 本单未跑全量 pytest（遵主班口径），故未给全量红名集。
