"""LLM驱动的问卷设计引擎：利用大语言模型进行构念分析、维度设计和题目生成"""

import json
import re
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, Future
from functools import lru_cache
import threading

from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APITimeoutError,
    APIStatusError,
    APIConnectionError,
)

from .construct_kb import CONSTRUCTS
from .item_templates import ALL_TEMPLATES

# 模块级线程池：最大2个并发LLM调用，避免阻塞Streamlit主线程
_llm_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="llm_engine")

# 取消标志：cancel_id -> bool，用于标记已取消的异步请求
_cancel_flags: dict = {}
_cancel_lock = threading.Lock()
_next_cancel_id = 0


class LLMEngineError(Exception):
    """LLM调用失败（网络、认证等）"""


class LLMResponseParseError(Exception):
    """LLM返回格式无法解析"""


class CancelledLLMError(Exception):
    """LLM请求已被用户取消"""


def _alloc_cancel_id() -> int:
    global _next_cancel_id
    with _cancel_lock:
        cid = _next_cancel_id
        _next_cancel_id += 1
        _cancel_flags[cid] = False
        return cid


def cancel_design_request(cancel_id: int) -> bool:
    """标记指定请求为已取消。返回True表示成功标记。"""
    with _cancel_lock:
        if cancel_id in _cancel_flags:
            _cancel_flags[cancel_id] = True
            return True
        return False


def _is_cancelled(cancel_id: int) -> bool:
    with _cancel_lock:
        return _cancel_flags.get(cancel_id, False)


def _cleanup_cancel_id(cancel_id: int):
    with _cancel_lock:
        _cancel_flags.pop(cancel_id, None)


def design_questionnaire_llm(
    research_question: str,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    timeout: int = 900,
    cancel_id: Optional[int] = None,
) -> Dict:
    """使用LLM设计问卷，返回与keyword引擎相同结构的design dict。"""
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(research_question)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response_text = _call_llm(
        messages=messages,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        cancel_id=cancel_id,
    )

    raw = _parse_and_validate(response_text, research_question)
    return _build_design_dict(raw, research_question)


# ================================================================
# System Prompt Builder
# ================================================================


