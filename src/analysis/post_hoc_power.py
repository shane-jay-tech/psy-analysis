"""事后样本量建议（不显示 achieved_power 数值）。

设计动机（Phase 1.3 仲裁，DeepSeek + Kimi 共识）：
- Hoenig & Heisey 2001 批判 post-hoc observed power 是循环论证：观测效应越小→
  power 越低→反向解释为"power 不足，所以才不显著"。这会让 p>.05 永远无法证否。
- 业界（SPSS Observed Power 默认关、JASP/jamovi 放独立模块）从不主动显示。

本模块的折中方案：
- 不暴露 achieved_power 数值。
- 仅当估计的当前 power < 0.80 时，给出"若想 0.80 把握检出该效应需要 n=X"。
- 输出脚注：n_needed 是观察效应量的函数，不可作为证据强度解读。

调用约定：在 runner.py 的 handler 跑完之后调用，从 output["result"] 提取
effect_size 与样本量；不修改 output["result"] 内任何字段；
结果写入 output["post_hoc_power"]（仲裁 Q2）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from src.experiment_design.power_analysis import calculate_sample_size, PowerResult


# 触发阈值（< 此值才给样本量建议；业界惯例 0.80）
POWER_THRESHOLD = 0.80

# 把内部 test_type 映射到 power_analysis 接受的口径
_TEST_TYPE_MAP = {
    "independent_ttest": ("t_test", False),
    "paired_ttest": ("paired_t", True),
    "one_sample_ttest": ("paired_t", True),  # 用单样本近似（df = n-1，与配对同形）
    "one_way_anova": ("anova", False),
    "welch_anova": ("anova", False),
    "two_way_anova": ("factorial", False),
    "repeated_anova": ("rm_anova", True),
    "pearson_corr": ("correlation", False),
    "spearman_corr": ("correlation", False),
    "chi_square_independence": ("chisq", False),
    "chi_square_gof": ("chisq", False),
}


# 提示文案（脚注，必须与每个建议一同显示）
FOOTNOTE = (
    "样本量建议基于观察到的效应量推算，仅供参考；"
    "不可作为「证据强度」解读（Hoenig & Heisey, 2001）。"
)


def _extract_n_from_output(output: Dict[str, Any]) -> int:
    """从 output 推断样本量。"""
    # 先从 descriptive 表的 N 列汇总
    desc = output.get("descriptive")
    if isinstance(desc, pd.DataFrame) and "N" in desc.columns:
        try:
            return int(desc["N"].sum())
        except Exception:
            pass
    # ttest result.group_stats 也有 N 列
    result = output.get("result")
    if result is not None:
        gs = getattr(result, "group_stats", None)
        if isinstance(gs, pd.DataFrame) and "N" in gs.columns:
            try:
                return int(gs["N"].sum())
            except Exception:
                pass
        # 单样本 t / 配对 t 用 df + 2 / df + 1
        df_attr = getattr(result, "df", None)
        if isinstance(df_attr, (int, float)) and df_attr > 0:
            test_type = output.get("test_type", "")
            if "paired" in test_type or "one_sample" in test_type:
                return int(df_attr) + 1
            return int(df_attr) + 2
    return 0


def _extract_chi_square_n(result) -> int:
    ct = getattr(result, "contingency_table", None)
    if isinstance(ct, pd.DataFrame):
        # gof 表的 contingency_table 有"观测频数"列
        if "观测频数" in ct.columns:
            try:
                return int(ct["观测频数"].sum())
            except Exception:
                pass
        # 独立性表是 crosstab，直接 sum().sum()
        try:
            arr = ct.select_dtypes(include="number")
            return int(arr.values.sum())
        except Exception:
            pass
    return 0


def _extract_correlation_n(result) -> int:
    nm = getattr(result, "n_matrix", None)
    if isinstance(nm, pd.DataFrame) and not nm.empty:
        try:
            # 取非对角线最大值（每对相关用的最小 n）
            arr = nm.to_numpy(dtype=float, copy=True)
            n_rows = arr.shape[0]
            off_diag = []
            for i in range(n_rows):
                for j in range(n_rows):
                    if i != j:
                        off_diag.append(arr[i, j])
            if off_diag:
                return int(min(off_diag))
        except Exception:
            pass
    return 0


def _extract_effect_n(test_type: str, output: Dict[str, Any]):
    """根据 test_type 从 result 抽取 (effect_size, n_groups, n)。"""
    result = output.get("result")
    if result is None:
        return None, 0, 0

    if test_type in ("independent_ttest", "paired_ttest", "one_sample_ttest"):
        d = getattr(result, "effect_size", None)
        n = _extract_n_from_output(output)
        return d, 2 if test_type == "independent_ttest" else 1, n

    if test_type in ("one_way_anova", "welch_anova", "repeated_anova", "two_way_anova"):
        eta = getattr(result, "effect_size", None)
        if eta is None:
            return None, 0, 0
        # eta_sq → cohen's f = sqrt(eta / (1 - eta))
        try:
            eta_f = float(eta)
            if eta_f < 0:
                eta_f = 0.0
            if eta_f >= 1:
                eta_f = 0.999
            f_eff = (eta_f / (1.0 - eta_f)) ** 0.5
        except Exception:
            return None, 0, 0
        # 估算组数：从 descriptive 行数
        n_groups = 0
        desc = output.get("descriptive")
        if isinstance(desc, pd.DataFrame):
            n_groups = int(desc.shape[0])
        if n_groups < 2:
            n_groups = 2
        n = _extract_n_from_output(output)
        return f_eff, n_groups, n

    if test_type in ("pearson_corr", "spearman_corr"):
        # 取最大相关系数（绝对值），代表"主要发现"
        cm = getattr(result, "corr_matrix", None)
        if not isinstance(cm, pd.DataFrame):
            return None, 0, 0
        try:
            arr = cm.to_numpy(dtype=float, copy=True)
            mask = ~pd_isnan(arr)
            arr_abs = abs_arr_off_diag(arr)
            if arr_abs is None:
                return None, 0, 0
            r_max = float(arr_abs)
        except Exception:
            return None, 0, 0
        n = _extract_correlation_n(result)
        return r_max, 1, n

    if test_type in ("chi_square_independence", "chi_square_gof"):
        w = getattr(result, "effect_size", None)
        df_chi = getattr(result, "df", 1)
        n = _extract_chi_square_n(result)
        return w, df_chi, n

    return None, 0, 0


def pd_isnan(arr):
    import numpy as np
    return np.isnan(arr)


def abs_arr_off_diag(arr):
    """取相关矩阵非对角线绝对值最大的元素。"""
    import numpy as np

    n = arr.shape[0]
    best = 0.0
    found = False
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            v = arr[i, j]
            if np.isfinite(v) and abs(v) > best:
                best = abs(v)
                found = True
    return best if found else None


def estimate_post_hoc(output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """估计当前样本量是否够用，给出 n_needed 建议。

    返回 dict 结构（写入 output["post_hoc_power"]）：
        {
            "needs_more_n": bool,            # 是否给出建议
            "observed_n": int,
            "observed_effect": float,
            "observed_effect_name": str,
            "n_needed_for_080": int,         # 仅 needs_more_n=True 时填充
            "alpha": float,
            "footnote": str,                 # 必须随建议一同显示的脚注
            "skipped_reason": str,           # needs_more_n=False 时的理由
        }
    None: test_type 不支持事后样本量估算。
    """
    test_type = output.get("test_type", "")
    if test_type not in _TEST_TYPE_MAP:
        return None

    effect, k, n = _extract_effect_n(test_type, output)
    if effect is None or n <= 0:
        return None
    try:
        effect = float(effect)
    except Exception:
        return None
    # 极小效应（接近 0）算 power 没意义
    if abs(effect) < 1e-4:
        return {
            "needs_more_n": False,
            "observed_n": n,
            "observed_effect": effect,
            "observed_effect_name": _effect_name(test_type),
            "skipped_reason": "观察效应量接近 0，事后样本量估算无意义。",
            "footnote": FOOTNOTE,
            "alpha": 0.05,
        }

    pa_test, paired = _TEST_TYPE_MAP[test_type]

    # 用 calculate_sample_size 求 power=0.80 时的 n
    try:
        if pa_test == "t_test":
            res_080: PowerResult = calculate_sample_size(
                pa_test, effect_size=abs(effect), power=POWER_THRESHOLD, alpha=0.05
            )
        elif pa_test == "paired_t":
            res_080 = calculate_sample_size(
                pa_test, effect_size=abs(effect), power=POWER_THRESHOLD, alpha=0.05
            )
        elif pa_test in ("anova", "rm_anova"):
            res_080 = calculate_sample_size(
                pa_test,
                effect_size=abs(effect),
                power=POWER_THRESHOLD,
                alpha=0.05,
                n_groups=max(int(k), 2),
            )
        elif pa_test == "correlation":
            res_080 = calculate_sample_size(
                pa_test, effect_size=abs(effect), power=POWER_THRESHOLD, alpha=0.05
            )
        elif pa_test == "chisq":
            res_080 = calculate_sample_size(
                pa_test,
                effect_size=abs(effect),
                power=POWER_THRESHOLD,
                alpha=0.05,
                df=max(int(k), 1),
            )
        else:
            return None
    except Exception:
        return None

    n_needed = int(res_080.required_n)

    # 比较：当前 n vs n_needed_for_080
    if n >= n_needed:
        return {
            "needs_more_n": False,
            "observed_n": n,
            "observed_effect": round(effect, 4),
            "observed_effect_name": _effect_name(test_type),
            "skipped_reason": (
                f"当前样本量 (n={n}) 已达到检出该效应所需的样本量 "
                f"(n≈{n_needed}, power={POWER_THRESHOLD:.2f})，无需补样。"
            ),
            "footnote": FOOTNOTE,
            "alpha": 0.05,
            "n_needed_for_080": n_needed,
        }

    return {
        "needs_more_n": True,
        "observed_n": n,
        "observed_effect": round(effect, 4),
        "observed_effect_name": _effect_name(test_type),
        "n_needed_for_080": n_needed,
        "alpha": 0.05,
        "footnote": FOOTNOTE,
    }


def _effect_name(test_type: str) -> str:
    if "ttest" in test_type:
        return "Cohen's d"
    if "anova" in test_type:
        return "Cohen's f (由 η² 反推)"
    if "corr" in test_type:
        return "r"
    if "chi_square" in test_type:
        return "Cohen's w / Cramer's V"
    return ""
