"""研究会话重置。

只清除当前研究产生的状态；用户偏好、模型配置和项目索引由调用方保留。
集中维护清理范围，避免新面板增加状态后遗留旧论文、证据或导出权限。
"""

from __future__ import annotations

from collections.abc import MutableMapping

from src.ui.state_keys import (
    ANALYSIS_CARDS_KEY,
    ANALYSIS_OUTPUT_KEY,
    ANALYSIS_PLAN_KEY,
    ANALYSIS_RECIPE_KEY,
    DATA_FRAME_KEY,
    DATA_INSPECTOR_KEY,
    DATA_META_KEY,
    EXPORT_ALLOWED_KEY,
    EXPORT_BLOCK_REASONS_KEY,
    PAPER_BUNDLE_KEY,
    PAPER_DIFF_SELECTION_KEY,
    PAPER_REVISED_BUNDLE_KEY,
    PROJECT_HEALTH_CHECKED_AT_KEY,
    PROJECT_HEALTH_ISSUES_KEY,
    RECIPE_EXECUTED_KEY,
    REVIEW_QUEUE_FILTERS_KEY,
    REVIEW_QUEUE_LAST_ACTION_KEY,
)


RESEARCH_SESSION_KEYS = {
    DATA_FRAME_KEY,
    DATA_META_KEY,
    DATA_INSPECTOR_KEY,
    ANALYSIS_OUTPUT_KEY,
    ANALYSIS_PLAN_KEY,
    ANALYSIS_CARDS_KEY,
    ANALYSIS_RECIPE_KEY,
    RECIPE_EXECUTED_KEY,
    PAPER_BUNDLE_KEY,
    PAPER_REVISED_BUNDLE_KEY,
    PAPER_DIFF_SELECTION_KEY,
    EXPORT_ALLOWED_KEY,
    EXPORT_BLOCK_REASONS_KEY,
    PROJECT_HEALTH_ISSUES_KEY,
    PROJECT_HEALTH_CHECKED_AT_KEY,
    REVIEW_QUEUE_FILTERS_KEY,
    REVIEW_QUEUE_LAST_ACTION_KEY,
    "file_name",
    "uploaded_df",
    "current_file_name",
    "analysis_history",
    "questionnaire_design",
    "experiment_engine",
    "paper_engine",
    "undergrad_path",
    "undergrad_step",
    "undergrad_wizard_data",
    "workspace",
    "upstream_state",
    "literature_review_state",
    "method_recommendations",
    "method_recommendation_result",
    "method_recommendation_history",
    "questionnaire_cleaned_result",
    "questionnaire_dimensions",
    "questionnaire_raw_df",
    "template_created_project",
    "template_selected_id",
    "template_source",
    "project_id",
    "apa_figures",
    "figure_collection",
    "evidence_store",
    "evidence_records",
    "consistency_issues",
    "research_deliverable_bundle",
    "download_history",
    "defense_qa_mastered",
    "_defense_qa_items",
    "_wizard_return",
    "_analysis_cache_key",
    "_df_hash_memo",
    "_workspace_last_saved",
    "_autosave_last_ts",
    "_autosave_last_error",
    "_ws_export_json",
    "_ws_export_ts",
    "_workspace_import_handled",
    "_uploaded_file_identity",
    "_upload_error",
    "_loaded_params",
    "polished_draft",
    "_q_design_pending",
    "_exp_design_pending",
}


SESSION_DEFAULTS = {
    DATA_FRAME_KEY: None,
    DATA_META_KEY: None,
    DATA_INSPECTOR_KEY: None,
    ANALYSIS_OUTPUT_KEY: None,
    ANALYSIS_PLAN_KEY: None,
    "file_name": None,
    "analysis_history": [],
    "questionnaire_design": None,
    "experiment_engine": None,
    "paper_engine": None,
    "undergrad_path": None,
    "undergrad_step": 0,
    "undergrad_wizard_data": {},
    "archive_tag": "",
}

RESEARCH_WIDGET_KEYS = {
    "file_uploader",
    "workspace_loader",
    "large_file_cols",
    "load_large_file",
    "request_input",
    "q_request_input",
    "items_upload_file",
    "questionnaire_import_file",
}


def _cancel_pending_ai_requests(session_state: MutableMapping) -> None:
    """取消仍在运行的问卷/实验请求，避免旧结果和成本泄漏到新研究。"""
    request_types = {
        "_q_design_pending": "questionnaire",
        "_exp_design_pending": "experiment",
    }
    for key, request_type in request_types.items():
        pending = session_state.get(key)
        if not isinstance(pending, dict):
            continue
        cancel_id = pending.get("cancel_id")
        if cancel_id is not None:
            try:
                if request_type == "questionnaire":
                    from src.questionnaire.llm_engine import cancel_design_request
                else:
                    from src.experiment_design import cancel_design_request
                cancel_design_request(cancel_id)
            except Exception:
                pass
        future = pending.get("future")
        if future is not None:
            try:
                future.cancel()
            except Exception:
                pass


def clear_research_session(session_state: MutableMapping) -> set[str]:
    """清空当前研究资产并恢复核心默认值，返回被清理的 key 集合。"""
    _cancel_pending_ai_requests(session_state)
    cleared = {key for key in RESEARCH_SESSION_KEYS if key in session_state}
    for key in RESEARCH_SESSION_KEYS:
        session_state.pop(key, None)
    for key, value in SESSION_DEFAULTS.items():
        session_state[key] = value.copy() if isinstance(value, (dict, list)) else value
    session_state["_pending_widget_resets"] = sorted(RESEARCH_WIDGET_KEYS)
    return cleared
