"""题目质量检查引擎：语法检查 / 冗余检测 / 平衡性检查 / 双向陈述检测"""
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class ItemQualityReport:
    total_items: int
    passed: int
    warnings: int
    errors: int
    item_scores: List[Dict] = field(default_factory=list)
    summary: str = ""
    # v3.7.10：整问卷级警告（如注意力检测题数量不达标），不挂在单题上
    overall_warnings: List[str] = field(default_factory=list)


def check_item_quality(
    items: List[Dict],
    construct_name: str = "",
    *,
    respondent_role: str = "",
    item_subject_template: str = "",
) -> ItemQualityReport:
    """
    对生成的题目列表进行全面的质量检查。

    v3.7.10 升级：除经典 6 类外，加入抽象度/过拟合/极端词/假设句/直问构念/镜像反向题检测，
    主语一致性按 item_subject_template 检查，整问卷级警告（注意力检测题配额）写入 overall_warnings。

    Args:
        items: 题目列表
        construct_name: 构念名（用于直问构念检查）
        respondent_role: 答题人角色（informational，目前未直接使用）
        item_subject_template: 题目主语模板（如「我...」「我们公司的 X...」），用于一致性检查
    """
    item_scores = []
    total_issues = 0
    errors = 0
    warnings = 0

    # 仅对构念题进行单题检查（注意力检测题等用 overall_warnings 处理）
    construct_items_only = [it for it in items if it.get("item_type", "construct") == "construct"]

    # 预计算：按维度分组（仅构念题）
    dim_items = {}
    for item in construct_items_only:
        dim = item.get("dimension", "默认维度")
        dim_items.setdefault(dim, []).append(item)

    for item in construct_items_only:
        idx = item.get("index", "?")
        dim_name = item.get("dimension", "默认维度")
        text = item.get("text", "")

        issues = []
        score = 10  # 满分10分

        # 1. 长度检查
        char_len = len(text)
        if char_len < 5:
            issues.append({"type": "error", "check": "长度检查", "msg": f"题目过短（{char_len}字），建议≥5字"})
            score -= 3
            errors += 1
        elif char_len > 50:
            issues.append({"type": "warning", "check": "长度检查", "msg": f"题目偏长（{char_len}字），建议≤50字"})
            score -= 1
            warnings += 1
        elif char_len > 40:
            issues.append({"type": "info", "check": "长度检查", "msg": f"题目略长（{char_len}字）"})
            score -= 0.5

        # 2. 语法完整性检查
        grammar_issues = _check_grammar(text)
        for gi in grammar_issues:
            issues.append(gi)
            score -= 2
            if gi["type"] == "error":
                errors += 1
            else:
                warnings += 1

        # 3. 双重陈述检查
        double_barreled = _check_double_barreled(text)
        if double_barreled:
            issues.append({"type": "error", "check": "双向陈述检查", "msg": double_barreled})
            score -= 3
            errors += 1

        # 4. 否定词复杂度检查
        neg_issues = _check_negation(text, item.get("reverse", False))
        if neg_issues:
            issues.append({"type": "warning", "check": "否定表达检查", "msg": neg_issues})
            score -= 1
            warnings += 1

        # 5. 模糊词检查
        vague = _check_vague_words(text)
        if vague:
            issues.append({"type": "info", "check": "模糊表达检查", "msg": vague})
            score -= 0.5

        # ----- v3.7.10 新增检查 -----

        # 6. 抽象度（行为锚定缺失）
        abs_msg = _check_abstractness(text, construct_name)
        if abs_msg:
            issues.append({"type": "warning", "check": "行为锚定检查", "msg": abs_msg})
            score -= 2
            warnings += 1

        # 7. 过拟合（情境过窄）
        of_msg = _check_overfitting(text)
        if of_msg:
            issues.append({"type": "warning", "check": "过拟合检查", "msg": of_msg})
            score -= 1.5
            warnings += 1

        # 8. 极端词
        ex_msg = _check_extreme_words(text)
        if ex_msg:
            issues.append({"type": "warning", "check": "极端词检查", "msg": ex_msg})
            score -= 1
            warnings += 1

        # 9. 假设句
        hyp_msg = _check_hypothetical(text)
        if hyp_msg:
            issues.append({"type": "warning", "check": "假设句检查", "msg": hyp_msg})
            score -= 2
            warnings += 1

        # 10. 直问构念
        dc_msg = _check_direct_construct_question(text, construct_name)
        if dc_msg:
            issues.append({"type": "warning", "check": "直问构念检查", "msg": dc_msg})
            score -= 1.5
            warnings += 1

        item_scores.append({
            "index": idx,
            "dimension": dim_name,
            "text": text,
            "score": max(0, score),
            "issues": issues,
            "status": "error" if score <= 3 else ("warning" if score <= 6 else "ok"),
        })

        if issues:
            total_issues += len(issues)

    # 11. 维度内冗余检查
    redundancy_issues = _check_redundancy(dim_items)
    for ri in redundancy_issues:
        idx_a, idx_b, sim = ri
        for iscore in item_scores:
            if iscore["index"] == idx_b:
                iscore["issues"].append({
                    "type": "warning",
                    "check": "冗余检测",
                    "msg": f"与题目#{idx_a}的语义相似度过高（{sim:.0%}），建议合并或删除其一",
                })
                iscore["score"] = max(0, iscore["score"] - 2)
                iscore["status"] = "error" if iscore["score"] <= 3 else ("warning" if iscore["score"] <= 6 else "ok")
                warnings += 1

    # 12. v3.7.10：镜像反向题检查
    mirror_issues = _check_mirror_reverse(construct_items_only)
    for mi in mirror_issues:
        for iscore in item_scores:
            if iscore["index"] == mi["index"]:
                iscore["issues"].append({
                    "type": "error",
                    "check": "镜像反向题检查",
                    "msg": mi["msg"],
                })
                iscore["score"] = max(0, iscore["score"] - 3)
                iscore["status"] = "error" if iscore["score"] <= 3 else ("warning" if iscore["score"] <= 6 else "ok")
                errors += 1

    # 13. v3.7.10：题目主语一致性
    subject_issues = _check_subject_consistency(construct_items_only, item_subject_template)
    for si in subject_issues:
        for iscore in item_scores:
            if iscore["index"] == si["index"]:
                iscore["issues"].append({
                    "type": "warning",
                    "check": "主语一致性检查",
                    "msg": si["msg"],
                })
                iscore["score"] = max(0, iscore["score"] - 2)
                iscore["status"] = "error" if iscore["score"] <= 3 else ("warning" if iscore["score"] <= 6 else "ok")
                warnings += 1

    # 14. v3.7.10：整问卷级警告（注意力检测题配额）
    overall_warnings = _check_attention_check_quota(items)

    passed = sum(1 for s in item_scores if s["status"] == "ok")

    # 生成摘要
    if total_issues == 0 and not overall_warnings:
        summary = f"✅ 所有{len(construct_items_only)}道构念题质量检查通过，平均得分优秀。"
    else:
        summary = f"共{len(construct_items_only)}道构念题：{passed}道通过 / {warnings}个警告 / {errors}个错误。"
        if errors > 0:
            summary += f"\n⚠ {errors}道题存在严重问题，建议修改后再发布。"
        if overall_warnings:
            summary += "\n" + "\n".join(overall_warnings)

    return ItemQualityReport(
        total_items=len(construct_items_only),
        passed=passed,
        warnings=warnings,
        errors=errors,
        item_scores=item_scores,
        summary=summary,
        overall_warnings=overall_warnings,
    )


