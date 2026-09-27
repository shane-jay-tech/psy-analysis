# 相关矩阵星标规则标准化裁决材料（correlation.py 三处）

> 信箱单：`s927-03`　班名：`qoder-executor-20260927-1430-psy75`　取数时刻：2026-09-27 14:31（本机 `date` 口径，休眠会双向校时）
> 仓／HEAD：`D:\code\psy-analysis` @ `11e536d`
> 🔴 **本档＝统计域方案档，零码改动**：`src/` 一字节未写；所有"统一成哪一个阈值／是否上 BH／对角与缺失怎么渲染"都写成**给人拍的判断题**（§四），本班不替统计学签字。
> 档内出现的每个数字只有两种来源：①**源码字面量**（星星档位、`round(...,4)` 位数）；②**合成随机数据上对代码行为的复现**（§三.3、§七 Q2/Q3，逐条标注"构造/合成"）。没有一枚是本仓任何真实样本的实测统计量。

---

## 〇、结论速览（三句话）

1. **"阈值三处各写一份"成立，但"三处阈值互不相同"不成立**：`correlation.py:83/:164/:219` 的三档字面量**逐字相同**（`0.001／0.01／0.05`，探针 P1 规范化后集合大小 = 1）。三处的真分叉在**行为**，不在数值——对角星、缺失值、判星精度三项（§一"差异"列）。所以本次重构的收益是**去重复＋行为对齐**，不是"把不同阈值统一"。
2. **最刺眼的一处不一致不在 `correlation.py` 里**：星标用**未舍入 p** 判（`:80-84` 早于 `:87-92`），而 `interpretation.py:207` 挑"显著相关"用的是**已舍入 p**（`p_matrix` 已是 4dp）⇒ 同一结果对象可被两套口径判反。本班用构造数据把它跑出来了：`0.0500*`、`0.0100**`、`0.0010***` 三枚自相矛盾读数（§三.3）。
3. **多重比较：现状为"完全无"**，而唯一的多重比较拦截闸（`guardrails.py:240-272`）只盯 `independent_ttest`/`mann_whitney`，文案不提"相关"（探针 P5 实测该函数体 45 行内 0 次出现"相关"）⇒ 相关矩阵**整体在闸外**。仓内确有可复用 BH 积木（`nonparametric.py:290 _apply_mc_correction`），但它有三处牙口问题（§三.4），接过来之前必须裁。

---

## 一、判据①：三处现状对照表

指纹（探针 P0 现取，`sha256` 前 12）：`src/analysis/correlation.py` = **238 行 / 8,584 B / `17d847172cfc`**（本班双法复核：`certutil -hashfile ... SHA256` 前 12 与 `.venv` Python `hashlib` 一致），mtime 2026-05-23 14:45；`git diff --numstat HEAD -- src/analysis/correlation.py` 输出**为空** ⇒ **工作树即 HEAD 版**（不是需要标"工作树版 mtime"的脏件）。

