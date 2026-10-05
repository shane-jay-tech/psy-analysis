# 向导假设检验 ⑱/⑲ 两缺陷裁决材料（s1002-39，2026-10-06，只读）

- 承 s920-15 遗留 1/2。两缺陷的在册钉桩**均活且绿**（test_afg_list_shaped…/test_afg_test_type_without…，复跑 2 passed）。

## 一、⑱ list 误标正态性（真 bug 形状）

### 复现读数（探针=在册钉桩例实况）

```
输入：assumptions = {"homogeneity": [{"passed": True}, {"passed": False}]}   # 方差齐性以 list 报
输出（用户可见）：「正态性检验未通过」＋推荐 Mann-Whitney U（Welch 零提及）
对照（dict 形态同语义）：「方差不齐已自动处理/无需切换」或推荐 Welch
```

### 根因行

undergrad_wizard.py 路由段（:1862 一带的 normality_failed/homogeneity_failed 判定循环）：对 `assumptions[key]` 的**形态不分派**——list 逐元素判 passed 时失败被归入 `normality_failed`（循环写在正态性判定块），而 dict 形态走按 key 分派的分支。

### 一行修法与推荐口径影响面

修法＝list 分支内按 `key`（homogeneity/normality）归桶（矿源「一行」）。**影响面（推荐口径会变的 test_type）**：仅当上游分析器以 **list 形态**汇报方差齐性时触发——受影响面=哪些分析器输出 list 形态 assumptions（`rg -n "assumptions\[|assumptions = \[" src/analysis/` 现取；本机初探 analysis 面以 dict 为主 ⇒ **实盘触发面可能为空**，属防御性修复而非现行 bug）。改后 ⑱ 钉桩（test_afg_list_shaped…）红，翻正为「list 形态正确路由到 Welch/齐性文案」。

## 二、⑲ 无替代映射零提示

### 现值清单

| test_type | nonparametric_map | welch_map | 假设失败时用户可见 |
|---|---|---|---|
| independent_ttest / paired_ttest / one_way_anova / pearson_corr | ✅ | ✅/部分 | 替代建议横幅 |
| **mediation / hierarchical_regression / moderation / partial_corr / 任意其余** | ❌ | ❌ | **零提示**（`alt is None: return`，:3385 段） |

复现实锚：test_afg_test_type_without_mapped_alternative_stays_silent（mediation+normality fail ⇒ markdowns==[]）。

### 补映射草案（统计口径供日间复核）

| test_type | 正态性失败替代 | 理由一句 |
|---|---|---|
| hierarchical_regression | 秩回归（rank-robust）或 robust SE 提示 | 非参数层级回归非主流，提示为主 |
| moderation | 变量变换提示＋robust 回归 | 同上 |
| partial_corr | Spearman 偏相关提示 | 秩次偏相关非标准，提示为主 |
| mediation | Bootstrap 提示（已有）＋正态性仅影响 CI 法 | 中介以 Bootstrap 为主 ⇒ 正态性失败影响有限，提示「建议确认 Bootstrap 已启用」 |

**替代方案**：不补映射、改为「无映射时显示通用提示『该检验暂无内置替代方案，请参考方法学文档』」——把静默变可观测，统计口径零风险（推荐先行）。

## 三、零码改自证

两缺陷现状复现走既有钉桩例（零新探针落盘）；src/ 零触碰。
