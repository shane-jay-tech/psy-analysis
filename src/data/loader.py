"""统一数据加载：CSV / Excel / SPSS，自动检测编码"""

import os
import pandas as pd
from typing import Tuple, Optional, BinaryIO

MAX_FILE_SIZE_MB = 50


def _check_file_size(file_obj):
    """检查文件大小，超过限制则抛出异常"""
    size_bytes = None
    if hasattr(file_obj, "getvalue"):
        size_bytes = len(file_obj.getvalue())
    elif hasattr(file_obj, "seek") and hasattr(file_obj, "tell"):
        pos = file_obj.tell()
        file_obj.seek(0, 2)
        size_bytes = file_obj.tell()
        file_obj.seek(pos)
    elif isinstance(file_obj, str) and os.path.exists(file_obj):
        size_bytes = os.path.getsize(file_obj)

    if size_bytes is not None:
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise ValueError(
                f"文件过大（{size_mb:.1f} MB），系统限制为 {MAX_FILE_SIZE_MB} MB。\n"
                f"建议：只保留分析所需的列，或拆分数据后分批上传。"
            )


def load_csv(file_path: str, usecols=None) -> Tuple[pd.DataFrame, dict]:
    """加载CSV文件，自动检测编码。支持 usecols 只加载指定列以节省内存。"""
    encodings_to_try = ["utf-8", "gbk", "gb2312", "gb18030", "latin-1"]
    detected_encoding = None
    df = None

    read_kwargs = {}
    if usecols is not None:
        read_kwargs["usecols"] = usecols

    for enc in encodings_to_try:
        try:
            df = pd.read_csv(file_path, encoding=enc, **read_kwargs)
            detected_encoding = enc
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if df is None:
        raise ValueError(
            f"无法识别文件编码，已尝试: {encodings_to_try}\n"
            "请将文件另存为 UTF-8 或 GBK 编码后重试。"
        )

    meta = {
        "source_type": "csv",
        "encoding": detected_encoding,
        "row_count": len(df),
        "col_count": len(df.columns),
    }
    return df, meta


def load_excel(file_path: str, sheet_name=None, usecols=None) -> Tuple[pd.DataFrame, dict]:
    """加载Excel文件，支持指定Sheet名称或索引，以及只加载指定列。"""
    read_kwargs = {"engine": "openpyxl", "sheet_name": sheet_name}
    if usecols is not None:
        read_kwargs["usecols"] = usecols
    df = pd.read_excel(file_path, **read_kwargs)
    meta = {
        "source_type": "excel",
        "encoding": None,
        "row_count": len(df),
        "col_count": len(df.columns),
        "sheet_name": sheet_name,
    }
    return df, meta


def load_spss(file_path: str) -> Tuple[pd.DataFrame, dict]:
    """加载SPSS .sav文件，应用值标签"""
    import pyreadstat

    df, meta_py = pyreadstat.read_sav(file_path)

    # 应用值标签（如 1→男, 2→女）
    for col in df.columns:
        if col in meta_py.variable_value_labels:
            labels = meta_py.variable_value_labels[col]
            if labels:
                df[col] = df[col].replace(labels)

    meta = {
        "source_type": "spss",
        "encoding": None,
        "row_count": len(df),
        "col_count": len(df.columns),
        "variable_labels": meta_py.column_names_to_labels,
    }
    return df, meta


