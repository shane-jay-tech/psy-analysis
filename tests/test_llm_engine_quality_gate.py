"""Gap2 接线验收：基础引擎 quality_gate（设计稿 questionnaire-gap2-wiring-design-20260905.md 第三节）。"""

import json

import pytest

from src.questionnaire import llm_engine

_CANNED = {
    "construct_name": "手机依赖",
    "dimensions": [{"name": "戒断反应", "desc": "无法使用手机时的不适", "item_count": 2}],
    "items": [
        {"text": "我能轻松使用手机完成日常工作", "reverse": False, "dimension": "戒断反应"},
        {"text": "没有手机时我会感到焦虑并且难以集中注意力", "reverse": False, "dimension": "戒断反应"},
    ],
    "instructions": "请根据实际情况作答",
}


@pytest.fixture()
def mock_llm(monkeypatch):
    monkeypatch.setattr(llm_engine, "_call_llm", lambda **kw: json.dumps(_CANNED, ensure_ascii=False))
    return _CANNED


def _design():
    return llm_engine.design_questionnaire_llm(
        research_question="手机依赖与日常功能",
        api_key="test-key",
        base_url="http://localhost",
        model="test-model",
    )


def test_quality_gate_runs_on_valid_items(mock_llm):
    d = _design()
    gate = d["quality_gate"]
    assert gate and not gate.get("skipped")
    assert gate["engine"] == "local_item_quality"
    assert isinstance(gate["score_avg"], (int, float)) and 0 <= gate["score_avg"] <= 10


def test_double_barreled_item_flagged(mock_llm):
    d = _design()
    gate = d["quality_gate"]
    assert gate["errors"] >= 1
    assert 2 in gate["items_flagged"]  # 第 2 条含「并且」双重装载
    assert any("双向陈述" in it.get("check", "") for it in gate["detail"][0]["issues"]) or gate["detail"]


def test_weak_reverse_item_flagged(monkeypatch):
    canned = dict(_CANNED)
    canned["items"] = [
        {"text": "我能轻松使用手机完成日常工作", "reverse": False, "dimension": "戒断反应"},
        {"text": "我从不觉得不使用手机会不便", "reverse": True, "dimension": "戒断反应"},
    ]
    monkeypatch.setattr(llm_engine, "_call_llm", lambda **kw: json.dumps(canned, ensure_ascii=False))
    d = _design()
    gate = d["quality_gate"]
    assert gate["warnings"] >= 1
    assert any(
        "否定" in iss.get("check", "") or "否定" in iss.get("msg", "")
        for it in gate["detail"]
        for iss in it.get("issues", [])
    )


def test_quality_check_exception_never_blocks(monkeypatch, mock_llm):
    def boom(*a, **kw):
        raise RuntimeError("质检故障")

    monkeypatch.setattr(llm_engine, "check_item_quality", boom)
    d = _design()
    assert d["quality_gate"] == {"skipped": True}
    assert len(d["items"]) == 2  # 主流程照常出卷


def test_items_not_mutated_by_gate(mock_llm):
    d = _design()
    assert [it["text"] for it in d["items"]] == [it["text"] for it in _CANNED["items"]]
    assert [it["reverse"] for it in d["items"]] == [it["reverse"] for it in _CANNED["items"]]
    assert all("quality_gate" not in it for it in d["items"])  # 旁路字段不落单题
