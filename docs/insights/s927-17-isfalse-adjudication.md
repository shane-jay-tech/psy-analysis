# s927-17 `assumption_router` 的 `is False` 身份比较：修法裁决材料（只读取证，零码改动）

- 班名：`qoder-executor-20260927-1940-psy79`（波次 28）；取证时刻 2026-09-27T19:41:27+08:00（`date` 现取）
- HEAD=`6cb3c96`；`git status --porcelain -- src/analysis/assumption_router.py` → **空（该件未改，工作树＝HEAD）**
- 判据：卷宗「完成标准」①4 处定位 ②三态行为差异表 ③推荐 ④零码改动
- 红线：本文只出**材料与写法真值表**；「None 算不算违反」与最终改法**不选案**（改的是生产码且直接影响统计建议链＝人工闸）

---

## 0 两句实况（两处否证，都不影响单子成立）

1. **「4 处」是搜索式产物，盘上现值 9 处。**
   `rg -c "is False" src/analysis/assumption_router.py` → **9**（HEAD 与工作树同）。
   卷宗/锚点口径的来源可复原：`rg "passed is False"`（属性式写法）只匹到 4 行（`:99 :103 :113 :128`）；另有 5 处同型缺陷写成 dict 取值式 `.get("passed") is False`（`:105 :115 :121 :130 :135`）被漏掉。
   锚点 `20260925-154314-4290` E1 自己列的是 6 处（`:99 :103 :113 :121 :130 :135`），**也漏 3 处**。
   ⇒ 任何「改这 4 处」的修法会原样留下 5 处同类；**改动面必须按 9 处计**。
2. **锚点给的「最小改法」两案不等价，其中一案有实测反证。**
   `x.passed is not True` 在 NumPy 2.5.1 下对 `np.bool_(True)` 也返回 True（`is not True` 走身份比较，`np.bool_(True) is not True` 成立）⇒ **把「通过」也判成违反**，逢 numpy 布尔必触发建议。真实 `check_normality` 双向读数见 §2.2。
   ⇒ 该案不能作为「最小改法」候选，必须从选项里划掉（这一条有磁盘证据，非意见）。

---

## 1 判据①：9 处定位与取道分类

$ rg --no-ignore -n "is False" src/analysis/assumption_router.py

| # | 行 | 谓词函数 | 取道 | 表达式 | 值的在世生产者（`rg` 实测） | 运行时真实类型 |
|---|---|---|---|---|---|---|
| 1 | `:99` | `_normality_violated` | 属性 | `norm.passed is False` | `assumptions.py:47/59`（`passed = p > alpha`） | `numpy.bool` |
| 2 | `:103` | `_normality_violated` | 属性（逐组） | `v.passed is False` | `check_normality_groups` → 同 `:47` | `numpy.bool` |
| 3 | `:105` | `_normality_violated` | dict | `v.get("passed") is False` | 序列化回流／卡层替身（见 §3.2） | `bool` / `None` |
| 4 | `:113` | `_homogeneity_violated` | 属性 | `homo.passed is False` | `assumptions.py:93/106` | `numpy.bool` |
| 5 | `:115` | `_homogeneity_violated` | dict | `homo.get("passed") is False` | `runner.py:122/137/152` ← `result.assumption_homogeneity` ← `anova.py:132`（`equal_var = levene_p > 0.05`，`anova.py:74`）、`anova.py:216`（**已包 `bool()`**）、`anova.py:588`（字面量） | `numpy.bool` / `bool` |
| 6 | `:121` | `_homogeneity_violated` | dict（旁路 result） | `ah.get("passed") is False` | 同上（`getattr(result,"assumption_homogeneity")`） | 同上 |
| 7 | `:128` | `_sphericity_violated` | 属性 | `sph.passed is False` | `assumptions.py:150/162` | `numpy.bool` |
| 8 | `:130` | `_sphericity_violated` | dict | `sph.get("passed") is False` | `anova.py:392`（`spher[1] > 0.05`，**未包 bool**）、`anova.py:465/717`、`anova.py:672`（**半包**：`bool(sph_pass) if pd.notna(...) else (float(p_sph) > 0.05)`） | `numpy.bool` / `bool` |
| 9 | `:135` | `_sphericity_violated` | dict（旁路 result） | `asph.get("passed") is False` | 同上 | 同上 |

