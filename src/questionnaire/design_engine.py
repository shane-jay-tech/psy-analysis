"""问卷设计核心引擎：解析研究问题 → 匹配构念 → 生成问卷"""

import jieba
from typing import Any, Dict, List, Optional, Tuple

from .construct_kb import CONSTRUCTS, CONSTRUCT_KEYWORDS, DOMAIN_KEYWORDS
from .construct_kb_extended import EXTENDED_CONSTRUCTS
from .item_templates import (
    get_recommended_template,
    generate_items_for_dimension,
    ALL_TEMPLATES,
)
from .scale_guidance import (
    recommend_scale_points,
    get_anchor_labels,
    recommend_scoring,
    recommend_item_count,
    reverse_item_ratio,
)
from .psychometrics import generate_psychometric_report


def design_questionnaire(
    research_question: str,
    llm_config: Optional[Dict] = None,
    use_academic_sources: bool = True,
    use_intent_chain: bool = True,
) -> Dict:
    """
    主入口：根据研究问题设计问卷。

    参数：
        research_question: 用户的研究问题（中文）
        llm_config: LLM配置 dict，包含 api_key, base_url, model 等。
                    若为 None 或无 api_key，使用内置关键词匹配引擎。
        use_academic_sources: 是否查询真实学术文献库以增强问卷的学术性和标准性。
                             默认开启，会查询 Crossref + 内置KB。

    返回：
    {
        "research_question": str,
        "matched_construct": dict | None,
        "construct_name": str,
        "is_exact_match": bool,
        "dimensions_used": list,
        "template_used": dict,
        "scale_config": dict,
        "items": list,
        "instructions": str,
        "scoring": str,
        "psychometrics": dict,
        "academic_enrichment": dict | None,  # 学术文献增强数据
        "llm_used": bool,
    }
    """
    question = research_question.strip()

    # --- LLM 路径 ---
    if llm_config and llm_config.get("api_key"):
        try:
            from .llm_engine import design_questionnaire_llm, LLMEngineError
            result = design_questionnaire_llm(
                research_question=question,
                api_key=llm_config["api_key"],
                base_url=llm_config.get("base_url", ""),
                model=llm_config.get("model", "deepseek-chat"),
                temperature=llm_config.get("temperature", 0.3),
                max_tokens=llm_config.get("max_tokens", 4096),
                timeout=llm_config.get("timeout", 60),
            )
            result["llm_used"] = True
            return result
        except LLMEngineError as e:
            import streamlit as st
            st.warning(f"⚠ LLM 调用失败（{e}），已自动回退到关键词匹配引擎。")
        except Exception as e:
            import streamlit as st
            st.warning(f"⚠ LLM 出现未知错误（{e}），已自动回退到关键词匹配引擎。")

    # --- 关键词匹配路径（原有逻辑） ---

    # Step 1: 分词
    words = list(jieba.cut(question))
    words = [w.strip() for w in words if len(w.strip()) >= 2]

    # Step 2: 匹配构念
    construct, match_info = _match_construct(
        words, question,
        use_chain=use_intent_chain,
        llm_config=llm_config,
    )

    # Step 3: 选择题型模板
    if construct:
        template = get_recommended_template(construct.get("domain", ""))
    else:
        template = ALL_TEMPLATES["likert_agreement"]

    # Step 4: 确定维度
    if construct:
        dimensions = construct.get("dimensions", [])
        construct_name = construct["name_zh"]
    else:
        # 通用构念：从问题推断
        dimensions, construct_name = _infer_dimensions(words, question, match_info.get("domain", ""))
        construct = {
            "name_zh": construct_name,
            "domain": match_info.get("domain", "其他"),
            "definition": f"自定义构念：{construct_name}",
            "dimensions": dimensions,
            "established_scales": [],
            "references": [],
        }

    # Step 5: 量表配置
    points = recommend_scale_points(construct)
    scale_type = "frequency" if template["name"].startswith("频率") else "agreement"
    anchors = get_anchor_labels(points, scale_type)
    item_counts = recommend_item_count(construct)

    # Step 5a: 学术文献增强（查询真实量表，优化题量/信度建议）
    academic_data = None
    if use_academic_sources and construct_name:
        try:
            from .academic_literature import get_academic_reference_for_construct
            academic_data = get_academic_reference_for_construct(
                construct_name,
                construct.get("domain", ""),
            )
            # 如果学术文献有题量数据，优先使用
            if academic_data and academic_data.get("recommended_item_count"):
                rec = academic_data["recommended_item_count"]
                item_counts["total"] = rec
                item_counts["per_dimension"] = max(2, rec // max(1, len(dimensions)))
        except Exception:
            academic_data = None

    # Step 6: 生成题目
    items = []
    domain = construct.get("domain", "")
    for dim in dimensions:
        dim_items = generate_items_for_dimension(
            dim, template, construct_name, len(items) + 1,
            domain=domain,
        )
        items.extend(dim_items)

    # 重新编号
    for i, item in enumerate(items):
        item["index"] = i + 1

    # 反向题比例
    n_reverse = sum(1 for it in items if it["reverse"])
    rev_info = reverse_item_ratio(len(items))

    # Step 7: 生成指导语和计分
    instructions = _generate_instructions(construct, template, points, anchors)
    scoring = recommend_scoring(construct, len(items), n_reverse)

    # Step 8: 信效度报告
    psych_report = generate_psychometric_report(construct, academic_data)

    return {
        "research_question": research_question,
        "matched_construct": CONSTRUCTS.get(construct_name) if construct_name in CONSTRUCTS else None,
        "construct_name": construct_name,
        "is_exact_match": match_info.get("exact", False),
        "match_reason": match_info.get("reason", ""),
        "dimensions_used": dimensions,
        "template_used": template,
        "scale_config": {
            "points": points,
            "scale_type": scale_type,
            "anchors": anchors,
            "n_items": len(items),
            "n_dimensions": len(dimensions),
            "n_reverse": n_reverse,
            "reverse_ratio": f"{rev_info['ratio']}%",
        },
        "items": items,
        "instructions": instructions,
        "scoring": scoring,
        "psychometrics": psych_report,
        "academic_enrichment": academic_data,
        "llm_used": False,
    }


def _match_construct(
    words: list,
    question: str,
    use_chain: bool = True,
    llm_config: Optional[Dict] = None,
) -> Tuple[Optional[dict], dict]:
    """
    将分词结果与构念知识库匹配。

    v2.0：优先使用意图识别链（策略模式），回退到关键词匹配。
    """
    # 优先使用意图识别链
    if use_chain:
        try:
            from .intent_recognizer import create_default_chain
            chain = create_default_chain(
                constructs=CONSTRUCTS,
                keywords=CONSTRUCT_KEYWORDS,
                extended_constructs=EXTENDED_CONSTRUCTS,
                llm_config=llm_config,
            )
            result = chain.recognize(question, words, llm_config=llm_config)
            if result.top_candidate and result.top_candidate.confidence >= 0.3:
                c = result.top_candidate
                all_constructs = {**CONSTRUCTS, **EXTENDED_CONSTRUCTS}
                construct = all_constructs.get(c.construct_name)
                source_note = {
                    "gold_standard": "（内置知识库）",
                    "keyword": "（来自自主学习知识库）",
                    "tfidf": "（语义匹配）",
                    "llm": "（LLM智能识别）",
                }.get(c.source, "")
                return construct, {
                    "exact": c.confidence >= 0.5,
                    "reason": f"{c.match_reason}{source_note}。",
                    "confidence": c.confidence,
                    "source": c.source,
                }
        except Exception:
            pass  # 回退到原有逻辑

    # 原有关键词匹配逻辑（兜底）
    # 合并所有知识库
    all_constructs = {**CONSTRUCTS, **EXTENDED_CONSTRUCTS}

    best_score = 0
    best_construct = None
    best_name = ""
    best_source = ""

    # 第一轮：计算所有构念的原始得分
    scores = {}
    for cname, keywords in CONSTRUCT_KEYWORDS.items():
        score = 0
        if cname in question:
            score += 3 + len(cname) * 0.5
        for kw in keywords:
            if kw in question:
                score += 2 + len(kw) * 0.1
            elif any(kw in w or w in kw for w in words):
                score += 1 + len(kw) * 0.05
        scores[cname] = score

    # 第二轮：当多个构念得分接近时，偏好更长的构念名（更具体）
    if scores:
        max_score = max(scores.values())
        candidates = [(name, s) for name, s in scores.items() if s >= max_score - 1.0]
        if len(candidates) > 1:
            # 按构念名长度降序，取最长（最具体）的
            candidates.sort(key=lambda x: (-len(x[0]), -x[1]))
            best_name = candidates[0][0]
            best_score = scores[best_name]
        else:
            best_name = candidates[0][0]
            best_score = candidates[0][1]

    if best_score >= 2 and best_name in all_constructs:
        construct = all_constructs[best_name]
        if best_name in EXTENDED_CONSTRUCTS:
            source_note = "（来自自主学习知识库）"
        else:
            source_note = "（内置知识库）"
        return construct, {
            "exact": True,
            "reason": f"在研究问题中识别到「{best_name}」相关关键词，匹配到已有构念知识库{source_note}。",
        }

    # 模糊匹配：尝试识别领域
    domain_scores = {}
    for domain, kws in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in question)
        if score > 0:
            domain_scores[domain] = score

    if domain_scores:
        best_domain = max(domain_scores, key=domain_scores.get)
        return None, {
            "exact": False,
            "domain": best_domain,
            "reason": f"未找到精确匹配的构念，但根据关键词判断属于「{best_domain}」领域。将基于通用测量学原则设计问卷。",
        }

    return None, {
        "exact": False,
        "domain": "其他",
        "reason": "无法明确归类到已知领域，将基于通用测量学原则设计问卷。建议进一步细化研究问题。",
    }


