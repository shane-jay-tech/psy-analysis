# s927-40 · `power_analysis` 异常吞掉缺陷裁决材料（只读出材料 · 2026-09-28）

- 班：`qoder-executor-20260928-1440-psy91`（信箱单 `s927-40`，主班 `qoder-main-drain-20260928-0115`）
- 性质：**只读材料**。生产码／测试件／配置／数据零改动；`git add`／`commit` 未执行。
- 🔴 **统计数值红线自约**：本文所有数字都是**「求解器当前返回了什么」这一实现事实**，
  不含任何"样本量应为多少／效应量是否合理／p 值／效力是否达标"的判定。
  三选一（抛错／哨兵／区间）的**选择权与任何数值口径的改动权都在人工闸**，本文只给改动面与回滚成本。
- 盘面绑定（读数只对这一态负责，取值时刻 2026-09-28 14:4x 本机 `date`）：

```
HEAD = 429495086addff5b59593ee6d70128fe60ae4963（短 4294950）
sha256 src/experiment_design/power_analysis.py = e4aa0f2b95af103422d6d5eac6ac7129657152dce954fe9f67fcad57352de11f
sha256 src/analysis/post_hoc_power.py          = 1dab54dd1f1b1bfe1bda648b7be62855eced77b8490bc55756c544cc5fd05c96
sha256 tests/test_power_analysis.py            = 52a10113a3b618395f5855dedcae8e54a1f847812ea41a2d291e2d0165595a0f
git diff --numstat HEAD -- src/experiment_design/power_analysis.py src/analysis/post_hoc_power.py \
    tests/test_power_analysis.py src/experiment_design/design_engine.py src/analysis/runner.py   → 空输出（本班零改动）
```

  ⚠ 工作树另有 **12 枚他班在途件**（`app.py`／`pytest.ini`／`requirements-lock.txt`／`src/analysis/__init__.py`／
  `src/analysis/cfa.py`／`src/analysis/result_card.py`／`src/output/interpretation.py`／`tests/test_cfa_sem_golden.py`
  ＋ 4 枚未跟踪）。**本文取证未涉及其中任何一件**；上面五个文件均干净＝与 HEAD 逐字节同。

---

## 1. 卷宗前提逐条实测（含否证）

| # | 卷宗／来账前提 | 实测结论 | 证据 |
|---|---|---|---|
| 1 | 锚点 `done/s922-12-psy-power-n-solvers.result.md` 遗留 1：`_solve_n_for_t_test` 的 `except Va[lueError: n = ceil(n_hi)]` 把搜索失败静默变成区间上界 | ❌ **该前提已过期——t 族此缺陷已修并入库**。`git log -- power_analysis.py` 现值只有两枚 commit：`2f08c60 feat(psy): s924-04＋s924-16 …（power 求解 A′ 拒答口径落地…）` 与初版 `ec45485`。现盘 `:109-112`（配对）／`:147-150`（独立）的 `except ValueError as exc:` 分支赋的是 `solved=False` ＋ `failure_reason=…` ＋ `n=0`，**不再取 `n_hi`** | `grep -n "except ValueError" src/experiment_design/power_analysis.py` 全文 7 处（见本文 §2 表）；`:109/:147` 两处的下一行是 `# 出口 A′：求根失败不再把区间上界当答案，返回未解哨兵` |
| 2 | 同锚点：假绿透出（`format_power_report` 对 NaN 恒打「✅ 达标」） | ❌ **t 族该通路已闭**：`format_power_report:392` 现为 `if not result.solved:` 前置分支 ⇒ 未解走「⛔ 求解失败／无法给出样本量建议」，`actual_power=nan` 不再进达标判据 | 代码 `:390-408`；探针实测 t 族两点报告建议行＝`- ⛔ 求解失败：…`（`tmp/…/probe_out.txt`） |
| 3 | 同锚点：「需 owner 拍板」 | ✅ **成立但范围已收窄**：t 族出口 A′ 已由 `s924-04` 落码（＝三案里的**哨兵值**案已被选中并执行）；**未随单修的是另外四族**——`tests/test_power_analysis.py:34-36` 逐字写着：「**未随单修**：anova/相关/卡方/多因素四族仍保留区间上界兜底（设计稿 §3.3 认定同雷，本波范围只有 t 族）」 | 同上 |
| 4 | 卷宗「构造触发用例（钉现状）」 | ✅ 已构造并实跑（见 §3）。⚠ 同时发现：**现有 27 个测试入参点里 0 个点命中上界兜底**（§3.2）⇒ 四族现状**没有任何用例在钉**，现状桩在 `2f08c60` 翻正 t 族时被整组撤掉了 | `tmp/…/probe_testimpact_out.txt` |