def _check_grammar(text: str) -> List[Dict]:
    """检查中文语法问题"""
    issues = []

    # 检查是否有无意义的模板占位符
    if "{{" in text or "}}" in text:
        issues.append({"type": "error", "check": "语法完整性", "msg": "题目包含未填充的模板占位符，疑似生成失败"})

    # 检查是否以标点结尾（好的题目通常不需要句号结尾）
    if text.endswith("吧") or text.endswith("吗") and "?" not in text and "？" not in text:
        issues.append({"type": "info", "check": "语法规范性", "msg": "疑问语气可能影响作答，建议改为陈述句"})

    # 检查句子是否完整（主谓结构）
    if len(text) >= 6:
        # 简单的完整性检查：是否包含动词或"的"字结构
        has_predicate = any(
            w in text for w in ["是", "有", "会", "能", "认为", "觉得", "感到", "表现"]
        )
        if not has_predicate:
            issues.append({"type": "warning", "check": "语法完整性", "msg": "题目可能缺少谓语，表达不够完整"})

    return issues


def _check_double_barreled(text: str) -> str:
    """检查是否一题多问（双向陈述）"""
    connectors = ["和", "或", "与", "并且", "以及", "还有", "同时", "另一方面"]
    # 排除合理的并列结构（如"开心和快乐"）
    synonyms_pairs = [
        ("开心", "快乐"), ("紧张", "焦虑"), ("疲劳", "疲惫"),
        ("担心", "担忧"), ("悲伤", "难过"),
    ]

    for conn in connectors:
        if conn in text:
            # 检查是否是同义并列
            is_synonym = False
            for w1, w2 in synonyms_pairs:
                if w1 in text and w2 in text:
                    is_synonym = True
                    break
            if not is_synonym:
                return f"题目包含「{conn}」连接多个概念，可能一题多问。建议拆分为两道题。"

    # v3.7 补：检测"又...又..."双重负载结构（"我又累又难过"）
    # 启发式：含至少 2 个"又"且不属于同义词
    you_count = text.count("又")
    if you_count >= 2:
        is_synonym = False
        for w1, w2 in synonyms_pairs:
            if w1 in text and w2 in text:
                is_synonym = True
                break
        if not is_synonym:
            return "题目使用「又...又...」连接多个概念，可能一题多问。建议拆分。"

    return ""


