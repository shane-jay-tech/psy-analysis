"""v5.8: 启动环境检查性能测试。

核心回归目标：env_check 的启动自检必须**不真正 import** 重型统计依赖
（pingouin/statsmodels/semopy/sklearn 等），把首次页面加载从 20s+ 降到毫秒级。
"""
import sys
import time
from pathlib import Path

from src.utils.env_check import (
    check_critical_deps,
    check_factor_analyzer,
    check_kaleido,
    check_semopy,
    run_deep_environment_check,
    run_startup_check,
)

HEAVY = ("pingouin", "statsmodels", "semopy", "sklearn", "scipy", "openpyxl")


class TestKaleidoTieredProbe:
    """s1004-32：kaleido 深检三级契约（包缺/浏览器缺/全具备，0e66 遗留）。

    深检后 check_kaleido 的真值取决于本机有无 Chrome/Chromium（真渲染依赖），
    故全环境断言改为分级契约断言，不再假设任一固定真值。
    """

    def test_browser_missing_reports_browser_tier_not_ok(self, monkeypatch):
        """无浏览器环境（env 清空模拟）⇒ False＋「浏览器」文案，不得假 ok。

        s1114：模拟须同时清 PLAYWRIGHT_BROWSERS_PATH——探测根新增该自定义根后，
        漏清会把本机真浏览器泄进"无浏览器"模拟（模拟不完整＝假红）。
        """
        monkeypatch.setenv("BROWSER_PATH", "")
        monkeypatch.setenv("PROGRAMFILES", "Z:/nonexistent-s1004-32")
        monkeypatch.setenv("PROGRAMFILES(X86)", "Z:/nonexistent-s1004-32")
        monkeypatch.setenv("LOCALAPPDATA", "Z:/nonexistent-s1004-32")
        monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
        ok, msg = check_kaleido()
        assert ok is False
        assert "浏览器" in msg

    def test_custom_playwright_root_is_probed_s1114(self, monkeypatch, tmp_path):
        """s1114 回归钉：PLAYWRIGHT_BROWSERS_PATH 自定义根下的 chromium 可被探测到。

        背景：自定义根环境（如 D:\\ms-playwright）下旧探测只认 LOCALAPPDATA 默认根
        ⇒ 返回 None ⇒ kaleido 有包无浏览器运行时（导出族 10F 根因）。
        """
        from src.utils.browser_detect import find_local_chromium

        fake_root = tmp_path / "ms-playwright"
        fake_chrome = fake_root / "chromium-1248" / "chrome-win64" / "chrome.exe"
        fake_chrome.parent.mkdir(parents=True)
        fake_chrome.write_bytes(b"fake")

        monkeypatch.setenv("BROWSER_PATH", "")
        monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "no-chrome-here"))
        monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path / "no-chrome-here"))
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "no-chrome-here"))
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(fake_root))

        found = find_local_chromium()
        assert found == fake_chrome

    def test_default_localappdata_root_still_probed_s1114(self, monkeypatch, tmp_path):
        """s1114 回归钉：默认 LOCALAPPDATA\\ms-playwright 根探测不回归（旧行为保持）。"""
        from src.utils.browser_detect import find_local_chromium

        fake_root = tmp_path / "default-mspw"
        fake_chrome = fake_root / "ms-playwright" / "chromium-1200" / "chrome-win" / "chrome.exe"
        fake_chrome.parent.mkdir(parents=True)
        fake_chrome.write_bytes(b"fake")

        monkeypatch.setenv("BROWSER_PATH", "")
        monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "no-chrome-here"))
        monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path / "no-chrome-here"))
        monkeypatch.setenv("LOCALAPPDATA", str(fake_root))
        monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

        assert find_local_chromium() == fake_chrome

    def test_all_present_reports_ok_with_browser_name(self, monkeypatch):
        """全具备（浏览器在）⇒ True＋附浏览器名（tier-3 契约）。"""
        import src.utils.env_check as ec

        # env_check 顶层按值导入 find_local_chromium ⇒ 须 patch env_check 名下引用
        monkeypatch.setattr(ec, "find_local_chromium", lambda: Path("C:/fake/chrome.exe"))
        ok, msg = check_kaleido()
        assert ok is True
        assert "chrome.exe" in msg

    def test_package_missing_reports_package_tier(self, monkeypatch):
        """包缺 ⇒ False＋「未安装」文案（tier-1 契约）。"""
        import src.utils.env_check as ec

        monkeypatch.setattr(ec, "_probe", lambda name: (False, "kaleido 未安装"))
        ok, msg = ec.check_kaleido()
        assert ok is False
        assert "未安装" in msg


def _fresh_modules():
    return {m for m in HEAVY if m in sys.modules}


class TestProbesDoNotImportHeavyDeps:
    def test_probes_report_ok_in_full_env(self):
        assert check_semopy()[0] is True
        # kaleido 深检后真值随浏览器在位与否（本机可能无 Chrome）⇒ 改由
        # TestKaleidoTieredProbe 分级契约覆盖，此处不再假设固定 True（s1004-32）。
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
