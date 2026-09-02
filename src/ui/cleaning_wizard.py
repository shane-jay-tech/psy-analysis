"""数据清洗向导 — 把 DataQualityReport 翻译为可一键处理的 UI 选项。

设计：
- 接受 df + DataQualityReport
- 渲染卡片式问题列表，每个问题附「处理选项」
- 处理后返回新 df + cleaning log（可追溯，论文方法部分引用）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from src.analysis.data_quality import DataQualityReport, data_quality_check


@dataclass
class CleaningStep:
    """一次清洗操作的记录。"""
    action: str
    target_cols: List[str] = field(default_factory=list)
    before_shape: Tuple[int, int] = (0, 0)
    after_shape: Tuple[int, int] = (0, 0)
    description_zh: str = ""

    def summary(self) -> str:
        rows_diff = self.before_shape[0] - self.after_shape[0]
        cols_diff = self.before_shape[1] - self.after_shape[1]
        if rows_diff > 0:
            return f"{self.description_zh}（删除 {rows_diff} 行）"
        if cols_diff > 0:
            return f"{self.description_zh}（删除 {cols_diff} 列）"
        return self.description_zh


# --------------------------------------------------------------------------- #
# 清洗动作（纯函数，不依赖 streamlit）
# --------------------------------------------------------------------------- #

def drop_rows_with_missing(df: pd.DataFrame, cols: List[str]) -> Tuple[pd.DataFrame, CleaningStep]:
    before = df.shape
    new_df = df.dropna(subset=cols).reset_index(drop=True)
    return new_df, CleaningStep(
        action="drop_missing_rows", target_cols=cols,
        before_shape=before, after_shape=new_df.shape,
        description_zh=f"删除「{','.join(cols)}」存在缺失值的记录",
    )


def drop_constant_columns(df: pd.DataFrame, cols: List[str]) -> Tuple[pd.DataFrame, CleaningStep]:
    before = df.shape
    new_df = df.drop(columns=[c for c in cols if c in df.columns])
    return new_df, CleaningStep(
        action="drop_constant_cols", target_cols=cols,
        before_shape=before, after_shape=new_df.shape,
        description_zh=f"删除常数列（无变异）：{','.join(cols)}",
    )


def impute_mean(df: pd.DataFrame, cols: List[str]) -> Tuple[pd.DataFrame, CleaningStep]:
    before = df.shape
    new_df = df.copy()
    for col in cols:
        if col in new_df.columns:
            mean_val = pd.to_numeric(new_df[col], errors="coerce").mean()
            new_df[col] = pd.to_numeric(new_df[col], errors="coerce").fillna(mean_val)
    return new_df, CleaningStep(
        action="impute_mean", target_cols=cols,
        before_shape=before, after_shape=new_df.shape,
        description_zh=f"对「{','.join(cols)}」用列均值填补缺失",
    )


def impute_median(df: pd.DataFrame, cols: List[str]) -> Tuple[pd.DataFrame, CleaningStep]:
    before = df.shape
    new_df = df.copy()
    for col in cols:
        if col in new_df.columns:
            med = pd.to_numeric(new_df[col], errors="coerce").median()
            new_df[col] = pd.to_numeric(new_df[col], errors="coerce").fillna(med)
    return new_df, CleaningStep(
        action="impute_median", target_cols=cols,
        before_shape=before, after_shape=new_df.shape,
        description_zh=f"对「{','.join(cols)}」用列中位数填补缺失",
    )


def winsorize_outliers(df: pd.DataFrame, cols: List[str], k: float = 1.5) -> Tuple[pd.DataFrame, CleaningStep]:
    """IQR Winsorize：把超出 Q1-k*IQR / Q3+k*IQR 的值压到边界。"""
    before = df.shape
    new_df = df.copy()
    for col in cols:
        if col not in new_df.columns:
            continue
        s = pd.to_numeric(new_df[col], errors="coerce")
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        low, high = q1 - k * iqr, q3 + k * iqr
        new_df[col] = s.clip(lower=low, upper=high)
    return new_df, CleaningStep(
        action="winsorize", target_cols=cols,
        before_shape=before, after_shape=new_df.shape,
        description_zh=f"对「{','.join(cols)}」做 Winsorize（IQR 边界压缩，k={k}）",
    )


def coerce_to_numeric(df: pd.DataFrame, cols: List[str]) -> Tuple[pd.DataFrame, CleaningStep]:
    before = df.shape
    new_df = df.copy()
    for col in cols:
        if col in new_df.columns:
            new_df[col] = pd.to_numeric(new_df[col], errors="coerce")
    return new_df, CleaningStep(
        action="coerce_numeric", target_cols=cols,
        before_shape=before, after_shape=new_df.shape,
        description_zh=f"将「{','.join(cols)}」转换为数值类型",
    )


# --------------------------------------------------------------------------- #
# 渲染逻辑
# --------------------------------------------------------------------------- #

def is_complex_missing_scenario(report: DataQualityReport) -> bool:
    """v2.8: 判断是否为本向导无法妥善处理的复杂缺失场景。

    触发条件：总体缺失率 > 10%。
    """
    return bool(report.missing_pct > 10.0)


def render_scope_panel(*, expanded: bool, key_prefix: str = "clean"):
    """v2.8: 数据清洗向导的边界说明面板。"""
    with st.expander(
        "⚠️ 本向导的适用范围（点击展开）",
        expanded=expanded,
    ):
        if expanded:
            st.warning(
                "⚠ 你的数据缺失率较高（>10%），可能超出本向导的适用范围，"
                "强烈建议参考下方说明咨询导师或使用专业工具。"
            )
        st.markdown(
            """
