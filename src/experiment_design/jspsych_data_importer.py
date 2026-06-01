"""jsPsych v6/v7 数据导入与预处理

支持 jsPsych v6 和 v7 CSV/JSON 格式的解析、清理和格式转换。
处理 jsPsych 典型的数据结构：嵌套JSON字段、时间戳、试次内变量。
v6 与 v7 的关键差异已通过自动检测和兼容路径处理。
"""

import csv
import json
import re
from io import StringIO
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd


# jsPsych v7 典型列名映射
_JSPsych_COLUMN_MAP = {
    "rt": "反应时_ms",
    "response": "反应",
    "stimulus": "刺激材料",
    "correct": "正确性",
    "trial_type": "试次类型",
    "trial_index": "试次序号",
    "time_elapsed": "累计时间_ms",
    "internal_node_id": "内部节点ID",
    "question": "题目文本",
    "choices": "选项列表",
    "button_pressed": "按键",
    "key_press": "按键码",
    "data": "自定义数据",
    "sender": "插件名称",
    "success": "数据保存状态",
}


@dataclass
class JsPsychData:
    """解析后的 jsPsych 数据结构"""
    raw_df: pd.DataFrame
    trial_df: pd.DataFrame              # 试次级数据（展开后）
    subject_ids: List[str]
    n_subjects: int
    n_trials_total: int
    trial_types: List[str]
    metadata: Dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    column_mapping: Dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"jsPsych数据集：{self.n_subjects}名被试，"
            f"共{self.n_trials_total}个试次，"
            f"试次类型：{', '.join(self.trial_types[:5])}"
            f"{'...' if len(self.trial_types) > 5 else ''}"
        )


