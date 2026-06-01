"""上游模块端到端集成测试：漏斗 → wizard 数据贯通、老项目兼容、降级路径。"""

import pytest
import streamlit as st

from src.upstream.tier import ResearchTier, get_active_tier, set_active_tier
from src.upstream.topic_funnel import (
    advance_stage,
    complete_funnel,
    restart_funnel,
    set_candidate_vars,
    update_stage_data,
)
from src.utils.workspace import (
    UPSTREAM_SESSION_KEY,
    _migrate_workspace,
    build_workspace_snapshot,
    get_upstream_state,
    restore_workspace,
)


@pytest.fixture
def mock_save():
    def _fn(session_state, project_id):
        pass
    return _fn


class TestEndToEndBeginnerFlow:
    """BEGINNER 完整流程：新项目 → 漏斗 → wizard 字段预填。"""

    def test_full_beginner_path_writes_to_wizard(self, mock_save):
        st.session_state.clear()
        # 模拟新项目（默认 phase=funnel）
        upstream = get_upstream_state(st.session_state)
        assert upstream["phase"] == "funnel"
        assert upstream["current_stage"] == 1

        # 阶段 1：填兴趣
        update_stage_data(upstream, 1, interest_text="我想研究大学生焦虑", completed=True)
        advance_stage(st.session_state, save_workspace_fn=mock_save)
        # 阶段 2
        update_stage_data(upstream, 2, interest_text="期末考试前焦虑加剧", completed=True)
        advance_stage(st.session_state, save_workspace_fn=mock_save)
        # 阶段 3：手动设置候选变量
        set_candidate_vars(
            st.session_state,
            dependent_vars=["焦虑"],
            independent_vars=["考试压力"],
            grouping_var="考试压力",
        )
        update_stage_data(upstream, 3, completed=True)
        advance_stage(st.session_state, save_workspace_fn=mock_save)
        # 阶段 4
        upstream["feasibility_results"] = {
            "falsifiable": {"answered": True, "raw": "如果错了，焦虑和压力无关"},
        }
        update_stage_data(upstream, 4, completed=True)
        advance_stage(st.session_state, save_workspace_fn=mock_save)
        # 阶段 5：定研究问题，完成漏斗
        upstream["research_question"] = "在大学生中，考试压力是否影响焦虑？"
        complete_funnel(st.session_state, save_workspace_fn=mock_save)

        # 验证 phase 切换 + wizard_data 已填充
        upstream = get_upstream_state(st.session_state)
        assert upstream["phase"] == "wizard"
        wd = st.session_state["undergrad_wizard_data"]
        assert wd["research_q"] == "在大学生中，考试压力是否影响焦虑？"
        assert wd["dv"] == "焦虑"
        assert wd["iv"] == "考试压力"


class TestAdvancedSkipPath:
    """ADVANCED tier：直接跳过漏斗，产物 schema 与 BEGINNER 一致。"""

    def test_advanced_skip_produces_same_schema_as_beginner(self, mock_save):
        # 路径 1：BEGINNER 完整漏斗
        st.session_state.clear()
        upstream_b = get_upstream_state(st.session_state)
        upstream_b["research_question"] = "X 影响 Y？"
        set_candidate_vars(
            st.session_state, dependent_vars=["Y"], independent_vars=["X"],
            grouping_var="X",
        )
        complete_funnel(st.session_state, save_workspace_fn=mock_save)
        beginner_wd = dict(st.session_state["undergrad_wizard_data"])

        # 路径 2：ADVANCED 跳过表单
        st.session_state.clear()
        set_active_tier(st.session_state, ResearchTier.ADVANCED)
        upstream_a = get_upstream_state(st.session_state)
        upstream_a["research_question"] = "X 影响 Y？"
        set_candidate_vars(
            st.session_state, dependent_vars=["Y"], independent_vars=["X"],
            grouping_var="X",
        )
        complete_funnel(st.session_state, save_workspace_fn=mock_save)
        advanced_wd = dict(st.session_state["undergrad_wizard_data"])

        # 关键字段必须一致
        for key in ["research_q", "dv", "iv"]:
            assert beginner_wd.get(key) == advanced_wd.get(key), \
                f"BEGINNER vs ADVANCED 在 {key} 上不一致"


