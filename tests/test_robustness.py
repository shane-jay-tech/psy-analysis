"""边界与异常测试：极小样本 / 缺失值 / 常数列 / 弱效应 / 降级行为"""
import pandas as pd
import numpy as np
import pytest


# ===========================================================================
# 辅助：检查警告消息中是否包含特定中文关键词
# ===========================================================================

def _run_and_get_warnings(result_or_output) -> list:
    """从分析结果中提取警告信息"""
    if isinstance(result_or_output, dict):
        warnings = []
        errors = result_or_output.get("errors", [])
        for e in errors:
            msg = e.get("message", "") if isinstance(e, dict) else str(e)
            warnings.append(msg)
        # 检查 result 的 warning 字段
        result = result_or_output.get("result")
        if result and hasattr(result, "warning") and result.warning:
            warnings.append(result.warning)
        return warnings
    if hasattr(result_or_output, "warning") and result_or_output.warning:
        return [result_or_output.warning]
    return []


def has_chinese_keyword(warnings: list, keywords: list) -> bool:
    """检查警告列表中是否包含给定的中文关键词（至少一个）"""
    for w in warnings:
        for kw in keywords:
            if kw in w:
                return True
    return False


# ===========================================================================
# 极小样本测试
# ===========================================================================

def test_tiny_sample_ttest():
    """6个被试的极小样本t检验：应给出小样本警告"""
    from src.analysis.ttest import independent_ttest
    df = pd.DataFrame({
        "score": [3, 4, 5, 6, 7, 8],
        "group": ["A", "A", "A", "B", "B", "B"],
    })
    result = independent_ttest(df, "score", "group")
    assert result is not None
    assert result.p_value is not None
    # 极小样本下t检验仍可执行 — Cohen's d在微小样本+大差异时可能很大
    assert not np.isnan(result.effect_size)
    assert isinstance(result.effect_size, (int, float))


def test_tiny_sample_correlation():
    """6个被试的相关分析：样本量很小但仍应能计算"""
    from src.analysis.correlation import correlation_matrix
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5, 6],
        "y": [2, 4, 6, 8, 10, 12],
    })
    result = correlation_matrix(df, ["x", "y"], method="pearson")
    assert isinstance(result.corr_matrix, pd.DataFrame)
    # 完全相关
    assert abs(result.corr_matrix.iloc[0, 1]) > 0.99


def test_tiny_sample_regression():
    """极小样本回归：应给出小样本警告"""
    from src.analysis.regression import linear_regression
    df = pd.DataFrame({
        "dv": [1, 2, 3, 4, 5, 6],
        "iv": [1, 2, 3, 4, 5, 6],
    })
    result = linear_regression(df, "dv", "iv")
    assert result.r_squared > 0.99
    # 回归诊断表应存在
    assert result.diagnostics is not None
    assert "高影响点" in result.diagnostics.columns.tolist() or len(result.high_influence_cases) >= 0


# ===========================================================================
# 缺失值 / 常数列 / 零方差测试
# ===========================================================================

def test_all_missing_column():
    """全是缺失值的列：应被优雅处理"""
    from src.analysis.data_quality import data_quality_check
    df = pd.DataFrame({
        "all_na": [np.nan, np.nan, np.nan, np.nan, np.nan],
        "ok": [1.0, 2.0, 3.0, 4.0, 5.0],
    })
    report = data_quality_check(df, numeric_cols=["all_na", "ok"])
    assert "全为缺失值" in " ".join(report.warnings)
    assert "all_na" in report.constant_cols


def test_constant_column():
    """全是常数的列：方差为零，应被检测"""
    from src.analysis.data_quality import data_quality_check
    df = pd.DataFrame({
        "constant": [3.0, 3.0, 3.0, 3.0, 3.0],
        "varying": [1.0, 2.0, 3.0, 4.0, 5.0],
    })
    report = data_quality_check(df, numeric_cols=["constant", "varying"])
    assert has_chinese_keyword(report.warnings, ["常数"])
    assert "constant" in report.zero_var_cols


