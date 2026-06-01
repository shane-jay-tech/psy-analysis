"""pytest 全局配置 — 警告分类与抑制。

v2.9 警告清理策略：
- fpdf2 的 ln=True 弃用警告 → 已修复源代码（用 new_x/new_y 替代）
- statsmodels 的 HLM 奇异协方差矩阵 → 第三方，HLM 测试预期数据下必然出现
- factor_analyzer 的 Moore-Penrose 伪逆 → 第三方，鲁棒性测试中故意构造的边界情况
- scipy 的 invalid value in divide → 第三方，pipeline 测试在小样本边界触发

每条 ignore 都注释了原因；保留可见的警告（如代码 bug、新弃用）。

v3.3: 新增 benchmark 标记与 --run-benchmark 命令行选项（反问质量基准）。
"""

import warnings

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-benchmark",
        action="store_true",
        default=False,
        help="运行反问质量基准测试（需 LLM API key）",
    )


def pytest_collection_modifyitems(config, items):
    """未传 --run-benchmark 时跳过 @pytest.mark.benchmark。"""
    if config.getoption("--run-benchmark", default=False):
        return
    skip_benchmark = pytest.mark.skip(reason="需要 --run-benchmark 才运行（默认跳过）")
    for item in items:
        if "benchmark" in item.keywords:
            item.add_marker(skip_benchmark)


def pytest_configure(config):
    """注册警告过滤器（按特异度从高到低）。"""
    config.addinivalue_line(
        "markers", "benchmark: 反问质量基准（默认跳过，需 --run-benchmark）",
    )

    # ------------------------------------------------------------- #
    # 第三方库内部警告（无法修复，仅抑制）
    # ------------------------------------------------------------- #

    # statsmodels HLM: 模拟数据下随机效应协方差矩阵奇异，
    # 在 test_ui.py 的 test_hlm_performance 中预期出现
    warnings.filterwarnings(
        "ignore",
        message=r".*[Rr]andom effects covariance.*singular.*",
        category=UserWarning,
        module=r"statsmodels.*",
    )

    # statsmodels HLM: sqrt(neg) 边界值
    warnings.filterwarnings(
        "ignore",
        message=r".*invalid value encountered in sqrt.*",
        category=RuntimeWarning,
        module=r"statsmodels.*",
    )

    # factor_analyzer: EFA Heywood 检测测试中故意构造的退化协方差矩阵
    warnings.filterwarnings(
        "ignore",
        message=r".*Moore-Penrose generalized matrix inversion.*",
        category=UserWarning,
        module=r"factor_analyzer.*",
    )

    # scipy.stats Shapiro 在小样本+常数列时除零
    warnings.filterwarnings(
        "ignore",
        message=r".*invalid value encountered in divide.*",
        category=RuntimeWarning,
        module=r"scipy.stats.*",
    )

    # ------------------------------------------------------------- #
    # 第三方依赖间接弃用警告（升级依赖时再处理）
    # ------------------------------------------------------------- #

    warnings.filterwarnings(
        "ignore",
        message=r".*pkg_resources is deprecated.*",
        category=DeprecationWarning,
    )

    warnings.filterwarnings(
        "ignore",
        message=r".*'cgi' is deprecated.*",
        category=DeprecationWarning,
    )

    # plotly.io.from_json 的内部 Pandas 兼容警告（非用户代码）
    warnings.filterwarnings(
        "ignore",
        category=FutureWarning,
        module=r"plotly\..*",
    )
