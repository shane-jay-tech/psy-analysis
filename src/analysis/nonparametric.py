"""非参数检验：Mann-Whitney U / Wilcoxon符号秩 / Kruskal-Wallis H / Friedman"""
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class NonParamResult:
    test_type: str  # "mann_whitney", "wilcoxon", "kruskal_wallis", "friedman"
    statistic: float
    p_value: float
    effect_size: float
    effect_size_name: str
    effect_size_ci: Optional[str] = None  # 效应量置信区间
    group_stats: Optional[pd.DataFrame] = None
    post_hoc: Optional[pd.DataFrame] = None
    warning: str = ""


def mann_whitney(df: pd.DataFrame, dv: str, iv: str,
                 exact: Optional[bool] = None) -> NonParamResult:
    """
    Mann-Whitney U 检验（两组独立样本的非参数比较）。
    效应量 r = Z / sqrt(N)，附带渐近置信区间。

    参数：
        exact: None=自动（n<10时尝试精确检验）,
               True=强制精确检验,
               False=强制渐近近似
    """
    groups = df[iv].dropna().unique()
    if len(groups) != 2:
        raise ValueError(f"Mann-Whitney U 检验需要恰好2个分组，但'{iv}'有{len(groups)}个水平。")

    g1 = pd.to_numeric(df[df[iv] == groups[0]][dv], errors="coerce").dropna()
    g2 = pd.to_numeric(df[df[iv] == groups[1]][dv], errors="coerce").dropna()

    n1, n2 = len(g1), len(g2)
    N = n1 + n2

    warning = ""
    use_exact = False

    # 自动决定是否使用精确检验
    if exact is None:
        use_exact = (n1 < 10 or n2 < 10)
    else:
        use_exact = exact

    method = "exact" if use_exact else "auto"
    try:
        u_stat, p_val = stats.mannwhitneyu(g1, g2, alternative="two-sided", method=method)
    except Exception:
        u_stat, p_val = stats.mannwhitneyu(g1, g2, alternative="two-sided")

    if use_exact:
        warning = f"✅ 使用精确Mann-Whitney U检验（各组n={n1},{n2}）。"
    elif min(n1, n2) < 10:
        warning = f"⚠ 样本量较小（各组n={n1},{n2}），p值基于渐近正态近似可能不准确。建议使用exact=True。"

    # 效应量 r = Z / sqrt(N)
    z = abs(stats.norm.ppf(max(p_val / 2, 1e-300)))
    r = z / np.sqrt(N)
    # r 的近似 95% CI (通过 Fisher z 变换)
    z_r = 0.5 * np.log((1 + r) / (1 - r)) if 0 < abs(r) < 1 else 0
    se_z = 1 / np.sqrt(N - 3) if N > 3 else 1
    z_low = z_r - 1.96 * se_z
    z_high = z_r + 1.96 * se_z
    r_low = (np.exp(2 * z_low) - 1) / (np.exp(2 * z_low) + 1)
    r_high = (np.exp(2 * z_high) - 1) / (np.exp(2 * z_high) + 1)

    group_stats = pd.DataFrame({
        "组别": [str(groups[0]), str(groups[1])],
        "N": [n1, n2],
        "中位数": [round(g1.median(), 2), round(g2.median(), 2)],
        "IQR": [
            f"{round(g1.quantile(0.25), 2)}-{round(g1.quantile(0.75), 2)}",
            f"{round(g2.quantile(0.25), 2)}-{round(g2.quantile(0.75), 2)}",
        ],
        "平均秩": [round(stats.rankdata(np.concatenate([g1, g2]))[:n1].mean(), 2),
                  round(stats.rankdata(np.concatenate([g1, g2]))[n1:].mean(), 2)],
    })

    return NonParamResult(
        test_type="mann_whitney",
        statistic=round(float(u_stat), 3),
        p_value=round(float(p_val), 4),
        effect_size=round(float(r), 3),
        effect_size_name="r (秩双列相关)",
        effect_size_ci=f"[{round(r_low, 3)}, {round(r_high, 3)}]",
        group_stats=group_stats,
        warning=warning,
    )