| 维度 | `:83` `correlation_matrix` | `:164` `partial_correlation` | `:219` `point_biserial_corr` |
|---|---|---|---|
| 所属函数行 | `:21-108` | `:111-186` | `:189-238` |
| 阈值字面量 | `0.001／0.01／0.05` | **同上，逐字相同** | **同上，逐字相同** |
| 表达式形态 | `lambda` + 逐列 `Series.apply` | `lambda` + 逐列 `Series.apply` | **内联标量三元式**（无 lambda，不进 DataFrame 路径） |
| 判星用的 p | **原始 p**（`p_df`，`sig_mask` 在 `:80-84` 生成，早于 `:87-92` 的 `round(...,4)`） | **原始 p**（`sig_mask` 在 `:161-165`，早于 `:167-172` 舍入） | **原始 p**（`:211` 求得 `p`，`:219` 判星，`p` 的舍入发生在 `:233` 整个 2×2 阵） |
| **对角线** | 🔴 **打星**：`:52-54` 把对角 p 硬置 `0.0` ⇒ 对角必得 `***`（探针 P2 实测 4×4 对角全 `***`） | 🔴 **打星**：`:132-134` 同样置 `0.0` ⇒ 对角 `***`（实测） | ✅ **强制空**：`:220` 字面写 `np.array([["", sig], [sig, ""]])` |
| **p=NaN（n<3 或求解异常）** | 空串 `""`（NaN 与三档比较恒 False） | 空串 `""` | 走不到（单标量；`stats.pointbiserialr` 不返回 NaN p，异常直接抛） |
| 矩阵形状 | k×k，上/下三角**重复打同一对** | k×k，同样重复 | 固定 2×2，同一对重复 2 次 |
| 单元格算术 | k²=16 / 独立对 k(k−1)/2=6（k=4 实测样例） | 同上 | 4 / 1 |
| 样本量口径（影响 CI，不影响星） | `:55`/`:61` **逐对** pairwise n | `:123` `dropna()` **全列成对删除** ⇒ n_arr 恒等（`:128`） | `:216` 单标量 n |
| 渲染落点 | UI 表 `renderers.py:142-151`（`f"{rv:.3f}{sig}"`）、CSV 导出 `renderers.py:743`（`sig_mask.to_csv()`）、热力图 `charts.py:259`（`f"{val:.2f}{sig}"`，**r 只留 2 位**）、文字报告 `interpretation.py:207-220` | 同 UI/CSV/热力图（同一 `CorrResult` 通道） | 同 UI/CSV（2×2） |
| 血缘登记 | `field_lineage.py:512` `"sig_mask": "S25_derived_table"`（三处共用同一字段名，**登记表里不区分哪个函数产的**） | 同 | 同 |
| 校正现状 | 🔴 **无任何多重比较校正** | 🔴 无 | 🔴 无（单检验， arguably 不需要） |
| 被谁钉桩 | 无测试断言 `correlation.py` 的星值：`test_golden_stats.py:324-353` 的 `TestGoldenCorrelation` 只断 `r>0.90`（`:330`）／`p<0.001`（`:337`）／对称（`:339`）／对角=1（`:349`）；`test_plotly_renderers.py:30-37` 传**自造** sig 矩阵，不接生产函数 | 同（`test_ui.py:46-58` 只跑通不断星） | 同（`test_ui.py:55-58`） |

**读表要点**：`:83` 与 `:164` 是**逐字孪生**（可安全合并）；`:219` 是**同数值、不同行为**的第三种写法——它既不产对角星，也不经历"原始 p→舍入 p"的双口径（因为它自己就是标量），所以"三处统一"若只统一字面量而不动行为，`:219` 与另两处的对角差异**依旧存在**。

---

## 二、"三处"之外的同族副本（统一常量必须同批改，否则新常量是假的单一来源）

探针 Q1（跨行感知扫描 `src/`+`tests/`，排除 `.venv/node_modules/tmp/archive/__pycache__`）＋ 手工补漏：

**(a) 判星表达式副本：生产码 7 处**

| # | 位置 | 形态 | 非显著档的渲染 | 本班怎么数到的 |
|---|---|---|---|---|
| 1-3 | `correlation.py:83/:164/:219` | 见 §一 | `""` | Q1 |
| 4 | `src/analysis/sem.py:172` | 内联三元，写进"显著"列 | `""` | Q1 |
| 5 | `src/output/apa_tables.py:106` | 内联三元（**自己算 pearsonr**，不读 `CorrResult`） | `""` | Q1 |
| 6 | `src/paper_writer/psychology_report_format.py:31` | `SIG_MARKS = {0.001:"***",0.01:"**",0.05:"*"}` **字典表** | 无第四档 | Q1（多行表靠 `"***"` 命中） |
| 7 | `src/output/apa_figures.py:101` | 内联三元，字面量写成 `.001/.01/.05`（**无前置 0**） | 🔴 **`"ns"`** | ⚠ Q1 的 `0\.001` 正则**漏计**，本班直读源码补上（见 §七"探针自曝"） |
| + | `src/paper_writer/section_writers.py:671-678` `_mark_significance()` | **已是函数**，`if/elif` 多行 | `""` | Q1（`:675` 命中 `"***"` 行） |

