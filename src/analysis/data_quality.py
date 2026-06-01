"""统一数据前置检查：缺失值 / 异常值 / 正态性 / 零方差"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Literal


@dataclass
class DataQualityReport:
    missing_pct: float = 0.0
    missing_cols: List[str] = field(default_factory=list)
    outlier_cols: List[str] = field(default_factory=list)
    zero_var_cols: List[str] = field(default_factory=list)
    constant_cols: List[str] = field(default_factory=list)
    normality_checks: Dict[str, Dict] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    n_total: int = 0
    n_complete: int = 0


MissingStrategy = Literal["listwise", "pairwise", "mean_imputation", "drop_column"]


def handle_missing(
    df: pd.DataFrame,
    numeric_cols: Optional[List[str]] = None,
    strategy: MissingStrategy = "listwise",
    drop_threshold: float = 0.50,
) -> Tuple[pd.DataFrame, Dict]:
    """
    按指定策略处理缺失值。

    参数：
        df: 原始数据框
        numeric_cols: 需要处理的数值列（None则自动选择）
        strategy:
            "listwise" — 删除含任何缺失值的行（完全案例分析）
            "pairwise" — 返回原始数据，缺失在分析时成对处理（仅标记策略）
            "mean_imputation" — 用列均值填充缺失值
            "drop_column" — 删除缺失比例超过 drop_threshold 的列
        drop_threshold: 删除列的缺失比例阈值（仅 strategy="drop_column" 时生效）

    返回：
        (处理后的数据框, 处理元信息字典)
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    result_df = df.copy()
    meta = {
        "strategy": strategy,
        "original_n": len(df),
        "original_n_cols": len(df.columns),
        "n_after": len(df),
        "rows_removed": 0,
        "cols_removed": 0,
        "removed_col_names": [],
        "imputed_cols": [],
        "description_zh": "",
    }

    if strategy == "listwise":
        # 仅对数值列检查缺失
        before = len(result_df)
        result_df = result_df.dropna(subset=numeric_cols)
        after = len(result_df)
        meta["n_after"] = after
        meta["rows_removed"] = before - after
        pct = (before - after) / before * 100 if before > 0 else 0
        meta["description_zh"] = (
            f"列表删除（Listwise Deletion）：删除了含缺失值的{meta['rows_removed']}行"
            f"（{pct:.1f}%），剩余{after}行完整数据。"
        )
        if pct > 15:
            meta["description_zh"] += (
                f" 警告：缺失比例较高（{pct:.1f}%），建议检查缺失机制（MCAR/MAR/MNAR），"
                "并考虑使用多重插补（Multiple Imputation）或全信息最大似然（FIML）方法。"
            )

    elif strategy == "pairwise":
        meta["n_after"] = len(result_df)
        meta["description_zh"] = (
            "成对删除（Pairwise Deletion）：分析时仅使用各变量对的有效观测，"
            "不统一删除整行。注意：不同分析可能基于不同样本量。"
        )

    elif strategy == "mean_imputation":
        imputed = []
        for col in numeric_cols:
            if col in result_df.columns and result_df[col].isna().any():
                mean_val = result_df[col].mean()
                result_df[col] = result_df[col].fillna(mean_val)
                imputed.append(col)
        meta["imputed_cols"] = imputed
        meta["n_after"] = len(result_df)
        meta["description_zh"] = (
            f"均值插补（Mean Imputation）：对{len(imputed)}个变量"
            f"（{', '.join(imputed[:5])}{'...' if len(imputed) > 5 else ''}）"
            "的缺失值用列均值填充。"
            "注意：均值插补会低估标准误，仅建议在缺失比例很低（<5%）时使用。"
        )

    elif strategy == "drop_column":
        # 删除缺失比例超过阈值的数值列
        cols_to_drop = []
        for col in numeric_cols:
            if col in result_df.columns:
                miss_rate = result_df[col].isna().mean()
                if miss_rate > drop_threshold:
                    cols_to_drop.append(col)
        if cols_to_drop:
            result_df = result_df.drop(columns=cols_to_drop)
        meta["cols_removed"] = len(cols_to_drop)
        meta["removed_col_names"] = cols_to_drop
        meta["n_after"] = len(result_df)
        meta["description_zh"] = (
            f"删除高缺失列（阈值>{drop_threshold:.0%}）：删除了{len(cols_to_drop)}列"
            f"（{', '.join(cols_to_drop[:5])}{'...' if len(cols_to_drop) > 5 else ''}）。"
        )

    # Task 2: 追加偏误警告到warnings列表
    if strategy == "listwise":
        pct_lost = meta["rows_removed"] / meta["original_n"] * 100 if meta["original_n"] > 0 else 0
        if pct_lost > 15:
            meta["warnings"] = [
                f"⚠ 缺失值处理偏误警告：当前缺失值处理策略为列表删除（Listwise），"
                f"导致有效样本量损失 {pct_lost:.1f}%（>{15}%），"
                f"可能导致参数估计偏差或统计检验力下降，建议评估多重插补方法（Multiple Imputation）的适用性。"
            ]
        else:
            meta["warnings"] = []
    elif strategy == "mean_imputation":
        if meta["imputed_cols"]:
            meta["warnings"] = [
                f"⚠ 缺失值处理偏误警告：当前缺失值处理策略为均值插补（Mean Imputation），"
                f"对 {len(meta['imputed_cols'])} 个变量进行了均值填充。"
                f"均值插补会低估变量标准误并扭曲变量间相关结构，"
                f"可能导致参数估计偏差或统计检验力下降，建议评估多重插补方法（Multiple Imputation）的适用性。"
            ]
        else:
            meta["warnings"] = []
    else:
        meta["warnings"] = []

    return result_df, meta


