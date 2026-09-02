"""发布门禁输出与完整模式覆盖契约。"""

from scripts import release_gate


def test_pytest_summary_ignores_trailing_docs_link():
    output = "100 passed, 2 skipped in 3.0s\n-- Docs: https://docs.pytest.org/"
    assert release_gate._pytest_summary(output) == "100 passed, 2 skipped in 3.0s"


def test_full_gate_exposes_required_system_level_contracts():
    required = {
        release_gate.check_statistics_and_evidence,
        release_gate.check_privacy_ai_integrity,
        release_gate.check_workspace_compatibility,
        release_gate.check_accessible_ui_flow,
        release_gate.check_performance_budget,
    }
    assert all(callable(check) for check in required)