⇒ 生产码里"三档判星"共 **7 份字面量副本 ＋ 1 个已存在的函数版**（`_mark_significance`）。它比 `correlation.py` 更接近"模块化"的正解，但**没人从相关矩阵调它**（`correlation.py` 不 import `paper_writer`）。

**(b) 图例/表注文案副本：4 处**（改了档位不改这里＝报告在说谎）

`src/ui/renderers.py:142`（Streamlit caption，转义星号）、`src/output/formatter.py:154` 与 `:156`（两条分支各一份）、`src/output/apa_tables.py:122`（APA 表注 `*p < .05. **p < .01. ***p < .001.`）。
⇒ 这 4 处是**给人看的口径声明**，与 §四 Q5（是否上校正）直接绑定：一旦星星改口径（BH 后 p／校正后档位），4 处文案必须同批换，且要新增"未校正"字样（census 档 R2 判据）。

---

## 三、多重比较处理现状（照读，不判对错）

### 3.1 三处本身：无校正、无同族信息

三处的入参只有**一个 p**（或一列 p），拿不到"这次矩阵一共比了多少对"，所以任何逐步法（Holm／BH）在**现函数签名下无法就地实现**——这是模块化必须解决的第一个结构问题，不是风格问题。

### 3.2 全仓唯一的多重比较拦截闸不覆盖它

`src/utils/guardrails.py:240` `check_multiple_comparisons(analysis_history, current_test_type, dv_vars)`：白名单只有 `independent_ttest`／`mann_whitney`（`:246`），触发条件是"最近 10 条（`:250`）里同类 ≥3 次（`:254`）且因变量集合 ≤3（`:258`）"，建议文案是 Bonferroni 或 ANOVA+Tukey。相关矩阵、偏相关、MANOVA 逐因变量表、回归逐系数全在闸外（与 `docs/insights/psy-exploratory-confirmatory-census-20260925.md` §三 缺口① 一致，本班独立复读确认）。

### 3.3 判星口径 vs 显示口径：可复算的自相矛盾

三处都"用原始 p 判星、用 `round(p,4)` 显示"（`:90`/`:170`/`:233`）。本班按 t 分布**反解**出精确样本相关（非随机撞，见探针 Q3 构造法）：

| 目标档 | 构造 r | raw p | 按 raw p 判星 | 读者看到的 p | 读者实际看到 |
|---|---|---|---|---|---|
| 0.05 | 0.36101410（n=30，df=28） | 0.04999510 | `*` | 0.0500 | 🔴 **`0.0500*`** |
| 0.01 | 0.46291925 | 0.00999510 | `**` | 0.0100 | 🔴 **`0.0100**`** |
| 0.001 | 0.57051276 | 0.00099510 | `***` | 0.0010 | 🔴 **`0.0010***`** |

（合成构造，非实测样本。）更后果的一条：`interpretation.py:207` 的 `if pd.notna(p) and p < 0.05` 读的是**已舍入** `p_matrix` ⇒ 上表第一行那种配对，**矩阵里带星、文字报告里整条不出现**（被 `p<0.05` 筛掉）。这是"同一结果两种显著性判定"，属可复现行为，不是风格问题。

### 3.4 可复用 BH 积木的三处牙口（现网实况）

`nonparametric.py:290 _apply_mc_correction(p_values, method)`（探针 Q4 实测返回）：

```
method='holm'       → [0.002, 0.036, 0.06, 0.096, 0.3]
method='bonferroni' → [0.002, 0.045, 0.1, 0.24, 1.0]
method='fdr'        → [0.002, 0.0225, 0.0333, 0.06, 0.3]      ← BH 在仓内的键名是 'fdr'，展示标签 'p (FDR-BH)'（:385）
method='none'       → [0.0004, 0.009, 0.02, 0.048, 0.3]
method='fdr_bh'/'BH'/'' → [0.0004, 0.009, 0.02, 0.048, 0.3]   ← 🔴 未登记名静默回落成"不校正"，不抛错
```

