"""效度分析：CVI / AVE / Fornell-Larcker / HTMT / 效标 / 已知组别

v3.7 新增模块。EFA 仍在 factor_analysis.py，CFA 仍在 cfa.py（CFA 内部已整合 AVE/CR/HTMT）。
"""
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class ValidityResult:
    """效度分析结果"""
    test_type: str           # cvi / ave / discriminant_fl / discriminant_htmt / criterion_validity / known_groups_validity
    main_value: float = 0.0  # 主指标（CVI / AVE 均值 / HTMT 最大值 / r / 检验统计量）
    detail: Optional[pd.DataFrame] = None
    interpretation: str = ""
    warning: str = ""
    # 类型专属字段
    fornell_larcker_pass: Optional[bool] = None
    criterion_r: Optional[float] = None
    criterion_p: Optional[float] = None
    criterion_ci_lower: Optional[float] = None
    criterion_ci_upper: Optional[float] = None
    known_groups_stat: Optional[float] = None     # t 或 F
    known_groups_p: Optional[float] = None
    known_groups_test: str = ""                    # "ttest" / "anova"
    known_groups_effect_size: Optional[float] = None
    known_groups_effect_name: str = ""             # "Cohen's d" / "η²"
    n_cases: int = 0


# ===========================================================================
# 1. 内容效度指数 CVI
# ===========================================================================
def content_validity_index(ratings_df: pd.DataFrame) -> ValidityResult:
    """
    内容效度指数（Content Validity Index）。

    输入：题目 × 专家评分矩阵，每个评分为 1-4 的 Likert（1=不相关，4=非常相关）。
    - 行：题目（index 为题目名）
    - 列：专家（每列一个专家）

    输出：
    - I-CVI 每题：≥3 分的专家比例（推荐 ≥ 0.78，n_experts ≥ 6 时）
    - S-CVI/Ave：所有 I-CVI 的均值（推荐 ≥ 0.90）
    - 修正版 κ*（Polit & Beck 2007）：扣除偶然一致性
    """
    if ratings_df.empty:
        raise ValueError("评分矩阵为空。")

    n_experts = ratings_df.shape[1]
    if n_experts < 3:
        raise ValueError(f"CVI 至少需要 3 位专家，当前 {n_experts}。建议 ≥ 6。")

    # 转数值
    rd = ratings_df.apply(pd.to_numeric, errors="coerce")
    if rd.isna().any().any():
        raise ValueError("评分矩阵包含无效或缺失值。请确保所有评分为 1-4 整数。")

    # I-CVI：每题给 3 或 4 分的专家比例
    high_relevance = (rd >= 3).sum(axis=1)
    i_cvi = high_relevance / n_experts

    # 偶然一致性 Pc = (n_experts! / (A!(n-A)!)) × 0.5^n_experts
    from math import comb
    pc = pd.Series(index=rd.index, dtype=float)
    for item in rd.index:
        a = int(high_relevance[item])
        pc[item] = comb(n_experts, a) * (0.5 ** n_experts)

    # 修正 κ* = (I-CVI - Pc) / (1 - Pc)
    kappa_star = pd.Series(index=rd.index, dtype=float)
    for item in rd.index:
        if pc[item] < 1.0:
            kappa_star[item] = (i_cvi[item] - pc[item]) / (1 - pc[item])
        else:
            kappa_star[item] = 0.0

    s_cvi_ave = float(i_cvi.mean())

    detail = pd.DataFrame({
        "题目": rd.index,
        "高相关专家数": high_relevance.values,
        "I-CVI": i_cvi.round(3).values,
        "Pc": pc.round(4).values,
        "修正κ*": kappa_star.round(3).values,
        "评估": [
            "优秀" if v >= 0.78 else ("可接受" if v >= 0.70 else "需修订")
            for v in i_cvi
        ],
    })

    low_items = detail[detail["I-CVI"] < 0.78]["题目"].tolist()
    warning = ""
    if low_items:
        warning += f"⚠ 以下题目 I-CVI<0.78，建议修订或删除：{', '.join(low_items[:5])}"
        if len(low_items) > 5:
            warning += f" 等 {len(low_items)} 项"
        warning += "。"
    if s_cvi_ave < 0.90:
        warning += f"⚠ S-CVI/Ave={s_cvi_ave:.3f}<0.90，整体内容效度需改进。"

    interpretation = f"S-CVI/Ave = {s_cvi_ave:.3f}，{n_experts} 位专家评估。"
    if s_cvi_ave >= 0.90:
        interpretation += "整体内容效度良好。"

    return ValidityResult(
        test_type="cvi",
        main_value=round(s_cvi_ave, 3),
        detail=detail,
        interpretation=interpretation,
        warning=warning,
        n_cases=n_experts,
    )


