"""边界值／缺失值／非法值／多量尺反向题的用例集（信箱单 20260925-120657-c47f）。

覆盖面（三处生产面＋一处声明面）：

* `src/questionnaire/import_cleaning.py`：`reverse_score`／`compute_dimension_scores`／
  `detect_invalid_responses`／`classify_columns`／`_is_likert_column`
* `src/analysis/data_quality.py::handle_missing`（四种缺失策略＋删列阈值的边界）
* `src/questionnaire/data_dictionary.py::Codebook`（量尺上下限／缺失码歧义的**声明级**判据）

两条书写规矩：

1. **每条用例都写预期值**（判据要求），期望值来自"量表定义的算术"而不是"跑出来的数"；
2. 期望值与现网实况**不一致**时，本档不改生产码，而是把该用例写成
   `test_..._现网实况_在册缺陷未修` 的**实况钉**（docstring 里写明"修复后本用例应转红"），
   并把缺陷登记进 result 的「遗留问题」交人工裁决。
   仓内件按纪律用"缺件即红"，不用 `skipif` 判文件在不在。
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.analysis.data_quality import handle_missing
from src.questionnaire.data_dictionary import (
    Codebook,
    CodebookEntry,
    codebook_from_schema,
)
from src.questionnaire.import_cleaning import (
    ScaleDimension,
    _is_likert_column,
    classify_columns,
    compute_dimension_scores,
    detect_invalid_responses,
    reverse_score,
)

# ---------------------------------------------------------------------------
# 边界值 × 多量尺：反向计分的算术预期
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lo, hi, inputs, expected",
    [
        (1, 5, [1, 2, 3, 4, 5], [5.0, 4.0, 3.0, 2.0, 1.0]),          # 五点：上下限互换
        (1, 6, [1, 2, 4, 6], [6.0, 5.0, 3.0, 1.0]),                  # 六点
        (1, 4, [1, 2, 3, 4], [4.0, 3.0, 2.0, 1.0]),                  # 四点
        (0, 5, [0, 1, 3, 5], [5.0, 4.0, 2.0, 0.0]),                  # 零点起：0 与 5 互换
        (0, 10, [0, 3, 5, 7, 10], [10.0, 7.0, 5.0, 3.0, 0.0]),       # 十一点数字评定尺
        (1, 7, [1, 2, 3, 4, 5, 7], [7.0, 6.0, 5.0, 4.0, 3.0, 1.0]),  # 七点
    ],
)
def test_reverse_score_boundaries_per_scale(lo, hi, inputs, expected):
    """每个量尺的上下限都必须精确落在另一端：反向题的预期值是 (lo+hi)-x。"""

    series = pd.Series([float(x) for x in inputs])
    got = reverse_score(series, max_score=hi, min_score=lo)
    assert got.tolist() == expected


def test_reverse_score_endpoints_are_exact_and_sum_is_constant():
    """任意点的"原分＋反向分"恒等于 (lo+hi) —— 多量尺反向题的守恒式。"""

    for lo, hi in [(1, 5), (1, 6), (0, 5), (1, 4), (0, 10)]:
        series = pd.Series([lo, hi], dtype="float64")
        got = reverse_score(series, max_score=hi, min_score=lo)
        assert (series + got).tolist() == [float(lo + hi), float(lo + hi)]


def test_reverse_score_preserves_nan_without_inventing_a_score():
    """缺失不能变成任何分数：NaN 反向后仍是 NaN（预期值 = nan）。"""

    got = reverse_score(pd.Series([1.0, np.nan, 5.0]), max_score=5, min_score=1)
    assert got.iloc[0] == 5.0
    assert math.isnan(got.iloc[1])
    assert got.iloc[2] == 1.0


def test_reverse_score_with_wrong_scale_args_is_a_silent_wrong_answer():
    """现网实况（钉，不是期望）：量尺参数给错时不报错，只给一个"看起来合法"的错分数。

    1-6 尺上的 1／6 用默认 1-5 参数反向 ⇒ 得 5／0；0 落在 1-5 尺外，但函数不拦。
    修复（加范围校验或按字典取量尺）后本用例应转红并随修案改写。
    """

    series = pd.Series([1.0, 6.0])
    got = reverse_score(series)  # 默认 max_score=5, min_score=1
    assert got.tolist() == [5.0, 0.0]
    assert 0.0 not in [1, 2, 3, 4, 5]  # 结果越出了默认量尺，无人报警


# ---------------------------------------------------------------------------
# 缺失值：计分面
# ---------------------------------------------------------------------------


def test_dimension_scores_partial_missing_averages_over_survivors():
    """现网实况（钉）：一行只答了两题，均分照算，且不告诉调用方分母变小了。

    预期（现状）：Q1=1、Q2=5、Q3=NaN ⇒ mean 3.0、sum 6.0。
    期望（人工裁决项）：应带"有效题数 2/3"的元数据，否则 3.0 与"三题都答 3"无法区分。
    """

    df = pd.DataFrame({"Q1": [1.0], "Q2": [5.0], "Q3": [np.nan]})
    dims = [ScaleDimension(name="焦虑", items=["Q1", "Q2", "Q3"])]
    scored = compute_dimension_scores(df, dims)
    assert scored["焦虑_mean"].iloc[0] == 3.0
    assert scored["焦虑_sum"].iloc[0] == 6.0
    assert list(scored.columns) == ["焦虑_mean", "焦虑_sum"]  # 没有任何有效题数列


def test_dimension_scores_all_missing_row_gives_nan_mean_but_zero_sum():
    """现网实况（钉）：整行缺失 ⇒ mean 是 NaN（正确），但 sum 是 **0.0**（与"真考了最低分"同形）。

    0.0 在 1-5 尺上比最小可能分还小，属"看起来是一格"的假值；
    本用例钉现状，修复（sum 也应 NaN 或带有效题数）后应转红。
    """

    df = pd.DataFrame({"Q1": [np.nan], "Q2": [np.nan]})
    dims = [ScaleDimension(name="抑郁", items=["Q1", "Q2"])]
    scored = compute_dimension_scores(df, dims)
    assert math.isnan(scored["抑郁_mean"].iloc[0])
    assert scored["抑郁_sum"].iloc[0] == 0.0


@pytest.mark.parametrize(
    "raw, expect_nan",
    [("", True), (" ", True), ("null", True), ("NA", True), ("-", True),
     ("N/A", True), ("缺", True), ("3", False)],
)
def test_missing_value_spellings_become_nan_and_never_a_number(raw, expect_nan):
    """缺失值书写形态：字符串记号一律 coerce 成 NaN，不得变成 0 或其它分数。"""

    df = pd.DataFrame({"Q1": [raw], "Q2": [2.0]})
    scored = compute_dimension_scores(df, [ScaleDimension(name="s", items=["Q1", "Q2"])])
    if expect_nan:
        assert scored["s_mean"].iloc[0] == 2.0, f"{raw!r} 被当成了数值"
    else:
        assert scored["s_mean"].iloc[0] == 2.5


def test_reverse_on_missing_item_stays_missing():
    """反向题缺答：反向步骤不得把 NaN 变成数（预期 nan），也不得把该行救活。"""

    df = pd.DataFrame({"Q1": [np.nan], "Q2": [2.0]})
    dims = [ScaleDimension(name="s", items=["Q1", "Q2"], reverse_items=["Q1"],
                           max_score=5, min_score=1)]
    scored = compute_dimension_scores(df, dims)
    # Q1 反向后仍是 NaN ⇒ 均分只由 Q2（=2）贡献；缺答没有被反向步骤救活成任何分数
    assert scored["s_mean"].iloc[0] == 2.0
    assert scored["s_sum"].iloc[0] == 2.0


# ---------------------------------------------------------------------------
# 非法值
# ---------------------------------------------------------------------------


def test_out_of_range_value_is_not_scored_越界不再变成有效分数():
    """**r5 B1 已修**（2026-09-27 用户裁决）：99 在 1-5 尺上是越界 ⇒ 置空，不进反向计分。

    改前 `(1+5)-99 = -93` 被吸收进均分（-44.0）；现在 Q1 先置 NaN ⇒ 均分只由 Q2(=5) 贡献。
    越界单元格按列回传（`out_of_range_counts`）⇒ 清洗日志与报告可显式播报，不静默吞掉。
    """

    df = pd.DataFrame({"Q1": [99.0], "Q2": [5.0]})
    dims = [ScaleDimension(name="s", items=["Q1", "Q2"], reverse_items=["Q1"],
                           max_score=5, min_score=1)]
    counts: dict = {}
    scored = compute_dimension_scores(df, dims, out_of_range_counts=counts)
    assert scored["s_mean"].iloc[0] == 5.0
    assert scored["s_sum"].iloc[0] == 5.0
    assert counts == {"Q1": 1}
    # 行级：带越界作答的行现被标无效（只在显式给逐题项范围时生效）
    assert bool(detect_invalid_responses(
        df, ["Q1", "Q2"], item_ranges={"Q1": (1, 5), "Q2": (1, 5)}).iloc[0]) is True
    # 向后兼容：不传 item_ranges 时行级判据与改前逐位一致
    assert bool(detect_invalid_responses(df, ["Q1", "Q2"]).iloc[0]) is False


def test_below_scale_min_is_dropped_not_scored():
    """**r5 B1 已修**：1-5 尺上的 0（非法）不再被当合法分数吃进均分（改前预期 2.0）。"""

    df = pd.DataFrame({"Q1": [0.0], "Q2": [4.0]})
    dims = [ScaleDimension(name="s", items=["Q1", "Q2"], max_score=5, min_score=1)]
    counts: dict = {}
    scored = compute_dimension_scores(df, dims, out_of_range_counts=counts)
    assert scored["s_mean"].iloc[0] == 4.0
    assert counts == {"Q1": 1}


def test_non_numeric_text_never_becomes_zero_score():
    """非法文本（"abc"）必须成 NaN：不得静默变 0 分（判据正面成立的一例）。"""

    df = pd.DataFrame({"Q1": ["abc"], "Q2": [4.0]})
    scored = compute_dimension_scores(df, [ScaleDimension(name="s", items=["Q1", "Q2"])])
    assert scored["s_mean"].iloc[0] == 4.0
    assert scored["s_sum"].iloc[0] == 4.0


def test_scientific_notation_value_is_out_of_range_and_dropped():
    """**r5 B1 已修**："1e5" 仍被 `to_numeric` 认成 100000，但它在 1-5 尺上越界 ⇒ 置空不计分。

    改前它会被直接平均进维度分（50002.0）——"越界静默变成有效分数"的第二种形态。
    """

    df = pd.DataFrame({"Q1": ["1e5"], "Q2": [4.0]})
    counts: dict = {}
    scored = compute_dimension_scores(
        df, [ScaleDimension(name="s", items=["Q1", "Q2"])], out_of_range_counts=counts)
    assert scored["s_mean"].iloc[0] == 4.0
    assert counts == {"Q1": 1}


def test_out_of_range_column_is_silently_reclassified_as_demographic():
    """现网实况（钉）：越界列不进题目桶，被 `classify_columns` 的 else 分支**并入人口学桶**。

    999 一列 ⇒ item_columns 里没有它 ⇒ 它不参与计分（这一侧是保护），
    但也没有任何"未识别列"告警（psy67 已在册的同一条：`未识别列=[]` 且无告警）。
    """

    df = pd.DataFrame({"Q1": [1, 2, 3], "Q2": [4, 5, 4], "怪列": [999, 999, 999]})
    cls = classify_columns(df)
    assert cls.item_columns == ["Q1", "Q2"]
    assert "怪列" in cls.demographic_columns
    assert not hasattr(cls, "unidentified_columns")  # 载体上根本没有"未识别"这一格


@pytest.mark.parametrize(
    "values, expected",
    [
        ([1, 2, 3, 4, 5], True),      # 1-5 尺
        ([0, 1, 2], True),            # 含 0 且跨度 <=9 ⇒ 仍算 Likert
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], False),  # 11 个唯值：超出 10 个上限
        ([1, 5, 99], False),          # max>10 ⇒ 判非量表列
        ([1, 5, -1], False),          # min<0
        ([1], False),                 # 唯一值 ⇒ 零方差，不算量表
    ],
)
def test_likert_column_boundary_rules(values, expected):
    """`_is_likert_column` 的边界：唯值数 1 判否、11 判否；值域 [-1,..]／[..,11] 判否。"""

    assert _is_likert_column(pd.Series(values, dtype="float64")) is expected


# ---------------------------------------------------------------------------
# handle_missing 四策略与阈值边界
# ---------------------------------------------------------------------------


def _mixed_df() -> pd.DataFrame:
    return pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0, 5.0],
                         "b": [10.0, np.nan, 0.0, np.nan, 50.0],
                         "c": [1, 1, 1, 1, 1]})


def test_handle_missing_listwise_expected_rows():
    df = _mixed_df()
    out, meta = handle_missing(df, numeric_cols=["a", "b"], strategy="listwise")
    assert len(out) == 2                       # 只有第 0、4 行两列齐全
    assert meta["rows_removed"] == 3
    assert meta["n_after"] == 2
    assert "60.0%" in meta["description_zh"]    # 3/5 被删
    assert "建议检查缺失机制" in meta["description_zh"]  # >15% 的加警


def test_handle_missing_listwise_at_15_percent_boundary_has_no_extra_warning():
    """阈值边界：正好 15%（删 1/≈6.67%…）—— 用 20 行删 3 行 = 15.0%，不触发高缺失警告。"""

    df = pd.DataFrame({"a": [1.0] * 20, "b": [1.0] * 20})
    df.loc[[0, 1, 2], "b"] = np.nan
    out, meta = handle_missing(df, numeric_cols=["a", "b"], strategy="listwise")
    assert meta["rows_removed"] == 3
    assert "建议检查缺失机制" not in meta["description_zh"]
    assert len(out) == 17


def test_handle_missing_pairwise_keeps_every_row():
    df = _mixed_df()
    out, meta = handle_missing(df, numeric_cols=["a", "b"], strategy="pairwise")
    assert len(out) == 5
    assert meta["rows_removed"] == 0
    assert "不同分析可能基于不同样本量" in meta["description_zh"]


def test_handle_missing_mean_imputation_expected_fill_value():
    df = _mixed_df()
    out, meta = handle_missing(df, numeric_cols=["a", "b"], strategy="mean_imputation")
    assert out["a"].isna().sum() == 0
    assert out.loc[2, "a"] == 3.0              # (1+2+4+5)/4
    assert out.loc[0, "b"] == 10.0
    assert out.loc[1, "b"] == 20.0             # (10+0+50)/3
    assert sorted(meta["imputed_cols"]) == ["a", "b"]
    assert "低估标准误" in meta["description_zh"]


def test_handle_missing_mean_imputation_fills_outlier_contaminated_mean_as_is():
    """现网实况（钉）：插补用的是**含非法值的列均值** ⇒ 非法值把Everyone 的填补值一起带偏。

    列 [1, 5, 99999] 的均值 33335.0 会填进缺失位 —— 越界值未参与任何拦截。
    """

    df = pd.DataFrame({"a": [1.0, 5.0, 99999.0, np.nan]})
    out, _ = handle_missing(df, numeric_cols=["a"], strategy="mean_imputation")
    assert out.loc[3, "a"] == 33335.0


@pytest.mark.parametrize(
    "n_missing, threshold, dropped",
    [(2, 0.50, False),   # 4 行缺 2 = 0.50：等于阈值 ⇒ **不删**（判据是严格大于）
     (3, 0.50, True),    # 0.75 ⇒ 删
     (2, 0.49, True),    # 阈值下调后 0.5 > 0.49 ⇒ 删
     (0, 0.50, False)],
)
def test_handle_missing_drop_column_threshold_boundary(n_missing, threshold, dropped):
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [1.0, 2.0, 3.0, 4.0]})
    if n_missing:
        df.iloc[:n_missing, df.columns.get_loc("a")] = np.nan
    out, meta = handle_missing(df, numeric_cols=["a", "b"],
                               strategy="drop_column", drop_threshold=threshold)
    assert (("a" in meta["removed_col_names"]) is dropped)
    assert meta["cols_removed"] == (1 if dropped else 0)
    assert "b" not in meta["removed_col_names"]


# ---------------------------------------------------------------------------
# 声明面：字典对量尺与缺失码的判据（这部分是真的会拦）
# ---------------------------------------------------------------------------


def test_codebook_flags_reverse_item_on_flat_scale():
    cb = Codebook(entries=[CodebookEntry(item_no="Q1", var_name="Q1", reverse=True,
                                        scale_min=3, scale_max=3)])
    assert [c.code for c in cb.conflicts()] == ["E_REVERSE_FLAT"]


def test_codebook_flags_inverted_scale_range():
    cb = Codebook(entries=[CodebookEntry(item_no="Q1", var_name="Q1", scale_min=5,
                                        scale_max=1)])
    assert "E_SCALE_RANGE" in [c.code for c in cb.conflicts()]


def test_codebook_flags_missing_code_colliding_with_legal_option():
    """1-5 尺上把 "3" 声明成缺失码 ⇒ 无法与真实作答区分（E_MISSING_AMBIGUOUS）；
    而 "0"／"9" 在尺外 ⇒ 不报歧义。这是"非法值不静默变有效分"的**声明级**正面判据。"""

    ambiguous = Codebook(entries=[CodebookEntry(item_no="Q1", var_name="Q1",
                                               scale_min=1, scale_max=5,
                                               missing_codes=("3",))])
    assert "E_MISSING_AMBIGUOUS" in [c.code for c in ambiguous.conflicts()]
    safe = Codebook(entries=[CodebookEntry(item_no="Q1", var_name="Q1",
                                          scale_min=1, scale_max=5,
                                          missing_codes=("0", "9", "-1"))])
    assert [c.code for c in safe.conflicts()] == []


def test_codebook_multi_scale_items_keep_their_own_ranges():
    """多量尺：同一份字典里 1-5 与 0-10 两尺各记各的，不被归成一个默认尺。"""

    cb = Codebook(entries=[
        CodebookEntry("A1", "A1", scale="SAS", scale_min=1, scale_max=5, reverse=True),
        CodebookEntry("B1", "B1", scale="NRS", scale_min=0, scale_max=10),
    ])
    assert cb.conflicts() == []
    a1, b1 = cb.entries
    assert (a1.scale_min, a1.scale_max, a1.reverse) == (1, 5, True)
    assert (b1.scale_min, b1.scale_max, b1.reverse) == (0, 10, False)


def test_demo_schema_is_registered_without_a_version_and_that_is_reported():
    """演示项目的 schema 没有版本键 ⇒ 字典判 E_VERSION（不伪造版本号）。"""

    import json
    import pathlib

    path = pathlib.Path(__file__).resolve().parents[1] / \
        "demo_projects/psychology_questionnaire_demo/questionnaire_schema.json"
    cb = codebook_from_schema(json.loads(path.read_text(encoding="utf-8")))
    codes = [c.code for c in cb.conflicts()]
    assert "E_VERSION" in codes
    assert any(c.code == "E_VERSION" and "no-version" in c.detail for c in cb.conflicts())


def test_detect_invalid_responses_expected_flags_per_rule():
    """无效作答标记的预期值：太快=真、全同=真、正常=假；越界值不在判据内（见上钉）。"""

    df = pd.DataFrame({
        "Q1": [1, 1, 2, 5, 999],
        "Q2": [1, 1, 4, 4, 999],
        "时长": [30, 300, 300, 300, 300],
    })
    mask = detect_invalid_responses(df, ["Q1", "Q2"], min_duration_seconds=60,
                                    duration_column="时长")
    assert mask.tolist() == [True, True, False, False, True]
    # 逐行预期：0 行 30 秒 < 60 ⇒ 太快；1 行 Q1=Q2=1 ⇒ std=0 命中「同质作答」；
    # 2 行 (2,4) ⇒ std≠0 且众数占比 0.5 ⇒ 不命中；3 行 (5,4) ⇒ 同样不命中；
    # 4 行 999,999 ⇒ std=0 命中（越界值本身仍不在判据内，只是恰好两列相同才被逮到）。
    assert mask.tolist() == [True, True, False, False, True]


def test_identical_answering_is_flagged_by_zero_std():
    df = pd.DataFrame({"Q1": [3, 3, 3], "Q2": [3, 3, 3], "Q3": [3, 3, 3]})
    mask = detect_invalid_responses(df, ["Q1", "Q2", "Q3"], min_duration_seconds=60)
    assert mask.tolist() == [True, True, True]
