"""v5.8: 启动环境检查性能测试。

核心回归目标：env_check 的启动自检必须**不真正 import** 重型统计依赖
（pingouin/statsmodels/semopy/sklearn 等），把首次页面加载从 20s+ 降到毫秒级。
"""
import sys
import time

from src.utils.env_check import (
    check_critical_deps,
    check_factor_analyzer,
    check_kaleido,
    check_semopy,
    run_deep_environment_check,
    run_startup_check,
)

HEAVY = ("pingouin", "statsmodels", "semopy", "sklearn", "scipy", "openpyxl")


def _fresh_modules():
    return {m for m in HEAVY if m in sys.modules}


class TestProbesDoNotImportHeavyDeps:
    def test_probes_report_ok_in_full_env(self):
        assert check_semopy()[0] is True
        assert check_kaleido()[0] is True
        assert check_factor_analyzer()[0] is True

    def test_probes_do_not_import_heavy_modules(self):
        before = _fresh_modules()
        check_semopy()
        check_kaleido()
        check_factor_analyzer()
        check_critical_deps()
        after = _fresh_modules()
        assert after == before, f"探测检查不应 import 重型依赖：新增 {after - before}"

    def test_critical_deps_all_ok_in_full_env(self):
        results = check_critical_deps()
        names = {r[0] for r in results}
        assert {"pandas", "numpy", "scipy", "statsmodels", "pingouin", "streamlit"} <= names
        assert all(ok for _, ok, _ in results)


class TestStartupCheckIsFast:
    def test_run_startup_check_returns_full_status(self):
        status = run_startup_check()
        for key in ("semopy_ok", "factor_analyzer_ok", "kaleido_ok", "llm_ok",
                    "critical_ok", "warnings", "errors", "details"):
            assert key in status
        assert status["critical_ok"] is True

    def test_run_startup_check_does_not_import_heavy_modules(self):
        before = _fresh_modules()
        run_startup_check()
        after = _fresh_modules()
        assert after == before, f"启动自检不应 import 重型依赖：新增 {after - before}"

    def test_fast_deep_check_skips_pdf_docx_generation(self):
        report = run_deep_environment_check(fast=True)
        check_names = [name for name, _, _ in report["checks"]]
        assert "PDF 生成" not in check_names
        assert "Word 生成" not in check_names

    def test_full_deep_check_includes_pdf_docx(self):
        report = run_deep_environment_check(fast=False)
        check_names = [name for name, _, _ in report["checks"]]
        assert "PDF 生成" in check_names
        assert "Word 生成" in check_names