def _check_negation(text: str, is_reverse: bool) -> str:
    """检查否定表达的复杂度"""
    neg_words = ["不", "没有", "并非", "非", "无"]
    neg_count = sum(text.count(w) for w in neg_words)

    if neg_count >= 2:
        return f"题目包含{neg_count}处否定词，可能造成理解困难，建议简化表达。"
    if neg_count == 1 and not is_reverse:
        return ""  # 一次否定是可以的
    if neg_count == 1 and is_reverse:
        return ""  # 反向题有一次否定是正常的

    return ""


def _check_vague_words(text: str) -> str:
    """检查模糊频率词"""
    vague = []
    if "经常" in text:
        vague.append("「经常」")
    if "有时候" in text:
        vague.append("「有时候」")
    if "偶尔" in text:
        vague.append("「偶尔」")
    if "常常" in text:
        vague.append("「常常」")

    if vague:
        return f"题目包含模糊频率词{'、'.join(vague)}，建议改用具体行为描述或锚定时间频率。"
    return ""


def _check_redundancy(dim_items: Dict[str, List[Dict]]) -> List[Tuple[int, int, float]]:
    """检查同一维度内的题目冗余（基于简单字符重叠率）"""
    issues = []

    for dim_name, items in dim_items.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                text_i = items[i].get("text", "")
                text_j = items[j].get("text", "")
                sim = _char_overlap_similarity(text_i, text_j)

                if sim > 0.75:
                    idx_a = items[i].get("index", 0)
                    idx_b = items[j].get("index", 0)
                    issues.append((idx_a, idx_b, sim))

    return issues


def _char_overlap_similarity(s1: str, s2: str) -> float:
    """基于字符集合的Jaccard相似度"""
    set1 = set(s1)
    set2 = set(s2)
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


# ===========================================================================
# v3.7.10：当代测量学规则的本地启发式检查（无 LLM 成本）
# ===========================================================================

# 行为锚定线索：题干含这些词暗示有具体行为/情境
_BEHAVIORAL_ANCHOR_HINTS = [
    "过去", "最近", "上周", "上月", "每天", "每周", "每月",
    "在", "时", "时候", "情况下", "场合", "面对",
    "做", "去", "完成", "参加", "尝试", "选择", "决定",
    "发现", "注意到", "意识到", "想到", "记得",
    "数", "次", "天", "小时", "分钟",
]

# 极端词：强迫极端反应
_EXTREME_WORDS = [
    "总是", "永远", "从不", "绝对", "必定", "完全", "彻底",
    "丝毫", "毫无", "万分", "极其", "百分之百",
    "决不", "断然", "无一例外",
]

