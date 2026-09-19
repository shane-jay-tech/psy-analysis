"""src/ui/template_center_panel._build_core_workspace 钉桩（s918-50）。

纯 dict 进纯 dict 出，无需 Streamlit：session_state 传普通 dict、df 用真 DataFrame。
导出链依赖这三键与 df_b64，此前零测试。
锚点：src/ui/template_center_panel.py:217（模块 289 行）。
"""
import base64
import io
from datetime import datetime

import pandas as pd
import pytest

from src.ui.template_center_panel import _build_core_workspace
from src.utils.workspace import CURRENT_SCHEMA

DF = pd.DataFrame({"分数": [1.5, 2.0, 3.25], "组别": ["a", "b", "c"]})


def test_core_snapshot_carries_the_three_meta_keys():
    ws = _build_core_workspace({"df": DF})

    assert ws["_schema"] == CURRENT_SCHEMA
    assert ws["_version"] == CURRENT_SCHEMA.lstrip("v")
    assert datetime.fromisoformat(ws["_saved_at"])           # 秒级 ISO，可解析
    assert len(ws["_saved_at"]) == 19


def test_dataframe_roundtrips_through_df_b64():
    ws = _build_core_workspace({"df": DF})

    csv = base64.b64decode(ws["df_b64"]).decode("utf-8")
    back = pd.read_csv(io.StringIO(csv))

    assert list(back.columns) == ["分数", "组别"]
    pd.testing.assert_frame_equal(back, DF)


def test_df_b64_is_written_with_index_false():
    ws = _build_core_workspace({"df": DF})

    first_line = base64.b64decode(ws["df_b64"]).decode("utf-8").splitlines()[0]

    assert first_line == "分数,组别"                      # 无索引列 ⇒ 回读不会多出 Unnamed 列


@pytest.mark.parametrize("session", [
    {},
    {"df": None},
    {"df": "not a dataframe"},                        # hasattr(to_csv) 守卫：非 DataFrame 不编码
])
def test_df_b64_absent_when_dataframe_missing_or_unusable(session):
    assert "df_b64" not in _build_core_workspace(session)


def test_present_fields_pass_through_by_reference_and_nulls_are_omitted():
    meta = {"n": 3}
    history = [{"test_type": "descriptive"}]

    ws = _build_core_workspace({"meta": meta, "analysis_history": history,
                                "inspector": None, "file_name": None})

    assert ws["meta"] is meta                              # 透传不复制（导出链按引用取）
    assert ws["analysis_history"] is history
    assert "inspector" not in ws and "file_name" not in ws   # None 值不留键


def test_empty_state_still_yields_a_minimal_valid_snapshot():
    ws = _build_core_workspace({})

    assert set(ws) == {"_schema", "_version", "_saved_at"}
    assert ws["_schema"] == CURRENT_SCHEMA


def test_df_b64_roundtrip_loses_dtype_for_datetime_and_categorical():
    """【现状缺陷钉桩】df_b64 走 CSV 文本往返 ⇒ 非数值列的类型信息**静默丢失**：
    datetime64 回来是 str、category 回来是 str，且 decode 端不报错。
    导出链若按原类型使用这些列，必须自行 `parse_dates=`/`astype` 复原。"""
    df = pd.DataFrame({"日期": pd.to_datetime(["2026-01-02", "2026-01-03"]),
                       "等级": pd.Categorical(["低", "中"])})

    ws = _build_core_workspace({"df": df})
    back = pd.read_csv(io.StringIO(base64.b64decode(ws["df_b64"]).decode("utf-8")))

    assert str(back["日期"].dtype) == "str" and str(df["日期"].dtype) != "str"
    assert str(back["等级"].dtype) == "str"

    typed = pd.read_csv(io.StringIO(base64.b64decode(ws["df_b64"]).decode("utf-8")),
                        parse_dates=["日期"], dtype={"等级": "category"})
    assert str(typed["日期"].dtype).startswith("datetime")
