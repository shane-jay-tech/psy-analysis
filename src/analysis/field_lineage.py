"""分析字段血缘登记（field lineage registry）v1 —— 只登记"字段←原始文件／抽取步骤／清洗规则／版本"。

信箱单 `20260925-120653-3298`。人读版登记表与不可追溯面取证见
``docs/insights/psy-field-lineage-20260925.md``。

四条硬边界（与同批 `data_dictionary` / `report_fields` / `result_schema` 同形）：

1. **不重算、不搬运任何统计数值**：本模块登记的只有"代码锚点名"与"版本常量名"，
   α／ω／效应量／置信区间／p 值／样本量的**数值一律不进本模块**（见
   ``tests/test_analysis_field_lineage.py`` 里"登记表不含任何数值字面量"那条结构断言）。
2. **不改判据、不接生产入口**：没有调用点在 ``runner`` / UI / 报告渲染里，
   本模块目前是**契约面本体**；接线属另一单。
3. **不写盘**：回溯探针（``trace_archive_dir``／``trace_project_dir``）只读，
   且只读 `params.json`／`data.csv` 的**表头与定位信息**，不参与任何计算。
4. **不可追溯即阻断结论**：``conclusion_gate`` 对登记表覆盖不到的字段、
   以及"无原始记录载体"的运行期字段（图表数据／快照 id／时间戳）一律判阻断，
   不给出"勉强可解释"的通道。

名词解释（避免与既有概念混淆）：

* **原始记录（raw record）**：一行用户数据（归档件 `archive/<id>/data.csv` 的一行，
  或工作区里当前 DataFrame 的一行）。
* **溯源链（chain）**：字段 → 抽取锚点 → 清洗规则 → 原始文件定位符 → 版本常量。
* **运行期字段（runtime-only）**：只在一次运行里存在、不对应任何原始记录的字段。
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

LINEAGE_VERSION = "psy-analysis/field-lineage/v1"

#: 登记表引用的版本常量（**只记常量名＋所在模块，不复制其值**）。
#: `result_schema.py` 已经声明"只引用 contracts 的版本号、不另立"，本模块同样不另立。
VERSION_ANCHORS: dict[str, str] = {
    "codebook": "src/questionnaire/data_dictionary.py::CODEBOOK_VERSION",
    "report_fields": "src/output/report_fields.py::REPORT_FIELDS_VERSION",
    "analysis_result": "src/analysis/contracts.py::ANALYSIS_RESULT_SCHEMA",
    "lineage": "LINEAGE_VERSION（本模块）",
}

#: 版本必挂集合：一条溯源链至少要挂上一个这里登记的版本锚。
REQUIRED_VERSION_DOMAINS: frozenset[str] = frozenset({"analysis_result", "lineage"})


# ---------------------------------------------------------------------------
# 原始文件登记
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RawSource:
    """一种"原始记录载体"：它在哪里、用什么定位、是否随仓入库。"""

    source_id: str
    description: str
    locator: str            # 人可复算的定位方式（文件名／键路径）
    tracked_in_git: bool    # False ⇒ gitignore 域，写坏了没有还原点，只读
    raw_backable: bool      # False ⇒ 该载体不对应"原始记录"，不得作结论字段


RAW_SOURCES: dict[str, RawSource] = {
    s.source_id: s for s in (
        RawSource(
            "R1_archive_copy",
            "一次完整分析的归档副本（隐私最小化后的 CSV，非用户原始文件本身）",
            "archive/<timestamp>_<archive_id>/data.csv ＋ 同目录 params.json",
            tracked_in_git=False,
            raw_backable=True,
        ),
        RawSource(
            "R2_workspace_upload",
            "用户当前会话上传的数据文件（原件不落盘为独立文件，仅以文件名与工作区快照存在）",
            "workspace['meta']／workspace['file_name']（src/utils/workspace.py）",
            tracked_in_git=False,
            raw_backable=True,
        ),
        RawSource(
            "R3_demo_fixture",
            "随仓的演示数据集（唯一可跨机复算的原始记录）",
            "demo_projects/psychology_questionnaire_demo/data.csv",
            tracked_in_git=True,
            raw_backable=True,
        ),
        RawSource(
            "R4_items_file",
            "题目文件（题号／量尺／反向题的来源）",
            "src/questionnaire/items_loader.py::parse_items_file 的入参文件",
            tracked_in_git=True,
            raw_backable=True,
        ),
        RawSource(
            "R5_registry",
            "仓内注册表／映射表（不来自任何用户数据）",
            "src/analysis/method_ids.py／method_catalog.py／config 的检验名映射",
            tracked_in_git=True,
            raw_backable=False,
        ),
        RawSource(
            "R6_runtime_only",
            "运行期派生物：图表负载、快照哈希、时间戳、卡片来源标签",
            "run_analysis 返回值／AnalysisResultCard 字段（无对应原始记录）",
            tracked_in_git=False,
            raw_backable=False,
        ),
        RawSource(
            "R7_plan_input",
            "用户在 UI 选定的分析计划（参数；其原始记录是归档件 params.json 的 params 节）",
            "src/parser/intent_resolver.py::AnalysisPlan 实例（随归档写在 params.json 的 params 节）",
            tracked_in_git=False,
            raw_backable=True,
        ),
    )
}


# ---------------------------------------------------------------------------
# 清洗规则登记
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CleaningRule:
    """一条清洗规则：锚点在哪、对字段做什么、会不会改数值。"""

    rule_id: str
    anchor: str
    effect: str
    changes_cell_values: bool
    report_only: bool


CLEANING_RULES: dict[str, CleaningRule] = {
    c.rule_id: c for c in (
        CleaningRule(
            "C1_column_bucketing",
            "src/questionnaire/import_cleaning.py::classify_columns",
            "决定哪些列进题目桶／人口学桶（分析变量的入选面）",
            changes_cell_values=False,
            report_only=False,
        ),
        CleaningRule(
            "C2_reverse_scoring",
            "src/questionnaire/import_cleaning.py::reverse_score",
            "反向题按量尺上下限翻转向尺（改取值，方向性影响 α／均值的输入面）",
            changes_cell_values=True,
            report_only=False,
        ),
        CleaningRule(
            "C3_invalid_detection",
            "src/questionnaire/import_cleaning.py::detect_invalid_responses",
            "标出越界作答（只标记，不静默改成缺失）",
            changes_cell_values=False,
            report_only=True,
        ),
        CleaningRule(
            "C4_dimension_scoring",
            "src/questionnaire/import_cleaning.py::compute_dimension_scores",
            "题目→维度分（派生列的产生步骤）",
            changes_cell_values=True,
            report_only=False,
        ),
        CleaningRule(
            "C5_missing_handling",
            "src/analysis/data_quality.py::handle_missing",
            "按 plan.missing_strategy 做行级剔除（默认 listwise），决定进入统计的有效行集",
            changes_cell_values=False,
            report_only=False,
        ),
        CleaningRule(
            "C6_quality_screening",
            "src/analysis/data_quality.py::data_quality_check",
            "恒定列／零方差列／缺失率／离群／正态性检查（只出报告与警告）",
            changes_cell_values=False,
            report_only=True,
        ),
        CleaningRule(
            "C7_privacy_redaction",
            "src/utils/guardrails.py::redact_dataframe_for_storage",
            "归档前删高敏感列、身份列稳定哈希（归档件与原件因此不逐字节等同）",
            changes_cell_values=True,
            report_only=False,
        ),
        CleaningRule(
            "C0_none_declared",
            "（无）",
            "该字段不经过任何清洗步骤",
            changes_cell_values=False,
            report_only=True,
        ),
    )
}


# ---------------------------------------------------------------------------
# 字段级溯源规范
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LineageSpec:
    """一个字段族（或一个字段）的溯源规范。

    ⚠ 这里登记的**只有锚点与定位符字符串**——任何统计数值都不属于本模块。
    """

    spec_id: str
    title: str
    raw_source: str                          # RAW_SOURCES 的键
    extraction_anchor: str                   # "文件::符号"
    cleaning_rules: tuple[str, ...]          # CLEANING_RULES 的键
    version_domains: tuple[str, ...]         # VERSION_ANCHORS 的键
    value_bearing: bool                      # True ⇒ 该字段承载统计数值，属红线面
    conclusion_eligible: bool                # False ⇒ 不得作为结论性陈述的支撑字段
    note: str = ""

    def chain(self) -> list[str]:
        """渲染成一条人可读的溯源链（不含任何数值）。"""
        src = RAW_SOURCES[self.raw_source]
        rules = "、".join(CLEANING_RULES[r].rule_id for r in self.cleaning_rules)
        vers = "、".join(f"{d}={VERSION_ANCHORS[d]}" for d in self.version_domains)
        return [
            f"字段族 {self.spec_id}（{self.title}）",
            f"抽取步骤 {self.extraction_anchor}",
            f"清洗规则 {rules}",
            f"原始文件 {src.source_id}：{src.locator}",
            f"版本 {vers}",
        ]


def _spec(spec_id: str, title: str, raw_source: str, extraction: str,
          cleaning: tuple[str, ...], versions: tuple[str, ...],
          *, value_bearing: bool, eligible: bool, note: str = "") -> LineageSpec:
    return LineageSpec(spec_id, title, raw_source, extraction, cleaning,
                       versions, value_bearing, eligible, note)


#: 按字段族登记。``FAMILY_RULES`` 负责把结果体里的**字段名**映射到这里的 spec_id。
FIELD_SPECS: dict[str, LineageSpec] = {
    s.spec_id: s for s in (
        _spec("S1_reliability_point", "信度点值（α／ω／CR／ICC／κ／分半／重测）",
              "R2_workspace_upload", "src/analysis/reliability.py::cronbach_alpha",
              ("C1_column_bucketing", "C2_reverse_scoring", "C5_missing_handling"),
              ("codebook", "report_fields", "lineage"),
              value_bearing=True, eligible=True,
              note="反向计分在清洗段就改变取值，因此 α 的血缘必须同时指向题目文件与清洗锚点。"),
        _spec("S2_ci_endpoint", "置信区间端点（ci_lower／ci_upper／bootstrap_ci／*_ci_*）",
              "R2_workspace_upload", "src/analysis/effect_size_ci.py::fisher_z_ci",
              ("C5_missing_handling",), ("report_fields", "analysis_result", "lineage"),
              value_bearing=True, eligible=True),
        _spec("S3_p_value", "显著性概率（p_value／chi2_p／bartlett_p／q_p_value／criterion_p）",
              "R2_workspace_upload", "src/analysis/ttest.py::independent_ttest",
              ("C5_missing_handling",), ("analysis_result", "lineage"),
              value_bearing=True, eligible=True),
        _spec("S4_test_statistic", "检验统计量与自由度（t_statistic／chi_sq／f_stat／df）",
              "R2_workspace_upload", "src/analysis/ttest.py::independent_ttest",
              ("C5_missing_handling",), ("analysis_result", "lineage"),
              value_bearing=True, eligible=True),
        _spec("S5_effect_size", "效应量（effect_size／eta_squared／r_squared／kmo／i_squared／pooled_effect）",
              "R2_workspace_upload", "src/analysis/effect_size_ci.py::fisher_z_ci",
              ("C5_missing_handling",), ("analysis_result", "lineage"),
              value_bearing=True, eligible=True),
        _spec("S6_sample_size", "样本量与计数（n_cases／n_obs／n_items／k／n_groups／n_total）",
              "R2_workspace_upload", "src/analysis/data_quality.py::data_quality_check",
              ("C5_missing_handling", "C6_quality_screening"), ("report_fields", "lineage"),
              value_bearing=True, eligible=True,
              note="⚠ 同名碰撞：RouteDecision.sample_size 是「建议样本量」（S21），"
                   "与观测 N 不是一回事，混用会让「N 够」这个结论指向错的血缘。"),
        _spec("S7_descriptive_table", "描述统计表（descriptive／group_stats／table／*_table）",
              "R2_workspace_upload", "src/analysis/descriptive.py::descriptive_stats",
              ("C5_missing_handling",), ("analysis_result", "lineage"),
              value_bearing=True, eligible=True),
        _spec("S8_variable_column", "题目／变量列本身（Q1…Qk、维度列）",
              "R4_items_file", "src/questionnaire/items_loader.py::parse_items_file",
              ("C1_column_bucketing", "C4_dimension_scoring"), ("codebook", "lineage"),
              value_bearing=False, eligible=True),
        _spec("S9_method_identity", "方法标识（test_type／canonical_method_id／method_id／test_name_zh）",
              "R5_registry", "src/analysis/method_catalog.py::resolve_method_id",
              ("C0_none_declared",), ("analysis_result", "lineage"),
              value_bearing=False, eligible=True),
        _spec("S10_plan_parameter", "分析计划参数（plan／parameters／confidence_level／formula）",
              "R7_plan_input", "src/parser/intent_resolver.py::AnalysisPlan",
              ("C0_none_declared",), ("analysis_result", "lineage"),
              value_bearing=False, eligible=True),
        _spec("S11_schema_version", "版本标记（schema_version／字典版本／报告字段版本）",
              "R5_registry", "src/analysis/contracts.py::ANALYSIS_RESULT_SCHEMA",
              ("C0_none_declared",), ("analysis_result", "lineage"),
              value_bearing=False, eligible=True),
        _spec("S12_warning_face", "警告与错误面（warnings／warning／errors／technical_notes／*_warning）",
              "R2_workspace_upload", "src/analysis/runner.py::run_analysis",
              ("C6_quality_screening",), ("analysis_result", "lineage"),
              value_bearing=False, eligible=True),
        _spec("S13_missing_meta", "缺失值处理元数据（missing_meta／missing_strategy／missing_pct／missing_cols）",
              "R2_workspace_upload", "src/analysis/data_quality.py::handle_missing",
              ("C5_missing_handling",), ("analysis_result", "lineage"),
              value_bearing=True, eligible=True),
        _spec("S14_assumptions", "假设检验面（assumptions／assumption_*／fit_indices／normality_checks）",
              "R2_workspace_upload", "src/analysis/assumptions.py::check_normality",
              ("C5_missing_handling", "C6_quality_screening"), ("analysis_result", "lineage"),
              value_bearing=True, eligible=True),
        _spec("S15_charts_payload", "图表数据负载（charts_data／figures／forest_fig）",
              "R6_runtime_only", "src/analysis/runner.py::run_analysis",
              ("C0_none_declared",), ("lineage",),
              value_bearing=False, eligible=False,
              note="运行期渲染负载：不对应任何原始记录，不得当作「可回溯」的证据。"),
        _spec("S16_snapshot_id", "快照标识（snapshot_id）",
              "R6_runtime_only", "src/analysis/runner.py::_generate_snapshot_id",
              ("C0_none_declared",), ("lineage",),
              value_bearing=False, eligible=False,
              note="它是 DataFrame 行哈希的前 12 位＋参数哈希＋秒级时间戳，"
                   "**不是文件路径**：凭它无法定位到用户上传的原件。"),
        _spec("S17_timestamp", "生成时间（created_at／timestamp）",
              "R6_runtime_only", "src/analysis/result_card.py::__post_init__",
              ("C0_none_declared",), ("lineage",),
              value_bearing=False, eligible=False),
        _spec("S18_card_provenance", "结果卡来源标签（provenance）",
              "R6_runtime_only", "src/analysis/result_card.py::build_card_from_output",
              ("C0_none_declared",), ("lineage",),
              value_bearing=False, eligible=False,
              note="现网只写 {method_id, generated_by} 两项，不含原始文件与清洗步骤；"
                   "字段名叫 provenance 不等于它就是血缘。"),
        _spec("S19_privacy_redaction", "脱敏报告面（privacy_redaction／redaction 报告）",
              "R1_archive_copy", "src/utils/guardrails.py::redact_dataframe_for_storage",
              ("C7_privacy_redaction",), ("lineage",),
              value_bearing=False, eligible=True,
              note="归档件与原件的差就在这里；血缘必须显式指向归档副本而非原件。"),
        _spec("S20_routing_advice", "方法切换建议（routing／suggested_test／post_hoc_power）",
              "R2_workspace_upload", "src/analysis/assumption_router.py::check_route",
              ("C5_missing_handling",), ("analysis_result", "lineage"),
              value_bearing=False, eligible=False,
              note="runner 注释自述「仅建议，不切换」，故不得写成结论。"),
        _spec("S21_recommended_size", "建议样本量（RouteDecision／SchemaReport 的 sample_size 语义）",
              "R2_workspace_upload", "src/analysis/post_hoc_power.py::estimate_post_hoc",
              ("C5_missing_handling",), ("analysis_result", "lineage"),
              value_bearing=True, eligible=False),
        _spec("S22_litfeed_record", "文献库记录字段（feed 条目的元数据）",
              "R5_registry", "src/literature_feed/storage/feed_store.py::ArticleRow",
              ("C0_none_declared",), ("lineage",),
              value_bearing=False, eligible=True,
              note="gitignore 域（data/literature_feed 不变量 181 件／21,059,126 B），"
                   "只读；任何血缘登记都不写它。"),
        _spec("S23_source_file_locator", "原始文件名定位符（file_name／原件名字段）",
              "R2_workspace_upload", "src/utils/archive_manager.py::archive_analysis",
              ("C7_privacy_redaction",), ("lineage",),
              value_bearing=False, eligible=True,
              note="这是全仓**唯一**把「用户上传的原件叫什么」落进结果侧的地方；"
                   "它只记名字，不记内容哈希，因此不足以单独完成回溯（见登记表的缺口一节）。"),
    )
}


# ---------------------------------------------------------------------------
# 字段名 → spec 的判定规则（顺序敏感：先具体后宽泛）
# ---------------------------------------------------------------------------

#: (字段名精确匹配表) ∪ (子串规则)。显式表优先，避免语义碰撞。
EXACT_FIELD_SPEC: dict[str, str] = {
    "alpha": "S1_reliability_point",
    "omega_value": "S1_reliability_point",
    "cr_per_factor": "S1_reliability_point",
    "icc_value": "S1_reliability_point",
    "kappa_value": "S1_reliability_point",
    "split_half_r": "S1_reliability_point",
    "test_retest_r": "S1_reliability_point",
    "main_value": "S1_reliability_point",
    "ci_lower": "S2_ci_endpoint",
    "ci_upper": "S2_ci_endpoint",
    "bootstrap_ci": "S2_ci_endpoint",
    "rmsea_ci_lower": "S2_ci_endpoint",
    "rmsea_ci_upper": "S2_ci_endpoint",
    "p_value": "S3_p_value",
    "chi2_p": "S3_p_value",
    "bartlett_p": "S3_p_value",
    "q_p_value": "S3_p_value",
    "criterion_p": "S3_p_value",
    "known_groups_p": "S3_p_value",
    "box_m": "S4_test_statistic",
    "chi2": "S4_test_statistic",
    "chi_sq": "S4_test_statistic",
    "q_statistic": "S4_test_statistic",
    "f_stat": "S4_test_statistic",
    "f_p": "S3_p_value",
    "df": "S4_test_statistic",
    "chi2_df": "S4_test_statistic",
    "q_df": "S4_test_statistic",
    "bartlett_df": "S4_test_statistic",
    "statistic": "S4_test_statistic",
    "t_statistic": "S4_test_statistic",
    "mean_diff": "S7_descriptive_table",
    "z_value": "S4_test_statistic",
    "tau_squared": "S5_effect_size",
    "i_squared": "S5_effect_size",
    "pooled_effect": "S5_effect_size",
    "pooled_se": "S5_effect_size",
    "kmo": "S5_effect_size",
    "effect_size": "S5_effect_size",
    "effect_size_name": "S9_method_identity",
    "eta_squared": "S5_effect_size",
    "r_squared": "S5_effect_size",
    "adj_r_squared": "S5_effect_size",
    "pseudo_r2": "S5_effect_size",
    "design_effect": "S5_effect_size",
    "residual_var": "S5_effect_size",
    "random_effect_var": "S5_effect_size",
    "avg_cluster_size": "S6_sample_size",
    "n_cases": "S6_sample_size",
    "n_obs": "S6_sample_size",
    "n_items": "S6_sample_size",
    "n_total": "S6_sample_size",
    "n_complete": "S6_sample_size",
    "n_groups": "S6_sample_size",
    "n_events": "S6_sample_size",
    "n_factors": "S6_sample_size",
    "k": "S6_sample_size",
    "sample_size": "S6_sample_size",
    "schema_version": "S11_schema_version",
    "test_type": "S9_method_identity",
    "canonical_method_id": "S9_method_identity",
    "method_id": "S9_method_identity",
    "card_id": "S9_method_identity",
    "test_name_zh": "S9_method_identity",
    "method_name": "S9_method_identity",
    "method_zh": "S9_method_identity",
    "plan": "S10_plan_parameter",
    "parameters": "S10_plan_parameter",
    "params": "S10_plan_parameter",
    "confidence_level": "S10_plan_parameter",
    "formula": "S10_plan_parameter",
    "dependent_vars": "S10_plan_parameter",
    "independent_vars": "S10_plan_parameter",
    "covariates": "S10_plan_parameter",
    "missing_strategy": "S13_missing_meta",
    "missing_meta": "S13_missing_meta",
    "missing_pct": "S13_missing_meta",
    "missing_cols": "S13_missing_meta",
    "charts_data": "S15_charts_payload",
    "figures": "S15_charts_payload",
    "forest_fig": "S15_charts_payload",
    "snapshot_id": "S16_snapshot_id",
    "created_at": "S17_timestamp",
    "provenance": "S18_card_provenance",
    "routing": "S20_routing_advice",
    "post_hoc_power": "S21_recommended_size",
    "privacy_redaction": "S19_privacy_redaction",
    "assumptions": "S14_assumptions",
    "assumption_status": "S14_assumptions",
    "warnings": "S12_warning_face",
    "warning": "S12_warning_face",
    "errors": "S12_warning_face",
    "technical_notes": "S12_warning_face",
    "reasoning": "S12_warning_face",
    "descriptive": "S7_descriptive_table",
    "result": "S4_test_statistic",
    "variables": "S8_variable_column",
    "columns": "S8_variable_column",
    "file_name": "S23_source_file_locator",
    # ↓ 判据点名的报告字段：统一名表的规范名与载体键名在这里不一致，逐个补登记。
    "omega": "S1_reliability_point",
    "ci": "S2_ci_endpoint",
    "cfi": "S24_fit_index",
    "tli": "S24_fit_index",
    "rmsea": "S24_fit_index",
    "srmr": "S24_fit_index",
    "aic": "S24_fit_index",
    "bic": "S24_fit_index",
    "log_likelihood": "S24_fit_index",
    "chi2": "S24_fit_index",
    "fit_acceptable": "S26_model_spec",
    "fit_good": "S26_model_spec",
    "is_fallback": "S26_model_spec",
    "fallback_note": "S12_warning_face",
    "loadings": "S25_derived_table",
    "communalities": "S25_derived_table",
    "eigenvalues": "S25_derived_table",
    "variance_explained": "S25_derived_table",
    "factor_cov": "S25_derived_table",
    "item_stats": "S25_derived_table",
    "group_stats": "S25_derived_table",
    "ave_per_factor": "S25_derived_table",
    "cr_per_factor": "S1_reliability_point",
    "study_effects": "S25_derived_table",
    "study_cis": "S2_ci_endpoint",
    "study_labels": "S8_variable_column",
    "study_weights": "S25_derived_table",
    "fixed_effects": "S25_derived_table",
    "random_effects": "S25_derived_table",
    "path_coefficients": "S25_derived_table",
    "indirect_effects": "S25_derived_table",
    "total_effects": "S25_derived_table",
    "simple_slopes": "S25_derived_table",
    "odds_ratios": "S25_derived_table",
    "post_hoc": "S25_derived_table",
    "univariate_tests": "S25_derived_table",
    "multivariate_tests": "S25_derived_table",
    "block_tests": "S25_derived_table",
    "diagnostics": "S14_assumptions",
    "classification_table": "S7_descriptive_table",
    "converged": "S26_model_spec",
    "is_mixedlm": "S26_model_spec",
    "is_welch": "S26_model_spec",
    "estimator": "S26_model_spec",
    "rotation": "S26_model_spec",
    "model": "S26_model_spec",
    "model_type": "S26_model_spec",
    "model_syntax": "S10_plan_parameter",
    "effect_type": "S9_method_identity",
    "kappa_method": "S9_method_identity",
    "icc_type": "S9_method_identity",
    "passed": "S26_model_spec",
    "sig_mask": "S25_derived_table",
    "zero_var_cols": "S13_missing_meta",
    "constant_cols": "S13_missing_meta",
    "outlier_cols": "S13_missing_meta",
    "icc": "S5_effect_size",
    "criterion_r": "S5_effect_size",
    "confidence": "S10_plan_parameter",
    "sample_relation": "S10_plan_parameter",
    "purpose": "S10_plan_parameter",
    "dv_type": "S10_plan_parameter",
    "iv_type": "S10_plan_parameter",
    "dv_count": "S6_sample_size",
    "n_covariates": "S6_sample_size",
    "time_points": "S10_plan_parameter",
    "has_covariate": "S10_plan_parameter",
    "assumptions_met": "S14_assumptions",
}

# 第二批：把"结果体里真的会出现在报告上"的三类字段族补进来
# （拟合指数／派生表与逐研究数组／模型与判定标记）。补一批少一批不可追溯面，
# 剩余的仍按"不可追溯 ⇒ 阻断结论"处理，不为了让覆盖率好看而兜一个"通用规范"。
FIELD_SPECS.update({
    s.spec_id: s for s in (
        _spec("S24_fit_index", "拟合指数与信息量（cfi／tli／rmsea／srmr／aic／bic／log_likelihood）",
              "R2_workspace_upload", "src/analysis/cfa.py::CFAResult",
              ("C5_missing_handling",), ("analysis_result", "lineage"),
              value_bearing=True, eligible=True,
              note="与 S14 的差别：S14 是「过／没过」的判定面，S24 是指数值本身。"),
        _spec("S25_derived_table", "派生表与逐案例／逐研究数组（loadings／group_stats／item_stats／study_effects）",
              "R2_workspace_upload", "src/analysis/regression.py::multiple_regression",
              ("C5_missing_handling",), ("analysis_result", "lineage"),
              value_bearing=True, eligible=True,
              note="表体的每个单元都是原始行的函数；血缘登记到「表由哪个处理器产出」这一层，"
                   "单元级回溯靠 params.json 的 columns 与行定位符。"),
        _spec("S26_model_spec", "模型与判定标记（converged／is_welch／estimator／rotation／model_type／passed）",
              "R7_plan_input", "src/analysis/sem.py::structural_equation_model",
              ("C0_none_declared",), ("analysis_result", "lineage"),
              value_bearing=False, eligible=True,
              note="标记位决定「这个数是怎么算出来的」，属结构性字段，本身不是统计量。"),
    )
})

#: 后缀兜底（在精确表之后生效）。
SUFFIX_RULES: tuple[tuple[str, str], ...] = (
    ("_ci", "S2_ci_endpoint"),
    ("_ci_lower", "S2_ci_endpoint"),
    ("_ci_upper", "S2_ci_endpoint"),
    ("_p", "S3_p_value"),
    ("_effect_size", "S5_effect_size"),
    ("_warning", "S12_warning_face"),
    ("_table", "S7_descriptive_table"),
    ("_matrix", "S7_descriptive_table"),
    ("_coef", "S7_descriptive_table"),
    ("_check", "S14_assumptions"),
    ("_checks", "S14_assumptions"),
    ("_pass", "S26_model_spec"),
    ("_effect", "S5_effect_size"),
    ("_warning", "S12_warning_face"),
)

#: 前缀兜底（`n_items`／`n_groups`／`n_obs` 这类计数字段）。
PREFIX_RULES: tuple[tuple[str, str], ...] = (
    ("n_", "S6_sample_size"),
)


@dataclass
class Coverage:
    """一批字段名的覆盖情况。"""

    traced: dict[str, str] = dc_field(default_factory=dict)      # field -> spec_id
    untraceable: list[str] = dc_field(default_factory=list)      # 登记表里没有的字段名

    @property
    def scanned(self) -> int:
        return len(self.traced) + len(self.untraceable)


@dataclass
class Gate:
    """结论门禁读数：哪些字段可以支撑结论、哪些必须阻断。"""

    blocked: bool
    supporting: list[str] = dc_field(default_factory=list)   # 可回溯且可作结论
    ineligible: list[str] = dc_field(default_factory=list)   # 有登记但不得作结论
    untraceable: list[str] = dc_field(default_factory=list)  # 登记不到

    def report_lines(self) -> list[str]:
        out = [f"血缘门禁：{'🚫 阻断' if self.blocked else '✅ 放行'}"
               f"（支撑 {len(self.supporting)}／不作结论 {len(self.ineligible)}"
               f"／不可追溯 {len(self.untraceable)}）"]
        for f in self.untraceable:
            out.append(f"  🚫 不可追溯：{f} —— 登记表内无该字段的溯源规范，不得据其出结论")
        for f in self.ineligible:
            out.append(f"  ⚠ 不得作结论：{f} —— 有登记，但载体不是原始记录或语义是建议")
        return out


def spec_for(field_name: str) -> LineageSpec | None:
    """按字段名取溯源规范；登记不到返回 ``None``（不猜、不兜一个"通用"规范）。"""

    spec_id = EXACT_FIELD_SPEC.get(field_name)
    if spec_id is None:
        for suffix, sid in SUFFIX_RULES:
            if field_name.endswith(suffix):
                spec_id = sid
                break
    if spec_id is None:
        for prefix, sid in PREFIX_RULES:
            if field_name.startswith(prefix):
                spec_id = sid
                break
    if spec_id is None:
        return None
    return FIELD_SPECS.get(spec_id)


def classify_fields(names: Iterable[str]) -> Coverage:
    coverage = Coverage()
    for name in names:
        spec = spec_for(name)
        if spec is None:
            coverage.untraceable.append(name)
        else:
            coverage.traced[name] = spec.spec_id
    return coverage


def conclusion_gate(names: Iterable[str]) -> Gate:
    """验收判据"发现不可追溯字段要阻断结论"的实现。"""

    gate = Gate(blocked=False)
    for name in names:
        spec = spec_for(name)
        if spec is None:
            gate.untraceable.append(name)
        elif not spec.conclusion_eligible:
            gate.ineligible.append(name)
        else:
            gate.supporting.append(name)
    gate.blocked = bool(gate.untraceable) or bool(gate.ineligible)
    return gate


def sample_fields(names: Sequence[str], *, seed: int, k: int) -> list[str]:
    """固定种子的随机抽样（判据要"随机抽样可回溯"，抽样必须可复算）。"""

    k = max(0, min(k, len(names)))
    return random.Random(seed).sample(list(names), k)


# ---------------------------------------------------------------------------
# 回溯探针：字段 → 原始记录（只读）
# ---------------------------------------------------------------------------

@dataclass
class TraceProbe:
    """一次"从结果回溯到原始记录"的读数。"""

    field: str
    spec_id: str | None
    chain: list[str]
    reached_raw_record: bool
    detail: str
    raw_row: Mapping[str, str] | None = None


def trace_archive_dir(archive_dir: Path | str, field: str = "alpha",
                      *, row: int = 0) -> TraceProbe:
    """从一个归档目录回溯：params.json（登记了 file_name／columns／行数列数）→ data.csv 的一行。

    只读；不解析任何统计量。``row`` 只是"原始记录在第几行"的定位，默认第一行。
    """

    spec = spec_for(field)
    d = Path(archive_dir)
    params_path = d / "params.json"
    data_path = d / "data.csv"
    if spec is None:
        return TraceProbe(field, None, [], False, "登记表内无该字段的溯源规范")
    src = RAW_SOURCES[spec.raw_source]
    if not src.raw_backable:
        return TraceProbe(field, spec.spec_id, spec.chain(), False,
                          f"登记的载体是 {src.source_id}（{src.description}）——"
                          "不对应任何一条原始记录，本探针不判通过")
    if not params_path.is_file() or not data_path.is_file():
        return TraceProbe(field, spec.spec_id, spec.chain(), False,
                          f"{d} 缺 params.json 或 data.csv，回溯断链")
    meta = json.loads(params_path.read_text(encoding="utf-8"))
    with data_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows = list(reader)
    if not rows or row >= len(rows):
        return TraceProbe(field, spec.spec_id, spec.chain(), False,
                          f"data.csv 无第 {row} 行（共 {len(rows)} 行）")
    detail = (f"结果字段 {field} ← 归档 {d.name} ← 原件名 {meta.get('file_name')!r}"
              f"（登记列 {len(header)} 个／原始行数 {meta.get('n_rows')}）← 第 {row} 行原始记录")
    return TraceProbe(field, spec.spec_id, spec.chain(), True, detail, dict(rows[row]))


def trace_project_dir(project_dir: Path | str, field: str = "alpha",
                      *, data_file: str = "data.csv", row: int = 0) -> TraceProbe:
    """从项目目录（演示数据集这类随仓件）回溯到原始记录行。"""

    spec = spec_for(field)
    d = Path(project_dir)
    data_path = d / data_file
    if spec is None:
        return TraceProbe(field, None, [], False, "登记表内无该字段的溯源规范")
    src = RAW_SOURCES[spec.raw_source]
    if not src.raw_backable:
        return TraceProbe(field, spec.spec_id, spec.chain(), False,
                          f"登记的载体是 {src.source_id}（{src.description}）——"
                          "不对应任何一条原始记录，本探针不判通过")
    if not data_path.is_file():
        return TraceProbe(field, spec.spec_id, spec.chain(), False,
                          f"{data_path} 不存在，回溯断链")
    with data_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows = list(reader)
    if not rows or row >= len(rows):
        return TraceProbe(field, spec.spec_id, spec.chain(), False,
                          f"{data_path.name} 无第 {row} 行（共 {len(rows)} 行）")
    detail = (f"结果字段 {field} ← {data_path}（表头 {len(header)} 列 × {len(rows)} 行）"
              f"← 第 {row} 行原始记录")
    return TraceProbe(field, spec.spec_id, spec.chain(), True, detail, dict(rows[row]))


__all__ = [
    "LINEAGE_VERSION",
    "VERSION_ANCHORS",
    "RawSource",
    "RAW_SOURCES",
    "CleaningRule",
    "CLEANING_RULES",
    "LineageSpec",
    "FIELD_SPECS",
    "EXACT_FIELD_SPEC",
    "SUFFIX_RULES",
    "PREFIX_RULES",
    "Coverage",
    "Gate",
    "TraceProbe",
    "spec_for",
    "classify_fields",
    "conclusion_gate",
    "sample_fields",
    "trace_archive_dir",
    "trace_project_dir",
]
