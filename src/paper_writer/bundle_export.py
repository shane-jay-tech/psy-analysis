"""PaperDraftBundle 导出桥接 — 连接 bundle 到 Word/Markdown/交付包输出。

统一导出入口：所有论文导出（Word/Markdown/打包）都从 bundle 出发，
不再从 session_state 散落字段拼装。
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .draft_bundle import PaperDraftBundle, PaperSection

logger = logging.getLogger(__name__)

SECTION_ORDER = ["introduction", "method", "result", "discussion"]
SECTION_TITLES_ZH = {
    "introduction": "引言",
    "method": "方法",
    "result": "结果",
    "discussion": "讨论",
}


@dataclass
class ExportMeta:
    """导出元信息。"""
    title: str
    author: str = ""
    affiliation: str = ""
    date: str = ""
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    bundle_source: str = ""
    exported_at: str = ""

    def __post_init__(self):
        if not self.exported_at:
            self.exported_at = datetime.now().strftime("%Y-%m-%d %H:%M")


@dataclass
class ExportResult:
    """导出结果。"""
    format: str  # markdown / docx / package
    content: bytes | str
    filename: str
    meta: ExportMeta
    warnings: list[str] = field(default_factory=list)


def bundle_to_markdown(
    bundle: PaperDraftBundle,
    *,
    include_source_tags: bool = True,
    include_provenance: bool = False,
) -> str:
    """将 bundle 转换为 Markdown 格式论文。"""
    parts = []

    parts.append(f"# {bundle.title}\n")

    for key in SECTION_ORDER:
        sec = bundle.sections.get(key)
        if sec:
            title_zh = SECTION_TITLES_ZH.get(key, key)
            parts.append(f"## {title_zh}\n")
            parts.append(sec.markdown)
            if include_source_tags:
                parts.append(f"\n<!-- source: {sec.source} -->")

    for key, sec in bundle.sections.items():
        if key not in SECTION_ORDER:
            parts.append(f"## {key}\n")
            parts.append(sec.markdown)
            if include_source_tags:
                parts.append(f"\n<!-- source: {sec.source} -->")

    if include_provenance and bundle.provenance:
        parts.append("\n---\n## 来源追溯\n")
        for k, v in bundle.provenance.items():
            parts.append(f"- **{k}**: {v}")

    if bundle.warnings:
        parts.append("\n---\n## 警告\n")
        for w in bundle.warnings:
            parts.append(f"- {w}")

    return "\n\n".join(parts)


def bundle_to_docx_args(
    bundle: PaperDraftBundle,
    meta: ExportMeta | None = None,
) -> dict[str, Any]:
    """将 bundle 转换为 docx_exporter 所需的参数字典。

    返回的字典可直接传给 src.output.docx_exporter 的导出函数。
    """
    if meta is None:
        meta = ExportMeta(title=bundle.title, bundle_source=bundle.source)

    sections_md: dict[str, str] = {}
    for key in SECTION_ORDER:
        sec = bundle.sections.get(key)
        if sec:
            sections_md[key] = sec.markdown

    for key, sec in bundle.sections.items():
        if key not in SECTION_ORDER:
            sections_md[key] = sec.markdown

    return {
        "title": meta.title,
        "author": meta.author,
        "affiliation": meta.affiliation,
        "date": meta.date,
        "abstract": meta.abstract,
        "keywords": meta.keywords,
        "sections": sections_md,
        "figures": bundle.figures,
        "descriptive_table": bundle.descriptive_table,
    }


def bundle_to_export_result(
    bundle: PaperDraftBundle,
    format: str = "markdown",
    meta: ExportMeta | None = None,
) -> ExportResult:
    """统一导出入口。"""
    if meta is None:
        meta = ExportMeta(title=bundle.title, bundle_source=bundle.source)

    warnings = list(bundle.warnings)

    if format == "markdown":
        content = bundle_to_markdown(bundle, include_source_tags=True)
        filename = f"{bundle.title}_论文.md"
        return ExportResult(
            format="markdown",
            content=content,
            filename=filename,
            meta=meta,
            warnings=warnings,
        )

    if format == "docx":
        args = bundle_to_docx_args(bundle, meta)
        filename = f"{bundle.title}_论文.docx"
        return ExportResult(
            format="docx",
            content=b"",  # actual bytes filled by docx_exporter
            filename=filename,
            meta=meta,
            warnings=warnings,
        )

    raise ValueError(f"Unsupported export format: {format}")


def validate_bundle_for_export(bundle: PaperDraftBundle) -> list[str]:
    """导出前校验 bundle，返回问题列表。"""
    issues = []
    if not bundle.title:
        issues.append("论文标题为空")
    if not bundle.sections:
        issues.append("论文无任何章节内容")
    for key in SECTION_ORDER:
        sec = bundle.sections.get(key)
        if sec and not sec.markdown.strip():
            title_zh = SECTION_TITLES_ZH.get(key, key)
            issues.append(f"{title_zh}章节内容为空")
    if bundle.warnings:
        issues.append(f"存在 {len(bundle.warnings)} 条警告，建议处理后再导出")
    return issues
