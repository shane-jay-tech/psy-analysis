import pandas as pd
import pytest

from src.parser import intent_resolver, tokenizer


def test_tokenize_filters_stops_numbers_punctuation_and_single_cjk(monkeypatch):
    monkeypatch.setattr(
        tokenizer.jieba,
        "lcut",
        lambda _text: [" ", "stop", "42", "。", "我", "ANOVA", "effect"],
    )
    monkeypatch.setattr(tokenizer, "STOPWORDS", {"stop"})

    assert tokenizer.tokenize("ignored") == ["ANOVA", "effect"]
    assert tokenizer.tokenize_keep_numbers("ignored") == ["42", "ANOVA", "effect"]


def test_score_test_types_ranks_exact_trigger_above_unmatched_types(monkeypatch):
    monkeypatch.setattr(
        intent_resolver,
        "TEST_KEYWORDS",
        {
            "exact": {"triggers": ["pearson"]},
            "partial": {"triggers": ["pear"]},
            "none": {"triggers": ["anova"]},
        },
    )

    ranked = intent_resolver._score_test_types(["pearson"], {})

    assert ranked[0][0] == "exact"
    assert ranked[0][1] == {"score": 1, "matched": ["pearson"]}
    assert ranked[-1][1]["score"] == 0


@pytest.mark.parametrize(
    ("token", "expected"),
    [("Score", "score_total"), ("scor_total", "score_total"), ("missing", None)],
)
def test_fuzzy_match_column_handles_case_similarity_and_misses(token, expected):
    assert intent_resolver._fuzzy_match_column(token, ["score_total", "group"]) == expected


def test_match_value_in_column_handles_exact_fuzzy_and_missing_columns():
    df = pd.DataFrame({"group": ["control", "treatment"]})

    assert intent_resolver._match_value_in_column("control", "group", df) is True
    assert intent_resolver._match_value_in_column("treatmen", "group", df) is True
    assert intent_resolver._match_value_in_column("other", "group", df) is False
    assert intent_resolver._match_value_in_column("anything", "missing", df) is False


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [(["100"], 100.0), (["-2.5"], -2.5), (["nothing"], None)],
)
def test_extract_test_value(tokens, expected):
    assert intent_resolver._extract_test_value(tokens) == expected


def _patch_tokens_and_ranking(monkeypatch, tokens, test_type, score=2):
    monkeypatch.setattr(intent_resolver, "tokenize", lambda _request: tokens)
    monkeypatch.setattr(intent_resolver, "tokenize_keep_numbers", lambda _request: tokens)
    monkeypatch.setattr(
        intent_resolver,
        "_score_test_types",
        lambda _tokens, _types: [(test_type, {"score": score, "matched": [test_type]})],
    )


def test_resolve_empty_request_returns_high_ambiguity_descriptive_plan(monkeypatch):
    monkeypatch.setattr(intent_resolver, "tokenize", lambda _request: [])
    monkeypatch.setattr(intent_resolver, "tokenize_keep_numbers", lambda _request: [])

    plan = intent_resolver.resolve(
        pd.DataFrame({"score": [1]}), "   ", {"score": {"type": "numeric"}}
    )

    assert plan.test_type == "descriptive"
    assert plan.ambiguity_score == 1.0
    assert plan.suggested_followups


def test_resolve_unmatched_request_defaults_to_all_numeric_columns(monkeypatch):
    monkeypatch.setattr(intent_resolver, "tokenize", lambda _request: ["unknown"])
    monkeypatch.setattr(intent_resolver, "tokenize_keep_numbers", lambda _request: ["unknown"])
    monkeypatch.setattr(
        intent_resolver,
        "_score_test_types",
        lambda _tokens, _types: [("ttest", {"score": 0, "matched": []})],
    )
    df = pd.DataFrame({"score": [1], "age": [20], "group": ["a"]})
    info = {
        "score": {"type": "numeric"},
        "age": {"type": "numeric"},
        "group": {"type": "categorical_binary"},
    }

    plan = intent_resolver.resolve(df, "unknown", info)

    assert plan.test_type == "descriptive"
    assert plan.dependent_vars == ["score", "age"]
    assert plan.ambiguity_score == 0.5


def test_resolve_upgrades_ttest_for_multi_level_group(monkeypatch):
    _patch_tokens_and_ranking(monkeypatch, ["score", "group"], "independent_ttest")
    df = pd.DataFrame({"score": [1, 2, 3], "group": ["a", "b", "c"]})
    info = {
        "score": {"type": "numeric"},
        "group": {"type": "categorical_multi"},
    }

    plan = intent_resolver.resolve(df, "compare", info)

    assert plan.test_type == "one_way_anova"
    assert plan.dependent_vars == ["score"]
    assert plan.independent_vars == ["group"]


def test_resolve_correlation_backfills_numeric_columns(monkeypatch):
    _patch_tokens_and_ranking(monkeypatch, ["request"], "pearson_corr")
    df = pd.DataFrame({f"x{i}": [i] for i in range(7)})
    info = {column: {"type": "numeric"} for column in df.columns}

    plan = intent_resolver.resolve(df, "correlate", info)

    assert plan.dependent_vars == ["x0", "x1", "x2", "x3", "x4"]


def test_resolve_reliability_moves_numeric_variables_to_scale_items(monkeypatch):
    _patch_tokens_and_ranking(monkeypatch, ["q1", "q2"], "cronbach_alpha")
    df = pd.DataFrame({"q1": [1], "q2": [2]})
    info = {"q1": {"type": "numeric"}, "q2": {"type": "numeric"}}

    plan = intent_resolver.resolve(df, "reliability", info)

    assert plan.dependent_vars == []
    assert plan.scale_items == ["q1", "q2"]


def test_resolve_extracts_test_value_and_generates_followups(monkeypatch):
    _patch_tokens_and_ranking(monkeypatch, ["score", "100"], "one_sample_ttest", score=0.5)
    df = pd.DataFrame({"score": [99, 101]})

    plan = intent_resolver.resolve(df, "test against 100", {"score": {"type": "numeric"}})

    assert plan.test_value == 100.0
    assert plan.ambiguity_score == 0.7
    assert len(plan.suggested_followups) == 2


def test_generate_followups_only_for_high_ambiguity():
    assert intent_resolver._generate_followups("ttest", 0.2, ["x"], {"x": "numeric"}) == []
    assert len(intent_resolver._generate_followups("ttest", 0.8, ["x"], {"x": "numeric"})) == 2
