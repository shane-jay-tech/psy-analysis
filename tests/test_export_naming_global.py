"""导出命名全局一致性扫描测试。

静态扫描所有 UI 文件中 st.download_button 的 file_name 参数，
确保用户结果文件都走 export_filename() 工具函数，而非硬编码。
"""
import ast
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = PROJECT_ROOT / "src" / "ui"

WHITELIST_PATTERNS = [
    "survey_template",
    "experiment_template",
    "README",
    "示例数据",
]


def _find_download_buttons(filepath: Path) -> list[dict]:
    """扫描 Python 文件中 st.download_button 的 file_name 参数。"""
    results = []
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return results

    for i, line in enumerate(source.splitlines(), 1):
        if "download_button" in line and "file_name" in line:
            m = re.search(r'file_name\s*=\s*["\']([^"\']+)["\']', line)
            if m:
                results.append({
                    "file": str(filepath.relative_to(PROJECT_ROOT)),
                    "line": i,
                    "filename": m.group(1),
                    "raw_line": line.strip(),
                })
    return results


def _is_whitelisted(filename: str) -> bool:
    return any(p in filename for p in WHITELIST_PATTERNS)


def _uses_export_filename(line: str) -> bool:
    return "export_filename" in line or "efn(" in line or "_efn(" in line


class TestExportNamingConsistency:
    """确保用户下载文件都走 export_filename()。"""

    def test_all_ui_files_parseable(self):
        """所有 UI 文件语法正确。"""
        for f in UI_DIR.glob("*.py"):
            source = f.read_text(encoding="utf-8", errors="ignore")
            ast.parse(source)

    def test_download_buttons_use_export_filename(self):
        """st.download_button 中 file_name 应使用 export_filename 或在白名单。"""
        violations = []

        for py_file in UI_DIR.glob("*.py"):
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            lines = source.splitlines()

            for i, line in enumerate(lines, 1):
                if "download_button" not in line:
                    continue
                if "file_name" not in line:
                    # file_name 可能在下一行
                    if i < len(lines) and "file_name" in lines[i]:
                        line = line + lines[i]
                    else:
                        continue

                # 如果 file_name 用了 export_filename / _efn，通过
                if _uses_export_filename(line):
                    continue

                # 检查是否是 session_state 获取（动态值，已通过其他路径设置）
                if "session_state" in line and "get" in line:
                    continue

                # 硬编码文件名 — 检查白名单
                m = re.search(r'file_name\s*=\s*["\']([^"\']+)["\']', line)
                if m and not _is_whitelisted(m.group(1)):
                    violations.append(
                        f"{py_file.name}:{i} — hardcoded: '{m.group(1)}'"
                    )

        if violations:
            msg = f"Found {len(violations)} hardcoded file_name(s):\n"
            msg += "\n".join(f"  {v}" for v in violations[:10])
            pytest.fail(msg)

    def test_export_filename_handles_edge_cases(self):
        """export_filename 处理中文、特殊字符、空标题。"""
        from src.utils.export_naming import export_filename

        # 正常情况
        result = export_filename("论文初稿", "docx", title="我的论文")
        assert result.endswith(".docx")
        assert "论文初稿" in result

        # 空标题
        result = export_filename("报告", "pdf", title="")
        assert result.endswith(".pdf")

        # 特殊字符
        result = export_filename("数据", "csv", title="test/file:name")
        assert "/" not in result
        assert ":" not in result
