# psy power_analysis 求解器缺陷修复设计稿（s923-03 · 2026-09-23）

> **性质：只读出稿，不改码。** 本文是设计稿，不是变更说明。
> 取证 HEAD：`f9b93c0`（全 sha `f9b93c099fe0fae950dd376f882f97542a3efa76`），取值时刻 2026-09-23 02:1x。
> `src/experiment_design/` 本单零改动（自证见第 7 节）。
> **统计数值红线**：本文列出的是「求解器返回了什么数」这一**实现事实**，
> 不为任何样本量结论背书，也不主张把任何数值改成什么；选哪个出口、改哪张卡，一律交主班＋owner 拍板。

---

## 1. 缺陷本体（两处，均已实测复现）

### D1 · 搜索失败被兜底成「区间上界」

`_solve_n_for_t_test` 用 `brentq` 在固定区间上求根。求根失败时 `except ValueError` 不报错，
而是**直接把区间上界当答案**：

| 位置 | 设计 | 搜索区间 | 兜底赋值 |
|---|---|---|---|
| `power_analysis.py:81-85` | 配对 t | `[2, 2000]` | `n = int(np.ceil(n_hi))` → **2000** |
| `power_analysis.py:115-118` | 独立 t | `[4, 4000]` | `N = N_hi` → **4000** |

同型写法另在 4 处（本次一并实测，见第 3.3 节）：`:164-167`（单因素 ANOVA，hi=2000）、
`:207-210`（相关，hi=3000）、`:238-241`（卡方，hi=5000）、`:284-287`（多因素，hi=2000）。
（`:264-267` 是 `design` 串解析失败退回 `"2x2"`，性质不同，已由 `tests/test_power_analysis.py:225` 钉住，不在本稿范围。）

### D2 · 兜底产物再经 NaN 盲比较透出成「✅ 达标」

兜底之后代码**又用上界回算一次效力**（`:87` / `:123`），大 df ＋ 大非中心参数处 scipy 返回 **NaN**，
于是 `actual_power=NaN` 进结果对象。下游 `format_power_report:380`：

```python
if result.actual_power < result.power - 0.02:      # NaN < 0.78 → 恒为 False
    lines.append("- ⚠ 实际效力略低于目标…")
else:
    lines.append("- ✅ 实际效力达到目标水平。")      # ← 永远走这条
```

⇒ 用户看到的完整报告长这样（`d=0.8` 独立 t，实测原样）：

```
## 统计效力分析报告
**检验方法：** 独立样本t检验
**预设效应量：** Cohen's d = 0.80（大效应）
- **所需总样本量：** N = **4000**
- **每组样本量：** n = **2000**（共2组）
- **实际达到效力：** 1-β ≈ nan          ← 明知是 nan
- **检验自由度：** df = 3998
### 建议
- ✅ 实际效力达到目标水平。              ← 紧邻着说达标
- 📊 …建议在计算基础上增加10%-20%的被试量。  ← 还要在 77 倍过检的数上再加
```

「`1-β ≈ nan`」与「✅ 实际效力达到目标水平」在同一屏，是本稿认为**优先级最高**的一处。

⚠️ **比来账更宽**：`zcode-bridge/done/s922-12-psy-power-n-solvers.result.md` 记的是
「独立 d=0.3/0.5/0.8、配对 d=0.3/0.4/0.5 共 6 点」。本次加密网格重测，实际污染 **11 点**，
且 **11 点全部透出 ✅**（不只它说的 2 个 NaN 点）。见第 3 节。

---

## 2. 为什么会走进兜底（机理，供选择出口时判断可行性）

`brentq` 要求 `f(n_lo)` 与 `f(n_hi)` 异号。本模块 `f(n) = power_at_n(n) - power`：

- **n 很大时 `power_at_n` 不是单调稳定量**。效力理论上随 n 趋近 1，但在大 df ＋ 大 ncp 处
  `nct.cdf` 数值溢出 ⇒ 返回 **NaN** ⇒ `f(n_hi)` 为 NaN ⇒ `brentq` 抛
  `ValueError: The function value at x=… is NaN; solver cannot continue.`
