"""P0-3: 专业一致性检查测试。

验证 7 类一致性检查能正确发现问题。
"""

import pytest

from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.paper_writer.research_deliverable import ResearchDeliverableBundle
from src.utils.professional_consistency import (
    ConsistencyIssue,
    check_consistency,
    _check_result_card_binding,
    _check_stat_consistency,
    _check_citation_refs,
    _check_evidence_coverage,
    _check_figure_refs,
    _check_method_match,
    _check_variable_naming,
)


def _make_bundle(**kwargs):
    defaults = {
        "project_id": "test",
        "title": "测试项目",
    }
    defaults.update(kwargs)
    return ResearchDeliverableBundle(**defaults)


def _make_paper(sections_dict):
    secs = {k: PaperSection(name=v[0], markdown=v[1], source="t")
            for k, v in sections_dict.items()}
    return PaperDraftBundle(title="测试论文", sections=secs, source="test")


class TestResultCardBinding:
    def test_result_section_without_cards_is_error(self):
        paper = _make_paper({"result": ("结果", "t(28)=2.1, p<.05")})
        bundle = _make_bundle(paper_bundle=paper, analysis_cards=[])
        issues = _check_result_card_binding(bundle)
        assert any(i.code == "RESULT_NO_CARD" for i in issues)

    def test_result_section_with_cards_ok(self):
        paper = _make_paper({"result": ("结果", "t(28)=2.1")})
        bundle = _make_bundle(
            paper_bundle=paper,
            analysis_cards=[{"method": "ttest", "apa_text": "t(28)=2.1"}],
        )
        issues = _check_result_card_binding(bundle)
        assert not issues

    def test_no_result_section_ok(self):
        paper = _make_paper({"intro": ("引言", "背景介绍")})
        bundle = _make_bundle(paper_bundle=paper, analysis_cards=[])
        issues = _check_result_card_binding(bundle)
        assert not issues


class TestStatConsistency:
    def test_stats_in_paper_without_cards_is_error(self):
        paper = _make_paper({"result": ("结果", "r = 0.45, p < .01")})
        bundle = _make_bundle(paper_bundle=paper, analysis_cards=[])
        issues = _check_stat_consistency(bundle)
        assert any(i.code == "STAT_NO_SOURCE" for i in issues)

    def test_stats_with_matching_cards_ok(self):
        paper = _make_paper({"result": ("结果", "r = 0.45")})
        bundle = _make_bundle(
            paper_bundle=paper,
            analysis_cards=[{"method": "pearson", "apa_text": "r = .45, p = .003"}],
        )
        issues = _check_stat_consistency(bundle)
        assert not issues

    def test_no_stats_in_paper_ok(self):
        paper = _make_paper({"intro": ("引言", "本研究探讨焦虑与自尊的关系")})
        bundle = _make_bundle(paper_bundle=paper, analysis_cards=[])
        issues = _check_stat_consistency(bundle)
        assert not issues


class TestCitationRefs:
    def test_citation_not_in_evidence_is_error(self):
        paper = _make_paper({"intro": ("引言", "焦虑与自尊负相关 (Wang, 2023)")})
        bundle = _make_bundle(
            paper_bundle=paper,
            evidence_records=[{"citation_key": "li2022", "claim": "something"}],
        )
        issues = _check_citation_refs(bundle)
        assert any(i.code == "CITATION_MISSING" for i in issues)

    def test_citation_in_evidence_ok(self):
        paper = _make_paper({"intro": ("引言", "根据 (Wang, 2023) 的研究")})
        bundle = _make_bundle(
            paper_bundle=paper,
            evidence_records=[{"citation_key": "wang2023", "claim": "焦虑负相关"}],
        )
        issues = _check_citation_refs(bundle)
        assert not issues

    def test_no_citations_ok(self):
        paper = _make_paper({"intro": ("引言", "本研究的背景")})
        bundle = _make_bundle(paper_bundle=paper, evidence_records=[])
        issues = _check_citation_refs(bundle)
        assert not issues