def data_quality_check(
    df: pd.DataFrame,
    numeric_cols: Optional[List[str]] = None,
    check_normality: bool = False,
    normality_alpha: float = 0.05,
) -> DataQualityReport:
    """
    统一数据前置检查，在所有分析执行前调用。

    参数：
        df: 数据框
        numeric_cols: 需要检查的数值列（None则自动选择）
        check_normality: 是否进行正态性检验（参数检验需要）
        normality_alpha: 正态性检验的α水平

    返回：DataQualityReport 包含所有警告信息
    """
    report = DataQualityReport()
    report.n_total = len(df)

    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if not numeric_cols:
        report.warnings.append("⚠ 未检测到数值型变量。")
        return report

    num_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    # 1. 缺失值比例报告
    total_cells = num_df.size
    missing_cells = num_df.isna().sum().sum()
    report.missing_pct = missing_cells / total_cells * 100 if total_cells > 0 else 0.0

    if report.missing_pct > 0:
        # 按列报告
        col_missing = num_df.isna().sum()
        cols_with_missing = col_missing[col_missing > 0]
        report.missing_cols = cols_with_missing.index.tolist()

        for col in cols_with_missing.index:
            col_pct = col_missing[col] / len(num_df) * 100
            if col_pct > 20:
                report.warnings.append(
                    f"⚠ 列「{col}」缺失值比例高达{col_pct:.1f}%，可能影响分析可靠性。"
                )
            elif col_pct > 5:
                report.warnings.append(
                    f"⚠ 列「{col}」缺失值比例为{col_pct:.1f}%，分析将使用列表删除。"
                )

        if report.missing_pct > 15:
            report.warnings.append(
                f"⚠ 总体缺失值比例达{report.missing_pct:.1f}%，列表删除可能造成较大样本损失。"
                "建议检查缺失机制（MCAR/MAR/MNAR）并考虑适当的缺失值处理方法。"
            )

    # 完整数据行数
    report.n_complete = num_df.dropna().shape[0]

    # 2. 零方差 / 常数列检测
    for col in numeric_cols:
        series = num_df[col].dropna()
        if len(series) == 0:
            report.constant_cols.append(col)
            report.warnings.append(f"❌ 列「{col}」全为缺失值，无法用于分析。")
        elif series.nunique() <= 1:
            report.zero_var_cols.append(col)
            report.warnings.append(
                f"⚠ 列「{col}」为常数列（仅1个唯一值={series.iloc[0]}），方差为0，无法进行需要变异性的分析。"
            )
        elif series.var() < 1e-8:
            report.zero_var_cols.append(col)
            report.warnings.append(
                f"⚠ 列「{col}」方差近乎为0（var={series.var():.2e}），可能影响分析稳定性。"
            )

    # 3. 异常值标记（基于IQR）
    for col in numeric_cols:
        series = num_df[col].dropna()
        if len(series) < 4 or col in report.zero_var_cols:
            continue

        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        if IQR == 0:
            continue

        lower_fence = Q1 - 1.5 * IQR
        upper_fence = Q3 + 1.5 * IQR
        outliers = series[(series < lower_fence) | (series > upper_fence)]

        if len(outliers) > 0:
            outlier_pct = len(outliers) / len(series) * 100
            if outlier_pct > 10:
                report.outlier_cols.append(col)
                report.warnings.append(
                    f"⚠ 列「{col}」中{len(outliers)}个值（{outlier_pct:.1f}%）被标记为IQR异常值"
                    f"（范围：[{lower_fence:.2f}, {upper_fence:.2f}]）。"
                    f"请确认这些值是真实数据还是录入错误。"
                )
            elif outlier_pct > 2:
                report.outlier_cols.append(col)
                report.warnings.append(
                    f"⚠ 列「{col}」存在{len(outliers)}个IQR异常值（{outlier_pct:.1f}%）。"
                )

    # 4. 正态性假设检查（仅在需要时）
    if check_normality:
        for col in numeric_cols:
            series = num_df[col].dropna()
            if len(series) < 3 or col in report.zero_var_cols:
                continue

            n = len(series)
            if n > 5000:
                z_score = (series - series.mean()) / series.std()
                stat, p = __import__('scipy.stats', fromlist=['kstest']).kstest(
                    z_score, 'norm'
                )
                test_name = "K-S"
            else:
                from scipy import stats as sp_stats
                stat, p = sp_stats.shapiro(series)
                test_name = "Shapiro-Wilk"

            report.normality_checks[col] = {
                "test": test_name,
                "statistic": round(float(stat), 4),
                "p_value": round(float(p), 4),
                "passed": p > normality_alpha,
                "message": (
                    f"正态性{'通过' if p > normality_alpha else '未通过'} "
                    f"({test_name}: W={stat:.3f}, p={p:.3f})"
                ),
            }

            if p <= normality_alpha:
                report.warnings.append(
                    f"⚠ 列「{col}」不符合正态分布（{test_name} p={p:.4f}）。"
                    "若分析假设正态性，请考虑使用非参数替代方法。"
                )

    # 5. 小样本警告
    if report.n_complete < 30:
        report.warnings.append(
            f"⚠ 完整数据仅{report.n_complete}条记录，样本量较小。"
            "参数检验的可靠性和效应量估计可能不够稳定。"
        )

    return report