- 于是**「效应量越大」反而越容易触发兜底**（d 大 ⇒ ncp 大 ⇒ 更容易 NaN）。
  这与直觉完全相反，也是它能长期存活的原因：d=0.2 这种"最难"的场景恰好是**对的**，
  而 d=0.8 这种一眼就该过的场景是错的。实测印证：独立 t **d=0.20→788 正确、d=0.40→200 正确，
  中间 d=0.30/0.50/0.60/0.70/0.80 全错**。
- 因此 s922-12 那句「污染不随 d 单调」是准确的，本稿沿用并加密到 7×2 网格。

---

## 3. 污染点数值表（每条都可 `python -c` 级内联复跑）

### 3.1 t 检验族（`power=0.80, alpha=0.05`）

**复跑命令**（一条出整张表）：

```bash
cd /d/code/psy-analysis && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import warnings, numpy as np; warnings.filterwarnings('ignore')
from src.experiment_design.power_analysis import _solve_n_for_t_test, format_power_report
for paired, hi in ((True,2000),(False,4000)):
    for d in (0.2,0.3,0.4,0.5,0.6,0.7,0.8):
        r=_solve_n_for_t_test(d,0.80,0.05,paired)
        print('paired' if paired else 'indep', d, r.required_n,
              'ceil_hit' if r.required_n>=hi else 'ok', r.actual_power,
              'FAKE-GREEN' if '✅ 实际效力达到目标水平' in format_power_report(r) else '')
"
```

**「真值」口径声明**（避免被误读成本稿背书的外部结论）：下表 `真值n` =
**以被测模块自身的 power 口径**，从搜索下界起逐个整数扫描、首个使 `power ≥ 0.80` 的 n。
参照函数用 `tests/test_power_analysis.py:58/68` 里既有的 `power_independent_t` / `power_paired_t`，
不是本稿另起的一把尺子。已知点与 `tests/test_power_analysis.py:238/248` 两句 docstring
（"真值应为 N=351/128/52"、"n=90/52/34"）**逐一吻合**，故口径一致。

| 设计 | d | 求解器返回 | 命中上界 | 真值 n | 过检倍数 | actual_power | 报告判定 |
|---|---|---|---|---|---|---|---|
| 配对 | 0.20 | 199 | 否 | 199 | 1.0x | 0.8017 | 正常 |
| 配对 | **0.30** | **2000** | **是** | 90 | **22.2x** | **nan** | ⛔ 假绿 |
| 配对 | **0.40** | **2000** | **是** | 52 | **38.5x** | 1.0000 | ⛔ 假绿 |
| 配对 | **0.50** | **2000** | **是** | 34 | **58.8x** | 1.0000 | ⛔ 假绿 |
| 配对 | **0.60** ★新 | **2000** | **是** | 24 | **83.3x** | 1.0000 | ⛔ 假绿 |
| 配对 | **0.70** ★新 | **2000** | **是** | 19 | **105.3x** | 1.0000 | ⛔ 假绿 |
| 配对 | **0.80** ★新 | **2000** | **是** | 15 | **133.3x** | 1.0000 | ⛔ 假绿 |
| 独立 | 0.20 | 788 | 否 | 787 | 1.0x | 0.8006 | 正常（另见最小性缺陷 D3） |
| 独立 | **0.30** | **4000** | **是** | 351 | **11.4x** | 1.0000 | ⛔ 假绿 |
| 独立 | 0.40 | 200 | 否 | 199 | 1.0x | 0.8036 | 正常 |
| 独立 | **0.50** | **4000** | **是** | 128 | **31.2x** | 1.0000 | ⛔ 假绿 |
| 独立 | **0.60** ★新 | **4000** | **是** | 90 | **44.4x** | 1.0000 | ⛔ 假绿 |
| 独立 | **0.70** ★新 | **4000** | **是** | 67 | **59.7x** | 1.0000 | ⛔ 假绿 |
| 独立 | **0.80** | **4000** | **是** | 52 | **76.9x** | **nan** | ⛔ 假绿 |