class TestEvidenceCoverage:
    def test_intro_without_evidence_is_warning(self):
        paper = _make_paper({"intro": ("引言", "研究背景")})
        bundle = _make_bundle(paper_bundle=paper, evidence_records=[])
        issues = _check_evidence_coverage(bundle)
        assert any(i.code == "NO_EVIDENCE" for i in issues)

    def test_intro_with_evidence_ok(self):
        paper = _make_paper({"intro": ("引言", "背景")})
        bundle = _make_bundle(
            paper_bundle=paper,
            evidence_records=[{"citation_key": "a2023", "claim": "x"}],
        )
        issues = _check_evidence_coverage(bundle)
        assert not issues


class TestFigureRefs:
    def test_figure_ref_without_figure_is_error(self):
        paper = _make_paper({"result": ("结果", "如图 3 所示")})
        bundle = _make_bundle(paper_bundle=paper, figures=[])
        issues = _check_figure_refs(bundle)
        assert any(i.code == "FIGURE_MISSING" for i in issues)

    def test_figure_ref_with_figures_ok(self):
        from src.output.apa_figures import APAFigure
        fig = APAFigure(figure_id="f1", title="t", caption="c", png_bytes=b"x", method="t")
        paper = _make_paper({"result": ("结果", "如图 1 所示")})
        bundle = _make_bundle(paper_bundle=paper, figures=[fig])
        issues = _check_figure_refs(bundle)
        assert not issues

    def test_no_figure_refs_ok(self):
        paper = _make_paper({"result": ("结果", "结果显著")})
        bundle = _make_bundle(paper_bundle=paper, figures=[])
        issues = _check_figure_refs(bundle)
        assert not issues


class TestMethodMatch:
    def test_different_method_is_warning(self):
        bundle = _make_bundle(
            analysis_cards=[{"method": "pearson_corr", "method_zh": "Pearson 相关"}],
            method_recommendations=[{"recommendation": "独立样本 t 检验"}],
        )
        issues = _check_method_match(bundle)
        assert any(i.code == "METHOD_MISMATCH" for i in issues)

    def test_same_method_ok(self):
        bundle = _make_bundle(
            analysis_cards=[{"method": "pearson_corr", "method_zh": "Pearson 相关"}],
            method_recommendations=[{"recommendation": "Pearson 相关"}],
        )
        issues = _check_method_match(bundle)
        assert not issues

    def test_no_recommendations_ok(self):
        bundle = _make_bundle(
            analysis_cards=[{"method": "ttest"}],
            method_recommendations=[],
        )
        issues = _check_method_match(bundle)
        assert not issues


class TestVariableNaming:
    def test_inconsistent_names_is_warning(self):
        paper = _make_paper({"result": ("结果", "焦虑水平显著下降")})
        bundle = _make_bundle(
            paper_bundle=paper,
            analysis_cards=[{
                "method": "ttest",
                "apa_text": "焦虑得分、自尊得分、孤独得分差异显著",
            }],
        )
        issues = _check_variable_naming(bundle)
        assert any(i.code == "VAR_NAME_INCONSISTENT" for i in issues)

    def test_consistent_names_ok(self):
        paper = _make_paper({"result": ("结果", "焦虑得分显著下降")})
        bundle = _make_bundle(
            paper_bundle=paper,
            analysis_cards=[{"method": "t", "apa_text": "焦虑得分差异显著"}],
        )
        issues = _check_variable_naming(bundle)
        assert not issues


class TestFullCheck:
    def test_clean_bundle_no_issues(self):
        paper = _make_paper({
            "intro": ("引言", "研究背景"),
            "result": ("结果", "结果显著"),
        })
        bundle = _make_bundle(
            paper_bundle=paper,
            analysis_cards=[{"method": "ttest", "apa_text": "t(28) = 2.10, p = .04, d = 0.55"}],
            evidence_records=[{"citation_key": "a2023", "claim": "c"}],
        )
        issues = check_consistency(bundle)
        errors = [i for i in issues if i.level == "ERROR"]
        assert not errors

    def test_empty_bundle_minimal_issues(self):
        bundle = _make_bundle()
        issues = check_consistency(bundle)
        assert isinstance(issues, list)

    def test_issue_dataclass_fields(self):
        issue = ConsistencyIssue(
            level="ERROR", code="TEST", title="t", detail="d", source="s", action="a"
        )
        assert issue.level == "ERROR"
        assert issue.code == "TEST"
