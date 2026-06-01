"""问卷题目文件解析（v4.1）。

把 .md / .docx / .txt 题目文件解析成 ItemsDoc，下游用于：
- AI 题目预审（src.questionnaire.ai_content_review）
- 正式问卷文档导出（Word / PDF）

设计要点：
- 抽题策略按优先级匹配：编号题 → bullet → 段落题，三类不混
- 标题取自首个 H1 / 首行；指导语取自标题与第一题之间的非空段落
- 反向题识别：末尾或题号附近含 (反向) / [R] / (R) 等标记
- 不联网、不调 LLM，纯 Python；数据加载器（loader.py）保持只做"被试数据"
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class ItemsDoc:
    """问卷题目解析结果。"""

    title: str = ""
    instructions: str = ""
    items: List[str] = field(default_factory=list)
    reverse_indices: List[int] = field(default_factory=list)
    source_format: str = ""
    raw_warnings: List[str] = field(default_factory=list)

    def n_items(self) -> int:
        return len(self.items)

    def n_reverse(self) -> int:
        return len(self.reverse_indices)


# ---------------------------------------------------------------------------
# 公共入口
# ---------------------------------------------------------------------------


_SUPPORTED_EXTS = (".md", ".markdown", ".docx", ".txt")


def parse_items_file(file_obj, file_name: str) -> ItemsDoc:
    """解析题目文件，返回 ItemsDoc。

    Args:
        file_obj: 路径字符串、bytes、BytesIO 或 Streamlit UploadedFile。
        file_name: 文件名（仅用于扩展名判断），大小写不敏感。

    Raises:
        ValueError: 不支持的扩展名 / 文件解码失败 / 未识别到任何题目。
    """
    name_lower = (file_name or "").lower().strip()
    if not name_lower.endswith(_SUPPORTED_EXTS):
        raise ValueError(
            f"不支持的题目文件格式：{file_name}\n"
            "支持 .md / .markdown / .docx / .txt 四种。"
        )

    if name_lower.endswith(".docx"):
        text, source_format = _extract_docx_text(file_obj), "docx"
    elif name_lower.endswith((".md", ".markdown")):
        text, source_format = _read_text(file_obj), "md"
        text = _strip_md_blocks(text)
    else:
        text, source_format = _read_text(file_obj), "txt"

    doc = _parse_text(text, source_format)
    if not doc.items:
        raise ValueError(
            "未能在文件中识别到任何题目。\n"
            "建议每行一道题，可以编号（1. ... / 1、 / (1)）、bullet（- / *）"
            "或纯文本逐行排列；并把标题放在文档首行。"
        )
    return doc


# ---------------------------------------------------------------------------
# 文件读取
# ---------------------------------------------------------------------------


def _read_text(file_obj) -> str:
    """通用文本读取：路径 / bytes / BytesIO / UploadedFile 都接。"""
    raw: Any
    if hasattr(file_obj, "read"):
        # 复位 cursor（streamlit 重复读时容易踩）
        try:
            file_obj.seek(0)
        except Exception:
            pass
        raw = file_obj.read()
    elif isinstance(file_obj, (bytes, bytearray)):
        raw = bytes(file_obj)
    elif isinstance(file_obj, str):
        with open(file_obj, "rb") as f:
            raw = f.read()
    else:
        raise ValueError(f"不支持的文件对象类型：{type(file_obj)!r}")

    if isinstance(raw, bytes):
        # 尝试常见编码：UTF-8 BOM / UTF-8 / GB18030（中文 .txt 常见）
        for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def _extract_docx_text(file_obj) -> str:
    """提取 .docx 的所有 paragraph 文本（不读 table）。"""
    try:
        from docx import Document
    except ImportError as exc:
        raise ValueError("缺少 python-docx 依赖，无法解析 Word 文件。") from exc

    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass
    if isinstance(file_obj, (bytes, bytearray)):
        file_obj = io.BytesIO(bytes(file_obj))

    doc = Document(file_obj)
    parts: List[str] = []
    for para in doc.paragraphs:
        text = (para.text or "").rstrip()
        if not text:
            parts.append("")  # 保留空行作为段落分隔
            continue
        # 用 Heading 样式的段落前面加 #，便于后续抽标题
        style_name = ""
        try:
            style_name = (para.style.name or "").lower()
        except Exception:
            pass
        if "heading 1" in style_name or style_name == "title":
            parts.append("# " + text)
        elif "heading 2" in style_name:
            parts.append("## " + text)
        else:
            parts.append(text)
    return "\n".join(parts)


def _strip_md_blocks(text: str) -> str:
    """去掉 Markdown 中的代码块和管道表格，避免它们混入题目。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out: List[str] = []
    in_code = False
    sep_re = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")
    pending: List[str] = []
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        # 表格识别：连续以 | 开头/含 | 的行 + 一个分隔行
        if "|" in line.strip() and line.strip().count("|") >= 1:
            pending.append(line)
            continue
        if pending:
            if any(sep_re.match(p) for p in pending):
                # 是表格，丢
                pending = []
            else:
                out.extend(pending)
                pending = []
        out.append(line)
    if pending:
        # 末尾未结束的 pending
        if not any(sep_re.match(p) for p in pending):
            out.extend(pending)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 抽题核心
