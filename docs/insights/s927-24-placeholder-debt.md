# s927-24 —— `_METHOD_ASSUMPTIONS` placeholder 债清单（两类）＋登记修正草案

- 班：`qoder-executor-20260928-0120-psy83`｜波次 40 文档／裁决材料位｜仓 `D:\code\psy-analysis`｜HEAD 现取＝`f0f3f73`（开工 porcelain 12）
- 卷宗锚点：`20260925-154313-ae49.result.md`（卷宗写 `outbox/`，实际在 **`done/`**——按 brief §3 属路径搬家，不判 failed）
- 🔴 **本班只出材料**：零码改动、零 git 写操作、**不写任何统计计算**（补实现＝造统计计算＝红线人工闸，本班不自修）、**不判定任何假设是否成立／任何检验是否通过**。
- 注册表本体：`src/analysis/assumption_router.py:272-367`（`_METHOD_ASSUMPTIONS`）

---

## 1. 结论摘要（含对卷宗／锚点口径的三处修正）

注册表现值：**15 法／existing 12 条／placeholder 45 条**（`describe_assumption_routes()` 实测，命令见 §5）。

| 类 | 条数 | 含义 |
|---|---|---|
| **类 I｜已实算被误登记** | **6 / 45** | 同仓已有计算与阈值告警，注册表却写 placeholder |
| **类 II-A｜真缺失・可自动检验** | **30 / 45** | 无实现，但有标准做法可补（多数依赖已在 `.venv`） |
| **类 II-B｜真缺失・结构性／语义性** | **9 / 45** | 不该由统计检验承担（设计属性／代码构造保证），宜改文案口径而非补实现 |
| 合计 | 45 | ✅ 与注册表逐条对齐 |

**对卷宗／锚点口径的三处修正（本班实测）**：

1. **卷宗标题「12 条线性假设＋VIF 已实算被误登记」混计了两种语义**：12 条含「线性」字样的条目里，**6 条是"多重共线性"族、6 条是"线性关系"族**（子串"线性"撞车）。共线性族恰恰是**唯一有实算**的那族，线性关系族一条都没实算。按标题去批量翻牌会把 5 条真缺失翻成 existing。
2. **「VIF 已实算」只覆盖同名两条中的一条**：`regression.py:131` 的 `_calc_vif` 只在 **multiple_regression** 路径调用；`hierarchical_regression`（`regression.py:195` 起）**全文不碰 `_calc_vif`**（grep 空命中）。⇒ `hierarchical_regression「自变量间无严重多重共线性（VIF）」` 属**类 II-A 真缺失**，不能跟着名字一起翻。
3. **注册表在生产运行时零消费者**（本班全仓复核）：`get_assumption_set` 命中只有 1 个测试件（`tests/test_two_way_anova_route.py:62`）＋兄弟班 tmp 探针；`describe_assumption_routes` 只有 `tests/test_assumption_route_count_pin.py`。**⇒ 修 `kind` 不改变任何用户可见行为**（风险面因此小），但也意味着"补实现"若不同时解决接线，产出还会是零调用者死码（与本域已取证到的「四道统计护栏零调用」同一形态）。

**另有第三种债，超出卷宗给的两分类，必须一并报**（§4）：existing 侧自身有 4 条口径／接线不符，且 48 个 runner 注册法里 **33 法完全没有假设集**。

---

## 2. 盘点口径（怎么算「已实算」）

一条 placeholder 判为**类 I**，须同时满足：① 同仓有计算该假设量的代码路径（不是文案、不是教学卡）；② 有**阈值判定**（不是只把数字放进表里展示）；③ 违反时**产出用户可见的 warning／raise**（不是静默）。
只满足 ①（"已算未判"）⇒ 记 II-A 并标 `半`，因为修法只是补判定，成本近零，优先级高于全新实现。

---

## 3. 类 I 清单（6 条・已实算被误登记）

