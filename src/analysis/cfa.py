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
    estimator: str = "MLW"
    # 评审意见 #4：调用方要的估计量与最终实际用的目标函数分开留痕，避免"改名"被误读成等价
    requested_estimator: str = ""
    # v8.7 修复（P16 取证，2026-09-25）：收敛状态此前只在局部变量里算完就丢，
    # 结果对象里没有任何字段承载它，下游无法判定"是否真的拟合过"。
    converged: Optional[bool] = None

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
# 评审意见 #3（GPT，2026-09-25）：CFI/TLI 因浮点误差轻微超 1（如 1.0000001）不应直接判不通过，
# 超出该容差才算"数值越界"。
FIT_RANGE_TOLERANCE = 1e-3

# s1007-37 双源归一：三键以 thresholds.py 单源为准（数值与原本地逐位一致，零语义变更）。
# srmr 留本地：good 档双源数值冲突（本地 0.05 vs thresholds.py SRMR 0.08）待主班裁以谁为准；
# 裁决②键面已定谳（s930-17：semopy calc_stats 无 SRMR 键，生产 :130 恒 0.0 占位）。
from src.analysis.thresholds import CFA as _TH_CFA, RMSEA as _TH_RMSEA, TLI as _TH_TLI  # noqa: E402

FIT_THRESHOLDS = {
    "cfi": {"good": _TH_CFA.good, "acceptable": _TH_CFA.acceptable},
    "tli": {"good": _TH_TLI.good, "acceptable": _TH_TLI.acceptable},
    "rmsea": {"good": _TH_RMSEA.good, "acceptable": _TH_RMSEA.acceptable},
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
    """评估模型拟合优劣

    v8.7 修复（P16 取证，2026-09-25）：入参是 semopy.calc_stats 的 DataFrame，
    pandas 3.x 下 getattr(stats, 'CFI') 取到的是 Series，随后的 >= 与 all([...])
    会抛 "truth value of a Series is ambiguous" —— 该异常被拟合链的 except 吞掉，
    结果是 is_fallback=True、指标全 0（看着像"拟合不佳"，实为"根本没评估"）。
    这里统一取标量，并对越界指标（CFI>1 等）显式告警。
    """
    cfi = _stat_scalar(getattr(result_cfa, 'CFI', 0), 0.0)
    tli = _stat_scalar(getattr(result_cfa, 'TLI', 0), 0.0)
    rmsea = _stat_scalar(getattr(result_cfa, 'RMSEA', 0), 0.0)
    srmr = _stat_scalar(getattr(result_cfa, 'SRMR', 0), 0.0)

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

    # v8.7（P16）：越界指标显式提示——CFI/TLI 超出 [0,1] 或 RMSEA 为负时，
    # "拟合良好"的字面结论不可采信（多与估计量、样本量或模型识别有关）。
    out_of_range = []
    clamp_notes = []
    if cfi > 1.0 + FIT_RANGE_TOLERANCE:
        out_of_range.append(f"CFI={cfi:.3f}>1")
    elif cfi > 1.0:
        clamp_notes.append(f"CFI={cfi:.4f}")
        cfi = 1.0
    if tli > 1.0 + FIT_RANGE_TOLERANCE:
        out_of_range.append(f"TLI={tli:.3f}>1")
    elif tli > 1.0:
        clamp_notes.append(f"TLI={tli:.4f}")
        tli = 1.0
    if rmsea < -FIT_RANGE_TOLERANCE:
        out_of_range.append(f"RMSEA={rmsea:.3f}<0")
    # 评审意见 #3：多项取值（pandas 3.x 下 stats 可能返回 Series）不得静默取首项
    multi_valued = [
        name for name, raw in (
            ("CFI", getattr(result_cfa, 'CFI', None)),
            ("TLI", getattr(result_cfa, 'TLI', None)),
            ("RMSEA", getattr(result_cfa, 'RMSEA', None)),
            ("SRMR", getattr(result_cfa, 'SRMR', None)),
        ) if hasattr(raw, 'iloc') and getattr(raw, 'size', 0) > 1
    ]
    if out_of_range:
        # 越界（CFI/TLI>1、RMSEA<0）说明数值本身不可信 —— 不允许判"良好/可接受"，
        # 也不允许静默通过（P16 取证点：CFI=1.0404 超界仍被判"拟合良好"）。
        summary = ("⚠ 拟合指标越界（" + "；".join(out_of_range) +
                   "），已按「未通过」处理：数值不可信，请核对估计量/样本量/模型识别。")
        is_good = False
        is_acceptable = False
    if clamp_notes:
        summary += f"（注：{'；'.join(clamp_notes)} 属浮点误差级别越界，已按边界值 1.0 处理）"
    if multi_valued:
        summary += f"（注：{'、'.join(multi_valued)} 在 semopy 输出中并非单值，已取首个值，结论需谨慎）"

    return is_acceptable, is_good, summary


# ═══════════════════════════════════════════════════════════════
# 主分析函数（semopy 路径）
# ═══════════════════════════════════════════════════════════════

# semopy 实际支持的目标函数（semopy/model.py 的 self.objectives）。
# v8.7 修复（P16 取证，2026-09-25）：历史默认值 "ML" 不在表内 —— model.fit(obj="ML")
# 直接抛 KeyError('ML is unknown objective function.')，被下面的 except 捕获后
# is_fallback=True、全部拟合指标落 0：任何 "CFI/RMSEA = 0" 的产出实际都是**未拟合**。
SEMOPY_OBJECTIVES = ("MLW", "ULS", "GLS", "WLS", "DWLS", "FIML")
# 只保留历史代码真实用过的 'ML'（本仓 cfa.py 的旧默认值）——评审意见 #4（GPT，2026-09-25）：
# 别名不是普遍语义等价（MLW 是 semopy 的 Wishart 形式 ML），遂不再臆测 MLE/MLM 等写法。
_SEMOPY_OBJECTIVE_ALIASES = {"ML": "MLW"}


def _resolve_objective(name: str) -> Tuple[str, str]:
    """把估计量名映射到 semopy 真实支持的目标函数，并返回（目标函数名, 告警文本）。"""
    if name in SEMOPY_OBJECTIVES:
        return name, ""
    if name in _SEMOPY_OBJECTIVE_ALIASES:
        mapped = _SEMOPY_OBJECTIVE_ALIASES[name]
        return mapped, f'estimator "{name}" 不是 semopy 目标函数名，已按其 ML 语义映射为 "{mapped}"'
    return "MLW", f'estimator "{name}" 不是 semopy 支持的目标函数（{"/".join(SEMOPY_OBJECTIVES)}），已回退 "MLW"'


def _round_or_nan(value, digits: int) -> float:
    """数值化并四舍五入；占位符（'-' / None / 非数值）返回 NaN。

    v8.7 修复（P16 取证）：semopy 载荷表里首指标的 SE/z/p 是字符串占位 "-"，
    原先 float("-") 抛 ValueError 被外层 except 吞掉 ⇒ 整张载荷表永远是 None。
    """
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return float("nan")


def _stat_scalar(value, default: float = 0.0) -> float:
    """把 semopy.calc_stats 的取值归一化成标量 float。

    v8.7 修复（P16 取证）：pandas 3.x 下 stats.get(col) 可能返回 Series，
    float(Series) 抛 TypeError，此前被 except 静默吞成 0.0（指标看着"有值"实为失值）。
    """
    if value is None:
        return default
    try:
        if hasattr(value, "iloc"):
            if getattr(value, "size", 0) == 0:
                return default
            value = value.iloc[0]
        return float(value)
    except (TypeError, ValueError):
        return default


def confirmatory_factor_analysis(
    df: pd.DataFrame,
    factors: Dict[str, List[str]],
    estimator: str = "MLW",
) -> CFAResult:
    """
    执行验证性因素分析。

    参数：
        df: 数据框，包含所有题目列
        factors: 因子-题目映射
            {"认知焦虑": ["CA1", "CA2", "CA3"], "躯体焦虑": ["SA1", "SA2"]}
        estimator: 估计方法，默认 "MLW"（semopy 的极大似然目标函数；
           传 "ML" 等别名会自动映射并记入 warnings）

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
    result.estimator = estimator  # 后面 _resolve_objective() 会覆盖成 semopy 真名

    if result.n_obs < 50:
        result.warnings.append(
            f"⚠ 有效样本量仅{result.n_obs}，CFA通常需要至少200个观测。结果解释需谨慎。"
        )

    try:
        # 构建模型语法
        model_syntax = _build_model_syntax(available_items, factors_clean)

        # 设定模型（v8.7 修复：目标函数名先映射到 semopy 真支持的名字，
        # 否则 model.fit 直接抛 KeyError → 整条拟合链被 except 吞成"全 0 占位"）
        obj_name, obj_warn = _resolve_objective(estimator)
        if obj_warn:
            result.warnings.append(f"⚠ {obj_warn}")
            print(f"[CFA] {obj_warn}")
        result.estimator = obj_name
        result.requested_estimator = estimator
        model = semopy.Model(model_syntax)
        model.fit(clean_df, obj=obj_name)

        # 检查收敛（v8.7：结果入库，不再算完即丢）
        # 注意：本机 semopy 版本的 inspect(mode="converged") 返回 None（该模式未实现），
        # 此时不能把 None 当成"未收敛"误报——None 表示"该版本不提供收敛信息"。
        converged_raw = model.inspect(mode="converged")
        if hasattr(converged_raw, 'iloc'):
            converged_raw = converged_raw.iloc[0, 0] if converged_raw.size > 0 else None
        if converged_raw is None:
            result.converged = None
        else:
            result.converged = bool(converged_raw)
            if not result.converged:
                result.warnings.append("⚠ 模型未收敛：CFI/TLI/RMSEA 等指标不可用于判断模型优度")

        # 提取拟合指标
        stats = semopy.calc_stats(model)

        # 映射拟合指标（v8.7：pandas 3.x 下 stats.get 可能返回 Series，
        # float(Series) 抛 TypeError 被静默吞成 0.0 —— 统一走 _stat_scalar 并留痕）
        coerced = 0
        for py_attr, stat_key in SEMOPY_FIT_MAP.items():
            raw = stats.get(stat_key, 0)
            val = _stat_scalar(raw, 0.0)
            if raw is None or (hasattr(raw, 'iloc') and getattr(raw, 'size', 0) > 1):
                coerced += 1
            setattr(result, py_attr, round(val, 3))
        if coerced:
            result.warnings.append(
                f"⚠ {coerced} 项拟合指标在 semopy 输出中不是标量（多半是 pandas 版本差异），"
                "已取首个可用值；请核对 pandas/semopy 版本组合"
            )

        # 评估拟合
        result.fit_acceptable, result.fit_good, result.fit_summary_zh = _assess_fit(stats)

        # 提取标准化因子载荷
        # v8.7 修复（P16 取证，2026-09-25）：
        #   ① 载荷算符兼容 —— 本机 semopy 用 "~"（旧版 "=~"），原过滤条件恒为空 ⇒ loadings 永远 None；
        #   ② 首指标的 SE/z/p 是字符串占位 "-"，float("-") 抛异常被裸 except 吞掉；
        #   ③ 失败不再静默（除留痕外，载荷缺失会直接写进 warnings）。
        try:
            estimates = model.inspect(mode="list", std_est=True)
            if estimates is not None and len(estimates) > 0 and 'op' in estimates.columns:
                ops = estimates['op'].astype(str)
                loading_rows = ops.isin(("=~", "~"))
                raw = estimates[loading_rows]
                if len(raw) > 0:
                    # 算符语义：旧版 semopy 用 "=~"，约定 lval=因子 / rval=题目；
                    # 本机版本改用 "~"，方向相反（lval=题目 / rval=因子）——
                    # 不区分就会把"潜在变量"和"观测变量"整列写反（下游 AVE/CR 会因此全空）。
                    use_tilde = bool((ops[loading_rows] == "~").all())
                    factor_col = raw['rval'] if use_tilde else raw['lval']
                    item_col = raw['lval'] if use_tilde else raw['rval']
                    load_col = raw['Est. Std'] if 'Est. Std' in raw.columns else raw['Estimate']
                    loadings_df = pd.DataFrame({
                        '潜在变量': list(factor_col.values),
                        '观测变量': list(item_col.values),
                        '标准载荷': [_round_or_nan(x, 3) for x in load_col],
                        'SE': [_round_or_nan(x, 3) for x in raw['Std. Err']],
                        'z值': [_round_or_nan(x, 3) for x in raw['z-value']],
                        'p值': [_round_or_nan(x, 4) for x in raw['p-value']],
                    })
                    result.loadings = loadings_df
                else:
                    result.warnings.append(
                        "⚠ semopy inspect() 未返回载荷行（算符 " + str(sorted(set(ops)))[:60] +
                        "）：载荷表为空，请核对 semopy 版本"
                    )
        except Exception as exc:
            result.warnings.append(f"⚠ 载荷表提取失败：{type(exc).__name__}: {exc}")

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
        # 案 B（s923-08 设计稿 §5，零数值变化）：拟合链抛异常时把"降级"明说出来。
        # 只置哨兵位与说明文本，不改任何拟合指标/载荷/效度数值——下游 renderers.py
        # 与 interpretation.py 早已消费 is_fallback，此前因这里没置位而始终显示成
        # "看着像结果"的全 0 对象。
        result.is_fallback = True
        result.fallback_note = (
            f"⚠ 非严格CFA，拟合指标不可用于判断模型优度：semopy 拟合链抛出 "
            f"{type(e).__name__}: {e}，下方 chi2/CFI/TLI/RMSEA/SRMR/AIC/BIC "
            "均为未拟合的占位 0。收敛效度（AVE/CR）与区分效度（HTMT/Fornell-Larcker）"
            "由独立的探索性支路算出，不依赖本次拟合，仅供参照。"
        )
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
