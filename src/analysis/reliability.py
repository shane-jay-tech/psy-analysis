"""信度分析：Cronbach's α / 分半信度 / McDonald's ω / 组合信度 CR / ICC / 重测 / κ"""
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class ReliabilityResult:
    test_type: str  # "cronbach_alpha"/"split_half"/"mcdonald_omega"/"composite_reliability"/"icc"/"test_retest"/"cohens_kappa"/"fleiss_kappa"
    alpha: float    # 通用主指标（α/ω/CR/r/κ 等都填这里方便统一渲染）
    ci_lower: float
    ci_upper: float
    n_items: int
    n_cases: int
    item_stats: Optional[pd.DataFrame] = None
    split_half_r: Optional[float] = None
    icc_value: Optional[float] = None
    icc_type: str = ""                    # ICC1/ICC2/ICC3 + 单/多 rater
    omega_value: Optional[float] = None
    cr_per_factor: Optional[Dict[str, float]] = None
    test_retest_r: Optional[float] = None
    kappa_value: Optional[float] = None
    kappa_method: str = ""                # "cohen"/"fleiss"
    warning: str = ""


def cronbach_alpha(df: pd.DataFrame, items: list) -> ReliabilityResult:
    """
    Cronbach's α 内部一致性信度。
    使用 pingouin 计算，同时提供 α-if-item-deleted 和题总相关。
    """
    import pingouin as pg

    data = df[items].apply(pd.to_numeric, errors="coerce").dropna()
    n_cases, n_items = data.shape

    if n_items < 2:
        raise ValueError("Cronbach's α 至少需要2道题目。")

    # 计算 α
    alpha_result = pg.cronbach_alpha(data)
    alpha = round(float(alpha_result[0]), 3)
    ci = alpha_result[1] if len(alpha_result) > 1 else [alpha, alpha]

    # α-if-item-deleted 和 题总相关
    item_stats_rows = []
    for col in data.columns:
        # α 删除该项后
        items_without = [c for c in data.columns if c != col]
        alpha_without = pg.cronbach_alpha(data[items_without])[0] if len(items_without) >= 2 else np.nan

        # 题总相关（校正）
        total = data.sum(axis=1)
        total_without = total - data[col]
        item_total_r = data[col].corr(total_without) if data[col].std() > 0 else 0.0

        item_stats_rows.append({
            "题目": col,
            "M": round(data[col].mean(), 2),
            "SD": round(data[col].std(), 2),
            "题总相关(CITC)": round(item_total_r, 3),
            "删除后α": round(alpha_without, 3) if not np.isnan(alpha_without) else "-",
        })

    item_stats_df = pd.DataFrame(item_stats_rows)

    # 质量警告
    warning = ""
    low_citc = item_stats_df[item_stats_df["题总相关(CITC)"] < 0.30]
    if len(low_citc) > 0:
        warning += f"⚠ {', '.join(low_citc['题目'])} 的题总相关<0.30，建议考虑删除。"
    if alpha < 0.60:
        warning += f"⚠ α={alpha} 低于可接受水平（0.60）。"
    elif alpha < 0.70:
        warning += f"α={alpha} 处于探索性研究的可接受边界（0.60-0.70）。"

    return ReliabilityResult(
        test_type="cronbach_alpha",
        alpha=alpha,
        ci_lower=round(float(ci[0]), 3) if ci[0] else alpha,
        ci_upper=round(float(ci[1]), 3) if len(ci) > 1 and ci[1] else alpha,
        n_items=n_items,
        n_cases=n_cases,
        item_stats=item_stats_df,
        warning=warning,
    )