1. **未知 method 静默通过**（`:331-332 else: corrected = sorted_values`）⇒ 谁把 BH 拼成 `fdr_bh`，会得到"自以为校正过、其实没校正"的星星，且**测试面零红**（现无参数化钉桩覆盖 `else`）。
2. **内部已 `round(p, 4)`**（`:339 return [round(p, 4) ...]`）⇒ 与 §3.3 的显示舍入叠加成**二次舍入**；校正后再判星的边界比现状更密。
3. **调用侧缺省是 `holm`**（`runner.py:735 getattr(plan,"mc_method","holm")`，FWER 口径）⇒ 若相关矩阵选 BH（FDR 口径），**同一份报告里会出现两种错误率口径**，且都叫"多重比较校正"。这条必须人拍（§四 Q5）。

---

## 四、给人拍的判断题（本班一律不裁）

每题给：各案后果 ＋ 可复算入口。判据来自卷宗"统计域只出方案不动数值"＋ brief §4（统计数值与效应量结论＝红线）。

**Q1 统一常量放哪儿？（工程题，但决定要不要动基线）**
- **案 A1：新建 `src/analysis/significance.py`**（草案见 §五 草案 A）。后果：不碰任何在册钉桩；不动外部在途脏件（本班核 `src/analysis/__init__.py` 工作树与 HEAD **均无 `correlation` 再导出**，新模块不需动它）。成本＝新增 1 件。
- **案 A2：把 `SIG_MARKS`（`psychology_report_format.py:31`）立为唯一真源**。后果：🔴 **同笔打断两枚在册黄金快照**——`test_psychology_report_format_golden.py:174` `SIG_MARKS == {0.001:"***",0.01:"**",0.05:"*"}`、`:175 len==3`、`:66` 顶层赋值必须恰为 6 个容器（加 `STAR_TIERS`/`STAR_LEGEND` 即翻红）；且 `test_ui.py:251` 会**二次执行**同一批金档判据（一处红＝两处红）。另加**分层倒置**：`src/analysis/*` 反向 import `src/paper_writer`（`docs/insights/psy-eta-threshold-caliber.md:158` 记过同一个坑）。⇒ **按纪律属"重钉 golden 基线"＝人工闸**，执行手无权自改。
- 复算入口：`.venv\Scripts\python.exe -m pytest tests/test_psychology_report_format_golden.py -q`（本班 14:3x 实测 **98 passed** 含 `test_golden_stats.py`，rc=0）。

**Q2 对角星留不留？** 现状 `:83/:164` 在 k×k 上给对角打 `***`（自相关被标成"极显著"），UI 表／CSV 导出／热力图三处都会印出 `1.000***`；`:219` 则强制空。三案：①全强制空（对齐 `:219`）②全写 `—`（对齐 `apa_tables.py` 的对角惯例）③留现状。**后果**：①②都会改**已入库 CSV 的字节**（`renderers.py:743`）与热力图标注，属"动现网输出"。本班倾向"现状自相矛盾必须裁"，但**不代裁**。

**Q3 `p=NaN` 与"不显著"要不要分家？** 探针 Q2 实测（合成，c 列与 a 列只共 2 个观测）：`p_matrix` 出 `NaN`、`sig_mask` 出 `""`、n_matrix 出 `2.0` ⇒ 读者无法区分"没算"和"算了不显著"。三案：①第四态符号（`"†"`/`"NA"`）②空串＋脚注 ③维持。**后果**：①改导出与所有渲染文案；③零改动但把歧义留给读者。

**Q4 判星用 raw p 还是显示 p？** §3.3 已给三枚矛盾读数。四案：①判星改用 `round(p,4)`（与读者所见一致，边界档会变）②显示位数提高到 6（改 CSV/UI 观感）③保留 raw p 判星＋图例改成严格语义并加"按未舍入 p 判星"脚注 ④维持现状。**注**：`STAT_FORMATS["correlation"]` 的 p 精度被 `test_psychology_report_format_golden.py` 钉成 `.3f`（`P_PRECISION`，`:136`/`:158` 一带参数化）⇒ ②若牵动 `STAT_FORMATS` 又落回 Q1-A2 的人工闸。

