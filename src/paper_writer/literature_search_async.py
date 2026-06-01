"""论文写作模块 — 文献搜索异步包装器

将耗时的在线文献搜索（Crossref API）封装为异步调用，
支持取消机制，避免阻塞 Streamlit 主线程。
"""

import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import List, Dict, Optional

from .literature_manager import LiteratureManager

# 模块级线程池
_search_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lit_search")

# 取消标志池
cancel_flags: dict = {}
_cancel_lock = threading.Lock()
_next_cancel_id = 0


class CancelledSearchError(Exception):
    """搜索请求已被用户取消"""


def _alloc_cancel_id() -> int:
    global _next_cancel_id
    with _cancel_lock:
        cid = _next_cancel_id
        _next_cancel_id += 1
        cancel_flags[cid] = False
        return cid


def cancel_search_request(cancel_id: int) -> bool:
    """标记指定搜索请求为已取消。"""
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


def search_literature_with_online(
    keywords: List[str],
    topic: str = "",
    include_online: bool = True,
    cancel_id: Optional[int] = None,
) -> List[Dict]:
    """同步执行：先搜索预置库，再在线搜索（可选）。

    参数：
        keywords: 搜索关键词列表
        topic: 研究主题（用于在线搜索查询）
        include_online: 是否包含在线搜索（Crossref）
        cancel_id: 取消标识符

    返回：
        文献字典列表
    """
    manager = LiteratureManager()

    # 1. 预置库搜索（快速，同步）
    preset_results = manager.search_presets(keywords, n=8)
    results = [
        {
            "key": e.key,
            "authors": e.authors,
            "year": e.year,
            "title": e.title,
            "journal": e.journal,
            "is_chinese": e.is_chinese,
            "source": e.source,
            "relevance": e.relevance_note,
        }
        for e in preset_results
    ]

    if cancel_id is not None and _is_cancelled(cancel_id):
        raise CancelledSearchError("文献搜索已被取消")

    # 2. 在线搜索（耗时，可选）
    if include_online:
        try:
            query = f"{topic} {' '.join(keywords)} 心理学" if topic else " ".join(keywords)
            online_results = manager.search_online(query, n=5)
            for or_ in online_results:
                construct = or_.get("construct", {})
                if construct:
                    ref = construct.get("reference", "")
                    if ref:
                        results.append({
                            "key": f"online_{hashlib.md5(ref.encode()).hexdigest()[:8]}",
                            "authors": construct.get("authors", []),
                            "year": construct.get("year", ""),
                            "title": construct.get("title", ""),
                            "journal": construct.get("journal", ""),
                            "is_chinese": any(
                                "一" <= c <= "鿿" for c in construct.get("title", "")
                            ),
                            "source": "crossref",
                            "relevance": "在线检索文献，需人工审核",
                        })
        except Exception:
            pass

    return results


def search_literature_async(
    keywords: List[str],
    topic: str = "",
    include_online: bool = True,
) -> dict:
    """异步执行文献搜索。

    返回 {"future": Future, "cancel_id": int}，供UI层取消使用。
    """
    cancel_id = _alloc_cancel_id()
    future = _search_executor.submit(
        search_literature_with_online,
        keywords,
        topic,
        include_online,
        cancel_id,
    )

    def _cleanup(_):
        _cleanup_cancel_id(cancel_id)

    future.add_done_callback(_cleanup)
    return {"future": future, "cancel_id": cancel_id}


import hashlib  # noqa: E402