★新 = s922-12 未测到、本次加密网格新增的 5 个污染点。
**14 个测点里 11 个被污染，污染率 79%；两个设计族各自只有 d=0.20（独立再加 0.40）是好的。**

> 注意最坏一行是**缺省路径**：`quick_sample_size("t_test")` 与
> `calculate_sample_size("t_test")` 的缺省 `effect_size=0.5` 正落在污染区 ⇒
> **不调参数的用户拿到的就是 4000**（实测 `required_n=4000, actual_power=1.0`）。
> 已由 `tests/test_power_analysis.py:328` 钉成现状。

### 3.2 相关族：同型兜底，但**污染方向相反**（欠配）

`t` 族是"真值远小于上界"⇒ **过配**；相关族在极小 r 处是"真值大于上界"⇒ **欠配**。同一条 `except`，两种错法。

```bash
cd /d/code/psy-analysis/tests && PYTHONIOENCODING=utf-8 ../.venv/Scripts/python.exe -c "
import warnings, sys; warnings.filterwarnings('ignore'); sys.path.insert(0,'..')
from test_power_analysis import power_correlation
from src.experiment_design.power_analysis import _solve_n_for_correlation
for r in (0.05,0.04,0.03):
    truth=next(n for n in range(5,20000) if power_correlation(n,r)>=0.80)
    res=_solve_n_for_correlation(r,0.80,0.05)
    print('r=',r,'求解器=',res.required_n,'真值=',truth,'actual=',round(float(res.actual_power),6))
"
```

| r | 求解器返回（上界） | 真值 n | 方向 | actual_power | `:380` 判据 `actual < 0.78` | 报告 |
|---|---|---|---|---|---|---|
| 0.05 | 3000 | **3138** | **欠配** | 0.782177 | False（差 0.0022 就判⚠） | ⛔ **✅ 达标** |
| 0.04 | 3000 | **4904** | 欠配 63% | 0.591359 | True | ⚠ 但建议只加 `int(3000*0.15)=450` ⇒ 3450，**仍差 1454**（覆盖缺口的 23.6%） |
| 0.03 | 3000 | **8719** | 欠配 191% | 0.375732 | True | ⚠ 同口径仍只加 450 ⇒ 3450，**仍差 5269**（覆盖缺口的 7.9%） |

⇒ 两点补充结论：
1. **`:380` 的 0.02 容差本身就是一条窄门**：r=0.05 差 0.002177 就翻到 ✅ 侧。
2. **⚠ 分支的 `+15%` 是硬编码比例**（`:381`，`int(result.required_n * 0.15)`），
   它的隐含假设是"缺口≤15%"，而兜底场景的缺口可以是 63%~191% ⇒ 即便走到了 ⚠，建议量仍是错的。

### 3.3 另外三个同型点：本次实测**未见污染**（但要连坐修）

| 位置 | 族 | 网格 | 命中上界 |
|---|---|---|---|
| `:164-167` | 单因素 ANOVA（hi=2000） | f∈{0.10,0.25,0.40} × k∈{2,3,5} = 9 点 | **0**（n 落在 21~395） |
| `:238-241` | 卡方（hi=5000） | w∈{0.1,0.2,0.3,0.5} × df∈{1,2,4} = 12 点 | **0**（n 落在 32~1194） |
| `:284-287` | 多因素（hi=2000/组） | f∈{0.10,0.25} × {2x2,2x3} = 4 点 | **0**（32~197/组） |
| `:207-210` | 相关（hi=3000） | r∈{0.05…0.50} = 6 点 | **1**（r=0.05，见 3.2） |

⇒ 修复若只做在 t 族，这 3 处仍是**同一枚未爆的雷**（上界更小的参数区一定会撞上）。
设计稿建议：抽公共求解工具，五处一起收口（见第 4 节出口 A′/B）。

### 3.4 顺带实测到的 D3（独立 t 的"最小性"缺陷，与 D1 不同源）

`:101-103` 的 `int()` 截断使 `power_at_total` 对 N 不单调：N=787（393/394）的效力 ≥ N=788（394/394）。
已由 `tests/test_power_analysis.py:131` 显式钉住（并特意注明"免得后来人误以为闭合测试已隐含最小性"）。
**D3 不在本稿三出口的目标内**，但任何改动 `power_at_total` 取整方式的方案都会惊动它 ⇒ 列此备忘。