**Q5 要不要给相关矩阵上多重比较校正？上哪种？**（🔴 纯统计题，本班只列形状）
- 族大小先要拍：k(k−1)/2（独立配对）／k(k−1)（含镜像单元）／k²（含对角）三种口径下乘数不同（§一算术行：k=4 → 6／12／16）。**"每对独立"本身也是建模假设**（同一批被试的共享变量正相关时，独立性不成立）。
- Holm（FWER，仓内其它处默认）vs BH（FDR，仓内键名 `fdr`）vs 不校正但**强制标"探索性"**（census R2）。
- 默认档：`runner.py:735` 已是 `"holm"`；相关矩阵若默认 BH＝**同类问题两套默认**；若默认 `"none"`＝改了也不起作用（多数用户不动 plan）。
- 🔴 若采纳：`_apply_mc_correction` 的**静默回落必须先加白名单校验**（§3.4.1），这本身是"改校正函数失败模式"，会牵动 `nonparametric.py` 的现有调用面（`mc_method` 7 处）＝另开单，不在本方案射程。
- 本班**不给任何"该用哪个 α／哪种法"的建议**，因为那是效应量与错误率结论面。

**Q6 新增"校正后 p"要不要进 `CorrResult`／导出？** 若加 `p_matrix_adjusted`/`mc_method`/`correction` 字段：①`field_lineage.py:512` 只登记了 `sig_mask`（`S25_derived_table`），新字段需同步登记（`test_analysis_field_lineage.py:141/:148` 要求必需键都有规范；`:110` 钉"登记表装不进数值"⇒ 数值只能进 `value_bearing` 类载体）；②进不进 CSV 导出面（`renderers.py:743`）＝**新增导出面**，census §改动清单已点名这类形状会触发 `test_export_gate_global_scan.py::test_all_download_buttons_accounted_for`（该条**此刻已在册红**，offender `src/ui/questionnaire_panel.py`）；③`interpretation.py` 要不要改用校正后 p 叙述（该件**外部在途脏件**，见 §六）。

---

## 五、判据②：重构方案 diff 草案（**全部未落地**，`src/` 零写入）

### 草案 A：星标规则模块化，数值与行为**一律照抄现值**（A1 落点，零基线冲击）

```diff
--- /dev/null
+++ b/src/analysis/significance.py
@@ -0,0 +1,34 @@
+"""相关／效应量星标的唯一来源（s927-03 草案）。
+
+🔴 数值全部照抄 src/analysis/correlation.py:83/:164/:219 的现网字面量；
+   本文件不新增、不删除、不改动任何阈值，也不做任何多重比较校正。
+   对角线／NaN／判星精度三处**行为**仍留在调用侧现状（见 docs/insights/s927-03-star-caliber.md §四 Q2-Q4），
+   人工裁决后才允许在本文件里收敛。
+"""
+from __future__ import annotations
+
+import pandas as pd
+
+#: 现网字面量，三处逐字相同（探针 P1 已核）。顺序＝由严到宽。
+STAR_TIERS: tuple[tuple[float, str], ...] = ((0.001, "***"), (0.01, "**"), (0.05, "*"))
+#: 不显著档（现网三处都是空串；apa_figures.py:101 用 "ns"，属 §四 Q2/Q3 未裁面，此处不改它）。
+NO_STAR: str = ""
+#: 图例唯一来源。改档位必须同批改 renderers.py:142 / formatter.py:154 / :156 / apa_tables.py:122。
+STAR_LEGEND: str = "\\*p<.05, \\*\\*p<.01, \\*\\*\\*p<.001"
+
+
+def stars_for_p(p: float) -> str:
+    """标量判星。NaN 与三档比较恒为 False ⇒ 返回 NO_STAR，与 :83/:164/:219 现行为一致。"""
+    for threshold, mark in STAR_TIERS:
+        if p < threshold:
+            return mark
+    return NO_STAR
+
+
+def star_matrix(p_df: pd.DataFrame) -> pd.DataFrame:
+    """逐列 apply 而非 DataFrame.map —— correlation.py:86 的在册注释说明 map 跨 pandas 版本变过。
+
+    入参必须是**未舍入**的 p 矩阵（现网 :83/:164 就是在 round 之前算的）；
+    对角是否打星由调用侧的 p_df 决定（:52-54/:132-134 把对角 p 置 0.0 ⇒ 现行为保留 ***）。
+    """
+    out = p_df.copy()
+    for c in out.columns:
+        out[c] = out[c].apply(stars_for_p)
+    return out
```

