"""报告字段统一口径测试：α／ω／项目数／样本量／CI 的字段名、缺字段提示、阈值中立。

对应信箱单 20260925-120658-c36e。红线：本件只验"字段怎么书写"，
不核对任何统计数值结论 —— 数值一律以字面断言原样搬运。
"""

from __future__ import annotations

import dataclasses
import math

import pytest

from src.analysis.reliability_bands import RELIABILITY_BANDS, UNACCEPTABLE
from src.output.report_fields import (
    REPORT_FIELDS_VERSION,
    REQUIRED_REPORT_FIELDS,
    collect_report_fields,
    format_value,
    missing_fields,
    read_field,
    render_report_fields,
)


def _result(**kw):
    base = {
        "alpha": 0.8125,
        "omega_value": 0.83,
        "n_items": 12,
        "n_cases": 240,
        "ci_lower": 0.76,
        "ci_upper": 0.855,
    }
    base.update(kw)
    for k in list(base):
        if base[k] is _DELETE:
            del base[k]
    return base


class _Delete:
    pass


_DELETE = _Delete()

# ---------------- 版本与字段清单 ----------------

def test_report_fields_dictionary_has_version():
    assert REPORT_FIELDS_VERSION == "psy-analysis/report-fields/v1"
    assert REQUIRED_REPORT_FIELDS == ("alpha", "omega", "n_items", "n_cases", "ci")


# ---------------- 字段名统一（别名） ----------------

def test_omega_alias_omega_value_is_unified():
    """现存载体把 ω 写成 omega_value（reliability.Rel 数据类），字典面统一读作 omega。"""
    value, miss = read_field(_result(), "omega")
    assert miss is None and value == 0.83


def test_item_count_alias_is_unified():
    value, miss = read_field({"item_count": 8}, "n_items")
    assert miss is None and value == 8


def test_sample_size_aliases_are_unified():
    for key in ("n_obs", "sample_size", "total_n", "n"):
        value, miss = read_field({key: 133, "n_items": 5}, "n_cases")
        assert miss is None, key
        assert value == 133, key


def test_ci_reads_endpoint_pair():
    value, miss = read_field(_result(), "ci")
    assert miss is None and value == (0.76, 0.855)


# ---------------- 缺字段提示（不伪完整） ----------------

def test_missing_field_produces_explicit_hint():
    lines = render_report_fields(_result(omega_value=None))
    assert any(ln.startswith("⚠ 缺字段：") and "ω" in ln for ln in lines)


def test_missing_field_never_renders_placeholder():
    """缺字段不得被写成 "-"／"?" 这类"看起来是一格"的占位符。"""
    lines = render_report_fields(_result(alpha=_DELETE))
    joined = "\n".join(lines)
    assert " = -" not in joined and "= ?" not in joined
    assert any(ln.startswith("⚠ 缺字段：α") for ln in lines)


def test_nan_is_reported_as_missing_not_rendered():
    assert math.isnan(float("nan"))
    value, miss = read_field(_result(alpha=float("nan")), "alpha")
    assert value is None and miss is not None and "NaN" in miss.reason


def test_type_mismatch_is_reported_with_the_offending_key():
    """现存反面形态：anova 把 effect_size_ci 写成字符串。类型不符必须点名，不静默。"""
    value, miss = read_field({"ci": "0.76~0.855"}, "ci")
    assert value is None
    assert miss is not None and "类型不符" in miss.reason


def test_collect_covers_every_requested_field_exactly_once():
    source = _result(omega_value=_DELETE)
    values, missing = collect_report_fields(source)
    assert set(values) | {m.field for m in missing} == set(REQUIRED_REPORT_FIELDS)
    assert "omega" not in values


# ---------------- 数值零改动 ----------------

def test_default_render_does_not_round():
    lines = render_report_fields(_result())
    assert "α = 0.8125" in lines, "默认书写口径必须原样搬运数值，不做舍入"
    assert "95% CI = [0.76, 0.855]" in lines


def test_explicit_decimals_matches_repo_rounding_call():
    """显式位数只能复现仓内既有 `round()` 行为（半偶），不得引入第二种舍入规则。

    实测：`format_value(0.8125, decimals=3)` 与 `round(0.8125, 3)` 同为 `0.812`
    （末位是"五成双"，不是"五入"）⇒ 与 `reliability.py` 的 `round(x, 3)` 同型可比。
    本班不裁"该报 0.812 还是 0.813"，见 result 遗留问题 2。
    """
    assert format_value(0.8125, decimals=3) == str(round(0.8125, 3))
    assert format_value(240, decimals=3) == "240", "整数计数不写成小数"
    assert format_value(0.8125, decimals=None) == "0.8125", "默认原样搬运"


def test_render_does_not_mutate_source():
    source = _result()
    before = dict(source)
    render_report_fields(source)
    assert source == before


# ---------------- 阈值中立（不自动替用户判断） ----------------

def test_renderer_emits_no_band_labels():
    """模板面不得出现任何档位标签：与 reliability_bands 的标签集逐条比对。"""
    band_labels = {b.label for b in RELIABILITY_BANDS} | {UNACCEPTABLE.label}
    assert band_labels, "档位标签集为空 ⇒ 本用例失去判别力"
    for alpha in (0.35, 0.62, 0.74, 0.95):
        lines = "\n".join(render_report_fields(_result(alpha=alpha)))
        for label in band_labels:
            assert label not in lines, f"渲染面出现档位标签：{label}"


def test_threshold_decision_stays_with_the_reader():
    values, missing = collect_report_fields(_result())
    assert missing == []
    assert set(values) == set(REQUIRED_REPORT_FIELDS)
    assert all(not str(v).startswith(("通过", "不通过", "合格")) for v in values.values())


# ---------------- 真实结果对象（dataclass）同样可读 ----------------

@dataclasses.dataclass
class _FakeRel:
    alpha: float
    omega_value: float
    n_items: int
    n_cases: int
    ci_lower: float
    ci_upper: float


def test_object_source_works_like_mapping_source():
    obj = _FakeRel(0.8125, 0.83, 12, 240, 0.76, 0.855)
    lines = render_report_fields(obj)
    assert lines == [
        "α = 0.8125",
        "ω = 0.83",
        "项目数 k = 12",
        "有效样本 N = 240",
        "95% CI = [0.76, 0.855]",
    ]


def test_missing_fields_helper_lists_names_for_gates():
    assert missing_fields({}) == ["alpha", "omega", "n_items", "n_cases", "ci"]
    assert missing_fields(_FakeRel(0.8, 0.82, 10, 200, 0.7, 0.9)) == []


@pytest.mark.parametrize("bad", [None, "", "0.8", float("nan"), [], {}, 0.8125])
def test_unusable_inputs_become_hints(bad):
    """除真数值外，一切形态都必须变成提示而不是值。"""
    value, miss = read_field({"alpha": bad}, "alpha")
    if bad == 0.8125:
        assert miss is None and value == 0.8125
    else:
        assert value is None and miss is not None and miss.field == "alpha"