# ===========================================================================
# 2. 平均方差抽取量 AVE
# ===========================================================================
def average_variance_extracted(loadings_df: pd.DataFrame) -> ValidityResult:
    """
    AVE（聚合效度）：每个因子下题目标准化载荷平方的均值。

    输入 loadings_df: 含列 ["因子", "题目", "标准化载荷"]（与 CFAResult.loadings 一致）。
    若 CFA 使用不同列名（如英文），自动尝试映射。

    AVE_f = mean(λᵢ²)，推荐 ≥ 0.50（Fornell & Larcker 1981）。
    """
    df = loadings_df.copy()
    # 列名兼容
    rename_map = {}
    for c in df.columns:
        cl = str(c).lower()
        if cl in ("factor", "因子"):
            rename_map[c] = "因子"
        elif cl in ("item", "题目", "indicator"):
            rename_map[c] = "题目"
        elif cl in ("loading", "stdloading", "标准化载荷", "std_loading"):
            rename_map[c] = "标准化载荷"
    if rename_map:
        df = df.rename(columns=rename_map)

    required = {"因子", "题目", "标准化载荷"}
    if not required.issubset(df.columns):
        raise ValueError(f"loadings_df 需含列 {required}，实际：{list(df.columns)}")

    df["标准化载荷"] = pd.to_numeric(df["标准化载荷"], errors="coerce")
    df = df.dropna(subset=["标准化载荷"])

    ave_per_factor = df.groupby("因子").apply(
        lambda g: (g["标准化载荷"] ** 2).mean()
    ).round(3)

    detail = pd.DataFrame({
        "因子": ave_per_factor.index,
        "AVE": ave_per_factor.values,
        "√AVE": np.sqrt(ave_per_factor.values).round(3),
        "评估": ["合格" if v >= 0.50 else "不达标" for v in ave_per_factor.values],
    })

    mean_ave = float(ave_per_factor.mean())
    low_factors = detail[detail["AVE"] < 0.50]["因子"].tolist()
    warning = ""
    if low_factors:
        warning = f"⚠ 因子 {', '.join(map(str, low_factors))} 的 AVE<0.50，聚合效度不足。"

    return ValidityResult(
        test_type="ave",
        main_value=round(mean_ave, 3),
        detail=detail,
        interpretation=f"AVE 均值={mean_ave:.3f}，{len(ave_per_factor)} 个因子。",
        warning=warning,
        n_cases=len(df),
    )


