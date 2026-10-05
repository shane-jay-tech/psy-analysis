# psychometrics 效度/信度阈值族集中常量化设计稿（s1002-36，2026-10-06，零数值改动）

- 承 s920-05 遗留 2/3。**全量盘点两文件四形态**；本稿只设计，数值一个不改。

## 一、点位普查（rg 复现命令与计数）

```
$ grep -nE "[0-9]\.[0-9]{2}" src/questionnaire/psychometrics.py | wc -l   → 15 处文案面
$ grep -nE "0\.(60|70|80|90)" src/analysis/reliability.py | wc -l         → 16 处代码判据面
$ grep -rn ">= 0.4" src/ui/undergrad_wizard.py                            → :3605（向导阈值，域外参照）
```

### A. psychometrics.py——**全部 15 处均为指南文案面**（f-string 字符串内），零代码判据

| 段 | 统计量 | 行号 | 阈值 |
|---|---|---|---|
| 内容效度 | CVI | :22 | ≥0.80 |
| 内容效度 | I-CVI | :37 | ≥0.78 |
| 内容效度 | S-CVI/Ave | :38 | ≥0.90 |
| EFA 前提 | KMO | :78 | ≥0.80 |
| EFA | 因子载荷 | :83 | ≥0.40（交叉 <0.30） |
| CFA | CFI/TLI | :88-89 | ≥0.90 可接受 / ≥0.95 良好 |
| CFA | RMSEA | :90 | <0.08 / <0.05 |
| CFA | SRMR | :91 | <0.08 |
| 聚合效度 | AVE | :93 | ≥0.50 |
| 组合信度 | CR | :95 | ≥0.70 |
| α 说明 | 题间相关 | :111 | 0.15-0.50 理想 |
| 项目分析 | CITC | :114 | <0.30 删题 |
| ICC | ICC | :117 | ≥0.70 |
| 分半 | 分半 | :121 | ≥0.70 |
| 题目冗余 | 相关 | :44-46 | 0.3-0.7 带 |

**要点**：psychometrics.py 的「阈值」全部是**给用户读的指南文案**——常量化的意义不是消重（多数只出现一次），而是**判据与文案同源**（改阈值时指南自动跟，防「代码判据 0.70/文案 0.80」漂移）。

### B. reliability.py——**代码判据面 16 处**（α 档位外同构裸写）

| 统计量 | 行号 | 形态 |
|---|---|---|
| α 档位 | :70-77 一族 | **已有档位逻辑**（s920-05 已常量化的那族，作为形态样板） |
| 分半 | :119 | `sb_r >= 0.70` 裸判＋warning 文案双写（矿源遗留 3 的第二份） |
| ω | :177-178 | `omega < 0.70` 裸判＋文案 |

### C. 域外参照（不在本稿迁移面，登记防漏）

- undergrad_wizard.py:3605 向导阈值 `>= 0.4`（文献相关性，非心理测量判据，**不入常量模块**）。

## 二、常量模块设计

**归属**：新建 `src/analysis/thresholds.py`（与 reliability 同域；psychometrics 在 questionnaire 域但消费同一批判据，import 方向 analysis←questionnaire 已有先例〔result_card〕）。

```python
# 每个统计量一组「档位表 + 判据线 + 文案模板」；数值照抄现值，零改动
CFA = ThresholdSet(good=0.95, acceptable=0.90, direction="ge", label="CFI")
RMSEA = ThresholdSet(good=0.05, acceptable=0.08, direction="le", label="RMSEA")
SCVI, ICVI, CVI = ...      # 0.90 / 0.78 / 0.80
AVE, CR, ICC = ...         # 0.50 / 0.70 / 0.70
CITC, SPLIT_HALF, OMEGA = ...  # 0.30 / 0.70 / 0.70
KMO, LOADING = ...         # 0.80 / 0.40
```

## 三、迁移顺序与快照红名单

1. **先落 thresholds.py**（纯增量，零红）；
2. **reliability.py 分半/ω 三处**（遗留 3 点名的第二份收敛点）换引用——红名单：`test_reliability_*` 若有钉裸字面量的用例需同批（先 `rg -n "0.70" tests/test_analysis_reliability*` 现取，预估 ≤3 例）；
3. **psychometrics.py 文案面 f-string 改插值**——红名单：`test_psychometrics_charac.py` 的文本包含断言若钉了「≥ 0.80」字样需同批（实测 :22/:37 等段有快照例，预估 2-4 例）；
4. **分半第二份**（design_engine 的 split_half 模板 :0.70 文案）属 experiment 域文案，独立小步收编。

## 四、零数值声明

本稿全文出现的数值均为**照抄现值的登记**（快照用途），非新判据；实施单落地时 diff 里每个数值必须能在本表找到同值出处。