---

## 4. 三出口对比

### 前置事实（决定各出口代价，均已实测）

| 事实 | 读数 | 影响 |
|---|---|---|
| 消费方 1 | `src/analysis/post_hoc_power.py:244-276`：6 处 `calculate_sample_size` 包在 **`try: … except Exception: return None`** 里 | 求解器一旦改为抛错，这里**静默变 None**——把"错数字"变成"没数字"，且无日志 |
| 消费方 2 | `src/experiment_design/design_engine.py:685-693`（`_auto_power_analysis`）→ `:571 format_power_report` | 走 markdown 导出 |
| UI 直连 | `app.py` **无** `experiment_design.power_analysis` 直接调用（`grep 样本量\|效力分析\|quick_sample_size -- app.py` 只命中 4 处无关文案） | 爆炸面不在主页，收敛成本低 |
| 既有契约 | `calculate_sample_size("nope")` → `ValueError: 不支持的检验类型: nope`（实测） | 本模块**已有"抛 ValueError"的先例**，出口 A 不算破接口风格 |
| 现状钉桩 | `tests/test_power_analysis.py`：**6 个函数 / 11 个用例实例**显式带 `currently`，docstring 反复写「**现状而非认可**」 | 翻正是**预期动作**，不是破坏稳定 |

> 📌 这 11 实例的分解：独立上界 3 ＋ 配对上界 3 ＋ NaN 透出 2 ＋ 「闭合≠最小」1 ＋ 坏 design 串 1 ＋ **缺省 quick 路径 1**。
> `s922-12` 自报的是「10 例」，**漏计了 `:328` 那条缺省 `quick_sample_size("t_test")` 继承上界的桩**——
> 而按第 3.1 节，那条恰恰是**不传参用户唯一会撞上的**一条。取证命令：
> `.venv/Scripts/python.exe -m pytest tests/test_power_analysis.py --collect-only -q \| grep -c currently` → **11**。

### 出口对比表

| 维度 | **A 显式失败** | **A′ 显式失败＋哨兵值**（A 的改良） | **B 扩界＋精度替代** | **C 最小修堵假绿** |
|---|---|---|---|---|
| 做法 | 五处 `except ValueError:` 由"赋上界"改为 `raise`（或返回带 `solved=False` 的结果） | 不抛，改在 `PowerResult` 加 `solved: bool` ＋ `failure_reason`；报告遇 `solved=False` 走"无法求解"分支 | 上界提到真值可能之上（相关族 ≥20000）；并绕过 NaN：先用粗网格扫出首个达标整数，或改 `brentq` 为二分/`xatol` 放宽 | 只把 `format_power_report:380` 判据改成 `not (actual >= power - 0.02)`，令 NaN 落进 ⚠/❓；兜底本身不动 |
| 消掉 D1？ | ✅ 彻底 | ✅ 彻底 | ✅（前提是界够大且无 NaN） | ❌ 完全没动 |
| 消掉 D2？ | ✅（不再产 NaN） | ✅ | ⚠ 部分：仍可能有别处 NaN | ✅ 只消 NaN→✅ 这一条通路 |
| 会不会给出**错数字** | 不会 | 不会 | 不会（若界真够大） | **会**——4000 照样返回，只是不再说"✅" |
| 对 `post_hoc_power.py:275` 的影响 | ⚠ **危险**：`except Exception: return None` 会把失败吞成 None，需**同步改**该处 | ✅ 无需抛错，消费方读 `solved` 即可 | 无 | 无 |
| 数值稳定性风险 | 低 | 低 | ⚠ 高：扩界会让**更多**点走进 NaN 区（3.1 已见"越大的 n 越容易 NaN"），可能把今天的"正确点"变成新的兜底点；须先验证 | 低 |
| 改动量 | 5 处 `except` ＋ 1 处消费方 ＋ 报告分支 ＋ 契约文档 | 数据结构 1 处 ＋ 报告 1 处 ＋ 5 处 `except` 赋哨兵 | 算法段重写（≈1 个数值方法改造） | **1 个布尔表达式** |
| 现有用例翻正量 | **9 实例**（第 5 节四个缺陷函数）＋ 连动 2 处 ＋ 可能新增分发用例 | 9 实例 ＋ `solved` 字段快照（`test_power_analysis.py:302` keyset 用例连带红） | 上界类 6 实例必红（答案变了）＋ NaN 2 ＋ 缺省 1；`:119`/`:142` 正确侧哨点**应保持绿**（天然的修复对照面） | **仅 2 实例**（`:254`）翻红，其余 7 个缺陷实例**原样保留**——因为 4000 这个数它根本没改 |
| 用户可见效果 | 明确看到"算不出来" | 明确看到"算不出来"＋原因 | 拿到正确样本量 | 看到 "N=4000 ＋ ⚠/❓"，仍会照抄 4000 |
| 主要风险 | 消费方吞异常 ⇒ 变成静默缺席（新假绿面） | 新字段成为第三套契约，需文档同步 | 工作量大且**可能自造新污染**；需数值实验 | **最危险**：把"错得离谱"伪装成"略有保留"，缺陷本体存活 |
| 符合红线程度 | 高（不产结论值） | 高 | 高 | ⚠ 中：4000 仍在输出面上 |
| 一次性收口 5 处 | ✅ | ✅ | ⚠ 逐族调界 | ❌ |

