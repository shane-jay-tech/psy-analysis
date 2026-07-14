"""Bundle 适配器 — 将各来源的论文内容转为 PaperDraftBundle。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from .draft_bundle import PaperDraftBundle, PaperSection


def bundle_from_wizard_template(
    method_text: str,
    result_text: str,
    *,
    title: str = "",
    ctx: dict | None = None,
    wiz_data: dict | None = None,
    discussion_text: str = "",
    introduction_text: str = "",
) -> PaperDraftBundle:
    """从向导模板文本创建 bundle。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sections = {}

    if introduction_text:
        sections["introduction"] = PaperSection(
            name="引言", markdown=introduction_text,
            source="template", generated_at=now,
        )
    if method_text:
        sections["method"] = PaperSection(
            name="方法", markdown=method_text,
            source="template", generated_at=now,
        )
    if result_text:
        sections["result"] = PaperSection(
            name="结果", markdown=result_text,
            source="template", generated_at=now,
        )
    if discussion_text:
        sections["discussion"] = PaperSection(
            name="讨论", markdown=discussion_text,
            source="template", generated_at=now,
        )

    meta = {}
    if ctx:
        meta["analysis_type"] = ctx.get("test_type", "")
    if wiz_data:
        meta["wizard_step"] = wiz_data.get("current_step", "")

    return PaperDraftBundle(
        title=title or "未命名论文",
        sections=sections,
        source="template",
        provenance={k: "template" for k in sections},
        meta=meta,
    )


def bundle_from_ai_result(
    method_md: str,
    result_md: str,
    *,
    title: str = "",
    model_name: str = "",
    discussion_md: str = "",
) -> PaperDraftBundle:
    """从 AI 增强生成结果创建 bundle。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sections = {}

    if method_md:
        sections["method"] = PaperSection(
            name="方法", markdown=method_md,
            source="ai", generated_at=now,
        )
    if result_md:
        sections["result"] = PaperSection(
            name="结果", markdown=result_md,
            source="ai", generated_at=now,
        )
    if discussion_md:
        sections["discussion"] = PaperSection(
            name="讨论", markdown=discussion_md,
            source="ai", generated_at=now,
        )

    return PaperDraftBundle(
        title=title or "AI 生成论文",
        sections=sections,
        source="ai",
        provenance={k: "ai" for k in sections},
        meta={"model": model_name} if model_name else {},
    )


def bundle_from_paper_engine(engine_result: dict, *, title: str = "") -> PaperDraftBundle:
    """从 PaperEngine 结果创建 bundle。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sections = {}

    section_map = {
        "method": "方法",
        "result": "结果",
        "discussion": "讨论",
        "introduction": "引言",
        "abstract": "摘要",
    }

    for key, label in section_map.items():
        content = engine_result.get(key, "") or engine_result.get(f"{key}_md", "")
        if content:
            sections[key] = PaperSection(
                name=label, markdown=content,
                source="paper_engine", generated_at=now,
            )

    return PaperDraftBundle(
        title=title or engine_result.get("title", "论文"),
        sections=sections,
        source="paper_engine",
        provenance={k: "paper_engine" for k in sections},
        meta=engine_result.get("meta", {}),
    )


def bundle_with_selected_sections(
    bundles: dict[str, PaperDraftBundle],
    selections: dict[str, str],
) -> PaperDraftBundle:
    """从多个 bundle 中按用户选择组合章节。

    Args:
        bundles: {"template": bundle1, "ai": bundle2, ...}
        selections: {"method": "ai", "result": "template", ...}
    """
    sections = {}
    provenance = {}

    for section_key, source_key in selections.items():
        bundle = bundles.get(source_key)
        if bundle and section_key in bundle.sections:
            sections[section_key] = bundle.sections[section_key]
            provenance[section_key] = source_key

    title = next(
        (b.title for b in bundles.values() if b.title and b.title != "未命名论文"),
        "混合版论文",
    )

    return PaperDraftBundle(
        title=title,
        sections=sections,
        source="mixed",
        provenance=provenance,
    )