@lru_cache(maxsize=1)
def _build_system_prompt() -> str:
    parts = []

    # --- Role ---
    parts.append(
        "你是一位经验丰富的心理测量学专家，精通量表编制、构念操作化、题目撰写和心理测量学评估。\n"
        "你的任务是根据用户的研究问题，设计一份符合心理测量学标准的完整问卷。\n"
        "你必须严格按照指定的 JSON 格式输出，不要添加任何额外的解释文字，只输出纯 JSON。\n"
    )

    # --- Knowledge Base Reference ---
    parts.append("## 心理学构念参考知识库\n")
    parts.append(
        "以下是常见的心理学构念及其维度结构，供你参考。"
        "当用户的研究问题与以下构念相关时，请基于这些学术定义和维度框架进行设计。"
        "当用户的研究问题涉及新构念时，请基于你的心理学专业知识合理推断维度结构。\n"
    )

    for cname, c in CONSTRUCTS.items():
        parts.append(f"### {cname} ({c['name_en']})")
        parts.append(f"- 领域: {c['domain']}")
        parts.append(f"- 定义: {c['definition'][:200]}")
        parts.append("- 维度:")
        for d in c["dimensions"]:
            parts.append(f"    - {d['name']}: {d['desc']} (建议{d['item_count']}题)")
        if c.get("established_scales"):
            parts.append("- 已有成熟量表参考:")
            for s in c["established_scales"][:3]:
                parts.append(f"    - {s}")
        parts.append("")

    # --- Item Writing Rules ---
    parts.append("## 题目撰写规范\n")
    parts.append(
        "1. **量表点数选择**：\n"
        "   - 临床/健康类构念（焦虑、抑郁等）：4点频率量表（去掉不确定选项，减少中间倾向）\n"
        "   - 人格/社会类构念（自尊、社会支持等）：5点同意度量表\n"
        "   - 态度/幸福感等宽泛构念：7点同意度量表\n"
        "2. **反向题比例**：总题量的 20%-30% 应为反向题，用于控制默认反应偏差\n"
        "3. **每维度题量**：3-8题，建议4-6题。题量过少信度不足，过多导致被试疲劳\n"
        "4. **题目措辞**：\n"
        "   - 每道题只包含一个核心概念（避免双重负载，如\"我又累又难过\"）\n"
        "   - 避免诱导性表述（如\"大多数人认为...\"）\n"
        "   - 避免社会称许性暗示\n"
        "   - 题目语言应适合目标人群的阅读水平\n"
        "   - 中文表达通顺自然，符合汉语表达习惯\n"
        "5. **锚定标签规范**：\n"
        "   - 频率量表：1=从不, 2=偶尔, 3=有时, 4=经常, 5=总是\n"
        "   - 同意度量表：1=完全不同意, 2=不太同意, 3=不确定, 4=比较同意, 5=完全同意\n"
        "   - 满意度量表：1=非常不满意, 5=非常满意\n"
        "6. **指导语规范**：包含研究目的说明、保密声明、填写说明、评分标准\n"
    )

    # --- Psychometric Standards ---
    parts.append("## 心理测量学标准\n")
    parts.append(
        "- 内容效度：I-CVI ≥ 0.78 为可接受，S-CVI/Ave ≥ 0.90\n"
        "- 结构效度：KMO ≥ 0.80, 因子载荷 ≥ 0.40, 交叉载荷 < 0.30\n"
        "- CFA拟合：CFI ≥ 0.90, RMSEA < 0.08, SRMR < 0.08\n"
        "- 内部一致性：Cronbach's α ≥ 0.70（可接受），≥ 0.80（良好）\n"
        "- 重测信度：ICC ≥ 0.70（间隔2-4周）\n"
        "- 组合信度：CR ≥ 0.70, 平均方差抽取量 AVE ≥ 0.50\n"
    )

    # --- JSON Schema ---
    parts.append("## 输出JSON格式\n")
    parts.append(
        '你必须严格输出以下格式的JSON（不要用markdown代码块包裹，直接输出JSON）：\n'
    )
    schema = {
        "construct_name": "中文构念名称（简洁，2-6字）",
        "construct_name_en": "English Name",
        "domain": "领域：临床与健康/人格/社会心理/教育心理/认知/组织行为/发展/其他",
        "definition": "构念的学术定义，2-4句，应包含理论来源或经典文献观点",
        "dimensions": [
            {
                "name": "维度中文名",
                "desc": "维度的详细描述",
                "item_count": 0,
                "example": "一条示例题目",
            }
        ],
        "scale_type": "likert_agreement / frequency / semantic_differential / situational / behavioral",
        "scale_points": 0,
        "scale_type_label": "agreement / frequency / satisfaction / importance",
        "anchor_labels": ["1=标签", "2=标签", "...", "N=标签"],
        "items": [
            {
                "text": "题目中文文本（完整的一句话，通顺自然）",
                "reverse": False,
                "dimension": "所属维度名称",
            }
        ],
        "instructions": "完整的问卷指导语，包含研究目的、保密声明、填写说明、评分标准",
        "scoring": "计分方式说明，包括正向题和反向题的计分规则、总分范围及含义",
        "psychometrics": {
            "内容效度": "针对本问卷的量身定制的内容效度保障策略",
            "表面效度": "表面效度检查要点",
            "结构效度": "EFA/CFA策略，预期因子数及拟合标准",
            "信度": "信度评估方案（α、重测、分半信度）",
            "社会称许性控制": "控制社会称许性偏差的策略",
        },
        "references": ["相关学术参考文献，APA格式，至少3条"],
        "established_scales": ["已有的成熟量表名称及简要说明"],
        "match_reason": "设计思路说明：为什么这样分解维度、为什么选择这种题型和量表点数、如何保障信效度",
    }
    parts.append(json.dumps(schema, ensure_ascii=False, indent=2))
    parts.append("")
    parts.append(
        "注意：\n"
        "1. dim_name 应为每个维度合理分配题目数量（3-6题/维度）\n"
        "2. items 中约20-30%的题目应设置 reverse=true\n"
        "3. items 按照维度顺序排列，同一维度的题目放在一起\n"
        "4. 确保 reverse=true 的题目措辞确实与该维度方向相反\n"
        "5. 所有中文字段务必使用中文输出"
    )

    return "\n".join(parts)


def _build_user_prompt(research_question: str) -> str:
    return (
        f"研究问题：{research_question}\n\n"
        "请根据上述研究问题，设计一份完整的心理学问卷。"
        "请严格输出符合系统提示中指定格式的 JSON。不要使用 markdown 代码块。"
    )


# ================================================================
# LLM API Caller
# ================================================================


