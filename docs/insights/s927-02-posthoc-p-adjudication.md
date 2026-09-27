# s927-02 · 事后多重比较 p 值显示规则：裁决材料（44a0 卷宗三条）

> 班次 `qoder-executor-20260927-1400-psy74`｜cwd `D:\code\psy-analysis`｜取数时刻 local **2026-09-27T14:06:43～14:15:43 +0800**（`date` 现取，逐段标注）
> 工作树现值：HEAD `11e536d`，`git status --porcelain` **13 行**（＝派单时 12 行＋本班 s927-01 产物 1 枚未跟踪档）
> 🔴 本班**零码改动**：未改任何检验实现、p 值、阈值、星标规则、golden 快照与期望数据；`data/` 零访问。
> 本档出现的数字分两类：**源码字面量／列名／形状／计数**（本班现取），以及**机械演算读数**（在合成数据与 golden fixture 上算，
> 明确标"演算"，不构成统计结论）。凡"哪个案更对"的地方一律写成给人拍的判断题（§四）。

---

## 一、锚点复核：三案里有两案的前提需要按磁盘实况改写

| # | 锚点／卷宗原述 | 磁盘实况（本班现取） | 处置 |
|---|---|---|---|
| 1 | 锚点路径 `outbox/20260925-120703-44a0.result.md` | outbox 查无此件，件在 `D:/code/zcode-bridge/done/`（8,452 B，mtime 09-25 16:51） | 按 brief §3a 到 `done/` 取用，不算缺陷 |
| 2 | 「`p (Games-Howell)` 列**实不存在**（anova.py:574）」 | **该行确实存在**：`"p (Games-Howell)": round(float(row["pval"]), 4)` 在 **anova.py:574**（blob `56f6ecc3`，718 行）；实测跑出的表列名就是 `['比较','均值差','SE','p (Games-Howell)']` | 卷宗「背景与锚点」段的这句**与磁盘冲突**（可能是写作时行号漂移或指代别处）⇒ 按实况改写为本档的实际命题：**列在世，问题是名实与显示层** |
| 3 | 「pingouin `pairwise_gameshowell` 默认**不对 p 做调整**」 | 安装版 **pingouin 0.6.1**（`.venv/Lib/site-packages/pingouin/pairwise.py:956`）：签名 `(data, dv, between, effsize)`，**没有 `p_adjust` 参数**（全函数体 `p_adjust` 命中 0 次）；p 的计算式是 `pval = studentized_range.sf(√2·|t|, ng, df)`（同文件 :1083-1084），docstring :992 自述 **"'pval': Games-Howell corrected p-values"** | **需要人工拍语义**：该 p 走的是 studentized range（与 Tukey 同一族分布），库方称其为 "corrected"；但它**不是** Holm／Bonferroni 那种对逐对 p 的同族乘性校正。锚点说"不调整"在"没有 p_adjust 参数、没有乘性校正"这个意义上成立，在"完全没有族系控制"这个意义上**不成立**。本班不裁这一句（统计语义），只把源码证据摆出来（§三·演算 A） |
| 4 | 卷宗要①「补 p-adjust」 | 0.6.1 的 `pairwise_gameshowell` **无处可传** adjust ⇒ "补调整"只能是**仓内自己再乘一遍**（改 anova.py:574 的取值式）或**换函数**（`pairwise_tests(padjust=...)`，该函数有 `padjust` 参数，:35-47） | 案①按此重述，见 §二 |
| 5 | 卷宗要②「改列名标注 unadjusted」 | 与 #3 直接冲突：若该 p 实为族系控制量，标 "unadjusted" 会**造成新的名实不符** | 列为 Q1（本班不裁） |

---

## 二、三案矩阵（按磁盘实况重述；「显示层代价」均为本班实测）

