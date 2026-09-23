# -*- coding: utf-8 -*-
"""perf_smoke --json 输出契约回归测试（d914-73）。

7 个基准函数全部 monkeypatch 掉（绝不真跑基准、绝不写真实 perf_history）；
只验证 --json 机器可读契约、_time_it 三态与退出码。
"""
import json
import sys

import pytest

from scripts import perf_smoke as ps

BENCH = [("test_imports", "core_imports"), ("test_load_csv", "csv_load"),
         ("test_run_descriptive", "descriptive"), ("test_run_ttest", "ttest"),
         ("test_run_correlation", "correlation"), ("test_docx_export", "docx_export"),
         ("test_learning_card", "learning_card")]


def _stub_all(monkeypatch, results_override=None):
    def make(_k):
        def fn(results, *, emit_text=True):
            payload = {"ms": 1.0, "status": "OK"}
            if results_override and _k in results_override:
                payload.update(results_override[_k])
            results.__setitem__(_k, payload)
        return fn
    for name, key in BENCH:
        monkeypatch.setattr(ps, name, make(key))


def _run_main(monkeypatch, capsys, extra_args=()):
    argv = ["perf_smoke.py", "--json", *extra_args]
    monkeypatch.setattr(sys, "argv", argv)
    ps.main()
    return json.loads(capsys.readouterr().out)


def test_a_json_output_contract(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ps, "HISTORY_FILE", tmp_path / "h.jsonl")
    _stub_all(monkeypatch)
    out = _run_main(monkeypatch, capsys, extra_args=("--no-history",))
    assert set(out.keys()) == {"timestamp", "run_type", "thresholds", "results", "summary"}
    assert out["summary"] == {"warnings": 0, "failures": 0}
    assert set(out["results"]) == {k for _, k in BENCH}
    assert all(v["status"] == "OK" for v in out["results"].values())


def test_b_no_history_writes_nothing(tmp_path, monkeypatch, capsys):
    history = tmp_path / "h.jsonl"
    monkeypatch.setattr(ps, "HISTORY_FILE", history)
    _stub_all(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["perf_smoke.py", "--json", "--no-history"])
    ps.main()
    assert not history.exists()


def test_c_time_it_warn_and_ok(monkeypatch):
    monkeypatch.setattr(ps, "THRESHOLDS", {"k": 100})
    results = {}
    clock = iter([0.0, 0.2])  # 200ms > 100ms 阈值
    monkeypatch.setattr(ps.time, "perf_counter", lambda: next(clock))
    ps._time_it("k", "slow op", lambda: None, results, emit_text=False)
    assert results["k"]["status"] == "WARN"

    clock = iter([0.0, 0.05])  # 50ms ≤ 100ms
    monkeypatch.setattr(ps.time, "perf_counter", lambda: next(clock))
    ps._time_it("k", "fast op", lambda: None, results, emit_text=False)
    assert results["k"]["status"] == "OK"


def test_d_time_it_failure_returns_none_and_marks_fail(monkeypatch):
    results = {}

    def boom():
        raise RuntimeError("boom")

    ret = ps._time_it("k", "exploding op", boom, results, emit_text=False)
    assert ret is None
    assert results["k"]["status"] == "FAIL"
    assert results["k"]["error"] == "boom"


def test_e_failures_raise_system_exit(tmp_path, monkeypatch, capsys):
    history = tmp_path / "h.jsonl"
    monkeypatch.setattr(ps, "HISTORY_FILE", history)
    _stub_all(monkeypatch, results_override={"core_imports": {"status": "FAIL",
                                                              "error": "probe"}})
    monkeypatch.setattr(sys, "argv", ["perf_smoke.py", "--json", "--no-history"])
    with pytest.raises(SystemExit) as exc:
        ps.main()
    assert exc.value.code == 1
    assert not history.exists()
