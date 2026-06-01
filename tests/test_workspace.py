"""工作区序列化与恢复测试"""

import pytest
import pandas as pd
import numpy as np
import streamlit as st

from src.utils.workspace import (
    build_workspace_snapshot,
    restore_workspace,
    _serialize_plan,
    _deserialize_plan,
    _serialize_analysis_output,
    _deserialize_analysis_output,
    _migrate_workspace,
    FutureSchemaError,
)
from src.parser.intent_resolver import AnalysisPlan


class TestSerializePlan:
    def test_none_returns_none(self):
        assert _serialize_plan(None) is None

    def test_dict_wrapper(self):
        d = {"foo": 1}
        s = _serialize_plan(d)
        assert s["__type__"] == "dict"
        assert s["data"] == d

    def test_analysis_plan_roundtrip(self):
        plan = AnalysisPlan(
            test_type="independent_ttest",
            dependent_vars=["score"],
            independent_vars=["group"],
            grouping_var="group",
            covariates=["age"],
            scale_items=["q1", "q2"],
            blocks=[["q1", "q2"]],
            test_value=0.5,
            confidence_level=0.99,
            raw_request="比较两组差异",
            parsed_keywords=["t检验"],
            ambiguity_score=0.2,
            suggested_followups=["换非参数检验"],
        )
        s = _serialize_plan(plan)
        restored = _deserialize_plan(s)
        assert restored.test_type == "independent_ttest"
        assert restored.dependent_vars == ["score"]
        assert restored.confidence_level == 0.99
        assert restored.suggested_followups == ["换非参数检验"]