def _call_llm(
    messages: list,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
    cancel_id: Optional[int] = None,
) -> str:
    if cancel_id is not None and _is_cancelled(cancel_id):
        raise CancelledLLMError("LLM 请求已被用户取消")
    try:
        from src.llm_gateway.gateway import llm_chat, LLMUnavailableError
        cancel_str = str(cancel_id) if cancel_id is not None else None
        resp = llm_chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            cancel_id=cancel_str,
            retries=1,
        )
        if resp.cancelled:
            raise CancelledLLMError("LLM 请求已被用户取消")
        if not resp.ok:
            raise LLMResponseParseError(resp.error or "LLM 返回了空内容")
        return resp.content.strip()
    except LLMUnavailableError as e:
        raise LLMEngineError(str(e))
    except LLMResponseParseError:
        raise
    except CancelledLLMError:
        raise
    except Exception as e:
        raise LLMEngineError(f"LLM 调用异常：{e}")


# ================================================================
# JSON Parser & Validator
# ================================================================


def _parse_and_validate(response_text: str, research_question: str) -> Dict:
    # Strip markdown code fences if present
    text = response_text.strip()

    # v3.7 健壮化：兼容前后带说明文字的 ```json 块
    fence_pattern = r"```(?:json)?\s*\n(.*?)\n```"
    m = re.search(fence_pattern, text, re.DOTALL)
    if m:
        text = m.group(1).strip()

    # Extract JSON: find first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1:
        raise LLMResponseParseError("LLM 返回内容中未找到有效的 JSON 结构。")

    # v3.7：如果找不到匹配的右括号（被截断），尝试自动补齐
    if end == -1 or start >= end:
        json_str = _try_repair_truncated_json(text[start:])
    else:
        json_str = text[start: end + 1]

    try:
        raw = json.loads(json_str)
    except json.JSONDecodeError as e:
        # v3.7 兜底：尝试修复截断的 JSON
        repaired = _try_repair_truncated_json(json_str)
        if repaired != json_str:
            try:
                raw = json.loads(repaired)
            except json.JSONDecodeError:
                raise LLMResponseParseError(
                    f"JSON 解析失败（位置 {e.pos}/{len(json_str)}）：{e}。"
                    f"最可能原因：max_tokens 太小导致 LLM 输出被截断。"
                    f"建议：重试一次，或换用更短的研究问题。"
                )
        else:
            raise LLMResponseParseError(
                f"JSON 解析失败（位置 {e.pos}/{len(json_str)}）：{e}。"
                f"最可能原因：max_tokens 太小导致 LLM 输出被截断。"
                f"建议：重试一次，或换用更短的研究问题。"
            )

    # Validate required keys
    required = ["construct_name", "dimensions", "items", "instructions"]
    missing = [k for k in required if k not in raw]
    if missing:
        raise LLMResponseParseError(f"LLM 返回的 JSON 缺少必要字段：{', '.join(missing)}")

    if not isinstance(raw["dimensions"], list) or len(raw["dimensions"]) == 0:
        raise LLMResponseParseError("dimensions 必须是非空数组")

    if not isinstance(raw["items"], list) or len(raw["items"]) == 0:
        raise LLMResponseParseError("items 必须是非空数组")

    # Fill defaults
    raw.setdefault("definition", f"{raw['construct_name']}的操作性定义。")
    raw.setdefault("domain", "其他")
    raw.setdefault("scale_type", "likert_agreement")
    raw.setdefault("scale_points", 5)
    raw.setdefault("scale_type_label", "agreement")
    raw.setdefault(
        "anchor_labels",
        ["1=完全不同意", "2=不太同意", "3=不确定", "4=比较同意", "5=完全同意"],
    )
    raw.setdefault("scoring", _default_scoring(raw))
    raw.setdefault("psychometrics", {})
    raw.setdefault("references", [])
    raw.setdefault("established_scales", [])
    raw.setdefault(
        "match_reason",
        f"由大语言模型基于心理学测量理论，针对「{research_question}」进行构念分析和维度设计。",
    )

    # Ensure each dimension has item_count
    for dim in raw["dimensions"]:
        dim.setdefault("item_count", 5)

    # Ensure each item has required fields
    dim_names = [d["name"] for d in raw["dimensions"]]
    for i, item in enumerate(raw["items"]):
        item.setdefault("reverse", False)
        item.setdefault("dimension", dim_names[0] if dim_names else "")
        # Add index
        item["index"] = i + 1

    return raw


