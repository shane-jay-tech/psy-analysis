# -*- coding: utf-8 -*-
"""s927-72：A′ 哨兵的**调用方识别**用例（design_engine 那条链）。

锚点：待人工台账 215①（`docs/insights/drain-20260923-pending-human.md`）——
「`s924-04` 落地 A′ 后留一条真传导缺陷：`design_engine.py:159` 在 `solved=False` 时仍把
`n_subjects=0` 往下送 ⇒ medium 效应的设计稿会写"每组 0 人"……engine 侧必须读 `solved`
改为不出数」。

本文件只钉**出口形态**：三个求解状态（正常解／无解／欠解）下，引擎的报告、程序随机化、
预算三处出口各自给出什么。**不重算任何统计量**，也不断言效应量／p 值／样本量的数值判定
——数值一律与「同一个真实求解器返回的 PowerResult 字段」互相对照（同源比较，不另起尺子）。

真实求解器给出的哨兵在本文件里只被**读取**，不构造、不改动：
- d=0.2 独立 t ⇒ `solved=True`（正常解）
- d=0.8 独立 t ⇒ `solved=False`，原因「迭代进入 NaN 发散区」（无解：求解器不可解）
- d=0.05 独立 t ⇒ `solved=False`，原因「超出搜索区间上界 4000（欠配）」（欠解：区间内无变号点）
引擎的 `effect_size_expected` 字符串表只能取到 0.2/0.5/0.8（见 `design_engine.py:147`），
「欠解」这一态在字符串 API 上不可达 ⇒ 该例用 monkeypatch 把**真实** PowerResult 注进
`_auto_power_analysis` 的返回位（注的是真哨兵，不是手搓假对象），以覆盖调用方的第三条分支。
"""

import pytest

from src.experiment_design.design_engine import ExperimentDesignEngine
from src.experiment_design.power_analysis import calculate_sample_size

#: 与 tests/test_experiment_design_ui_detail_branch.py:70-79 同族的离线夹具参数
#: （被试间单因素模板 ⇒ `_auto_power_analysis` 走 t_test 分支）
KW = dict(
    topic="考察不同情绪状态对大学生认知控制能力的影响",
    target_population="在校大学生",
    design_type_hint="被试间",
    ivs=["情绪状态"],
    dvs=["反应时"],
    n_subjects_hint=0,
    power=0.80,
    include_budget=True,
)

REFUSAL_MARK = "未给出"


def _build(effect_size_expected="medium"):
    eng = ExperimentDesignEngine()
    design = eng.design_experiment(**{**KW, "effect_size_expected": effect_size_expected})
    return eng, design, eng.format_design_report(design)


# ═══════════════ ①正常解：d=0.2，求解器给数 ⇒ 引擎照旧出数 ═══════════════

def test_normal_solve_passes_numbers_through_unchanged():
    """求解成功 ⇒ 调用方取 required_n/required_per_group，三处出口与哨兵前完全一致。"""
    eng, d, report = _build("small")
    pr = d.power_result

    assert pr.solved is True, "夹具漂移：d=0.2 的独立 t 本应可解，请先复核求解器再改断言"
    assert d.power_solved is True
    assert d.power_failure_reason == ""
    # 同源比较：引擎字段 == 求解器字段（不写死任何统计数值）
    assert d.n_subjects == pr.required_n
    assert d.n_per_group == pr.required_per_group
    assert d.n_groups == pr.n_groups

    assert f"**计划样本量：** N = {d.n_subjects}" in report
    assert f"**分组：** 共{d.n_groups}组，每组{d.n_per_group}人" in report
    assert REFUSAL_MARK not in report, "可解态却出现拒答文案 ⇒ :159 分支判反了"
    assert f"每组{d.n_per_group}人" in d.procedure.randomization["description"]
    assert "| 被试费 |" in d.budget_estimate


# ═══════════════ ②无解：d=0.8 NaN 发散 ⇒ 三处出口全部拒答 ═══════════════

