"""P0-3: 论文就绪度评分测试。"""

import pytest
import pandas as pd
from src.utils.readiness_scorer import compute_readiness, ReadinessReport, ReadinessItem


class TestReadinessEmpty:
    def test_empty_session_returns_report(self):
        report = compute_readiness({})
        assert isinstance(report, ReadinessReport)
        assert report.total_score < 10
        assert report.grade == "未就绪"

    def test_empty_has_8_dimensions(self):
        report = compute_readiness({})
        assert len(report.items) == 8

    def test_next_step_not_empty(self):
        report = compute_readiness({})
        assert report.next_step != ""


class TestReadinessDataHealth:
    def test_no_data_scores_zero(self):
        report = compute_readiness({})
        data_item = next(i for i in report.items if i.dimension == "数据健康")
        assert data_item.score == 0
        assert data_item.status == "missing"

    def test_small_sample_warns(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
        report = compute_readiness({"uploaded_df": df})
        data_item = next(i for i in report.items if i.dimension == "数据健康")
        assert data_item.status == "warning"

    def test_good_data_scores_high(self):
        df = pd.DataFrame({"x": range(50), "y": range(50)})
        report = compute_readiness({"uploaded_df": df})
        data_item = next(i for i in report.items if i.dimension == "数据健康")
        assert data_item.score == 100
        assert data_item.status == "good"


class TestReadinessMethodMatch:
    def test_no_recs_no_cards(self):
        report = compute_readiness({})
        item = next(i for i in report.items if i.dimension == "方法匹配")
        assert item.score == 0

    def test_recs_without_cards_partial(self):
        report = compute_readiness({
            "method_recommendations": [{"method_id": "ttest"}],
            "analysis_cards": [],
        })
        item = next(i for i in report.items if i.dimension == "方法匹配")
        assert item.status == "warning"
        assert item.score == 40

    def test_recs_with_cards_full(self):
        report = compute_readiness({
            "method_recommendations": [{"method_id": "ttest"}],
            "analysis_cards": [{"method": "ttest", "apa_text": "t(28) = 2.1"}],
        })
        item = next(i for i in report.items if i.dimension == "方法匹配")
        assert item.score == 100


class TestReadinessStatResults:
    def test_no_cards_zero(self):
        report = compute_readiness({})
        item = next(i for i in report.items if i.dimension == "统计结果")
        assert item.score == 0

    def test_cards_with_apa_scores_high(self):
        report = compute_readiness({
            "analysis_cards": [
                {"method": "ttest", "apa_text": "t(28) = 2.10, p = .04, d = 0.55", "effect_sizes": [{"name": "d", "value": 0.55}]},
            ]
        })
        item = next(i for i in report.items if i.dimension == "统计结果")
        assert item.score == 100


class TestReadinessGrades:
    def test_full_project_high_score(self):
        ss = {
            "uploaded_df": pd.DataFrame({"x": range(50), "y": range(50)}),
            "method_recommendations": [{"method_id": "ttest"}],
            "analysis_cards": [{"method": "ttest", "apa_text": "t(28) = 2.10, p = .04, d = 0.55", "effect_sizes": [{"name": "d", "value": 0.55}]}],
            "apa_figures": [{"figure_id": "f1"}],
            "evidence_records": [{"citation_key": "wang2023", "claim": "test", "quality_grade": "A"}],
            "paper_bundle": {"title": "test"},
            "consistency_issues": [],
        }
        report = compute_readiness(ss)
        assert report.total_score >= 80
        assert report.grade in ("接近完成", "可提交前检查")

    def test_blockers_cap_grade(self):
        ss = {
            "uploaded_df": pd.DataFrame({"x": range(50)}),
            "analysis_cards": [{"method": "t", "apa_text": "ok long enough text"}],
        }

        class FakeIssue:
            level = "ERROR"
        ss["consistency_issues"] = [FakeIssue()]
        report = compute_readiness(ss)
        assert "未就绪" in report.grade or len(report.blockers) > 0


class TestReadinessWeights:
    def test_weights_sum_to_one(self):
        report = compute_readiness({})
        total_weight = sum(item.weight for item in report.items)
        assert total_weight == pytest.approx(1.0, abs=0.01)


class TestReadinessReport:
    def test_report_fields(self):
        report = compute_readiness({})
        assert hasattr(report, "total_score")
        assert hasattr(report, "grade")
        assert hasattr(report, "items")
        assert hasattr(report, "blockers")
        assert hasattr(report, "high_priority")
        assert hasattr(report, "next_step")
