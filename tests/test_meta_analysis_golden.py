"""s923-47：meta_analysis 数值金档（fixed / random、Q / I² / τ²）。

金档来源纪律（红线域＝统计结论）：
- 下面 GOLDEN 里的**每一个数都是本机 `src/analysis/meta_analysis.py` 现码实测输出**（未手算、未外推），
  取值环境：`.venv` python 3.12.9 / numpy 2.5.1 / scipy 1.18.0 / pandas 3.0.3，日期 2026-09-24。
- **本件零生产码改动**：若现码输出与教科书公式或卷宗预期不符，本件只会红，不会去改 `src/analysis/`。
  实测对拍结论：生产输出与独立实现的逆方差/DL 公式在全部字段上逐位相同（见 `TestIndependentCrossCheck`）。
- 期望值保留生产码的舍入口径（pooled/CI/p/Q-q_p 4 位、z/Q 3 位、I² 1 位、τ² 4 位、权重与效应量 1/4 位），
  断言统一用 `TOL = 1e-6`。

复跑对拍（不依赖本仓 tmp/，任何机器一条命令重取金档）：

    # cd D:/code/psy-analysis && .venv/Scripts/python.exe -c "
    # import numpy as np, pandas as pd
    # from src.analysis.meta_analysis import run_meta_analysis
    # A=pd.DataFrame({'e':[0.35,0.20,0.55,0.10,0.45,0.30],'s':[0.10,0.08,0.15,0.06,0.12,0.09]})
    # for m in ('fixed','random'):
    #     r=run_meta_analysis(A,effect_col='e',se_col='s',model=m,generate_plot=False)
    #     print(m,r.pooled_effect,r.pooled_se,r.ci_lower,r.ci_upper,r.z_value,r.p_value,
    #           r.q_statistic,r.q_p_value,r.i_squared,r.tau_squared,r.study_weights)
    # np.random.seed(42)
    # B=pd.DataFrame({'e':np.random.normal(0.3,0.15,50),'s':np.random.uniform(0.05,0.2,50)})
    # r=run_meta_analysis(B,effect_col='e',se_col='s',model='random',generate_plot=False)
    # print('B',r.pooled_effect,r.q_statistic,r.i_squared,r.tau_squared)"

金档内联于下方 `GOLDEN`（同一次实测的完整字段，含 study_effects / study_cis）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.analysis.meta_analysis import run_meta_analysis

TOL = 1e-6

# ---------------------------------------------------------------------------
# 固定输入（决定论，不靠随机数流；B 组才用 seed）
# ---------------------------------------------------------------------------

A_EFFECTS = [0.35, 0.20, 0.55, 0.10, 0.45, 0.30]
A_SES = [0.10, 0.08, 0.15, 0.06, 0.12, 0.09]

# Q(3) = 0.599 < df = 3 ⇒ τ² 与 I² 双双落在 0 分支（齐次组）
D_EFFECTS = [0.05, 0.12, 0.02, 0.08]
D_SES = [0.09, 0.11, 0.08, 0.10]


def _df(effects, ses, labels=None):
    return pd.DataFrame({
        "effect_size": [float(x) for x in effects],
        "se": [float(x) for x in ses],
        "study": labels or [f"研究{i + 1}" for i in range(len(effects))],
    })


def _b_tables():
    """与 tests/test_ui.py::test_meta_analysis_performance 同源的 seed42 表（k=50）。

    用完**立刻还原全局随机流**：`np.random.seed` 是进程级状态，金档件不该把它留给兄弟用例
    （否则同进程合跑时别人的读数会被本班用例的播种顺序影响）。
    """
    saved = np.random.get_state()
    try:
        np.random.seed(42)
        effects = np.random.normal(0.3, 0.15, 50)
        ses = np.random.uniform(0.05, 0.2, 50)
    finally:
        np.random.set_state(saved)
    return _df(effects, ses, [f"研究{i}" for i in range(1, 51)])


# ---------------------------------------------------------------------------
# 金档（生产码实测输出，取值环境见模块 docstring）
# ---------------------------------------------------------------------------

GOLDEN = {
    "A_fixed": {
        "k": 6, "pooled_effect": 0.2421, "pooled_se": 0.036, "ci_lower": 0.1715,
        "ci_upper": 0.3127, "z_value": 6.724, "p_value": 0.0, "q_statistic": 14.679,
        "q_df": 5, "q_p_value": 0.0118, "i_squared": 65.9, "tau_squared": 0.0,
        "study_weights": [13.0, 20.3, 5.8, 36.0, 9.0, 16.0],
        "study_effects": [0.35, 0.2, 0.55, 0.1, 0.45, 0.3],
        "study_cis": [(0.1540036, 0.5459964), (0.04320288, 0.35679712),
                      (0.2560054, 0.8439946), (-0.01759784, 0.21759784),
                      (0.21480432, 0.68519568), (0.12360324, 0.47639676)],
        "weights_sum": 100.1,
    },
    "A_random": {
        "k": 6, "pooled_effect": 0.2946, "pooled_se": 0.0655, "ci_lower": 0.1661,
        "ci_upper": 0.423, "z_value": 4.494, "p_value": 0.0, "q_statistic": 14.679,
        "q_df": 5, "q_p_value": 0.0118, "i_squared": 65.9, "tau_squared": 0.0162,
        "study_weights": [16.4, 19.0, 11.1, 21.7, 14.0, 17.7],
        "study_effects": [0.35, 0.2, 0.55, 0.1, 0.45, 0.3],
        "study_cis": [(0.1540036, 0.5459964), (0.04320288, 0.35679712),
                      (0.2560054, 0.8439946), (-0.01759784, 0.21759784),
                      (0.21480432, 0.68519568), (0.12360324, 0.47639676)],
        "weights_sum": 99.9,
    },
    "A_random_conf99": {
        "k": 6, "pooled_effect": 0.2946, "pooled_se": 0.0655, "ci_lower": 0.1257,
        "ci_upper": 0.4634, "z_value": 4.494, "p_value": 0.0, "q_statistic": 14.679,
        "q_df": 5, "q_p_value": 0.0118, "i_squared": 65.9, "tau_squared": 0.0162,
        "weights_sum": 99.9,
    },
    "A_fixed_conf90": {
        "k": 6, "pooled_effect": 0.2421, "pooled_se": 0.036, "ci_lower": 0.1829,
        "ci_upper": 0.3013, "z_value": 6.724, "p_value": 0.0, "q_statistic": 14.679,
        "q_df": 5, "q_p_value": 0.0118, "i_squared": 65.9, "tau_squared": 0.0,
        "weights_sum": 100.1,
    },
    "D_random": {
        "k": 4, "pooled_effect": 0.0589, "pooled_se": 0.0465, "ci_lower": -0.0323,
        "ci_upper": 0.15, "z_value": 1.266, "p_value": 0.2056, "q_statistic": 0.599,
        "q_df": 3, "q_p_value": 0.8966, "i_squared": 0.0, "tau_squared": 0.0,
        "study_weights": [26.7, 17.9, 33.8, 21.6],
        "study_effects": [0.05, 0.12, 0.02, 0.08],
        "study_cis": [(-0.12639676, 0.22639676), (-0.09559604, 0.33559604),
                      (-0.13679712, 0.17679712), (-0.1159964, 0.2759964)],
        "weights_sum": 100.0,
    },
    "B_random": {
        "k": 50, "pooled_effect": 0.2697, "pooled_se": 0.0215, "ci_lower": 0.2275,
        "ci_upper": 0.3118, "z_value": 12.547, "p_value": 0.0, "q_statistic": 104.62,
        "q_df": 49, "q_p_value": 0.0, "i_squared": 53.2, "tau_squared": 0.0104,
        "weights_sum": 100.1,
    },
    "B_fixed": {
        "k": 50, "pooled_effect": 0.2842, "pooled_se": 0.0135, "ci_lower": 0.2578,
        "ci_upper": 0.3105, "z_value": 21.12, "p_value": 0.0, "q_statistic": 104.62,
        "q_df": 49, "q_p_value": 0.0, "i_squared": 53.2, "tau_squared": 0.0,
        "weights_sum": 100.1,
    },
}

SCALAR_FIELDS = ["k", "pooled_effect", "pooled_se", "ci_lower", "ci_upper", "z_value",
                 "p_value", "q_statistic", "q_df", "q_p_value", "i_squared", "tau_squared"]


def _run(df, model="random", confidence=0.95, effect_type="d", **kw):
    return run_meta_analysis(df, effect_col="effect_size", se_col="se", label_col="study",
                             model=model, confidence=confidence, effect_type=effect_type,
                             generate_plot=False, **kw)


def _assert_golden(result, key):
    g = GOLDEN[key]
    for f in SCALAR_FIELDS:
        if f in g:
            assert getattr(result, f) == pytest.approx(g[f], abs=TOL), f"{key}.{f}"
    if "study_weights" in g:
        assert result.study_weights == pytest.approx(g["study_weights"], abs=TOL)
    if "study_effects" in g:
        assert result.study_effects == pytest.approx(g["study_effects"], abs=TOL)
    if "study_cis" in g:
        assert len(result.study_cis) == len(g["study_cis"])
        for (lo, hi), (glo, ghi) in zip(result.study_cis, g["study_cis"]):
            assert lo == pytest.approx(glo, abs=TOL)
            assert hi == pytest.approx(ghi, abs=TOL)
    assert sum(result.study_weights) == pytest.approx(g["weights_sum"], abs=1e-9)


# ---------------------------------------------------------------------------
# 一、固定效应模型金档
# ---------------------------------------------------------------------------

class TestFixedEffectGolden:
    def test_A_fixed_full_vector(self):
        _assert_golden(_run(_df(A_EFFECTS, A_SES), model="fixed"), "A_fixed")

    def test_A_fixed_weights_are_inverse_variance_percentages(self):
        """逆方差权重百分比＝(1/se²)/Σ(1/se²)·100，逐研究钉到 1e-6。"""
        w = np.array([1 / s ** 2 for s in A_SES])
        expect = [round(float(x / w.sum() * 100), 1) for x in w]
        assert _run(_df(A_EFFECTS, A_SES), model="fixed").study_weights == pytest.approx(
            expect, abs=TOL)

    def test_A_fixed_tau_squared_is_hard_zero(self):
        """固定效应分支 τ² 恒为 0.0（即使 Q 显著），这是与随机效应的唯一结构性差别。"""
        assert _run(_df(A_EFFECTS, A_SES), model="fixed").tau_squared == 0.0


# ---------------------------------------------------------------------------
# 二、随机效应模型（DerSimonian–Laird）金档
# ---------------------------------------------------------------------------

class TestRandomEffectGolden:
    def test_A_random_full_vector(self):
        _assert_golden(_run(_df(A_EFFECTS, A_SES), model="random"), "A_random")

    def test_A_random_tau_squared_and_shift_direction(self):
        """τ²=0.0162（Q=14.679 > df=5 才有）；随机汇总被拉向等权均值 0.325 一侧。"""
        r = _run(_df(A_EFFECTS, A_SES), model="random")
        assert r.tau_squared == pytest.approx(0.0162, abs=TOL)
        assert r.pooled_effect == pytest.approx(0.2946, abs=TOL)
        assert r.pooled_effect > GOLDEN["A_fixed"]["pooled_effect"]
        assert r.pooled_effect < float(np.mean(A_EFFECTS))
        assert r.pooled_se > GOLDEN["A_fixed"]["pooled_se"]        # 随机 SE 更宽
        assert r.ci_upper - r.ci_lower > (GOLDEN["A_fixed"]["ci_upper"]
                                          - GOLDEN["A_fixed"]["ci_lower"])

    def test_A_random_dl_tau_matches_closed_form(self):
        """DL 闭式：τ² = (Q − df) / (Σw − Σw²/Σw)，w＝逆方差权重。"""
        w = 1.0 / np.array(A_SES) ** 2
        pooled_fe = float((w * np.array(A_EFFECTS)).sum() / w.sum())
        q = float((w * (np.array(A_EFFECTS) - pooled_fe) ** 2).sum())
        dfree = len(A_EFFECTS) - 1
        c = float(w.sum() - (w ** 2).sum() / w.sum())
        tau = max(0.0, (q - dfree) / c)
        r = _run(_df(A_EFFECTS, A_SES), model="random")
        assert round(tau, 4) == pytest.approx(r.tau_squared, abs=TOL)
        assert round(r.q_statistic, 3) == pytest.approx(round(q, 3), abs=TOL)
        assert r.i_squared == pytest.approx(round(max(0.0, (q - dfree) / q * 100), 1), abs=TOL)

    def test_homogeneous_set_collapses_both_models(self):
        """Q(3)=0.599 < df ⇒ τ²=I²=0 ⇒ 随机与固定逐字段相同（金档 D 组）。"""
        rd = _run(_df(D_EFFECTS, D_SES), model="random")
        _assert_golden(rd, "D_random")
        rf = _run(_df(D_EFFECTS, D_SES), model="fixed")
        for f in SCALAR_FIELDS:
            assert getattr(rf, f) == pytest.approx(getattr(rd, f), abs=TOL)
        assert rd.tau_squared == 0.0 and rd.i_squared == 0.0
        assert rd.p_value == pytest.approx(0.2056, abs=TOL)       # 非退化 p（对照组）
        assert rd.q_p_value == pytest.approx(0.8966, abs=TOL)


# ---------------------------------------------------------------------------
# 三、异质性族：Q / df / q_p / I²
# ---------------------------------------------------------------------------

class TestHeterogeneityGolden:
    def test_A_heterogeneity_triple(self):
        r = _run(_df(A_EFFECTS, A_SES), model="random")
        assert r.q_statistic == pytest.approx(14.679, abs=TOL)
        assert r.q_df == 5
        assert r.q_p_value == pytest.approx(0.0118, abs=TOL)
        assert r.i_squared == pytest.approx(65.9, abs=TOL)

    def test_q_and_i_squared_identical_across_models(self):
        """Q/I² 由固定效应权重算出 ⇒ 两模型的异质性读数必须逐位相同（random 不得重算）。"""
        rf, rr = (_run(_df(A_EFFECTS, A_SES), model=m) for m in ("fixed", "random"))
        for f in ("q_statistic", "q_df", "q_p_value", "i_squared"):
            assert getattr(rf, f) == pytest.approx(getattr(rr, f), abs=TOL)

    def test_q_p_value_is_chi2_upper_tail(self):
        """q_p 与 scipy 独立实现的 χ²(5) 上侧尾概率一致。"""
        r = _run(_df(A_EFFECTS, A_SES), model="fixed")
        assert r.q_p_value == pytest.approx(
            float(1 - stats.chi2.cdf(r.q_statistic, r.q_df)), abs=1e-4)

    def test_B_heterogeneity_k50(self):
        r = _run(_b_tables(), model="random")
        assert r.q_statistic == pytest.approx(104.62, abs=TOL)
        assert r.q_df == 49
        assert r.i_squared == pytest.approx(53.2, abs=TOL)
        assert r.tau_squared == pytest.approx(0.0104, abs=TOL)


# ---------------------------------------------------------------------------
# 四、k 与权重和
# ---------------------------------------------------------------------------

class TestKAndWeightSum:
    def test_k_and_weight_vectors(self):
        rf, rr = _run(_df(A_EFFECTS, A_SES), model="fixed"), _run(_df(A_EFFECTS, A_SES))
        assert (rf.k, rr.k) == (6, 6)
        assert len(rf.study_weights) == len(rr.study_weights) == 6
        assert rf.study_weights == pytest.approx(GOLDEN["A_fixed"]["study_weights"], abs=TOL)
        assert rr.study_weights == pytest.approx(GOLDEN["A_random"]["study_weights"], abs=TOL)

    def test_weights_sum_is_not_exactly_100(self):
        """金档实测：逐研究权重各自 round(…,1) 后再求和 ⇒ 和会漂到 100.1 / 99.9。

        这不是 bug，但报告表 `format_meta_analysis` 的"汇总 100.0"行是**硬编码**，
        与该列实际相加结果不一致（见 result 的遗留问题）。
        """
        assert sum(_run(_df(A_EFFECTS, A_SES), model="fixed").study_weights) == pytest.approx(
            100.1, abs=1e-9)
        assert sum(_run(_df(A_EFFECTS, A_SES)).study_weights) == pytest.approx(99.9, abs=1e-9)
        assert sum(_run(_df(D_EFFECTS, D_SES)).study_weights) == pytest.approx(100.0, abs=1e-9)

    def test_study_effects_rounded_to_4dp(self):
        r = _run(_df([0.333333, 0.777777, 0.5], [0.1, 0.2, 0.15]), model="fixed")
        assert r.study_effects == pytest.approx([0.3333, 0.7778, 0.5], abs=TOL)


# ---------------------------------------------------------------------------
# 五、置信水平与其他入口参数
# ---------------------------------------------------------------------------

class TestConfidenceAndOptions:
    def test_conf99_vector(self):
        _assert_golden(_run(_df(A_EFFECTS, A_SES), confidence=0.99), "A_random_conf99")

    def test_conf90_fixed_vector(self):
        _assert_golden(_run(_df(A_EFFECTS, A_SES), model="fixed", confidence=0.90),
                       "A_fixed_conf90")

    def test_ci_width_monotone_in_confidence_point_estimate_fixed(self):
        """置信水平只动 CI：汇总点估计/z/p/Q/I²/τ² 必须逐位不动，CI 宽度随置信度单调增。"""
        runs = {c: _run(_df(A_EFFECTS, A_SES), model="random", confidence=c)
                for c in (0.90, 0.95, 0.99)}
        widths = [runs[c].ci_upper - runs[c].ci_lower for c in (0.90, 0.95, 0.99)]
        assert widths == sorted(widths) and widths[0] < widths[1] < widths[2]
        for c in (0.90, 0.99):
            assert runs[c].pooled_effect == pytest.approx(0.2946, abs=TOL)
            assert runs[c].z_value == pytest.approx(4.494, abs=TOL)
            assert runs[c].p_value == pytest.approx(0.0, abs=TOL)
            assert runs[c].tau_squared == pytest.approx(0.0162, abs=TOL)
            assert runs[c].i_squared == pytest.approx(65.9, abs=TOL)

    def test_effect_type_is_label_only_not_unit_conversion(self):
        """effect_type="r"/"z" 与 "d" 的**全部数值**逐位相同（它只改森林图/报告的单位标签）。

        口径提醒：调用方若把相关系数 r 直接塞进 effect_col 并要求 d 的解读，本函数不会换算。
        """
        base = _run(_df(A_EFFECTS, A_SES), model="random", effect_type="d")
        for et in ("r", "z", "nonsense"):
            alt = _run(_df(A_EFFECTS, A_SES), model="random", effect_type=et)
            for f in SCALAR_FIELDS:
                assert getattr(alt, f) == pytest.approx(getattr(base, f), abs=TOL)
            assert alt.effect_type == et

    def test_se_derived_from_ci_bounds_equals_given_se(self):
        """se_col 缺省时按 (hi−lo)/(2·z_crit) 反推 se ⇒ 结果与直接给 se 逐位相同。"""
        z = float(stats.norm.ppf(0.975))
        df_ci = pd.DataFrame({
            "effect_size": A_EFFECTS,
            "lo": [e - z * s for e, s in zip(A_EFFECTS, A_SES)],
            "hi": [e + z * s for e, s in zip(A_EFFECTS, A_SES)],
            "study": [f"研究{i + 1}" for i in range(6)],
        })
        via_ci = run_meta_analysis(df_ci, effect_col="effect_size", ci_lower_col="lo",
                                   ci_upper_col="hi", label_col="study", model="random",
                                   generate_plot=False)
        _assert_golden(via_ci, "A_random")


# ---------------------------------------------------------------------------
# 六、边界与入参校验
# ---------------------------------------------------------------------------

class TestBoundary:
    def test_k_lt_2_raises(self):
        with pytest.raises(ValueError, match="至少需要2项研究"):
            _run(_df([0.3], [0.1]))

    def test_missing_se_columns_raises(self):
        df = pd.DataFrame({"effect_size": [0.3, 0.4], "study": ["a", "b"]})
        with pytest.raises(ValueError, match="必须提供 se_col"):
            run_meta_analysis(df, effect_col="effect_size", label_col="study",
                              generate_plot=False)

    def test_default_model_is_random_not_fixed(self):
        """不传 model ⇒ 走随机效应（金档两模型的 pooled 相差 0.0525，够区分）。

        刻意绕开 `_run()` 助手直调生产函数：助手会显式塞 model="random"，
        那样就测不到签名里的默认值（变异实测：改掉默认值只有本版写法会红）。
        """
        df = _df(A_EFFECTS, A_SES)
        r = run_meta_analysis(df, effect_col="effect_size", se_col="se",
                              label_col="study", generate_plot=False)
        assert r.model == "random"
        assert r.pooled_effect == pytest.approx(0.2946, abs=TOL)
        assert r.tau_squared == pytest.approx(0.0162, abs=TOL)

    def test_labels_default_when_label_col_absent(self):
        df = pd.DataFrame({"effect_size": A_EFFECTS, "se": A_SES})
        r = run_meta_analysis(df, effect_col="effect_size", se_col="se", model="fixed",
                              generate_plot=False)
        assert r.study_labels == ["研究1", "研究2", "研究3", "研究4", "研究5", "研究6"]
        assert r.pooled_effect == pytest.approx(0.2421, abs=TOL)


# ---------------------------------------------------------------------------
# 七、独立实现全量对拍（发现缺陷用，不用来"改齐"生产码）
# ---------------------------------------------------------------------------

class TestIndependentCrossCheck:
    @staticmethod
    def _independent(effects, ses, model, confidence=0.95):
        e = np.asarray(effects, float)
        s = np.asarray(ses, float)
        zc = float(stats.norm.ppf(1 - (1 - confidence) / 2))
        w_fe = 1.0 / s ** 2
        pooled_fe = float((w_fe * e).sum() / w_fe.sum())
        q = float((w_fe * (e - pooled_fe) ** 2).sum())
        dfree = len(e) - 1
        i2 = max(0.0, (q - dfree) / q * 100) if q > 0 else 0.0
        if model == "fixed":
            pooled, se, tau = pooled_fe, float(np.sqrt(1 / w_fe.sum())), 0.0
            pct = [float(x / w_fe.sum() * 100) for x in w_fe]
        else:
            c = float(w_fe.sum() - (w_fe ** 2).sum() / w_fe.sum())
            tau = max(0.0, (q - dfree) / c) if (c > 0 and q > dfree) else 0.0
            w_re = 1.0 / (s ** 2 + tau)
            pooled = float((w_re * e).sum() / w_re.sum())
            se = float(np.sqrt(1 / w_re.sum()))
            pct = [float(x / w_re.sum() * 100) for x in w_re]
        z = pooled / se
        return {
            "pooled_effect": round(pooled, 4), "pooled_se": round(se, 4),
            "ci_lower": round(pooled - zc * se, 4), "ci_upper": round(pooled + zc * se, 4),
            "z_value": round(z, 3), "p_value": round(float(2 * (1 - stats.norm.cdf(abs(z)))), 4),
            "q_statistic": round(q, 3), "q_df": dfree,
            "q_p_value": round(float(1 - stats.chi2.cdf(q, dfree)), 4),
            "i_squared": round(i2, 1), "tau_squared": round(tau, 4),
            "weights_sum": round(sum(round(x, 1) for x in pct), 1),
        }

    @pytest.mark.parametrize("key,effect_type", [
        ("A_fixed", "fixed"), ("A_random", "random"), ("D_random", "random"),
    ])
    def test_matches_independent_implementation(self, key, effect_type):
        src = {"A_fixed": (A_EFFECTS, A_SES), "A_random": (A_EFFECTS, A_SES),
               "D_random": (D_EFFECTS, D_SES)}[key]
        mine = self._independent(src[0], src[1], effect_type)
        for f, v in mine.items():
            assert GOLDEN[key][f] == pytest.approx(v, abs=TOL), f"{key}: {f}"

    def test_golden_is_not_a_rounding_tightrope(self):
        """金档稳定性守卫：现码输出必须仍等于独立实现的**未舍入**值舍入后的结果。

        若哪天 float 噪声把某个数推到舍入翻转点附近（半格 = 5e-5 / 5e-4 / 5e-2），
        金档会立刻红；实测最小余量 1.1e-6（B 组 ci_upper），距翻转点仍有 ~4.9e-5。
        """
        e = np.asarray(A_EFFECTS, float)
        s = np.asarray(A_SES, float)
        w = 1.0 / s ** 2
        raw_pooled = float((w * e).sum() / w.sum())
        step = 1e-4
        dist_to_tie = abs((raw_pooled % step) - step / 2)
        assert dist_to_tie > 1e-6, f"金档落在舍入翻转点 {dist_to_tie:g} 附近，须换表重取"
