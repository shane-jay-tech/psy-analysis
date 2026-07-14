"""交付包资产完整度检查测试。"""

import pytest

from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
from src.paper_writer.research_deliverable import ResearchDeliverableBundle
from src.ui.deliverable_center_panel import _check_asset_completeness


@pytest.fixture
def full_bundle():
    paper = PaperDraftBundle(
        title="完整项目",
        sections={"intro": PaperSection(name="引言", markdown="x", source="t")},
        source="template",
    )
    return ResearchDeliverableBundle(
        project_id="full",
        title="完整项目",
        paper_bundle=paper,
        analysis_cards=[{"method": "ttest", "apa_text": "t=2.1"}],
        evidence_records=[
            {"citation_key": "a2023", "claim": "c1"},
            {"citation_key": "b2023", "claim": "c2"},
            {"citation_key": "c2023", "claim": "c3"},
        ],
        data_cleaning_log=[{"step": "列分类", "action": "done"}],
        method_recommendations=[{"recommendation": "独立样本 t 检验"}],
    )


class TestAssetCompleteness:
    def test_full_bundle_no_issues(self, full_bundle):
        errors, warnings = _check_asset_completeness(full_bundle)
        assert errors == []
        assert warnings == []

    def test_no_cards_is_error(self, full_bundle):
        full_bundle.analysis_cards = []
        errors, warnings = _check_asset_completeness(full_bundle)
        assert any("结果卡" in e for e in errors)

    def test_no_method_rec_is_warning(self, full_bundle):
        full_bundle.method_recommendations = []
        errors, warnings = _check_asset_completeness(full_bundle)
        assert any("方法推荐" in w for w in warnings)

    def test_no_evidence_is_warning(self, full_bundle):
        full_bundle.evidence_records = []
        errors, warnings = _check_asset_completeness(full_bundle)
        assert any("证据表" in w for w in warnings)

    def test_few_evidence_is_warning(self, full_bundle):
        full_bundle.evidence_records = [{"citation_key": "x", "claim": "y"}]
        errors, warnings = _check_asset_completeness(full_bundle)
        assert any("少于 3 条" in w for w in warnings)

    def test_no_cleaning_log_is_warning(self, full_bundle):
        full_bundle.data_cleaning_log = []
        errors, warnings = _check_asset_completeness(full_bundle)
        assert any("清洗日志" in w for w in warnings)

    def test_empty_bundle_has_errors(self):
        bundle = ResearchDeliverableBundle(title="空")
        errors, warnings = _check_asset_completeness(bundle)
        assert len(errors) >= 1
        assert any("结果卡" in e for e in errors)
