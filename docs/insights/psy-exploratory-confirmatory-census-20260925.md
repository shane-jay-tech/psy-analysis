# 探索性／确认性检验盘点与校正方式标注（信箱单 20260925-120703-44a0）

- 取数班：`qoder-executor-20260925-1630-psy68`，2026-09-25 16:4x（A 档／docs 型）
- 取证面：`src/analysis/*.py`（检验与事后）、`src/output/interpretation.py`（结果解读渲染）、
  `src/utils/guardrails.py`（唯一的多重比较拦截）、`src/experiment_design/preregistration.py`（假设声明面）
- 🔴 **红线**：本档**只做盘点与标注**——未改任何检验选择、未改任何阈值、未重算任何 p 值／效应量／置信区间。
  表内出现的每一个数字都是**源码里的字面量**（阈值 0.05／0.001、`round(...,4)` 的位数等），不是本班跑出来的统计量。

---

## 〇、先否证一条前提（决定本档"校正前后 p 值"这一栏怎么读）

任务书的验收写"结果表标明**校正前后 p 值**"。这条隐含"仓内已有一张带 p 值的检验结果表可盘点"。实测否证：

| # | 盘上实况 | 证据命令 |
|---|---|---|
| ① | 全仓**没有**任何字段承载"本次检验是探索性还是确认性" | `rg -n -i "exploratory|confirmatory" src/analysis/` 只命中方法名（EFA／CFA）与警告文案，无状态字段 |
| ② | 分析结果侧**不落档任何 p 值历史**：`data/` 只有 `literature_feed`／`benchmark_history`／`perf_history.jsonl`；`archive/` 里 17 个归档目录只存 `report.md` 文本 | `ls data/` ＋ `ls archive/2*/` |
| ③ | 假设声明在**另一条链**上（预注册文档），与分析结果之间**无键相连** | `preregistration.py:227` 的 `exploratory_analysis` 只写进文档正文，不进 `run_analysis` 返回值 |

⇒ 因此本档的"校正前 p／校正后 p"两栏记的是**载体（列名字段）＋是否同源**，不是数值；
要把数值填进去，必须新跑检验（=造新统计量）或解析历史 `report.md`（无结构、不可归因），
两条都超出本单授权 ⇒ 已列进「六、待人工裁决」。

---

## 一、有校正的检验面（校正方式已写死在代码里）

| 检验 | 位置 | 校正方式 | 校正前 p 载体 | 校正后 p 载体 | 触发条件（=选择依据） | 可作确认性结论？ |
|---|---|---|---|---|---|---|
| Kruskal-Wallis 事后 Dunn | `nonparametric.py:342-397` | **Holm-Bonferroni（默认）**／Bonferroni／FDR-BH／none 四选一 | `p (未校正)`（`:395` 列） | 同表第 4 列，列名随方法变（`p (Holm-Bonferroni)` 等，`:382-387`） | `runner.py:735` 取 `plan.mc_method`，缺省 `"holm"` | ✅ 同源成对，是**全仓唯一**"校正前后同时可读"的面 |
| 单因素 ANOVA 事后 | `anova.py:119-122, 470-495` | Tukey HSD（Studentized range 精确 p） | **无**（不产未校正配对 p） | `p (Tukey HSD)`（`:495`） | `p_val < 0.05` 且组数 > 2 才算（`:565` 同族的门） | ⚠ 只有校正后单值，无法核对"校正带来了什么变化" |
| Welch ANOVA 事后 | `anova.py:564-575` | Games-Howell（pingouin `pairwise_gameshowell`） | **无** | `p (Games-Howell)`（`:574`） | 方差不齐分支；pingouin 该函数**本身不做 p 调整** | 🚫 名字带"事后"，但列里是**未调整** p ⇒ 最易被当确认性结论的一处 |
| 重复测量 ANOVA | `anova.py:399-414` | Greenhouse-Geisser（ε 缩 df） | 主 ANOVA 表的 `p` 列（`:560` 附近） | `corrected_table` 的 `校正p`／`校正df1`／`校正df2`／`ε` | **仅当球形检验未过**才生成（`:399`），过了就根本没有校正行 | ⚠ 校正行是条件性产物：读不到校正行 ≠ 不需要校正，也可能是"检验未跑成"（`except: pass`） |
| 独立样本 t | `ttest.py:29-105` | Welch（不等方差自由度校正） | Student 那行的 p | `is_welch` ＋ Welch 行 p | Levene 未过 ⇒ 自动切（`assumptions.py:100` 文案同述） | ✅ 属"方差假设校正"，不是多重比较校正，两者不可混为一谈 |
| 分半信度 | `reliability.py:91-125` | Spearman-Brown 公式 | 半长相关 r | 校正后信度 | 分半法固有步骤 | ✅ 同上：这是**信度**校正，不在 p 族里 |