# ---------------------------------------------------------------------------


# 编号题：1. / 1、 / 1) / 1） / (1) / （1） / 第1题
# 末尾必须吃到至少一个分隔符（句点/顿号/右括号/空格），避免误匹配 "20 个朋友"。
_NUMBERED_RE = re.compile(
    r"^\s*(?:第\s*)?[(（]?\s*(\d+)\s*"
    r"(?:[)）][.、)）\s]*|[.、][.、)）\s]*|\s+)"
)
# bullet：- / * / +（后必须跟空格）
_BULLET_RE = re.compile(r"^\s*[-*+]\s+")
# 标题：# / ## H1/H2
_HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.*?)\s*$")
# 反向题标记
_REVERSE_RE = re.compile(
    r"[（(\[]\s*(?:反向|反向题|reverse|R|r)\s*[)）\]]"
    r"|\s+\(R\)\s*$"
    r"|\s+\[R\]\s*$"
    r"|\s+反向\s*$"
)


def _is_item_line(line: str) -> Optional[Tuple[str, str]]:
    """判断一行是否是题目行，返回 (style, cleaned_text)，否则 None。

    style ∈ {"numbered", "bullet"}；纯段落题的判断在第二轮做。
    """
    if _HEADING_RE.match(line):
        return None
    m = _NUMBERED_RE.match(line)
    if m:
        rest = line[m.end():].strip()
        if rest:
            return ("numbered", rest)
    if _BULLET_RE.match(line):
        rest = _BULLET_RE.sub("", line, count=1).strip()
        if rest:
            return ("bullet", rest)
    return None


def _clean_item(text: str) -> str:
    """清洗题目文本：去尾标点空白、压缩内部空白。"""
    t = re.sub(r"\s+", " ", text).strip()
    return t


