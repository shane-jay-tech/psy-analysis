"""趋势聚合 + IO/HR/OB 加权 + 方法加权（Phase 4d / Round 2）。

公开入口：
- DomainWeights / load_default_weights：YAML 加载 + 同义词查询（IO/HR/OB 三域）
- MethodWeights / load_default_method_weights：YAML 加载 + 同义词查询（研究方法扁平词表）
- compute_recency_decay / compute_priority_score：候选打分（方法加权可选）
- update_candidate_scores：批量回填 priority_score（方法加权可选）
- compute_keyword_trends / TrendRow / compute_domain_summary：关键词趋势聚合

数据路径：data/literature_feed/{domain,method}_weights.yaml（D 盘）。UI 设置页可编辑。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..paths import DOMAIN_WEIGHTS_PATH, METHOD_WEIGHTS_PATH, TRENDING_WEIGHTS_PATH
from .aggregator import (
    TrendRow,
    compute_domain_summary,
    compute_keyword_trends,
)
from .domain_weights import DomainWeights
from .method_weights import MethodWeights
from .trending_weights import (
    TrendingEntry,
    TrendingWeights,
    compute_trending_weights,
    load_default_trending,
    load_trending_weights,
    write_trending_yaml,
)
from .scorer import (
    DEFAULT_HALF_LIFE_DAYS,
    compute_domain_score,
    compute_method_score,
    compute_priority_score,
    compute_recency_decay,
    update_candidate_scores,
)

DOMAIN_WEIGHTS_FILENAME = "domain_weights.yaml"
TRENDING_WEIGHTS_FILENAME = "trending_weights.yaml"
METHOD_WEIGHTS_FILENAME = "method_weights.yaml"


def default_weights_path() -> Path:
    return DOMAIN_WEIGHTS_PATH


def load_default_weights(path: Optional[Path] = None) -> DomainWeights:
    """加载 D:\\code\\psy-analysis\\data\\literature_feed\\domain_weights.yaml。"""
    return DomainWeights.from_yaml_path(path or default_weights_path())


def default_method_weights_path() -> Path:
    return METHOD_WEIGHTS_PATH


def load_default_method_weights(path: Optional[Path] = None) -> MethodWeights:
    """加载 D:\\code\\psy-analysis\\data\\literature_feed\\method_weights.yaml。"""
    return MethodWeights.from_yaml_path(path or default_method_weights_path())


__all__ = [
    "DomainWeights",
    "MethodWeights",
    "TrendingEntry",
    "TrendingWeights",
    "TrendRow",
    "DEFAULT_HALF_LIFE_DAYS",
    "DOMAIN_WEIGHTS_FILENAME",
    "METHOD_WEIGHTS_FILENAME",
    "compute_domain_score",
    "compute_domain_summary",
    "compute_keyword_trends",
    "compute_method_score",
    "compute_priority_score",
    "compute_recency_decay",
    "default_method_weights_path",
    "default_weights_path",
    "load_default_method_weights",
    "load_default_trending",
    "load_default_weights",
    "load_trending_weights",
    "update_candidate_scores",
    "write_trending_yaml",
    "compute_trending_weights",
    "default_trending_path",
    "TRENDING_WEIGHTS_FILENAME",
]
