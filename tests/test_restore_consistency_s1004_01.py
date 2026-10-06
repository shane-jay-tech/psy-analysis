# -*- coding: utf-8 -*-
"""s1004-01：恢复路径一致性测试（df-only 源点封死验证 + 其余键照恢复的②③面）。

结论前提复核（本单第一步）：s930-01 遗留 2「恢复路径 :634 只 set df 仍是源点」
**已被 s927-28 案 a（fd78891，09-28）消化**——restore_workspace 现值为四键闸
（df_b64 齐四键才写 df，缺任一整组不写）。矿源「只 set df」形态在 HEAD 已不存在，
本单无可补缺口，改判报告型 + 补一致性验证三例（任务书③兑现）。
"""
from __future__ import annotations

import base64
import io
import json

import pandas as pd
import pytest
import streamlit as st

from src.utils.workspace import CURRENT_SCHEMA, restore_workspace

PARTNER_KEYS = ("meta", "inspector", "file_name", "analysis_history")


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})


def _csv_b64(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return base64.b64encode(buf.getvalue().encode("utf-8")).decode("ascii")


def _project_file(tmp_path, payload: dict, name: str = "proj.json"):
    p = tmp_path / name
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    loaded = json.loads(p.read_text(encoding="utf-8"))
    return p, loaded


@pytest.fixture(autouse=True)
def _clean_session():
    st.session_state.clear()
    yield
    st.session_state.clear()


def test_complete_payload_restores_df_and_all_partner_keys(tmp_path):
    """②③面正向：四键齐备的快照恢复后，df 与四键逐键与快照一致（一致性断言）。"""
    df = _sample_df()
    meta = {"project": "测试", "created": "2026-10-07"}
    inspector = {"rows": 2, "cols": 2}
    payload = {"_schema": CURRENT_SCHEMA, "df_b64": _csv_b64(df),
               "meta": meta, "inspector": inspector,
               "file_name": "demo.csv", "analysis_history": ["run1"]}
    _p, loaded = _project_file(tmp_path, payload)

    restored = restore_workspace(loaded)

    assert restored >= 5
    pd.testing.assert_frame_equal(st.session_state.df, df)
    for k, expect in (("meta", meta), ("inspector", inspector),
                      ("file_name", "demo.csv"), ("analysis_history", ["run1"])):
        assert st.session_state.get(k) == expect, f"{k} 恢复后与快照不一致"


def test_df_only_snapshot_still_refused_source_sealed(tmp_path):
    """df-only 快照（源点形态）：整组不写＝源点已被案 a 封死（s930-01 遗留 2 前提不成立）。"""
    payload = {"_schema": CURRENT_SCHEMA, "df_b64": _csv_b64(_sample_df())}
    _p, loaded = _project_file(tmp_path, payload)

    restored = restore_workspace(loaded)

    assert restored == 0
    assert st.session_state.get("df") is None


def test_partial_keys_restore_others_while_df_blocked(tmp_path):
    """②③面（案 a 边界）：缺 analysis_history 时 df 不写，其余三键照恢复。"""
    df = _sample_df()
    payload = {"_schema": CURRENT_SCHEMA, "df_b64": _csv_b64(df),
               "meta": {"project": "p"}, "inspector": {"rows": 2},
               "file_name": "f.csv"}
    # 故意不含 analysis_history
    _p, loaded = _project_file(tmp_path, payload)

    restored = restore_workspace(loaded)

    assert st.session_state.get("df") is None
    assert st.session_state.get("meta") == {"project": "p"}
    assert st.session_state.get("inspector") == {"rows": 2}
    assert st.session_state.get("file_name") == "f.csv"
    assert st.session_state.get("analysis_history") is None
