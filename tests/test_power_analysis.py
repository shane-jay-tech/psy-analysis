# -*- coding: utf-8 -*-
"""src/experiment_design/power_analysis.py 的逆解 N 求解器钉桩（s922-12）。

覆盖任务书点名的四个锚点（2026-09-22 复核，行号全部命中，零漂移）：
:57 `_solve_n_for_t_test`、:308 `calculate_sample_size`、:352 `format_power_report`、
:393 `quick_sample_size`；五个逆解器分别是
`_solve_n_for_t_test`:57 / `_solve_n_for_anova_f`:136 / `_solve_n_for_correlation`:186 /
`_solve_n_for_chisq`:226 / `_solve_n_for_factorial_anova`:257。
补测前 tests/ 对这五个符号 + `format_power_report` + `quick_sample_size` **符号级 0 命中**，
`calculate_sample_size` 只在 `tests/test_ui.py` 出现（实测口径见 result 的「证据」）。

钉桩手法=**正代-回代闭合**：让求解器求出 N，再用测试侧独立重写的教科书功效函数把 N 代回去，
断言①回代值与 `PowerResult.actual_power` 逐位闭合（容差 `TOL_CLOSURE`）②回代值 ≥ 目标效力
③（能成立处）N−1 不达标 = 最小性。测试侧重写的是 Cohen(1988)/G*Power 的标准式子
（非中心 t/F/χ² 与 Fisher-z），不是把实现里的闭包抄一遍——实现改 ncp 或 df 的任一处都会打断闭合。

红线自约（s922-12 建档时零生产码改动；s924-04 翻正亦不动任何可解点公式）：
本文件登记并钉桩求解器行为，不评判任何样本量结论，也不改判据。

⚠ 补测中发现一处**数值缺陷（s922-12 只读登记）**：`_solve_n_for_t_test` 在若干**标准效应量**下
曾返回搜索区间上界（独立/配对两族），而不是真解。根因实测：scipy 的 `nct.cdf`
在「大 df + 大非中心参数」处返回 **NaN** ⇒ `brentq` 抛 `ValueError` ⇒ 旧 `:84-85` 与 `:117-118` 的
`except ValueError: n = ceil(n_hi)` 兜底把上界当答案返回，且 `actual_power` 本身也可能是 NaN。
受污染点位（本机实测，全部命中兜底；「真值」= 本模块自己的功效式下首个达标 N，逐点扫描得出）：
独立 d=0.3/0.5/0.8 → 上界（真值 N=351/128/52），配对 d=0.3/0.4/0.5 → 上界（真值 n=90/52/34）；
未污染：独立 d=0.1/0.2/0.4、配对 d=0.1/0.15/0.2。
兜底不随效应量单调出现，因为命中与否取决于 `brentq` 的迭代路径是否走进 NaN 区。

✅ **s924-04 已按设计稿 §4 出口 A′ 落地 t 族**（docs/insights/psy-power-solver-redesign-20260923.md）：
求解失败不再返回区间上界，而是返回 `PowerResult(solved=False, failure_reason=…)` 哨兵；
报告遇未解走「无法给出样本量建议」分支；`quick_sample_size` 键集 +1 键（`solved`）。
原「currently_returns_the_bracket_ceiling / leak_a_nan / inherits_the_ceiling」三组现状桩
**按第 5 节清单翻正为哨兵断言**（当时红就是提醒，今天已翻正）。
**未随单修**：anova/相关/卡方/多因素四族仍保留区间上界兜底（设计稿 §3.3 认定同雷，
本波范围只有 t 族）；独立 t 最小性 D3（`:131` 桩）与坏 design 串（`:225` 桩）不动。
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.stats import ncf, ncx2, nct, norm

from src.experiment_design.power_analysis import (
    PowerResult,
    _solve_n_for_anova_f,
    _solve_n_for_chisq,
    _solve_n_for_correlation,
    _solve_n_for_factorial_anova,
    _solve_n_for_t_test,
    calculate_sample_size,
    format_power_report,
    quick_sample_size,
)

TARGET = 0.80
ALPHA = 0.05
TOL_CLOSURE = 1e-9        # 回代功效 vs 求解器自报 actual_power 的闭合容差


# ─────────────────── 测试侧独立重写的功效式（教科书口径） ───────────────────
def power_independent_t(total_n: float, d: float, alpha: float = ALPHA, ratio: float = 1.0) -> float:
    """两组各自 n1/n2 的非中心 t 双侧效力；ncp = d * sqrt(n1*n2/(n1+n2))。"""
    n1, n2 = int(total_n // (1 + ratio)), int(total_n - total_n // (1 + ratio))
    n1, n2 = max(n1, 2), max(n2, 2)
    df = n1 + n2 - 2
    ncp = d * np.sqrt(n1 * n2 / (n1 + n2))
    t_crit = nct.ppf(1 - alpha / 2, df, 0)
    return float((1 - nct.cdf(t_crit, df, ncp)) + nct.cdf(-t_crit, df, ncp))


def power_paired_t(n: float, d: float, alpha: float = ALPHA) -> float:
    df = max(n, 2) - 1
    ncp = d * np.sqrt(max(n, 2))
    t_crit = nct.ppf(1 - alpha / 2, df, 0)
    return float((1 - nct.cdf(t_crit, df, ncp)) + nct.cdf(-t_crit, df, ncp))


def power_anova(n: float, f: float, k: int, alpha: float = ALPHA,
                repeated: bool = False, rho: float = 0.5) -> float:
    df1 = k - 1
    df2 = (n - 1) * (k - 1) if repeated else n - k
    ncp = n * (k / (1 - rho) if repeated else k) * f ** 2
    f_crit = ncf.ppf(1 - alpha, df1, df2, 0)
    return float(1 - ncf.cdf(f_crit, df1, df2, ncp))


def power_correlation(n: float, r: float, alpha: float = ALPHA) -> float:
    zr = 0.5 * np.log((1 + r) / (1 - r))
    se = 1.0 / np.sqrt(n - 3)
    z_crit = norm.ppf(1 - alpha / 2)
    return float((1 - norm.cdf(z_crit, loc=zr / se, scale=1.0)) + norm.cdf(-z_crit, loc=zr / se, scale=1.0))


def power_chisq(n: float, w: float, dfree: int, alpha: float = ALPHA) -> float:
    ncp = n * w ** 2
    chi_crit = ncx2.ppf(1 - alpha, dfree, 0)
    return float(1 - ncx2.cdf(chi_crit, dfree, ncp))


def power_factorial(n_per: float, f: float, design: str, alpha: float = ALPHA) -> float:
    factors = [int(x) for x in design.split("x")]
    k = int(np.prod(factors))
    df1 = max(1, min(int(np.prod([x - 1 for x in factors])), k - 1))
    df2 = n_per * k - k
    ncp = n_per * k * f ** 2
    f_crit = ncf.ppf(1 - alpha, df1, df2, 0)
    return float(1 - ncf.cdf(f_crit, df1, df2, ncp))


def assert_round_trip(result: PowerResult, power_at, n_key: str = "required_n") -> tuple[int, float]:
    """闭合三断言：回代值可算、与自报 actual_power 逐位吻合、且不低于目标效力。"""
    n = getattr(result, n_key)
    recomputed = power_at(n)
    assert not math.isnan(recomputed), f"回代功效 NaN（n={n}）——求解器给出的 N 不可验算"
    assert abs(recomputed - float(result.actual_power)) <= TOL_CLOSURE, (
        f"正代-回代不闭合：回代={recomputed!r} 自报={result.actual_power!r} N={n}")
    assert recomputed >= TARGET - 1e-12, f"回代效力 {recomputed} 未达目标 {TARGET}（N={n}）"
    return n, recomputed


# ═════════════════ 一、五个逆解器的闭合钉桩（未被污染区间） ═════════════════
def test_solve_n_for_t_test_independent_closes_at_d_020():
    """独立样本 t：d=0.2 ⇒ 每侧 394 人、总 N=788（教科书 394/组），回代闭合。"""
    r = _solve_n_for_t_test(0.20, TARGET, ALPHA, paired=False)
    n, _ = assert_round_trip(r, lambda n: power_independent_t(n, 0.20))

    assert (r.test_type, r.n_groups) == ("independent_t", 2)
    assert n == 788 and r.required_per_group == 394
    assert r.df == n - 2
    assert r.effect_size_label == "小" and r.effect_size_name == "Cohen's d"
    assert r.note == "独立组设计，两组分别394人和394人，共788人"


def test_solve_n_for_t_test_independent_is_not_minimal_under_n_minus_one_currently():
    """现状钉桩：独立 t 的 `power_at_total`（:101-103）用 int() 截断分组 ⇒ **少一个人也可能达标**，
    所以这一族的「最小 N」只能用 `brentq` 的连续根 + ceil 理解，不能用 N−1 判据反推。
    N=787 分成 393/394，其效力反而 ≥ N=788 的 394/394 门槛——本例把这条不单调钉在测试里，
    免得后来人误以为闭合测试已经隐含了最小性。"""
    r = _solve_n_for_t_test(0.20, TARGET, ALPHA, paired=False)

    assert power_independent_t(r.required_n - 1, 0.20) >= TARGET          # 注意方向：不是 <
    assert power_independent_t(r.required_n, 0.20) >= TARGET


@pytest.mark.parametrize("d", [0.10, 0.15, 0.20])
def test_solve_n_for_t_test_paired_closes_and_is_minimal(d):
    """配对 t：闭合 + 最小性（N−1 不达标）双条都成立。"""
    r = _solve_n_for_t_test(d, TARGET, ALPHA, paired=True)
    n, _ = assert_round_trip(r, lambda n: power_paired_t(n, d))

    assert power_paired_t(n - 1, d) < TARGET, f"d={d}：N−1 也达标，最小性断链"
    assert (r.test_type, r.n_groups, r.df) == ("paired_t", 1, n - 1)
    assert r.required_per_group == n                                     # 配对：被试数即组内数
    assert r.note == f"配对设计，需要{n}名被试"


@pytest.mark.parametrize("f_effect, k, expected_n", [
    (0.25, 3, 55),      # G*Power 同输入同值
    (0.10, 2, 395),
    (0.40, 4, 22),
])
def test_solve_n_for_anova_f_group_between_closes_and_is_minimal(f_effect, k, expected_n):
    """组间 ANOVA：`required_n` 在这一族是**每组人数**（总 N = n*k，只出现在 note 里）。"""
    r = _solve_n_for_anova_f(f_effect, k, TARGET, ALPHA, is_repeated=False)
    n, _ = assert_round_trip(r, lambda n: power_anova(n, f_effect, k))

    assert n == expected_n and r.required_per_group == n
    assert power_anova(n - 1, f_effect, k) < TARGET
    assert (r.test_type, r.n_groups, r.df) == ("oneway_anova", k, k - 1)
    assert r.effect_size_name == "Cohen's f"
    assert f"共N={n * k}" in r.note and "独立组" in r.note


@pytest.mark.parametrize("f_effect, k, rho, expected_n", [
    (0.25, 3, 0.5, 28),
    (0.10, 2, 0.5, 199),
    (0.40, 4, 0.7, 7),
])
def test_solve_n_for_anova_f_repeated_measures_closes(f_effect, k, rho, expected_n):
    """重复测量：ncp 多一个 /(1-ρ) 放大，df2=(n-1)(k-1)——两条都在闭合式里，改一处即红。"""
    r = _solve_n_for_anova_f(f_effect, k, TARGET, ALPHA, is_repeated=True, correlation=rho)
    n, _ = assert_round_trip(r, lambda n: power_anova(n, f_effect, k, repeated=True, rho=rho))

    assert n == expected_n and r.test_type == "rm_anova"
    assert power_anova(n - 1, f_effect, k, repeated=True, rho=rho) < TARGET
    assert f"ρ={rho}" in r.assumptions and "重复测量" in r.note


@pytest.mark.parametrize("r_effect, expected_n", [(0.10, 783), (0.30, 85), (0.50, 30)])
def test_solve_n_for_correlation_closes_and_is_minimal(r_effect, expected_n):
    """Pearson 相关：Fisher-z 变换 + n−3 自由度口径。"""
    r = _solve_n_for_correlation(r_effect, TARGET, ALPHA)
    n, _ = assert_round_trip(r, lambda n: power_correlation(n, r_effect))

    assert n == expected_n and power_correlation(n - 1, r_effect) < TARGET
    assert (r.test_type, r.n_groups, r.df) == ("correlation", 1, n - 2)
    assert r.effect_size_name == "r" and r.required_per_group == n


@pytest.mark.parametrize("w, dfree, expected_n", [(0.10, 1, 785), (0.30, 1, 88), (0.10, 4, 1194), (0.50, 2, 39)])
def test_solve_n_for_chisq_closes_and_is_minimal(w, dfree, expected_n):
    """卡方：λ = N·w²，df 由入参直传（是唯一「df 不进 ncp」的一族）。"""
    r = _solve_n_for_chisq(w, dfree, TARGET, ALPHA)
    n, _ = assert_round_trip(r, lambda n: power_chisq(n, w, dfree))

    assert n == expected_n and power_chisq(n - 1, w, dfree) < TARGET
    assert (r.test_type, r.df) == ("chisq", dfree)
    assert f"自由度df={dfree}" in r.assumptions


@pytest.mark.parametrize("design, k, df1, expected_per", [
    ("2x2", 4, 1, 32),
    ("2x3", 6, 2, 27),
    ("3x3", 9, 4, 22),
    ("2x2x2", 8, 1, 16),
])
def test_solve_n_for_factorial_anova_closes_and_is_minimal(design, k, df1, expected_per):
    """多因素：df1 = min(∏(f−1), k−1)，required_n 是**总** N = 每组 × k。"""
    r = _solve_n_for_factorial_anova(0.25, design, TARGET, ALPHA)
    per, _ = assert_round_trip(r, lambda n: power_factorial(n, 0.25, design), n_key="required_per_group")

    assert per == expected_per and r.required_n == per * k and r.n_groups == k
    assert power_factorial(per - 1, 0.25, design) < TARGET
    assert r.df == df1 and r.test_type == "factorial_anova"
    assert r.note == f"{design}设计，{k}个实验条件，每组{per}人，共{per * k}人"


def test_factorial_anova_bad_design_string_falls_back_to_2x2_currently():
    """现状钉桩：`design` 解析失败（:264-267）静默退成 [2,2]，不抛错——写错 "2*2"/"2x" 也照样出数。"""
    for bad in ("2*2", "", "abc", "2x"):
        assert _solve_n_for_factorial_anova(0.25, bad, TARGET, ALPHA).n_groups == 4


# ═════════ 二、A′ 哨兵（s924-04 翻正）：t 族不可解不再产上界假数 ═════════
@pytest.mark.parametrize("d", [0.30, 0.50, 0.60, 0.70, 0.80])
def test_solve_n_for_t_test_independent_unsolvable_returns_solved_false_sentinel(d):
    """翻正自 s922-12 的区间上界现状桩：本族求根失败 ⇒ `solved=False` 哨兵。
    数值字段一律清零/NaN（真值应为 N=351/128/90/67/52，扫描法属出口 B，本波未做）。"""
    r = _solve_n_for_t_test(d, TARGET, ALPHA, paired=False)

    assert r.solved is False
    assert r.failure_reason                                      # 失败必须可见、可归因
    assert r.required_n == 0 and r.required_per_group == 0       # 不再返回搜索上界假数
    assert r.n_groups == 2 and r.df == 0
    assert math.isnan(float(r.actual_power))
    assert "无法求解" in r.note


@pytest.mark.parametrize("d", [0.30, 0.40, 0.50, 0.60, 0.70, 0.80])
def test_solve_n_for_t_test_paired_unsolvable_returns_solved_false_sentinel(d):
    """翻正自配对族上界现状桩（真值 n=90/52/34/24/19/15，同上属 B 口径不在此断言）。"""
    r = _solve_n_for_t_test(d, TARGET, ALPHA, paired=True)

    assert r.solved is False
    assert r.failure_reason
    assert r.required_n == 0 and r.required_per_group == 0 and r.df == 0
    assert math.isnan(float(r.actual_power))
    assert "无法求解" in r.note


@pytest.mark.parametrize("paired, d", [(False, 0.80), (True, 0.30)])
def test_t_test_unsolved_report_cannot_leak_fake_green(paired, d):
    """翻正自 NaN 假绿现状桩：未解点报告走「无法给出样本量建议」分支，
    既不出现 `1-β ≈ nan`，也不出现「✅ 实际效力达到目标水平。」。
    可解点的反向不变量（含 ✅ ⇒ actual_power ≥ power−0.02）由
    `test_solvable_points_never_pair_check_with_low_power` 补钉。"""
    r = _solve_n_for_t_test(d, TARGET, ALPHA, paired=paired)
    report = format_power_report(r)

    assert r.solved is False
    assert "### 无法给出样本量建议" in report
    assert "✅ 实际效力达到目标水平。" not in report
    assert "1-β ≈" not in report                                  # 实际效力数值行整段不透出
    assert "所需总样本量" not in report                            # 假数整段不透出


def test_solvable_points_never_pair_check_with_low_power():
    """可解面不变量：返回解的点位上，报告出现 ✅ 必须与实际效力达标同时成立。"""
    for d in (0.10, 0.20, 0.40):
        r = _solve_n_for_t_test(d, TARGET, ALPHA, paired=False)
        assert r.solved is True
        if "✅" in format_power_report(r):
            assert r.actual_power >= r.power - 0.02


@pytest.mark.parametrize("paired, d", [(False, 0.03), (True, 0.02)])
def test_t_test_under_allocation_returns_solved_false_with_reason(paired, d):
    """**欠配**形态哨兵（设计稿 §3.2 反方向污染在 t 族的对应面）：
    真值样本量高于搜索区间上界 ⇒ solved=False 且 failure_reason 点名「欠配」，
    不再把上界当答案。判据②要求：欠配场景 solved 存在且为 False。"""
    r = _solve_n_for_t_test(d, TARGET, ALPHA, paired=paired)

    assert "solved" in r.__dict__ and r.solved is False
    assert "欠配" in r.failure_reason
    assert r.required_n == 0 and r.required_per_group == 0


# ═════════════════ 三、公开 API 的分发闭合（:308 calculate_sample_size） ═════════════════
@pytest.mark.parametrize("alias, expected_type", [
    ("t_test", "independent_t"), ("t检验", "independent_t"), ("independent_t", "independent_t"),
    ("paired_t", "paired_t"), ("配对t检验", "paired_t"),
    ("anova", "oneway_anova"), ("方差分析", "oneway_anova"),
    ("rm_anova", "rm_anova"), ("重复测量方差分析", "rm_anova"),
    ("factorial", "factorial_anova"), ("因素方差分析", "factorial_anova"), ("多因素", "factorial_anova"),
    ("correlation", "correlation"), ("相关", "correlation"), ("相关分析", "correlation"),
    ("chisq", "chisq"), ("卡方", "chisq"), ("卡方检验", "chisq"),
])
def test_calculate_sample_size_dispatches_every_alias_to_the_documented_solver(alias, expected_type):
    """18 个别名 ⇒ 5 个求解器的分发表钉桩（改别名、漏分支都会红），且与直调求解器逐字段同值。"""
    kwargs = {"effect_size": 0.20 if expected_type.endswith("t") else 0.30}
    got = calculate_sample_size(alias, **kwargs)
    assert got.test_type == expected_type
    direct = {
        "independent_t": lambda: _solve_n_for_t_test(0.20, TARGET, ALPHA, paired=False),
        "paired_t": lambda: _solve_n_for_t_test(0.20, TARGET, ALPHA, paired=True),
        "oneway_anova": lambda: _solve_n_for_anova_f(0.30, 2, TARGET, ALPHA),
        "rm_anova": lambda: _solve_n_for_anova_f(0.30, 2, TARGET, ALPHA, is_repeated=True),
        "factorial_anova": lambda: _solve_n_for_factorial_anova(0.30, "2x2", TARGET, ALPHA),
        "correlation": lambda: _solve_n_for_correlation(0.30, TARGET, ALPHA),
        "chisq": lambda: _solve_n_for_chisq(0.30, 1, TARGET, ALPHA),
    }[expected_type]()
    assert (got.required_n, got.required_per_group, got.n_groups, got.df) == \
           (direct.required_n, direct.required_per_group, direct.n_groups, direct.df)
    assert got.note == direct.note


def test_calculate_sample_size_rejects_unknown_test_type():
    with pytest.raises(ValueError, match="不支持的检验类型"):
        calculate_sample_size("wilcoxon")


# ═════════════════ 四、quick_sample_size / format_power_report 快照 ═════════════════
def test_quick_sample_size_keyset_and_mirrors_calculate_sample_size():
    """键集合契约 + 与 :308 的逐字段同源（quick 只是薄封装，不许自己另算一套）。
    s924-04 起键集 +1 键 `solved`（A′ 哨兵）；t_test@0.30 落在不可解区 ⇒ 走哨兵镜像分支。"""
    keys = {"test", "n_total", "n_per_group", "n_groups", "effect_label",
            "actual_power", "note", "solved"}
    for test_type in ("correlation", "chisq", "t_test", "rm_anova", "factorial"):
        d = quick_sample_size(test_type, 0.30)
        assert set(d) == keys
        src = calculate_sample_size(test_type, 0.30)
        assert d["solved"] == src.solved
        assert d["n_total"] == src.required_n and d["n_per_group"] == src.required_per_group
        assert d["n_groups"] == src.n_groups and d["test"] == src.test_name_zh
        assert d["note"] == src.note and d["effect_label"] == src.effect_size_label
        if src.solved:
            assert d["actual_power"] == pytest.approx(round(float(src.actual_power), 3))
        else:
            assert math.isnan(d["actual_power"])     # 未解 ⇒ NaN 占位，不是假数


def test_quick_sample_size_snapshot_correlation_r_030():
    """单点全文快照（现状数值，非结论背书）。"""
    assert quick_sample_size("correlation", 0.30) == {
        "test": "Pearson相关分析",
        "n_total": 85,
        "n_per_group": 85,
        "n_groups": 1,
        "effect_label": "中",
        "actual_power": pytest.approx(0.8),
        "note": "需要85名被试以检测r=0.30的相关",
        "solved": True,
    }


def test_quick_sample_size_defaults_to_d_half_now_reports_unsolved():
    """翻正自缺省路径现状桩：缺省 d=0.5 落在不可解区 ⇒ `solved=False`、`n_total=0`，
    不再把搜索区间上界当答案透出（这条钉的正是「不传参用户」拿到的数）。"""
    d = quick_sample_size("t_test")

    assert d["solved"] is False
    assert d["n_total"] == 0 and d["n_per_group"] == 0 and d["n_groups"] == 2
    assert math.isnan(d["actual_power"])


def test_format_power_report_snapshot_single_group():
    """整段文本快照：版式、百分号、小数位（0.800）都在这里钉死。"""
    r = PowerResult(
        test_type="correlation", test_name_zh="Pearson相关分析", required_n=85, required_per_group=85,
        n_groups=1, power=0.8, alpha=0.05, effect_size=0.3, effect_size_name="r", effect_size_label="中",
        actual_power=0.800346, df=83, note="需要85名被试以检测r=0.30的相关",
        assumptions="效应量r=0.30，双侧α=0.05，效力1-β=0.8",
    )
    assert format_power_report(r) == "\n".join([
        "## 统计效力分析报告",
        "",
        "**检验方法：** Pearson相关分析",
        "**预设效应量：** r = 0.30（中效应）",
        "**显著性水平：** α = 0.05",
        "**目标统计效力：** 1-β = 80%",
        "",
        "### 样本量建议",
        "- **所需总样本量：** N = **85**",
        "- **实际达到效力：** 1-β ≈ 0.800",
        "- **检验自由度：** df = 83",
        "",
        "### 说明",
        "需要85名被试以检测r=0.30的相关",
        "",
        "*计算前提：* 效应量r=0.30，双侧α=0.05，效力1-β=0.8",
        "",
        "### 建议",
        "- ✅ 实际效力达到目标水平。",
        "- 📊 考虑到数据质量（无效作答、注意力检查失败等），建议在计算基础上增加10%-20%的被试量。",
        "- 🔄 若为在线施测，建议额外增加15%-25%以应对更高的无效作答率。",
    ])


def test_format_power_report_short_power_branch_and_group_lines():
    """三条条件排版：n_groups>1 才出「每组样本量」；效力差 0.02 以上才出 ⚠。
    s924-04 起 ⚠ 缓冲量 = ceil(N×缺口)（缺口=目标−实际，含 6 位浮点护栏），不再固定 15%：
    N=10、actual=0.5、power=0.8 ⇒ 缺口 0.300 ⇒ ceil(round(3.0000000000000004,6))=3。"""
    r = PowerResult(test_type="chisq", test_name_zh="卡方检验", required_n=10, required_per_group=6,
                    n_groups=3, power=0.8, alpha=0.05, effect_size=0.1, effect_size_name="w",
                    effect_size_label="小", actual_power=0.5, df=1, note="n", assumptions="a")
    lines = format_power_report(r).split("\n")

    assert "- **每组样本量：** n = **6**（共3组）" in lines
    assert "- ⚠ 实际效力低于目标（缺口 0.300），按缺口另行估算建议增加约3名被试，重算后复核。" in lines
    assert not any("✅" in l for l in lines)
    # 恰好卡在 0.02 边界内侧 ⇒ 仍走 ✅ 分支（判据是 < power-0.02，边界不翻）
    ok = PowerResult(**{**{k: getattr(r, k) for k in
                           ("test_type", "test_name_zh", "required_n", "required_per_group", "n_groups",
                            "power", "alpha", "effect_size", "effect_size_name", "effect_size_label",
                            "df", "note", "assumptions")}, "actual_power": 0.7801})
    assert "- ✅ 实际效力达到目标水平。" in format_power_report(ok).split("\n")


# ═════════ 五、s924-04 新增：post_hoc_power 的 A′ 哨兵与裸 except 收窄 ═════════
from types import SimpleNamespace  # noqa: E402

from src.analysis import post_hoc_power  # noqa: E402


def _fake_t_output(effect, df_value, test_type="independent_ttest"):
    """不经 runner 的最小 output：result 带 effect_size/df 即可走通提取链。"""
    return {"test_type": test_type,
            "result": SimpleNamespace(effect_size=effect, df=df_value)}


class TestPostHocUnsolvedSentinel:
    def test_independent_t_unsolvable_effect_returns_solved_false_without_needed_key(self):
        """观察 d=0.5（不可解区）⇒ solved 存在且为 False，且 **不再返回区间上界假数**
        （n_needed_for_080 键整个不出现）。"""
        ph = post_hoc_power.estimate_post_hoc(_fake_t_output(0.5, 28))

        assert ph is not None
        assert "solved" in ph and ph["solved"] is False
        assert "n_needed_for_080" not in ph
        assert ph["needs_more_n"] is False
        assert "拒答" in ph["skipped_reason"]
        assert ph["observed_n"] == 30 and ph["observed_effect"] == 0.5
        assert ph["footnote"]

    def test_paired_t_unsolvable_effect_returns_solved_false(self):
        ph = post_hoc_power.estimate_post_hoc(
            _fake_t_output(0.3, 29, test_type="paired_ttest"))

        assert ph["solved"] is False and "n_needed_for_080" not in ph
        assert ph["observed_n"] == 30

    def test_solvable_effect_keeps_advice_and_flags_solved_true(self):
        """可解面哨兵：d=0.2、n=200 ⇒ 建议 788 与翻桩前逐位一致，且新增 solved=True 键。"""
        ph = post_hoc_power.estimate_post_hoc(_fake_t_output(0.2, 198))

        assert ph["solved"] is True
        assert ph["needs_more_n"] is True and ph["n_needed_for_080"] == 788

    def test_solver_exception_becomes_visible_sentinel_not_silent_none(self, monkeypatch):
        """:275 收窄自证：求解器抛 ValueError 不再被裸 except 吞成 None，而是转哨兵；
        非求解异常（如 KeyError）不再被本层捕获（静默缺席面同步消失）。"""
        def raiser(*a, **kw):
            raise ValueError("boom")
        monkeypatch.setattr(post_hoc_power, "calculate_sample_size", raiser)

        ph = post_hoc_power.estimate_post_hoc(_fake_t_output(0.5, 28))
        assert ph["solved"] is False
        assert "ValueError" in ph["skipped_reason"]

        def weird(*a, **kw):
            raise KeyError("not-a-solver-error")
        monkeypatch.setattr(post_hoc_power, "calculate_sample_size", weird)
        with pytest.raises(KeyError):
            post_hoc_power.estimate_post_hoc(_fake_t_output(0.5, 28))
