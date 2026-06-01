"""研究方法加权词表加载器（与 domain_weights 平行的扁平版）。

YAML schema (data/literature_feed/method_weights.yaml)::

    version: 1
    default_weight: 1.0
    method_multiplier: 1.5
    methods:
      - canonical: 纵向设计
        synonyms: [longitudinal design, 纵向研究]

设计决策：
- 同义词命中 → canonical 命中（不重复计分）
- 不分子域（与 IO/HR/OB 三域不同），方法是单层概念
- 词表外的 keyword 默认权重 1.0，不加权但不阻拦其他打分
- 用法：在 priority_score 公式里多乘 (1 + method_score)，与 domain_score 并列
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

_DEFAULT_MULTIPLIER = 1.5
_DEFAULT_WEIGHT = 1.0


@dataclass(frozen=True)
class MethodWeights:
    """不可变方法加权词表。canonical → multiplier 的查表在加载时构建。"""

    version: int
    default_weight: float
    method_multiplier: float
    # 保留原始结构供 UI 编辑
    methods: Tuple[Tuple[str, Tuple[str, ...]], ...] = field(default_factory=tuple)
    # 反向索引：canonical_lower → canonical
    _index: Mapping[str, str] = field(default_factory=dict, repr=False)
    # 反向索引：synonym_lower → canonical
    _syn_index: Mapping[str, str] = field(default_factory=dict, repr=False)

    # ------------------------------ 构造 ------------------------------ #

    @classmethod
    def from_yaml_path(cls, path: Path) -> "MethodWeights":
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("缺少 PyYAML，无法加载 method_weights.yaml") from exc
        if not Path(path).exists():
            logger.warning("method_weights.yaml 不存在，使用空词表：%s", path)
            return cls.empty()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_mapping(data)

    @classmethod
    def from_mapping(cls, data: Mapping) -> "MethodWeights":
        version = int(data.get("version", 1) or 1)
        default_weight = float(data.get("default_weight", _DEFAULT_WEIGHT) or _DEFAULT_WEIGHT)
        method_multiplier = float(
            data.get("method_multiplier", _DEFAULT_MULTIPLIER) or _DEFAULT_MULTIPLIER
        )
        methods_raw = data.get("methods") or []

        seq: List[Tuple[str, Tuple[str, ...]]] = []
        index: Dict[str, str] = {}
        syn_index: Dict[str, str] = {}

        for entry in methods_raw:
            if not isinstance(entry, dict):
                continue
            canonical = (entry.get("canonical") or "").strip()
            if not canonical:
                continue
            synonyms_raw = entry.get("synonyms") or []
            synonyms = tuple(
                s.strip() for s in synonyms_raw if isinstance(s, str) and s.strip()
            )
            seq.append((canonical, synonyms))
            key = canonical.lower()
            if key not in index:
                index[key] = canonical
            for syn in synonyms:
                syn_key = syn.lower()
                if syn_key not in syn_index:
                    syn_index[syn_key] = canonical
            if key not in syn_index:
                syn_index[key] = canonical

        return cls(
            version=version,
            default_weight=default_weight,
            method_multiplier=method_multiplier,
            methods=tuple(seq),
            _index=index,
            _syn_index=syn_index,
        )

    @classmethod
    def empty(cls) -> "MethodWeights":
        return cls(
            version=1,
            default_weight=_DEFAULT_WEIGHT,
            method_multiplier=_DEFAULT_MULTIPLIER,
            methods=(),
            _index={},
            _syn_index={},
        )

    # ------------------------------ 查询 ------------------------------ #

    def is_method(self, term: str) -> bool:
        """该词条是否为已配置的方法（canonical 或 同义词命中）。"""
        if not term:
            return False
        key = term.strip().lower()
        if not key:
            return False
        return key in self._index or key in self._syn_index

    def canonical_for(self, term: str) -> Optional[str]:
        """同义词或 canonical 都映射到 canonical；未知返回 None。"""
        if not term:
            return None
        key = term.strip().lower()
        if key in self._index:
            return self._index[key]
        return self._syn_index.get(key)

    def multiplier_for(self, term: str) -> float:
        """命中已配置方法 → method_multiplier；其他 → default_weight。"""
        return self.method_multiplier if self.is_method(term) else self.default_weight

    def score_hits(self, hits: Iterable[str]) -> float:
        """把命中的方法词条集合转成 method_score。

        method_score = Σ (method_multiplier - default_weight) per unique canonical hit。
        - 0 命中 → 0
        - 1 命中 → 0.5（默认配置）
        - 2 命中 → 1.0
        - canonical 与同义词只计一次
        """
        seen = set()
        total = 0.0
        for term in hits or []:
            canonical = self.canonical_for(term) or term
            key = canonical.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            mult = self.multiplier_for(canonical)
            total += max(0.0, mult - self.default_weight)
        return total

    def flat_synonyms(self) -> Dict[str, List[str]]:
        """返回 {canonical: [synonyms...]}，与 extract_iohr_hits 现有签名兼容。

        用法：method_weights.flat_synonyms() 直接喂给 extract_iohr_hits 复用扫描逻辑。
        """
        return {canonical: list(synonyms) for canonical, synonyms in self.methods}

    def all_canonical(self) -> List[str]:
        """列出所有 method canonical。"""
        return [canonical for canonical, _ in self.methods]
