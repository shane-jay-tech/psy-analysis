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
from pathlib import Path

import pytest


_APP_TEST_FILES = {
    "test_e2e_rendering.py",
    "test_e2e_ui.py",
    "test_e2e_v52_paths.py",
    "test_playwright_e2e.py",
    "test_playwright_golden_research_flow.py",
}


@pytest.fixture(autouse=True)
def isolate_streamlit_app_test_storage(request, monkeypatch, tmp_path):
    """AppTest 不得读取或写入用户真实项目、偏好、档案和事件日志。"""
    if Path(str(request.node.fspath)).name not in _APP_TEST_FILES:
        return

    from src.utils import archive_manager, autosave, project_manager, usage_logger, user_prefs

    app_home = tmp_path / ".psy_analysis"
    projects_dir = app_home / "projects"
    monkeypatch.setenv("PSY_ANALYSIS_HOME", str(app_home))
    monkeypatch.setenv("PSY_ANALYSIS_ARCHIVE_DIR", str(tmp_path / "archive"))
    monkeypatch.setenv("PSY_ANALYSIS_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(project_manager, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(project_manager, "INDEX_FILE", projects_dir / "index.json")
    monkeypatch.setattr(user_prefs, "PREFS_DIR", app_home)
    monkeypatch.setattr(user_prefs, "PREFS_FILE", app_home / "user_prefs.json")
    monkeypatch.setattr(autosave, "LEGACY_AUTOSAVE_FILE", app_home / "autosave.json")
    monkeypatch.setattr(autosave, "LEGACY_META_FILE", app_home / "autosave_meta.json")
    monkeypatch.setattr(archive_manager, "ARCHIVE_ROOT", tmp_path / "archive")
    monkeypatch.setattr(usage_logger, "_LOG_DIR", tmp_path / "logs")


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
