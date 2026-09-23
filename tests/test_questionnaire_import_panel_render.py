# -*- coding: utf-8 -*-
"""src/ui/questionnaire_import_panel.py 渲染层补面（s923-01）。

对象是两处此前零 AppTest/桩级命中的渲染面（锚点复核于 2026-09-23，行号逐字一致）：
  * `:170 def _render_results(session_state: dict)` —— 消费 `_CLEANED_KEY` 渲染结果的那一半；
  * `:203 def get_cleaning_log_for_deliverable(session_state: dict) -> list[dict]` —— 日志摊平。

来账：`zcode-bridge/done/s922-10-psy-qimport-3more.result.md` 把 `_render_results` 记为
「同族补面缺口，留作下一单」，并指出 `get_cleaning_log_for_deliverable` **只被 dict 层测过**
——现存的 `tests/test_questionnaire_import_panel.py::test_cleaning_log_for_deliverable`
和 `::test_empty_deliverable_log` 确实只断言 dict 长度/首元素，且后者测的是
「session_state 里根本没有 result」这一形态，**「有 result 但 log 为空」从未被覆盖**（本件补上）。

只加测试，**不改生产码**。

口径说明（为什么是「会话桩级」而不是 `streamlit.testing.v1.AppTest`）：
`tests/conftest.py::_APP_TEST_FILES` 是一枚**文件名白名单**——不在名单里的文件享受不到
`isolate_streamlit_app_test_storage` 的存储隔离（PSY_ANALYSIS_HOME / archive / logs 重定向）。
要走真 AppTest 就得把本文件名追加进 conftest，那会违反本单完成标准
「porcelain 相对开工仅新增该一件」。故沿用本仓渲染面板的既有主流桩型
（见 `tests/test_items_upload_airview.py:28 FakeSt` ／ `tests/test_feed_panel_charac.py:146`）：
`monkeypatch.setattr(panel, "st", fake)` ＋ `__getattr__` 对未预期调用直接判红。
**后来人若要把本件升级成真 AppTest，必须同时改 `_APP_TEST_FILES`，否则等于零隔离。**
"""
import pandas as pd
import pytest

import src.ui.questionnaire_import_panel as qip
from src.questionnaire.import_cleaning import (
    CleaningLogEntry,
    CleaningResult,
    ScaleDimension,
    export_cleaning_log,
    run_questionnaire_cleaning,
)

# --------------------------------------------------------------------------- #
# 记录型 st 桩：只放行 _render_results 实际会打的那几个方法，其余一律判红
# --------------------------------------------------------------------------- #


class FakeColumn:
    def __init__(self, host):
        self.host = host

    def metric(self, label, value, **k):
        self.host.metrics.append((label, value))


class FakeSt:
    def __init__(self):
        self.infos: list[str] = []
        self.markdowns: list[str] = []
        self.dataframes: list[object] = []
        self.downloads: list[tuple] = []
        self.metrics: list[tuple] = []
        self.columns_calls: list[int] = []

    def info(self, msg, **k):
        self.infos.append(msg)

    def markdown(self, msg, **k):
        self.markdowns.append(msg)

    def dataframe(self, data, **k):
        self.dataframes.append(data)

    def columns(self, spec, **k):
        self.columns_calls.append(spec)
        n = spec if isinstance(spec, int) else len(spec)
        return tuple(FakeColumn(self) for _ in range(n))

    def download_button(self, *a, **k):
        self.downloads.append(a)

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


# --------------------------------------------------------------------------- #
# 夹具：真跑 import_cleaning（纯本地、零网络、零 IO），读数不靠编
# --------------------------------------------------------------------------- #


def _raw_df(n: int = 30) -> pd.DataFrame:
    import numpy as np

    np.random.seed(42)
    return pd.DataFrame({
        "id": range(1, n + 1),
        "gender": np.random.choice(["M", "F"], n),
        "Q1": np.random.randint(1, 6, n),
        "Q2": np.random.randint(1, 6, n),
        "Q3": np.random.randint(1, 6, n),
        "Q4": np.random.randint(1, 6, n),
        "duration": np.random.randint(30, 300, n),
    })


