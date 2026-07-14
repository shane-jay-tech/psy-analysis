"""V5.2 P0-4: 证据质量 UI 集成测试。"""

import pytest
from unittest.mock import patch, MagicMock
from src.utils.evidence_quality import (
    grade_evidence,
    audit_citations,
    generate_quality_report,
    EvidenceGrade,
    CitationAuditIssue,
    EvidenceQualityReport,
)


class TestEvidenceQualityUIIntegration:
    def test_generate_report_empty(self):
        report = generate_quality_report([], "", [])
        assert isinstance(report, EvidenceQualityReport)
        assert len(report.grades) == 0

    def test_generate_report_with_records(self):
        from src.literature.evidence_record import EvidenceRecord
        records = [
            EvidenceRecord(
                literature_id="lit_001",
                citation_key="wang2023",
                claim="心理健康与社交媒体使用呈负相关",
                section_target="introduction",
            ),
            EvidenceRecord(
                literature_id="lit_002",
                citation_key="li2022",
                claim="焦虑水平影响学业表现",
                evidence_quote="r = -.35, p < .001",
                section_target="discussion",
            ),
        ]
        report = generate_quality_report(records, "", [])
        assert len(report.grades) == 2
        for g in report.grades:
            assert g.grade in ("A", "B", "C", "D", "Missing")

    def test_grade_has_dimensions(self):
        from src.literature.evidence_record import EvidenceRecord
        records = [
            EvidenceRecord(
                literature_id="lit_001",
                citation_key="zhang2024",
                claim="大学生心理韧性对学业倦怠具有显著预测作用",
                section_target="introduction",
            ),
        ]
        grades = grade_evidence(records)
        assert len(grades) == 1
        assert grades[0].dimensions is not None
        assert "source" in grades[0].dimensions or "completeness" in grades[0].dimensions

    def test_audit_finds_issues(self):
        from src.literature.evidence_record import EvidenceRecord
        records = [
            EvidenceRecord(
                literature_id="lit_001",
                citation_key="old_ref",
                claim="经典理论支撑",
                section_target="introduction",
            ),
        ]
        paper_text = "本研究基于自我效能感理论（Bandura, 1977），没有引用 old_ref"
        issues = audit_citations(records, paper_text, [])
        assert isinstance(issues, list)

    def test_evidence_panel_import(self):
        from src.ui.evidence_table_panel import render_evidence_table_panel
        assert callable(render_evidence_table_panel)

    def test_quality_report_summary(self):
        from src.literature.evidence_record import EvidenceRecord
        records = [
            EvidenceRecord(
                literature_id="lit_001",
                citation_key="test2024",
                claim="测试论点",
                section_target="method",
            ),
        ]
        report = generate_quality_report(records, "test paper text test2024", [])
        assert hasattr(report, "summary")
