"""测试方法 ID 一致性：确保系统各层使用一致的方法标识符。"""

import pytest
from src.analysis.method_ids import resolve_method_id, CANONICAL_IDS, get_table_route_group


class TestMethodIdResolution:
    """resolve_method_id 别名映射。"""

    def test_canonical_unchanged(self):
        assert resolve_method_id("pearson_corr") == "pearson_corr"
        assert resolve_method_id("independent_ttest") == "independent_ttest"

    def test_alias_resolves(self):
        assert resolve_method_id("pearson_correlation") == "pearson_corr"
        assert resolve_method_id("independent_t_test") == "independent_ttest"
        assert resolve_method_id("paired_t_test") == "paired_ttest"
        assert resolve_method_id("descriptive_statistics") == "descriptive"

    def test_unknown_passthrough(self):
        assert resolve_method_id("some_future_method") == "some_future_method"
        assert resolve_method_id("") == ""


class TestTableRouteConsistency:
    """APA 表格路由能正确匹配 canonical method_id。"""

    def test_pearson_corr_routes(self):
        assert get_table_route_group("pearson_corr") == "pearson_corr"
        assert get_table_route_group("pearson_correlation") == "pearson_corr"

    def test_regression_routes(self):
        assert get_table_route_group("multiple_regression") == "multiple_regression"
        assert get_table_route_group("hierarchical_regression") == "multiple_regression"

    def test_hlm_routes(self):
        assert get_table_route_group("hlm") == "hlm"
        assert get_table_route_group("mixed_effects") == "hlm"
        assert get_table_route_group("hierarchical_linear_model") == "hlm"


class TestCardBuilderMatchesRouter:
    """result_card 的 builder key 与 table router 的 method 条件一致。"""

    def test_card_builder_has_pearson_corr(self):
        from src.analysis.result_card import _CARD_BUILDERS
        assert "pearson_corr" in _CARD_BUILDERS or "pearson_correlation" in _CARD_BUILDERS

    def test_default_methods_have_table_route(self):
        """default 方法应该有对应的表格路由组（或明确豁免）。"""
        from src.utils.method_exposure import _DEFAULT_METHODS

        NO_TABLE_EXEMPT = {
            "factorial_anova", "repeated_anova", "omega",
            "spearman_correlation",
        }

        for method in _DEFAULT_METHODS:
            canonical = resolve_method_id(method)
            route = get_table_route_group(canonical)
            if canonical not in NO_TABLE_EXEMPT and method not in NO_TABLE_EXEMPT:
                assert route is not None, (
                    f"Default method '{method}' (canonical: '{canonical}') "
                    f"has no table route group and is not in exempt list"
                )


class TestRegistryAlignment:
    """analysis runner 注册的方法 ID 与 canonical 映射对齐。"""

    def test_key_methods_resolvable(self):
        key_methods = [
            "pearson_corr", "independent_ttest", "paired_ttest",
            "one_way_anova", "multiple_regression", "cronbach_alpha",
            "efa", "cfa", "sem", "hlm", "mediation", "moderation",
        ]
        for m in key_methods:
            assert resolve_method_id(m) == m, f"{m} should be canonical"