DIMENSIONS = [
    ScaleDimension(name="scale_a", items=["Q1", "Q2"], reverse_items=["Q2"]),
    ScaleDimension(name="scale_b", items=["Q3", "Q4"], reverse_items=[]),
]


@pytest.fixture
def st(monkeypatch):
    fake = FakeSt()
    monkeypatch.setattr(qip, "st", fake)
    return fake


@pytest.fixture
def cleaned_state():
    """带维度＋时长过滤的完整清洗态（实测 log 4 条、df_scored 非空）。"""
    result = run_questionnaire_cleaning(
        _raw_df(), dimensions=DIMENSIONS, duration_column="duration", min_duration_seconds=60,
    )
    return {qip._CLEANED_KEY: result}, result


# --------------------------------------------------------------------------- #
# 一、_render_results 的空态守卫
# --------------------------------------------------------------------------- #


def test_missing_cleaned_result_renders_hint_only(st):
    """没有 _CLEANED_KEY 时只出一条 info 并立即 return，后续渲染一个都不该发生。"""
    qip._render_results({})

    assert st.infos == ["请先执行清洗"]
    assert st.markdowns == []
    assert st.metrics == []
    assert st.dataframes == []
    assert st.downloads == []


def test_present_but_scoreless_state_still_short_circuits(st):
    """守卫读的是 `.get(_CLEANED_KEY)`，因此 None 值与缺键同形——钉住这个等价性。"""
    qip._render_results({qip._CLEANED_KEY: None})
    assert st.infos == ["请先执行清洗"]
    assert st.downloads == []


# --------------------------------------------------------------------------- #
# 二、_render_results 的摘要与日志渲染
# --------------------------------------------------------------------------- #


def test_summary_metrics_render_the_three_sample_counts(st, cleaned_state):
    """三列 metric 的标签与数值直接取自 result.summary（口径逐字对齐 :179-181）。"""
    state, result = cleaned_state
    assert result.summary["original_n"] == 30  # 夹具实测锚，改了夹具就该在这里红
    qip._render_results(state)

    assert st.metrics == [
        ("原始样本", result.summary["original_n"]),
        ("有效样本", result.summary["valid_n"]),
        ("剔除样本", result.summary["invalid_n"]),
    ]
    assert st.columns_calls == [3]


def test_each_log_entry_renders_exactly_one_markdown_line(st, cleaned_state):
    """清洗日志区一条 entry 一行，形如 `- **step**: action`，条数与顺序都不得漂。"""
    state, result = cleaned_state
    assert len(result.log) == 4  # 实测：列分类 / 无效样本检测 / 样本清洗 / 量表计分
    qip._render_results(state)

    body = [m for m in st.markdowns if m.startswith("- **")]
    assert body == [f"- **{e.step}**: {e.action}" for e in result.log]


def test_download_payload_is_same_log_as_rendered_body(st, cleaned_state):
    """端到端钉子：下载件与屏上日志区必须同源，否则会交付一份用户没看过的日志。"""
    state, result = cleaned_state
    qip._render_results(state)

    assert len(st.downloads) == 1
    label, data, file_name, mime = st.downloads[0]
    assert label == "📥 下载清洗日志"
    assert file_name == "cleaning_log.md"
    assert mime == "text/markdown"
    assert data == export_cleaning_log(result.log, format="markdown")
    for e in result.log:
        assert e.step in data and e.action in data