**推荐（仅建议，不代拍板）**：**A′ 为主 ＋ B 为后续**。
理由三句：① A′ 是唯一能同时消掉 D1/D2 **又不被 `post_hoc_power.py:275` 的裸 `except Exception` 吞掉**的出口（这是 A 的致命伤，实测已坐实）；
② B 单独做不安全——3.1 的证据显示"把界推大"恰好把更多点推进 NaN 区，必须先有 A′ 的失败可见性再谈扩界；
③ C 便宜但它做的正是本稿定义的问题本身（把不可信结果说得像可信），建议**只作为 A′ 落地前的临时止血**，且必须连 `:381` 的 `+15%` 硬编码一起处理（见 3.2 第 2 点），否则 ⚠ 分支同样在骗人。

**无论选哪个，这两条是前置件**（属实现缺陷，不属统计结论）：
- `post_hoc_power.py:275` 的 `except Exception: return None` 要么收窄到具体异常，要么加日志——
  否则任何"显式失败"方案到这里都会退化成静默缺席。
- `format_power_report:380` 对 NaN 恒 False 这一条，任何出口都要覆盖（A′/B 是靠不产 NaN 覆盖，C 是靠改判据覆盖）。

---

## 5. 需同步翻正的钉桩清单

全部在 `tests/test_power_analysis.py`，均为 `s922-12` 刻意留的「现状而非认可」桩。**本单一条没改。**

