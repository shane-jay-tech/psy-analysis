"""自审循环：导出带标记 Markdown → 用户/导师批注 → 解析回 ReadingNote / LiteratureItem。

v3.5 单用户场景：「导师批注」简化为「自审批注」——同一用户自己审阅自己的文献综述。
机制：标记格式 [REVIEW:literature_key] / [REVIEW_NOTE:note_id]，批注格式 [COMMENT: ...]。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .models import LiteratureItem, ReadingNote


_REVIEW_LIT_RE = re.compile(r"\[REVIEW:([a-zA-Z0-9_-]+)\]")
_REVIEW_NOTE_RE = re.compile(r"\[REVIEW_NOTE:([a-zA-Z0-9_-]+)\]")
_REVIEW_MATRIX_RE = re.compile(r"\[REVIEW_MATRIX:([a-zA-Z0-9_-]+):([^\]]+)\]")
_COMMENT_RE = re.compile(r"\[COMMENT:\s*([^\]]+)\]")


def export_for_review(
    items: List[LiteratureItem],
    notes: List[ReadingNote],
    matrix: Optional[Dict[str, Any]] = None,
    *,
    title: str = "文献综述自审版",
) -> str:
    """生成带 REVIEW 标记的 Markdown，供用户/导师批注。"""
    lines: List[str] = [
        f"# {title}",
        "",
        f"_导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        "---",
        "**批注格式**：在任意 [REVIEW:...] 标记下方插入 `[COMMENT: 你的批注]`，"
        "再用 `import_review_comments` 导回。",
        "---",
        "",
    ]

    notes_by_lit: Dict[str, List[ReadingNote]] = {}
    for n in notes:
        notes_by_lit.setdefault(n.literature_key, []).append(n)

    for it in items:
        first_author = it.authors[0] if it.authors else "Unknown"
        lines.append(f"## [REVIEW:{it.key}] {first_author} ({it.year})")
        lines.append("")
        lines.append(f"**{it.title}**")
        lines.append("")
        lines.append(f"_期刊：{it.journal}　DOI：{it.doi or '—'}　相关性：{it.relevance_score:.0%}_")
        lines.append("")
        if it.abstract:
            lines.append(f"> {it.abstract[:200]}")
            lines.append("")

        # 笔记
        for n in notes_by_lit.get(it.key, []):
            lines.append(f"### [REVIEW_NOTE:{n.note_id}] [{n.type}] {n.page_or_section or ''}")
            lines.append("")
            lines.append(n.content)
            lines.append("")

        lines.append("---")
        lines.append("")

    # 矩阵
    if matrix and matrix.get("dimensions"):
        lines.append("## 文献矩阵")
        lines.append("")
        for lit_key, row in (matrix.get("cells") or {}).items():
            for d in matrix["dimensions"]:
                cell = row.get(d, "")
                if cell:
                    lines.append(f"- [REVIEW_MATRIX:{lit_key}:{d}] {cell}")
        lines.append("")

    return "\n".join(lines)


def import_review_comments(md_text: str) -> Dict[str, List[Dict[str, str]]]:
    """解析批注后的 Markdown，返回每个目标的批注列表。

    返回结构：
        {
            "literature": {literature_key: [comment, ...], ...},
            "notes":      {note_id: [comment, ...], ...},
            "matrix":     {literature_key:dimension: [comment, ...], ...},
        }
    """
    if not md_text:
        return {"literature": {}, "notes": {}, "matrix": {}}

    result = {
        "literature": {},
        "notes": {},
        "matrix": {},
    }

    lines = md_text.split("\n")
    current_target: Optional[Tuple[str, str]] = None     # (kind, id)

    for line in lines:
        # 检测当前块的 target
        m_lit = _REVIEW_LIT_RE.search(line)
        if m_lit:
            current_target = ("literature", m_lit.group(1))
            continue
        m_note = _REVIEW_NOTE_RE.search(line)
        if m_note:
            current_target = ("notes", m_note.group(1))
            continue
        m_matrix = _REVIEW_MATRIX_RE.search(line)
        if m_matrix:
            current_target = ("matrix", f"{m_matrix.group(1)}:{m_matrix.group(2)}")
            continue

        # 检测 COMMENT
        for m_comment in _COMMENT_RE.finditer(line):
            comment_text = m_comment.group(1).strip()
            if not comment_text or current_target is None:
                continue
            kind, target_id = current_target
            bucket = result.get(kind, {})
            bucket.setdefault(target_id, []).append({
                "text": comment_text,
                "imported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    return result


def apply_review_comments_to_state(
    lr_state: Dict[str, Any],
    parsed_comments: Dict[str, Dict[str, List[Dict[str, str]]]],
) -> Dict[str, int]:
    """把解析后的批注写入 lr_state 中相应的 literature_items / notes。

    Returns: {"literature": N, "notes": N, "matrix": N}
    """
    counts = {"literature": 0, "notes": 0, "matrix": 0}

    # literature
    for it in (lr_state.get("literature_items") or []):
        if not isinstance(it, dict):
            continue
        comments = parsed_comments.get("literature", {}).get(it.get("key"))
        if comments:
            existing = it.get("review_comments") or []
            existing.extend(comments)
            it["review_comments"] = existing
            counts["literature"] += len(comments)

    # notes
    for n in (lr_state.get("notes") or []):
        if not isinstance(n, dict):
            continue
        comments = parsed_comments.get("notes", {}).get(n.get("note_id"))
        if comments:
            existing = n.get("review_comments") or []
            existing.extend(comments)
            n["review_comments"] = existing
            counts["notes"] += len(comments)

    # matrix
    matrix = lr_state.get("matrix") or {}
    matrix_comments = matrix.get("review_comments") or {}
    for cell_key, comments in parsed_comments.get("matrix", {}).items():
        existing = matrix_comments.get(cell_key) or []
        existing.extend(comments)
        matrix_comments[cell_key] = existing
        counts["matrix"] += len(comments)
    matrix["review_comments"] = matrix_comments
    lr_state["matrix"] = matrix

    return counts
