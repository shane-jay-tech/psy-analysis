"""文献文件解析（v4.7 丢文献写综述流水线 - 第 1 步）。

把用户上传的 PDF / docx / txt 文件解析为 IngestedDoc：
- 抽取正文 full_text（完整，不在此截断）
- 启发式抽取 title / abstract / year（尽力而为，真正的理解交给后续 summarize 的 LLM）
- 构建 LiteratureItem（复用现有模型，key 用 uuid 保证唯一）

设计原则：
- 单篇解析失败不抛异常向上冒泡（批量入口 ingest_files 捕获），保证一篇坏文件不毁整批
- 扫描版/无文本层 PDF → extraction_ok=False + 明确 warning，提示用户手动粘贴
"""

from __future__ import annotations

import io
import os
import re
import uuid
from dataclasses import dataclass
from typing import List, Tuple

import pypdf
from docx import Document as DocxDocument

from src.literature_review.models import LiteratureItem


@dataclass
class IngestedDoc:
    """单篇文献解析结果。"""
    item: LiteratureItem
    full_text: str
    extraction_ok: bool
    warnings: List[str]
    source_filename: str


# 正文判定为"几乎没有文本"的阈值（低于此判为扫描版）
_MIN_TEXT_LEN = 50


def _extract_text_pdf(data: bytes) -> Tuple[str, List[str], bool]:
    """从 PDF 字节流提取文本，返回 (full_text, warnings, extraction_ok)。"""
    warnings: List[str] = []
    reader = pypdf.PdfReader(io.BytesIO(data))
    pages_text: List[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        pages_text.append(page_text)
    full_text = "\n".join(pages_text)
    extraction_ok = True
    if len(full_text.strip()) < _MIN_TEXT_LEN:
        warnings.append("可能是扫描版PDF，没有文本层，建议手动粘贴摘要")
        extraction_ok = False
    return full_text, warnings, extraction_ok


def _heuristic_title(full_text: str) -> str:
    """启发式标题：前 5 个非空行里，挑长度适中（>=8 且最短）的一行；都很短则取最短。"""
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    if not lines:
        return ""
    first5 = lines[:5]
    # 优先选长度 >=8 的较短行（避免选到页码/单字这种过短行）
    candidates = [ln for ln in first5 if len(ln) >= 8]
    pool = candidates or first5
    return min(pool, key=len)


def _heuristic_abstract(full_text: str) -> str:
    """启发式摘要：抓 'abstract'/'摘要' 关键词之后到下一个空行之间的段落。"""
    lines = full_text.splitlines()
    capture = False
    abstract_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not capture:
            if re.search(r"(abstract|摘要)", stripped, re.I):
                capture = True
            continue
        if not stripped:
            break
        abstract_lines.append(stripped)
    return "\n".join(abstract_lines).strip()


def _heuristic_year(full_text: str) -> int:
    """启发式年份：第一个 19xx / 20xx。"""
    match = re.search(r"\b(19|20)\d{2}\b", full_text)
    return int(match.group()) if match else 0


def ingest_file(filename: str, data: bytes) -> IngestedDoc:
    """解析单个文件，返回 IngestedDoc。支持 .pdf / .docx / .txt。"""
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""
    warnings: List[str] = []
    extraction_ok = True

    if ext == ".pdf":
        full_text, warnings, extraction_ok = _extract_text_pdf(data)
    elif ext == ".docx":
        doc = DocxDocument(io.BytesIO(data))
        full_text = "\n".join(p.text for p in doc.paragraphs)
    elif ext == ".txt":
        try:
            full_text = data.decode("utf-8")
        except UnicodeDecodeError:
            full_text = data.decode("gbk", errors="replace")
    else:
        extraction_ok = False
        warnings.append(f"不支持的文件格式: {ext}（仅支持 .pdf / .docx / .txt）")

    item = LiteratureItem(
        key=str(uuid.uuid4()),
        title=_heuristic_title(full_text),
        abstract=_heuristic_abstract(full_text),
        year=_heuristic_year(full_text),
        authors=[],
        source="upload",
    )
    return IngestedDoc(
        item=item,
        full_text=full_text,
        extraction_ok=extraction_ok,
        warnings=warnings,
        source_filename=filename,
    )


def ingest_files(files: List[Tuple[str, bytes]]) -> List[IngestedDoc]:
    """批量解析；单文件异常不影响其它文件。"""
    results: List[IngestedDoc] = []
    for filename, data in files:
        try:
            results.append(ingest_file(filename, data))
        except Exception as e:  # noqa: BLE001 - 单篇兜底，绝不让整批崩
            results.append(IngestedDoc(
                item=LiteratureItem(key=str(uuid.uuid4()), source="upload"),
                full_text="",
                extraction_ok=False,
                warnings=[f"文件处理失败: {e}"],
                source_filename=filename,
            ))
    return results
