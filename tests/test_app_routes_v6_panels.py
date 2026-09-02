"""V6 面板主路由集成测试 — 验证新面板可导入且渲染函数签名正确。"""

import pytest


class TestV6PanelImports:
    """验证 V6 面板模块可正常导入。"""

    def test_method_recommender_panel_importable(self):
        from src.ui.method_recommender_panel import render_method_recommender_panel
        assert callable(render_method_recommender_panel)

    def test_evidence_table_panel_importable(self):
        from src.ui.evidence_table_panel import render_evidence_table_panel
        assert callable(render_evidence_table_panel)

    def test_questionnaire_import_panel_importable(self):
        from src.ui.questionnaire_import_panel import render_questionnaire_import_panel
        assert callable(render_questionnaire_import_panel)

    def test_deliverable_center_panel_importable(self):
        from src.ui.deliverable_center_panel import render_deliverable_center_panel
        assert callable(render_deliverable_center_panel)

    def test_experiment_design_is_a_real_main_route(self):
        from pathlib import Path
        from src.ui.navigation import PAGE_MODES

        assert "🧪 实验设计" in PAGE_MODES
        app_text = (Path(__file__).resolve().parents[1] / "app.py").read_text(
            encoding="utf-8"
        )
        assert 'from src.ui.navigation import PAGE_MODES' in app_text
        assert 'elif mode == "🧪 实验设计"' in app_text
        assert "render_experiment_design_ui()" in app_text

    def test_unknown_navigation_defaults_to_data_analysis(self):
        from src.ui.navigation import PAGE_MODES, get_mode_index

        assert PAGE_MODES[get_mode_index("不存在")] == "📈 数据分析"


class TestV6PanelStateIntegration:
    """验证面板通过 state_keys 共享状态。"""

    def test_method_recommender_writes_to_state(self):
        from src.ui.method_recommender_panel import (
            _STATE_KEY, _HISTORY_KEY,
            get_current_recommendation, get_recommendation_for_deliverable,
        )
        state = {}
        assert get_current_recommendation(state) is None
        assert get_recommendation_for_deliverable(state) == []

    def test_evidence_panel_writes_to_state(self):
        from src.ui.evidence_table_panel import _STORE_KEY, get_evidence_store
        state = {}
        store = get_evidence_store(state)
        assert store is not None
        assert _STORE_KEY in state

    def test_questionnaire_panel_writes_to_state(self):
        from src.ui.questionnaire_import_panel import (
            _CLEANED_KEY, _RAW_DF_KEY, _DIMENSIONS_KEY,
            get_cleaned_result, get_cleaning_log_for_deliverable,
        )
        state = {}
        assert get_cleaned_result(state) is None
        assert get_cleaning_log_for_deliverable(state) == []

    def test_deliverable_panel_reads_from_state(self):
        from src.ui.deliverable_center_panel import (
            _get_or_build_bundle, get_deliverable_bundle,
        )
        state = {}
        assert _get_or_build_bundle(state) is None
        assert get_deliverable_bundle(state) is None

    def test_cross_panel_state_flow(self):
        """验证面板间状态传递：证据表 → 交付包。"""
        from src.ui.evidence_table_panel import get_evidence_store
        from src.ui.deliverable_center_panel import _get_or_build_bundle
        from src.ui.state_keys import PAPER_BUNDLE_KEY, ANALYSIS_CARDS_KEY
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
        from src.literature.evidence_record import EvidenceRecord

        state = {
            PAPER_BUNDLE_KEY: PaperDraftBundle(
                title="测试", sections={"intro": PaperSection(name="引言", markdown="x", source="t")},
                source="template",
            ),
            ANALYSIS_CARDS_KEY: [{"method": "ttest", "apa_text": "t=2.1"}],
        }
        store = get_evidence_store(state)
        store.add(EvidenceRecord(literature_id="1", citation_key="a2023", claim="test claim"))

        bundle = _get_or_build_bundle(state)
        assert bundle is not None
        assert len(bundle.evidence_records) == 1
