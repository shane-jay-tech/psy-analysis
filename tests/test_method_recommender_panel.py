"""方法推荐向导 UI 面板测试 — 验证面板服务层集成和状态管理。"""

import pytest

from src.analysis.method_recommender import (
    MethodRecommendation,
    ResearchDesignInput,
    recommend_method,
)
from src.ui.method_recommender_panel import (
    PURPOSE_OPTIONS,
    DV_TYPE_OPTIONS,
    IV_TYPE_OPTIONS,
    SAMPLE_RELATION_OPTIONS,
    ASSUMPTION_OPTIONS,
    _STATE_KEY,
    _HISTORY_KEY,
    get_recommendation_for_deliverable,
    get_current_recommendation,
)


@pytest.fixture
def session_state():
    return {}


class TestPanelOptions:
    """UI 选项映射完整性。"""

    def test_purpose_options_cover_all_rules(self):
        assert "差异比较" in PURPOSE_OPTIONS
        assert "相关关系" in PURPOSE_OPTIONS
        assert "预测/回归" in PURPOSE_OPTIONS
        assert "中介效应" in PURPOSE_OPTIONS
        assert "调节效应" in PURPOSE_OPTIONS
        assert "信效度" in PURPOSE_OPTIONS

    def test_dv_type_options(self):
        assert len(DV_TYPE_OPTIONS) >= 4
        assert "连续变量" in DV_TYPE_OPTIONS

    def test_iv_type_options(self):
        assert "分组变量（分类）" in IV_TYPE_OPTIONS

    def test_sample_relation_options(self):
        assert "独立样本" in SAMPLE_RELATION_OPTIONS
        assert "配对样本" in SAMPLE_RELATION_OPTIONS
        assert "重复测量" in SAMPLE_RELATION_OPTIONS


class TestPanelStateIntegration:
    """面板与 session_state 集成。"""

    def test_recommendation_stored_in_state(self, session_state):
        design = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=2
        )
        rec = recommend_method(design)
        session_state[_STATE_KEY] = rec
        assert get_current_recommendation(session_state) is rec
        assert rec.primary_method == "independent_ttest"

    def test_history_accumulates(self, session_state):
        session_state[_HISTORY_KEY] = []
        designs = [
            ResearchDesignInput(purpose="difference", dv_type="continuous",
                                iv_type="categorical", sample_relation="independent", n_groups=2),
            ResearchDesignInput(purpose="correlation", dv_type="continuous"),
        ]
        for d in designs:
            rec = recommend_method(d)
            session_state[_HISTORY_KEY].append({
                "design": d.__dict__,
                "recommendation": rec.primary_method,
            })
        history = get_recommendation_for_deliverable(session_state)
        assert len(history) == 2
        assert history[0]["recommendation"] == "independent_ttest"
        assert history[1]["recommendation"] == "pearson_corr"

    def test_empty_state_returns_none(self, session_state):
        assert get_current_recommendation(session_state) is None

    def test_empty_history_returns_empty(self, session_state):
        assert get_recommendation_for_deliverable(session_state) == []


class TestAllScenariosFromUI:
    """验证所有 12 场景能从 UI 选项组合触发。"""

    @pytest.mark.parametrize("purpose_label,dv_label,iv_label,relation_label,expected", [
        ("差异比较", "连续变量", "分组变量（分类）", "独立样本", "independent_ttest"),
        ("差异比较", "连续变量", "分组变量（分类）", "配对样本", "paired_ttest"),
        ("相关关系", "连续变量", "连续变量", "独立样本", "pearson_corr"),
        ("预测/回归", "连续变量", "连续变量", "独立样本", "multiple_regression"),
        ("预测/回归", "二分类", "连续变量", "独立样本", "binary_logistic"),
        ("中介效应", "连续变量", "连续变量", "独立样本", "mediation"),
        ("调节效应", "连续变量", "连续变量", "独立样本", "moderation"),
        ("信效度", "连续变量", "连续变量", "独立样本", "cronbach_alpha"),
    ])
    def test_ui_option_combo_produces_correct_method(
        self, purpose_label, dv_label, iv_label, relation_label, expected
    ):
        design = ResearchDesignInput(
            purpose=PURPOSE_OPTIONS[purpose_label],
            dv_type=DV_TYPE_OPTIONS[dv_label],
            iv_type=IV_TYPE_OPTIONS[iv_label],
            sample_relation=SAMPLE_RELATION_OPTIONS[relation_label],
            n_groups=2,
        )
        rec = recommend_method(design)
        assert rec.primary_method == expected

    def test_three_groups_from_ui(self):
        design = ResearchDesignInput(
            purpose=PURPOSE_OPTIONS["差异比较"],
            dv_type=DV_TYPE_OPTIONS["连续变量"],
            iv_type=IV_TYPE_OPTIONS["分组变量（分类）"],
            sample_relation=SAMPLE_RELATION_OPTIONS["独立样本"],
            n_groups=3,
        )
        rec = recommend_method(design)
        assert rec.primary_method == "one_way_anova"

    def test_repeated_measures_from_ui(self):
        design = ResearchDesignInput(
            purpose=PURPOSE_OPTIONS["差异比较"],
            dv_type=DV_TYPE_OPTIONS["连续变量"],
            iv_type=IV_TYPE_OPTIONS["分组变量（分类）"],
            sample_relation=SAMPLE_RELATION_OPTIONS["重复测量"],
            time_points=4,
        )
        rec = recommend_method(design)
        assert rec.primary_method == "repeated_anova"

    def test_chi_square_from_ui(self):
        design = ResearchDesignInput(
            purpose=PURPOSE_OPTIONS["差异比较"],
            dv_type=DV_TYPE_OPTIONS["二分类"],
            iv_type=IV_TYPE_OPTIONS["分组变量（分类）"],
            sample_relation=SAMPLE_RELATION_OPTIONS["独立样本"],
        )
        rec = recommend_method(design)
        assert rec.primary_method == "chi_square_independence"

    def test_ancova_from_ui(self):
        design = ResearchDesignInput(
            purpose=PURPOSE_OPTIONS["差异比较"],
            dv_type=DV_TYPE_OPTIONS["连续变量"],
            iv_type=IV_TYPE_OPTIONS["分组变量（分类）"],
            sample_relation=SAMPLE_RELATION_OPTIONS["独立样本"],
            n_groups=2,
            has_covariate=True,
        )
        rec = recommend_method(design)
        assert rec.primary_method == "ancova"


class TestRecommendationToDeliverable:
    """推荐结果能进入交付包。"""

    def test_history_serializable(self, session_state):
        session_state[_HISTORY_KEY] = []
        design = ResearchDesignInput(
            purpose="difference", dv_type="continuous",
            iv_type="categorical", sample_relation="independent", n_groups=2
        )
        rec = recommend_method(design)
        session_state[_HISTORY_KEY].append({
            "design": design.__dict__,
            "recommendation": rec.primary_method,
        })
        import json
        json_str = json.dumps(get_recommendation_for_deliverable(session_state), ensure_ascii=False)
        assert "independent_ttest" in json_str