| 维度 | 案① 补调整（再乘 k／换 `pairwise_tests(padjust=…)`） | 案② 改列名（加 `unadjusted`／`adjusted` 标注） | 案③ 双列（校正前后并排） |
|---|---|---|---|
| 动什么 | **动数值**：`anova.py:574` 的取值式（或改调用 :567 的函数） | 只动列名字符串＋三处写死该串的读者 | 新增一列 ⇒ 同案②的读者面 ＋ 需新算未校正 p（现成无处可取，见 §三·演算 A） |
| 谁读这个列名 | 事后表在**数值层无人读列名**；三个显示层位置写死字符串（§三·甲） | 同左：改名不破计算，但破显示 | 同左，另加"新列叫什么"的第二套命名问题 |
| golden 影响 | 事后表**不在 golden 数值面**（fixture 只有 F/p/η² 阈值）⇒ 不破 golden；但破 `tests/test_welch_anova.py:48` 之外的**无**（该钉桩只钉列名不钉数值）⇒ **案①实际零测试阻力**，代价全在统计口径 | 撞 **`tests/test_welch_anova.py:48`** 一枚精确名钉桩 | 加列不破 `test_robustness.py:173-197`（它用 `any(... in c)`），但 `mc_method="none"` 已有**同键塌缩**先例（§三·乙 2） |
| 现网默认路径是否已经坏 | 否（此项不涉当前崩溃） | **是**：现网默认路径已在抛 `KeyError`（§三·丙，两例实测） | 同案②（新增列名后，若沿用 `p (未校正)` 这个名字，会撞上现存的 `p (Bonferroni)` 硬编码族） |
| 可回滚成本 | 中（改数值式需重跑历史报告口径） | 低（纯文案＋3 处读者） | 低～中（加列不改旧列） |
| 红线归属 | 🔴 统计数值域，须人工签字 | 🟡 显示规则，工程可裁但需一致 | 🟡 显示规则＋需新算一列 p（触统计） |

---

## 三、现取证据（全部可复算）

### 甲、三处写死列名的显示层（改名＝同时动这三处）

| 位置 | 现文（blob 级直检） | 影响 |
|---|---|---|
| `src/output/interpretation.py:166` | `lines.append("\n🔍 **事后多重比较（Tukey HSD）：**")` | 标题写死方法名，且该标题在 `welch_anova`（GH 分支）下也归同一函数族 |
| `src/output/interpretation.py:167/169` | `sig_pairs = r.post_hoc[r.post_hoc["p (Tukey HSD)"] < 0.05]`、`f"…p={row['p (Tukey HSD)']:.4f} ⭐"` | 精确列名读者：喂进非 Tukey 表 ⇒ `KeyError`（实测见 §丙-3） |
| `src/ui/renderers.py:136` | `st.caption("事后多重比较 (Tukey HSD):")` | 位于 `elif isinstance(result, ANOVAResult):` 分支内、**无条件**执行 ⇒ Games-Howell 表、mixed 的 `p (校正)` 表在 UI 上都被标成 Tukey |
| （对照）`src/ui/renderers.py:733` | `buf.write("\n# 事后多重比较\n")` | 导出 CSV 面**不写方法名**（口径与 UI 不一致，两份产物对同一张表说法不同） |

另有 `src/output/interpretation.py:284-287` 的 Kruskal‑Wallis／Dunn 分支写死 `p (Bonferroni)`——见 §丙-1。

### 乙、三条事后分支的真实表头（合成数据跑通，14:06:43～14:07:39）

```
welch_anova   → ['比较','均值差','SE','p (Games-Howell)']     （anova.py:567 调 pg.pairwise_gameshowell，:574 取 row["pval"]）
one_way_anova → ['比较','均值差','SE','p (Tukey HSD)']        （anova.py:122 调自实现 _tukey_hsd :470-498，非 pingouin）
mixed_anova   → ['对比','T','p','p (校正)',"Cohen's d"]        （anova.py:687-701 调 pg.pairwise_tests(padjust="bonferroni")，双列样板已在仓内）
kruskal_wallis→ ['比较','Z','p (未校正)','p (<方法名>)']        （nonparametric.py:391-396，p_label 来自 method_names :382-388）
repeated_measures_anova → **不产事后表**（anova.py:304-468，只有 GG `corrected_table`）
```