# 假设/条件句标记
_HYPOTHETICAL_MARKERS = [
    ("如果", "就"), ("如果", "会"), ("如果", "便"), ("如果", "那"),
    ("假设", "会"), ("假设", "就"), ("假如", "会"), ("假如", "就"),
    ("假使", "会"), ("倘若", "会"), ("要是", "就"), ("要是", "会"),
]

# 过窄情境标记词（罕见名词组合）
_OVERFITTING_NARROW_NOUNS = [
    "地铁", "公交", "电梯", "排队",
    "手机没电", "没电时", "停电", "断网",
    "冰激凌", "炸鸡", "可乐",
    "周三下午", "周一早上", "凌晨三点",
]


def _check_abstractness(text: str, construct_name: str = "") -> str:
    """v3.7.10: 检测题目是否抽象（仅含构念词无可观察行为/情境锚定）。

    判据（同时满足才算抽象）：
    1. 长度 ≤ 12 字（短题更容易抽象）
    2. 不含任何行为锚定线索词
    3. 含「感到/感觉/觉得/认为」等抽象状态动词
    """
    if not text or len(text) > 16:
        return ""
    has_anchor = any(hint in text for hint in _BEHAVIORAL_ANCHOR_HINTS)
    if has_anchor:
        return ""
    abstract_verbs = ["感到", "感觉", "觉得", "认为", "感受到"]
    has_abstract_verb = any(v in text for v in abstract_verbs)
    if has_abstract_verb and len(text) <= 12:
        return f"题目较为抽象（{len(text)}字，仅含「感到/觉得」等状态词），缺少可观察行为或具体情境锚定，建议增加时间窗口（如「过去一周」）或行为描述。"
    return ""


def _check_overfitting(text: str) -> str:
    """v3.7.10: 检测题目是否情境过窄（含过度具体的罕见情境）。

    判据：题干含 ≥2 个 _OVERFITTING_NARROW_NOUNS 中的词，或者含「在 X 时 Y」的极窄场景描述。
    """
    if not text:
        return ""
    hits = [w for w in _OVERFITTING_NARROW_NOUNS if w in text]
    if len(hits) >= 2:
        return f"题目情境过窄（含「{'、'.join(hits)}」等罕见场景词组合），仅在特定场景成立可能损害外部效度。建议泛化到一类典型情境。"
    if len(hits) == 1 and len(text) <= 20:
        # 单个罕见名词 + 短题更可疑
        return f"题目可能情境过窄（含「{hits[0]}」），建议判断该情境是否典型而非边缘。"
    return ""


def _check_extreme_words(text: str) -> str:
    """v3.7.10: 检测极端词（破坏区分度）。"""
    if not text:
        return ""
    hits = [w for w in _EXTREME_WORDS if w in text]
    if hits:
        return f"题目含极端词「{'、'.join(hits)}」，会强迫被试选极端选项、降低区分度，建议改为「常」「较少」等中性表述。"
    return ""


def _check_hypothetical(text: str) -> str:
    """v3.7.10: 检测假设/条件句（测的是想象不是行为）。"""
    if not text:
        return ""
    for prefix, suffix in _HYPOTHETICAL_MARKERS:
        if prefix in text and suffix in text:
            # 确认 prefix 在 suffix 前
            if text.find(prefix) < text.find(suffix):
                return f"题目为假设/条件句（「{prefix}...{suffix}...」结构），测的是被试的想象而非实际行为。建议改为描述实际经历。"
    return ""


def _check_direct_construct_question(text: str, construct_name: str = "") -> str:
    """v3.7.10: 检测是否直接问构念（题干含构念名）。"""
    if not text or not construct_name:
        return ""
    # 仅当构念名 ≥ 2 字才检查（避免单字误报）
    if len(construct_name) < 2:
        return ""
    if construct_name in text:
        return f"题目直接含构念名「{construct_name}」，应改为行为锚定描述。"
    return ""


