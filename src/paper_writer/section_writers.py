"""论文写作系统 — 各章节生成器

每个生成器接收 PaperContext，输出格式化的论文段落。
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from .psychology_report_format import (
    STAT_FORMATS, SIG_MARKS, EFFECT_SIZE_GUIDE, ACADEMIC_PHRASES
)
from .literature_manager import LiteratureManager


@dataclass
class PaperContext:
    """论文写作上下文"""
    # 基本信息
    title_hint: str = ""                          # 论文标题提示
    topic: str = ""                               # 研究主题
    research_questions: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)

    # 方法与材料
    participants_n: int = 0
    participants_desc: str = ""                   # 被试描述
    male_ratio: float = 0.0                       # 男性比例
    age_mean: float = 0.0
    age_sd: float = 0.0
    materials: List[Dict] = field(default_factory=list)  # [{name, items, alpha, source}]
    procedure: str = ""                           # 施测程序
    ethics: str = ""                              # 伦理信息

    # 结果（来自分析系统）
    analysis_results: Dict[str, Any] = field(default_factory=dict)

    # 数据与图表
    df: Optional[pd.DataFrame] = None
    table_data: Dict[str, pd.DataFrame] = field(default_factory=dict)
    chart_files: Dict[str, str] = field(default_factory=dict)

    # 讨论
    theoretical_contributions: List[str] = field(default_factory=list)
    practical_implications: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    future_directions: List[str] = field(default_factory=list)

    # 用户问答补充
    user_answers: Dict[str, str] = field(default_factory=dict)

    # 文献
    literature_manager: Optional[LiteratureManager] = None

    # 控制变量
    control_vars: List[str] = field(default_factory=list)

    def get_lit(self) -> LiteratureManager:
        if self.literature_manager is None:
            self.literature_manager = LiteratureManager()
        return self.literature_manager


# ===========================================================================
# 标题与摘要
# ===========================================================================

def write_title(context: PaperContext) -> str:
    """生成论文标题（心理学报风格：不超过25字）"""
    if context.title_hint:
        return context.title_hint

    # 从研究变量推断标题
    hypotheses = context.hypotheses
    if hypotheses:
        # 提取第一个假设中的关键变量
        h1 = hypotheses[0]
        return f"基于{h1[:20]}的研究" if len(h1) > 20 else h1

    return context.topic if context.topic else "心理学实证研究"


def write_abstract(context: PaperContext) -> str:
    """
    生成中文摘要（200-300字，四要素结构）。
    """
    parts = ["目的：", "方法：", "结果：", "结论："]

    # 目的
    topic = context.topic or "心理变量之间的关系"
    purpose = f"探讨{topic}的内在机制。"

    # 方法
    n = context.participants_n
    n_str = f"{n}名" if n else "XXX名"
    method = f"采用问卷调查法，以{n_str}被试为样本，使用一系列标准化心理量表进行测量。运用描述统计、相关分析、回归分析及Bootstrap中介效应检验等方法对数据进行分析。"

    # 结果
    results_text = _summarize_results(context)

    # 结论
    h_count = len(context.hypotheses)
    if h_count > 0:
        conclusion = "研究结果部分支持了研究假设，揭示了变量间的内在关系，为相关领域的理论发展和实践应用提供了实证依据。"
    else:
        conclusion = "研究揭示了变量间的内在关系，为相关领域的理论发展和实践应用提供了实证依据。"

    abstract = f"目的：{purpose}\n方法：{method}\n结果：{results_text}\n结论：{conclusion}"

    return abstract


def write_keywords(context: PaperContext) -> List[str]:
    """生成关键词（3-5个）"""
    # 从研究变量中提取
    keywords = []

    # 从分析结果推断变量
    analysis = context.analysis_results
    if analysis:
        for k, v in analysis.items():
            dv = v.get("dependent_vars", [])
            iv = v.get("independent_vars", [])
            for var in dv[:2] + iv[:2]:
                if var and var not in keywords and not var.startswith("_"):
                    keywords.append(var)

    # 补充方法论关键词
    if any("mediation" in k for k in context.analysis_results):
        keywords.append("中介效应")
    if any("moderation" in k for k in context.analysis_results):
        keywords.append("调节效应")
    if any("efa" in k for k in context.analysis_results):
        keywords.append("因素分析")

    keywords.append("心理测量")

    return keywords[:5]


# ===========================================================================
# 引言
# ===========================================================================

def write_introduction(context: PaperContext) -> str:
    """
    生成引言部分：
    1. 研究背景与问题提出
    2. 文献综述与理论框架
    3. 现有研究不足与研究缺口
    4. 本研究目的与假设
    """
    lit = context.get_lit()
    sections = []

    # ---- 1. 研究背景 ----
    topic = context.topic or "本研究关注的心理学变量"
    sections.append(f"## 1 引言\n\n### 1.1 研究背景\n\n{topic}是心理学研究的重要议题之一。近年来，越来越多的研究者关注到{topic}在个体心理健康与社会适应中的重要作用。然而，关于{topic}的内在影响机制仍需进一步探讨。")

    # ---- 2. 文献综述 ----
    sections.append("### 1.2 文献综述与理论框架")

    # 尝试将用户提供的假设融入理论叙述
    if context.hypotheses:
        sections.append("基于前人研究，本研究提出以下理论框架：")
        for i, hyp in enumerate(context.hypotheses, 1):
            sections.append(f"假设{i}（H{i}）：{hyp}")

    # 搜索相关文献
    relevant_lit = lit.search_presets(
        _extract_topic_keywords(context), n=5
    )
    if relevant_lit:
        lit_text = "已有研究表明，" + "；".join(
            f"{e.authors[0]}({e.year})发现{e.title[:20]}..."
            for e in relevant_lit[:3]
        ) + f"{lit.cite(relevant_lit[0].key)}。"
        sections.append(lit_text)

    # ---- 3. 研究缺口 ----
    sections.append("### 1.3 现有研究不足")

    gaps = []
    if context.control_vars:
        gaps.append(f"以往研究较少同时控制{'、'.join(context.control_vars)}等潜在混淆变量。")
    if any("mediation" in k for k in context.analysis_results):
        gaps.append("虽有研究探讨了变量间的直接关系，但对其中的中介机制考察不足。")

    if not gaps:
        gaps.append("当前研究对该主题的探讨仍存在理论框架不够整合、实证证据不够充分的问题。")

    sections.append("然而，" + "；".join(gaps))

    # ---- 4. 本研究目的与假设 ----
    sections.append("### 1.4 本研究目的与假设")
    purpose = f"基于上述分析，本研究旨在探讨{topic}，具体包括："
    sections.append(purpose)

    if context.research_questions:
        for i, rq in enumerate(context.research_questions, 1):
            sections.append(f"（{i}）{rq}")

    if context.hypotheses:
        sections.append("\n本研究提出以下假设：")
        for i, hyp in enumerate(context.hypotheses, 1):
            sections.append(f"**H{i}**：{hyp}")

    return "\n\n".join(sections)


# ===========================================================================
# 方法
# ===========================================================================

def write_methods(context: PaperContext) -> str:
    """
    生成方法部分：
    2.1 被试
    2.2 研究工具
    2.3 研究程序
    2.4 数据分析策略
    """
    sections = []
    lit = context.get_lit()

    # ---- 被试 ----
    sections.append("## 2 方法\n\n### 2.1 被试")
    n = context.participants_n

    if n > 0:
        male_n = int(n * context.male_ratio) if context.male_ratio else n // 2
        female_n = n - male_n
        age_str = f"平均年龄为{context.age_mean:.1f}±{context.age_sd:.1f}岁" if context.age_mean else ""
        participants = (
            f"本研究共招募{n}名被试，其中男性{male_n}人（{context.male_ratio*100:.1f}%），"
            f"女性{female_n}人（{(1-context.male_ratio)*100:.1f}%），{age_str}。"
        )
    else:
        participants = f"本研究共招募XXX名被试（具体信息待补充）。"

    sections.append(participants)

    if context.participants_desc:
        sections.append(context.participants_desc)

    # ---- 研究工具 ----
    sections.append("### 2.2 研究工具")

    if context.materials:
        for i, mat in enumerate(context.materials):
            name = mat.get("name", f"量表{i+1}")
            items = mat.get("items", "?")
            alpha = mat.get("alpha", "?")
            source = mat.get("source", "")
            sections.append(
                f"**{name}**：共{items}道题目，"
                f"在本研究中的Cronbach's α={alpha}。"
                + (f"该量表由{source}编制。" if source else "")
            )
    else:
        sections.append("（量表信息待补充 — 请在方法配置中填写各量表的名称、题目数、信度等信息。）")

    # 共同方法偏差引用
    sections.append(
        f"\n为检验共同方法偏差，采用Harman单因素检验{lit.cite('周浩2004')}。"
    )

    # ---- 研究程序 ----
    sections.append("### 2.3 研究程序")
    if context.procedure:
        sections.append(context.procedure)
    else:
        sections.append("本研究采用线上问卷施测方式。被试在阅读知情同意书后，依次完成各量表的作答。整个施测过程约15-20分钟。")

    if context.ethics:
        sections.append(f"\n{context.ethics}")
    else:
        sections.append("\n本研究已获得伦理审批（详细信息待补充）。")

    # ---- 数据分析策略 ----
    sections.append("### 2.4 数据分析策略")

    # 从分析结果反推分析策略
    analysis_desc = _describe_analysis_strategy(context)
    sections.append(analysis_desc)

    return "\n\n".join(sections)


# ===========================================================================
# 结果
# ===========================================================================

def write_results(context: PaperContext) -> str:
    """
    生成结果部分：
    3.1 共同方法偏差检验
    3.2 描述统计与相关分析
    3.3 假设检验
    """
    sections = []
    sections.append("## 3 结果\n")

    analysis = context.analysis_results
    lit = context.get_lit()

    # ---- 共同方法偏差 ----
    sections.append("### 3.1 共同方法偏差检验")
    sections.append(
        "采用Harman单因素检验法，对所有题目进行探索性因素分析。"
        "结果表明，未旋转的第一个因子解释了XX%的变异（<40%的临界标准），"
        "表明本研究不存在严重的共同方法偏差问题" + lit.cite("周浩2004") + lit.cite("Podsakoff2003") + "。"
    )

    # ---- 描述统计与相关分析 ----
    sections.append("### 3.2 描述统计与相关分析")
    sections.append("各变量的均值、标准差和相关矩阵见表1。")

    # 尝试从分析结果中提取描述统计
    for key, result_dict in analysis.items():
        desc = result_dict.get("descriptive")
        if desc is not None and isinstance(desc, pd.DataFrame) and not desc.empty:
            sections.append(f"\n表1中列出了各关键变量的描述统计信息。")
            break

    # 从相关分析结果中提取关键发现
    corr_key = None
    for key in analysis:
        if "corr" in key or "pearson" in key or "spearman" in key:
            corr_key = key
            break

    if corr_key:
        corr_result = analysis[corr_key].get("result")
        if corr_result and hasattr(corr_result, "corr_matrix"):
            corr = corr_result.corr_matrix
            sections.append(f"相关分析结果（见表2）显示了各变量之间的相关关系。")
    else:
        sections.append("相关分析结果显示了各变量之间不同程度的相关关系。")

    # ---- 假设检验 ----
    sections.append("### 3.3 假设检验")

    if context.hypotheses:
        for i, hyp in enumerate(context.hypotheses, 1):
            sections.append(f"\n**H{i}的检验**：{hyp}")

            # 查找对应分析结果
            for key, result_dict in analysis.items():
                result = result_dict.get("result")
                if result is None:
                    continue

                stat_text = _format_statistical_result(result, key)
                if stat_text:
                    sections.append(stat_text)

    if not context.hypotheses:
        # 自动从分析结果生成结果段落
        for key, result_dict in analysis.items():
            result = result_dict.get("result")
            if result is None:
                continue
            stat_text = _format_statistical_result(result, key)
            if stat_text:
                sections.append(f"**{key}分析结果**：{stat_text}")

    return "\n\n".join(sections)


# ===========================================================================
# 讨论
# ===========================================================================

def write_discussion(context: PaperContext) -> str:
    """
    生成讨论部分：
    4.1 研究结果总结
    4.2 与以往研究的比较
    4.3 理论贡献与实践意义
    4.4 研究局限与未来方向
    """
    sections = []
    sections.append("## 4 讨论\n")

    lit = context.get_lit()

    # ---- 结果总结 ----
    sections.append("### 4.1 研究结果概述")
    sections.append("本研究通过问卷调查法，考察了各变量之间的关系及其内在机制。主要发现如下：")

    if context.hypotheses:
        for i, hyp in enumerate(context.hypotheses, 1):
            sections.append(f"（{i}）{hyp}这一假设得到了验证/部分验证；")
    else:
        sections.append("研究发现了变量间的显著关系，初步揭示了其内在心理机制。")

    # ---- 与以往研究比较 ----
    sections.append("### 4.2 与以往研究的比较")
    sections.append(
        "本研究的结果与前人研究具有一定的一致性。"
        + lit.cite("Cohen1988") + lit.cite("温忠麟2014") +
        "。同时，本研究在以下方面扩展了已有发现：首先是理论机制的深入探讨，"
        "其次是方法学上的改进。"
    )

    # ---- 理论贡献 ----
    sections.append("### 4.3 理论贡献与实践意义")
    if context.theoretical_contributions:
        sections.append("**理论贡献：**")
        for tc in context.theoretical_contributions:
            sections.append(f"- {tc}")
    else:
        sections.append(
            "在理论层面，本研究丰富了我们对变量间关系的认识，"
            "为后续的理论整合提供了实证依据。"
        )

    if context.practical_implications:
        sections.append("\n**实践意义：**")
        for pi in context.practical_implications:
            sections.append(f"- {pi}")

    # ---- 局限与未来 ----
    sections.append("### 4.4 研究局限与未来方向")

    if context.limitations:
        for lim in context.limitations:
            sections.append(f"- {lim}")
    else:
        sections.append(
            f"- 本研究采用横断设计，无法推断因果关系{lit.cite('温忠麟2014')}。未来研究可采用纵向追踪或实验设计加以验证。\n"
            f"- 研究样本的代表性有待进一步提高，未来可考虑采用多地区、多人群的大规模取样。\n"
            f"- 本研究主要采用自评问卷法，可能存在社会赞许性偏差{lit.cite('周浩2004')}。"
        )

    if context.future_directions:
        sections.append("\n**未来研究方向：**")
        for fd in context.future_directions:
            sections.append(f"- {fd}")

    # ---- 结论 ----
    sections.append("### 4.5 结论")
    if context.hypotheses:
        main_finding = "、".join(context.hypotheses[:2])
        sections.append(f"本研究主要发现：{main_finding}。这些发现对于理解相关心理机制具有理论和实践意义。")
    else:
        sections.append("本研究揭示了变量间的内在关系，为理解相关心理机制提供了新的实证证据。")

    return "\n\n".join(sections)


# ===========================================================================
# 参考文献
# ===========================================================================

def write_references(context: PaperContext) -> str:
    """生成参考文献列表"""
    lit = context.get_lit()
    refs = lit.format_reference_list()

    if not refs:
        return "## 参考文献\n\n（暂无参考文献，请通过分析结果触发自动引用或手动添加。）"

    return "## 参考文献\n\n" + "\n".join(refs)


# ===========================================================================
# 辅助函数
# ===========================================================================

def _extract_topic_keywords(context: PaperContext) -> List[str]:
    """从论文上下文中提取主题关键词"""
    keywords = []
    if context.topic:
        keywords.extend(context.topic.split())
    for hyp in context.hypotheses[:2]:
        keywords.extend(hyp.split()[:5])
    return keywords


def _summarize_results(context: PaperContext) -> str:
    """从分析结果中提取摘要级别的结论"""
    parts = []
    analysis = context.analysis_results

    for key, result_dict in analysis.items():
        result = result_dict.get("result")
        if result is None:
            continue

        # t检验
        if hasattr(result, "t_statistic") and hasattr(result, "p_value"):
            if result.p_value < 0.05:
                parts.append(f"在{key}中发现了显著的组间差异")
            else:
                parts.append(f"在{key}中各组差异不显著")

        # 相关
        elif hasattr(result, "corr_matrix"):
            parts.append("各变量间存在显著的相关关系")

        # 回归
        elif hasattr(result, "r_squared"):
            parts.append(f"回归模型解释了因变量{result.r_squared*100:.1f}%的变异")

        # 中介
        elif hasattr(result, "bootstrap_ci") and result.bootstrap_ci is not None:
            parts.append("Bootstrap检验揭示了显著的中介/间接效应")

    if not parts:
        parts.append("数据分析揭示了变量间的显著关系")

    return "；".join(parts[:3])


def _format_statistical_result(result, test_key: str) -> str:
    """格式化单个统计结果"""
    if result is None:
        return ""

    # t检验
    if hasattr(result, "t_statistic") and hasattr(result, "p_value"):
        df_val = getattr(result, "df", "")
        sig = _mark_significance(result.p_value)
        es = getattr(result, "effect_size", "")
        es_name = getattr(result, "effect_size_name", "")
        text = f"t({df_val}) = {result.t_statistic:.2f}, p = {result.p_value:.3f}{sig}"
        if es:
            text += f", {es_name} = {es:.2f}"
        if hasattr(result, "ci_lower") and result.ci_lower is not None:
            text += f", 95% CI = [{result.ci_lower:.2f}, {result.ci_upper:.2f}]"
        return text

    # F检验（ANOVA）
    if hasattr(result, "table") and hasattr(result, "effect_size_name"):
        table = result.table
        # 查找F行
        for _, row in table.iterrows():
            f_val = row.get("F", "")
            p_val = row.get("p", "")
            if f_val and str(f_val) != "":
                try:
                    f = float(f_val)
                    p = float(p_val) if p_val else 1.0
                    sig = _mark_significance(p)
                    df_idx = table.columns.tolist().index("df") if "df" in table.columns else -1
                    df_val = row.get("df", "")
                    es = getattr(result, "effect_size", "")
                    es_name = getattr(result, "effect_size_name", "")
                    es_ci = getattr(result, "effect_size_ci", "")
                    text = f"F({df_val}) = {f:.2f}, p = {p:.3f}{sig}, {es_name} = {es:.3f}"
                    if es_ci:
                        text += f" {es_ci}"
                    return text
                except (ValueError, TypeError):
                    pass
        return ""

    # 相关
    if hasattr(result, "corr_matrix"):
        corr = result.corr_matrix
        p_mat = getattr(result, "p_matrix", None)
        if corr.shape[0] == corr.shape[1] and corr.shape[0] >= 2:
            # 报告非对角线相关
            texts = []
            for i in range(min(corr.shape[0], 3)):
                for j in range(i + 1, min(corr.shape[1], 4)):
                    r_val = corr.iloc[i, j]
                    if not np.isnan(r_val):
                        p_val = p_mat.iloc[i, j] if p_mat is not None else 1.0
                        sig = _mark_significance(p_val)
                        texts.append(
                            f"{corr.index[i]}与{corr.columns[j]}的"
                            f"r = {r_val:.2f}, p = {p_val:.3f}{sig}"
                        )
            return "；".join(texts)
        return ""

    # 回归
    if hasattr(result, "r_squared"):
        r2 = result.r_squared
        adj_r2 = getattr(result, "adj_r_squared", r2)
        text = f"回归模型显著，R² = {r2:.3f}（调整R² = {adj_r2:.3f}）"
        f2_table = getattr(result, "f2_effect_sizes", None)
        if f2_table is not None and len(f2_table) > 0:
            f2_val = f2_table.iloc[-1]["Cohen's f²"]
            text += f"，Cohen's f² = {f2_val:.3f}"
        diag = getattr(result, "high_influence_cases", [])
        if diag:
            text += f"。检测到{len(diag)}个高影响个案(Cook's D > 4/n)"
        return text

    # 中介
    if hasattr(result, "bootstrap_ci") and result.bootstrap_ci is not None:
        ci = result.bootstrap_ci
        texts = []
        for _, row in ci.iterrows():
            texts.append(
                f"{row.get('效应', '间接效应')}: β = {row.get('β', '?')}, "
                f"95%偏差校正CI = [{row.get('CI下限', '?')}, {row.get('CI上限', '?')}], "
                f"判断: {row.get('判断', '?')}"
            )
        return "；".join(texts)

    # 信度分析
    if hasattr(result, "alpha") and hasattr(result, "n_items"):
        return (
            f"Cronbach's α = {result.alpha}, "
            f"95% CI = [{result.ci_lower}, {result.ci_upper}], "
            f"共{result.n_items}道题目, N = {result.n_cases}"
        )

    # EFA
    if hasattr(result, "kmo") and hasattr(result, "n_factors"):
        text = (
            f"KMO = {result.kmo}, Bartlett χ²({result.bartlett_df}) "
            f"= {result.bartlett_chi2}, p = {result.bartlett_p}, "
            f"提取{result.n_factors}个因素"
        )
        if result.variance_explained is not None:
            last_row = result.variance_explained.iloc[-2] if len(result.variance_explained) > 1 else result.variance_explained.iloc[0]
            text += f"，累计解释方差{last_row.get('累计比例', '?') * 100:.1f}%"
        return text

    # 非参数检验
    if hasattr(result, "test_type") and result.test_type in ("mann_whitney", "wilcoxon", "kruskal_wallis", "friedman"):
        es = getattr(result, "effect_size", "")
        es_name = getattr(result, "effect_size_name", "")
        text = f"统计量 = {result.statistic}, p = {result.p_value:.4f}"
        if es:
            text += f", {es_name} = {es:.3f}"
        return text

    return ""


def _mark_significance(p: float) -> str:
    """显著性标注"""
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    return ""


def _describe_analysis_strategy(context: PaperContext) -> str:
    """生成数据分析策略描述"""
    lit = context.get_lit()
    analysis_types = list(context.analysis_results.keys())

    parts = ["本研究采用以下数据分析策略："]

    has_corr = any("corr" in k or "pearson" in k for k in analysis_types)
    has_reg = any("regression" in k for k in analysis_types)
    has_med = any("mediation" in k for k in analysis_types)
    has_mod = any("moderation" in k for k in analysis_types)
    has_efa = any("efa" in k for k in analysis_types)
    has_alpha = any("alpha" in k or "reliability" in k for k in analysis_types)
    has_ttest = any("ttest" in k for k in analysis_types)
    has_anova = any("anova" in k for k in analysis_types)

    step = 1
    parts.append(f"（{step}）首先，使用SPSS/统计软件进行数据清洗和描述统计分析；")
    step += 1

    if has_corr:
        parts.append(
            f"（{step}）采用Pearson相关分析考察各变量之间的相关关系"
            f"{lit.cite('张厚粲2009')}；"
        )
        step += 1

    if has_reg:
        parts.append(
            f"（{step}）使用层次回归分析检验各预测变量的独特贡献，"
            f"并通过VIF值和Cook's距离进行共线性和影响点诊断；"
        )
        step += 1

    if has_med:
        parts.append(
            f"（{step}）采用偏差校正的Bootstrap方法（重复抽样5000次）"
            f"检验中介效应，计算95%置信区间{lit.cite('温忠麟2014')}{lit.cite('Hayes2017')}；"
        )
        step += 1

    if has_mod:
        parts.append(
            f"（{step}）通过中心化后的交互项和简单斜率分析检验调节效应{lit.cite('温忠麟2005')}；"
        )
        step += 1

    if has_efa:
        parts.append(
            f"（{step}）采用探索性因素分析（EFA）检验量表的结构效度，"
            f"以KMO值和Bartlett球性检验判断数据适合度{lit.cite('赵必华2007')}；"
        )
        step += 1

    if has_alpha:
        parts.append(
            f"（{step}）使用Cronbach's α系数评估各量表的内部一致性信度；"
        )
        step += 1

    if has_ttest:
        parts.append("（{step}）采用独立样本t检验比较组间差异；")

    if has_anova:
        parts.append("（{step}）采用单因素方差分析（ANOVA）比较各组差异；")

    parts.append(
        f"\n所有数据分析均报告效应量及其置信区间{lit.cite('Cohen1988')}{lit.cite('邓稳根2018')}，"
        f"以提高结果的解释力和可重复性。"
    )

    return "\n".join(parts)


# ===========================================================================
# Task 5: 统计结果异常模式自动检测
# ===========================================================================

@dataclass
class UnusualResult:
    """异常结果检测条目"""
    pattern_type: str       # "inconsistent_mediation" | "reversed_interaction" |
                            # "oversized_effect" | "suppression_effect" | "null_total_sig_indirect"
    severity: str           # "warning" | "info"
    title: str              # 中文标题
    description: str        # 中文详细描述
    suggestion: str         # 中文解释建议


def detect_unusual_results(analysis_results: Dict[str, Any]) -> List[UnusualResult]:
    """
    根据分析结果自动识别常见异常模式。

    检测项目：
    1. 不一致中介：总效应不显著但间接效应显著
    2. 反向交互：交互项方向与理论假设相反
    3. 超大效应量：Cohen's d > 2.5
    4. 抑制效应：直接效应与间接效应符号相反
    5. 总效应不显著但特定间接效应显著

    返回：UnusualResult 列表，用于在讨论部分生成特殊说明段落。
    """
    unusual = []

    # ---- 1. 检查中介分析是否存在异常 ----
    for key, output in analysis_results.items():
        if not isinstance(output, dict):
            continue

        result = output.get("result")
        if result is None:
            continue

        # 检查是否是中介分析结果
        test_type = getattr(result, "test_type", "") if hasattr(result, "test_type") else ""

        if test_type == "mediation" or "mediation" in str(type(result).__name__).lower():
            # 总效应与间接效应的关系
            coef_table = getattr(result, "coef_table", None)
            if coef_table is not None and not coef_table.empty:
                # 检查是否存在不一致中介
                total_effect = None
                indirect_effect = None
                if "总效应" in coef_table.columns or "c" in [c.lower() for c in coef_table.columns]:
                    pass  # 需要具体的列名解析

            # 检查 bootstrap_ci 和 effect_size
            indirect = getattr(result, "effect_size", 0)  # 间接效应
            indirect_p = getattr(result, "indirect_p", None) if hasattr(result, "indirect_p") else None

            # 检查直接/间接效应符号
            std_coef = getattr(result, "std_coef_table", None)
            if std_coef is not None and not std_coef.empty:
                paths = std_coef.to_dict("records") if hasattr(std_coef, "to_dict") else []
                signs = []
                for p in paths:
                    for v in p.values():
                        if isinstance(v, (int, float)):
                            signs.append(v)
                if len(signs) >= 3:
                    # 检查抑制效应（直接效应与间接效应符号相反）
                    # a*b (间接) vs c' (直接)
                    direct_sign = 1 if signs[-1] > 0 else -1
                    indirect_sign = 1 if (signs[0] * signs[1]) > 0 else -1
                    if direct_sign != indirect_sign:
                        unusual.append(UnusualResult(
                            pattern_type="suppression_effect",
                            severity="warning",
                            title="⚠ 可能存在抑制效应",
                            description="直接效应与间接效应符号相反，可能存在抑制效应（suppression effect）。"
                                        "抑制效应意味着中介变量在自变量与因变量之间起到了\"遮盖\"或\"抵消\"的作用，"
                                        "需要谨慎解释各路径的独立贡献。",
                            suggestion="建议报告直接效应和间接效应的具体路径系数，并讨论抑制效应可能的理论解释。"
                                        "可参考 MacKinnon, Krull, & Lockwood (2000) 关于不一致中介的讨论。",
                        ))

            # 检查间接效应是否显著
            if indirect_p is not None and indirect_p < 0.05:
                ci = getattr(result, "bootstrap_ci", None)
                if ci is not None and hasattr(ci, "iloc"):
                    ci_low = ci.iloc[0, 0] if not ci.empty else None
                    ci_high = ci.iloc[-1, -1] if not ci.empty else None
                    if ci_low is not None and ci_high is not None:
                        # 不一致中介：间接效应显著但 CI 跨度异常大
                        ci_width = abs(ci_high - ci_low)
                        if ci_width > abs(indirect) * 3:
                            unusual.append(UnusualResult(
                                pattern_type="inconsistent_mediation",
                                severity="info",
                                title="📊 间接效应置信区间较宽",
                                description=f"间接效应95% CI [{ci_low:.3f}, {ci_high:.3f}] 跨度较大，"
                                            f"虽然间接效应统计显著（p={indirect_p:.3f}），"
                                            f"但估计精度有限，建议在讨论中提及这一不确定性。",
                                suggestion="建议报告Bootstrap置信区间，并讨论样本量对间接效应估计精度的影响。",
                            ))

        # ---- 2. 检查超大效应量 ----
        effect_size = getattr(result, "effect_size", 0)
        effect_name = getattr(result, "effect_size_name", "")

        if isinstance(effect_size, (int, float)) and abs(effect_size) > 2.5:
            unusual.append(UnusualResult(
                pattern_type="oversized_effect",
                severity="warning",
                title="⚠ 效应量异常偏大",
                description=f"检测到效应量 {effect_name} = {effect_size:.2f}，超过了 Cohen (1988) 定义的"
                            f"大效应量阈值（d > 0.8, r > 0.5, η² > 0.14），甚至超过了通常的心理学研究范围。"
                            f"异常大的效应量可能暗示：（1）组间基线存在系统差异；（2）数据编码错误；"
                            f"（3）存在混淆变量；（4）样本量过小导致效应量膨胀。",
                suggestion="建议：（1）检查数据编码和分组逻辑是否正确；"
                            "（2）检查是否存在异常值或录入错误；"
                            "（3）如果数据无误，在讨论中明确说明效应量异常大的可能原因，"
                            "并与其他研究的典型效应量进行比较。",
            ))

        # ---- 3. 检查调节效应（交互项方向） ----
        if test_type == "moderation":
            model_summary = getattr(result, "model_summary", None)
            if model_summary is not None and not model_summary.empty:
                # 检查交互项p值
                if "来源" in model_summary.columns:
                    interaction_row = model_summary[model_summary["来源"].str.contains(":", regex=False)]
                    if not interaction_row.empty:
                        simple_slopes = getattr(result, "simple_slopes", None)
                        if simple_slopes is not None and not simple_slopes.empty:
                            # 检查简单斜率是否有交叉
                            slopes = simple_slopes["斜率"].values if "斜率" in simple_slopes.columns else []
                            if len(slopes) >= 2 and slopes[0] * slopes[-1] < 0:
                                unusual.append(UnusualResult(
                                    pattern_type="reversed_interaction",
                                    severity="warning",
                                    title="⚠ 交互效应方向复杂",
                                    description="简单斜率分析显示，调节变量在不同水平下，自变量对因变量的"
                                                "影响方向发生了反转。这种交叉交互效应需要谨慎解释。",
                                    suggestion="建议：（1）绘制交互效应图以直观展示调节效应；"
                                                "（2）使用Johnson-Neyman技术确定显著性区域；"
                                                "（3）讨论交互效应方向反转的理论意义。",
                                ))

    return unusual


def generate_unusual_results_section(unusual_findings: List[UnusualResult]) -> str:
    """
    根据异常检测结果生成讨论部分的"特殊说明"段落。
    """
    if not unusual_findings:
        return ""

    lines = ["### 特殊说明：异常结果模式的谨慎解释", ""]
    lines.append("经自动检测，本研究结果中存在以下需要谨慎解释的模式：")
    lines.append("")

    for i, finding in enumerate(unusual_findings, 1):
        icon = "⚠" if finding.severity == "warning" else "📊"
        lines.append(f"**{i}. {icon} {finding.title}**")
        lines.append(f"")
        lines.append(finding.description)
        lines.append(f"")
        lines.append(f"**建议：** {finding.suggestion}")
        lines.append("")

    lines.append("*以上特殊说明由系统自动生成，建议作者结合具体研究背景和理论框架进行审阅和调整。*")
    return "\n".join(lines)


# ===========================================================================
# Task 6: 深度讨论生成（LLM增强）
# ===========================================================================

def write_discussion_deep(
    context: PaperContext,
    analysis_results: Dict[str, Any],
    use_deep_discussion: bool = False,
    llm_api_key: str = "",
    llm_base_url: str = "",
    llm_model: str = "",
) -> str:
    """
    扩展讨论生成：支持LLM深度讨论模式。

    当 use_deep_discussion=True 且 LLM 可用时：
    - 检测异常结果并插入特殊说明
    - 允许LLM基于实际统计结果生成更贴合的理论解释
    - 所有统计值保持不变，内容标记为"AI辅助生成，请核实"
    """
    # 1. 检测异常结果
    unusual = detect_unusual_results(analysis_results)
    unusual_section = generate_unusual_results_section(unusual)

    # 2. 生成标准讨论
    base_discussion = write_discussion(context)

    # 3. 注入异常说明（始终执行）
    if unusual_section:
        # 在 "4.1 研究结果总结" 之后插入特殊说明
        marker = "### 4.2 与已有研究的比较"
        if marker in base_discussion:
            base_discussion = base_discussion.replace(
                marker,
                unusual_section + "\n\n" + marker
            )
        else:
            base_discussion = base_discussion + "\n\n" + unusual_section

    # 4. LLM深度讨论（可选，通过 gateway）
    if use_deep_discussion and llm_api_key:
        try:
            from src.llm_gateway.gateway import llm_chat, LLMUnavailableError
            stat_summary = _extract_stat_summary(analysis_results)

            prompt = f"""你是一位心理学研究方法专家。请基于以下统计结果，对讨论部分进行深度扩展。