# ===========================================================================
# 3. 区分效度（Fornell-Larcker）
# ===========================================================================
def discriminant_fornell_larcker(ave_dict: Dict[str, float],
                                  factor_corr_df: pd.DataFrame) -> ValidityResult:
    """
    Fornell-Larcker 准则：每个因子 √AVE 应大于该因子与所有其他因子的相关绝对值。

    输入：
    - ave_dict: {因子: AVE}
    - factor_corr_df: 因子相关矩阵（DataFrame，行列均为因子名）

    输出 detail：对角线填 √AVE，非对角填因子相关，违例位置标记。
    """
    factors = list(ave_dict.keys())
    if not all(f in factor_corr_df.index and f in factor_corr_df.columns for f in factors):
        raise ValueError("factor_corr_df 的行列必须涵盖 ave_dict 中所有因子。")

    sqrt_ave = {f: float(np.sqrt(ave_dict[f])) for f in factors}

    # 构建 FL 矩阵：对角线 √AVE，下三角因子相关
    fl_matrix = pd.DataFrame(index=factors, columns=factors, dtype=object)
    violations = []
    for i, f_i in enumerate(factors):
        for j, f_j in enumerate(factors):
            if i == j:
                fl_matrix.loc[f_i, f_j] = f"{sqrt_ave[f_i]:.3f}"
            elif i > j:
                r = float(factor_corr_df.loc[f_i, f_j])
                fl_matrix.loc[f_i, f_j] = f"{r:.3f}"
                # 检验：sqrt(AVE) > |r| ?
                if abs(r) >= sqrt_ave[f_i] or abs(r) >= sqrt_ave[f_j]:
                    violations.append((f_i, f_j, r))
                    fl_matrix.loc[f_i, f_j] = f"{r:.3f} ⚠"
            else:
                fl_matrix.loc[f_i, f_j] = ""

    passed = len(violations) == 0
    warning = ""
    if violations:
        worst = max(violations, key=lambda x: abs(x[2]))
        warning = (f"⚠ 区分效度未通过：{worst[0]} vs {worst[1]} 相关 r={worst[2]:.3f} "
                   f"≥ √AVE，存在共线。共 {len(violations)} 处违例。")

    return ValidityResult(
        test_type="discriminant_fl",
        main_value=1.0 if passed else 0.0,
        detail=fl_matrix.reset_index().rename(columns={"index": "因子"}),
        interpretation="对角线为 √AVE，下三角为因子相关。√AVE 应大于该行/列因子相关。",
        warning=warning,
        fornell_larcker_pass=passed,
        n_cases=len(factors),
    )


# ===========================================================================
# 4. 区分效度（HTMT）
# ===========================================================================
def discriminant_htmt(df: pd.DataFrame, factors: Dict[str, List[str]],
                       threshold: float = 0.85) -> ValidityResult:
    """
    Heterotrait-Monotrait Ratio (HTMT, Henseler et al. 2015)。

    HTMT_AB = mean(异质相关) / sqrt(mean(单质相关_A) × mean(单质相关_B))
    - 异质：因子A的题目和因子B的题目之间相关
    - 单质：因子内题目两两相关（不含对角）

    阈值：≤ 0.85（严格）或 ≤ 0.90（宽松）。超过提示区分效度不足。
    """
    factor_names = list(factors.keys())
    if len(factor_names) < 2:
        raise ValueError("HTMT 至少需要 2 个因子。")

    all_items = [it for items in factors.values() for it in items]
    data = df[all_items].apply(pd.to_numeric, errors="coerce").dropna()
    n_cases = len(data)
    corr = data.corr().abs()

    htmt_matrix = pd.DataFrame(index=factor_names, columns=factor_names, dtype=float)
    violations = []
    for f_a in factor_names:
        items_a = factors[f_a]
        if len(items_a) < 2:
            continue
        # 单质平均（A 内部）：上三角
        ma = corr.loc[items_a, items_a].values
        i_idx = np.triu_indices_from(ma, k=1)
        mean_mono_a = float(np.mean(ma[i_idx])) if len(i_idx[0]) > 0 else np.nan

        for f_b in factor_names:
            if f_a == f_b:
                htmt_matrix.loc[f_a, f_b] = np.nan
                continue
            items_b = factors[f_b]
            if len(items_b) < 2:
                continue
            mb = corr.loc[items_b, items_b].values
            j_idx = np.triu_indices_from(mb, k=1)
            mean_mono_b = float(np.mean(mb[j_idx])) if len(j_idx[0]) > 0 else np.nan

            # 异质平均（A vs B）
            mab = corr.loc[items_a, items_b].values
            mean_hetero = float(np.mean(mab))

            denom = np.sqrt(mean_mono_a * mean_mono_b)
            htmt = mean_hetero / denom if denom > 0 else np.nan
            htmt_matrix.loc[f_a, f_b] = round(htmt, 3)

            if not np.isnan(htmt) and htmt > threshold and f_a < f_b:
                violations.append((f_a, f_b, htmt))

    max_htmt = float(np.nanmax(htmt_matrix.values))
    warning = ""
    if violations:
        worst = max(violations, key=lambda x: x[2])
        warning = (f"⚠ HTMT 区分效度违例 {len(violations)} 处，"
                   f"最严重：{worst[0]} vs {worst[1]} HTMT={worst[2]:.3f}>{threshold}。")
    elif max_htmt > threshold:
        warning = f"⚠ 最大 HTMT={max_htmt:.3f} 超过阈值 {threshold}。"

    return ValidityResult(
        test_type="discriminant_htmt",
        main_value=round(max_htmt, 3),
        detail=htmt_matrix.reset_index().rename(columns={"index": "因子"}),
        interpretation=f"最大 HTMT={max_htmt:.3f}（阈值 {threshold}）。",
        warning=warning,
        fornell_larcker_pass=(len(violations) == 0),
        n_cases=n_cases,
    )


