"""PaperDraftBundle — 论文交付统一对象。

所有论文输出（模板版/AI版/润色版/混合版）统一为同一结构，
Word 导出和 UI 都只接收 bundle，不再直接读 session_state。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class PaperSection:
    """论文单个章节。"""
    name: str
    markdown: str
    source: str  # template / ai / polished / manual
    generated_at: str = ""
    confidence_note: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")


@dataclass
class PaperDraftBundle:
    """论文草稿包 — 统一交付对象。"""
    title: str
    sections: dict[str, PaperSection] = field(default_factory=dict)
    source: str = "template"  # template / ai / polished / manual / mixed
    provenance: dict[str, str] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    figures: list[Any] = field(default_factory=list)
    descriptive_table: Any | None = None
    defense_qa_md: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def method_md(self) -> str:
        sec = self.sections.get("method")
        return sec.markdown if sec else ""

    @property
    def result_md(self) -> str:
        sec = self.sections.get("result")
        return sec.markdown if sec else ""

    @property
    def discussion_md(self) -> str:
        sec = self.sections.get("discussion")
        return sec.markdown if sec else ""

    @property
    def introduction_md(self) -> str:
        sec = self.sections.get("introduction")
        return sec.markdown if sec else ""

    def all_markdown(self) -> str:
        """按顺序拼接所有章节 markdown。"""
        order = ["introduction", "method", "result", "discussion"]
        parts = []
        for key in order:
            if key in self.sections:
                parts.append(self.sections[key].markdown)
        for key, sec in self.sections.items():
            if key not in order:
                parts.append(sec.markdown)
        return "\n\n".join(parts)

    def section_sources(self) -> dict[str, str]:
        """返回各章节的来源信息。"""
        return {k: v.source for k, v in self.sections.items()}