def test_scored_preview_section_absent_when_df_scored_is_none(st):
    """不传 dimensions 的分支：df_scored 为 None ⇒ 不出预览区、不调 dataframe，但摘要照出。"""
    result = run_questionnaire_cleaning(_raw_df())
    assert result.df_scored is None  # 实测读数
    qip._render_results({qip._CLEANED_KEY: result})

    assert st.dataframes == []
    assert not any("维度得分预览" in m for m in st.markdowns)
    assert [lab for lab, _ in st.metrics] == ["原始样本", "有效样本", "剔除样本"]
    assert len(st.downloads) == 1


def test_scored_preview_present_with_dimensions_and_caps_at_ten_rows(st, cleaned_state):
    """对照分支：df_scored 非空时出预览，且送进 dataframe 的是 head(10) 而非全表。"""
    state, result = cleaned_state
    qip._render_results(state)

    assert any("维度得分预览" in m for m in st.markdowns)
    assert len(st.dataframes) == 1
    shown = st.dataframes[0]
    assert isinstance(shown, pd.DataFrame)
    assert len(shown) == min(10, len(result.df_scored))
    assert list(shown.columns) == list(result.df_scored.head(10).columns)


# --------------------------------------------------------------------------- #
# 三、get_cleaning_log_for_deliverable 的摊平（空 log／多条 log 两形态）
# --------------------------------------------------------------------------- #

FLATTEN_KEYS = {"step", "action", "affected_rows", "affected_cols", "detail"}


def test_deliverable_flattens_every_entry_in_order(cleaned_state):
    """多条 log：逐条摊平成 dict，键集恰为 5 个，值与 entry 属性一一对应，顺序不变。"""
    state, result = cleaned_state
    out = qip.get_cleaning_log_for_deliverable(state)

    assert len(out) == len(result.log) == 4
    assert all(set(d) == FLATTEN_KEYS for d in out)
    assert out == [
        {"step": e.step, "action": e.action, "affected_rows": e.affected_rows,
         "affected_cols": e.affected_cols, "detail": e.detail}
        for e in result.log
    ]
    # 逐字锚一条真实读数，防止上面那个「与源对账」式断言两边一起漂
    assert out[1] == {"step": "无效样本检测", "action": "标记 1 个无效样本",
                      "affected_rows": 1, "affected_cols": 0,
                      "detail": "作答时长过短或同质作答比例过高"}


def test_deliverable_defaults_materialize_for_bare_entry():
    """dataclass 默认值（affected_rows=0 / detail=''）在摊平后必须**显式存在**，不能缺键。"""
    entry = CleaningLogEntry(step="列分类", action="识别 4 题项列")
    assert entry.affected_rows == 0 and entry.detail == ""  # 默认值实测
    out = qip.get_cleaning_log_for_deliverable(
        {qip._CLEANED_KEY: CleaningResult(df_cleaned=pd.DataFrame(), log=[entry])}
    )
    assert out == [{"step": "列分类", "action": "识别 4 题项列",
                    "affected_rows": 0, "affected_cols": 0, "detail": ""}]
    assert set(out[0]) == FLATTEN_KEYS


def test_deliverable_empty_list_when_result_present_but_log_empty():
    """**本单补的真缺口**：有 result 但 log 为空 ⇒ []，与「没有 result」同值但不同路径。

    现存 `test_empty_deliverable_log` 测的是 session_state 里根本没挂 result，
    这条挂上的是一个 log=[] 的 CleaningResult——两条分支必须各自成立。
    """
    state = {qip._CLEANED_KEY: CleaningResult(df_cleaned=pd.DataFrame(), log=[])}
    assert qip.get_cleaned_result(state) is not None  # 前置：确实进了非空守卫
    assert qip.get_cleaning_log_for_deliverable(state) == []


def test_render_and_deliverable_agree_on_entry_count(st, cleaned_state):
    """两个出口对同一份 log 的读数必须相等：屏上几行，交付包里就几条。"""
    state, result = cleaned_state
    qip._render_results(state)
    rendered = [m for m in st.markdowns if m.startswith("- **")]
    assert len(rendered) == len(qip.get_cleaning_log_for_deliverable(state)) == len(result.log)
