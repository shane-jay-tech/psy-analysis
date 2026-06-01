"""知识库搜索：优先查询Crossref API → 降级为LLM搜索

数据来源优先级：
1. Crossref API（academic_api）— 真实学术文献元数据 → 缓存7天
2. LLM生成（llm_generated）— 训练知识推断 → 缓存24小时
"""

import time
import json
import hashlib
import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple

CACHE_DIR = Path(__file__).parent / ".kb_cache"
CACHE_DIR.mkdir(exist_ok=True)

# 不同来源的缓存TTL
CACHE_TTL = {
    "academic_api": 604800,   # 7天
    "llm_generated": 86400,   # 24小时
    "unknown": 86400,         # 默认24小时
}

# API请求超时
API_TIMEOUT = 15  # 秒


def search_literature(
    construct_name: str,
    domain: str = "",
    prefer_api: bool = True,
) -> List[Dict]:
    """
    搜索与指定构念相关的学术文献。

    参数：
        construct_name: 构念名称（中文）
        domain: 所属领域（可选，辅助搜索）
        prefer_api: 是否优先使用真实学术API（默认True）

    返回：
        [{"source": "academic_api", "construct": {...}, "doi": "...", "timestamp": ...}, ...]
    """
    results = []

    # ========== 第1优先级：Crossref API ==========
    if prefer_api:
        # 检查缓存
        api_results = []
        cache_key_api = hashlib.md5(f"crossref:{construct_name}:{domain}".encode()).hexdigest()
        cache_file_api = CACHE_DIR / f"api_{cache_key_api}.json"

        if cache_file_api.exists():
            try:
                cached = json.loads(cache_file_api.read_text(encoding="utf-8"))
                if time.time() - cached.get("timestamp", 0) < CACHE_TTL["academic_api"]:
                    api_results = cached.get("results", [])
            except Exception:
                pass

        if not api_results:
            try:
                api_results = _search_crossref(construct_name, domain)
                cache_file_api.write_text(
                    json.dumps({
                        "timestamp": time.time(),
                        "results": api_results,
                        "source": "academic_api",
                    }, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception:
                api_results = []

        if api_results:
            results.extend(api_results)

    # ========== 第2优先级：LLM（降级） ==========
    if not results or not prefer_api:
        cache_key_llm = hashlib.md5(f"llm:{construct_name}:{domain}".encode()).hexdigest()
        cache_file_llm = CACHE_DIR / f"llm_{cache_key_llm}.json"

        llm_results = []
        if cache_file_llm.exists():
            try:
                cached = json.loads(cache_file_llm.read_text(encoding="utf-8"))
                if time.time() - cached.get("timestamp", 0) < CACHE_TTL["llm_generated"]:
                    llm_results = cached.get("results", [])
            except Exception:
                pass

        if not llm_results:
            try:
                llm_results = _search_via_llm(construct_name, domain)
                if llm_results:
                    cache_file_llm.write_text(
                        json.dumps({
                            "timestamp": time.time(),
                            "results": llm_results,
                            "source": "llm_generated",
                        }, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
            except Exception:
                llm_results = []

        if llm_results:
            results.extend(llm_results)

    return results


# ===========================================================================
# Crossref API 搜索
# ===========================================================================

def _search_crossref(construct_name: str, domain: str = "") -> List[Dict]:
    """
    通过 Crossref API (https://api.crossref.org/works) 搜索学术文献。

    查询策略：使用中英文关键词组合搜索。
    响应字段：title, author, published, container-title, DOI, abstract, subject
    """
    import urllib.request
    import urllib.parse

    # 构建查询：构念名 + psychology + scale/measurement
    query_terms = [construct_name]
    if domain:
        query_terms.append(domain)
    # 添加心理学相关术语以过滤
    query_terms.append("psychology")

    # 尝试中英文
    query = " ".join(query_terms)
    encoded_query = urllib.parse.quote(query)

    url = f"https://api.crossref.org/works?query={encoded_query}&rows=5&filter=type:journal-article"
    # 礼貌标识：Crossref要求提供User-Agent
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PsyAnalysis/2.0 (mailto:research@example.com; Academic research tool)",
        },
    )

    results = []

    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        items = data.get("message", {}).get("items", [])
        if not items:
            return results

        for item in items:
            try:
                title = item.get("title", [""])[0] if item.get("title") else ""
                doi = item.get("DOI", "")
                publisher = item.get("publisher", "")
                container = item.get("container-title", [""])[0] if item.get("container-title") else ""
                abstract = item.get("abstract", "")

                # 作者
                authors = item.get("author", [])
                author_names = []
                for a in authors[:5]:
                    family = a.get("family", "")
                    given = a.get("given", "")
                    if family:
                        author_names.append(f"{family}, {given}" if given else family)
                first_author = author_names[0] if author_names else ""

                # 出版年份
                published = item.get("published-print", {}) or item.get("published-online", {}) or {}
                year = ""
                date_parts = published.get("date-parts", [[None]])[0]
                if date_parts and date_parts[0]:
                    year = str(date_parts[0])

                # 主题/关键词
                subjects = item.get("subject", [])

                if not title:
                    continue

                # 提取相关信息
                reference_str = f"{first_author} ({year}). {title}. {container}."
                if doi:
                    reference_str += f" doi:{doi}"

                results.append({
                    "source": "academic_api",
                    "api": "crossref",
                    "doi": doi,
                    "construct": {
                        "name_zh": construct_name,
                        "title": title,
                        "abstract": _truncate(abstract, 500),
                        "authors": author_names,
                        "year": year,
                        "journal": container,
                        "subjects": subjects[:5],
                        "reference": reference_str,
                    },
                    "timestamp": time.time(),
                })
            except Exception:
                continue

    except Exception:
        pass

    return results


# ===========================================================================
# LLM 降级搜索（保持原有逻辑，标注来源为 llm_generated）
# ===========================================================================

def _search_via_llm(construct_name: str, domain: str = "") -> List[Dict]:
    """通过LLM查询文献信息（降级方案）"""
    from config.llm_providers import get_provider_config

    provider = get_provider_config("deepseek")
    if not provider or not provider.get("api_key"):
        return []

    import urllib.request

    prompt = f"""你是一位心理学测量学专家。请为构念「{construct_name}」提供以下信息，用JSON格式回复：

{{
  "name_zh": "{construct_name}",
  "name_en": "英文名称",
  "domain": "{domain or '请推断所属领域'}",
  "definition": "学术定义（50-150字）",
  "dimensions": [
    {{"name": "维度1名称", "desc": "描述", "item_count": 4}},
    {{"name": "维度2名称", "desc": "描述", "item_count": 4}}
  ],
  "established_scales": ["已有量表名 — 题目数"],
  "references": ["作者 (年份). 标题. 期刊."],
  "typical_scale": "推荐的量表格式"
}}

请确保：
1. definition基于主流学术文献
2. dimensions基于公认理论结构（2-5个维度）
3. established_scales列出最常用的测量工具
4. references必须是真实的学术文献

只返回JSON，不要加任何解释文字。"""

    try:
        api_data = json.dumps({
            "model": provider.get("model", "deepseek-chat"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 2048,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{provider['base_url']}/chat/completions",
            data=api_data,
            headers={
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        content = data["choices"][0]["message"]["content"]
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            parsed = json.loads(content[json_start:json_end])
            return [{
                "source": "llm_generated",
                "construct": parsed,
                "timestamp": time.time(),
            }]
    except Exception:
        pass

    return []


# ===========================================================================
# 验证与缓存管理
# ===========================================================================

def verify_by_doi(doi: str) -> Optional[Dict]:
    """
    通过DOI从Crossref验证条目真实性。
    返回文献元数据，或None（无法验证时）。
    """
    import urllib.request
    import urllib.parse

    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PsyAnalysis/2.0 (mailto:research@example.com)",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data.get("message", {})
        return {
            "doi": doi,
            "title": msg.get("title", [""])[0] if msg.get("title") else "",
            "publisher": msg.get("publisher", ""),
            "year": str(
                (msg.get("published-print", {}) or msg.get("published-online", {}) or {})
                .get("date-parts", [[None]])[0][0] or ""
            ),
            "verified": True,
        }
    except Exception:
        return None


def clear_cache(source: str = None):
    """
    清除搜索缓存。
    source: "academic_api", "llm_generated", 或 None（全部清除）
    """
    if source == "academic_api":
        pattern = "api_*.json"
    elif source == "llm_generated":
        pattern = "llm_*.json"
    else:
        pattern = "*.json"

    for f in CACHE_DIR.glob(pattern):
        f.unlink()
    return True


# ===========================================================================
# 辅助函数
# ===========================================================================

def _truncate(text: str, max_len: int) -> str:
    """截断文本"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)  # 去除HTML标签
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text
