"""src/ui/undergrad_wizard 两纯助手钉桩（s918-49）。

`_build_figure_specs` 里的 6 个画图函数一律打桩（只记调用参数、返回哨兵对象）⇒ 不起 plotly、不落盘；
`_record_download` 用假 `st`（session_state 走普通 dict）。
锚点：src/ui/undergrad_wizard.py:1553 与 :866（模块 3715 行，此前两助手零覆盖）。
"""
import datetime as dt

import pandas as pd
import pytest

import src.ui.undergrad_wizard as uw
import src.visualization.charts as charts

DF = pd.DataFrame({"分数": [1.0, 2.0, 3.0, 4.0], "组别": ["a", "a", "b", "b"]})
SPEC_KEYS = {"fig", "test_name_zh", "chart_type", "variables", "timestamp"}


@pytest.fixture
def figs(monkeypatch):
    """把 6 个画图函数换成哨兵，避免真画图；顺带记录调用参数。"""
    calls = []

    def make(name):
        def _fn(*a, **k):
            calls.append({"fn": name, "args": a, "kwargs": k})
            return f"<fig:{name}>"
        return _fn

    for fn in ("bar_with_error", "box_plot", "scatter_with_regression",
               "correlation_heatmap", "distribution_plot", "qq_plot"):
        monkeypatch.setattr(charts, fn, make(fn))
    return calls


def _spec(output, ctx=None, wiz_data=None):
    return uw._build_figure_specs(output, ctx or {}, wiz_data if wiz_data is not None else {"df": DF})


def test_empty_output_yields_no_specs(figs):
    assert _spec({}) == []
    assert _spec({"charts_data": {"box_data": {"dv": "分数", "iv": "组别"}}}, wiz_data={}) == []


def test_missing_dataframe_short_circuits(figs):
    out = {"charts_data": {"box_data": {"dv": "分数", "iv": "组别"}}}

    assert _spec(out, wiz_data={"df": None}) == []
    assert _spec(out, wiz_data={}) == []
    assert _spec({"charts_data": {}}) == []
    assert _spec({"charts_data": None}) == []
    assert figs == []                                   # 一条画图调用都没发


def test_box_spec_shape_arguments_and_title(figs):
    out = {"charts_data": {"box_data": {"dv": "分数", "iv": "组别"}}}

    specs = _spec(out, ctx={"test_name_zh": "独立样本t检验"})

    assert len(specs) == 1
    spec = specs[0]
    assert set(spec) == SPEC_KEYS
    assert spec["fig"] == "<fig:box_plot>"
    assert spec["chart_type"] == "箱线图"
    assert spec["variables"] == ["分数", "组别"]
    assert spec["test_name_zh"] == "独立样本t检验"
    assert dt.datetime.strptime(spec["timestamp"], "%Y-%m-%d %H:%M")   # 分钟级、无秒
    assert figs[0]["args"] == (DF, "分数", "组别")
    assert figs[0]["kwargs"] == {"title": "分数 分组箱线图"}


def test_ctx_without_test_name_falls_back_to_analysis(figs):
    specs = _spec({"charts_data": {"box_data": {"dv": "分数", "iv": "组别"}}}, ctx={})

    assert specs[0]["test_name_zh"] == "分析"


def test_multiple_sources_keep_a_stable_order_and_per_type_variables(figs):
    corr = pd.DataFrame({"分数": [1.0, 2.0], "自尊": [3.0, 4.0]})
    out = {"charts_data": {
        "scatter_cols": ["分数", "组别"],
        "box_data": {"dv": "分数", "iv": "组别"},
        "corr_matrix": corr,
    }}

    specs = _spec(out)

    assert [s["chart_type"] for s in specs] == ["箱线图", "相关热力图", "散点图"]
    assert specs[1]["variables"] == ["分数", "自尊"]      # 热力图取列名清单
    assert specs[2]["variables"] == ["分数", "组别"]      # 散点只取前两列
    assert specs[2]["fig"] == "<fig:scatter_with_regression>"


def test_single_column_scatter_request_is_dropped(figs):
    specs = _spec({"charts_data": {"scatter_cols": ["分数"]}})

    assert specs == []


def test_histogram_caps_at_three_and_skips_columns_absent_from_df(figs):
    out = {"charts_data": {"histogram_cols": ["分数", "组别", "缺失A", "缺失B"]}}

    specs = _spec(out)

    assert [s["variables"] for s in specs] == [["分数"], ["组别"]]   # 第 3 个之后不画；缺列的跳过
    assert all(s["chart_type"] == "分布图" for s in specs)


def test_qq_requires_the_column_to_exist_but_box_and_scatter_do_not(figs):
    """不对称守卫：分布图/QQ 图会核 `col in df.columns`，箱线图与散点图不核 ⇒
    传错列名时后两者照样把请求送进画图函数（真函数下会炸或画空图）。"""
    assert _spec({"charts_data": {"qq_col": "不存在的列"}}) == []

    specs = _spec({"charts_data": {"box_data": {"dv": "不存在的列", "iv": "组别"}}})

    assert len(specs) == 1
    assert figs[0]["args"] == (DF, "不存在的列", "组别")


class FakeState(dict):
    pass


class FakeST:
    def __init__(self):
        self.session_state = FakeState()


@pytest.fixture
def fake_st(monkeypatch):
    fake = FakeST()
    monkeypatch.setattr(uw, "st", fake)
    return fake


def test_record_download_appends_type_filename_and_second_level_ts(fake_st):
    uw._record_download("zip", "图表.zip")
    uw._record_download("word", "论文.docx")

    history = fake_st.session_state["download_history"]
    assert [h["type"] for h in history] == ["zip", "word"]
    assert history[0]["filename"] == "图表.zip"
    assert len(history[0]["ts"]) == 19
    dt.datetime.strptime(history[0]["ts"], "%Y-%m-%d %H:%M:%S")


def test_download_history_is_capped_at_the_latest_thirty(fake_st):
    for i in range(35):
        uw._record_download("zip", f"f{i}.zip")

    history = fake_st.session_state["download_history"]

    assert len(history) == 30
    assert [h["filename"] for h in history] == [f"f{i}.zip" for i in range(5, 35)]
