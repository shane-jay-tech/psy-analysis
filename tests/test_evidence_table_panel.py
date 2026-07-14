"""证据表 UI 面板测试。"""

import pytest

from src.literature.evidence_record import EvidenceRecord, EvidenceStore
from src.ui.evidence_table_panel import (
    _STORE_KEY,
    _SECTION_OPTIONS,
    _SECTION_LABELS,
    _get_store,
    get_evidence_store,
)


@pytest.fixture
def session_state():
    return {}


class TestEvidenceStoreState:
    def test_get_store_creates_if_missing(self, session_state):
        store = _get_store(session_state)
        assert isinstance(store, EvidenceStore)
        assert _STORE_KEY in session_state

    def test_get_store_reuses_existing(self, session_state):
        existing = EvidenceStore()
        existing.add(EvidenceRecord(literature_id="1", citation_key="x", claim="test"))
        session_state[_STORE_KEY] = existing
        store = _get_store(session_state)
        assert len(store.records) == 1

    def test_get_evidence_store_public(self, session_state):
        store = get_evidence_store(session_state)
        assert isinstance(store, EvidenceStore)


class TestSectionOptions:
    def test_all_sections_have_labels(self):
        for section in _SECTION_OPTIONS:
            assert section in _SECTION_LABELS

    def test_section_labels_in_chinese(self):
        assert _SECTION_LABELS["introduction"] == "引言"
        assert _SECTION_LABELS["discussion"] == "讨论"


class TestEvidenceWorkflow:
    def test_add_evidence_to_store(self, session_state):
        store = _get_store(session_state)
        record = EvidenceRecord(
            literature_id="lit_001",
            citation_key="wang2023",
            claim="焦虑与倦怠正相关",
            section_target="introduction",
            tags=["焦虑"],
        )
        store.add(record)
        assert len(store.records) == 1

    def test_coverage_check_from_panel(self, session_state):
        store = _get_store(session_state)
        store.add(EvidenceRecord(literature_id="1", citation_key="a", claim="claim a"))
        store.add(EvidenceRecord(literature_id="2", citation_key="b", claim="claim b"))
        result = store.check_citation_coverage(["a", "b", "c"])
        assert result["coverage_rate"] == pytest.approx(2 / 3)
        assert "c" in result["missing"]

    def test_evidence_export_markdown(self, session_state):
        store = _get_store(session_state)
        store.add(EvidenceRecord(
            literature_id="1", citation_key="test",
            claim="test claim", section_target="method"
        ))
        md = store.to_markdown()
        assert "test" in md
        assert "方法" in md

    def test_evidence_export_csv(self, session_state):
        store = _get_store(session_state)
        store.add(EvidenceRecord(literature_id="1", citation_key="k", claim="c"))
        csv = store.to_csv()
        assert "citation_key" in csv
        assert "k" in csv

    def test_bibtex_import_creates_records(self, session_state):
        from src.literature.bibtex_ris_io import parse_bibtex
        store = _get_store(session_state)
        bibtex = """@article{test2024,
  title = {Test Article},
  author = {Author, A},
  year = {2024},
}
"""
        entries = parse_bibtex(bibtex)
        for e in entries:
            store.add(EvidenceRecord(
                literature_id=f"imported_{e.citation_key}",
                citation_key=e.citation_key,
                claim=e.title,
                section_target="introduction",
            ))
        assert len(store.records) == 1
        assert store.records[0].citation_key == "test2024"

    def test_ris_import_creates_records(self, session_state):
        from src.literature.bibtex_ris_io import parse_ris
        store = _get_store(session_state)
        ris = """TY  - JOUR
ID  - wang2023
TI  - Test
AU  - Wang
PY  - 2023
ER  -
"""
        entries = parse_ris(ris)
        for e in entries:
            store.add(EvidenceRecord(
                literature_id=f"imported_{e.citation_key}",
                citation_key=e.citation_key or "wang2023",
                claim=e.title,
                section_target="introduction",
            ))
        assert len(store.records) == 1

    def test_store_persists_across_panel_calls(self, session_state):
        store1 = _get_store(session_state)
        store1.add(EvidenceRecord(literature_id="1", citation_key="x", claim="y"))
        store2 = _get_store(session_state)
        assert len(store2.records) == 1
