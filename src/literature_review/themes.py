"""主题聚类 + Gap 识别。

设计：
- 聚类算法：优先用 sklearn KMeans（依赖现有 factor_analyzer 间接已装），
            失败时降级到基于关键词重叠的简单层次聚类
- Gap 识别：LLM 可用时调 LLM；不可用时降级为基于矩阵空格的启发式分析
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from .models import GapAnalysis, LiteratureItem, LiteratureMatrix, ReadingNote, ThemeCluster


# ---------------------------------------------------------------------------
# 文本预处理
# ---------------------------------------------------------------------------

# 中文+英文停用词（精简版）
_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "其", "为", "与", "及", "等", "对", "中", "从", "可", "之",
    "以", "于", "或", "但", "都是", "进行", "研究", "分析",
    "the", "of", "and", "to", "in", "a", "is", "for", "on", "with", "as", "by",
    "an", "this", "that", "these", "those", "be", "are", "was", "were", "from",
    "study", "research", "analysis",
}


def _tokenize(text: str) -> List[str]:
    """简单中英文分词（jieba 可选；失败时按 2-gram + 英文单词）。"""
    if not text:
        return []
    text = text.lower()
    # 英文单词
    en_tokens = re.findall(r"[a-z]+", text)
    en_tokens = [t for t in en_tokens if len(t) >= 3 and t not in _STOPWORDS]

    # 中文：用 jieba（已有依赖）
    try:
        import jieba
        zh_tokens = list(jieba.cut(text))
        zh_tokens = [t.strip() for t in zh_tokens
                      if len(t.strip()) >= 2 and t.strip() not in _STOPWORDS]
    except Exception:
        # fallback：字符 bigram
        zh_only = re.sub(r"[a-z\s\d\W]+", " ", text)
        zh_tokens = [zh_only[i:i+2] for i in range(len(zh_only) - 1) if zh_only[i:i+2].strip()]
        zh_tokens = [t for t in zh_tokens if t not in _STOPWORDS]

    return en_tokens + zh_tokens


def _top_keywords(texts: List[str], top_n: int = 5) -> List[str]:
    """从文本列表中提取 top-n 最频繁词（去重 + 去停用词）。"""
    counter: Counter = Counter()
    for t in texts:
        for tok in _tokenize(t):
            counter[tok] += 1
    return [w for w, _ in counter.most_common(top_n)]


# ---------------------------------------------------------------------------
# 主题聚类
# ---------------------------------------------------------------------------

def auto_cluster_themes(
    notes: List[ReadingNote],
    *,
    n_clusters: int = 3,
    use_kmeans: bool = True,
) -> List[ThemeCluster]:
    """对所有阅读笔记的 content 做聚类。

    v3.5: 调用方可读 last_cluster_method 全局变量获得方法标识，
    或用 cluster_themes_with_meta 直接拿 method。
    """
    result = cluster_themes_with_meta(notes, n_clusters=n_clusters, use_kmeans=use_kmeans)
    return result["themes"]


def cluster_themes_with_meta(
    notes: List[ReadingNote],
    *,
    n_clusters: int = 3,
    use_kmeans: bool = True,
) -> Dict[str, Any]:
    """v3.5 带方法标识的聚类入口。

    Returns:
        {"themes": List[ThemeCluster], "method": "kmeans" | "keyword_overlap" | "by_literature" | "empty"}
    """
    if not notes:
        return {"themes": [], "method": "empty"}

    if len(notes) < n_clusters * 2:
        return {
            "themes": _cluster_by_literature(notes),
            "method": "by_literature",
        }

    if use_kmeans:
        try:
            themes = _kmeans_cluster(notes, n_clusters)
            return {"themes": themes, "method": "kmeans"}
        except Exception:
            pass

    return {
        "themes": _keyword_overlap_cluster(notes, n_clusters),
        "method": "keyword_overlap",
    }


def _cluster_by_literature(notes: List[ReadingNote]) -> List[ThemeCluster]:
    """笔记数太少时的简单分组：按文献 key 分组。"""
    by_lit: Dict[str, List[ReadingNote]] = {}
    for n in notes:
        by_lit.setdefault(n.literature_key, []).append(n)

    clusters: List[ThemeCluster] = []
    for i, (lit_key, lit_notes) in enumerate(by_lit.items(), 1):
        contents = [n.content for n in lit_notes]
        keywords = _top_keywords(contents, top_n=5)
        clusters.append(ThemeCluster(
            theme_name=f"主题 {i}（按文献分组）",
            literature_keys=[lit_key],
            centroid_keywords=keywords,
            summary=f"{lit_key} 相关笔记 {len(lit_notes)} 条",
        ))
    return clusters


def _kmeans_cluster(notes: List[ReadingNote], n_clusters: int) -> List[ThemeCluster]:
    """KMeans 聚类（sklearn）。"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans

    contents = [n.content for n in notes]
    # 自定义 tokenizer：用 _tokenize
    vectorizer = TfidfVectorizer(
        tokenizer=_tokenize,
        token_pattern=None,
        lowercase=False,
        max_features=200,
    )
    X = vectorizer.fit_transform(contents)

    actual_k = min(n_clusters, X.shape[0])
    km = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    labels = km.fit_predict(X)

    feature_names = vectorizer.get_feature_names_out()
    clusters: List[ThemeCluster] = []
    for cid in range(actual_k):
        cluster_notes = [n for n, l in zip(notes, labels) if l == cid]
        if not cluster_notes:
            continue
        # 取 cluster centroid 的 top-5 关键词
        centroid = km.cluster_centers_[cid]
        top_indices = centroid.argsort()[::-1][:5]
        keywords = [feature_names[i] for i in top_indices]
        lit_keys = sorted({n.literature_key for n in cluster_notes if n.literature_key})
        clusters.append(ThemeCluster(
            theme_name=f"主题 {cid + 1}",
            literature_keys=lit_keys,
            centroid_keywords=keywords,
            summary=f"{len(cluster_notes)} 条笔记，涉及 {len(lit_keys)} 篇文献",
        ))
    return clusters


