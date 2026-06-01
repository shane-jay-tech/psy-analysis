"""单被试实验设计：AB设计 / 多基线设计 + PND / NAP 效应量

单被试研究（single-subject research / N-of-1 design）通过重复测量追踪
个体在基线期（A）和干预期（B）的行为变化，常用于特殊教育、临床干预、
行为分析等领域。

实现方法：
- AB设计：1个基线期 + 1个干预期
- 多基线设计：跨行为/被试/情境的多个AB序列
- PND（非重叠数据百分比）：两期之间非重叠数据的比例
- NAP（非重叠对百分比）：两两比较中干预优于基线的比例
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import numpy as np
import pandas as pd


@dataclass
class SingleSubjectDesign:
    """单被试实验设计模板"""
    design_type: str  # "ab" / "multiple_baseline" / "reversal" / "alternating"
    participant_id: str
    target_behaviors: List[str]  # 目标行为列表

    # 各行为的阶段数据
    baseline_phases: Dict[str, List[float]] = field(default_factory=dict)
    intervention_phases: Dict[str, List[float]] = field(default_factory=dict)

    # 设计参数
    baseline_min_points: int = 5
    intervention_min_points: int = 5
    stability_criterion: float = 0.20  # 基线稳定性标准（变异系数）

    metadata: Dict = field(default_factory=dict)


@dataclass
class SingleSubjectResult:
    """单被试数据分析结果"""
    participant_id: str
    behavior: str
    baseline_n: int
    intervention_n: int
    baseline_mean: float
    baseline_sd: float
    intervention_mean: float
    intervention_sd: float
    mean_change: float
    pnd: float  # 非重叠数据百分比
    nap: float  # 非重叠对百分比
    pnd_interpretation: str
    nap_interpretation: str
    effect_size_interpretation: str
    baseline_stable: bool
    has_improvement: bool
    raw_data: pd.DataFrame = field(default_factory=pd.DataFrame)


# ============================================================
# 核心 API
# ============================================================


def create_ab_design(
    participant_id: str,
    target_behaviors: List[str],
    baseline_length: int = 8,
    intervention_length: int = 12,
) -> SingleSubjectDesign:
    """
    创建 AB 设计（单基线 + 单干预）。

    A期（基线）：多次测量目标行为，不做干预
    B期（干预）：实施干预后继续测量

    参数：
        participant_id: 被试编号
        target_behaviors: 目标行为名称列表（如 ["课堂专注行为", "作业完成率"]）
        baseline_length: 基线期最小测量点数
        intervention_length: 干预期最小测量点数
    """
    return SingleSubjectDesign(
        design_type="ab",
        participant_id=participant_id,
        target_behaviors=target_behaviors,
        baseline_min_points=baseline_length,
        intervention_min_points=intervention_length,
        metadata={
            "phases": [
                {"name": "A (基线期)", "n_points": baseline_length, "description": "不干预，仅观察记录"},
                {"name": "B (干预期)", "n_points": intervention_length, "description": "实施干预措施，持续记录"},
            ],
            "design_description": (
                f"AB设计：基线期观察{baseline_length}次，随后进入干预阶段"
                f"观察{intervention_length}次。通过比较A/B两期的水平、趋势和"
                f"变异性来评估干预效果。"
            ),
        },
    )


def create_multiple_baseline_design(
    participant_id: str,
    target_behaviors: List[str],
    baseline_lengths: Optional[List[int]] = None,
    intervention_length: int = 12,
    stagger: int = 4,
) -> SingleSubjectDesign:
    """
    创建多基线设计（跨行为）。

    每条基线的长度不同（逐渐递增的基线长度），
    以控制历史和成熟效应。

    参数：
        participant_id: 被试编号
        target_behaviors: 目标行为列表
        baseline_lengths: 各行为基线期长度（None 则自动递增）
        intervention_length: 各行为干预期统一长度
        stagger: 基线间错开间距（点数）
    """
    n = len(target_behaviors)
    if baseline_lengths is None:
        baseline_lengths = [5 + i * stagger for i in range(n)]

    phases_desc = []
    for i, behavior in enumerate(target_behaviors):
        phases_desc.append({
            "behavior": behavior,
            "baseline_n": baseline_lengths[i],
            "intervention_n": intervention_length,
            "baseline_start": f"第1天",
            "intervention_start": f"第{baseline_lengths[i] + 1}天",
        })

    return SingleSubjectDesign(
        design_type="multiple_baseline",
        participant_id=participant_id,
        target_behaviors=target_behaviors,
        baseline_min_points=min(baseline_lengths) if baseline_lengths else 5,
        intervention_min_points=intervention_length,
        metadata={
            "phases": phases_desc,
            "stagger": stagger,
            "design_description": (
                f"多基线设计（跨{n}个行为）：每个行为有不同长度的基线期"
                f"（{', '.join(str(b) for b in baseline_lengths)}次），"
                f"干预期统一{intervention_length}次。"
                f"基线间错开{stagger}点，控制历史和成熟威胁内部效度。"
            ),
        },
    )


# ============================================================
# 数据分析
# ============================================================


def analyze_single_subject(
    baseline: List[float],
    intervention: List[float],
    behavior_name: str = "",
    participant_id: str = "",
) -> SingleSubjectResult:
    """
    分析单被试数据：计算基线稳定性、PND、NAP。

    参数：
        baseline: 基线期数据点列表
        intervention: 干预期数据点列表
        behavior_name: 行为名称（用于报告）
        participant_id: 被试编号

    返回：
        SingleSubjectResult 含各分析指标
    """
    base = np.array(baseline, dtype=float)
    inter = np.array(intervention, dtype=float)

    n_base = len(base)
    n_inter = len(inter)

    if n_base < 3 or n_inter < 3:
        raise ValueError(
            f"基线期（n={n_base}）和干预期（n={n_inter}）各需至少3个数据点。"
        )

    base_mean = float(np.mean(base))
    base_sd = float(np.std(base, ddof=1))
    inter_mean = float(np.mean(inter))
    inter_sd = float(np.std(inter, ddof=1))

    mean_change = inter_mean - base_mean

    # 基线稳定性（变异系数）
    cv = abs(base_sd / base_mean) if base_mean != 0 else float("inf")
    baseline_stable = cv < 0.20

    # PND: 非重叠数据百分比
    pnd = _compute_pnd(base, inter)

    # NAP: 非重叠对百分比
    nap = _compute_nap(base, inter)

    # 解释
    pnd_interp = _interpret_pnd(pnd)
    nap_interp = _interpret_nap(nap)

    has_improvement = (pnd >= 0.70) or (nap >= 0.65)

    if pnd >= 0.90:
        es_interp = "干预效果非常显著（PND≥90%）"
    elif pnd >= 0.70:
        es_interp = "干预效果中等（70%≤PND<90%）"
    elif pnd >= 0.50:
        es_interp = "干预效果较弱（50%≤PND<70%），可能存在其他混淆因素"
    else:
        es_interp = "干预效果不明确（PND<50%），建议检查基线稳定性或延长观察期"

    # 构建原始数据表
    raw_df = pd.DataFrame({
        "阶段": ["A (基线)"] * n_base + ["B (干预)"] * n_inter,
        "序号": list(range(1, n_base + 1)) + list(range(1, n_inter + 1)),
        "测量值": list(base) + list(inter),
    })

    return SingleSubjectResult(
        participant_id=participant_id,
        behavior=behavior_name,
        baseline_n=n_base,
        intervention_n=n_inter,
        baseline_mean=round(base_mean, 3),
        baseline_sd=round(base_sd, 3),
        intervention_mean=round(inter_mean, 3),
        intervention_sd=round(inter_sd, 3),
        mean_change=round(mean_change, 3),
        pnd=round(pnd, 3),
        nap=round(nap, 3),
        pnd_interpretation=pnd_interp,
        nap_interpretation=nap_interp,
        effect_size_interpretation=es_interp,
        baseline_stable=baseline_stable,
        has_improvement=has_improvement,
        raw_data=raw_df,
    )


def analyze_multiple_behaviors(
    data: Dict[str, Tuple[List[float], List[float]]],
    participant_id: str = "",
) -> List[SingleSubjectResult]:
    """
    批量分析多个行为（多基线设计）。

    参数：
        data: {行为名: (baseline列表, intervention列表), ...}
        participant_id: 被试编号

    返回：
        SingleSubjectResult 列表
    """
    results = []
    for behavior, (baseline, intervention) in data.items():
        result = analyze_single_subject(
            baseline, intervention, behavior, participant_id
        )
        results.append(result)
    return results


# ============================================================
# PND / NAP 计算
# ============================================================


def _compute_pnd(baseline: np.ndarray, intervention: np.ndarray) -> float:
    """
    计算非重叠数据百分比 (Percentage of Non-overlapping Data)。

    PND = 干预期中超出基线期最极端数据点的比例
    - 对于期望提升的行为：超出基线期最大值的干预点比例
    - 对于期望降低的行为：低于基线期最小值的干预点比例

    返回 0-1 之间的值。
    """
    # 判断行为方向：如果干预均值 > 基线均值，则期望提升
    if intervention.mean() >= baseline.mean():
        extreme = baseline.max()
        n_overlap = np.sum(intervention > extreme)
    else:
        extreme = baseline.min()
        n_overlap = np.sum(intervention < extreme)

    return n_overlap / len(intervention)


def _compute_nap(baseline: np.ndarray, intervention: np.ndarray) -> float:
    """
    计算非重叠对百分比 (Non-overlap of All Pairs)。

    NAP = P(干预 > 基线) + 0.5 × P(干预 = 基线)
    基于所有基线-干预数据对的两两比较。

    取值范围：0-1，0.5 表示完全重叠（干预无效）。
    """
    n_b = len(baseline)
    n_i = len(intervention)
    total_pairs = n_b * n_i

    if total_pairs == 0:
        return 0.5

    better = 0
    ties = 0

    for b_val in baseline:
        for i_val in intervention:
            if i_val > b_val:
                better += 1
            elif i_val == b_val:
                ties += 1

    return (better + 0.5 * ties) / total_pairs


def _interpret_pnd(pnd: float) -> str:
    """PND 指标的通用解释"""
    if pnd >= 0.90:
        return "非常有效（PND ≥ 90%）"
    elif pnd >= 0.70:
        return "中等有效（70% ≤ PND < 90%）"
    elif pnd >= 0.50:
        return "效果存疑（50% ≤ PND < 70%）"
    else:
        return "无效（PND < 50%）"


def _interpret_nap(nap: float) -> str:
    """NAP 指标的通用解释"""
    if nap >= 0.93:
        return "强效（NAP ≥ 0.93）"
    elif nap >= 0.66:
        return "中效（0.66 ≤ NAP < 0.93）"
    elif nap >= 0.56:
        return "弱效（0.56 ≤ NAP < 0.66）"
    else:
        return "无效或效果极小（NAP < 0.56）"


# ============================================================
# 报告生成
# ============================================================


def format_single_subject_report(
    results: List[SingleSubjectResult],
    design: Optional[SingleSubjectDesign] = None,
) -> str:
    """
    生成单被试研究报告（APA 7 格式，中文）。
    """
    lines = ["## 单被试实验分析报告", ""]

    if design:
        lines.append(f"**设计类型**：{_design_type_name(design.design_type)}")
        lines.append(f"**被试编号**：{design.participant_id}")
        lines.append(
            f"**目标行为**：{', '.join(design.target_behaviors)}"
        )
        lines.append("")
        lines.append(design.metadata.get("design_description", ""))

    lines.extend(["", "### 分析结果", ""])

    for r in results:
        lines.extend([
            f"#### {r.behavior or '目标行为'}",
            "",
            "| 指标 | 基线期 (A) | 干预期 (B) | 变化 |",
            "|------|-----------|-----------|------|",
            f"| N | {r.baseline_n} | {r.intervention_n} | — |",
            f"| M | {r.baseline_mean:.3f} | {r.intervention_mean:.3f} | "
            f"{r.mean_change:+.3f} |",
            f"| SD | {r.baseline_sd:.3f} | {r.intervention_sd:.3f} | — |",
            "",
            f"**基线稳定性**：{'✅ 稳定（CV<20%）' if r.baseline_stable else '⚠ 不稳定（CV≥20%），效果估计可能不够可靠'}",
            "",
            "**效应量指标**：",
            f"- PND = {r.pnd:.3f}（{r.pnd_interpretation}）",
            f"- NAP = {r.nap:.3f}（{r.nap_interpretation}）",
            "",
            f"**结论**：{r.effect_size_interpretation}",
            "",
        ])

        # 如有多余空间，加入原始数据表
        if len(results) <= 3 and not r.raw_data.empty:
            lines.append("**原始数据**：")
            lines.append("")
            lines.append("| 阶段 | 序号 | 测量值 |")
            lines.append("|------|------|--------|")
            for _, row in r.raw_data.iterrows():
                lines.append(
                    f"| {row['阶段']} | {int(row['序号'])} | {row['测量值']:.2f} |"
                )
            lines.append("")

    lines.append("*注：PND 和 NAP 为单被试研究常用非参数效应量指标，"
                  "解释时需结合基线稳定性、行为类型和研究背景综合判断。*")

    return "\n".join(lines)


def _design_type_name(dt: str) -> str:
    names = {
        "ab": "AB 设计",
        "multiple_baseline": "多基线设计",
        "reversal": "倒返设计 (ABAB)",
        "alternating": "交替处理设计",
    }
    return names.get(dt, dt)
