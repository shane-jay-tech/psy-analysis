"""实验设计系统 — 统计效力分析（先验样本量计算）

基于 scipy 的非中心分布计算达到目标统计效力所需的最小样本量。
参考: Cohen (1988), Faul et al. (2007, G*Power)
"""

import numpy as np
from scipy.stats import nct, ncf, ncx2, norm
from scipy.optimize import brentq
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class PowerResult:
    """统计效力分析结果"""
    test_type: str = ""
    test_name_zh: str = ""
    required_n: int = 0
    required_per_group: int = 0
    n_groups: int = 0
    power: float = 0.80
    alpha: float = 0.05
    effect_size: float = 0.0
    effect_size_name: str = ""
    effect_size_label: str = ""         # 小/中/大
    actual_power: float = 0.0           # 实际达到的效力
    df: int = 0
    note: str = ""
    assumptions: str = ""


# ── 效应量基准（Cohen的约定） ──────────────────────────────────
EFFECT_BENCHMARKS = {
    "cohens_d": [(0.20, "小"), (0.50, "中"), (0.80, "大")],
    "cohens_f": [(0.10, "小"), (0.25, "中"), (0.40, "大")],
    "cohens_f2": [(0.02, "小"), (0.15, "中"), (0.35, "大")],
    "r": [(0.10, "小"), (0.30, "中"), (0.50, "大")],
    "cohens_w": [(0.10, "小"), (0.30, "中"), (0.50, "大")],
    "eta_sq": [(0.01, "小"), (0.06, "中"), (0.14, "大")],
}


def _label_effect(value: float, benchmarks: list) -> str:
    """给效应量打小/中/大标签"""
    label = "极小"
    for threshold, name in benchmarks:
        if value >= threshold:
            label = name
    return label


# ═══════════════════════════════════════════════════════════════
# 核心计算函数
# ═══════════════════════════════════════════════════════════════

def _solve_n_for_t_test(d: float, power: float, alpha: float,
                        paired: bool, ratio: float = 1.0) -> PowerResult:
    """求解独立样本或配对样本t检验所需的样本量。

    使用非中心t分布迭代搜索。delta = d * sqrt(n1*n2/(n1+n2))。
    对于配对检验，delta = d * sqrt(n)。
    """
    if paired:
        # 配对t检验: df = n-1, ncp = d * sqrt(n)
        def power_at_n(n):
            n = max(n, 2)
            df = n - 1
            ncp = d * np.sqrt(n)
            t_crit = nct.ppf(1 - alpha / 2, df, 0)
            # 双侧检验: power = P(|t| > t_crit | t ~ nct(df, ncp))
            p_right = 1 - nct.cdf(t_crit, df, ncp)
            p_left = nct.cdf(-t_crit, df, ncp)
            return p_right + p_left

        def f(n):
            return power_at_n(n) - power

        # 从合理范围搜索
        n_lo, n_hi = 2, 2000
        try:
            n = brentq(f, n_lo, n_hi, maxiter=100)
            n = int(np.ceil(n))
        except ValueError:
            n = int(np.ceil(n_hi))

        actual = power_at_n(n)
        return PowerResult(
            test_type="paired_t", test_name_zh="配对样本t检验",
            required_n=n, required_per_group=n, n_groups=1,
            power=power, alpha=alpha, effect_size=d,
            effect_size_name="Cohen's d", effect_size_label=_label_effect(d, EFFECT_BENCHMARKS["cohens_d"]),
            actual_power=actual, df=n - 1,
            note=f"配对设计，需要{n}名被试",
            assumptions=f"效应量d={d:.2f}，双侧α={alpha}，效力1-β={power}",
        )
    else:
        # 独立样本t检验: n2 = ratio * n1
        def power_at_total(N):
            """给定总样本量，计算效力"""
            n1 = max(N / (1 + ratio), 2)
            n2 = max(N - n1, 2)
            n1, n2 = int(n1), int(n2)
            df = n1 + n2 - 2
            ncp = d * np.sqrt(n1 * n2 / (n1 + n2))
            t_crit = nct.ppf(1 - alpha / 2, df, 0)
            p_right = 1 - nct.cdf(t_crit, df, ncp)
            p_left = nct.cdf(-t_crit, df, ncp)
            return p_right + p_left

        def f(N):
            return power_at_total(N) - power

        N_lo, N_hi = 4, 4000
        try:
            N = brentq(f, N_lo, N_hi, maxiter=100)
        except ValueError:
            N = N_hi

        n1 = max(int(np.ceil(N / (1 + ratio))), 2)
        n2 = max(int(np.ceil(ratio * n1)), 2)
        N_actual = n1 + n2
        actual = power_at_total(N_actual)

        return PowerResult(
            test_type="independent_t", test_name_zh="独立样本t检验",
            required_n=N_actual, required_per_group=n1, n_groups=2,
            power=power, alpha=alpha, effect_size=d,
            effect_size_name="Cohen's d", effect_size_label=_label_effect(d, EFFECT_BENCHMARKS["cohens_d"]),
            actual_power=actual, df=N_actual - 2,
            note=f"独立组设计，两组分别{n1}人和{n2}人，共{N_actual}人",
            assumptions=f"效应量d={d:.2f}，双侧α={alpha}，效力1-β={power}，分组比={ratio}",
        )


