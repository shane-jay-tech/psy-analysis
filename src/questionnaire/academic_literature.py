"""学术文献集成：查询真实量表 → 增强问卷设计的学术性和标准性

数据来源：
  1. Crossref API — 学术期刊中的量表开发与验证文献
  2. 内置构念库 — 每个构念已记录的 established_scales 和 references
  3. 扩展构念库 — construct_kb_extended.EXTENDED_CONSTRUCTS（用户编辑追加）

缓存策略：Crossref结果缓存7天，内置KB查询即时。
"""

import json
import time
import hashlib
import urllib.request
import urllib.parse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CACHE_DIR = Path(__file__).parent / ".academic_cache"
CACHE_DIR.mkdir(exist_ok=True)

API_TIMEOUT = 15
CACHE_TTL = 604800  # 7天


def search_established_scales(
    construct_name: str,
    domain: str = "",
    max_results: int = 8,
) -> List[Dict]:
    """
    搜索与构念相关的真实量表文献。

    返回：
    [
      {
        "scale_name": "量表名称",
        "authors": ["作者1", "作者2"],
        "year": "2020",
        "journal": "期刊名",
        "doi": "10.xxxx/xxxxx",
        "n_items": 24,
        "n_dimensions": 4,
        "reliability": {"alpha": 0.89, "test_retest": None},
        "validity": {"cfa_cfi": 0.93, "cfa_rmsea": 0.06},
        "sample_size": 500,
        "population": "大学生",
        "language": "中文/英文",
        "abstract": "摘要...",
        "reference_apa7": "APA7引用",
        "source": "crossref" / "builtin_kb",
        "credibility": 0.9,
        "has_full_items": False,
      },
      ...
    ]
    """
    results = []

    # ---- 第1来源：内置KB已有的量表记录 ----
    from .construct_kb import CONSTRUCTS
    from .construct_kb_extended import EXTENDED_CONSTRUCTS

    all_kb = {**CONSTRUCTS, **EXTENDED_CONSTRUCTS}
    if construct_name in all_kb:
        entry = all_kb[construct_name]
        for scale_ref in entry.get("established_scales", []):
            results.append(_parse_scale_ref(scale_ref, entry, "builtin_kb"))
        # 添加参考文献中的量表信息
        for ref in entry.get("references", []):
            parsed = _parse_reference_for_scale(ref)
            if parsed:
                parsed["source"] = "builtin_kb"
                parsed["credibility"] = 1.0
                results.append(parsed)

    # ---- 第2来源：Crossref API搜索 ----
    cache_key = hashlib.md5(
        f"scales:{construct_name}:{domain}".encode()
    ).hexdigest()
    cache_file = CACHE_DIR / f"scales_{cache_key}.json"

    api_results = []
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - cached.get("timestamp", 0) < CACHE_TTL:
                api_results = cached.get("results", [])
        except Exception:
            pass

    if not api_results:
        try:
            api_results = _search_crossref_scales(construct_name, domain, max_results)
            cache_file.write_text(
                json.dumps({
                    "timestamp": time.time(),
                    "results": api_results,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            api_results = []

    for r in api_results:
        r["source"] = "crossref"
        r["credibility"] = 0.9
        results.append(r)

    # 去重（按scale_name + year）
    seen = set()
    deduped = []
    for r in results:
        key = (r.get("scale_name", ""), r.get("year", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped


def get_academic_reference_for_construct(
    construct_name: str,
    domain: str = "",
) -> Dict:
    """
    获取构念的学术文献增强包。

    返回与 design_questionnaire() 兼容的增强字段：
    {
      "established_scales": [...],
      "academic_references_apa7": [...],
      "scale_reliability_norms": {...},
      "recommended_item_count": int,  # 基于已发表量表的题量建议
      "academic_source_count": int,
      "search_timestamp": float,
    }
    """
    scales = search_established_scales(construct_name, domain)

    if not scales:
        return {
            "established_scales": [],
            "academic_references_apa7": [],
            "scale_reliability_norms": {},
            "recommended_item_count": 15,
            "academic_source_count": 0,
            "search_timestamp": time.time(),
        }

    refs = []
    for s in scales:
        ref = s.get("reference_apa7", "")
        if ref and ref not in refs:
            refs.append(ref)

    # 汇总信度常模
    alphas = []
    sample_sizes = []
    item_counts = []
    for s in scales:
        rel = s.get("reliability", {})
        if rel and rel.get("alpha"):
            alphas.append(rel["alpha"])
        if s.get("sample_size"):
            sample_sizes.append(s["sample_size"])
        if s.get("n_items"):
            item_counts.append(s["n_items"])

    reliability_norms = {
        "mean_alpha": round(sum(alphas) / len(alphas), 3) if alphas else None,
        "alpha_range": f"{min(alphas):.2f}-{max(alphas):.2f}" if alphas else "未知",
        "total_studies": len(scales),
        "total_sample": sum(sample_sizes) if sample_sizes else None,
        "typical_n_items": int(sum(item_counts) / len(item_counts)) if item_counts else 15,
    }

    recommended_items = int(sum(item_counts) / len(item_counts)) if item_counts else 15
    # 限制在合理范围
    recommended_items = max(8, min(recommended_items, 60))

    return {
        "established_scales": [
            {
                "name": s.get("scale_name", ""),
                "authors": s.get("authors", []),
                "year": s.get("year", ""),
                "doi": s.get("doi", ""),
                "n_items": s.get("n_items", 0),
                "alpha": (s.get("reliability") or {}).get("alpha"),
                "source": s.get("source", "unknown"),
                "credibility": s.get("credibility", 0.5),
            }
            for s in scales
        ],
        "academic_references_apa7": refs,
        "scale_reliability_norms": reliability_norms,
        "recommended_item_count": recommended_items,
        "academic_source_count": len(scales),
        "search_timestamp": time.time(),
    }


def generate_academic_report(
    construct_name: str,
    academic_data: Dict,
) -> str:
    """
    基于学术文献数据生成中文报告。

    包含：已有量表概览、信度常模、题量建议、学术参考。
    """
    if not academic_data or not academic_data.get("established_scales"):
        return (
            f"⚠ 未找到「{construct_name}」的相关已发表量表。\n"
            "问卷将基于通用测量学原则生成，建议在研究完成后进行全面的信效度检验。"
        )

    scales = academic_data["established_scales"]
    norms = academic_data.get("scale_reliability_norms", {})
    refs = academic_data.get("academic_references_apa7", [])

    lines = [
        f"## 「{construct_name}」学术文献报告\n",
        f"### 已有量表概览\n",
        f"共检索到 **{len(scales)}** 个已发表的测量工具：\n",
    ]

    for i, s in enumerate(scales, 1):
        name = s.get("name", "未知名量表")
        authors = ", ".join(s.get("authors", [])[:3])
        year = s.get("year", "")
        n_items = s.get("n_items", "?")
        alpha = s.get("alpha")
        doi = s.get("doi", "")
        cred = s.get("credibility", 0.5)
        source_label = "学术API" if cred >= 0.9 else ("内置KB" if cred >= 0.8 else "文献引用")

        lines.append(f"**{i}. {name}** ({authors}, {year})")
        lines.append(f"   - 题目数：{n_items}题")
        if alpha:
            lines.append(f"   - Cronbach's α = {alpha}")
        if doi:
            lines.append(f"   - DOI: [{doi}](https://doi.org/{doi})")
        lines.append(f"   - 来源：{source_label}")
        lines.append("")

    if norms.get("mean_alpha"):
        lines.append(f"### 信度常模")
        lines.append(f"- 平均 Cronbach's α：**{norms['mean_alpha']}**")
        lines.append(f"- α 范围：{norms['alpha_range']}")
        lines.append(f"- 汇总样本量：{norms.get('total_sample', 'N/A')}")
        lines.append(f"- 典型题目数：{norms.get('typical_n_items', 'N/A')}题")
        lines.append("")

    lines.append(f"### 建议")
    lines.append(
        f"- 推荐题目数：**{norms.get('typical_n_items', 15)}**题 "
        f"（基于已发表量表的平均值）"
    )
    lines.append(
        f"- 预期 Cronbach's α ≥ {max(0.70, (norms.get('mean_alpha') or 0.85) - 0.05):.2f}"
    )
    lines.append("")

    if refs:
        lines.append("### APA7 参考文献")
        for i, ref in enumerate(refs[:10], 1):
            lines.append(f"{i}. {ref}")
        lines.append("")

    return "\n".join(lines)


# ===========================================================================
# 内部实现
# ===========================================================================


def _parse_scale_ref(ref_text: str, entry: Dict, source: str) -> Dict:
    """解析 established_scales 条目为结构化数据"""
    # 格式如: "心理资本问卷 (PCQ-24; Luthans et al., 2007) — 24题"
    match = re.match(r"(.+?)\s*[\(（](.+?)[\)）]\s*[—–-]*\s*(\d+)?.*", ref_text)
    if match:
        name = match.group(1).strip()
        rest = match.group(2)
        n_items = int(match.group(3)) if match.group(3) else None
        year_match = re.search(r"(\d{4})", rest)
        year = year_match.group(1) if year_match else ""
        authors = rest.split(";")[0].strip() if ";" in rest else rest
        refs = entry.get("references", [])
        reliability = {}
        sample_size = None
        for ref in refs:
            if name.split("(")[0].strip()[:5] in ref:
                alpha_match = re.search(r"[αα]\s*[=＝]?\s*(0?\.\d+)", ref)
                if alpha_match:
                    reliability["alpha"] = float(alpha_match.group(1))
                n_match = re.search(r"[Nn]\s*[=＝]?\s*(\d+)", ref)
                if n_match:
                    sample_size = int(n_match.group(1))
        return {
            "scale_name": name,
            "authors": [authors],
            "year": year,
            "n_items": n_items,
            "reliability": reliability,
            "sample_size": sample_size,
            "source": source,
            "credibility": 1.0 if source == "builtin_kb" else 0.9,
            "reference_apa7": refs[0] if refs else ref_text,
        }
    return {"scale_name": ref_text, "source": source, "credibility": 1.0}


def _parse_reference_for_scale(ref_text: str) -> Optional[Dict]:
    """从APA7参考文献中解析量表信息"""
    # 格式: "Luthans, F., ... (2007). Psychological capital... Oxford."
    match = re.match(r"(.+?)\s*[\(（](\d{4})[\)）]", ref_text)
    if not match:
        return None
    authors = match.group(1).strip()
    year = match.group(2)
    # 提取标题
    title_match = re.search(r"[\)）]\.\s*(.+?)(?:\s*\.\s*(?:Oxford|New York|London|Springer|Elsevier|Routledge|Sage|Wiley|Taylor|Francis|APA|American|McGraw|Jossey))", ref_text)
    title = title_match.group(1).strip() if title_match else ""
    if len(title) < 5:
        return None
    return {
        "scale_name": title[:60],
        "authors": [a.strip() for a in authors.split(",")[:3]],
        "year": year,
        "reference_apa7": ref_text,
        "source": "builtin_kb",
        "credibility": 1.0,
    }


def _search_crossref_scales(
    construct_name: str, domain: str = "", max_results: int = 8
) -> List[Dict]:
    """通过 Crossref API 搜索量表开发和验证文献"""
    query_parts = [construct_name, "scale", "validation", "psychometric"]
    if domain:
        query_parts.insert(1, domain)
    query = " ".join(query_parts)
    encoded = urllib.parse.quote(query)

    url = (
        f"https://api.crossref.org/works"
        f"?query={encoded}"
        f"&rows={max_results}"
        f"&filter=type:journal-article"
        f"&sort=relevance"
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PsyAnalysis/2.0 (mailto:research@example.com; Academic tool)",
        },
    )

    results = []
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for item in data.get("message", {}).get("items", []):
            parsed = _parse_crossref_item(item)
            if parsed:
                results.append(parsed)
    except Exception:
        pass

    return results


def _parse_crossref_item(item: Dict) -> Optional[Dict]:
    """解析单个 Crossref 条目为量表信息"""
    title = (item.get("title") or [""])[0]
    if not title:
        return None
    # 过滤：标题需包含量表/测量相关词
    scale_keywords = [
        "scale", "inventory", "questionnaire", "measure", "assessment",
        "量表", "问卷", "测量", "评定",
    ]
    has_scale_kw = any(kw.lower() in title.lower() for kw in scale_keywords)
    if not has_scale_kw:
        return None

    doi = item.get("DOI", "")
    publisher = item.get("publisher", "")
    container = (item.get("container-title") or [""])[0]

    # 作者
    authors_data = item.get("author", [])
    author_names = []
    for a in authors_data[:5]:
        family = a.get("family", "")
        given = a.get("given", "")
        if family:
            author_names.append(f"{family}, {given}" if given else family)

    # 年份
    date_parts = (
        item.get("published-print", {})
        or item.get("published-online", {})
        or item.get("created", {})
        or {}
    ).get("date-parts", [[None]])[0]
    year = str(date_parts[0]) if date_parts and date_parts[0] else ""

    # 构建APA7引用
    first_author = author_names[0] if author_names else ""
    ref_apa7 = f"{first_author} ({year}). {title}. {container}."
    if doi:
        ref_apa7 += f" https://doi.org/{doi}"

    # 尝试从标题/摘要中提取n_items和alpha
    abstract = item.get("abstract", "")
    n_items = None
    alpha_val = None
    combined = f"{title} {abstract}"

    item_match = re.search(r"(\d+)[-–\s]*items?", combined, re.IGNORECASE)
    if item_match:
        n_items = int(item_match.group(1))

    alpha_match = re.search(r"[αα]\s*[=＝]\s*(0?\.\d+)", combined)
    if alpha_match:
        alpha_val = float(alpha_match.group(1))

    return {
        "scale_name": _truncate(title, 120),
        "authors": author_names[:5],
        "year": year,
        "journal": container,
        "doi": doi,
        "n_items": n_items,
        "reliability": {"alpha": alpha_val} if alpha_val else {},
        "abstract": _truncate(abstract, 300),
        "reference_apa7": ref_apa7,
    }


def _truncate(text: str, max_len: int) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text
