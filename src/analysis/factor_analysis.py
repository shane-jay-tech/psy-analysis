"""因素分析：探索性因素分析（EFA）"""
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class EFAResult:
    test_type: str = "efa"
    kmo: float = 0.0
    bartlett_chi2: float = 0.0
    bartlett_df: int = 0
    bartlett_p: float = 1.0
    n_factors: int = 0
    loadings: Optional[pd.DataFrame] = None
    eigenvalues: Optional[pd.DataFrame] = None
    variance_explained: Optional[pd.DataFrame] = None
    communalities: Optional[pd.DataFrame] = None
    rotation: str = "varimax"
    n_cases: int = 0
    n_items: int = 0
    min_loading_threshold: float = 0.40
    cross_loading_warning: str = ""
    heywood_warning: str = ""
    communality_warning: str = ""
    warning: str = ""


def exploratory_factor_analysis(
    df: pd.DataFrame,
    items: List[str],
    n_factors: Optional[int] = None,
    rotation: str = "varimax",
    method: str = "minres",
    min_loading_threshold: float = 0.40,
    seed: int = 42,
) -> EFAResult:
    """
    探索性因素分析（EFA）。

    参数：
        df: 数据框
        items: 题目列名列表
        n_factors: 因素数量（None则通过平行分析自动确定）
        rotation: "varimax" | "promax"
        method: "minres" | "ml" | "principal"
        min_loading_threshold: 最小因子载荷阈值（默认0.40）
        seed: 平行分析随机种子（默认42，确保可复现）
    """
    from factor_analyzer import FactorAnalyzer
    from factor_analyzer.factor_analyzer import calculate_kmo, calculate_bartlett_sphericity

    data = df[items].apply(pd.to_numeric, errors="coerce").dropna()
    n_cases, n_items = data.shape

    if n_items < 3:
        raise ValueError("EFA至少需要3道题目。")
    if n_cases < max(5 * n_items, 100):
        raise ValueError(f"样本量不足。建议至少为题目数的5倍（{5*n_items}），当前N={n_cases}。")

    # KMO 和 Bartlett
    try:
        kmo_all, kmo_model = calculate_kmo(data)
        kmo_val = round(float(kmo_model), 3)
    except Exception:
        kmo_val = 0.0

    try:
        chi2, bart_p = calculate_bartlett_sphericity(data)
        bartlett_chi2 = round(float(chi2), 3)
        bartlett_df = n_items * (n_items - 1) // 2
        bartlett_p = round(float(bart_p), 4)
    except Exception:
        bartlett_chi2 = 0.0
        bartlett_df = 0
        bartlett_p = 1.0

    warning = ""
    if kmo_val < 0.5:
        warning += f"⚠ KMO={kmo_val} < 0.50，数据不适合因素分析。"
    elif kmo_val < 0.6:
        warning += f"⚠ KMO={kmo_val} 偏低（< 0.60），因素分析结果可能不稳定。"
    if bartlett_p >= 0.05:
        warning += f"⚠ Bartlett检验p={bartlett_p} ≥ 0.05，相关矩阵可能为单位矩阵。"

    # 确定因素数量（传入seed）
    if n_factors is None:
        n_factors = _parallel_analysis(data, n_items, seed=seed)

    n_factors = max(1, min(n_factors, n_items))

    # 执行 EFA
    try:
        fa = FactorAnalyzer(n_factors=n_factors, rotation=rotation, method=method)
        fa.fit(data)
    except TypeError as e:
        if "force_all_finite" in str(e):
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*force_all_finite.*")
                fa = FactorAnalyzer(n_factors=n_factors, rotation=rotation, method=method)
                try:
                    fa.fit(data)
                except Exception:
                    fa.fit(data.values)
        else:
            raise

    # 载荷矩阵
    loadings_arr = fa.loadings_
    loadings_df = pd.DataFrame(
        loadings_arr,
        index=items,
        columns=[f"因素{i+1}" for i in range(n_factors)],
    )
    loadings_df = loadings_df.round(3)

    # 特征值
    ev, ev_var = fa.get_eigenvalues()
    cum_var = np.cumsum(ev) / np.sum(ev)
    eigenvalues_df = pd.DataFrame({
        "因素": [f"因素{i+1}" for i in range(n_items)],
        "特征值": np.round(ev, 3),
        "解释方差比例": np.round(ev / np.sum(ev), 3),
        "累计解释方差比例": np.round(cum_var, 3),
    })

    # 方差解释
    variance_df = pd.DataFrame({
        "因素": [f"因素{i+1}" for i in range(n_factors)] + ["合计"],
        "SS载荷": np.round(
            list(fa.get_factor_variance()[0]) + [sum(fa.get_factor_variance()[0])], 3
        ),
        "解释方差比例": np.round(
            list(fa.get_factor_variance()[1]) + [sum(fa.get_factor_variance()[1])], 3
        ),
        "累计比例": np.round(
            list(fa.get_factor_variance()[2]) + [sum(fa.get_factor_variance()[2])], 3
        ),
    })

    # 公因子方差（Communality）
    communalities_arr = fa.get_communalities()
    communalities_df = pd.DataFrame({
        "题目": items,
        "共同度": np.round(communalities_arr, 3),
    })

    # ========== 新增质量检查 ==========

    # 1. 共同度过低警告（< 0.3）
    communality_warning = ""
    low_comm = communalities_df[communalities_df["共同度"] < 0.3]
    if len(low_comm) > 0:
        low_items = ", ".join(low_comm["题目"])
        communality_warning = (
            f"⚠ {len(low_comm)}道题目的共同度低于0.30（{low_items}），"
            f"这些题目与提取因素的关联较弱，建议考虑删除。"
        )
        warning += communality_warning

    # 2. Heywood情况检测（共同度 > 1.0）
    heywood_warning = ""
    heywood_items = communalities_df[communalities_df["共同度"] > 1.0]
    if len(heywood_items) > 0:
        hw_items = ", ".join(heywood_items["题目"])
        heywood_warning = (
            f"❌ 检测到Heywood情况：{len(heywood_items)}道题目的共同度超过1.0"
            f"（{hw_items}），共同度={heywood_items['共同度'].tolist()}。"
            f"这是不合理的结果，通常意味着因素数量过多、模型识别问题或数据矩阵非正定。"
            f"建议减少因素数量、检查变量之间的复共线性，或使用主轴因子法（principal axis）替代。"
        )
        warning += " " + heywood_warning if warning else heywood_warning

    # 3. 交叉载荷检测和高亮（使用可配置阈值）
    cross_load_warning, cross_loading_warning = _check_loadings_with_threshold(
        loadings_df, min_loading_threshold
    )
    if cross_loading_warning:
        warning += " " + cross_loading_warning if warning else cross_loading_warning

    return EFAResult(
        test_type="efa",
        kmo=kmo_val,
        bartlett_chi2=bartlett_chi2,
        bartlett_df=bartlett_df,
        bartlett_p=bartlett_p,
        n_factors=n_factors,
        loadings=loadings_df,
        eigenvalues=eigenvalues_df,
        variance_explained=variance_df,
        communalities=communalities_df,
        rotation=rotation,
        n_cases=n_cases,
        n_items=n_items,
        min_loading_threshold=min_loading_threshold,
        cross_loading_warning=cross_loading_warning,
        heywood_warning=heywood_warning,
        communality_warning=communality_warning,
        warning=warning.strip(),
    )