def wilcoxon_signed_rank(df: pd.DataFrame, col1: str, col2: str,
                         exact: Optional[bool] = None) -> NonParamResult:
    """Wilcoxon 符号秩检验（配对样本的非参数比较）。

    参数：
        exact: None=自动（n<10时尝试精确检验）,
               True=强制精确检验,
               False=强制渐近近似
    """
    x = pd.to_numeric(df[col1], errors="coerce")
    y = pd.to_numeric(df[col2], errors="coerce")
    mask = x.notna() & y.notna()
    x, y = x[mask], y[mask]

    n = len(x)
    use_exact = exact if exact is not None else (n < 10)
    warning = ""

    if use_exact:
        try:
            w_stat, p_val = stats.wilcoxon(x, y, method="exact")
            warning = f"✅ 使用精确Wilcoxon符号秩检验（n={n}）。"
        except Exception:
            w_stat, p_val = stats.wilcoxon(x, y)
            warning = f"⚠ 精确检验不可用（n={n}），使用渐近近似。"
    else:
        w_stat, p_val = stats.wilcoxon(x, y)
        if n < 10:
            warning = f"⚠ 样本量较小（n={n}），p值基于渐近正态近似可能不准确。建议使用exact=True。"

    # 配对秩双列相关系数 r
    # CI计算：Fisher z变换（与Mann-Whitney的r相同方法）
    diff = x - y
    nonzero = diff[diff != 0]
    if len(nonzero) > 0:
        r_plus = sum(stats.rankdata(abs(nonzero))[nonzero > 0])
        r_total = sum(stats.rankdata(abs(nonzero)))
        r = 2 * r_plus / r_total - 1 if r_total > 0 else 0
    else:
        r = 0.0

    # 匹配对秩双列相关 r 的近似 95% CI (Fisher z变换)
    z_r = 0.5 * np.log((1 + r) / (1 - r)) if 0 < abs(r) < 1 else 0
    se_z = 1 / np.sqrt(n - 3) if n > 3 else 1
    z_low = z_r - 1.96 * se_z
    z_high = z_r + 1.96 * se_z
    r_low = (np.exp(2 * z_low) - 1) / (np.exp(2 * z_low) + 1)
    r_high = (np.exp(2 * z_high) - 1) / (np.exp(2 * z_high) + 1)

    group_stats = pd.DataFrame({
        "测量": [col1, col2, "差值"],
        "N": [n, n, n],
        "中位数": [round(x.median(), 2), round(y.median(), 2), round(diff.median(), 2)],
        "IQR": [
            f"{round(x.quantile(0.25), 2)}-{round(x.quantile(0.75), 2)}",
            f"{round(y.quantile(0.25), 2)}-{round(y.quantile(0.75), 2)}",
            f"{round(diff.quantile(0.25), 2)}-{round(diff.quantile(0.75), 2)}",
        ],
    })

    return NonParamResult(
        test_type="wilcoxon",
        statistic=round(float(w_stat), 3),
        p_value=round(float(p_val), 4),
        effect_size=round(float(r), 3),
        effect_size_name="匹配对秩双列相关",
        effect_size_ci=f"[{round(r_low, 3)}, {round(r_high, 3)}]",
        group_stats=group_stats,
        warning=warning,
    )


