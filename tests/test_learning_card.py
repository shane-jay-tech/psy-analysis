"""src/output/learning_card.py 生成与格式化测试（s918-44）。

纯离线：读内置 `LEARNING_DB`，无网络、无文件、无 Streamlit。
锚点：src/output/learning_card.py:13 class LearningCard、:1652 def format_learning_card_text（1682 行）。
"""
import pytest

from src.output.learning_card import (
    LEARNING_DB,
    LearningCard,
    format_learning_card_text,
    generate_learning_card,
)

CARD_FIELDS = {"test_type", "test_name_zh", "decision_logic", "spss_path", "spss_steps",
               "methodology_steps", "common_mistakes", "key_concepts"}
LIST_FIELDS = ("spss_steps", "methodology_steps", "common_mistakes")


@pytest.mark.parametrize("test_type", ["cronbach_alpha", "mediation", "hlm"])
def test_known_types_return_a_card_with_every_field_filled(test_type):
    card = generate_learning_card(test_type, "显示名")

    assert isinstance(card, LearningCard)
    assert set(vars(card)) == CARD_FIELDS
    assert card.test_type == test_type and card.test_name_zh == "显示名"
    assert card.decision_logic and card.spss_path
    assert all(isinstance(getattr(card, f), list) and getattr(card, f) for f in LIST_FIELDS)
    assert isinstance(card.key_concepts, dict) and card.key_concepts   # 术语→释义 映射，不是列表


@pytest.mark.parametrize("test_type", ["no_such_method", "", None])
def test_unknown_or_blank_type_returns_none_not_an_empty_card(test_type):
    assert generate_learning_card(test_type, "X") is None


def test_formatter_tolerates_none_end_to_end():
    assert format_learning_card_text(None) == ""
    assert format_learning_card_text(generate_learning_card("no_such", "X")) == ""


def test_rendered_card_has_title_line_and_all_five_sections():
    text = format_learning_card_text(generate_learning_card("pearson_corr", "皮尔逊相关"))

    assert text.startswith("## 📖 方法学习卡片：皮尔逊相关")
    assert text.count("### ") == 5
    for section in ("为什么选这个方法", "分析步骤", "SPSS", "常见误区", "关键概念"):
        assert any(section in line for line in text.splitlines() if line.startswith("### ")), section
    assert len(text) > 400


def test_title_carries_the_display_name_not_the_internal_key():
    text = format_learning_card_text(generate_learning_card("cronbach_alpha", "信度分析"))

    first_line = text.splitlines()[0]
    assert "信度分析" in first_line
    assert "cronbach_alpha" not in first_line


def test_every_database_entry_is_renderable_and_keeps_the_input_name():
    for key in LEARNING_DB:
        card = generate_learning_card(key, f"名-{key}")
        assert card is not None and card.test_name_zh == f"名-{key}"
        assert card.test_type == key


def test_the_three_method_tables_have_a_containment_gap_of_fifteen_types():
    """【口径不一致钉桩】卡片库 48 类 ⊇ 关键词表 33 类 ⊇? 模板 26 类：
    关键词表与模板都被卡片库完全覆盖，但有 **15 类卡片是意图路由当前认不出来的**
    （cfa/ave/icc/cvi/cohens_kappa… 多为测量学与 SEM 族）
    ⇒ 这些卡片写好了却走不到用户面前。"""
    from src.output.reasoning import TEST_TEMPLATES
    from src.parser.keyword_dict import TEST_KEYWORDS

    db, kw, tp = set(LEARNING_DB), set(TEST_KEYWORDS), set(TEST_TEMPLATES)

    assert (kw | tp) <= db
    assert len(db - kw) == 15
    assert "cfa" in db - kw and "icc" in db - kw
    assert kw - db == set() and tp - db == set()