| 行号 | 用例 | 现在钉的是什么 | 哪个出口会让它红 | 翻正后的断言方向 |
|---|---|---|---|---|
| `:232-243` | `…_independent_currently_returns_the_bracket_ceiling`（参数 d=0.30/0.50/0.80 → 4000） | 兜底返回上界 | A/A′/B | 断言 `required_n` 等于 docstring 已写的真值 351/128/52；**建议参数扩到 0.30/0.50/0.60/0.70/0.80 五点**（3.1 新测的 0.60/0.70 现无覆盖） |
| `:246-251` | `…_paired_currently_returns_the_bracket_ceiling`（d=0.30/0.40/0.50 → 2000） | 同上（配对） | A/A′/B | 真值 90/52/34；**建议扩到 0.60/0.70/0.80**（真值 24/19/15） |
| `:254-264` | `test_t_test_ceiling_can_leak_a_nan_actual_power_currently`（`(False,0.80)`、`(True,0.30)`） | NaN 进对象 **且** 报告出现 `"nan"` ＋ `"✅ 实际效力达到目标水平。"` | **A/A′/B/C 全部** | 反向断言：`actual_power` 非 NaN，且报告含 ✅ 时 `actual_power ≥ power − 0.02` 必须成立 |
| `:328-330` | `test_quick_sample_size_defaults_to_d_half_and_inherits_the_ceiling_currently` | 缺省 `quick_sample_size("t_test")` → 4000 | A/A′/B | 缺省路径落到真值 128；**这条最该翻**，因为它钉的是不传参用户拿到的数 |
| `:131-139` | `…_is_not_minimal_under_n_minus_one_currently` | 独立 t 取整导致 N−1 也达标（D3） | 仅当改动 `:101-103` 取整方式时 | 属 D3，与本稿两缺陷不同源；若做 B 要一并评估 |
| `:119-128` | `…_independent_closes_at_d_020` | d=0.20 → 788 正确 | 预期**保持绿**（回归对照面） | 不动，用作"修复没把好的那侧弄坏"的哨点 |
| `:142-145` | `…_paired_closes_and_is_minimal`（d=0.10/0.15/0.20） | 配对族低 d 正确 | 预期**保持绿** | 同上哨点 |
| `:302` | `test_quick_sample_size_keyset_and_mirrors_calculate_sample_size` | 返回 dict 的**键集快照** | **A′ 专属**：加 `solved` 字段必红 | 键集快照需同步 ＋1 键（纪律档 §5.4：这是纯增量 ＋N，可直接保留） |
| `:333` | `test_format_power_report_snapshot_single_group` | **整段文本快照**（版式/百分号/小数位） | A/A′/C 若改报告文案则红 | 文案改了就要回写快照；本稿刻意**不预测新文案** |
| `:225` | `test_factorial_anova_bad_design_string_falls_back_to_2x2_currently` | `:264-267` 解析兜底 | 仅当把 5 处兜底抽公共工具时可能连带 | 备忘：抽公共件别顺手改掉这处不同性质的兜底 |

⚠️ **翻正口径提醒**（纪律档 §四 psy 条：判"某件有无单测"要先查是否被标跳过）：上述桩今天**全在真跑**，
`tests/test_power_analysis.py` 收集 **55 例、全绿、零 skip**（读数见第 7 节），所以这些"现状钉桩"不是假象覆盖。
`s922-12` 那句「现状钉桩 10 例」里有 **2 例其实是"正确侧哨点"而非缺陷桩**（`:119` 独立 d=0.20→788、
`:142` 配对 d=0.10/0.15/0.20），**真正要翻正的是 4 个函数 / 9 个用例实例**：
`:232`（3）＋ `:246`（3）＋ `:254`（2）＋ `:328`（1）。
另 **2 处属连动面**（不是缺陷桩，但改了字段/文案必红）：`:302` 键集快照、`:333` 整段文本快照。
剩下 `:131`（D3 最小性）与 `:225`（坏 design 串）本稿判为**不同源、不动**。

---

## 6. 待主班／owner 裁决清单（本单一律未动）

1. **选哪个出口**（A / A′ / B / C / A′→B 分期）——本稿建议 A′ 主、B 续、C 仅作临时止血。
2. **`post_hoc_power.py:275` 的裸 `except Exception: return None` 是否随单收窄**——它是任何"显式失败"方案的前置件，但改它属**另一个模块的行为改动**。
3. **`format_power_report:381` 的 `+15%` 硬编码缓冲**要不要一并处理（3.2 已证它在欠配场景下给出的建议量仍严重不足）。
4. **`PowerResult` 加字段**（A′）是否触及 `data/benchmark_history` 快照口径（本单未触该目录，见第 7 节）。
5. **D3（取整最小性）**是否并入同一张票。
6. 上述任一条落地后 `tests/test_power_analysis.py` 的翻正清单（第 5 节）。

---

## 7. 本单自证：`src/experiment_design/` 零改动

```bash
cd /d/code/psy-analysis
git --no-pager diff --name-only -- src/experiment_design/      # → 空
git status --porcelain -- src/experiment_design/ tests/test_power_analysis.py   # → 空（两件都干净）
git --no-pager log --oneline -3 -- src/experiment_design/power_analysis.py
#  → ec45485 2026-06-01 chore: 初始化版本库 + .gitignore，清理 __pycache__   ← 仅此一枚提交
```
⇒ `power_analysis.py` **自建仓以来零改动**，因此第 3 节测出的 11 点污染
**不是 s922-12 之后引入的回归**，而是那次采样只测了 6 个点、本稿把网格加密到 14 个点的结果。

