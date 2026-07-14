"""意图识别链：多策略分级识别研究问题对应的心理学构念

使用策略模式（Strategy Pattern）实现可组合、可扩展的识别链。
识别链分为三层：
  Layer 1 — 关键词评分（快速路径，基于 jieba 分词 + 构念关键词库）
  Layer 2 — TF-IDF 语义相似度（回退路径，基于词级+bigram综合相似度）
  Layer 3 — LLM 消歧（高精度路径，当置信度不足时启用）

返回统一格式的 IntentResult，包含置信度和候选排序。
"""

import jieba
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class IntentCandidate:
    """识别候选"""
    construct_name: str          # 构念中文名
    confidence: float            # 置信度 0-1
    source: str                  # 来源：keyword / tfidf / llm / gold_standard
    match_reason: str            # 匹配理由
    construct_def: str = ""      # 构念定义（摘要）
    dimensions: List[str] = field(default_factory=list)
    domain: str = ""             # 所属领域


@dataclass
class IntentResult:
    """意图识别结果"""
    research_question: str
    top_candidate: Optional[IntentCandidate] = None
    candidates: List[IntentCandidate] = field(default_factory=list)
    layers_used: List[str] = field(default_factory=list)
    is_ambiguous: bool = False
    suggestion: str = ""


# ============================================================
# 策略接口
# ============================================================


class IntentStrategy(ABC):
    """意图识别策略抽象基类"""

    name: str = "base"

    @abstractmethod
    def recognize(
        self,
        question: str,
        words: List[str],
        context: Optional[Dict] = None,
    ) -> List[IntentCandidate]:
        """返回候选列表（可能为空），按置信度降序排列"""
        ...


# ============================================================
# Layer 1: 关键词评分策略
# ============================================================


class KeywordIntentStrategy(IntentStrategy):
    """
    基于 jieba 分词 + 构念关键词库的快速匹配。

    继承 design_engine._match_construct 的核心逻辑，
    将其抽离为独立策略，输出标准化的 IntentCandidate 列表。
    """

    name = "keyword"

    def __init__(self, constructs: Dict = None, keywords: Dict = None,
                 extended_constructs: Dict = None):
        self._constructs = constructs or {}
        self._keywords = keywords or {}
        self._extended = extended_constructs or {}

    def recognize(
        self,
        question: str,
        words: List[str],
        context: Optional[Dict] = None,
    ) -> List[IntentCandidate]:
        all_constructs = {**self._constructs, **self._extended}
        if not self._keywords or not all_constructs:
            return []

        scores = {}
        for cname, kw_list in self._keywords.items():
            score = 0.0
            if cname in question:
                score += 3.0 + len(cname) * 0.5
            for kw in kw_list:
                if kw in question:
                    score += 2.0 + len(kw) * 0.1
                elif any(kw in w or w in kw for w in words):
                    score += 1.0 + len(kw) * 0.05
            if score > 0:
                scores[cname] = score

        if not scores:
            return []

        max_possible = 10.0
        candidates = []
        for cname, raw_score in sorted(scores.items(), key=lambda x: -x[1]):
            confidence = min(raw_score / max_possible, 0.95)
            if confidence < 0.15:
                continue
            construct = all_constructs.get(cname, {})
            source = "gold_standard" if cname in self._constructs else "keyword"
            candidates.append(IntentCandidate(
                construct_name=cname,
                confidence=round(confidence, 3),
                source=source,
                match_reason=(
                    f"在研究问题中识别到「{cname}」相关关键词，"
                    f"匹配得分 {raw_score:.1f}（关键词匹配引擎）"
                ),
                construct_def=construct.get("definition", ""),
                dimensions=construct.get("dimensions", []),
                domain=construct.get("domain", ""),
            ))

        return candidates


# ============================================================
# Layer 2: TF-IDF 语义相似度策略
# ============================================================


