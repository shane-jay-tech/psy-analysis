"""src/parser/keyword_dict.py 结构一致性契约测试（s918-30）。

只钉结构与现值：顶层键集、词条非空/无重复、requires 词表、编码可读。
**不做语义/心理测量学评价**（触发词是否恰当不属本单范围）。
"""
from pathlib import Path

import pytest

from src.parser import keyword_dict as k

TOPLEVEL = ["STOPWORDS", "TEST_KEYWORDS", "VARIABLE_ROLE_KEYWORDS"]

TEST_KEYS = [
    "descriptive", "independent_ttest", "paired_ttest", "one_sample_ttest",
    "one_way_anova", "welch_anova", "two_way_anova", "repeated_anova",
    "pearson_corr", "spearman_corr", "linear_regression", "multiple_regression",
    "binary_logistic", "ordinal_logistic", "multinomial_logistic", "manova",
    "mixed_anova", "hlm", "sem", "chi_square_independence", "cronbach_alpha",
    "mann_whitney", "wilcoxon", "kruskal_wallis", "friedman", "split_half",
    "ancova", "mediation", "moderation", "efa", "partial_corr",
    "point_biserial", "hierarchical_regression",
]

# 同一触发词挂在两个检验类型下——现状 4 条，新增第 5 条即歧义扩大，本例会失败
AMBIGUOUS_TRIGGERS = {
    "重复测量": {"paired_ttest", "repeated_anova"},
    "交互效应": {"moderation", "two_way_anova"},
    "分层回归": {"hierarchical_regression", "multiple_regression"},
    "控制变量": {"ancova", "partial_corr"},
}

REQUIRES_VOCAB = {
    "categorical", "covariates_min", "dv", "dv_binary", "dv_multinomial",
    "dv_ordinal", "dvs_min", "factor_structure", "grouping", "groups",
    "groups_min", "items_min", "iv", "ivs", "ivs_min", "measures_min",
    "pairs", "structural_paths", "vars", "vars_min",
}

N_TRIGGERS = 277


def _all_triggers():
    return [(w, key) for key, entry in k.TEST_KEYWORDS.items() for w in entry["triggers"]]


def test_module_exposes_exactly_three_public_tables():
    assert sorted(n for n in dir(k) if n.isupper() and not n.startswith("_")) == TOPLEVEL
    assert len(k.TEST_KEYWORDS) == 33
    assert len(k.STOPWORDS) == 79
    assert list(k.VARIABLE_ROLE_KEYWORDS) == ["dependent", "independent", "grouping"]


def test_test_key_set_and_order_do_not_move():
    assert list(k.TEST_KEYWORDS) == TEST_KEYS


def test_every_entry_has_two_fields_and_a_clean_non_empty_trigger_list():
    for key, entry in k.TEST_KEYWORDS.items():
        assert set(entry) == {"triggers", "requires"}, key
        triggers = entry["triggers"]
        assert isinstance(triggers, list) and triggers, key
        assert all(isinstance(w, str) and w and w == w.strip() for w in triggers), key
        assert len(triggers) == len(set(triggers)), f"{key} 组内重复"

    assert len(_all_triggers()) == N_TRIGGERS


def test_cross_type_trigger_ambiguity_stays_at_four():
    seen = {}
    for word, key in _all_triggers():
        seen.setdefault(word, set()).add(key)

    assert {w: owners for w, owners in seen.items() if len(owners) > 1} == AMBIGUOUS_TRIGGERS


def test_requires_values_are_only_int_or_bool_within_known_vocab():
    for key, entry in k.TEST_KEYWORDS.items():
        assert set(entry["requires"]) <= REQUIRES_VOCAB, key
        for req, val in entry["requires"].items():
            assert isinstance(val, (int, bool)) and not isinstance(val, float), f"{key}.{req}"


def test_stopwords_is_a_deduplicated_set_of_plain_strings():
    assert isinstance(k.STOPWORDS, set)
    assert all(isinstance(w, str) and w and w == w.strip() for w in k.STOPWORDS)
    assert "" not in k.STOPWORDS


def test_dictionary_is_valid_utf8_without_replacement_chars():
    text = Path(k.__file__).read_text(encoding="utf-8")

    assert Path(k.__file__).name == "keyword_dict.py"
    assert "\ufffd" not in text


def test_greek_and_superscript_triggers_are_not_gbk_encodable():
    """`χ²` 存进 UTF-8 词表没问题，但打到 GBK 控制台会抛 UnicodeEncodeError——
    与桥日志编码族同因（打印未指定编码）；钉住以防有人顺手改写成 ASCII 而丢语义。"""
    assert "χ²" in {w for w, _ in _all_triggers()}
    with pytest.raises(UnicodeEncodeError):
        "χ²".encode("gbk")
