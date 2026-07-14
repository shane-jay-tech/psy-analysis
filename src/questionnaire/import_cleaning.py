"""问卷数据导入、清洗与量表计分。

支持问卷星/Excel/CSV 导入，自动识别题目列，反向计分，维度计分，无效样本标记。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import io

import numpy as np
import pandas as pd


@dataclass
class ColumnClassification:
    """列分类结果。"""
    item_columns: list[str] = field(default_factory=list)
    demographic_columns: list[str] = field(default_factory=list)
    metadata_columns: list[str] = field(default_factory=list)
    timestamp_columns: list[str] = field(default_factory=list)

    @property
    def all_identified(self) -> list[str]:
        return self.item_columns + self.demographic_columns + self.metadata_columns + self.timestamp_columns


@dataclass
class ScaleDimension:
    """量表维度定义。"""
    name: str
    items: list[str]
    reverse_items: list[str] = field(default_factory=list)
    max_score: int = 5
    min_score: int = 1


@dataclass
class CleaningLogEntry:
    """清洗日志条目。"""
    step: str
    action: str
    affected_rows: int = 0
    affected_cols: int = 0
    detail: str = ""


@dataclass
class CleaningResult:
    """清洗结果。"""
    df_cleaned: pd.DataFrame
    df_scored: Optional[pd.DataFrame] = None
    invalid_mask: Optional[pd.Series] = None
    log: list[CleaningLogEntry] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def classify_columns(df: pd.DataFrame) -> ColumnClassification:
    """自动识别列类型。"""
    result = ColumnClassification()
    metadata_keywords = {"id", "编号", "序号", "ip", "来源", "提交", "开始", "结束", "时长", "用时"}
    demo_keywords = {"性别", "年龄", "年级", "专业", "学历", "gender", "age", "grade"}
    timestamp_keywords = {"time", "date", "时间", "日期"}

    for col in df.columns:
        col_lower = col.lower().strip()

        if any(kw in col_lower for kw in timestamp_keywords):
            result.timestamp_columns.append(col)
        elif any(kw in col_lower for kw in metadata_keywords):
            result.metadata_columns.append(col)
        elif any(kw in col_lower for kw in demo_keywords):
            result.demographic_columns.append(col)
        elif _is_likert_column(df[col]):
            result.item_columns.append(col)
        else:
            result.demographic_columns.append(col)
    return result


def _is_likert_column(series: pd.Series) -> bool:
    """判断是否为 Likert 量表列。"""
    if series.dtype not in (np.int64, np.float64, int, float, "int64", "float64"):
        try:
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.isna().sum() > len(series) * 0.5:
                return False
            series = numeric
        except (ValueError, TypeError):
            return False

    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    unique_vals = sorted(non_null.unique())
    if len(unique_vals) < 2 or len(unique_vals) > 10:
        return False
    min_val = unique_vals[0]
    max_val = unique_vals[-1]
    if min_val >= 0 and max_val <= 10 and (max_val - min_val) <= 9:
        return True
    return False


def reverse_score(series: pd.Series, max_score: int = 5, min_score: int = 1) -> pd.Series:
    """反向计分。"""
    return (max_score + min_score) - series


def compute_dimension_scores(
    df: pd.DataFrame,
    dimensions: list[ScaleDimension],
) -> pd.DataFrame:
    """计算各维度得分（均分）。"""
    scored = pd.DataFrame(index=df.index)
    for dim in dimensions:
        dim_df = pd.DataFrame(index=df.index)
        for item in dim.items:
            if item not in df.columns:
                continue
            col_data = pd.to_numeric(df[item], errors="coerce")
            if item in dim.reverse_items:
                col_data = reverse_score(col_data, dim.max_score, dim.min_score)
            dim_df[item] = col_data
        if not dim_df.empty:
            scored[f"{dim.name}_mean"] = dim_df.mean(axis=1)
            scored[f"{dim.name}_sum"] = dim_df.sum(axis=1)
    return scored


def detect_invalid_responses(
    df: pd.DataFrame,
    item_columns: list[str],
    min_duration_seconds: float = 60,
    max_identical_ratio: float = 0.9,
    duration_column: Optional[str] = None,
) -> pd.Series:
    """检测无效作答。"""
    invalid = pd.Series(False, index=df.index)

    if duration_column and duration_column in df.columns:
        duration = pd.to_numeric(df[duration_column], errors="coerce")
        too_fast = duration < min_duration_seconds
        invalid = invalid | too_fast

    if item_columns:
        item_data = df[item_columns].apply(pd.to_numeric, errors="coerce")
        row_std = item_data.std(axis=1)
        identical = row_std == 0
        invalid = invalid | identical

        mode_count = item_data.apply(lambda row: row.value_counts().iloc[0] if len(row.dropna()) > 0 else 0, axis=1)
        total_items = item_data.notna().sum(axis=1)
        high_identical = (mode_count / total_items.clip(lower=1)) > max_identical_ratio
        invalid = invalid | high_identical

    return invalid


def run_questionnaire_cleaning(
    df: pd.DataFrame,
    dimensions: Optional[list[ScaleDimension]] = None,
    duration_column: Optional[str] = None,
    min_duration_seconds: float = 60,
    max_identical_ratio: float = 0.9,
) -> CleaningResult:
    """完整问卷清洗流程。"""
    log = []
    original_n = len(df)

    classification = classify_columns(df)
    log.append(CleaningLogEntry(
        step="列分类",
        action=f"识别 {len(classification.item_columns)} 题项列, "
               f"{len(classification.demographic_columns)} 人口学列, "
               f"{len(classification.metadata_columns)} 元数据列",
        affected_cols=len(classification.all_identified),
    ))

    item_cols = classification.item_columns
    invalid_mask = detect_invalid_responses(
        df, item_cols,
        min_duration_seconds=min_duration_seconds,
        max_identical_ratio=max_identical_ratio,
        duration_column=duration_column,
    )
    n_invalid = invalid_mask.sum()
    log.append(CleaningLogEntry(
        step="无效样本检测",
        action=f"标记 {n_invalid} 个无效样本",
        affected_rows=int(n_invalid),
        detail=f"作答时长过短或同质作答比例过高",
    ))

    df_cleaned = df[~invalid_mask].copy()
    log.append(CleaningLogEntry(
        step="样本清洗",
        action=f"保留 {len(df_cleaned)}/{original_n} 有效样本",
        affected_rows=original_n - len(df_cleaned),
    ))

    df_scored = None
    if dimensions:
        df_scored = compute_dimension_scores(df_cleaned, dimensions)
        log.append(CleaningLogEntry(
            step="量表计分",
            action=f"计算 {len(dimensions)} 个维度得分",
            affected_cols=len(dimensions) * 2,
        ))

    summary = {
        "original_n": original_n,
        "valid_n": len(df_cleaned),
        "invalid_n": int(n_invalid),
        "item_columns": len(item_cols),
        "dimensions_scored": len(dimensions) if dimensions else 0,
    }

    return CleaningResult(
        df_cleaned=df_cleaned,
        df_scored=df_scored,
        invalid_mask=invalid_mask,
        log=log,
        summary=summary,
    )


def export_cleaning_log(log: list[CleaningLogEntry], format: str = "markdown") -> str:
    """导出清洗日志。"""
    if format == "markdown":
        lines = ["# 数据清洗日志\n"]
        for i, entry in enumerate(log, 1):
            lines.append(f"## 步骤 {i}: {entry.step}\n")
            lines.append(f"- 操作: {entry.action}")
            if entry.affected_rows:
                lines.append(f"- 影响行数: {entry.affected_rows}")
            if entry.affected_cols:
                lines.append(f"- 影响列数: {entry.affected_cols}")
            if entry.detail:
                lines.append(f"- 说明: {entry.detail}")
            lines.append("")
        return "\n".join(lines)
    else:
        import json
        return json.dumps(
            [{"step": e.step, "action": e.action, "affected_rows": e.affected_rows,
              "affected_cols": e.affected_cols, "detail": e.detail} for e in log],
            ensure_ascii=False, indent=2,
        )
