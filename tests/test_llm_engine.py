"""Quick functional test of LLM integration — does not call any API.

s930-14 函数化改造（s927-42 遗留）：原脚本形态在 collect 期以 import 副作用执行断言
（收集 0 例、单跑 rc=5、无用例名无 FAIL 行，可归因性差）。本版把 11 段断言逐条迁入
具名测试函数，**断言表达式逐字保留**（不改 >=/== 等判据）。旧→新映射见各函数 docstring
的「原 Test N」标记。
"""
import sys

import pytest

sys.path.insert(0, ".")

from config.llm_providers import LLM_PROVIDERS
from src.questionnaire.construct_kb import CONSTRUCTS
from src.questionnaire.llm_engine import (
    LLMResponseParseError,
    _build_system_prompt,
    _build_user_prompt,
    _parse_and_validate,
)

VALID_JSON = '''{
  "construct_name": "手机依赖",
  "dimensions": [{"name": "戒断反应", "desc": "无法使用手机时的不适", "item_count": 5}],
  "items": [
    {"text": "没有手机时我会感到焦虑", "reverse": false, "dimension": "戒断反应"},
    {"text": "我能轻松放下手机", "reverse": true, "dimension": "戒断反应"}
  ],
  "instructions": "测试指导语"
}'''


def test_1_system_prompt_covers_all_constructs():
    """原 Test 1：系统 prompt 长度＋构念全名覆盖。"""
    prompt = _build_system_prompt()
    assert len(prompt) > 3000, f"Prompt too short: {len(prompt)} chars"
    for cname in CONSTRUCTS:
        assert cname in prompt, f"Missing construct: {cname}"


def test_1b_construct_sections_bidirectional_conservation():
    """原 Test 1b：构念条目的**枚数＋集合双向守恒**（s924-03 双向看守）。

    N = 51 现取于 2026-09-24（HEAD `86fcf2f`，`src/questionnaire/construct_kb.py`
    字节 sha8 `3c660295`），与 `tests/test_construct_kb_census.py:15` 的 TOTAL、
    `tests/test_construct_kb_extended_placeholder.py:42` 的 CENSUS_TOTAL 三处同值
    ⇒ 增减构念时这三处连同本行注记要一起同步。
    为什么上面那个 in 循环不够：实测 CONSTRUCTS 里有 3 对名字互为子串（"焦虑" 是
    "社交焦虑" 的一部分），漏渲染一整节也可能照样绿。这里改按 prompt 的构念小节
    标题做守恒——生产码唯一产点是 `src/questionnaire/llm_engine.py:141` 的
    `### {cname} ({name_en})`（实测全文只有它产 `### `，其余分节都是 `## `）
    ⇒ 少一节、多一节、名字串位三种破法都当场红。
    """
    prompt = _build_system_prompt()
    construct_sections = [ln[4:].split(" (")[0] for ln in prompt.splitlines() if ln.startswith("### ")]
    assert len(construct_sections) == len(CONSTRUCTS), (
        f"prompt 里的构念小节 {len(construct_sections)} 枚 ≠ CONSTRUCTS {len(CONSTRUCTS)} 条"
    )
    assert set(construct_sections) == set(CONSTRUCTS), (
        f"prompt 漏渲染 {sorted(set(CONSTRUCTS) - set(construct_sections))}；"
        f"多渲染 {sorted(set(construct_sections) - set(CONSTRUCTS))}"
    )


def test_2_user_prompt_contains_question():
    """原 Test 2：User prompt。"""
    user_prompt = _build_user_prompt("测试问题")
    assert "测试问题" in user_prompt


def test_3_parse_valid_json():
    """原 Test 3：JSON parsing。"""
    result = _parse_and_validate(VALID_JSON, "测试研究问题")
    assert result["construct_name"] == "手机依赖"
    assert len(result["items"]) == 2
    assert result["items"][1]["reverse"] == True


def test_4_markdown_fence_stripping():
    """原 Test 4：JSON with markdown fences。"""
    fenced_json = "```json" + chr(10) + VALID_JSON + chr(10) + "```"
    result2 = _parse_and_validate(fenced_json, "测试")
    assert result2["construct_name"] == "手机依赖"


def test_5_missing_optional_keys_defaults():
    """原 Test 5：Missing optional keys。"""
    minimal_json = '''{"construct_name": "测试", "dimensions": [{"name": "D1", "desc": "desc"}], "items": [{"text": "Q1"}], "instructions": "test"}'''
    result3 = _parse_and_validate(minimal_json, "test")
    assert result3["domain"] == "其他"
    assert result3["scale_points"] == 5


def test_6_malformed_json_raises():
    """原 Test 6：Malformed JSON raises error。"""
    with pytest.raises(LLMResponseParseError):
        _parse_and_validate("not json at all", "test")


def test_7_empty_dimensions_raises():
    """原 Test 7：JSON without items raises error。"""
    with pytest.raises(LLMResponseParseError):
        _parse_and_validate('{"construct_name": "X", "dimensions": [], "instructions": "x"}', "test")


def test_8_keyword_engine_fallback():
    """原 Test 8：Keyword engine still works。"""
    from src.questionnaire.design_engine import design_questionnaire

    design = design_questionnaire("调查大学生的社交焦虑水平")
    assert design["llm_used"] == False
    assert design["construct_name"] in CONSTRUCTS


def test_9_explicit_none_config():
    """原 Test 9：Keyword engine with llm_config=None。"""
    from src.questionnaire.design_engine import design_questionnaire

    design2 = design_questionnaire("测量员工的工作满意度", llm_config=None)
    assert design2["llm_used"] == False


def test_10_provider_presets():
    """原 Test 10：Provider presets。"""
    assert "deepseek" in LLM_PROVIDERS
    assert LLM_PROVIDERS["deepseek"]["base_url"] == "https://api.deepseek.com"
    assert LLM_PROVIDERS["zhipu"]["default_model"] == "glm-4-plus"   # v3.7 升级
    assert LLM_PROVIDERS["ollama"]["base_url"] == "http://localhost:11434/v1"


LLM_DESIGN = {
    "research_question": "测试",
    "matched_construct": None,
    "construct_name": "手机依赖",
    "is_exact_match": False,
    "match_reason": "LLM生成",
    "dimensions_used": [{"name": "戒断反应", "desc": "无法使用手机时的不适", "item_count": 5}],
    "template_used": {"name": "Likert同意度量表"},
    "scale_config": {
        "points": 5, "scale_type": "agreement",
        "anchors": ["1=完全不同意", "5=完全同意"],
        "n_items": 5, "n_dimensions": 1, "n_reverse": 1, "reverse_ratio": "20%",
    },
    "items": [
        {"index": 1, "text": "测试题目", "reverse": False, "dimension": "戒断反应"},
    ],
    "instructions": "请作答",
    "scoring": "5点计分",
    "psychometrics": {"信度": "测试"},
    "llm_definition": "手机依赖是一种...",
    "llm_references": ["Smith, J. (2023). Test reference."],
    "llm_established_scales": ["手机依赖量表 (MDS, 2020)"],
    "llm_used": True,
    "llm_generated": True,
}


def test_11_report_generator_handles_llm_fields():
    """原 Test 11：Report generator handles LLM fields。"""
    from src.questionnaire.report_generator import generate_design_report

    report = generate_design_report(LLM_DESIGN)
    assert "手机依赖是一种" in report
    assert "Smith, J. (2023)" in report
