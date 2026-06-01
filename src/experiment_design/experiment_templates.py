"""实验设计系统 — 心理学实验范式模板库

涵盖中国心理学研究中常见的实验范式，提供结构化的设计模板。
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class DesignTemplate:
    """实验设计模板"""
    id: str
    name: str                           # 模板名称
    category: str                       # 类别
    design_type: str                    # "between_subjects" | "within_subjects" | "mixed" | "survey"
    description: str                    # 模板描述
    typical_ivs: List[Dict]             # 典型自变量
    typical_dvs: List[Dict]             # 典型因变量
    n_conditions_range: str             # 条件数范围
    duration_range: str                 # 实验时长范围
    sample_size_hint: str               # 样本量参考
    design_diagram: str                 # 设计图示（文本描述）
    key_considerations: List[str]       # 关键注意事项
    control_vars: List[str]             # 需控制的变量
    analysis_plan: List[str]            # 推荐分析方案
    references: List[str]               # 方法参考文献


# ═══════════════════════════════════════════════════════════════
# 模板库
# ═══════════════════════════════════════════════════════════════

TEMPLATES = {

    # ── 1. 单因素被试间设计 ──────────────────────────────
    "between_subjects_single": DesignTemplate(
        id="between_subjects_single",
        name="单因素被试间实验设计",
        category="基础实验设计",
        design_type="between_subjects",
        description=(
            "将被试随机分配到自变量的不同水平（实验条件），每个被试只接受一种处理。"
            "这是最基本的实验设计，适用于自变量操作不会产生延续效应的情形。"
        ),
        typical_ivs=[
            {"name": "自变量", "levels": "2-4个水平", "example": "反馈类型（积极/消极/无反馈）", "manipulation": "实验操作或指导语操纵"},
        ],
        typical_dvs=[
            {"name": "任务表现", "measure": "正确率、反应时"},
            {"name": "心理状态", "measure": "自评量表得分"},
            {"name": "生理指标", "measure": "心率、皮肤电、脑电"},
        ],
        n_conditions_range="2-4个水平",
        duration_range="15-40分钟",
        sample_size_hint="每组30-50人（中等效应量d=0.5，80%效力）。实际样本量建议通过先验统计效力分析确定。",
        design_diagram="R: 被试随机化 → X₁ (条件1) → O₁\nR: 被试随机化 → X₂ (条件2) → O₂\n...",
        key_considerations=[
            "随机分配是控制个体差异的关键，确保两组在无关变量上的同质性",
            "注意实验操作的忠实度（treatment fidelity），确保不同条件的唯一差异是自变量的变化",
            "实验者和被试的双盲可减少期望效应",
            "操作检验（manipulation check）必不可少：确认自变量的操纵确实引起了预期变化",
        ],
        control_vars=[
            "被试年龄、性别", "实验环境（温度、光照、噪音）",
            "实验者效应（标准化指导语、双盲）", "施测时间（控制日间/晚间差异）",
        ],
        analysis_plan=[
            "1. 描述性统计：各条件M ± SD",
            "2. 独立样本t检验（2水平）或单因素方差分析（≥3水平）",
            "3. 效应量：Cohen's d（2水平）或η²（≥3水平）及其置信区间",
            "4. 检验统计假设（正态性、方差齐性）",
            "5. 必要时使用非参数替代：Mann-Whitney U或Kruskal-Wallis",
        ],
        references=[
            "Cohen, J. (1988). Statistical power analysis for the behavioral sciences (2nd ed.).",
            "舒华, 张亚旭. (2008). 心理学研究方法: 实验设计和数据分析. 人民教育出版社.",
        ],
    ),

    # ── 2. 单因素被试内设计 ──────────────────────────────
    "within_subjects_single": DesignTemplate(
        id="within_subjects_single",
        name="单因素被试内实验设计",
        category="基础实验设计",
        design_type="within_subjects",
        description=(
            "每个被试接受自变量的所有水平。被试内设计通过将个体差异从误差项中分离，"
            "通常具有更高的统计效力。但需要注意顺序效应、练习效应和疲劳效应。"
        ),
        typical_ivs=[
            {"name": "自变量", "levels": "2-6个水平", "example": "记忆负荷（低/中/高）", "manipulation": "刺激参数变化或指导语操纵"},
        ],
        typical_dvs=[
            {"name": "认知表现", "measure": "正确率、反应时、d'"},
            {"name": "主观体验", "measure": "李克特量表评分"},
            {"name": "眼动数据", "measure": "注视时长、扫视路径"},
        ],
        n_conditions_range="2-6个水平",
        duration_range="20-50分钟",
        sample_size_hint="每组25-40人（中等效应量d=0.5，80%效力，被试内设计效率更高）。",
        design_diagram="被试1: X₁→O₁, X₂→O₂, X₃→O₃\n被试2: X₂→O₂, X₃→O₃, X₁→O₁\n（条件顺序经拉丁方平衡）",
        key_considerations=[
            "必须使用拉丁方设计或完全交叉平衡来控制顺序效应",
            "注意延续效应（carry-over effect）：前一条件可能影响后一条件的表现",
            "条件间插入适当休息（30秒-1分钟）或填充任务",
            "练习效应：对于认知任务，可增加充分的练习阶段使其趋于稳定",
            "疲劳效应：控制总实验时长不超过60分钟",
        ],
        control_vars=[
            "条件呈现顺序（拉丁方平衡）", "条件间休息间隔",
            "练习效应（充分的练习阶段）", "疲劳效应（控制总时长）",
        ],
        analysis_plan=[
            "1. 描述性统计：各条件M ± SD",
            "2. 重复测量方差分析（含球形假设检验，必要时使用Greenhouse-Geisser校正）",
            "3. 效应量：广义η²（generalized η²）",
            "4. 事后多重比较（Bonferroni或Holm校正）",
            "5. 如球形假设严重违反，考虑多水平模型（HLM）替代",
        ],
        references=[
            "舒华, 张亚旭. (2008). 心理学研究方法: 实验设计和数据分析. 人民教育出版社.",
            "Bakeman, R. (2005). Recommended effect size statistics for repeated measures designs. Behavior Research Methods, 37(3), 379-384.",
        ],
    ),

    # ── 3. 多因素被试间设计 ──────────────────────────────
    "factorial_between": DesignTemplate(
        id="factorial_between",
        name="多因素被试间实验设计",
        category="进阶实验设计",
        design_type="between_subjects",
        description=(
            "同时操纵两个或多个自变量，所有因素均为被试间变量。"
            "允许研究者考察因素的主效应和交互作用。"
        ),
        typical_ivs=[
            {"name": "因素A", "levels": "2-3个水平", "example": "情绪状态（积极/中性/消极）"},
            {"name": "因素B", "levels": "2-3个水平", "example": "任务难度（简单/困难）"},
        ],
        typical_dvs=[
            {"name": "行为表现", "measure": "任务正确率、决策时间"},
            {"name": "认知加工", "measure": "记忆再认成绩、问题解决分数"},
        ],
        n_conditions_range="4-9个条件（2×2到3×3）",
        duration_range="20-45分钟",
        sample_size_hint="每个条件30-40人。2×2设计共需120-160人。根据交互作用的效应量进行效力分析。",
        design_diagram="       因素B\n       简单   困难\n因素A 积极  n=35  n=35\n      中性  n=35  n=35\n      消极  n=35  n=35",
        key_considerations=[
            "交互作用是因素设计的核心关注点",
            "注意各条件被试量的均衡（增加统计效力）",
            "解释主效应时需谨慎，尤其存在交互作用时",
            "简单效应分析用于分解交互作用",
            "建议提前进行统计效力分析（交互作用通常需要更大样本量）",
        ],
        control_vars=[
            "被试人口学变量", "实验环境标准化",
            "各因素操作的有效性检验", "各条件的被试量平衡",
        ],
        analysis_plan=[
            "1. 各条件的描述统计（M ± SD）",
            "2. 两因素方差分析（Type III SS）",
            "3. 主效应和交互作用的效应量（partial η²）",
            "4. 如交互作用显著：简单效应分析（Bonferroni校正）",
            "5. 交互作用图解（交互作用图）",
        ],
        references=[
            "Rosenthal, R., & Rosnow, R. L. (2008). Essentials of behavioral research (3rd ed.). McGraw-Hill.",
            "舒华, 张亚旭. (2008). 心理学研究方法. 人民教育出版社.",
        ],
    ),

    # ── 4. 混合设计 ─────────────────────────────────
    "mixed_design": DesignTemplate(
        id="mixed_design",
        name="混合实验设计",
        category="进阶实验设计",
        design_type="mixed",
        description=(
            "同时包含被试间因素和被试内因素。这种设计结合了被试内设计的统计效力优势"
            "和被试间设计避免延续效应的优势。"
        ),
        typical_ivs=[
            {"name": "被试间因素", "levels": "2-3个水平", "example": "组别（实验组/控制组）"},
            {"name": "被试内因素", "levels": "2-4个水平", "example": "时间点（前测/后测/追踪）"},
        ],
        typical_dvs=[
            {"name": "行为指标", "measure": "任务表现、反应时"},
            {"name": "心理指标", "measure": "量表得分变化"},
        ],
        n_conditions_range="4-12个条件（如2×3=6条件）",
        duration_range="25-60分钟",
        sample_size_hint="每组30-50人。需要考虑被试间因素和被试内因素的交互作用效力。",
        design_diagram="       被试内: 时间1  时间2  时间3\n被试间 实验组  O₁₁    O₁₂    O₁₃  (n=35)\n      控制组  O₂₁    O₂₂    O₂₃  (n=35)",
        key_considerations=[
            "被试内因素的顺序必须平衡（拉丁方）",
            "注意被试间因素和被试内因素可能存在的交互作用",
            "被试流失率在追踪设计中尤其重要",
            "测量时间点可能引入练习效应或历史效应",
        ],
        control_vars=[
            "被试内因素顺序", "被试间因素的随机分配",
            "练习/疲劳效应", "测量工具的信度（跨时间一致性）",
            "实验者的标准化操作",
        ],
        analysis_plan=[
            "1. 各条件描述统计",
            "2. 两因素混合方差分析：被试间×被试内",
            "3. 交互作用显著时进行简单效应分析",
            "4. 效应量：partial η²或generalized η²",
            "5. 必要时进行多重比较校正",
        ],
        references=[
            "Maxwell, S. E., & Delaney, H. D. (2004). Designing experiments and analyzing data (2nd ed.).",
            "舒华, 张亚旭. (2008). 心理学研究方法. 人民教育出版社.",
        ],
    ),

    # ── 5. 问卷调查研究设计 ──────────────────────────────
    "survey_correlational": DesignTemplate(
        id="survey_correlational",
        name="问卷调查研究设计",
        category="非实验设计",
        design_type="survey",
        description=(
            "通过标准化问卷收集数据，考察变量之间的相关关系和预测关系。"
            "这是心理学中最常见的研究方法之一，适合研究难以操纵或伦理上不能操纵的变量。"
        ),
        typical_ivs=[
            {"name": "预测变量", "levels": "连续或分类", "example": "自尊、社会支持、人格特质"},
            {"name": "调节/中介变量", "levels": "连续", "example": "应对方式（中介）、性别（调节）"},
        ],
        typical_dvs=[
            {"name": "结果变量", "measure": "标准化量表得分"},
            {"name": "心理健康指标", "measure": "焦虑、抑郁、幸福感等量表"},
        ],
        n_conditions_range="N/A（非实验设计）",
        duration_range="15-30分钟",
        sample_size_hint=(
            "至少200人（中等效应量r=0.2，80%效力）。"
            "中介/调节模型建议300-500人以上。结构方程模型至少200人或观测变量数的10-20倍。"
        ),
        design_diagram="所有被试 → 填写问卷（人口学 + 多个量表） → 数据分析",
        key_considerations=[
            "共同方法偏差是问卷研究的主要威胁：使用Harman单因素检验、标记变量等技术",
            "横断设计无法推断因果关系，需在讨论部分明确说明",
            "自评问卷可能存在社会赞许偏差",
            "量表的中文修订版信效度必须报告",
            "注意题目顺序效应：随机化或固定化呈现顺序",
            "设置注意力检查题（attention check）以筛选无效作答",
        ],
        control_vars=[
            "性别、年龄等人口学变量",
            "共同方法偏差（程序性控制和统计检验）",
            "社会赞许性（可加入Marlowe-Crowne社会赞许量表）",
            "作答顺序效应",
        ],
        analysis_plan=[
            "1. 共同方法偏差检验（Harman单因素检验）",
            "2. 各变量的描述统计和相关矩阵",
            "3. 信度分析（Cronbach's α）",
            "4. 主要分析：回归分析 / 中介效应（Bootstrap法） / 调节效应 / 结构方程模型",
            "5. 效应量及其置信区间",
            "6. 必要时进行稳健性检验（控制人口学变量后）",
        ],
        references=[
            "Podsakoff, P. M., et al. (2003). Common method biases in behavioral research. JAP, 88(5), 879-903.",
            "温忠麟, 叶宝娟. (2014). 中介效应分析: 方法和模型发展. 心理科学进展, 22(5), 731-745.",
            "周浩, 龙立荣. (2004). 共同方法偏差的统计检验与控制方法. 心理科学进展, 12(6), 942-950.",
        ],
    ),

    # ── 6. 情绪诱发实验 ──────────────────────────────
    "emotion_induction": DesignTemplate(
        id="emotion_induction",
        name="情绪诱发实验设计",
        category="特定范式",
        design_type="within_subjects",
        description=(
            "通过标准化刺激材料（图片、视频、音乐或回忆任务）诱发特定情绪状态，"
            "考察情绪对认知或行为的影响。常用的情绪诱发材料包括中国情绪图片系统(CAPS)、"
            "国际情绪图片系统(IAPS)和情绪电影片段。"
        ),
        typical_ivs=[
            {"name": "情绪类型", "levels": "2-4种（积极/中性/消极/恐惧等）", "example": "观看积极vs.消极情绪图片"},
            {"name": "诱发方法", "levels": "图片/视频/音乐/回忆/组合", "example": "使用CAPS标准化图片"},
        ],
        typical_dvs=[
            {"name": "情绪自评", "measure": "PANAS、SAM（效价+唤醒度）"},
            {"name": "认知任务", "measure": "注意偏向（点探测/Stroop）、记忆提取"},
            {"name": "生理指标", "measure": "心率、皮肤电反应(SCR)、心率变异性(HRV)"},
        ],
        n_conditions_range="3-4种情绪条件",
        duration_range="30-50分钟",
        sample_size_hint="25-40人（被试内设计）。考虑情绪诱发的个体差异，建议每情绪条件后测量情绪状态作为操作检验。",
        design_diagram="基线情绪测量 → 情绪诱发（条件i）→ 情绪操作检验 → 认知任务 → 恢复期 → 下一条件",
        key_considerations=[
            "情绪诱发效果的个体差异：需进行操作检验",
            "情绪恢复：条件间必须有充分的洗脱期（wash-out period），确保情绪回到基线",
            "基线情绪的测量：实验开始前评估被试的情绪状态",
            "图片/视频材料的预实验评定：确保材料在中国样本中的有效性",
            "情绪诱发效果的时效性：注意诱发效果的持续时间",
            "伦理考虑：消极情绪诱发后必须进行积极情绪恢复",
        ],
        control_vars=[
            "基线情绪状态", "情绪诱发效果的个体差异",
            "条件呈现顺序（拉丁方平衡）", "情绪恢复期时长",
            "实验环境（光照、温度）", "实验者态度",
        ],
        analysis_plan=[
            "1. 情绪操作检验：各条件下情绪自评的差异（重复测量ANOVA）",
            "2. 主要分析：情绪条件对认知任务的影响",
            "3. 效应量：广义η²",
            "4. 必要时控制基线情绪状态（ANCOVA）",
        ],
        references=[
            "白露, 马慧, 黄宇霞, 罗跃嘉. (2005). 中国情绪图片系统的编制. 中国心理卫生杂志, 19(11), 719-722.",
            "Lang, P. J., Bradley, M. M., & Cuthbert, B. N. (2008). IAPS technical manual.",
            "郑希付. (2003). 不同情绪模式的图片刺激启动效应. 心理学报, 35(3), 352-357.",
        ],
    ),

    # ── 7. 干预研究设计 ──────────────────────────────
    "intervention_study": DesignTemplate(
        id="intervention_study",
        name="干预研究设计（前测-后测控制组设计）",
        category="应用研究",
        design_type="mixed",
        description=(
            "评估心理干预（如认知行为治疗、正念训练、团体辅导等）的效果。"
            "通常包含实验组和控制组的前测、后测及追踪测量。"
            "这是临床与咨询心理学、教育心理学中最关键的实验设计之一。"
        ),
        typical_ivs=[
            {"name": "组别（被试间）", "levels": "2-3（实验组/控制组/安慰剂组）", "example": "正念训练组 vs. 等待对照组"},
            {"name": "时间点（被试内）", "levels": "2-3（前测/后测/追踪）", "example": "干预前、干预后、3个月追踪"},
        ],
        typical_dvs=[
            {"name": "主要结果", "measure": "目标症状/行为的变化（如焦虑、抑郁量表得分）"},
            {"name": "次要结果", "measure": "相关心理变量的变化（如生活质量、社会功能）"},
        ],
        n_conditions_range="4-9个条件（2组×2-3时间点）",
        duration_range="数周至数月（含追踪期）",
        sample_size_hint=(
            "每组至少30-40人（中等效应量f=0.25，80%效力）。"
            "考虑20-30%的流失率，初始招募量应增加。建议进行先验效力分析。"
        ),
        design_diagram="        前测(T1)  干预(8周)  后测(T2)  追踪(T3, 3个月)\n实验组   O₁₁     X        O₁₂      O₁₃\n控制组   O₂₁              O₂₂      O₂₃",
        key_considerations=[
            "随机分配：尽可能使用真随机（计算机生成随机序列），而非便利分配",
            "干预忠实度：使用标准化干预手册（treatment manual），记录干预执行情况",
            "治疗师效应：如有多个治疗师，需考察治疗师的随机效应",
            "等待对照组的伦理处理：研究结束后为对照组提供同样的干预",
            "被试流失（attrition）：追踪各阶段的脱落率及脱落原因",
            "盲法：至少确保数据收集者对被试分组不知情（单盲）",
            "样本量的保守估计：考虑追踪阶段的流失率",
        ],
        control_vars=[
            "基线水平（前测得分作为协变量）", "被试流失率及流失偏差",
            "干预执行的忠实度", "治疗师效应",
            "额外治疗/帮助寻求行为", "期望效应",
        ],
        analysis_plan=[
            "1. 两组基线水平的等值检验（独立t检验或卡方检验）",
            "2. 主要分析：2（组别）×3（时间点）混合方差分析或潜变量增长模型",
            "3. 或使用ANCOVA：控制前测得分，比较后测得分的组间差异",
            "4. 效应量：partial η²或Cohen's d（组间后测差异）",
            "5. 意向治疗分析（ITT）和完成者分析（completer analysis）",
            "6. 临床显著性：可靠变化指数（Reliable Change Index, RCI）",
        ],
        references=[
            "Kazdin, A. E. (2017). Research design in clinical psychology (5th ed.). Pearson.",
            "Shadish, W. R., Cook, T. D., & Campbell, D. T. (2002). Experimental and quasi-experimental designs.",
            "Jacobson, N. S., & Truax, P. (1991). Clinical significance. JCCP, 59(1), 12-19.",
        ],
    ),

    # ── 8. 启动实验 ─────────────────────────────────
    "priming_experiment": DesignTemplate(
        id="priming_experiment",
        name="启动实验设计",
        category="特定范式",
        design_type="between_subjects",
        description=(
            "考察先前的刺激（启动刺激）对后续刺激（目标刺激）加工的影响。"
            "广泛应用于社会认知、语义加工和潜意识知觉等领域。"
        ),
        typical_ivs=[
            {"name": "启动类型", "levels": "2-3（一致/不一致/中性/无启动）", "example": "语义相关 vs. 语义无关启动词"},
            {"name": "SOA（stimulus onset asynchrony）", "levels": "可选：短SOA vs. 长SOA", "example": "200ms vs. 800ms"},
        ],
        typical_dvs=[
            {"name": "反应时", "measure": "目标刺激的反应潜伏期（ms）"},
            {"name": "正确率", "measure": "目标判断的正确百分比"},
            {"name": "启动量", "measure": "RT(不一致) - RT(一致)"},
        ],
        n_conditions_range="2-3个条件（仅计算启动类型）",
        duration_range="20-35分钟",
        sample_size_hint="每组30-40人。启动效应通常较小，需要足够的统计效力。",
        design_diagram="启动刺激（短暂呈现） → 掩蔽/间隔 → 目标刺激 → 反应（按键判断）",
        key_considerations=[
            "SOA的设置：短SOA(≤300ms)考察自动加工，长SOA(>500ms)可能涉及策略加工",
            "启动刺激的掩蔽：阈下启动需要前后掩蔽",
            "启动刺激是否可见的意识检验：实验后询问被试是否察觉到启动刺激",
            "刺激材料的预实验评定：确保启动词和目标词的相关性",
            "填充试次（fillers）：加入中性试次以减少被试的策略性反应",
        ],
        control_vars=[
            "SOA", "启动词和目标词的关联强度",
            "反应手（左右手按键平衡）", "试次顺序（随机化或伪随机化）",
        ],
        analysis_plan=[
            "1. 数据清洗：删除极端反应时（如<200ms或>3SD）",
            "2. 主要分析：启动类型对反应时/正确率的效应（重复测量ANOVA）",
            "3. 启动量的计算和比较",
            "4. 效应量：η²或Cohen's d",
        ],
        references=[
            "Meyer, D. E., & Schvaneveldt, R. W. (1971). Facilitation in recognizing pairs of words. JEP, 90(2), 227-234.",
            "周仁来, 杨莹. (2004). 阈下语义启动效应研究述评. 心理科学进展, 12(1), 83-92.",
        ],
    ),

    # ── 9. 内隐联想测验（IAT）──────────────────────────
    "iat": DesignTemplate(
        id="iat",
        name="内隐联想测验（IAT）设计",
        category="特定范式",
        design_type="within_subjects",
        description=(
            "通过测量概念词和属性词之间自动化联系的反应时差异，"
            "评估内隐态度、内隐刻板印象或内隐自我概念。"
            "经典的7-block IAT由Greenwald等人(1998)提出。"
        ),
        typical_ivs=[
            {"name": "任务类型（Block）", "levels": "5-7个（练习+正式）", "example": "相容任务 vs. 不相容任务"},
        ],
        typical_dvs=[
            {"name": "反应时", "measure": "各block的平均反应时"},
            {"name": "D值", "measure": "IAT效应（标准化的反应时差异）"},
        ],
        n_conditions_range="7个Block（5类任务）",
        duration_range="10-15分钟",
        sample_size_hint="至少40人（IAT效应通常中等大小）。",
        design_diagram=(
            "Block 1: 目标概念辨别（练习）— 如: 花/昆虫\n"
            "Block 2: 属性词辨别（练习）— 如: 积极/消极\n"
            "Block 3: 相容联合任务（练习）— 花+积极 / 昆虫+消极\n"
            "Block 4: 相容联合任务（正式）\n"
            "Block 5: 反转目标辨别（练习）— 昆虫/花（按键反转）\n"
            "Block 6: 不相容联合任务（练习）— 昆虫+积极 / 花+消极\n"
            "Block 7: 不相容联合任务（正式）"
        ),
        key_considerations=[
            "Block顺序的固定性：通常相容任务在前，不相容在后（可部分被试反转以消除顺序效应）",
            "正确率反馈：每个Block内，错误反应需强制修正（红色叉号）",
            "D值的计算：使用Greenwald等人(2003)改进的D值算法",
            "反应时截断：建议<400ms或>10,000ms的极端值剔除",
            "刺激词的代表性：确保概念词和属性词的类别代表性",
            "被试的认真度：过高的错误率（>25%）或过快反应（<300ms占总试次>10%）为无效数据",
        ],
        control_vars=[
            "Block顺序效应（部分被试反转）", "反应手和按键对应关系",
            "刺激词的类别代表性", "错误率",
        ],
        analysis_plan=[
            "1. 数据清洗：按Greenwald et al. (2003)标准程序",
            "2. 计算D值：均值差/标准差（含练习Block的SD）",
            "3. D值的单样本t检验（与0比较）",
            "4. D值与外显态度的相关分析",
            "5. 效应量和置信区间",
        ],
        references=[
            "Greenwald, A. G., McGhee, D. E., & Schwartz, J. L. K. (1998). Measuring individual differences in implicit cognition. JPSP, 74(6), 1464-1480.",
            "Greenwald, A. G., Nosek, B. A., & Banaji, M. R. (2003). Understanding and using the IAT. JPSP, 85(2), 197-216.",
            "蔡华俭. (2003). Greenwald提出的内隐联想测验介绍. 心理科学进展, 11(3), 339-344.",
        ],
    ),
}


def get_template(template_id: str) -> Optional[DesignTemplate]:
    """获取设计模板"""
    return TEMPLATES.get(template_id)


def list_templates() -> List[Dict]:
    """列出所有模板的概要信息"""
    return [
        {
            "id": tid,
            "name": t.name,
            "category": t.category,
            "design_type": t.design_type,
            "description": t.description[:80] + "...",
        }
        for tid, t in TEMPLATES.items()
    ]


def recommend_template(topic: str, keywords: List[str]) -> List[DesignTemplate]:
    """根据研究主题推荐合适的实验设计模板"""
    topic_lower = topic.lower()
    kw_lower = [k.lower() for k in keywords]
    all_text = topic_lower + " " + " ".join(kw_lower)

    scores = {}
    for tid, tmpl in TEMPLATES.items():
        score = 0
        tmpl_text = f"{tmpl.name} {tmpl.description} {tmpl.category}"
        for kw in kw_lower:
            if kw in tmpl_text.lower():
                score += 1
        # 问卷/调查研究关键词
        if any(w in all_text for w in ["问卷", "调查", "相关", "关系", "影响", "预测", "量表"]):
            if tmpl.id == "survey_correlational":
                score += 5
        # 干预研究关键词
        if any(w in all_text for w in ["干预", "治疗", "训练", "辅导", "效果", "前后测", "追踪"]):
            if tmpl.id == "intervention_study":
                score += 5
        # 情绪关键词
        if any(w in all_text for w in ["情绪", "情感", "积极", "消极", "诱发"]):
            if tmpl.id == "emotion_induction":
                score += 5
        # 启动关键词
        if any(w in all_text for w in ["启动", "潜意识", "阈下"]):
            if tmpl.id == "priming_experiment":
                score += 5
        # 内隐/IAT关键词
        if any(w in all_text for w in ["内隐", "IAT", "态度"]):
            if tmpl.id == "iat":
                score += 5
        # 因素/交互关键词
        if any(w in all_text for w in ["因素", "交互", "调节", "中介"]):
            if tmpl.id in ("factorial_between", "mixed_design"):
                score += 3
        # 被试内关键词
        if any(w in all_text for w in ["被试内", "重复", "脑电", "眼动"]):
            if tmpl.id == "within_subjects_single":
                score += 3

        scores[tid] = score

    # 排序返回
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top = [TEMPLATES[tid] for tid, s in ranked if s > 0]
    if not top:
        top = [TEMPLATES["between_subjects_single"]]  # 默认

    return top[:3]
