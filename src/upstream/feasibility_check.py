"""可研究性检查（v3.3 完整 4 项：可证伪 + 可测量 + 可操作 + 有意义）。

- 可证伪：仅记录学生回答，不打分（v3.2）
- 可测量：接 construct_kb established_scales（v3.2）
- 可操作：v3.3 新增，关键词触发高门槛资源警告 + 替代方案
- 有意义：v3.3 新增，LLM 生成 2-3 个反思问题（不打分，不阻塞）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 可证伪（仅记录，不打分）
# ---------------------------------------------------------------------------

def check_falsifiability(user_answer: str) -> Dict[str, Any]:
    """记录学生对「如果假设错了会观察到什么」的回答。

    设计原则：不主动判定对错（这是 LLM 反问的事），只做最弱的形式判断：
    - 空回答 → 警告
    - 含否定词（"不"/"无"/"反向"）→ 视为有效作答
    """
    answer = (user_answer or "").strip()
    if not answer:
        return {
            "answered": False,
            "raw": "",
            "warning": "未填写——请尝试想象「如果你的假设错了，数据会长什么样？」",
        }
    has_negation = any(token in answer for token in ["不", "无", "没有", "反向", "相反"])
    return {
        "answered": True,
        "raw": answer,
        "has_negation": has_negation,
        "warning": "" if has_negation else
                    "回答中没看到否定情形——再想想，什么样的结果会让你说「我错了」？",
    }


# ---------------------------------------------------------------------------
# 可测量（依赖 construct_kb 的 established_scales）
# ---------------------------------------------------------------------------

def check_measurability(
    candidate_vars: Dict[str, Any],
    constructs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """检查 candidate_vars 中的变量是否对应 construct_kb 中有成熟量表的构念。

    Args:
        candidate_vars: AnalysisPlan schema 字段（dependent_vars/independent_vars/...）
        constructs: 可注入的构念库（默认从 construct_kb 加载）

    Returns:
        {
            "all_measurable": bool,
            "results": [{"variable": str, "matched_construct": str|None,
                         "scales": [str], "warning": str}],
        }
    """
    if constructs is None:
        try:
            from src.questionnaire.construct_kb import CONSTRUCTS
            constructs = CONSTRUCTS
        except Exception:
            constructs = {}

    vars_to_check: List[str] = []
    if isinstance(candidate_vars, dict):
        vars_to_check.extend(candidate_vars.get("dependent_vars", []) or [])
        vars_to_check.extend(candidate_vars.get("independent_vars", []) or [])
        gv = candidate_vars.get("grouping_var")
        if gv and gv not in vars_to_check:
            vars_to_check.append(gv)

    if not vars_to_check:
        return {
            "all_measurable": False,
            "results": [],
            "warning": "未识别到候选变量——请先回到阶段 3 完成变量识别。",
        }

    results: List[Dict[str, Any]] = []
    for var in vars_to_check:
        if not var:
            continue
        construct_name, scales = _match_construct(var, constructs)
        if construct_name and scales:
            results.append({
                "variable": var,
                "matched_construct": construct_name,
                "scales": scales[:3],     # 只展示前 3 个量表
                "warning": "",
            })
        elif construct_name:
            results.append({
                "variable": var,
                "matched_construct": construct_name,
                "scales": [],
                "warning": f"匹配到构念「{construct_name}」但无成熟量表，需自编或换变量。",
            })
        else:
            results.append({
                "variable": var,
                "matched_construct": None,
                "scales": [],
                "warning": f"「{var}」未匹配到 construct_kb 中的成熟构念，"
                            f"请检查命名或考虑替换。",
            })

    all_measurable = all(r["scales"] for r in results)
    return {
        "all_measurable": all_measurable,
        "results": results,
    }


def _match_construct(
    variable_name: str,
    constructs: Dict[str, Any],
) -> tuple[Optional[str], List[str]]:
    """简单字符串匹配：精确名 → 包含关系。返回 (construct_name, scales)。"""
    var = (variable_name or "").strip().lower()
    if not var:
        return None, []

    # 精确匹配 name_zh / name_en
    for key, info in constructs.items():
        if key.lower() == var or info.get("name_zh", "").lower() == var \
           or info.get("name_en", "").lower() == var:
            return key, list(info.get("established_scales", []) or [])

    # 包含匹配（变量名含构念名 或 反之）
    for key, info in constructs.items():
        zh = info.get("name_zh", "").lower()
        if zh and (zh in var or var in zh):
            return key, list(info.get("established_scales", []) or [])

    return None, []


# ---------------------------------------------------------------------------
# v3.3 可操作检查（资源依赖 + 伦理风险）
# ---------------------------------------------------------------------------

@dataclass
class OperabilityResult:
    is_feasible: bool                              # 本科可执行？
    concerns: List[Dict[str, str]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    # v3.4: 时间预算估算（仅在 is_feasible=True 时填充）
    time_budget: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "is_feasible": self.is_feasible,
            "concerns": list(self.concerns),
            "suggestions": list(self.suggestions),
            "time_budget": dict(self.time_budget) if self.time_budget else None,
        }


# v3.4 时间预算关键词库
_DESIGN_KEYWORDS = {
    "experiment": ["实验", "操纵", "随机分配", "对照组", "前后测", "组间设计", "组内设计",
                   "PsychoPy", "n-back", "刺激"],
    "survey":     ["问卷", "量表", "横断面", "调查", "自评", "他评", "问卷法"],
}


def _estimate_time_budget(research_q: str, candidate_vars: Dict[str, Any]) -> Dict[str, Any]:
    """估算研究类型与时间预算（仅可行场景下调用）。"""
    blob = (research_q or "")
    if isinstance(candidate_vars, dict):
        for key in ("dependent_vars", "independent_vars", "covariates"):
            for v in candidate_vars.get(key, []) or []:
                blob += " " + str(v)
        gv = candidate_vars.get("grouping_var")
        if gv:
            blob += " " + str(gv)
    blob_lower = blob.lower()

    is_experiment = any(kw in blob_lower for kw in _DESIGN_KEYWORDS["experiment"])
    is_survey = any(kw in blob_lower for kw in _DESIGN_KEYWORDS["survey"])

    if is_experiment:
        return {
            "design_type": "experiment",
            "design_label": "实验研究（行为实验）",
            "weeks_min": 8,
            "weeks_max": 12,
            "suggestion": "建议预留 8-12 周，含预实验、正式实验、数据分析。",
            "breakdown": [
                "1-2 周：伦理审批 + 实验程序确定",
                "1 周：预实验（5-10 人）+ 调整",
                "3-4 周：正式实验（含被试招募）",
                "2-3 周：数据清洗与分析",
                "1-2 周：结果解读与论文撰写",
            ],
        }
    if is_survey:
        return {
            "design_type": "survey",
            "design_label": "横断面问卷研究",
            "weeks_min": 4,
            "weeks_max": 8,
            "suggestion": "建议预留 4-8 周，含伦理审批、数据收集、分析。",
            "breakdown": [
                "1 周：伦理审批 + 量表组装",
                "2-3 周：发放问卷 + 数据收集（线上/线下）",
                "1-2 周：数据清洗 + 分析",
                "1-2 周：结果解读与论文撰写",
            ],
        }
    # 不能确定 → 给保守估算
    return {
        "design_type": "unknown",
        "design_label": "研究类型暂不明确",
        "weeks_min": 6,
        "weeks_max": 10,
        "suggestion": "暂未识别明确的研究类型；按一般本科论文经验，建议预留 6-10 周。",
        "breakdown": [
            "请在阶段 3-4 明确研究设计后获得更精准的估算",
        ],
    }


# 高门槛资源关键词（独立维护，便于扩展）
HIGH_BARRIER_KEYWORDS: Dict[str, Dict[str, str]] = {
    # 神经成像（设备成本+伦理审批）
    "fMRI":      {"category": "neuroimaging", "alt": "用 PsychoPy 行为实验或问卷量表替代"},
    "MRI":       {"category": "neuroimaging", "alt": "用行为实验或问卷代替脑成像"},
    "脑成像":     {"category": "neuroimaging", "alt": "用行为指标（反应时/正确率）替代"},
    "脑电":      {"category": "neuroimaging", "alt": "用反应时任务替代 ERP"},
    "EEG":       {"category": "neuroimaging", "alt": "用行为反应时替代 ERP"},
    "ERP":       {"category": "neuroimaging", "alt": "用行为反应时替代 ERP"},
    "近红外":     {"category": "neuroimaging", "alt": "用行为指标替代 fNIRS"},
    "fNIRS":     {"category": "neuroimaging", "alt": "用行为指标替代 fNIRS"},
    # 眼动
    "眼动":      {"category": "eye_tracking", "alt": "用注视/选择任务的反应时替代眼动"},
    "Tobii":     {"category": "eye_tracking", "alt": "用反应时任务替代眼动"},
    # 纵向追踪（时间成本）
    "纵向追踪 6 个月": {"category": "longitudinal", "alt": "改为横断面研究或 2 时点短期追踪"},
    "纵向追踪 1 年":   {"category": "longitudinal", "alt": "改为横断面或 2-3 时点短期追踪"},
    "追踪 2 年":      {"category": "longitudinal", "alt": "改为横断面研究"},
    "追踪 3 年":      {"category": "longitudinal", "alt": "改为横断面研究"},
    "纵向研究":       {"category": "longitudinal", "alt": "本科论文一般做横断面，建议改为相关研究"},
    # 临床患者群体（伦理审批+被试招募）
    "抑郁症患者":     {"category": "clinical_population", "alt": "改用「抑郁倾向较高的普通学生」（自报量表）"},
    "焦虑症患者":     {"category": "clinical_population", "alt": "改用「特质焦虑较高的普通学生」"},
    "精神分裂":      {"category": "clinical_population", "alt": "本科生不宜研究此群体，建议改主题"},
    "PTSD 患者":     {"category": "clinical_population", "alt": "改用「亲历过应激事件的普通群体」"},
    "临床诊断":      {"category": "clinical_population", "alt": "改用自报量表分代替临床诊断"},
    # 儿童群体（伦理审批+学校配合）
    "婴幼儿":       {"category": "minors", "alt": "改为大学生或成年人样本"},
    "学龄前儿童":    {"category": "minors", "alt": "改为大学生或成年人样本（儿童被试需家长知情同意+学校审批）"},
    "幼儿园":       {"category": "minors", "alt": "改为大学生群体（儿童被试需层层伦理审批）"},
}

_CATEGORY_LABEL = {
    "neuroimaging":         "神经成像设备",
    "eye_tracking":         "眼动设备",
    "longitudinal":         "长周期追踪",
    "clinical_population":  "临床患者群体",
    "minors":               "未成年人/儿童群体",
}


def check_operability(
    research_q: str,
    candidate_vars: Optional[Dict[str, Any]] = None,
    *,
    use_llm_check: bool = True,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
) -> OperabilityResult:
    """检查研究是否本科生可执行（避免高门槛资源/伦理风险）。

    v3.6: 静态关键词层未命中时，调 LLM 网关补充检测（VR/AR/EMA 等新型设计）。

    Args:
        research_q: 研究问题文本
        candidate_vars: 候选变量字典
        use_llm_check: 静态层未命中时是否启用 LLM 检查
        llm_config: 注入用 LLM 配置（测试）
        requests_module: 注入 requests（测试）

    Returns:
        OperabilityResult.is_feasible=True 当无任何高门槛关键词/LLM 命中。
    """
    blob = (research_q or "").strip()
    if isinstance(candidate_vars, dict):
        for key in ("dependent_vars", "independent_vars", "covariates"):
            for v in candidate_vars.get(key, []) or []:
                blob += " " + str(v)
        gv = candidate_vars.get("grouping_var")
        if gv:
            blob += " " + str(gv)

    if not blob.strip():
        return OperabilityResult(is_feasible=True)

    concerns: List[Dict[str, str]] = []
    suggestions: List[str] = []
    seen_categories: set = set()

    blob_lower = blob.lower()
    for kw, meta in HIGH_BARRIER_KEYWORDS.items():
        if kw.lower() in blob_lower:
            cat = meta["category"]
            label = _CATEGORY_LABEL.get(cat, cat)
            concerns.append({
                "keyword": kw,
                "category": cat,
                "label": label,
                "issue": f"研究涉及「{kw}」（{label}），本科论文资源/时间通常不足",
            })
            if cat not in seen_categories:
                suggestions.append(meta["alt"])
                seen_categories.add(cat)

    # v3.6 LLM 辅助检测（仅静态层未命中时）
    if use_llm_check and not concerns:
        llm_concern = _llm_operability_check(
            research_q, candidate_vars or {},
            llm_config=llm_config,
            requests_module=requests_module,
        )
        if llm_concern:
            concerns.append({
                "keyword": llm_concern.get("source_term", "LLM 识别"),
                "category": "llm_detected",
                "label": "LLM 识别的高门槛设计",
                "issue": llm_concern.get("reason", ""),
            })
            if llm_concern.get("suggestion"):
                suggestions.append(llm_concern["suggestion"])

    is_feasible = (not concerns)
    time_budget = _estimate_time_budget(research_q, candidate_vars or {}) \
        if is_feasible else None
    return OperabilityResult(
        is_feasible=is_feasible,
        concerns=concerns,
        suggestions=suggestions,
        time_budget=time_budget,
    )


# ---------------------------------------------------------------------------
# v3.6 LLM 辅助检测（带 session 缓存避免反复调用）
# ---------------------------------------------------------------------------

_OPERABILITY_LLM_PROMPT = """\
你是研究方法学评审。判断下面的研究设计是否需要本科生难以获取的特殊设备/软件/群体。