def _keyword_overlap_cluster(notes: List[ReadingNote], n_clusters: int) -> List[ThemeCluster]:
    """降级聚类：按关键词重叠分组。"""
    # 每条笔记提取 top-3 关键词
    note_keywords: Dict[str, set] = {}
    for n in notes:
        kws = _top_keywords([n.content], top_n=3)
        note_keywords[n.note_id] = set(kws)

    # 贪心分组：将相似度 >0.3 的笔记合并
    groups: List[Dict[str, Any]] = []
    for n in notes:
        kw_set = note_keywords[n.note_id]
        added = False
        for g in groups:
            if g["keywords"] and len(kw_set & g["keywords"]) / max(1, len(kw_set | g["keywords"])) > 0.3:
                g["notes"].append(n)
                g["keywords"] = g["keywords"] | kw_set
                added = True
                break
        if not added:
            groups.append({"notes": [n], "keywords": set(kw_set)})

    # 取最大的 n_clusters 个组
    groups.sort(key=lambda g: -len(g["notes"]))
    groups = groups[:n_clusters]

    clusters: List[ThemeCluster] = []
    for i, g in enumerate(groups, 1):
        lit_keys = sorted({n.literature_key for n in g["notes"] if n.literature_key})
        clusters.append(ThemeCluster(
            theme_name=f"主题 {i}",
            literature_keys=lit_keys,
            centroid_keywords=list(g["keywords"])[:5],
            summary=f"{len(g['notes'])} 条笔记，涉及 {len(lit_keys)} 篇文献",
        ))
    return clusters


# ---------------------------------------------------------------------------
# Gap 识别
# ---------------------------------------------------------------------------

def identify_gaps(
    research_q: str,
    notes: List[ReadingNote],
    matrix: Optional[LiteratureMatrix] = None,
    *,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
) -> List[GapAnalysis]:
    """识别研究空白：优先 LLM，降级到启发式。"""
    gaps: List[GapAnalysis] = []

    # LLM 可用 → 调 LLM
    if llm_config and (llm_config.get("api_key") or llm_config.get("provider") == "ollama"):
        gaps_from_llm = _llm_identify_gaps(research_q, notes, matrix, llm_config, requests_module)
        if gaps_from_llm:
            return gaps_from_llm

    # 启发式降级
    gaps_heuristic = _heuristic_identify_gaps(research_q, notes, matrix)
    return gaps_heuristic


