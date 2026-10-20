# -*- coding: utf-8 -*-
"""s930-01：快照写侧 df/inspector 成对（q927-28 遗留·写侧补法①）。

q927-28/s922-108 已证：「df 有、inspector 尚未跑」的正常中间态经
build_workspace_snapshot 自然产出 df-only 快照文件（恢复侧 s927-28 案 a 整组拦下）。
写侧补法①＝df 落快照时 inspector 缺席则当场跑 inspect_dataframe 并回填 session。

三钉：
  P1 成对：df 在 / inspector None ⇒ 快照含 inspector 键且 session 被回填；
  P2 幂等：inspector 已在 ⇒ 不重跑（不覆盖用户既有 inspector 对象）；
  P3 变异锚：inspect_dataframe 抛异常 ⇒ 维持 df-only（不炸快照）。

运行：python -m pytest tests/test_workspace_pair_write_s93001.py -q
"""
import pandas as pd
import streamlit as st

from src.utils.workspace import build_workspace_snapshot


def _setup_df_only():
    st.session_state.clear()
    st.session_state.df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    st.session_state.pop("inspector", None)


def test_p1_snapshot_pairs_inspector_and_backfills_session():
    """P1 成对：df-only session ⇒ 快照带 inspector＋session 回填（修复前此例红）。"""
    _setup_df_only()
    ws = build_workspace_snapshot()
    assert "df_b64" in ws
    assert "inspector" in ws, "df 落快照必须成对补 inspector（df-only 中间态未消除）"
    assert ws["inspector"], "成对补跑的 inspector 不应为空"
    assert st.session_state.get("inspector") == ws["inspector"], "session 未回填"


def test_p2_existing_inspector_is_not_overwritten():
    """P2 幂等：inspector 已在 ⇒ 保持用户既有对象（成对逻辑只在缺席时补）。"""
    _setup_df_only()
    sentinel = {"n_rows": 2, "marker": "user-kept"}
    st.session_state.inspector = sentinel
    ws = build_workspace_snapshot()
    assert ws["inspector"] is sentinel, "既有 inspector 被覆盖＝P2 破坏"


def test_p3_inspector_failure_keeps_df_only(monkeypatch):
    """P3 变异锚：inspect_dataframe 抛异常 ⇒ 快照不炸、维持 df-only（恢复侧有拦截）。"""
    _setup_df_only()
    import src.utils.workspace as ws_mod

    def _boom(df):
        raise RuntimeError("synthetic inspect failure")

    monkeypatch.setattr("src.data.inspector.inspect_dataframe", _boom)
    ws = build_workspace_snapshot()          # 不抛＝通过
    assert "df_b64" in ws
    assert "inspector" not in ws             # 检查失败 ⇒ 维持 df-only（恢复侧拦）
    assert "inspector" not in st.session_state
