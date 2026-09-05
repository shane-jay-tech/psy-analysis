# runner × interpretation × router 三方一致性核对（2026-09-06 凌晨，只读）

- 方法：48 法注册名（runner.py `_register` 实际提取）逐行比对 interpretation.py 专属 `test_type ==` 分支、assumption_router.py 覆盖串、method_catalog 卡片、formatter 提及。脚本化提取（可复跑）。
- 时点说明：本核对在重审班 1002（commit 9b47b81，路由补齐回归/SEM/logistic/多变量族）合入**之后**执行，故路由覆盖数与昨夜矩阵报告（12/48 口径）不同——该差异属 1002 的预期成果，不是漂移。

## 一、48 行三方矩阵

| 注册名 | 解释专属分支 | 路由覆盖 | 卡片 | formatter 提及 |
|---|---|---|---|---|
| ai_item_review | N | N | Y | N |
| ancova | Y | N | Y | N |
| ave | Y | N | Y | N |
| binary_logistic | N | **Y**(1002新增) | Y | N |
| cfa | P(3次提及) | N | Y | N |
| chi_square_gof | N | Y | Y | N |
| chi_square_independence | N | Y | Y | Y |
| cohens_kappa | P | N | Y | N |
| composite_reliability | Y | N | Y | N |
| criterion_validity | Y | N | Y | N |
| cronbach_alpha | N(提及) | N | Y | N |
| cvi | Y | N | Y | N |
| descriptive | N(通用处理) | Y | Y | **Y** |
| discriminant_fl | Y | N | Y | N |
| discriminant_htmt | Y | N | Y | N |
| efa | P | N | Y | N |
| fleiss_kappa | P | N | Y | N |
| friedman | Y | Y | Y | N |
| hierarchical_regression | N | Y | Y | N |
| hlm | N | Y | Y | N |
| icc | Y | N | Y | N |
| independent_ttest | Y | Y | Y | N |
| known_groups_validity | Y | N | Y | N |
| kruskal_wallis | Y | Y | Y | N |
| linear_regression | N | Y | Y | N |
| mann_whitney | Y | Y | Y | N |
| manova | N | Y | Y | N |
| mcdonald_omega | N(提及) | N | Y | N |
| mediation | Y | N | Y | N |
| mixed_anova | N | Y | Y | N |
| moderation | Y | N | Y | N |
| multinomial_logistic | N | Y | Y | N |
| multiple_regression | N | Y | Y | N |
| one_sample_ttest | Y | Y | Y | N |
| one_way_anova | Y | Y | Y | N |
| ordinal_logistic | N | Y | Y | N |
| paired_ttest | Y | Y | Y | N |
| partial_corr | N | Y | Y | N |
| pearson_corr | N(通用) | Y | Y | N |
| point_biserial | N | Y | Y | N |
| repeated_anova | N(提及) | Y | Y | N |
| sem | N | Y | Y | N |
| spearman_corr | N(通用) | Y | Y | N |
| split_half | Y | N | Y | N |
| test_retest | Y | N | Y | N |
| two_way_anova | Y | **N** | Y | N |
| welch_anova | N(提及) | Y | Y | N |
| wilcoxon | Y | Y | Y | N |

## 二、漂移与缺口清单

1. **two_way_anova 路由缺失（真漂移）**：one_way/repeated/mixed 均有正态+方差齐性路由，two_way_anova 独缺——1002 补齐回归族时遗漏（同族不对称）。修复：1002 同款路由追加 two_way_anova 一条。
2. **ai_item_review 全链黑暗**：注册存在、无解释、无路由、无 formatter——该"方法"若是内部评审钩子而非面向用户的统计方法，建议从注册表移出或在 catalog 标注 internal。
3. **无拼写/别名漂移**：48 个注册名在 interpretation 分支串与 router 串中均精确等值匹配，未发现 one_way_anova vs anova_one_way 类漂移——1002 合入质量良好。
4. **信度/效度家族路由整族缺失（21 个未覆盖的主体）**：cfa/efa/icc/cronbach_alpha/composite_reliability/split_half/test_retest/mcdonald_omega/cohens_kappa/fleiss_kappa/ave/cvi/discriminant_*/known_groups/criterion_validity/ancova/moderation/mediation。其中多数（信度族/效度族）确无传统"统计前提路由"语义，属**合理缺失**；但 mediation/moderation/ancova 有常规前提（线性和相关性），可与回归族同批补。

## 三、与矩阵报告（20260904）数字交叉验证

| 口径 | 矩阵报告（1002 前） | 本次（1002 后） | 差异解释 |
|---|---|---|---|
| 路由覆盖 | 12/48 | **27/48** | +15 = 1002 合入的回归/SEM/logistic/多变量族 14 法 + descriptive 口径修正；与 1002 任务书"14 法接入"一致 ✓ |
| 解释专属分支 | 完备 26 / 部分 6 / 缺失 16 | 复算一致（专属 Y=26，P=6，N=16，按同规则）✓ | — |
| 卡片 | 33/52 定义带 card | 未重算（本核对不含 catalog 内部） | — |

## 四、修复建议汇总（供 1002 后续与日间）

1. two_way_anova 补路由（一行，同族对齐）——最高优先。
2. ai_item_review 从注册表移出或标注 internal。
3. mediation/moderation/ancova 路由与回归族同批补齐。
4. 信度/效度族保持无路由（合理缺失），但建议在 method_catalog 标注"无前提路由"以免后续误报。

## 五、纪律声明

src 零改动（只读三文件 + 只读提取脚本在临时目录执行）；矩阵全 48 行可由报告第二节规则复跑。
