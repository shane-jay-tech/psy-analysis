"""`src/analysis/field_lineage.py` 的血缘登记件测试（信箱单 20260925-120653-3298）。

三件事：① 登记表自洽（引用到的 spec／载体／清洗规则／版本锚都必须存在）；
② 每条溯源链的代码锚点**必须在世**（改了名就红，不做 skip）；
③ 红线面：登记表结构上装不进任何统计数值。

引仓内件一律"缺件即红"，不用 ``skipif`` 判文件在不在
（口径来源：``tests/test_skip_gates_are_explained_and_not_misjudged.py``）。
"""

from __future__ import annotations

import pathlib
import re

import pytest

from src.analysis import field_lineage as fl
from src.analysis import result_schema
from src.output import report_fields

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEMO_DIR = REPO_ROOT / "demo_projects" / "psychology_questionnaire_demo"

#: 锚点书写：``路径::符号``，路径必须是仓内相对路径。
ANCHOR_RE = re.compile(r"^(?P<file>[^\s:]+\.py)(?:::(?P<symbol>[A-Za-z_][A-Za-z0-9_]*))?$")


def _all_specs() -> list[fl.LineageSpec]:
    return list(fl.FIELD_SPECS.values())


# ---------------------------------------------------------------------------
# ① 登记表自洽
# ---------------------------------------------------------------------------

def test_registry_is_self_consistent():
    for spec in _all_specs():
        assert spec.raw_source in fl.RAW_SOURCES, spec.spec_id
        for rule in spec.cleaning_rules:
            assert rule in fl.CLEANING_RULES, (spec.spec_id, rule)
        for domain in spec.version_domains:
            assert domain in fl.VERSION_ANCHORS, (spec.spec_id, domain)
        assert spec.version_domains, spec.spec_id


def test_every_mapping_points_to_a_registered_spec():
    for name, sid in fl.EXACT_FIELD_SPEC.items():
        assert sid in fl.FIELD_SPECS, (name, sid)
    for rules in (fl.SUFFIX_RULES, fl.PREFIX_RULES):
        for _, sid in rules:
            assert sid in fl.FIELD_SPECS, sid


def test_specs_are_unique_and_non_empty():
    assert len(_all_specs()) >= 20
    for spec in _all_specs():
        assert spec.title, spec.spec_id
        assert len(spec.chain()) == 5


# ---------------------------------------------------------------------------
# ② 代码锚点必须在世（改名即红）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("spec", _all_specs(), ids=lambda s: s.spec_id)
def test_extraction_anchor_exists_in_repo(spec):
    m = ANCHOR_RE.match(spec.extraction_anchor)
    assert m, f"锚点书写不合规范：{spec.extraction_anchor!r}"
    path = REPO_ROOT / m.group("file")
    assert path.is_file(), f"锚点文件不存在：{path}"
    symbol = m.group("symbol")
    if symbol:
        text = path.read_text(encoding="utf-8")
        assert re.search(rf"\b{re.escape(symbol)}\b", text), (
            f"锚点符号 {symbol} 不在 {m.group('file')} 里（被改名或删了 ⇒ 血缘断链）"
        )


@pytest.mark.parametrize("rule", list(fl.CLEANING_RULES.values()),
                         ids=lambda c: c.rule_id)
def test_cleaning_rule_anchor_exists_in_repo(rule):
    if rule.rule_id == "C0_none_declared":
        assert rule.anchor == "（无）"
        return
    m = ANCHOR_RE.match(rule.anchor)
    assert m, f"清洗锚点书写不合规范：{rule.anchor!r}"
    path = REPO_ROOT / m.group("file")
    assert path.is_file(), f"清洗锚点文件不存在：{path}"
    text = path.read_text(encoding="utf-8")
    assert re.search(rf"\b{re.escape(m.group('symbol'))}\b", text), (
        f"清洗符号 {m.group('symbol')} 不在 {m.group('file')} 里"
    )


def test_version_anchors_point_at_real_constants():
    assert (REPO_ROOT / "src/analysis/contracts.py").is_file()
    from src.analysis import contracts
    assert contracts.ANALYSIS_RESULT_SCHEMA
    from src.output import report_fields as rf
    assert rf.REPORT_FIELDS_VERSION
    from src.questionnaire import data_dictionary as dd
    assert dd.CODEBOOK_VERSION


# ---------------------------------------------------------------------------
# ③ 红线：登记面装不进统计数值
# ---------------------------------------------------------------------------

def test_registry_carries_no_numeric_values():
    """登记表任何一项都不允许是 int/float —— 数值不属血缘登记面。"""

    offenders: list[str] = []
    for spec in _all_specs():
        for value in (spec.raw_source, spec.extraction_anchor, *spec.cleaning_rules,
                      *spec.version_domains):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                offenders.append(f"{spec.spec_id}:{value!r}")
        for value in (spec.value_bearing, spec.conclusion_eligible):
            assert isinstance(value, bool)
    assert offenders == []