def _check_subject_consistency(items: List[Dict], item_subject_template: str = "") -> List[Dict]:
    """v3.7.10: 检测题目主语是否与 item_subject_template 一致。

    返回：每个不一致的题的 issue，格式 [{index, msg}]
    """
    if not item_subject_template:
        return []
    issues = []
    # 模板属性：自评型（以"我"开头且不含"我们"） vs 对象评估型
    is_self_template = (
        item_subject_template.startswith("我")
        and not item_subject_template.startswith("我们")
    )
    is_org_template = (
        item_subject_template.startswith("我们")
        or item_subject_template.startswith("现行")
        or item_subject_template.startswith("公司")
        or "标准" in item_subject_template[:6]
        or "流程" in item_subject_template[:6]
    )
    for item in items:
        if item.get("item_type") and item["item_type"] != "construct":
            continue   # 注意力检测题等不参与主语一致性检查
        text = item.get("text", "")
        if not text:
            continue
        starts_with_self = text.startswith("我") and not text.startswith("我们")
        starts_with_org = (
            text.startswith("我们")
            or text.startswith("现行")
            or text.startswith("公司")
        )
        if is_self_template and not starts_with_self:
            # 模板要求自评（"我..."），题目却不是「我」开头 → 不一致
            issues.append({
                "index": item.get("index", "?"),
                "msg": f"题目主语与 item_subject_template「{item_subject_template}」不一致（题目应以「我」开头）",
            })
        elif is_org_template and not starts_with_org:
            # 模板要求评对象（"我们公司的 X..."），题目却不是 → 不一致
            issues.append({
                "index": item.get("index", "?"),
                "msg": f"题目主语与 item_subject_template「{item_subject_template}」不一致（题目应描述评估对象，不应以「我」开头）",
            })
    return issues


def _check_mirror_reverse(items: List[Dict]) -> List[Dict]:
    """v3.7.10: 检测镜像反向题（reverse=True 题与同维度正向题字符相似度过高）。

    使用现有 _char_overlap_similarity；阈值 0.75。

    返回：每个镜像题的 issue [{index, msg}]
    """
    issues = []
    # 按维度分组
    by_dim: Dict[str, List[Dict]] = {}
    for it in items:
        if it.get("item_type") and it["item_type"] != "construct":
            continue
        d = it.get("dimension", "默认维度")
        by_dim.setdefault(d, []).append(it)
    for dim_name, dim_items in by_dim.items():
        positives = [it for it in dim_items if not it.get("reverse", False)]
        reverses = [it for it in dim_items if it.get("reverse", False)]
        for rev in reverses:
            rev_text = rev.get("text", "")
            for pos in positives:
                pos_text = pos.get("text", "")
                sim = _char_overlap_similarity(rev_text, pos_text)
                if sim >= 0.75:
                    issues.append({
                        "index": rev.get("index", "?"),
                        "msg": f"反向题与正向题 #{pos.get('index', '?')} 字符相似度 {sim:.0%}，可能为镜像题（仅加'不'），应改为描述与维度方向相反的具体情境",
                    })
                    break   # 一道反向题命中一个就够了
    return issues