**类型注解与运行时不符（根因位点）**：`assumptions.py:15 passed: bool`，而实测产出 `numpy.bool`（§2.2）。
**本仓既有「包 `bool()`」先例**：`anova.py:216`、`anova.py:672` ⇒ 归一化写法不是新发明，是同仓惯例未铺开。
**全仓同型写法对照**：`src/ui/items_upload_panel.py:157` `keep is False or (isinstance(keep, float) and pd.isna(keep))` —— 该处**显式处理 None/NaN 三态**，是「身份比较＋未知态」的在册正例，可作参照系（非缺陷）。

在世消费链（决定影响面）：`runner.py:958 decision = assumption_router.check_route(analysis_df, plan, output)` → `:960 output["routing"] = to_dict(decision)`（`:904` 预置 `None`）→ `src/ui/renderers.py:52 routing = output.get("routing")`。⇒ 修好即 UI 会出现新的路由建议；修坏（案B）则**所有 numpy 布尔的检验都会亮建议**。

---

## 2 判据②：三态行为差异表（全部为实测，非推演）

### 2.1 真值表

$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe <沙盒>/probe_isfalse.py （numpy 2.5.1）

| `passed` 取值 | 现状 `is False` | 案B `is not True` | 案C `bool(x) is False` | 案D `x == False` |
|---|---|---|---|---|
| `True`（Python） | False | False | False | False |
| `False`（Python） | **True** | True | True | True |
| `np.bool_(True)` | False ✅ | **True ❌（误报违反）** | False ✅ | False ✅ |
| `np.bool_(False)` | **False ❌（漏报）** | True ✅ | True ✅ | True ✅ |
| `None`（键缺失） | False | True（视为违反） | True（视为违反） | False |
| 键缺失（`.get` → None） | False | True | True | False |
| `int 0` | False | True | True | True |
| `float('nan')` | False | True | False（`bool(nan)=True`） | False |

→ 读法：**案B 是唯一有「把通过判成违反」实锤的选项**（对 `np.bool_(True)` 恒真），必须排除。
案C 与案D 只在 **None / nan / 0** 三个非布尔态上分岔：C 把 None 算违反、D 不算；两者都把 `nan` 算不违反（C 因 `bool(nan)=True`，D 因 `nan == False` 为假）；C/D 都会把 `0` 算违反。
案D 额外风险：`==` 若遇 `ndarray` 返回数组，进 `if` 会抛 `ValueError`（本仓生产者实测**无 ndarray 位点**，上表第七列按标量成立）。

### 2.2 真实生产者双向读数（不是手搓夹具）

$ PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "…from src.analysis import assumptions; check_normality(lognormal 40) / check_normality(normal 40)…"

| 用例 | `type(passed).__module__` | 值 | 现状 `is False` | 案B `is not True` | 案C |
|---|---|---|---|---|---|
| 违反（lognormal，Shapiro p=0.0） | `numpy`（`numpy.bool`） | `False` | **False（漏报）** | True | True |
| 通过（normal 40） | `numpy`（`numpy.bool`） | `True` | False | **True（误报）** | False |

⇒ 与锚点 `20260925-154314-4290` E1 的「真实违反不产出建议」同证；本表补上锚点未测的另一向：**案B 会把「通过」也产出建议**（逢 numpy 布尔必建议）。
⇒ 现状在真实路径上的净效果 = **9 处里 4 处属性式 + 5 处 dict 式中，凡值来自 scipy 比较的都恒 False**；只有走字面量早退（`assumptions.py:33/88/123/135`、`anova.py:588`）才产出建议——锚点 D 段（n=1 退化组）是**唯一在用出口**，这与本表一致。

### 2.3 测试面为何全绿（在册缺陷的成因，不复跑）

`tests/test_assumption_router.py:18-29` 的夹具 `_failed()/_passed()` 手写字面量 `passed=False/True` ⇒ `is False` 成立 ⇒ 测试恒绿。锚点 E5 已作此归因（**该缺陷在在册测试面是空白，不是测试红名**）。本班未跑 pytest，引该读数前请主班按需复算。

---