class TestLegacyProjectCompat:
    """老项目（v3.1 之前）升级 v3.2 后应直接进 wizard，不被漏斗拦。"""

    def test_legacy_v2_9_with_research_q_skips_funnel(self):
        """模拟 v3.1 创建的项目（_schema=v2.9 + 已有 research_q）。"""
        legacy_ws = {
            "_schema": "v2.9",
            "_version": "2.9",
            "file_name": "legacy.csv",
            "undergrad_wizard_data": {
                "title": "已有标题",
                "research_q": "已有研究问题",
                "hypothesis": "H1: ...",
                "iv": "压力",
                "dv": "焦虑",
            },
        }
        migrated = _migrate_workspace(legacy_ws)
        assert migrated["_schema"] == "v3.5"
        upstream = migrated["upstream_state"]
        # 关键：phase=wizard 让老项目直接进 wizard 而非漏斗
        assert upstream["phase"] == "wizard"
        # 反向填充验证
        assert upstream["research_question"] == "已有研究问题"
        assert upstream["candidate_vars"]["dependent_vars"] == ["焦虑"]
        assert upstream["candidate_vars"]["independent_vars"] == ["压力"]

    def test_legacy_empty_v2_9_goes_to_funnel(self):
        """空白 v2.9（无 wizard_data）应走漏斗（视为新项目）。"""
        legacy_ws = {"_schema": "v2.9", "file_name": "empty.csv"}
        migrated = _migrate_workspace(legacy_ws)
        assert migrated["upstream_state"]["phase"] == "funnel"


class TestRestartFunnelKeepsHistory:
    """从 wizard「回到选题漏斗」应保留 stages 历史。"""

    def test_restart_preserves_stage_data(self, mock_save):
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        # 走完漏斗
        update_stage_data(upstream, 1, interest_text="原始兴趣", completed=True)
        update_stage_data(upstream, 2, interest_text="具体现象", completed=True)
        upstream["research_question"] = "已确定的问题"
        complete_funnel(st.session_state, save_workspace_fn=mock_save)
        assert get_upstream_state(st.session_state)["phase"] == "wizard"

        # 回到漏斗
        restart_funnel(st.session_state, keep_history=True, save_workspace_fn=mock_save)
        upstream = get_upstream_state(st.session_state)
        assert upstream["phase"] == "funnel"
        # v3.3: keep_history=True 跳到 stage 5（"继续修改"语义）
        assert upstream["current_stage"] == 5
        # 历史保留
        assert upstream["stages"]["1"]["interest_text"] == "原始兴趣"
        assert upstream["stages"]["2"]["interest_text"] == "具体现象"
        assert upstream["research_question"] == "已确定的问题"


