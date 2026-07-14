"""AI 助教 — 把当前研究上下文注入 system prompt，多轮对话指导。

职责拆分：
- build_tutor_system_prompt(): 把 plan + result + ctx 转成 system 描述
- build_tutor_messages(): 维护多轮对话历史
- chat_with_tutor(): 统一封装 LLM 调用（ollama / openai 兼容）
- format_result_summary(): 把 result dataclass 转成易读文本

设计目标：
- 上下文注入用户的具体数值（n=200, d=0.55, p=.024），让 AI 答得到点子上
- 不再是「润色」工具，而是「陪练」：方法选择/效应量解释/局限讨论/答辩练习
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #

@dataclass
class TutorContext:
    """构造 system prompt 所需的研究上下文。"""
    test_type: str = ""
    test_name_zh: str = ""
    sample_size: int = 0
    dv: str = ""
    iv: str = ""
    p_value: Optional[float] = None
    effect_size: Optional[float] = None
    effect_size_name: str = ""
    extra_stats: Dict[str, Any] = field(default_factory=dict)
    # v3.2 上游漏斗扩展：phase 决定 system prompt 走哪条分支
    phase: str = ""           # "" (论文导师，默认) | "funnel" (苏格拉底反问)
    funnel_stage: int = 0     # 1..5（仅 phase="funnel" 时使用）
    # v3.3 跨阶段一致性：跟踪已问主题，防止退行和重复
    asked_themes: List[str] = field(default_factory=list)
    current_stage_progress: int = 0     # 当前阶段已进行的问答轮次


@dataclass
class ChatMessage:
    role: str  # "user" / "assistant"
    content: str


# --------------------------------------------------------------------------- #
# system prompt 构造
# --------------------------------------------------------------------------- #

TUTOR_BASE_PROMPT = """\
你是一位资深心理学研究方法导师，正在指导本科生写毕业论文。
你的角色定位：
- **风格**：耐心、平实、中文回答，避免过度学术腔
- **重点**：把统计概念翻译成本科生能懂的话；先给具体数字结论，再讲背后道理
- **态度**：诚实——遇到边界情况会承认「不确定」「需要看更多信息」
- **避免**：使用「应该」「必须」过强语气；引用学生没提到的复杂方法（HLM/SEM 等）；编造数据

你能力的边界：
- 不替学生做决定，而是给出 2-3 个选项 + 利弊
- 不预测论文能否通过，而是指出当前数据的支持强度
- 涉及伦理或学术不端时（如「能不能改 p 值」），明确拒绝并说明
"""


# v3.2 上游漏斗：苏格拉底反问 system prompt
FUNNEL_BASE_PROMPT = """\
你是一位心理学研究方法导师，但**这一阶段你的唯一任务是反问，不是给答案**。
学生正在做选题漏斗，从「模糊兴趣」收敛到「可研究的具体问题」。

# 你必须遵守的输出规则（违反任何一条都算失败）
1. **每次输出只能是 1-2 个反问句**，每句以「？」结尾，每句 ≤80 字
2. **禁止陈述句**——不要解释、不要列举、不要总结
3. **禁止给答案**——不要说「我觉得你应该研究 X」「这个题目很好」
4. **必须引用学生上一轮的具体词**——让学生感到你在听他说，不是抛模板
5. **避免连珠炮**——如果一个反问已经够锋利，就只问一个

# 你的目标（按阶段不同）
- 阶段 1（兴趣捕捉）：把学生的抽象兴趣 → 具体的「让你不爽/困惑的现象」
- 阶段 2（现象具象化）：把宽泛现象 → 「什么人在什么场景下的什么差异」
- 阶段 3（变量识别）：把现象 → 「X 差异 vs Y 差异」的可观察对子
- 阶段 4（可研究性检查）：逼学生想清楚「如果假设错了会观察到什么」
- 阶段 5（问题陈述）：把候选问题 → 标准句式「在[人群]中，[X]是否影响[Y]？」

# 几个范例

学生：「我想研究手机依赖。」
你（差）：手机依赖是个值得研究的话题，建议从屏幕时间和心理健康入手……（错：陈述句+给答案）
你（对）：「手机依赖」具体指什么——刷停不下来？还是注意力被打断？

