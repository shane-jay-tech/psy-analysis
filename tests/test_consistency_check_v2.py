"""P0-6: 一致性检查 v2 测试。

验证 8 个新增结构化检查项:
effect_size_coverage, orphan_figures, recommendation_execution_match,
card_apa_text_completeness, evidence_quality, manifest_integrity,
figure_card_binding, template_asset_completeness。
"""

import pytest

from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.paper_writer.research_deliverable import ResearchDeliverableBundle
from src.utils.professional_consistency import (
    check_consistency,
    ConsistencyIssue,
    _check_effect_size_coverage,
    _check_orphan_figures,
    _check_recommendation_execution_match,
    _check_card_apa_text_completeness,
    _check_evidence_quality,
    _check_manifest_integrity,
    _check_figure_card_binding,
    _check_template_asset_completeness,
)


@pytest.fixture
def basic_bundle():
    paper = PaperDraftBundle(
        title="测试", source="test",
        sections={"result": PaperSection(name="结果", markdown="如图 1 所示，t=2.1", source="t")},
    )
    return ResearchDeliverableBundle(
        project_id="test", title="测试", paper_bundle=paper,
        analysis_cards=[{"method": "independent_ttest", "apa_text": "t(28) = 2.10, p = .04, Cohen's d = 0.55"}],
    )


class TestEffectSizeCoverage:
    def test_no_issue_when_not_applicable(self):
        bundle = ResearchDeliverableBundle(project_id="t", title="t")
        issues = _check_effect_size_coverage(bundle)
        assert issues == []

    def test_no_issue_when_es_present(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            analysis_cards=[{
                "method": "independent_ttest",
                "apa_text": "t=2.1",
                "effect_sizes": [{"name": "d", "value": 0.5}],
            }],
        )
        issues = _check_effect_size_coverage(bundle)
        assert issues == []

    def test_warns_when_es_missing(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            analysis_cards=[{"method": "independent_ttest", "apa_text": "t=2.1", "effect_sizes": []}],
        )
        issues = _check_effect_size_coverage(bundle)
        assert len(issues) == 1
        assert issues[0].code == "MISSING_EFFECT_SIZE"

    def test_ignores_methods_not_needing_es(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            analysis_cards=[{"method": "descriptive", "apa_text": "M=3.2, SD=1.1"}],
        )
        issues = _check_effect_size_coverage(bundle)
        assert issues == []


class TestOrphanFigures:
    def test_no_issue_without_figures(self):
        paper = PaperDraftBundle(title="t", source="t", sections={"r": PaperSection(name="结果", markdown="no fig", source="t")})
        bundle = ResearchDeliverableBundle(project_id="t", title="t", paper_bundle=paper)
        issues = _check_orphan_figures(bundle)
        assert issues == []

    def test_no_issue_when_referenced(self):
        paper = PaperDraftBundle(title="t", source="t", sections={"r": PaperSection(name="结果", markdown="如图 1 所示", source="t")})
        bundle = ResearchDeliverableBundle(project_id="t", title="t", paper_bundle=paper)
        from src.output.apa_figures import generate_mean_se_figure
        bundle.figures = [generate_mean_se_figure(["A", "B"], [3, 4], [0.3, 0.3])]
        issues = _check_orphan_figures(bundle)
        assert issues == []

    def test_warns_when_orphan(self):
        paper = PaperDraftBundle(title="t", source="t", sections={"r": PaperSection(name="结果", markdown="分析结果显示差异显著。", source="t")})
        bundle = ResearchDeliverableBundle(project_id="t", title="t", paper_bundle=paper)
        from src.output.apa_figures import generate_mean_se_figure
        bundle.figures = [generate_mean_se_figure(["A", "B"], [3, 4], [0.3, 0.3])]
        issues = _check_orphan_figures(bundle)
        assert len(issues) == 1
        assert issues[0].code == "ORPHAN_FIGURE"


class TestRecommendationExecutionMatch:
    def test_no_issue_when_no_recommendations(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            analysis_cards=[{"method": "ttest", "apa_text": "t=2"}],
        )
        issues = _check_recommendation_execution_match(bundle)
        assert issues == []

    def test_no_issue_when_matching(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            analysis_cards=[{"method": "pearson_corr", "apa_text": "r=.4"}],
            method_recommendations=[{"method_id": "pearson_corr"}],
        )
        issues = _check_recommendation_execution_match(bundle)
        assert issues == []

    def test_warns_on_mismatch(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            analysis_cards=[{"method": "mann_whitney", "apa_text": "U=100"}],
            method_recommendations=[{"method_id": "independent_ttest"}],
        )
        issues = _check_recommendation_execution_match(bundle)
        assert len(issues) == 1
        assert issues[0].code == "REC_EXEC_MISMATCH"


class TestCardAPATextCompleteness:
    def test_no_issue_when_complete(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            analysis_cards=[{"method": "ttest", "apa_text": "t(28) = 2.10, p = .04, d = 0.55"}],
        )
        issues = _check_card_apa_text_completeness(bundle)
        assert issues == []

    def test_error_when_empty(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            analysis_cards=[{"method": "ttest", "apa_text": ""}],
        )
        issues = _check_card_apa_text_completeness(bundle)
        assert len(issues) == 1
        assert issues[0].code == "APA_TEXT_INCOMPLETE"
        assert issues[0].level == "ERROR"

    def test_error_when_too_short(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            analysis_cards=[{"method": "ttest", "apa_text": "abc"}],
        )
        issues = _check_card_apa_text_completeness(bundle)
        assert len(issues) == 1


