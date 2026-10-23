# SRMR good 档双源冲突证据材料（s1023-04 出材件，决议#21 主班闸）

> 性质：**纯材料件，零数值改动**。s1007-37 遗留「srmr good 档 0.05 vs 0.08 双源冲突」维持主班闸（决议#21 未裁数值口径）；本件只做双源定位、钉桩现值核对与改判影响面普查，**不裁决、不改任何数值**。

## 一、双源对照表（2026-10-24 实测）

| | 源① cfa.py 本地 | 源② thresholds.py 统一档 |
|---|---|---|
| 位置 | `src/analysis/cfa.py:84` | `src/analysis/thresholds.py:33` |
| 现值 | `"srmr": {"good": 0.05, "acceptable": 0.08}` | `SRMR = ThresholdSet(good=0.08, acceptable=0.08, direction="le")` |
| good 档 | **0.05** | **0.08** |
| 消费点 | cfa.py:140 `good_srmr` 判据、:147 `is_good`、:151 summary 文案「SRMR ≤ .05」 | golden JSON 侧＋设计稿文案侧（见下同侧清单） |
| 来源链 | s1007-37 归一单「srmr 留本地」时发现冲突后按原值钉住（commit a1004ea） | thresholds 模块设计稿（psy-thresholds-module-design-20261006）落地值 |

**源②同侧证据（0.08 侧）**：
- `tests/fixtures/golden_stats/psychometrics/cfa_expected.json:12` → `"SRMR_max": 0.08`
- `docs/insights/psy-thresholds-module-design-20261006.md:24` → 登记表「CFA ｜ SRMR ｜ :91 ｜ <0.08」（设计稿文案侧）
- `src/paper_writer/literature_manager.py:951` → 仓内在档文献注「SRMR<0.08」经典口径

**第三面（UI 内联，跟随源①侧）**：`src/ui/renderers.py:264` → SRMR delta 文案 `"≤.05 良好" if r.srmr <= 0.05 else ("≤.08 可接受" ...)`——good 档展示判据内联 0.05，未引 thresholds 单源。

**提示词文案面（无判读逻辑，改判后是否随动待裁）**：`llm_engine.py:172`、`llm_engine_premium.py:951/:1582` → 均写「SRMR < 0.08」（文案层，与源②同值）。

## 二、钉桩测试双侧现值核对（实跑绿）

| 钉桩 | 位置 | 现值断言 |
|---|---|---|
| s1007-37 双源钉桩·源①侧 | `tests/test_cfa_thresholds_unified_s1007_37.py:17` | `cfa.FIT_THRESHOLDS["srmr"] == {"good": 0.05, "acceptable": 0.08}` |
| s1007-37 双源钉桩·源②侧 | 同件 `:18` | `th.SRMR.good == 0.08 and th.SRMR.acceptable == 0.08` |
| thresholds golden 钉桩 | `tests/test_thresholds_golden.py:16` | `"SRMR": (0.08, 0.08, "le", "SRMR")` |
| golden 耦合件边界声明 | `tests/test_cfa_sem_golden.py:254` | 「SRMR 键待裁决②后接，本用例不消费」 |

`$ python -m pytest tests/test_cfa_thresholds_unified_s1007_37.py tests/test_thresholds_golden.py tests/test_cfa_sem_golden.py -q` → **27 passed**（2026-10-24 02:55 前后实测，双侧钉桩现值与盘面一致）。

## 三、改判影响面普查（改判波及的测试/文档）

**若裁 0.08（源②侧胜，即现 thresholds/golden/设计稿/文献注既有 majority）**：
| 波及面 | 动作 |
|---|---|
| cfa.py:84 | good 0.05→0.08（或按 s1007-37 原案直接引 `th.SRMR` 单源归一，消灭本地键） |
| cfa.py:151 | good summary 文案「SRMR ≤ .05」→「.08」 |
| renderers.py:264 | UI delta 文案 good 分支 0.05→0.08（内联面与档位联动） |
| test_cfa_thresholds_unified_s1007_37.py:17 | 断言改 0.08（钉桩测试改断言即闭环，s1007-37 遗留原文口径） |

**若裁 0.05（源①侧胜）**：
| 波及面 | 动作 |
|---|---|
| thresholds.py:33 | good 0.08→0.05 |
| test_thresholds_golden.py:16 | EXPECTED["SRMR"] good 0.08→0.05 |
| cfa_expected.json:12 | `SRMR_max` 0.08→0.05（golden fixture 数值面）＋test_cfa_sem_golden 消费面复核 |
| 设计稿 :24 | 登记表「<0.08」→「<0.05」（＋行号指针漂移顺带订正，见 §四） |
| renderers.py:264 | 无需改（已随源①侧 0.05） |

## 四、锚点漂移与连带发现（留痕）

1. 设计稿登记表行号指针整体过时（:22/:91/:121 等——现 thresholds.py 全文仅 46 行）：**文档滞后实锤**，属文档偏离对账单（s1023-10）范围，本件只登记不改文档。
2. renderers.py:264 的内联 good 档判据（0.05）未引 thresholds 单源——构成**第三处隐性数值源**，无论裁哪侧都建议实施单顺带收归单源（属实施面，本件不实施）。
3. s1014-01 所记钉桩「双侧在位」现值复核 ✅ 与本件 §二一致，无漂移。

## 五、裁决注意（供主班，非本件结论）

- 裁决语义本质：SRMR good 档与 RMSEA good 档是否同值（源① 0.05 与 RMSEA good 同档）还是与 acceptable/文献经典口径同值（源② 0.08）。仓内不持有外部文献数值结论，文献注仅 literature_manager.py:951 一处「SRMR<0.08」——数值口径裁决所需外部依据需主班自持。
- 裁决后闭环路径：s1007-37 遗留原文已备「裁后本钉桩测试改断言即闭环」。
