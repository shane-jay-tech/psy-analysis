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


@pytest.mark.parametrize(
    "logger_fn,event",
    [(ul.log_event, "page_visit"), (ul.log_error, "export_failed")],
    ids=["log_event", "log_error"],
)
def test_dir_creation_failure_is_swallowed_like_write_failures(monkeypatch, tmp_path, logger_fn, event):
    """s919-04 翻正（原钉「目录创建失败逃逸 try 块」）：`_ensure_log_dir()` 已在 try 内 ⇒ 不抛进 UI 主路径。

    刻意 monkeypatch `_ensure_log_dir` 本身成 raise，而不是 patch `Path.mkdir`：
    只有异常发生在调用方 try 之内才算数，patch 真 mkdir 会把 try 外的调用一起吞掉，测不出位置。
    """
    monkeypatch.setattr(ul, "_ENABLED", True)
    monkeypatch.setattr(ul, "_LOG_DIR", tmp_path / "gone")

    def boom():
        raise OSError("cannot create log dir")

    monkeypatch.setattr(ul, "_ensure_log_dir", boom)

    logger_fn(event, page_id="x")                      # 不抛 ＝ 本单的全部契约
    assert not (tmp_path / "gone").exists()            # 建目录失败即中止，不会带着缺失目录继续写盘


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


# ────────────── s920-07：目录调用期解析＋建不出来要吱一声＋读侧不许崩 ──────────────
def test_log_dir_is_resolved_at_call_time_not_import_time(monkeypatch, tmp_path):
    """`_LOG_DIR=None` 时认环境变量，且是**每次调用**都认（改前先 import 定死了，后来设 env 无效）。"""
    a = tmp_path / "a"
    b = tmp_path / "b"
    monkeypatch.setattr(ul, "_LOG_DIR", None)
    monkeypatch.setenv("PSY_ANALYSIS_LOG_DIR", str(a))
    assert ul._log_dir() == a
    monkeypatch.setenv("PSY_ANALYSIS_LOG_DIR", str(b))
    assert ul._log_dir() == b                      # 换了立刻生效，不需要重导入


def test_explicit_override_beats_the_environment(monkeypatch, tmp_path):
    """tests/conftest.py 与多处既有用例是直接打桩 `_LOG_DIR` 的——这条优先级不许变。"""
    monkeypatch.setattr(ul, "_LOG_DIR", tmp_path / "pinned")
    monkeypatch.setenv("PSY_ANALYSIS_LOG_DIR", str(tmp_path / "env"))
    assert ul._log_dir() == tmp_path / "pinned"


def test_default_log_dir_is_still_the_configured_one(monkeypatch, tmp_path):
    """默认值不许被本次改动带跑：无覆盖、无环境变量 ⇒ 回到 `app_paths.LOG_DIR`。"""
    from src.utils.app_paths import LOG_DIR

    monkeypatch.setattr(ul, "_LOG_DIR", None)
    monkeypatch.delenv("PSY_ANALYSIS_LOG_DIR", raising=False)
    assert ul._log_dir() == LOG_DIR


def test_mkdir_failure_alerts_once_and_still_raises(monkeypatch, caplog, tmp_path):
    import logging

    class ReadOnlyDir:
        """模拟"目录解析得出来、但建不出来"（只读盘/权限不足）。"""

        def mkdir(self, *a, **k):
            raise OSError("只读盘")

        def __str__(self):
            return "logs"

    monkeypatch.setattr(ul, "_ALERTED", set())
    monkeypatch.setattr(ul, "_log_dir", lambda: ReadOnlyDir())

    with caplog.at_level(logging.WARNING, logger=""):
        for _ in range(5):
            with pytest.raises(OSError):
                ul._ensure_log_dir()               # 语义不变：建不出来照样抛

    alerts = [r.getMessage() for r in caplog.records if "[usage-log-alert]" in r.getMessage()]
    assert len(alerts) == 1                        # 但一次比静默强：报一次，不报五次
    assert "mkdir_failed" in alerts[0] and "只读盘" in alerts[0]


def test_alert_message_does_not_re_resolve_the_dir(monkeypatch, caplog):
    """回归自捉：告警文案里再调一次 `_log_dir()` 会在 except 里二次抛异常，结果一条告警都发不出去。"""
    import logging

    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        raise OSError("环境变量坏了")

    monkeypatch.setattr(ul, "_ALERTED", set())
    monkeypatch.setattr(ul, "_log_dir", flaky)

    with caplog.at_level(logging.WARNING, logger=""):
        with pytest.raises(OSError):
            ul._ensure_log_dir()

    assert calls["n"] == 1                         # 只解析一次，不在异常处理里重试
    alerts = [r.getMessage() for r in caplog.records if "[usage-log-alert]" in r.getMessage()]
    assert len(alerts) == 1 and "未解析" in alerts[0]


@pytest.mark.parametrize("reader", ["get_usage_summary", "get_error_summary"])
def test_readers_degrade_to_empty_summary_instead_of_crashing(monkeypatch, reader):
    """改前三处 `_ensure_log_dir()` 在 try 外面 ⇒ 目录坏了读摘要直接把界面带崩。"""
    monkeypatch.setattr(ul, "_ensure_log_dir", lambda: (_ for _ in ()).throw(OSError("建不出来")))

    out = getattr(ul, reader)()

    assert out[f"total_{'events' if reader.endswith('usage_summary') else 'errors'}"] == 0
    assert out[f"{'events' if reader.endswith('usage_summary') else 'errors'}_by_type"] == {}
    assert out["period_days"] == 7                 # 摘要结构照旧，只是空