def load_jspsych_json(file_obj) -> Tuple[pd.DataFrame, dict]:
    """v3.7 N7: 加载 jsPsych v6/v7 导出的 JSON（数组）或 JSONL（每行一对象）。

    自动嗅探：以 `[` 开头视为 JSON 数组；其余视为 JSONL。
    展开嵌套 `data` 字段，应用列名归一化。

    Args:
        file_obj: 文件路径字符串、字节、或类文件对象。

    Returns:
        (DataFrame, metadata_dict)
    """
    import io
    import json as _json

    # 读出文本
    if hasattr(file_obj, "read"):
        raw = file_obj.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig", errors="replace")
        else:
            text = raw
    elif isinstance(file_obj, (bytes, bytearray)):
        text = file_obj.decode("utf-8-sig", errors="replace")
    else:
        with open(file_obj, "r", encoding="utf-8-sig") as f:
            text = f.read()

    text = text.lstrip("﻿").strip()
    if not text:
        raise ValueError("jsPsych JSON 文件为空。")

    trials = []
    fmt = ""
    if text.startswith("["):
        # JSON 数组
        try:
            trials = _json.loads(text)
        except _json.JSONDecodeError as exc:
            raise ValueError(f"jsPsych JSON 数组解析失败：{exc}")
        if not isinstance(trials, list):
            raise ValueError("jsPsych JSON 顶层不是数组。")
        fmt = "json_array"
    else:
        # JSONL（每行一对象）
        for ln, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                trials.append(_json.loads(line))
            except _json.JSONDecodeError:
                # 容错：跳过坏行
                continue
        fmt = "jsonl"

    if not trials:
        raise ValueError("未能从 jsPsych JSON 文件解析到任何试次数据。")

    df = pd.DataFrame(trials)

    # 展开 data 列（jsPsych v6 经典字段）
    try:
        from src.experiment_design.jspsych_data_importer import (
            _flatten_json_data_column,
            _normalize_jspsych_columns,
        )
        warnings: list = []
        df = _flatten_json_data_column(df, warnings)
        df = _normalize_jspsych_columns(df)
    except Exception:
        pass

    meta = {
        "source_type": "jspsych_json",
        "encoding": "utf-8",
        "row_count": len(df),
        "col_count": len(df.columns),
        "format": fmt,
        "n_trials": len(trials),
    }
    return df, meta


def pivot_jspsych_to_wide(
    df: pd.DataFrame,
    *,
    subject_col: str = "subject",
    condition_col: str = "condition",
    value_col: str = "反应时_ms",
    agg: str = "mean",
) -> Tuple[pd.DataFrame, dict]:
    """v3.9 N9: jsPsych 长表 → 被试级宽表（每被试一行，每条件一列）。

    适用：jsPsych 导出的试次级长表（每行一个 trial），分析常需要被试级
    宽表（如配对 t 检验：列 = ``congruent`` / ``incongruent``）。

    自动嗅探常见列名变体（``subject``/``subj_id``/``participant``、
    ``condition``/``trial_type``、``rt``/``反应时``/``反应时_ms``），找不到
    时按显式参数严格校验并抛 ``ValueError`` 列出可用列。

    Args:
        df: 长表 DataFrame
        subject_col: 被试 ID 列（默认 ``"subject"``，自动嗅探变体）
        condition_col: 条件列（默认 ``"condition"``，自动嗅探）
        value_col: 聚合的数值列（默认 ``"反应时_ms"``）
        agg: ``"mean"`` 或 ``"median"``（其他值默认按 mean 处理）

    Returns:
        (wide_df, meta)。wide_df 行=被试 ID，列=条件值；meta 含
        ``n_subjects / n_conditions / agg / pivoted_from`` 字段。

    Raises:
        ValueError: 缺必要列。
    """
    if df is None or df.empty:
        raise ValueError("待 pivot 的 DataFrame 为空。")

    cols = list(df.columns)

    def _resolve(target: str, fallbacks: list) -> str:
        if target in cols:
            return target
        for fb in fallbacks:
            if fb in cols:
                return fb
        # 部分匹配：要求别名是列名的子串（单向）；避免短词如 "rt" 倒匹配 "participant"
        for c in cols:
            for fb in [target] + fallbacks:
                if len(fb) >= 3 and fb in c:
                    return c
        raise ValueError(
            f"找不到列「{target}」（可用列：{cols}）。可用 ``subject_col`` / "
            f"``condition_col`` / ``value_col`` 参数指定。"
        )

    sub = _resolve(subject_col, ["subj_id", "subject_id", "participant", "被试", "id"])
    cond = _resolve(condition_col, ["trial_type", "condition_name", "条件", "stimulus_type"])
    val = _resolve(value_col, ["反应时_ms", "反应时", "rt", "RT", "response_time"])

    agg_func = "mean" if str(agg).lower() == "mean" else "median"
    wide = df.pivot_table(
        index=sub, columns=cond, values=val, aggfunc=agg_func
    )
    # 把 NaN 行/列摘要保留信息但不强删（让调用方决定）
    wide = wide.reset_index()
    wide.columns.name = None

    meta = {
        "source_type": "jspsych_pivoted",
        "n_subjects": int(wide.shape[0]),
        "n_conditions": int(wide.shape[1] - 1),  # 减去 subject 列
        "agg": agg_func,
        "subject_col": sub,
        "condition_col": cond,
        "value_col": val,
        "pivoted_from": "jspsych_long",
    }
    return wide, meta