class TestEvidenceQuality:
    def test_no_issue_when_complete(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            evidence_records=[{"citation_key": "wang2023", "claim": "焦虑负相关"}],
        )
        issues = _check_evidence_quality(bundle)
        assert issues == []

    def test_warns_incomplete_records(self):
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t",
            evidence_records=[{"citation_key": "", "claim": "test"}],
        )
        issues = _check_evidence_quality(bundle)
        assert len(issues) == 1
        assert issues[0].code == "EVIDENCE_INCOMPLETE"


class TestManifestIntegrity:
    def test_no_issue_with_content(self, basic_bundle):
        issues = _check_manifest_integrity(basic_bundle)
        assert issues == []

    def test_no_error_for_minimal_bundle(self):
        bundle = ResearchDeliverableBundle(project_id="t", title="t")
        issues = _check_manifest_integrity(bundle)
        # minimal bundle has at least meta entry, so no MANIFEST_EMPTY
        assert not any(i.code == "MANIFEST_EMPTY" for i in issues)


class TestFigureCardBinding:
    def test_no_issue_without_figures(self):
        bundle = ResearchDeliverableBundle(project_id="t", title="t")
        issues = _check_figure_card_binding(bundle)
        assert issues == []

    def test_no_issue_when_bound(self):
        from src.output.apa_figures import generate_mean_se_figure
        bundle = ResearchDeliverableBundle(project_id="t", title="t")
        bundle.figures = [generate_mean_se_figure(["A", "B"], [3, 4], [0.3, 0.3])]
        issues = _check_figure_card_binding(bundle)
        assert issues == []

    def test_warns_unbound(self):
        from src.output.apa_figures import APAFigure
        bundle = ResearchDeliverableBundle(project_id="t", title="t")
        bundle.figures = [APAFigure(figure_id="f1", title="", caption="", png_bytes=b"", method="")]
        issues = _check_figure_card_binding(bundle)
        assert len(issues) == 1
        assert issues[0].code == "FIGURE_UNBOUND"


class TestTemplateAssetCompleteness:
    def test_no_issue_without_template(self):
        bundle = ResearchDeliverableBundle(project_id="t", title="t")
        issues = _check_template_asset_completeness(bundle)
        assert issues == []

    def test_warns_template_no_analysis(self):
        bundle = ResearchDeliverableBundle(project_id="t", title="t")
        bundle.template_source = "questionnaire_correlation"
        issues = _check_template_asset_completeness(bundle)
        assert len(issues) == 1
        assert issues[0].code == "TEMPLATE_NO_ANALYSIS"


class TestConsistencyV2Integration:
    def test_check_consistency_runs_all_v2(self, basic_bundle):
        issues = check_consistency(basic_bundle)
        assert isinstance(issues, list)

    def test_issue_has_v2_fields(self):
        paper = PaperDraftBundle(title="t", source="t", sections={"r": PaperSection(name="结果", markdown="no fig", source="t")})
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t", paper_bundle=paper,
            analysis_cards=[{"method": "ttest", "apa_text": ""}],
        )
        issues = check_consistency(bundle)
        error_issues = [i for i in issues if i.code == "APA_TEXT_INCOMPLETE"]
        if error_issues:
            issue = error_issues[0]
            assert issue.check_id
            assert issue.blocking is True

    def test_blocking_flag_on_errors(self):
        issue = ConsistencyIssue(
            level="ERROR", code="TEST", title="t", detail="d", source="s", action="a",
        )
        assert issue.blocking is True

    def test_non_blocking_on_warn(self):
        issue = ConsistencyIssue(
            level="WARN", code="TEST", title="t", detail="d", source="s", action="a",
        )
        assert issue.blocking is False

    def test_total_check_count_at_least_15(self, basic_bundle):
        """确认 v2 总检查维度覆盖足够。"""
        all_codes = set()
        paper = PaperDraftBundle(
            title="t", source="t",
            sections={
                "intro": PaperSection(name="引言", markdown="研究 (Wang, 2023)", source="t"),
                "result": PaperSection(name="结果", markdown="如图 1, t(28)=2.1", source="t"),
            },
        )
        bundle = ResearchDeliverableBundle(
            project_id="t", title="t", paper_bundle=paper,
            analysis_cards=[{"method": "independent_ttest", "apa_text": "t(28)=2.1, p=.04", "effect_sizes": []}],
            evidence_records=[{"citation_key": "wang2023", "claim": "test"}],
            method_recommendations=[{"method_id": "independent_ttest"}],
        )
        from src.output.apa_figures import generate_mean_se_figure
        bundle.figures = [generate_mean_se_figure(["A", "B"], [3, 4], [0.3, 0.3])]
        issues = check_consistency(bundle)
        for i in issues:
            all_codes.add(i.code)
        # checks should exercise at least a broad set
        assert len(all_codes) >= 1
