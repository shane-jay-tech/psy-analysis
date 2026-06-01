"""路由配置表测试（v3.3）：防止后续维度扩展时静默 fallback。"""

import pytest

from src.upstream.routing import (
    ROUTING_TABLE,
    RouteNotFoundError,
    is_valid_route,
    list_all_routes,
    resolve_route,
)


class TestLegalCombinations:
    def test_funnel_beginner_resolves(self):
        assert resolve_route(True, "funnel", "beginner") == "funnel_beginner"

    def test_funnel_advanced_resolves(self):
        assert resolve_route(True, "funnel", "advanced") == "funnel_advanced"

    def test_wizard_beginner_resolves(self):
        assert resolve_route(True, "wizard", "beginner") == "wizard"

    def test_wizard_advanced_resolves(self):
        assert resolve_route(True, "wizard", "advanced") == "wizard"

    def test_done_phase_resolves(self):
        assert resolve_route(True, "done", "beginner") == "wizard"
        assert resolve_route(True, "done", "advanced") == "wizard"


class TestNonUndergradMode:
    def test_undergrad_mode_false_returns_non_undergrad(self):
        # 非本科模式时所有 phase/tier 都走 non_undergrad
        assert resolve_route(False, "funnel", "beginner") == "non_undergrad"
        assert resolve_route(False, None, None) == "non_undergrad"
        assert resolve_route(False, "anything", "advanced") == "non_undergrad"


class TestIllegalCombinations:
    def test_unknown_phase_raises(self):
        with pytest.raises(RouteNotFoundError, match="phase"):
            resolve_route(True, "literature", "beginner")

    def test_unknown_tier_raises(self):
        with pytest.raises(RouteNotFoundError, match="tier"):
            resolve_route(True, "funnel", "expert")


class TestMissingDimensions:
    def test_missing_phase_raises(self):
        with pytest.raises(RouteNotFoundError, match="phase"):
            resolve_route(True, None, "beginner")
        with pytest.raises(RouteNotFoundError, match="phase"):
            resolve_route(True, "", "beginner")

    def test_missing_tier_raises(self):
        with pytest.raises(RouteNotFoundError, match="tier"):
            resolve_route(True, "funnel", None)


class TestPhaseTransitions:
    def test_funnel_to_wizard_transition_legal(self):
        """phase=funnel → wizard 转换后路由应正常解析。"""
        assert resolve_route(True, "funnel", "beginner") == "funnel_beginner"
        # 转换后
        assert resolve_route(True, "wizard", "beginner") == "wizard"

    def test_tier_transition_legal(self):
        """tier=beginner → advanced 切换后路由应正常解析。"""
        assert resolve_route(True, "funnel", "beginner") == "funnel_beginner"
        assert resolve_route(True, "funnel", "advanced") == "funnel_advanced"


class TestBackwardCompat:
    def test_routing_table_covers_all_v3_2_combinations(self):
        """v3.2 已支持的组合在 v3.3 路由表中必须仍然合法。"""
        v3_2_combinations = [
            (True, "funnel", "beginner"),
            (True, "funnel", "advanced"),
            (True, "wizard", "beginner"),
            (True, "wizard", "advanced"),
        ]
        for combo in v3_2_combinations:
            assert combo in ROUTING_TABLE, f"v3.2 组合 {combo} 在 v3.3 路由表中缺失"

    def test_is_valid_route_no_exception(self):
        assert is_valid_route(True, "funnel", "beginner") is True
        assert is_valid_route(True, "literature", "beginner") is False
        assert is_valid_route(False, None, None) is True

    def test_list_all_routes_returns_copy(self):
        """list_all_routes 不应让外部修改污染 ROUTING_TABLE。"""
        routes = list_all_routes()
        routes[(True, "fake", "ghost")] = "danger"
        # 原表不变
        assert (True, "fake", "ghost") not in ROUTING_TABLE


# ---------------------------------------------------------------------------
# v3.4 路由维度校验
# ---------------------------------------------------------------------------

class TestRoutingTableValidation:
    def test_validate_at_startup_passes(self):
        """v3.4 启动自检：当前路由表应全部合法。"""
        from src.upstream.routing import validate_routing_table_at_startup
        result = validate_routing_table_at_startup()
        assert result["ok"] is True, f"启动自检失败：{result}"
        assert result["missing"] == []
        assert result["errors"] == []

    def test_validation_detects_missing_combinations(self):
        """模拟移除一个组合后，自检应报告 missing。"""
        from src.upstream import routing
        from src.upstream.routing import (
            ROUTING_TABLE,
            validate_routing_table_at_startup,
        )
        # 备份
        backup = dict(ROUTING_TABLE)
        try:
            ROUTING_TABLE.pop((True, "wizard", "advanced"), None)
            result = validate_routing_table_at_startup()
            assert result["ok"] is False
            assert (True, "wizard", "advanced") in result["missing"]
        finally:
            ROUTING_TABLE.clear()
            ROUTING_TABLE.update(backup)

    def test_literature_review_phase_resolves(self):
        """v3.4 新增 phase=literature_review 应正常解析。"""
        from src.upstream.routing import resolve_route
        assert resolve_route(True, "literature_review", "beginner") == "literature_review_beginner"
        assert resolve_route(True, "literature_review", "advanced") == "literature_review_advanced"

    def test_phase_lifecycle_funnel_to_done(self):
        from src.upstream.routing import get_phase_lifecycle, next_phase
        lifecycle = get_phase_lifecycle()
        assert lifecycle == ["funnel", "literature_review", "wizard", "done"]
        assert next_phase("funnel") == "literature_review"
        assert next_phase("literature_review") == "wizard"
        assert next_phase("done") is None