class TFIDFIntentStrategy(IntentStrategy):
    """
    基于词级 Jaccard + bigram 字符级相似度的语义匹配。

    当关键词策略未能给出高置信度匹配时使用。
    """

    name = "tfidf"

    def __init__(self, constructs: Dict = None, extended_constructs: Dict = None):
        self._constructs = constructs or {}
        self._extended = extended_constructs or {}
        self._all = {**self._constructs, **self._extended}

    def recognize(
        self,
        question: str,
        words: List[str],
        context: Optional[Dict] = None,
    ) -> List[IntentCandidate]:
        if not self._all:
            return []

        candidates = []
        for cname, construct in self._all.items():
            texts = [construct.get("definition", ""), cname]
            for dim in construct.get("dimensions", []):
                if isinstance(dim, dict):
                    texts.append(dim.get("name", ""))
                    texts.append(dim.get("desc", ""))
                else:
                    texts.append(str(dim))

            combined_text = " ".join(texts)
            sim = _combined_similarity(question, combined_text, words, cname)

            if sim > 0.20:
                candidates.append(IntentCandidate(
                    construct_name=cname,
                    confidence=round(min(sim, 0.85), 3),
                    source="tfidf",
                    match_reason=(
                        f"通过语义匹配识别到「{cname}」，"
                        f"相似度 {sim:.2f}（TF-IDF语义分析）"
                    ),
                    construct_def=construct.get("definition", ""),
                    dimensions=construct.get("dimensions", []),
                    domain=construct.get("domain", ""),
                ))

        candidates.sort(key=lambda c: -c.confidence)
        return candidates


# ============================================================
# Layer 3: LLM 消歧策略（可选）
# ============================================================


class LLMIntentStrategy(IntentStrategy):
    """使用 LLM 进行高精度构念消歧。"""

    name = "llm"

    def __init__(self, llm_config: Dict = None):
        self._config = llm_config or {}

    def recognize(
        self,
        question: str,
        words: List[str],
        context: Optional[Dict] = None,
    ) -> List[IntentCandidate]:
        if not self._config or not self._config.get("api_key"):
            return []

        try:
            return _call_llm_for_intent(question, self._config)
        except Exception:
            return []


def _call_llm_for_intent(question: str, config: Dict) -> List[IntentCandidate]:
    """调用 LLM 识别研究问题中的心理学构念（通过 gateway）"""
    import json
    import re

    system_prompt = (
        "你是一位心理学测量学专家。请分析以下研究问题，识别其中最核心的心理学构念（construct）。\n\n"
        "要求：\n"
        "1. 识别1-3个最相关的心理学构念\n"
        "2. 为每个构念提供置信度（0-1之间）\n"
        "3. 给出匹配理由\n"
        "4. 如果构念不明确，给出领域方向建议\n\n"
        "请严格按照以下JSON格式输出：\n"
        '{"candidates": [{"construct_name": "...", "confidence": 0.9, '
        '"reason": "...", "domain": "...", "dimensions": ["..."]}]}'
    )

    try:
        from src.llm_gateway.gateway import llm_chat
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"研究问题：{question}"},
        ]
        resp = llm_chat(messages, temperature=0.1, max_tokens=1024, retries=1)
        if not resp.ok:
            return []
        content = resp.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```\w*\n?", "", content)
            content = re.sub(r"\n```$", "", content)
        data = json.loads(content)

        candidates = []
        for item in data.get("candidates", []):
            candidates.append(IntentCandidate(
                construct_name=item.get("construct_name", ""),
                confidence=min(max(float(item.get("confidence", 0.5)), 0.0), 1.0),
                source="llm",
                match_reason=item.get("reason", ""),
                construct_def="",
                dimensions=item.get("dimensions", []),
                domain=item.get("domain", ""),
            ))
        return candidates
    except Exception:
        return []


# ============================================================
# 意图识别链（Chain of Responsibility）
# ============================================================


