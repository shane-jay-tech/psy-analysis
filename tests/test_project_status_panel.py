"""src/ui/project_status_panel.py 纯渲染冒烟测试（s918-25）。

假 `st` 记录每次调用（monkeypatch 自动还原）＋ fake ReadinessReport；
`compute_readiness` 也被换掉——**本单不跑真评分器，不对就绪度数值下结论**。
锚点：src/ui/project_status_panel.py:7，77 行，盲区审计 :42「真盲区：importers=0」。
"""
import pytest

import src.ui.project_status_panel as pnl
from src.utils.readiness_scorer import ReadinessItem, ReadinessReport


class _Col:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class RecordingStreamlit:
    def __init__(self):
        self.calls = []

    def columns(self, widths):
        self.calls.append(("columns", tuple(widths)))
        return [_Col() for _ in widths]

    def metric(self, label, value):
        self.calls.append(("metric", label, value))

    def markdown(self, text):
        self.calls.append(("markdown", text))

    def progress(self, value, **kw):
        self.calls.append(("progress", value))

    def subheader(self, text):
        self.calls.append(("subheader", text))

    def error(self, text):
        self.calls.append(("error", text))

    def warning(self, text):
        self.calls.append(("warning", text))

    def info(self, text):
        self.calls.append(("info", text))

    def write(self, text):
        self.calls.append(("write", text))

    def caption(self, text):
        self.calls.append(("caption", text))

    def expander(self, text, **kw):
        self.calls.append(("expander", text))
        return _Col()

    def __getattr__(self, name):
        def _rec(*a, **k):
            self.calls.append((name, *a))
        return _rec

    def of(self, kind):
        return [c for c in self.calls if c[0] == kind]


def _item(dim, score, weight, status, detail=""):
    return ReadinessItem(dimension=dim, score=score, weight=weight, status=status, detail=detail)


def _report(**kw):
    base = dict(
        total_score=72.6,
        grade="接近完成",
        items=[_item("数据健康", 80, 0.15, "good", "N=120"),
               _item("方法匹配", 55, 0.2, "warning"),
               _item("结果完整", 30, 0.25, "error")],
        blockers=["缺少敏感性分析"],
        high_priority=["补效果量"],
        optional=["统一图表字号"],
        next_step="先处理阻断项",
    )
    base.update(kw)
    return ReadinessReport(**base)


@pytest.fixture
def fake(monkeypatch):
    rec = RecordingStreamlit()
    monkeypatch.setattr(pnl, "st", rec)
    return rec


def test_score_header_uses_the_grade_icon_and_three_metrics(fake):
    pnl._render_score_header(_report())

    assert fake.of("columns") == [("columns", (1, 1, 1))]
    values = [c[2] for c in fake.of("metric")]
    assert values == ["73 / 100", "🟢 接近完成", "1 个"]


def test_unrecognised_grade_falls_back_to_white_circle(fake):
    pnl._render_score_header(_report(grade="外星等级"))

    assert fake.of("metric")[1][2] == "⚪ 外星等级"


def test_dimension_breakdown_keeps_report_order_and_truncates_weight(fake):
    pnl._render_dimension_breakdown(_report())

    dims = [c[1] for c in fake.of("markdown")]
    assert dims == ["✅ **数据健康** (15%)", "⚠️ **方法匹配** (20%)", "❌ **结果完整** (25%)"]
    assert [c[1] for c in fake.of("write")] == ["80", "55", "30"]
    assert [c[1] for c in fake.of("caption")] == ["N=120"]


def test_progress_bar_is_capped_and_unknown_status_uses_blank_square(fake):
    pnl._render_dimension_breakdown(_report(items=[
        _item("超范围", 160, 0.1, "weird_status"),
        _item("半分", 50, 0.34, "missing"),
    ]))

    assert [c[1] for c in fake.of("progress")] == [1.0, 0.5]
    assert fake.of("markdown")[0][1].startswith("⬜")


def test_action_sections_only_render_when_their_list_is_non_empty(fake):
    pnl._render_action_items(_report(blockers=[], high_priority=[], optional=["只有可选项"]))

    assert fake.of("subheader") == []
    assert fake.of("error") == []
    assert fake.of("warning") == []
    assert fake.of("expander") == [("expander", "📝 可选优化")]
    assert fake.of("info") == [("info", "只有可选项")]


def test_next_step_divider_only_when_present(fake):
    pnl._render_next_step(_report(next_step=""))
    assert fake.calls == []

    pnl._render_next_step(_report(next_step="跑敏感性分析"))
    assert ("divider",) in fake.calls
    assert fake.of("info") == [("info", "🎯 **跑敏感性分析**")]


def test_panel_entry_feeds_session_state_to_scorer_then_renders_four_sections(fake, monkeypatch):
    seen = {}
    report = _report()

    def fake_compute(session_state):
        seen["arg"] = session_state
        return report

    monkeypatch.setattr(pnl, "compute_readiness", fake_compute)
    state = {"analysis_output": object()}

    pnl.render_project_status_panel(state)

    assert seen["arg"] is state
    kinds = [c[0] for c in fake.calls]
    for expected in ("columns", "subheader", "markdown", "divider", "info"):
        assert expected in kinds, expected


def test_empty_report_renders_without_raising(fake, monkeypatch):
    monkeypatch.setattr(pnl, "compute_readiness", lambda ss: _report(
        total_score=0.0, grade="未就绪", items=[], blockers=[], high_priority=[], optional=[], next_step=""))

    pnl.render_project_status_panel({})

    assert [c[1] for c in fake.of("metric")] == ["总分", "等级", "阻断项"]
    assert fake.of("markdown") == []
