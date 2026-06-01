"""列类型推断与缺失值报告"""

import pandas as pd
import numpy as np
from typing import Dict, List


def infer_column_type(series: pd.Series) -> str:
    """
    推断单列类型：
    - numeric: 数值型
    - categorical_binary: 二分类（2个水平）
    - categorical_multi: 多分类（3+水平）
    - datetime: 日期型
    - text_free: 文本型（高基数字符串）
    """
    s = series.dropna()
    if len(s) == 0:
        return "numeric"

    # 日期型检测
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # 数值型
    if pd.api.types.is_numeric_dtype(series):
        n_unique = s.nunique()
        # 整数且只有少量不同值 → 可能是编码的分类变量
        if n_unique <= 2:
            return "categorical_binary"
        elif n_unique <= 15 and n_unique / len(s) < 0.05:
            # 少量值且比例低 → 可能是编码分组变量
            return "categorical_multi"
        return "numeric"

    # 字符串/对象型
    if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
        # 尝试转为数值
        try:
            pd.to_numeric(s, errors="raise")
            return "numeric"  # 存储为字符串的数值
        except (ValueError, TypeError):
            pass

        n_unique = s.nunique()
        ratio = n_unique / len(s)

        if n_unique <= 2:
            return "categorical_binary"
        elif n_unique <= 20 and ratio <= 0.15:
            return "categorical_multi"
        else:
            return "text_free"

    return "text_free"


def inspect_dataframe(df: pd.DataFrame) -> Dict:
    """
    推断 DataFrame 所有列的类型，返回完整的变量信息字典。
    """
    columns_info = {}
    for col in df.columns:
        col_type = infer_column_type(df[col])
        n_missing = int(df[col].isna().sum())
        n_total = len(df)
        n_unique = df[col].nunique()

        info = {
            "type": col_type,
            "n_missing": n_missing,
            "missing_rate": round(n_missing / n_total, 4) if n_total > 0 else 0.0,
            "n_unique": n_unique,
            "dtype": str(df[col].dtype),
        }

        # 分类型变量提供值列表
        if col_type in ("categorical_binary", "categorical_multi"):
            vals = df[col].dropna().unique()
            info["unique_values"] = sorted(
                [str(v) for v in vals[:30]]  # 最多显示30个
            )

        # 数值型变量提供基本统计
        if col_type == "numeric":
            try:
                numeric_vals = pd.to_numeric(df[col], errors="coerce").dropna()
                info["mean"] = round(float(numeric_vals.mean()), 2)
                info["std"] = round(float(numeric_vals.std()), 2)
                info["min"] = round(float(numeric_vals.min()), 2)
                info["max"] = round(float(numeric_vals.max()), 2)
            except (ValueError, TypeError):
                pass

        columns_info[col] = info

    return columns_info


def generate_missing_report(df: pd.DataFrame) -> str:
    """生成缺失值中文报告"""
    total = len(df)
    lines = [f"总样本量: {total}\n"]

    missing_stats = df.isna().sum()
    missing_cols = missing_stats[missing_stats > 0]

    if len(missing_cols) == 0:
        lines.append("✓ 无缺失值")
    else:
        for col, count in missing_cols.items():
            pct = count / total * 100
            lines.append(f"  {col}: {count} 个缺失 ({pct:.1f}%)")

    return "\n".join(lines)