def _try_repair_truncated_json(json_str: str) -> str:
    """v3.7：尝试修复被 max_tokens 截断的 JSON。

    策略：
    1. 移除尾部明显不完整的 token（如尾部不闭合的 string、未完成的 key:）
    2. 按层级补齐缺失的 `]` 和 `}`
    3. 如果尾部停在 string 中（含未闭合的 ""），先关 string

    返回：尝试修复后的 JSON 字符串。仍可能失败，由 caller 决定是否再 parse。
    """
    if not json_str or not json_str.strip():
        return json_str

    s = json_str.rstrip()

    # 1) 处理尾部未闭合的 string（找最后一个未匹配的 "）
    in_string = False
    escape = False
    last_complete_pos = -1
    bracket_stack: list = []   # 记录 { [ 的栈
    for i, ch in enumerate(s):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "[{":
            bracket_stack.append(ch)
            last_complete_pos = i
        elif ch in "]}":
            if bracket_stack:
                opener = bracket_stack[-1]
                if (opener == "[" and ch == "]") or (opener == "{" and ch == "}"):
                    bracket_stack.pop()
                    last_complete_pos = i

    # 如果还在 string 中，截断到最后一个完整位置
    if in_string and last_complete_pos > 0:
        s = s[: last_complete_pos + 1]
        # 重建 bracket_stack
        bracket_stack = []
        in_string = False
        escape = False
        for ch in s:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in "[{":
                bracket_stack.append(ch)
            elif ch in "]}":
                if bracket_stack:
                    bracket_stack.pop()

    # 2) 移除尾部不完整结构（如 ", "、"key": ）
    s = s.rstrip().rstrip(",").rstrip()
    # 如果尾部是 "key":  这种半截（值缺失），删除
    s = re.sub(r',\s*"[^"]*"\s*:\s*$', "", s)
    s = re.sub(r'"[^"]*"\s*:\s*$', "", s)
    s = s.rstrip().rstrip(",").rstrip()

    # 3) 补齐缺失的右括号
    while bracket_stack:
        opener = bracket_stack.pop()
        if opener == "{":
            s += "}"
        elif opener == "[":
            s += "]"

    return s


def _default_scoring(raw: Dict) -> str:
    points = raw.get("scale_points", 5)
    n_items = len(raw.get("items", []))
    n_reverse = sum(1 for it in raw.get("items", []) if it.get("reverse"))
    total_range = f"{n_items}~{n_items * points}"
    return (
        f"采用{points}点 Likert 量表计分（1-{points}分）。\n"
        f"正向题：选择1计1分，选择{points}计{points}分。\n"
        f"反向题（共{n_reverse}题）：反向计分。\n"
        f"总分范围：{total_range}分。总分越高表示{raw['construct_name']}水平越高。"
    )


# ================================================================
# Task 6: LLM 辅助反向题改写
# ================================================================


