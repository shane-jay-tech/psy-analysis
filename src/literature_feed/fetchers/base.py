"""SourceFetcher 抽象基类与共享数据类型。

设计：每个具体 fetcher 实现 ``fetch_since(since_date) -> FetchResult``，
返回归一化的 ``RawArticle`` 列表 + 原始 payload（写 JSONL 归档用）。
错误一律走异常分类（``FetchError`` 子类），调度器按 source 隔离。
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# 异常分类
# ---------------------------------------------------------------------------

class FetchError(RuntimeError):
    """通用 fetcher 错误。"""


class SchemaChangedError(FetchError):
    """页面结构变了（解析返回空或缺关键字段）→ UI 标 schema_changed。"""


class RateLimitedError(FetchError):
    """限流（429 / 503 + Retry-After）→ 调度器跳过本次但保留下次。"""

    def __init__(self, message: str = "", retry_after: Optional[int] = None):
        super().__init__(message or "rate limited")
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# DTO
# ---------------------------------------------------------------------------

@dataclass
class RawArticle:
    """归一化后的文章记录（与 ``ArticleRow`` 对齐，但不直接入库）。

    抓取阶段的产物，下一步走 ``csl_normalizer`` 校准 + ``FeedStore.upsert_article``。
    """
    title: str
    source_id: str
    provenance: str                            # "crossref" / "official_site" / "manual"
    authors: List[Dict[str, str]] = field(default_factory=list)
    abstract: Optional[str] = None
    issued_date: Optional[str] = None          # ISO 8601 (YYYY-MM-DD)
    doi: Optional[str] = None
    container_title: Optional[str] = None
    publisher: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    metadata_status: str = "complete"
    raw_payload: Optional[Dict[str, Any]] = None  # 原始结构（写 JSONL）
    raw_hash: Optional[str] = None
    source_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source_id": self.source_id,
            "provenance": self.provenance,
            "authors": list(self.authors),
            "abstract": self.abstract,
            "issued_date": self.issued_date,
            "doi": self.doi,
            "container_title": self.container_title,
            "publisher": self.publisher,
            "keywords": list(self.keywords),
            "metadata_status": self.metadata_status,
            "source_url": self.source_url,
        }


@dataclass
class FetchResult:
    """单次 fetch 的输出（一个 source 一次调用）。"""
    source_id: str
    articles: List[RawArticle] = field(default_factory=list)
    raw_records: List[Dict[str, Any]] = field(default_factory=list)  # 写 JSONL 的原始结构
    probe_signature: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class SourceConfig:
    """单 source 的抓取配置。"""
    source_id: str
    journal_name: str
    fetcher_type: str
    issn: Optional[str] = None
    doi_prefix: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit_seconds: float = 5.0           # 请求间隔
    user_agent: str = "psy-analysis-literature-feed/0.1 (academic; contact: research@psy-analysis.local)"
    contact_email: str = "research@psy-analysis.local"
    extra: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------

class SourceFetcher(abc.ABC):
    """所有 fetcher 都派生自这里。"""

    def __init__(self, config: SourceConfig) -> None:
        self.config = config

    @property
    def source_id(self) -> str:
        return self.config.source_id

    @abc.abstractmethod
    def fetch_since(
        self,
        since_date: Optional[str] = None,
        *,
        limit: int = 20,
    ) -> FetchResult:
        """抓取 ``since_date``（含）之后的文章，最多 ``limit`` 条。"""

    def health_signature(self) -> str:
        """简短的 fetcher 版本/解析器签名，便于检测页面结构变更。"""
        return f"{self.config.fetcher_type}:{self.config.source_id}:v1"