def _solve_n_for_anova_f(f_effect: float, k: int, power: float, alpha: float,
                         is_repeated: bool = False, correlation: float = 0.5) -> PowerResult:
    """求解ANOVA所需样本量。

    组间：lambda = n * k * f^2
    重复测量：lambda = n * k * f^2 / (1 - rho)
    """
    name = "重复测量方差分析" if is_repeated else "单因素方差分析"
    ttype = "rm_anova" if is_repeated else "oneway_anova"

    # 计算非中心参数与样本量的关系
    if is_repeated:
        factor = k / (1 - correlation)
    else:
        factor = k

    def power_at_n(n):
        n = max(n, k + 1)
        df1 = k - 1
        df2 = (n - 1) * (k - 1) if is_repeated else n - k
        ncp = n * factor * f_effect ** 2
        f_crit = ncf.ppf(1 - alpha, df1, df2, 0)
        return 1 - ncf.cdf(f_crit, df1, df2, ncp)

    def f(n):
        return power_at_n(n) - power

    n_lo, n_hi = k + 1, 2000
    try:
        n = brentq(f, n_lo, n_hi, maxiter=100)
    except ValueError:
        n = n_hi

    n = int(np.ceil(n))
    n_per = n
    actual = power_at_n(n)

    return PowerResult(
        test_type=ttype, test_name_zh=name,
        required_n=n, required_per_group=n_per, n_groups=k,
        power=power, alpha=alpha, effect_size=f_effect,
        effect_size_name="Cohen's f", effect_size_label=_label_effect(f_effect, EFFECT_BENCHMARKS["cohens_f"]),
        actual_power=actual, df=(k - 1),
        note=f"{k}个水平/组，每组{n_per}人（{'重复测量' if is_repeated else '独立组'}），共{'n=' + str(n) if is_repeated else 'N=' + str(n * k)}",
        assumptions=f"效应量f={f_effect:.2f}，α={alpha}，效力1-β={power}" + (
            f"，重复测量相关ρ={correlation}" if is_repeated else ""
        ),
    )


def _solve_n_for_correlation(r: float, power: float, alpha: float) -> PowerResult:
    """求解相关分析所需样本量。

    使用 Fisher z 变换: z = 0.5 * ln((1+r)/(1-r))
    z检验的ncp = z * sqrt(n-3)
    """
    zr = 0.5 * np.log((1 + r) / (1 - r))

    def power_at_n(n):
        n = max(n, 5)
        se = 1.0 / np.sqrt(n - 3)
        z_crit = norm.ppf(1 - alpha / 2)
        # 双侧
        p_right = 1 - norm.cdf(z_crit, loc=zr / se, scale=1.0)
        p_left = norm.cdf(-z_crit, loc=zr / se, scale=1.0)
        return p_right + p_left

    def f(n):
        return power_at_n(n) - power

    n_lo, n_hi = 5, 3000
    try:
        n = brentq(f, n_lo, n_hi, maxiter=100)
    except ValueError:
        n = n_hi

    n = int(np.ceil(n))
    actual = power_at_n(n)

    return PowerResult(
        test_type="correlation", test_name_zh="Pearson相关分析",
        required_n=n, required_per_group=n, n_groups=1,
        power=power, alpha=alpha, effect_size=r,
        effect_size_name="r", effect_size_label=_label_effect(abs(r), EFFECT_BENCHMARKS["r"]),
        actual_power=actual, df=n - 2,
        note=f"需要{n}名被试以检测r={r:.2f}的相关",
        assumptions=f"效应量r={r:.2f}，双侧α={alpha}，效力1-β={power}",
    )


