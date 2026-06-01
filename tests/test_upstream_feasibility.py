"""可研究性检查测试（v3.3: 可证伪 + 可测量 + 可操作 + 有意义反思）。"""

from unittest.mock import MagicMock

from src.upstream.feasibility_check import (
    HIGH_BARRIER_KEYWORDS,
    check_falsifiability,
    check_measurability,
    check_operability,
    suggest_significance_reflection,
)


class TestFalsifiability:
    def test_empty_answer_warns(self):
        r = check_falsifiability("")
        assert r["answered"] is False
        assert "未填写" in r["warning"]

    def test_negation_passes(self):
        r = check_falsifiability("如果假设错了，相反方向也可能出现")
        assert r["answered"] is True
        assert r["has_negation"] is True
        assert r["warning"] == ""

    def test_no_negation_warns(self):
        r = check_falsifiability("我觉得我的研究很有意义")
        assert r["answered"] is True
        assert r["has_negation"] is False
        assert "否定" in r["warning"] or "错" in r["warning"]


class TestMeasurability:
    def test_no_vars_warns(self):
        r = check_measurability({})
        assert r["all_measurable"] is False
        assert "未识别到候选变量" in r.get("warning", "")

    def test_anxiety_var_matches_real_construct(self):
        """焦虑应该匹配到 construct_kb 中的构念并有量表。"""
        r = check_measurability({
            "dependent_vars": ["焦虑"],
            "independent_vars": ["压力"],
        })
        # 至少焦虑应被识别
        anx_result = next((x for x in r["results"] if x["variable"] == "焦虑"), None)
        assert anx_result is not None
        assert anx_result["matched_construct"] is not None
        # 焦虑构念应有 established_scales（STAI 等）
        assert len(anx_result["scales"]) > 0

    def test_unknown_var_warns(self):
        r = check_measurability({"dependent_vars": ["量子情感波动指数_完全不存在"]})
        result = r["results"][0]
        assert result["matched_construct"] is None
        assert "未匹配" in result["warning"]


# ---------------------------------------------------------------------------
# v3.3: 可操作检查
# ---------------------------------------------------------------------------

class TestOperability:
    def test_normal_research_is_feasible(self):
        """正常本科研究应通过可操作检查。"""
        r = check_operability(
            "在大学生中，社交焦虑与孤独感是否相关？",
            {"dependent_vars": ["社交焦虑"], "independent_vars": ["孤独感"]},
        )
        assert r.is_feasible is True
        assert r.concerns == []

    def test_fmri_keyword_triggers_warning(self):
        """fMRI 应触发神经成像警告。"""
        r = check_operability(
            "用 fMRI 研究焦虑的脑机制",
            {"dependent_vars": ["焦虑"]},
        )
        assert r.is_feasible is False
        assert any(c["category"] == "neuroimaging" for c in r.concerns)
        # 应有替代方案
        assert any("PsychoPy" in s or "行为" in s for s in r.suggestions)

    def test_longitudinal_triggers_warning(self):
        """纵向追踪 1 年应触发时间成本警告。"""
        r = check_operability(
            "纵向追踪 1 年研究学业拖延的发展轨迹",
            None,
        )
        assert r.is_feasible is False
        assert any(c["category"] == "longitudinal" for c in r.concerns)

    def test_clinical_population_triggers_warning(self):
        """抑郁症患者应触发临床伦理警告。"""
        r = check_operability(
            "招募抑郁症患者研究治疗效果",
            {"independent_vars": ["治疗类型"]},
        )
        assert r.is_feasible is False
        assert any(c["category"] == "clinical_population" for c in r.concerns)
        assert any("自报量表" in s or "普通学生" in s for s in r.suggestions)

    def test_minors_triggers_warning(self):
        """学龄前儿童应触发未成年人伦理警告。"""
        r = check_operability(
            "研究学龄前儿童的注意力发展",
            None,
        )
        assert r.is_feasible is False
        assert any(c["category"] == "minors" for c in r.concerns)

    def test_keyword_in_variable_name_triggers(self):
        """关键词出现在变量名中也应触发。"""
        r = check_operability(
            "X 影响 Y",
            {"dependent_vars": ["EEG 信号"], "independent_vars": ["任务难度"]},
        )
        assert r.is_feasible is False

    def test_empty_input_is_feasible(self):
        r = check_operability("", None)
        assert r.is_feasible is True

    def test_keyword_library_extensible(self):
        """关键词库以字典形式独立维护。"""
        assert isinstance(HIGH_BARRIER_KEYWORDS, dict)
        assert len(HIGH_BARRIER_KEYWORDS) > 0
        # 每条都应有 category 和 alt
        for kw, meta in HIGH_BARRIER_KEYWORDS.items():
            assert "category" in meta
            assert "alt" in meta


# ---------------------------------------------------------------------------
# v3.4 时间预算估算
# ---------------------------------------------------------------------------

class TestTimeBudget:
    def test_survey_design_gets_4_to_8_weeks(self):
        r = check_operability(
            "用问卷调查大学生焦虑水平",
            {"dependent_vars": ["焦虑量表"], "independent_vars": ["性别"]},
        )
        assert r.is_feasible
        assert r.time_budget is not None
        assert r.time_budget["design_type"] == "survey"
        assert r.time_budget["weeks_min"] == 4
        assert r.time_budget["weeks_max"] == 8
        assert "breakdown" in r.time_budget

    def test_experiment_design_gets_8_to_12_weeks(self):
        r = check_operability(
            "通过 PsychoPy 实验研究 n-back 任务对工作记忆的影响",
            {"dependent_vars": ["反应时"], "independent_vars": ["实验组别"]},
        )
        assert r.is_feasible
        assert r.time_budget is not None
        assert r.time_budget["design_type"] == "experiment"
        assert r.time_budget["weeks_min"] == 8
        assert r.time_budget["weeks_max"] == 12

    def test_high_barrier_skips_time_budget(self):
        """不可行场景下不应估算时间预算（以免误导）。"""
        r = check_operability(
            "用 fMRI 研究焦虑的脑机制",
            {"dependent_vars": ["焦虑"]},
            use_llm_check=False,
        )
        assert not r.is_feasible
        assert r.time_budget is None