学生：「我想研究焦虑。」
你（差）：焦虑分几种类型，特质焦虑和状态焦虑都可以研究。（错：陈述句）
你（对）：是哪种人的焦虑让你想研究？大学生？还是某个特殊群体？
"""


def _funnel_stage_focus(stage: int) -> str:
    """根据阶段返回当下需要逼出的核心问题。"""
    focus = {
        1: "把抽象兴趣具体化为「让你不爽/困惑的现象」",
        2: "把宽泛现象切成「什么人 + 什么场景 + 什么差异」",
        3: "从现象提炼出「X 差异 → Y 差异」的可观察变量对",
        4: "逼出「如果假设错了，会观察到什么」的可证伪条件",
        5: "把候选问题收敛到「在[人群]中，[X]是否影响[Y]？」标准句式",
    }
    return focus.get(stage, "推进当前阶段的关键判断")


def build_tutor_system_prompt(ctx: TutorContext, *, has_result: bool = True) -> str:
    """注入研究上下文，返回完整的 system prompt。

    v3.2：当 ctx.phase == "funnel" 时切换为苏格拉底反问 prompt。
    """
    if ctx.phase == "funnel":
        parts = [FUNNEL_BASE_PROMPT, ""]
        parts.append("# 当前阶段")
        parts.append(f"- 阶段 {ctx.funnel_stage}：{_funnel_stage_focus(ctx.funnel_stage)}")
        # v3.3: 注入已覆盖话题，防止退行和重复
        if ctx.asked_themes:
            parts.append("")
            parts.append("# 已覆盖的话题（不要再问，也不要退回到这些）")
            for t in ctx.asked_themes[-8:]:
                parts.append(f"- {t}")
        parts.append("")
        parts.append("# 现在请反问学生（仅 1-2 个问号句，每句 ≤80 字）。")
        parts.append("如果上述话题已覆盖，请提出尚未触及的角度。")
        return "\n".join(parts)

    parts = [TUTOR_BASE_PROMPT]
    parts.append("")
    parts.append("# 学生当前研究上下文")
    parts.append("")

    if ctx.test_name_zh or ctx.test_type:
        parts.append(f"- **统计方法**：{ctx.test_name_zh or ctx.test_type}")
    if ctx.sample_size:
        parts.append(f"- **样本量**：n = {ctx.sample_size}")
    if ctx.dv:
        parts.append(f"- **因变量**：{ctx.dv}")
    if ctx.iv:
        parts.append(f"- **自变量/分组变量**：{ctx.iv}")

    if has_result:
        parts.append("")
        parts.append("# 学生当前的分析结果")
        parts.append("")
        if ctx.p_value is not None:
            sig = "显著" if ctx.p_value < 0.05 else "不显著"
            parts.append(f"- **p 值**：p = {ctx.p_value:.4f}（{sig}）")
        if ctx.effect_size is not None:
            es_name = ctx.effect_size_name or "效应量"
            parts.append(f"- **效应量**：{es_name} = {ctx.effect_size:.3f}")
        for k, v in ctx.extra_stats.items():
            parts.append(f"- **{k}**：{v}")

    parts.append("")
    parts.append("# 请基于以上信息回答学生的问题")
    parts.append(
        "如果学生的问题需要的信息你没有（如「我的方差齐性怎么样？」"
        "但 ctx 里没给 Levene 结果），请明确说「这个信息我看不到，"
        "你能告诉我吗？」，而不是猜测。"
    )

    return "\n".join(parts)


def build_tutor_messages(
    system_prompt: str,
    history: List[ChatMessage],
    new_user_msg: str,
    *,
    history_limit: int = 10,
) -> List[Dict[str, str]]:
    """构造 OpenAI 兼容的 messages 列表。

    Args:
        system_prompt: 已构造好的系统提示
        history: 对话历史（不含本轮新消息）
        new_user_msg: 学生本轮提问
        history_limit: 保留最近 N 轮（避免 token 超限）

    Returns:
        [{"role": "system", "content": ...}, {"role": "user/assistant", ...}, ...]
    """
    messages = [{"role": "system", "content": system_prompt}]
    # 截取最近 N 条
    recent = history[-history_limit:] if len(history) > history_limit else list(history)
    for msg in recent:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": new_user_msg})
    return messages


# --------------------------------------------------------------------------- #
# LLM 调用（ollama / openai 兼容）
# --------------------------------------------------------------------------- #

class TutorAPIError(RuntimeError):
    """AI 助教调用失败的友好异常。"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _openai_chat_url(base_url: str) -> str:
    """拼 OpenAI 兼容的 chat/completions 端点，幂等处理已含 /v1 的 base_url。

    .env.local 里四组 base_url 均以 ``/v1`` 结尾（与 D:\\code 协作系统约定一致），
    若直接再拼 ``/v1/chat/completions`` 会得到 ``/v1/v1/...`` → 404。
    本函数确保最终恰好一个 ``/v1``，无论 base_url 是否自带。
    """
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")].rstrip("/")
    return f"{base}/v1/chat/completions"


