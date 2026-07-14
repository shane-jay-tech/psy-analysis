"""P0-7: 性能日志和缓存管理测试。"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch
from src.utils.perf_logger import (
    log_perf_event,
    read_perf_log,
    clear_perf_log,
    perf_summary,
    perf_timer,
    PERF_LOG_PATH,
)
from src.utils.cache_manager import (
    scan_cache,
    clear_category,
    clear_all_cache,
    clear_expired,
    format_size,
    CacheReport,
)


class TestPerfLogger:
    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path, monkeypatch):
        test_log = tmp_path / "perf_log.jsonl"
        monkeypatch.setattr("src.utils.perf_logger.PERF_LOG_PATH", test_log)
        monkeypatch.setattr("src.utils.perf_logger._ENABLED", True)
        self.log_path = test_log
        yield
        if test_log.exists():
            test_log.unlink()

    def test_log_event_creates_file(self):
        log_perf_event("test_event", duration_ms=100)
        assert self.log_path.exists()

    def test_log_event_jsonl_format(self):
        log_perf_event("zip_export", duration_ms=1500, project_id="demo")
        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["event"] == "zip_export"
        assert entry["duration_ms"] == 1500
        assert entry["project_id"] == "demo"
        assert "timestamp" in entry

    def test_read_perf_log(self):
        log_perf_event("a", duration_ms=10)
        log_perf_event("b", duration_ms=20)
        entries = read_perf_log()
        assert len(entries) == 2

    def test_clear_perf_log(self):
        log_perf_event("x", duration_ms=5)
        count = clear_perf_log()
        assert count >= 1
        assert not self.log_path.exists()

    def test_perf_summary(self):
        log_perf_event("export", duration_ms=100)
        log_perf_event("export", duration_ms=200)
        log_perf_event("analysis", duration_ms=50)
        summary = perf_summary()
        assert summary["total_events"] == 3
        assert summary["by_event"]["export"]["count"] == 2
        assert summary["by_event"]["export"]["avg_ms"] == 150

    def test_perf_timer_context(self):
        with perf_timer("test_op", project="demo"):
            time.sleep(0.01)
        entries = read_perf_log()
        assert len(entries) == 1
        assert entries[0]["event"] == "test_op"
        assert entries[0]["duration_ms"] >= 10

    def test_perf_timer_error(self):
        with pytest.raises(ValueError):
            with perf_timer("failing_op"):
                raise ValueError("test error")
        entries = read_perf_log()
        assert entries[0]["status"] == "error"
        assert entries[0]["error_type"] == "ValueError"


class TestCacheManager:
    def test_scan_empty_cache(self):
        report = scan_cache()
        assert isinstance(report, CacheReport)

    def test_format_size_bytes(self):
        assert format_size(500) == "500 B"

    def test_format_size_kb(self):
        assert "KB" in format_size(2048)

    def test_format_size_mb(self):
        assert "MB" in format_size(2 * 1024 * 1024)

    def test_clear_nonexistent_category(self):
        count = clear_category("nonexistent_category")
        assert count == 0

    def test_clear_expired_no_crash(self):
        count = clear_expired(max_age_hours=0)
        assert isinstance(count, int)
