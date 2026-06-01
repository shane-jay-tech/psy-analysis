"""Prompt builders for construct and method extraction.

PROMPT_VERSION must be bumped whenever system or user message templates change,
because it is part of the extraction cache key.
"""

from __future__ import annotations

import secrets
from typing import Dict, List

PROMPT_VERSION = "v1"

_CONSTRUCT_SYSTEM = """\
你是一名心理学文献分析专家。任务是从论文摘要中抽取心理学构念（psychological constructs）。

硬性规则：
1. 所有字段（name、definition、evidence_quote）使用中文。
2. evidence_quote 必须满足：
   - 长度 ≥ 10 字符
   - 是摘要原文中连续出现的逐字片段（不得改写、不得截断汉字）
   - 找不到符合要求的原文片段就不要返回该构念
3. 最多 6 个构念；摘要不足以支撑某个就不要返回它；完全无法支撑就返回空列表。
4. 不要推断或猜测摘要未明确涉及的构念。
5. 仅返回合法 JSON，不要 markdown 围栏（```），不要任何前后说明。

输出格式：
{"constructs":[{"name":"构念名","definition":"简短定义","evidence_quote":"摘要逐字片段","confidence":0.85,"novelty_hint":null}]}

confidence ∈ [0,1]，novelty_hint 无新颖性写 null。\
"""

_METHOD_SYSTEM = """\
你是一名心理学文献分析专家。任务是从论文摘要中抽取研究方法（research methods）。

硬性规则：
1. 所有字段（name、evidence_quote）使用中文。
2. evidence_quote 必须满足：
   - 长度 ≥ 10 字符
   - 是摘要原文中连续出现的逐字片段（不得改写、不得截断汉字）
   - 找不到符合要求的原文片段就不要返回该方法
3. 最多 4 种方法；摘要不足以支撑某个就不要返回它；完全无法支撑就返回空列表。
4. method_category 取值仅限：experimental / survey / qualitative / meta_analysis / computational / other
5. 不要推断或猜测摘要未明确涉及的方法。
6. 仅返回合法 JSON，不要 markdown 围栏（```），不要任何前后说明。

输出格式：
{"methods":[{"name":"方法名","method_category":"survey","evidence_quote":"摘要逐字片段","confidence":0.9,"novelty_hint":null}]}

confidence ∈ [0,1]，novelty_hint 无新颖性写 null。\
"""

_RETRY_SUFFIX = (
    "\n\n再次提醒：仅返回 JSON，不要 markdown 围栏。"
    "evidence_quote 必须是摘要分隔符之间内容的逐字连续子串。"
)


def _make_delimiter() -> str:
    """每次随机一个不可被作者预测的分隔符，防止摘要里塞 ``>>>`` 截断 prompt。"""
    return f"<<<ABSTRACT-{secrets.token_hex(8)}>>>"


def _user_message(*, title: str, abstract: str, journal: str) -> str:
    delim = _make_delimiter()
    # 极罕见碰撞：摘要里恰好出现同样 token 时，重新摇直到不冲突
    while delim in abstract:
        delim = _make_delimiter()
    lines = [f"论文标题：{title}"]
    if journal:
        lines.append(f"期刊：{journal}")
    lines.append(f"摘要（在两个分隔符 {delim} 之间）：")
    lines.append(delim)
    lines.append(abstract)
    lines.append(delim)
    return "\n".join(lines)


def build_construct_prompt(
    *,
    title: str,
    abstract: str,
    journal: str = "",
    retry: bool = False,
) -> List[Dict[str, str]]:
    """构念抽取 messages。retry=True 追加收紧提醒。"""
    system = _CONSTRUCT_SYSTEM + (_RETRY_SUFFIX if retry else "")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": _user_message(title=title, abstract=abstract, journal=journal)},
    ]


def build_method_prompt(
    *,
    title: str,
    abstract: str,
    journal: str = "",
    retry: bool = False,
) -> List[Dict[str, str]]:
    """方法抽取 messages。retry=True 追加收紧提醒。"""
    system = _METHOD_SYSTEM + (_RETRY_SUFFIX if retry else "")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": _user_message(title=title, abstract=abstract, journal=journal)},
    ]