需要警惕的高门槛资源（含但不限于）：
- 神经成像（fMRI/EEG/fNIRS）
- 眼动仪（Tobii/Eyelink）
- VR/AR 设备
- EMA（生态瞬时评估）需要专门 app
- 大型纵向追踪（≥6 月）
- 临床患者群体（需医院合作）
- 未成年人/儿童（需 IRB+学校配合）
- 特殊人群（残障/罕见病/精神疾病）
- 行为编码（需多名编码员训练）

输出严格 JSON（不要 markdown）：
{{
  "is_high_barrier": true/false,
  "reason": "<≤60 字简短理由；非高门槛时填空字符串>",
  "suggestion": "<若高门槛，给出本科生可行的替代方案 ≤80 字>",
  "source_term": "<触发判断的关键词>"
}}
"""


def _llm_operability_check(
    research_q: str,
    candidate_vars: Dict[str, Any],
    *,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
) -> Optional[Dict[str, Any]]:
    """LLM 检查；不可用/低门槛时返回 None。带 session_state 缓存。"""
    blob = (research_q or "").strip()
    if isinstance(candidate_vars, dict):
        for key in ("dependent_vars", "independent_vars", "covariates"):
            for v in candidate_vars.get(key, []) or []:
                blob += " " + str(v)

    if not blob.strip():
        return None

    # session 缓存
    cache_key = blob.strip().lower()[:200]
    try:
        import streamlit as st
        cache = st.session_state.get("_operability_llm_cache")
        if not isinstance(cache, dict):
            cache = {}
            st.session_state["_operability_llm_cache"] = cache
        if cache_key in cache:
            return cache[cache_key]
    except Exception:
        cache = None

    try:
        from src.llm_gateway import LLMUnavailableError, llm_chat
        user_msg = f"研究问题：{research_q}\n候选变量：{candidate_vars}"
        response = llm_chat(
            [{"role": "system", "content": _OPERABILITY_LLM_PROMPT},
              {"role": "user", "content": user_msg}],
            temperature=0.2,
            llm_config=llm_config,
            requests_module=requests_module,
            retries=0,
        )
        if not response.ok:
            return None

        # 解析 JSON
        import json
        text = response.content.strip()
        if text.startswith("```"):
            first_nl = text.find("\n")
            text = text[first_nl + 1:] if first_nl > 0 else text
            if text.endswith("```"):
                text = text[: -3]
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        parsed = json.loads(text[start: end + 1])

        result = None
        if parsed.get("is_high_barrier"):
            result = {
                "reason": parsed.get("reason", "")[:200],
                "suggestion": parsed.get("suggestion", "")[:200],
                "source_term": parsed.get("source_term", "")[:50],
            }

        # 写缓存
        if cache is not None:
            cache[cache_key] = result

        return result
    except (LLMUnavailableError, Exception):
        return None


# ---------------------------------------------------------------------------
# v3.3 有意义反思（不打分，只生成反思问题）
# ---------------------------------------------------------------------------

# 默认反思问题（LLM 不可用时使用）
_DEFAULT_REFLECTION_QUESTIONS = [
    "如果你的假设被验证，对真实生活有什么改变？",
    "已有研究中类似问题的结论是什么？你的研究在哪一点上有所不同？",
    "这个问题对你的目标领域（学术/实务）有什么贡献？",
]


def suggest_significance_reflection(
    research_q: str,
    *,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
) -> Dict[str, Any]:
    """生成 2-3 个「有意义性」反思问题。

    不打分、不阻塞——只是软性提示。LLM 可用时根据具体研究问题定制；
    不可用时返回默认问题。

    Returns:
        {"questions": [...], "is_llm_generated": bool}
    """
    rq = (research_q or "").strip()
    if not rq:
        return {"questions": list(_DEFAULT_REFLECTION_QUESTIONS), "is_llm_generated": False}

    # 没 LLM 配置 → 直接默认
    if not llm_config or not (llm_config.get("api_key") or llm_config.get("provider") == "ollama"):
        return {"questions": list(_DEFAULT_REFLECTION_QUESTIONS), "is_llm_generated": False}

    # 有 LLM → 通过网关调用
    try:
        from src.llm_gateway import LLMUnavailableError, llm_chat
        from src.paper_writer.ai_tutor import build_tutor_messages

        sys_prompt = (
            "你是研究方法导师。根据下面学生的研究问题，生成 3 个"
            "「有意义性反思」问题——每个问题以问号结尾，每条 ≤50 字，"
            "目的是让学生自己思考研究价值，不要给答案。\n"
            "输出格式：每行一条，无编号无前缀。"
        )
        msgs = build_tutor_messages(sys_prompt, [], rq)
        response = llm_chat(
            msgs,
            temperature=0.4,
            llm_config=llm_config,
            requests_module=requests_module,
            retries=0,
        )
        raw = response.content if response.ok else ""
        lines = [
            l.strip().lstrip("-").lstrip("•").strip()
            for l in (raw or "").split("\n")
            if l.strip()
        ]
        questions = [l for l in lines if len(l) >= 5 and ("？" in l or "?" in l)]
        if 2 <= len(questions) <= 5:
            return {"questions": questions[:3], "is_llm_generated": True}
    except (LLMUnavailableError, Exception):
        pass

    return {"questions": list(_DEFAULT_REFLECTION_QUESTIONS), "is_llm_generated": False}
