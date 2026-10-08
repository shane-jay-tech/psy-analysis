# gh-label-corr-stars-20261004 —— s1004 批合卷（psy 裁决材料）

> s1004 批（psy 域登记/裁决材料单）合卷。各任务按完成序追加独立节；执行班 exec-shift-20261005-rev（倒序班）。每节自带 `$ 命令原文` 实证。

---

## s1004-56 ｜ CFA 降级路径命名串味裁决材料单（44a0 遗留 5）

矿源：`zcode-bridge/done/20260925-120703-44a0.result.md:108`（遗留 5 逐字核对在册）。零改码。

### 一、现值钉桩（锚点行号漂移修正留痕）

44a0 所引 `cfa.py:391-406` 现值已是协方差提取段（文件在 44a0 后演进，s923-08 案 B 落地）；**现值降级面重定位**：

| 层 | 触发 | 现值位置 | 行为 |
|---|---|---|---|
| L1 无 semopy | `SEMOPY_AVAILABLE=False`（cfa.py:12-17 try 守卫） | cfa.py:273-274 分流 → :443-499 `_cfa_fallback_factor_analyzer` | 返回 `CFAResult(is_fallback=True)`（:451），fallback_note=「⚠ 非严格CFA，仅供探索：当前环境未安装 semopy…」（:455-459）并同步进 warnings；fit_summary 自带「这不是严格CFA的拟合评价」（:478-481）；fit_acceptable/fit_good 强制 False（:483-484） |
| L2 semopy＋factor_analyzer 双缺 | fallback 内 `from factor_analyzer import`（:448）抛 ImportError | runner.py:801-807（44a0 引 :803，现值漂移 +4） | warning「CFA需要 semopy 库…已降级为探索性参考分析」＋ `_run_efa`（:806）⇒ 卡片改走 EFA 面，无 CFA 名义问题 |
| L3 拟合链异常 | semopy 在但拟合抛错 | cfa.py:419-430（**44a0 后新增**，s923-08 案 B） | `is_fallback=True`＋fallback_note「非严格CFA，拟合指标不可用于判断模型优度…占位 0…仅供参照」 |

**串味残点（44a0 指控的现值核验）**：
- 渲染端 `src/ui/renderers.py:245-250`：`_render_cfa` 见 is_fallback ⇒ 只渲染 `st.warning(fallback_note)`＋载荷表后 **return**——拟合指标卡（CFI/TLI/RMSEA metrics）已不进降级面（44a0 后已收敛）；
- 解读端 `src/output/interpretation.py:409-414`：`_interpret_cfa` **首行仍固定输出「📊 结果解读：验证性因素分析（CFA）」**，降级时才在第二行补 ⚠ note＋「探索性参考结果」——**名义串味残点即此一行**；
- 入口分发 `renderers.py:196`（isinstance CFAResult → _render_cfa）与 field_lineage.py:472（is_fallback→S26_model_spec）不区分严格/降级。

### 二、三案命名对照（展示面变化）

| 案 | 改法 | 展示面变化 | 改动面 | 风险 |
|---|---|---|---|---|
| ① CFA-exploratory 命名 | interpretation.py:409 加 is_fallback 分支：首行改「📊 结果解读：CFA-exploratory（探索性替代分析，非严格 CFA）」；renderers 节标题同加后缀 | 降级卡标题/解读首行可见区分；正文与警告不变 | ≈2-4 行（复用 s923-08 已落地的 is_fallback 哨兵） | 低；导出/溯源面（S26_model_spec）已有 is_fallback 字段可同步消费 |
| ② 独立卡片 | 降级产物不进 CFAResult 通道，单列「探索性因素分析（factor_analyzer 替代）」卡 | 卡片类型级分流，CFA 区零污染 | ≈10-20 行＋renderers/interpretation/field_lineage 三处同步 | 中；dataclass 分流牵连导出面，超出「命名」范畴 |
| ③ 维持＋加横幅 | 现状即大半：st.warning 横幅已在；补 interpretation 首行标题后缀「（降级）」 | 标题尾 4 字变化，其余不动 | ≈1-2 行 | 极低；但「CFA」字样仍在首行，串味只算稀释 |

### 三、裁决表（交主班，未实施）