def _infer_dimensions(words: list, question: str, domain: str = "") -> Tuple[list, str]:
    """
    当无法匹配到已知构念时，根据领域和关键词智能推断维度结构。

    v2.0 改进：
      - 领域专用维度模板（非总是ABC认知-情感-行为三层面）
      - 维度数 2-6 个，根据构念复杂度自适应
      - 每维度题量 3-8 题，根据维度广度可调
    """
    # 提取构念名称
    construct_name = _extract_construct_name(question)

    # 根据领域选择维度模板
    if domain in _DOMAIN_DIMENSION_TEMPLATES:
        dims = _DOMAIN_DIMENSION_TEMPLATES[domain](construct_name, words, question)
    else:
        dims = _generic_dimensions(construct_name, words, question)

    return dims, construct_name or "目标构念"


def _extract_construct_name(question: str) -> str:
    """从研究问题中提取可能的构念名称"""
    for suffix in ["水平", "程度", "状况", "情况", "行为", "态度", "感受", "满意度", "能力",
                    "状态", "倾向", "意愿", "表现"]:
        idx = question.find(suffix)
        if idx > 0:
            before = question[:idx]
            for sep in ["的", "在", "对", "关于", "调查", "研究", "测量", "了解", "探究"]:
                last_sep = before.rfind(sep)
                if last_sep >= 0:
                    candidate = before[last_sep + len(sep):].strip()
                    if 2 <= len(candidate) <= 8:
                        return candidate
            candidate = before[-5:].strip() if len(before) >= 2 else question[:8]
            if len(candidate) >= 2:
                return candidate
            break

    if len(question) > 4:
        cleaned = question.replace("调查", "").replace("研究", "").replace("测量", "").replace("了解", "").strip()
        return cleaned[:12]

    return "目标构念"


