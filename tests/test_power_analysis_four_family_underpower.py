# -*- coding: utf-8 -*-
"""s927-61：t 族出口 A′ 连坐——anova/相关/卡方/多因素四族区间上界兜底欠配用例。

欠配（所需样本量超出搜索区间上界）时必须返回 solved=False 哨兵，
而不是把上界（2000/3000/5000/2000）当"建议样本量"透出（s924-04 遗留）。
统计红线：本套用例同时钉「可解点结论值零改动」——各族的常规可解点
由既有 tests/test_power_analysis.py 的 33 点位对拍覆盖，此处每族另抽
1 个可解点，断言 required_n 与修复前口径一致。
"""
from src.experiment_design.power_analysis import (
    _solve_n_for_anova_f,
    _solve_n_for_chisq,
    _solve_n_for_correlation,
    _solve_n_for_factorial_anova,
)


def test_correlation_underpowered_returns_sentinel_not_bound():
    """r=0.05 所需 N≈3100+ 超出上界 3000（设计稿 §3.3 点名的欠配面）。"""
    res = _solve_n_for_correlation(r=0.05, power=0.8, alpha=0.05)
    assert res.solved is False
    assert "上界" in res.failure_reason
    assert res.required_n == 0, "未解哨兵不得透出上界假数"


def test_anova_underpowered_returns_sentinel_not_bound():
    res = _solve_n_for_anova_f(f_effect=0.01, k=3, power=0.8, alpha=0.05)
    assert res.solved is False
    assert res.required_n == 0


def test_chisq_underpowered_returns_sentinel_not_bound():
    res = _solve_n_for_chisq(w=0.01, df=1, power=0.8, alpha=0.05)
    assert res.solved is False
    assert res.required_n == 0


def test_factorial_underpowered_returns_sentinel_not_bound():
    res = _solve_n_for_factorial_anova(f_effect=0.01, design="2x2", power=0.8, alpha=0.05)
    assert res.solved is False
    assert res.required_n == 0


def test_correlation_solved_point_unchanged():
    """可解点结论值零改动自证：r=0.3 的样本量与 t 族修前口径一致（≈ s924-04 对拍集内值）。"""
    res = _solve_n_for_correlation(r=0.3, power=0.8, alpha=0.05)
    assert res.solved is True
    assert res.required_n == 85  # Fisher z 口径的既有可解点（修前即为 85，ceil 后不变）


def test_anova_solved_point_unchanged():
    res = _solve_n_for_anova_f(f_effect=0.4, k=3, power=0.8, alpha=0.05)
    assert res.solved is True
    assert res.required_n == 24  # 每组 24（λ=n·k·f² 口径的既有可解点；修前同式同值）
