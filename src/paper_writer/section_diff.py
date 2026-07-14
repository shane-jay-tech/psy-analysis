"""论文章节差异对比工具 — 基于 difflib 的段落级 diff。

用于 AI 增强后让用户逐段选择原文或 AI 版，
生成混合版 PaperDraftBundle。
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParagraphDiff:
    """单个段落的差异。"""
    index: int
    original: str
    revised: str
    change_type: str  # unchanged / modified / added / removed
    selected: str = "original"  # original / revised

    @property
    def is_changed(self) -> bool:
        return self.change_type != "unchanged"


@dataclass
class SectionDiff:
    """一个章节的完整 diff 结果。"""
    section_name: str
    paragraphs: list[ParagraphDiff] = field(default_factory=list)

    @property
    def change_count(self) -> int:
        return sum(1 for p in self.paragraphs if p.is_changed)

    @property
    def total_paragraphs(self) -> int:
        return len(self.paragraphs)

    def get_selected_text(self) -> str:
        """根据当前选择状态生成最终文本。"""
        parts = []
        for p in self.paragraphs:
            if p.selected == "revised" and p.revised:
                parts.append(p.revised)
            elif p.selected == "original" and p.original:
                parts.append(p.original)
            elif p.original:
                parts.append(p.original)
            elif p.revised:
                parts.append(p.revised)
        return "\n\n".join(parts)

    def select_all_original(self):
        for p in self.paragraphs:
            p.selected = "original"

    def select_all_revised(self):
        for p in self.paragraphs:
            p.selected = "revised"

    def select_paragraph(self, index: int, choice: str):
        if 0 <= index < len(self.paragraphs):
            self.paragraphs[index].selected = choice


def compute_section_diff(
    original: str,
    revised: str,
    section_name: str = "",
) -> SectionDiff:
    """计算两个版本之间的段落级差异。"""
    orig_paras = _split_paragraphs(original)
    rev_paras = _split_paragraphs(revised)

    matcher = difflib.SequenceMatcher(None, orig_paras, rev_paras)
    paragraphs = []
    idx = 0

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for k in range(i1, i2):
                paragraphs.append(ParagraphDiff(
                    index=idx,
                    original=orig_paras[k],
                    revised=rev_paras[j1 + (k - i1)],
                    change_type="unchanged",
                    selected="original",
                ))
                idx += 1
        elif op == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                orig = orig_paras[i1 + k] if (i1 + k) < i2 else ""
                rev = rev_paras[j1 + k] if (j1 + k) < j2 else ""
                paragraphs.append(ParagraphDiff(
                    index=idx,
                    original=orig,
                    revised=rev,
                    change_type="modified",
                    selected="original",
                ))
                idx += 1
        elif op == "insert":
            for k in range(j1, j2):
                paragraphs.append(ParagraphDiff(
                    index=idx,
                    original="",
                    revised=rev_paras[k],
                    change_type="added",
                    selected="revised",
                ))
                idx += 1
        elif op == "delete":
            for k in range(i1, i2):
                paragraphs.append(ParagraphDiff(
                    index=idx,
                    original=orig_paras[k],
                    revised="",
                    change_type="removed",
                    selected="original",
                ))
                idx += 1

    return SectionDiff(section_name=section_name, paragraphs=paragraphs)


def _split_paragraphs(text: str) -> list[str]:
    """按空行分割段落。"""
    if not text:
        return []
    paras = []
    current = []
    for line in text.split("\n"):
        if line.strip() == "":
            if current:
                paras.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paras.append("\n".join(current))
    return paras
