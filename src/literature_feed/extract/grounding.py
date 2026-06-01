"""LLM 输出的 JSON 解析 + evidence_quote grounding 校验。"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, Optional

# 任意空白：ASCII 空格、全角空格 U+3000、不间断空格 U+00A0、tab、CR、LF
_WS_RE = re.compile(r"[ 　 \t\r\n]+")


def _normalize_ws(text: str) -> str:
    """NFKC 规范化 + 折叠空白成单个 ASCII 空格 + 两端 strip。"""
    return _WS_RE.sub(" ", unicodedata.normalize("NFKC", text or "")).strip()


def quote_in_abstract(quote: str, abstract: str, *, min_len: int = 10) -> bool:
    """quote 是否为 abstract 的逐字子串（NFKC + 空白折叠后）。

    中文不做小写化（NFKC 后已经规范）。归一化后 quote 短于 min_len 直接 False。
    """
    nq = _normalize_ws(quote)
    if len(nq) < min_len:
        return False
    return nq in _normalize_ws(abstract)


def parse_llm_json(raw: str) -> Optional[Dict[str, Any]]:
    """容错 JSON 解析。

    顺序：
    1. strip + 去掉 ```json ... ``` 围栏（LLM 偶尔违规加）
    2. json.loads 直接试
    3. 回退：抓最外层 { ... } 再试
    4. 全都失败返回 None
    """
    if not raw:
        return None
    text = raw.strip()

    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last <= first:
        return None
    try:
        result = json.loads(text[first : last + 1])
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        return None
    return None
