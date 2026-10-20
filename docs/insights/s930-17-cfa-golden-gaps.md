# CFA golden 钉桩缺口与四条裁决项对照材料

> 产出单：s930-17（exec-shift-20261002-0151）｜2026-10-02
> 矿源：s927-10 遗留（tolerance 段/loadings_min-max 零使用＋四条人工裁决项）。
> 零生产码/测试改动；interpretation.py 为在途 M 件只读。

## 一、钉桩缺口复核（tolerance 段／loadings_min-max）

| 项 | 矿源断言 | 本班复核 | 结论 |
|---|---|---|---|
| `cfa_expected.json` tolerance 段（CFI 0.05/TLI 0.05/RMSEA 0.03/SRMR 0.03） | 两版测试都没用过 | **cfa 侧确认零消费**——test_cfa_sem_golden.py 的 `golden["tolerance"]` 消费点在 `_golden("sem")`（sem_expected.json，:312）；`_golden("cfa")` 消费段（:268 起 `expected`）未见 tolerance 取用 | **缺口仍在**（cfa 面 tolerance 无钉）；且注意 cfa.py:79 有**生产侧自有**阈值（srmr acceptable 0.08 等）——JSON tolerance 与生产常量双源，补钉前需先裁以谁为准 |
| loadings_min 0.50 / loadings_max 0.95 | 从不被钉 | 在 `expected` 段内（:13/:16 现读），cfa 测试消费段零引用 | **缺口仍在**；0.50/0.95 的语义是「载荷界内」验收带——`test_loadings_and_path_rows_shapes` 只钉行数未钉值域，是最小补钉位 |

## 二、四条裁决项逐点现状

| 裁决项 | 本班实测 | 材料结论 |
|---|---|---|
| ① CFI/TLI 越界 clamp 容差 1e-3 与「判未通过」口径 | `cfa.py:73` `FIT_RANGE_TOLERANCE = 1e-3` 在位（评审意见 #3 注释：浮点误差超 1 如 1.0000001 不判不通过）；golden 件 ：260-275 钉「越界（CFI/TLI>1）必须判不通过」＋ clamp 与判据并存 | 双机制**职责分明**：1e-3 管「数值 sanitation」（1.0000001→1.0），fit_acceptable 管「实质越界」（>1+1e-3 判不通过）——与统计规范兼容，**建议维持**；唯一要写进档的是两者次序（先 clamp 后判），现实现即此序 |
| ② semopy 2.3.11 是否本就不出 SRMR | **实测定谳**：calc_stats 键面＝{AGFI,AIC,BIC,CFI,DoF,DoF Baseline,GFI,LogLik,NFI,RMSEA,TLI,chi2,chi2 Baseline,chi2 p-value}——**无 SRMR**；生产侧 cfa.py:130 `getattr(result_cfa,'SRMR',0)` 恒落 0.0 | **成立**——srmr=0.0 是「不提供」占位而非真值 0（真值 0 会被 cfa.py:79 的 0.05 阈误判「极好」）。**建议**：srmr 字段显式标 `None`/「semopy 不提供」＋下游展示面跳过该行，消除 0.0 假信号 |
| ③ chi2 p-value 与 chi2/DoF 同源性 | calc_stats 键面三键并存（chi2/DoF/chi2 p-value）——semopy 内部 p-value 由 chi2 分布生存函数自 chi2/DoF 计算（非独立测量） | **同源成立**：三键是同一统计量的三个投影，验证 p 时不得当作第二证据源 |
| ④ interpretation.py 显著载荷计数 R5（p<0.05 数 4 枚 NaN 的口径） | interpretation.py 为在途 M 件；grep 无「CFA 载荷 p<0.05 计数」现读点（:421 行号已漂/该面在在途 diff 中） | **R5 待在途收口后复核**——在途版行号与语义都以工作树为准不可靠，现裁会裁在移动靶上 |

## 三、建议

1. 补钉最小位＝`test_loadings_and_path_rows_shapes` 加载总值域断言（0.50≤|loading|≤0.95，数字全读 cfa_expected.json）——顺手可把 tolerance 段一并接上（CFI/TLI/RMSEA 三键，SRMR 键等裁决②改标后再接）；
2. 裁决②建议批「srmr 显式不提供」；①③维持现状并登记口径注记；④挂起等在途。