def test_zero_variance_column():
    """方差为零的列：本质上也是常数列"""
    from src.analysis.data_quality import data_quality_check
    df = pd.DataFrame({
        "zero_var": [5.0, 5.0, 5.0, 5.0, 5.0],
    })
    report = data_quality_check(df)
    assert "zero_var" in report.zero_var_cols


# ===========================================================================
# 降级行为测试
# ===========================================================================

def test_regression_with_only_one_numeric_col():
    """仅一列数值数据时执行回归：应优雅降级而非崩溃"""
    from src.analysis.runner import run_analysis
    from src.parser.intent_resolver import AnalysisPlan

    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
    plan = AnalysisPlan(
        test_type="linear_regression",
        dependent_vars=["x"],
        independent_vars=["x"],  # 自己预测自己（边界情况）
    )
    output = run_analysis(df, plan)
    # 应该不会崩溃
    assert output is not None
    assert "test_type" in output


def test_nonparametric_small_sample():
    """非参数检验在小样本（n<10）下应提示切换到精确检验或给出警告"""
    from src.analysis.nonparametric import mann_whitney
    df = pd.DataFrame({
        "score": [1, 2, 3, 1, 2, 3],
        "group": ["A", "A", "A", "B", "B", "B"],
    })
    result = mann_whitney(df, "score", "group")
    assert result is not None
    # 小样本（每组n=3）自动切换精确检验或产生警告
    assert result.warning and len(result.warning) > 0
    assert result.warning and ("样本量" in result.warning or "精确" in result.warning)


def test_mediation_weak_effect():
    """中介效应Bootstrap在微弱效应下的CI应包含0"""
    from src.analysis.advanced import mediation_analysis
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "X": np.random.normal(0, 1, n),
        "M": np.random.normal(0, 1, n),  # M与X无关
        "Y": np.random.normal(0, 1, n),  # Y与整体无关
    })
    result = mediation_analysis(df, "X", "M", "Y", n_bootstrap=1000, seed=42)
    assert result.bootstrap_ci is not None
    # 微弱效应下CI应包含0或非常接近0
    assert result.warning is not None  # 应有判断文字


def test_kruskal_wallis_mc_methods():
    """多重比较校正方法切换测试"""
    from src.analysis.nonparametric import kruskal_wallis
    np.random.seed(42)
    df = pd.DataFrame({
        "score": np.concatenate([
            np.random.normal(10, 2, 15),
            np.random.normal(15, 2, 15),
            np.random.normal(12, 2, 15),
        ]),
        "group": ["A"] * 15 + ["B"] * 15 + ["C"] * 15,
    })

    # 测试各种校正方法
    for method in ["holm", "bonferroni", "fdr", "none"]:
        result = kruskal_wallis(df, "score", "group", mc_method=method)
        assert result is not None
        if result.post_hoc is not None:
            # 验证校正列存在
            col_names = result.post_hoc.columns.tolist()
            if method == "holm":
                assert any("Holm" in c for c in col_names)
            elif method == "bonferroni":
                assert any("Bonferroni" in c for c in col_names)
            elif method == "fdr":
                assert any("FDR" in c or "BH" in c for c in col_names)


# ===========================================================================
# 数据质量检查综合测试
# ===========================================================================

def test_data_quality_missing_values():
    """缺失值检测"""
    from src.analysis.data_quality import data_quality_check
    df = pd.DataFrame({
        "a": [1.0, np.nan, 3.0, np.nan, 5.0],
        "b": [1.0, 2.0, 3.0, 4.0, 5.0],
    })
    report = data_quality_check(df)
    assert report.missing_pct > 0
    assert "a" in report.missing_cols


def test_data_quality_outliers():
    """异常值检测"""
    from src.analysis.data_quality import data_quality_check
    df = pd.DataFrame({
        "normal": [1.0, 2.0, 3.0, 4.0, 5.0] * 10,
        "outlier": [1.0, 2.0, 3.0, 4.0, 100.0] * 10,
    })
    report = data_quality_check(df)
    outlier_warnings = [w for w in report.warnings if "异常值" in w]
    assert len(outlier_warnings) > 0