```diff
--- a/src/analysis/correlation.py
+++ b/src/analysis/correlation.py
@@ -79,10 +79,8 @@ def correlation_matrix(
     # 显著性标记
-    sig_mask = p_df.copy()
-    for c in sig_mask.columns:
-        sig_mask[c] = sig_mask[c].apply(
-            lambda p: "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
-        )
+    from .significance import star_matrix
+    sig_mask = star_matrix(p_df)
```
（`:161-165` 同样替换；`:219` 替换为 `sig = stars_for_p(p)`，`:220` 的 `[["", sig],[sig, ""]]` **原样不动**——它是对角差异的另一半，动它要过 §四 Q2。）

⇒ A 案净效果：**7 份字面量副本先收 3 份**（相关矩阵三处），**输出字节零变化**（本班按 §一"逐字相同"与 NaN/对角行为逐项对齐论证；可跑性由主班收班时定向复点，见 §七）。**A 案不解决任何统计问题**，它只把"改一处不等于改全族"变成"改一处即改全族"，为 Q1-Q6 的裁决提供一个可改的位点。

### 草案 B：行为对齐（**依赖 Q2/Q3/Q4 先拍**，此处只给形状）

```diff
@@ correlation.py:52-54（correlation_matrix 对角）  ——  案 B1：对角不产星
-            if i == j:
-                corr_arr[i, j] = 1.0
-                p_arr[i, j] = 0.0
+            if i == j:
+                corr_arr[i, j] = 1.0
+                p_arr[i, j] = np.nan          # ← 若采 B1：对角改 NaN，需同批定 Q3（NaN 渲染符号）
```
```diff
@@ correlation.py:219（point_biserial）——  案 B0：反向对齐矩阵系（对角也打星）
-    sig_mask_arr = np.array([["", sig], [sig, ""]])
+    sig_mask_arr = np.array([[sig, sig], [sig, sig]])   # ⚠ 不推荐：对角 1.000*** 会被读成结果
```
```diff
@@ correlation.py:87-92 ——  案 B2：判星改用显示值（消除 §3.3 的 0.0500*）
-    sig_mask = star_matrix(p_df)
+    sig_mask = star_matrix(p_matrix_rounded)   # 需把本块整体上移到 round 之后；同时 interpretation.py:207 才有同一口径
```
⇒ B 案每条都**改现网读者可见输出**（UI 表、CSV 导出字节、热力图标注），本班一律未动。

### 草案 C：可选 BH（**默认关，且默认值本身要人拍**）

```diff
@@ correlation.py:21 def correlation_matrix(df, columns, method="pearson",
+                                        mc_method: str = "none",     # 与 runner.py:735 的 "holm" 缺省是否一致＝§四 Q5
)
```
```python
# 伪码（不落 src）：
if mc_method != "none":
    ps = [(i, j, p_df.iat[i, j]) for i in ... for j in ... ]        # 族大小口径待 Q5 拍
    adj = _apply_mc_correction([p for *_ , p in ps], mc_method)      # nonparametric.py:290
    # 🔴 前置：给 _apply_mc_correction 加 method 白名单，未知值抛错——否则静默"不校正"（§3.4.1）
    sig_mask = star_matrix(adj_df)
    legend = f"星号基于 {mc_method} 校正后 p"                        # 4 处文案（§二b）同批改
```
⇒ C 案牵动：新导出面（Q6）、`field_lineage` 登记、4 处图例、`_apply_mc_correction` 失败模式、与 `holm` 默认的口径冲突。**建议顺序＝A 先落（零风险），Q1-Q6 人拍后 B/C 各自单开**。

---

## 六、门禁与人工闸清单

