"""信效度保障策略：内容效度、结构效度、信度评估指南"""

from typing import Dict


def content_validity_guidance(construct: dict) -> str:
    """
    内容效度保障指南。
    内容效度指题目能否充分覆盖构念的各个维度。
    """
    dims = construct.get("dimensions", [])
    n_dims = len(dims)

    if n_dims == 0:
        return (
            "内容效度是问卷质量的基石，确保题目真正测量了目标构念。\n\n"
            "**保障策略：**\n"
            "1. 基于明确的构念定义生成题目\n"
            "2. 邀请3-5名相关领域专家评审题目与构念的匹配度\n"
            "3. 计算内容效度指数 (CVI)：专家评定\"相关\"的比例 ≥ 0.80 为可接受\n"
            "4. 检查题目是否覆盖了构念的所有理论维度（无遗漏、无冗余）"
        )

    dim_names = [d["name"] for d in dims]
    dim_list = "、".join(dim_names)

    return (
        f"本构念包含 {n_dims} 个维度：{dim_list}。\n\n"
        "**内容效度保障策略：**\n\n"
        "1. **维度-题目匹配表**：将每道题映射到对应维度，确保没有维度被遗漏\n"
        "2. **专家评审法**：邀请3-5名相关领域专家评审：\n"
        "   - 每道题是否测量了目标维度？（1=不相关, 4=非常相关）\n"
        "   - 计算内容效度指数 (I-CVI ≥ 0.78 为可接受)\n"
        "   - 量表水平内容效度指数 (S-CVI/Ave ≥ 0.90)\n"
        "3. **认知访谈**：选取5-8名目标被试进行认知访谈，检验题目是否被正确理解\n"
        "4. **可读性检查**：确保题目语言适合目标人群的阅读水平\n"
        "   - 避免双重否定（如\"我不认为我不应该...\"）\n"
        "   - 避免专业术语（除非被试群体为专业人员）\n"
        "   - 每道题只包含一个核心概念（避免双重负载）\n"
        "5. **题目冗余度检查**：同一维度内题目之间的相关性应在0.3-0.7之间\n"
        "   - r < 0.3：题目可能不测同一维度\n"
        "   - r > 0.7：题目可能过于重复，考虑删减"
    )


def face_validity_checklist() -> list:
    """
    表面效度检查清单。
    表面效度是问卷"看起来"是否测量了它应该测量的东西。
    """
    return [
        "题目语言是否清晰易懂，没有歧义？",
        "题目是否避免了诱导性表述（如\"大多数人都认为...\"）？",
        "题目是否避免了社会称许性暗示（如\"你是一个好人吗\"）？",
        "量表标题和指导语是否清晰说明了填写方式？",
        "是否避免了过于极端或敏感的表述？",
        "排版是否清晰（题目间距合理、字体大小合适）？",
    ]


def construct_validity_guidance(construct: dict) -> str:
    """
    结构效度保障指南。
    结构效度指问卷分数是否反映了理论假设的构念结构。
    """
    dims = construct.get("dimensions", [])
    n_dims = len(dims)
    total_items = sum(d.get("item_count", 5) for d in dims)

    guidance = [
        "结构效度用于验证问卷的理论因子结构是否与实际数据吻合。\n",
        "**探索性因素分析 (EFA)：**\n"
        f"- 建议样本量：N ≥ {total_items * 10}（题目数的10倍以上，最少200）\n"
        "- 前提检验：KMO ≥ 0.80 为良好，Bartlett球形检验p < 0.05\n"
        "- 抽取方法：主成分分析（PCA）或主轴因子法（PAF）\n"
        "- 旋转方法：理论上维度相关时用斜交旋转（如Promax），独立时用正交旋转（如Varimax）\n"
        "- 保留标准：特征值 > 1（Kaiser准则）+ 碎石图拐点\n"
        f"- 预期抽取 {n_dims} 个因子，解释总方差 ≥ 60%\n"
        "- 保留标准：因子载荷 ≥ 0.40，交叉载荷 < 0.30\n\n"
        "**验证性因素分析 (CFA)：**\n"
        "- 在EFA后用独立样本进行CFA验证\n"
        "- 拟合指标标准：\n"
        "  χ²/df < 3（良好）, < 5（可接受）\n"
        "  CFI ≥ 0.90（可接受）, ≥ 0.95（良好）\n"
        "  TLI ≥ 0.90（可接受）, ≥ 0.95（良好）\n"
        "  RMSEA < 0.08（可接受）, < 0.05（良好）, 90%CI不包含0.08以上\n"
        "  SRMR < 0.08（良好）\n\n"
        "**聚合效度与区分效度：**\n"
        "- 平均方差抽取量 (AVE) ≥ 0.50 表示聚合效度良好\n"
        "- AVE的平方根 > 维度间相关系数 表示区分效度良好\n"
        "- 组合信度 (CR) ≥ 0.70"
    ]
    return "\n".join(guidance)


