"""s1025-03 工单-2：AnalysisPlan.item_ranges 工作区序列化往返钉桩。

两例：①带域 plan 保存→载入后 item_ranges 等值往返（JSON 面列表→tuple 还原）；
②无域 plan 与旧工作区文件（无该键）载入后维持 None＝零行为变更。
"""

import json

from src.utils.workspace import _serialize_plan, _deserialize_plan
from src.parser.intent_resolver import AnalysisPlan


def _plan(item_ranges=None):
    return AnalysisPlan(
        test_type="independent_ttest",
        dependent_vars=["score"],
        independent_vars=["group"],
        grouping_var="group",
        covariates=[],
        scale_items=["q1", "q2"],
        blocks=[],
        test_value=None,
        confidence_level=0.95,
        raw_request="t检验",
        parsed_keywords=[],
        ambiguity_score=0.0,
        suggested_followups=[],
        item_ranges=item_ranges,
    )


def test_plan_with_item_ranges_roundtrip_preserves_tuples():
    plan = _plan({"q1": (1.0, 5.0), "q2": (1, 7)})
    snap = _serialize_plan(plan)
    assert snap["item_ranges"] == {"q1": [1.0, 5.0], "q2": [1, 7]}
    loaded = _deserialize_plan(json.loads(json.dumps(snap)))
    assert loaded.item_ranges == {"q1": (1.0, 5.0), "q2": (1.0, 7.0)}
    assert all(isinstance(v, tuple) for v in loaded.item_ranges.values())


def test_plan_without_item_ranges_stays_none():
    assert _deserialize_plan(_serialize_plan(_plan(None))).item_ranges is None
    legacy = _serialize_plan(_plan(None))
    legacy.pop("item_ranges")
    assert _deserialize_plan(legacy).item_ranges is None