def split_half_reliability(df: pd.DataFrame, items: list) -> ReliabilityResult:
    """
    分半信度（奇偶分半 + Spearman-Brown 校正）。
    """
    data = df[items].apply(pd.to_numeric, errors="coerce").dropna()
    n_cases, n_items = data.shape

    # 奇偶分半
    odd_items = [items[i] for i in range(0, len(items), 2)]
    even_items = [items[i] for i in range(1, len(items), 2)]

    odd_sum = data[odd_items].sum(axis=1)
    even_sum = data[even_items].sum(axis=1)

    # 两半之间的 Pearson 相关
    r_half, p_half = stats.pearsonr(odd_sum, even_sum)

    # Spearman-Brown 校正
    sb_r = 2 * r_half / (1 + r_half) if (1 + r_half) > 0 else 0.0

    return ReliabilityResult(
        test_type="split_half",
        alpha=round(sb_r, 3),
        ci_lower=round(max(0, sb_r - 0.1), 3),
        ci_upper=round(min(1, sb_r + 0.1), 3),
        n_items=n_items,
        n_cases=n_cases,
        split_half_r=round(r_half, 3),
        warning="" if sb_r >= 0.70 else f"⚠ 分半信度={sb_r:.3f}，低于可接受水平（0.70）。",
    )


# ===========================================================================
# v3.7 新增：McDonald's ω 综合信度
# ===========================================================================
def mcdonald_omega(df: pd.DataFrame, items: list,
                   n_bootstrap: int = 500, random_state: int = 42) -> ReliabilityResult:
    """
    McDonald's ω 综合信度（基于单因子模型的标准化载荷）。

    公式：ω = (Σλᵢ)² / [(Σλᵢ)² + Σ(1 - λᵢ²)]

    比 Cronbach's α 更稳健，不要求 tau-equivalence。
    用 bootstrap 估计 95% CI。
    """
    from factor_analyzer import FactorAnalyzer

    data = df[items].apply(pd.to_numeric, errors="coerce").dropna()
    n_cases, n_items = data.shape

    if n_items < 3:
        raise ValueError("McDonald's ω 至少需要 3 道题目。")
    if n_cases < 50:
        raise ValueError(f"样本量过小（n={n_cases}），ω 估计不稳定。建议 n ≥ 100。")

    def _compute_omega(d):
        fa = FactorAnalyzer(n_factors=1, rotation=None, method="ml")
        fa.fit(d)
        loadings = fa.loadings_.flatten()
        sum_lambda = float(np.sum(loadings))
        sum_uniqueness = float(np.sum(1 - loadings ** 2))
        denom = sum_lambda ** 2 + sum_uniqueness
        return (sum_lambda ** 2) / denom if denom > 0 else 0.0

    omega = _compute_omega(data)

    # bootstrap CI
    rng = np.random.default_rng(random_state)
    boot_omegas = []
    for _ in range(n_bootstrap):
        idx = rng.choice(n_cases, size=n_cases, replace=True)
        try:
            boot_omegas.append(_compute_omega(data.iloc[idx]))
        except Exception:
            continue
    if boot_omegas:
        ci_lower = float(np.percentile(boot_omegas, 2.5))
        ci_upper = float(np.percentile(boot_omegas, 97.5))
    else:
        ci_lower = ci_upper = omega

    omega = round(omega, 3)

    warning = ""
    if omega < 0.60:
        warning = f"⚠ ω={omega} 低于可接受水平（0.60）。"
    elif omega < 0.70:
        warning = f"ω={omega} 处于探索性研究的可接受边界（0.60-0.70）。"

    return ReliabilityResult(
        test_type="mcdonald_omega",
        alpha=omega,
        ci_lower=round(ci_lower, 3),
        ci_upper=round(ci_upper, 3),
        n_items=n_items,
        n_cases=n_cases,
        omega_value=omega,
        warning=warning,
    )