| # | 触发条件 | 在册闸 | 本班处置 |
|---|---|---|---|
| 1 | 常量落 `psychology_report_format.py` 或扩 `SIG_MARKS` 形状 | `test_psychology_report_format_golden.py:174/:175/:66`（＋ `test_ui.py:251` 二次执行） | 🔴 **人工闸**（重钉 golden），本班未动，写成 §四 Q1 |
| 2 | 对角/NaN/精度行为变更（B 案） | 无测试钉星 ⇒ **不会红**，但改 UI/CSV/热力图读者可见输出（`renderers.py:142-151`/`:743`、`charts.py:259`） | 🔴 人工裁（"不红≠可改"） |
| 3 | 新增 `CorrResult` 字段／新导出面 | `test_analysis_field_lineage.py:141/:148/:110`；`test_export_gate_global_scan.py::test_all_download_buttons_accounted_for`（**此刻已在册红**） | 🔴 人工闸＋登记，本班未动 |
| 4 | 上 BH/Holm | `runner.py:735` 缺省 `holm`；`_apply_mc_correction:331-332` 静默回落 | 🔴 人工裁口径，本班未动 |
| 5 | 牵动 `interpretation.py`（Q4/Q6 的第二判星点） | 该件是**外部在途脏件**：` M`，mtime 2026-09-26 11:47，`git diff --numstat HEAD` = `2 2`（脏在 `:102` 与 `:622`，**与本档引的 `:200-220` 窗口无交集**——本班逐字比过 HEAD 版与工作树版，该 21 行一致） | 本班只读；改它需外部写手收口 |
| 6 | brief／纪律档说的"`--freeze` 重钉基线" | 🔴 **本仓现值无此机制**：`tests/conftest.py:57` 唯一 `pytest_addoption` 是 `--run-benchmark`；全仓 `.py`（排 `.venv/node_modules/tmp`）`--freeze` 字面量 **0 命中**（探针 Q6）。`scripts/research_release_gate.py`（未跟踪在途件，141 行/5,341 B）选项只有 `--confirm-review`/`--fail-probe`，不含 `freeze` 亦不含 `correlation`（Q5 实测）。⇒ **等价闸形态＝硬编码全等快照**（本表 #1） | 据实收窄，不据此判 failed；`psy-eta-threshold-caliber.md:161/:175` 的"`test_golden_stats.py` 系另有 `--freeze`"在本仓**复算不通过**，列此否证 |

---

## 七、取证与复算入口（命令＋读数，全部本班现取）

**环境**：一律 `D:\code\psy-analysis\.venv\Scripts\python.exe`（系统 python 包集不同）；中文输出加 `PYTHONIOENCODING=utf-8`；`rg` 在本机不可用（兄弟班 `probe_posthoc.py` 曾收 `rg: command not found`），故本班普查用 Python 正则，不引 `rg` 命令。

| 探针 | 关键读数 |
|---|---|
| `D:\code\tmp\qoder-executor-20260927-1430-psy75\probe_s92703.py` → `out_a.txt` | P0 指纹（correlation.py 238/8,584/`17d847172cfc`）；P1 三处**逐字相同**（命中 3、规范化去重后大小 1）；P1b 判星副本（含测试钉桩）＋图例副本 4；P2 对角星 `['***']`×2 处 vs `['']`×1 处；P4 `_apply_mc_correction` 七种 method 实测返回；P5 闸不覆盖相关；P6 在册钉桩 |
| `...\probe_s92703_b.py` → `out_b.txt` | Q1 跨行副本普查；Q2 真 NaN 塌缩（p_matrix `NaN`／sig_mask `""`／n=2.0 三矩阵对照）；**Q3 三枚边界矛盾读数**（0.0500*／0.0100**／0.0010***，反解构造）；Q4 点二列 dtype；Q5/Q6 `--freeze` 否证 |
| `git diff --numstat HEAD -- <16 枚引用路径>` | 仅 `src/output/interpretation.py 2 2`，其余**全空＝工作树即 HEAD**（本班 14:3x 现取，见 §一/§六）。工作树规模：brief §5 记 psy `12` 行 porcelain ⇒ **已漂移**，本班开工实测 **14**（外部新增 `?? docs/insights/s927-01-*.md`、`?? docs/insights/s927-02-*.md`），收档前复点 **15**（＋本班本档）；`git rev-parse --short HEAD` = `11e536d` **未动**，`src/` 零 ` M` 新增 |
| 定向测试（并发窗内，**禁全量**） | `-m pytest tests/test_psychology_report_format_golden.py tests/test_golden_stats.py -q` → **98 passed, rc=0**（31.12s）；`-m pytest tests/test_analysis_field_lineage.py tests/test_plotly_renderers.py -q` → **70 passed, rc=0**（1.81s）；`-m pytest "...::test_sig_marks_three_tiers_exact" "...::test_module_declares_exactly_the_six_golden_constants" -q` → **2 passed, rc=0**（0.48s）。⇒ 在册钉桩**在世且绿**，故 §四 Q1-A2 的"会翻红"论断是基线在世的推断，不是本班已证红。**未跑全量**（兄弟班撞顶前 4 件定向 63 passed，本班无交集需求） |

