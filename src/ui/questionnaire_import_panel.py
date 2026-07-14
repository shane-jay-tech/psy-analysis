"""问卷导入清洗 Streamlit 面板。

分步向导：上传 → 列识别 → 维度设置 → 反向题 → 清洗 → 计分 → 下一步。
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.questionnaire.import_cleaning import (
    ColumnClassification,
    ScaleDimension,
    CleaningResult,
    classify_columns,
    run_questionnaire_cleaning,
    export_cleaning_log,
)

_CLEANED_KEY = "questionnaire_cleaned_result"
_DIMENSIONS_KEY = "questionnaire_dimensions"
_RAW_DF_KEY = "questionnaire_raw_df"


def render_questionnaire_import_panel(session_state: dict | None = None):
    """渲染问卷导入清洗面板。"""
    if session_state is None:
        session_state = st.session_state

    st.subheader("📋 问卷导入与清洗")

    tab1, tab2, tab3, tab4 = st.tabs(["上传数据", "列识别与维度", "清洗与计分", "结果与导出"])

    with tab1:
        _render_upload(session_state)
    with tab2:
        _render_column_config(session_state)
    with tab3:
        _render_cleaning(session_state)
    with tab4:
        _render_results(session_state)


def _render_upload(session_state: dict):
    """上传数据文件。"""
    uploaded = st.file_uploader("上传问卷数据", type=["csv", "xlsx", "xls"])
    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            session_state[_RAW_DF_KEY] = df
            st.success(f"已加载 {len(df)} 行 x {len(df.columns)} 列")
            st.dataframe(df.head(5))
        except Exception as e:
            st.error(f"读取失败: {e}")

    if _RAW_DF_KEY in session_state and session_state[_RAW_DF_KEY] is not None:
        df = session_state[_RAW_DF_KEY]
        st.caption(f"当前数据: {len(df)} 行, {len(df.columns)} 列")


def _render_column_config(session_state: dict):
    """列识别和维度配置。"""
    df = session_state.get(_RAW_DF_KEY)
    if df is None:
        st.info("请先在上传数据中加载文件")
        return

    classification = classify_columns(df)
    st.markdown("### 自动识别结果")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**题项列** ({len(classification.item_columns)}): {', '.join(classification.item_columns[:10])}")
        st.markdown(f"**人口学** ({len(classification.demographic_columns)}): {', '.join(classification.demographic_columns)}")
    with col2:
        st.markdown(f"**元数据** ({len(classification.metadata_columns)}): {', '.join(classification.metadata_columns)}")
        st.markdown(f"**时间戳** ({len(classification.timestamp_columns)}): {', '.join(classification.timestamp_columns)}")

    st.markdown("### 维度配置")
    st.caption("配置量表的维度结构（每个维度包含哪些题项、哪些是反向题）")

    dims = session_state.get(_DIMENSIONS_KEY, [])
    n_dims = st.number_input("维度数量", min_value=1, max_value=10, value=max(len(dims), 1))

    new_dims = []
    for i in range(n_dims):
        with st.expander(f"维度 {i + 1}", expanded=(i == 0)):
            existing = dims[i] if i < len(dims) else None
            name = st.text_input(
                f"维度名称", value=existing.name if existing else f"维度{i + 1}",
                key=f"dim_name_{i}",
            )
            items_str = st.text_input(
                "题项列（逗号分隔）",
                value=",".join(existing.items) if existing else "",
                key=f"dim_items_{i}",
                placeholder="Q1,Q2,Q3,Q4,Q5",
            )
            reverse_str = st.text_input(
                "反向题（逗号分隔）",
                value=",".join(existing.reverse_items) if existing else "",
                key=f"dim_reverse_{i}",
                placeholder="Q3",
            )
            col1, col2 = st.columns(2)
            with col1:
                max_score = st.number_input(
                    "最高分", value=existing.max_score if existing else 5,
                    key=f"dim_max_{i}",
                )
            with col2:
                min_score = st.number_input(
                    "最低分", value=existing.min_score if existing else 1,
                    key=f"dim_min_{i}",
                )
            items = [x.strip() for x in items_str.split(",") if x.strip()]
            reverse = [x.strip() for x in reverse_str.split(",") if x.strip()]
            new_dims.append(ScaleDimension(
                name=name, items=items, reverse_items=reverse,
                max_score=int(max_score), min_score=int(min_score),
            ))

    if st.button("保存维度配置"):
        session_state[_DIMENSIONS_KEY] = new_dims
        st.success(f"已保存 {len(new_dims)} 个维度")


def _render_cleaning(session_state: dict):
    """执行清洗和计分。"""
    df = session_state.get(_RAW_DF_KEY)
    dims = session_state.get(_DIMENSIONS_KEY, [])

    if df is None:
        st.info("请先上传数据")
        return

    st.markdown("### 无效样本检测规则")
    col1, col2 = st.columns(2)
    with col1:
        min_duration = st.number_input("最短作答时长（秒）", value=60, min_value=0)
    with col2:
        max_identical = st.slider("同质作答阈值", 0.5, 1.0, 0.9, 0.05)

    duration_col = None
    duration_candidates = [c for c in df.columns if any(k in c.lower() for k in ["时长", "用时", "duration", "time"])]
    if duration_candidates:
        duration_col = st.selectbox("作答时长列", ["(不使用)"] + duration_candidates)
        if duration_col == "(不使用)":
            duration_col = None

    if st.button("执行清洗与计分", type="primary"):
        result = run_questionnaire_cleaning(
            df,
            dimensions=dims if dims else None,
            duration_column=duration_col,
            min_duration_seconds=min_duration,
            max_identical_ratio=max_identical,
        )
        session_state[_CLEANED_KEY] = result
        st.success(
            f"清洗完成: {result.summary['valid_n']}/{result.summary['original_n']} 有效, "
            f"剔除 {result.summary['invalid_n']} 无效样本"
        )


def _render_results(session_state: dict):
    """展示清洗结果和导出。"""
    result: CleaningResult | None = session_state.get(_CLEANED_KEY)
    if result is None:
        st.info("请先执行清洗")
        return

    st.markdown("### 清洗摘要")
    col1, col2, col3 = st.columns(3)
    col1.metric("原始样本", result.summary["original_n"])
    col2.metric("有效样本", result.summary["valid_n"])
    col3.metric("剔除样本", result.summary["invalid_n"])

    if result.df_scored is not None:
        st.markdown("### 维度得分预览")
        st.dataframe(result.df_scored.head(10))

    st.markdown("### 清洗日志")
    for entry in result.log:
        st.markdown(f"- **{entry.step}**: {entry.action}")

    md_log = export_cleaning_log(result.log, format="markdown")
    st.download_button("📥 下载清洗日志", md_log, "cleaning_log.md", "text/markdown")

    st.markdown("### 下一步")
    st.info("清洗完成后可进入: 信度分析 / 描述统计 / 方法推荐向导")


def get_cleaned_result(session_state: dict) -> CleaningResult | None:
    """获取清洗结果（供外部使用）。"""
    return session_state.get(_CLEANED_KEY)


def get_cleaning_log_for_deliverable(session_state: dict) -> list[dict]:
    """获取清洗日志用于交付包。"""
    result = session_state.get(_CLEANED_KEY)
    if result is None:
        return []
    return [{"step": e.step, "action": e.action, "affected_rows": e.affected_rows,
             "affected_cols": e.affected_cols, "detail": e.detail} for e in result.log]
