# -*- coding: utf-8 -*-
"""AnalysisResult 版本化契约回归测试（d914-74）。

纯 Python 数据结构断言：不调 run_analysis、不构造统计计划、不碰统计结果。
"""
import json

from src.analysis.contracts import ANALYSIS_RESULT_SCHEMA, AnalysisResult


def test_a_schema_constant_value():
    assert ANALYSIS_RESULT_SCHEMA == "psy-analysis/analysis-result/v1"


def test_b_default_schema_version_set():
    r = AnalysisResult()
    assert r["schema_version"] == ANALYSIS_RESULT_SCHEMA
    assert r.schema_version == ANALYSIS_RESULT_SCHEMA


def test_c_existing_version_not_overwritten():
    r = AnalysisResult({"schema_version": "x"})
    assert r.schema_version == "x"


def test_d_dict_compatibility():
    r = AnalysisResult({"test_type": "ttest_ind"})
    assert r["test_type"] == "ttest_ind"
    assert r.get("nope") is None
    json.dumps(dict(r), ensure_ascii=False)  # 可序列化


def test_e_canonical_method_id_three_level_fallback():
    assert AnalysisResult({"canonical_method_id": "x"}).canonical_method_id == "x"
    assert AnalysisResult({"test_type": "y"}).canonical_method_id == "y"
    assert AnalysisResult({}).canonical_method_id == ""
    assert AnalysisResult({"canonical_method_id": None, "test_type": "y"}).canonical_method_id == "y"


def test_f_kwargs_construction():
    assert AnalysisResult(a=1)["a"] == 1
