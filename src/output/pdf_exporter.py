"""PDF 导出器 — docx → PDF 转换，支持多后端降级。

优先级:
1. Microsoft Word COM (Windows, 需 pywin32 + MS Word)
2. LibreOffice headless (跨平台, 需安装 LibreOffice)
3. 降级: 返回 None + 明确原因

设计原则:
- PDF 导出失败绝不阻断主流程（Word/ZIP 照常导出）
- 清晰告知用户不可用原因和手动替代方案
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PDFResult:
    """PDF 转换结果。"""
    success: bool
    pdf_bytes: Optional[bytes] = None
    method: str = ""
    error: str = ""
    suggestion: str = ""


def convert_docx_to_pdf(docx_bytes: bytes) -> PDFResult:
    """将 docx 字节流转为 PDF。自动选择可用后端。"""
    backends = [
        _try_word_com,
        _try_libreoffice,
    ]
    for backend in backends:
        result = backend(docx_bytes)
        if result.success:
            return result

    return PDFResult(
        success=False,
        method="none",
        error="当前环境无可用 PDF 转换工具",
        suggestion="请手动将 .docx 文件通过 Word 或 WPS 另存为 PDF；或安装 LibreOffice (https://www.libreoffice.org/)",
    )


def check_pdf_availability() -> tuple[bool, str]:
    """检查当前环境是否支持 PDF 转换。返回 (可用, 方法名)。"""
    if _word_com_available():
        return True, "Microsoft Word COM"
    if _libreoffice_available():
        return True, "LibreOffice"
    return False, ""


def _word_com_available() -> bool:
    if os.name != "nt":
        return False
    try:
        import win32com.client  # noqa: F401
        return True
    except ImportError:
        return False


def _libreoffice_available() -> bool:
    paths = _get_libreoffice_paths()
    for p in paths:
        if Path(p).exists():
            return True
    try:
        result = subprocess.run(
            ["soffice", "--version"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_libreoffice_paths() -> list[str]:
    if os.name == "nt":
        return [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
    return ["/usr/bin/soffice", "/usr/local/bin/soffice", "/opt/libreoffice/program/soffice"]


def _try_word_com(docx_bytes: bytes) -> PDFResult:
    if os.name != "nt":
        return PDFResult(success=False, method="word_com", error="非 Windows 环境")
    try:
        import win32com.client
    except ImportError:
        return PDFResult(success=False, method="word_com", error="pywin32 未安装")

    tmp_dir = tempfile.mkdtemp(prefix="psy_pdf_")
    docx_path = os.path.join(tmp_dir, "paper.docx")
    pdf_path = os.path.join(tmp_dir, "paper.pdf")

    try:
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        try:
            doc = word.Documents.Open(docx_path)
            doc.SaveAs2(pdf_path, FileFormat=17)  # 17 = wdFormatPDF
            doc.Close()
        finally:
            word.Quit()

        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            return PDFResult(success=True, pdf_bytes=pdf_bytes, method="word_com")
        else:
            return PDFResult(success=False, method="word_com", error="Word 转换后 PDF 文件为空")
    except Exception as e:
        return PDFResult(success=False, method="word_com", error=f"Word COM 转换失败: {e}")
    finally:
        _cleanup_tmp(tmp_dir)


def _try_libreoffice(docx_bytes: bytes) -> PDFResult:
    soffice = None
    for p in _get_libreoffice_paths():
        if Path(p).exists():
            soffice = p
            break
    if not soffice:
        try:
            subprocess.run(["soffice", "--version"], capture_output=True, timeout=5)
            soffice = "soffice"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return PDFResult(success=False, method="libreoffice", error="LibreOffice 未安装")

    tmp_dir = tempfile.mkdtemp(prefix="psy_pdf_")
    docx_path = os.path.join(tmp_dir, "paper.docx")

    try:
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        result = subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp_dir, docx_path],
            capture_output=True, timeout=60,
        )

        pdf_path = os.path.join(tmp_dir, "paper.pdf")
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            return PDFResult(success=True, pdf_bytes=pdf_bytes, method="libreoffice")
        else:
            stderr = result.stderr.decode(errors="replace")[:200]
            return PDFResult(success=False, method="libreoffice",
                             error=f"LibreOffice 转换后无 PDF 输出: {stderr}")
    except subprocess.TimeoutExpired:
        return PDFResult(success=False, method="libreoffice", error="LibreOffice 转换超时（60s）")
    except Exception as e:
        return PDFResult(success=False, method="libreoffice", error=f"LibreOffice 转换失败: {e}")
    finally:
        _cleanup_tmp(tmp_dir)


def _cleanup_tmp(tmp_dir: str):
    """清理临时目录。"""
    import shutil
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass
