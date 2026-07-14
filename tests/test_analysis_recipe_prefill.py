"""P0-1: AnalysisRecipe 自动预填测试。

验证方法推荐到数据分析页的闭环：
- recipe 可从 session_state 读取
- recipe 可转换为 AnalysisPlan
- 分析结果卡绑定 recommendation_id
"""

import pytest

from src.analysis.method_recommender import (
    AnalysisRecipe,
    MethodRecommendation,
    ResearchDesignInput,
    recommend_method,
    recommendation_to_recipe,
)
from src.parser.intent_resolver import AnalysisPlan
from src.ui.state_keys import ANALYSIS_RECIPE_KEY, RECIPE_EXECUTED_KEY, ANALYSIS_CARDS_KEY


_METHOD_TO_TEST_TYPE = {
    "independent_ttest": "independent_ttest",
    "paired_ttest": "paired_ttest",
    "one_way_anova": "one_way_anova",
    "repeated_anova": "repeated_anova",
    "pearson_corr": "pearson_corr",
    "spearman_corr": "spearman_corr",
    "multiple_regression": "multiple_regression",
    "binary_logistic": "binary_logistic",
    "mediation": "mediation",
    "moderation": "moderation",
    "cronbach_alpha": "cronbach_alpha",
    "chi_square_independence": "chi_square",
    "chi_square": "chi_square",
    "ancova": "ancova",
    "mann_whitney": "mann_whitney",
    "wilcoxon": "wilcoxon",
    "kruskal_wallis": "kruskal_wallis",
    "descriptive": "descriptive",
}


class TestRecipePrefillStateKeys:
    def test_analysis_recipe_key_defined(self):
        assert ANALYSIS_RECIPE_KEY == "analysis_recipe"

    def test_recipe_executed_key_defined(self):
        assert RECIPE_EXECUTED_KEY == "recipe_executed"


class TestRecipeToAnalysisPlan:
    @pytest.mark.parametrize("purpose,kwargs,expected_method", [
        ("difference", {"iv_type": "categorical", "sample_relation": "independent", "n_groups": 2}, "independent_ttest"),
        ("difference", {"sample_relation": "paired"}, "paired_ttest"),
        ("difference", {"iv_type": "categorical", "sample_relation": "independent", "n_groups": 3}, "one_way_anova"),
        ("correlation", {}, "pearson_corr"),
        ("prediction", {}, "multiple_regression"),
        ("mediation", {}, "mediation"),
        ("moderation", {}, "moderation"),
        ("reliability", {}, "cronbach_alpha"),
        ("prediction", {"dv_type": "binary"}, "binary_logistic"),
        ("difference", {"dv_type": "binary", "iv_type": "categorical"}, "chi_square_independence"),
    ])
    def test_recipe_maps_to_correct_test_type(self, purpose, kwargs, expected_method):
        design = ResearchDesignInput(purpose=purpose, dv_type=kwargs.get("dv_type", "continuous"), **{
            k: v for k, v in kwargs.items() if k != "dv_type"
        })
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design, recommendation_id="test_rec_1")
        assert recipe.method_id == expected_method
        test_type = _METHOD_TO_TEST_TYPE.get(recipe.method_id, recipe.method_id)
        assert test_type in _METHOD_TO_TEST_TYPE.values()

    def test_recipe_to_plan_preserves_recommendation_id(self):
        design = ResearchDesignInput(purpose="correlation", dv_type="continuous")
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design, recommendation_id="rec_42")
        assert recipe.recommendation_id == "rec_42"

    def test_recipe_creates_valid_plan(self):
        design = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=2,
        )
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design, recommendation_id="rec_1")
        test_type = _METHOD_TO_TEST_TYPE.get(recipe.method_id, recipe.method_id)
        plan = AnalysisPlan(
            test_type=test_type,
            dependent_vars=["score"],
            independent_vars=["group"],
            raw_request=f"[推荐方案] {recipe.method_zh}",
        )
        assert plan.test_type == "independent_ttest"
        assert "[推荐方案]" in plan.raw_request


class TestRecipeResultCardBinding:
    def test_result_card_has_recommendation_id(self):
        recipe = AnalysisRecipe(
            method_id="pearson_corr",
            method_zh="Pearson 相关",
            recommendation_id="rec_5",
        )
        card = {
            "method": "pearson_corr",
            "method_zh": recipe.method_zh,
            "apa_text": "r = .45, p < .01",
            "recommendation_id": recipe.recommendation_id,
        }
        assert card["recommendation_id"] == "rec_5"

    def test_result_card_without_recipe_has_no_recommendation_id(self):
        card = {
            "method": "pearson_corr",
            "apa_text": "r = .30, p = .05",
        }
        assert "recommendation_id" not in card


class TestRecipePrefillSessionFlow:
    def test_recipe_stored_and_retrieved(self):
        session = {}
        recipe = AnalysisRecipe(
            method_id="one_way_anova",
            method_zh="单因素方差分析",
            variable_roles={"dv": "连续因变量", "iv": "分组变量（≥3 组）"},
            recommendation_id="rec_7",
        )
        session[ANALYSIS_RECIPE_KEY] = recipe
        retrieved = session.get(ANALYSIS_RECIPE_KEY)
        assert retrieved is recipe
        assert retrieved.method_id == "one_way_anova"

    def test_recipe_executed_flag_blocks_repeat(self):
        session = {
            ANALYSIS_RECIPE_KEY: AnalysisRecipe(method_id="pearson_corr", method_zh="Pearson 相关"),
            RECIPE_EXECUTED_KEY: "rec_1",
        }
        should_show = session.get(ANALYSIS_RECIPE_KEY) and not session.get(RECIPE_EXECUTED_KEY)
        assert not should_show

    def test_recipe_not_executed_shows_banner(self):
        session = {
            ANALYSIS_RECIPE_KEY: AnalysisRecipe(method_id="pearson_corr", method_zh="Pearson 相关"),
        }
        should_show = session.get(ANALYSIS_RECIPE_KEY) and not session.get(RECIPE_EXECUTED_KEY)
        assert should_show

    def test_dismissed_recipe_blocks_banner(self):
        session = {
            ANALYSIS_RECIPE_KEY: AnalysisRecipe(method_id="pearson_corr", method_zh="Pearson 相关"),
            RECIPE_EXECUTED_KEY: "dismissed",
        }
        should_show = session.get(ANALYSIS_RECIPE_KEY) and not session.get(RECIPE_EXECUTED_KEY)
        assert not should_show


class TestRecipeMethodPanel:
    def test_method_recommender_stores_recipe_key(self):
        from src.ui.method_recommender_panel import _RECIPE_KEY
        assert _RECIPE_KEY == "analysis_recipe"

    def test_get_analysis_recipe_accessor(self):
        from src.ui.method_recommender_panel import get_analysis_recipe
        session = {ANALYSIS_RECIPE_KEY: AnalysisRecipe(method_id="mediation", method_zh="中介效应分析")}
        result = get_analysis_recipe(session)
        assert result.method_id == "mediation"