```bash
.venv/Scripts/python.exe -m pytest tests/test_power_analysis.py -q
# → 55 passed in 3.17s          （零 skip、零 xfail ⇒ 11 个现状钉桩实例今天全部真跑）
.venv/Scripts/python.exe -m pytest tests/test_power_analysis.py --collect-only -q | grep -c currently
# → 11
```

**红线自证**：本稿未改任何生产码、未改任何测试常量、未写库、未联网、未调 LLM、零积分；
文中所有样本量数字都是「求解器当前返回了什么」的**实现事实读数**，
其"真值"列另明确声明为「按模块自身 power 口径整数扫描」，**不作为对外效力分析结论背书**。
不变量 `data/benchmark_history/` 逐文件 sha256_8 与开工基线逐位相同：
`3d83f7e9 / dff47515 / 092d61b0 / 909b4799`。

---

## 附：一句话总结

**这条链上有两个缺陷叠在一起**：`except ValueError: n = 上界` 把"算不出来"伪装成"算出来了"，
`NaN < x` 恒 False 又把这份伪装判成"✅ 达标"。前者在 5 处同型、后者在报告出口单点。
t 检验族 14 个常规效应量测点里 11 个中招、过检 11~133 倍，而缺省参数（`d=0.5`）正好落在中招区；
相关族则在极小 r 处朝反方向中招（欠配 63%~191%）。**最小修（只改 NaN 判据）能堵住最刺眼的那句 ✅，
但它会让系统继续输出 4000 这个错数** —— 这是本稿不建议只走 C 的唯一理由。

---

## 勘误（s927-62 追加 · 2026-09-29T05:0x 现取 · 纯插入，上文一字未改）

- 追加班：`qoder-executor-20260929-0450-psy102`（信箱单 `s927-62`）；HEAD `4d3608e`。
  开工前置自检：`git status --porcelain -- docs/insights/psy-power-solver-redesign-20260923.md` → 0 行（干净 ⇒ 工作树==HEAD）。
- 勘误来源：`docs/insights/psy-power-sibling-fallback-census-20260924.md` §9 待订正清单第 3、4 条（该清单由 `s924-05` 产出）。
- 形态约束：原正文（含 `:180`/`:181` 两行表格）**未改一字**；本段只做追加，`git diff --numstat` 删除列为 0。

| 本稿位置 | 本稿原写法 | 现读（命令 → 值） | 该怎么读 |
|---|---|---|---|
| `:180`（消费方 1） | 「`src/analysis/post_hoc_power.py:244-276`：**6 处** `calculate_sample_size`」 | `rg -c "calculate_sample_size\(" src/analysis/post_hoc_power.py` → **5** | 计数取 **5**；`244-276` 这个区间也过期（A′ 落地后 `post_hoc_power.py` 已被 `2f08c60`/`7d1f05f` 改写，行号一律现取） |
| `:181`（消费方 2） | 「`src/experiment_design/design_engine.py:685-693`（`_auto_power_analysis`）→ `:571 format_power_report`」 | `rg -n "def _auto_power_analysis" src/experiment_design/design_engine.py` → **`:755`**；`rg -n "return calculate_sample_size" …` → 7 处 **`:759/:761/:763/:765/:767/:769/:771`** | 函数体实跨 `:755-:771`，**6 行宽的区间圈不住**（本稿少列 2 个 return）；`→ :571` 未复核，引用前现取 |

⚠ 两条纪律提示（写给下一个引用本稿的人）：
① 本稿的行号是 2026-09-23 的快照，`src/experiment_design/{power_analysis,design_engine}.py` 与 `src/analysis/post_hoc_power.py` 此后均被改写过 ⇒ **任何行号引用前必跑上表命令**；
② `design_engine.py` 在 2026-09-29 凌晨刚随 `7d1f05f`（s927-72）入库，引用时按 HEAD／工作树双报（本班验该档与本档此刻均干净，故单值即可）。