# ---------------------------------------------------------------------------
# v3.6 LLM 辅助检测
# ---------------------------------------------------------------------------

class TestLLMOperabilityCheck:
    def test_llm_identifies_VR_as_high_barrier(self):
        """VR 不在静态关键词库中，但 LLM 应识别为高门槛。"""
        from src.llm_gateway import clear_cache
        clear_cache()
        # mock LLM 返回 high barrier=true
        import json as _j
        import streamlit as st
        st.session_state.clear()
        llm_response = _j.dumps({
            "is_high_barrier": True,
            "reason": "VR 设备成本高且本科一般无法获取",
            "suggestion": "建议改用 360° 全景视频通过手机播放",
            "source_term": "VR",
        })
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"choices": [{"message": {"content": llm_response}}]}
        mock_req = MagicMock()
        mock_req.post.return_value = mock_resp

        r = check_operability(
            "使用 VR 沉浸式环境研究焦虑",
            {"dependent_vars": ["焦虑"]},
            use_llm_check=True,
            llm_config={"provider": "openai", "base_url": "https://x",
                          "api_key": "sk-test", "model": "gpt-4"},
            requests_module=mock_req,
        )
        assert not r.is_feasible
        assert any(c.get("category") == "llm_detected" for c in r.concerns)
        assert any("360" in s or "全景" in s for s in r.suggestions)

    def test_llm_judges_normal_survey_low_barrier(self):
        """普通问卷研究 LLM 应判定低门槛。"""
        from src.llm_gateway import clear_cache
        clear_cache()
        import json as _j
        import streamlit as st
        st.session_state.clear()
        llm_response = _j.dumps({
            "is_high_barrier": False,
            "reason": "",
            "suggestion": "",
            "source_term": "",
        })
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"choices": [{"message": {"content": llm_response}}]}
        mock_req = MagicMock()
        mock_req.post.return_value = mock_resp

        r = check_operability(
            "用问卷调查大学生焦虑水平",
            {"dependent_vars": ["焦虑量表"]},
            use_llm_check=True,
            llm_config={"provider": "openai", "base_url": "https://x",
                          "api_key": "sk-test", "model": "gpt-4"},
            requests_module=mock_req,
        )
        assert r.is_feasible
        assert not any(c.get("category") == "llm_detected" for c in r.concerns)

    def test_no_llm_falls_back_to_static_only(self):
        """LLM 不可用时仅用静态检查（不报错）。"""
        r = check_operability(
            "用 VR 沉浸式环境研究焦虑",
            {"dependent_vars": ["焦虑"]},
            use_llm_check=True,
            llm_config={"provider": "openai", "api_key": ""},   # 无 key
        )
        # LLM 不可用 → 仅静态检查 → VR 不在 HIGH_BARRIER_KEYWORDS → is_feasible=True
        # （这是 v3.5 的 behaviour，正是 v3.6 LLM 辅助要补的盲区）
        assert r.is_feasible


# ---------------------------------------------------------------------------
# v3.3: 有意义反思
# ---------------------------------------------------------------------------

class TestSignificanceReflection:
    def test_no_llm_returns_default_questions(self):
        r = suggest_significance_reflection("X 影响 Y？", llm_config=None)
        assert r["is_llm_generated"] is False
        assert len(r["questions"]) >= 2
        assert all("?" in q or "？" in q for q in r["questions"])

    def test_empty_input_returns_default(self):
        r = suggest_significance_reflection("")
        assert r["is_llm_generated"] is False
        assert len(r["questions"]) >= 2

    def test_llm_generated_returns_custom(self):
        """LLM 可用时返回定制问题。"""
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "choices": [{"message": {"content":
                "你的研究对真实学校教学有什么启发？\n"
                "已有研究中类似主题的发现是什么？\n"
                "你的发现对教育政策有什么影响？"
            }}],
        }
        mock_req = MagicMock()
        mock_req.post.return_value = mock_resp

        r = suggest_significance_reflection(
            "学习动机对成绩的影响",
            llm_config={
                "provider": "openai", "base_url": "https://x",
                "api_key": "sk-test", "model": "gpt-4",
            },
            requests_module=mock_req,
        )
        assert r["is_llm_generated"] is True
        assert len(r["questions"]) >= 2
        assert any("学校" in q or "教育" in q for q in r["questions"])

    def test_llm_failure_falls_back_to_default(self):
        """LLM 调用失败应降级到默认问题。"""
        mock_resp = MagicMock(status_code=500)
        mock_resp.text = "Server Error"
        mock_req = MagicMock()
        mock_req.post.return_value = mock_resp

        r = suggest_significance_reflection(
            "X 影响 Y",
            llm_config={
                "provider": "openai", "base_url": "https://x",
                "api_key": "sk-test", "model": "gpt-4",
            },
            requests_module=mock_req,
        )
        assert r["is_llm_generated"] is False
        assert len(r["questions"]) >= 2
