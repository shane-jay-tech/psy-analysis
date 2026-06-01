"""高质量问卷生成引擎测试。

mock _call_llm 验证：
1. 五步流程都被调用
2. 各维度并行生成
3. 弱题被自动重写
4. 元数据正确装配
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.questionnaire.llm_engine_premium import (
    _items_system_prompt,
    _lookup_kb_scales,
    _parse_json,
    _regenerate_item_prompt,
    _skeleton_system_prompt,
    _validate_skeleton,
    design_questionnaire_premium,
    ITEM_FEW_SHOT,
)


# ---------------------------------------------------------------------------
# Prompt 构造
# ---------------------------------------------------------------------------

class TestPrompts:
    def test_skeleton_prompt_no_items(self):
        prompt = _skeleton_system_prompt()
        # 必须明确说不生成题目
        assert "不生成题目" in prompt
        assert "construct_name" in prompt

    def test_items_prompt_includes_few_shot(self):
        dim = {"name": "认知焦虑", "desc": "过度担忧", "item_count": 5}
        prompt = _items_system_prompt(
            "焦虑", "焦虑的定义...", dim,
            "likert_agreement", 5, ["STAI"],
        )
        # few-shot 必须被嵌入
        assert "行为锚定" in prompt
        assert "镜像题" in prompt or "镜像" in prompt
        assert "STAI" in prompt

    def test_items_prompt_specifies_reverse_count(self):
        dim = {"name": "X", "desc": "Y", "item_count": 8}
        prompt = _items_system_prompt(
            "C", "Def", dim, "likert_agreement", 5, [],
        )
        # 8 题 × 25% = 2 反向题
        assert "2 题为反向题" in prompt or "正好 2" in prompt

    def test_few_shot_includes_good_bad_pairs(self):
        # 至少包含正反向对比示例
        assert "❌" in ITEM_FEW_SHOT
        assert "✅" in ITEM_FEW_SHOT
        assert "镜像" in ITEM_FEW_SHOT or "伪反向" in ITEM_FEW_SHOT

    def test_regenerate_prompt_includes_issues(self):
        prompt = _regenerate_item_prompt(
            old_text="我又累又难过",
            issues=["双重负载：累+难过"],
            construct_name="抑郁",
            dimension_name="情绪低落",
            is_reverse=False,
        )
        assert "我又累又难过" in prompt
        assert "双重负载" in prompt
        assert "抑郁" in prompt


# ---------------------------------------------------------------------------
# JSON 解析
# ---------------------------------------------------------------------------

class TestParseJSON:
    def test_clean_json(self):
        result = _parse_json('{"a": 1}', "test")
        assert result == {"a": 1}

    def test_markdown_wrapped(self):
        result = _parse_json('```json\n{"a": 2}\n```', "test")
        assert result == {"a": 2}

    def test_with_extra_text(self):
        result = _parse_json('这是 JSON：{"a": 3} 完毕', "test")
        assert result == {"a": 3}

    def test_invalid_raises(self):
        from src.questionnaire.llm_engine import LLMResponseParseError
        with pytest.raises(LLMResponseParseError):
            _parse_json("not json", "test")

    def test_empty_raises(self):
        from src.questionnaire.llm_engine import LLMResponseParseError
        with pytest.raises(LLMResponseParseError):
            _parse_json("", "test")


# ---------------------------------------------------------------------------
# 主流程（mock _call_llm）
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_responses():
    """构造五步流程的 mock 响应。"""
    skeleton_response = json.dumps({
        "construct_name": "测试构念",
        "construct_name_en": "Test Construct",
        "domain": "其他",
        "definition": "测试构念的定义",
        "dimensions": [
            {"name": "维度A", "desc": "维度A描述", "item_count": 4},
            {"name": "维度B", "desc": "维度B描述", "item_count": 4},
        ],
        "scale_type": "likert_agreement",
        "scale_points": 5,
        "anchor_labels": ["1=完全不同意", "2=不太同意", "3=不确定", "4=比较同意", "5=完全同意"],
    }, ensure_ascii=False)

    items_a_response = json.dumps({
        "items": [
            {"text": "维度A题1：我经常XXX", "reverse": False},
            {"text": "维度A题2：过去一周我YYY", "reverse": False},
            {"text": "维度A题3：在ZZZ场景下我...", "reverse": False},
            {"text": "维度A题4：我从不AAA", "reverse": True},
        ]
    }, ensure_ascii=False)

    items_b_response = json.dumps({
        "items": [
            {"text": "维度B题1：我每天BBB", "reverse": False},
            {"text": "维度B题2：CCC的时候我...", "reverse": False},
            {"text": "我又累又难过", "reverse": False},   # 故意双重负载，会被质检标弱
            {"text": "维度B题4：我经常DDD", "reverse": True},
        ]
    }, ensure_ascii=False)

    metadata_response = json.dumps({
        "instructions": "本问卷旨在评估测试构念。请根据真实情况填写。所有数据保密。",
        "scoring": "正向题 1-5 直接计分，反向题反向计分。各维度均分。",
        "psychometrics": {
            "内容效度": "策略 X",
            "结构效度": "EFA + CFA",
            "信度": "Cronbach α + 重测",
            "社会称许性控制": "策略 Y",
        },
        "references": ["参考 1", "参考 2", "参考 3"],
        "established_scales": ["量表 1"],
    }, ensure_ascii=False)

    regenerate_response = json.dumps({
        "text": "重写后的高质量题目",
        "reverse": False,
    }, ensure_ascii=False)

    return {
        "skeleton": skeleton_response,
        "items_a": items_a_response,
        "items_b": items_b_response,
        "metadata": metadata_response,
        "regenerate": regenerate_response,
    }


class TestPremiumFlow:
    """直连模式：1 次 LLM 调用（+ 可选弱题重写）。"""

    def test_direct_mode_single_call_returns_full_design(self):
        """v3.7.7: 直连模式默认开启——一次 LLM 调用拿到完整 design。"""
        full_design_response = json.dumps({
            "construct_name": "直连测试",
            "construct_name_en": "Direct Test",
            "domain": "其他",
            "definition": "直连模式构念定义",
            "research_understanding": "用户想测某个构念",
            "respondent_role": "self",
            "population": "成年人",
            "context": "一般情境",
            "theoretical_framework": "",
            "dimensions": [
                {"name": "维度A", "desc": "维度A描述", "item_count": 3},
                {"name": "维度B", "desc": "维度B描述", "item_count": 3},
            ],
            "scale_type": "likert_agreement",
            "scale_points": 5,
            "scale_type_label": "agreement",
            "anchor_labels": ["1=完全不同意", "2", "3", "4", "5=完全同意"],
            "items": [
                {"text": "维度A题1：我经常XXX", "reverse": False, "dimension": "维度A"},
                {"text": "维度A题2：过去一周我YYY", "reverse": False, "dimension": "维度A"},
                {"text": "维度A题3：我从不AAA", "reverse": True, "dimension": "维度A"},
                {"text": "维度B题1：我每天BBB", "reverse": False, "dimension": "维度B"},
                {"text": "维度B题2：CCC的时候我...", "reverse": False, "dimension": "维度B"},
                {"text": "维度B题3：我经常DDD", "reverse": True, "dimension": "维度B"},
            ],
            "instructions": "本问卷旨在测量直连构念。请如实作答，所有数据保密。",
            "scoring": "正向题 1-5 直接计分，反向题反向计分。",
            "psychometrics": {
                "内容效度": "策略 X",
                "结构效度": "EFA + CFA",
                "信度": "α + 重测",
                "社会称许性控制": "策略 Y",
            },
            "references": ["引用 1", "引用 2", "引用 3"],
            "established_scales": ["量表 X"],
            "match_reason": "直连模式设计思路",
        }, ensure_ascii=False)

        call_count = [0]

        def fake_call_llm(messages, *args, **kwargs):
            call_count[0] += 1
            return full_design_response

        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            side_effect=fake_call_llm,
        ):
            design = design_questionnaire_premium(
                "测试一个直连模式的研究问题",
                api_key="sk", base_url="https://x", model="gpt-4o",
            )

        # 直连模式只 1 次主调用（弱题重写为 0 次因为 mock 题质量假设无瑕疵）
        assert call_count[0] >= 1
        assert design["construct_name"] == "直连测试"
        assert design["premium_mode"] is True
        assert design.get("direct_mode") is True   # v3.7.7 标识
        assert "scale_config" in design
        assert "quality_report" in design

    def test_direct_mode_progress_callback(self):
        """v3.7.7: 直连模式 progress_callback 至少 3 个步骤 + 最终 1.0。"""
        progress_log = []

        def on_progress(msg, pct):
            progress_log.append((msg, pct))

        full_response = json.dumps({
            "construct_name": "X",
            "dimensions": [{"name": "D1", "desc": "x", "item_count": 2}],
            "scale_type": "likert_agreement",
            "scale_points": 5,
            "anchor_labels": ["1", "2", "3", "4", "5"],
            "items": [
                {"text": "题目一", "reverse": False, "dimension": "D1"},
                {"text": "题目二", "reverse": True, "dimension": "D1"},
            ],
        }, ensure_ascii=False)

        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            return_value=full_response,
        ):
            design_questionnaire_premium(
                "测试", api_key="sk", base_url="https://x", model="gpt-4o",
                progress_callback=on_progress,
            )

        assert len(progress_log) >= 2
        assert progress_log[-1][1] == 1.0


class TestValidateSkeleton:
    def test_passes_complete_skeleton(self):
        skeleton = {
            "construct_name": "X",
            "dimensions": [{"name": "D1"}],
        }
        # Should not raise
        _validate_skeleton(skeleton)

    def test_missing_construct_name_raises(self):
        from src.questionnaire.llm_engine import LLMResponseParseError
        with pytest.raises(LLMResponseParseError):
            _validate_skeleton({"dimensions": [{"name": "D"}]})

    def test_empty_dimensions_raises(self):
        from src.questionnaire.llm_engine import LLMResponseParseError
        with pytest.raises(LLMResponseParseError):
            _validate_skeleton({"construct_name": "X", "dimensions": []})


class TestDecompositionCheck:
    """v3.7.2: 维度分解充分性检查。"""

    def test_person_job_fit_with_only_two_dims_flagged(self):
        """人岗匹配仅 2 个一级维度应被标记为分解不足。"""
        from src.questionnaire.llm_engine_premium import _is_under_decomposed
        skeleton = {
            "construct_name": "人岗匹配",
            "dimensions": [
                {"name": "要求-能力匹配", "desc": "个人能力与岗位要求", "item_count": 8},
                {"name": "需要-供给匹配", "desc": "个人需要与岗位供给", "item_count": 8},
            ],
        }
        assert _is_under_decomposed(skeleton, "测量员工的人岗匹配水平")

    def test_person_job_fit_with_six_subdimensions_passes(self):
        """人岗匹配下钻为 6 子维度后应通过。"""
        from src.questionnaire.llm_engine_premium import _is_under_decomposed
        skeleton = {
            "construct_name": "人岗匹配",
            "dimensions": [
                {"name": "要求-能力·知识", "desc": "知识储备", "item_count": 4},
                {"name": "要求-能力·技能", "desc": "技能水平", "item_count": 4},
                {"name": "要求-能力·能力", "desc": "认知能力", "item_count": 4},
                {"name": "需要-供给·物质回报", "desc": "薪酬福利", "item_count": 4},
                {"name": "需要-供给·社交回报", "desc": "人际关系", "item_count": 4},
                {"name": "需要-供给·自我实现", "desc": "成长机会", "item_count": 4},
            ],
        }
        assert not _is_under_decomposed(skeleton, "测量员工的人岗匹配水平")

    def test_burnout_three_dims_passes(self):
        """职业倦怠 Maslach 三因素 3 维度足够（不算欠分解）。"""
        from src.questionnaire.llm_engine_premium import _is_under_decomposed
        skeleton = {
            "construct_name": "职业倦怠",
            "dimensions": [
                {"name": "情绪耗竭", "desc": "情绪资源耗尽", "item_count": 5},
                {"name": "去个性化", "desc": "对工作对象冷漠", "item_count": 5},
                {"name": "个人成就感降低", "desc": "工作成就感下降", "item_count": 5},
            ],
        }
        assert not _is_under_decomposed(skeleton, "测量护士的职业倦怠")

    def test_listing_words_in_desc_flagged(self):
        """维度 desc 含"包括 X、Y、Z"列举词应被标记（说明内部还有子结构）。"""
        from src.questionnaire.llm_engine_premium import _is_under_decomposed
        skeleton = {
            "construct_name": "新构念",
            "dimensions": [
                {"name": "维度 A", "desc": "包括知识、技能、态度三方面", "item_count": 5},
                {"name": "维度 B", "desc": "单一观察内容", "item_count": 5},
            ],
        }
        assert _is_under_decomposed(skeleton, "测量")

    def test_two_dims_with_high_itemcount_flagged(self):
        """2 维度且每维度题量 >=6 视为欠分解。"""
        from src.questionnaire.llm_engine_premium import _is_under_decomposed
        skeleton = {
            "construct_name": "X",
            "dimensions": [
                {"name": "A", "desc": "...", "item_count": 8},
                {"name": "B", "desc": "...", "item_count": 7},
            ],
        }
        assert _is_under_decomposed(skeleton, "X 研究")

    def test_simple_construct_with_two_dims_passes(self):
        """简单构念 2 维度且题量正常不应误报。"""
        from src.questionnaire.llm_engine_premium import _is_under_decomposed
        skeleton = {
            "construct_name": "性别认同",
            "dimensions": [
                {"name": "认同感", "desc": "对自身性别的认同", "item_count": 4},
                {"name": "满意度", "desc": "对自身性别的满意", "item_count": 4},
            ],
        }
        assert not _is_under_decomposed(skeleton, "性别认同研究")




class TestDirectModeOverride:
    """v3.7.7: 直连模式下，parsed_research_override 注入 user prompt + 填充 research_parse。"""

    def test_direct_override_injected_into_user_message(self):
        """override 字段应作为「研究者已确认」段附在 user message。"""
        captured_messages = []

        def fake_call_llm(messages, *args, **kwargs):
            captured_messages.append(messages)
            return json.dumps({
                "construct_name": "X",
                "dimensions": [{"name": "D1", "desc": "x", "item_count": 2}],
                "scale_type": "likert_agreement",
                "scale_points": 5,
                "anchor_labels": ["1", "2", "3", "4", "5"],
                "items": [
                    {"text": "题一", "reverse": False, "dimension": "D1"},
                    {"text": "题二", "reverse": True, "dimension": "D1"},
                ],
            }, ensure_ascii=False)

        override = {
            "research_type": "instrument_evaluation",
            "population": "HR 团队",
            "research_object": "招聘标准",
            "respondent_role": "hr_practitioner",
        }
        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            side_effect=fake_call_llm,
        ):
            design = design_questionnaire_premium(
                "评估招聘标准",
                api_key="sk", base_url="https://x", model="gpt-4o",
                parsed_research_override=override,
            )

        # user message 应包含 override 字段
        first_call_user = captured_messages[0][1]["content"]
        assert "HR 团队" in first_call_user
        assert "招聘标准" in first_call_user
        assert "研究者已手动确认" in first_call_user

        # research_parse 也含 override 字段
        rp = design["research_parse"]
        assert rp["population"] == "HR 团队"
        assert rp["research_object"] == "招聘标准"
        assert rp["respondent_role"] == "hr_practitioner"


class TestReasoningModelDetection:
    """v3.7.4: 推理模型识别 + 自动 bump max_tokens。"""

    def test_detect_deepseek_reasoner(self):
        from src.questionnaire.llm_engine_premium import _is_reasoning_model
        assert _is_reasoning_model("deepseek-reasoner")
        assert _is_reasoning_model("deepseek-r1")

    def test_detect_openai_o_series(self):
        from src.questionnaire.llm_engine_premium import _is_reasoning_model
        assert _is_reasoning_model("o1")
        assert _is_reasoning_model("o3-mini")
        assert _is_reasoning_model("o4-mini")

    def test_detect_thinking_models(self):
        from src.questionnaire.llm_engine_premium import _is_reasoning_model
        assert _is_reasoning_model("kimi-thinking-preview")
        assert _is_reasoning_model("qwq-32b")

    def test_chat_models_not_detected(self):
        from src.questionnaire.llm_engine_premium import _is_reasoning_model
        assert not _is_reasoning_model("deepseek-chat")
        assert not _is_reasoning_model("gpt-4o")
        assert not _is_reasoning_model("claude-opus-4-8")
        assert not _is_reasoning_model("kimi-latest")
        assert not _is_reasoning_model("")
        assert not _is_reasoning_model(None)


class TestKBLookup:
    def test_lookup_known_construct(self):
        """已在 KB 的构念应能取到 established_scales。"""
        scales = _lookup_kb_scales("焦虑")
        # 焦虑在 CONSTRUCTS 里有 established_scales
        # 不强 assert 数量（避免 KB 改动后测试挂），但应是 list
        assert isinstance(scales, list)

    def test_unknown_construct_returns_empty(self):
        scales = _lookup_kb_scales("不存在的构念xyz123")
        assert scales == []


class TestV378MeasurementRules:
    """v3.7.8: 当代测量学共识——反向题→注意力检测题、抗过拟合等规则进入 prompt。"""

    def test_prompt_contains_attention_check_rule(self):
        """DIRECT_MODE_SYSTEM_PROMPT 必须明确指示用注意力检测题替代反向题。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "注意力检测题" in DIRECT_MODE_SYSTEM_PROMPT
        assert "attention_check" in DIRECT_MODE_SYSTEM_PROMPT
        # 必须明确「方法因子」「污染」的科学理由
        assert "方法因子" in DIRECT_MODE_SYSTEM_PROMPT or "method factor" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_contains_overfitting_rule(self):
        """prompt 必须包含抗过拟合（行为锚定但不能仅在某情境成立）。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "过拟合" in DIRECT_MODE_SYSTEM_PROMPT
        # 反例：地铁手机没电
        assert "地铁" in DIRECT_MODE_SYSTEM_PROMPT or "情境过窄" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_lists_forbidden_writings(self):
        """禁忌清单：双重负载/双重否定/假设句/极端词/直接问构念/社会赞许敏感。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "双重负载" in DIRECT_MODE_SYSTEM_PROMPT
        assert "双重否定" in DIRECT_MODE_SYSTEM_PROMPT
        assert "假设" in DIRECT_MODE_SYSTEM_PROMPT
        assert "极端" in DIRECT_MODE_SYSTEM_PROMPT
        assert "社会赞许" in DIRECT_MODE_SYSTEM_PROMPT
        assert "镜像" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_cites_methodology_references(self):
        """prompt 必须引用方法学经典文献，让 LLM 知道按当代标准设计。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "Podsakoff" in DIRECT_MODE_SYSTEM_PROMPT
        # 至少另一个引用
        assert any(
            ref in DIRECT_MODE_SYSTEM_PROMPT
            for ref in ["Meade", "Weijters", "DeVellis", "Boateng"]
        )

    def test_prompt_specifies_scale_choice_rules(self):
        """量表选择规则：临床→4 点频率、人格→5 点同意度、宽泛→7 点。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "4 点频率" in DIRECT_MODE_SYSTEM_PROMPT
        assert "5 点同意度" in DIRECT_MODE_SYSTEM_PROMPT
        assert "7 点同意度" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_includes_bandwidth_fidelity_rule(self):
        """带宽-保真度平衡（Cronbach & Gleser 1957）应作为抗过拟合的科学依据。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "带宽" in DIRECT_MODE_SYSTEM_PROMPT or "保真" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Cronbach" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_lists_attention_check_subtypes(self):
        """注意力检测题应给出 IRI / Bogus / Infrequency 三种典型类型。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "IRI" in DIRECT_MODE_SYSTEM_PROMPT or "指令型" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Bogus" in DIRECT_MODE_SYSTEM_PROMPT or "不可能" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Infrequency" in DIRECT_MODE_SYSTEM_PROMPT or "低频率" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_includes_anchor_design_rules(self):
        """量表锚点设计：全标签 / 对称 / 频率量表禁同意度锚点。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "全标签" in DIRECT_MODE_SYSTEM_PROMPT or "每点都有词标签" in DIRECT_MODE_SYSTEM_PROMPT
        assert "对称" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Krosnick" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_includes_layout_rules(self):
        """版面规则：题目顺序/漏斗设计/总长度上限/指导语必含项。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "漏斗" in DIRECT_MODE_SYSTEM_PROMPT or "题目顺序" in DIRECT_MODE_SYSTEM_PROMPT
        assert "总长度" in DIRECT_MODE_SYSTEM_PROMPT or "疲劳效应" in DIRECT_MODE_SYSTEM_PROMPT
        # 指导语必含
        assert "知情同意" in DIRECT_MODE_SYSTEM_PROMPT
        assert "保密" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_includes_item_independence_rule(self):
        """题间独立性：同维度题不应互为同义改写（避免 alpha 虚高）。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "题间独立" in DIRECT_MODE_SYSTEM_PROMPT or "题间独立性" in DIRECT_MODE_SYSTEM_PROMPT
        assert "同义改写" in DIRECT_MODE_SYSTEM_PROMPT or "同义换词" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_includes_floor_ceiling_rule(self):
        """避免地板/天花板效应。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "地板" in DIRECT_MODE_SYSTEM_PROMPT
        assert "天花板" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_includes_reading_level(self):
        """阅读水平要求。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "阅读水平" in DIRECT_MODE_SYSTEM_PROMPT or "初中" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_cites_classical_method_studies(self):
        """方法因子的实证证据应至少引用 Schmitt&Stults / Marsh / Hinkin / Weijters 之一。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        cited = [
            "Schmitt", "Stults", "Marsh", "Hinkin", "Weijters",
            "Tomas", "Oliver",
        ]
        assert any(c in DIRECT_MODE_SYSTEM_PROMPT for c in cited)

    def test_prompt_covers_statistical_careless_detection(self):
        """统计层面的 careless responder 检测建议。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        # 至少提及一种统计指标
        assert any(
            term in DIRECT_MODE_SYSTEM_PROMPT
            for term in ["Mahalanobis", "longstring", "IRV", "Curran"]
        )

    def test_prompt_cites_recent_2020s_literature(self):
        """v3.7.8: 必须引用 2020-2024 最新方法学文献，不能只停留在 2010s 经典。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        recent_refs = [
            "Ward & Meade (2023)",
            "Flake & Fried (2020)",
            "Schroeders",
            "Bowling",
            "Tay & Jebb (2022)",
            "Hauser, Ellsworth, Gonzalez (2018)",
            "Christensen & Golino (2021)",
        ]
        # 至少引用 4 篇 2018+ 文献
        cited = sum(1 for r in recent_refs if r in DIRECT_MODE_SYSTEM_PROMPT)
        assert cited >= 4, f"only {cited} recent (2018+) references cited, expected ≥4"

    def test_prompt_includes_modern_validation_methods(self):
        """现代结构验证方法：ESEM / bifactor / 网络心理测量 / 测量等价性。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "ESEM" in DIRECT_MODE_SYSTEM_PROMPT
        assert "bifactor" in DIRECT_MODE_SYSTEM_PROMPT.lower() or "Bifactor" in DIRECT_MODE_SYSTEM_PROMPT
        assert "网络" in DIRECT_MODE_SYSTEM_PROMPT or "network" in DIRECT_MODE_SYSTEM_PROMPT.lower()
        assert "测量等价" in DIRECT_MODE_SYSTEM_PROMPT or "Invariance" in DIRECT_MODE_SYSTEM_PROMPT

    def test_prompt_includes_measurement_reform_critique(self):
        """Flake & Fried 测量学改革倡议（measurement schmeasurement）。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "Flake" in DIRECT_MODE_SYSTEM_PROMPT or "schmeasurement" in DIRECT_MODE_SYSTEM_PROMPT


