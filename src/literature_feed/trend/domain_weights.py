"""IO/HR/OB 加权词表加载器。

YAML schema (data/literature_feed/domain_weights.yaml)::

    version: 1
    default_weight: 1.0
    domain_multiplier: 1.5
    domains:
      IO:
        concepts:
          - canonical: 变革型领导
            synonyms: [transformational leadership, 变革型]

设计决策：
- 同义词命中 → canonical 命中（不重复计分）
- 一个 canonical 同时落在多个 domain 时，取首个 domain（YAML 顺序为准）
- 词表外的 keyword 默认权重 1.0，依然在趋势里被追踪、不加权
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

_DEFAULT_MULTIPLIER = 1.5
_DEFAULT_WEIGHT = 1.0
_DOMAINS = ("IO", "HR", "OB")


@dataclass(frozen=True)
class DomainWeights:
    """不可变加权词表。canonical → domain 的反向索引在加载时构建。"""

    version: int
    default_weight: float
    domain_multiplier: float
    # 保留原始结构供 UI 编辑
    by_domain: Mapping[str, Tuple[Tuple[str, Tuple[str, ...]], ...]] = field(default_factory=dict)
    # 反向索引：canonical_lower → (canonical, domain)
    _index: Mapping[str, Tuple[str, str]] = field(default_factory=dict, repr=False)
    # 反向索引：synonym_lower → canonical
    _syn_index: Mapping[str, str] = field(default_factory=dict, repr=False)

    # ------------------------------ 构造 ------------------------------ #

    @classmethod
    def from_yaml_path(cls, path: Path) -> "DomainWeights":
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("缺少 PyYAML，无法加载 domain_weights.yaml") from exc
        if not Path(path).exists():
            logger.warning("domain_weights.yaml 不存在，使用空词表：%s", path)
            return cls.empty()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_mapping(data)

    @classmethod
    def from_mapping(cls, data: Mapping) -> "DomainWeights":
        version = int(data.get("version", 1) or 1)
        default_weight = float(data.get("default_weight", _DEFAULT_WEIGHT) or _DEFAULT_WEIGHT)
        domain_multiplier = float(data.get("domain_multiplier", _DEFAULT_MULTIPLIER) or _DEFAULT_MULTIPLIER)
        domains_raw = data.get("domains") or {}

        by_domain: Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]] = {}
        index: Dict[str, Tuple[str, str]] = {}
        syn_index: Dict[str, str] = {}

        for dom_key in _DOMAINS:
            block = domains_raw.get(dom_key) or {}
            concepts = block.get("concepts") or []
            seq: List[Tuple[str, Tuple[str, ...]]] = []
            for entry in concepts:
                if not isinstance(entry, dict):
                    continue
                canonical = (entry.get("canonical") or "").strip()
                if not canonical:
                    continue
                synonyms_raw = entry.get("synonyms") or []
                synonyms = tuple(s.strip() for s in synonyms_raw if isinstance(s, str) and s.strip())
                seq.append((canonical, synonyms))
                key = canonical.lower()
                # 一个 canonical 落在多个 domain → 首个生效
                if key not in index:
                    index[key] = (canonical, dom_key)
                for syn in synonyms:
                    syn_key = syn.lower()
                    if syn_key not in syn_index:
                        syn_index[syn_key] = canonical
                # 同时把 canonical 自己也作为 synonym 入查表
                if key not in syn_index:
                    syn_index[key] = canonical
            by_domain[dom_key] = tuple(seq)

        return cls(
            version=version,
            default_weight=default_weight,
            domain_multiplier=domain_multiplier,
            by_domain=by_domain,
            _index=index,
            _syn_index=syn_index,
        )

    @classmethod
    def empty(cls) -> "DomainWeights":
        return cls(
            version=1,
            default_weight=_DEFAULT_WEIGHT,
            domain_multiplier=_DEFAULT_MULTIPLIER,
            by_domain={d: () for d in _DOMAINS},
            _index={},
            _syn_index={},
        )

    # ------------------------------ 查询 ------------------------------ #

    def domain_for(self, concept: str) -> Optional[str]:
        """返回 concept 所属 domain（IO/HR/OB），未命中返回 None。

        先查 canonical，再走同义词→canonical→domain。
        """
        if not concept:
            return None
        key = concept.strip().lower()
        if not key:
            return None
        hit = self._index.get(key)
        if hit is not None:
            return hit[1]
        canonical = self._syn_index.get(key)
        if canonical is None:
            return None
        return self._index.get(canonical.lower(), (None, None))[1]

    def canonical_for(self, term: str) -> Optional[str]:
        """同义词或 canonical 都映射到 canonical；未知返回 None。"""
        if not term:
            return None
        key = term.strip().lower()
        if key in self._index:
            return self._index[key][0]
        return self._syn_index.get(key)

    def multiplier_for(self, concept: str) -> float:
        """命中 IO/HR/OB → domain_multiplier；其他 → default_weight。"""
        return self.domain_multiplier if self.domain_for(concept) is not None else self.default_weight

    def score_hits(self, hits: Iterable[str]) -> float:
        """把命中词条集合转成 domain_score。

        domain_score = Σ (multiplier - default_weight) per unique canonical hit。
        - 0 命中 → 0
        - 1 命中 → 0.5（默认配置）
        - 2 命中 → 1.0
        - canonical 重复仅计一次（已在 extract_iohr_hits 去重，但这里再 set 一次）
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
        """返回 {canonical: [synonyms...]}，与 extract_iohr_hits 现有签名兼容。"""
        out: Dict[str, List[str]] = {}
        for dom in _DOMAINS:
            for canonical, synonyms in self.by_domain.get(dom, ()):
                # 合并同 canonical 跨 domain（理论不该发生，防御性）
                if canonical in out:
                    for s in synonyms:
                        if s not in out[canonical]:
                            out[canonical].append(s)
                else:
                    out[canonical] = list(synonyms)
        return out

    def all_canonical(self, *, domain: Optional[str] = None) -> List[str]:
        """列出所有 canonical（可选限定 domain）。"""
        result: List[str] = []
        for dom in _DOMAINS:
            if domain and dom != domain:
                continue
            for canonical, _ in self.by_domain.get(dom, ()):
                result.append(canonical)
        return result