def load_word_table(file_obj, table_index: int = 0) -> Tuple[pd.DataFrame, dict]:
    """v3.7 N7+: 从 Word (.docx) 文档中提取表格作为数据源。

    取文档中的第 table_index 个表格（默认第一个），第一行作表头。
    若文档无表格则抛 ValueError。

    Args:
        file_obj: 文件路径或类文件对象。
        table_index: 多表格时取第几个（0-indexed，默认 0）。
    """
    try:
        from docx import Document
    except ImportError as exc:
        raise ValueError("缺少 python-docx 依赖，无法解析 Word 文件。") from exc

    doc = Document(file_obj)
    tables = doc.tables
    if not tables:
        raise ValueError("Word 文档中未找到表格。请将数据存为 CSV/Excel 或在 Word 中插入表格后重试。")

    if not (0 <= table_index < len(tables)):
        raise ValueError(f"表格索引越界：文档共 {len(tables)} 个表格，请求第 {table_index + 1} 个。")

    tbl = tables[table_index]
    rows = [[cell.text.strip() for cell in row.cells] for row in tbl.rows]
    if not rows:
        raise ValueError("Word 表格为空。")
    header, *body = rows
    if not body:
        # 仅有表头无数据
        df = pd.DataFrame(columns=header)
    else:
        # 列数不齐时按表头长度截断/补齐
        n_cols = len(header)
        norm_body = [r[:n_cols] + [""] * (n_cols - len(r)) for r in body]
        df = pd.DataFrame(norm_body, columns=header)

    # 数值列尽力转 numeric（失败保留原值）
    for col in df.columns:
        try:
            converted = pd.to_numeric(df[col], errors="raise")
            df[col] = converted
        except (ValueError, TypeError):
            pass

    meta = {
        "source_type": "word",
        "encoding": None,
        "row_count": len(df),
        "col_count": len(df.columns),
        "table_index": table_index,
        "n_tables": len(tables),
    }
    return df, meta


def load_markdown_table(file_obj, table_index: int = 0) -> Tuple[pd.DataFrame, dict]:
    """v3.7 N7+: 从 Markdown (.md) 文件中提取管道表格作为数据源。

    解析形如 `| col1 | col2 |\\n|---|---|\\n| v1 | v2 |` 的 GFM 表格。
    若文档无表格则抛 ValueError。

    Args:
        file_obj: 文件路径或类文件对象。
        table_index: 多表格时取第几个（0-indexed，默认 0）。
    """
    import re as _re

    if hasattr(file_obj, "read"):
        raw = file_obj.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig", errors="replace")
        else:
            text = raw
    elif isinstance(file_obj, (bytes, bytearray)):
        text = file_obj.decode("utf-8-sig", errors="replace")
    else:
        with open(file_obj, "r", encoding="utf-8-sig") as f:
            text = f.read()

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    # 找出所有表格块（连续以 | 开头/包含的行 + 紧跟分隔行 ---）
    tables: list = []
    cur: list = []
    sep_re = _re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")
    for line in lines:
        s = line.strip()
        if "|" in s:
            cur.append(s)
        else:
            if len(cur) >= 2 and any(sep_re.match(x) for x in cur):
                tables.append(cur)
            cur = []
    if len(cur) >= 2 and any(sep_re.match(x) for x in cur):
        tables.append(cur)

    if not tables:
        raise ValueError(
            "Markdown 文件中未找到表格（GFM 管道格式）。\n"
            "若这是问卷题目而非被试数据，请到「📋 问卷设计 → 📤 上传现有题目」上传。"
        )
    if not (0 <= table_index < len(tables)):
        raise ValueError(f"表格索引越界：共 {len(tables)} 个表格。")

    block = tables[table_index]
    parsed_rows = []
    for ln in block:
        if sep_re.match(ln):
            continue
        # 切分单元格
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        parsed_rows.append(cells)
    if len(parsed_rows) < 2:
        raise ValueError("Markdown 表格至少需要表头 + 一行数据。")

    header, *body = parsed_rows
    n_cols = len(header)
    norm_body = [r[:n_cols] + [""] * (n_cols - len(r)) for r in body]
    df = pd.DataFrame(norm_body, columns=header)

    for col in df.columns:
        try:
            converted = pd.to_numeric(df[col], errors="raise")
            df[col] = converted
        except (ValueError, TypeError):
            pass

    meta = {
        "source_type": "markdown",
        "encoding": "utf-8",
        "row_count": len(df),
        "col_count": len(df.columns),
        "table_index": table_index,
        "n_tables": len(tables),
    }
    return df, meta


