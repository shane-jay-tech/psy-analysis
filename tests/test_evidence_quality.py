"""P0-4: 证据质量分层与引用审计测试。"""

import pytest
from src.utils.evidence_quality import (
    grade_evidence,
    audit_citations,
    generate_quality_report,
    EvidenceGrade,
    CitationAuditIssue,
    EvidenceQualityReport,
)


class TestGradeEvidence:
    def test_empty_records(self):
        assert grade_evidence([]) == []

    def test_missing_citation_key(self):
        grades = grade_evidence([{"claim": "test"}])
        assert grades[0].grade == "Missing"

    def test_high_quality_record(self):
        rec = {
            "citation_key": "wang2023",
            "claim": "焦虑与自尊呈显著负相关，r = -.45",
            "source_type": "journal",
            "year": 2023,
        }
        grades = grade_evidence([rec])
        assert grades[0].grade in ("A", "B")

    def test_low_quality_record(self):
        rec = {
            "citation_key": "unknown1990",
            "claim": "",
            "source_type": "webpage",
            "year": 1990,
        }
        grades = grade_evidence([rec])
        assert grades[0].grade in ("C", "D")

    def test_grade_dimensions_populated(self):
        rec = {"citation_key": "li2024", "claim": "大学生抑郁检出率约20%", "year": 2024}
        grades = grade_evidence([rec])
        assert "source" in grades[0].dimensions
        assert "recency" in grades[0].dimensions
        assert "relevance" in grades[0].dimensions
        assert "completeness" in grades[0].dimensions

    def test_multiple_records(self):
        recs = [
            {"citation_key": "a2023", "claim": "claim A", "source_type": "journal", "year": 2023},
            {"citation_key": "b2020", "claim": "claim B", "source_type": "thesis", "year": 2020},
        ]
        grades = grade_evidence(recs)
        assert len(grades) == 2

    def test_recent_year_boosts_grade(self):
        rec = {"citation_key": "new2025", "claim": "recent finding with good support", "source_type": "journal", "year": 2025}
        grades = grade_evidence([rec])
        assert grades[0].grade == "A"


class TestAuditCitations:
    def test_no_issues_for_empty(self):
        issues = audit_citations([], "", [])
        assert issues == []

    def test_incomplete_info_detected(self):
        records = [{"citation_key": "", "claim": "test"}]
        issues = audit_citations(records)
        assert any(i.code == "CITATION_INCOMPLETE" for i in issues)

    def test_unused_evidence_detected(self):
        records = [{"citation_key": "wang2023", "claim": "test"}]
        paper_text = "本研究探讨了焦虑问题。"
        issues = audit_citations(records, paper_text)
        assert any(i.code == "EVIDENCE_UNUSED" for i in issues)

    def test_no_unused_when_referenced(self):
        records = [{"citation_key": "wang2023", "claim": "test"}]
        paper_text = "根据 Wang (2023) 的研究..."
        issues = audit_citations(records, paper_text)
        assert not any(i.code == "EVIDENCE_UNUSED" for i in issues)

    def test_stale_reference_info(self):
        records = [{"citation_key": "old1990", "claim": "test", "year": 1990}]
        issues = audit_citations(records)
        assert any(i.code == "STALE_REFERENCE" for i in issues)

    def test_claim_no_evidence_error(self):
        paper_text = "研究表明焦虑与睡眠质量负相关。"
        issues = audit_citations([], paper_text)
        assert any(i.code == "CLAIM_NO_EVIDENCE" for i in issues)


class TestGenerateReport:
    def test_report_structure(self):
        records = [
            {"citation_key": "wang2023", "claim": "焦虑负相关", "source_type": "journal", "year": 2023},
        ]
        report = generate_quality_report(records)
        assert isinstance(report, EvidenceQualityReport)
        assert len(report.grades) == 1
        assert "total" in report.summary
        assert "grade_distribution" in report.summary

    def test_report_with_paper_text(self):
        records = [
            {"citation_key": "wang2023", "claim": "test", "year": 2023},
            {"citation_key": "", "claim": ""},
        ]
        paper_text = "根据 Wang (2023) 的发现..."
        report = generate_quality_report(records, paper_text)
        assert len(report.grades) == 2
        assert report.summary["total"] == 2

    def test_empty_report(self):
        report = generate_quality_report([])
        assert report.summary["total"] == 0
        assert report.audit_issues == []