def chat_with_tutor(
    messages: List[Dict[str, str]],
    *,
    provider: str,
    base_url: str,
    api_key: str = "",
    model: str = "",
    temperature: float = 0.5,
    timeout: int = 60,
    requests_module=None,
) -> str:
    """统一调 LLM，返回 assistant 的回复内容。

    Args:
        provider: "ollama" 或 OpenAI 兼容的 provider 名（"deepseek" / "zhipu" / "openai" 等）
        base_url: 提供商的 base URL
        api_key: 非 ollama 时必填
        model: 模型名
        requests_module: 可注入的 requests 模块（测试用）

    Raises:
        TutorAPIError: HTTP 错误或返回格式异常
    """
    if requests_module is None:
        import requests as requests_module

    if provider == "ollama":
        url = f"{base_url.rstrip('/')}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        resp = requests_module.post(url, json=payload, timeout=timeout)
        if resp.status_code != 200:
            raise TutorAPIError(
                f"Ollama 服务返回 {resp.status_code}：{_safe_text(resp)}",
                status_code=resp.status_code,
            )
        try:
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            raise TutorAPIError(f"Ollama 返回格式异常：{e}")

    # OpenAI 兼容
    url = _openai_chat_url(base_url)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    resp = requests_module.post(url, json=payload, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise TutorAPIError(
            f"AI 服务返回 {resp.status_code}：{_safe_text(resp)}",
            status_code=resp.status_code,
        )
    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        raise TutorAPIError(f"AI 返回格式异常：{e}")


def _safe_text(resp) -> str:
    try:
        text = resp.text
        return text[:200] if text else ""
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
# v3.6 流式调用
# --------------------------------------------------------------------------- #

def chat_with_tutor_stream(
    messages: List[Dict[str, str]],
    *,
    provider: str,
    base_url: str,
    api_key: str = "",
    model: str = "",
    temperature: float = 0.5,
    timeout: int = 60,
    requests_module=None,
):
    """流式调用 LLM，逐块 yield 文本片段。

    支持：
    - ollama: /api/chat 默认 stream，返回 ndjson
    - OpenAI 兼容：stream=True 返回 SSE `data: {...}\\n\\n`

    若底层不支持流式或解析失败，则回退到一次性调用并 yield 整段（generator 兼容）。
    """
    if requests_module is None:
        import requests as requests_module

    if provider == "ollama":
        url = f"{base_url.rstrip('/')}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        try:
            resp = requests_module.post(url, json=payload, timeout=timeout, stream=True)
            if resp.status_code != 200:
                raise TutorAPIError(
                    f"Ollama 服务返回 {resp.status_code}：{_safe_text(resp)}",
                    status_code=resp.status_code,
                )
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    if isinstance(line, bytes):
                        line = line.decode("utf-8", errors="ignore")
                    obj = json.loads(line)
                    chunk = obj.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if obj.get("done"):
                        break
                except (json.JSONDecodeError, AttributeError):
                    continue
        except (TutorAPIError, Exception) as exc:
            # 流式失败 → 回退一次性调用
            full = chat_with_tutor(
                messages, provider=provider, base_url=base_url,
                api_key=api_key, model=model, temperature=temperature,
                timeout=timeout, requests_module=requests_module,
            )
            if full:
                yield full
        return

    # OpenAI 兼容
    url = _openai_chat_url(base_url)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    try:
        resp = requests_module.post(url, json=payload, headers=headers, timeout=timeout, stream=True)
        if resp.status_code != 200:
            raise TutorAPIError(
                f"AI 服务返回 {resp.status_code}：{_safe_text(resp)}",
                status_code=resp.status_code,
            )
        for line in resp.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="ignore")
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                obj = json.loads(data_str)
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                chunk = delta.get("content", "")
                if chunk:
                    yield chunk
            except json.JSONDecodeError:
                continue
    except (TutorAPIError, Exception):
        # 回退一次性
        full = chat_with_tutor(
            messages, provider=provider, base_url=base_url,
            api_key=api_key, model=model, temperature=temperature,
            timeout=timeout, requests_module=requests_module,
        )
        if full:
            yield full


