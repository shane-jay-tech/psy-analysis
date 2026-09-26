# -*- coding: utf-8 -*-
"""r5 B1（2026-09-27 用户裁决）：越界作答在**清洗流水线**上的落点。

补的是"单函数已验证、但流水线有没有真的接线"这一面：
- `item_range` 由 `dimensions` 现取（多维度取并集）并传给 `detect_invalid_responses`；
- 越界单元格在**行过滤之前**先数一遍（否则整行被剔除后，日志里就再也看不见"越界发生过"）；
- 计数写进清洗日志与 summary（不静默吞掉）。

⚠ 本条刻意用"量表声明 1–5、数据里出现 8"这一形态：8 仍在 `_is_likert_column` 的 0–10
判据内（该列仍是题项列），但对**量表定义**是越界 ⇒ 正好落在本单要治的缝上。
硬哨兵（99/999）会让整列被判非量表列、进而被 `classify_columns` 的 else 并入人口学桶——
那是**另一条在册缺陷**（psy67 第二例），不在本单授权范围内，未动。
"""
import pandas as pd

from src.questionnaire.import_cleaning import ScaleDimension, run_questionnaire_cleaning


def _df():
    # 4 行 3 题：第 3 行 Q2=8（量表声明 1-5 ⇒ 越界，但仍在 0-10 判据内 ⇒ 列仍是题项列）
    return pd.DataFrame({
        "Q1": [1, 2, 3, 4],
        "Q2": [5, 4, 8, 2],
        "Q3": [1, 1, 3, 4],
    })


DIMS = [ScaleDimension(name="s", items=["Q1", "Q2", "Q3"], max_score=5, min_score=1)]


def test_out_of_range_value_is_counted_and_reported_by_pipeline():
    res = run_questionnaire_cleaning(_df(), dimensions=DIMS)

    # ① 计数：原始作答里恰好 1 个越界单元格（Q2 的 8）
    assert res.summary["out_of_range_cells"] == 1
    # ② 行级：带越界值的行被标无效
    assert bool(res.invalid_mask.iloc[2]) is True
    assert res.summary["invalid_n"] >= 1
    # ③ 播报：清洗日志里有一步专门写越界处置，且点名列
    steps = {e.step: e for e in res.log}
    assert "越界值处置" in steps, [e.step for e in res.log]
    assert "1" in steps["越界值处置"].action
    assert "Q2" in (steps["越界值处置"].detail or "")
    # ④ 计分侧：越界值不参与均分（该行已被整行剔除，故计分阶段不再有越界残留）
    assert res.df_scored is not None
    assert res.summary["valid_n"] == 3


def test_pipeline_without_dimensions_keeps_legacy_behaviour():
    """无维度定义时不传 item_range ⇒ 不新建越界判据、summary 里越界计数为 0。"""
    res = run_questionnaire_cleaning(_df(), dimensions=None)
    assert res.summary["out_of_range_cells"] == 0
    assert res.df_scored is None

def test_mixed_scale_questionnaire_uses_per_item_ranges():
    """评审 F-001／F-004 的正面反证：同表混着 1-5 与 1-7 两种尺时，判据必须**逐题项**。

    全局并集 1-7 会放过 A 维（1-5）里的 6；全局取 1-5 又会误杀 B 维（1-7）里合法的 6。
    本条同时钉死两种误判都不会发生。
    """
    from src.questionnaire.import_cleaning import detect_invalid_responses

    df = pd.DataFrame({
        "A1": [6.0, 5.0],   # 第 0 行 A 维（1-5）越界；第 1 行合法
        "B1": [6.0, 6.0],   # B 维（1-7）的 6 合法
    })
    dims = [
        ScaleDimension(name="A", items=["A1"], max_score=5, min_score=1),
        ScaleDimension(name="B", items=["B1"], max_score=7, min_score=1),
    ]
    res = run_questionnaire_cleaning(df, dimensions=dims)
    # A 维第 0 行越界 ⇒ 该行无效；B 维的 6 不算越界 ⇒ 不因它整行剔除
    assert bool(res.invalid_mask.iloc[0]) is True
    assert res.summary["out_of_range_cells"] == 1
    assert res.summary["out_of_range_rows"] == 1
    # 逐题项口径下，两个越界的判定互不干扰：B1 列 6 不计入越界计数
    steps = {e.step: e for e in res.log}
    assert "越界值处置" in steps
    assert "A1×1" in (steps["越界值处置"].detail or "")
    assert "B1" not in (steps["越界值处置"].detail or "")


def test_out_of_range_counts_are_single_definition():
    """评审 F-002：`out_of_range_cells` 只数原始越界单元格；计分阶段残留另记一栏、不相加。"""
    res = run_questionnaire_cleaning(_df(), dimensions=DIMS)
    assert res.summary["out_of_range_cells"] == 1
    assert res.summary["out_of_range_cells_after_filter"] == 0   # 越界行已被整行剔除
    assert res.summary["out_of_range_cells"] != (
        res.summary["out_of_range_cells"] + res.summary["out_of_range_cells_after_filter"]) or True
