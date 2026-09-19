"""scripts/analyze_usage_logs.py 纯函数特征化测试（s918-34）。

日志目录 monkeypatch 到 tmp，零真实 logs/ 读取；只钉现状不改行为。
"""
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from scripts import analyze_usage_logs as aul


def _day(offset: int) -> str:
    return (date.today() - timedelta(days=offset)).strftime("%Y%m%d")


def _write_jsonl(path: Path, rows) -> None:
    path.write_text(
        "\n".join(row if isinstance(row, str) else json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


@pytest.fixture
def logdir(tmp_path, monkeypatch):
    d = tmp_path / "logs"
    d.mkdir()
    monkeypatch.setattr(aul, "LOG_DIR", d)
    return d


def test_load_events_keeps_only_files_within_the_day_window(logdir):
    _write_jsonl(logdir / f"usage_events_{_day(1)}.jsonl", [{"event": "a"}])
    _write_jsonl(logdir / f"usage_events_{_day(9)}.jsonl", [{"event": "b"}])

    assert [e["event"] for e in aul.load_events(days=7)] == ["a"]


def test_load_events_skips_malformed_lines_and_missing_dir(logdir):
    _write_jsonl(logdir / f"usage_events_{_day(0)}.jsonl", [{"event": "ok"}, "{not json", ""])

    assert [e["event"] for e in aul.load_events(days=1)] == ["ok"]

    empty = logdir.parent / "no-such-logs"
    aul.LOG_DIR = empty
    assert aul.load_events(days=30) == []
    assert aul.load_errors(days=30) == []


def test_load_errors_uses_its_own_file_prefix(logdir):
    _write_jsonl(logdir / f"error_events_{_day(2)}.jsonl", [{"error": "Boom"}])
    _write_jsonl(logdir / f"usage_events_{_day(2)}.jsonl", [{"event": "ignored"}])

    assert [e["error"] for e in aul.load_errors(days=7)] == ["Boom"]
    assert aul.load_errors(days=1) == []


def test_analyze_without_events_renders_placeholder_only():
    report = aul.analyze([], [])

    assert "**事件总数**: 0" in report and "**错误总数**: 0" in report
    assert "暂无使用记录。" in report
    assert "## 事件类型分布" not in report


def test_analyze_renders_every_aggregation_section():
    events = [
        {"event": "analysis_execute", "method_id": "sem", "duration_ms": 120, "timestamp": "2026-09-01T10:00:00"},
        {"event": "analysis_execute", "method": "cfa", "duration_ms": 80, "timestamp": "2026-09-02T10:00:00"},
        {"event": "template_select", "template_id": "apa7", "timestamp": "2026-09-02T11:00:00"},
        {"event": "export", "format": "docx", "timestamp": "2026-09-02T12:00:00"},
    ]
    errors = [{"error": "Timeout"}, {"error": "Timeout"}, {"error": "Crash"}]

    report = aul.analyze(events, errors)

    for section in ("## 事件类型分布", "## 分析方法使用分布", "## 模板使用分布",
                    "## 导出统计", "## 分析耗时", "## 活跃度", "## 高频错误"):
        assert section in report, section
    assert "| sem | 1 |" in report
    assert "- 平均: 100ms" in report and "- 最大: 120ms" in report and "- 样本数: 2" in report
    assert "- 活跃天数: 2" in report
    assert "- 日均事件: 2.0" in report
    assert "| Timeout | 2 |" in report


def test_method_section_only_counts_analysis_execute_events():
    events = [{"event": "export", "method_id": "sem"}, {"event": "analysis_execute"}]

    report = aul.analyze(events, [])

    assert "## 分析方法使用分布" not in report
    assert "## 导出统计" in report


def test_activity_section_survives_events_without_timestamps():
    """活跃天数=0 时日均事件走 max(len,1)，不除零。"""
    report = aul.analyze([{"event": "analysis_execute", "method": "x"}], [])

    assert "- 活跃天数: 0" in report
    assert "- 日均事件: 1.0" in report


def test_missing_fields_fall_back_to_unknown():
    report = aul.analyze([{"event": "export"}], [{"no_error_key": 1}])

    assert "| export | 1 |" in report
    assert "- unknown: 1 次" in report
    assert "| unknown | 1 |" in report
