"""版本号一致性测试 — 确保 src/version.py 是唯一事实源。"""
import re
from pathlib import Path

from src.version import APP_VERSION, APP_VERSION_LABEL


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_version_label_matches_version():
    """APP_VERSION_LABEL 与 APP_VERSION 一致。"""
    assert APP_VERSION_LABEL == f"v{'.'.join(APP_VERSION.split('.')[:2])}"


def test_app_py_imports_from_version_module():
    """app.py 从 src.version 读取版本而非硬编码。"""
    app_py = PROJECT_ROOT / "app.py"
    text = app_py.read_text(encoding="utf-8", errors="ignore")
    assert "from src.version import" in text


def test_report_script_uses_version_module():
    """generate_system_report.py 从 src.version 读取版本。"""
    script = PROJECT_ROOT / "scripts" / "generate_system_report.py"
    text = script.read_text(encoding="utf-8", errors="ignore")
    assert "from src.version import" in text