class IntentRecognitionChain:
    """
    意图识别链：按策略优先级依次尝试，直到获得满意置信度。

    流程：
    1. 先运行关键词策略（快速路径）
    2. 若最佳置信度 < 阈值，运行 TF-IDF 策略
    3. 若仍然不足且 LLM 可用，运行 LLM 策略
    4. 合并并排序所有候选

    使用示例：
        chain = IntentRecognitionChain(keyword_strategy, tfidf_strategy)
        result = chain.recognize("调查大学生的自尊水平")
    """

    def __init__(self, *strategies: IntentStrategy,
                 confidence_threshold: float = 0.5):
        self._strategies = list(strategies)
        self._threshold = confidence_threshold

    def add_strategy(self, strategy: IntentStrategy):
        self._strategies.append(strategy)
        return self

    def recognize(
        self,
        question: str,
        words: Optional[List[str]] = None,
        llm_config: Optional[Dict] = None,
    ) -> IntentResult:
        if words is None:
            words = list(jieba.cut(question))
            words = [w.strip() for w in words if len(w.strip()) >= 2]

        all_candidates: List[IntentCandidate] = []
        layers_used: List[str] = []

        for strategy in self._strategies:
            if strategy.name == "llm" and llm_config:
                strategy._config = llm_config

            try:
                candidates = strategy.recognize(question, words)
                if candidates:
                    layers_used.append(strategy.name)
                    all_candidates.extend(candidates)

                    best_confidence = max(c.confidence for c in candidates)
                    if best_confidence >= self._threshold and strategy.name == "keyword":
                        break
            except Exception:
                continue

        # 去重（按 construct_name）并取每个构念的最高置信度
        merged: Dict[str, IntentCandidate] = {}
        for c in all_candidates:
            if c.construct_name not in merged or c.confidence > merged[c.construct_name].confidence:
                merged[c.construct_name] = c

        unique_candidates = sorted(merged.values(), key=lambda c: -c.confidence)

        top = unique_candidates[0] if unique_candidates else None
        is_ambiguous = top is None or top.confidence < self._threshold

        if top is None:
            suggestion = (
                "未能识别到明确的心理学构念。"
                "建议：1）在问题中明确提及具体心理学概念；"
                "2）尝试使用更常见的研究术语；"
                "3）缩小研究范围，聚焦特定领域。"
            )
        elif is_ambiguous:
            if len(unique_candidates) >= 2:
                c1, c2 = unique_candidates[0], unique_candidates[1]
                suggestion = (
                    f"识别结果不够确定（置信度 {top.confidence:.0%}）。"
                    f"最可能的构念是「{c1.construct_name}」，"
                    f"其次是「{c2.construct_name}」。建议查看具体定义后选择。"
                )
            else:
                suggestion = (
                    f"识别置信度较低（{top.confidence:.0%}）。"
                    f"建议提供更详细的研究问题描述以提升识别准确性。"
                )
        else:
            suggestion = (
                f"已成功识别到「{top.construct_name}」构念"
                f"（置信度 {top.confidence:.0%}，来源：{'→'.join(layers_used)}）。"
            )

        return IntentResult(
            research_question=question,
            top_candidate=top,
            candidates=unique_candidates,
            layers_used=layers_used,
            is_ambiguous=is_ambiguous,
            suggestion=suggestion,
        )


def create_default_chain(
    constructs: Dict = None,
    keywords: Dict = None,
    extended_constructs: Dict = None,
    llm_config: Dict = None,
) -> IntentRecognitionChain:
    """创建带有默认三层策略的识别链"""
    chain = IntentRecognitionChain()

    if constructs and keywords:
        chain.add_strategy(KeywordIntentStrategy(
            constructs=constructs,
            keywords=keywords,
            extended_constructs=extended_constructs or {},
        ))

    if constructs:
        chain.add_strategy(TFIDFIntentStrategy(
            constructs=constructs,
            extended_constructs=extended_constructs or {},
        ))

    if llm_config and llm_config.get("api_key"):
        chain.add_strategy(LLMIntentStrategy(llm_config=llm_config))

    return chain


# ============================================================
# 相似度计算
# ============================================================


def _combined_similarity(
    question: str,
    construct_text: str,
    words: List[str],
    construct_name: str,
) -> float:
    """综合相似度：词级Jaccard + bigram字符相似度 + 构念名精确匹配加权"""
    c_words = list(jieba.cut(construct_text))
    c_words = [w.strip() for w in c_words if len(w.strip()) >= 1]
    word_set_q = set(words)
    word_set_c = set(c_words)

    if not word_set_q or not word_set_c:
        return 0.0

    intersection = len(word_set_q & word_set_c)
    union = len(word_set_q | word_set_c)
    word_sim = intersection / union if union > 0 else 0.0

    name_bonus = 0.3 if construct_name in question else 0.0

    def _bigrams(s):
        return set(s[i:i+2] for i in range(len(s) - 1))

    bg_q = _bigrams(question)
    bg_c = _bigrams(construct_text)
    if bg_q and bg_c:
        bg_intersect = len(bg_q & bg_c)
        bg_union = len(bg_q | bg_c)
        bg_sim = bg_intersect / bg_union if bg_union > 0 else 0.0
    else:
        bg_sim = 0.0

    combined = 0.4 * word_sim + 0.3 * bg_sim + name_bonus
    return min(combined, 1.0)