**探针自曝（三条，防后班照抄错数）**：
① Q1 的 `0\.001` 正则**漏计** `apa_figures.py:101`（该处字面量写作 `.001/.01/.05`，无前置 0），本班直读源码补为第 7 份副本——照正则数会得到"6 份"的错数。
② 探针 A 的 P1 里"阈值三元组"一行**打印有缺陷**（生成器写进了 `set()` 的推导式，输出成 `<generator object>`）⇒ 该行的结论**不采信**；"三处逐字相同"另有两条独立证据支撑：`len(set(规范化表达式)) == 1`（同段已打印）＋三处源码文本直读（§一表首两行）。
③ 本班一次 `Grep`（模式含 `--freeze`）返回的读数把 `--freeze` 与"correlation 族"记到 `scripts/research_release_gate.py:15/66/71/84/296`，另一次工具输出把 `correlation.py` 的 sha 前 12 记作 `a8a5b1378945`。磁盘双法复核（`certutil -hashfile` ＋ `.venv` `hashlib`）一致给出 `17d847172cfc...`，该件实测 238 行/8,584 B；`research_release_gate.py` 实测 **141 行**（`:296` 不可能存在）且 `freeze`/`correlation` 命中数均 **0** ⇒ **这两串读数本班无法复现，一律不采信**，本档只引磁盘现值（brief §0）。归因（并发串流／缓存／其它）**本班不判**，交主班现取。

---

## 八、遗留（交主班／人工）

1. §四 Q1-Q6 六题**全部未裁**，其中 Q1-A2、Q6、§六 #1/#3 属人工闸形状（重钉基线／新增导出面）。
2. `:219`（点二列）**是否属于"该统一"射程**存疑：它是单检验，不存在同族膨胀，且对角行为本就正确。本班把它纳入 A 案的引用改造（纯去重），但**不**把它纳入 B/C 案的行为对齐。
3. 生产码副本 7 处只收 3 处的方案（A 案）会留下"半统一"状态：`sem.py:172`/`apa_tables.py:106`/`apa_figures.py:101`/`SIG_MARKS`/`_mark_significance` 五处仍各写一份，且 `apa_figures.py:101` 的 `"ns"` 档与另两处不同——是否一并纳入，属**改动面 vs 一致性**的人工取舍（A 案射程外）。
4. `interpretation.py:207` 的第四处判定（读舍入 p 筛"显著相关"）在 `correlation.py` 之外，本档只登记不处置——它正被外部写手改动。
5. 兄弟班 `qoder-executor-20260927-1400-psy74` 的沙盒里留有 `probe03.py`（同单 `s927-03` 的未完成探针），本班**只读参考、未改动、未删除**；本班从零重跑并自建档内所有读数。该班探针的 S0 段指纹与本班 P0 段**同一文件同一算法却给出不同 sha**（`a8a5b1378945` vs 本班双法复核的 `17d847172cfc`）——本班**不据此指控任何写手，也不判定文件曾变动**（`git diff --numstat HEAD` 现为空 ⇒ 现值等同 HEAD），只按 §七 探针自曝③ 记为"不可复现读数"，归因交主班。
6. 本班**未做**也**不该由本班做**的两件：① A 案的落地后定向复点（`test_golden_stats.py` ＋ `test_ui.py` ＋ `test_effect_size_ci.py` 等）需写权；② `--freeze` 类基线重钉在本仓不存在（§六 #6），若后续要新建该旗标属信箱/门禁层新功能，另开单。