| # | 法 | 条目（注册表行） | 实算位置（工作树＝HEAD，无差） | 阈值／出口 | 修正要点 |
|---|---|---|---|---|---|
| I-1 | `multiple_regression` | 自变量间无严重多重共线性（VIF）（`:282`） | `regression.py:131 _calc_vif` → `:319`（statsmodels `variance_inflation_factor`），结果落 `RegressionResult.vif_table`（`:18/:187`） | `:132-134` `VIF > 10` ⇒ `⚠ …可能存在严重共线性问题。` | kind→existing；**须同时补 `computed_in`**（VIF 不在 `assumptions.py`，白名单容不下，见 §6） |
| I-2 | `multiple_regression` | 样本量充足（常见口径每预测变量 ≥10–20 例）（`:285`） | `regression.py:166` `if n < (k + 1) * 10:` ⇒ `:167` 告警 | 实现口径＝**10×(k+1)**；注册表 name 写「10–20」 | kind→existing 时**必须把 name 改成实现的真实口径**，否则把 kind 的债换成 note 的债（本班不裁该不该改成 20×） |
| I-3 | `binary_logistic` | 因变量为真二分类（`:298`） | `logistic_regression.py:50-59`：`len(unique_vals) != 2` ⇒ `raise ValueError("二元 Logistic 回归要求因变量恰好有 2 个类别…")`；`set(unique_vals) != {0,1}` 另有一支 | 硬校验（raise），非诊断 | kind→existing／或单列「前置校验」类。⚠ 该条一旦动，`tests/test_assumption_router.py:210` 的 `len(s.existing_checks) == 0` 立刻红 |
| I-4 | `manova` | 组间协方差矩阵齐性（Box's M）（`:314`） | `manova.py:163 _box_m_test`，`:127` 调用，结果落 `MANOVAResult.box_m`（`:15`） | `:130-131` `box_m["p"] < 0.001` ⇒ 告警并建议优先看 Pillai's Trace | 同名条目在 `test_assumption_router.py:227` 只被断言"名字里含 Box"，**不锁 kind** ⇒ 这条翻牌**不翻红**（改动面最小的一条） |
| I-5 | `sem` | 样本量充足（常见口径 ≥ 10–20 × 自由参数）（`:340`） | `sem.py:71` `if result.n_obs < len(available) * 5:` ⇒ `:72-73` 告警 | 实现口径＝**5×观测变量数**，与 name 写的「10–20×自由参数」**不同** | 同 I-2：翻 kind 必带口径订正。⚠ `test_assumption_router.py:233` 断言 `len(s.existing_checks) == 0`（"sem 全 placeholder"）会红 |
| I-6 | `chi_square_independence` | 期望频数充足（各单元格期望 ≥ 5）（`:362`） | `chi_square.py:47-52`：`np.any(expected < 5)` ⇒ `有 x% 的单元格期望频数小于5…2×2 建议 Fisher 精确` | 阈值 5，出口＝`ChiSquareResult.warning` | 同法同族另一条 `chi_square_gof（:357）` **只算不判**（`:109/:120` 算了 `expected_freq` 并进表，无 `<5` 判定）⇒ 落 II-A·`半`。⚠ `test_assumption_router.py:255` 断言两法 `len(existing_checks)==0` 会红 |

---

## 4. 类 III：existing 侧的既存债（不在卷宗两分类内，但不报就会误导修法）

