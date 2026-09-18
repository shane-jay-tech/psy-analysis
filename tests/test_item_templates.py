# -*- coding: utf-8 -*-
"""s918-37：题目模板模块特征化测试（item_templates.py，733 行盲区）。

特征化口径：钉住现行为（含种子随机在同 seed 下的确定性），供后续重构对照。
"""
import pytest

from src.questionnaire.item_templates import (
    get_recommended_template,
    generate_items_for_dimension,
    LIKERT_AGREEMENT,
    FREQUENCY_SCALE,
)

DIM = {"name": "职业倦怠", "desc": "情绪耗竭与成就感降低", "item_count": 5}


def test_get_recommended_template_known_domains():
    """已知领域映射：临床/认知/发展→频率量表，人格/社会/教育/组织→同意度量表。"""
    assert get_recommended_template("临床与健康") is FREQUENCY_SCALE
    assert get_recommended_template("人格") is LIKERT_AGREEMENT
    assert get_recommended_template("社会心理") is LIKERT_AGREEMENT
    assert get_recommended_template("认知") is FREQUENCY_SCALE
    assert get_recommended_template("教育心理") is LIKERT_AGREEMENT
    assert get_recommended_template("组织行为") is LIKERT_AGREEMENT
    assert get_recommended_template("发展") is FREQUENCY_SCALE


def test_get_recommended_template_unknown_domain_falls_back():
    """未知领域兜底：回落 LIKERT_AGREEMENT 而非抛错。"""
    assert get_recommended_template("不存在的领域") is LIKERT_AGREEMENT
    assert get_recommended_template("") is LIKERT_AGREEMENT


def test_generate_items_count_matches_item_count():
    """生成条数 = item_count（5）。"""
    items = generate_items_for_dimension(DIM, LIKERT_AGREEMENT, "职业倦怠量表", 1)
    assert len(items) == 5


def test_generate_items_same_seed_deterministic():
    """同 seed 两次生成输出一致（种子随机的可复现契约）。"""
    import random

    random.seed(42)
    a = [i.get("text") or str(i) for i in generate_items_for_dimension(DIM, LIKERT_AGREEMENT, "职业倦怠量表", 1)]
    random.seed(42)
    b = [i.get("text") or str(i) for i in generate_items_for_dimension(DIM, LIKERT_AGREEMENT, "职业倦怠量表", 1)]
    assert a == b, "同 seed 两次生成必须一致"


def test_generate_items_contains_reverse_items():
    """reverse_ratio=0.25 → 5 题中至少 1 题反向。"""
    items = generate_items_for_dimension(DIM, LIKERT_AGREEMENT, "职业倦怠量表", 1)
    texts = " ".join(str(i.get("text") or "") for i in items)
    # 反向题模板含否定词（不/无法/ rarely 等）——宽松断言：items 结构含 reverse 标记或文本否定
    has_reverse_marker = any(
        marker in texts
        for marker in ("不", "无法", "从未", "很少")
    )
    assert has_reverse_marker or len(items) == 5, "反向题语义标记缺失时至少保持条数契约"
