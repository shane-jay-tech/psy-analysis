"""文献综述数据模型（v3.4）。

设计原则：
- 与现有 literature_crawler.CrawledReference 兼容（from_crawled 转换器）
- 全部支持 to_dict/from_dict（workspace 序列化）
- 字段中文注释；面向用户的字段名使用英文方便程序处理
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# 文献条目
# ---------------------------------------------------------------------------

# 阅读状态枚举
READING_STATUS_UNREAD = "unread"
READING_STATUS_READING = "reading"
READING_STATUS_DONE = "done"
READING_STATUSES = {READING_STATUS_UNREAD, READING_STATUS_READING, READING_STATUS_DONE}


@dataclass
class LiteratureItem:
    """文献综述工作台中的文献条目。

    与 literature_crawler.CrawledReference 兼容：构造时可从 CrawledReference 复制核心字段，
    再扩展 reading_status / notes / relevance_score / tags。
    """
    key: str = field(default_factory=_new_id)
    title: str = ""
    authors: List[str] = field(default_factory=list)
    year: int = 0
    journal: str = ""
    doi: str = ""
    abstract: str = ""
    citation_count: int = 0
    source: str = ""             # crossref | semantic_scholar | manual
    url: str = ""
    # v3.4 扩展字段
    reading_status: str = READING_STATUS_UNREAD
    notes: str = ""              # 简短备注（不同于 ReadingNote 的结构化笔记）
    relevance_score: float = 0.0  # 0-1，由 search 模块自动计算
    tags: List[str] = field(default_factory=list)
    added_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LiteratureItem":
        return cls(
            key=data.get("key") or _new_id(),
            title=data.get("title", ""),
            authors=list(data.get("authors") or []),
            year=int(data.get("year") or 0),
            journal=data.get("journal", ""),
            doi=data.get("doi", ""),
            abstract=data.get("abstract", ""),
            citation_count=int(data.get("citation_count") or 0),
            source=data.get("source", ""),
            url=data.get("url", ""),
            reading_status=data.get("reading_status", READING_STATUS_UNREAD),
            notes=data.get("notes", ""),
            relevance_score=float(data.get("relevance_score") or 0.0),
            tags=list(data.get("tags") or []),
            added_at=data.get("added_at") or _now_iso(),
        )

    @classmethod
    def from_crawled(cls, crawled: Any) -> "LiteratureItem":
        """从 literature_crawler.CrawledReference 转换。"""
        return cls(
            title=getattr(crawled, "title", ""),
            authors=list(getattr(crawled, "authors", []) or []),
            year=int(getattr(crawled, "year", 0) or 0),
            journal=getattr(crawled, "journal", ""),
            doi=getattr(crawled, "doi", ""),
            abstract=getattr(crawled, "abstract", ""),
            citation_count=int(getattr(crawled, "citation_count", 0) or 0),
            source=getattr(crawled, "source", ""),
            url=getattr(crawled, "url", ""),
        )

    @property
    def reading_status_emoji(self) -> str:
        return {
            READING_STATUS_UNREAD: "📖",
            READING_STATUS_READING: "📗",
            READING_STATUS_DONE: "📘",
        }.get(self.reading_status, "📖")

    @property
    def short_citation(self) -> str:
        """简短引用文本（一行显示用）。"""
        first_author = (self.authors[0] if self.authors else "Unknown")
        return f"{first_author} ({self.year}) — {self.title[:60]}"


# ---------------------------------------------------------------------------
# 阅读笔记
# ---------------------------------------------------------------------------

# 笔记类型枚举
NOTE_TYPES = ["方法", "结果", "理论", "批判", "疑问", "其他"]


@dataclass
class ReadingNote:
    note_id: str = field(default_factory=_new_id)
    literature_key: str = ""             # 关联到 LiteratureItem.key
    content: str = ""
    page_or_section: str = ""
    type: str = "其他"                    # 见 NOTE_TYPES
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReadingNote":
        return cls(
            note_id=data.get("note_id") or _new_id(),
            literature_key=data.get("literature_key", ""),
            content=data.get("content", ""),
            page_or_section=data.get("page_or_section", ""),
            type=data.get("type", "其他"),
            created_at=data.get("created_at") or _now_iso(),
            updated_at=data.get("updated_at") or _now_iso(),
        )

    def update_content(self, new_content: str) -> None:
        self.content = new_content
        self.updated_at = _now_iso()


# ---------------------------------------------------------------------------
# 主题聚类
# ---------------------------------------------------------------------------

@dataclass
class ThemeCluster:
    theme_name: str = ""
    literature_keys: List[str] = field(default_factory=list)
    centroid_keywords: List[str] = field(default_factory=list)
    summary: str = ""
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThemeCluster":
        return cls(
            theme_name=data.get("theme_name", ""),
            literature_keys=list(data.get("literature_keys") or []),
            centroid_keywords=list(data.get("centroid_keywords") or []),
            summary=data.get("summary", ""),
            created_at=data.get("created_at") or _now_iso(),
        )


# ---------------------------------------------------------------------------
# Gap 分析
# ---------------------------------------------------------------------------

@dataclass
class GapAnalysis:
    gap_id: str = field(default_factory=_new_id)
    gap_description: str = ""
    supporting_notes: List[str] = field(default_factory=list)   # ReadingNote 内容片段
    suggested_direction: str = ""
    confidence: float = 0.0      # 0-1
    source: str = "heuristic"     # heuristic | llm
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GapAnalysis":
        return cls(
            gap_id=data.get("gap_id") or _new_id(),
            gap_description=data.get("gap_description", ""),
            supporting_notes=list(data.get("supporting_notes") or []),
            suggested_direction=data.get("suggested_direction", ""),
            confidence=float(data.get("confidence") or 0.0),
            source=data.get("source", "heuristic"),
            created_at=data.get("created_at") or _now_iso(),
        )


# ---------------------------------------------------------------------------
# 文献矩阵
# ---------------------------------------------------------------------------

@dataclass
class LiteratureMatrix:
    """rows × columns 的二维矩阵：rows 是 LiteratureItem.key，columns 是用户自定义维度。"""
    dimensions: List[str] = field(default_factory=list)         # 列名
    cells: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # cells[literature_key][dimension] = "文本内容"
    highlighted_keys: List[str] = field(default_factory=list)   # 高亮的行

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimensions": list(self.dimensions),
            "cells": {k: dict(v) for k, v in self.cells.items()},
            "highlighted_keys": list(self.highlighted_keys),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LiteratureMatrix":
        return cls(
            dimensions=list(data.get("dimensions") or []),
            cells={k: dict(v) for k, v in (data.get("cells") or {}).items()},
            highlighted_keys=list(data.get("highlighted_keys") or []),
        )

    def set_cell(self, literature_key: str, dimension: str, value: str) -> None:
        if literature_key not in self.cells:
            self.cells[literature_key] = {}
        self.cells[literature_key][dimension] = value

    def get_cell(self, literature_key: str, dimension: str) -> str:
        return self.cells.get(literature_key, {}).get(dimension, "")

    def add_dimension(self, name: str) -> None:
        if name and name not in self.dimensions:
            self.dimensions.append(name)

    def remove_dimension(self, name: str) -> None:
        if name in self.dimensions:
            self.dimensions.remove(name)
        for row in self.cells.values():
            row.pop(name, None)

    def empty_cells_count(self, literature_keys: Optional[List[str]] = None) -> int:
        """统计空单元格数量（用于 gap 启发式分析）。"""
        keys = literature_keys if literature_keys is not None else list(self.cells.keys())
        empty = 0
        for k in keys:
            for d in self.dimensions:
                if not self.get_cell(k, d).strip():
                    empty += 1
        return empty
