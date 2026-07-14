"""统一导出文件命名规则。

格式：{项目名}_{模块}_{日期}.{ext}
示例：我的研究_数据分析_20260702.docx
"""
import re
from datetime import datetime

import streamlit as st


def export_filename(module: str, ext: str, title: str | None = None) -> str:
    """生成统一格式的导出文件名。

    Args:
        module: 模块标识（如 "数据分析"、"问卷设计"、"论文"）
        ext: 文件扩展名（不含点，如 "docx"、"xlsx"、"pdf"、"zip"）
        title: 可选项目名/文档标题，为空时尝试从 session_state 取
    """
    if not title:
        title = _get_project_name()
    title = _sanitize(title)
    module = _sanitize(module)
    date_str = datetime.now().strftime("%Y%m%d")
    return f"{title}_{module}_{date_str}.{ext.lstrip('.')}"


def _get_project_name() -> str:
    """尝试从 session_state 获取当前项目名。"""
    for key in ("project_name", "current_project", "thesis_title"):
        val = st.session_state.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return "导出"


def _sanitize(s: str) -> str:
    """移除文件名不安全字符，保留中文。"""
    s = s.strip()[:30]
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', '', s)
    return s or "未命名"
