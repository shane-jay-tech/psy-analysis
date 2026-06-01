"""Quick functional test of LLM integration — does not call any API."""
import sys
sys.path.insert(0, ".")

from config.llm_providers import LLM_PROVIDERS
from src.questionnaire.llm_engine import _build_system_prompt, _build_user_prompt, _parse_and_validate
from src.questionnaire.construct_kb import CONSTRUCTS

# Test 1: System prompt
prompt = _build_system_prompt()
assert len(prompt) > 3000, f"Prompt too short: {len(prompt)} chars"
print(f"System prompt: {len(prompt)} chars")
for cname in CONSTRUCTS:
    assert cname in prompt, f"Missing construct: {cname}"
print(f"All {len(CONSTRUCTS)} constructs in system prompt: OK")

# Test 2: User prompt
user_prompt = _build_user_prompt("测试问题")
assert "测试问题" in user_prompt
print("User prompt: OK")

# Test 3: JSON parsing
valid_json = """{
  "construct_name": "手机依赖",
  "dimensions": [{"name": "戒断反应", "desc": "无法使用手机时的不适", "item_count": 5}],
  "items": [
    {"text": "没有手机时我会感到焦虑", "reverse": false, "dimension": "戒断反应"},
    {"text": "我能轻松放下手机", "reverse": true, "dimension": "戒断反应"}
  ],
  "instructions": "测试指导语"
}"""
result = _parse_and_validate(valid_json, "测试研究问题")
assert result["construct_name"] == "手机依赖"
assert len(result["items"]) == 2
assert result["items"][1]["reverse"] == True
print(f"JSON parse: OK ({len(result['items'])} items)")

# Test 4: JSON with markdown fences
fenced_json = "```json\n" + valid_json + "\n```"
result2 = _parse_and_validate(fenced_json, "测试")
assert result2["construct_name"] == "手机依赖"
print("Markdown fence stripping: OK")

# Test 5: Missing optional keys
minimal_json = '{"construct_name": "测试", "dimensions": [{"name": "D1", "desc": "desc"}], "items": [{"text": "Q1"}], "instructions": "test"}'
result3 = _parse_and_validate(minimal_json, "test")
assert result3["domain"] == "其他"
assert result3["scale_points"] == 5
print("Default value filling: OK")

# Test 6: Malformed JSON raises error
from src.questionnaire.llm_engine import LLMResponseParseError
try:
    _parse_and_validate("not json at all", "test")
    assert False, "Should have raised"
except LLMResponseParseError:
    print("Malformed JSON rejection: OK")

# Test 7: JSON without items raises error
try:
    _parse_and_validate('{"construct_name": "X", "dimensions": [], "instructions": "x"}', "test")
    assert False, "Should have raised"
except LLMResponseParseError:
    print("Empty dimensions rejection: OK")

# Test 8: Keyword engine still works
from src.questionnaire.design_engine import design_questionnaire
design = design_questionnaire("调查大学生的社交焦虑水平")
assert design["llm_used"] == False
assert design["construct_name"] in CONSTRUCTS
print(f"Keyword engine fallback: OK (matched: {design['construct_name']})")

# Test 9: Keyword engine with llm_config=None
design2 = design_questionnaire("测量员工的工作满意度", llm_config=None)
assert design2["llm_used"] == False
print(f"Explicit None config: OK (matched: {design2['construct_name']})")

# Test 10: Provider presets
assert "deepseek" in LLM_PROVIDERS
assert LLM_PROVIDERS["deepseek"]["base_url"] == "https://api.deepseek.com"
assert LLM_PROVIDERS["zhipu"]["default_model"] == "glm-4-plus"   # v3.7 升级
assert LLM_PROVIDERS["ollama"]["base_url"] == "http://localhost:11434/v1"
print(f"Provider presets: OK ({len(LLM_PROVIDERS)} providers)")

# Test 11: Report generator handles LLM fields
from src.questionnaire.report_generator import generate_design_report
llm_design = {
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
report = generate_design_report(llm_design)
assert "手机依赖是一种" in report
assert "Smith, J. (2023)" in report
print("Report generator with LLM fields: OK")

print("\n=== All 11 tests passed ===")
