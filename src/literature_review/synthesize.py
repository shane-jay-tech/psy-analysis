"""综述合成（v4.7 丢文献写综述流水线 - 第 3 步）。

把 N 篇 PaperSummary 合成一篇连贯的中文文献综述正文：
- 由代码生成并固定「编号→文献」映射（citation_map），LLM 只能使用给定编号，保证文内引用与参考文献编号一致
- 参考文献列表由代码拼接（不靠 LLM），保证编号不串
- 主题给定时围绕主题组织
- 摘要总量过大时按字符预算截断并 warning

设计原则：LLM 失败 → ok=False + 兜底输出逐篇摘要清单，绝不抛异常。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.literature_review.summarize import PaperSummary
from src.llm_gateway.gateway import llm_chat

# 喂给 LLM 的压缩摘要字符预算（超出则截断保留前若干篇）
_MAX_COMPRESSED_CHARS = 24000


@dataclass
class ReviewResult:
    """综述合成结果。"""
    markdown: str
    title: str
    citation_map: List[Dict] = field(default_factory=list)
    ok: bool = False
    error: str = ""
    warnings: List[str] = field(default_factory=list)


def _compress_summaries(summaries: List[PaperSummary]) -> List[str]:
    """把每篇结构化摘要压成带固定编号的一行，供 LLM prompt 使用。"""
    compressed: List[str] = []
    for i, s in enumerate(summaries, start=1):
        title = s.title or "无标题"
        q = s.structured.get("研究问题", "未提供")
        f = s.structured.get("主要发现", "未提供")
        m = s.structured.get("方法", "未提供")
        compressed.append(f"[{i}] 题目:{title}；研究问题:{q}；方法:{m}；主要发现:{f}")
    return compressed


def _build_reference_list(citation_map: List[Dict]) -> str:
    """根据 citation_map 拼接参考文献节（条目间留空行，避免渲染时挤成一段）。"""
    lines = ["## 参考文献", ""]
    for entry in citation_map:
        lines.append(f"[{entry['index']}] {entry['citation']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _build_fallback_markdown(summaries: List[PaperSummary]) -> str:
    """LLM 不可用时：列出各篇结构化摘要清单。"""
    lines = ["## 无法生成综述正文，以下为各篇摘要清单", ""]
    for i, s in enumerate(summaries, start=1):
        lines.append(f"### [{i}] {s.title or '无标题'}")
        if s.structured:
            for k, v in s.structured.items():
                lines.append(f"- {k}：{v}")
        else:
            lines.append("- （无摘要内容）")
        lines.append("")
    return "\n".join(lines).rstrip()


def synthesize_review(
    summaries: List[PaperSummary],
    *,
    topic: str = "",
    model: Optional[str] = None,
) -> ReviewResult:
    """合成综述正文；任何失败都返回兜底结果，不抛异常。"""
    valid = [s for s in summaries if (s.ok or s.structured)]
    if not valid:
        return ReviewResult(
            markdown="",
            title="",
            citation_map=[],
            ok=False,
            error="无有效文献摘要，无法生成综述（可能全部解析失败或 LLM 不可用）",
            warnings=[],
        )

    warnings: List[str] = []
    compressed = _compress_summaries(valid)

    # 字符预算截断：保留尽量多的前若干篇
    if sum(len(e) for e in compressed) > _MAX_COMPRESSED_CHARS:
        kept, cum = [], 0
        for e in compressed:
            if cum + len(e) > _MAX_COMPRESSED_CHARS:
                break
            kept.append(e)
            cum += len(e)
        kept = kept or compressed[:1]  # 至少保留一篇
        n = len(kept)
        valid = valid[:n]
        compressed = kept
        warnings.append(f"文献过多，已压缩为前 {n} 篇参与综述合成（其余仅计入参考文献缺省略）")

    citation_map = [
        {"index": i, "key": s.literature_key, "citation": (s.title or "无标题")}
        for i, s in enumerate(valid, start=1)
    ]

    citations_block = "\n".join(compressed)
    parts = [
        "以下是若干篇文献的压缩摘要，每篇前的 [N] 是其固定引用编号：",
        citations_block,
        "",
        "请基于上述文献撰写一篇结构完整、行文连贯的中文文献综述，包含：",
        "1）标题；2）引言（研究背景与本综述范围）；"
        "3）按主题分节的主体（每节综合多篇文献，文内引用只能使用上面给定的 [N] 编号，"
        "不要自创编号，不要编造文献）；4）研究缺口与未来方向；5）小结。",
        "注意：不要在正文末尾自行罗列参考文献列表（参考文献由系统另行生成）。",
    ]
    if topic:
        parts.insert(0, f"本综述的研究主题是「{topic}」，请围绕该主题组织全文，并在引言中点明主题。")
    user_msg = "\n".join(parts)
    system_msg = "你是严谨的学术写作助手，擅长撰写结构完整、引用规范的心理学文献综述。"

    try:
        response = llm_chat(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            model=model,
            temperature=0.3,
            retries=1,
        )
        body = (response.content or "").strip()
        if not body:
            raise ValueError("LLM 返回空内容")
        refs = _build_reference_list(citation_map)
        full_md = f"{body}\n\n{refs}"
        title_str = f"《{topic}》文献综述" if topic else "文献综述"
        return ReviewResult(
            markdown=full_md,
            title=title_str,
            citation_map=citation_map,
            ok=True,
            error="",
            warnings=warnings,
        )
    except Exception as e:  # noqa: BLE001 - 兜底
        return ReviewResult(
            markdown=_build_fallback_markdown(valid),
            title=f"《{topic}》文献综述" if topic else "文献综述",
            citation_map=citation_map,
            ok=False,
            error=str(e),
            warnings=warnings,
        )
