"""苏格拉底反问引擎：基于 ai_tutor 扩展，加输出校验 + fallback 兜底。

调用流：
1. 构造 TutorContext(phase="funnel", funnel_stage=N)
2. build_tutor_system_prompt 自动切到 FUNNEL_BASE_PROMPT
3. 注入 [学生上一轮说: ...] 提示，强化引用
4. 调 chat_with_tutor（temperature=0.3）
5. 后处理校验：必须含 ?、≤150 字、句数 ≤2
6. 校验失败 → 重试 1 次（temperature=0.2）
7. 仍失败 → fallback 模板（按阶段选）
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.paper_writer.ai_tutor import (
    ChatMessage,
    TutorAPIError,
    TutorContext,
    build_tutor_messages,
    build_tutor_system_prompt,
    chat_with_tutor,
)
from src.upstream.topic_funnel_kb import (
    get_fallback_question,
    match_examples_by_semantics,
    render_examples_for_prompt,
)


# ---------------------------------------------------------------------------
# 输出校验
# ---------------------------------------------------------------------------

# 中英文问号都接受
_QUESTION_MARK_RE = re.compile(r"[?？]")

# 用于切句：中英文标点
_SENT_SPLIT_RE = re.compile(r"[？\?！\!。\.\n]+")


def _validate_socratic_output(text: str, max_chars: int = 150, max_sentences: int = 2) -> bool:
    """校验 LLM 输出是否符合苏格拉底反问规则。

    要求：
    - 含至少一个问号（中英）
    - 总长度 ≤ max_chars
    - 句数 ≤ max_sentences
    - 不为空
    """
    if not isinstance(text, str):
        return False
    text = text.strip()
    if not text:
        return False
    if len(text) > max_chars:
        return False
    if not _QUESTION_MARK_RE.search(text):
        return False
    sentences = [s for s in _SENT_SPLIT_RE.split(text) if s.strip()]
    if len(sentences) > max_sentences:
        return False
    return True


# ---------------------------------------------------------------------------
# v3.3 退行检测 + 重复检测
# ---------------------------------------------------------------------------

# 阶段关键词指纹（用于检测反问是否退回到更早阶段）
_STAGE_FINGERPRINT: Dict[int, List[str]] = {
    1: ["为什么对", "为什么想", "感兴趣", "在意", "第一感受", "让你不爽", "让你困惑"],
    2: ["具体场景", "什么人", "什么时候", "什么情境", "具体表现", "典型场景"],
    3: ["变量", "测量", "X 越多", "Y 就越", "中介", "调节", "因变量", "自变量"],
    4: ["假设错", "证伪", "靠谱", "量表", "本科一年", "工程量", "新东西"],
    5: ["在[人群]", "标准句式", "答辩", "核心问题", "一句话回答"],
}


def _bigram_similarity(a: str, b: str) -> float:
    """字符级 bigram 最大覆盖率（max-coverage）。

    比 Jaccard 对短中文更友好：只要一方被另一方大量包含就视为相似。
    专为「反问重复检测」场景设计——子集关系应被识别为重复。
    """
    if not a or not b:
        return 0.0
    bg_a = {a[i:i+2] for i in range(max(0, len(a) - 1))}
    bg_b = {b[i:i+2] for i in range(max(0, len(b) - 1))}
    if not bg_a or not bg_b:
        return 0.0
    inter = len(bg_a & bg_b)
    cov_a = inter / len(bg_a)
    cov_b = inter / len(bg_b)
    return max(cov_a, cov_b)


# v3.4: 学生输入引用历史的标志短语（学生 quote 旧阶段不应触发退行）
_STUDENT_REFERENCE_PHRASES = [
    "正如我之前说",
    "像我在阶段",
    "如我前面提",
    "我之前提到",
    "前面我说过",
    "之前讲过",
    "前面那个",
    "上一阶段我",
    "刚才说的",
]

# v3.4: 阶段 4 学生具体分析方法关键词（保护性识别）
_METHOD_DISCUSSION_KEYWORDS = [
    "问卷", "实验", "样本量", "量表", "量化", "实验设计",
    "操纵", "对照组", "基线", "测量", "方差", "信度", "效度",
]


def _is_student_referencing_history(text: str) -> bool:
    """学生输入是否含引用历史的标志短语（用于退行检测豁免）。"""
    if not isinstance(text, str):
        return False
    return any(phrase in text for phrase in _STUDENT_REFERENCE_PHRASES)


def _is_substantive_method_discussion(text: str, current_stage: int) -> bool:
    """学生输入是否在阶段 4+ 做实质方法讨论（>100 字 + 含方法关键词）。"""
    if current_stage < 4 or not isinstance(text, str):
        return False
    if len(text) < 100:
        return False
    return any(kw in text for kw in _METHOD_DISCUSSION_KEYWORDS)


def _check_no_regression(
    new_question: str,
    current_stage: int,
    asked_themes: List[str],
    *,
    repeat_threshold: float = 0.7,
    is_from_student: bool = False,
) -> Dict[str, Any]:
    """检测反问是否退行到更早阶段或重复已问主题。

    v3.4: 加入误判保护——学生输入引用历史/具体方法讨论时跳过退行检测。
    AI 反问保留完整退行检测（is_from_student=False）。

    Args:
        new_question: 待检测的文本（AI 反问 或 学生输入）
        current_stage: 当前阶段 1-5
        asked_themes: 已问过的主题
        repeat_threshold: 重复阈值
        is_from_student: 是否来自学生（True 时启用误判保护）

    Returns:
        {"ok": bool, "reason": str, "violation": "regression"|"duplicate"|None}
    """
    if not new_question or not isinstance(new_question, str):
        return {"ok": False, "reason": "empty", "violation": None}

    # v3.4 学生侧误判保护：引用短语 / 阶段 4+ 实质方法讨论 → 跳过退行检测
    skip_regression = False
    if is_from_student:
        if _is_student_referencing_history(new_question):
            skip_regression = True
        elif _is_substantive_method_discussion(new_question, current_stage):
            skip_regression = True

    # 1) 退行检测（AI 反问 或 学生未豁免时）
    if not skip_regression:
        for stage_id, fingerprints in _STAGE_FINGERPRINT.items():
            if stage_id < current_stage - 1:
                for kw in fingerprints:
                    if kw in new_question:
                        return {
                            "ok": False,
                            "reason": f"反问含阶段 {stage_id} 关键词「{kw}」，应聚焦阶段 {current_stage}",
                            "violation": "regression",
                        }

    # 2) 重复检测：与已问主题任意条相似度 > 阈值
    for theme in (asked_themes or []):
        sim = _bigram_similarity(new_question, theme)
        if sim >= repeat_threshold:
            return {
                "ok": False,
                "reason": f"与已问主题相似度 {sim:.0%}，应换角度",
                "violation": "duplicate",
            }

    return {"ok": True, "reason": "", "violation": None}


def extract_theme_from_question(question: str, max_len: int = 30) -> str:
    """从反问中提取核心主题词（启发式：去掉问号+前缀虚词，截短）。

    用于把 LLM 的反问压缩成 asked_themes 中的简短条目，便于后续比较。
    """
    if not question:
        return ""
    t = question.strip().rstrip("？?！!。.")
    # 去掉前缀虚词
    for prefix in ["请问", "那么", "你能", "可不可以", "可以"]:
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
    return t[:max_len]


def _truncate_to_first_questions(text: str, max_questions: int = 2) -> str:
    """从 LLM 长输出中提取前 max_questions 个问号句。"""
    if not isinstance(text, str):
        return ""
    parts = re.split(r"([?？])", text)
    pieces: List[str] = []
    buf = ""
    for chunk in parts:
        buf += chunk
        if chunk in "?？":
            pieces.append(buf.strip())
            buf = ""
            if len(pieces) >= max_questions:
                break
    return " ".join(pieces).strip()


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def ask_socratic_stream(
    stage: int,
    user_input: str,
    history: Optional[List[ChatMessage]] = None,
    *,
    llm_config: Dict[str, Any],
    requests_module: Any = None,
    history_limit: int = 6,
    topic_hint: str = "",
    asked_themes: Optional[List[str]] = None,
    inject_examples: bool = True,
    on_chunk: Optional[Any] = None,
) -> str:
    """v3.6 流式反问。逐块通过 on_chunk(chunk) 通知调用方；最终返回校验后的全文。

    若流式完成后校验不过 → 静默重试或 fallback（不再走流式 UI）。
    """
    from src.llm_gateway import LLMUnavailableError, llm_chat_stream

    history = list(history or [])
    asked_themes = list(asked_themes or [])
    ctx = TutorContext(
        phase="funnel",
        funnel_stage=stage,
        asked_themes=asked_themes,
        current_stage_progress=len(history) // 2,
    )
    sys_prompt = build_tutor_system_prompt(ctx)
    if inject_examples:
        examples = match_examples_by_semantics(user_input, top_k=2)
        ex_block = render_examples_for_prompt(examples)
        if ex_block:
            sys_prompt = sys_prompt + "\n\n" + ex_block

    prev_user = _last_user_message(history)
    prefixed = user_input
    if prev_user:
        prefixed = f"[学生上一轮说: {prev_user[:200]}]\n{user_input}"
    msgs = build_tutor_messages(sys_prompt, history, prefixed, history_limit=history_limit)

    accumulated: List[str] = []
    try:
        for chunk in llm_chat_stream(
            msgs,
            temperature=0.3,
            llm_config=llm_config,
            requests_module=requests_module,
        ):
            accumulated.append(chunk)
            if on_chunk:
                try:
                    on_chunk(chunk)
                except Exception:
                    pass
    except LLMUnavailableError:
        return get_fallback_question(stage, topic=topic_hint)

    full = "".join(accumulated).strip()
    # 校验 + 后处理
    if not _validate_socratic_output(full):
        truncated = _truncate_to_first_questions(full, max_questions=2)
        if _validate_socratic_output(truncated):
            return truncated
        # 流式回答不合格 → 走非流式同步重试一次
        return ask_socratic(
            stage, user_input, history,
            llm_config=llm_config,
            requests_module=requests_module,
            history_limit=history_limit,
            topic_hint=topic_hint,
            asked_themes=asked_themes,
            inject_examples=inject_examples,
        )

    # 退行/重复检测
    check = _check_no_regression(full, stage, asked_themes)
    if not check["ok"]:
        return ask_socratic(
            stage, user_input, history,
            llm_config=llm_config,
            requests_module=requests_module,
            history_limit=history_limit,
            topic_hint=topic_hint,
            asked_themes=asked_themes,
            inject_examples=inject_examples,
        )

    return full


def ask_socratic(
    stage: int,
    user_input: str,
    history: Optional[List[ChatMessage]] = None,
    *,
    llm_config: Dict[str, Any],
    requests_module: Any = None,
    history_limit: int = 6,
    topic_hint: str = "",
    asked_themes: Optional[List[str]] = None,
    inject_examples: bool = True,
) -> str:
    """苏格拉底反问主入口。

    Args:
        stage: 漏斗阶段 1..5
        user_input: 学生本轮输入
        history: 已有对话历史（不含本轮新消息）
        llm_config: 必须含 provider/base_url/api_key/model
        requests_module: 注入用（测试）
        history_limit: 保留最近 N 轮
        topic_hint: 用于 fallback 模板替换的话题词
        asked_themes: v3.3 已问过的反问主题（防退行+防重复）
        inject_examples: v3.3 是否在 system prompt 后注入语义匹配的范例

    Returns:
        反问字符串。LLM 失败/校验不过 → fallback 模板，永远不抛异常。
    """
    history = list(history or [])
    asked_themes = list(asked_themes or [])
    ctx = TutorContext(
        phase="funnel",
        funnel_stage=stage,
        asked_themes=asked_themes,
        current_stage_progress=len(history) // 2,
    )
    sys_prompt = build_tutor_system_prompt(ctx)

    # v3.3: 注入语义匹配范例
    if inject_examples:
        examples = match_examples_by_semantics(user_input, top_k=2)
        ex_block = render_examples_for_prompt(examples)
        if ex_block:
            sys_prompt = sys_prompt + "\n\n" + ex_block

    # 在用户输入前注入「学生上一轮说」提示，强化引用上轮表述
    prev_user = _last_user_message(history)
    prefixed = user_input
    if prev_user:
        prefixed = f"[学生上一轮说: {prev_user[:200]}]\n{user_input}"

    msgs = build_tutor_messages(sys_prompt, history, prefixed, history_limit=history_limit)

    def _accept(text: str) -> Optional[str]:
        """格式校验 + 退行/重复校验。通过则返回，否则 None。"""
        if not _validate_socratic_output(text):
            text = _truncate_to_first_questions(text, max_questions=2)
            if not _validate_socratic_output(text):
                return None
        # v3.3 退行/重复检测
        check = _check_no_regression(text, stage, asked_themes)
        if not check["ok"]:
            return None
        return text

    # 第一次尝试
    raw = _safe_chat(msgs, llm_config, requests_module, temperature=0.3)
    if raw is not None:
        accepted = _accept(raw.strip())
        if accepted is not None:
            return accepted

    # v3.3 重试时强化 prompt：加上「禁止重复」+ 已覆盖话题
    retry_prompt = sys_prompt + "\n\n# 上次输出不合格——请改换角度，禁止重复以下已问主题：\n"
    if asked_themes:
        for t in asked_themes[-5:]:
            retry_prompt += f"- {t}\n"
    retry_msgs = build_tutor_messages(retry_prompt, history, prefixed, history_limit=history_limit)

    raw2 = _safe_chat(retry_msgs, llm_config, requests_module, temperature=0.2)
    if raw2 is not None:
        accepted2 = _accept(raw2.strip())
        if accepted2 is not None:
            return accepted2

    # Fallback 模板兜底
    return get_fallback_question(stage, topic=topic_hint)


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _safe_chat(
    msgs: List[Dict[str, str]],
    llm_config: Dict[str, Any],
    requests_module: Any,
    temperature: float,
) -> Optional[str]:
    """包一层 try：失败返回 None，永不抛。

    v3.5: 通过 LLM 网关调用（gateway 内部仍委托 chat_with_tutor，行为一致）；
    保留 LLMUnavailableError 捕获作为降级入口。
    """
    try:
        from src.llm_gateway import LLMUnavailableError, llm_chat
        response = llm_chat(
            msgs,
            temperature=temperature,
            llm_config=llm_config,
            requests_module=requests_module,
            retries=0,    # 上层已有重试逻辑
        )
        if response.cancelled or not response.content:
            return None
        return response.content
    except LLMUnavailableError:
        return None
    except Exception:
        # 兜底：网关导入失败也降级（极端兼容）
        try:
            return chat_with_tutor(
                msgs,
                provider=llm_config.get("provider", ""),
                base_url=llm_config.get("base_url", ""),
                api_key=llm_config.get("api_key", ""),
                model=llm_config.get("model", ""),
                temperature=temperature,
                timeout=llm_config.get("timeout", 30),
                requests_module=requests_module,
            )
        except (TutorAPIError, Exception):
            return None


def _last_user_message(history: List[ChatMessage]) -> str:
    for msg in reversed(history):
        role = getattr(msg, "role", None) if not isinstance(msg, dict) else msg.get("role")
        content = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")
        if role == "user":
            return content or ""
    return ""