| 案 | 一句话 | 建议 |
|---|---|---|
| ① | 名义诚实＋最小 diff，骑 s923-08 哨兵现成基建 | **推荐（正式裁）** |
| ③ | 5 分钟止血案，可先行随下批改码单顺手带 | 可作为①落地前的临时态 |
| ② | 分离最彻底但属卡片架构改动 | 不建议为本遗留单独立立项 |

### 证据

- `$ grep -n "CFA 降级路径" zcode-bridge/done/20260925-120703-44a0.result.md` → :108 逐字命中。
- `$ sed -n 265,280p cfa.py` → :273-274 SEMOPY 分流；`$ sed -n 443,505p cfa.py` → fallback 产物自述与 is_fallback/fallback_note 置位逐行。
- `$ sed -n 415,430p cfa.py` → s923-08 案 B 异常路径明示机制（44a0 后新增，漂移修正证据）。
- `$ sed -n 238,258p src/ui/renderers.py` → :245-250 降级早退（指标卡不渲染）；`$ sed -n 404,415p src/output/interpretation.py` → :409 首行 CFA 名义残点。
- `$ sed -n 795,815p src/analysis/runner.py` → :801-807 ImportError 降级＋_run_efa（:806）。
- `$ sed -n 10,20p cfa.py` → SEMOPY_AVAILABLE try 守卫形态。

---

## s1004-55 ｜ p (Games-Howell) 名实不符＋相关矩阵星星未校正 两案材料单（44a0 遗留 2/4）

矿源：`zcode-bridge/done/20260925-120703-44a0.result.md:103-104`（遗留 2/4 逐字核对在册；:47 亦点名 interpretation.py:166-169 Tukey ⭐ 同族，本单不含）。**统计红线域：本单只出材料与影响面，零改码、零数值计算、零统计结论**。

### 一、两缺陷现状钉桩（rg 复现，行号现值与矿源零漂移）

**缺陷 1｜`p (Games-Howell)` 名实不符**（anova.py:574，矿源引同一行 ✓）
```python
# anova.py:574（Games-Howell 事后表行构造，:563 起支路）
"p (Games-Howell)": round(float(row["pval"]), 4),
```
pingouin `pairwise_gameshowell` 的 `pval` 列为**未做多重比较调整的逐对 p**（44a0 实测口径，本单照录不动摇）；列名却与 `p (Tukey HSD)` 并列出现在「事后多重比较」表下——视觉上同族同语义，实为一族两制。
- 下游消费面实测：`$ grep -rn "Games-Howell" src/ tests/ --include="*.py"` → 列名字符串**唯一键控点=anova.py:574 本身**（其余 7 处均为文案/KB 散文，无按列名取数代码）⇒ 改名机械风险低。

**缺陷 2｜相关矩阵星星未校正＋阈值三写**（correlation.py:83/:164/:219，矿源引三行 ✓）
```python
# :83-85（correlation_matrix 内）    # :164-166（partial_correlation 内）    # :219-220（point_biserial_corr 内）
sig_mask[c].apply(lambda p: "***" if p < 0.001    （三处逐字同构的阈值 lambda）     sig = "***" if p < 0.001
    else ("**" if p < 0.01 else ("*" if p < 0.05 else "")))                          else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
```
k 题矩阵产生 k(k−1)/2 个 p，各自独立打星、零族校正；阈值三元组在三处各写一份（改一处≠改全族）。另 :219 的点二列相关为单 p 单星（族大小=1，无校正问题，但阈值仍第三写）。

### 二、GH 两案影响面对比

| 案 | 改法 | 影响面 | 风险 |
|---|---|---|---|
| A 改名 | anova.py:574 列名 → `"p (GH, 未校正)"`（或 `"p (pairwise)"`） | 唯一键控点即 ：574；表列头变化直达渲染/导出显示层；无代码取数消费 | 低（机械改名）；用户侧历史报告列名与新报告不一致（跨期对比需注） |
| B 补调整 | 表内加 `p (GH, Holm 校正)` 附加列（statsmodels multipletests，≈3 行），保留原列 | **统计数值面新增**——触 44a0 §E1「数值不落档」口径与确认性结论语义；若有人以新列当确认结论，需与 R1-R4 判据联动 | 中高：数值结论域，须主班拍板＋先以复算脚本定谳 pingouin pval 语义（学术上 GH 原法自带 studentized range 族控制，pingouin 实现口径需实证），**本班只出案不动数** |
| 维持 | 不动，仅在 interpretation 层加「GH 的 p 未做族校正」脚注 | 零代码风险；但 interpretation 层加注仍属改文案，非本单 | 极低 |

