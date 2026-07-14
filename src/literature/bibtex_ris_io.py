"""BibTeX 和 RIS 格式导入导出。

第一版支持 BibTeX 的基本导入/导出，以及 RIS 导入。
不依赖外部库，使用正则解析。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BibEntry:
    """标准化的文献条目。"""
    entry_type: str = "article"
    citation_key: str = ""
    title: str = ""
    author: str = ""
    year: str = ""
    journal: str = ""
    volume: str = ""
    number: str = ""
    pages: str = ""
    doi: str = ""
    abstract: str = ""
    keywords: str = ""
    extra: dict = field(default_factory=dict)

    def to_bibtex(self) -> str:
        lines = [f"@{self.entry_type}{{{self.citation_key},"]
        fields = [
            ("title", self.title),
            ("author", self.author),
            ("year", self.year),
            ("journal", self.journal),
            ("volume", self.volume),
            ("number", self.number),
            ("pages", self.pages),
            ("doi", self.doi),
            ("abstract", self.abstract),
            ("keywords", self.keywords),
        ]
        for key, val in fields:
            if val:
                lines.append(f"  {key} = {{{val}}},")
        for key, val in self.extra.items():
            if val:
                lines.append(f"  {key} = {{{val}}},")
        lines.append("}")
        return "\n".join(lines)


def parse_bibtex(text: str) -> list[BibEntry]:
    """解析 BibTeX 字符串，返回条目列表。"""
    entries = []
    pattern = r"@(\w+)\s*\{([^,]*),(.*?)\n\}"
    matches = re.finditer(pattern, text, re.DOTALL)

    for m in matches:
        entry_type = m.group(1).lower()
        citation_key = m.group(2).strip()
        body = m.group(3)

        entry = BibEntry(entry_type=entry_type, citation_key=citation_key)
        field_pattern = r"(\w+)\s*=\s*\{(.*?)\}"
        for fm in re.finditer(field_pattern, body, re.DOTALL):
            key = fm.group(1).lower()
            val = fm.group(2).strip()
            if key == "title":
                entry.title = val
            elif key == "author":
                entry.author = val
            elif key == "year":
                entry.year = val
            elif key == "journal":
                entry.journal = val
            elif key == "volume":
                entry.volume = val
            elif key == "number":
                entry.number = val
            elif key == "pages":
                entry.pages = val
            elif key == "doi":
                entry.doi = val
            elif key == "abstract":
                entry.abstract = val
            elif key == "keywords":
                entry.keywords = val
            else:
                entry.extra[key] = val
        entries.append(entry)
    return entries


def parse_ris(text: str) -> list[BibEntry]:
    """解析 RIS 格式字符串。"""
    entries = []
    current: Optional[BibEntry] = None
    authors = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if len(line) < 5 or line[2:4] != "  " or line[4] != "-":
            continue

        tag = line[:2].strip()
        value = line[6:].strip() if len(line) > 6 else ""

        if tag == "TY":
            current = BibEntry()
            authors = []
            type_map = {"JOUR": "article", "BOOK": "book", "CONF": "inproceedings", "THES": "phdthesis"}
            current.entry_type = type_map.get(value, "misc")
        elif tag == "ER":
            if current:
                if authors:
                    current.author = " and ".join(authors)
                entries.append(current)
            current = None
            authors = []
        elif current:
            if tag == "TI" or tag == "T1":
                current.title = value
            elif tag == "AU" or tag == "A1":
                authors.append(value)
            elif tag == "PY" or tag == "Y1":
                current.year = value[:4] if len(value) >= 4 else value
            elif tag == "JO" or tag == "JF" or tag == "T2":
                current.journal = value
            elif tag == "VL":
                current.volume = value
            elif tag == "IS":
                current.number = value
            elif tag == "SP":
                current.pages = value
            elif tag == "EP":
                if current.pages:
                    current.pages = f"{current.pages}-{value}"
                else:
                    current.pages = value
            elif tag == "DO":
                current.doi = value
            elif tag == "AB":
                current.abstract = value
            elif tag == "KW":
                if current.keywords:
                    current.keywords += f", {value}"
                else:
                    current.keywords = value
            elif tag == "ID":
                current.citation_key = value

    if current:
        if authors:
            current.author = " and ".join(authors)
        entries.append(current)
    return entries


def entries_to_bibtex(entries: list[BibEntry]) -> str:
    """导出为 BibTeX 格式文本。"""
    return "\n\n".join(e.to_bibtex() for e in entries)


def entries_to_ris(entries: list[BibEntry]) -> str:
    """导出为 RIS 格式文本。"""
    lines = []
    type_map = {"article": "JOUR", "book": "BOOK", "inproceedings": "CONF", "phdthesis": "THES"}

    for e in entries:
        lines.append(f"TY  - {type_map.get(e.entry_type, 'GEN')}")
        if e.citation_key:
            lines.append(f"ID  - {e.citation_key}")
        if e.title:
            lines.append(f"TI  - {e.title}")
        if e.author:
            for author in e.author.split(" and "):
                lines.append(f"AU  - {author.strip()}")
        if e.year:
            lines.append(f"PY  - {e.year}")
        if e.journal:
            lines.append(f"JO  - {e.journal}")
        if e.volume:
            lines.append(f"VL  - {e.volume}")
        if e.number:
            lines.append(f"IS  - {e.number}")
        if e.pages:
            parts = e.pages.split("-")
            lines.append(f"SP  - {parts[0]}")
            if len(parts) > 1:
                lines.append(f"EP  - {parts[1]}")
        if e.doi:
            lines.append(f"DO  - {e.doi}")
        if e.abstract:
            lines.append(f"AB  - {e.abstract}")
        if e.keywords:
            for kw in e.keywords.split(","):
                lines.append(f"KW  - {kw.strip()}")
        lines.append("ER  - ")
        lines.append("")
    return "\n".join(lines)
