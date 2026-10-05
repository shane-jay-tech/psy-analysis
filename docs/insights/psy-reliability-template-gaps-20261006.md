# ReliabilityResult 指南模板缺口裁决材料（s1002-37，2026-10-06，报告型零文案落码）

- 承 s920-06 遗留 1/2。**现值实测定谳**（python 直查 TEST_TEMPLATES 键集）：
  模板 26 键中无 `mcdonald_omega`/`composite_reliability`/`icc`/`test_retest`/`cohens_kappa`/`fleiss_kappa` **六类全缺**。

## 一、六类现状表

| test_type | 有无 TEST_TEMPLATES | 有无 _RELIABILITY_MAIN_LABEL 主值标签 | 现状用户可见面 |
|---|---|---|---|
| mcdonald_omega | **无** | **有（"ω"，:647）** | why/steps/alts 三段空/default 兜底；主值标签正常 |
| composite_reliability | **无** | **有（"CR"，:648）** | 同上 |
| icc | **无** | **无** | 三段空/default＋**主值无标签**（`.alpha` 槽位装 icc 值照搬 α 文案＝错语义） |
| test_retest | **无** | **无** | 同上 |
| cohens_kappa | **无** | **无** | 同上 |
| fleiss_kappa | **无** | **无** | 同上 |

数据侧佐证：ReliabilityResult 是**多态载荷**（字段含 icc_value/omega_value/cr_per_factor/test_retest_r/kappa_value/kappa_method），六类全往 `.alpha` 槽位装值——`:516` 前提文案「小样本会导致**α**估计不稳定」被六类复用 ⇒ **语义漂移实锤**（ω/CR/κ 说「α 估计不稳定」不知所指）。

## 二、_RELIABILITY_MAIN_LABEL 扩展面（标签草案，供日间复核）

```python
"icc": "ICC",
"test_retest": "重测信度 r",
"cohens_kappa": "κ (Cohen)",
"fleiss_kappa": "κ (Fleiss)",
```
- 归属注意：κ 两族是**一致性系数非信度系数**，扩展时建议表名语义改为 `_RELIABILITY_MAIN_LABEL` → `_AGREEMENT_MAIN_LABEL` 或加注释分层（数据建模裁量）。

## 三、TEST_TEMPLATES 六条文案草案（骨架，判据文本须日间复核）

每条四段（why/steps/interpretation_guide/alternatives）骨架要点：
1. **mcdonald_omega**：why=ω 处理非 τ 等价（各题载荷不等）时的 α 替代；steps=单因子/多因子结构声明＋样本量；interp=≥0.70 可接受（引用 thresholds 模块同源，勿裸写）；alts=α（τ 等价时）、CR。
2. **composite_reliability**：why=CFA 框架下的组合信度；steps=因子结构先经 CFA 确定；interp=≥0.70/AVE≥0.50 配套读；alts=ω、α。
3. **icc**：why=连续型评分者一致性/重测；steps=模型（single/average、absolute/consistency）声明＋评分者数；interp=≥0.70 可接受；alts=Cohen/Fleiss κ（分类型）。
4. **test_retest**：why=时间稳定性；steps=间隔声明＋被试稳定性；interp=≥0.70；alts=ICC。
5. **cohens_kappa**：why=两评分者分类一致（校正机遇一致）；steps=二分/多分类＋边际分布；interp=≥0.60 实质一致（Landis-Koch 族，判据文本复核点）；alts=Fleiss κ（多评分者）、Gwet AC1。
6. **fleiss_kappa**：why=多评分者分类一致；steps=评分者数≥3＋类别固定；interp=同 κ 族；alts=Krippendorff α。

**前提文案修正**（:516 语义问题）：六类拆出后该条改为按 test_type 分发——信度族保留「α 估计不稳定」措辞仅限 cronbach_alpha/split_half，ω/CR 改「载荷模型不稳定」，ICC/重测改「评分者/间隔稳定性不足」，κ 改「类别边际过偏」。

## 四、实施红名单预估

- reasoning.py 六条新增＝纯增量零红；`_RELIABILITY_MAIN_LABEL` 扩展 4 行＝增量零红；
- :516 分发改 if/elif 族＝需 `rg -n "α 估计不稳定" tests/` 现取钉该文案的快照例（预估 1-2 例同批）。
- 语义红线：全部草案为**建议文本**，判据数值与措辞须经日间（测量学）复核后才可落码。