# ============================================================
# 领域专用维度模板
# ============================================================

def _organization_dimensions(name: str, words: list, question: str) -> list:
    """组织行为学维度模板"""
    return [
        {"name": f"{name}的认知评价", "desc": f"对工作环境中{name}的认知判断和评价",
         "item_count": 4, "example": f"我认为自己在工作中具备较高的{name}"},
        {"name": f"{name}的情感体验", "desc": f"与{name}相关的工作情感和主观感受",
         "item_count": 4, "example": f"工作中我常体验到与{name}相关的积极情绪"},
        {"name": f"{name}的行为表现", "desc": f"与{name}相关的工作行为和应对方式",
         "item_count": 4, "example": f"面对挑战时我采取与{name}一致的行动"},
        {"name": f"{name}的动机驱动", "desc": f"驱动{name}的内在动机和外在激励因素",
         "item_count": 3, "example": f"追求{name}是驱动我努力工作的原因之一"},
    ]


def _development_dimensions(name: str, words: list, question: str) -> list:
    """发展心理学维度模板"""
    if "儿童" in question or "幼儿" in question:
        return [
            {"name": f"{name}的发展水平", "desc": f"{name}在当前发展阶段的表现水平",
             "item_count": 4},
            {"name": f"{name}的环境因素", "desc": f"影响{name}发展的家庭和学校环境因素",
             "item_count": 4},
            {"name": f"{name}的发展困难", "desc": f"{name}发展过程中遇到的困难和挑战",
             "item_count": 3},
        ]
    elif "青少年" in question or "中学生" in question:
        return [
            {"name": f"{name}的自我认知", "desc": f"青少年对自身{name}的认知和评价",
             "item_count": 4},
            {"name": f"{name}的同伴影响", "desc": f"同伴关系对{name}的影响",
             "item_count": 3},
            {"name": f"{name}的行为表现", "desc": f"{name}在日常生活中的行为表现",
             "item_count": 4},
            {"name": f"{name}的家庭支持", "desc": f"家庭环境对{name}的支持和影响",
             "item_count": 3},
        ]
    else:
        return [
            {"name": f"{name}的适应状态", "desc": f"个体在{name}方面的适应和发展水平",
             "item_count": 4},
            {"name": f"{name}的保护因素", "desc": f"有助于{name}积极发展的个人和环境因素",
             "item_count": 4},
            {"name": f"{name}的风险因素", "desc": f"阻碍{name}发展的风险因素",
             "item_count": 3},
        ]


