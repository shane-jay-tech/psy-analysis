# 非法值静默计分三案裁决材料（c47f 遗留）——s1004-54

> 执行班 exec-shift-20261005-rev ｜ 2026-10-05T01:52 实测 ｜ 性质：裁决材料+落地核验，**零改码零数值计算**
> 矿源：`zcode-bridge/done/20260925-120657-c47f.result.md:63-78`（E2 六条实测读数＋机理链逐字核对在册）。

## 一、⚠ 总漂移：三案已于 2026-09-27 r5 B1 用户裁决并落地

任务书前提「三案待裁、执行手不自拍」已过时——**`6a12eb9`「psy: 越界作答不再当有效分数（r5 B1，统计口径；含 GPT 独立评审处置）」已收编**，采用 **案 b＋案 c 组合**（案 a 未采）。本单转为落地核验＋残余面登记。

## 二、三案 → 落地形态对账（触点/风险/回滚）

| 案 | c47f 提案 | 落地形态（现值实测） | 触点 | 风险面 | 回滚链 |
|---|---|---|---|---|---|
| a | `reverse_score` 前按字典量尺越界校验并**抛错** | **未采**：`import_cleaning.py:109-111` 仍为无校验线性变换 `(max+min)-series` | — | 裸调 `reverse_score` 绕过 compute 的调用方仍会静默产出负分（残余风险，见 §四） | — |
| b | `detect_invalid_responses` 增「越界占比」判据 | **已采（变体升级）**：:150 起新增 `item_ranges={题项: (lo,hi)}` 参数——**逐题项**量尺范围，含越界作答的行标无效（评审 F-001/F-004 多尺共存驱动，比「全局占比」更精细） | import_cleaning.py:150-162＋调用面 | 行级无效数改变 ⇒ 下游 α/N 输入面已随 9/27 裁决一并接受 | revert 6a12eb9 |
| c | `compute_dimension_scores` 对越界值置 NaN | **已采（前置化）**：:114-124 先把 `[dim.min_score, dim.max_score]` 之外值置 NaN **再做反向**（docstring 明记 r5 B1 与「-93 进均分」案例），越界单元格按列计数进 `out_of_range_counts` | import_cleaning.py:114-148＋data_quality.py 计数通道 | 历史复算结果全变（9/27 已拍板接受） | revert 6a12eb9 |

**9/27 新增管道测试件**：`tests/test_out_of_range_pipeline_20260927.py`（4 例）——越界计数（`out_of_range_cells==1`）、行级无效（`invalid_mask.iloc[2] is True`）、清洗日志「越界值处置」步三点名，全绿。

## 三、落地证绿（定向复跑）

`$ "D:/Program/python.exe" -m pytest tests/test_data_transforms.py tests/test_out_of_range_pipeline_20260927.py tests/test_questionnaire_boundary_and_invalid_values.py tests/test_questionnaire_import_cleaning.py -q`
→ **89 passed，rc=0**（2.47s）。c47f E2 的三条🚫读数（-44.0／2.0 吃 0／50002.0）所对应的用例族现值全绿；两条✅（文本 NaN、缺失记号）回归面无破坏。

## 四、残余面登记（建议日间/主班核查，本单未动）

1. **插补面二次污染**（c47f E2 点名 `mean_imputation`，`[1,5,99999]→33335.0`）：r5 B1 治了计分与行判据两面，`src/analysis/data_quality.py` 的插补面未见越界防护 grep 命中——若插补仍吃含越界的列均值，属 c47f 机理链第 4 口子未闭合，建议单独立单。
2. **案 a 未采的裸调风险**：`reverse_score` 公共函数仍可被绕过 compute 的调用方静默误用（`src/data/transforms.py:98` 另有一平行实现）；当前仓内调用是否全部经 compute 前置 NaN 通道，建议纳入 n930 类巡检口径。
3. **classify_columns 哨兵桶**（c47f:40 表三：99/999 硬哨兵整列被并入人口学桶）：test_out_of_range 文件头注「正好落在本单要治的缝上」——该缝现状由 item_ranges 判据兜住行级，列级分桶静默改桶面未见专门处置，随残余面①并查。

## 五、证据

- `$ grep -n "E2\|越界\|静默计分" zcode-bridge/done/20260925-120657-c47f.result.md` → :15/:43/:63-78 逐字命中（六读数＋四口子机理）。
- `$ sed -n 106,124p src/questionnaire/import_cleaning.py` → :109-111 reverse_score 无校验现值＋:114-124 compute r5 B1 docstring；`$ sed -n 150,162p` → item_ranges 参数与 docstring。
- `$ git log --oneline -2 -- src/questionnaire/import_cleaning.py` → 6a12eb9（r5 B1 收编笔）/ 097a657。
- `$ grep -n "def test\|assert" tests/test_out_of_range_pipeline_20260927.py` → 4 例三断言面。
- `$ pytest <四件> -q` → 89 passed rc=0。
- 零改码：`git status` 本单前后无 src/tests 变更（只新增本档）。