def load_data(file_path_or_bytes, sheet_name=None, usecols=None) -> Tuple[pd.DataFrame, dict]:
    """
    统一入口：根据文件扩展名或BytesIO对象加载数据。
    支持 CSV (.csv), Excel (.xlsx/.xls), SPSS (.sav), jsPsych (.json/.jsonl),
    Word 表格 (.docx), Markdown 表格 (.md/.markdown)
    usecols: 只加载指定列（列名列表），可显著降低大文件内存占用。
    返回 (DataFrame, metadata_dict)
    """
    if hasattr(file_path_or_bytes, "name"):
        file_name = file_path_or_bytes.name.lower()
        file_obj = file_path_or_bytes
    else:
        file_name = str(file_path_or_bytes).lower()
        file_obj = file_path_or_bytes

    _check_file_size(file_obj)

    if file_name.endswith(".csv"):
        return load_csv(file_obj, usecols=usecols)
    elif file_name.endswith((".xlsx", ".xls")):
        return load_excel(file_obj, sheet_name=sheet_name, usecols=usecols)
    elif file_name.endswith(".sav"):
        if usecols is not None:
            st = __import__("streamlit", fromlist=["warning"])
            st.warning("⚠ SPSS 文件暂不支持 usecols 列筛选，将加载全部列。")
        return load_spss(file_obj)
    elif file_name.endswith((".json", ".jsonl")):
        df, meta = load_jspsych_json(file_obj)
        if usecols is not None:
            df = df[[c for c in usecols if c in df.columns]]
            meta["col_count"] = len(df.columns)
        return df, meta
    elif file_name.endswith(".docx"):
        df, meta = load_word_table(file_obj)
        if usecols is not None:
            df = df[[c for c in usecols if c in df.columns]]
            meta["col_count"] = len(df.columns)
        return df, meta
    elif file_name.endswith((".md", ".markdown")):
        df, meta = load_markdown_table(file_obj)
        if usecols is not None:
            df = df[[c for c in usecols if c in df.columns]]
            meta["col_count"] = len(df.columns)
        return df, meta
    else:
        raise ValueError(
            f"不支持的文件格式: {file_name}\n"
            "支持的格式：CSV (.csv), Excel (.xlsx/.xls), SPSS (.sav), "
            "jsPsych (.json/.jsonl), Word (.docx), Markdown (.md)"
        )


def validate_data(df: pd.DataFrame) -> list:
    """检查数据质量，返回问题列表"""
    issues = []

    if df.empty:
        issues.append("⚠ 文件为空，没有可用数据。")
        return issues

    if len(df.columns) == 0:
        issues.append("⚠ 未检测到任何列。")
        return issues

    # 检查全空列
    all_na_cols = [c for c in df.columns if df[c].isna().all()]
    if all_na_cols:
        issues.append(f"⚠ 以下列全为空值：{', '.join(all_na_cols)}")

    # 检查重复列名
    dup_cols = df.columns[df.columns.duplicated()].tolist()
    if dup_cols:
        issues.append(f"⚠ 存在重复列名：{', '.join(dup_cols)}")

    # 检查缺失率
    missing_rate = df.isna().mean()
    high_missing = missing_rate[missing_rate > 0.2]
    for col, rate in high_missing.items():
        issues.append(f"⚠ 列'{col}'缺失率 {rate:.1%}")

    return issues