⇒ **本单的实际裁决对象不是"t 族兜底"，而是它的四个同型兄弟 ＋ 两处旁支**。卷宗若按字面执行会做一遍已完成的决定，故按磁盘实况收窄（w40-brief §3 锚点口径）。

---

## 2. 缺陷现场（HEAD 4294950 现值行号）

`src/experiment_design/power_analysis.py` 内 `except ValueError` 共 **7 枚**，`except Exception` **0 枚**：

| 处 | 行号现值 | 兜底语句 |  solved 字段 | 报告出口 | 归属 |
|---|---|---|---|---|---|
| A | `:109-112` | `solved,failure_reason=False,…; n=0` | ✅ 有（False） | ⛔ 拒答 | 配对 t（**已修**，s924-04） |
| B | `:147-150` | 同上，`N=0` | ✅ 有（False） | ⛔ 拒答 | 独立 t（**已修**） |
| C | `:204-205` | `n = n_hi`（`n_hi=2000`，`k+1` 为下界） | ❌ **恒 True（默认值）** | 出数 | 单因素 **与** 重复测量 ANOVA **共用这一枚** |
| D | `:247-248` | `n = n_hi`（`n_hi=3000`） | ❌ 恒 True | 出数 | Pearson 相关 |
| E | `:278-279` | `n = n_hi`（`n_hi=5000`） | ❌ 恒 True | 出数 | 卡方 |
| F | `:324-325` | `n_per = n_hi`（`n_hi=2000` ⇒ `required_n = 2000×k`） | ❌ 恒 True | 出数 | 多因素 |
| G | `:304-305` | `factors = [2, 2]`（`design` 串解析失败静默退 2x2） | — | 出数 | 多因素入参校验 |

两处**结构性放大**（是形状事实，非数值主张）：

- **C–F 的 `n = int(np.ceil(n))` 与 `actual = power_at_n(n)` 落在 `try` 之外**（如 `:207/:209`），而 t 族配对枚把 `ceil` 包在 `try` 之内（`:107`）⇒ C–F 兜底后**必然再回算一次效力并当作答案输出**，没有任何"这是兜底"的痕迹留在对象里。
- **`PowerResult.solved` 的默认值是 `True`**（`:35`），C–F 的构造器调用**不传 `solved`**（`:211-221` 等）⇒ 兜底产物在类型层面与真解**完全同形**。下游 `post_hoc_power.py:307` 的守卫写的是 `if not getattr(res_080, "solved", True)` ⇒ 对 C–F **恒不触发**（哨兵字段存在且为 True）。

---

## 3. 触发用例（钉现状 · 沙盒只读，未写入仓库）

探针与原文输出：`D:\code\tmp\qoder-executor-20260928-1440-psy91\probe_s927_40_siblings.py` → `probe_out.txt`（班目录，用完自清；复算入口见本 §3 命令）。
触发入参取自归档 census `docs/insights/psy-power-sibling-fallback-census-20260924.md` §3 的实测命中点，同参复跑。

```bash
cd /d/code/psy-analysis
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "D:/code/tmp/qoder-executor-20260928-1440-psy91/probe_s927_40_siblings.py"
```

### 3.1 兜底点的返回对象现状（原文摘录，未取整未改写）