def reliability_guidance(construct: dict) -> str:
    """
    信度保障指南。
    """
    return (
        "**内部一致性信度 (Cronbach's α)：**\n"
        "- α ≥ 0.90：优秀\n"
        "- α ≥ 0.80：良好\n"
        "- α ≥ 0.70：可接受（探索性研究可放宽至0.60）\n"
        "- α < 0.60：需要修订\n\n"
        "注意事项：\n"
        "1. α受题量影响，题量多α偏高。推荐同时报告平均题间相关 (0.15-0.50为理想)\n"
        "2. 每个维度应单独计算α，而非整个量表一个α\n"
        "3. 查看\"删除该项后的α\" (alpha-if-item-deleted)：若删除某题后α显著提升，考虑删题\n"
        "4. 纠正题总相关 (CITC) < 0.30 的题目应考虑删除\n\n"
        "**重测信度：**\n"
        "- 间隔2-4周对同一批被试重测，计算两次得分的组内相关系数 (ICC)\n"
        "- ICC ≥ 0.70 为可接受（适用于相对稳定的构念如人格）\n"
        "- 状态型构念（如焦虑、心情）的重测信度预期较低，属正常现象\n\n"
        "**分半信度：**\n"
        "- 将题目按奇偶序号分为两半，计算Spearman-Brown校正后的相关系数\n"
        "- ≥ 0.70 为可接受"
    )


def social_desirability_guidance() -> str:
    """
    社会称许性控制建议。
    """
    return (
        "社会称许性是指被试倾向于按照社会期望而非真实感受作答。\n\n"
        "**控制策略：**\n"
        "1. **匿名性保证**：在指导语中强调匿名性和保密性\n"
        "   \"本问卷采用匿名作答，答案无对错之分，请根据真实感受回答。\"\n"
        "2. **题目措辞**：减少评价性语言\n"
        "   - 避免\"你应该...\" / \"好的做法是...\"\n"
        "   - 使用中性描述：\"我有时会...\" 而非 \"我做...对吗\"\n"
        "3. **嵌入社会称许性量表**：\n"
        "   - Marlowe-Crowne社会称许性量表（简版13题）\n"
        "   - 若社会称许性得分与构念得分显著相关，分析时将其作为协变量控制\n"
        "4. **加入测谎题**：\n"
        "   - \"我从未说过谎\"（几乎所有人都会说过的谎）\n"
        "   - \"我有时会犯错\"（反向题，几乎所有人都会犯错）\n"
        "   - 若被试在这类题目上出现极端不一致的回答，标记为可疑作答\n"
        "5. **平衡措辞**：使用正向和反向题目减少默认同意偏差"
    )


def generate_psychometric_report(
    construct: dict,
    academic_data: dict = None,
) -> Dict[str, str]:
    """生成完整的信效度策略报告，可选集成学术文献数据"""
    report = {
        "内容效度": content_validity_guidance(construct),
        "表面效度": "请逐项检查以下表面效度要求：\n" + "\n".join(
            f"  ☐ {item}" for item in face_validity_checklist()
        ),
        "结构效度": construct_validity_guidance(construct),
        "信度": reliability_guidance(construct),
        "社会称许性控制": social_desirability_guidance(),
    }

    # 学术文献增强
    if academic_data and academic_data.get("established_scales"):
        from .academic_literature import generate_academic_report
        report["学术文献参考"] = generate_academic_report(
            construct.get("name_zh", ""),
            academic_data,
        )

    return report