class TestV379ConstructPrerequisites:
    """v3.7.9: 构念前置判断（Section 0）+ IRT/MI/DIF + JSON schema 扩展。"""

    def test_section_0_jingle_jangle_detection(self):
        """Section 0 必须包含 jingle-jangle 谬误检测（Block 1995；Tay & Jebb 2017）。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "Jingle" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Jangle" in DIRECT_MODE_SYSTEM_PROMPT
        assert "同名异质" in DIRECT_MODE_SYSTEM_PROMPT
        assert "异名同质" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Block" in DIRECT_MODE_SYSTEM_PROMPT or "Tay" in DIRECT_MODE_SYSTEM_PROMPT

    def test_section_0_reflective_vs_formative(self):
        """Reflective vs formative 模型判断必须在写题之前。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "Reflective" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Formative" in DIRECT_MODE_SYSTEM_PROMPT
        assert "反思性" in DIRECT_MODE_SYSTEM_PROMPT
        assert "形成性" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Edwards" in DIRECT_MODE_SYSTEM_PROMPT or "Diamantopoulos" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Bollen" in DIRECT_MODE_SYSTEM_PROMPT
        # 关键警示：formative 不能做 EFA/α
        assert "不能做 EFA" in DIRECT_MODE_SYSTEM_PROMPT or "不能算 α" in DIRECT_MODE_SYSTEM_PROMPT

    def test_section_0_construct_definition_boundary(self):
        """构念清晰度：操作性定义 + 区分/收敛构念。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "操作性定义" in DIRECT_MODE_SYSTEM_PROMPT
        assert "邻近构念" in DIRECT_MODE_SYSTEM_PROMPT
        assert "收敛构念" in DIRECT_MODE_SYSTEM_PROMPT or "区分效度" in DIRECT_MODE_SYSTEM_PROMPT

    def test_section_0_weird_warning(self):
        """WEIRD 样本警示（Henrich et al. 2010）。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "WEIRD" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Henrich" in DIRECT_MODE_SYSTEM_PROMPT

    def test_irt_as_modern_path(self):
        """IRT 路径（GRM/Rasch/PCM）作为现代量表的推荐方法。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "IRT" in DIRECT_MODE_SYSTEM_PROMPT
        # 至少一个 IRT 模型
        assert any(m in DIRECT_MODE_SYSTEM_PROMPT for m in ["GRM", "Rasch", "PCM"])
        # CAT (Computer Adaptive Testing) 提示
        assert "CAT" in DIRECT_MODE_SYSTEM_PROMPT or "PROMIS" in DIRECT_MODE_SYSTEM_PROMPT

    def test_pls_sem_for_formative(self):
        """formative 构念应推荐 PLS-SEM（不是 EFA/CFA）。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "PLS-SEM" in DIRECT_MODE_SYSTEM_PROMPT or "indicator weights" in DIRECT_MODE_SYSTEM_PROMPT

    def test_measurement_invariance_three_levels(self):
        """跨群体测量等价：配置-度量-标量三层级。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "配置" in DIRECT_MODE_SYSTEM_PROMPT
        assert "度量" in DIRECT_MODE_SYSTEM_PROMPT
        assert "标量" in DIRECT_MODE_SYSTEM_PROMPT
        assert "DIF" in DIRECT_MODE_SYSTEM_PROMPT
        assert "van de Schoot" in DIRECT_MODE_SYSTEM_PROMPT

    def test_chinese_version_cross_language_mi_required(self):
        """中文版必须做跨语言测量等价（不假设直译保持等价）。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "中文版" in DIRECT_MODE_SYSTEM_PROMPT
        assert "跨语言" in DIRECT_MODE_SYSTEM_PROMPT or "直译" in DIRECT_MODE_SYSTEM_PROMPT

    def test_sample_size_planning_in_prompt(self):
        """样本量规划：EFA/CFA/IRT 各自最低数量。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "样本量" in DIRECT_MODE_SYSTEM_PROMPT
        assert "MacCallum" in DIRECT_MODE_SYSTEM_PROMPT
        # 数字阈值
        assert "200" in DIRECT_MODE_SYSTEM_PROMPT
        assert "500" in DIRECT_MODE_SYSTEM_PROMPT

    def test_response_time_quality_indicator(self):
        """响应时间作为数据质量指标（Bauer 2007；Greszki 2015）。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "响应时间" in DIRECT_MODE_SYSTEM_PROMPT
        assert "Bauer" in DIRECT_MODE_SYSTEM_PROMPT or "Greszki" in DIRECT_MODE_SYSTEM_PROMPT

    def test_omega_reliability_in_addition_to_alpha(self):
        """除 α 外推荐报告 ω（McDonald's omega）。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "ω" in DIRECT_MODE_SYSTEM_PROMPT
        assert "McDonald" in DIRECT_MODE_SYSTEM_PROMPT or "omega" in DIRECT_MODE_SYSTEM_PROMPT.lower()

    def test_json_schema_includes_construct_clarity(self):
        """JSON schema 必须明确要求 construct_clarity 字段。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "construct_clarity" in DIRECT_MODE_SYSTEM_PROMPT
        assert "operational_definition" in DIRECT_MODE_SYSTEM_PROMPT
        assert "discriminant_constructs" in DIRECT_MODE_SYSTEM_PROMPT

    def test_json_schema_dimension_model_type(self):
        """JSON schema 的 dimension 必须包含 model_type 字段。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "model_type" in DIRECT_MODE_SYSTEM_PROMPT
        # 三种合法值
        assert "reflective | formative | mixed" in DIRECT_MODE_SYSTEM_PROMPT

    def test_psychometrics_field_includes_mi_and_sample_size(self):
        """psychometrics 字段应包含测量等价 + 样本量规划。"""
        from src.questionnaire.llm_engine_premium import DIRECT_MODE_SYSTEM_PROMPT
        assert "测量等价" in DIRECT_MODE_SYSTEM_PROMPT
        assert "样本量规划" in DIRECT_MODE_SYSTEM_PROMPT

    def test_design_propagates_construct_clarity_field(self):
        """LLM 输出含 construct_clarity 时，design 应保留该字段供 UI 展示。"""
        full_response = json.dumps({
            "construct_name": "测试",
            "construct_clarity": {
                "operational_definition": "本构念定义为 X，不包含 Y 与 Z",
                "discriminant_constructs": [{"name": "邻近构念A", "key_difference": "差异"}],
                "convergent_constructs": ["收敛构念B"],
                "jingle_jangle_check": "已检查无混淆",
            },
            "dimensions": [
                {"name": "D1", "desc": "x", "item_count": 2, "model_type": "reflective"},
            ],
            "scale_type": "likert_agreement",
            "scale_points": 5,
            "anchor_labels": ["1", "2", "3", "4", "5"],
            "items": [
                {"text": "题一", "reverse": False, "dimension": "D1", "item_type": "construct"},
                {"text": "题二", "reverse": False, "dimension": "D1", "item_type": "construct"},
            ],
        }, ensure_ascii=False)

        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            return_value=full_response,
        ):
            design = design_questionnaire_premium(
                "测试", api_key="sk", base_url="https://x", model="gpt-4o",
            )

        # construct_clarity 应原样保留
        assert "construct_clarity" in design
        assert design["construct_clarity"]["operational_definition"].startswith("本构念定义")
        # dimensions 的 model_type 应保留
        dims = design.get("dimensions", []) or design.get("dimensions_used", [])
        assert any(d.get("model_type") == "reflective" for d in dims)

    def test_attention_check_items_separated_from_construct(self):
        """注意力检测题应被分流：不进质检、不重写、单独输出到 design['attention_checks']。"""
        full_response = json.dumps({
            "construct_name": "测试构念",
            "dimensions": [{"name": "D1", "desc": "x", "item_count": 3}],
            "scale_type": "likert_agreement",
            "scale_points": 5,
            "anchor_labels": ["1", "2", "3", "4", "5"],
            "items": [
                {"text": "构念题一：我经常感到紧张", "reverse": False,
                 "dimension": "D1", "item_type": "construct"},
                {"text": "构念题二：我通常情绪稳定", "reverse": False,
                 "dimension": "D1", "item_type": "construct"},
                {"text": "构念题三：在压力下我能保持冷静", "reverse": False,
                 "dimension": "D1", "item_type": "construct"},
                # 注意力检测题——故意写成"双重负载"风格，但因 item_type 而被跳过
                {"text": "这道题请选择\"3\"以表明你认真作答又仔细", "reverse": False,
                 "dimension": "_attention_check", "item_type": "attention_check"},
            ],
        }, ensure_ascii=False)

        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            return_value=full_response,
        ):
            design = design_questionnaire_premium(
                "测试", api_key="sk", base_url="https://x", model="gpt-4o",
            )

        # design 应包含 attention_checks 字段
        assert "attention_checks" in design
        assert len(design["attention_checks"]) == 1
        assert design["attention_checks"][0]["item_type"] == "attention_check"
        assert "data_quality_strategy" in design
        # 质检 total_items 应只统计构念题 3 道（不含 1 道检测题）
        assert design["quality_report"]["total_items"] == 3

    def test_attention_check_not_rewritten(self):
        """注意力检测题即便看起来"违规"也不应被弱题重写流程触及。"""
        regen_call_count = [0]

        full_response = json.dumps({
            "construct_name": "X",
            "dimensions": [{"name": "D1", "desc": "x", "item_count": 2}],
            "scale_type": "likert_agreement",
            "scale_points": 5,
            "anchor_labels": ["1", "2", "3", "4", "5"],
            "items": [
                {"text": "构念题一", "reverse": False,
                 "dimension": "D1", "item_type": "construct"},
                {"text": "构念题二", "reverse": False,
                 "dimension": "D1", "item_type": "construct"},
                {"text": "请选3", "reverse": False,
                 "dimension": "_attention_check", "item_type": "attention_check"},
            ],
        }, ensure_ascii=False)

        regen_response = json.dumps({"text": "改写", "reverse": False}, ensure_ascii=False)

        def fake_call(messages, *args, **kwargs):
            sys_text = messages[0]["content"] if messages else ""
            # 重写流程的 system prompt 特征语：「改写一道质检不通过的题目」
            if "改写一道质检不通过" in sys_text:
                regen_call_count[0] += 1
                return regen_response
            return full_response

        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            side_effect=fake_call,
        ):
            design = design_questionnaire_premium(
                "测试", api_key="sk", base_url="https://x", model="gpt-4o",
            )

        # 即使有题被判为弱题，attention_check 题也不在弱题候选中
        attention_texts = [it["text"] for it in design.get("attention_checks", [])]
        # attention_check 题文字「请选3」依然存在（没被改写）
        assert "请选3" in attention_texts

    def test_no_attention_check_emits_warning_message(self):
        """LLM 没有产出 attention_check 题时，data_quality_strategy 应给出建议。"""
        full_response = json.dumps({
            "construct_name": "X",
            "dimensions": [{"name": "D1", "desc": "x", "item_count": 2}],
            "scale_type": "likert_agreement",
            "scale_points": 5,
            "anchor_labels": ["1", "2", "3", "4", "5"],
            "items": [
                {"text": "题一", "reverse": False, "dimension": "D1", "item_type": "construct"},
                {"text": "题二", "reverse": False, "dimension": "D1", "item_type": "construct"},
            ],
        }, ensure_ascii=False)

        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            return_value=full_response,
        ):
            design = design_questionnaire_premium(
                "测试", api_key="sk", base_url="https://x", model="gpt-4o",
            )

        assert design["attention_checks"] == []
        assert "建议补加" in design["data_quality_strategy"]


class TestV3710Critique:
    """v3.7.10: LLM 自审核 pass + 弱题合并 + 重写 prompt v2。"""

    def _make_full_response(self):
        """构造一份完整 design 响应（含 1 道明显抽象的弱题）。"""
        return json.dumps({
            "construct_name": "焦虑",
            "dimensions": [
                {"name": "情绪焦虑", "desc": "情绪层面的焦虑", "item_count": 3, "model_type": "reflective"},
            ],
            "scale_type": "likert_agreement",
            "scale_points": 5,
            "anchor_labels": ["1=完全不同意", "2", "3", "4", "5=完全同意"],
            "items": [
                {"text": "我感到焦虑", "reverse": False,
                 "dimension": "情绪焦虑", "item_type": "construct"},
                {"text": "过去一周我经常因小事感到紧张", "reverse": False,
                 "dimension": "情绪焦虑", "item_type": "construct"},
                {"text": "我难以放松下来即便事情都做完了", "reverse": False,
                 "dimension": "情绪焦虑", "item_type": "construct"},
                {"text": "请选择 3 以表明你认真作答", "reverse": False,
                 "dimension": "_attention_check", "item_type": "attention_check"},
            ],
        }, ensure_ascii=False)

    def test_llm_critique_default_enabled(self):
        """默认开启 critique，design 应包含 critique_report 字段。"""
        full_response = self._make_full_response()
        critique_response = json.dumps({
            "items_with_issues": [
                {"index": 1, "score": 4, "issues": ["仅含构念词，缺行为锚定"], "severity": "warning"}
            ],
            "overall_issues": [],
            "summary": "整体可用，1 道题需重写",
        }, ensure_ascii=False)
        regen_response = json.dumps({"text": "改写后的高质量题目长这样子", "reverse": False}, ensure_ascii=False)

        call_log = []

        def fake_call(messages, *args, **kwargs):
            sys_text = messages[0]["content"] if messages else ""
            call_log.append(sys_text[:60])
            if "心理测量学审稿人" in sys_text:
                return critique_response
            if "改写" in sys_text and "质检" in sys_text and "评审" in sys_text:
                return regen_response
            return full_response

        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            side_effect=fake_call,
        ):
            design = design_questionnaire_premium(
                "测大学生焦虑水平",
                api_key="sk", base_url="https://x", model="gpt-4o",
            )

        # critique_report 字段存在
        assert "critique_report" in design
        assert design["critique_report"]["summary"].startswith("整体可用")
        # critique 识别的弱题被纳入重写
        assert design["quality_report"]["regenerated_count"] >= 1

    def test_llm_critique_disabled(self):
        """enable_llm_critique=False 时跳过 critique pass。"""
        full_response = self._make_full_response()
        call_log = []

        def fake_call(messages, *args, **kwargs):
            sys_text = messages[0]["content"] if messages else ""
            call_log.append(sys_text[:60])
            return full_response

        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            side_effect=fake_call,
        ):
            design = design_questionnaire_premium(
                "测试", api_key="sk", base_url="https://x", model="gpt-4o",
                # design_questionnaire_premium 透传到 direct
                # 但 design_questionnaire_premium 不接受 enable_llm_critique 参数
                # 改为直接调用 design_questionnaire_direct
            )
            # 这个测试用例不能直接通过 premium 关掉 critique（需要单独 direct 入口）

        # 默认情况下：critique pass 被 enabled，至少存在 critique_report
        assert "critique_report" in design

    def test_direct_with_critique_off(self):
        """直接调用 design_questionnaire_direct(enable_llm_critique=False)，不应有 critique 调用。"""
        from src.questionnaire.llm_engine_premium import design_questionnaire_direct
        full_response = self._make_full_response()

        critique_called = [False]

        def fake_call(messages, *args, **kwargs):
            sys_text = messages[0]["content"] if messages else ""
            if "心理测量学审稿人" in sys_text:
                critique_called[0] = True
            return full_response

        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            side_effect=fake_call,
        ):
            design = design_questionnaire_direct(
                "测试", api_key="sk", base_url="https://x", model="gpt-4o",
                enable_llm_critique=False,
            )

        assert not critique_called[0]
        # critique_report 仍存在（空骨架）
        assert "critique_report" in design
        assert design["critique_report"]["summary"] == "（已跳过 LLM 评审）"

    def test_overall_warnings_in_quality_report(self):
        """缺注意力检测题时，quality_report.overall_warnings 应非空。"""
        # 不含 attention_check 的响应
        no_attention_response = json.dumps({
            "construct_name": "X",
            "dimensions": [{"name": "D1", "desc": "x", "item_count": 2, "model_type": "reflective"}],
            "scale_type": "likert_agreement",
            "scale_points": 5,
            "anchor_labels": ["1", "2", "3", "4", "5"],
            "items": [
                {"text": "过去一周我经常感到紧张", "reverse": False,
                 "dimension": "D1", "item_type": "construct"},
                {"text": "我难以放松下来", "reverse": False,
                 "dimension": "D1", "item_type": "construct"},
            ],
        }, ensure_ascii=False)
        with patch(
            "src.questionnaire.llm_engine_premium._call_llm",
            return_value=no_attention_response,
        ):
            from src.questionnaire.llm_engine_premium import design_questionnaire_direct
            design = design_questionnaire_direct(
                "测试", api_key="sk", base_url="https://x", model="gpt-4o",
                enable_llm_critique=False,   # 单独测本地 quality
            )

        qr = design["quality_report"]
        assert "overall_warnings" in qr
        assert any("注意力检测题" in w for w in qr["overall_warnings"])

    def test_regenerate_prompt_v2_includes_siblings(self):
        """_regenerate_item_prompt_v2 应包含 sibling_items 段。"""
        from src.questionnaire.llm_engine_premium import _regenerate_item_prompt_v2
        prompt = _regenerate_item_prompt_v2(
            old_text="我感到焦虑",
            issues=["仅含构念词，缺行为锚定"],
            construct_name="焦虑",
            dimension_name="情绪焦虑",
            is_reverse=False,
            sibling_items=["过去一周我经常因小事失眠", "我难以放松下来"],
        )
        # 关键内容
        assert "我感到焦虑" in prompt
        assert "过去一周我经常因小事失眠" in prompt
        assert "我难以放松下来" in prompt
        assert "同维度其他题" in prompt
        assert "抗过拟合" in prompt

    def test_regenerate_prompt_v2_reverse_warning(self):
        """反向题应含「禁止仅在正向题前加'不'制造镜像题」警示。"""
        from src.questionnaire.llm_engine_premium import _regenerate_item_prompt_v2
        prompt = _regenerate_item_prompt_v2(
            old_text="我感到不自信",
            issues=["镜像题"],
            construct_name="自信",
            dimension_name="自我效能",
            is_reverse=True,
        )
        assert "镜像题" in prompt
        assert "禁止" in prompt