| 入参（触发点） | `required_n` | `actual_power` | `solved` | 报告建议行（原文） |
|---|---|---|---|---|
| ANOVA 单因素 f=0.01 k=2 | 2000（＝`n_hi`） | 0.09688943025853003 | **True** | `- ⚠ 实际效力低于目标（缺口 0.703），按缺口另行估算建议增加约1407名被试，重算后复核。` |
| ANOVA 重复测量 f=0.01 k=2 ρ=0.5 | 2000（＝`n_hi`） | 0.14537829334924435 | **True** | `- ⚠ …（缺口 0.655）…增加约1310名被试…` |
| 相关 r=0.05 | 3000（＝`n_hi`） | 0.7821774151081128 | **True** | `- ✅ 实际效力达到目标水平。` |
| 卡方 w=0.02 df=1 | 5000（＝`n_hi`） | 0.2929889364479872 | **True** | `- ⚠ …（缺口 0.507）…增加约2536名被试…` |
| 卡方 w=0.30 **df=6000** | 5000（＝`n_hi`，**低于该函数自己声明的下限 `df+2=6002`**） | 0.9989164001581933 | **True** | `- ✅ 实际效力达到目标水平。` |
| 多因素 2x2 f=0.01 | 8000（＝`2000×k`） | 0.1454489510140281 | **True** | `- ⚠ …（缺口 0.655）…增加约5237名被试…` |
| 对照：独立 t d=0.5 | 0 | nan | **False** | `- ⛔ 求解失败：数值求解失败（迭代进入 NaN 发散区…）` |
| 对照：配对 t d=0.3 | 0 | nan | **False** | `- ⛔ 求解失败：…` |

三点形状事实：

1. **C–F 全部把「求根失败」包装成「一个正常答案」**——对象里没有 `solved=False`、没有 `failure_reason`、`note` 也是肯定句（如 `需要5000名被试`）。
2. **相关族 r=0.05 一行的 `actual_power` 明显低于目标，却仍打「✅ 达标」**：判据是 `format_power_report:435` 的 `result.actual_power < result.power - 0.02`，缓冲带 0.02 使该点落进 ✅ 分支。**这条 ✅/⚠ 分界与 t 族的 NaN 恒假是两种不同成因，但在报告里同样不可见**。
   ⇒ 是否要收窄这个缓冲带、以何值为条件，**属判据阈值改动＝人工闸，本班未动、不建议具体数字**。
3. **卡方 `df` 大到 `n_lo = df + 2 > n_hi = 5000` 时区间上下界颠倒**，兜底照样返回 `5000`——一个违反该函数自身下限声明的数，且不抛错。这是 C–F 里唯一**不依赖效应量大小**、纯由入参形状就能稳定触发的分支。

`design` 串旁支（G）现状，同探针实跑：`"2*2"` / `""` / `"abc"` / `"2x"` 四种坏串 ⇒ 全部 `n_groups=4`、`required_n=128`，`note` 里的设计名**原样回显用户输入**（`''` 时输出「设计，4个实验条件…」）。既有用例 `tests/test_power_analysis.py:230-234` 已把这四个静默退 2x2 钉成现状桩。