def kruskal_wallis(
    df: pd.DataFrame,
    dv: str,
    iv: str,
    mc_method: str = "holm",
) -> NonParamResult:
    """
    Kruskal-Wallis H 检验（多组独立样本的非参数比较）+ Dunn 事后检验。

    参数：
        mc_method: 多重比较校正方法
                   "holm" — Holm-Bonferroni 校正（默认，逐步下降法）
                   "bonferroni" — 传统 Bonferroni 校正
                   "fdr" — Benjamini-Hochberg FDR 校正
                   "none" — 不校正
    """
    groups = []
    group_names = []
    clean = df[[dv, iv]].dropna()

    for name, group in clean.groupby(iv):
        gv = pd.to_numeric(group[dv], errors="coerce").dropna().values
        if len(gv) > 0:
            groups.append(gv)
            group_names.append(str(name))

    if len(groups) < 2:
        raise ValueError("Kruskal-Wallis 检验至少需要2个分组。")

    h_stat, p_val = stats.kruskal(*groups)

    # 小样本警告
    min_n = min(len(g) for g in groups)
    warning = ""
    if min_n < 10:
        warning = (
            f"⚠ 部分组样本量较小（最小n={min_n}），Kruskal-Wallis H统计量基于渐近χ²近似，"
            "p值可能不够精确。建议每组至少n≥10，或考虑使用置换检验（permutation test）。"
        )

    # 效应量 η²H（暂无标准置信区间计算方法）
    N = sum(len(g) for g in groups)
    eta_sq_h = max(0.0, (h_stat - len(groups) + 1) / (N - len(groups))) if N > len(groups) else 0.0
    # ε²（epsilon-squared）的置信区间暂无公认的标准计算方法；
    # 文献中常用的是 bootstrap 法，但该方法尚未在主流统计软件中标准化。
    # 使用者如需 CI，建议在分析后手动执行 bootstrap（b=5000，分位数法）。
    ci_note = "暂无置信区间（ε²/η²H的标准CI计算方法尚未确立，建议使用bootstrap法）"

    # Dunn 事后检验
    post_hoc = None
    if p_val < 0.05 and len(groups) > 2:
        post_hoc = _dunn_test(groups, group_names, mc_method)

    # 分组描述
    all_data_ranks = stats.rankdata(np.concatenate(groups))
    rows = []
    start = 0
    for i, name in enumerate(group_names):
        n_i = len(groups[i])
        rows.append({
            "组别": name,
            "N": n_i,
            "中位数": round(np.median(groups[i]), 2),
            "IQR": f"{round(np.percentile(groups[i], 25), 2)}-{round(np.percentile(groups[i], 75), 2)}",
            "平均秩": round(all_data_ranks[start:start + n_i].mean(), 2),
        })
        start += n_i

    return NonParamResult(
        test_type="kruskal_wallis",
        statistic=round(float(h_stat), 3),
        p_value=round(float(p_val), 4),
        effect_size=round(float(eta_sq_h), 3),
        effect_size_name="η²H",
        effect_size_ci=ci_note,
        group_stats=pd.DataFrame(rows),
        post_hoc=post_hoc,
        warning=warning,
    )


def friedman_test(df: pd.DataFrame, columns: list) -> NonParamResult:
    """Friedman 检验（重复测量的非参数比较）。

    Kendall's W 效应量的置信区间暂无标准计算方法，结果中 ci_lower/ci_upper 为 None。
    """
    data = df[columns].apply(pd.to_numeric, errors="coerce").dropna()
    n, k = data.shape
    if n < 3:
        raise ValueError("Friedman 检验至少需要3个有效样本。")

    chi2, p_val = stats.friedmanchisquare(*[data[c].values for c in columns])

    # Kendall's W（一致性系数）
    W = chi2 / (n * (k - 1)) if n * (k - 1) > 0 else 0.0

    warning = ""
    if n < 10:
        warning = (
            f"⚠ 样本量较小（n={n}），Friedman检验统计量基于渐近χ²近似，"
            "p值可能不够准确。建议样本量n≥15以保证近似有效性。"
        )
    # Kendall's W 暂无标准置信区间公式
    ci_note = "暂无置信区间（Kendall's W的标准CI计算方法未知）"

    return NonParamResult(
        test_type="friedman",
        statistic=round(float(chi2), 3),
        p_value=round(float(p_val), 4),
        effect_size=round(float(W), 3),
        effect_size_name="Kendall's W",
        effect_size_ci=ci_note,
        warning=warning,
    )


