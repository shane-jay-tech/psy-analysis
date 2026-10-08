"""问卷数据导入、清洗与量表计分。

支持问卷星/Excel/CSV 导入，自动识别题目列，反向计分，维度计分，无效样本标记。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import io
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


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
    out_of_range_counts: Optional[dict] = None,
) -> pd.DataFrame:
    """计算各维度得分（均分）。

    案 a（决议#17，2026-10-09 用户裁决「非法输入直接报错不静默」；c47f 案 a 原文
    「reverse_score 前按字典量尺做越界校验并抛错」）：越界值在计分前**直接抛
    ValueError**——错误信息含列名、量表域、越界数与首处行索引，**不含原始值**。
    历史：r5 B1（2026-09-27）曾裁 mask+count（置 NaN＋out_of_range_counts 播报）；
    本裁决升格为最严案，mask 路径退役（counts 仍先记账再抛，供上层日志留痕）。
    清洗管道（clean_questionnaire）先行整行剔除无效样本 ⇒ 正常管道流不受扰；
    直调计分入口遇脏数据即抛＝「静默计分」面终结。
    """
    scored = pd.DataFrame(index=df.index)
    for dim in dimensions:
        dim_df = pd.DataFrame(index=df.index)
        for item in dim.items:
            if item not in df.columns:
                continue
            col_data = pd.to_numeric(df[item], errors="coerce")
            lo, hi = float(dim.min_score), float(dim.max_score)
            out_of_range = col_data.notna() & ((col_data < lo) | (col_data > hi))
            n_out = int(out_of_range.sum())
            if n_out:
                if out_of_range_counts is not None:
                    out_of_range_counts[item] = out_of_range_counts.get(item, 0) + n_out
                raise ValueError(
                    f"越界值校验失败（案 a，决议#17）：列 {item} 存在 {n_out} 个"
                    f"量表域 [{lo:g}, {hi:g}] 之外的取值"
                    f"（首个位置：行索引 {out_of_range.idxmax()}）——非法输入不静默计分"
                )
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
    item_ranges: Optional[dict] = None,
) -> pd.Series:
    """检测无效作答。

    r5 B1：新增 `item_ranges={题项: (lo, hi)}`（**逐题项**的量表取值范围）——把含越界作答的
    行也标成无效。逐题项而非"全局一个区间"：多维度问卷里同一张表可能混着 1-5 与 1-7 两种尺
    （评审 F-001/F-004），全局区间会既放过 A 维的 6、又误杀 B 维的 6。
    不传时行为与本改前逐位一致（向后兼容，既有调用方零改动）；非数值内容先经 `to_numeric`
    归一为 NaN，故 NaN/空串/文本不会被误判成越界（评审 F-003 复核：该归一在本函数既有实现里就有）。
    """
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

        if item_ranges:
            hit = pd.Series(False, index=item_data.index)
            for col in item_data.columns:
                rng = item_ranges.get(col)
                if not rng:
                    continue
                lo, hi = float(rng[0]), float(rng[1])
                hit = hit | ((item_data[col] < lo) | (item_data[col] > hi))
            invalid = invalid | hit.fillna(False)

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
    # r5 B1：量表取值范围从维度定义现取（多维度时取并集），交给无效样本检测做越界判据。
    item_ranges: dict = {}
    for _d in dimensions or []:
        _rng = (float(_d.min_score), float(_d.max_score))
        for _it in _d.items:
            if _it in item_ranges and tuple(item_ranges[_it]) != _rng:
                # 同一题项被两个维度声明了不同尺 ⇒ 取交集（更严的一侧），并留痕供人工核对
                _lo = max(item_ranges[_it][0], _rng[0])
                _hi = min(item_ranges[_it][1], _rng[1])
                item_ranges[_it] = (_lo, _hi)
                logger.warning("题项 %s 被多个维度声明了不同量表范围，按交集取 (%.2f, %.2f)",
                               _it, _lo, _hi)
            else:
                item_ranges[_it] = _rng
    # r5 B1：越界单元格在**行过滤之前**先在原始作答上数一遍——否则含越界的行会被
    # "无效样本"整行剔掉，日志里就再也看不见"越界发生过"（静默吞掉正是本单要治的形态）。
    raw_out_of_range: dict = {}
    out_of_range_rows = 0
    if item_ranges and item_cols:
        _items = df[item_cols].apply(pd.to_numeric, errors="coerce")
        _row_hit = pd.Series(False, index=df.index)
        for _col in item_cols:
            _rng = item_ranges.get(_col)
            if not _rng:
                continue
            _lo, _hi = float(_rng[0]), float(_rng[1])
            _hit = (_items[_col] < _lo) | (_items[_col] > _hi)
            _n = int(_hit.fillna(False).sum())
            if _n:
                raw_out_of_range[_col] = _n
                _row_hit = _row_hit | _hit.fillna(False)
        out_of_range_rows = int(_row_hit.sum())
    invalid_mask = detect_invalid_responses(
        df, item_cols,
        min_duration_seconds=min_duration_seconds,
        max_identical_ratio=max_identical_ratio,
        duration_column=duration_column,
        item_ranges=item_ranges or None,
    )
    n_invalid = invalid_mask.sum()
    log.append(CleaningLogEntry(
        step="无效样本检测",
        action=f"标记 {n_invalid} 个无效样本",
        affected_rows=int(n_invalid),
        detail="作答时长过短、同质作答比例过高，或量表越界（越界详解见下一步）",
    ))
    if raw_out_of_range:
        _total_raw = sum(raw_out_of_range.values())
        log.append(CleaningLogEntry(
            step="越界值处置",
            action=f"原始作答中检出 {_total_raw} 个越界单元格，涉及 {out_of_range_rows} 行"
                   f"（这些行按无效样本整行剔除；口径＝逐题项量表范围）",
            affected_rows=out_of_range_rows,
            affected_cols=len(raw_out_of_range),
            detail="逐列：" + "、".join(
                f"{k}×{v}" for k, v in sorted(raw_out_of_range.items())[:10]),
        ))

    df_cleaned = df[~invalid_mask].copy()
    log.append(CleaningLogEntry(
        step="样本清洗",
        action=f"保留 {len(df_cleaned)}/{original_n} 有效样本",
        affected_rows=original_n - len(df_cleaned),
    ))

    df_scored = None
    out_of_range_counts: dict = {}
    if dimensions:
        df_scored = compute_dimension_scores(
            df_cleaned, dimensions, out_of_range_counts=out_of_range_counts)
        log.append(CleaningLogEntry(
            step="量表计分",
            action=f"计算 {len(dimensions)} 个维度得分",
            affected_cols=len(dimensions) * 2,
        ))
        if out_of_range_counts:
            total_out = sum(out_of_range_counts.values())
            log.append(CleaningLogEntry(
                step="越界值处置",
                action=f"置空 {total_out} 个越界作答（不计入维度分）",
                affected_cols=len(out_of_range_counts),
                detail="逐列：" + "、".join(
                    f"{k}×{v}" for k, v in sorted(out_of_range_counts.items())[:10]),
            ))

    summary = {
        "original_n": original_n,
        "valid_n": len(df_cleaned),
        "invalid_n": int(n_invalid),
        "item_columns": len(item_cols),
        "dimensions_scored": len(dimensions) if dimensions else 0,
        # r5 B1（评审 F-002）：单一口径——out_of_range_cells 只数"原始题项单元格越界"。
        # 计分阶段的残留单独记在 out_of_range_cells_after_filter（越界行已被整行剔除时恒 0），
        # 两者语义不同、不相加，避免同一单元格被重复计数或误读成两批事件。
        "out_of_range_cells": sum(raw_out_of_range.values()),
        "out_of_range_rows": out_of_range_rows,
        "out_of_range_cells_after_filter": sum(out_of_range_counts.values()),
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