# ===========================================================================
# 5. 效标效度（同时 / 预测）
# ===========================================================================
def criterion_validity(df: pd.DataFrame, scale_items: list, criterion_col: str,
                        kind: str = "concurrent") -> ValidityResult:
    """
    效标效度：量表总分与外部效标的 Pearson 相关。

    kind="concurrent" 同时效度（外部效标同期测量）
    kind="predictive" 预测效度（外部效标延迟测量）

    返回 r + 95% CI（Fisher Z 转换）+ p 值。
    """
    if kind not in ("concurrent", "predictive"):
        raise ValueError("kind 须为 'concurrent' 或 'predictive'。")

    cols = list(scale_items) + [criterion_col]
    data = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    n_cases = len(data)
    if n_cases < 10:
        raise ValueError(f"样本量过小（n={n_cases}），效标效度估计不稳定。")

    scale_total = data[scale_items].sum(axis=1)
    crit = data[criterion_col]

    r, p = stats.pearsonr(scale_total, crit)
    r = float(r)

    # Fisher Z CI
    if abs(r) < 1.0 and n_cases > 3:
        z = 0.5 * np.log((1 + r) / (1 - r))
        se = 1.0 / np.sqrt(n_cases - 3)
        ci_lower = (np.exp(2 * (z - 1.96 * se)) - 1) / (np.exp(2 * (z - 1.96 * se)) + 1)
        ci_upper = (np.exp(2 * (z + 1.96 * se)) - 1) / (np.exp(2 * (z + 1.96 * se)) + 1)
    else:
        ci_lower = ci_upper = r

    r = round(r, 3)
    detail = pd.DataFrame([{
        "效标": criterion_col,
        "类型": "同时效度" if kind == "concurrent" else "预测效度",
        "r": r,
        "95% CI": f"[{ci_lower:.3f}, {ci_upper:.3f}]",
        "p": round(float(p), 4),
        "n": n_cases,
    }])

    warning = ""
    if abs(r) < 0.30:
        warning = f"⚠ 与效标的相关 r={r} 偏低，效度不足。"
    elif abs(r) < 0.50:
        warning = f"r={r}：中等效标效度。"

    return ValidityResult(
        test_type="criterion_validity",
        main_value=r,
        detail=detail,
        interpretation=f"量表与{criterion_col}相关 r={r}, p={p:.4f}, n={n_cases}。",
        warning=warning,
        criterion_r=r,
        criterion_p=round(float(p), 4),
        criterion_ci_lower=round(float(ci_lower), 3),
        criterion_ci_upper=round(float(ci_upper), 3),
        n_cases=n_cases,
    )