class TestFunnelBranches:
    """v3.3 漏斗分支系统：归档、切换、删除、跨保存恢复。"""

    def test_archive_creates_branch_in_history(self, mock_save):
        from src.upstream.topic_funnel import (
            archive_current_branch,
            get_funnel_history,
            update_stage_data,
        )
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        update_stage_data(upstream, 1, interest_text="原选题", completed=True)
        upstream["research_question"] = "在 X 中，A 是否影响 B？"
        upstream["candidate_vars"] = {
            "dependent_vars": ["B"], "independent_vars": ["A"],
            "grouping_var": "A", "covariates": [],
        }

        bid = archive_current_branch(st.session_state, save_workspace_fn=mock_save)
        assert bid is not None
        history = get_funnel_history(st.session_state)
        assert len(history) == 1
        assert history[0]["branch_id"] == bid
        assert history[0]["final_research_q"] == "在 X 中，A 是否影响 B？"

    def test_archive_and_restart_clears_active(self, mock_save):
        from src.upstream.topic_funnel import (
            archive_current_branch_and_restart,
            update_stage_data,
        )
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        update_stage_data(upstream, 1, interest_text="第一次尝试", completed=True)
        upstream["research_question"] = "第一次问题"

        bid = archive_current_branch_and_restart(st.session_state, save_workspace_fn=mock_save)
        assert bid is not None

        upstream = get_upstream_state(st.session_state)
        # active 已清空
        assert upstream["stages"] == {}
        assert upstream["research_question"] == ""
        assert upstream["current_stage"] == 1
        # 但分支保留
        assert len(upstream["funnel_history"]) == 1

    def test_switch_to_branch_archives_current(self, mock_save):
        from src.upstream.topic_funnel import (
            archive_current_branch_and_restart,
            switch_to_branch,
            update_stage_data,
        )
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)

        # 第一次选题
        update_stage_data(upstream, 1, interest_text="A 题目", completed=True)
        upstream["research_question"] = "A 题目的问题"
        upstream["candidate_vars"] = {"dependent_vars": ["A_dv"], "independent_vars": ["A_iv"], "grouping_var": "", "covariates": []}
        bid_a = archive_current_branch_and_restart(st.session_state, save_workspace_fn=mock_save)

        # 第二次选题
        update_stage_data(upstream, 1, interest_text="B 题目", completed=True)
        upstream["research_question"] = "B 题目的问题"
        upstream["candidate_vars"] = {"dependent_vars": ["B_dv"], "independent_vars": ["B_iv"], "grouping_var": "", "covariates": []}

        # 切回 A 分支
        ok = switch_to_branch(st.session_state, bid_a, save_workspace_fn=mock_save)
        assert ok is True

        upstream = get_upstream_state(st.session_state)
        # active 应是 A 内容
        assert upstream["research_question"] == "A 题目的问题"
        assert upstream["candidate_vars"]["dependent_vars"] == ["A_dv"]
        # B 应被归档为新分支
        history = upstream["funnel_history"]
        b_branches = [b for b in history if b.get("final_research_q") == "B 题目的问题"]
        assert len(b_branches) == 1

    def test_delete_branch_removes_from_history(self, mock_save):
        from src.upstream.topic_funnel import (
            archive_current_branch_and_restart,
            delete_branch,
            update_stage_data,
        )
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        update_stage_data(upstream, 1, interest_text="将被删除", completed=True)
        upstream["research_question"] = "待删除"
        bid = archive_current_branch_and_restart(st.session_state, save_workspace_fn=mock_save)

        ok = delete_branch(st.session_state, bid, save_workspace_fn=mock_save)
        assert ok is True
        upstream = get_upstream_state(st.session_state)
        assert all(b["branch_id"] != bid for b in (upstream["funnel_history"] or []))

    def test_branches_persist_across_save_load(self):
        from src.utils.workspace import build_workspace_snapshot, restore_workspace
        from src.upstream.topic_funnel import (
            archive_current_branch_and_restart,
            update_stage_data,
        )
        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        update_stage_data(upstream, 1, interest_text="保存前", completed=True)
        upstream["research_question"] = "保存前的问题"
        bid = archive_current_branch_and_restart(st.session_state)

        ws = build_workspace_snapshot()
        assert "funnel_history" in ws["upstream_state"]

        st.session_state.clear()
        restore_workspace(ws)
        upstream = get_upstream_state(st.session_state)
        assert any(b["branch_id"] == bid for b in upstream["funnel_history"])


class TestUpstreamStatePersistsAcrossSaveLoad:
    """漏斗中途保存 → 清空 → 加载，状态完整恢复（模拟切项目场景）。"""

    def test_mid_funnel_save_load_preserves_all_state(self):
        from src.paper_writer.ai_tutor import ChatMessage

        st.session_state.clear()
        upstream = get_upstream_state(st.session_state)
        upstream["current_stage"] = 3
        update_stage_data(
            upstream, 1,
            interest_text="阶段 1 的描述",
            ai_history=[
                ChatMessage(role="user", content="我想研究睡眠"),
                ChatMessage(role="assistant", content="哪种人群？"),
            ],
            completed=True,
        )
        set_candidate_vars(
            st.session_state, dependent_vars=["睡眠质量"], independent_vars=["压力"],
        )

        # 保存
        ws = build_workspace_snapshot()
        assert "upstream_state" in ws
        # 模拟清空后恢复
        st.session_state.clear()
        n = restore_workspace(ws)
        assert n >= 1

        # 验证完整性
        restored = get_upstream_state(st.session_state)
        assert restored["current_stage"] == 3
        assert restored["stages"]["1"]["interest_text"] == "阶段 1 的描述"
        h = restored["stages"]["1"]["ai_history"]
        assert h[0].role == "user"
        assert h[1].content == "哪种人群？"
        assert restored["candidate_vars"]["dependent_vars"] == ["睡眠质量"]
