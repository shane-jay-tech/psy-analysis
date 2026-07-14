"""P0-5: 反馈日志与诊断包测试。"""

import pytest
import tempfile
from pathlib import Path
from src.utils.feedback_logger import (
    FeedbackLogger,
    FeedbackEvent,
    generate_diagnostic_package,
    clear_feedback_logs,
    _sanitize_error,
)


class TestFeedbackLogger:
    def test_create_logger(self):
        logger = FeedbackLogger(session_id="test123")
        assert logger.session_id == "test123"

    def test_auto_session_id(self):
        logger = FeedbackLogger()
        assert len(logger.session_id) == 8

    def test_log_page_visit(self):
        logger = FeedbackLogger()
        logger.log_page_visit("数据分析")
        assert len(logger._events) == 1
        assert logger._events[0].event_type == "page_visit"
        assert logger._events[0].page == "数据分析"

    def test_log_action(self):
        logger = FeedbackLogger()
        logger.log_action("分析", "run_ttest", method="independent")
        assert logger._events[0].action == "run_ttest"
        assert logger._events[0].metadata["method"] == "independent"

    def test_log_error(self):
        logger = FeedbackLogger()
        logger.log_error("分析", "ValueError", "column 'x' not found")
        assert logger._events[0].error_type == "ValueError"

    def test_log_export(self):
        logger = FeedbackLogger()
        logger.log_export("word", True, duration_ms=1500)
        assert logger._events[0].metadata["success"] is True
        assert logger._events[0].duration_ms == 1500

    def test_save_session(self, tmp_path):
        logger = FeedbackLogger(session_id="save_test", log_dir=tmp_path)
        logger.log_page_visit("模板中心")
        logger.log_action("模板中心", "create_project")
        path = logger.save_session()
        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_get_session_summary(self):
        logger = FeedbackLogger()
        logger.log_page_visit("数据分析")
        logger.log_error("数据分析", "Error")
        logger.log_export("zip", True)
        summary = logger.get_session_summary()
        assert summary["total_events"] == 3
        assert summary["error_count"] == 1
        assert summary["export_count"] == 1
        assert summary["export_success"] == 1


class TestDiagnosticPackage:
    def test_empty_session(self):
        pkg = generate_diagnostic_package({})
        assert pkg["version"] == "5.1"
        assert pkg["system_state"]["has_data"] is False

    def test_with_data(self):
        import pandas as pd
        ss = {
            "uploaded_df": pd.DataFrame({"x": [1, 2, 3]}),
            "analysis_cards": [{"method": "t"}],
            "evidence_records": [{"key": "a"}],
        }
        pkg = generate_diagnostic_package(ss)
        assert pkg["system_state"]["has_data"] is True
        assert pkg["system_state"]["data_shape"] == [3, 1]
        assert pkg["system_state"]["n_analysis_cards"] == 1

    def test_with_logger(self):
        logger = FeedbackLogger(session_id="diag")
        logger.log_page_visit("test")
        pkg = generate_diagnostic_package({}, feedback_logger=logger)
        assert pkg["session_summary"]["total_events"] == 1

    def test_anonymizes_template(self):
        ss = {"template_source": "my_secret_template"}
        pkg = generate_diagnostic_package(ss)
        assert "my_secret_template" not in str(pkg)


class TestSanitizeError:
    def test_removes_windows_paths(self):
        msg = "File not found: C:\\Users\\john\\data\\file.csv"
        result = _sanitize_error(msg)
        assert "john" not in result
        assert "<path>" in result

    def test_removes_emails(self):
        msg = "Contact user@example.com for help"
        result = _sanitize_error(msg)
        assert "user@example.com" not in result

    def test_removes_phone(self):
        msg = "Call 13812345678 for support"
        result = _sanitize_error(msg)
        assert "13812345678" not in result

    def test_truncates_long_messages(self):
        msg = "x" * 1000
        result = _sanitize_error(msg)
        assert len(result) <= 500


class TestClearLogs:
    def test_clear_nonexistent_dir(self, tmp_path):
        count = clear_feedback_logs(tmp_path / "nonexist")
        assert count == 0

    def test_clear_existing_logs(self, tmp_path):
        (tmp_path / "session_a.jsonl").write_text("{}")
        (tmp_path / "session_b.jsonl").write_text("{}")
        count = clear_feedback_logs(tmp_path)
        assert count == 2
        assert not list(tmp_path.glob("*.jsonl"))