# ===========================================================================
# 6. 已知组别效度（Known-groups）
# ===========================================================================
def known_groups_validity(df: pd.DataFrame, scale_items: list,
                           group_col: str) -> ValidityResult:
    """
    已知组别效度：量表是否能区分预先已知差异的群体。

    自动选择检验：
    - 2 组 → 独立样本 t 检验，效应量 Cohen's d
    - ≥3 组 → 单因素 ANOVA，效应量 η²

    返回 t/F + p + 效应量。
    """
    cols = list(scale_items) + [group_col]
    data = df[cols].dropna()
    data[scale_items] = data[scale_items].apply(pd.to_numeric, errors="coerce")
    data = data.dropna()
    n_cases = len(data)

    scale_total = data[scale_items].sum(axis=1)
    groups = data[group_col]
    group_levels = groups.unique()
    k = len(group_levels)

    if k < 2:
        raise ValueError(f"分组变量「{group_col}」只有 {k} 个组，需 ≥2。")

    if k == 2:
        g1 = scale_total[groups == group_levels[0]]
        g2 = scale_total[groups == group_levels[1]]
        if len(g1) < 3 or len(g2) < 3:
            raise ValueError(f"每组样本量过少（{len(g1)}, {len(g2)}）。")
        t_stat, p = stats.ttest_ind(g1, g2, equal_var=False)
        # Cohen's d (pooled SD)
        n1, n2 = len(g1), len(g2)
        pooled_sd = np.sqrt(((n1 - 1) * g1.var(ddof=1) + (n2 - 1) * g2.var(ddof=1)) / (n1 + n2 - 2))
        d = (g1.mean() - g2.mean()) / pooled_sd if pooled_sd > 0 else 0.0
        d = abs(float(d))
        effect_size = round(d, 3)
        effect_name = "Cohen's d"
        test_method = "ttest"
        stat_value = round(float(t_stat), 3)

        detail_rows = []
        for lv in group_levels:
            sub = scale_total[groups == lv]
            detail_rows.append({"组": lv, "n": len(sub),
                                "M": round(sub.mean(), 3), "SD": round(sub.std(ddof=1), 3)})
        detail = pd.DataFrame(detail_rows)
    else:
        groups_list = [scale_total[groups == lv] for lv in group_levels]
        if any(len(g) < 3 for g in groups_list):
            raise ValueError("某组样本量 <3。")
        f_stat, p = stats.f_oneway(*groups_list)
        # η² = SS_between / SS_total
        grand = scale_total.mean()
        ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups_list)
        ss_total = ((scale_total - grand) ** 2).sum()
        eta_sq = ss_between / ss_total if ss_total > 0 else 0.0
        effect_size = round(float(eta_sq), 3)
        effect_name = "η²"
        test_method = "anova"
        stat_value = round(float(f_stat), 3)

        detail_rows = []
        for lv, g in zip(group_levels, groups_list):
            detail_rows.append({"组": lv, "n": len(g),
                                "M": round(g.mean(), 3), "SD": round(g.std(ddof=1), 3)})
        detail = pd.DataFrame(detail_rows)

    p = float(p)

    # 效应量解读
    if test_method == "ttest":
        if effect_size >= 0.80:
            ef_level = "大"
        elif effect_size >= 0.50:
            ef_level = "中"
        elif effect_size >= 0.20:
            ef_level = "小"
        else:
            ef_level = "极小"
    else:
        if effect_size >= 0.14:
            ef_level = "大"
        elif effect_size >= 0.06:
            ef_level = "中"
        elif effect_size >= 0.01:
            ef_level = "小"
        else:
            ef_level = "极小"

    warning = ""
    if p >= 0.05:
        warning = f"⚠ 组间差异不显著（p={p:.4f}），已知组别效度证据不足。"
    elif effect_size < (0.20 if test_method == "ttest" else 0.01):
        warning = f"⚠ 效应量{effect_name}={effect_size}（{ef_level}），实际意义有限。"

    interp_test = "独立样本 t 检验" if test_method == "ttest" else "单因素 ANOVA"
    interp = (f"{interp_test}：{'t' if test_method == 'ttest' else 'F'}={stat_value}, "
              f"p={p:.4f}, {effect_name}={effect_size}（{ef_level}）。")

    return ValidityResult(
        test_type="known_groups_validity",
        main_value=effect_size,
        detail=detail,
        interpretation=interp,
        warning=warning,
        known_groups_stat=stat_value,
        known_groups_p=round(p, 4),
        known_groups_test=test_method,
        known_groups_effect_size=effect_size,
        known_groups_effect_name=effect_name,
        n_cases=n_cases,
    )