| # | 条目 | 债 |
|---|---|---|
| III-1 | `linear/multiple/hierarchical_regression`、`hlm` 的「残差正态性 → `check_normality`（应用于回归残差）」 | 运行时**从不在残差上跑**：`_needs_normality_check`（`runner.py:1002-1009`）含 `linear_regression`/`multiple_regression`，但它只把 `check_normality=True` 传给 `data_quality_check`，后者 `:257-275` 是**逐原始数值列**做 Shapiro ⇒ kind 对、**note 语义错** |
| III-2 | `mixed_anova`「球形假设 → `check_sphericity`」 | 实际计算在 `anova.py:386-401` 用 **`pingouin.pg.sphericity`**；`assumptions.check_sphericity`（`:112`）全仓**零调用者**（仅注册表引用）⇒ 指向错对象 |
| III-3 | `manova`「各组方差齐性（逐因变量）→ `check_homogeneity`」 | `runner.py:337` manova handler 不填 `output["assumptions"]`，`MANOVAResult` 无 `assumption_homogeneity` 字段（grep 空）⇒ 该 existing **永不触发**；`assumptions.check_homogeneity` 同样零运行时调用者 |
| III-4 | `two_way_anova`「正态性 → `check_normality`（逐单元格）」 | handler（`runner.py:142-153`）只填 `homogeneity`，不填 normality；逐单元格只体现在 note 文字里 |
| III-5 | 覆盖面 | runner 注册 **48 法**，注册表只有 **15 键** ⇒ **33 法无任何假设集**，含最常用的 `independent_ttest`／`paired_ttest`／`one_way_anova`／`welch_anova`／`repeated_anova`／`ancova`／`pearson_corr`／`spearman_corr`／`mediation`／`moderation`／`efa`／`cfa`／非参数族／信度族（`keys - reg = ∅`，`reg - keys = 33`）；`:220` 注释「注册名与 runner.py @_register 完全对齐」**只在子集方向成立** |
| III-6 | 设计阻塞 | `_EXISTING_CHECK_NAMES`（`:233-235`）白名单只有 4 个名字，且 `tests/test_assumption_router.py:193-195` 强制**每条 existing 的 `check_name` 必须 ∈ 白名单且在 `assumptions` 模块上可取为 callable** ⇒ 类 I 那 6 条的计算点（`regression.py`／`manova.py`／`sem.py`／`chi_square.py`／`logistic_regression.py`）**结构上无法登记为 existing**。锚点件 E4 已点到这层（"placeholder 是设计使然而非疏漏"），本班复核成立 |

> 净含义：债不是单向的。类 I 是"算了没登记"，III-1…III-4 是"登记了但没那么算／没接线"。**只修类 I 会把注册表变成一半真话**。

---

## 5. 类 II-A 清单（30 条・真缺失、可自动检验）＋实现优先级

优先级依据：① 依赖是否已在 `.venv`（实测 `statsmodels 0.14.6`／`scipy 1.18.0`／`pingouin 0.6.1`／`sklearn 1.5.2`）；② 是否已有"算了一半"的量；③ 覆盖面（同名条目数）。🔴 全部属"造统计计算"＝人工闸，本班不写码。

| P | 假设族 | 条目数・法 | 现状｜可补口径（不含结论） |
|---|---|---|---|
| **P0 接线・零新增计算** | 两组方差齐性（`point_biserial`「两组方差齐性与线性关系」`:353`） | 1 | `assumptions.check_homogeneity` 已在世但零调用 ⇒ 先拆条（该条把"齐性"与"线性"捆一条，不可登记）再接线 |
| **P0 接线** | 球形（`mixed_anova`，III-2 的指向修正） | — | 已在算（`anova.py:390`），修的是注册表指向，不新增计算 |
| **P1 补判定（半实算）** | 期望频数 ≥5（`chi_square_gof` `:357`） | 1 | `expected_freq` 已在手（`:109/:120`），只缺 `<5` 判定与告警 |
| **P1 补判定（半实算）** | 各层级样本量充足（`hlm` `:334`） | 1 | `hlm.py:70-83` 已算 `n_groups`／`avg_cluster_size`／`design_effect`＋已有 ICC，缺阈值判定 |
| **P1 补判定（半实算）** | 单元格样本量充足且无空单元格（`two_way_anova` `:329`） | 1 | `anova.py:211` 已分组计数，但 `if len(g) >= 2` 是**静默过滤**，用户不可见 |
| **P1 标准检验件** | 残差同方差性／异方差（`linear`/`multiple`/`hierarchical_regression`、`hlm` 按层级）`:277/:283/:291/:335` | 4 | 无 Breusch-Pagan／White。`statsmodels.stats.diagnostic.het_breuschpagan` 在依赖内。⚠ `_compute_diagnostics`（`regression.py:334-395`，Cook's D／学生化删除残差／杠杆）**不等价**，勿用它顶替登记 |
| **P1 标准检验件** | 观测间相互独立（回归／logistic 族）`:278/:284/` 及 binary/multinomial/ordinal | 5 | 无 Durbin-Watson（全仓仅 `learning_card.py:373`、`defense_qa_kb.py:1144` 文案提及）；`statsmodels.stats.stattools.durbin_watson` 在依赖内 |
| **P2** | 因变量与自变量的线性关系（`:276`）；`partial_corr` 变量间线性（`:347`）；manova 因变量间线性相关（`:316`） | 3 | 无 Box-Tidwell／RESET／偏相关图（锚点 E4 复核成立）。**与 s927-10 同一教训**：补这类"检验"要连"缺项不得静默落 0"一起设计 |
| **P2** | logit 线性（binary `:295` Box-Tidwell、multinomial `:301`） | 2 | 同上，且需先定"对哪个协变量做、交互项怎么进模型" |
| **P2** | logistic 族自变量多重共线性（`:296/:302/:308`） | 3 | 无 VIF；`logistic_regression.py:140` 的极大系数／完美分离告警是**代理**，不得当作该条已实算 |
| **P2** | 多元正态性（manova `:313`、sem ``观测变量多元正态` :339`） | 2 | 现只有逐列 Shapiro（`data_quality.py:257`），无联合口径（偏度-峰度型／Mardia） |
| **P2** | 极端多元异常值（manova `:317` Mahalanobis） | 1 | `sklearn.covariance.mahalanobis` 在依赖内（1.5.2） |
| **P3** | 比例优势／平行线（ordinal `:307`） | 1 | 需似然比／分数检验，本仓无有序模型诊断面 |
| **P3** | 随机效应近似正态（hlm `:333`） | 1 | 需 BLUP 抽取，`statsmodels` 接口口径待人工定 |
| **P3** | 模型可识别（sem `:341`）；sem 指标间共线性（`:342`） | 2 | semopy 无现成 identify；成本最高、收益面窄 |
| **P3** | `hierarchical_regression` 的 VIF（`:289`） | 1 | 见 §1 修正 2：同名条目**未实算**，若把 I-1 的实现复用到该路径＝新接线 |