# ===========================================================================
# 多重比较校正
# ===========================================================================

def _apply_mc_correction(p_values: List[float], method: str) -> List[float]:
    """
    应用多重比较校正。

    参数：
        p_values: 原始未校正p值列表
        method: "holm" | "bonferroni" | "fdr" | "none"

    返回：校正后的p值列表（保持原始顺序）
    """
    n = len(p_values)
    if n == 0:
        return []

    if method == "none":
        return p_values

    # 创建带索引的列表以便排序后恢复顺序
    indexed = [(i, p) for i, p in enumerate(p_values)]
    sorted_p = sorted(indexed, key=lambda x: x[1])
    sorted_values = [p for _, p in sorted_p]

    if method == "bonferroni":
        corrected = [min(p * n, 1.0) for p in sorted_values]
    elif method == "holm":
        # Holm-Bonferroni: 逐步下降
        corrected = [0.0] * n
        for rank, (orig_idx, p) in enumerate(sorted_p):
            adjusted = p * (n - rank)
            # 确保单调性：当前校正值不小于前一个校正值
            if rank > 0:
                adjusted = max(adjusted, corrected[rank - 1])
            corrected[rank] = min(adjusted, 1.0)
    elif method == "fdr":
        # Benjamini-Hochberg
        corrected = [0.0] * n
        for rank, (orig_idx, p) in enumerate(sorted_p):
            adjusted = p * n / (rank + 1)
            if rank > 0:
                adjusted = max(adjusted, corrected[rank - 1])
            corrected[rank] = min(adjusted, 1.0)
    else:
        corrected = sorted_values

    # 恢复原始顺序
    result = [0.0] * n
    for (orig_idx, _), corrected_p in zip(sorted_p, corrected):
        result[orig_idx] = corrected_p

    return [round(p, 4) for p in result]


def _dunn_test(
    groups: list,
    names: list,
    mc_method: str = "holm",
) -> pd.DataFrame:
    """
    Dunn 事后多重比较。

    参数：
        mc_method: "holm" (默认), "bonferroni", "fdr", "none"
    """
    from itertools import combinations

    all_data = np.concatenate(groups)
    ranks = stats.rankdata(all_data)
    N = len(all_data)
    k = len(groups)

    start = 0
    rank_sums = []
    ns = []
    for g in groups:
        n = len(g)
        rank_sums.append(ranks[start:start + n].sum())
        ns.append(n)
        start += n

    # 计算所有比较的原始p值
    comparisons_data = []
    for (i, j) in combinations(range(k), 2):
        z_num = abs(rank_sums[i] / ns[i] - rank_sums[j] / ns[j])
        z_denom = np.sqrt((N * (N + 1) / 12) * (1 / ns[i] + 1 / ns[j]))
        z = z_num / z_denom if z_denom > 0 else 0.0
        p_uncorrected = 2 * stats.norm.sf(abs(z))
        comparisons_data.append((i, j, z, p_uncorrected))

    # 提取原始p值并校正
    raw_p_values = [cd[3] for cd in comparisons_data]
    corrected_ps = _apply_mc_correction(raw_p_values, mc_method)

    method_names = {
        "holm": "p (Holm-Bonferroni)",
        "bonferroni": "p (Bonferroni)",
        "fdr": "p (FDR-BH)",
        "none": "p (未校正)",
    }
    p_label = method_names.get(mc_method, f"p ({mc_method})")

    rows = []
    for idx, (i, j, z, p_unc) in enumerate(comparisons_data):
        rows.append({
            "比较": f"{names[i]} vs {names[j]}",
            "Z": round(float(z), 3),
            "p (未校正)": round(float(p_unc), 4),
            p_label: round(float(corrected_ps[idx]), 4),
        })

    return pd.DataFrame(rows)
