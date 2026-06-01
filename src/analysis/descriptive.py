"""描述性统计分析"""

import pandas as pd
import numpy as np
from scipy import stats


def descriptive_stats(df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
    """
    计算数值型变量的描述性统计。
    返回 DataFrame 格式，包含：N, M, SD, Min, Max, Skewness, Kurtosis, SEM
    """
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()

    if not columns:
        return pd.DataFrame({"提示": ["未找到数值型变量"]})

    results = []
    for col in columns:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) == 0:
            continue

        results.append({
            "变量": col,
            "N": len(s),
            "M": round(s.mean(), 2),
            "SD": round(s.std(), 2),
            "SEM": round(s.sem(), 3),
            "Min": round(s.min(), 2),
            "Max": round(s.max(), 2),
            "偏度": round(float(s.skew()), 3),
            "峰度": round(float(s.kurtosis()), 3),
        })

    return pd.DataFrame(results)


def grouped_descriptive(
    df: pd.DataFrame, dv: str, group_col: str
) -> pd.DataFrame:
    """
    分组描述统计：按 group_col 分组，计算 dv 的 M, SD, N, SEM
    """
    if dv not in df.columns or group_col not in df.columns:
        return pd.DataFrame()

    results = []
    for name, group in df.groupby(group_col):
        s = pd.to_numeric(group[dv], errors="coerce").dropna()
        if len(s) == 0:
            continue
        results.append({
            "组别": str(name),
            "N": len(s),
            "M": round(s.mean(), 2),
            "SD": round(s.std(), 2),
            "SEM": round(s.sem(), 3),
            "Min": round(s.min(), 2),
            "Max": round(s.max(), 2),
        })

    return pd.DataFrame(results)


def frequency_table(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """分类变量的频数统计"""
    if col not in df.columns:
        return pd.DataFrame()

    freq = df[col].value_counts(dropna=False)
    pct = df[col].value_counts(normalize=True, dropna=False) * 100

    result = pd.DataFrame({
        "类别": freq.index.astype(str),
        "频数": freq.values,
        "百分比(%)": [round(v, 2) for v in pct.values],
    })

    return result.reset_index(drop=True)