def _cognitive_dimensions(name: str, words: list, question: str) -> list:
    """认知心理学维度模板"""
    return [
        {"name": f"{name}的基本能力", "desc": f"{name}核心能力的基线水平",
         "item_count": 5},
        {"name": f"{name}的策略运用", "desc": f"运用{name}相关策略的灵活性和有效性",
         "item_count": 4},
        {"name": f"{name}的情境影响", "desc": f"不同情境因素对{name}表现的影响",
         "item_count": 3},
    ]


def _clinical_dimensions(name: str, words: list, question: str) -> list:
    """临床与健康心理学维度模板"""
    return [
        {"name": f"{name}的核心症状/体验", "desc": f"{name}的核心心理症状或主观体验",
         "item_count": 5},
        {"name": f"{name}的功能影响", "desc": f"{name}对日常生活功能的干扰程度",
         "item_count": 4},
        {"name": f"{name}的应对方式", "desc": f"个体面对{name}时采用的应对策略",
         "item_count": 4},
        {"name": f"{name}的社会支持", "desc": f"社会支持系统对缓解{name}的作用",
         "item_count": 3},
    ]


def _social_dimensions(name: str, words: list, question: str) -> list:
    """社会心理学维度模板"""
    return [
        {"name": f"{name}的人际层面", "desc": f"在人际互动中{name}的表现和体验",
         "item_count": 4},
        {"name": f"{name}的群体层面", "desc": f"在群体情境中{name}的表现",
         "item_count": 3},
        {"name": f"{name}的自我层面", "desc": f"与{name}相关的自我认知和评价",
         "item_count": 4},
    ]


def _education_dimensions(name: str, words: list, question: str) -> list:
    """教育心理学维度模板"""
    return [
        {"name": f"{name}的动机信念", "desc": f"驱动{name}的内在动机和自我效能信念",
         "item_count": 4},
        {"name": f"{name}的策略方法", "desc": f"实现{name}所使用的学习策略和方法",
         "item_count": 4},
        {"name": f"{name}的情感体验", "desc": f"与{name}相关的学业情感体验",
         "item_count": 3},
        {"name": f"{name}的环境支持", "desc": f"教师和同伴对{name}的支持",
         "item_count": 3},
    ]


def _personality_dimensions(name: str, words: list, question: str) -> list:
    """人格领域维度模板"""
    return [
        {"name": f"{name}的内在特质", "desc": f"{name}的稳定内在倾向和特质表现",
         "item_count": 4},
        {"name": f"{name}的外在表现", "desc": f"{name}在可观察行为中的表现",
         "item_count": 4},
        {"name": f"{name}的情境变异", "desc": f"{name}在不同情境下的变化和差异",
         "item_count": 3},
    ]


