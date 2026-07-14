"""文献逐篇结构化摘要（v4.7 丢文献写综述流水线 - 第 2 步）。

对每篇 IngestedDoc 调 LLM 网关生成结构化摘要（研究问题/理论框架/方法/样本/主要发现/局限，
给定研究主题时追加"与主题相关性"）。

设计原则：
- 超长正文头尾保留、中间省略（方法与结论通常在两端）
- LLM 不可用 / 单篇失败 → ok=False + 用原文摘要兜底，绝不抛异常中断批量
- 全程走 src.llm_gateway.gateway.llm_chat，不直连 API
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.literature_review.ingest import IngestedDoc
from src.llm_gateway.gateway import llm_chat

# 结构化摘要的固定维度（用于 UI 展示顺序与综述压缩）
BASE_DIMENSIONS = ["研究问题", "理论框架", "方法", "样本", "主要发现", "局限"]
RELEVANCE_DIMENSION = "与主题相关性"


@dataclass
class PaperSummary:
    """单篇结构化摘要。"""
    literature_key: str
    title: str
    structured: Dict[str, str] = field(default_factory=dict)
    raw_text: str = ""   # LLM 原始输出兜底
    ok: bool = False
    error: str = ""


def _build_user_prompt(topic: str) -> str:
    """根据是否有研究主题动态生成维度提示（避免硬编码维度个数）。"""
    dims = list(BASE_DIMENSIONS)
    if topic:
        dims.append(RELEVANCE_DIMENSION)
    dims_str = "、".join(dims)
    extra = ""
    if topic:
        extra = f"\n本次研究主题是「{topic}」，请在「{RELEVANCE_DIMENSION}」维度评估该文献与此主题的相关程度与可借鉴之处。"
    return (
        f"请分析下面这篇文献，输出以下维度（每个维度一行，用全角冒号「：」分隔维度名与内容）：{dims_str}。"
        f"{extra}\n若某维度文献中确实没有提及，写「未提及」。\n\n文献正文：\n"
    )


def _truncate(text: str, max_chars: int) -> str:
    """超长正文头尾保留、中间省略。"""
    if len(text) <= max_chars:
        return text
    head_len = int(max_chars * 0.6)
    tail_len = max_chars - head_len
    return text[:head_len] + "\n...[中间内容已省略]...\n" + text[-tail_len:]


def summarize_paper(
    doc: IngestedDoc,
    *,
    topic: str = "",
    model: Optional[str] = None,
    max_chars: int = 12000,
) -> PaperSummary:
    """对单篇文献调 LLM 生成结构化摘要；任何失败都返回兜底结果，不抛异常。"""
    text_for_llm = _truncate(doc.full_text, max_chars)
    system_msg = (
        "你是严谨的心理学文献分析助手。请只依据给定文献内容，按要求的维度逐行输出，"
        "格式为「维度名：内容」（全角冒号），不要输出额外说明。"
    )
    user_msg = _build_user_prompt(topic) + text_for_llm

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
        raw_text = response.content or ""
        structured: Dict[str, str] = {}
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or "：" not in line:
                continue
            key, val = line.split("：", 1)
            key, val = key.strip(), val.strip()
            if key:
                structured[key] = val
        return PaperSummary(
            literature_key=doc.item.key,
            title=doc.item.title,
            structured=structured,
            raw_text=raw_text,
            ok=bool(structured),
            error="" if structured else "LLM 返回内容无法解析为维度",
        )
    except Exception as e:  # noqa: BLE001 - 单篇兜底
        abstract = (doc.item.abstract or "").strip()
        fallback = f"LLM不可用，以下为原文摘要：{abstract}" if abstract else "LLM不可用，且未能从原文抽取到摘要"
        return PaperSummary(
            literature_key=doc.item.key,
            title=doc.item.title,
            structured={"摘要兜底": fallback},
            raw_text="",
            ok=False,
            error=str(e),
        )


def summarize_papers(
    docs: List[IngestedDoc],
    *,
    topic: str = "",
    model: Optional[str] = None,
) -> List[PaperSummary]:
    """批量摘要；解析失败的文件给占位摘要并跳过 LLM 调用。"""
    results: List[PaperSummary] = []
    for doc in docs:
        if not doc.extraction_ok:
            warn = "；".join(doc.warnings) if doc.warnings else "文件解析失败"
            results.append(PaperSummary(
                literature_key=doc.item.key,
                title=doc.item.title or doc.source_filename,
                structured={},
                raw_text="",
                ok=False,
                error=f"文件解析失败，跳过LLM摘要（{warn}）",
            ))
        else:
            results.append(summarize_paper(doc, topic=topic, model=model))
    return results
