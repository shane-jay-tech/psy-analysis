"""实验设计系统 — 核心设计引擎

根据用户输入的研究方向和目标人群等信息，生成符合心理学标准的完整实验设计方案。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import random

from .power_analysis import calculate_sample_size, format_power_report, PowerResult
from .procedure_builder import build_full_procedure, ExperimentProcedure
from .experiment_templates import (
    DesignTemplate, get_template, recommend_template, TEMPLATES
)


@dataclass
class ExperimentDesign:
    """完整的实验设计方案"""
    # 基本框架
    title: str = ""
    design_type: str = ""                        # 设计类型标识
    design_type_zh: str = ""                     # 设计类型中文名
    template_id: str = ""                        # 使用的模板ID
    template_name: str = ""                      # 模板名称

    # 研究问题与假设
    background: str = ""                         # 研究背景
    research_questions: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)

    # 变量定义
    independent_vars: List[Dict] = field(default_factory=list)
    dependent_vars: List[Dict] = field(default_factory=list)
    control_vars: List[str] = field(default_factory=list)

    # 被试
    target_population: str = ""                  # 目标人群
    inclusion_criteria: List[str] = field(default_factory=list)
    exclusion_criteria: List[str] = field(default_factory=list)
    n_subjects: int = 0
    n_per_group: int = 0
    n_groups: int = 0

    # 效力分析
    power_result: Optional[PowerResult] = None

    # 材料
    materials: List[Dict] = field(default_factory=list)
    apparatus: List[str] = field(default_factory=list)

    # 程序
    procedure: Optional[ExperimentProcedure] = None

    # 数据分析
    analysis_plan: List[str] = field(default_factory=list)
    analysis_plan_detailed: str = ""

    # 伦理
    ethics: List[str] = field(default_factory=list)

    # 参考文献
    references: List[str] = field(default_factory=list)

    # 附加信息
    notes: List[str] = field(default_factory=list)
    budget_estimate: str = ""


class ExperimentDesignEngine:
    """实验设计引擎"""

    def __init__(self):
        self.design: Optional[ExperimentDesign] = None
        self.logs: List[str] = []

    def design_experiment(
        self,
        topic: str,
        target_population: str = "",
        hypotheses: List[str] = None,
        design_type_hint: str = "",
        n_subjects_hint: int = 0,
        n_groups_hint: int = 0,
        materials_hint: List[Dict] = None,
        ivs: List[str] = None,
        dvs: List[str] = None,
        power: float = 0.80,
        alpha: float = 0.05,
        effect_size_expected: str = "medium",
        include_budget: bool = False,
    ) -> ExperimentDesign:
        """设计完整的心理学实验。

        参数:
            topic: 研究主题/方向
            target_population: 目标人群描述
            hypotheses: 研究假设列表
            design_type_hint: 设计类型提示（如"被试间"、"被试内"、"混合"、"问卷"）
            n_subjects_hint: 被试量提示（0=自动计算）
            n_groups_hint: 组数提示
            materials_hint: 材料提示 [{"name": ..., "items": ..., "alpha": ...}]
            ivs: 自变量名称列表
            dvs: 因变量名称列表
            power: 目标统计效力
            alpha: 显著性水平
            effect_size_expected: "small" | "medium" | "large"
            include_budget: 是否包含预算估算
        """
        self.logs = []
        self._log(f"开始设计实验: {topic}")

        design = ExperimentDesign()

        # 1. 推荐设计模板
        keywords = self._extract_keywords(topic, hypotheses or [])
        templates = recommend_template(topic, keywords)
        template = self._select_template(templates, design_type_hint)
        design.template_id = template.id
        design.template_name = template.name
        design.design_type = template.design_type
        design.design_type_zh = _design_type_to_chinese(template.design_type)
        self._log(f"选择设计模板: {template.name} ({design.design_type_zh})")

        # 2. 生成标题
        design.title = self._generate_title(topic, template)

        # 3. 研究背景（基于模板描述生成）
        design.background = self._generate_background(topic, template)

        # 4. 研究假设
        design.research_questions = [f"RQ{i+1}: {hyp}" for i, hyp in enumerate(hypotheses)] if hypotheses else self._generate_default_rq(topic, template)
        design.hypotheses = hypotheses or self._generate_default_hypotheses(topic, template)

        # 5. 变量定义
        design.independent_vars = self._define_ivs(template, ivs, n_groups_hint)
        design.dependent_vars = self._define_dvs(template, dvs)
        design.control_vars = template.control_vars.copy()
        self._log(f"定义变量: {len(design.independent_vars)} IVs, {len(design.dependent_vars)} DVs")

        # 6. 被试
        design.target_population = target_population or "在校大学生（普通成人样本）"
        design.inclusion_criteria = self._generate_inclusion_criteria(target_population, template)
        design.exclusion_criteria = self._generate_exclusion_criteria(template)

        # 7. 效力分析 + 样本量
        effect_map = {"small": 0.2, "medium": 0.5, "large": 0.8}
        es_expected = effect_map.get(effect_size_expected, 0.5)

        if n_subjects_hint > 0:
            design.n_subjects = n_subjects_hint
            design.n_per_group = n_subjects_hint // max(n_groups_hint, 2) if n_groups_hint > 0 else n_subjects_hint
            design.n_groups = max(n_groups_hint, 2) if n_groups_hint > 0 else 2
            design.power_result = None
            self._log(f"使用用户指定样本量: N={n_subjects_hint}")
        else:
            power_result = _auto_power_analysis(template, es_expected, power, alpha)
            design.power_result = power_result
            design.n_subjects = power_result.required_n
            design.n_per_group = power_result.required_per_group
            design.n_groups = power_result.n_groups
            self._log(f"效力分析完成: N={power_result.required_n}, 效力={power_result.actual_power:.3f}")

        # 8. 材料
        design.materials = materials_hint or self._suggest_materials(topic, template)
        design.apparatus = self._suggest_apparatus(template)
        self._log(f"推荐材料: {len(design.materials)}个量表/工具")

        # 9. 实验程序
        conditions = self._generate_condition_labels(design.independent_vars)
        design.procedure = build_full_procedure(
            design_type=template.design_type,
            topic=topic,
            n_conditions=len(conditions),
            n_subjects=design.n_subjects,
            conditions=conditions,
            materials=design.materials,
        )
        self._log(f"构建程序: {len(design.procedure.phases)}个阶段, 总时长{design.procedure.total_duration_min}分钟")

        # 10. 数据分析计划
        design.analysis_plan = template.analysis_plan.copy()
        design.analysis_plan_detailed = self._generate_analysis_plan(template, design)

        # 11. 伦理
        design.ethics = self._generate_ethics(template, design)

        # 12. 参考文献
        design.references = template.references.copy()

        # 13. 补充说明
        design.notes = self._generate_notes(template, design)

        # 14. 预算（可选）
        if include_budget:
            design.budget_estimate = self._estimate_budget(design)

        self.design = design
        self._log("实验设计完成！")
        return design

    # ── 内部辅助 ──────────────────────────────────────

    def _log(self, msg: str):
        self.logs.append(msg)

    def _extract_keywords(self, topic: str, hypotheses: List[str]) -> List[str]:
        """从主题和假设中提取关键词"""
        import re
        all_text = topic + " " + " ".join(hypotheses)
        # 常见心理学关键词
        trigger = {
            "问卷": "问卷", "调查": "调查", "相关": "相关",
            "干预": "干预", "治疗": "治疗", "训练": "训练", "辅导": "辅导",
            "情绪": "情绪", "情感": "情感",
            "启动": "启动", "潜意识": "潜意识", "阈下": "阈下",
            "内隐": "内隐", "IAT": "IAT", "态度": "态度",
            "认知": "认知", "记忆": "记忆", "注意": "注意",
            "实验": "实验", "被试内": "被试内", "重复测量": "重复测量",
            "中介": "中介", "调节": "调节", "交互": "交互",
            "纵向": "纵向", "追踪": "追踪", "发展": "发展",
            "神经": "神经", "脑电": "脑电", "fMRI": "fMRI", "ERP": "ERP",
        }
        found = []
        for word, kw in trigger.items():
            if word in all_text:
                found.append(kw)
        # 也从 topic 中提取长于2字的词
        words = re.findall(r'[一-鿿]{2,}', topic)
        found.extend([w for w in words if w not in found][:5])
        return found

    def _select_template(self, templates: List[DesignTemplate], hint: str) -> DesignTemplate:
        """选择最合适的模板"""
        hint_map = {
            "被试间": "between_subjects", "被试内": "within_subjects",
            "混合": "mixed", "问卷": "survey",
            "干预": "intervention_study", "情绪": "emotion_induction",
            "启动": "priming_experiment", "内隐": "iat",
        }
        target_type = hint_map.get(hint, "")
        if target_type:
            # 先在推荐列表中搜索
            for t in templates:
                if t.id == target_type or t.design_type == target_type:
                    return t
            # 再在所有模板中搜索（用户明确指定了设计类型）
            for tid, t in TEMPLATES.items():
                if t.id == target_type or t.design_type == target_type or tid == target_type:
                    return t
        return templates[0] if templates else TEMPLATES["between_subjects_single"]

    def _generate_title(self, topic: str, template: DesignTemplate) -> str:
        """生成研究标题"""
        design_label = template.name.split("设计")[0] if "设计" in template.name else template.name
        return f"{design_label}: {topic}"

    def _generate_background(self, topic: str, template: DesignTemplate) -> str:
        """生成研究背景段落"""
        return (
            f"{topic}是心理学研究中的重要议题。"
            f"已有研究从不同角度对该问题进行了探讨，但仍存在一些未解决的问题有待进一步澄清。"
            f"本研究采用{template.name}范式，旨在通过严格的实验控制，"
            f"系统考察相关变量之间的因果关系或相关模式，为该领域的理论发展和实践应用提供实证依据。\n\n"
            f"具体而言，本研究关注{template.description[:100]}...\n\n"
            f"**研究目的：**\n"
            f"1. 考察{topic}中关键变量的效应\n"
            f"2. 通过实验设计控制混淆变量，获得可靠的因果推断\n"
            f"3. 为理论构建和实践干预提供数据支持"
        )

    def _generate_default_rq(self, topic: str, template: DesignTemplate) -> List[str]:
        n_vars = min(len(template.typical_ivs), 2)
        rqs = [f"RQ1: {topic}中相关变量之间的关系是怎样的？"]
        if n_vars > 1:
            rqs.append(f"RQ2: 变量之间的交互作用如何影响结果？")
        return rqs

    def _generate_default_hypotheses(self, topic: str, template: DesignTemplate) -> List[str]:
        return [
            f"H1: {topic}中的主要效应具有统计显著性。",
            f"H2: 各条件之间存在显著差异。",
        ]

    def _define_ivs(self, template: DesignTemplate, user_ivs: List[str], n_groups: int) -> List[Dict]:
        """定义自变量"""
        if user_ivs:
            ivs = []
            for i, name in enumerate(user_ivs):
                n_levels = max(2, n_groups) if n_groups > 0 else 2
                labels = [f"{name}水平{j+1}" for j in range(n_levels)]
                ivs.append({
                    "name": name,
                    "type": "被试间变量" if template.design_type in ("between_subjects", "factorial") else "被试内变量",
                    "levels": n_levels,
                    "levels_labels": labels,
                    "manipulation": "实验操作或指导语操纵",
                })
            return ivs
        # 确保模板中的levels是整数
        result = []
        for iv in template.typical_ivs:
            iv_copy = iv.copy()
            if isinstance(iv_copy.get("levels"), str):
                import re
                nums = re.findall(r'\d+', str(iv_copy["levels"]))
                iv_copy["levels"] = int(nums[0]) if nums else 2
            result.append(iv_copy)
        return result

    def _define_dvs(self, template: DesignTemplate, user_dvs: List[str]) -> List[Dict]:
        if user_dvs:
            return [
                {"name": name, "measure": "根据具体实验任务确定（如量表得分、反应时、正确率等）"}
                for name in user_dvs
            ]
        return template.typical_dvs.copy()

    def _generate_inclusion_criteria(self, population: str, template: DesignTemplate) -> List[str]:
        criteria = [
            "自愿参加实验并签署知情同意书",
            "视力或矫正视力正常（如涉及视觉刺激）",
            "无重大精神疾病史",
        ]
        if "大学生" in population:
            criteria.append("全日制在校大学生")
        if "老年" in population or "老人" in population:
            criteria.append("年龄≥60岁")
            criteria.append("MMSE得分≥24（排除认知障碍）")
        if "儿童" in population or "青少年" in population:
            criteria.append("获得家长/监护人的知情同意")
        return criteria

    def _generate_exclusion_criteria(self, template: DesignTemplate) -> List[str]:
        criteria = [
            "色盲或色弱（如涉及颜色刺激）",
            "实验前24小时内饮酒或使用影响中枢神经系统的药物",
            "实验前晚睡眠不足6小时",
        ]
        if template.id == "emotion_induction":
            criteria.append("目前正在经历重大情绪波动或创伤事件")
        if template.id == "intervention_study":
            criteria.append("正在接受其他心理治疗或干预")
        return criteria

    def _generate_condition_labels(self, ivs: List[Dict]) -> List[str]:
        """生成实验条件标签"""
        labels = []
        for iv in ivs:
            levels = iv.get("levels", 2)
            if isinstance(levels, str):
                # 从描述中提取数字，如 "2-4个水平" → 取最小值2
                import re
                nums = re.findall(r'\d+', levels)
                levels = int(nums[0]) if nums else 2
            labels_list = iv.get("levels_labels", [])
            for j in range(int(levels)):
                if j < len(labels_list):
                    labels.append(labels_list[j])
                else:
                    labels.append(f"{iv['name']}水平{j+1}")
        if not labels:
            labels = ["实验组", "控制组"]
        return labels

    def _suggest_materials(self, topic: str, template: DesignTemplate) -> List[Dict]:
        """根据主题推荐实验材料/量表"""
        materials = []

        # 根据主题关键词推荐量表
        topic_lower = topic.lower()

        common_scales = {
            "焦虑": {"name": "焦虑自评量表 (SAS)", "items": "20", "alpha": "0.82-0.89", "source": "Zung, 1971; 中文版由王征宇等修订"},
            "抑郁": {"name": "流调中心抑郁量表 (CES-D)", "items": "20", "alpha": "0.85-0.90", "source": "Radloff, 1977; 中文版由章婕等修订"},
            "自尊": {"name": "Rosenberg自尊量表 (SES)", "items": "10", "alpha": "0.80-0.88", "source": "Rosenberg, 1965; 中文版由季益富等修订"},
            "社会支持": {"name": "领悟社会支持量表 (PSSS)", "items": "12", "alpha": "0.85-0.91", "source": "Zimet et al., 1988; 中文版由姜乾金修订"},
            "应对": {"name": "简易应对方式问卷 (SCSQ)", "items": "20", "alpha": "0.78-0.89", "source": "解亚宁, 1998"},
            "自我效能": {"name": "一般自我效能感量表 (GSES)", "items": "10", "alpha": "0.87-0.91", "source": "Schwarzer, 1995; 中文版由王才康等修订"},
            "主观幸福感": {"name": "生活满意度量表 (SWLS)", "items": "5", "alpha": "0.79-0.89", "source": "Diener et al., 1985"},
            "人格": {"name": "大五人格量表 (BFI-44)", "items": "44", "alpha": "0.75-0.85", "source": "John et al., 1991; 中文版由李金德修订"},
            "正念": {"name": "五因素正念量表 (FFMQ)", "items": "39", "alpha": "0.80-0.90", "source": "Baer et al., 2006; 中文版由邓玉琴等修订"},
            "社交焦虑": {"name": "社交回避与苦恼量表 (SAD)", "items": "28", "alpha": "0.85-0.90", "source": "Watson & Friend, 1969; 中文版由林雄标等修订"},
        }

        for keyword, scale in common_scales.items():
            if keyword in topic_lower:
                materials.append(scale)

        # 如果没有匹配到，推荐基础量表
        if not materials:
            if template.id == "survey_correlational":
                materials.append({"name": "相关心理变量量表", "items": "待定", "alpha": "待定", "source": "根据具体研究变量选择有中文修订版的标准化量表"})
            elif template.id in ("between_subjects_single", "within_subjects_single"):
                materials.append({"name": "实验刺激材料", "items": "待标定", "alpha": "N/A（需预实验评定）", "source": "根据实验目的自行编制或选用标准化刺激库"})

        return materials

    def _suggest_apparatus(self, template: DesignTemplate) -> List[str]:
        """建议实验设备"""
        apparatus = []
        if template.id in ("within_subjects_single", "priming_experiment", "iat"):
            apparatus.append("安装E-Prime / PsychoPy / jsPsych的计算机（15-17寸显示器，分辨率≥1920×1080）")
        if template.id == "emotion_induction":
            apparatus.append("音频播放设备（耳机）— 音乐诱发用")
        if "神经" in template.description or "脑电" in template.description:
            apparatus.append("脑电采集设备（EEG）或近红外光谱成像设备（fNIRS）")
        if template.id == "survey_correlational":
            apparatus.append("在线问卷平台（Credamo/问卷星/腾讯问卷）")
        apparatus.append("标准化实验环境（隔音、恒温约22°C、光照均匀）")
        return apparatus

    def _generate_analysis_plan(self, template: DesignTemplate, design: ExperimentDesign) -> str:
        """生成详细的数据分析计划"""
        lines = [
            f"## 数据分析计划",
            f"",
            f"### 1. 数据预处理",
            f"- 检查数据的完整性和分布特征",
            f"- 识别并处理缺失值（报告缺失比例和处理方法）",
            f"- 检测异常值（如Z分数 > |3|或IQR规则）",
            f"- 检验正态性假设（Shapiro-Wilk检验，Q-Q图）",
            f"",
            f"### 2. 初步分析",
            f"- 计算各变量的描述性统计（M, SD, 偏度, 峰度）",
            f"- 生成变量间相关矩阵",
            f"- 检验各条件/组的基线等值性",
            f"",
            f"### 3. 主要分析",
        ]

        for step in template.analysis_plan:
            lines.append(f"- {step}")

        lines.extend([
            f"",
            f"### 4. 效应量与置信区间",
            f"- 报告所有检验的效应量（根据检验类型选择相应的效应量指标）",
            f"- 报告效应量的95%置信区间",
            f"",
            f"### 5. 补充分析",
            f"- 对可能的混淆变量进行控制后重新分析（稳健性检验）",
            f"- 如涉及多个假设检验，应用多重比较校正（Holm-Bonferroni法）",
        ])

        return "\n".join(lines)

    def _generate_ethics(self, template: DesignTemplate, design: ExperimentDesign) -> List[str]:
        """生成伦理考虑清单"""
        ethics = [
            "本研究方案需提交所在机构的伦理委员会审批",
            "所有被试在参与前需签署书面的知情同意书",
            "告知被试其有权在任何时候退出实验，且不会带来任何不利后果",
            "被试数据匿名化处理，仅以编号标识",
            "数据存储于加密设备，仅研究团队有权访问",
            "研究结果发表时仅报告群体统计结果，不涉及个人可识别信息",
        ]
        if template.id == "emotion_induction":
            ethics.append("实验结束后进行积极情绪恢复程序（如观看积极图片或视频），确保被试离开时情绪状态恢复至基线水平")
        if template.id == "intervention_study":
            ethics.append("研究结束后，为等待对照组提供与实验组相同的干预方案（延迟干预）")
        if "被试费" in (design.budget_estimate or ""):
            ethics.append("被试费的设定应合理，既体现对被试付出的尊重，又不构成不当诱导")
        return ethics

    def _generate_notes(self, template: DesignTemplate, design: ExperimentDesign) -> List[str]:
        """生成补充说明"""
        notes = [
            f"**预实验建议：** 正式实验前建议进行小规模预实验（n=10-20），以检验实验程序、材料清晰度和时间安排的合理性。",
            f"**数据管理：** 建议采用标准化的数据命名和存档规范，确保数据的可追溯性和可重复性。",
            f"**预注册：** 建议在数据收集前在研究预注册平台（如OSF、AsPredicted或中国临床试验注册中心）进行预注册，提高研究的透明度和可重复性。",
        ]
        if template.id == "survey_correlational":
            notes.append("**共同方法偏差控制：** 建议采用程序性控制（匿名作答、平衡题目顺序、反向题）和统计检验（Harman单因素检验、ULMC法）。")
        if template.id == "intervention_study":
            notes.append("**CONSORT报告标准：** 建议按CONSORT声明的要求报告干预研究的方法和结果。")
        if template.id == "iat":
            notes.append("**IAT的信度：** IAT的重测信度通常在r=0.50-0.60之间，解释结果时需考虑测量误差。")
        return notes

    def _estimate_budget(self, design: ExperimentDesign) -> str:
        """估算实验预算"""
        n = design.n_subjects
        per_subject = 30  # 心理学实验被试费大致标准（元）
        total_fee = n * per_subject

        lines = [
            f"## 实验预算估算",
            f"",
            f"| 项目 | 单位成本 | 数量 | 小计 |",
            f"|------|----------|------|------|",
            f"| 被试费 | {per_subject}元/人 | {n}人 | {total_fee}元 |",
            f"| 问卷平台费 | 约500元 | 1次 | 500元 |",
            f"| 材料打印费 | 约2元/份 | {n}份 | {n*2}元 |",
            f"| 杂项（文具等） | 约300元 | 1次 | 300元 |",
            f"| **合计** | | | **约{total_fee + 500 + n*2 + 300}元** |",
            f"",
            f"*此为粗略估算，实际费用因地区和具体需求而异。*",
        ]
        return "\n".join(lines)

    def format_design_report(self, design: ExperimentDesign = None) -> str:
        """生成完整的实验设计报告（Markdown文本）"""
        d = design or self.design
        if d is None:
            return "尚未创建设计方案。请先调用 design_experiment()。"

        lines = []

        # 标题
        lines.append(f"# 心理学实验设计方案")
        lines.append(f"")
        lines.append(f"## 1. 研究题目")
        lines.append(f"{d.title}")
        lines.append(f"")

        # 实验设计类型
        lines.append(f"## 2. 实验设计")
        lines.append(f"**设计类型：** {d.design_type_zh}（{d.template_name}）")
        lines.append(f"")

        # 研究背景
        lines.append(f"## 3. 研究背景与目的")
        lines.append(d.background)
        lines.append(f"")

        # 研究假设
        lines.append(f"## 4. 研究假设")
        for h in d.hypotheses:
            lines.append(f"- {h}")
        lines.append(f"")

        # 变量定义
        lines.append(f"## 5. 变量定义")
        lines.append(f"### 5.1 自变量")
        for iv in d.independent_vars:
            lines.append(f"- **{iv['name']}**：{iv.get('type', '')}，{iv.get('levels', '?')}个水平")
            if 'levels_labels' in iv:
                lines.append(f"  水平: {', '.join(iv['levels_labels'])}")
            if 'manipulation' in iv:
                lines.append(f"  操纵方式: {iv['manipulation']}")
        lines.append(f"")
        lines.append(f"### 5.2 因变量")
        for dv in d.dependent_vars:
            lines.append(f"- **{dv['name']}**：{dv.get('measure', '')}")
        lines.append(f"")
        lines.append(f"### 5.3 控制变量")
        for cv in d.control_vars:
            lines.append(f"- {cv}")
        lines.append(f"")

        # 被试
        lines.append(f"## 6. 被试")
        lines.append(f"**目标人群：** {d.target_population}")
        lines.append(f"**计划样本量：** N = {d.n_subjects}")
        if d.n_groups > 1:
            lines.append(f"**分组：** 共{d.n_groups}组，每组{d.n_per_group}人")
        lines.append(f"")
        lines.append(f"### 纳入标准")
        for c in d.inclusion_criteria:
            lines.append(f"- {c}")
        lines.append(f"")
        lines.append(f"### 排除标准")
        for c in d.exclusion_criteria:
            lines.append(f"- {c}")
        lines.append(f"")

        # 效力分析
        if d.power_result:
            lines.append(f"## 7. 统计效力分析")
            lines.append(format_power_report(d.power_result))
            lines.append(f"")

        # 材料
        lines.append(f"## 8. 实验材料与设备")
        if d.materials:
            lines.append(f"### 量表/问卷")
            for m in d.materials:
                lines.append(f"- **{m.get('name', '未知')}**：{m.get('items', '?')}题，α = {m.get('alpha', '待定')}")
                if m.get('source'):
                    lines.append(f"  来源: {m['source']}")
        if d.apparatus:
            lines.append(f"### 实验设备")
            for a in d.apparatus:
                lines.append(f"- {a}")
        lines.append(f"")

        # 实验程序
        if d.procedure:
            lines.append(f"## 9. 实验程序")
            lines.append(f"**预计总时长：** {d.procedure.total_duration_min} 分钟")
            lines.append(f"")
            lines.append(f"### 时间线")
            lines.append(f"| 阶段 | 时间 | 时长 | 内容 |")
            lines.append(f"|------|------|------|------|")
            for t in d.procedure.timeline:
                lines.append(f"| {t['name']} | {t['start_min']}-{t['end_min']}分钟 | {t['duration_min']}分钟 | - |")
            lines.append(f"")

            for phase in d.procedure.phases:
                lines.append(f"### {phase['name']}（{phase['duration_min']}分钟）")
                lines.append(phase['description'])
                lines.append(f"")
                lines.append(f"**检查清单：**")
                for item in phase.get('checklist', []):
                    lines.append(f"- [ ] {item}")
                lines.append(f"")

            # 随机化
            if d.procedure.randomization:
                lines.append(f"### 随机化方案")
                lines.append(f"**方法：** {d.procedure.randomization.get('method', '')}")
                lines.append(d.procedure.randomization.get('description', ''))
                lines.append(f"")

            # 平衡
            if d.procedure.counterbalancing:
                lines.append(f"### 顺序平衡方案")
                lines.append(f"**方法：** {d.procedure.counterbalancing.get('method', '')}")
                lines.append(d.procedure.counterbalancing.get('description', ''))
                ls = d.procedure.counterbalancing.get('latin_square', [])
                if ls:
                    lines.append(f"")
                    lines.append(f"**拉丁方矩阵：**")
                    for row in ls:
                        lines.append(f"- {' → '.join(row)}")
                lines.append(f"")

            # 指导语
            if d.procedure.instructions:
                lines.append(f"### 实验指导语")
                for inst in d.procedure.instructions[:2]:  # 只展示主要的
                    lines.append(f"**{inst['title']}**")
                    lines.append(f"```")
                    lines.append(inst['text'][:300])
                    if len(inst['text']) > 300:
                        lines.append("...")
                    lines.append(f"```")
                    lines.append(f"")

        # 数据分析
        lines.append(f"## 10. 数据分析计划")
        lines.append(d.analysis_plan_detailed)
        lines.append(f"")

        # 伦理
        lines.append(f"## 11. 伦理考虑")
        for e in d.ethics:
            lines.append(f"- {e}")
        lines.append(f"")

        # 补充说明
        if d.notes:
            lines.append(f"## 12. 补充说明")
            for n in d.notes:
                lines.append(f"- {n}")
            lines.append(f"")

        # 预算
        if d.budget_estimate:
            lines.append(f"## 13. 实验预算")
            lines.append(d.budget_estimate)
            lines.append(f"")

        # 参考文献
        lines.append(f"## 14. 参考文献")
        for i, ref in enumerate(d.references):
            lines.append(f"[{i+1}] {ref}")

        return "\n".join(lines)


def _design_type_to_chinese(dt: str) -> str:
    """将设计类型标识转换为中文名"""
    mapping = {
        "between_subjects": "被试间设计",
        "within_subjects": "被试内设计",
        "mixed": "混合设计",
        "survey": "问卷调查研究",
        "quasi_experimental": "准实验设计",
    }
    return mapping.get(dt, dt)


def _auto_power_analysis(template: DesignTemplate, effect_size: float,
                         power: float, alpha: float) -> PowerResult:
    """根据设计类型自动进行效力分析"""
    if template.design_type == "survey":
        return calculate_sample_size("correlation", effect_size=effect_size, power=power, alpha=alpha)
    elif template.id in ("between_subjects_single",):
        return calculate_sample_size("t_test", effect_size=effect_size, power=power, alpha=alpha)
    elif template.id in ("factorial_between",):
        return calculate_sample_size("factorial", effect_size=0.25, power=power, alpha=alpha, design="2x2")
    elif template.id == "mixed_design":
        return calculate_sample_size("rm_anova", effect_size=effect_size, power=power, alpha=alpha, n_groups=2)
    elif template.id == "within_subjects_single":
        return calculate_sample_size("rm_anova", effect_size=effect_size, power=power, alpha=alpha, n_groups=3)
    elif template.id == "intervention_study":
        return calculate_sample_size("factorial", effect_size=0.25, power=power, alpha=alpha, design="2x2")
    else:
        return calculate_sample_size("t_test", effect_size=effect_size, power=power, alpha=alpha)