# 领域→维度模板映射
_DOMAIN_DIMENSION_TEMPLATES = {
    "组织行为": _organization_dimensions,
    "发展": _development_dimensions,
    "认知": _cognitive_dimensions,
    "临床与健康": _clinical_dimensions,
    "社会心理": _social_dimensions,
    "教育心理": _education_dimensions,
    "人格": _personality_dimensions,
}


def _generic_dimensions(name: str, words: list, question: str) -> list:
    """通用维度模板（降级方案）"""
    # 尝试通过关键词判断构念的复杂度
    n_complexity = len([w for w in words if len(w) >= 2])
    if n_complexity <= 2:
        return [
            {"name": f"{name}的整体水平", "desc": f"{name}的总体状况和水平",
             "item_count": 5},
            {"name": f"{name}的影响因素", "desc": f"与{name}相关的内外部因素",
             "item_count": 4},
        ]
    elif n_complexity <= 4:
        return [
            {"name": f"{name}的认知层面", "desc": f"对{name}的认知、看法和评价",
             "item_count": 4},
            {"name": f"{name}的情感/体验层面", "desc": f"与{name}相关的情感体验和主观感受",
             "item_count": 4},
            {"name": f"{name}的行为层面", "desc": f"与{name}相关的行为表现和应对方式",
             "item_count": 4},
        ]
    else:
        return [
            {"name": f"{name}的认知评估", "desc": f"对{name}的认知和评价", "item_count": 4},
            {"name": f"{name}的情感体验", "desc": f"与{name}相关的情感", "item_count": 4},
            {"name": f"{name}的行为表现", "desc": f"与{name}相关的行为", "item_count": 4},
            {"name": f"{name}的动机因素", "desc": f"驱动{name}的动机", "item_count": 3},
            {"name": f"{name}的环境影响", "desc": f"情境因素对{name}的影响", "item_count": 3},
        ]


def _generate_instructions(
    construct: dict,
    template: dict,
    points: int,
    anchors: list,
) -> str:
    """生成问卷指导语"""
    construct_name = construct["name_zh"]
    domain = construct.get("domain", "")
    definition = construct.get("definition", "")

    # 选取定义的前半句
    short_def = definition.split("。")[0] if definition else ""
    if len(short_def) > 80:
        short_def = short_def[:80] + "..."

    anchor_text = "\n".join(f"    {a}" for a in anchors)

    return (
        f"【{construct_name}问卷】\n\n"
        f"尊敬的参与者：\n\n"
        f"感谢您参与本次研究。本问卷旨在了解您的{construct_name}状况。\n"
        f"{short_def}\n\n"
        f"填写说明：\n"
        f"1. 请仔细阅读每个题目，根据您的实际感受选择最符合的选项\n"
        f"2. 答案没有对错之分，请按真实情况作答\n"
        f"3. 本问卷采用匿名方式，您的回答将严格保密，仅用于学术研究\n"
        f"4. 每道题均为单选题，请不要漏答\n\n"
        f"评分标准：\n{anchor_text}\n\n"
        f"预计完成时间：约{max(3, len(construct.get('dimensions', [])) * 2)}分钟\n\n"
        f"请开始作答："
    )


# ===========================================================================
# Task 4: 反向题人工审阅接口
# ===========================================================================

def get_unreviewed_reverse_items(design_result: Dict) -> List[Dict]:
    """
    返回所有需要人工审阅的反向题列表（自然度<5分）。

    参数：
        design_result: design_questionnaire() 返回的完整设计结果

    返回：需要审阅的反向题列表，每项含 index, text, score, deductions, suggestion
    """
    from .item_quality import evaluate_reverse_item_naturalness

    items = design_result.get("items", [])
    unreviewed = []

    for item in items:
        if item.get("reverse", False):
            text = item.get("text", "")
            score, deductions = evaluate_reverse_item_naturalness(text)
            if score < 5.0:
                unreviewed.append({
                    "index": item.get("index", "?"),
                    "dimension": item.get("dimension", ""),
                    "text": text,
                    "naturalness_score": score,
                    "deductions": deductions,
                    "suggestion": "建议人工审阅并改写：请检查否定表达是否自然、是否可被被试准确理解。",
                })

    return unreviewed
