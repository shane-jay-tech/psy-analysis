# -*- coding: utf-8 -*-
r"""正文内引用替换器：[key] → (Author, Year)。

口径与 literature_manager.LiteratureEntry.format_reference 同源：
- 1/2 作者拼写全名（中文 2 作者用「与」连接），≥3 作者用 et al.（中文用「等」）——
  APA 7 正文内引用规则；>20 作者的省略号规则仅用于参考文献表，正文一律 First et al.
- 英文作者形如 "Smith, J. A." 时取逗号前姓氏段；无逗号则原样使用（确定性规则）。
- 未知 key 的方括号组保持原文，并收集进诊断结构；已知与未知混合的组整组不替换。
- 仅替换不被其他方括号包夹的组（(?<!\[)...(?!\])），嵌套方括号不误伤。
"""
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .literature_manager import LiteratureEntry

_BRACKET_RE = re.compile(r"(?<!\[)\[([^\[\]]+)\](?!\])")


@dataclass
class InTextCitationResult:
    text: str
    replaced_groups: int = 0
    unknown_keys: List[str] = field(default_factory=list)


def _surname(author: str) -> str:
    """英文 "Smith, J. A." → "Smith"；中文或无逗号原样。"""
    author = author.strip()
    if "," in author:
        return author.split(",")[0].strip()
    return author


def _format_authors_in_text(entry: LiteratureEntry) -> str:
    authors = [a for a in entry.authors if a and a.strip()]
    if not authors:
        return entry.key
    if len(authors) == 1:
        return _surname(authors[0])
    if len(authors) == 2:
        if entry.is_chinese:
            return f"{_surname(authors[0])}与{_surname(authors[1])}"
        return f"{_surname(authors[0])} & {_surname(authors[1])}"
    if entry.is_chinese:
        return f"{_surname(authors[0])}等"
    return f"{_surname(authors[0])} et al."


def _author_year(entry: LiteratureEntry) -> str:
    return f"{_format_authors_in_text(entry)}, {entry.year}"


def format_in_text_citation(entry: LiteratureEntry) -> str:
    """单条文献的正文内引用形态：(Author, Year)。"""
    return f"({_author_year(entry)})"


def _resolve(key: str, library: Any) -> Optional[LiteratureEntry]:
    if isinstance(library, dict):
        return library.get(key)
    get_entry = getattr(library, "get_entry", None)
    if callable(get_entry):
        return get_entry(key)
    entries = getattr(library, "entries", None)
    if isinstance(entries, dict):
        return entries.get(key)
    return None


def replace_inline_citations(text: str, library: Any) -> InTextCitationResult:
    """把正文中的 [key] / [key1; key2]（分号可全角）替换为
    (Author, Year) / (Author1, Year1; Author2, Year2)。

    分号分隔的多 key 保持原顺序；key 前后空白容错；未知 key 组原样保留。
    """
    result = InTextCitationResult(text=text)
    seen_unknown = set()

    def _sub(match: "re.Match") -> str:
        inner = match.group(1)
        keys = [seg.strip() for seg in re.split(r"[;；]", inner) if seg.strip()]
        if not keys:
            return match.group(0)
        entries = [_resolve(k, library) for k in keys]
        if any(e is None for e in entries):
            for k, e in zip(keys, entries):
                if e is None and k not in seen_unknown:
                    seen_unknown.add(k)
                    result.unknown_keys.append(k)
            return match.group(0)
        result.replaced_groups += 1
        return "(" + "; ".join(_author_year(e) for e in entries) + ")"

    result.text = _BRACKET_RE.sub(_sub, text)
    return result
