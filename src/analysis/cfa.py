"""验证性因素分析（CFA）

基于 semopy 实现单阶 CFA 模型，提供模型拟合、标准载荷和显著性检验。
若 semopy 不可用，降级为基于 factor_analyzer 的简化固定载荷分析。
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

try:
    import semopy
    SEMOPY_AVAILABLE = True
except ImportError:
    SEMOPY_AVAILABLE = False


@dataclass
class CFAResult:
    """CFA分析结果"""
    test_type: str = "cfa"
    n_factors: int = 0
    n_items: int = 0
    n_obs: int = 0
    estimator: str = "ML"

    # 模型拟合指标
    chi2: float = 0.0
    chi2_df: int = 0
    chi2_p: float = 0.0
    cfi: float = 0.0
    tli: float = 0.0
    rmsea: float = 0.0
    rmsea_ci_lower: float = 0.0
    rmsea_ci_upper: float = 0.0
    srmr: float = 0.0
    aic: float = 0.0
    bic: float = 0.0

    # 因子载荷
    loadings: Optional[pd.DataFrame] = None           # 标准载荷 + SE + z + p
    # 因子协方差/相关
    factor_cov: Optional[pd.DataFrame] = None

    # 拟合评判
    fit_acceptable: bool = False
    fit_good: bool = False
    fit_summary_zh: str = ""

    # v3.7 整合效度：AVE / CR / HTMT / Fornell-Larcker
    ave_per_factor: Optional[Dict[str, float]] = None
    cr_per_factor: Optional[Dict[str, float]] = None
    htmt_matrix: Optional[pd.DataFrame] = None
    discriminant_fl_pass: Optional[bool] = None
    discriminant_htmt_pass: Optional[bool] = None
    fl_matrix: Optional[pd.DataFrame] = None  # Fornell-Larcker 矩阵（对角线√AVE，下三角因子相关）

    # 降级信息
    is_fallback: bool = False
    fallback_note: str = ""
    warnings: List[str] = field(default_factory=list)


# CFA 模型拟合阈值
FIT_THRESHOLDS = {
    "cfi": {"good": 0.95, "acceptable": 0.90},
    "tli": {"good": 0.95, "acceptable": 0.90},
    "rmsea": {"good": 0.05, "acceptable": 0.08},
    "srmr": {"good": 0.05, "acceptable": 0.08},
}

# fit_measure 名称映射到 semopy 返回的字段
SEMOPY_FIT_MAP = {
    "chi2": "chi2",
    "chi2_df": "DoF",
    "chi2_p": "p-value",
    "cfi": "CFI",
    "tli": "TLI",
    "rmsea": "RMSEA",
    "rmsea_ci_lower": "RMSEA 90% CI (LB)",
    "rmsea_ci_upper": "RMSEA 90% CI (UB)",
    "srmr": "SRMR",
    "aic": "AIC",
    "bic": "BIC",
}


def _build_model_syntax(items: List[str], factors: Dict[str, List[str]]) -> str:
    """根据因子-题目映射构建 semopy 模型语法。

    factors: {"因子1名称": ["item1", "item2", "item3"], "因子2名称": [...]}
    """
    lines = []
    for factor_name, item_list in factors.items():
        # 定义潜在变量
        item_str = " + ".join(item_list)
        lines.append(f"{factor_name} =~ {item_str}")

    # 添加因子间协方差（semopy默认会自动添加，但显式写出更清晰）
    factor_names = list(factors.keys())
    for i in range(len(factor_names)):
        for j in range(i + 1, len(factor_names)):
            lines.append(f"{factor_names[i]} ~~ {factor_names[j]}")

    return "\n".join(lines)


def _assess_fit(result_cfa) -> Tuple[bool, bool, str]:
    """评估模型拟合优劣"""
    cfi = getattr(result_cfa, 'CFI', 0) or 0
    tli = getattr(result_cfa, 'TLI', 0) or 0
    rmsea = getattr(result_cfa, 'RMSEA', 0) or 0
    srmr = getattr(result_cfa, 'SRMR', 0) or 0

    good_cfi = cfi >= FIT_THRESHOLDS["cfi"]["good"]
    good_tli = tli >= FIT_THRESHOLDS["tli"]["good"]
    good_rmsea = rmsea <= FIT_THRESHOLDS["rmsea"]["good"]
    good_srmr = srmr <= FIT_THRESHOLDS["srmr"]["good"]

    acc_cfi = cfi >= FIT_THRESHOLDS["cfi"]["acceptable"]
    acc_tli = tli >= FIT_THRESHOLDS["tli"]["acceptable"]
    acc_rmsea = rmsea <= FIT_THRESHOLDS["rmsea"]["acceptable"]
    acc_srmr = srmr <= FIT_THRESHOLDS["srmr"]["acceptable"]

    is_good = all([good_cfi, good_tli, good_rmsea, good_srmr])
    is_acceptable = all([acc_cfi, acc_tli, acc_rmsea, acc_srmr])

    if is_good:
        summary = "模型拟合良好（CFI ≥ .95, TLI ≥ .95, RMSEA ≤ .05, SRMR ≤ .05）。"
    elif is_acceptable:
        summary = "模型拟合可接受（CFI ≥ .90, TLI ≥ .90, RMSEA ≤ .08, SRMR ≤ .08）。"
    else:
        summary = "模型拟合不理想。"
        issues = []
        if not acc_cfi:
            issues.append(f"CFI={cfi:.3f}低于.90")
        if not acc_tli:
            issues.append(f"TLI={tli:.3f}低于.90")
        if not acc_rmsea:
            issues.append(f"RMSEA={rmsea:.3f}高于.08")
        if not acc_srmr:
            issues.append(f"SRMR={srmr:.3f}高于.08")
        summary += " 问题指标：" + "；".join(issues) + "。建议检查模型设定或考虑修正指数（MI）调整模型。"

    return is_acceptable, is_good, summary


# ═══════════════════════════════════════════════════════════════
# 主分析函数（semopy 路径）
# ═══════════════════════════════════════════════════════════════

def confirmatory_factor_analysis(
    df: pd.DataFrame,
    factors: Dict[str, List[str]],
    estimator: str = "ML",
) -> CFAResult:
    """
    执行验证性因素分析。

    参数：
        df: 数据框，包含所有题目列
        factors: 因子-题目映射
            {"认知焦虑": ["CA1", "CA2", "CA3"], "躯体焦虑": ["SA1", "SA2"]}
        estimator: 估计方法，默认 "ML"（极大似然）

    返回：CFAResult 包含拟合指标、载荷表、因子协方差
    """
    if not SEMOPY_AVAILABLE:
        return _cfa_fallback_factor_analyzer(df, factors)

    result = CFAResult()
    all_items = [item for items in factors.values() for item in items]

    # 数据准备：只保留所需列
    available_items = [c for c in all_items if c in df.columns]
    if len(available_items) < len(all_items):
        missing = set(all_items) - set(available_items)
        result.warnings.append(f"⚠ 以下题目在数据中不存在: {', '.join(missing)}")
    if len(available_items) < 3:
        result.warnings.append("❌ 可用题目不足3个，无法进行CFA。")
        return result

    # 只保留可用题目
    factors_clean = {
        k: [item for item in v if item in available_items]
        for k, v in factors.items()
    }
    factors_clean = {k: v for k, v in factors_clean.items() if len(v) >= 3}

    if not factors_clean:
        result.warnings.append("❌ 每个因子至少需要3个题目指标。")
        return result

    clean_df = df[available_items].apply(pd.to_numeric, errors="coerce").dropna()
    result.n_obs = len(clean_df)
    result.n_items = len(available_items)
    result.n_factors = len(factors_clean)
    result.estimator = estimator

    if result.n_obs < 50:
        result.warnings.append(
            f"⚠ 有效样本量仅{result.n_obs}，CFA通常需要至少200个观测。结果解释需谨慎。"
        )

    try:
        # 构建模型语法
        model_syntax = _build_model_syntax(available_items, factors_clean)

        # 设定模型
        model = semopy.Model(model_syntax)
        model.fit(clean_df, obj=estimator)

        # 检查收敛
        converged = model.inspect(mode="converged")
        if hasattr(converged, 'iloc'):
            converged = converged.iloc[0, 0] if converged.size > 0 else False

        # 提取拟合指标
        stats = semopy.calc_stats(model)

        # 映射拟合指标
        for py_attr, stat_key in SEMOPY_FIT_MAP.items():
            val = stats.get(stat_key, 0)
            if val is None:
                val = 0.0
            try:
                val = float(val)
            except (ValueError, TypeError):
                val = 0.0
            setattr(result, py_attr, round(val, 3))

        # 评估拟合
        result.fit_acceptable, result.fit_good, result.fit_summary_zh = _assess_fit(stats)

        # 提取标准化因子载荷
        try:
            estimates = model.inspect(mode="list", std_est=True)
            if estimates is not None and len(estimates) > 0:
                loadings_df = estimates[estimates['op'] == '=~'].copy()
                if len(loadings_df) > 0:
                    loadings_df = loadings_df[['lval', 'rval', 'Estimate', 'Std. Err', 'z-value', 'p-value']]
                    loadings_df.columns = ['潜在变量', '观测变量', '标准载荷', 'SE', 'z值', 'p值']
                    # 如果还有 Est.std 列，用它覆盖标准载荷
                    if 'Est. Std' in estimates.columns:
                        std_ests = estimates[estimates['op'] == '=~'][['lval', 'rval', 'Est. Std']]
                        std_ests.columns = ['潜在变量', '观测变量', '标准载荷']
                        loadings_df['标准载荷'] = std_ests['标准载荷'].values
                    loadings_df['标准载荷'] = loadings_df['标准载荷'].apply(lambda x: round(float(x), 3))
                    loadings_df['SE'] = loadings_df['SE'].apply(lambda x: round(float(x), 3))
                    loadings_df['z值'] = loadings_df['z值'].apply(lambda x: round(float(x), 3))
                    loadings_df['p值'] = loadings_df['p值'].apply(lambda x: round(float(x), 4))
                    result.loadings = loadings_df
        except Exception:
            pass

        # 提取因子协方差
        try:
            estimates = model.inspect(mode="list", std_est=True)
            if estimates is not None and 'op' in estimates.columns:
                cov_df = estimates[estimates['op'] == '~~'].copy()
                lvals = cov_df['lval'].unique()
                rvals = cov_df['rval'].unique()
                factor_names = list(factors_clean.keys())
                # 只保留因子间协方差（排除误差方差）
                cov_rows = cov_df[
                    cov_df['lval'].isin(factor_names) &
                    cov_df['rval'].isin(factor_names) &
                    (cov_df['lval'] != cov_df['rval'])
                ]
                if len(cov_rows) > 0:
                    result.factor_cov = pd.DataFrame({
                        '因子1': cov_rows['lval'].values,
                        '因子2': cov_rows['rval'].values,
                        '协方差': [round(float(x), 3) for x in cov_rows.get('Estimate', [0])],
                    })
        except Exception:
            pass

    except Exception as e:
        result.warnings.append(f"⚠ semopy模型拟合失败：{e}")
        result.fit_summary_zh = f"模型拟合出错：{e}。请检查数据质量和因子-题目映射。"

    # v3.7 顺手算 AVE / CR / HTMT / Fornell-Larcker
    _attach_validity_metrics(result, clean_df, factors_clean)

    return result


# ═══════════════════════════════════════════════════════════════
# 降级路径（semopy 不可用时）
# ═══════════════════════════════════════════════════════════════

def _cfa_fallback_factor_analyzer(
    df: pd.DataFrame,
    factors: Dict[str, List[str]],
) -> CFAResult:
    """
    使用 factor_analyzer 进行简化版固定载荷验证性分析。
    不是严格CFA，输出仅供探索性参考。
    """
    from factor_analyzer import FactorAnalyzer

    result = CFAResult(is_fallback=True)
    all_items = [item for items in factors.values() for item in items]
    available_items = [c for c in all_items if c in df.columns]
    clean_df = df[available_items].apply(pd.to_numeric, errors="coerce").dropna()

    result.n_obs = len(clean_df)
    result.n_items = len(available_items)
    result.n_factors = len(factors)
    result.fallback_note = (
        "⚠ 非严格CFA，仅供探索：当前环境未安装 semopy 库，使用 factor_analyzer "
        "进行探索性因素分析作为替代。要获得完整CFA（χ², CFI, TLI, RMSEA, SRMR），"
        "请安装 semopy：pip install semopy"
    )
    result.warnings.append(result.fallback_note)

    try:
        n_factors = len(factors)
        fa = FactorAnalyzer(n_factors=n_factors, rotation=None)
        fa.fit(clean_df)

        loadings = fa.loadings_
        result.loadings = pd.DataFrame(
            loadings,
            index=available_items,
            columns=list(factors.keys()),
        ).round(3)

        # 简单拟合评估
        if hasattr(fa, 'get_communalities'):
            communalities = fa.get_communalities()
            avg_communality = np.mean(communalities) if len(communalities) > 0 else 0
            if avg_communality > 0.5:
                result.fit_summary_zh = f"平均公共度 = {avg_communality:.3f}（可接受）。注意：这不是严格CFA的拟合评价。"
            else:
                result.fit_summary_zh = f"平均公共度 = {avg_communality:.3f}（偏低）。注意：这不是严格CFA的拟合评价。"

        result.fit_acceptable = False
        result.fit_good = False

    except Exception as e:
        result.warnings.append(f"⚠ 降级EFA分析也失败：{e}")

    # 降级路径同样尝试附加效度指标（基于近似载荷）
    _attach_validity_metrics(result, clean_df, factors)

    return result


# ═══════════════════════════════════════════════════════════════
# v3.7 整合效度指标：AVE / CR / HTMT / Fornell-Larcker
# ═══════════════════════════════════════════════════════════════

def _attach_validity_metrics(result: CFAResult,
                              clean_df: pd.DataFrame,
                              factors: Dict[str, List[str]]) -> None:
    """在 CFA 主结果上附加 AVE / CR / HTMT / Fornell-Larcker。
    任何子计算异常均不影响主结果，记入 warnings。"""
    if clean_df.empty or not factors:
        return

    # 1. 抽取每因子的标准化载荷；若 semopy 拟合未产出 loadings，回退到 per-factor 单因子 FA
    if result.loadings is not None:
        loadings_long = _extract_loadings_long(result.loadings, factors)
    else:
        loadings_long = _fallback_loadings_per_factor(clean_df, factors, result.warnings)
    if loadings_long.empty:
        return

    try:
        # 2. 计算 AVE 和 CR per factor
        ave_per_factor: Dict[str, float] = {}
        cr_per_factor: Dict[str, float] = {}
        for fname, group in loadings_long.groupby("因子"):
            lambdas = group["标准化载荷"].astype(float).values
            if len(lambdas) < 2:
                continue
            ave = float(np.mean(lambdas ** 2))
            sum_l = float(np.sum(lambdas))
            sum_uniq = float(np.sum(1 - lambdas ** 2))
            denom = sum_l ** 2 + sum_uniq
            cr = (sum_l ** 2) / denom if denom > 0 else 0.0
            ave_per_factor[str(fname)] = round(ave, 3)
            cr_per_factor[str(fname)] = round(cr, 3)
        result.ave_per_factor = ave_per_factor
        result.cr_per_factor = cr_per_factor

        # 3. Fornell-Larcker：用因子总分（sum score）作为因子相关代理
        from .validity import discriminant_fornell_larcker, discriminant_htmt
        factor_scores = pd.DataFrame({
            f: clean_df[items].sum(axis=1)
            for f, items in factors.items()
            if all(it in clean_df.columns for it in items)
        })
        if factor_scores.shape[1] >= 2 and ave_per_factor:
            corr = factor_scores.corr()
            try:
                fl_res = discriminant_fornell_larcker(ave_per_factor, corr)
                result.fl_matrix = fl_res.detail
                result.discriminant_fl_pass = fl_res.fornell_larcker_pass
            except Exception as e:
                result.warnings.append(f"Fornell-Larcker 计算失败：{e}")

            # 4. HTMT
            try:
                htmt_res = discriminant_htmt(clean_df, factors)
                result.htmt_matrix = htmt_res.detail
                result.discriminant_htmt_pass = htmt_res.fornell_larcker_pass
            except Exception as e:
                result.warnings.append(f"HTMT 计算失败：{e}")

    except Exception as e:
        result.warnings.append(f"效度指标附加失败：{e}")


def _fallback_loadings_per_factor(clean_df: pd.DataFrame,
                                    factors: Dict[str, List[str]],
                                    warnings_list: List[str]) -> pd.DataFrame:
    """semopy 拟合失败时的兜底：每个因子用 factor_analyzer 跑单因子提取标准化载荷。"""
    try:
        from factor_analyzer import FactorAnalyzer
    except Exception as e:
        warnings_list.append(f"无法回退计算载荷（factor_analyzer 不可用）：{e}")
        return pd.DataFrame()

    rows = []
    for fname, items in factors.items():
        items_avail = [it for it in items if it in clean_df.columns]
        if len(items_avail) < 2:
            continue
        sub = clean_df[items_avail]
        try:
            fa = FactorAnalyzer(n_factors=1, rotation=None, method="ml")
            fa.fit(sub)
            lambdas = fa.loadings_.flatten()
        except Exception:
            try:
                fa = FactorAnalyzer(n_factors=1, rotation=None, method="principal")
                fa.fit(sub)
                lambdas = fa.loadings_.flatten()
            except Exception as e2:
                warnings_list.append(f"因子「{fname}」载荷回退失败：{e2}")
                continue
        for it, lam in zip(items_avail, lambdas):
            rows.append({"因子": fname, "题目": it, "标准化载荷": float(lam)})
    return pd.DataFrame(rows)


def _extract_loadings_long(loadings_df: pd.DataFrame,
                            factors: Dict[str, List[str]]) -> pd.DataFrame:
    """把 CFA loadings 表统一成 long format ['因子', '题目', '标准化载荷']。

    支持两种输入：
    1. semopy 路径：列含 ['潜在变量', '观测变量', '标准载荷', ...] 的 long 表
    2. fallback 路径：行=题目、列=因子的 wide 表
    """
    if "潜在变量" in loadings_df.columns and "观测变量" in loadings_df.columns:
        col_load = "标准载荷" if "标准载荷" in loadings_df.columns else "Estimate"
        out = loadings_df[["潜在变量", "观测变量", col_load]].copy()
        out.columns = ["因子", "题目", "标准化载荷"]
        return out

    # fallback wide 格式：每行一道题，每列一个因子
    rows = []
    for fname, items in factors.items():
        if fname not in loadings_df.columns:
            continue
        for it in items:
            if it in loadings_df.index:
                lam = loadings_df.loc[it, fname]
                if pd.notna(lam):
                    rows.append({"因子": fname, "题目": it, "标准化载荷": float(lam)})
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════
# 便捷函数：单因子CFA
# ═══════════════════════════════════════════════════════════════

def single_factor_cfa(df: pd.DataFrame, items: List[str],
                      factor_name: str = "因子1") -> CFAResult:
    """对一组题目进行单因子CFA"""
    factors = {factor_name: items}
    return confirmatory_factor_analysis(df, factors)


def multi_factor_cfa_compare(
    df: pd.DataFrame,
    items: List[str],
    factor_models: List[Dict[str, List[str]]],
) -> pd.DataFrame:
    """
    比较多因子模型拟合。

    参数：
        items: 所有题目的列表
        factor_models: 多个因子模型
            [{"单因子": {"因子1": ["item1",...,"item6"]}},
             {"双因子": {"因子A": ["item1","item2","item3"],
                       "因子B": ["item4","item5","item6"]}}]

    返回：模型比较表
    """
    rows = []
    for model_dict in factor_models:
        for model_name, factors in model_dict.items():
            cfa_result = confirmatory_factor_analysis(df, factors)
            rows.append({
                "模型": model_name,
                "因子数": cfa_result.n_factors,
                "χ²": cfa_result.chi2,
                "df": cfa_result.chi2_df,
                "CFI": cfa_result.cfi,
                "TLI": cfa_result.tli,
                "RMSEA": cfa_result.rmsea,
                "SRMR": cfa_result.srmr,
                "AIC": cfa_result.aic,
                "BIC": cfa_result.bic,
                "拟合判断": cfa_result.fit_summary_zh[:60],
            })

    return pd.DataFrame(rows).sort_values("AIC")