## 3 「None 视为违反」的语义合理性 —— 交人拍题（本班不选案）

判据本身落在统计建议链的行为改变上，属人工裁。把可查的盘面事实摊开：

### 3.1 只有 5 处 dict 取道存在 None
`AssumptionResult.passed` 注解为 `bool`（`assumptions.py:15`），生产位点 `:33/:47→:59/:88/:93→:106/:123/:135/:150→:162` **没有一个产 None** ⇒ #1/#2/#4/#7 四处（属性取道）**无所谓 None 语义**，改它们只需回答「np.bool_(False) 算不算违反」（答案显然是算，属机械修正）。
⇒ 「None 语义」这一题**只绑在 #3/#5/#6/#8/#9 五处**（dict 取道）。把两件事分开裁，可把红线题缩小到 5/9。

### 3.2 None 从哪里来（需要人确认的两条）
- 键缺失：`.get("passed")` 返回 None。本仓字面 dict 生产者（`anova.py:132/216/392/588/672`、`ttest.py:99`、`data_quality.py:279`）**都带 `passed` 键** ⇒ 常规路径上不产 None。
- 但「未知态」在本仓**已被建模**：`src/analysis/result_card.py:99 "passed": info.get("passed", None)`（在途件；`git show HEAD:src/analysis/result_card.py` 同一行在第 **90** 行，**HEAD 与工作树同形**，该件在途 diff `180 insertions(+), 13 deletions(-)` 未改这条语义）⇒ 卡层明确把 None 当「不知道」，与「按违反处理」的读法**语义相反**。
  ⇒ 若路由器把 None 判违反，同一个 `passed` 字段在 UI 的两处出口会得到相反解释（卡=未知、路由=违反）。这是要不要接受的分叉，请人裁。
- `src/analysis/field_lineage.py:511 "passed": "S26_model_spec"` —— 同名字段在该模块里是**血缘键（字符串）**，不是布尔。若任何回流把血缘结构喂进 `output["assumptions"]`，案C 会把 `"S26_model_spec"` 当「真值→不违反」、案D 当「不等 False→不违反」，两案同形，但说明 `passed` 这个键名在本仓**跨层复用**，扩语义前需确认无回流。回流路径本班未追（时间盒），列入遗留。

### 3.3 两种选择的后果（只列，不评好坏）
| 若 None 判「违反」 | 若 None 判「不违反」（维持现状方向） |
|---|---|
| 路由在假设信息不全时也会推非参/Welch 替代 → 用户可能被导向不必要的方法切换（`hard_route_allowed` 只在 n<20／n>5000 拦截，`assumption_router.py:150-154`） | 键缺失/未知继续静默 → 与卡层「未知」表达一致，但把现状的 fail-open 原样保留 |
| 与案C 的 `bool()` 语义天然一致（`bool(None) is False`） | 需要案D 或在案C 外单加显式 `is None` 分支 |

---

## 4 判据③：推荐（材料排序；选案权在人）

1. **先排除案B（`is not True`）**——有 §2.2 的实测反证（把通过判违反），这是零争议的一步。
2. **改动面按 9 处计**（§1），不要按卷宗的 4 处开工；否则 #3/#5/#6/#8/#9 五处留同类。
3. **首选「生产者侧归一」而非「消费者侧换算子」**：在 §1 表末列的比较式位点包 `bool()`（`assumptions.py:47/93/150`、`anova.py:74→132`、`anova.py:392`、`data_quality.py:279`、`ttest.py:99`），消费侧 9 处 `is False` 一行不动。
   理由：① 一次修完 9 处的共同根因（类型谎言 `passed: bool` vs `numpy.bool`）；② **不引入 §3 的 None 语义决策**（None 本来就不出现在属性取道）；③ 同仓已有先例 `anova.py:216/672`；④ 改动点少且逐个可测。
   ⚠ 但这仍是改生产码且直接改变统计建议链的运行时输出 ⇒ **人工闸，本班未改**。
