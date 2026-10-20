# repeated_anova subject_col 透传设计稿（plan 增字段前置）——s1004-43

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T02:3x ｜ 性质：**只设计**，零码改动
> 矿源：`zcode-bridge/done/20260925-154315-a7a1.result.md` 遗留 5（逐字核对在册：不传 subject_col／无逐时点 N／不查正态三处读数）。
> 禁令守约：正态检查是否补属 s927-18 前提覆盖域，**本稿不裁**。

## 一、三处读数现状取证

| # | 读数 | 证据 |
|---|---|---|
| 1 | handler 未透传 | `$ sed -n 156,164p src/analysis/runner.py` → `_run_repeated_anova` 只调 `anova.repeated_measures_anova(df, plan.dependent_vars)` 两参（:163），`subject_col` 未传 |
| 2 | 函数签名已支持 | `$ sed -n 304,329p src/analysis/anova.py` → `def repeated_measures_anova(df, dv_cols, subject_col: str = None, ...)`（:306），函数体 `if subject_col and subject_col in df.columns: cols.append(subject_col)`（:327-329）在世——**能力已在，只差最后一公里** |
| 3 | 无逐时点 N／不查正态 | 函数体：listwise `clean.dropna()` 后直接 AnovaRM；ANOVAResult 无 per-timepoint N 字段；无 normality 分支（正态面本稿不裁，仅登记缺口） |

## 二、三步透传方案（每步波及面行数估算）

**步骤 1｜被试列来源（两案，前置裁决）**

| 案 | 动作 | 波及面 |
|---|---|---|
| 1a 复用 `plan.grouping_var` | 零 schema 改动——grouping_var 在重复测量（无组间因子）语境下语义空闲，mixed_anova 已用它做 subject（runner.py:175 `plan.grouping_var or "subject"`） | handler 透传 1 行；风险=「grouping_var=组间因子」的旧语义混载，需 docstring 声明 |
| 1b plan 增 `subject_col` 字段（a7a1 原案） | `intent_resolver.py:18` 区 dataclass +1 行（`subject_col: Optional[str] = None`）；解析层填充位 +3~5 行（从 raw_request 识别「被试/subject」关键词）或先 UI 传参 | schema +1、解析 +3~5、UI +2~3 ≈ **6~9 行**；优点=语义干净、与 mixed_anova 的 grouping_var 不串 |

**步骤 2｜handler 透传**

- runner.py:163 一行：`anova.repeated_measures_anova(df, plan.dependent_vars, subject_col=plan.subject_col or plan.grouping_var)`（1a/1b 通吃）；缺列时沿用 mixed_anova 同款存在性报错（runner.py:177-178 原文可复制，+3 行）。
- 波及面：**1 行主改动＋3 行报错**；结果卡零变（subject 列只参与对齐，不进表）。

**步骤 3｜逐时点 N 展示**

- anova.py：`ANOVAResult` 增 `n_per_timepoint: Optional[Dict[str, int]] = None`（+1 字段）；函数体在 clean 前后各算一次 `df[dv_cols].notna().sum().to_dict()` 与 listwise 后 N（+3~4 行）——正好把「listwise 掉了多少被试」暴露出来（a7a1 E3 同族的静默丢失面）。
- 渲染面：renderers/interpretation 结果卡 +2~3 行（「各时点 N：T1=45/T2=43/T3=41（完整 Case N=40）」）。
- 波及面合计 ≈ **7~9 行**；golden 快照面（test_output_snapshot_roundtrip 族）若断言渲染文本需同步 +1~2 处期望值。

**三步合计 ≈ 9~15 行（1a）或 13~21 行（1b）**，均不触统计数值计算面（subject 列只改对齐方式——⚠ 这会改变 listwise 丢行行为，属**输入面变化**，落地时须带 golden 对照：合法完整宽表结果应逐字节不变，含缺失宽表的 N 面变化如实进 result 遗留）。

## 三、留主班三问

1. 步骤 1 选 1a（零 schema、语义借载）还是 1b（+6~9 行、语义干净）——本稿倾向 **1a**（改动面最小且 mixed_anova 已立先例）；
2. 步骤 3 的逐时点 N 是否并入 s927-18 的前提覆盖域一齐做（同触渲染面，一次改两处省一轮回归）；
3. 正态检查缺口（读数 3 后半）按禁令不裁，登记 s927-18。

### 证据存根

- `$ sed -n 156,164p src/analysis/runner.py` → 未透传逐字；`$ sed -n 304,329p src/analysis/anova.py` → 签名与 subject_col 消费位；`$ grep -n "grouping_var" src/parser/intent_resolver.py` → :18 字段在世。
- 零码改动守约：仓内仅本档。