1. **自实现 Tukey 与 pingouin 的 p 无差**：同一合成三组数据上
   `max|Δ| = 0.0`（4 位小数，3 对；pingouin 返回列名是 `p_tukey`）⇒ 案②若只想把 `p (Tukey HSD)` 标注为"族系控制 p"，
   不存在"两版实现打架"的额外代价。
2. **`mc_method="none"` 会让双列塌成单列**（实测 14:12:26）：
   `holm/bonferroni/fdr → 形状 (3,4)`，`none → 列 ['比较','Z','p (未校正)'] 形状 (3,3)`
   ——机制：`nonparametric.py:395-396` 先写字面键 `"p (未校正)"`，再写 `p_label` 键，而 `method_names["none"]` 恰为同一个串
   ⇒ 字典同键覆盖。⇒ **案③在本仓有"双列会因取值塌成单列"的现成反例**，新列名要避开与既有字面键重合。
3. **`p (校正)` 全仓零读者**：`grep -rn "p (校正)" --include=*.py src/` → 只有写入处 `anova.py:700` 一处命中。
   ⇒ mixed 分支已经"双列"，但显示层（§甲）没有跟着改，UI 仍标 Tukey。

### 丙、现网默认路径上的两处实测崩溃／静默（这是本单最硬的取证）

```
（1）显著 Kruskal-Wallis + 默认设置 → 结果解读抛 KeyError
$ probe_reach.py 14:15:21（runner 全路径：AnalysisPlan(test_type="kruskal_wallis") → run_analysis → generate_interpretation）
  runner 产出的事后表列：['比较','Z','p (未校正)','p (Holm-Bonferroni)']   ← 默认 mc_method="holm"（runner.py:735）
  generate_interpretation(output) → KeyError: 'p (Bonferroni)'            ← interpretation.py:285 写死的列名
  把 mc_method 显式设为 "bonferroni" 重跑 → 正常，正文含 "🔍 **Dunn事后多重比较：**"
  AnalysisPlan 字段数 29，**`mc_method` 不是其字段**（`'mc_method' in fields → False`）
    ⇒ runner.py:735 的 `getattr(plan, "mc_method", "holm")` 在现网恒为 "holm"，
      即"用户根本选不到 bonferroni"，该 KeyError 在默认路径上是**常开**的（只要 KW 显著且 ≥3 组）。
  调用侧无兜底：app.py:1470-1472、src/ui/renderers.py:692、src/ui/undergrad_wizard.py:3107
    三处 `generate_interpretation(...)` 都不在 try 块内（app.py 最近的 try 在 :1464-:1468，已在调用之前闭合）。

（2）welch_anova 的事后表在解读层"整体消失"
  _interpret_anova 的分支只有 `test_type == "one_way_anova"` 与 `== "two_way_anova"`（直检）
  → 传 "welch_anova" 时返回长度 61 的正文，含 '事后'? False（全文只有标题＋一句方差齐性提示）
  → ANOVAResult.test_type 字段值对两版都是字面 'one_way'（实测）⇒ 结果对象自身区分不了两张表，只能靠 plan 字符串

（3）把 GH 表塞进 one_way_anova 分支（模拟"同名槽位换实现"）
  → KeyError: 'p (Tukey HSD)'
```

**与本案的关系**：这三处都是**显示规则**问题，不是统计口径问题；改列名（案②）若不同批改 §甲 那几处硬编码，
会把"名实不符"升级成"现网红屏"。案①（补调整）则完全不碰这三处。

### 丁、演算读数（不构成统计结论）

