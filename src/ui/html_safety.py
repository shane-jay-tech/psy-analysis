"""面向本地下载文件的安全 HTML 转换。"""

from __future__ import annotations

import html


def questionnaire_report_to_html_fragment(report: str) -> str:
    """转义问卷报告文本，仅允许系统生成的标题与分隔线标签。"""
    safe_lines: list[str] = []
    for line in str(report).splitlines():
        safe_line = html.escape(line)
        if safe_line.startswith("## "):
            safe_line = f"<h2>{safe_line[3:]}</h2>"
        elif safe_line.startswith("# "):
            safe_line = f"<h1>{safe_line[2:]}</h1>"
        elif safe_line.strip() == "---":
            safe_line = "<hr>"
        safe_lines.append(safe_line)
    return "<br>".join(safe_lines)