# ============================================================
# 向后兼容：分析意图识别包装函数
# ============================================================


def recognize_intent(
    df,
    request: str,
    col_info: Dict,
    use_llm: bool = False,
    llm_config: Optional[Dict] = None,
) -> Dict:
    """
    多策略分析意图识别（兼容旧接口）。

    返回:
    {"best_match": str, "confidence": float, "candidates": [...],
     "is_ambiguous": bool, "disambiguation_text": str, "matched_keywords": [...]}
    """
    from difflib import SequenceMatcher
    from src.parser.keyword_dict import TEST_KEYWORDS
    from src.parser.tokenizer import tokenize

    tokens = tokenize(request)
    candidates = []

    for test_type, config in TEST_KEYWORDS.items():
        score = 0.0
        matched = []
        triggers = config.get("triggers", [])
        for trigger in triggers:
            if trigger in tokens:
                score += 2.0
                matched.append(trigger)
            elif any(trigger in t for t in tokens):
                score += 1.0
                matched.append(trigger + "(部分)")
            elif len(trigger) >= 2:
                for t in tokens:
                    if len(t) >= 2 and SequenceMatcher(None, trigger, t).ratio() > 0.75:
                        score += 0.5
                        matched.append(trigger + "(模糊)")
                        break
        candidates.append({
            "test_type": test_type, "score": score,
            "reason": f"关键词命中: {', '.join(matched[:5])}" if matched else "",
            "matched_keywords": matched,
        })

    # Layer 2: 列类型适配
    numeric_cols = [c for c, t in col_info.items() if t == "numeric"]
    binary_cols = [c for c, t in col_info.items() if t == "categorical_binary"]
    multi_cols = [c for c, t in col_info.items() if t == "categorical_multi"]

    for cand in candidates:
        test_type = cand["test_type"]
        if len(numeric_cols) >= 2 and test_type in ("pearson_corr", "spearman_corr", "partial_corr", "descriptive"):
            cand["score"] += 1.0
        if len(binary_cols) >= 1 and test_type in ("independent_ttest", "point_biserial"):
            cand["score"] += 1.0
        if len(multi_cols) >= 1 and test_type in ("one_way_anova", "kruskal_wallis"):
            cand["score"] += 1.0
        if len(numeric_cols) >= 3 and test_type in ("multiple_regression", "hierarchical_regression"):
            cand["score"] += 0.5
        if len(binary_cols) == 0 and len(multi_cols) == 0:
            if test_type in ("independent_ttest", "one_way_anova", "chi_square_independence",
                             "mann_whitney", "kruskal_wallis"):
                cand["score"] -= 1.0

    # Layer 3: 语义模式
    patterns = {
        "预测": ["multiple_regression", "linear_regression"],
        "影响": ["multiple_regression", "mediation"],
        "中介": ["mediation"], "调节": ["moderation"],
        "结构": ["efa"], "维度": ["efa"],
        "信度": ["cronbach_alpha", "split_half"],
        "一致性": ["cronbach_alpha"],
    }
    for pattern_kw, target_types in patterns.items():
        if pattern_kw in request:
            for cand in candidates:
                if cand["test_type"] in target_types:
                    cand["score"] += 1.5
                    cand["reason"] += f" 语义匹配: {pattern_kw}"

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    best = candidates[0] if candidates else {"test_type": "descriptive", "score": 0, "reason": "默认"}
    top_score = best["score"]
    max_possible = max(c["score"] for c in candidates) if candidates else 1
    confidence = min(1.0, top_score / max(3, max_possible)) if max_possible > 0 else 0.5
    is_ambiguous = confidence < 0.5 or (len(candidates) >= 2 and candidates[1]["score"] > top_score * 0.75)

    disambiguation_text = ""
    if is_ambiguous and len(candidates) >= 2:
        from config.settings import get_test_name
        options = [c["test_type"] for c in candidates[:3]]
        names = [get_test_name(t) for t in options]
        disambiguation_text = (
            f"您的分析需求可能匹配多种统计方法：{'、'.join(names)}。"
            f"系统选择了最合适的「{names[0]}」。如需调整，请明确指定分析方法。"
        )

    return {
        "best_match": best["test_type"],
        "confidence": round(confidence, 2),
        "candidates": candidates[:5],
        "is_ambiguous": is_ambiguous,
        "disambiguation_text": disambiguation_text,
        "matched_keywords": best.get("matched_keywords", []),
    }