**本向导处理本科论文常见的数据清洗场景：**

✅ **支持**：
- 缺失值删除（listwise 列表删除）
- 均值/中位数填补（单变量简单插补）
- 常数列检测与删除
- IQR 异常值识别与 Winsorize 处理
- 强制类型转换（字符串 → 数值）

❌ **不支持**：
- 多重插补（MICE / Multiple Imputation）
- 完全信息最大似然（FIML）
- 期望最大化（EM 算法）
- 模式混合插补、贝叶斯插补

**如果你的数据满足以下任一条件，建议咨询导师或使用专业工具：**

- 缺失率超过 10%
- 临床/纵向追踪数据
- 缺失机制非随机（MNAR — Missing Not At Random）
- 多变量复杂缺失模式（变量间缺失模式相关）

**专业工具推荐：**
- **R 语言**：`mice` 包（多重插补的金标准）
- **SPSS**：Missing Values 模块
- **Mplus**：FIML（结构方程模型最大似然估计）
- **Python**：`fancyimpute`、`scikit-learn` 的 `IterativeImputer`
            """
        )


def render_cleaning_wizard(df: pd.DataFrame, *, key_prefix: str = "clean") -> Tuple[
    pd.DataFrame, List[CleaningStep]
]:
    """主入口：渲染清洗向导，返回 (清洗后 df, 清洗日志)。

    使用 session_state 持久化：
    - {prefix}_df: 当前清洗后 df
    - {prefix}_log: 清洗步骤列表
    """
    df_key = f"{key_prefix}_df"
    log_key = f"{key_prefix}_log"

    if df_key not in st.session_state or st.session_state[df_key] is None:
        st.session_state[df_key] = df.copy()
        st.session_state[log_key] = []

    current_df: pd.DataFrame = st.session_state[df_key]
    log: List[CleaningStep] = st.session_state[log_key]

    # 重新跑质量检查（每次 rerun 后基于当前 df）
    numeric_cols = current_df.select_dtypes(include=[np.number]).columns.tolist()
    report = data_quality_check(current_df, numeric_cols=numeric_cols)

    # v2.8: 边界说明面板（缺失率高时自动展开）
    is_complex = is_complex_missing_scenario(report)
    render_scope_panel(expanded=is_complex, key_prefix=key_prefix)

    # 顶部摘要
    cols_summary = st.columns(4)
    cols_summary[0].metric("当前样本量", f"{current_df.shape[0]} 行")
    cols_summary[1].metric("变量数", f"{current_df.shape[1]} 列")
    cols_summary[2].metric("总体缺失率", f"{report.missing_pct:.1f}%")
    cols_summary[3].metric("已执行清洗", f"{len(log)} 步")

    # 健康度判定
    issues_count = (
        len(report.missing_cols) + len(report.zero_var_cols)
        + len(report.constant_cols) + len(report.outlier_cols)
    )
    if issues_count == 0:
        st.success("✅ 数据质量良好，无需清洗。可直接进入下一步分析。")
    else:
        st.warning(f"⚠ 检测到 {issues_count} 个数据质量问题，请逐项处理（或点击「一键应用建议」）。")

    # ── 一键应用建议 ──
    if issues_count > 0:
        if st.button(
            "🪄 一键应用所有建议（保守策略：删常数列 + 列表删缺失）",
            type="primary", width="stretch",
            key=f"{key_prefix}_auto",
        ):
            new_df = current_df
            if report.constant_cols:
                new_df, step = drop_constant_columns(new_df, report.constant_cols)
                log.append(step)
            missing_critical = [
                c for c in report.missing_cols
                if c in new_df.columns
            ]
            if missing_critical:
                new_df, step = drop_rows_with_missing(new_df, missing_critical)
                log.append(step)
            st.session_state[df_key] = new_df
            st.session_state[log_key] = log
            st.rerun()

    # ── 逐项处理 ──
    if report.constant_cols:
        with st.expander(f"🚫 常数列（{len(report.constant_cols)}）— 强烈建议删除", expanded=True):
            st.markdown(f"以下列只有一个取值，无法用于任何统计分析：**{', '.join(report.constant_cols)}**")
            if st.button("删除这些列", key=f"{key_prefix}_drop_const"):
                new_df, step = drop_constant_columns(current_df, report.constant_cols)
                st.session_state[df_key] = new_df
                log.append(step)
                st.rerun()

    if report.missing_cols:
        with st.expander(f"❓ 缺失值（{len(report.missing_cols)} 列）", expanded=True):
            preview = current_df[report.missing_cols].isna().sum().to_frame("缺失数")
            preview["缺失率"] = (preview["缺失数"] / len(current_df) * 100).round(1).astype(str) + "%"
            st.dataframe(preview, width="stretch")

            target = st.multiselect(
                "选择要处理的列",
                report.missing_cols,
                default=report.missing_cols,
                key=f"{key_prefix}_miss_cols",
            )

            cols = st.columns(3)
            if cols[0].button("删除含缺失的行", key=f"{key_prefix}_drop_miss",
                              disabled=not target):
                new_df, step = drop_rows_with_missing(current_df, target)
                st.session_state[df_key] = new_df
                log.append(step)
                st.rerun()
            if cols[1].button("均值填补", key=f"{key_prefix}_imp_mean", disabled=not target):
                new_df, step = impute_mean(current_df, target)
                st.session_state[df_key] = new_df
                log.append(step)
                st.rerun()
            if cols[2].button("中位数填补", key=f"{key_prefix}_imp_med", disabled=not target):
                new_df, step = impute_median(current_df, target)
                st.session_state[df_key] = new_df
                log.append(step)
                st.rerun()

            st.caption(
                "💡 选择建议：(1) 缺失 < 5% → 删除行；(2) 5-15% → 中位数填补；"
                "(3) > 15% → 考虑改用多重插补或全信息最大似然 (FIML)"
            )

    if report.outlier_cols:
        with st.expander(f"📍 异常值（{len(report.outlier_cols)} 列）", expanded=False):
            st.markdown(
                f"以下列含 IQR 异常值：**{', '.join(report.outlier_cols)}**。"
                "建议：先确认是否为录入错误，再决定是否处理。"
            )
            target = st.multiselect(
                "选择 Winsorize 处理的列（保守做法，把极端值压到边界）",
                report.outlier_cols,
                key=f"{key_prefix}_out_cols",
            )
            if st.button("Winsorize（IQR 1.5 倍边界）", key=f"{key_prefix}_winz",
                         disabled=not target):
                new_df, step = winsorize_outliers(current_df, target, k=1.5)
                st.session_state[df_key] = new_df
                log.append(step)
                st.rerun()

    # ── 已执行步骤 + 撤销 ──
    if log:
        with st.expander(f"📋 已执行步骤（{len(log)} 步，可撤销）", expanded=False):
            for i, step in enumerate(log, start=1):
                cols = st.columns([5, 1])
                cols[0].markdown(f"{i}. {step.summary()}")
            if st.button("⏪ 全部撤销，恢复原始数据", key=f"{key_prefix}_reset",
                         type="secondary"):
                st.session_state[df_key] = df.copy()
                st.session_state[log_key] = []
                st.rerun()

    return current_df, log


def cleaning_log_to_method_paragraph(log: List[CleaningStep]) -> str:
    """把清洗日志转为论文方法部分的中文段落。"""
    if not log:
        return ""
    parts = ["在数据分析前，我们对数据进行了以下预处理："]
    for i, step in enumerate(log, start=1):
        parts.append(f"({i}) {step.summary()}；")
    return "\n".join(parts)
