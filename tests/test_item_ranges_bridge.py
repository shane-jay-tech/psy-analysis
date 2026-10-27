"""s1025-03 工单-1：问卷→统计链交接桥钉桩。

①run_questionnaire_cleaning 的 CleaningResult 现在携带 item_ranges（含多维度交集规则）；
②bridge_item_ranges_to_plan 仅在键⊆df 列时附挂，其余零行为变更。
"""

import pandas as pd

from src.questionnaire.import_cleaning import (
    ScaleDimension,
    bridge_item_ranges_to_plan,
    run_questionnaire_cleaning,
)
from src.parser.intent_resolver import AnalysisPlan


def _df():
    return pd.DataFrame(
        {
            "q1": [1, 2, 3, 4, 5, 3],
            "q2": [2, 3, 4, 5, 4, 3],
            "q3": [5, 4, 3, 2, 1, 3],
            "性别": ["男", "女", "男", "女", "男", "女"],
        }
    )


def _dims():
    return [
        ScaleDimension(name="焦虑", items=["q1", "q2"], min_score=1, max_score=5),
        ScaleDimension(name="回避", items=["q3"], min_score=1, max_score=7),
    ]


def test_cleaning_result_carries_item_ranges():
    result = run_questionnaire_cleaning(_df(), dimensions=_dims())
    assert result.item_ranges == {"q1": (1.0, 5.0), "q2": (1.0, 5.0), "q3": (1.0, 7.0)}


def test_cleaning_result_item_ranges_intersection_on_conflict():
    dims = [
        ScaleDimension(name="A", items=["q1"], min_score=1, max_score=5),
        ScaleDimension(name="B", items=["q1", "q2"], min_score=2, max_score=7),
    ]
    result = run_questionnaire_cleaning(_df(), dimensions=dims)
    # q1 双维度声明不同尺 ⇒ 取交集 (2, 5)（更严一侧）
    assert result.item_ranges["q1"] == (2.0, 5.0)


def test_cleaning_without_dimensions_keeps_ranges_none():
    result = run_questionnaire_cleaning(_df(), dimensions=None)
    assert result.item_ranges is None


def test_bridge_attaches_when_keys_subset_of_columns():
    plan = AnalysisPlan(test_type="independent_ttest")
    cleaned = run_questionnaire_cleaning(_df(), dimensions=_dims())
    bridge_item_ranges_to_plan(plan, cleaned, _df())
    assert plan.item_ranges == {"q1": (1.0, 5.0), "q2": (1.0, 5.0), "q3": (1.0, 7.0)}


def test_bridge_skips_when_columns_mismatch():
    plan = AnalysisPlan(test_type="independent_ttest")
    cleaned = run_questionnaire_cleaning(_df(), dimensions=_dims())
    other_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    bridge_item_ranges_to_plan(plan, cleaned, other_df)
    assert plan.item_ranges is None


def test_bridge_noop_without_ranges_or_plan():
    plan = AnalysisPlan(test_type="independent_ttest")
    bridge_item_ranges_to_plan(plan, None, _df())
    assert plan.item_ranges is None
    no_ranges = run_questionnaire_cleaning(_df(), dimensions=None)
    bridge_item_ranges_to_plan(plan, no_ranges, _df())
    assert plan.item_ranges is None