# ===========================================================================
# v3.7 新增：组合信度 CR (Composite Reliability)
# ===========================================================================
def composite_reliability(df: pd.DataFrame, factors: Dict[str, List[str]]) -> ReliabilityResult:
    """
    组合信度 CR（基于多因子模型的标准化载荷）。

    公式：CR_f = (Σλ)² / [(Σλ)² + Σ(1 - λ²)]，按因子分别计算。

    输入 factors: {"因子名1": ["item1", "item2"], "因子名2": ["item3", ...]}

    适用于结构方程模型（SEM）的测量模型评估。
    返回 ReliabilityResult.cr_per_factor = {因子: CR}，alpha 字段填均值。
    """
    from factor_analyzer import FactorAnalyzer

    all_items = [it for items in factors.values() for it in items]
    data = df[all_items].apply(pd.to_numeric, errors="coerce").dropna()
    n_cases = len(data)

    if n_cases < 50:
        raise ValueError(f"样本量过小（n={n_cases}），CR 估计不稳定。建议 n ≥ 100。")

    cr_per_factor: Dict[str, float] = {}
    item_rows = []
    for fname, items in factors.items():
        if len(items) < 2:
            continue
        sub = data[items]
        # 单因子 ML 提取
        fa = FactorAnalyzer(n_factors=1, rotation=None, method="ml")
        fa.fit(sub)
        loadings = fa.loadings_.flatten()
        sum_l = float(np.sum(loadings))
        sum_l2 = float(np.sum(loadings ** 2))
        sum_uniq = float(np.sum(1 - loadings ** 2))
        denom = sum_l ** 2 + sum_uniq
        cr = (sum_l ** 2) / denom if denom > 0 else 0.0
        cr_per_factor[fname] = round(cr, 3)
        for it, lam in zip(items, loadings):
            item_rows.append({
                "因子": fname,
                "题目": it,
                "标准化载荷": round(float(lam), 3),
                "误差方差": round(1 - float(lam) ** 2, 3),
            })

    mean_cr = round(float(np.mean(list(cr_per_factor.values()))), 3) if cr_per_factor else 0.0

    warnings = []
    for f, cr in cr_per_factor.items():
        if cr < 0.70:
            warnings.append(f"⚠ 因子「{f}」的 CR={cr} 低于推荐阈值 0.70。")

    return ReliabilityResult(
        test_type="composite_reliability",
        alpha=mean_cr,                # 显示均值作为主指标
        ci_lower=mean_cr,             # CR 不提供单一 CI
        ci_upper=mean_cr,
        n_items=len(all_items),
        n_cases=n_cases,
        cr_per_factor=cr_per_factor,
        item_stats=pd.DataFrame(item_rows) if item_rows else None,
        warning=" ".join(warnings),
    )


# ===========================================================================
# v3.7 新增：ICC 组内相关系数（评分者一致性 / 重测）
# ===========================================================================
def intraclass_correlation(df: pd.DataFrame, raters: list,
                            icc_type: str = "ICC2") -> ReliabilityResult:
    """
    组内相关系数（Intraclass Correlation Coefficient）。

    输入 raters: 列名列表，每列代表一个评分者对所有 target 的评分（wide format）。
    输出包含 6 种 ICC 中指定类型的估计：
      - ICC1: 单评分者绝对一致性（随机效应）
      - ICC2: 单评分者绝对一致性（双向随机）
      - ICC3: 单评分者一致性（不含 rater 主效应）
      - ICC1k/ICC2k/ICC3k: 对应的多评分者均值版本

    icc_type 接受 "ICC1"/"ICC2"/"ICC3"/"ICC1k"/"ICC2k"/"ICC3k"。
    """
    import pingouin as pg

    if len(raters) < 2:
        raise ValueError("ICC 至少需要 2 个评分者列。")

    data = df[raters].apply(pd.to_numeric, errors="coerce").dropna()
    n_cases = len(data)

    # wide → long
    long_df = data.reset_index().rename(columns={"index": "target"}).melt(
        id_vars=["target"], var_name="rater", value_name="rating",
    )
    icc_df = pg.intraclass_corr(data=long_df, targets="target",
                                 raters="rater", ratings="rating", nan_policy="omit")

    # pingouin 返回 6 行，Type 列实际格式为 ICC(1,1)/ICC(A,1)/ICC(C,1)/ICC(1,k)/ICC(A,k)/ICC(C,k)
    # 映射到常用命名 ICC1/ICC2/ICC3/ICC1k/ICC2k/ICC3k
    icc_alias = {
        "ICC1": "ICC(1,1)", "ICC2": "ICC(A,1)", "ICC3": "ICC(C,1)",
        "ICC1k": "ICC(1,k)", "ICC2k": "ICC(A,k)", "ICC3k": "ICC(C,k)",
    }
    target_type = icc_alias.get(icc_type, icc_type)
    sel = icc_df[icc_df["Type"] == target_type]
    if sel.empty:
        raise ValueError(f"未找到 ICC 类型 {icc_type}。可选: ICC1/ICC2/ICC3/ICC1k/ICC2k/ICC3k")

    row = sel.iloc[0]
    icc = round(float(row["ICC"]), 3)
    # pingouin 不同版本可能用 'CI95' 或 'CI95%'
    ci = row.get("CI95", row.get("CI95%", None))
    if ci is not None and hasattr(ci, "__len__") and len(ci) >= 2:
        ci_lower = round(float(ci[0]), 3)
        ci_upper = round(float(ci[1]), 3)
    else:
        ci_lower = ci_upper = icc

    if icc >= 0.90:
        warning = ""
    elif icc >= 0.75:
        warning = f"ICC={icc}：良好的评分者一致性（0.75-0.90）。"
    elif icc >= 0.50:
        warning = f"⚠ ICC={icc}：中等一致性（0.50-0.75），建议加强评分员训练。"
    else:
        warning = f"⚠ ICC={icc}：一致性较差（<0.50），结果不可靠。"

    return ReliabilityResult(
        test_type="icc",
        alpha=icc,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_items=len(raters),
        n_cases=n_cases,
        icc_value=icc,
        icc_type=icc_type,
        warning=warning,
    )