def test_unsolved_nan_divergence_engine_refuses_to_emit_numbers():
    """求解器返回未解哨兵 ⇒ 引擎不得把 required_n=0 当成计划量往下送（台账 215①）。"""
    eng, d, report = _build("large")
    pr = d.power_result

    assert pr.solved is False, "夹具漂移：d=0.8 走 A′ 未解分支，若已可解请连带复核本文件三例"
    assert "NaN" in pr.failure_reason
    assert d.power_solved is False
    assert d.power_failure_reason == pr.failure_reason

    # 报告出口：既不能出现「N = 0」也不能出现「每组0人」
    assert "N = 0" not in report, "拒答态仍输出 N = 0 ——假样本量泄漏"
    assert "每组0人" not in report, "拒答态仍输出分组人数 ——假样本量泄漏"
    assert "**计划样本量：**" in report and REFUSAL_MARK in report
    assert d.power_failure_reason in report, "拒答必须可见：诊断文本要随出口透出"

    # 程序出口：随机化方案不再由 0 充数，但方案本体（method）仍在场
    rand = d.procedure.randomization
    assert "每组0人" not in rand["description"], "随机化文案仍写每组 0 人"
    assert rand["description"] and "未给出" in rand["description"]
    assert rand["assignments"] == []
    assert rand["method"], "只应替换数值文案，method 等非数值字段不得被清空"

    # 预算出口：费用表整段不出（人数不可引用）
    assert "| 被试费 |" not in d.budget_estimate
    assert "无法估算" in d.budget_estimate

    # 引擎日志不得再宣称「效力分析完成」
    assert not any("效力分析完成" in line for line in eng.logs), (
        f"哨兵态仍记录『效力分析完成』：{[l for l in eng.logs if '效力' in l]}"
    )


# ═══════════════ ③欠解：d=0.05 目标超出搜索区间上界 ⇒ 同口径拒答 ═══════════════

def test_underpowered_unsolved_engine_refuses_to_emit_numbers(monkeypatch):
    """「区间内无变号点（欠配）」这一态与②同判据：调用方一律读 solved，不出数。

    d=0.05 不在引擎的 effect_size_expected 字符串表里（`:147` 只有 small/medium/large），
    故把真实求解器返回的哨兵注进 `_auto_power_analysis` 的返回位——
    注入的是 `calculate_sample_size` 的真产物，不是手搓对象。
    """
    real = calculate_sample_size("t_test", effect_size=0.05, power=0.80, alpha=0.05)
    assert real.solved is False and "超出搜索区间上界" in real.failure_reason

    monkeypatch.setattr(
        "src.experiment_design.design_engine._auto_power_analysis",
        lambda template, effect_size, power, alpha: real,
    )

    eng, d, report = _build("medium")

    assert d.power_solved is False
    assert d.power_failure_reason == real.failure_reason
    assert d.n_subjects == 0 and d.n_per_group == 0
    assert "N = 0" not in report and "每组0人" not in report
    assert "未给出" in report
    # n_groups 是模板决定的结构量，不随求解失败而消失 ⇒ 仍为求解器给的 2
    assert d.n_groups == real.n_groups == 2


# ═══════════════ ④回归对照：用户指定样本量路径不受本次改动影响 ═══════════════

def test_user_specified_n_subjects_path_still_emits_numbers():
    """:150-155（n_subjects_hint>0，power_result=None）必须继续正常出数。

    这一例是「零版式变化」的对照面：本次只给哨兵态加了拒答分支，
    用户显式给样本量的路径一个字都没改。
    """
    eng = ExperimentDesignEngine()
    d = eng.design_experiment(**{**KW, "n_subjects_hint": 60, "n_groups_hint": 2})
    report = eng.format_design_report(d)

    assert d.power_result is None, "引擎行为已变（:154 不再置 None），本对照组需复核"
    assert d.power_solved is True, "用户指定样本量不该被判成未求解"
    assert d.n_subjects == 60 and d.n_per_group == 30
    assert f"**计划样本量：** N = {d.n_subjects}" in report
    assert "| 被试费 |" in d.budget_estimate
    assert REFUSAL_MARK not in report