def _check_attention_check_quota(items: List[Dict]) -> List[str]:
    """v3.7.10: 检查注意力检测题数量配额（report 级警告）。

    返回 overall_warnings 字符串列表。
    """
    warnings = []
    construct_items = [it for it in items if it.get("item_type", "construct") == "construct"]
    attention_items = [it for it in items if it.get("item_type") == "attention_check"]
    n_construct = len(construct_items)
    n_attention = len(attention_items)
    if n_construct == 0:
        return warnings
    expected_min = 1
    expected_max = max(3, n_construct // 10)
    if n_attention < expected_min:
        warnings.append(
            f"⚠️ 注意力检测题数量不足（当前 {n_attention} 道，建议 ≥ 1 道）。"
            f"无注意力检测题难以识别 careless responder（Meade & Craig 2012）。"
        )
    elif n_attention > expected_max:
        warnings.append(
            f"⚠️ 注意力检测题过多（当前 {n_attention} 道，建议 ≤ {expected_max} 道）。"
            f"过多检测题增加被试负担、降低正常题作答质量。"
        )
    return warnings


# ===========================================================================
# Task 3: 反向题自然度评分
# ===========================================================================

# 常见的抽象/生僻心理学术语（出现则适当扣分）
_ABSTRACT_TERMS = [
    "认知失调", "自我效能", "元认知", "习得性无助", "图式",
    "归因风格", "内隐联想", "认知重评", "情感失调", "自我概念",
    "防御机制", "心理弹性", "去中心化", "过度泛化", "灾难化",
    "述情障碍", "自我客体化", "反刍思维", "自我分化",
]

# 双重否定模式
_DOUBLE_NEGATION_PATTERNS = [
    re.compile(r"不是不"), re.compile(r"没有不"), re.compile(r"并非不"),
    re.compile(r"不会不"), re.compile(r"不可能不"), re.compile(r"不太[^，。]*不"),
]

# 句首否定词
_SENTENCE_INITIAL_NEGATIONS = ["不", "没有", "并非", "我从不", "我几乎不"]


def evaluate_reverse_item_naturalness(item_text: str) -> float:
    """
    评估反向题的自然度，返回0-10的分数。

    评分规则（基于简单语言规则，不依赖外部模型）：
    - 长度：>30字扣2分，<6字扣2分
    - 双重否定（如"不是不"）：扣3分
    - 否定词位于句首：扣1分
    - 含生僻抽象词汇：每词扣1分（最多扣3分）
    - 否定词过多（≥2个）：扣1分
    """
    text = item_text.strip()
    score = 10.0
    deductions = []

    # 1. 长度检查
    char_len = len(text)
    if char_len > 30:
        score -= 2
        deductions.append(f"句子过长（{char_len}字），建议≤30字（-2分）")
    elif char_len < 6:
        score -= 2
        deductions.append(f"句子过短（{char_len}字），建议≥6字（-2分）")

    # 2. 双重否定检查
    has_double_neg = False
    for pattern in _DOUBLE_NEGATION_PATTERNS:
        if pattern.search(text):
            has_double_neg = True
            break
    if has_double_neg:
        score -= 3
        deductions.append("包含双重否定（如'不是不'），理解困难（-3分）")

    # 3. 句首否定词
    for neg in _SENTENCE_INITIAL_NEGATIONS:
        if text.startswith(neg):
            score -= 1
            deductions.append("否定词位于句首，可能影响作答自然度（-1分）")
            break

    # 4. 生僻抽象词汇
    abstract_count = 0
    for term in _ABSTRACT_TERMS:
        if term in text:
            abstract_count += 1
    if abstract_count > 0:
        deduct = min(abstract_count, 3)
        score -= deduct
        deductions.append(f"含{abstract_count}个抽象生僻术语（-{deduct}分）")

    # 5. 否定词数量过多
    neg_words = ["不", "没有", "并非", "非", "无"]
    neg_count = sum(text.count(w) for w in neg_words)
    if neg_count >= 2:
        score -= 1
        deductions.append(f"否定词过多（{neg_count}处）（-1分）")

    score = max(0.0, score)
    return score, deductions


def verify_semantic_polarity(
    positive_item: str,
    reverse_item: str,
) -> Dict:
    """
    验证正向题和反向题是否真正语义对立（而非表面否定）。

    检查维度：
    1. 共享内容骨架（正反题应讨论同一主题，字符重叠 >30%）
    2. 否定覆盖率（反向题应至少包含1处否定或极性翻转）
    3. 语义距离（内容高度一致但极性相反 → 理想；内容差异大 → 可能不是对立）
    4. 极性置信度综合评分

    返回：
        {
            "is_valid_pair": bool,
            "polarity_score": float (0-10),
            "shared_content_ratio": float,
            "negation_count_reverse": int,
            "issues": list,
            "suggestion": str,
        }
    """
    pos = positive_item.strip()
    rev = reverse_item.strip()
    issues = []
    score = 10.0

    # 1. 内容重叠率（基于字符集的 Jaccard）
    pos_chars = set(pos)
    rev_chars = set(rev)
    union = len(pos_chars | rev_chars)
    intersection = len(pos_chars & rev_chars)
    shared_ratio = intersection / union if union > 0 else 0

    if shared_ratio < 0.20:
        score -= 4
        issues.append("正反题内容几乎完全不同，可能并非讨论同一维度")
    elif shared_ratio < 0.30:
        score -= 2
        issues.append("正反题内容重叠较低，语义可能偏离")

    # 2. 否定词检测
    neg_words = ["不", "没有", "并非", "非", "无", "很少", "几乎不", "难以", "无法"]
    pos_neg = sum(pos.count(w) for w in neg_words)
    rev_neg = sum(rev.count(w) for w in neg_words)

    if rev_neg == 0:
        # 检查是否有语义极性翻转（靠反义词库）
        has_antonym = _detect_antonym_flip(pos, rev)
        if not has_antonym:
            score -= 5
            issues.append("反向题既无否定词也无反义翻转，可能是正向题的机械复制")
        else:
            score -= 1
            issues.append("反向题靠反义词实现但无语法否定，自然度可接受")
    elif rev_neg >= 3:
        score -= 2
        issues.append("反向题否定词过多，理解难度偏高")

    # 3. 长度差异检查
    len_diff = abs(len(pos) - len(rev))
    if len_diff > 15:
        score -= 1
        issues.append(f"正反题长度差异较大（{len_diff}字），可能内容不对称")

    # 4. 相同题干的占比判断
    # 如果反题只是简单在正题前加"不"，得分偏低
    if rev.startswith("不" + pos[:5]) or rev.startswith("我并不" + pos[1:5]):
        score -= 1
        issues.append("反向题为机械否定形式，表达不够自然")

    score = max(0.0, score)
    is_valid = score >= 5.0

    return {
        "is_valid_pair": is_valid,
        "polarity_score": round(score, 1),
        "shared_content_ratio": round(shared_ratio, 3),
        "negation_count_reverse": rev_neg,
        "issues": issues,
        "suggestion": (
            "正向-反向题对质量良好" if is_valid
            else "反向题未真正语义对立，需要重写" + ("；".join(issues))
        ),
    }


def _detect_antonym_flip(pos_text: str, rev_text: str) -> bool:
    """检测是否存在反义替换（非否定词驱动的极性翻转）"""
    antonym_pairs = [
        ("积极", "消极"), ("主动", "被动"), ("乐观", "悲观"),
        ("经常", "很少"), ("总是", "几乎不"), ("善于", "不善于"),
        ("容易", "不容易"), ("愿意", "不愿意"), ("相信", "怀疑"),
        ("满意", "不满意"), ("成功", "失败"), ("接纳", "排斥"),
        ("热情", "冷淡"), ("自信", "自卑"), ("重视", "忽视"),
        ("坚持", "放弃"), ("投入", "疏离"), ("关注", "忽略"),
        ("开放", "保守"), ("稳定", "波动"), ("独立", "依赖"),
    ]
    for pos_word, neg_word in antonym_pairs:
        if pos_word in pos_text and neg_word in rev_text:
            return True
    return False


def verify_all_pairs(items: List[Dict]) -> List[Dict]:
    """
    对题目列表中的所有正向-反向题对进行语义极性验证。

    自动配对同一维度下的正向题和反向题。
    """
    import itertools

    # 按维度分组
    dim_items = {}
    for item in items:
        dim = item.get("dimension", "默认")
        dim_items.setdefault(dim, {"positive": [], "reverse": []})
        if item.get("reverse"):
            dim_items[dim]["reverse"].append(item)
        else:
            dim_items[dim]["positive"].append(item)

    results = []
    for dim_name, groups in dim_items.items():
        pos_items = groups["positive"]
        rev_items = groups["reverse"]

        for p_item, r_item in itertools.product(pos_items, rev_items):
            result = verify_semantic_polarity(
                p_item.get("text", ""),
                r_item.get("text", ""),
            )
            result["dimension"] = dim_name
            result["positive_index"] = p_item.get("index", "?")
            result["reverse_index"] = r_item.get("index", "?")
            results.append(result)

    return results


def diagnose_reverse_item(item_text: str) -> Dict:
    """
    诊断反向题并返回详细报告。
    """
    score, deductions = evaluate_reverse_item_naturalness(item_text)
    needs_review = score < 5.0
    return {
        "text": item_text,
        "naturalness_score": score,
        "needs_review": needs_review,
        "deductions": deductions,
        "suggestion": "建议人工审阅并改写" if needs_review else "自然度可接受",
    }


# ===========================================================================
# Task 5: 题目区分度预估计（模拟数据法）
# ===========================================================================

@dataclass
class DiscriminationReport:
    """题目区分度预估计报告"""
    n_simulate: int = 500
    n_dimensions: int = 0
    n_items: int = 0
    item_results: List[Dict] = field(default_factory=list)
    weak_items: List[Dict] = field(default_factory=list)
    summary: str = ""


def estimate_item_discrimination(
    items: List[Dict],
    n_simulate: int = 500,
    seed: int = 42,
    weak_threshold: float = 0.30,
) -> DiscriminationReport:
    """
    基于模拟数据预估计题目的区分度（校正后项目-总体相关）。

    方法：
    - 为每个维度生成隐"真分数"θ ~ N(0, 1)
    - 每道题 = θ + ε（ε ~ N(0, σ²)，σ² = 1 - 期望信度 ≈ 0.3）
    - 反向题先反转再计算
    - 计算每个维度的校正后题总相关（该题得分与去除该题后的维度总分之间的相关）
    - 标记区分度 < weak_threshold 的弱题目

    注意：此为预收集阶段的质量预检，用于识别表述可能存在问题的题目。
    实际区分度需在正式施测后通过项目分析确认。

    返回：
        DiscriminationReport：每道题目的区分度估计及弱题标记
    """
    import numpy as np
    from scipy.stats import pearsonr

    rng = np.random.default_rng(seed)

    # 按维度分组
    dim_groups = {}
    for item in items:
        dim = item.get("dimension", "默认")
        dim_groups.setdefault(dim, []).append(item)

    # 为每个维度生成模拟数据
    all_scores = {}
    dim_residual_var = 0.3  # 题目独特方差

    for dim_name, dim_items in dim_groups.items():
        n_items = len(dim_items)
        # 生成维度真分数
        theta = rng.normal(0, 1, n_simulate)
        # 为每道题生成观察分数
        for item in dim_items:
            idx = item.get("index", "")
            # 题目 = 真分数 + 随机误差
            error = rng.normal(0, np.sqrt(dim_residual_var), n_simulate)
            obs = theta + error
            # 反向题反转
            if item.get("reverse"):
                obs = -obs
            # 离散化为 1-5 Likert
            obs_discrete = np.clip(np.round(3 + obs), 1, 5).astype(int)
            all_scores[idx] = obs_discrete

        # 存储维度真分数用于维度间相关
        all_scores[f"_theta_{dim_name}"] = theta

    # 计算每个维度的校正后题总相关
    item_results = []
    weak_items = []

    for dim_name, dim_items in dim_groups.items():
        item_ids = [item.get("index", "") for item in dim_items]
        # 维度总分（模拟数据中所有题的总和）
        dim_scores = np.column_stack([all_scores[idx] for idx in item_ids])
        dim_total = dim_scores.sum(axis=1)

        for item in dim_items:
            idx = item.get("index", "")
            item_score = all_scores[idx]
            # 校正后总分（去掉当前题）
            corrected_total = dim_total - item_score
            if corrected_total.std() > 0:
                corr, _ = pearsonr(item_score, corrected_total)
            else:
                corr = 0.0

            discrimination = max(0.0, round(float(corr), 3))
            is_weak = discrimination < weak_threshold

            result_entry = {
                "index": idx,
                "dimension": dim_name,
                "text": item.get("text", ""),
                "is_reverse": item.get("reverse", False),
                "discrimination": discrimination,
                "is_weak": is_weak,
                "interpretation": _interpret_discrimination(discrimination),
            }
            item_results.append(result_entry)

            if is_weak:
                weak_items.append(result_entry)

    # 摘要
    n_weak = len(weak_items)
    n_total = len(item_results)
    if n_weak == 0:
        summary = f"✅ 所有{n_total}道题目的模拟区分度均 ≥{weak_threshold}，题目质量良好。"
    else:
        summary = (
            f"在{n_simulate}次模拟下，{n_total}道题中有{n_weak}道区分度 <{weak_threshold}，"
            f"建议在正式施测前修改或替换弱题。"
        )

    return DiscriminationReport(
        n_simulate=n_simulate,
        n_dimensions=len(dim_groups),
        n_items=n_total,
        item_results=item_results,
        weak_items=weak_items,
        summary=summary,
    )


def _interpret_discrimination(d: float) -> str:
    """解读区分度值"""
    if d >= 0.40:
        return "优秀（≥0.40）"
    elif d >= 0.30:
        return "可接受（0.30-0.40）"
    elif d >= 0.20:
        return "偏低（0.20-0.30），建议修改"
    else:
        return "很差（<0.20），强烈建议删除或重写"