def _parallel_analysis(data: pd.DataFrame, n_items: int, seed: int = 42) -> int:
    """平行分析：比较实际特征值与随机数据特征值，确定因素数量"""
    from factor_analyzer import FactorAnalyzer

    fa_full = FactorAnalyzer(n_factors=n_items, rotation=None)
    fa_full.fit(data)
    ev_actual, _ = fa_full.get_eigenvalues()
    actual_ev = ev_actual[:n_items]

    n_cases = data.shape[0]
    n_random = 50
    np.random.seed(seed)
    random_ev = np.zeros((n_random, n_items))

    for i in range(n_random):
        random_data = np.random.normal(size=(n_cases, n_items))
        fa_r = FactorAnalyzer(n_factors=n_items, rotation=None)
        try:
            fa_r.fit(random_data)
            ev_r, _ = fa_r.get_eigenvalues()
            random_ev[i, :] = ev_r[:n_items]
        except Exception:
            random_ev[i, :] = 1.0

    mean_random_ev = random_ev.mean(axis=0)

    n_factors = int(sum(actual_ev > mean_random_ev))
    return max(1, n_factors)


def _check_loadings_with_threshold(
    loadings_df: pd.DataFrame,
    threshold: float = 0.40,
) -> tuple:
    """
    检查载荷质量（使用可配置阈值）。

    返回: (旧格式warning用于兼容, 详细交叉载荷描述)
    """
    # 找出每个题目的最大绝对载荷和归属因素
    cross_load_items = []
    low_load_items = []

    for item in loadings_df.index:
        row = loadings_df.loc[item]
        abs_row = row.abs()
        max_load = abs_row.max()
        assigned_factor = abs_row.idxmax()
        max_val = row[assigned_factor]

        # 计数大于阈值的载荷
        high_loads = [col for col in loadings_df.columns if abs(row[col]) > threshold]
        n_high = len(high_loads)

        if n_high > 1:
            cross_load_items.append(
                f"「{item}」在{', '.join(high_loads)}上载荷均>{threshold}（{', '.join(f'{row[c]:.3f}' for c in high_loads)}）"
            )
        if max_load < threshold:
            low_load_items.append(f"「{item}」（最大载荷={max_val:.3f}）")

    messages = []
    detailed = ""

    if cross_load_items:
        msg = "⚠ 交叉载荷检测：" + "；".join(cross_load_items) + f"。建议考虑删除或修改这些题目以提高因素结构的简洁性。"
        messages.append(msg)
        detailed += msg
    if low_load_items:
        msg = "⚠ 低载荷检测：" + "；".join(low_load_items) + f"（阈值={threshold}）。建议考虑删除这些题目。"
        messages.append(msg)
        if detailed:
            detailed += " "
        detailed += msg

    return " ".join(messages), detailed
