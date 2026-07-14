"""项目健康检查测试。"""
from dataclasses import dataclass, field

import pytest

from src.utils.project_health import (
    ProjectHealthIssue,
    run_health_checks,
    has_blocking_issues,
    issues_summary,
)


class _MockBundle:
    def __init__(self, warnings=None, sections=None):
        self.warnings = warnings or []
        self.sections = sections or {}


class TestRunHealthChecks:
    def test_no_data_is_error(self):
        issues = run_health_checks(has_data=False)
        assert any(i.code == "NO_DATA" and i.level == "ERROR" for i in issues)

    def test_with_data_no_error(self):
        issues = run_health_checks(has_data=True, variable_types_set=True)
        assert not any(i.code == "NO_DATA" for i in issues)

    def test_variable_types_missing_is_warn(self):
        issues = run_health_checks(has_data=True, variable_types_set=False)
        assert any(i.code == "VAR_TYPES_MISSING" and i.level == "WARN" for i in issues)

    def test_literature_pending_is_info(self):
        issues = run_health_checks(has_data=True, variable_types_set=True,
                                   literature_pending_count=5)
        assert any(i.code == "LITERATURE_PENDING" and i.level == "INFO" for i in issues)

    def test_literature_insufficient_is_warn(self):
        issues = run_health_checks(has_data=True, variable_types_set=True,
                                   literature_approved_count=1)
        assert any(i.code == "LITERATURE_INSUFFICIENT" for i in issues)

    def test_bundle_warnings_propagated(self):
        bundle = _MockBundle(warnings=["统计量可能不一致"])
        issues = run_health_checks(has_data=True, variable_types_set=True,
                                   paper_bundle=bundle)
        assert any(i.code == "BUNDLE_WARNING" for i in issues)

    def test_result_without_analysis_is_error(self):
        bundle = _MockBundle(sections={"result": object()})
        issues = run_health_checks(has_data=True, variable_types_set=True,
                                   paper_bundle=bundle, analysis_results=[])
        assert any(i.code == "RESULT_NO_ANALYSIS" and i.level == "ERROR" for i in issues)

    def test_healthy_project(self):
        issues = run_health_checks(
            has_data=True,
            variable_types_set=True,
            literature_pending_count=0,
            literature_approved_count=10,
            analysis_results=[{"test": "ttest"}],
        )
        errors = [i for i in issues if i.level == "ERROR"]
        assert len(errors) == 0


class TestHasBlockingIssues:
    def test_error_blocks(self):
        issues = [ProjectHealthIssue(level="ERROR", code="X", title="", detail="", module="")]
        assert has_blocking_issues(issues) is True

    def test_warn_does_not_block(self):
        issues = [ProjectHealthIssue(level="WARN", code="X", title="", detail="", module="")]
        assert has_blocking_issues(issues) is False

    def test_empty_does_not_block(self):
        assert has_blocking_issues([]) is False


class TestIssuesSummary:
    def test_counts(self):
        issues = [
            ProjectHealthIssue(level="ERROR", code="A", title="", detail="", module=""),
            ProjectHealthIssue(level="WARN", code="B", title="", detail="", module=""),
            ProjectHealthIssue(level="WARN", code="C", title="", detail="", module=""),
            ProjectHealthIssue(level="INFO", code="D", title="", detail="", module=""),
        ]
        s = issues_summary(issues)
        assert s == {"ERROR": 1, "WARN": 2, "INFO": 1}