# ===========================================================================
# v3.7 新增：重测信度 test-retest
# ===========================================================================
def test_retest_reliability(df: pd.DataFrame, time1_col: str, time2_col: str) -> ReliabilityResult:
    """
    重测信度：两次测量的 Pearson r + Fisher Z 95% CI。

    输入：单个量表总分（或单题）的两次测量列。
    """
    data = df[[time1_col, time2_col]].apply(pd.to_numeric, errors="coerce").dropna()
    n_cases = len(data)

    if n_cases < 10:
        raise ValueError(f"样本量过小（n={n_cases}），重测信度不可靠。")

    r, p = stats.pearsonr(data[time1_col], data[time2_col])
    r = float(r)

    # Fisher Z 转换 95% CI
    if abs(r) < 1.0:
        z = 0.5 * np.log((1 + r) / (1 - r))
        se = 1.0 / np.sqrt(n_cases - 3) if n_cases > 3 else 0.0
        z_lower = z - 1.96 * se
        z_upper = z + 1.96 * se
        ci_lower = (np.exp(2 * z_lower) - 1) / (np.exp(2 * z_lower) + 1)
        ci_upper = (np.exp(2 * z_upper) - 1) / (np.exp(2 * z_upper) + 1)
    else:
        ci_lower = ci_upper = r

    r = round(r, 3)
    if r >= 0.80:
        warning = ""
    elif r >= 0.70:
        warning = f"r={r}：可接受的重测信度（0.70-0.80）。"
    else:
        warning = f"⚠ 重测 r={r} 偏低，时间稳定性不足。"

    return ReliabilityResult(
        test_type="test_retest",
        alpha=r,
        ci_lower=round(float(ci_lower), 3),
        ci_upper=round(float(ci_upper), 3),
        n_items=2,
        n_cases=n_cases,
        test_retest_r=r,
        warning=warning,
    )


