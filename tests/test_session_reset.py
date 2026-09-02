"""新研究会话重置回归测试。"""

from src.ui.session_reset import clear_research_session


def test_clear_research_session_removes_cross_project_assets_but_keeps_preferences():
    state = {
        "df": object(),
        "analysis_output": {"p": 0.01},
        "analysis_cards": [{"id": "old"}],
        "paper_bundle": {"sections": {"results": "old"}},
        "uploaded_df": object(),
        "research_deliverable_bundle": object(),
        "evidence_store": object(),
        "export_allowed": True,
        "figure_collection": ["old-figure"],
        "quick_model_id": "deepseek",
        "privacy_accepted": True,
        "onboarding_completed": True,
        "_active_project_id": "new-project",
    }

    cleared = clear_research_session(state)

    assert "paper_bundle" in cleared
    assert state["df"] is None
    assert state["analysis_output"] is None
    assert state["analysis_history"] == []
    for key in (
        "analysis_cards",
        "paper_bundle",
        "evidence_store",
        "export_allowed",
        "figure_collection",
        "uploaded_df",
        "research_deliverable_bundle",
    ):
        assert key not in state
    assert state["quick_model_id"] == "deepseek"
    assert state["privacy_accepted"] is True
    assert state["onboarding_completed"] is True
    assert state["_active_project_id"] == "new-project"
    assert "file_uploader" in state["_pending_widget_resets"]
    assert "workspace_loader" in state["_pending_widget_resets"]


def test_clear_research_session_returns_fresh_mutable_defaults():
    first = {}
    second = {}
    clear_research_session(first)
    clear_research_session(second)
    first["analysis_history"].append("x")
    first["undergrad_wizard_data"]["x"] = 1
    assert second["analysis_history"] == []
    assert second["undergrad_wizard_data"] == {}


def test_clear_research_session_cancels_pending_future():
    class FakeFuture:
        cancelled = False

        def cancel(self):
            self.cancelled = True

    future = FakeFuture()
    state = {"_q_design_pending": {"future": future}}
    clear_research_session(state)
    assert future.cancelled is True
    assert "_q_design_pending" not in state
