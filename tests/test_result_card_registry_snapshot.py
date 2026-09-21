"""s922-122：结果卡注册表快照 ＋ MANOVA / ICC 通用卡现状钉桩。

把 `KNOWN_ISSUES.md:118-119` 的两条已知边界（MANOVA 结果卡片缺失 / ICC 评估卡片缺失）
第一次真正锁进测试：注册表键集用**排序集合**逐位比对，
新增或删除任何卡片模板都会翻红，倒逼同步回写 KNOWN_ISSUES 边界表。

基线读数取自开工前实测（判据 2 要求先跑后写死），命令原文：

    .venv/Scripts/python.exe -c "from src.analysis.result_card import _CARD_BUILDERS; \\
        print(len(_CARD_BUILDERS)); print(sorted(_CARD_BUILDERS))"
    -> 44
    -> ['ancova', 'ave_cr', 'binary_logistic', 'cfa', ... 'wilcoxon_signed_rank']

    同批实测：distinct builders = 29；alias groups = 14（其中 _build_hlm 占 3 键）
             get_card_builder_id('manova') -> None；resolve_method_id('manova') -> 'manova'
             'manova' in _CARD_BUILDERS -> False；'icc' in _CARD_BUILDERS -> False

红线：本件只用**合成假对象**驱动展示层，不改任何统计数值，也不改 `src/analysis/result_card.py`。
"""
import inspect
import pathlib
import re

import pytest