## 6. 类 II-B 清单（9 条・结构性／语义性，不宜补统计检验）

| 条目（行号） | 法 | 为什么不宜自动检验 | 建议改法（不新增计算） |
|---|---|---|---|
| 嵌套模型间可比（`:290`） | hierarchical_regression | 由代码构造保证（逐层增变量） | note 改写为「由实现构造保证：每层仅增入变量、其余设定不变」，kind 保持 placeholder 会持续误导 ⇒ 建议新 kind `structural_guarantee` |
| 因变量类别互斥且穷尽（`:304`） | multinomial_logistic | 数据设计属性；仓内已有部分校验（`:301` 起的类别数校验） | 归到「前置校验已做部分＋人工确认」双句 |
| 观测间相互独立（被试间）（`:323`、`:328`） | mixed_anova、two_way_anova | 设计问题，数据无法自证（长格式 `subject` 已在 `runner.py:166-177` 强制） | `structural_guarantee`／人工核查清单条目 |
| 观测间相互独立（`:358`、`:363`） | chi_square_gof、chi_square_independence | 同上（每单元仅贡献一次计数）是设计约束 | 同上 |
| 类别互斥且穷尽（`:359`、`:364`） | 卡方两法 | 语义属性 | 同上 |
| 二分变量为真二分（非人为切分）（`:351`） | point_biserial | "人为切分"不可由数据判定 | 同上 |

---

## 7. 登记修正草案（三案・给主班裁；本班不执行）

**共同的会翻红清单（本班逐枚定位到行）** —— 修 `kind` 前必须知道它会撞哪几枚钉：