在 **golden fixture** `tests/fixtures/golden_stats/anova/one_way_anova.csv`（24 行，3 组）上，
对 Games-Howell 事后 p 做不同显示规则的机械重算（14:12:26 与 14:15:43 两次一致）：

| 口径 | 三对 p（round4） | 跨 0.05 的对数 | 相对现列的最大绝对差 |
|---|---|---|---|
| 现列值（pingouin `pval`，studentized range） | 0.0035／0.0000／0.0003 | 3/3 | 0.0000 |
| 仓内可另算的"逐对 t 型" p（`2·t.sf`） | 0.0013／0.0000／0.0001 | 3/3 | 0.0022 |
| 对现列再 ×k（Bonferroni） | 0.0106／0.0000／0.0008 | 3/3 | 0.0071 |
| 对现列做 Holm | 0.0035／0.0000／0.0005 | 3/3 | 0.0002 |
| 对"逐对 t 型"p 做 Holm | 0.0013／0.0000／0.0002 | 3/3 | 0.0022 |

- 逐位关系（同一次演算）：`2·t.sf` **三对全部小于**现列值；现列值 **三对全部小于** Bonferroni(现列)
  ⇒ 现列值处在"逐对型"与"乘 k 型"之间，与 §一·#3 的语义争议一致（它已带 studentized range 的族系控制成分）。
- 该 fixture 上五种口径的"跨 0.05 对数"**全是 3/3**（差异不显现）
  ⇒ 要看到差别必须另造 p 落在 `(0.05/k, 0.05)` 区间的样例；本班不为凑读数去调数据（红线）。
- 复算命令：`D:\code\tmp\qoder-executor-20260927-1400-psy74\probe_padjust.py`（只读，fixture 未改）。

### 戊、golden 与测试面（判据②的清单）

| 测试件（blob／行数） | 钉的是什么 | 案① | 案② | 案③ |
|---|---|---|---|---|
| `tests/test_golden_stats.py`（`9d141631`／407 行）`TestGoldenOneWayAnova:133-159` | 只断 `post_hoc is not None` 与 `len>=3`，**不读列名不读 p** | 不破 | 不破 | 不破 |
| 同上 `TestGoldenKruskalWallis:226-244` | 只断 statistic/p/effect_size 阈值 | 不破 | 不破 | 不破 |
| 同上 `TestGoldenCorrelation:324-` | 读 `corr_matrix`／`p_matrix` **数值**，不读星标字符串 | 无关 | 无关 | 无关 |
| fixture `tests/fixtures/golden_stats/anova/one_way_anova_expected.json`（`18419212`／19 行） | `f_statistic 28.5／p_value 0.0001／effect_size_min 0.70`，**无事后 p 键** | 不破 | 不破 | 不破 |
| `tests/test_welch_anova.py:41-48`（`09883c00`／56 行）`test_welch_anova_posthoc_games_howell` | `"p (Games-Howell)" in result.post_hoc.columns`（**精确列名，全仓唯一一枚**） | 不破（列名不变） | **必破**（改名即红） | 不破（只加列） |
| `tests/test_robustness.py:173-197`（`c1fe2a07`／330 行）`test_kruskal_wallis_mc_methods` | `any("Holm"/"Bonferroni"/"FDR" in c)`；`none` 分支无断言 | 不破 | 若改 Dunn 列名则**必破** | 不破（`any` 语义） |
| `tests/test_output_interpretation_helpers.py`（`df379b0f`／50 行，4 例） | 只测效应量分档与"缺结果"兜底，**事后分支零覆盖** | — | — | — |
| 交付包／导出面 | 未见事后表文案钉桩（`grep 事后/Games/Tukey` 于 golden_delivery 等 5 件 0 命中） | — | — | UI caption 与导出 CSV 会各说一套（§甲） |

基线（改前，本班 14:10:19 现取，定向 4 件）：**63 passed / 0 failed**
`pytest tests/test_welch_anova.py tests/test_nonparametric.py tests/test_output_interpretation_helpers.py tests/test_golden_stats.py -q`
（并发窗内未跑全量。）