def test_gate_and_classify_are_pure_over_names():
    names = ["alpha", "n_cases", "charts_data", "nope_xyz"]
    first = fl.classify_fields(names)
    second = fl.classify_fields(names)
    assert first.traced == second.traced
    assert first.untraceable == second.untraceable
    gate_a = fl.conclusion_gate(names)
    gate_b = fl.conclusion_gate(names)
    assert (gate_a.blocked, gate_a.supporting, gate_a.ineligible) == \
           (gate_b.blocked, gate_b.supporting, gate_b.ineligible)


# ---------------------------------------------------------------------------
# ④ 验收面：判据点名的字段全部有登记
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", list(report_fields.REQUIRED_REPORT_FIELDS))
def test_report_fields_are_registered(name):
    spec = fl.spec_for(name)
    assert spec is not None, f"报告字段 {name} 没有溯源规范"
    assert spec.value_bearing, f"报告字段 {name} 应登记为承载统计数值"


@pytest.mark.parametrize("key", list(result_schema.REQUIRED_RESULT_KEYS))
def test_required_result_keys_are_registered(key):
    assert fl.spec_for(key) is not None, f"结果体必需键 {key} 没有溯源规范"


def test_sample_size_collision_is_registered_as_two_different_specs():
    """观测 N 与建议样本量必须分属两条规范，否则"样本够"这个结论会指错血缘。"""

    observed = fl.spec_for("n_cases")
    recommended = fl.spec_for("post_hoc_power")
    assert observed is not None and recommended is not None
    assert observed.spec_id != recommended.spec_id
    assert recommended.conclusion_eligible is False


# ---------------------------------------------------------------------------
# ⑤ 随机抽样可回溯到原始记录
# ---------------------------------------------------------------------------

def test_demo_fixture_is_present_and_has_rows():
    """缺件即红：演示件不在就是登记失效，不允许 skip 掉。"""

    assert DEMO_DIR.is_dir(), f"演示项目目录缺失：{DEMO_DIR}"
    probe = fl.trace_project_dir(DEMO_DIR, "alpha", row=0)
    assert probe.reached_raw_record is True, probe.detail
    assert probe.raw_row, "回溯到的原始记录行为空"


@pytest.mark.parametrize("seed", [68, 2026, 9])
def test_random_sampled_value_bearing_fields_trace_to_raw_record(seed):
    statistical = [
        name for name in list(report_fields.REQUIRED_REPORT_FIELDS)
        + list(result_schema.REQUIRED_RESULT_KEYS)
        if (spec := fl.spec_for(name)) is not None and spec.value_bearing
        and fl.RAW_SOURCES[spec.raw_source].raw_backable
    ]
    picked = fl.sample_fields(statistical, seed=seed, k=3)
    assert picked
    for name in picked:
        probe = fl.trace_project_dir(DEMO_DIR, name, row=1)
        assert probe.chain[0].startswith("字段族"), probe.chain
        assert probe.reached_raw_record is True, (name, probe.detail)


def test_runtime_only_fields_never_claim_a_raw_record():
    for name in ("charts_data", "snapshot_id", "created_at", "provenance"):
        probe = fl.trace_project_dir(DEMO_DIR, name, row=0)
        assert probe.reached_raw_record is False
        assert "不对应任何一条原始记录" in probe.detail


def test_untraceable_field_blocks_conclusion():
    gate = fl.conclusion_gate(["alpha", "totally_unknown_field_xyz"])
    assert gate.blocked is True
    assert gate.untraceable == ["totally_unknown_field_xyz"]
    lines = gate.report_lines()
    assert any("🚫" in line for line in lines)


def test_ineligible_field_also_blocks_conclusion():
    gate = fl.conclusion_gate(["alpha", "snapshot_id"])
    assert gate.blocked is True
    assert gate.ineligible == ["snapshot_id"]
    assert gate.supporting == ["alpha"]


def test_clean_eligible_set_passes_gate():
    gate = fl.conclusion_gate(["alpha", "omega", "ci", "n_cases", "n_items"])
    assert gate.blocked is False
    assert len(gate.supporting) == 5


def test_missing_archive_dir_reports_broken_chain_not_crash(tmp_path):
    probe = fl.trace_archive_dir(tmp_path / "nope", "alpha")
    assert probe.reached_raw_record is False
    assert "缺 params.json 或 data.csv" in probe.detail


def test_archive_trace_reaches_row_through_params_json(tmp_path):
    one = tmp_path / "20260925_163000_abcdef0123456789"
    one.mkdir()
    (one / "params.json").write_text(
        '{"archive_id": "abcdef0123456789", "file_name": "t.csv", '
        '"n_rows": 2, "n_cols": 2, "columns": ["组别", "焦虑得分"]}',
        encoding="utf-8")
    (one / "data.csv").write_text("组别,焦虑得分\n实验,4\n对照,2\n", encoding="utf-8")
    probe = fl.trace_archive_dir(one, "alpha", row=1)
    assert probe.reached_raw_record is True, probe.detail
    assert probe.raw_row == {"组别": "对照", "焦虑得分": "2"}
    assert "t.csv" in probe.detail