| 测试件 | 断言 | 撞车方式 |
|---|---|---|
| `tests/test_assumption_router.py:186-195` | 每条 existing 的 `check_name ∈ _EXISTING_CHECK_NAMES`（4 名）且在 `assumptions` 模块 callable | 🔴 **结构阻塞**：类 I 六条的计算点全在白名单外（III-6） |
| `tests/test_assumption_router.py:197-201` | 每条 placeholder 必须 `check_name == ""` 且 note 非空 | 新增字段／改 kind 需保持该不变量 |
| `tests/test_assumption_router.py:210-215` | `binary_logistic` 的 `len(existing_checks) == 0` | I-3 翻牌即红 |
| `tests/test_assumption_router.py:233-237` | `sem` 全 placeholder（`len(existing)==0`） | I-5 翻牌即红 |
| `tests/test_assumption_router.py:255-260` | 两卡方法 `len(existing)==0` | I-6 翻牌即红 |
| `tests/test_assumption_router.py:262-264` | **`multiple_regression` 的「多重共线性」必须是 placeholder** | 🔴 这枚钉**正是把 §1 那个矛盾焊死在盘上的东西**；I-1 翻牌必红 |
| `tests/test_two_way_anova_route.py:62` 区段 | `len(aset.placeholders) == 2`（two_way） | 该法任何一条 placeholder 变动即红 |
| `tests/test_assumption_route_count_pin.py:60-70 / 135-160` | 快照＝**15 个方法 id 的集合**＋`KNOWN_ISSUES.md:144`「15 法」注记三向判等 | ✅ 只钉**键集**，不钉 per-entry kind ⇒ 类 I 翻牌**不碰这枚**；但若为 III-5 扩 33 法，必须同步改快照＋文档注记（该件另有"快照不得自证"的反假绿守卫，绕不过） |

**方案 A｜止血（改动面最小・零测试翻红）**
只改 6 条类 I 的 **note**：从通用「系统暂无自动检验实现」改为「本假设已由 `<文件:行>` 的 `<判据>` 承担，注册表 kind 暂未登记（s927-24 登记债）」。
✅ 不动 kind ⇒ `:197-201` 不变量仍成立 ⇒ **全部 8 枚钉零红**；把"暂无实现"这句**事实错误**先止住。
❌ kind 仍与事实不符；`:262` 那枚"必须是 placeholder"的红利仍在（下轮仍会被误读为"确实没实现"）。

**方案 B｜结构修正（推荐・中等改动面）**
给 `MethodAssumption` 增加第三维，把"是否已实算／在哪／是否运行时接线"与 kind 解耦：

```python
@dataclass(frozen=True)
class MethodAssumption:
    name: str
    kind: str                 # _EXISTING | _PLACEHOLDER | 新增：_COMPUTED_ELSEWHERE | _STRUCTURAL
    check_name: str = ""      # 仅 _EXISTING 使用（白名单语义不变，III-6 不被强行撑破）
    note: str = ""
    computed_in: str = ""     # 例 "src/analysis/regression.py:131 _calc_vif（VIF>10）"
    wired: bool = True        # False＝算得出但运行时不接（III-1…III-4 直接可见）
```
- 6 条类 I → `kind=_COMPUTED_ELSEWHERE` ＋ `computed_in` 逐条填真实阈值口径（I-2／I-5 的"10×vs10–20×"、"5×指标vs10–20×参数"必须在此显形）；
- 9 条 II-B → `kind=_STRUCTURAL`；
- `describe_assumption_routes()` 的画像加两个计数，`test_assumption_route_count_pin.py:145` 的画像全量断言（`set(profile)==set(registry)`）**仍成立**（键集不变）；
- 需同步改的测试：`:262`（翻成"必须非 placeholder 且 computed_in 指 regression.py"）、`:210/:233/:255`（把 `len(existing)==0` 改成 `len(existing)==0 and 新增维度符合预期`）、`:186-195`（白名单不变量按新 kind 分流）。⇒ **红是设计内的红，且每枚都有明确改法**，符合"增删留痕"的既有钉桩哲学。
- 回滚成本：单文件 dataclass ＋注册表 literal ＋ 3 个测试件；注册表无运行时消费者 ⇒ **零用户可见行为变化**（这是本案最重要的低风险论据）。

**方案 C｜扩白名单把 6 条真登记成 existing**（不推荐）
`_EXISTING_CHECK_NAMES` 扩到跨模块符号、`:195` 的 `getattr(assumptions_mod, …)` 改成多模块解析。
❌ 要把 `_calc_vif`／`_box_m_test` 等私有函数变公开契约；且现有 4 条 existing 本身有 III-1…III-4 的接线债，扩完会出现"登记 existing 但 `wired=False`"的假绿面。若走 C，必须先做 B 的 `wired` 维度。