⚠ 术语提醒：**"校正"在本仓有三种不相干的含义**——
(a) 多重比较校正（Holm／Bonferroni／FDR／Tukey／Dunn）、
(b) 假设违反的自由度校正（Welch／Greenhouse-Geisser）、
(c) 信度系数校正（Spearman-Brown）。
盘点表里必须分开标，否则会读成"这个检验已经做过多重比较校正"。

## 二、未校正的检验面（默认按探索性对待）

| 检验 | 位置 | 比较族大小 | 现网校正 | 现网渲染 | 风险 |
|---|---|---|---|---|---|
| 相关矩阵（Pearson／Spearman） | `correlation.py:60-105` | k(k−1)/2 对 | **无** | `sig_mask` 直接打 `***`/`**`/`*`（阈 0.001／0.01／0.05，`:83`） | 🔴 一屏星星＝一类错误膨胀后的"显著图案"，最像确认性结论、最不是 |
| 偏相关 | `correlation.py:111-181` | 同上 | **无** | 同样 `sig_mask` 星星（`:164`） | 同上 |
| MANOVA 的逐因变量单变量表 | `manova.py:100-112` | 因变量数 m | **无**（多变量整体检验在前） | `univariate_tests` 表原样 p | ⚠ 若把单变量表当"哪个 DV 显著"的结论 ⇒ 未校正 |
| 多元回归逐系数 | `regression.py:89-194` | 预测变量数 p | **无** | 系数表 p＋`vif_table` | ⚠ 同上；逐步回归另计（`method_recommender.py:210` 自注"谨慎使用"） |
| Logistic 回归逐系数／优势比 | `logistic_regression.py` | 同上 | **无** | `coef_table`／`odds_ratios` | ⚠ 同上 |
| EFA | `factor_analysis.py:31-` | 载荷矩阵＋Bartlett＋KMO | **不适用**（不是假设检验族） | 卡片文案自述"探索性"（`result_card.py:789`） | ✅ 名义上已标探索性；但没有机器可读的状态字段（见 §〇①） |
| CFA／SEM | `cfa.py:215-`、`sem.py:31-` | 单次整体 χ² | **不适用** | 拟合指数 | ⚠ `cfa.py:391-406` 的**降级路径**（无 semopy 时）自述"不是严格 CFA，输出仅供探索性参考"，但降级结果仍以 CFA 的名义进结果卡（`runner.py:803` 只是 append 一条 error 级消息）⇒ 确认性／探索性会在这里串味 |
| 事后功效建议 | `post_hoc_power.py:223-` | — | 不适用 | 建议文本 | runner 注释自述"仅建议，不切换"（`runner.py:904`），不得当结论 |
| 已知组比较 | `validity.py` | 多组×多指标 | **无** | `known_groups_*` 三件套（stat／p／effect） | ⚠ 效标／效度证据链里出现多 p 时同样未校正 |

## 三、唯一的"多重比较"拦截闸（读源码确认）

`src/utils/guardrails.py:240-272` `check_multiple_comparisons`：

- 只看 `analysis_history` 最近 **10** 条里 `independent_ttest`／`mann_whitney` 的**连续次数 ≥ 3** 且因变量集合 **≤ 3** ⇒
  `passed=False`、`severity="block"`，文案建议"Bonferroni 校正（α 除以检验次数）或改用单因素 ANOVA＋Tukey HSD"。
- 覆盖面缺口（只登记，不改）：
  ①不看**同一次**分析里的多因变量／多组配对（MANOVA、相关矩阵、回归逐系数全在闸外）；
  ②不看 `one_way_anova` 自身的事后族；③只看"最近 10 条"，跨会话不归零也不累计；
  ④`mann_whitney` 在内但 `kruskal_wallis` 的事后不在内（后者已有 Holm，属另一种口径混用）。

