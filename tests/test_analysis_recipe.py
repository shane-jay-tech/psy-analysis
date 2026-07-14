"""AnalysisRecipe 测试 — 方法推荐到分析执行的桥梁。"""

import pytest

from src.analysis.method_recommender import (
    AnalysisRecipe,
    MethodRecommendation,
    ResearchDesignInput,
    recommend_method,
    recommendation_to_recipe,
)


class TestAnalysisRecipeCreation:
    """验证 AnalysisRecipe 可从推荐结果生成。"""

    @pytest.mark.parametrize("purpose,extra,expected_method", [
        ("correlation", {}, "pearson_corr"),
        ("difference", {"iv_type": "categorical", "sample_relation": "independent"}, "independent_ttest"),
        ("prediction", {}, "multiple_regression"),
        ("mediation", {}, "mediation"),
        ("moderation", {}, "moderation"),
        ("reliability", {}, "cronbach_alpha"),
    ])
    def test_recipe_generated_for_common_scenarios(self, purpose, extra, expected_method):
        design = ResearchDesignInput(purpose=purpose, dv_type="continuous", sample_size=100, **extra)
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design, recommendation_id="test_1")
        assert recipe.method_id == expected_method
        assert recipe.method_zh != ""
        assert recipe.recommendation_id == "test_1"

    def test_recipe_has_variable_roles(self):
        design = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", sample_size=50,
        )
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design)
        assert len(recipe.variable_roles) > 0
        assert "dv" in recipe.variable_roles or "x" in recipe.variable_roles

    def test_recipe_carries_assumption_checks(self):
        design = ResearchDesignInput(purpose="difference", dv_type="continuous", sample_size=50)
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design)
        assert recipe.assumption_checks == rec.assumption_checks

    def test_recipe_carries_warnings(self):
        design = ResearchDesignInput(purpose="difference", dv_type="continuous", sample_size=10)
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design)
        assert recipe.confidence == rec.confidence

    def test_recipe_to_dict(self):
        design = ResearchDesignInput(purpose="correlation", dv_type="continuous", sample_size=30)
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design, recommendation_id="r1")
        d = recipe.to_dict()
        assert d["method_id"] == "pearson_corr"
        assert d["recommendation_id"] == "r1"
        assert isinstance(d["variable_roles"], dict)

    def test_recipe_includes_parameters(self):
        design = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            n_groups=3, sample_size=90,
        )
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design)
        assert recipe.parameters.get("n_groups") == 3

    def test_chi_square_recipe(self):
        design = ResearchDesignInput(
            purpose="difference", dv_type="binary", iv_type="categorical", sample_size=100
        )
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design)
        assert recipe.method_id == "chi_square_independence"
        assert "var1" in recipe.variable_roles

    def test_paired_recipe(self):
        design = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            sample_relation="paired", sample_size=30,
        )
        rec = recommend_method(design)
        recipe = recommendation_to_recipe(rec, design)
        assert recipe.method_id == "paired_ttest"


class TestRecipeStateIntegration:
    """验证 recipe 在 session_state 中的存取。"""

    def test_get_recipe_none_initially(self):
        from src.ui.method_recommender_panel import get_analysis_recipe, _RECIPE_KEY
        assert get_analysis_recipe({}) is None

    def test_recipe_stored_and_retrieved(self):
        from src.ui.method_recommender_panel import get_analysis_recipe, _RECIPE_KEY
        recipe = AnalysisRecipe(method_id="pearson_corr", method_zh="Pearson 相关")
        state = {_RECIPE_KEY: recipe}
        assert get_analysis_recipe(state) is recipe
