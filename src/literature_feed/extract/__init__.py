"""LLM 抽取层公开 API。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .extractor import ExtractionError, ExtractionStats, LLMExtractor
from .grounding import parse_llm_json, quote_in_abstract
from .prompts import (
    PROMPT_VERSION,
    build_construct_prompt,
    build_method_prompt,
)

if TYPE_CHECKING:
    from ..storage.budget_tracker import BudgetTracker
    from ..storage.feed_store import FeedStore


def extract_for_article(
    article_id: int,
    *,
    store: "FeedStore",
    budget: "BudgetTracker",
    force: bool = False,
    **kwargs: Any,
) -> ExtractionStats:
    """便捷：临时建一个 LLMExtractor 抽一篇。"""
    return LLMExtractor(store, budget, **kwargs).extract_for_article(article_id, force=force)


__all__ = [
    "LLMExtractor",
    "ExtractionError",
    "ExtractionStats",
    "extract_for_article",
    "PROMPT_VERSION",
    "build_construct_prompt",
    "build_method_prompt",
    "quote_in_abstract",
    "parse_llm_json",
]