def _detect_reverse(item_text: str) -> Tuple[str, bool]:
    """检测题目是否为反向题；返回 (剥掉标记后的纯题干, is_reverse)。"""
    is_rev = bool(_REVERSE_RE.search(item_text))
    cleaned = _REVERSE_RE.sub("", item_text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned, is_rev


# ---------------------------------------------------------------------------
# 指导语启发式（v4.5）—— 段落兜底分支用
# ---------------------------------------------------------------------------

# 强信号前缀：行首匹配即认定为指导语
_INSTRUCTION_PREFIXES = (
    "指导语", "说明", "填写说明", "请阅读", "请根据", "请仔细", "请按",
    "请您", "请就", "请在", "请于", "请如实",
    "背景信息", "答题方式", "作答方式", "评分方式",
    "注意事项", "本问卷", "本调查", "本研究", "本量表",
    "为了", "欢迎", "感谢", "亲爱的", "尊敬的", "敬启者",
    "您将", "您好", "下面", "以下", "如下",
)

# 弱信号关键词：行内含且行长 ≥ 阈值时计入指导语
_INSTRUCTION_KEYWORDS = (
    "无对错", "保密", "匿名", "不涉及对错", "无标准答案",
    "您的回答", "您的答复", "您的真实", "如实作答", "如实填写",
    "回答均无对错", "结果仅用于", "用于学术研究", "答题须知",
    "保护您的隐私", "感谢您的", "请您仔细",
)

# 长行阈值：超过这个长度且含弱信号关键词，视为指导语
_INSTRUCTION_LONG_LEN = 40


def _looks_like_instruction(s: str) -> bool:
    """启发式判断一行是否更像指导语而非题目（仅在段落兜底分支用）。

    判定规则（任一即真）：
        1. 行首命中 ``_INSTRUCTION_PREFIXES``
        2. 行长 ≥ ``_INSTRUCTION_LONG_LEN`` 且包含 ``_INSTRUCTION_KEYWORDS`` 之一
        3. 行长 ≥ 80 字符（典型 Likert 题干很少这么长，长段落几乎确定是指导语）
    """
    s = s.strip()
    if not s:
        return False
    for p in _INSTRUCTION_PREFIXES:
        if s.startswith(p):
            return True
    if len(s) >= 80:
        return True
    if len(s) >= _INSTRUCTION_LONG_LEN:
        for kw in _INSTRUCTION_KEYWORDS:
            if kw in s:
                return True
    return False


def _parse_text(text: str, source_format: str) -> ItemsDoc:
    """主解析逻辑：识别标题、指导语、题目、反向题。"""
    if not text:
        return ItemsDoc(source_format=source_format, raw_warnings=["文件为空。"])

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]

    # ---- 1. 标题：第一个 H1，否则第一条非空非题目的短行 ----
    title = ""
    title_idx: Optional[int] = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        m = _HEADING_RE.match(ln)
        if m and len(m.group(1)) == 1:
            title = m.group(2).strip()
            title_idx = i
            break
    if not title:
        # 退化策略：第一条非空、非编号、长度合理的行
        for i, ln in enumerate(lines):
            s = ln.strip()
            if not s:
                continue
            if _is_item_line(ln) is not None:
                break  # 第一条就是题目，没标题
            if len(s) <= 60:
                title = s
                title_idx = i
            break

    # ---- 2. 抽题（先找编号/bullet）----
    items_with_idx: List[Tuple[int, str, str]] = []  # (line_index, style, text)
    first_heading_skipped = title_idx is not None
    for i, ln in enumerate(lines):
        if first_heading_skipped and i == title_idx:
            continue
        # 跳过其他标题行
        if _HEADING_RE.match(ln):
            continue
        hit = _is_item_line(ln)
        if hit:
            items_with_idx.append((i, hit[0], hit[1]))

    # ---- 3. 抽题失败时的兜底：纯段落每行一题（条件较严：连续 ≥3 行非空）----
    used_paragraph_fallback = False
    skipped_as_instruction: List[Tuple[int, str]] = []  # (line_idx, text) 用于回填指导语
    if not items_with_idx:
        candidates: List[Tuple[int, str, str]] = []
        for i, ln in enumerate(lines):
            s = ln.strip()
            if not s:
                continue
            if title_idx is not None and i == title_idx:
                continue
            if _HEADING_RE.match(ln):
                continue
            # v4.5: 用启发式过滤指导语（前缀 + 长文+关键词 + 超长行）
            if _looks_like_instruction(s):
                skipped_as_instruction.append((i, s))
                continue
            candidates.append((i, "plain", s))
        if len(candidates) >= 3:
            items_with_idx = candidates
            used_paragraph_fallback = True

    if not items_with_idx:
        return ItemsDoc(
            title=title,
            source_format=source_format,
            raw_warnings=["未识别到题目（既无编号 / bullet，也未触发段落兜底）。"],
        )

    # ---- 4. 指导语：标题之后、第一题之前的非空非标题行拼接 ----
    first_item_line = items_with_idx[0][0]
    instr_buf: List[str] = []
    start_i = (title_idx + 1) if title_idx is not None else 0
    for i in range(start_i, first_item_line):
        s = lines[i].strip()
        if not s:
            continue
        if _HEADING_RE.match(lines[i]):
            continue
        if _is_item_line(lines[i]) is not None:
            break
        instr_buf.append(s)
    instructions = " ".join(instr_buf).strip()

    # ---- 5. 反向题识别 + 文本清洗 ----
    items: List[str] = []
    reverse_indices: List[int] = []
    for k, (_idx, _style, raw) in enumerate(items_with_idx):
        cleaned, is_rev = _detect_reverse(raw)
        cleaned = _clean_item(cleaned)
        if not cleaned:
            continue
        items.append(cleaned)
        if is_rev:
            reverse_indices.append(len(items) - 1)

    warnings: List[str] = []
    # 风格混杂提醒
    styles = {s for _i, s, _t in items_with_idx}
    if len(styles) > 1 and "plain" not in styles:
        warnings.append(f"文件中混用了多种题目格式：{sorted(styles)}；已统一抽出。")
    if used_paragraph_fallback:
        warnings.append("未发现编号或 bullet 题目，已按「每行一题」段落规则抽取，请核对。")
    # 反向题标记数量异常
    if len(reverse_indices) > len(items) * 0.5 and len(items) >= 4:
        warnings.append(
            f"反向题占比 {len(reverse_indices)}/{len(items)}；通常 ≤ 30%，请确认标记是否正确。"
        )

    return ItemsDoc(
        title=title,
        instructions=instructions,
        items=items,
        reverse_indices=reverse_indices,
        source_format=source_format,
        raw_warnings=warnings,
    )


# ---------------------------------------------------------------------------
# 反序列化（UI / 测试便捷）
# ---------------------------------------------------------------------------


def items_doc_from_lines(
    items: List[str],
    *,
    title: str = "",
    instructions: str = "",
    reverse_indices: Optional[List[int]] = None,
    source_format: str = "manual",
) -> ItemsDoc:
    """直接从已经清洗过的题目列表构造 ItemsDoc，用于 UI 编辑后回写。"""
    cleaned = [_clean_item(s) for s in items if s and s.strip()]
    rev = [i for i in (reverse_indices or []) if 0 <= i < len(cleaned)]
    return ItemsDoc(
        title=title.strip(),
        instructions=instructions.strip(),
        items=cleaned,
        reverse_indices=sorted(set(rev)),
        source_format=source_format,
    )