def rewrite_reverse_item_llm(
    positive_text: str,
    dimension_name: str,
    construct_name: str,
    api_key: str,
    base_url: str,
    model: str = "gpt-4o",
    temperature: float = 0.3,
    max_tokens: int = 512,
    timeout: int = 60,
) -> Dict:
    """
    使用 LLM 将正向题改写为自然的中文反向题（语义否定而非机械加\"不\"）。

    参数：
        positive_text: 正向题文本
        dimension_name: 所属维度名
        construct_name: 所属构念名
        api_key / base_url / model: LLM 连接参数
        temperature: 控制创造性（0.3=保守改写）
        max_tokens: 最大输出 token
        timeout: 超时秒数

    返回：
        {
            "success": bool,
            "reverse_text": str,
            "method": "llm" | "fallback",
            "analysis": str,   # LLM对改写策略的简要说明
            "warning": str,    # 如有
        }
    """
    from .item_templates import _apply_semantic_negation

    system_prompt = (
        "你是一位心理测量学和中文语言表达专家。"
        "你的任务是将正向心理学题目改写为自然流畅的中文反向题。\n\n"
        "改写要求：\n"
        "1. 反向题必须对正向题内容形成语义否定，而非简单机械地加\"不\"字\n"
        "2. 使用自然的中文否定表达方式（反义词替换、句型调整等）\n"
        "3. 保持反向题与正向题讨论相同的具体行为/感受/信念\n"
        '4. 避免双重否定（如"不是不"）\n'
        "5. 避免生僻心理学术语\n"
        "6. 反向题长度应与原题相近（±10字）\n"
        "7. 反向题读起来应自然，如同一个人在日常对话中的表达\n\n"
        "输出格式：纯 JSON，不要添加任何额外文字。\n"
        '{"reverse_text": "改写后的反向题", "analysis": "改写策略的简要说明（20字以内）"}'
    )

    user_prompt = (
        f"构念：{construct_name}\n"
        f"维度：{dimension_name}\n"
        f"正向题：{positive_text}\n\n"
        "请将以上正向题改写为自然的中文反向题。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response_text = _call_llm(
            messages=messages,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        # 解析 JSON
        import json
        import re
        text = response_text.strip()
        fence_pattern = r"^```(?:json)?\s*\n(.*?)\n```\s*$"
        m = re.match(fence_pattern, text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            parsed = json.loads(text[start:end + 1])
            reverse_text = parsed.get("reverse_text", "").strip()
            analysis = parsed.get("analysis", "LLM 改写")
            if reverse_text and len(reverse_text) >= 3:
                return {
                    "success": True,
                    "reverse_text": reverse_text,
                    "method": "llm",
                    "analysis": analysis,
                    "warning": "",
                }
    except Exception:
        pass

    # 降级：语义否定
    fallback_text = _apply_semantic_negation(positive_text)
    return {
        "success": True,
        "reverse_text": fallback_text,
        "method": "fallback",
        "analysis": "LLM 改写失败，使用语义否定规则",
        "warning": "LLM 不可用或返回无效，已回退到规则引擎",
    }


def rewrite_all_reverse_items(
    items: list,
    construct_name: str,
    api_key: str,
    base_url: str,
    model: str = "gpt-4o",
    use_llm: bool = True,
) -> list:
    """
    改写题目列表中所有反向题（原地替换 reverse=True 的题目文本）。

    参数：
        items: 题目列表（含 text、reverse、dimension 字段）
        construct_name: 构念名（供 LLM 上下文）
        use_llm: False 时跳过 LLM，直接使用语义否定规则

    返回：更新后的题目列表（新增 llm_rewritten 字段标记改写来源）
    """
    from .item_templates import _apply_semantic_negation

    for item in items:
        if not item.get("reverse"):
            continue

        pos_text = item.get("text", "")
        dim_name = item.get("dimension", "")

        if use_llm:
            result = rewrite_reverse_item_llm(
                positive_text=pos_text,
                dimension_name=dim_name,
                construct_name=construct_name,
                api_key=api_key,
                base_url=base_url,
                model=model,
            )
            item["text"] = result["reverse_text"]
            item["llm_rewritten"] = result["method"] == "llm"
            item["rewrite_method"] = result["method"]
        else:
            item["text"] = _apply_semantic_negation(pos_text)
            item["llm_rewritten"] = False
            item["rewrite_method"] = "semantic_rule"

    return items


def design_questionnaire_llm_async(
    research_question: str,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    timeout: int = 900,
) -> dict:
    """异步版本：在后台线程中执行LLM调用。
    返回 {"future": Future, "cancel_id": int}，供UI层取消使用。

    v3.7: 包装 v3.6 LLM 网关 — cache 命中时返回 immediate Future，避免重复 API 调用。
    cache key 基于 (research_question, model, temperature)，同 prompt 二次设计秒回。
    """
    # v3.7 cache 检查（手动构造 messages-like key）
    cache_key = _make_design_cache_key(research_question, model, temperature)
    cached_design = _design_cache_get(cache_key)
    if cached_design is not None:
        # 立即完成的 Future
        cancel_id = _alloc_cancel_id()
        immediate_future = _llm_executor.submit(lambda: cached_design)

        def _cleanup_imm(_):
            _cleanup_cancel_id(cancel_id)
        immediate_future.add_done_callback(_cleanup_imm)
        # 记录 trace（缓存命中）
        _record_design_trace(model, cached=True, success=True)
        return {"future": immediate_future, "cancel_id": cancel_id, "from_cache": True}

    cancel_id = _alloc_cancel_id()

    def _run_with_cache():
        import time as _time
        _start = _time.time()
        try:
            result = design_questionnaire_llm(
                research_question, api_key, base_url, model,
                temperature, max_tokens, timeout, cancel_id,
            )
            # 写缓存
            _design_cache_put(cache_key, result)
            _record_design_trace(
                model, cached=False, success=True,
                elapsed_ms=(_time.time() - _start) * 1000,
            )
            return result
        except CancelledLLMError:
            _record_design_trace(model, cached=False, success=False, cancelled=True)
            raise
        except Exception as exc:
            _record_design_trace(
                model, cached=False, success=False,
                elapsed_ms=(_time.time() - _start) * 1000, error=str(exc)[:120],
            )
            raise

    future = _llm_executor.submit(_run_with_cache)

    def _cleanup(_):
        _cleanup_cancel_id(cancel_id)

    future.add_done_callback(_cleanup)
    return {"future": future, "cancel_id": cancel_id, "from_cache": False}


# ================================================================
# v3.7 设计结果缓存（独立于 gateway 缓存，因为返回的是 dict 不是 str）
# ================================================================

import hashlib as _hashlib

_design_cache: Dict[str, Dict] = {}
_design_cache_lock = threading.Lock()
_DESIGN_CACHE_MAX = 50


def _make_design_cache_key(question: str, model: str, temperature: float) -> str:
    blob = f"{question.strip()[:500]}|{model}|{round(temperature, 2)}"
    return _hashlib.md5(blob.encode("utf-8")).hexdigest()


def _design_cache_get(key: str) -> Optional[Dict]:
    with _design_cache_lock:
        return _design_cache.get(key)


def _design_cache_put(key: str, value: Dict) -> None:
    if not value:
        return
    with _design_cache_lock:
        if len(_design_cache) >= _DESIGN_CACHE_MAX:
            try:
                first = next(iter(_design_cache))
                _design_cache.pop(first, None)
            except StopIteration:
                pass
        _design_cache[key] = value


def clear_design_cache() -> None:
    with _design_cache_lock:
        _design_cache.clear()


def _record_design_trace(
    model: str,
    *,
    cached: bool = False,
    success: bool = True,
    cancelled: bool = False,
    elapsed_ms: float = 0.0,
    error: str = "",
) -> None:
    """v3.7: 把问卷设计调用记录到 v3.6 LLM trace（统一统计）。"""
    try:
        from src.llm_gateway.gateway import LLMTrace, _record_trace
        from datetime import datetime
        _record_trace(LLMTrace(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            module="questionnaire_design",
            model=model,
            backend="openai_sdk",
            elapsed_ms=elapsed_ms,
            cached=cached,
            success=success,
            cancelled=cancelled,
            error=error,
        ))
    except Exception:
        pass


# ================================================================
# Design Dict Builder
# ================================================================


def _build_design_dict(raw: Dict, research_question: str) -> Dict:
    dims = raw["dimensions"]
    items = []

    for i, item_data in enumerate(raw["items"]):
        items.append(
            {
                "index": i + 1,
                "text": item_data["text"],
                "reverse": item_data.get("reverse", False),
                "dimension": item_data.get("dimension", dims[0]["name"] if dims else ""),
            }
        )

    n_reverse = sum(1 for it in items if it["reverse"])
    scale_type_key = raw.get("scale_type", "likert_agreement")
    template = ALL_TEMPLATES.get(scale_type_key, ALL_TEMPLATES["likert_agreement"])

    return {
        "research_question": research_question,
        "matched_construct": None,
        "construct_name": raw["construct_name"],
        "is_exact_match": False,
        "match_reason": raw.get(
            "match_reason",
            "由大语言模型基于心理学测量理论生成设计。",
        ),
        "dimensions_used": dims,
        "template_used": template,
        "scale_config": {
            "points": raw.get("scale_points", 5),
            "scale_type": raw.get("scale_type_label", "agreement"),
            "anchors": raw.get(
                "anchor_labels",
                ["1=完全不同意", "2=不太同意", "3=不确定", "4=比较同意", "5=完全同意"],
            ),
            "n_items": len(items),
            "n_dimensions": len(dims),
            "n_reverse": n_reverse,
            "reverse_ratio": f"{round(n_reverse / len(items) * 100) if items else 0}%",
        },
        "items": items,
        "instructions": raw.get("instructions", ""),
        "scoring": raw.get("scoring", ""),
        "psychometrics": raw.get("psychometrics", {}),
        "llm_definition": raw.get("definition", ""),
        "llm_references": raw.get("references", []),
        "llm_established_scales": raw.get("established_scales", []),
        "llm_generated": True,
        "llm_used": True,
    }