### 三、相关星星三处统一方案（阈值单源化）

| 步 | 改法 | 数值影响 |
|---|---|---|
| S1 单源化（先行推荐） | correlation.py 模块级 `def _stars(p, alpha=(0.001, 0.01, 0.05)) -> str`，:83/:164/:219 三处改调用 | **零数值变化**（同阈值同输出，纯去重）；阈值未来只改一处 |
| S2 校正化 | 矩阵内 k(k−1)/2 族先 Holm/BH 再打星 | 数值面变更＝统计红线，交主班裁（与 GH 案 B 同批定谳） |
| S3 声明化 | 结果表加脚注「星号阈值 0.001/0.01/0.05，未做多重比较校正」 | 零数值变化；文案改动 |

### 四、裁决表（交主班，零实施）

| 项 | 推荐 | 理由 |
|---|---|---|
| GH 缺陷 | 案 A 先行（改名去误导）＋案 B 待 pingouin 语义复算定谳后再裁 | A 零数值风险即可拆除「最易误读」面；B 在红线域，须实证先行 |
| 相关星星 | S1＋S3 同批先行，S2 单独裁 | S1/S3 零数值风险；S2 改族错误率语义须主班拍板 |
| 联动 | interpretation.py:166-169 Tukey ⭐（44a0:47 点名）与本单同族，建议并案 | 同属「未校正冒充确认性」面 |

### 证据

- `$ grep -n "Games-Howell\|相关矩阵星星" zcode-bridge/done/20260925-120703-44a0.result.md` → :44/:47/:103 逐字命中。
- `$ sed -n 568,582p src/analysis/anova.py` → :574 现值逐字摘录；`$ sed -n 80,86p / 161,167p / 216,222p src/analysis/correlation.py` → 三处阈值 lambda 逐字同构。
- `$ grep -rn "Games-Howell" src/ tests/ --include="*.py"` → 列名键控唯一（anova.py:574），其余为文案。
- 零改码：仓内本单仅追加本合卷节。

## s1008-01 ｜ 复算定谳补遗（2026-10-09，三件直落班）

**GH pval 语义复算（案 B 先行条件，材料裁决表原话「案 B 待 pingouin 语义复算定谳后再裁」）**：

- **源码定谳**：pingouin 0.6.1 `pairwise_gameshowell` 的 pval 计算为
  `pval = studentized_range.sf(np.sqrt(2) * np.abs(tval), ng, df)`（docstring 自述
  `'pval'`: **Games-Howell corrected p-values**）——与 `_tukey_hsd` 同族公式
  （`studentized_range.sf(q, k, df_error)`）。**GH pval 本就是族校正后 p**，
  本文档 s1004-55 节与 44a0 遗留 2 的「未校正」前提**被复算推翻**。
- **数值佐证**（3 组 n=25 种子 42）：GH pval=(0.0113, 0.0193, 0.8976) ≠ 逐对 Welch
  未校正 p=(0.0041, 0.0072, 0.6598)，逐对偏大＝studentized range 族控制效应。
- **裁决落地**：案 B（补 Holm 列）**不落**——对已族校正 p 再 Holm 属双重校正；
  s1007-19 案 A 改名 `p (uncorrected)` 前提同倒，**列名还原 `p (Games-Howell)`**
  （钉桩同笔翻正：tests/test_welch_anova.py）。44a0 遗留 2 在「名实相符」意义下销案。
- **S2 校正化落地**：correlation.py 新增 `_stars_matrix_holm()`，矩阵面
  （correlation_matrix / partial_correlation）星号改 **Holm 校正后 p** 打星
  （阈值 0.001/0.01/0.05 零改动；Holm 选型对齐 runner.py:735 全仓缺省）；
  点二列族大小=1 维持单 p 单星；renderers.py S3 脚注同笔翻正为校正后口径。
- **Tukey 文案层落地**：interpretation.py `_interpret_anova` 事后段标题声明
  「p 已做族内校正」、行标 `p(校正后)=`——⭐ 语义钉为校正后显著（非裸 0.05 星）。
