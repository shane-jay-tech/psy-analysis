import json
from pathlib import Path

import pandas as pd
import pytest

from src.utils import archive_manager, privacy_ethics, usage_logger


def test_sensitive_text_scan_detects_each_pattern_and_masks_samples():
    text = (
        "id 11010519491231002X phone 13800138000 mail user@example.com "
        "key sk-abcdefghijklmnopqrstuvwxyz password=secret"
    )

    findings = privacy_ethics.scan_text_for_sensitive(text, source="fixture")

    assert {finding.pattern_type for finding in findings} == {
        "id_card",
        "phone",
        "email",
        "api_key",
        "password",
    }
    assert all(finding.location == "fixture" for finding in findings)
    assert all("***" in finding.masked_sample for finding in findings)
    assert sum(finding.severity == "high" for finding in findings) == 3


def test_dataframe_scan_can_limit_itself_to_column_names():
    df = pd.DataFrame(
        {
            "email_address": ["person@example.com"],
            "notes": ["call 13800138000"],
        }
    )

    names_only = privacy_ethics.scan_dataframe_for_sensitive(df, column_names_only=True)
    full = privacy_ethics.scan_dataframe_for_sensitive(df)

    assert [finding.pattern_type for finding in names_only] == ["column_name"]
    assert {finding.pattern_type for finding in full} >= {"column_name", "email", "phone"}


def test_export_pre_check_distinguishes_medium_from_high_severity():
    medium = privacy_ethics.export_pre_check("contact person@example.com")
    high = privacy_ethics.export_pre_check("contact 13800138000")

    assert medium == {
        "safe": True,
        "findings": medium["findings"],
        "high_count": 0,
        "total_count": 1,
    }
    assert high["safe"] is False
    assert high["high_count"] == high["total_count"] == 1


def test_cache_discovery_size_and_selective_clear(tmp_path):
    cache = tmp_path / "data" / "cache"
    other = tmp_path / "data" / "tmp"
    cache.mkdir(parents=True)
    other.mkdir(parents=True)
    (cache / "payload.bin").write_bytes(b"x" * 20_000)
    (other / "keep.txt").write_text("keep", encoding="utf-8")

    discovered = privacy_ethics.get_cache_dirs(str(tmp_path))
    result = privacy_ethics.clear_cache(str(tmp_path), targets=["data/cache"])

    by_path = {item["path"]: item for item in discovered}
    assert by_path["data/cache"]["size_mb"] > 0
    assert set(by_path) == {"data/cache", "data/tmp"}
    assert result == {"cleared": ["data/cache"], "errors": []}
    assert cache.is_dir() and list(cache.iterdir()) == []
    assert (other / "keep.txt").exists()


def test_cache_clear_reports_os_errors(tmp_path, monkeypatch):
    cache = tmp_path / "data" / "cache"
    cache.mkdir(parents=True)

    def fail(_path):
        raise OSError("locked")

    monkeypatch.setattr(privacy_ethics.shutil, "rmtree", fail)
    result = privacy_ethics.clear_cache(str(tmp_path))

    assert result["cleared"] == []
    assert "locked" in result["errors"][0]


@pytest.fixture
def isolated_archive(tmp_path, monkeypatch):
    root = tmp_path / "archive"
    monkeypatch.setattr(archive_manager, "ARCHIVE_ROOT", root)
    return root


def test_archive_round_trip_index_and_tag_queries(isolated_archive):
    df = pd.DataFrame({"score": [1, 2], "group": ["a", "b"]})

    saved = archive_manager.archive_analysis(
        df,
        {"test_type": "ttest", "test_name_zh": "T"},
        "# report",
        {"alpha": 0.05},
        tag="course/unsafe",
        file_name="input.csv",
    )

    archive_dir = Path(saved["path"])
    assert archive_dir.is_dir()
    assert {p.name for p in archive_dir.iterdir()} == {"data.csv", "params.json", "report.md"}
    entries = archive_manager.list_archives()
    assert len(entries) == archive_manager.get_archive_count() == 1
    assert entries[0]["archive_id"] == saved["archive_id"]
    assert archive_manager.list_archives("course/unsafe") == entries
    assert archive_manager.list_tags() == ["course/unsafe"]
    assert archive_manager.get_tag_counts() == {"course/unsafe": 1}

    loaded = archive_manager.load_archive(saved["archive_id"])
    pd.testing.assert_frame_equal(loaded["df"], df)
    assert loaded["params"]["params"] == {"alpha": 0.05}
    assert loaded["report"] == "# report"


