# -*- coding: utf-8 -*-
"""文献调度 CLI 退出码契约钉桩（s918-43）。

`__main__.py:5-8` docstring 声明 0/1/2 三码，`scripts/run_daily_feed.bat` 用
`set RC=%ERRORLEVEL%` 透传给 Task Scheduler，此前 90 行真盲区、零测试。
只 monkeypatch `run_daily`，不触网、不建库、不加锁。
可复跑：.venv/Scripts/python.exe -m pytest tests/test_scheduler_cli.py -q
"""
from __future__ import annotations

import json
import sys

import pytest

from src.literature_feed.scheduler import __main__ as cli
from src.literature_feed.scheduler.daily_runner import (
    DEFAULT_DAYS_BACK,
    DEFAULT_FETCH_LIMIT,
    MAX_EXTRACT_ARTICLES_PER_RUN,
)


class _Summary:
    """最小 RunSummary 替身：CLI 只用到 .status 与 .to_dict()。"""

    def __init__(self, status="completed", payload=None):
        self.status = status
        self._payload = payload if payload is not None else {"status": status, "run_id": 7}

    def to_dict(self):
        return self._payload


@pytest.fixture
def captured(monkeypatch, capsys):
    """返回 (calls, emit)；emit(summary_or_exc) 决定 run_daily 的返回值或抛出物。"""
    calls = []
    holder = {"result": _Summary(), "raise": None}

    def fake_run_daily(**kwargs):
        calls.append(kwargs)
        if holder["raise"] is not None:
            raise holder["raise"]
        return holder["result"]

    monkeypatch.setattr(cli, "run_daily", fake_run_daily)
    capsys.readouterr()  # 清掉 import 期可能残留的输出

    def emit(result=None, raises=None):
        holder["result"] = result if result is not None else _Summary()
        holder["raise"] = raises
        return calls

    emit.inputs = calls
    emit.capsys = capsys
    return emit


# --- 退出码契约（docstring :5-8）------------------------------------------------


def test_normal_run_returns_zero(captured):
    captured(_Summary("completed"))
    assert cli.main([]) == 0


def test_partial_still_returns_zero(captured):
    """docstring 明示「即使 partial 也算 0，靠 summary 看具体」。"""
    captured(_Summary("partial"))
    assert cli.main([]) == 0


def test_skipped_locked_returns_one(captured):
    """锁被占时仍打 summary 再返回 1：bat 侧「末行有 JSON」不等于 rc=0。"""
    captured(_Summary("skipped_locked"))
    assert cli.main(["--json-summary"]) == 1
    assert json.loads(captured.capsys.readouterr().out.strip())["status"] == "skipped_locked"


def test_top_level_exception_returns_two_not_traceback(captured):
    captured(raises=RuntimeError("boom"))
    assert cli.main([]) == 2  # 被 except 兜住，不把异常抛给 bat


def test_exception_path_suppresses_json_summary(captured):
    """rc=2 时 summary 从未产生，末行不应是 JSON（bat 会误读成一次成功的运行）。"""
    captured(raises=RuntimeError("boom"))
    assert cli.main(["--json-summary"]) == 2
    assert captured.capsys.readouterr().out.strip() == ""


# --- --json-summary 末行 JSON（:81-82）-----------------------------------------


def test_json_summary_last_line_parses(captured):
    payload = {"status": "completed", "run_id": 7, "sources": {}}
    captured(_Summary("completed", payload))
    assert cli.main(["--json-summary"]) == 0
    out = captured.capsys.readouterr().out.strip().splitlines()
    assert json.loads(out[-1]) == payload


def test_json_summary_absent_by_default(captured):
    captured(_Summary("completed"))
    assert cli.main([]) == 0
    assert captured.capsys.readouterr().out == ""


# --- 参数 → run_daily kwargs 透传（:66-76）--------------------------------------


def test_source_append_and_flags_forward(captured):
    cli.main(["--source", "jap", "--source", "job", "--no-extract",
              "--trigger", "manual", "--days-back", "3", "--max-extract", "2"])
    kw = captured.inputs[-1]
    assert kw["sources"] == ["jap", "job"] and kw["trigger"] == "manual"
    assert kw["do_extract"] is False and kw["days_back"] == 3 and kw["max_extract"] == 2


def test_trending_defaults_are_on_and_forwarded(captured):
    """--compute-trending 默认 True，只有 --no-compute-trending 才关；CLI 层不夹带计算。"""
    cli.main([])
    kw = captured.inputs[-1]
    assert kw["compute_trending"] is True
    assert (kw["trending_window"], kw["trending_cap"]) == (30, 1.3)
    cli.main(["--no-compute-trending"])
    assert captured.inputs[-1]["compute_trending"] is False


def test_parser_defaults_match_docstring():
    """钉住 :34/:36/:41 help 文本里的「默认 14/20/12」与常量、与 docstring 三者一致。"""
    ns = cli._build_parser().parse_args([])
    assert (ns.days_back, ns.fetch_limit, ns.max_extract) == (14, 20, 12)
    assert (DEFAULT_DAYS_BACK, DEFAULT_FETCH_LIMIT, MAX_EXTRACT_ARTICLES_PER_RUN) == (14, 20, 12)
    assert ns.trigger == "scheduler" and ns.source is None
    assert ns.no_extract is False and ns.json_summary is False
    assert ns.log_level == "INFO" and ns.compute_trending is True


def test_unknown_flag_exits_two_via_argparse(captured):
    """argparse 自己 SystemExit(2)——与「顶层异常」同码，bat 侧无法区分两种失败。"""
    with pytest.raises(SystemExit) as ei:
        cli.main(["--no-such-flag"])
    assert ei.value.code == 2
    assert captured.inputs == []  # 未进入 run_daily


def test_log_level_choices_reject_lowercase(captured):
    with pytest.raises(SystemExit) as ei:
        cli.main(["--log-level", "debug"])
    assert ei.value.code == 2


def test_stdout_encode_failure_escapes_main(captured, monkeypatch, capsys):
    """钉住 :81-82 在 try 之外：stdout 打不出 JSON（如 cp936 控制台遇 ✓）时异常**逃逸**，
    进程码由 CPython 给 1——与 docstring 的「锁被占用」同号。实测见 result 第二节。"""
    captured(_Summary("completed", {"msg": "✓"}))

    class _GbkStdout:
        def write(self, _s):
            raise UnicodeEncodeError("gbk", "", 0, 1, "illegal multibyte")

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", _GbkStdout())
    capsys.readouterr()
    with pytest.raises(UnicodeEncodeError):
        cli.main(["--json-summary"])
