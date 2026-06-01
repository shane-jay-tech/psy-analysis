"""选题漏斗状态机测试。"""

import pytest
import streamlit as st

from src.upstream.topic_funnel import (
    MAX_STAGE,
    MIN_STAGE,
    STAGES,
    advance_stage,
    complete_funnel,
    get_stage,
    get_stage_data,
    go_to_stage,
    recognize_constructs,
    restart_funnel,
    set_candidate_vars,
    update_stage_data,
)
from src.utils.workspace import UPSTREAM_SESSION_KEY, get_upstream_state


@pytest.fixture
def mock_save():
    """提供一个无副作用的 save_workspace_fn（避免触发实际文件 IO）。"""
    calls = []
    def _fn(session_state, project_id):
        calls.append((dict(session_state.get(UPSTREAM_SESSION_KEY, {})), project_id))
    _fn.calls = calls
    return _fn


class TestStages:
    def test_five_stages_defined(self):
        assert len(STAGES) == 5
        assert MIN_STAGE == 1
        assert MAX_STAGE == 5

    def test_get_stage_by_id(self):
        s = get_stage(3)
        assert s is not None
        assert "变量" in s.name


class TestStageData:
    def test_default_stage_data_is_empty(self):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        data = get_stage_data(upstream, 1)
        assert data["interest_text"] == ""
        assert data["completed"] is False
        assert data["ai_history"] == []

    def test_update_stage_data_merges(self):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        update_stage_data(upstream, 2, interest_text="社交焦虑")
        update_stage_data(upstream, 2, completed=True)
        data = get_stage_data(upstream, 2)
        assert data["interest_text"] == "社交焦虑"
        assert data["completed"] is True


class TestAdvanceStage:
    def test_advance_marks_current_completed_and_increments(self, mock_save):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        upstream["current_stage"] = 1

        new_stage = advance_stage(st.session_state, save_workspace_fn=mock_save, project_id="p1")
        assert new_stage == 2
        # 阶段 1 应被标记完成
        assert get_stage_data(upstream, 1)["completed"] is True
        # 强制保存被触发
        assert len(mock_save.calls) == 1

    def test_advance_clamps_at_max(self, mock_save):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        upstream["current_stage"] = 5
        new_stage = advance_stage(st.session_state, save_workspace_fn=mock_save)
        assert new_stage == 5  # 不超过 MAX_STAGE


class TestRestartFunnel:
    def test_restart_keeps_history_by_default(self, mock_save):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        upstream["phase"] = "wizard"
        update_stage_data(upstream, 1, interest_text="不该被清", completed=True)
        upstream["research_question"] = "已有问题"

        restart_funnel(st.session_state, save_workspace_fn=mock_save)

        upstream = get_upstream_state(st.session_state)
        assert upstream["phase"] == "funnel"
        # v3.3: keep_history=True 跳到 stage 5（"继续修改"语义），让用户快速回到结尾微调
        assert upstream["current_stage"] == 5
        # 历史保留
        assert get_stage_data(upstream, 1)["interest_text"] == "不该被清"
        assert upstream["research_question"] == "已有问题"

    def test_restart_clears_when_keep_history_false(self, mock_save):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        update_stage_data(upstream, 1, interest_text="将被清", completed=True)
        upstream["research_question"] = "也将被清"

        restart_funnel(st.session_state, keep_history=False, save_workspace_fn=mock_save)

        upstream = get_upstream_state(st.session_state)
        assert upstream["stages"] == {}
        assert upstream["research_question"] == ""


class TestCompleteFunnel:
    def test_completes_and_propagates_to_wizard(self, mock_save):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        upstream["research_question"] = "在大学生中，睡眠时长是否影响焦虑？"
        upstream["candidate_vars"] = {
            "dependent_vars": ["焦虑"],
            "independent_vars": ["睡眠时长"],
            "grouping_var": "",
            "covariates": [],
        }

        payload = complete_funnel(st.session_state, save_workspace_fn=mock_save)

        # phase 切换
        upstream = get_upstream_state(st.session_state)
        assert upstream["phase"] == "wizard"
        assert get_stage_data(upstream, 5)["completed"] is True
        # wizard_data 被填充
        wd = st.session_state["undergrad_wizard_data"]
        assert wd["research_q"] == upstream["research_question"]
        assert wd["dv"] == "焦虑"
        assert wd["iv"] == "睡眠时长"
        assert payload["dv"] == "焦虑"

    def test_complete_does_not_overwrite_existing_title(self, mock_save):
        st.session_state.clear()
        st.session_state["undergrad_wizard_data"] = {"title": "用户已填的标题"}
        upstream = get_upstream_state(st.session_state)
        upstream["research_question"] = "测试"

        complete_funnel(st.session_state, save_workspace_fn=mock_save)
        wd = st.session_state["undergrad_wizard_data"]
        assert wd["title"] == "用户已填的标题"


class TestSetCandidateVars:
    def test_writes_analysis_plan_schema(self):
        st.session_state.clear()
        set_candidate_vars(
            st.session_state,
            dependent_vars=["焦虑"],
            independent_vars=["压力"],
            grouping_var="性别",
            covariates=["年龄"],
        )
        upstream = get_upstream_state(st.session_state)
        cv = upstream["candidate_vars"]
        assert cv["dependent_vars"] == ["焦虑"]
        assert cv["covariates"] == ["年龄"]
        assert cv["grouping_var"] == "性别"


class TestRecognizeConstructs:
    def test_empty_input_returns_ambiguous(self):
        result = recognize_constructs("")
        assert result["is_ambiguous"] is True
        assert result["candidates"] == []

    def test_anxiety_text_matches_construct(self):
        # 应能识别到「焦虑」构念
        result = recognize_constructs("我想研究大学生的焦虑水平")
        # 不严格断言 top_construct（取决于关键词库），但至少有候选
        assert isinstance(result["candidates"], list)
        # 「焦虑」构念应该出现在候选名中
        names = [c["name"] for c in result["candidates"]]
        assert "焦虑" in names or any("焦虑" in n for n in names)