---

## 四、给人拍的判断题（各案后果＋可复算读数；本班不替统计签字）

| 编号 | 问题 | 选 A 的后果 | 选 B 的后果 | 复算入口 |
|---|---|---|---|---|
| **Q1** | `p (Games-Howell)` 里的 p，**语义上算不算"已做族系控制"**？（pingouin 0.6.1 用 studentized range，docstring 自称 corrected；锚点断言"不调整"） | 若判"已控制"⇒ 案②（标 unadjusted）**作废**，只剩文案统一（§甲 三处）；案①变"重复校正"风险 | 若判"仍属探索性、需再加同族乘性校正"⇒ 案①落地，历史事后 p 全部重算，导出件与交付包文案需重出 | `probe_padjust.py`（§丁 五口径对照）、`.venv/.../pingouin/pairwise.py:956/992/1083` |
| **Q2** | 三处写死 `p (Tukey HSD)` 的显示层，改名时**一起改还是留兼容别名**？ | 一起改：干净，但要同批动 `test_welch_anova.py:48`（唯一名钉桩） | 留别名（旧列名继续存在＋新列名并存）：零测试阻力，但把"两名一实"的歧义固化 | §甲表＋§戊第 5 行 |
| **Q3** | 案③的双列里，"未校正"那一列**用哪种算法**（`2·t.sf` 逐对 p？还是 Bonferroni？）——两者数值不同（§丁：0.0013 vs 0.0106） | 用逐对 t 型：与常见 APA"校正前/后"表一致 | 用乘 k 型：与 §乙-2 的 Dunn 现例（Holm）更同族 | 同上 |
| **Q4** | `mc_method` 选不到（`AnalysisPlan` 无此字段）＋解读层写死 `p (Bonferroni)` ⇒ **默认路径 KeyError**。是补字段让 UI 能选，还是把解读层改成"取实际存在的校正列"？ | 补字段：改动面在 `contracts/intent_resolver/plan_ui/runner` 四件；UI 需新增控件（触导出/门禁账本口径） | 改显示层：只动 `interpretation.py:285/287`，零新增入口；但"默认 Holm、文案却写 Bonferroni"的历史文档需复核 | `probe_reach.py`（14:15:21 全路径实测） |
| **Q5** | `welch_anova` 在解读层**没有分支**（事后表整体不播）——算不算本单范围内的必修缺陷？ | 算：则 §丙-2 与本案同名一并修，Games-Howell 才有"人话" | 不算：另立新单；本单只裁列名 | §丙-2 |
| **Q6** | 导出 CSV 不写方法名、UI caption 写死 Tukey（§甲）——两份产物对同一张表口径不同，以哪份为准？ | 以 CSV（中性标题）为准 ⇒ UI 文案改中性 | 以 UI 为准 ⇒ 导出面补方法名（动导出面账本＝在册红名形状） | §甲 |

---

## 五、推荐（工程排序）与最强反对意见

**统计报告伦理角度的落点（卷宗判据③，写成人能拍的形状）**：
无论 Q1 怎么裁，**"事后多重比较"标题下同时并列 `p (Tukey HSD)`、`p (Games-Howell)`、`p (校正)`、`p (Holm-Bonferroni)` 四种不同族系的 p，
而显示层只说"Tukey HSD"**这一事实，本身就是"把探索性输出当确认性结论"的温床——
问题不在"少乘了一个 k"，而在**读者无法从界面判断这张表的错误率口径是什么**。
因此推荐的顺序是：**先让口径可见且自洽（P0/P1），再谈要不要再加一层校正（P2）**。

- **P0（零统计风险，纯显示层自洽）**：修 §丙-1 的默认 `KeyError`（按 Q4 的第二条：让解读层读"实际存在的校正列"）
  ＋修 §丙-3 的同类脆弱点（同一处代码容错）＋把 §甲 三处"写死 Tukey"改成"按实际列名播方法名"。
  这一档**不改任何数值**，破 0 条 golden，只可能碰 `test_welch_anova.py:48`（若顺手改名）。