# --------------------------------------------------------------------------- #
# 上下文构造工具（从 wizard 的 output / ctx / plan 抽取）
# --------------------------------------------------------------------------- #

def context_from_analysis(output: dict, ctx: dict) -> TutorContext:
    """从 wizard 的 output + wizard_results_context 提炼 TutorContext。"""
    if not output:
        return TutorContext()

    result = output.get("result")
    test_type = ctx.get("test_type") or output.get("test_type", "")

    p_val = output.get("p_value")
    if p_val is None and result is not None:
        p_val = getattr(result, "p_value", None)

    es = output.get("effect_size")
    if es is None and result is not None:
        es = getattr(result, "effect_size", None)

    es_name = output.get("effect_size_name", "")
    if not es_name and result is not None:
        es_name = getattr(result, "effect_size_name", "")

    extra: Dict[str, Any] = {}
    if result is not None:
        for attr in ("t_statistic", "df", "f_statistic", "chi_sq"):
            val = getattr(result, attr, None)
            if val is not None:
                extra[attr] = round(float(val), 3) if isinstance(val, (int, float)) else val
        eq = getattr(result, "assumption_equal_var", None)
        if isinstance(eq, dict):
            extra["Levene 方差齐性"] = (
                "通过" if eq.get("passed") else "未通过"
            ) + f"（p={eq.get('p_value', '—')}）"

    return TutorContext(
        test_type=test_type,
        test_name_zh=ctx.get("test_name_zh") or output.get("test_name_zh", ""),
        sample_size=ctx.get("sample_size", 0) or 0,
        dv=ctx.get("dv", "") or "",
        iv=ctx.get("iv", "") or "",
        p_value=float(p_val) if isinstance(p_val, (int, float)) else None,
        effect_size=float(es) if isinstance(es, (int, float)) else None,
        effect_size_name=es_name,
        extra_stats=extra,
    )


# --------------------------------------------------------------------------- #
# 推荐问题（无对话历史时给本科生灵感）
# --------------------------------------------------------------------------- #

SUGGESTED_QUESTIONS_BY_CATEGORY = {
    "method_choice": [
        "为什么我的研究适合用这个方法？",
        "如果我换一个方法（比如非参数检验），结果会更可信吗？",
    ],
    "effect_size": [
        "我的效应量算大算小？这个数字背后是什么意思？",
        "效应量和 p 值哪个更重要？答辩老师会怎么问？",
    ],
    "limitations": [
        "我的研究有哪些局限？怎么在论文里写得既诚实又不显得弱？",
        "样本量这么少，结果还能信吗？",
    ],
    "next_steps": [
        "下一步如果要继续研究，建议做什么？",
        "我的结果不显著，论文怎么写才不会被批？",
    ],
    "defense": [
        "答辩老师最可能挑刺哪里？",
        "如果有人质疑因果推断，我怎么回应？",
    ],
}


def get_suggested_questions(test_type: str = "") -> List[str]:
    """根据检验类型返回 5-6 条推荐问题。"""
    base: List[str] = []
    base.extend(SUGGESTED_QUESTIONS_BY_CATEGORY["method_choice"][:1])
    base.extend(SUGGESTED_QUESTIONS_BY_CATEGORY["effect_size"][:1])
    base.extend(SUGGESTED_QUESTIONS_BY_CATEGORY["limitations"][:1])
    base.extend(SUGGESTED_QUESTIONS_BY_CATEGORY["defense"][:1])
    base.extend(SUGGESTED_QUESTIONS_BY_CATEGORY["next_steps"][:1])
    return base
