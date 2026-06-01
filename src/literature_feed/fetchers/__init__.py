"""抓取层：source-aware fetchers + 共享基类。

每个 fetcher 实现 ``SourceFetcher`` 接口；调度器并行调用，按 source 隔离失败。
"""

from .base import (
    FetchResult,
    RawArticle,
    SourceFetcher,
    SourceConfig,
    FetchError,
    SchemaChangedError,
    RateLimitedError,
)

__all__ = [
    "FetchResult",
    "RawArticle",
    "SourceFetcher",
    "SourceConfig",
    "FetchError",
    "SchemaChangedError",
    "RateLimitedError",
]