### 3.2 现有用例的波及面（决定"三案任一会不会当场撞红"）

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "D:/code/tmp/qoder-executor-20260928-1440-psy91/probe_s927_40_testimpact.py"
```

把 `tests/test_power_analysis.py` 里全部 sibling 相关入参（6 组 ANOVA 闭合例、3 相关、4 卡方、4 多因素、坏 design 桩、18 别名分发例、`quick_sample_size` 键集例、`correlation r=0.30` 快照例）逐一求解：

```
现有用例入参共 27 点；命中上界兜底的点数 = 0
```

⇒ **C–F 的现状在测试面上是"零覆盖"**：三案任一一案落地，现有 27 点全部保持绿；
不新增用例就没有任何断言会为该决定负责（**改判据不红＝改判据无牙**）。
按 w46-brief §A.4：这条决定了「生产码 4 处 ＋ 新用例」**必须同笔入库**，分开提交＝HEAD 上该判据无人守。

---

## 4. 影响面（谁会把兜底产物读成答案）

| 消费点 | 现值 | 读到什么 |
|---|---|---|
| `src/analysis/post_hoc_power.py:267-290`（`calculate_sample_size` 六种 `pa_test` 全在这里） | `getattr(res_080, "solved", True)` `:307` | 四族兜底 ⇒ 守卫恒不触发 ⇒ `n_needed_for_080` 直接取兜底数（`:312`） |
| `src/analysis/runner.py:966` | `try: ph = estimate_post_hoc(output) … except Exception: output["post_hoc_power"] = None` | **第二层吞点**：真抛错（案甲）在这里被吞成 `None`，与"没这条建议"不可区分 |
| `src/analysis/field_lineage.py:329/335/445`（`S20_routing_advice`／`S21_recommended_size`） | 字段谱 | `post_hoc_power` 是**已登记的结果卡字段**＝会进交付物 |
| `src/experiment_design/design_engine.py:685-701`（`_auto_power_analysis`，6 条模板分支）→ `:157-162` | **无 try**；`design.n_subjects = power_result.required_n` | 案甲下 ⇒ 生成流程直接抛到 UI；案乙下 ⇒ `n_subjects=0` 继续往下送（此半段是**已入库在册缺陷**，台账 215①：「`design_engine.py:159` 在 `solved=False` 时仍把 `n_subjects=0` 往下送」） |
| `src/experiment_design/design_engine.py:571` ＋ `src/ui/experiment_design_ui.py:289` | `format_power_report(d.power_result)` | 用户屏上的报告正文 |
| `quick_sample_size:466` | `"solved": result.solved` | 四族恒 `True`（探针：`quick_sample_size('anova', 0.01)['solved'] is True`） |

`solved` 字段的**跨层传递只到 t 族为止**；把四族接进 A′ 时，`post_hoc:307` 与 `runner:966` 两层吞点必须一起看——这条是归档 census `s924-05` 交给 `s924-04` 的硬顺序（台账 209⑧：「A′ 哨兵要穿两层吞点…**补 factorial 分支必须先上哨兵**」），今天仍然成立。

---

## 5. 三案矩阵（改动面／回滚成本，均不含数值主张）

| | **案甲 抛错** | **案乙 哨兵值（A′ 后四族）** | **案丙 扩界＋稳健求根** |
|---|---|---|---|
| 改哪些行 | C–F 四处 `except ValueError:` → `raise`（`:204/:247/:278/:324`，各 −1/+2 行） | 四处改为 `solved=False` ＋ `failure_reason` ＋ `n=0`，并把 `solved=`／`failure_reason=` 写进四处 `PowerResult(...)`（`:211-221`/`:253-261`/`:284-292`/`:331-339`），约 ±30 行 | 重排四族的搜索策略（先定位变号点再 brentq；或换 `sf`／正态近似），约 ±60–120 行，且**改动可解点的求解路径** |
| 现有用例 | 27 点零命中 ⇒ **不撞红**；但 `test_calculate_sample_size_rejects_unknown_test_type`（`:236` 只接 `"不支持的检验类型"`）与新抛错文本无冲突 | 同左 ⇒ **不撞红**；`format_power_report:392`／`quick_sample_size` 键集例已为哨兵态备好，无需改 | **会动到现值**：所有闭合例/快照例（`55/395/22/28/199/7/783/85/30/785/88/1194/39/128/162/198/85/88/92/46/24…` 等）都是它的可能波及面 ⇒ 属"重钉基线"，**人工闸** |
| 必须同笔的件 | 4 处生产码 ＋ **新用例**（否则零覆盖）＋ 若同时修 `runner:966` 的第二层吞点则再加 `tests/test_post_hoc_power.py` | 4 处生产码 ＋ 新用例 ＋（若要堵住 `n_subjects=0`）`design_engine.py:157-162` ＋ `tests/test_experiment_design_ui_detail_branch.py:463` 的 `solved` 条件化已有先例可复用 | 4（或 6）处生产码 ＋ 全部闭合/快照例重钉 ＋ 一份对外金标准对照表（s922-12 遗留 4 明写"那是另一单"） |
| 用户可见变化 | 生成流程**当场抛异常**（`_auto_power_analysis` 无 try ⇒ 直达 Streamlit 帧）；事后 power 在 `runner` 被吞成 `None` | 屏上从"一个数"变成「⛔ 无法给出样本量建议」；事后 power 走 `_unsolved_post_hoc` 显式哨兵 | 屏上数的**含义变了**（同一入参可能给出与历史报告不同的数） |
| 回滚成本 | 最低（4 处 `except` 逐字回退；无历史数据重算） | 低（4 处 ＋ 4 个构造器参数回退；`PowerResult` 字段本就存在，删引用即可） | **最高**（历史报告里的数与新数不可比，需重算策略；已产出的交付物无法复算同一态） |
| 与已入库口径的一致性 | 与 A′（t 族）反向：同一模块两种失败语义 | **与 A′ 同构**：沿用已落地的 `solved`／`failure_reason`／⛔ 报告分支，模块内语义统一 | 与 A′ 正交（可叠加在甲/乙之后做） |
| 是否触及统计数值 | 否 | 否（只把"拒答"扩到四族） | **是**——可解点数值可能变，属基线重钉＝人工闸 |

---

## 6. 推荐（材料级建议，不含任何数值口径）

1. **案乙**（A′ 向四族回移）——理由三条：①与本模块**已入库**的 t 族口径同构，不制造第二种失败语义；②改动面局限在四个 `except` 分支与四次构造器调用，不触碰任何可解点的公式；③回滚成本最低（逐字回退）。
   案丙不是"更差的甲/乙"，而是**另一件事**：它要重钉基线，按 s922-12 遗留 4 应单开金标准对照单。
2. **案乙要成立，必须同批做三件**（缺一件则等于把"假数"换成"看不见的数"）：
   ①四族新用例（触发点取自本文 §3.1，含卡方 `df+2 > n_hi` 的区间颠倒例）；
   ②`design_engine.py:157-162` 的 `solved` 读取（台账 215① 的在册项，不一起做就是"每组 0 人"继续下行）；
   ③`runner.py:966` 的 `except Exception → None` 与 `post_hoc` 哨兵的关系要说清（否则拒答与"没有建议"仍不可区分）。
3. **G（`design` 串静默退 2x2）与「✅ 缓冲带 0.02」两项建议单列**：前者是入参校验，改法是显式报错还是回显警告属产品口径；后者的**阈值数值**属判据改动，两把尺都不归执行手。
4. **本班未做的事**（守红线）：未改任何 `except`、未改任何区间上下界、未改 `0.02` 缓冲带、未改任何公式、未新增/删除用例、未 `git add`。

---

## 7. 复算入口

```bash
cd /d/code/psy-analysis
# 定向三跑（本班实跑原文）
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_power_analysis.py -q              # 67 passed
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_post_hoc_power.py \
    tests/test_experiment_design_ui_detail_branch.py -q                                               # 23 passed, 1 xfailed
# 触发用例（本文 §3）——⚠ 沙盒探针已在收班时删除（w40 §6「用完自己清」），
#   下面两行是**重建入口**：按 §3 的入参表（8 例）与 §3.2 的 27 点入参清单各写一支脚本即可复跑。
#   PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "<班目录探针>.py"
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "D:/code/tmp/qoder-executor-20260928-1440-psy91/probe_s927_40_siblings.py"
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "D:/code/tmp/qoder-executor-20260928-1440-psy91/probe_s927_40_testimpact.py"
```

⚠ 复算前提是 `HEAD=4294950` ＋ 上述 sha256；盘面一动，§2 行号即漂（census `s924-05` 记的 `:163-167/:206-210/:237-241/:283-287` 就已随 A′ 落码漂到本文的 `:201-205/:244-248/:275-279/:321-325`）。
⚠ 探针文件在班目录（`D:\code\tmp\qoder-executor-20260928-1440-psy91\`），**非仓内路径**；本班收班时清理，届时以本文 §3 的原文输出为准，或按上面命令重建探针。