class TestSerializeAnalysisOutput:
    def test_empty_dict_returns_none(self):
        assert _serialize_analysis_output({}) is None

    def test_dataframe_roundtrip(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        ao = {"test_type": "anova", "descriptive": df}
        s = _serialize_analysis_output(ao)
        restored = _deserialize_analysis_output(s)
        assert restored["test_type"] == "anova"
        pd.testing.assert_frame_equal(restored["descriptive"], df)


class TestBuildAndRestoreWorkspace:
    def test_build_snapshot_contains_version(self):
        st.session_state.clear()
        st.session_state.df = pd.DataFrame({"x": [1, 2]})
        ws = build_workspace_snapshot()
        assert ws["_version"] == "3.5"
        assert ws["_schema"] == "v3.5"
        assert "df_b64" in ws

    def test_restore_workspace_roundtrip(self):
        st.session_state.clear()
        st.session_state.df = pd.DataFrame({"x": [1, 2, 3]})
        st.session_state.meta = {"source_type": "csv"}
        st.session_state.file_name = "demo.csv"
        ws = build_workspace_snapshot()

        st.session_state.clear()
        n = restore_workspace(ws)
        assert n >= 3
        assert st.session_state.file_name == "demo.csv"
        pd.testing.assert_frame_equal(st.session_state.df, pd.DataFrame({"x": [1, 2, 3]}))

    def test_migration_from_v1_to_current(self):
        """v1 (workspace_v1) → 当前版本: 添加 experiment_design 和 paper_engine_state 占位"""
        old_ws = {
            "_schema": "workspace_v1",
            "_version": "2.5.1",
            "file_name": "old.csv",
        }
        migrated = _migrate_workspace(old_ws)
        assert migrated["_schema"] == "v3.5"
        assert migrated["_migrated_from"] == "workspace_v1"
        assert "experiment_design" in migrated
        assert "paper_engine_state" in migrated

    def test_migration_v2_5_to_current(self):
        """v2.5 → 当前版本: 填充 pipeline_config 默认值"""
        old_ws = {
            "_schema": "v2.5",
            "file_name": "v25_data.csv",
        }
        migrated = _migrate_workspace(old_ws)
        assert migrated["_schema"] == "v3.5"
        assert migrated["_migrated_from"] == "v2.5"
        assert "pipeline_config" in migrated
        assert migrated["pipeline_config"] is None

    def test_migration_v2_5_1_to_current(self):
        old_ws = {
            "_schema": "v2.5.1",
            "file_name": "v251_data.csv",
        }
        migrated = _migrate_workspace(old_ws)
        assert migrated["_schema"] == "v3.5"
        assert "pipeline_config" in migrated

    def test_migration_v3_5_no_change(self):
        """v3.5 (current) 无需迁移"""
        ws = {
            "_schema": "v3.5",
            "file_name": "current.csv",
        }
        migrated = _migrate_workspace(ws)
        assert migrated["_schema"] == "v3.5"
        assert "_migrated_from" not in migrated

    def test_migration_future_version_rejected(self):
        """未来版本 (v3.6) 应拒绝加载"""
        future_ws = {
            "_schema": "v3.6",
            "file_name": "future.csv",
        }
        with pytest.raises(FutureSchemaError, match="请升级系统"):
            _migrate_workspace(future_ws)

    def test_migration_workspace_v2_normalized(self):
        """旧版 _schema='workspace_v2' 归一化为 v2.5 后迁移到当前版本"""
        old_ws = {
            "_schema": "workspace_v2",
            "file_name": "wsv2.csv",
        }
        migrated = _migrate_workspace(old_ws)
        assert migrated["_schema"] == "v3.5"
        assert "pipeline_config" in migrated


class TestV29WorkspaceIntegration:
    """v2.9: 图表收藏夹/答辩掌握状态/下载历史的工作区集成。"""

    def test_v2_8_workspace_migrates_to_v3_5_with_empty_collections(self):
        """v2.8 工作区加载时应自动初始化空收藏夹/掌握状态/下载历史并升至 v3.4。"""
        old_ws = {"_schema": "v2.8", "file_name": "old_v28.csv"}
        migrated = _migrate_workspace(old_ws)
        assert migrated["_schema"] == "v3.5"
        assert migrated["figure_collection"] == []
        assert migrated["defense_qa_mastered"] == {}
        assert migrated["download_history"] == []
        assert "upstream_state" in migrated

    def test_figure_collection_round_trip(self):
        """图表收藏夹保存到工作区并恢复。"""
        import plotly.graph_objects as go
        from src.utils.figure_collection import FigureCollection, SESSION_KEY

        st.session_state.clear()
        coll = FigureCollection()
        fig = go.Figure(go.Scatter(x=[1, 2], y=[3, 4]))
        coll.add(
            title="测试图",
            test_type="independent_ttest",
            variables=["焦虑", "性别"],
            fig_object=fig,
            note="论文必用",
            chart_type="箱线图",
        )
        st.session_state[SESSION_KEY] = coll

        ws = build_workspace_snapshot()
        assert "figure_collection" in ws
        assert len(ws["figure_collection"]) == 1
        assert ws["figure_collection"][0]["title"] == "测试图"

        # 清空再恢复
        st.session_state.clear()
        restore_workspace(ws)
        restored_coll = st.session_state.get(SESSION_KEY)
        assert restored_coll is not None
        assert len(restored_coll) == 1
        assert restored_coll.entries[0].title == "测试图"
        assert restored_coll.entries[0].note == "论文必用"

    def test_defense_qa_mastered_round_trip(self):
        st.session_state.clear()
        st.session_state["defense_qa_mastered"] = {"Q1": True, "Q2": False}
        ws = build_workspace_snapshot()
        assert ws["defense_qa_mastered"] == {"Q1": True, "Q2": False}

        st.session_state.clear()
        restore_workspace(ws)
        assert st.session_state["defense_qa_mastered"] == {"Q1": True, "Q2": False}

    def test_download_history_round_trip(self):
        st.session_state.clear()
        history = [
            {"file": "论文初稿.docx", "type": "Word", "ts": "2026-05-17 10:00"},
        ]
        st.session_state["download_history"] = history
        ws = build_workspace_snapshot()
        assert ws["download_history"] == history

        st.session_state.clear()
        restore_workspace(ws)
        assert st.session_state["download_history"] == history


class TestV32UpstreamMigration:
    """v3.2: upstream_state（选题漏斗+ResearchTier）迁移与持久化。"""

    def test_v2_9_workspace_migrates_to_v3_5_with_default_upstream(self):
        """空 v2.9 工作区（无 wizard_data）→ v3.4 应有 phase=funnel 默认 upstream_state。"""
        old_ws = {"_schema": "v2.9", "file_name": "v29.csv"}
        migrated = _migrate_workspace(old_ws)
        assert migrated["_schema"] == "v3.5"
        assert migrated["_migrated_from"] == "v2.9"
        upstream = migrated["upstream_state"]
        assert upstream["tier"] == "beginner"
        assert upstream["phase"] == "funnel"      # 空项目走漏斗
        assert upstream["current_stage"] == 1
        assert upstream["research_question"] == ""
        assert upstream["candidate_vars"]["dependent_vars"] == []

    def test_v2_9_with_wizard_data_skips_funnel(self):
        """v2.9 老项目（已有 research_q）→ v3.2 phase=wizard 跳过漏斗，反向填充 candidate_vars。"""
        old_ws = {
            "_schema": "v2.9",
            "undergrad_wizard_data": {
                "title": "大学生焦虑研究",
                "research_q": "学业压力如何影响焦虑？",
                "hypothesis": "压力越大焦虑越高",
                "iv": "学业压力",
                "dv": "焦虑水平",
            },
        }
        migrated = _migrate_workspace(old_ws)
        upstream = migrated["upstream_state"]
        assert upstream["phase"] == "wizard"      # 老项目跳过漏斗
        assert upstream["current_stage"] == 5
        assert upstream["research_question"] == "学业压力如何影响焦虑？"
        assert upstream["candidate_vars"]["dependent_vars"] == ["焦虑水平"]
        assert upstream["candidate_vars"]["independent_vars"] == ["学业压力"]
        assert upstream["candidate_vars"]["grouping_var"] == "学业压力"

    def test_v2_9_with_wizard_results_context_extracts_vars(self):
        """v2.9 老项目（wizard_results_context 优先）→ candidate_vars 从 ctx 取。"""
        old_ws = {
            "_schema": "v2.9",
            "undergrad_wizard_data": {
                "research_q": "测试问题",
                "wizard_results_context": {
                    "test_type": "independent_ttest",
                    "dv": "成绩",
                    "iv": "组别",
                },
            },
        }
        migrated = _migrate_workspace(old_ws)
        upstream = migrated["upstream_state"]
        assert upstream["candidate_vars"]["dependent_vars"] == ["成绩"]
        assert upstream["candidate_vars"]["independent_vars"] == ["组别"]

    def test_upstream_state_round_trip(self):
        """build → restore 应保留完整 upstream_state（含 stages 历史）。"""
        from src.utils.workspace import (
            UPSTREAM_SESSION_KEY,
            _default_upstream_state,
        )
        from src.paper_writer.ai_tutor import ChatMessage

        st.session_state.clear()
        state = _default_upstream_state()
        state["tier"] = "advanced"
        state["phase"] = "funnel"
        state["current_stage"] = 3
        state["research_question"] = "X 是否影响 Y？"
        state["candidate_vars"] = {
            "dependent_vars": ["焦虑"],
            "independent_vars": ["睡眠"],
            "grouping_var": "睡眠",
            "covariates": ["年龄"],
        }
        state["stages"] = {
            "1": {
                "interest_text": "我想研究睡眠",
                "ai_history": [
                    ChatMessage(role="assistant", content="什么人群？"),
                    ChatMessage(role="user", content="大学生"),
                ],
                "completed": True,
                "output": {"summary": "大学生睡眠"},
            }
        }
        state["feasibility_results"] = {"falsifiable": "睡眠时长与焦虑无关"}
        st.session_state[UPSTREAM_SESSION_KEY] = state

        ws = build_workspace_snapshot()
        assert "upstream_state" in ws
        # stages 中的 ChatMessage 必须序列化为 dict
        stage1_history = ws["upstream_state"]["stages"]["1"]["ai_history"]
        assert isinstance(stage1_history[0], dict)
        assert stage1_history[0]["role"] == "assistant"

        # 恢复
        st.session_state.clear()
        restore_workspace(ws)
        restored = st.session_state[UPSTREAM_SESSION_KEY]
        assert restored["tier"] == "advanced"
        assert restored["current_stage"] == 3
        assert restored["research_question"] == "X 是否影响 Y？"
        assert restored["candidate_vars"]["covariates"] == ["年龄"]
        # ChatMessage 应被还原
        h = restored["stages"]["1"]["ai_history"]
        assert h[0].role == "assistant"
        assert h[1].content == "大学生"
        assert restored["feasibility_results"]["falsifiable"] == "睡眠时长与焦虑无关"

    def test_get_upstream_state_self_heals_missing_keys(self):
        """get_upstream_state 应补全缺失键（向前兼容旧字段集）。"""
        from src.utils.workspace import (
            UPSTREAM_SESSION_KEY,
            get_upstream_state,
        )
        st.session_state.clear()
        # 模拟从旧版本恢复的不完整 state
        st.session_state[UPSTREAM_SESSION_KEY] = {"tier": "beginner"}
        state = get_upstream_state(st.session_state)
        assert "phase" in state
        assert "stages" in state
        assert "candidate_vars" in state
        assert state["tier"] == "beginner"      # 不覆盖已有值


# ---------------------------------------------------------------------------
# v3.7 N6: 断点续读位置标记
# ---------------------------------------------------------------------------

class TestN6_LastPosition:
    def test_update_last_position_writes_to_state(self):
        from src.utils.workspace import (
            UPSTREAM_SESSION_KEY,
            update_last_position,
        )
        st.session_state.clear()
        update_last_position("funnel", step=3, session_state=st.session_state)
        state = st.session_state[UPSTREAM_SESSION_KEY]
        assert state["last_position"]["phase"] == "funnel"
        assert state["last_position"]["step"] == 3
        assert "选题漏斗" in state["last_position"]["label"]
        assert "stage 3" in state["last_position"]["label"]
        assert state["last_position"]["timestamp"]   # 非空 ISO

    def test_update_last_position_wizard_step_label(self):
        from src.utils.workspace import update_last_position
        st.session_state.clear()
        update_last_position("wizard", step=5, session_state=st.session_state)
        pos = st.session_state["upstream_state"]["last_position"]
        assert "数据分析向导" in pos["label"]
        assert "第 5 步" in pos["label"]

    def test_get_last_position_returns_none_when_unset(self):
        from src.utils.workspace import get_last_position
        st.session_state.clear()
        assert get_last_position(st.session_state) is None

    def test_get_last_position_returns_dict(self):
        from src.utils.workspace import get_last_position, update_last_position
        st.session_state.clear()
        update_last_position("literature_review", session_state=st.session_state)
        pos = get_last_position(st.session_state)
        assert pos is not None
        assert pos["phase"] == "literature_review"
        assert "文献综述" in pos["label"]

    def test_update_overwrites_previous(self):
        from src.utils.workspace import get_last_position, update_last_position
        st.session_state.clear()
        update_last_position("funnel", step=1, session_state=st.session_state)
        update_last_position("funnel", step=4, session_state=st.session_state)
        pos = get_last_position(st.session_state)
        assert pos["step"] == 4

    def test_custom_label_respected(self):
        from src.utils.workspace import update_last_position
        st.session_state.clear()
        update_last_position("funnel", step=2,
                              label="自定义标签：选题阶段 - 兴趣捕捉",
                              session_state=st.session_state)
        pos = st.session_state["upstream_state"]["last_position"]
        assert pos["label"] == "自定义标签：选题阶段 - 兴趣捕捉"

    def test_humanize_elapsed_minutes(self):
        from datetime import datetime, timedelta
        from src.utils.workspace import humanize_elapsed
        ts = (datetime.now() - timedelta(minutes=15)).isoformat(timespec="seconds")
        assert humanize_elapsed(ts) == "15 分钟前"

    def test_humanize_elapsed_hours(self):
        from datetime import datetime, timedelta
        from src.utils.workspace import humanize_elapsed
        ts = (datetime.now() - timedelta(hours=3)).isoformat(timespec="seconds")
        assert humanize_elapsed(ts) == "3 小时前"

    def test_humanize_elapsed_days(self):
        from datetime import datetime, timedelta
        from src.utils.workspace import humanize_elapsed
        ts = (datetime.now() - timedelta(days=2)).isoformat(timespec="seconds")
        assert humanize_elapsed(ts) == "2 天前"

    def test_humanize_elapsed_just_now(self):
        from datetime import datetime
        from src.utils.workspace import humanize_elapsed
        ts = datetime.now().isoformat(timespec="seconds")
        assert humanize_elapsed(ts) == "刚刚"

    def test_humanize_elapsed_invalid(self):
        from src.utils.workspace import humanize_elapsed
        assert humanize_elapsed("") == ""
        assert humanize_elapsed("not-a-date") == ""

    def test_is_at_last_position_when_unset(self):
        from src.utils.workspace import is_at_last_position
        st.session_state.clear()
        assert is_at_last_position(st.session_state) is True

    def test_is_at_last_position_when_match(self):
        from src.utils.workspace import (
            UPSTREAM_SESSION_KEY,
            is_at_last_position,
            update_last_position,
        )
        st.session_state.clear()
        st.session_state[UPSTREAM_SESSION_KEY] = {
            "phase": "funnel",
            "current_stage": 3,
        }
        update_last_position("funnel", step=3, session_state=st.session_state)
        assert is_at_last_position(st.session_state) is True

    def test_is_at_last_position_when_diff(self):
        from src.utils.workspace import (
            UPSTREAM_SESSION_KEY,
            is_at_last_position,
            update_last_position,
        )
        st.session_state.clear()
        update_last_position("funnel", step=3, session_state=st.session_state)
        # 用户已经走到了 stage 5
        st.session_state[UPSTREAM_SESSION_KEY]["phase"] = "funnel"
        st.session_state[UPSTREAM_SESSION_KEY]["current_stage"] = 5
        assert is_at_last_position(st.session_state) is False

    def test_default_state_includes_last_position(self):
        """新建的 upstream_state 含 last_position 占位（向前兼容老快照）。"""
        from src.utils.workspace import get_upstream_state
        st.session_state.clear()
        state = get_upstream_state(st.session_state)
        assert "last_position" in state
        assert state["last_position"]["phase"] == ""
