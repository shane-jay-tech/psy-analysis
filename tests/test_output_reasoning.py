"""src/output/reasoning.py 解释文案生成器特征化测试（s918-29）。

合成最小 output dict 调 generate_reasoning：只断言结构（四段非空 / StepCheck 形状）
与文案**存在性**，不评价文案或统计口径是否恰当。src 零改动。
"""
from types import SimpleNamespace

import pytest

from src.output.reasoning import (
    AnalysisReasoning,
    StepCheck,
    TEST_TEMPLATES,
    generate_reasoning,
)

DEFAULT_STEPS = ["执行统计分析", "输出结果和图表"]
DEFAULT_GUIDE = "请查看上方的统计结果表格和检验指标。"


def _plan(dv=("焦虑分", "抑郁分"), iv=("组别",)):
    return SimpleNamespace(dependent_vars=list(dv), independent_vars=list(iv))


_UNSET = object()


def _out(test_type="descriptive", name="描述统计", plan=_UNSET, result=None, **kw):
    base = {
        "test_type": test_type,
        "test_name_zh": name,
        "plan": _plan() if plan is _UNSET else plan,
        "result": result,
        "assumptions": {},
    }
    base.update(kw)
    return base


def test_descriptive_returns_all_four_sections_non_empty():
    ar = generate_reasoning(_out("descriptive", "描述统计"))

    assert isinstance(ar, AnalysisReasoning)
    assert ar.test_type == "descriptive" and ar.test_name_zh == "描述统计"
    assert ar.why_this_test and ar.interpretation_guide
    assert ar.analysis_steps and all(isinstance(s, str) for s in ar.analysis_steps)
    assert ar.data_requirements
    assert ar.learning_card is not None


def test_stepcheck_fields_have_their_declared_types():
    ar = generate_reasoning(_out("descriptive"))

    for step in ar.data_requirements + ar.assumption_checks:
        assert isinstance(step, StepCheck)
        assert isinstance(step.name, str) and step.name
        assert isinstance(step.result, str)
        assert isinstance(step.passed, bool)
        assert isinstance(step.detail, str)


def test_plan_variables_are_injected_and_truncated():
    plan = _plan(dv=tuple(f"v{i}" for i in range(1, 8)), iv=("g1", "g2", "g3", "g4"))

    why = generate_reasoning(_out("independent_ttest", "独立样本t检验", plan=plan)).why_this_test

    assert "v1, v2, v3, v4, v5" in why and "等7个" in why
    assert "g1, g2, g3" in why and "g4" not in why


@pytest.mark.parametrize(
    "test_type,expected_reqs",
    [("descriptive", 2), ("independent_ttest", 2), ("paired_ttest", 2),
     ("one_way_anova", 2), ("cronbach_alpha", 2), ("mediation", 2),
     ("moderation", 1), ("ancova", 1), ("no_such_type", 0)],
)
def test_data_requirements_are_per_branch_fixed_length(test_type, expected_reqs):
    assert len(generate_reasoning(_out(test_type, "X", result=None)).data_requirements) == expected_reqs


def test_unknown_test_type_falls_back_to_default_copy_and_steps():
    ar = generate_reasoning(_out("no_such_type", "自定义分析", plan=None))

    assert ar.why_this_test == "已选择「自定义分析」进行数据分析。"
    assert ar.analysis_steps == DEFAULT_STEPS
    assert ar.interpretation_guide == DEFAULT_GUIDE
    assert ar.alternatives == []


def test_empty_output_dict_does_not_raise():
    ar = generate_reasoning({})

    assert ar.test_type == "" and ar.why_this_test == "已选择「」进行数据分析。"
    assert ar.analysis_steps == DEFAULT_STEPS


def test_efa_kmo_gate_flips_at_zero_point_six():
    for kmo, passed in [(0.42, False), (0.6, True), (0.75, True)]:
        reqs = generate_reasoning(_out("efa", "探索性因子分析", result=SimpleNamespace(kmo=kmo))).data_requirements

        kmo_step = next(s for s in reqs if s.name == "KMO抽样充分性")
        assert kmo_step.result == f"KMO={kmo}"
        assert kmo_step.passed is passed


def test_assumption_checks_stay_empty_without_a_result_object():
    assert generate_reasoning(_out("independent_ttest", "t", result=None)).assumption_checks == []

    result = SimpleNamespace(assumption_homogeneity={"p_value": 0.01, "statistic": 5.2, "passed": False})
    ar = generate_reasoning(_out("independent_ttest", "t", result=result))

    assert [(s.name, s.result, s.passed) for s in ar.assumption_checks] == [
        ("方差齐性（Levene）", "未通过", False)
    ]
    assert "p=0.01" in ar.assumption_checks[0].detail


def test_alpha_injection_is_currently_a_noop_placeholder_missing_from_templates():
    """`_build_guide` 用 replace("当前α=", ...) 注入实测 α，但**没有任何模板含这个占位**，
    注入永不生效；α 值不进解读指南。本例钉住该缺陷，补占位后会失败——届时翻正。"""
    ar = generate_reasoning(_out("cronbach_alpha", "信度", result=SimpleNamespace(alpha=0.82)))

    assert ar.interpretation_guide == TEST_TEMPLATES["cronbach_alpha"]["guide"]
    assert "0.82" not in ar.interpretation_guide


def test_effect_size_appends_only_when_guide_lacks_the_word():
    tmpl_guide = TEST_TEMPLATES["independent_ttest"]["guide"]
    with_es = generate_reasoning(
        _out("independent_ttest", "t", result=SimpleNamespace(effect_size=0.8, effect_size_name="d"))
    ).interpretation_guide
    appended = "" if "效应量" in tmpl_guide else " 效应量：d=0.8"

    assert with_es == tmpl_guide + appended


def test_data_quality_warnings_are_a_noop_branch():
    class DQ:
        warnings = ["缺失 12%"]

    plain = generate_reasoning(_out("descriptive", "描述统计"))
    with_dq = generate_reasoning(_out("descriptive", "描述统计", data_quality=DQ()))

    assert with_dq.interpretation_guide == plain.interpretation_guide
    assert with_dq.alternatives == plain.alternatives