- **P1（口径声明）**：事后表所在导出面统一写"本表 p 为〈方法名〉p 值，族系错误率口径＝〈…〉"，
  并把 §乙-2 的"双列塌成单列"隐患在新列命名时避开。
- **P2（案①）**：只有在 Q1 判"仍需同族乘性校正"后才做，且需人工先定"在哪些 test_type 上生效、历史报告是否重出"。

**最强反对意见**

1. **"P0 才是真正危险的一步"**：现网默认路径的 `KeyError` 一直在"挡着"Dunn/KW 的 ⭐ 播报（`interpretation.py:287`）。
   修好崩溃＝**首次让这批带星结论进入正文**，等于零统计评审地把一整个输出面从"崩"变成"给人读"。
   反对者会要求 P0 拆成"先不崩但不打星"（去掉 ⭐／改为只报 p 值），把"播报"与"标注显著"分两单。
2. **"让显示层自适应实际列名"会掩掉真问题**：列名不齐整本来是**能被看见的**症状；
   代码去"猜哪列是校正列"之后，Q1 的语义争议将永久无人再提（本档 §一·#3 就是靠列名不一致才被发现的）。
3. **"案①成本被低估"**：0.6.1 的 `pairwise_gameshowell` 无 `p_adjust` 参数（§一·#4），"补调整"只能是仓内自乘 k
   ——那是**换统计量**而不是打开库功能，且会与 studentized range 的族系控制**叠两次**（保守到无power）。
   若真要走案①，正确形状是换用 `pairwise_tests(padjust=...)`，但那条路是 Welch t 族而非 Games-Howell 的 studentized range 族 ⇒ 换了就不是"GH 事后检验"了。
4. **双列（案③）在导出面上会诱导"挑小的那个 p 报"**：APA 伦理上常见告诫是"报告校正后 p"，
   并把未校正值一起印出来＝给选择性报告留了口子；反对者主张"只印一列＋把口径写死"，而不是并排两列。
5. **本班证据的边界**：§丁 全部落在 golden fixture 与合成数据上，五种口径"跨 0.05 对数"同为 3/3
   ⇒ 本档**没有**、也不能给出"改调整后会有多少比例的现网结论翻转"的数；那需要人工放行后在受控真实数据上重跑（交主班进待人工台账）。

---

## 六、本班零改动自证

- 写动作只落 `docs/insights/s927-02-posthoc-p-adjudication.md`（本档）与沙盒 `D:\code\tmp\qoder-executor-20260927-1400-psy74\`
  （`probe_posthoc.py`／`probe_posthoc2.py`／`probe_posthoc3.py`／`probe_reach.py`／`probe_padjust.py`，落班自清）。
- 未改：`src/analysis/anova.py`（blob `56f6ecc3`，收班复点仍为 `56f6ecc3…`）、`src/output/interpretation.py`
  （`971cb581…`，**外部在途脏件，本班只读未写**）、`src/analysis/nonparametric.py`（`c38f1f1d…`）、
  `src/ui/renderers.py`（`ade79fe6…`）、`src/analysis/runner.py`（`ffde4479…`）、
  `tests/test_golden_stats.py`／`test_welch_anova.py`／`test_robustness.py`／`test_output_interpretation_helpers.py`、
  `tests/fixtures/golden_stats/**`（含 `one_way_anova_expected.json` `18419212…`）、`demo_projects/**`。
- 未跑全量套件；只在 14:10:19 跑了 4 件定向测试（63 passed）。
- `data/` 零访问；探针输入＝合成 DataFrame ＋ git 跟踪的 fixture CSV；未开库、未建快照。
- 外部在途 12 枚脏件（含 `src/output/interpretation.py`）本班未做任何 `checkout`／`restore`／改平。