def test_clear_logs_is_quiet_when_the_dir_is_unavailable(monkeypatch):
    monkeypatch.setattr(ul, "_ensure_log_dir", lambda: (_ for _ in ()).throw(OSError("建不出来")))

    ul.clear_logs()                                # 不抛就是全部要求


# ===========================================================================
# s924-66：三处静默吞错接观测（写侧 / 读侧 / 清除侧）
# ===========================================================================
# 触发面探针（本机实测，原文见 outbox/s924-66.result.md「证据」）：
#   ① `chmod 555` **目录** 后 append 写 → **写入成功**（Windows 语义下只读属性不拦创建），
#      所以卷宗建议的"tmp 只读目录"在本机**造不出 OSError**；
#   ② `chmod 444` **文件** 后 append 写 → `PermissionError`（真机触发，不是打桩）⇒ 本件按 ② 走。
#   读侧用坏 JSONL 真触发，无需打桩。

def test_write_failure_warns_once_with_path_and_never_the_payload(monkeypatch, caplog, tmp_path):
    """写侧 OSError 不再静默：报**一条**带路径的 warning，且待写内容一个字都不许进日志。"""
    import logging
    import os
    from datetime import date

    secret = "SELF-SECRET-绝不该进日志-4d17"
    monkeypatch.setattr(ul, "_LOG_DIR", tmp_path)
    monkeypatch.setattr(ul, "_ALERTED", set())
    log_file = tmp_path / f"usage_events_{date.today().strftime('%Y%m%d')}.jsonl"
    log_file.write_text("", encoding="utf-8")
    os.chmod(log_file, 0o444)                      # 只读文件 ⇒ open(..., "a") 真抛 PermissionError
    try:
        with caplog.at_level(logging.WARNING, logger=""):
            for _ in range(5):
                ul.log_event("page_visit", page_id=secret)   # 对外语义不变：照旧不抛
    finally:
        os.chmod(log_file, 0o644)                  # 还原，别让 tmp 留只读件

    alerts = [r.getMessage() for r in caplog.records if "[usage-log-alert]" in r.getMessage()]
    assert len(alerts) == 1, "要吱声（0 条＝静默回归），但按 kind 去重（5 次埋点刷 5 条会淹掉控制台）"
    msg = alerts[0]
    assert "write_failed" in msg and log_file.name in msg, f"警告里要有可定位的文件名：{msg}"
    assert "PermissionError" in msg, f"要带异常类型：{msg}"
    assert secret not in msg and "page_visit" not in msg, f"红线：事件正文不得进日志：{msg}"


@pytest.mark.parametrize(
    "reader, prefix, field, total_key",
    [("get_usage_summary", "usage_events", "event", "total_events"),
     ("get_error_summary", "error_events", "error", "total_errors")],
)
def test_read_side_aggregates_one_warning_per_degraded_file(monkeypatch, caplog, tmp_path,
                                                           reader, prefix, field, total_key):
    """读侧坏行：**按文件汇总一条** warning，报出"读到几行／已计几条"——坏行数量从不可知变可知。

    顺带钉住现状行为零变：一条坏行会让该文件**余下的行不再计入**（本单是纯加观测，
    没改成逐行容错——那会改返回值，属另一单）。warning 里的 3/2 就是这次"吞掉 1 条"的痕。
    """
    import logging
    from datetime import date

    d = tmp_path / "logs"
    d.mkdir()
    monkeypatch.setattr(ul, "_LOG_DIR", d)
    day = date.today().strftime("%Y%m%d")
    lines = [json.dumps({field: "ok1"}),
             json.dumps({field: "ok2"}),
             "{这一行不是JSON",
             json.dumps({field: "ok3"})]
    (d / f"{prefix}_{day}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger=""):
        out = getattr(ul, reader)(days=7)

    assert out[total_key] == 2                     # 对外返回值不变：坏行后那条没被计（钉现状）
    assert out["period_days"] == 7
    alerts = [r.getMessage() for r in caplog.records if "read_degraded" in r.getMessage()]
    assert len(alerts) == 1, "按文件汇总，不是逐行刷屏"
    assert "读到=3行" in alerts[0] and "已计=2条" in alerts[0], f"计数没报出来：{alerts[0]}"
    assert "JSONDecodeError" in alerts[0]
    assert "ok3" not in alerts[0] and "这一行不是JSON" not in alerts[0], \
        f"红线：不回贴任何行内容：{alerts[0]}"


def test_clear_logs_reports_undeletable_files(monkeypatch, caplog, tmp_path):
    """`clear_logs` 的删除失败同样是裸 pass（实测第 5 个静默点，卷宗未列）：清不掉要留痕。"""
    import logging
    import os
    from datetime import date

    d = tmp_path / "logs"
    d.mkdir()
    monkeypatch.setattr(ul, "_LOG_DIR", d)
    monkeypatch.setattr(ul, "_ALERTED", set())
    day = date.today().strftime("%Y%m%d")
    victim = d / f"usage_events_{day}.jsonl"
    victim.write_text('{"event": "x"}\n', encoding="utf-8")
    os.chmod(victim, 0o444)                        # 只读 ⇒ unlink 真抛（Windows 上成立）
    try:
        with caplog.at_level(logging.WARNING, logger=""):
            ul.clear_logs()                        # 照旧不抛
    finally:
        os.chmod(victim, 0o644)
    alerts = [r.getMessage() for r in caplog.records if "clear_failed" in r.getMessage()]
    assert len(alerts) == 1 and victim.name in alerts[0]
    assert "OSError" in alerts[0] or "PermissionError" in alerts[0]