def _solve_n_for_chisq(w: float, df: int, power: float, alpha: float) -> PowerResult:
    """求解卡方检验所需样本量。

    lambda = N * w^2, 其中 w 是 Cohen's w 效应量
    """
    def power_at_n(n):
        n = max(n, df + 2)
        ncp = n * w ** 2
        chi_crit = ncx2.ppf(1 - alpha, df, 0)
        return 1 - ncx2.cdf(chi_crit, df, ncp)

    n_lo, n_hi = df + 2, 5000
    try:
        n = brentq(lambda n: power_at_n(n) - power, n_lo, n_hi, maxiter=100)
    except ValueError:
        n = n_hi

    n = int(np.ceil(n))
    actual = power_at_n(n)

    return PowerResult(
        test_type="chisq", test_name_zh="卡方检验",
        required_n=n, required_per_group=n, n_groups=1,
        power=power, alpha=alpha, effect_size=w,
        effect_size_name="Cohen's w", effect_size_label=_label_effect(w, EFFECT_BENCHMARKS["cohens_w"]),
        actual_power=actual, df=df,
        note=f"需要{n}名被试",
        assumptions=f"效应量w={w:.2f}，自由度df={df}，α={alpha}，效力1-β={power}",
    )


def _solve_n_for_factorial_anova(f_effect: float, design: str,
                                  power: float, alpha: float) -> PowerResult:
    """求解多因素方差分析所需样本量。

    design: "2x2", "2x3", "3x3", "2x2x2" 等
    """
    # 解析设计
    try:
        factors = [int(x) for x in design.split("x")]
    except ValueError:
        factors = [2, 2]  # 默认2x2

    k = np.prod(factors)  # 总组数
    df_effect = np.prod([f - 1 for f in factors])  # 交互作用df

    # 使用交互作用的df作为最保守估计（通常最难检测）
    df1 = max(1, min(df_effect, k - 1))

    def power_at_n(n_per):
        n_per = max(n_per, 2)
        N = n_per * k
        df2 = N - k
        ncp = n_per * k * f_effect ** 2
        f_crit = ncf.ppf(1 - alpha, df1, df2, 0)
        return 1 - ncf.cdf(f_crit, df1, df2, ncp)

    n_lo, n_hi = 2, 2000
    try:
        n_per = brentq(lambda n: power_at_n(n) - power, n_lo, n_hi, maxiter=100)
    except ValueError:
        n_per = n_hi

    n_per = int(np.ceil(n_per))
    N = n_per * k
    actual = power_at_n(n_per)

    return PowerResult(
        test_type="factorial_anova", test_name_zh=f"{design}因素方差分析",
        required_n=N, required_per_group=n_per, n_groups=k,
        power=power, alpha=alpha, effect_size=f_effect,
        effect_size_name="Cohen's f", effect_size_label=_label_effect(f_effect, EFFECT_BENCHMARKS["cohens_f"]),
        actual_power=actual, df=df1,
        note=f"{design}设计，{k}个实验条件，每组{n_per}人，共{N}人",
        assumptions=f"效应量f={f_effect:.2f}，α={alpha}，效力1-β={power}，df1={df1}",
    )


# ═══════════════════════════════════════════════════════════════
# 公开API
# ═══════════════════════════════════════════════════════════════

