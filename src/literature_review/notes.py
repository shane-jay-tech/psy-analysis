"""阅读笔记 CRUD：create / edit / delete / 按文献聚合 / 按主题聚合 / Markdown 导出。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from .models import NOTE_TYPES, ReadingNote


# ---------------------------------------------------------------------------
# CRUD（操作 List[ReadingNote]，调用方负责持久化）
# ---------------------------------------------------------------------------

def create_note(
    notes: List[ReadingNote],
    *,
    literature_key: str,
    content: str,
    type: str = "其他",
    page_or_section: str = "",
) -> ReadingNote:
    """新建笔记并 append 到 notes 列表。返回新笔记。"""
    if type not in NOTE_TYPES:
        type = "其他"
    note = ReadingNote(
        literature_key=literature_key,
        content=content or "",
        page_or_section=page_or_section or "",
        type=type,
    )
    notes.append(note)
    return note


def edit_note(notes: List[ReadingNote], note_id: str, new_content: str) -> bool:
    """编辑指定 note_id 的内容；返回是否成功。"""
    for n in notes:
        if n.note_id == note_id:
            n.update_content(new_content)
            return True
    return False


def delete_note(notes: List[ReadingNote], note_id: str) -> bool:
    """删除指定 note_id；返回是否成功。"""
    for i, n in enumerate(notes):
        if n.note_id == note_id:
            notes.pop(i)
            return True
    return False


def get_notes_by_literature(
    notes: List[ReadingNote], literature_key: str,
) -> List[ReadingNote]:
    """按文献 key 聚合笔记。"""
    return [n for n in notes if n.literature_key == literature_key]


def get_notes_by_theme(
    notes: List[ReadingNote],
    theme_literature_keys: Iterable[str],
) -> List[ReadingNote]:
    """按主题包含的文献 key 列表聚合笔记。"""
    keys = set(theme_literature_keys or [])
    return [n for n in notes if n.literature_key in keys]


def filter_notes_by_type(
    notes: List[ReadingNote],
    type: str,
) -> List[ReadingNote]:
    """按笔记类型过滤。"""
    if type not in NOTE_TYPES:
        return []
    return [n for n in notes if n.type == type]


# ---------------------------------------------------------------------------
# Markdown 导出
# ---------------------------------------------------------------------------

def export_notes_markdown(
    notes: List[ReadingNote],
    *,
    literature_lookup: Optional[Dict[str, Any]] = None,
    title: str = "阅读笔记",
) -> str:
    """导出笔记为 Markdown（可粘贴到 Word/Notion）。

    Args:
        notes: 笔记列表
        literature_lookup: {literature_key → LiteratureItem}（可选，用于显示文献标题）
        title: 文档标题
    """
    if not notes:
        return f"# {title}\n\n（暂无笔记）\n"

    lines: List[str] = [f"# {title}", "", f"_导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_", ""]

    # 按文献分组
    by_lit: Dict[str, List[ReadingNote]] = {}
    for n in notes:
        by_lit.setdefault(n.literature_key, []).append(n)

    for lit_key, lit_notes in by_lit.items():
        # 文献标题
        if literature_lookup and lit_key in literature_lookup:
            item = literature_lookup[lit_key]
            authors = getattr(item, "authors", []) or []
            year = getattr(item, "year", "")
            article_title = getattr(item, "title", "")
            first_author = authors[0] if authors else "Unknown"
            heading = f"## {first_author} ({year})"
            lines.extend([heading, "", f"**{article_title}**", ""])
        else:
            lines.extend([f"## 文献 `{lit_key}`", ""])

        for n in lit_notes:
            type_label = n.type or "其他"
            page = f"（{n.page_or_section}）" if n.page_or_section else ""
            lines.append(f"### [{type_label}]{page}")
            lines.append("")
            # 简单 Markdown 渲染（保留原文）
            lines.append(_safe_markdown(n.content))
            lines.append("")
            lines.append(f"_笔记 ID: {n.note_id}　创建于 {n.created_at}_")
            lines.append("")

    return "\n".join(lines)


_MD_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


def _safe_markdown(text: str) -> str:
    """简单清理 Markdown：保留粗体/列表/引用，转义裸 < > 防 HTML 注入。"""
    if not text:
        return ""
    safe = text.replace("<", "&lt;").replace(">", "&gt;")
    return safe


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------

def notes_to_dict_list(notes: List[ReadingNote]) -> List[Dict[str, Any]]:
    return [n.to_dict() for n in notes]


def notes_from_dict_list(data: List[Dict[str, Any]]) -> List[ReadingNote]:
    if not isinstance(data, list):
        return []
    return [ReadingNote.from_dict(d) for d in data if isinstance(d, dict)]