def _heuristic_identify_gaps(
    research_q: str,
    notes: List[ReadingNote],
    matrix: Optional[LiteratureMatrix] = None,
) -> List[GapAnalysis]:
    """启发式 gap 检测：
    1. 矩阵中空单元格率高的维度 → 该维度信息缺失
    2. 笔记中"疑问"类型的内容 → 学生自己识别的 gap
    """
    gaps: List[GapAnalysis] = []

    # 1) 空单元格分析
    if matrix and matrix.dimensions and matrix.cells:
        for dim in matrix.dimensions:
            empty_count = 0
            total = len(matrix.cells)
            for row in matrix.cells.values():
                if not row.get(dim, "").strip():
                    empty_count += 1
            if total > 0 and empty_count / total >= 0.5:
                gaps.append(GapAnalysis(
                    gap_description=f"维度「{dim}」在 {empty_count}/{total} 篇文献中信息缺失。",
                    suggested_direction=f"建议进一步精读这些文献，或将「{dim}」作为你研究的核心切入点。",
                    confidence=0.6,
                    source="heuristic",
                ))

    # 2) 学生自己提的疑问
    question_notes = [n for n in notes if n.type == "疑问"]
    for n in question_notes[:3]:
        gaps.append(GapAnalysis(
            gap_description=f"你在阅读笔记中提出了疑问：{n.content[:80]}",
            supporting_notes=[n.content[:120]],
            suggested_direction="这可能正是你的研究切入点——已有文献未充分回答的问题。",
            confidence=0.7,
            source="heuristic",
        ))

    if not gaps:
        gaps.append(GapAnalysis(
            gap_description="暂未识别到明显的研究空白。",
            suggested_direction="建议先添加更多阅读笔记（特别是「疑问」类型），再返回此页查看。",
            confidence=0.0,
            source="heuristic",
        ))

    return gaps


def _llm_identify_gaps(
    research_q: str,
    notes: List[ReadingNote],
    matrix: Optional[LiteratureMatrix],
    llm_config: Dict[str, Any],
    requests_module: Any = None,
) -> List[GapAnalysis]:
    """LLM 调用版（v3.5 通过 gateway；失败返回空，由调用方降级）。"""
    try:
        from src.llm_gateway import LLMUnavailableError, llm_chat
        from src.paper_writer.ai_tutor import build_tutor_messages
        # 拼接笔记摘要
        notes_summary = "\n".join(
            f"- [{n.type}] {n.content[:120]}"
            for n in notes[:20]
        )
        sys_prompt = (
            "你是研究方法导师。基于学生提供的研究问题和阅读笔记，"
            "识别已有文献尚未充分覆盖的 2-3 个研究空白（gap）。\n"
            "每个 gap 输出 3 行：\n"
            "1. 简述（1 句，≤50 字）\n"
            "2. 建议方向（1 句，≤80 字）\n"
            "3. 置信度（0.0-1.0）\n"
            "用 `===` 分隔多个 gap。"
        )
        user_msg = (
            f"研究问题：{research_q}\n\n"
            f"已有阅读笔记：\n{notes_summary or '（暂无笔记）'}"
        )
        messages = build_tutor_messages(sys_prompt, [], user_msg)
        response = llm_chat(
            messages,
            temperature=0.3,
            llm_config=llm_config,
            requests_module=requests_module,
            retries=0,
        )
        if not response.ok:
            return []
        return _parse_llm_gap_response(response.content)
    except (LLMUnavailableError, Exception):
        return []


def _parse_llm_gap_response(text: str) -> List[GapAnalysis]:
    """解析 LLM 输出（按 === 分隔的 3 行格式）。"""
    if not text:
        return []
    gaps: List[GapAnalysis] = []
    for block in text.split("==="):
        lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        desc = lines[0].lstrip("0123456789. ")
        direction = lines[1].lstrip("0123456789. ") if len(lines) > 1 else ""
        confidence = 0.5
        if len(lines) >= 3:
            try:
                # 提取数字
                m = re.search(r"([\d.]+)", lines[2])
                if m:
                    confidence = max(0.0, min(1.0, float(m.group(1))))
            except Exception:
                pass
        gaps.append(GapAnalysis(
            gap_description=desc[:200],
            suggested_direction=direction[:200],
            confidence=confidence,
            source="llm",
        ))
    return gaps


def generate_gap_report(gaps: List[GapAnalysis]) -> str:
    """导出 gap 分析为 Markdown 报告。"""
    if not gaps:
        return "# Gap 分析报告\n\n（暂未识别到研究空白）\n"
    lines = ["# Gap 分析报告", ""]
    for i, g in enumerate(gaps, 1):
        lines.append(f"## Gap {i}")
        lines.append("")
        lines.append(f"**描述**：{g.gap_description}")
        lines.append("")
        if g.supporting_notes:
            lines.append("**支撑证据**：")
            for n in g.supporting_notes:
                lines.append(f"  - {n}")
            lines.append("")
        if g.suggested_direction:
            lines.append(f"**建议方向**：{g.suggested_direction}")
            lines.append("")
        lines.append(f"_置信度：{g.confidence:.0%}　来源：{g.source}_")
        lines.append("")
    return "\n".join(lines)
