"""分析结果 schema 校验测试：结果体／警告面／样本量／版本四域。

对应信箱单 20260925-120713-7575。红线：不得为让现网通过而放宽判据；
本件里的"现网真结果"用例是**把现状钉住**（它当前就该报 sample_size/missing），不是让它变绿。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analysis.contracts import ANALYSIS_RESULT_SCHEMA, AnalysisResult
from src.analysis.result_schema import (
    REQUIRED_RESULT_KEYS,
    SUPPORTED_SCHEMA_VERSIONS,
    ResultSchemaError,
    SchemaReport,
    enforce_result,
    find_sample_size,
    iter_reports,
    validate_result,
)


def _ok_output(**over):
    """一份"契约齐全"的合成结果（形状照 runner.run_analysis 的初始化面）。"""
    base = {
        "schema_version": ANALYSIS_RESULT_SCHEMA,
        "test_type": "independent_ttest",
        "canonical_method_id": "independent_ttest",
        "test_name_zh": "独立样本 t 检验",
        "plan": object(),
        "result": None,
        "assumptions": {},
        "errors": [{"severity": "error", "message": "组别取值不足"}],
        "charts_data": {},
        "reasoning": None,
        "data_quality": None,
        "missing_strategy": "listwise",
        "n_cases": 80,
    }
    base.update(over)
    for k in list(base):
        if base[k] is _DELETE:
            del base[k]
    return base


class _Delete:
    pass


_DELETE = _Delete()


def _kinds(report: SchemaReport):
    return {(i.domain, i.kind) for i in report.issues}


# ---------------- 版本域 ----------------

def test_supported_version_is_the_contracts_constant():
    assert SUPPORTED_SCHEMA_VERSIONS == frozenset({ANALYSIS_RESULT_SCHEMA})


def test_missing_version_is_an_error():
    report = validate_result(_ok_output(schema_version=_DELETE))
    assert ("version", "missing") in _kinds(report)
    assert not report.ok


def test_unknown_version_is_rejected_not_downgraded():
    report = validate_result(_ok_output(schema_version="psy-analysis/analysis-result/v9"))
    assert ("version", "unknown_version") in _kinds(report)


def test_nan_and_wrong_type_versions_are_named():
    assert ("version", "nan") in _kinds(validate_result(_ok_output(schema_version=float("nan"))))
    assert ("version", "type") in _kinds(validate_result(_ok_output(schema_version=1)))


# ---------------- 结果体域 ----------------

@pytest.mark.parametrize("key", [k for k in REQUIRED_RESULT_KEYS if k != "schema_version"])
def test_every_required_key_missing_is_reported(key):
    report = validate_result(_ok_output(**{key: _DELETE}))
    assert any(i.domain == "result" and i.kind == "missing" and key in i.message
               for i in report.issues), key


def test_assumptions_and_charts_data_must_be_mappings():
    report = validate_result(_ok_output(assumptions=[], charts_data=None))
    assert ("result", "type") in _kinds(report)
    assert ("result", "missing") in _kinds(report)


def test_empty_result_object_is_reported():
    assert validate_result({}).ok is False
    assert validate_result(None).issues[0].kind == "missing"


# ---------------- 警告域 ----------------

def test_plain_string_warning_is_accepted():
    report = validate_result(_ok_output(result=object(), errors=["仅提示：样本偏小"]))
    assert report.ok and report.issues == []


def test_blank_warning_message_is_reported():
    report = validate_result(_ok_output(errors=["   "]))
    assert ("warnings", "empty") in _kinds(report)


def test_warning_entry_without_message_is_reported():
    report = validate_result(_ok_output(errors=[{"severity": "warning"}]))
    assert ("warnings", "nan") in _kinds(report)


def test_unknown_severity_is_reported():
    report = validate_result(_ok_output(errors=[{"severity": "fatal", "message": "x"}]))
    assert ("warnings", "bad_severity") in _kinds(report)


def test_warning_entry_of_unsupported_shape_is_reported():
    report = validate_result(_ok_output(errors=[42]))
    assert ("warnings", "type") in _kinds(report)


def test_data_quality_warnings_must_be_strings():
    class _DQ:
        warnings = ["ok", 7]

    report = validate_result(_ok_output(data_quality=_DQ()))
    assert ("warnings", "type") in _kinds(report)


def test_errors_list_itself_wrong_type():
    report = validate_result(_ok_output(errors="全部通过"))
    assert ("warnings", "type") in _kinds(report)


# ---------------- 伪完整 ----------------

def test_result_none_without_error_entry_is_pseudo_complete():
    report = validate_result(_ok_output(result=None, errors=[]))
    assert ("result", "pseudo_complete") in _kinds(report)


def test_result_none_with_error_entry_is_not_pseudo_complete():
    report = validate_result(_ok_output(result=None,
                                        errors=[{"severity": "error", "message": "数据不足"}]))
    assert ("result", "pseudo_complete") not in _kinds(report)
    assert report.ok


# ---------------- 样本量域 ----------------

@pytest.mark.parametrize("key", ["n", "n_cases", "n_obs", "n_valid", "sample_size"])
def test_any_declared_carrier_supplies_sample_size(key):
    payload = {k: v for k, v in _ok_output().items() if k != "n_cases"}
    payload[key] = 64
    report = validate_result(payload)
    assert report.sample_size == 64


def test_nested_result_carrier_is_used():
    class _R:
        n_cases = 42

    report = validate_result(_ok_output(result=_R(), n_cases=_DELETE))
    assert report.sample_size == 42


def test_sample_size_nan_is_not_filled_with_zero():
    value, issue = find_sample_size({"n_cases": float("nan")})
    assert value is None and issue.kind == "nan"


@pytest.mark.parametrize("bad", [0, -5, 3.5, "80", True])
def test_unusable_sample_sizes_are_rejected(bad):
    value, issue = find_sample_size({"n_cases": bad})
    assert value is None and issue is not None and issue.domain == "sample_size"


def test_integral_float_sample_size_is_accepted_as_int():
    value, issue = find_sample_size({"n_cases": 80.0})
    assert issue is None and value == 80


# ---------------- 降级与报错出口 ----------------

def test_raise_mode_raises_with_the_full_report():
    with pytest.raises(ResultSchemaError) as exc:
        enforce_result(_ok_output(schema_version=_DELETE), mode="raise")
    assert exc.value.report.errors
    assert "version/missing" in str(exc.value)


def test_annotate_mode_adds_report_and_error_entry_without_touching_values():
    source = _ok_output(schema_version=_DELETE, errors=[])
    before = {k: v for k, v in source.items()}
    enforce_result(source, mode="annotate")
    assert source["schema_validation"]["ok"] is False
    assert source["schema_validation"]["schema_version"] is None
    assert any(e.get("severity") == "error" for e in source["errors"])
    for k, v in before.items():
        assert source[k] == v or source[k] is v, f"既有键被改写：{k}"


def test_report_mode_writes_nothing():
    source = _ok_output(schema_version="x")
    report = enforce_result(source, mode="report")
    assert isinstance(report, SchemaReport) and "schema_validation" not in source


def test_unknown_mode_is_a_hard_error():
    with pytest.raises(ValueError):
        enforce_result(_ok_output(), mode="whatever")


def test_valid_result_passes_clean_and_writes_no_annotation():
    source = _ok_output(result=object(), errors=[])
    enforce_result(source, mode="annotate")
    assert "schema_validation" not in source


def test_iter_reports_keeps_each_verdict_separate():
    reports = iter_reports([_ok_output(), _ok_output(schema_version=_DELETE)])
    assert [r.ok for r in reports] == [True, False]


# ---------------- 现网真结果（钉现状，不放宽） ----------------

def test_live_independent_ttest_result_reports_missing_sample_size():
    """真跑一次 independent_ttest：版本域应通过，样本量域**今天必报 missing**。

    实测（`TTestResult` 无 n 族字段、runner 输出也无顶层 n）⇒ 本用例是对现状的取证，
    不是对目标的妥协：修法是给契约补一等公民样本量，而不是把判据放宽。
    """
    from src.analysis.runner import run_analysis
    from src.parser.intent_resolver import AnalysisPlan

    rng = np.random.default_rng(7)
    frame = pd.DataFrame({
        "score": np.concatenate([rng.normal(70, 8, 40), rng.normal(65, 8, 40)]),
        "grp": ["A"] * 40 + ["B"] * 40,
    })
    plan = AnalysisPlan(test_type="independent_ttest", dependent_vars=["score"],
                        independent_vars=["grp"], raw_request="schema-probe")
    output = run_analysis(frame, plan)

    assert isinstance(output, AnalysisResult)
    report = validate_result(output)
    assert report.schema_version == ANALYSIS_RESULT_SCHEMA
    assert report.sample_size is None
    assert ("sample_size", "missing") in _kinds(report)
    assert ("version", "missing") not in _kinds(report)
    assert ("result", "pseudo_complete") not in _kinds(report), "真跑出结果，不该被判伪完整"


def test_reliability_result_carries_its_own_sample_size():
    """同一判据在带 n 的结果族上必须直接通过 ⇒ 证明缺的是契约面，不是判据太严。"""
    from src.analysis.reliability import cronbach_alpha

    rng = np.random.default_rng(11)
    frame = pd.DataFrame(rng.integers(1, 6, size=(120, 6)), columns=[f"Q{i}" for i in range(1, 7)])
    res = cronbach_alpha(frame, list(frame.columns))
    value, issue = find_sample_size(res)
    assert issue is None and value == 120