4. 若不动生产者：案C（`bool(x.passed) is False`）比案D 稳（不依赖 `==`、不受 ndarray 歧义影响），但**必须显式写 None 分支**并按 §3 由人定语义，否则「None→违反」是顺带发生的，不是被批准的。
5. **不论选哪条，测试夹具必须同批改**：`tests/test_assumption_router.py:18-29` 的字面量夹具是当前假绿的成因；建议加「用真实 `assumptions.check_normality` 产出对象」的回归测（草案见 §5），并参照本仓反自证式快照守卫的在册写法（`tests/test_assumption_route_count_pin.py:160-171` 钉「活对象不是替身」）。

---

## 5 测试草案（**未落盘**，供放行后直接取用）

```python
# tests/test_assumption_router_tristate.py（草案）
import numpy as np, pandas as pd, pytest
from src.analysis import assumptions
from src.analysis.assumption_router import _normality_violated, _homogeneity_violated, check_route

@pytest.mark.parametrize("value,expect_violated", [
    (True, False), (False, True),
    (np.bool_(True), False), (np.bool_(False), True),      # 现状漏报的两例
    (None, None),   # ← None 期望值由主班裁（True/False 二选一）后落定，不留 None
])
def test_normality_predicate_tracks_numpy_bool(value, expect_violated):
    if expect_violated is None:
        pytest.skip("None 语义待人工裁决（s927-17 §3）")
    out = {"assumptions": {"normality": assumptions.AssumptionResult(
        test_name="Shapiro-Wilk", statistic=0.85, p_value=0.001,
        passed=value, message_zh="", suggested_action="")}}
    assert _normality_violated(out) is expect_violated

def test_real_check_normality_is_not_silently_ignored():
    """反『手搓字面量假绿』：用真实生产者，不用夹具。"""
    s = pd.Series(np.random.default_rng(9).lognormal(3, 1.0, 40))
    r = assumptions.check_normality(s)
    assert r.passed is False or type(r.passed).__module__ == "numpy", "类型回归：若已归一为 Python bool，此断言自动收紧"
    assert _normality_violated({"assumptions": {"normality": r}}) is True

def test_dict_sites_homogeneity_np_bool():
    """#5/#6：runner 把 result.assumption_homogeneity 原样塞进 output（runner.py:122/137/152）。"""
    out = {"assumptions": {"homogeneity": {"passed": np.bool_(False), "p_value": 0.0}}}
    assert _homogeneity_violated(out) is True
```

（草案只覆盖 #1/#4/#5 三类代表；放行后应扩到 9 处逐位钉，防「改 4 留 5」复发。）

---

## 6 判据④：零码改动自证

- 未改任何被跟踪文件；未 add／commit／checkout／restore／stash／clean；在途 8 枚 ` M` 件只读（`assumption_router.py` 本身不在途）。
- 探针与沙盒件只落 `D:\code\tmp\qoder-executor-20260927-1940-psy79\`（`probe_isfalse.py`），仓根零残留。
- `data/` 零写：本班探针为纯内存（`pd.Series`/`np.random`），未开库；`data/` 全树指纹 187 文件／21,103,172 B 跑前后 `cmp -s` 一致（见 result 证据节）。
- **未跑 pytest**；在册红 `test_export_gate_global_scan` 未复跑、未归因；未触 `tests/test_paper_writer.py::TestLiteratureManager::test_online_search_graceful`（该件无 `@pytest.mark.online`，禁联网口径下会静默外呼 CrossRef——本班不需要文献链子集）。
- 解释器全程 `.venv\Scripts\python.exe`（numpy 实装 2.5.1，与 `requirements-lock.txt` 4 处不符一事本班不处置，重钉 lock＝人工闸）。

---

## 7 交人工／遗留

1. §3「None 算不算违反」＝行为决策，**本班未选案**；建议与 `result_card.py` 卡层三态语义一并裁（两者对同一字段读法相反）。
2. `passed` 键跨层复用（`field_lineage.py:511` 是字符串血缘键）是否有回流进 `output["assumptions"]` 的路径——本班未追（时间盒 25 分钟），需人确认后再定「归一化」清单是否穷尽。
3. 生产码归一（§4.3）＝人工闸；放行时请一并要求「9 处全覆盖 + 夹具同批改」，否则会出现「修了属性路、留下 dict 路」的新空白。
4. §2.3 的「测试假绿」归因引自锚点 E5＋本班读夹具行号（`tests/test_assumption_router.py:18-29`），**未复跑该件**；主班若要引用请现跑。
