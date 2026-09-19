"""src/ui/quick_entries.py 最小特征化测试（s918-27）。

只跑 `_run_quick_analysis` 一条路径：合成 2 组数据、假 `st`（无 Streamlit 运行时）、
归档函数打桩（**否则测试会往真实归档目录写文件**）。
红线：只断言「不抛异常＋产出键存在」，**不对任何显著性/统计数值下结论**。
"""
from contextlib import contextmanager

import pandas as pd
import pytest

import src.ui.quick_entries as qe
import src.utils.archive_manager as archive_manager


class RerunRequested(Exception):
    """真实 st.rerun() 在脚本运行时以异常终止本轮，这里同构模拟。"""


class FakeState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        self.pop(key, None)


class FakeStreamlit:
    def __init__(self):
        self.session_state = FakeState()
        self.reruns = 0
        self.warnings = []

    @contextmanager
    def spinner(self, *args, **kwargs):
        yield

    def rerun(self):
        self.reruns += 1
        raise RerunRequested()

    def warning(self, msg):
        # s919-13：归档/KB 失败现在要出声（quick_entries 的两处 st.warning），故假 st 得收得住
        self.warnings.append(msg)

    def __getattr__(self, name):
        raise AssertionError(f"本单不该触发页面渲染: st.{name}")


DF = pd.DataFrame({"分数": [3, 4, 5, 6, 7, 8, 3, 4, 5, 6, 7, 8],
                   "组别": ["A"] * 6 + ["B"] * 6})
OUTPUT_KEYS = ["test_name_zh", "plan", "result", "errors", "descriptive",
               "assumptions", "data_quality", "reasoning", "charts_data"]


@pytest.fixture
def fake_st(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(qe, "st", fake)
    calls = []
    monkeypatch.setattr(archive_manager, "archive_analysis",
                        lambda *a, **k: calls.append(a))
    fake.archive_calls = calls
    return fake


def _rerun(fn, *args, **kwargs):
    with pytest.raises(RerunRequested):
        fn(*args, **kwargs)


def test_quick_analysis_populates_session_state_with_expected_keys(fake_st):
    _rerun(qe._run_quick_analysis, DF, "independent_ttest", dv="分数", iv="组别")

    output = fake_st.session_state["analysis_output"]
    assert isinstance(output, dict)
    for key in OUTPUT_KEYS:
        assert key in output, key
    assert output["result"] is not None
    assert fake_st.session_state["plan"].test_type == "independent_ttest"


def test_history_entry_records_dv_and_iv_lists(fake_st):
    _rerun(qe._run_quick_analysis, DF, "independent_ttest", dv="分数", iv="组别")

    assert fake_st.session_state["analysis_history"] == [
        {"test_type": "independent_ttest", "dv": ["分数"], "iv": ["组别"]}
    ]


def test_dv_list_takes_precedence_over_single_dv(fake_st):
    _rerun(qe._run_quick_analysis, DF, "descriptive", dv="组别", dv_list=["分数"])

    assert fake_st.session_state["plan"].dependent_vars == ["分数"]
    assert fake_st.session_state["plan"].independent_vars == []


def test_quick_entry_flags_are_cleared_before_rerun(fake_st):
    fake_st.session_state["quick_entry"] = "x"
    fake_st.session_state["show_quick_detail"] = "y"

    _rerun(qe._run_quick_analysis, DF, "descriptive", dv_list=["分数"])

    assert "quick_entry" not in fake_st.session_state
    assert "show_quick_detail" not in fake_st.session_state


def test_archiving_is_attempted_once_per_analysis(fake_st):
    _rerun(qe._run_quick_analysis, DF, "independent_ttest", dv="分数", iv="组别")

    assert len(fake_st.archive_calls) == 1


def test_archiving_failure_lands_results_but_warns(fake_st, monkeypatch):
    """s919-13 翻正：改前是 `except Exception: pass`，"分析结果照常落盘、用户看不到任何提示"
    （旧用例名 test_archiving_failure_is_swallowed_silently 钉的就是那个现状）。
    现在两件事都要成立：① 控制流不变（结果照样进 session_state、照常 rerun）；
    ② 用户看得见"归档失败"，且带上异常类型便于报障。"""
    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(archive_manager, "archive_analysis", boom)

    _rerun(qe._run_quick_analysis, DF, "independent_ttest", dv="分数", iv="组别")

    assert "analysis_output" in fake_st.session_state          # ① 控制流未变
    assert len(fake_st.warnings) == 1                          # ② 恰好一条提示
    assert "归档失败" in fake_st.warnings[0] and "OSError" in fake_st.warnings[0]
