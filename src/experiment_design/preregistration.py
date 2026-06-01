"""预注册文档生成器

根据 AsPredicted.org 标准格式生成心理学研究预注册文档。
支持从实验设计对象自动提取信息填入模板。

参考：AsPredicted.org 模板 (https://aspredicted.org/)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# AsPredicted 标准9题模板
_ASPREDICTED_TEMPLATE = [
    {
        "id": 1,
        "title": "数据收集是否已经开始？",
        "key": "data_collection_started",
        "hint": "如果已开始，请说明已收集数据的情况。",
    },
    {
        "id": 2,
        "title": "主要假设是什么？",
        "key": "hypotheses",
        "hint": "请明确陈述研究假设，包含预期的效应方向和大小（如有可能）。",
    },
    {
        "id": 3,
        "title": "因变量是什么？",
        "key": "dependent_variables",
        "hint": "描述每个因变量的测量方式、计分方法和信度证据。",
    },
    {
        "id": 4,
        "title": "研究条件/分组是什么？",
        "key": "conditions",
        "hint": "描述自变量各水平、分组方式和随机化方法。",
    },
    {
        "id": 5,
        "title": "分析计划是什么？",
        "key": "analysis_plan",
        "hint": "指定每个假设对应的统计检验方法、效应量指标、多重比较校正方法。",
    },
    {
        "id": 6,
        "title": "计划样本量是多少？",
        "key": "sample_size",
        "hint": "说明目标样本量、统计检验力分析依据、数据排除标准。",
    },
    {
        "id": 7,
        "title": "数据排除规则是什么？",
        "key": "exclusion_rules",
        "hint": "说明被试排除标准、异常值处理方法、数据质量检查流程。",
    },
    {
        "id": 8,
        "title": "是否要报告探索性分析？",
        "key": "exploratory_analysis",
        "hint": "区分验证性分析和探索性分析，描述可能的探索方向。",
    },
    {
        "id": 9,
        "title": "其他需要预注册的信息？",
        "key": "other",
        "hint": "如操纵检查、协变量、调节变量、中介变量等。",
    },
]


# OSF 预注册扩展模板（额外题目）
_OSF_EXTENDED_QUESTIONS = [
    {
        "id": 10,
        "title": "研究设计类型",
        "key": "design_type",
        "hint": "实验/准实验/相关/纵向/横断等。",
    },
    {
        "id": 11,
        "title": "随机化方法",
        "key": "randomization_method",
        "hint": "描述使用的随机化程序（如 Qualtrics 随机分组、block randomization 等）。",
    },
    {
        "id": 12,
        "title": "盲法设置",
        "key": "blinding",
        "hint": "单盲/双盲/非盲，被试是否知道研究假设。",
    },
    {
        "id": 13,
        "title": "操纵检查",
        "key": "manipulation_check",
        "hint": "如何进行自变量操纵有效性的检查。",
    },
]


@dataclass
class PreregistrationDoc:
    """预注册文档"""
    title: str
    author: str
    date: str
    template: str  # "aspredicted" or "osf"
    sections: List[Dict]
    metadata: Dict = field(default_factory=dict)

    def to_markdown(self) -> str:
        """生成 Markdown 格式的预注册文档"""
        lines = [
            f"# 预注册文档",
            f"",
            f"**研究标题**：{self.title}",
            f"**作者**：{self.author}",
            f"**预注册日期**：{self.date}",
            f"**模板**：{self.template.upper()}",
            f"",
            f"---",
            f"",
        ]

        for sec in self.sections:
            lines.append(f"## {sec['id']}. {sec['title']}")
            lines.append("")
            lines.append(sec.get("content", "（待填写）"))
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(
            f"> 本文档由心理学研究工具系统自动生成（{self.date}）。"
            f"研究者应在数据收集开始前完成所有内容的确认和补充。"
        )

        return "\n".join(lines)

    def to_text(self) -> str:
        """生成纯文本格式"""
        lines = [
            f"预注册文档",
            f"{'=' * 50}",
            f"研究标题：{self.title}",
            f"作者：{self.author}",
            f"预注册日期：{self.date}",
            f"模板：{self.template.upper()}",
            f"{'=' * 50}",
            f"",
        ]
        for sec in self.sections:
            lines.append(f"--- {sec['id']}. {sec['title']} ---")
            lines.append(sec.get("content", "（待填写）"))
            lines.append("")
        return "\n".join(lines)


def generate_preregistration(
    title: str = "",
    author: str = "",
    hypotheses: str = "",
    dependent_variables: str = "",
    conditions: str = "",
    analysis_plan: str = "",
    sample_size_info: str = "",
    exclusion_rules: str = "",
    exploratory: str = "",
    other: str = "",
    design_type: str = "",
    randomization: str = "",
    blinding: str = "",
    manipulation_check: str = "",
    template: str = "aspredicted",
    experiment_design: Optional[Dict] = None,
) -> PreregistrationDoc:
    """
    生成 AsPredicted/OSF 格式的预注册文档。

    参数：
        title: 研究标题
        author: 研究者姓名
        hypotheses: 研究假设
        dependent_variables: 因变量描述
        conditions: 实验条件/分组
        analysis_plan: 统计分析计划
        sample_size_info: 样本量及检验力分析依据
        exclusion_rules: 数据排除标准
        exploratory: 探索性分析计划
        other: 其他预注册信息
        design_type: 研究设计类型
        randomization: 随机化方法
        blinding: 盲法设置
        manipulation_check: 操纵检查
        template: "aspredicted" 或 "osf"
        experiment_design: 实验设计结果字典（可选，从中自动提取信息）

    返回：
        PreregistrationDoc 对象，可调用 .to_markdown() 或 .to_text() 生成文档。
    """
    # 如果提供了实验设计对象，自动提取信息
    if experiment_design:
        extracted = _extract_from_design(experiment_design)
        if not title and extracted.get("title"):
            title = extracted["title"]
        if not hypotheses and extracted.get("hypotheses"):
            hypotheses = extracted["hypotheses"]
        if not dependent_variables and extracted.get("dependent_variables"):
            dependent_variables = extracted["dependent_variables"]
        if not conditions and extracted.get("conditions"):
            conditions = extracted["conditions"]
        if not analysis_plan and extracted.get("analysis_plan"):
            analysis_plan = extracted["analysis_plan"]
        if not sample_size_info and extracted.get("sample_size_info"):
            sample_size_info = extracted["sample_size_info"]

    # 构建各节
    content_map = {
        "data_collection_started": "否，数据收集尚未开始。本预注册文档在数据收集前提交。",
        "hypotheses": hypotheses or "（请明确陈述研究假设）",
        "dependent_variables": dependent_variables or "（请描述各个因变量及其测量方式）",
        "conditions": conditions or "（请描述实验条件/分组设置）",
        "analysis_plan": analysis_plan or "（请说明每个假设对应的统计分析方法）",
        "sample_size": sample_size_info or "（请说明计划样本量和检验力分析依据）",
        "exclusion_rules": exclusion_rules or _default_exclusion_rules(),
        "exploratory_analysis": exploratory or "本研究主要进行验证性分析。如有可能的探索性分析，将明确标注为探索性。",
        "other": other or "无。",
    }

    sections = []
    for q in _ASPREDICTED_TEMPLATE:
        sections.append({
            "id": q["id"],
            "title": q["title"],
            "key": q["key"],
            "hint": q["hint"],
            "content": content_map.get(q["key"], "（待填写）"),
        })

    if template.lower() == "osf":
        osf_map = {
            "design_type": design_type or _detect_design_type(experiment_design),
            "randomization_method": randomization or "（请描述随机化方法）",
            "blinding": blinding or "（请说明盲法设置）",
            "manipulation_check": manipulation_check or "（如适用，请描述操纵检查方法）",
        }
        for q in _OSF_EXTENDED_QUESTIONS:
            sections.append({
                "id": q["id"],
                "title": q["title"],
                "key": q["key"],
                "hint": q["hint"],
                "content": osf_map.get(q["key"], "（待填写）"),
            })

    return PreregistrationDoc(
        title=title or "（研究标题）",
        author=author or "（研究者）",
        date=datetime.now().strftime("%Y-%m-%d"),
        template=template.lower(),
        sections=sections,
        metadata={
            "generator": "心理学研究工具系统 v2.0",
            "standard": "AsPredicted.org" if template.lower() == "aspredicted" else "OSF Preregistration",
        },
    )


def generate_preregistration_from_analysis(
    analysis_type: str,
    research_question: str = "",
    variables: Dict[str, str] = None,
    sample_n: int = None,
    power_info: Dict = None,
) -> PreregistrationDoc:
    """
    从分析计划反向生成预注册文档（适用于已有分析方案的情况）。

    参数：
        analysis_type: 分析类型（如 "independent t-test", "one-way ANOVA"）
        research_question: 研究问题
        variables: 变量映射 {"iv": "自变量名", "dv": "因变量名"}
        sample_n: 计划样本量
        power_info: 检验力分析结果
    """
    vars_ = variables or {}

    # 自动生成假设语句
    iv_name = vars_.get("iv", "自变量")
    dv_name = vars_.get("dv", "因变量")

    if "t-test" in analysis_type.lower() or "t检验" in analysis_type:
        hypotheses = (
            f"H1：{iv_name}的不同水平在{dv_name}上存在显著差异。"
            f"预期效应量为中等（Cohen's d = 0.50）。"
        )
        analysis = (
            f"采用独立样本t检验比较{iv_name}两组在{dv_name}上的差异。"
            f"效应量使用Cohen's d及其95%置信区间。"
            f"显著性水平α = 0.05（双侧）。"
        )
    elif "anova" in analysis_type.lower() or "方差分析" in analysis_type:
        hypotheses = (
            f"H1：{iv_name}的不同水平在{dv_name}上存在显著差异。"
            f"预期至少两组间差异具有中等效应量（η² ≥ 0.06）。"
        )
        analysis = (
            f"采用单因素被试间方差分析（one-way between-subjects ANOVA）。"
            f"违反球形假设时使用Greenhouse-Geisser校正。"
            f"事后多重比较使用Tukey HSD法。"
            f"效应量使用偏η²及95%置信区间。"
        )
    elif "correlation" in analysis_type.lower() or "相关" in analysis_type:
        v1 = vars_.get("var1", "变量X")
        v2 = vars_.get("var2", "变量Y")
        hypotheses = f"H1：{v1}与{v2}之间存在显著相关关系。预期r ≥ 0.30。"
        analysis = (
            f"采用Pearson积差相关分析。"
            f"相关系数报告95%置信区间（Fisher z转换法）。"
            f"显著性水平α = 0.05（双侧）。"
        )
    elif "regression" in analysis_type.lower() or "回归" in analysis_type:
        hypotheses = (
            f"H1：{iv_name}能够显著预测{dv_name}。"
            f"预期R² ≥ 0.10。"
        )
        analysis = (
            f"采用（多元）线性回归分析。"
            f"报告标准化回归系数β、R²、调整R²。"
            f"检验多重共线性（VIF < 5）。"
        )
    else:
        hypotheses = f"H1：{iv_name}对{dv_name}存在显著效应。"
        analysis = "（请指定具体分析方法）"

    # 样本量
    n_info = ""
    if sample_n:
        n_info = f"计划收集有效样本 N = {sample_n}。"
    if power_info:
        pw = power_info
        n_info += (
            f"检验力分析：效应量 {pw.get('effect_size', '?')}、"
            f"α = {pw.get('alpha', 0.05)}、"
            f"检验力 1-β = {pw.get('power', 0.80)}，"
            f"所需样本量 N = {pw.get('required_n', sample_n or '?')}。"
        )

    return generate_preregistration(
        title=research_question or "（研究标题）",
        author="",
        hypotheses=hypotheses,
        dependent_variables=f"{dv_name}：{vars_.get('dv_desc', '（请描述测量工具）')}",
        conditions=f"{iv_name}：{vars_.get('iv_desc', '（请描述各水平/条件）')}",
        analysis_plan=analysis,
        sample_size_info=n_info or f"计划样本量：N = {sample_n or '（待确定）'}。",
    )


def validate_preregistration(doc: PreregistrationDoc) -> Dict:
    """
    验证预注册文档的完整性。

    返回包含完整性和缺失项信息的字典。
    """
    issues = []
    required = ["hypotheses", "dependent_variables", "conditions", "analysis_plan", "sample_size"]

    for sec in doc.sections:
        content = sec.get("content", "").strip()
        if sec["key"] in required and ("待填写" in content or not content):
            issues.append({
                "section": sec["id"],
                "title": sec["title"],
                "severity": "error",
                "msg": f"第{sec['id']}题「{sec['title']}」尚未填写完整。",
            })

    completeness = 1.0 - len([i for i in issues if i["severity"] == "error"]) / max(1, len(required))
    return {
        "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
        "completeness": round(completeness, 2),
        "issues": issues,
        "suggestion": (
            "预注册文档已完整填写，可以提交至 AsPredicted.org 或 OSF。"
            if completeness >= 1.0
            else f"预注册文档完成度 {completeness:.0%}，请在数据收集前补充缺失内容。"
        ),
    }


# ============================================================
# 内部辅助函数
# ============================================================


def _extract_from_design(design: Dict) -> Dict:
    """从实验设计对象中提取预注册信息"""
    extracted = {}

    # 标题
    if "title" in design:
        extracted["title"] = design["title"]
    elif "research_question" in design:
        extracted["title"] = design["research_question"]

    # 假设
    hypotheses_parts = []
    if "hypotheses" in design:
        for h in design["hypotheses"] if isinstance(design["hypotheses"], list) else [design["hypotheses"]]:
            hypotheses_parts.append(str(h))
    if hypotheses_parts:
        extracted["hypotheses"] = "\n".join(hypotheses_parts)

    # 因变量
    if "dependent_variables" in design:
        dvs = design["dependent_variables"]
        if isinstance(dvs, list):
            dv_lines = []
            for dv in dvs:
                if isinstance(dv, dict):
                    dv_lines.append(
                        f"- {dv.get('name', '?')}：{dv.get('measurement', dv.get('desc', ''))}"
                    )
                else:
                    dv_lines.append(f"- {dv}")
            extracted["dependent_variables"] = "\n".join(dv_lines)
        else:
            extracted["dependent_variables"] = str(dvs)

    # 条件
    if "conditions" in design:
        conds = design["conditions"]
        if isinstance(conds, list):
            extracted["conditions"] = "\n".join(f"- {c}" for c in conds)
        else:
            extracted["conditions"] = str(conds)

    # 分析计划
    if "analysis_plan" in design:
        extracted["analysis_plan"] = str(design["analysis_plan"])
    elif "analysis_type" in design:
        extracted["analysis_plan"] = f"采用{design['analysis_type']}进行分析。"

    # 样本量
    if "sample_size" in design:
        n = design["sample_size"]
        if isinstance(n, dict):
            extracted["sample_size_info"] = (
                f"计划样本量 N = {n.get('total', '?')}。\n"
                f"检验力分析：{n.get('power_analysis', '')}"
            )
        else:
            extracted["sample_size_info"] = f"计划样本量 N = {n}。"

    if "power" in design:
        pw = design["power"]
        if isinstance(pw, dict) and not extracted.get("sample_size_info"):
            extracted["sample_size_info"] = (
                f"检验力分析：效应量 = {pw.get('effect_size', '?')}、"
                f"α = {pw.get('alpha', 0.05)}、"
                f"1-β = {pw.get('power', 0.80)}、"
                f"所需N = {pw.get('required_n', '?')}。"
            )

    return extracted


def _default_exclusion_rules() -> str:
    """生成默认的数据排除规则"""
    return (
        "数据排除标准：\n"
        "1. 未完成全部实验试次的被试数据将被排除\n"
        "2. 反应时低于200ms（预期反应）或高于3SD的被试数据将被标记\n"
        "3. 未通过注意力检查（attention check）的被试数据将被排除\n"
        "4. 作答呈现明显规律（如连续10题选择同一选项）的数据将被排除\n"
        "\n异常值处理：\n"
        "反应时分析使用中位数取代均值以降低异常值影响，或使用Winsorized方法处理。"
    )


def _detect_design_type(design: Optional[Dict]) -> str:
    """从设计对象检测研究设计类型"""
    if not design:
        return "（请说明研究设计类型）"

    design_str = str(design).lower()
    if "between" in design_str or "被试间" in design_str:
        return "被试间设计（Between-subjects design）"
    elif "within" in design_str or "被试内" in design_str or "重复测量" in design_str:
        return "被试内设计（Within-subjects design / Repeated measures）"
    elif "mixed" in design_str or "混合" in design_str:
        return "混合设计（Mixed design）"
    else:
        return "（请说明研究设计类型：实验/准实验/相关/纵向/横断）"
