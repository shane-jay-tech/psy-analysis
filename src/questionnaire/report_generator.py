"""设计报告生成器：将设计结果格式化为完整的 Markdown/HTML 报告"""

from typing import Dict


def generate_design_report(design: Dict) -> str:
    """
    生成完整的问卷设计报告（Markdown 格式），
    可用于在 Streamlit 中显示和导出 HTML。
    """
    parts = []

    # ====================
    # 封面信息
    # ====================
    parts.append(f"# 📋 心理学问卷设计报告\n")
    parts.append(f"## 研究问题\n")
    parts.append(f"> {design['research_question']}\n")

    # ====================
    # 构念识别
    # ====================
    parts.append("---\n")
    parts.append("## 🔍 构念识别与设计思路\n")

    if design["is_exact_match"]:
        construct = design["matched_construct"]
        parts.append(f"**识别结果：** 在研究问题中识别到核心构念「**{design['construct_name']}**」")
        parts.append(f"（{construct['name_en']}），属于 **{construct['domain']}** 领域。\n")
        parts.append(f"**匹配方式：** {design['match_reason']}\n")

        if construct.get("established_scales"):
            parts.append("**已有成熟量表参考：**")
            for scale in construct["established_scales"]:
                parts.append(f"- {scale}")
            parts.append("")
            parts.append("本研究工具的设计参考了上述成熟量表的维度结构和题目编制方式，但并非简单翻译或改编，而是基于本研究的具体目标和被试群体进行独立设计。\n")
    else:
        parts.append(f"**识别结果：** {design['match_reason']}\n")
        parts.append(f"将基于通用心理测量学原则，构建「{design['construct_name']}」的测量框架。\n")

    # ====================
    # 构念定义与理论框架
    # ====================
    parts.append("---\n")
    parts.append("## 📖 构念定义与理论框架\n")

    construct = design.get("matched_construct") or {}
    definition = (
        construct.get("definition")
        or design.get("llm_definition")
        or f"{design['construct_name']}的定义将基于文献综述和理论分析确定。"
    )
    parts.append(f"### 构念定义\n{definition}\n")

    parts.append("### 维度结构\n")
    dims = design["dimensions_used"]
    parts.append(f"本问卷包含 **{len(dims)}** 个理论维度：\n")
    for i, dim in enumerate(dims):
        parts.append(f"**{i+1}. {dim['name']}**")
        parts.append(f"   - 描述：{dim['desc']}")
        parts.append(f"   - 题目数：{dim.get('item_count', '-')} 题")
        if dim.get("example"):
            parts.append(f"   - 示例：\"{dim['example']}\"")
        parts.append("")

    # 维度结构图（ASCII art）
    parts.append("### 维度结构图\n")
    parts.append("```")
    parts.append(f"{design['construct_name']}")
    for dim in dims:
        parts.append(f"├── {dim['name']} ({dim.get('item_count', '?')}题)")
    parts.append("```\n")

    # ====================
    # 量表配置
    # ====================
    parts.append("---\n")
    parts.append("## ⚙ 量表技术参数\n")

    sc = design["scale_config"]
    template = design["template_used"]
    parts.append(f"| 参数 | 设置 |")
    parts.append(f"|------|------|")
    parts.append(f"| 题型 | {template['name']} |")
    parts.append(f"| 量表点数 | {sc['points']} 点 Likert |")
    parts.append(f"| 总题量 | {sc['n_items']} 题 |")
    parts.append(f"| 维度数 | {sc['n_dimensions']} |")
    parts.append(f"| 反向题数 | {sc['n_reverse']} 题（{sc['reverse_ratio']}） |")
    parts.append(f"| 预计用时 | 约 {max(3, sc['n_items'] // 3)} 分钟 |")
    parts.append("")

    # 锚定标签
    parts.append("### 评分锚定\n")
    for anchor in sc["anchors"]:
        parts.append(f"- {anchor}")
    parts.append("")

    # ====================
    # 指导语
    # ====================
    parts.append("---\n")
    parts.append("## 📝 问卷指导语\n")
    parts.append(f"```")
    parts.append(design["instructions"])
    parts.append(f"```\n")

    # ====================
    # 完整问卷
    # ====================
    parts.append("---\n")
    parts.append("## 📋 问卷题目\n")

    # 按维度分组展示
    current_dim = None
    for item in design["items"]:
        if item["dimension"] != current_dim:
            current_dim = item["dimension"]
            parts.append(f"\n### 📌 {current_dim}\n")
        rev_mark = " 🔄" if item["reverse"] else ""
        parts.append(f"**Q{item['index']}.** {item['text']}{rev_mark}")
        parts.append(f"   [1] [2] [3] [4] [5]\n")

    # ====================
    # 计分方式
    # ====================
    parts.append("---\n")
    parts.append("## 🔢 计分方式\n")
    parts.append(design["scoring"])
    parts.append("")

    # 标注反向题
    rev_items = [item for item in design["items"] if item["reverse"]]
    if rev_items:
        parts.append("### 反向计分题号\n")
        parts.append(f"以下 {len(rev_items)} 道题目需要反向计分：")
        parts.append(", ".join([f"Q{item['index']}" for item in rev_items]))
        parts.append("")

    # ====================
    # 信效度保障
    # ====================
    parts.append("---\n")
    parts.append("## ✅ 信效度保障策略\n")

    psych = design["psychometrics"]
    for section, content in psych.items():
        parts.append(f"### {section}\n")
        parts.append(content)
        parts.append("")

    # ====================
    # 施测建议
    # ====================
    parts.append("---\n")
    parts.append("## 🎯 施测建议\n")
    parts.append(f"- **施测对象**：根据研究问题确定的目标群体")
    parts.append(f"- **施测方式**：纸笔或在线问卷（推荐使用问卷星/Qualtrics等平台）")
    parts.append(f"- **施测时间**：{max(3, design['scale_config']['n_items'] // 3)}-{max(5, design['scale_config']['n_items'] // 2)} 分钟")
    parts.append(f"- **预测试**：正式施测前，建议选取30-50名目标被试进行预测试，检验题目理解度和信度")
    parts.append(f"- **正式施测样本量**：建议 N ≥ {design['scale_config']['n_items'] * 10}（基于EFA的样本量要求）")
    parts.append("")

    # ====================
    # 参考文献
    # ====================
    has_construct_refs = construct and construct.get("references")
    has_llm_refs = bool(design.get("llm_references"))

    if has_construct_refs or has_llm_refs:
        parts.append("---\n")
        parts.append("## 📚 参考文献\n")
        if has_construct_refs:
            for i, ref in enumerate(construct["references"]):
                parts.append(f"{i+1}. {ref}")
        if has_llm_refs:
            if has_construct_refs:
                parts.append("")
            parts.append("*以下为 LLM 生成的参考文献，请务必核实后再引用：*\n")
            for i, ref in enumerate(design.get("llm_references", [])):
                parts.append(f"{i+1}. {ref}")
        parts.append("")

    # 通用参考文献
    parts.append("### 测量学通用参考文献\n")
    general_refs = [
        "DeVellis, R. F., & Thorpe, C. T. (2021). Scale Development: Theory and Applications (5th ed.). SAGE.",
        "Nunnally, J. C., & Bernstein, I. H. (1994). Psychometric Theory (3rd ed.). McGraw-Hill.",
        "Furr, R. M. (2017). Psychometrics: An Introduction (3rd ed.). SAGE.",
        "Haynes, S. N., Richard, D. C. S., & Kubany, E. S. (1995). Content validity in psychological assessment: A functional approach to concepts and methods. Psychological Assessment, 7(3), 238-247.",
        "Hinkin, T. R. (1998). A brief tutorial on the development of measures for use in survey questionnaires. Organizational Research Methods, 1(1), 104-121.",
        "Hu, L., & Bentler, P. M. (1999). Cutoff criteria for fit indexes in covariance structure analysis. Structural Equation Modeling, 6(1), 1-55.",
    ]
    for i, ref in enumerate(general_refs):
        parts.append(f"{i+1}. {ref}")

    return "\n".join(parts)


def generate_design_summary(design: Dict) -> str:
    """生成简短的设计摘要（用于UI展示）"""
    sc = design["scale_config"]
    dims = design["dimensions_used"]

    lines = [
        f"## 问卷设计摘要\n",
        f"**构念**：{design['construct_name']}",
        f"**匹配方式**：{'精确匹配已有构念知识库' if design['is_exact_match'] else '基于关键词推断'}",
        f"**题型**：{design['template_used']['name']}（{sc['points']}点计分）",
        f"**题量**：{sc['n_items']} 题（{sc['n_dimensions']}个维度）",
        f"**反向题**：{sc['n_reverse']} 题",
        f"**预计用时**：约 {max(3, sc['n_items'] // 3)} 分钟\n",
        "### 维度分配：",
    ]

    for dim in dims:
        n = dim.get("item_count", "?")
        lines.append(f"- {dim['name']}：{n} 题")

    return "\n".join(lines)