def parse_jspsych_csv(
    filepath_or_buffer: str,
    subject_col: str = "subject",
    drop_empty_trials: bool = True,
    flatten_json_cols: bool = True,
    encoding: str = "utf-8-sig",
    jspsych_version: Optional[str] = None,
) -> JsPsychData:
    """
    解析 jsPsych v6/v7 导出的 CSV 文件，自动清洗并转换为分析就绪的 DataFrame。

    参数：
        filepath_or_buffer: CSV 文件路径或可读缓冲区
        subject_col: 被试ID列名（默认 "subject"，也兼容 "_worker_id" / "PROLIFIC_PID"）
        drop_empty_trials: 是否删除无反应的空试次
        flatten_json_cols: 是否展开JSON格式的列（如 data 列）
        encoding: 文件编码，默认 utf-8-sig（兼容BOM）
        jspsych_version: "v6" / "v7" / None（自动检测），指定 jsPsych 版本以应用兼容路径

    返回：
        JsPsychData 对象，包含原始数据、试次级数据、元信息等
    """
    warnings = []

    # 尝试多种编码
    df = None
    for enc in [encoding, "utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]:
        try:
            df = pd.read_csv(filepath_or_buffer, encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if df is None:
        raise ValueError(
            f"无法读取CSV文件，尝试了多种编码均失败。"
            f"请检查文件是否为有效的CSV格式。"
        )

    original_n = len(df)
    metadata = {
        "source": str(filepath_or_buffer),
        "encoding_used": enc,
        "original_rows": original_n,
        "original_cols": len(df.columns),
        "parse_time": datetime.now(timezone.utc).isoformat(),
    }

    # --- 自动检测 jsPsych 版本 ---
    if jspsych_version is None:
        # v7 特征: 有 sender 列, internal_node_id 列
        # v6 特征: 有 plugin 列, 无 sender
        if "sender" in df.columns or "internal_node_id" in df.columns:
            jspsych_version = "v7"
        elif "plugin" in df.columns:
            jspsych_version = "v6"
        else:
            # 从 trial_type 内容判断：v6 trial_type 是插件名（html-keyboard-response等）
            if "trial_type" in df.columns:
                sample = df["trial_type"].dropna().iloc[0] if len(df) > 0 else ""
                if isinstance(sample, str) and ("html-" in sample or "survey-" in sample or "image-" in sample):
                    jspsych_version = "v6"
                else:
                    jspsych_version = "v7"
            else:
                jspsych_version = "v7"
    metadata["jspsych_version"] = jspsych_version

    # --- v6 兼容处理 ---
    if jspsych_version == "v6":
        # v6 的 trial_type 引用插件名，实际的实验条件可能在 data 列或 stimulus 列中
        if "trial_type" in df.columns and flatten_json_cols:
            # 尝试从 trial_type 提取有意义信息
            warnings.append(
                "检测到 jsPsych v6 格式数据。trial_type 列为插件名，"
                "实验条件信息可能存储在 data 列或 stimulus 列中。"
            )
        # v6 可能缺少某些 v7 专有列，添加占位
        if "sender" not in df.columns:
            df["sender"] = "jspsych-v6"

    # --- 识别被试ID列 ---
    id_col = _detect_subject_column(df, subject_col)
    metadata["subject_col"] = id_col

    # --- 识别 jsPsych 列并映射 ---
    col_mapping = {}
    for col in df.columns:
        if col in _JSPsych_COLUMN_MAP:
            col_mapping[col] = _JSPsych_COLUMN_MAP[col]
    metadata["jspsych_columns_found"] = list(col_mapping.keys())

    # --- 移除 jsPsych 内部列 ---
    internal_patterns = [
        r"^view_history", r"^stimulus", r"^mouse_track",
        r"^canvas_", r"^webgazer_", r"^interactive_",
    ]
    cols_to_drop = []
    for col in df.columns:
        if any(re.match(p, col) for p in internal_patterns):
            cols_to_drop.append(col)
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        metadata["dropped_internal_cols"] = cols_to_drop

    # --- 检测试次类型 ---
    trial_type_col = None
    for candidate in ["trial_type", "task", "phase", "block_type"]:
        if candidate in df.columns:
            trial_type_col = candidate
            break

    if trial_type_col:
        trial_types = df[trial_type_col].dropna().unique().tolist()
    else:
        trial_types = []
    metadata["trial_type_col"] = trial_type_col

    # --- 展开 JSON 列 ---
    if flatten_json_cols:
        df = _flatten_json_data_column(df, warnings)

    # --- 提取被试列表 ---
    if id_col and id_col in df.columns:
        subject_ids = df[id_col].dropna().unique().tolist()
    else:
        subject_ids = ["unknown"]
        warnings.append("未找到被试ID列，所有数据视为同一被试。")

    # --- 删除空试次 ---
    if drop_empty_trials:
        before = len(df)
        df = _drop_empty_trials(df, warnings)
        after = len(df)
        if before != after:
            metadata["dropped_empty_trials"] = before - after

    # --- 标准化列名 ---
    df = _normalize_jspsych_columns(df)

    # --- 反应时自动检测与转换 ---
    df = _detect_and_convert_rt(df, warnings)

    n_subjects = len(subject_ids)
    n_trials = len(df)

    return JsPsychData(
        raw_df=pd.read_csv(filepath_or_buffer, encoding=enc),
        trial_df=df,
        subject_ids=subject_ids,
        n_subjects=n_subjects,
        n_trials_total=n_trials,
        trial_types=trial_types,
        metadata=metadata,
        warnings=warnings,
        column_mapping=col_mapping,
    )


def parse_jspsych_json(
    filepath: str,
    encoding: str = "utf-8",
) -> JsPsychData:
    """
    解析 jsPsych 的 JSON 行格式数据（每行一个试次的JSON对象）。

    部分 jsPsych 版本以 JSONL 格式存储数据。
    """
    trials = []
    warnings = []

    with open(filepath, "r", encoding=encoding) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                trial = json.loads(line)
                trials.append(trial)
            except json.JSONDecodeError:
                warnings.append(f"第{line_num}行JSON解析失败")

    if not trials:
        raise ValueError("未能从文件中解析到任何有效的JSON试次数据。")

    df = pd.DataFrame(trials)
    df = _normalize_jspsych_columns(df)
    df = _detect_and_convert_rt(df, warnings)

    # 检测被试ID
    subject_ids = []
    for col in ["subject", "worker_id", "PROLIFIC_PID", "participant_id"]:
        if col in df.columns:
            subject_ids = df[col].dropna().unique().tolist()
            break
    if not subject_ids:
        subject_ids = ["unknown"]

    trial_type_col = None
    for c in ["trial_type", "task", "phase"]:
        if c in df.columns:
            trial_type_col = c
            break
    trial_types = df[trial_type_col].dropna().unique().tolist() if trial_type_col else []

    return JsPsychData(
        raw_df=df.copy(),
        trial_df=df,
        subject_ids=subject_ids,
        n_subjects=len(subject_ids),
        n_trials_total=len(df),
        trial_types=trial_types,
        metadata={
            "source": filepath,
            "format": "jsonl",
            "parse_time": datetime.now(timezone.utc).isoformat(),
            "total_trials": len(trials),
        },
        warnings=warnings,
    )


def to_wide_format(
    jsdata: JsPsychData,
    subject_col: str = "subject",
    pivot_col: str = "trial_type",
    agg_col: str = "rt",
    agg_func: str = "mean",
) -> pd.DataFrame:
    """
    将 jsPsych 长格式数据转换为被试×条件宽格式。

    参数：
        jsdata: JsPsychData 对象
        subject_col: 被试列名
        pivot_col: 用于展开的列（如 trial_type）
        agg_col: 聚合的列（如 rt）
        agg_func: 聚合函数，'mean' 或 'median'

    返回：
        宽格式 DataFrame，行=被试，列=条件
    """
    df = jsdata.trial_df.copy()
    if subject_col not in df.columns or pivot_col not in df.columns:
        raise ValueError(
            f"缺少必要的列：{subject_col} 或 {pivot_col}。"
            f"可用列：{list(df.columns)}"
        )

    if agg_col not in df.columns:
        raise ValueError(f"聚合列 '{agg_col}' 不存在。可用列：{list(df.columns)}")

    agg = "mean" if agg_func == "mean" else "median"
    pivot_df = df.pivot_table(
        index=subject_col,
        columns=pivot_col,
        values=agg_col,
        aggfunc=agg,
    ).reset_index()

    pivot_df.columns.name = None
    return pivot_df


def extract_condition_variables(
    jsdata: JsPsychData,
) -> pd.DataFrame:
    """
    从 jsPsych 数据中提取实验条件变量（factorial design）。

    自动识别 jsPsych 的 factorial design 数据结构，
    将嵌套的条件变量展平为独立列。
    """
    df = jsdata.trial_df.copy()

    condition_cols = []

    # 常见条件变量来源
    for col in ["condition", "group", "condition_name", "counterbalance"]:
        if col in df.columns:
            condition_cols.append(col)

    # 从 data 列中提取（如果已展开）
    for col in df.columns:
        if col.startswith("data_") and not col.startswith("data_internal"):
            condition_cols.append(col)

    # 从 trial_type 提取因子
    if "trial_type" in df.columns:
        # 检查 trial_type 是否编码了多因素（如 "congruent_left"）
        types = df["trial_type"].dropna().unique()
        # 尝试按 _ 或 - 分割
        parts = []
        for t in types:
            for sep in ["_", "-"]:
                split = str(t).split(sep)
                if len(split) > 1:
                    parts.append(split)
                    break
        if parts and all(len(p) == len(parts[0]) for p in parts):
            n_factors = len(parts[0])
            for fi in range(n_factors):
                factor_name = f"factor_{chr(65 + fi)}"
                df[factor_name] = df["trial_type"].apply(
                    lambda x, fi=fi: str(x).split("_")[fi] if "_" in str(x)
                    else str(x).split("-")[fi] if "-" in str(x) else None
                )
                condition_cols.append(factor_name)

    if "subject" in df.columns:
        cols = ["subject"] + condition_cols
    else:
        cols = condition_cols

    available_cols = [c for c in cols if c in df.columns]
    return df[available_cols].drop_duplicates() if available_cols else df


def get_summary_stats(
    jsdata: JsPsychData,
    group_by: str = "trial_type",
    dv: str = "rt",
) -> pd.DataFrame:
    """
    按条件汇总反应时/正确率等指标。

    返回包含 N, M, SD, 正确率 的汇总表。
    """
    df = jsdata.trial_df.copy()

    if dv not in df.columns:
        available = [c for c in df.columns if "rt" in c.lower() or "反应时" in c]
        if available:
            dv = available[0]
        else:
            raise ValueError(f"找不到因变量列 '{dv}'。可用列：{list(df.columns)}")

    if group_by not in df.columns:
        raise ValueError(f"分组列 '{group_by}' 不存在。")

    # 确保 dv 是数值
    df[dv] = pd.to_numeric(df[dv], errors="coerce")

    agg_dict = {dv: ["count", "mean", "std"]}

    # 如果有正确率列
    acc_col = None
    for c in ["correct", "accuracy", "acc"]:
        if c in df.columns:
            acc_col = c
            agg_dict[c] = "mean"
            break

    grouped = df.groupby(group_by).agg(agg_dict).round(3)
    grouped.columns = ["_".join(c).strip("_") for c in grouped.columns]

    rename_map = {}
    for col in grouped.columns:
        if col.startswith(f"{dv}_"):
            suffix = col[len(dv) + 1:]
            rename_map[col] = {"count": "N", "mean": "M", "std": "SD"}.get(suffix, col)
        if acc_col and col.startswith(f"{acc_col}_"):
            rename_map[col] = "正确率"
    grouped = grouped.rename(columns=rename_map)

    return grouped.reset_index()


# ============================================================
# 内部辅助函数
# ============================================================


def _detect_subject_column(df: pd.DataFrame, fallback: str) -> Optional[str]:
    """自动检测被试ID列"""
    candidates = [
        fallback,
        "subject",
        "worker_id",
        "PROLIFIC_PID",
        "participant",
        "participant_id",
        "subj",
        "id",
        "SONA_ID",
        "mturk_worker_id",
    ]
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _flatten_json_data_column(df: pd.DataFrame, warnings: List[str]) -> pd.DataFrame:
    """展开 data 列中的JSON数据"""
    if "data" not in df.columns:
        return df

    expanded_rows = []
    for idx, row in df.iterrows():
        raw = row.get("data", "")
        if pd.isna(raw) or str(raw).strip() == "":
            expanded_rows.append(row.to_dict())
            continue

        try:
            if isinstance(raw, str):
                parsed = json.loads(raw)
            elif isinstance(raw, dict):
                parsed = raw
            else:
                expanded_rows.append(row.to_dict())
                continue

            new_row = row.to_dict()
            for k, v in parsed.items():
                if isinstance(v, (list, dict)):
                    new_row[f"data_{k}"] = json.dumps(v, ensure_ascii=False)
                else:
                    new_row[f"data_{k}"] = v
            expanded_rows.append(new_row)
        except (json.JSONDecodeError, TypeError):
            expanded_rows.append(row.to_dict())

    return pd.DataFrame(expanded_rows)


def _drop_empty_trials(df: pd.DataFrame, warnings: List[str]) -> pd.DataFrame:
    """删除无反应的空试次"""
    before = len(df)

    # 检查是否有 response 或 rt 列
    if "response" in df.columns:
        df = df[df["response"].notna()]
        # 空字符串也算空
        df = df[df["response"].astype(str).str.strip() != ""]

    if "rt" in df.columns:
        # rt 为 null 或 0 视为空
        df = df[df["rt"].notna()]
        df = df[pd.to_numeric(df["rt"], errors="coerce") > 0]

    if "reaction_time" in df.columns:
        df = df[df["reaction_time"].notna()]

    return df


def _normalize_jspsych_columns(df: pd.DataFrame) -> pd.DataFrame:
    """标准化 jsPsych 列名：英文→中文映射"""
    rename = {}
    for col in df.columns:
        if col in _JSPsych_COLUMN_MAP:
            rename[col] = _JSPsych_COLUMN_MAP[col]
    return df.rename(columns=rename)


def _detect_and_convert_rt(df: pd.DataFrame, warnings: List[str]) -> pd.DataFrame:
    """自动检测并转换反应时列（ms 和 s 统一）"""
    rt_cols = [c for c in df.columns if c.lower() in ("rt", "reaction_time", "反应时_ms")]
    if not rt_cols:
        return df

    for col in rt_cols:
        original = df[col].copy()
        numeric = pd.to_numeric(df[col], errors="coerce")

        if numeric.isna().all():
            continue

        # 检测单位：如果最大值 < 100，可能是秒
        max_val = numeric.max()
        if max_val < 100 and max_val > 0:
            warnings.append(
                f"检测到反应时列 '{col}' 最大值仅 {max_val:.1f}，疑似以秒为单位，"
                f"已自动转换为毫秒。请核实原始数据。"
            )
            numeric = numeric * 1000

        df[col] = numeric.round(1)

    return df


def get_trial_timeline(jsdata: JsPsychData, subject: str = None) -> pd.DataFrame:
    """
    提取试次时间线，按 time_elapsed 排序。

    参数：
        jsdata: JsPsychData 对象
        subject: 指定被试ID，None 则取第一个
    """
    df = jsdata.trial_df.copy()

    if subject and "subject" in df.columns:
        df = df[df["subject"] == subject]
    elif "subject" in df.columns and not subject:
        first_subj = df["subject"].iloc[0] if len(df) > 0 else None
        if first_subj:
            df = df[df["subject"] == first_subj]

    # 按累计时间排序
    if "累计时间_ms" in df.columns:
        df = df.sort_values("累计时间_ms")
    elif "time_elapsed" in df.columns:
        df = df.sort_values("time_elapsed")

    return df.reset_index(drop=True)