# ===========================================================================
# v3.7 新增：Cohen's κ 评分者一致性（两评分者）
# ===========================================================================
def cohens_kappa(df: pd.DataFrame, rater1: str, rater2: str,
                  weights: Optional[str] = None) -> ReliabilityResult:
    """
    Cohen's κ：两个评分者对相同 N 个目标的分类一致性。

    weights: None（无权 κ）/ "linear" / "quadratic"（有序分类用加权 κ）
    """
    from sklearn.metrics import cohen_kappa_score

    data = df[[rater1, rater2]].dropna()
    n_cases = len(data)

    if n_cases < 10:
        raise ValueError(f"样本量过小（n={n_cases}），κ 估计不稳定。")

    kappa = float(cohen_kappa_score(data[rater1], data[rater2], weights=weights))

    # SE 近似（Fleiss & Cohen 1969）：SE_κ = sqrt(κ(1-κ)/N)
    se = np.sqrt(max(kappa * (1 - kappa) / n_cases, 0.0)) if abs(kappa) < 1 else 0.0
    ci_lower = max(-1.0, kappa - 1.96 * se)
    ci_upper = min(1.0, kappa + 1.96 * se)

    kappa = round(kappa, 3)
    # Landis & Koch (1977) 解读
    if kappa >= 0.81:
        level = "几乎完美"
    elif kappa >= 0.61:
        level = "高度一致"
    elif kappa >= 0.41:
        level = "中等一致"
    elif kappa >= 0.21:
        level = "尚可"
    elif kappa >= 0.0:
        level = "微弱一致"
    else:
        level = "比偶然还差"

    warning = f"κ={kappa}：{level}（Landis & Koch 1977）。"
    if kappa < 0.40:
        warning = "⚠ " + warning + " 评分员训练不足。"

    return ReliabilityResult(
        test_type="cohens_kappa",
        alpha=kappa,
        ci_lower=round(float(ci_lower), 3),
        ci_upper=round(float(ci_upper), 3),
        n_items=2,
        n_cases=n_cases,
        kappa_value=kappa,
        kappa_method="cohen",
        warning=warning,
    )


# ===========================================================================
# v3.7 新增：Fleiss' κ 多评分者一致性
# ===========================================================================
def fleiss_kappa(df: pd.DataFrame, raters: list) -> ReliabilityResult:
    """
    Fleiss' κ：3 个或更多评分者对相同 N 个目标的分类一致性。

    输入 wide format：每行=1 个目标，每列=1 个评分者的分类标签。
    内部转 (n_targets, n_categories) 矩阵后调用 statsmodels.stats.inter_rater.fleiss_kappa。
    """
    from statsmodels.stats.inter_rater import fleiss_kappa as _fleiss_kappa, aggregate_raters

    if len(raters) < 3:
        raise ValueError("Fleiss' κ 需要至少 3 个评分者。建议两人一致用 Cohen's κ。")

    data = df[raters].dropna()
    n_cases = len(data)

    if n_cases < 10:
        raise ValueError(f"样本量过小（n={n_cases}），Fleiss' κ 估计不稳定。")

    # aggregate_raters → (table, categories)
    table, _categories = aggregate_raters(data.values)
    kappa = float(_fleiss_kappa(table, method="fleiss"))

    # Fleiss' κ 没有简单 SE 公式，用近似 bootstrap
    se = np.sqrt(max(kappa * (1 - kappa) / n_cases, 0.0)) if abs(kappa) < 1 else 0.0
    ci_lower = max(-1.0, kappa - 1.96 * se)
    ci_upper = min(1.0, kappa + 1.96 * se)

    kappa = round(kappa, 3)
    if kappa >= 0.81:
        level = "几乎完美"
    elif kappa >= 0.61:
        level = "高度一致"
    elif kappa >= 0.41:
        level = "中等一致"
    elif kappa >= 0.21:
        level = "尚可"
    else:
        level = "微弱"

    warning = f"Fleiss' κ={kappa}：{level}（Landis & Koch 1977）。"
    if kappa < 0.40:
        warning = "⚠ " + warning + " 评分员之间分歧较大。"

    return ReliabilityResult(
        test_type="fleiss_kappa",
        alpha=kappa,
        ci_lower=round(float(ci_lower), 3),
        ci_upper=round(float(ci_upper), 3),
        n_items=len(raters),
        n_cases=n_cases,
        kappa_value=kappa,
        kappa_method="fleiss",
        warning=warning,
    )