def calculate_sample_size(
    test_type: str,
    effect_size: float = 0.5,
    power: float = 0.80,
    alpha: float = 0.05,
    n_groups: int = 2,
    design: str = "2x2",
    paired: bool = False,
    correlation: float = 0.5,
    ratio: float = 1.0,
    df: int = 1,
) -> PowerResult:
    """统一的样本量计算接口。

    参数:
        test_type: "t_test" | "anova" | "correlation" | "chisq" | "factorial" | "rm_anova"
        effect_size: Cohen's d / f / r / w
        power: 目标统计效力 (默认0.80)
        alpha: 显著性水平 (默认0.05)
        n_groups: 组数/水平数（ANOVA用）
        design: 因素设计格式（如 "2x2", "2x3"）
        paired: 是否配对设计
        correlation: 重复测量之间相关（仅rm_anova）
        ratio: 分组比（仅独立t检验，n2/n1）
        df: 卡方自由度
    """
    if test_type in ("t_test", "t检验", "independent_t"):
        return _solve_n_for_t_test(effect_size, power, alpha, paired=False, ratio=ratio)
    elif test_type in ("paired_t", "配对t检验"):
        return _solve_n_for_t_test(effect_size, power, alpha, paired=True)
    elif test_type in ("anova", "方差分析", "oneway_anova"):
        return _solve_n_for_anova_f(effect_size, n_groups, power, alpha, is_repeated=False)
    elif test_type in ("rm_anova", "重复测量方差分析"):
        return _solve_n_for_anova_f(effect_size, n_groups, power, alpha, is_repeated=True, correlation=correlation)
    elif test_type in ("factorial", "因素方差分析", "多因素"):
        return _solve_n_for_factorial_anova(effect_size, design, power, alpha)
    elif test_type in ("correlation", "相关", "相关分析"):
        return _solve_n_for_correlation(effect_size, power, alpha)
    elif test_type in ("chisq", "卡方", "卡方检验"):
        return _solve_n_for_chisq(effect_size, df, power, alpha)
    else:
        raise ValueError(f"不支持的检验类型: {test_type}")


def format_power_report(result: PowerResult) -> str:
    """格式化效力分析报告（中文）"""
    lines = [
        f"## 统计效力分析报告",
        f"",
        f"**检验方法：** {result.test_name_zh}",
        f"**预设效应量：** {result.effect_size_name} = {result.effect_size:.2f}（{result.effect_size_label}效应）",
        f"**显著性水平：** α = {result.alpha}",
        f"**目标统计效力：** 1-β = {result.power:.0%}",
        f"",
        f"### 样本量建议",
        f"- **所需总样本量：** N = **{result.required_n}**",
    ]
    if result.n_groups > 1:
        lines.append(f"- **每组样本量：** n = **{result.required_per_group}**（共{result.n_groups}组）")
    lines.extend([
        f"- **实际达到效力：** 1-β ≈ {result.actual_power:.3f}",
        f"- **检验自由度：** df = {result.df}",
        f"",
        f"### 说明",
        f"{result.note}",
        f"",
        f"*计算前提：* {result.assumptions}",
        f"",
        f"### 建议",
    ])

    # 添加具体建议
    if result.actual_power < result.power - 0.02:
        lines.append(f"- ⚠ 实际效力略低于目标，建议增加{int(result.required_n * 0.15)}名被试作为缓冲。")
    else:
        lines.append(f"- ✅ 实际效力达到目标水平。")

    lines.append(f"- 📊 考虑到数据质量（无效作答、注意力检查失败等），建议在计算基础上增加10%-20%的被试量。")
    lines.append(f"- 🔄 若为在线施测，建议额外增加15%-25%以应对更高的无效作答率。")

    return "\n".join(lines)


# ── 便捷函数 ──────────────────────────────────────────────

def quick_sample_size(test_type: str, effect_size: float = 0.5) -> Dict:
    """快速估算样本量，返回简洁字典。"""
    result = calculate_sample_size(test_type, effect_size)
    return {
        "test": result.test_name_zh,
        "n_total": result.required_n,
        "n_per_group": result.required_per_group,
        "n_groups": result.n_groups,
        "effect_label": result.effect_size_label,
        "actual_power": round(result.actual_power, 3),
        "note": result.note,
    }