from src.analysis.result_card import (
    _CARD_BUILDERS,
    AnalysisResultCard,
    build_card_from_output,
    get_card_builder_id,
    resolve_method_id,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
KNOWN_ISSUES_PATH = REPO_ROOT / "KNOWN_ISSUES.md"

# ---- 实测基线（判据 2）----
BASELINE_REGISTRY_KEY_COUNT = 44
BASELINE_DISTINCT_BUILDER_COUNT = 29

BASELINE_REGISTRY_KEYS = [
    "ancova", "ave_cr", "binary_logistic", "cfa", "chi_square", "chi_square_test",
    "confirmatory_factor_analysis", "cronbach_alpha", "descriptive",
    "discriminant_validity", "efa", "exploratory_factor_analysis", "factorial_anova",
    "hierarchical_linear_model", "hierarchical_regression", "hlm", "independent_ttest",
    "kruskal_wallis", "logistic_regression", "mann_whitney", "mann_whitney_u",
    "mcdonalds_omega", "mediation", "mixed_anova", "mixed_effects", "moderation",
    "multiple_regression", "omega", "one_sample_ttest", "one_way_anova", "paired_ttest",
    "partial_corr", "partial_correlation", "pearson_corr", "pearson_correlation",
    "repeated_anova", "repeated_measures_anova", "sem", "spearman_corr",
    "spearman_correlation", "structural_equation_model", "two_way_anova", "wilcoxon",
    "wilcoxon_signed_rank",
]

# 一个 builder 挂多键的别名表（改名/拆并别名也会翻红）
BASELINE_ALIAS_GROUPS = {
    "_build_cfa": ["cfa", "confirmatory_factor_analysis"],
    "_build_chi_square": ["chi_square", "chi_square_test"],
    "_build_efa": ["efa", "exploratory_factor_analysis"],
    "_build_hlm": ["hierarchical_linear_model", "hlm", "mixed_effects"],
    "_build_logistic_regression": ["binary_logistic", "logistic_regression"],
    "_build_mann_whitney": ["mann_whitney", "mann_whitney_u"],
    "_build_mcdonalds_omega": ["mcdonalds_omega", "omega"],
    "_build_partial_corr": ["partial_corr", "partial_correlation"],
    "_build_pearson_corr": ["pearson_corr", "pearson_correlation"],
    "_build_repeated_anova": ["repeated_anova", "repeated_measures_anova"],
    "_build_sem": ["sem", "structural_equation_model"],
    "_build_spearman_corr": ["spearman_corr", "spearman_correlation"],
    "_build_two_way_anova": ["factorial_anova", "two_way_anova"],
    "_build_wilcoxon": ["wilcoxon", "wilcoxon_signed_rank"],
}

# 29 个去重后的 builder 函数名（实测取自同一批 python -c 探针）
BASELINE_BUILDER_NAMES = {
    "_build_ancova", "_build_ave_cr", "_build_cfa", "_build_chi_square",
    "_build_cronbach_alpha", "_build_descriptive", "_build_discriminant_validity", "_build_efa",
    "_build_hierarchical_regression", "_build_hlm", "_build_independent_ttest", "_build_kruskal_wallis",
    "_build_logistic_regression", "_build_mann_whitney", "_build_mcdonalds_omega", "_build_mediation",
    "_build_mixed_anova", "_build_moderation", "_build_multiple_regression", "_build_one_sample_ttest",
    "_build_one_way_anova", "_build_paired_ttest", "_build_partial_corr", "_build_pearson_corr",
    "_build_repeated_anova", "_build_sem", "_build_spearman_corr", "_build_two_way_anova",
    "_build_wilcoxon",
}

GENERIC_WARNING_RE = re.compile(r"方法 '([^']+)' 暂无专用结果卡模板")


class FakeManovaResult:
    """合成对象：只用来验证通用卡的类型标注，不含任何真实统计量。"""

    test_type = "manova"


class FakeHlmResult:
    """合成 HLM 结果对象（展示层输入），数值均为随意设定值。"""

    model_type = "random_intercept"
    n_groups = 12
    avg_group_size = 8.5
    group_var = "class_id"
    icc = 0.213
    fixed_effects = None
    group_variance = 0.5
    residual_variance = 1.5


class FakeLowIcmHlmResult(FakeHlmResult):
    icc = 0.01


class FakeAliasedIccResult(FakeHlmResult):
    icc = None
    intraclass_correlation = 0.31


# ---------------------------------------------------------------- 注册表快照

class TestCardBuilderRegistrySnapshot:

    def test_key_count_matches_measured_baseline(self):
        assert len(_CARD_BUILDERS) == BASELINE_REGISTRY_KEY_COUNT

    def test_key_set_snapshot_sorted_comparison(self):
        # 判据 2：排序集合比对——增删任一卡片模板必翻红
        assert sorted(_CARD_BUILDERS) == BASELINE_REGISTRY_KEYS

    def test_snapshot_is_exactly_the_baseline_length(self):
        assert len(BASELINE_REGISTRY_KEYS) == BASELINE_REGISTRY_KEY_COUNT

    def test_all_values_are_two_arg_builders_from_this_module(self):
        for key, builder in _CARD_BUILDERS.items():
            assert callable(builder), key
            assert builder.__module__ == "src.analysis.result_card", key
            assert builder.__name__.startswith("_build_"), key
            assert builder.__name__ in BASELINE_BUILDER_NAMES, key
            params = list(inspect.signature(builder).parameters)
            assert len(params) == 2, (key, params)

    def test_distinct_builder_count_snapshot(self):
        assert len(set(_CARD_BUILDERS.values())) == BASELINE_DISTINCT_BUILDER_COUNT
        assert {b.__name__ for b in _CARD_BUILDERS.values()} == BASELINE_BUILDER_NAMES
        assert len(BASELINE_BUILDER_NAMES) == BASELINE_DISTINCT_BUILDER_COUNT

    def test_alias_group_table_snapshot(self):
        groups: dict = {}
        for key, builder in _CARD_BUILDERS.items():
            groups.setdefault(builder.__name__, []).append(key)
        assert {n: sorted(ks) for n, ks in groups.items() if len(ks) > 1} == BASELINE_ALIAS_GROUPS

    def test_manova_and_icc_have_no_dedicated_key(self):
        # KNOWN_ISSUES 两条边界的反向锁：一旦有人注册了专用卡，本条与下面的
        # test_known_issues_rows_stay_in_sync_with_registry 一起翻红
        assert "manova" not in _CARD_BUILDERS
        assert "icc" not in _CARD_BUILDERS
        assert get_card_builder_id("manova") is None
        assert resolve_method_id("manova") == "manova"

    def test_known_issues_rows_stay_in_sync_with_registry(self):
        # 双向锁：文档行存在 ⇔ 注册表无该键。给 manova/icc 补专用卡时，
        # 不同步删掉 KNOWN_ISSUES 行就会在这里翻红（而不是只在上一例翻红）。
        text = KNOWN_ISSUES_PATH.read_text(encoding="utf-8")
        manova_row = "| MANOVA 结果卡片缺失 |" in text
        icc_row = "| ICC 评估卡片缺失 |" in text
        assert manova_row is ("manova" not in _CARD_BUILDERS)
        assert icc_row is ("icc" not in _CARD_BUILDERS)
        assert manova_row and icc_row


# ---------------------------------------------------------------- MANOVA 走通用卡

class TestManovaFallsBackToGenericCard:

    def test_manova_emits_generic_template_warning(self):
        card = build_card_from_output({
            "test_type": "manova",
            "test_name_zh": "多元方差分析",
            "result": FakeManovaResult(),
        })
        assert isinstance(card, AnalysisResultCard)
        assert card.warnings == ["方法 'manova' 暂无专用结果卡模板"]
        m = GENERIC_WARNING_RE.match(card.warnings[0])
        assert m and m.group(1) == "manova"

    def test_generic_card_only_records_result_type(self):
        card = build_card_from_output({"test_type": "manova", "result": FakeManovaResult()})
        assert card.technical_notes == ["结果对象类型: FakeManovaResult"]
        assert card.effect_sizes == []
        assert card.tables == []

    def test_generic_card_without_result_leaves_technical_notes_empty(self):
        card = build_card_from_output({"test_type": "manova"})
        assert card.technical_notes == []
        assert card.warnings == ["方法 'manova' 暂无专用结果卡模板"]
        assert card.provenance == {"method_id": "manova", "generated_by": "AnalysisResultCard"}

    def test_manova_keeps_method_name_and_empty_apa_text(self):
        card = build_card_from_output({
            "test_type": "manova", "test_name_zh": "多元方差分析", "result": FakeManovaResult()})
        assert card.method_id == "manova"
        assert card.method_name == "多元方差分析"
        assert card.assumption_status == "not_checked"

    def test_registered_method_emits_no_generic_warning(self):
        # 对照组：证明该 warning 由注册表分派产生，而非无条件追加
        card = build_card_from_output({"test_type": "descriptive"})
        assert [w for w in card.warnings if GENERIC_WARNING_RE.search(w)] == []

    @pytest.mark.parametrize("method_id", ["manova", "totally_unknown_method_xyz"])
    def test_any_unregistered_id_takes_the_same_path(self, method_id):
        card = build_card_from_output({"test_type": method_id})
        assert card.warnings == [f"方法 '{method_id}' 暂无专用结果卡模板"]


# ---------------------------------------------------------------- ICC 非独立卡片

class TestIccIsOnlyPartialSupportInsideHlmCard:

    def test_icc_surfaces_as_effect_size_entry(self):
        card = build_card_from_output({"test_type": "hlm", "result": FakeHlmResult()})
        assert card.effect_sizes == [{"name": "ICC", "value": 0.213}]

    def test_icc_text_lands_in_apa_and_plain_summaries(self):
        card = build_card_from_output({"test_type": "hlm", "result": FakeHlmResult()})
        assert "ICC = 0.213" in card.apa_text
        assert "21.3%" in card.plain_language_summary

    def test_low_icc_adds_warning(self):
        card = build_card_from_output({"test_type": "hlm", "result": FakeLowIcmHlmResult()})
        assert card.warnings == ["ICC = 0.010 很低，组间差异微小，OLS 近似可能已足够"]

    def test_alias_attribute_fallback_supported(self):
        card = build_card_from_output({"test_type": "hlm", "result": FakeAliasedIccResult()})
        assert card.effect_sizes == [{"name": "ICC", "value": 0.31}]

    def test_hlm_result_without_icc_yields_no_icc_effect_size(self):
        class NoIcc(FakeHlmResult):
            icc = None
            intraclass_correlation = None

        card = build_card_from_output({"test_type": "hlm", "result": NoIcc()})
        assert card.effect_sizes == []
        assert "ICC" not in card.apa_text

    def test_no_dedicated_icc_builder_key(self):
        # ICC 只在 _build_hlm 内部被顺带处理，注册表里没有 icc / intraclass 键
        assert not [k for k in _CARD_BUILDERS if "icc" in k or "intraclass" in k]
        groups = {}
        for key, builder in _CARD_BUILDERS.items():
            groups.setdefault(builder.__name__, []).append(key)
        assert sorted(groups["_build_hlm"]) == ["hierarchical_linear_model", "hlm", "mixed_effects"]

    def test_group_var_is_ignored_without_covariates(self):
        # 现状钉桩：result_card.py:1242 的三元式优先级使 group_var 不生效，
        # APA 文本里分组变量名退化为字面量「分组变量」
        card = build_card_from_output({"test_type": "hlm", "result": FakeHlmResult()})
        assert "class_id" not in card.apa_text
        assert "分组变量 分组变量（12 组，平均每组 8.5 人）" in card.apa_text
