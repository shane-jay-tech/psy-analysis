"""研究交付包导出中心测试。"""

import json
import pytest

from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.paper_writer.research_deliverable import ResearchDeliverableBundle
from src.ui.deliverable_center_panel import (
    _BUNDLE_KEY,
    EXPORT_MODES,
    EXPORT_MODE_CONTENTS,
    _get_or_build_bundle,
    _generate_export_content,
    get_deliverable_bundle,
    _render_export,
)
from src.ui.state_keys import PAPER_BUNDLE_KEY, ANALYSIS_CARDS_KEY


@pytest.fixture
def paper_bundle():
    return PaperDraftBundle(
        title="焦虑与自尊",
        sections={
            "introduction": PaperSection(name="引言", markdown="背景...", source="template"),
            "result": PaperSection(name="结果", markdown="r=-0.42", source="data"),
        },
        source="template",
    )


@pytest.fixture
def session_state(paper_bundle):
    return {
        PAPER_BUNDLE_KEY: paper_bundle,
        ANALYSIS_CARDS_KEY: [{"method": "pearson_corr", "apa_text": "r=-0.42, p<.001"}],
        "project_id": "test_proj",
    }


class TestBundleAssembly:
    def test_builds_from_session_state(self, session_state):
        bundle = _get_or_build_bundle(session_state)
        assert bundle is not None
        assert bundle.title == "焦虑与自尊"
        assert bundle.project_id == "test_proj"
        assert len(bundle.analysis_cards) == 1

    def test_returns_none_when_empty(self):
        bundle = _get_or_build_bundle({})
        assert bundle is None

    def test_includes_evidence_if_present(self, session_state):
        from src.literature.evidence_record import EvidenceRecord, EvidenceStore
        store = EvidenceStore()
        store.add(EvidenceRecord(literature_id="1", citation_key="x", claim="test"))
        session_state["evidence_store"] = store
        bundle = _get_or_build_bundle(session_state)
        assert len(bundle.evidence_records) == 1

    def test_includes_cleaning_log_if_present(self, session_state):
        from src.questionnaire.import_cleaning import CleaningLogEntry
        from dataclasses import dataclass, field

        @dataclass
        class FakeResult:
            log: list = field(default_factory=list)
        fake = FakeResult(log=[CleaningLogEntry(step="test", action="cleaned")])
        session_state["questionnaire_cleaned_result"] = fake
        bundle = _get_or_build_bundle(session_state)
        assert len(bundle.data_cleaning_log) == 1


class TestExportModes:
    def test_three_modes_exist(self):
        assert len(EXPORT_MODES) == 3
        assert "简版" in EXPORT_MODES
        assert "标准版" in EXPORT_MODES
        assert "完整版" in EXPORT_MODES

    def test_basic_has_minimal_content(self):
        assert "论文正文" in EXPORT_MODE_CONTENTS["basic"]
        assert "参考文献" in EXPORT_MODE_CONTENTS["basic"]
        assert len(EXPORT_MODE_CONTENTS["basic"]) == 2

    def test_full_has_all_content(self):
        assert len(EXPORT_MODE_CONTENTS["full"]) >= 8
        assert "AI差异记录" in EXPORT_MODE_CONTENTS["full"]


class TestExportContent:
    def test_basic_mode_output(self, session_state):
        bundle = _get_or_build_bundle(session_state)
        content = _generate_export_content(bundle, "basic")
        assert "焦虑与自尊" in content
        assert "引言" in content
        assert "背景" in content

    def test_standard_mode_includes_cards(self, session_state):
        bundle = _get_or_build_bundle(session_state)
        content = _generate_export_content(bundle, "standard")
        assert "统计结果卡" in content
        assert "pearson_corr" in content

    def test_full_mode_includes_health(self, session_state):
        bundle = _get_or_build_bundle(session_state)
        bundle.health_report = [{"level": "WARN", "message": "文献少"}]
        bundle.ai_diff_log = {"introduction": "revised"}
        content = _generate_export_content(bundle, "full")
        assert "健康报告" in content
        assert "AI 差异" in content

    def test_exportability_check(self, session_state):
        bundle = _get_or_build_bundle(session_state)
        exportable, reasons = bundle.is_exportable()
        assert exportable is True

    def test_not_exportable_without_paper(self):
        bundle = ResearchDeliverableBundle(analysis_cards=[{"m": "t"}])
        exportable, reasons = bundle.is_exportable()
        assert exportable is False


class TestDeliverableState:
    def test_get_deliverable_bundle_none(self):
        assert get_deliverable_bundle({}) is None

    def test_get_deliverable_bundle_after_set(self, session_state):
        bundle = _get_or_build_bundle(session_state)
        session_state[_BUNDLE_KEY] = bundle
        assert get_deliverable_bundle(session_state) is bundle


def test_render_export_stops_before_download_when_gate_blocks(session_state, monkeypatch):
    from unittest.mock import patch

    bundle = _get_or_build_bundle(session_state)
    monkeypatch.setattr(
        "src.ui.deliverable_center_panel.run_export_gate",
        lambda _state: (False, ["[PRIVACY_HIGH] 敏感信息"], []),
    )
    with patch("streamlit.error") as error, patch("streamlit.download_button") as download:
        _render_export(bundle, session_state)
    error.assert_called_once()
    download.assert_not_called()
