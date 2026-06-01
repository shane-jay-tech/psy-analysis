"""domain_weights.yaml I/O 种子条目回归（2026-05-30 加）。

验证 4 条新增 canonical：
- IO: 家长式领导 / 伦理型领导 / 工作旺盛感
- OB: 领导-成员交换

包括 canonical 命中、同义词反查、score_hits 加权效果，以及未配置概念
保持默认权重（回归保护）。
"""

from __future__ import annotations

from src.literature_feed.paths import DOMAIN_WEIGHTS_PATH
from src.literature_feed.trend.domain_weights import DomainWeights


def _load() -> DomainWeights:
    return DomainWeights.from_yaml_path(DOMAIN_WEIGHTS_PATH)


def test_new_canonicals_are_loaded_in_correct_domains():
    dw = _load()

    io_canonicals = set(dw.all_canonical(domain="IO"))
    ob_canonicals = set(dw.all_canonical(domain="OB"))

    # IO 新增
    assert "家长式领导" in io_canonicals
    assert "伦理型领导" in io_canonicals
    assert "工作旺盛感" in io_canonicals

    # OB 新增
    assert "领导-成员交换" in ob_canonicals

    # IO 不应误收 OB 那条
    assert "领导-成员交换" not in io_canonicals


def test_synonyms_reverse_lookup_to_correct_domain():
    dw = _load()

    # 家长式领导
    assert dw.domain_for("paternalistic leadership") == "IO"
    assert dw.domain_for("威权领导") == "IO"
    assert dw.domain_for("德行领导") == "IO"

    # 伦理型领导
    assert dw.domain_for("ethical leadership") == "IO"
    assert dw.domain_for("道德型领导") == "IO"

    # 工作旺盛感
    assert dw.domain_for("thriving at work") == "IO"
    assert dw.domain_for("旺盛感") == "IO"

    # LMX
    assert dw.domain_for("LMX") == "OB"
    assert dw.domain_for("leader-member exchange") == "OB"
    assert dw.domain_for("上下级交换") == "OB"


def test_score_hits_includes_new_canonicals():
    dw = _load()

    # 仅传新增的 4 条 canonical（用同义词混入，验证反查也命中）
    new_hits = [
        "paternalistic leadership",   # 家长式领导
        "ethical leadership",          # 伦理型领导
        "thriving at work",            # 工作旺盛感
        "LMX",                         # 领导-成员交换
    ]
    score_new = dw.score_hits(new_hits)

    # 默认配置：multiplier=1.5, default=1.0 → 每个 unique canonical 贡献 0.5
    expected = 0.5 * 4
    assert abs(score_new - expected) < 1e-6, (
        f"4 个新 canonical 应贡献 score={expected}，实际 {score_new}"
    )

    # 同义词去重：把 paternalistic leadership 和 威权领导 同时传入仍只算一次
    deduped = dw.score_hits(new_hits + ["威权领导"])
    assert abs(deduped - score_new) < 1e-6, (
        "canonical+synonym 应在 score_hits 内部去重"
    )


def test_unconfigured_concept_keeps_default_weight():
    """回归保护：本次新增没让随机词条意外被加权。"""
    dw = _load()

    # 一个明确不在词表里的词
    assert dw.domain_for("xyz-not-a-real-construct") is None
    assert dw.multiplier_for("xyz-not-a-real-construct") == dw.default_weight

    # 默认 default_weight 仍是 1.0、multiplier 仍是 1.5（没被改坏）
    assert dw.default_weight == 1.0
    assert dw.domain_multiplier == 1.5