def test_archive_without_report_and_invalid_or_missing_index(isolated_archive):
    assert archive_manager.list_archives() == []
    isolated_archive.mkdir(parents=True)
    (isolated_archive / "index.json").write_text("not json", encoding="utf-8")
    assert archive_manager.list_archives() == []
    assert archive_manager.load_archive("missing") is None

    saved = archive_manager.archive_analysis(
        pd.DataFrame({"x": [1]}), {}, "", {}, tag=""
    )
    assert not (Path(saved["path"]) / "report.md").exists()


def test_archive_index_deduplicates_and_limits_history(isolated_archive):
    for index in range(205):
        archive_manager._update_index(
            str(index),
            {
                "archive_id": str(index),
                "timestamp": f"2026-01-01T00:{index:03d}:00",
            },
        )
    archive_manager._update_index(
        "204", {"archive_id": "204", "timestamp": "9999-01-01T00:00:00"}
    )

    entries = archive_manager.list_archives()
    assert len(entries) == 200
    assert entries[0]["archive_id"] == "204"
    assert sum(entry["archive_id"] == "204" for entry in entries) == 1


def test_sanitize_tag_has_safe_fallback_and_length_limit():
    assert archive_manager._sanitize_tag("../../course name") == "coursename"
    assert len(archive_manager._sanitize_tag("a" * 100)) == 50
    assert archive_manager._sanitize_tag("../..") not in {"", ".", ".."}


@pytest.fixture
def isolated_usage_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_logger, "_LOG_DIR", tmp_path / "logs")
    usage_logger.set_enabled(True)
    yield tmp_path / "logs"
    usage_logger.set_enabled(True)


def test_usage_and_error_logging_can_be_disabled_and_summarized(isolated_usage_logs):
    usage_logger.log_event("page_visit", page="home")
    usage_logger.log_event("page_visit")
    usage_logger.log_error("export_failed", severity="warning")
    usage_logger.set_enabled(False)
    usage_logger.log_event("ignored")

    usage = usage_logger.get_usage_summary()
    errors = usage_logger.get_error_summary()

    assert usage_logger.is_enabled() is False
    assert usage["total_events"] == 2
    assert usage["events_by_type"] == {"page_visit": 2}
    assert errors["total_errors"] == 1
    assert errors["errors_by_type"] == {"export_failed": 1}


def test_usage_summaries_ignore_invalid_files(isolated_usage_logs):
    isolated_usage_logs.mkdir(parents=True)
    (isolated_usage_logs / "usage_events_20260101.jsonl").write_text("not json", encoding="utf-8")
    (isolated_usage_logs / "error_events_20260101.jsonl").write_text("{", encoding="utf-8")

    assert usage_logger.get_usage_summary(days=1)["total_events"] == 0
    assert usage_logger.get_error_summary(days=1)["total_errors"] == 0


def test_feedback_package_and_log_cleanup(isolated_usage_logs, tmp_path, monkeypatch):
    class Diagnosis:
        def to_dict(self):
            return {"status": "ok"}

    from src.utils import environment_diagnosis

    monkeypatch.setattr(environment_diagnosis, "run_full_diagnosis", lambda: Diagnosis())
    usage_logger.log_event("visit")
    usage_logger.log_error("failure")

    output = usage_logger.export_feedback_package(tmp_path / "feedback")

    assert json.loads((output / "usage_summary.json").read_text(encoding="utf-8"))["total_events"] == 1
    assert json.loads((output / "error_summary.json").read_text(encoding="utf-8"))["total_errors"] == 1
    assert json.loads((output / "environment_diagnosis.json").read_text(encoding="utf-8")) == {"status": "ok"}
    assert (output / "README.md").exists()

    usage_logger.clear_logs()
    assert list(isolated_usage_logs.glob("*.jsonl")) == []
