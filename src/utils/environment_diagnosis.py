"""环境诊断模块 — v5.3 新增。

检测运行环境的各项依赖，为用户和发布门禁提供诊断信息。
"""
import sys
import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DiagnosisItem:
    name: str
    status: str  # "ok" | "warning" | "missing" | "error"
    detail: str
    required: bool = True


@dataclass
class EnvironmentDiagnosis:
    items: list[DiagnosisItem] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(i.status == "ok" for i in self.items if i.required)

    @property
    def summary(self) -> dict:
        return {
            "total": len(self.items),
            "ok": sum(1 for i in self.items if i.status == "ok"),
            "warning": sum(1 for i in self.items if i.status == "warning"),
            "missing": sum(1 for i in self.items if i.status == "missing"),
            "error": sum(1 for i in self.items if i.status == "error"),
            "all_required_ok": self.all_ok,
        }

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "items": [
                {"name": i.name, "status": i.status, "detail": i.detail, "required": i.required}
                for i in self.items
            ],
        }


def run_full_diagnosis(project_root: Optional[Path] = None) -> EnvironmentDiagnosis:
    """运行完整环境诊断。"""
    diag = EnvironmentDiagnosis()

    # Python version
    py_ver = platform.python_version()
    py_ok = sys.version_info >= (3, 10)
    diag.items.append(DiagnosisItem(
        name="Python 版本",
        status="ok" if py_ok else "error",
        detail=f"Python {py_ver}" + ("" if py_ok else " (需要 ≥3.10)"),
        required=True,
    ))

    # Streamlit
    try:
        import streamlit
        diag.items.append(DiagnosisItem("Streamlit", "ok", f"v{streamlit.__version__}"))
    except ImportError:
        diag.items.append(DiagnosisItem("Streamlit", "missing", "未安装 streamlit"))

    # pandas/numpy/scipy
    for pkg_name, display in [("pandas", "Pandas"), ("numpy", "NumPy"), ("scipy", "SciPy")]:
        try:
            pkg = __import__(pkg_name)
            diag.items.append(DiagnosisItem(display, "ok", f"v{pkg.__version__}"))
        except ImportError:
            diag.items.append(DiagnosisItem(display, "missing", f"未安装 {pkg_name}"))

    # python-docx
    try:
        import docx  # noqa: F401
        diag.items.append(DiagnosisItem("python-docx", "ok", "Word 导出可用"))
    except ImportError:
        diag.items.append(DiagnosisItem("python-docx", "missing", "Word 导出不可用"))

    # matplotlib (for figures)
    try:
        import matplotlib
        diag.items.append(DiagnosisItem("Matplotlib", "ok", f"v{matplotlib.__version__}"))
    except ImportError:
        diag.items.append(DiagnosisItem("Matplotlib", "missing", "图表生成不可用"))

    # Word/LibreOffice (PDF conversion)
    word_path = shutil.which("WINWORD") or shutil.which("WINWORD.EXE")
    lo_path = shutil.which("soffice") or shutil.which("soffice.exe")
    if word_path:
        diag.items.append(DiagnosisItem("Microsoft Word", "ok", "PDF 转换可用", required=False))
    elif lo_path:
        diag.items.append(DiagnosisItem("LibreOffice", "ok", "PDF 转换可用（备用）", required=False))
    else:
        diag.items.append(DiagnosisItem("PDF 转换", "warning", "Word/LibreOffice 均未找到，PDF 导出不可用", required=False))

    # Chinese fonts
    try:
        import matplotlib.font_manager as fm
        zh_fonts = [f.name for f in fm.fontManager.ttflist
                    if any(kw in f.name for kw in ["SimHei", "YaHei", "SimSun", "FangSong", "KaiTi"])]
        if zh_fonts:
            diag.items.append(DiagnosisItem("中文字体", "ok", f"可用：{', '.join(set(zh_fonts)[:3])}"))
        else:
            diag.items.append(DiagnosisItem("中文字体", "warning", "未检测到常用中文字体，图表可能显示异常", required=False))
    except Exception:
        diag.items.append(DiagnosisItem("中文字体", "warning", "无法检测字体", required=False))

    # Playwright
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        diag.items.append(DiagnosisItem("Playwright", "ok", "浏览器 E2E 可用", required=False))
    except ImportError:
        diag.items.append(DiagnosisItem("Playwright", "missing", "浏览器 E2E 不可用（不影响正常使用）", required=False))

    # LLM API Key
    import os
    has_key = bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY") or
                   os.environ.get("DEEPSEEK_API_KEY"))
    if has_key:
        diag.items.append(DiagnosisItem("LLM API Key", "ok", "AI 辅助功能可用", required=False))
    else:
        diag.items.append(DiagnosisItem("LLM API Key", "warning", "未配置，AI 辅助功能不可用（统计分析不受影响）", required=False))

    # Cache directories
    if project_root:
        cache_dirs = []
        for d in [".cache", "__pycache__", ".streamlit", "temp_exports"]:
            p = project_root / d
            if p.exists():
                size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                cache_dirs.append(f"{d}: {size/1024/1024:.1f}MB")
        if cache_dirs:
            diag.items.append(DiagnosisItem("缓存目录", "ok", "; ".join(cache_dirs), required=False))

    # WebView2
    if platform.system() == "Windows":
        webview_ok = shutil.which("msedge") is not None or Path(
            os.environ.get("LOCALAPPDATA", ""), "Microsoft", "EdgeWebView"
        ).exists()
        diag.items.append(DiagnosisItem(
            "WebView2",
            "ok" if webview_ok else "warning",
            "桌面模式可用" if webview_ok else "桌面模式可能不可用，将使用浏览器模式",
            required=False,
        ))

    return diag


def format_diagnosis_for_streamlit(diag: EnvironmentDiagnosis) -> list[dict]:
    """格式化诊断结果供 Streamlit 渲染。"""
    icons = {"ok": "✅", "warning": "⚠️", "missing": "❌", "error": "\U0001f6ab"}
    return [
        {"icon": icons.get(i.status, "❓"), "name": i.name, "detail": i.detail, "required": i.required}
        for i in diag.items
    ]
