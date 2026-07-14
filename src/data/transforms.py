"""数据变换引擎：计算变量、重新编码、筛选样本

心理学问卷数据处理的核心三件套，替代 SPSS 的 Compute / Recode / Select Cases。
支持自然语言意图驱动（AI 解析后调用）和直接 API 调用两种方式。
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union


@dataclass
class TransformResult:
    """数据变换结果"""
    success: bool = True
    df: Optional[pd.DataFrame] = None
    description: str = ""
    rows_before: int = 0
    rows_after: int = 0
    new_columns: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ===========================================================================
# 计算变量（Compute Variable）
# ===========================================================================

def compute_mean(df: pd.DataFrame, items: List[str], new_col: str) -> TransformResult:
    """计算指定题目的均值（忽略缺失值）。

    用途：量表总分 = 各题目均值
    """
    result = TransformResult(rows_before=len(df))
    missing = [c for c in items if c not in df.columns]
    if missing:
        result.success = False
        result.description = f"列不存在: {missing}"
        return result

    df = df.copy()
    df[new_col] = df[items].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    result.df = df
    result.rows_after = len(df)
    result.new_columns = [new_col]
    result.description = f"已计算 {new_col} = mean({', '.join(items)})"
    return result


def compute_sum(df: pd.DataFrame, items: List[str], new_col: str) -> TransformResult:
    """计算指定题目的总和。

    用途：量表总分 = 各题目求和
    """
    result = TransformResult(rows_before=len(df))
    missing = [c for c in items if c not in df.columns]
    if missing:
        result.success = False
        result.description = f"列不存在: {missing}"
        return result

    df = df.copy()
    df[new_col] = df[items].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    result.df = df
    result.rows_after = len(df)
    result.new_columns = [new_col]
    result.description = f"已计算 {new_col} = sum({', '.join(items)})"
    return result


def compute_formula(df: pd.DataFrame, new_col: str, formula: str) -> TransformResult:
    """通过公式计算新变量。

    支持 pandas eval 语法，如：
    - "Q1 + Q2 + Q3"
    - "(Q1 + Q2) / 2"
    - "age * 12"
    """
    result = TransformResult(rows_before=len(df))
    df = df.copy()

    try:
        df[new_col] = df.eval(formula)
        result.df = df
        result.rows_after = len(df)
        result.new_columns = [new_col]
        result.description = f"已计算 {new_col} = {formula}"
    except Exception as e:
        result.success = False
        result.description = f"公式计算失败: {e}"

    return result


# ===========================================================================
# 重新编码（Recode）
# ===========================================================================

def reverse_score(
    df: pd.DataFrame,
    items: List[str],
    scale_max: int,
    scale_min: int = 1,
    suffix: str = "_R",
) -> TransformResult:
    """反向计分。

    公式：新分 = scale_max + scale_min - 原分
    如 5 点量表 (1-5)：reverse = 6 - original

    参数：
        items: 需要反向计分的题目列名
        scale_max: 量表最大值（如 5 点量表填 5）
        scale_min: 量表最小值（默认 1）
        suffix: 反向计分后新列名后缀（默认 "_R"）
    """
    result = TransformResult(rows_before=len(df))
    missing = [c for c in items if c not in df.columns]
    if missing:
        result.success = False
        result.description = f"列不存在: {missing}"
        return result

    df = df.copy()
    total = scale_max + scale_min
    new_cols = []
    for item in items:
        new_name = f"{item}{suffix}"
        df[new_name] = total - pd.to_numeric(df[item], errors="coerce")
        new_cols.append(new_name)

    result.df = df
    result.rows_after = len(df)
    result.new_columns = new_cols
    result.description = f"已反向计分 {len(items)} 题（{scale_min}-{scale_max} 量表），新列: {', '.join(new_cols)}"
    return result


def recode_bins(
    df: pd.DataFrame,
    col: str,
    bins: List[float],
    labels: List[str],
    new_col: Optional[str] = None,
) -> TransformResult:
    """连续变量分箱（如年龄→年龄段）。

    参数：
        col: 原始列名
        bins: 分箱边界，如 [0, 18, 35, 60, 100]
        labels: 各区间标签，如 ["未成年", "青年", "中年", "老年"]
        new_col: 新列名（默认为 col + "_group"）
    """
    result = TransformResult(rows_before=len(df))
    if col not in df.columns:
        result.success = False
        result.description = f"列 {col} 不存在"
        return result

    df = df.copy()
    if new_col is None:
        new_col = f"{col}_group"

    df[new_col] = pd.cut(
        pd.to_numeric(df[col], errors="coerce"),
        bins=bins,
        labels=labels,
        include_lowest=True,
    )

    result.df = df
    result.rows_after = len(df)
    result.new_columns = [new_col]
    result.description = f"已将 {col} 分箱为 {labels}，存入 {new_col}"
    return result


def recode_map(
    df: pd.DataFrame,
    col: str,
    mapping: Dict[Any, Any],
    new_col: Optional[str] = None,
) -> TransformResult:
    """值映射重编码。

    参数：
        col: 原始列
        mapping: 旧值→新值的映射，如 {1: "男", 2: "女"} 或 {"非常不满意": "不满意", "不满意": "不满意"}
        new_col: 新列名（默认覆盖原列）
    """
    result = TransformResult(rows_before=len(df))
    if col not in df.columns:
        result.success = False
        result.description = f"列 {col} 不存在"
        return result

    df = df.copy()
    target = new_col if new_col else col
    df[target] = df[col].map(mapping).fillna(df[col])

    result.df = df
    result.rows_after = len(df)
    result.new_columns = [target] if new_col else []
    result.description = f"已重编码 {col} → {target}（{len(mapping)} 种映射）"
    return result


# ===========================================================================
# 筛选样本（Select Cases）
# ===========================================================================

def filter_by_condition(
    df: pd.DataFrame,
    condition: str,
) -> TransformResult:
    """按条件筛选样本。

    支持 pandas query 语法：
    - "gender == '女'"
    - "age > 18 and age < 65"
    - "score >= 60"
    - "group == '实验组'"
    """
    result = TransformResult(rows_before=len(df))
    try:
        filtered = df.query(condition)
        result.df = filtered
        result.rows_after = len(filtered)
        result.description = f"筛选条件: {condition}（{result.rows_before} → {result.rows_after} 行）"
        if result.rows_after == 0:
            result.warnings.append("筛选后无数据，请检查条件是否正确。")
    except Exception as e:
        result.success = False
        result.description = f"筛选条件错误: {e}"
    return result


def filter_outliers(
    df: pd.DataFrame,
    cols: List[str],
    method: str = "zscore",
    threshold: float = 3.0,
) -> TransformResult:
    """异常值筛除。

    方法：
    - "zscore": Z 分数绝对值 > threshold 的为异常值
    - "iqr": 超出 Q1-1.5*IQR 或 Q3+1.5*IQR 的为异常值
    """
    result = TransformResult(rows_before=len(df))
    missing = [c for c in cols if c not in df.columns]
    if missing:
        result.success = False
        result.description = f"列不存在: {missing}"
        return result

    df_num = df.copy()
    for c in cols:
        df_num[c] = pd.to_numeric(df_num[c], errors="coerce")

    mask = pd.Series(True, index=df.index)

    if method == "zscore":
        from scipy import stats
        for c in cols:
            z = np.abs(stats.zscore(df_num[c].dropna()))
            valid_idx = df_num[c].dropna().index
            outlier_idx = valid_idx[z > threshold]
            mask.loc[outlier_idx] = False
    elif method == "iqr":
        for c in cols:
            q1 = df_num[c].quantile(0.25)
            q3 = df_num[c].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            mask &= (df_num[c] >= lower) & (df_num[c] <= upper) | df_num[c].isna()

    filtered = df[mask]
    n_removed = result.rows_before - len(filtered)
    result.df = filtered
    result.rows_after = len(filtered)
    result.description = f"异常值筛除（{method}, 阈值={threshold}）：移除 {n_removed} 行"
    if n_removed > result.rows_before * 0.1:
        result.warnings.append(f"移除比例超过 10%（{n_removed}/{result.rows_before}），请确认阈值设置。")
    return result


def filter_by_values(
    df: pd.DataFrame,
    col: str,
    keep_values: Optional[List[Any]] = None,
    exclude_values: Optional[List[Any]] = None,
) -> TransformResult:
    """按值列表筛选/排除样本。

    参数：
        col: 筛选列
        keep_values: 保留这些值的样本
        exclude_values: 排除这些值的样本
    """
    result = TransformResult(rows_before=len(df))
    if col not in df.columns:
        result.success = False
        result.description = f"列 {col} 不存在"
        return result

    if keep_values is not None:
        filtered = df[df[col].isin(keep_values)]
        desc = f"保留 {col} 为 {keep_values} 的样本"
    elif exclude_values is not None:
        filtered = df[~df[col].isin(exclude_values)]
        desc = f"排除 {col} 为 {exclude_values} 的样本"
    else:
        result.success = False
        result.description = "需指定 keep_values 或 exclude_values"
        return result

    result.df = filtered
    result.rows_after = len(filtered)
    result.description = f"{desc}（{result.rows_before} → {result.rows_after} 行）"
    return result
