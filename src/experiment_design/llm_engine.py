"""LLM驱动的实验设计增强引擎

利用大语言模型对规则引擎生成的实验设计方案进行深度增强，
生成更丰富的研究背景、假设、程序描述和分析计划。
"""

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Optional

from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APITimeoutError,
    APIStatusError,
    APIConnectionError,
)

# 模块级线程池：最大2个并发LLM调用
_llm_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="exp_llm_engine")

# 取消标志池
cancel_flags: dict = {}
_cancel_lock = threading.Lock()
_next_cancel_id = 0


class LLMEngineError(Exception):
    """LLM调用失败"""


class LLMResponseParseError(Exception):
    """LLM返回格式无法解析"""


class CancelledLLMError(Exception):
    """LLM请求已被用户取消"""


def _alloc_cancel_id() -> int:
    global _next_cancel_id
    with _cancel_lock:
        cid = _next_cancel_id
        _next_cancel_id += 1
        cancel_flags[cid] = False
        return cid


def cancel_design_request(cancel_id: int) -> bool:
    """标记指定请求为已取消。"""
    with _cancel_lock:
        if cancel_id in cancel_flags:
            cancel_flags[cancel_id] = True
            return True
        return False


def _is_cancelled(cancel_id: int) -> bool:
    with _cancel_lock:
        return cancel_flags.get(cancel_id, False)


def _cleanup_cancel_id(cancel_id: int):
    with _cancel_lock:
        cancel_flags.pop(cancel_id, None)


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


def _build_system_prompt() -> str:
    return (
        "你是一位经验丰富的心理学研究方法学专家，精通实验设计、统计分析和学术写作。\n"
        "你的任务是根据用户的研究方向和基本信息，生成一份高质量的实验设计内容。\n"
        "你必须严格按照指定的 JSON 格式输出，不要添加任何额外的解释文字，只输出纯 JSON。\n\n"
        "## 输出规范\n"
        "1. 研究背景应基于真实心理学理论和文献，引用经典理论框架\n"
        "2. 研究假设应具体、可检验，包含方向性预测\n"
        "3. 实验程序应详细、可操作，包含每个阶段的具体步骤和时间安排\n"
        "4. 变量操纵应明确说明如何操作自变量\n"
        "5. 测量方案应说明因变量的具体测量指标和工具\n"
        "6. 数据分析计划应具体说明将使用的统计方法\n"
        "7. 所有输出必须为中文\n\n"
        "## 输出JSON格式\n"
        '{\n'
        '  "background": "详细的研究背景（300-500字），包含理论依据和文献回顾",\n'
        '  "hypotheses": [\n'
        '    "H1: 具体、可检验的研究假设1（包含方向性预测）",\n'
        '    "H2: 具体、可检验的研究假设2（如有交互作用等）"\n'
        '  ],\n'
        '  "research_questions": [\n'
        '    "RQ1: 研究问题1",\n'
        '    "RQ2: 研究问题2"\n'
        '  ],\n'
        '  "iv_details": [\n'
        '    {\n'
        '      "name": "自变量名称",\n'
        '      "manipulation": "详细的操纵方式描述（200字以上）",\n'
        '      "levels": ["水平1", "水平2"]\n'
        '    }\n'
        '  ],\n'
        '  "dv_details": [\n'
        '    {\n'
        '      "name": "因变量名称",\n'
        '      "measure": "测量工具/指标",\n'
        '      "details": "详细的测量方案（100字以上）"\n'
        '    }\n'
        '  ],\n'
        '  "procedure_phases": [\n'
        '    {\n'
        '      "name": "阶段名称",\n'
        '      "duration_min": 10,\n'
        '      "description": "详细描述该阶段的具体操作步骤",\n'
        '      "checklist": ["检查项1", "检查项2"]\n'
        '    }\n'
        '  ],\n'
        '  "analysis_plan": "详细的数据分析计划（200字以上），说明具体的统计方法和软件",\n'
        '  "ethics_notes": ["伦理考虑1", "伦理考虑2"],\n'
        '  "expected_results": "预期的结果模式及理论解释"\n'
        '}\n'
    )


def _build_user_prompt(
    topic: str,
    target_population: str = "",
    design_type: str = "",
    ivs: list = None,
    dvs: list = None,
) -> str:
    parts = [
        f"研究主题：{topic}",
    ]
    if target_population:
        parts.append(f"目标人群：{target_population}")
    if design_type:
        parts.append(f"设计类型：{design_type}")
    if ivs:
        parts.append(f"自变量：{', '.join(ivs)}")
    if dvs:
        parts.append(f"因变量：{', '.join(dvs)}")

    parts.append(
        "\n请根据上述信息，生成一份详细的实验设计内容。"
        "请严格输出符合系统提示中指定格式的 JSON。不要使用 markdown 代码块。"
    )
    return "\n".join(parts)


def _parse_json_response(response_text: str) -> Dict:
    text = response_text.strip()
    fence_pattern = r"^```(?:json)?\s*\n(.*?)\n```\s*$"
    m = re.match(fence_pattern, text, re.DOTALL)
    if m:
        text = m.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise LLMResponseParseError("LLM 返回内容中未找到有效的 JSON 结构。")

    json_str = text[start : end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise LLMResponseParseError(f"JSON 解析失败：{e}")


def design_experiment_llm(
    topic: str,
    api_key: str,
    base_url: str,
    model: str,
    target_population: str = "",
    design_type: str = "",
    ivs: list = None,
    dvs: list = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    timeout: int = 900,
    cancel_id: Optional[int] = None,
) -> Dict:
    """使用LLM增强实验设计内容。

    返回一个包含增强后字段的字典，可直接用于更新 ExperimentDesign 对象。
    """
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(topic, target_population, design_type, ivs, dvs)

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

    raw = _parse_json_response(response_text)

    # 填充默认值，确保字段存在
    result = {
        "background": raw.get("background", ""),
        "hypotheses": raw.get("hypotheses", []),
        "research_questions": raw.get("research_questions", []),
        "iv_details": raw.get("iv_details", []),
        "dv_details": raw.get("dv_details", []),
        "procedure_phases": raw.get("procedure_phases", []),
        "analysis_plan": raw.get("analysis_plan", ""),
        "ethics_notes": raw.get("ethics_notes", []),
        "expected_results": raw.get("expected_results", ""),
        "llm_enhanced": True,
    }

    return result


def design_experiment_llm_async(
    topic: str,
    api_key: str,
    base_url: str,
    model: str,
    target_population: str = "",
    design_type: str = "",
    ivs: list = None,
    dvs: list = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    timeout: int = 900,
) -> dict:
    """异步版本：在后台线程中执行LLM调用。

    返回 {"future": Future, "cancel_id": int}，供UI层取消使用。
    """
    cancel_id = _alloc_cancel_id()
    future = _llm_executor.submit(
        design_experiment_llm,
        topic,
        api_key,
        base_url,
        model,
        target_population,
        design_type,
        ivs,
        dvs,
        temperature,
        max_tokens,
        timeout,
        cancel_id,
    )

    def _cleanup(_):
        _cleanup_cancel_id(cancel_id)

    future.add_done_callback(_cleanup)
    return {"future": future, "cancel_id": cancel_id}
