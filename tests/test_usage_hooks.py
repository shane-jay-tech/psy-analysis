"""src/utils/usage_hooks.py 事件桥特征化测试（s918-22）。

抽代表性钩子钉「事件名＋字段透传＋改名」，并划清异常吞掉的**真实归属层**（在 usage_logger 的
`except OSError`，不在钩子层）。`log_event`/`log_error` 一律打桩——**测试不写真实埋点文件**；
唯一触及写盘的那例也把 `_LOG_DIR` 指到 tmp。
锚点：src/utils/usage_hooks.py:12，92 行。
"""
import json

import pytest

import src.utils.usage_hooks as uh
import src.utils.usage_logger as ul


@pytest.fixture
def spy(monkeypatch):
    events, errors = [], []

    def fake_log_event(name, **kw):
        events.append((name, kw))

    def fake_log_error(name, **kw):
        errors.append((name, kw))

    monkeypatch.setattr(uh, "log_event", fake_log_event)
    monkeypatch.setattr(uh, "log_error", fake_log_error)
    return {"events": events, "errors": errors}


def test_page_visit_and_template_select_pass_their_id_through(spy):
    uh.on_page_visit("analysis")
    uh.on_template_select("apa7-table")

    assert spy["events"] == [("page_visit", {"page_id": "analysis"}),
                             ("template_select", {"template_id": "apa7-table"})]


def test_analysis_execute_carries_success_flag_and_duration(spy):
    uh.on_analysis_execute("independent_ttest", True, 1500)

    assert spy["events"] == [("analysis_execute",
                             {"method_id": "independent_ttest", "success": True, "duration_ms": 1500})]


def test_consistency_check_renames_its_counter_fields(spy):
    """形参叫 error_count/warning_count，落到事件里变成 errors/warnings——改名处易错。"""
    uh.on_consistency_check(3, 5)

    assert spy["events"] == [("consistency_check", {"errors": 3, "warnings": 5})]


def test_diagnosis_run_renames_ok_count(spy):
    uh.on_diagnosis_run(8, 2, 1)

    assert spy["events"] == [("diagnosis_run", {"ok": 8, "warnings": 2, "errors": 1})]


def test_privacy_precheck_records_only_counts_no_raw_text(spy):
    uh.on_privacy_precheck(high_count=1, medium_count=0, safe=False)

    name, fields = spy["events"][0]
    assert name == "privacy_precheck"
    assert set(fields) == {"high_count", "medium_count", "safe"}


def test_optional_template_id_is_forwarded_as_none(spy):
    uh.on_method_recommend("pearson_corr")

    assert spy["events"] == [("method_recommend",
                             {"recommended_method": "pearson_corr", "template_id": None})]


def test_error_display_goes_to_log_error_not_log_event(spy):
    uh.on_error_display("ValueError", "high")

    assert spy["events"] == []
    assert spy["errors"] == [("ValueError", {"severity": "high"})]


def test_hooks_do_not_swallow_exceptions_themselves(spy, monkeypatch):
    """吞异常发生在 usage_logger 的 `except OSError`，钩子层是裸调用。"""
    def boom(name, **kw):
        raise ValueError("bad event")

    monkeypatch.setattr(uh, "log_event", boom)

    with pytest.raises(ValueError, match="bad event"):
        uh.on_export("docx", True, 120)


def test_analysis_timer_reports_success_and_elapsed(spy, monkeypatch):
    ticks = iter([1_000.0, 1_000.25])
    monkeypatch.setattr(uh.time, "time", lambda: next(ticks))

    with uh.AnalysisTimer("sem") as timer:
        assert timer.method_id == "sem"

    assert spy["events"] == [("analysis_execute",
                             {"method_id": "sem", "success": True, "duration_ms": 250})]


def test_analysis_timer_reports_failure_and_still_propagates(spy):
    with pytest.raises(RuntimeError):
        with uh.AnalysisTimer("hlm"):
            raise RuntimeError("model singular")

    name, fields = spy["events"][0]
    assert (name, fields["method_id"], fields["success"]) == ("analysis_execute", "hlm", False)
    assert fields["duration_ms"] >= 0


def test_logger_swallows_only_the_write_failure(monkeypatch, tmp_path):
    """`except OSError` 只包住 open/write；埋点写盘失败静默丢弃。"""
    monkeypatch.setattr(ul, "_ENABLED", True)
    monkeypatch.setattr(ul, "_ensure_log_dir", lambda: None)

    def boom(*a, **k):
        raise OSError("disk gone")

    monkeypatch.setattr(ul, "open", boom, raising=False)

    ul.log_event("page_visit", page_id="x")  # 不抛


def test_dir_creation_failure_escapes_the_try_block(monkeypatch):
    """`_ensure_log_dir()` 在 try 之外被调用 ⇒ 目录建不出来时异常会**抛进 UI 主路径**，
    而不是像写盘那样静默。钉住这个可用性缺口。"""
    monkeypatch.setattr(ul, "_ENABLED", True)

    def boom():
        raise OSError("cannot create log dir")

    monkeypatch.setattr(ul, "_ensure_log_dir", boom)

    with pytest.raises(OSError, match="cannot create log dir"):
        ul.log_event("page_visit", page_id="x")


def test_kill_switch_makes_logging_a_noop(monkeypatch, tmp_path):
    monkeypatch.setattr(ul, "_ENABLED", False)
    monkeypatch.setattr(ul, "_ensure_log_dir", lambda: tmp_path.mkdir(exist_ok=True))

    ul.log_event("page_visit", page_id="y")

    assert list(tmp_path.glob("*.jsonl")) == []


def test_logger_writes_one_json_line_per_event_with_epoch_seconds(monkeypatch, tmp_path):
    target = tmp_path / "usage2"
    monkeypatch.setattr(ul, "_LOG_DIR", target)
    monkeypatch.setattr(ul, "_ensure_log_dir", lambda: target.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(ul, "_ENABLED", True)

    ul.log_event("export", format="docx", success=True, duration_ms=10)

    files = list(target.glob("usage_events_*.jsonl"))
    assert len(files) == 1
    entry = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert entry["event"] == "export" and entry["format"] == "docx"
    assert len(entry["timestamp"]) == 19  # 秒级 ISO，无毫秒