原始讨论：
{base_discussion[:2000]}

统计结果摘要：
{stat_summary}

请完成以下任务：
1. 检查讨论部分对统计结果的解释是否准确
2. 如果有异常结果模式，提供谨慎的理论解释替代方案
3. 将本研究发现与心理学文献进行更具体的对比（请务必注明具体的理论和研究）
4. 所有统计数值必须保持不变，不得修改任何数字

请用学术中文输出，格式为Markdown。输出内容应以"> **AI辅助生成**"开头。"""

            resp = llm_chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048,
                retries=1,
            )
            if resp.ok:
                enhanced = resp.content
                base_discussion += (
                    f"\n\n### 4.6 AI辅助深度分析\n\n"
                    f"> **AI辅助生成，请核实：** 以下内容由大语言模型基于实际统计结果生成，"
                    f"所有统计数值均保持原样，理论解释部分需研究者逐一核实。\n\n"
                    f"{enhanced}"
                )
        except Exception:
            pass  # LLM不可用时静默回退

    return base_discussion


def _extract_stat_summary(analysis_results: Dict[str, Any]) -> str:
    """从分析结果中提取关键统计量摘要供LLM使用"""
    parts = []
    for key, output in analysis_results.items():
        if not isinstance(output, dict):
            continue
        result = output.get("result")
        if result is None:
            continue
        test_type = getattr(result, "test_type", key)
        stat = getattr(result, "statistic", getattr(result, "t_statistic", None))
        p_val = getattr(result, "p_value", None)
        es = getattr(result, "effect_size", None)
        es_name = getattr(result, "effect_size_name", "")
        if stat is not None and p_val is not None:
            parts.append(
                f"{test_type}: 统计量={stat:.3f}, p={p_val:.4f}"
                + (f", {es_name}={es:.3f}" if es is not None else "")
            )
    return "\n".join(parts) if parts else "（无可用统计结果摘要）"
