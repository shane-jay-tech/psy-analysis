"""SEM 结构方程模型：在 CFA（测量模型）基础上扩展结构路径（潜变量间回归关系）"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict

try:
    import semopy
    SEMOPY_AVAILABLE = True
except ImportError:
    SEMOPY_AVAILABLE = False


@dataclass
class SEMResult:
    test_type: str = "sem"
    model_syntax: str = ""
    fit_indices: Optional[Dict[str, float]] = None
    fit_acceptable: bool = False
    fit_good: bool = False
    fit_summary: str = ""
    path_coefficients: Optional[pd.DataFrame] = None
    loadings: Optional[pd.DataFrame] = None
    r_squared: Optional[Dict[str, float]] = None
    indirect_effects: Optional[pd.DataFrame] = None
    total_effects: Optional[pd.DataFrame] = None
    n_obs: int = 0
    warnings: List[str] = field(default_factory=list)


def structural_equation_model(
    df: pd.DataFrame,
    measurement_model: Dict[str, List[str]],
    structural_paths: List[str],
    estimator: str = "ML",
) -> SEMResult:
    """
    完整结构方程模型：测量模型 + 结构模型。

    参数：
        df: 数据框
        measurement_model: 因子-题目映射（测量模型）
            {"自尊": ["SE1","SE2","SE3"], "焦虑": ["ANX1","ANX2","ANX3"], "孤独": ["LON1","LON2"]}
        structural_paths: 结构路径列表（semopy 语法）
            ["焦虑 ~ 自尊", "孤独 ~ 焦虑 + 自尊"]
            含义：焦虑 由 自尊 预测；孤独 由 焦虑和自尊预测
        estimator: 估计方法（ML / DWLS）

    返回：
        SEMResult 包含路径系数、拟合指标、R²、间接效应等
    """
    if not SEMOPY_AVAILABLE:
        result = SEMResult()
        result.warnings.append("semopy 未安装，无法执行 SEM。请运行 pip install semopy。")
        return result

    result = SEMResult()

    all_items = [item for items in measurement_model.values() for item in items]
    available = [c for c in all_items if c in df.columns]
    if len(available) < len(all_items):
        missing = set(all_items) - set(available)
        result.warnings.append(f"以下观测变量在数据中不存在: {', '.join(missing)}")

    clean = df[available].copy()
    for c in available:
        clean[c] = pd.to_numeric(clean[c], errors="coerce")
    clean = clean.dropna()
    result.n_obs = len(clean)

    if result.n_obs < len(available) * 5:
        result.warnings.append(
            f"样本量（{result.n_obs}）相对于观测变量数（{len(available)}）偏小，"
            f"建议 N ≥ {len(available) * 5}。"
        )

    syntax_lines = []
    for factor, items in measurement_model.items():
        valid_items = [it for it in items if it in available]
        if valid_items:
            syntax_lines.append(f"{factor} =~ {' + '.join(valid_items)}")

    for path in structural_paths:
        syntax_lines.append(path)

    model_syntax = "\n".join(syntax_lines)
    result.model_syntax = model_syntax

    try:
        model = semopy.Model(model_syntax)
        obj = "MLW" if estimator == "ML" else estimator
        model.fit(clean, obj=obj)
    except Exception as e:
        result.warnings.append(f"SEM 拟合失败: {e}")
        return result

    try:
        stats_obj = semopy.calc_stats(model)
        fit = {}
        for idx_name in ["CFI", "TLI", "RMSEA", "chi2", "chi2 p-value", "AIC", "BIC", "GFI", "AGFI"]:
            if idx_name in stats_obj.columns:
                val = stats_obj[idx_name].values[0]
                if pd.notna(val):
                    fit[idx_name] = round(float(val), 4)

        result.fit_indices = fit
        cfi = fit.get("CFI", 0)
        rmsea = fit.get("RMSEA", 1)
        result.fit_good = cfi >= 0.95 and rmsea <= 0.06
        result.fit_acceptable = cfi >= 0.90 and rmsea <= 0.08

        if result.fit_good:
            result.fit_summary = "模型拟合良好"
        elif result.fit_acceptable:
            result.fit_summary = "模型拟合可接受"
        else:
            result.fit_summary = "模型拟合不佳，建议检查模型设定或修正"
    except Exception as e:
        result.warnings.append(f"拟合指标计算失败: {e}")

    try:
        estimates = model.inspect()
        path_rows = []
        loading_rows = []

        latent_vars = set(measurement_model.keys())
        observed_vars = set(item for items in measurement_model.values() for item in items)

        for _, row in estimates.iterrows():
            op = row.get("op", "")
            lval = str(row.get("lval", ""))
            rval = str(row.get("rval", ""))

            if op != "~":
                continue

            est_raw = row.get("Estimate", 0)
            se_raw = row.get("Std. Err", "-")
            z_raw = row.get("z-value", "-")
            p_raw = row.get("p-value", "-")

            def _safe_float(v, default=0):
                if v is None or (isinstance(v, str) and v.strip() == "-"):
                    return default
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return default

            est = _safe_float(est_raw, 0)
            se = _safe_float(se_raw, 0)
            z = _safe_float(z_raw, 0)
            p = _safe_float(p_raw, 1)

            if lval in observed_vars and rval in latent_vars:
                loading_rows.append({
                    "潜变量": rval,
                    "观测变量": lval,
                    "载荷": round(est, 3),
                    "SE": round(se, 3) if se > 0 else "-",
                    "z": round(z, 3) if z != 0 else "-",
                    "p": round(p, 4) if p < 1 else "-",
                })
            elif lval in latent_vars and rval in latent_vars:
                path_rows.append({
                    "因变量": lval,
                    "自变量": rval,
                    "B": round(est, 3),
                    "SE": round(se, 3),
                    "z": round(z, 3),
                    "p": round(p, 4),
                    "显著": "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "",
                })

        if path_rows:
            result.path_coefficients = pd.DataFrame(path_rows)
        if loading_rows:
            result.loadings = pd.DataFrame(loading_rows)
    except Exception as e:
        result.warnings.append(f"参数提取失败: {e}")

    try:
        latent_vars = list(measurement_model.keys())
        endogenous = set()
        for path in structural_paths:
            dv_part = path.split("~")[0].strip()
            endogenous.add(dv_part)

        r2_dict = {}
        estimates = model.inspect()
        for endo in endogenous:
            var_rows = estimates[(estimates["lval"] == endo) & (estimates["op"] == "~~") & (estimates["rval"] == endo)]
            if not var_rows.empty:
                residual_var = float(var_rows.iloc[0]["Estimate"])
                total_var = clean[measurement_model.get(endo, [])].mean(axis=1).var() if endo in measurement_model else 1
                if total_var > 0 and residual_var < total_var:
                    r2_dict[endo] = round(1 - residual_var / total_var, 3)

        if r2_dict:
            result.r_squared = r2_dict
    except Exception:
        pass

    try:
        path_df = result.path_coefficients
        if path_df is not None and len(path_df) >= 2:
            indirect_rows = _compute_indirect_effects(path_df, measurement_model)
            if indirect_rows:
                result.indirect_effects = pd.DataFrame(indirect_rows)
    except Exception:
        pass

    return result


def _compute_indirect_effects(
    path_df: pd.DataFrame,
    measurement_model: Dict[str, List[str]],
) -> List[Dict]:
    """
    从路径系数表中识别并计算间接效应。
    如 X→M→Y 的间接效应 = a * b
    """
    latent_vars = set(measurement_model.keys())
    effects = {}
    for _, row in path_df.iterrows():
        dv = row["因变量"]
        iv = row["自变量"]
        if dv not in effects:
            effects[dv] = {}
        effects[dv][iv] = row["B"]

    indirect_rows = []
    for mediator in latent_vars:
        if mediator not in effects:
            continue
        for iv in effects[mediator]:
            a = effects[mediator][iv]
            for dv in effects:
                if dv == mediator:
                    continue
                if mediator in effects.get(dv, {}):
                    b = effects[dv][mediator]
                    indirect = a * b
                    indirect_rows.append({
                        "路径": f"{iv} → {mediator} → {dv}",
                        "a (X→M)": round(a, 3),
                        "b (M→Y)": round(b, 3),
                        "间接效应 (a×b)": round(indirect, 3),
                    })

    return indirect_rows