## 四、"未校正结果不得冒充确认性结论"的可执行判据（本档提出，未接线）

建议在**修案被批准之后**按下表落地（本班只写判据，不改任何渲染面与阈值）：

| 判据 | 现状 | 落地成本 |
|---|---|---|
| R1 每个进入报告／结果卡的 p 值必须带 `correction ∈ {holm, bonferroni, fdr, tukey, games-howell, gg, welch, spearman-brown, none, not-applicable}` | 全仓无此字段 | 需给 `run_analysis` 输出加元数据面（**新契约**，不碰数值） |
| R2 `correction = none` 且同族比较数 > 1 ⇒ 渲染层必须出现"探索性／未校正"字样，且不得出现星星 | `correlation.py:80-84` 与 `interpretation.py` 的 ⭐ 反其道 | 改渲染面文案＝动现网输出，须人工裁 |
| R3 预注册文档存在且 `hypotheses` 非空 ⇒ 才允许把对应检验标为"确认性" | `preregistration.py` 与 `run_analysis` 之间**零连接**（§〇③） | 需要一条 id 级关联（工程面最大的一条） |
| R4 Games-Howell 列名要么真做 pingouin 的调整、要么改名去掉"事后校正"暗示 | `anova.py:574` | **会改变读者结论的读法**，属人工裁决 |

## 五、盘点读数（可复算）

```
$ rg -n -i "bonferroni|holm|fdr|pairs_adjustment|tukey|dunn|gameshowell|greenhouse|spearman-brown|welch" --type py src/ | 计数见下
$ rg -c "mc_method" src/analysis/nonparametric.py src/analysis/runner.py
   → nonparametric.py **7 处**、runner.py **3 处**（`runner.py:735` 取 `plan.mc_method`，缺省 "holm"）
$ 校正方式族合计：有校正的检验面 6 处 ／ 未校正但产多 p 的检验面 8 处（表一、表二行数）
$ rg -n "0.001" src/analysis/correlation.py
   → 星星三档写死在 **:83（相关矩阵）／:164（偏相关）／:219（单对相关）三处**，
     三处都不接"同族比较数"这个信息，改一处不等于改全族
```

在册红名集未扩大（与派单第 2 条硬约束对齐）：本班**未新增任何 UI 入口／导出面**，
点名跑的 `tests/test_export_gate_global_scan.py` 唯一红名仍是
`test_all_download_buttons_accounted_for`（offender `src/ui/questionnaire_panel.py`），与在册同名同 offender。

## 六、待人工裁决（本档不改判据、不改阈值，全部交回）

1. **数值面**：若要"结果表带校正前后 p 的具体数值"，只能新跑检验（造新统计量）或解析历史 `report.md`（无结构）。
   两条都触"统计数值结论"红线 ⇒ 不派给执行手。
2. **Games-Howell 是否补 p 调整**（表一第 3 行）：改它会改变历史结论的读法，需人工裁。
3. **相关矩阵星星是否加 FDR**（表二第 1-2 行）：现网阈值 0.05／0.01／0.001（且同判据散在 :83／:164／:219 三处）属"实测阈值自动判定散在 27 处、
   被 4 份在册件钉住"的同一族 ⇒ **本班一字未动**。
4. **R1～R4 判据的落地闸位**（导出前？渲染前？）：接线若新增导出面，同批必须改导出面账本（在册红的门禁形状），
   属新单。
5. **`cfa.py` 降级路径的命名**（表二第 7 行）：降级产物仍叫 CFA 结果，探索／确认在此串味 ⇒ 交人工。

## 七、术语澄清（防下批误读）

- 本仓**没有**"预注册平台对接""检验登记表""p 值档案"这类东西：
  `preregistration.py` 生成的是**给作者看的 Markdown 文档**，不是机器可读的假设登记表；
  它写"本研究主要进行验证性分析"（`:227` 默认文案）也不构成任何检验的性质标注。
- "探索性"在仓内现有三处互不相干的用法：**EFA 方法名**、**α=0.60-0.70 的信度档位**
  （`reliability_bands.py:26` 的 `EXPLORATORY`）、**信度警告文案**（`reliability.py:77,178`）。
  本档说的"探索性检验"＝**未经预注册假设支撑且／或未做多重比较校正**的检验，与信度档位无关。