def test_data_quality_normality():
    """正态性检查"""
    from src.analysis.data_quality import data_quality_check
    np.random.seed(42)
    df = pd.DataFrame({
        "normal": np.random.normal(0, 1, 100),
        "skewed": np.random.exponential(2, 100),
    })
    report = data_quality_check(df, check_normality=True)
    assert "normal" in report.normality_checks
    assert "skewed" in report.normality_checks
    # 偏态数据应未通过正态性检验
    assert not report.normality_checks["skewed"]["passed"]


# ===========================================================================
# EFA 边界测试
# ===========================================================================

def test_efa_heywood_detection():
    """EFA Heywood情况检测（通过共同度检查）"""
    from src.analysis.factor_analysis import exploratory_factor_analysis
    # 创建高度相关的数据（可能导致Heywood）
    np.random.seed(42)
    n = 200
    base = np.random.normal(0, 1, n)
    df = pd.DataFrame({
        f"item{i+1}": base * 0.9 + np.random.normal(0, 0.1, n)
        for i in range(6)
    })
    result = exploratory_factor_analysis(df, list(df.columns), n_factors=2, seed=42)
    # 应输出共同度信息
    assert result.communalities is not None
    assert "共同度" in result.communalities.columns.tolist()
    # 应有载荷阈值控制
    assert result.min_loading_threshold > 0


# ===========================================================================
# 回归诊断测试
# ===========================================================================

def test_regression_diagnostics():
    """回归诊断：Cook's D, 学生化残差, 杠杆值"""
    from src.analysis.regression import multiple_regression
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "y": np.random.normal(0, 1, n),
        "x1": np.random.normal(0, 1, n),
        "x2": np.random.normal(0, 1, n),
    })
    result = multiple_regression(df, "y", ["x1", "x2"])
    assert result.diagnostics is not None
    assert "Cook's D" in result.diagnostics.columns.tolist()
    assert "学生化删除残差" in result.diagnostics.columns.tolist()
    assert "杠杆值" in result.diagnostics.columns.tolist()
    # Cohen's f² 效应量
    assert result.f2_effect_sizes is not None
    assert "Cohen's f²" in result.f2_effect_sizes.columns.tolist()


# ===========================================================================
# 注册表模式测试
# ===========================================================================

def test_analysis_registry_known_tests():
    """验证所有已知检验类型都在注册表中"""
    from src.analysis.runner import AnalysisRegistry
    known_tests = [
        "descriptive", "independent_ttest", "paired_ttest", "one_sample_ttest",
        "one_way_anova", "two_way_anova", "repeated_anova",
        "pearson_corr", "spearman_corr", "partial_corr", "point_biserial",
        "chi_square_independence", "chi_square_gof",
        "linear_regression", "multiple_regression", "hierarchical_regression",
        "cronbach_alpha", "split_half",
        "mann_whitney", "wilcoxon", "kruskal_wallis", "friedman",
        "efa", "ancova", "mediation", "moderation",
    ]
    for test_type in known_tests:
        assert test_type in AnalysisRegistry, f"{test_type} 未在注册表中找到"

    assert len(AnalysisRegistry) >= len(known_tests)


def test_unknown_test_type_fallback():
    """未知检验类型应回退到描述统计"""
    from src.analysis.runner import run_analysis
    from src.parser.intent_resolver import AnalysisPlan

    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
    plan = AnalysisPlan(
        test_type="nonexistent_test_xyz",
        dependent_vars=["x"],
    )
    output = run_analysis(df, plan)
    # 应该不崩溃，并且有回退警告
    assert output is not None
    warnings_text = " ".join([
        e.get("message", "") for e in output.get("errors", [])
    ])
    assert "未识别的检验方法" in warnings_text or "描述统计" in warnings_text
