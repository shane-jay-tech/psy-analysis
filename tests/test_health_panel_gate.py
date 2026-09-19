"""src/ui/health_panel.py 导出门禁 `check_export_allowed` 特征化测试（s918-24）。

只测这个决定「用户能否导出」的纯门禁（＋其 `issues=None` 分支的采集入口），渲染函数不测。
假 `st` 经 monkeypatch 注入；`run_health_checks` 打桩，不跑真健康检查。
src/ 零改动。
"""
import pytest

import src.ui.health_panel as hp
from src.utils.project_health import ProjectHealthIssue


def _issue(code, level, title, detail="d"):
    return ProjectHealthIssue(code=code, level=level, title=title, detail=detail,
                              module="m", action_label="", action_target="")


ERR = _issue("no_data", "ERROR", "尚未加载数据", "请先上传数据文件")
WARN = _issue("no_lit", "WARN", "文献太少")
INFO = _issue("hint", "INFO", "小提示")


class RecordingStreamlit:
    def __init__(self, session_state=None):
        self.session_state = session_state if session_state is not None else {}
        self.errors = []
        self.markdowns = []

    def error(self, msg):
        self.errors.append(msg)

    def markdown(self, text, **kw):
        self.markdowns.append(text)

    def __getattr__(self, name):
        return lambda *a, **k: None


@pytest.fixture
def fake(monkeypatch):
    rec = RecordingStreamlit()
    monkeypatch.setattr(hp, "st", rec)
    return rec


def test_no_issues_at_all_allows_export(fake):
    assert hp.check_export_allowed([]) is True
    assert fake.errors == [] and fake.markdowns == []


@pytest.mark.parametrize("issues", [[INFO], [WARN], [WARN, INFO], [INFO, INFO]])
def test_only_non_error_levels_never_block(fake, issues):
    assert hp.check_export_allowed(issues) is True
    assert fake.errors == []


def test_a_single_error_blocks_export_and_shows_the_reason(fake):
    assert hp.check_export_allowed([ERR]) is False
    assert fake.errors == ["🚫 存在阻断性问题，无法导出："]
    assert fake.markdowns == ["- **尚未加载数据**: 请先上传数据文件"]


def test_only_error_rows_are_listed_when_levels_are_mixed(fake):
    assert hp.check_export_allowed([WARN, ERR, INFO,
                                    _issue("no_roles", "ERROR", "变量角色未设置")]) is False

    assert len(fake.markdowns) == 2
    assert fake.markdowns[0].startswith("- **尚未加载数据**")
    assert fake.markdowns[1] == "- **变量角色未设置**: d"


def test_level_comparison_is_case_sensitive_so_lowercase_slips_through(fake):
    """门禁是 `level == "ERROR"` 严格串比较：写小写就不阻断。"""
    assert hp.check_export_allowed([_issue("x", "error", "小写错误")]) is True
    assert hp.check_export_allowed([_issue("y", "FATAL", "未知级别")]) is True


def test_default_argument_collects_issues_from_session_state(fake, monkeypatch):
    seen = {}

    def fake_checks(**kw):
        seen.update(kw)
        return [ERR]

    fake.session_state.update({"df": object(), "variable_roles": {"x": "num"},
                               "literature_pending_count": 3, "literature_approved_count": 1})
    monkeypatch.setattr(hp, "run_health_checks", fake_checks)

    assert hp.check_export_allowed() is False
    assert seen == {"has_data": True, "variable_types_set": True,
                    "literature_pending_count": 3, "literature_approved_count": 1,
                    "paper_bundle": None, "analysis_results": None}


def test_collection_without_session_keys_defaults_to_not_ready(fake, monkeypatch):
    monkeypatch.setattr(hp, "run_health_checks", lambda **kw: [])

    assert hp.check_export_allowed(None) is True
    assert fake.errors == []


def test_collection_failure_propagates_instead_of_being_swallowed(fake, monkeypatch):
    """任务书写「_collect_issues 异常吞掉」，但 health_panel.py 全文 try/except 零命中——
    实测异常直接冒泡（门禁既不放行也不拦下，页面报错）。"""
    def boom(**kw):
        raise RuntimeError("health check broke")

    monkeypatch.setattr(hp, "run_health_checks", boom)

    with pytest.raises(RuntimeError, match="health check broke"):
        hp.check_export_allowed()
