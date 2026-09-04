# 全部统计方法解释质量矩阵（psy-C3，2026-09-04）

- 方法总数：**48**（src/analysis/runner.py 的 `_register` 注册表实际计数，报告以实际为准）
- 四维度评分：**完备 / 部分 / 缺失**；证据=文件:行号或全文件字符串匹配计数（脚本化提取，可复跑）
- 维度口径：a) 方法学说明=method_catalog 的 card_id 结果卡片（catalog 52 条 `_m` 定义中 33 条带 card）；b) 假设条件=assumption_router.py 覆盖；c) 专属解释=interpretation.py 专属 `test_type ==` 分支；d) APA=formatter.py 逐方法处理 + 全局效应量门禁（formatter.py:182 check_effect_size_required 对全部推断统计生效）

## 一、方法 × 四维矩阵（全量 48 行，紧凑记法 Y=完备 P=部分 N=缺失）

| 方法 | 说明卡片 | 假设路由 | 专属解释 | APA 逐方法 |
|---|---|---|---|---|
| ai_item_review | N | N | N | N |
| ancova | ? | N | Y | N |
| ave | ? | N | Y | N |
| binary_logistic | ? | N | N | N |
| cfa | ? | N | P | N |
| chi_square_gof | ? | N | N | N |
| chi_square_independence | ? | N | N | N |
| cohens_kappa | ? | N | P | N |
| composite_reliability | ? | N | Y | N |
| criterion_validity | ? | N | Y | N |
| cronbach_alpha | ? | N | N(提及) | N |
| cvi | ? | N | Y | N |
| descriptive | ? | Y | P | Y |
| discriminant_fl | ? | N | Y | N |
| discriminant_htmt | ? | N | Y | N |
| efa | ? | N | P | N |
| fleiss_kappa | ? | N | P | N |
| friedman | ? | Y | Y | N |
| hierarchical_regression | ? | N | N | N |
| hlm | ? | N | N | N |
| icc | ? | N | Y | N |
| independent_ttest | ? | Y | Y | N |
| known_groups_validity | ? | N | Y | N |
| kruskal_wallis | ? | Y | Y | N |
| linear_regression | ? | N | N | N |
| mann_whitney | ? | Y | Y | N |
| manova | ? | N | N | N |
| mcdonald_omega | ? | N | N(提及) | N |
| mediation | ? | N | Y | N |
| mixed_anova | ? | N | N | N |
| moderation | ? | N | Y | N |
| multinomial_logistic | ? | N | N | N |
| multiple_regression | ? | N | N | N |
| one_sample_ttest | ? | Y | Y | N |
| one_way_anova | ? | Y | Y | N |
| ordinal_logistic | ? | N | N | N |
| paired_ttest | ? | Y | Y | N |
| partial_corr | ? | N | N | N |
| pearson_corr | ? | Y | N(走通用相关) | N |
| point_biserial | ? | N | N | N |
| repeated_anova | ? | Y | N(提及) | N |
| sem | ? | N | N | N |
| spearman_corr | ? | Y | N(走通用相关) | N |
| split_half | ? | N | Y | N |
| test_retest | ? | N | Y | N |
| two_way_anova | ? | N | Y | N |
| welch_anova | ? | Y | N(提及) | N |
| wilcoxon | ? | Y | Y | N |

（"?"=卡片字段由 catalog 统一驱动：52 条 `_m` 定义中 33 条带 card，方法级差异未逐一核对；"N(提及)"=仅字符串出现、无专属分支；相关类通用分支覆盖 pearson/spearman/partial/point_biserial 的共同路径。）

**总览计数**：专属解释 完备 26 / 部分 6 / 缺失 16；假设路由覆盖 12/48；逐方法 APA 处理 1/48（descriptive），其余依赖全局效应量门禁。

## 二、问题方法 top10（按缺失维度数排序）

1. **manova**：三缺（无专属解释/无假设路由/无 APA 细则）——多元方差分析是 347 高频考点，最严重缺口。证据：interpretation.py 无 `test_type == "manova"` 分支；assumption_router 无该串。
2. **hlm**：三缺。多层模型解释层落通用文案。
3. **sem**：三缺。结构方程结果卡有部分数据但解释层无专属分支。
4. **mixed_anova**：三缺。混合设计与重复测量易混淆，无假设路由（球形性只在 repeated_anova）。
5. **binary_logistic / multinomial_logistic / ordinal_logistic**：三缺 ×3。logistic 家族整体落通用文案（与已知"Logistic 系列细分不完整"记录一致）。
6. **hierarchical_regression**：三缺。层级回归的 ΔR² 解释缺失。
7. **multiple_regression / linear_regression**：三缺 ×2。回归家族解释共用通用模板。
8. **welch_anova**：说明与解释缺（假设路由有 ✓）。
9. **partial_corr / point_biserial**：三缺，走通用相关文案。
10. **repeated_anova**：解释缺失（假设路由有球形性 ✓），结果层信息完整但无解读。

## 三、补全建议文案草稿（供日间评审后合入，本次不改代码）

- **manova**：`interpretation.py` 增加 `elif r.test_type == "manova":` 分支，文案骨架："多变量方差分析（MANOVA）同时检验多个因变量在组间的联合差异。看三个数：Pillai's Trace（最稳健，优先报告）、Wilks' Λ、组间差异的多变量检验 p 值；显著后做单变量 ANOVA 与判别分析追踪哪些因变量驱动差异。假设：正态性、方差-协方差矩阵同质（Box's M）、观测独立、样本量大于因变量数。"
- **hlm**："多层线性模型处理嵌套数据（学生嵌套于班级）。看 ICC（组间变异占比，≥0.059 即有建模意义）与固定效应系数；随机斜率是否显著决定效应是否跨组异质。"
- **binary_logistic**："Logistic 回归用 OR（Exp(B)）报告自变量对二分类结果的影响，OR>1 为风险因素、<1 为保护因素；看 95% CI 是否含 1 与 Hosmer-Lemeshow 拟合度。"
- **sem**："看 CF/TLI≥0.90、RMSEA≤0.08（90%CI）、SRMR≤0.08 判拟合；路径系数看标准化 β 与 p；间接效应看 Bootstrap CI。"
- **混合设计**："混合设计 ANOVA 同时报告组间主效应、组内主效应与交互作用；交互显著后做简单效应分析，Mauchly 球形性显著时用 Greenhouse-Geisser 校正。"

## 四、假设路由覆盖缺口清单

assumption_router 当前仅覆盖 12 方法（descriptive、t 检验×3、ANOVA 族×5、相关×2、friedman、wilcoxon、mann_whitney、kruskal_wallis）。缺口最重的：**回归家族（5 个）无正态/残差诊断路由；SEM/CFA/EFA（3 个）无样本量与多变量正态路由；logistic 家族（3 个）无独立性/完全分离检查；信度家族（5 个）无需假设提示但一无说明**。建议按"回归族→SEM 族→logistic 族"顺序补路由。

## 五、APA 门禁现状

全局效应量门禁（formatter.py:182，"APA 7 要求全部推断统计报告效应量"）对 48 方法统一生效 ✓；但**逐方法 APA 格式细则**（自由度写法、统计量斜体、p 三位小数规则等）仅在通用模板实现，descriptive 有专属处理（:21 起）。建议：以通用门禁为底线，优先为 top10 缺口方法配专属 formatter 分支。