**排期建议**：A（本轮）→ B（下一轮，与 III-1…III-4 接线债同批）→ II-A 的 P0/P1（"补判定"类，改动小、可测）→ P2/P3（真新实现，逐条走人工闸＋判据先写规格）。**III-5（33 法无假设集）单列裁**：扩法要同时改快照与 `KNOWN_ISSUES.md:144` 注记，属"文档＋测试＋注册表"三向动作，别和 kind 修正混一次提交。

---

## 8. 取证命令（全部只读，他人可重跑）

```bash
cd /d/code/psy-analysis && git rev-parse --short HEAD      # f0f3f73
# 注册表画像（15/12/45）与逐条 placeholder 名
.venv/Scripts/python.exe -c "from src.analysis.assumption… import _METHOD_ASSUMPTIONS,_PLACEHOLDER,_EXISTING …"   # 见 §1
# 注册表键 vs runner 注册法
.venv/Scripts/python.exe -c "re.findall(r'@_register\(\"([a-z0-9_]+)\"', runner.py)"      # 48 法；keys-reg=∅；reg-keys=33
# 类 I 的实算点（逐条定位）
grep -n "variance_inflation\|_calc_vif\|VIF" src/analysis/regression.py        # 127-134 / 187 / 319-331
grep -n "n < (k + 1) \* 10" src/analysis/regression.py                          # 166-167
grep -n "恰好有 2 个类别\|is_numeric_dtype(y)" src/analysis/logistic_regression.py   # 50-59
grep -n "_box_m_test\|box_m\[" src/analysis/manova.py                            # 15/127/130/163
grep -n "n_obs < len(available)" src/analysis/sem.py                             # 71-73
grep -n "expected < 5" src/analysis/chi_square.py                                 # 47-52
# 类 II 的"不存在"证明（须带 --no-ignore 口径，锚点 E1 的工具坑：rg 会吞 src/data/）
grep -rni "durbin\|breusch\|het_breuschpagan\|white_test" src/                    # 仅文案 2 处
grep -rni "box_tidwell\|RESET\|resid.*图" src/                                    # 仅占位登记＋教学文案
grep -rn "_calc_vif" src/analysis/regression.py | grep -n hierarchical            # 空＝hierarchical 不算 VIF
# 运行时接线债
grep -rn "get_assumption_set" --include=*.py . | grep -v assumption_router.py     # 仅 1 测试件＋兄弟班 tmp 探针
grep -rn "check_homogeneity\|check_sphericity" --include=*.py src/ | grep -v "assumptions.py\|assumption_router.py"   # 零调用者
grep -n "pg.sphericity" src/analysis/anova.py                                      # 390（实际球形来源）
grep -n "check_normality=_needs_normality_check" src/analysis/runner.py            # 914；:1002-1009 名单
# 会翻红的钉
grep -n "placeholder\|existing_checks" tests/test_assumption_router.py | head      # 186-277 区段
grep -n "placeholders) == 2" tests/test_two_way_anova_route.py                      # 62 区段
grep -n "假设检验路由" KNOWN_ISSUES.md                                              # :144「15 法」注记
```
本班**未跑 pytest**（避免与兄弟班并发负载混淆；§7 的红利清单是从断言源码静态定位的，非执行所得）；未产出任何 p 值／效应量／假设成立性判定。零写自证：`data/` 前后采样 diff 为空（承 s927-10 同一份基线），未开 SQLite 连接，`~/.psy_analysis` 未碰。

## 9. 红线声明与遗留

- 🔴 卷宗判据是「清单＋登记修正草案＋优先级＋零码改动」，**不要求**判定任何假设是否成立 ⇒ 未命中红线，状态 `done`。
- 文中出现的一切阈值（VIF>10、期望频数<5、p<.001、10×k、5×指标）都是**在册实现与注册表文字的对账**，不是本班对任何数据下的判断。
- 遗留：① I-2／I-5 的口径冲突（10–20× vs 10×、10–20×参数 vs 5×指标）属统计规范取舍，**本班不裁哪个对**；② III-5 扩法是否值得做＝产品决策；③ `_STRUCTURAL`／`_COMPUTED_ELSEWHERE` 两个新 kind 的命名需与 s927-21 的缺失机制登记口径对齐（两单都会往同一注册表写，别写出第三套词）；④ II-A 全部项＝造统计计算＝人工闸，本班零实现。
