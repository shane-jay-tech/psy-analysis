"""N10 苏格拉底基准漂移观测 — 离线单测。

只测纯函数：archive / latest report / compare reports / write markdown。
不调真实 LLM，不调 pytest --run-benchmark。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.benchmark


def _fake_report(*, model: str, replies: dict[str, str]) -> dict:
    """构造一份 benchmark 报告，replies = {case_id: llm_reply}。"""
    cases = [
        {
            "case_id": "stage1_case1",
            "stage": 1,
            "input": "我想研究领导力",
            "expected_dimensions": ["概念", "对象", "情境"],
            "llm_reply": replies.get("stage1_case1", ""),
            "manual_score": None, "manual_notes": "", "error": None,
        },
        {
            "case_id": "stage1_case2",
            "stage": 1,
            "input": "我想研究情绪",
            "expected_dimensions": ["范围", "测量"],
            "llm_reply": replies.get("stage1_case2", ""),
            "manual_score": None, "manual_notes": "", "error": None,
        },
    ]
    return {
        "version": "v3.3",
        "generated_at": "2026-05-29T00:00:00",
        "llm": {"provider": "deepseek", "model": model},
        "n_cases": len(cases),
        "results": cases,
    }


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    """重定向 REPORT_DIR / HISTORY_DIR 到 tmp。"""
    import importlib
    import scripts.evaluate_socratic_benchmark as m
    importlib.reload(m)

    report_dir = tmp_path / "reports"
    history_dir = tmp_path / "history"
    monkeypatch.setattr(m, "REPORT_DIR", report_dir)
    monkeypatch.setattr(m, "HISTORY_DIR", history_dir)
    return m, report_dir, history_dir


class TestLatestReport:

    def test_returns_none_when_dir_missing(self, isolated_paths):
        m, report_dir, _ = isolated_paths
        assert m._latest_report(report_dir) is None

    def test_returns_none_when_dir_empty(self, isolated_paths):
        m, report_dir, _ = isolated_paths
        report_dir.mkdir()
        assert m._latest_report(report_dir) is None

    def test_picks_most_recent_by_mtime(self, isolated_paths, tmp_path):
        import time
        m, report_dir, _ = isolated_paths
        report_dir.mkdir()
        old = report_dir / "benchmark_OLD.json"
        old.write_text("{}")
        time.sleep(0.05)
        new = report_dir / "benchmark_NEW.json"
        new.write_text("{}")
        assert m._latest_report(report_dir) == new


class TestArchiveToHistory:

    def test_creates_history_dir_and_copies(self, isolated_paths, tmp_path):
        m, report_dir, history_dir = isolated_paths
        report_dir.mkdir()
        latest = report_dir / "benchmark_X.json"
        report = _fake_report(model="deepseek-chat", replies={"stage1_case1": "测概念对象"})
        latest.write_text(json.dumps(report), encoding="utf-8")

        archived = m._archive_to_history(latest, history_dir)
        assert archived.parent == history_dir
        assert archived.name.startswith("socratic_benchmark_")
        assert archived.name.endswith("Z.json")
        # 内容相同
        assert json.loads(archived.read_text(encoding="utf-8")) == report


class TestCompareReports:

    def test_detects_improvement(self, isolated_paths):
        m, _, _ = isolated_paths
        old = _fake_report(model="m1", replies={
            "stage1_case1": "随便回答",  # 几乎不命中
            "stage1_case2": "随便回答",
        })
        new = _fake_report(model="m1", replies={
            "stage1_case1": "我们要明确概念、对象、情境",  # 命中 3 维度
            "stage1_case2": "范围 + 测量都得说清",
        })
        rows, summary = m._compare_reports(old, new)
        assert summary["improved"] >= 1
        assert summary["regressed"] == 0
        assert summary["cand_avg_pct"] > summary["base_avg_pct"]

    def test_detects_regression(self, isolated_paths):
        m, _, _ = isolated_paths
        old = _fake_report(model="m1", replies={
            "stage1_case1": "概念、对象、情境都说清",
            "stage1_case2": "范围 + 测量",
        })
        new = _fake_report(model="m1", replies={
            "stage1_case1": "随便",
            "stage1_case2": "随便",
        })
        rows, summary = m._compare_reports(old, new)
        assert summary["regressed"] >= 1
        assert summary["cand_avg_pct"] < summary["base_avg_pct"]

    def test_same_when_identical(self, isolated_paths):
        m, _, _ = isolated_paths
        same = _fake_report(model="m1", replies={
            "stage1_case1": "概念、对象、情境",
            "stage1_case2": "范围、测量",
        })
        rows, summary = m._compare_reports(same, same)
        assert summary["regressed"] == 0
        assert summary["improved"] == 0
        assert summary["same"] == summary["n"]


class TestTrackDrift:

    def test_no_report_returns_error(self, isolated_paths, capsys):
        m, _, _ = isolated_paths
        rc = m._track_drift()
        assert rc == 1
        out = capsys.readouterr().out
        assert "未在" in out

    def test_first_run_only_archives(self, isolated_paths, capsys):
        m, report_dir, history_dir = isolated_paths
        report_dir.mkdir()
        latest = report_dir / "benchmark_first.json"
        latest.write_text(json.dumps(
            _fake_report(model="m1", replies={"stage1_case1": "概念对象", "stage1_case2": "范围测量"})
        ), encoding="utf-8")

        rc = m._track_drift()
        assert rc == 0
        # 应只有一个归档 + 一个 markdown
        archives = list(history_dir.glob("socratic_benchmark_*.json"))
        assert len(archives) == 1
        md = history_dir / "_latest_drift.md"
        assert md.exists()
        assert "仅记录起点" in md.read_text(encoding="utf-8")

    def test_second_run_compares_and_writes_drift(self, isolated_paths):
        import time
        m, report_dir, history_dir = isolated_paths
        report_dir.mkdir()

        # 第一次：差答案
        first = report_dir / "benchmark_v1.json"
        first.write_text(json.dumps(
            _fake_report(model="m1", replies={"stage1_case1": "随便", "stage1_case2": "随便"})
        ), encoding="utf-8")
        m._track_drift()

        time.sleep(1.1)  # 保证 UTC 时间戳秒级不同

        # 第二次：好答案
        second = report_dir / "benchmark_v2.json"
        second.write_text(json.dumps(
            _fake_report(model="m1", replies={
                "stage1_case1": "明确概念、对象、情境",
                "stage1_case2": "说清范围、测量",
            })
        ), encoding="utf-8")
        # 让第二次的 mtime 更新
        second.touch()
        m._track_drift()

        archives = sorted(history_dir.glob("socratic_benchmark_*.json"))
        assert len(archives) == 2

        md_content = (history_dir / "_latest_drift.md").read_text(encoding="utf-8")
        assert "上一次归档" in md_content
        # 应识别为改进
        assert "改进" in md_content or "改进" in md_content or "+" in md_content
