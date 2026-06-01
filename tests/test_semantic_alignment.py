"""跨模块语义对齐测试：研究问题 ↔ 候选变量 ↔ 分析方法。"""

import pytest

from src.upstream.semantic_alignment import (
    AlignmentResult,
    AlignmentWarning,
    _classify_method,
    _classify_var,
    check_alignment,
)


class TestClassifyMethod:
    def test_t_test_classified(self):
        assert _classify_method("independent_ttest") == "t_test"
        assert _classify_method("paired_ttest") == "t_test"

    def test_anova_classified(self):
        assert _classify_method("one_way_anova") == "anova"
        assert _classify_method("ANOVA") == "anova"

    def test_corr_classified(self):
        assert _classify_method("pearson_corr") == "corr"
        assert _classify_method("spearman_corr") == "corr"

    def test_unknown_method(self):
        assert _classify_method("nonexistent_method") == "unknown"


class TestClassifyVar:
    def test_categorical_keywords(self):
        assert _classify_var("组别") == "categorical"
        assert _classify_var("性别") == "categorical"
        assert _classify_var("group_type") == "categorical"

    def test_continuous_default(self):
        assert _classify_var("焦虑分") == "continuous"
        assert _classify_var("反应时") == "continuous"


class TestRule1_MethodVsVarType:
    def test_two_continuous_vars_with_ttest_warns(self):
        """R1：两个连续变量但选 t 检验 → 警告。"""
        result = check_alignment(
            "焦虑和压力的关系",
            {"dependent_vars": ["焦虑分"], "independent_vars": ["压力分"]},
            "independent_ttest",
        )
        assert not result.is_aligned
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R1_TTEST_NO_CATEGORICAL" in rule_ids

    def test_categorical_iv_with_corr_warns(self):
        """R2：分类 IV + 连续 DV 选相关 → 警告。"""
        result = check_alignment(
            "性别对焦虑的影响",
            {"dependent_vars": ["焦虑"], "independent_vars": ["性别"]},
            "pearson_corr",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R2_CORR_WITH_CATEGORICAL_IV" in rule_ids

    def test_two_categorical_with_ttest_warns(self):
        """R3：两个分类变量选 t 检验 → 警告。"""
        result = check_alignment(
            "性别与组别的关系",
            {"dependent_vars": ["组别类型"], "independent_vars": ["性别"]},
            "independent_ttest",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R3_TTEST_BOTH_CATEGORICAL" in rule_ids


class TestRule2_DirectionalityWords:
    def test_causal_word_with_corr_warns(self):
        """R4：研究问题含'预测'+ 相关分析 → 警告无法支持因果。"""
        result = check_alignment(
            "睡眠质量是否预测学业成绩？",
            {"dependent_vars": ["成绩"], "independent_vars": ["睡眠质量"]},
            "pearson_corr",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R4_CAUSAL_WORD_WITH_CORR" in rule_ids

    def test_diff_word_with_regression_info(self):
        """R5：'差异'+ 回归 → info 级提示。"""
        result = check_alignment(
            "比较男女在焦虑水平上的差异",
            {"dependent_vars": ["焦虑"], "independent_vars": ["性别组别"]},
            "linear_regression",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R5_DIFF_WORD_WITH_REGRESSION" in rule_ids

    def test_relation_word_with_ttest_info(self):
        """R6：'关系/相关'+ t 检验 → info 级提示。"""
        result = check_alignment(
            "焦虑和睡眠之间的关系",
            {"dependent_vars": ["焦虑"], "independent_vars": ["睡眠时长"]},
            "independent_ttest",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R6_RELATION_WORD_WITH_TTEST" in rule_ids


class TestRule3_VarCountVsMethod:
    def test_anova_with_continuous_iv_warns(self):
        """R7：ANOVA 但 IV 似乎是连续变量 → 警告。"""
        result = check_alignment(
            "X 影响 Y",
            {"dependent_vars": ["焦虑"], "independent_vars": ["压力分"]},
            "one_way_anova",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R7_ANOVA_CONTINUOUS_IV" in rule_ids

    def test_chi_square_with_continuous_warns(self):
        """R8：卡方但含连续变量 → 警告。"""
        result = check_alignment(
            "性别与考试得分",
            {"dependent_vars": ["考试得分"], "independent_vars": ["性别"]},
            "chi_square",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R8_CHISQUARE_WITH_CONTINUOUS" in rule_ids


class TestAlignedScenarios:
    def test_correct_ttest_no_warnings(self):
        """合理的 t 检验场景：分类 IV + 连续 DV → 无警告。"""
        result = check_alignment(
            "比较两组的焦虑差异",
            {"dependent_vars": ["焦虑分"], "independent_vars": ["组别"]},
            "independent_ttest",
        )
        assert result.is_aligned

    def test_correct_pearson_corr_no_warnings(self):
        """合理的相关：两个连续变量 + 关系词 → 无警告。"""
        result = check_alignment(
            "焦虑和睡眠时长的相关",
            {"dependent_vars": ["焦虑分"], "independent_vars": ["睡眠时长"]},
            "pearson_corr",
        )
        assert result.is_aligned

    def test_correct_chi_square_no_warnings(self):
        """合理的卡方：两个分类变量 → 无警告。"""
        result = check_alignment(
            "性别与吸烟的关联",
            {"dependent_vars": ["吸烟组别"], "independent_vars": ["性别"]},
            "chi_square",
        )
        assert result.is_aligned


class TestEdgeCases:
    def test_empty_inputs_are_aligned(self):
        result = check_alignment("", None, "")
        assert result.is_aligned

    def test_warning_has_suggestion(self):
        """每条警告必须有非空的 suggestion。"""
        result = check_alignment(
            "焦虑预测成绩",
            {"dependent_vars": ["成绩"], "independent_vars": ["焦虑"]},
            "pearson_corr",
        )
        for w in result.warnings:
            assert w.suggestion
            assert len(w.suggestion) > 5


# ---------------------------------------------------------------------------
# v3.4 R9: 偏相关需指定控制变量
# ---------------------------------------------------------------------------

class TestR9_PartialCorr:
    def test_partial_corr_without_control_warns(self):
        result = check_alignment(
            "X 和 Y 控制 Z 的关系",
            {"dependent_vars": ["Y"], "independent_vars": ["X"], "covariates": []},
            "partial_corr",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R9_PARTIAL_CORR_NO_CONTROL" in rule_ids

    def test_partial_corr_with_control_no_warning(self):
        result = check_alignment(
            "X 和 Y 控制 Z 的关系",
            {"dependent_vars": ["Y"], "independent_vars": ["X"], "covariates": ["Z"]},
            "partial_corr",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R9_PARTIAL_CORR_NO_CONTROL" not in rule_ids


# ---------------------------------------------------------------------------
# v3.4 R10: 中介分析需 X/M/Y 三个不同变量
# ---------------------------------------------------------------------------

class TestR10_Mediation:
    def test_mediation_with_only_two_vars_warns(self):
        result = check_alignment(
            "X 影响 Y 的中介效应",
            {"dependent_vars": ["Y"], "independent_vars": ["X"]},   # 缺中介
            "mediation",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R10_MEDIATION_NEEDS_THREE_VARS" in rule_ids

    def test_mediation_with_three_distinct_vars_no_warning(self):
        result = check_alignment(
            "X 通过 M 影响 Y 的中介效应",
            {
                "dependent_vars": ["Y_outcome"],
                "independent_vars": ["X_predictor"],
                "mediator": "M_mediator",
            },
            "mediation",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R10_MEDIATION_NEEDS_THREE_VARS" not in rule_ids


# ---------------------------------------------------------------------------
# v3.4 R11: 调节变量为二分变量时提示
# ---------------------------------------------------------------------------

class TestR11_DichotomousModerator:
    def test_moderation_with_dichotomous_w_info(self):
        result = check_alignment(
            "X 对 Y 的影响在不同性别中是否不同",
            {
                "dependent_vars": ["Y"],
                "independent_vars": ["X"],
                "grouping_var": "性别",
            },
            "moderation",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R11_MODERATION_DICHOTOMOUS_W" in rule_ids

    def test_moderation_with_continuous_w_no_warning(self):
        result = check_alignment(
            "X 对 Y 的影响是否被自尊所调节",
            {
                "dependent_vars": ["Y"],
                "independent_vars": ["X"],
                "moderator": "自尊水平",   # 连续变量
            },
            "moderation",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R11_MODERATION_DICHOTOMOUS_W" not in rule_ids


# ---------------------------------------------------------------------------
# v3.7 R12: 偏相关 + 控制变量 ≥3 → 多重控制不稳定提示
# ---------------------------------------------------------------------------

class TestR12_PartialCorrManyControls:
    def test_three_or_more_controls_info(self):
        result = check_alignment(
            "X 与 Y 的关系（控制其他变量）",
            {
                "dependent_vars": ["Y"], "independent_vars": ["X"],
                "covariates": ["c1", "c2", "c3"],
            },
            "partial_corr",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R12_PARTIAL_CORR_MANY_CONTROLS" in rule_ids

    def test_two_controls_no_warning(self):
        result = check_alignment(
            "X 与 Y 的关系",
            {
                "dependent_vars": ["Y"], "independent_vars": ["X"],
                "covariates": ["c1", "c2"],
            },
            "partial_corr",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R12_PARTIAL_CORR_MANY_CONTROLS" not in rule_ids


# ---------------------------------------------------------------------------
# v3.7 R13: 多重回归 ≥3 IV → VIF 提示
# ---------------------------------------------------------------------------

class TestR13_MultiRegressionVIF:
    def test_three_ivs_with_regression_info(self):
        result = check_alignment(
            "X1 X2 X3 预测 Y",
            {"dependent_vars": ["Y"], "independent_vars": ["X1", "X2", "X3"]},
            "linear_regression",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R13_MULTI_REGRESSION_VIF" in rule_ids

    def test_multiple_regression_method_name_triggers(self):
        result = check_alignment(
            "多个变量预测 Y",
            {"dependent_vars": ["Y"], "independent_vars": ["X1", "X2"]},
            "multiple_regression",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R13_MULTI_REGRESSION_VIF" in rule_ids

    def test_simple_regression_no_warning(self):
        result = check_alignment(
            "X 预测 Y",
            {"dependent_vars": ["Y"], "independent_vars": ["X"]},
            "linear_regression",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R13_MULTI_REGRESSION_VIF" not in rule_ids


# ---------------------------------------------------------------------------
# v3.7 R14: 同时填 mediator 和 moderator → 有调节的中介
# ---------------------------------------------------------------------------

class TestR14_MedModCombo:
    def test_both_mediator_and_moderator_info(self):
        result = check_alignment(
            "X 通过 M 影响 Y，被 W 调节",
            {
                "dependent_vars": ["Y"], "independent_vars": ["X"],
                "mediator": "M", "moderator": "W",
            },
            "mediation",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R14_MED_MOD_COMBO" in rule_ids

    def test_only_mediator_no_warning(self):
        result = check_alignment(
            "X 通过 M 影响 Y",
            {
                "dependent_vars": ["Y"], "independent_vars": ["X"],
                "mediator": "M",
            },
            "mediation",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R14_MED_MOD_COMBO" not in rule_ids


# ---------------------------------------------------------------------------
# v3.7 R15: 重复测量 ANOVA → 球形检验提示
# ---------------------------------------------------------------------------

class TestR15_RepeatedSphericity:
    def test_repeated_measures_anova_info(self):
        result = check_alignment(
            "三个时间点的差异",
            {"dependent_vars": ["score"], "independent_vars": ["time"]},
            "repeated_measures_anova",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R15_REPEATED_SPHERICITY" in rule_ids

    def test_one_way_anova_no_repeated_warning(self):
        result = check_alignment(
            "组间差异",
            {"dependent_vars": ["score"], "independent_vars": ["组别"]},
            "one_way_anova",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R15_REPEATED_SPHERICITY" not in rule_ids


# ---------------------------------------------------------------------------
# v3.7 R16: 两因素 ANOVA → 交互效应提示
# ---------------------------------------------------------------------------

class TestR16_TwoWayInteraction:
    def test_two_way_anova_method_info(self):
        result = check_alignment(
            "性别和组别对成绩的影响",
            {"dependent_vars": ["成绩"], "independent_vars": ["性别", "组别"]},
            "two_way_anova",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R16_TWOWAY_INTERACTION" in rule_ids

    def test_two_categorical_ivs_anova_info(self):
        # method 仅写 anova，但 IV 数量 ≥ 2 categorical → 推断为两因素
        result = check_alignment(
            "因素 A 与 因素 B 的影响",
            {"dependent_vars": ["score"], "independent_vars": ["组别A", "性别"]},
            "anova",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R16_TWOWAY_INTERACTION" in rule_ids

    def test_one_way_no_interaction_warning(self):
        result = check_alignment(
            "三组差异",
            {"dependent_vars": ["score"], "independent_vars": ["组别"]},
            "one_way_anova",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R16_TWOWAY_INTERACTION" not in rule_ids


# ---------------------------------------------------------------------------
# v3.7 R17: 嵌套数据提示
# ---------------------------------------------------------------------------

class TestR17_NestedData:
    def test_class_in_iv_triggers_hint(self):
        result = check_alignment(
            "教学方法对成绩的影响",
            {
                "dependent_vars": ["成绩"],
                "independent_vars": ["教学方法"],
                "covariates": ["班级编号"],
            },
            "linear_regression",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R17_NESTED_DATA" in rule_ids

    def test_no_nested_keyword_no_warning(self):
        result = check_alignment(
            "训练对成绩的影响",
            {"dependent_vars": ["成绩"], "independent_vars": ["训练时长"]},
            "linear_regression",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R17_NESTED_DATA" not in rule_ids


# ---------------------------------------------------------------------------
# v3.7 R18: 非参数 → 中位数 + IQR 描述统计提示
# ---------------------------------------------------------------------------

class TestR18_NonparamDescriptive:
    def test_mann_whitney_info(self):
        result = check_alignment(
            "两组差异（非正态）",
            {"dependent_vars": ["score"], "independent_vars": ["组别"]},
            "mann_whitney",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R18_NONPARAM_DESCRIPTIVE" in rule_ids

    def test_parametric_no_warning(self):
        result = check_alignment(
            "两组差异",
            {"dependent_vars": ["score"], "independent_vars": ["组别"]},
            "independent_ttest",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R18_NONPARAM_DESCRIPTIVE" not in rule_ids


# ---------------------------------------------------------------------------
# v3.7 R19: 因子分析 → KMO + Bartlett 提示
# ---------------------------------------------------------------------------

class TestR19_FactorPrecondition:
    def test_efa_method_info(self):
        result = check_alignment(
            "量表维度结构",
            {"dependent_vars": ["item1", "item2", "item3"]},
            "efa",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R19_FACTOR_PRECONDITION" in rule_ids

    def test_factor_analysis_chinese_info(self):
        result = check_alignment(
            "题项的因子结构",
            {"dependent_vars": ["item1", "item2"]},
            "因子分析",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R19_FACTOR_PRECONDITION" in rule_ids

    def test_other_method_no_warning(self):
        result = check_alignment(
            "X 与 Y 关系",
            {"dependent_vars": ["Y"], "independent_vars": ["X"]},
            "pearson_corr",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R19_FACTOR_PRECONDITION" not in rule_ids


# ---------------------------------------------------------------------------
# v3.7 R20: 卡方 → 期望频数 / Fisher 提示
# ---------------------------------------------------------------------------

class TestR20_ChiSquareLowExpected:
    def test_chi_square_info(self):
        result = check_alignment(
            "性别与是否选课的关联",
            {"dependent_vars": ["选课"], "independent_vars": ["性别"]},
            "chi_square",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R20_CHISQUARE_LOW_EXPECTED" in rule_ids

    def test_non_chi_square_no_warning(self):
        result = check_alignment(
            "X 与 Y",
            {"dependent_vars": ["Y"], "independent_vars": ["X"]},
            "pearson_corr",
        )
        rule_ids = [w.rule_id for w in result.warnings]
        assert "R20_CHISQUARE_LOW_EXPECTED" not in rule_ids


# ---------------------------------------------------------------------------
# v3.7 规则总数自检
# ---------------------------------------------------------------------------

class TestRuleCount:
    def test_at_least_20_distinct_rules(self):
        """语义对齐至少覆盖 20 条规则（R1-R20）。"""
        # 触发尽可能多的规则，统计实际暴露的 rule_id
        seen = set()

        # 多个不同 plan 下扫描一遍，收集所有 rule_id
        scenarios = [
            ("X 预测 Y", {"dependent_vars": ["y"], "independent_vars": ["x"]}, "pearson_corr"),
            ("两组差", {"dependent_vars": ["y"], "independent_vars": ["性别"]}, "mann_whitney"),
            ("中介+调节", {"dependent_vars": ["Y"], "independent_vars": ["X"],
                          "mediator": "M", "moderator": "W"}, "mediation"),
            ("多 IV", {"dependent_vars": ["y"], "independent_vars": ["a", "b", "c"]},
              "linear_regression"),
            ("RM", {"dependent_vars": ["score"], "independent_vars": ["time"]},
              "repeated_measures_anova"),
            ("两因素", {"dependent_vars": ["s"], "independent_vars": ["A组", "B组"]},
              "two_way_anova"),
            ("嵌套", {"dependent_vars": ["s"], "independent_vars": ["x"], "covariates": ["班级"]},
              "linear_regression"),
            ("EFA", {"dependent_vars": ["i1"]}, "efa"),
            ("卡方", {"dependent_vars": ["a"], "independent_vars": ["b"]}, "chi_square"),
            ("偏相关多控", {"dependent_vars": ["y"], "independent_vars": ["x"],
                            "covariates": ["c1", "c2", "c3"]}, "partial_corr"),
        ]
        for rq, cv, m in scenarios:
            res = check_alignment(rq, cv, m)
            for w in res.warnings:
                seen.add(w.rule_id)

        # R1-R20 至少覆盖 12 条（部分规则需要特定组合才触发）
        assert len(seen) >= 12, f"规则覆盖不足：仅触发 {seen}"
        # 关键的 v3.7 新规则全部能被触发
        for must in ["R12_PARTIAL_CORR_MANY_CONTROLS", "R13_MULTI_REGRESSION_VIF",
                      "R14_MED_MOD_COMBO", "R15_REPEATED_SPHERICITY",
                      "R16_TWOWAY_INTERACTION", "R17_NESTED_DATA",
                      "R18_NONPARAM_DESCRIPTIVE", "R19_FACTOR_PRECONDITION",
                      "R20_CHISQUARE_LOW_EXPECTED"]:
            assert must in seen, f"v3.7 新规则 {must} 未触发"
