"""构念知识库：心理学常见构念的学术定义、维度结构和参考文献

每个条目包含：
- name_zh / name_en: 中英文名称
- domain: 所属领域
- definition: 构念的学术定义
- dimensions: 子维度列表 {name, desc, item_count}
- typical_scale: 建议的量表格式
- established_scales: 已有的成熟量表
- references: 可引用的学术文献
"""

CONSTRUCTS = {
    # ================================================================
    # 临床与健康心理学
    # ================================================================
    "焦虑": {
        "name_zh": "焦虑",
        "name_en": "Anxiety",
        "domain": "临床与健康",
        "definition": (
            "焦虑是个体在面对潜在威胁或不确定性时产生的一种以担忧、紧张和恐惧为核心特征的"
            "情绪状态（Spielberger, 1983）。状态焦虑是暂时的情绪反应，特质焦虑是相对稳定的"
            "人格倾向。焦虑涉及认知（过度担忧、灾难化思维）、情感（紧张不安）、"
            "生理（心悸、出汗、肌肉紧张）和行为（回避、警觉）四个层面。"
        ),
        "dimensions": [
            {"name": "认知焦虑", "desc": "过度担忧、灾难化预期、注意力难以集中",
             "item_count": 5, "example": "我经常担心会发生不好的事情"},
            {"name": "情感焦虑", "desc": "紧张、不安、恐惧的主观体验",
             "item_count": 4, "example": "我感到紧张不安"},
            {"name": "生理焦虑", "desc": "心悸、出汗、呼吸急促、肌肉紧张等躯体反应",
             "item_count": 5, "example": "我感到心跳加速或心悸"},
            {"name": "行为焦虑", "desc": "回避行为、坐立不安、言语急促",
             "item_count": 4, "example": "我会避开让我紧张的情境"},
        ],
        "typical_scale": "4点频率量表（1=从不, 2=偶尔, 3=经常, 4=总是）",
        "established_scales": [
            "状态-特质焦虑问卷 (STAI; Spielberger, 1983) — 40题",
            "贝克焦虑量表 (BAI; Beck, Epstein, Brown & Steer, 1988) — 21题",
            "焦虑自评量表 (SAS; Zung, 1971) — 20题",
            "广泛性焦虑障碍量表 (GAD-7; Spitzer et al., 2006) — 7题",
        ],
        "references": [
            "Spielberger, C. D. (1983). Manual for the State-Trait Anxiety Inventory. Consulting Psychologists Press.",
            "Beck, A. T., Epstein, N., Brown, G., & Steer, R. A. (1988). An inventory for measuring clinical anxiety: Psychometric properties. Journal of Consulting and Clinical Psychology, 56(6), 893-897.",
            "Zung, W. W. K. (1971). A rating instrument for anxiety disorders. Psychosomatics, 12(6), 371-379.",
        ],
    },

    "抑郁": {
        "name_zh": "抑郁",
        "name_en": "Depression",
        "domain": "临床与健康",
        "definition": (
            "抑郁是一种以持续的情绪低落、兴趣减退和快感缺失为核心特征的心境障碍"
            "（APA, 2013）。其症状包括情感（悲伤、空虚）、认知（无价值感、自责、"
            "注意困难）、动机（意志减退）和躯体（食欲/睡眠改变、疲劳）四个方面。"
        ),
        "dimensions": [
            {"name": "情感症状", "desc": "悲伤、空虚、易激惹等情绪体验",
             "item_count": 4, "example": "我感到心情低落或悲伤"},
            {"name": "认知症状", "desc": "无价值感、过度自责、悲观思维",
             "item_count": 5, "example": "我觉得自己是个失败者"},
            {"name": "动机/行为症状", "desc": "兴趣丧失、社交退缩、意志活动减少",
             "item_count": 4, "example": "我对以前喜欢的事情失去了兴趣"},
            {"name": "躯体症状", "desc": "食欲/体重变化、睡眠障碍、疲劳感",
             "item_count": 5, "example": "我睡眠不好（入睡困难或早醒）"},
        ],
        "typical_scale": "4点频率量表（0=从不, 1=有时, 2=经常, 3=总是）",
        "established_scales": [
            "贝克抑郁量表第二版 (BDI-II; Beck, Steer & Brown, 1996) — 21题",
            "流调中心抑郁量表 (CES-D; Radloff, 1977) — 20题",
            "患者健康问卷抑郁量表 (PHQ-9; Kroenke et al., 2001) — 9题",
            "抑郁自评量表 (SDS; Zung, 1965) — 20题",
        ],
        "references": [
            "Beck, A. T., Steer, R. A., & Brown, G. K. (1996). Manual for the Beck Depression Inventory-II. Psychological Corporation.",
            "Radloff, L. S. (1977). The CES-D scale: A self-report depression scale for research in the general population. Applied Psychological Measurement, 1(3), 385-401.",
            "Kroenke, K., Spitzer, R. L., & Williams, J. B. W. (2001). The PHQ-9: Validity of a brief depression severity measure. Journal of General Internal Medicine, 16(9), 606-613.",
        ],
    },

    "压力": {
        "name_zh": "压力",
        "name_en": "Stress / Perceived Stress",
        "domain": "临床与健康",
        "definition": (
            "心理压力是个体对环境需求超出自身应对资源时的主观评估和反应"
            "（Lazarus & Folkman, 1984）。包括压力源（外部事件）、"
            "压力感知（主观评估）和压力反应（生理、心理和行为反应）。"
        ),
        "dimensions": [
            {"name": "压力感知", "desc": "对生活情境的主观压力评估",
             "item_count": 5, "example": "在过去一个月里，你感到事情超出你控制的程度"},
            {"name": "情绪反应", "desc": "紧张、易怒、焦虑等情绪应激反应",
             "item_count": 4, "example": "我因为压力而感到烦躁易怒"},
            {"name": "躯体反应", "desc": "头痛、疲劳、睡眠困难等躯体症状",
             "item_count": 4, "example": "压力让我感到身体疲惫"},
            {"name": "应对资源", "desc": "个体感知到的应对能力和支持",
             "item_count": 4, "example": "我觉得自己有能力应对当前的压力"},
        ],
        "typical_scale": "5点频率量表（0=从不, 4=总是）",
        "established_scales": [
            "感知压力量表 (PSS; Cohen, Kamarck & Mermelstein, 1983) — 14/10题",
            "生活事件量表 (LES; Holmes & Rahe, 1967)",
            "抑郁-焦虑-压力量表 (DASS-21; Lovibond & Lovibond, 1995)",
        ],
        "references": [
            "Lazarus, R. S., & Folkman, S. (1984). Stress, Appraisal, and Coping. Springer.",
            "Cohen, S., Kamarck, T., & Mermelstein, R. (1983). A global measure of perceived stress. Journal of Health and Social Behavior, 24(4), 385-396.",
        ],
    },

    "主观幸福感": {
        "name_zh": "主观幸福感",
        "name_en": "Subjective Well-Being",
        "domain": "临床与健康",
        "definition": (
            "主观幸福感是个体根据自定标准对其生活质量的整体性评价（Diener, 1984），"
            "包含生活满意度（认知评价）和情感平衡（积极与消极情感的比率）两个核心成分。"
        ),
        "dimensions": [
            {"name": "生活满意度", "desc": "对整体生活及各领域的认知评价",
             "item_count": 6, "example": "我对我的生活感到满意"},
            {"name": "积极情感", "desc": "愉快、满足、兴奋等积极情绪的频率和强度",
             "item_count": 5, "example": "我经常感到快乐"},
            {"name": "消极情感", "desc": "悲伤、焦虑、愤怒等消极情绪的频率和强度",
             "item_count": 5, "example": "我经常感到难过（反向计分）"},
        ],
        "typical_scale": "7点同意度量表（1=完全不同意, 7=完全同意）",
        "established_scales": [
            "生活满意度量表 (SWLS; Diener et al., 1985) — 5题",
            "积极与消极情感量表 (PANAS; Watson, Clark & Tellegen, 1988) — 20题",
            "牛津幸福感问卷 (OHQ; Hills & Argyle, 2002) — 29题",
        ],
        "references": [
            "Diener, E. (1984). Subjective well-being. Psychological Bulletin, 95(3), 542-575.",
            "Diener, E., Emmons, R. A., Larsen, R. J., & Griffin, S. (1985). The Satisfaction With Life Scale. Journal of Personality Assessment, 49(1), 71-75.",
            "Watson, D., Clark, L. A., & Tellegen, A. (1988). Development and validation of brief measures of positive and negative affect: The PANAS scales. Journal of Personality and Social Psychology, 54(6), 1063-1070.",
        ],
    },

    # ================================================================
    # 人格心理学
    # ================================================================
    "自尊": {
        "name_zh": "自尊",
        "name_en": "Self-Esteem",
        "domain": "人格",
        "definition": (
            "自尊是个体对自我价值的整体性评价和情感体验（Rosenberg, 1965）。"
            "高自尊者通常接纳自己、认可自身价值；低自尊者倾向于自我怀疑和自我贬低。"
            "自尊可分为外显自尊（意识层面的自我评价）和内隐自尊（无意识的自我态度）。"
        ),
        "dimensions": [
            {"name": "自我价值感", "desc": "对自身整体价值的评价",
             "item_count": 5, "example": "我觉得自己是有价值的人"},
            {"name": "自我接纳", "desc": "接纳自己的优点和不足",
             "item_count": 5, "example": "我能够接受自己的缺点"},
            {"name": "自我效能感", "desc": "对自己能力的信心",
             "item_count": 4, "example": "我相信自己能够完成设定的目标"},
        ],
        "typical_scale": "4点同意度量表（1=完全不同意, 4=完全同意）",
        "established_scales": [
            "Rosenberg自尊量表 (RSES; Rosenberg, 1965) — 10题",
            "Coopersmith自尊问卷 (Coopersmith, 1967) — 58题",
        ],
        "references": [
            "Rosenberg, M. (1965). Society and the Adolescent Self-Image. Princeton University Press.",
        ],
    },

    "自我效能感": {
        "name_zh": "自我效能感",
        "name_en": "Self-Efficacy",
        "domain": "人格",
        "definition": (
            "自我效能感是个体对自己组织和执行达成特定目标所需行为的能力信念"
            "（Bandura, 1997）。自我效能感影响个体的行为选择、努力程度、"
            "坚持性和情绪反应。区别于自尊（对自我价值的评价），自我效能感"
            "是特定领域的（也可测量一般自我效能感）。"
        ),
        "dimensions": [
            {"name": "一般自我效能", "desc": "对自身应对各类任务和挑战能力的总体信念",
             "item_count": 5, "example": "我总能找到解决困难的办法"},
            {"name": "坚持性", "desc": "面对困难时不放弃的信念",
             "item_count": 3, "example": "即使遇到挫折，我也不会轻易放弃"},
            {"name": "效能预期", "desc": "对未来完成任务的预期和信心",
             "item_count": 4, "example": "我有信心完成我设定的目标"},
        ],
        "typical_scale": "5点同意度量表（1=完全不符合, 5=完全符合）",
        "established_scales": [
            "一般自我效能感量表 (GSES; Schwarzer & Jerusalem, 1995) — 10题",
            "学业自我效能感量表 (Bandura, 2006)",
        ],
        "references": [
            "Bandura, A. (1997). Self-Efficacy: The Exercise of Control. Freeman.",
            "Schwarzer, R., & Jerusalem, M. (1995). Generalized Self-Efficacy Scale. In J. Weinman, S. Wright, & M. Johnston (Eds.), Measures in Health Psychology.",
        ],
    },

    # ================================================================
    # 社会心理学
    # ================================================================
    "社会支持": {
        "name_zh": "社会支持",
        "name_en": "Social Support",
        "domain": "社会心理",
        "definition": (
            "社会支持是个体感知到来自他人或社会网络的物质、情感和信息援助"
            "（Cohen & Wills, 1985）。可分为客观支持（实际获得的帮助）"
            "和主观支持（感知到的支持可用性）。社会支持是心理健康的重要保护因素。"
        ),
        "dimensions": [
            {"name": "情感支持", "desc": "被关心、被理解、被尊重的感受",
             "item_count": 4, "example": "有人真心关心我的感受"},
            {"name": "工具支持", "desc": "获得实际的物质帮助或服务",
             "item_count": 3, "example": "在我需要时有人可以帮我做事"},
            {"name": "信息支持", "desc": "获得建议、指导和反馈",
             "item_count": 3, "example": "有人能在我做决定时给我建议"},
            {"name": "陪伴支持", "desc": "有人可以一起活动、分享时光",
             "item_count": 2, "example": "我有可以一起休闲娱乐的伙伴"},
        ],
        "typical_scale": "5点同意度量表（1=完全不同意, 5=完全同意）",
        "established_scales": [
            "社会支持评定量表 (SSRS; 肖水源, 1994) — 10题",
            "多维社会支持感知量表 (MSPSS; Zimet et al., 1988) — 12题",
            "社会支持行为量表 (ISSB; Barrera, 1981)",
        ],
        "references": [
            "Cohen, S., & Wills, T. A. (1985). Stress, social support, and the buffering hypothesis. Psychological Bulletin, 98(2), 310-357.",
            "Zimet, G. D., Dahlem, N. W., Zimet, S. G., & Farley, G. K. (1988). The Multidimensional Scale of Perceived Social Support. Journal of Personality Assessment, 52(1), 30-41.",
        ],
    },

    "孤独感": {
        "name_zh": "孤独感",
        "name_en": "Loneliness",
        "domain": "社会心理",
        "definition": (
            "孤独感是个体因期望的社会关系与实际的社会关系之间存在的差距而产生的"
            "不愉快体验（Peplau & Perlman, 1982）。区别于客观的社会隔离，"
            "孤独感是主观感受——一个人可以在人群中感到孤独。"
        ),
        "dimensions": [
            {"name": "情感孤独", "desc": "缺乏亲密、依恋的情感联结",
             "item_count": 5, "example": "我没有人可以真正倾诉心事"},
            {"name": "社交孤独", "desc": "缺乏社交网络和团体归属感",
             "item_count": 5, "example": "我觉得自己不属于任何群体"},
        ],
        "typical_scale": "4点频率量表（1=从不, 4=总是）",
        "established_scales": [
            "UCLA孤独量表第三版 (Russell, 1996) — 20题",
            "De Jong Gierveld孤独量表 (De Jong Gierveld & Van Tilburg, 2006) — 11题",
        ],
        "references": [
            "Peplau, L. A., & Perlman, D. (1982). Loneliness: A Sourcebook of Current Theory, Research and Therapy. Wiley.",
            "Russell, D. W. (1996). UCLA Loneliness Scale (Version 3): Reliability, validity, and factor structure. Journal of Personality Assessment, 66(1), 20-40.",
        ],
    },

    # ================================================================
    # 教育心理学
    # ================================================================
    "学习动机": {
        "name_zh": "学习动机",
        "name_en": "Academic Motivation",
        "domain": "教育心理",
        "definition": (
            "学习动机是激发和维持个体学习行为并使其朝向特定学业目标的内在心理动力"
            "（Pintrich & Schunk, 2002）。自我决定理论区分内在动机（出于兴趣和"
            "愉悦）、外在动机（出于外部奖惩）和去动机（缺乏动机）。"
        ),
        "dimensions": [
            {"name": "内在动机", "desc": "出于兴趣、好奇和愉悦而学习",
             "item_count": 5, "example": "我学习是因为我对知识本身感兴趣"},
            {"name": "外在动机", "desc": "出于成绩、奖励、认可等外部因素而学习",
             "item_count": 5, "example": "我努力学习是为了获得好成绩"},
            {"name": "成就动机", "desc": "追求成功和避免失败的倾向",
             "item_count": 4, "example": "我享受攻克难题后的成就感"},
            {"name": "自我效能", "desc": "对自己学习能力的信心",
             "item_count": 4, "example": "我相信自己能够学好这门课程"},
        ],
        "typical_scale": "7点同意度量表（1=完全不符合, 7=完全符合）",
        "established_scales": [
            "学业动机量表 (AMS; Vallerand et al., 1989) — 28题",
            "学习动机策略问卷 (MSLQ; Pintrich et al., 1993) — 动机部分31题",
        ],
        "references": [
            "Pintrich, P. R., & Schunk, D. H. (2002). Motivation in Education: Theory, Research, and Applications. Prentice Hall.",
            "Vallerand, R. J., Pelletier, L. G., Blais, M. R., et al. (1992). The Academic Motivation Scale: A measure of intrinsic, extrinsic, and amotivation in education. Educational and Psychological Measurement, 52(4), 1003-1017.",
        ],
    },

    "考试焦虑": {
        "name_zh": "考试焦虑",
        "name_en": "Test Anxiety",
        "domain": "教育心理",
        "definition": (
            "考试焦虑是学生在评价情境中产生的以担忧、紧张和生理唤起为特征的"
            "特定情境焦虑（Sarason, 1984）。包含担忧（认知成分）和情绪性"
            "（情感-生理成分）两个核心维度。"
        ),
        "dimensions": [
            {"name": "担忧/认知", "desc": "对考试结果的负面预期、自我贬低思维",
             "item_count": 5, "example": "考试时我会想\"我肯定考不好\""},
            {"name": "情绪性/生理", "desc": "考试情境中的紧张、心跳加快等生理反应",
             "item_count": 5, "example": "考试前我会感到心跳加速"},
        ],
        "typical_scale": "4点频率量表（1=几乎从不, 4=几乎总是）",
        "established_scales": [
            "考试焦虑量表 (TAI; Spielberger, 1980) — 20题",
            "Sarason考试焦虑量表 (Sarason, 1984)",
        ],
        "references": [
            "Sarason, I. G. (1984). Stress, anxiety, and cognitive interference: Reactions to tests. Journal of Personality and Social Psychology, 46(4), 929-938.",
        ],
    },

    # ================================================================
    # 组织行为心理学
    # ================================================================
    "工作满意度": {
        "name_zh": "工作满意度",
        "name_en": "Job Satisfaction",
        "domain": "组织行为",
        "definition": (
            "工作满意度是员工对其工作及工作各方面的一种积极或消极的情感评价"
            "（Locke, 1976）。包括对工作本身、薪酬、晋升、上级、同事等"
            "多个方面的满意度。"
        ),
        "dimensions": [
            {"name": "工作本身满意度", "desc": "对工作内容、挑战性和意义的评价",
             "item_count": 4, "example": "我觉得我的工作很有意义"},
            {"name": "薪酬满意度", "desc": "对工资、福利的公平感和满意程度",
             "item_count": 3, "example": "我认为我的薪酬与付出相匹配"},
            {"name": "发展满意度", "desc": "对晋升机会和职业发展的评价",
             "item_count": 3, "example": "我在工作中能看到成长和发展的空间"},
            {"name": "关系满意度", "desc": "对上级和同事关系的评价",
             "item_count": 4, "example": "我与同事们相处融洽"},
            {"name": "工作环境满意度", "desc": "对物理环境和工作条件的评价",
             "item_count": 2, "example": "我的工作环境舒适宜人"},
        ],
        "typical_scale": "5点同意度量表（1=非常不满意, 5=非常满意）",
        "established_scales": [
            "明尼苏达满意度问卷 (MSQ; Weiss et al., 1967) — 长版100题/短版20题",
            "工作描述指数 (JDI; Smith, Kendall & Hulin, 1969)",
            "工作满意度量表 (JSS; Spector, 1985) — 36题",
        ],
        "references": [
            "Locke, E. A. (1976). The nature and causes of job satisfaction. In M. D. Dunnette (Ed.), Handbook of Industrial and Organizational Psychology.",
            "Weiss, D. J., Dawis, R. V., England, G. W., & Lofquist, L. H. (1967). Manual for the Minnesota Satisfaction Questionnaire.",
        ],
    },

    "职业倦怠": {
        "name_zh": "职业倦怠",
        "name_en": "Burnout",
        "domain": "组织行为",
        "definition": (
            "职业倦怠是个体在工作环境中因长期暴露于情绪和人际压力而产生的一种"
            "以情绪耗竭、去人格化和个人成就感降低为特征的心理综合征"
            "（Maslach & Jackson, 1981）。常见于助人行业和高压力职业。"
        ),
        "dimensions": [
            {"name": "情绪耗竭", "desc": "情感资源耗尽、感到疲惫不堪",
             "item_count": 5, "example": "一天的工作让我感到精疲力竭"},
            {"name": "去人格化", "desc": "对服务对象/工作产生冷漠、疏远的态度",
             "item_count": 5, "example": "我对工作中面对的人越来越冷漠"},
            {"name": "个人成就感降低", "desc": "对自己工作能力和成就的评价下降",
             "item_count": 5, "example": "我觉得自己的工作没有价值"},
        ],
        "typical_scale": "7点频率量表（0=从不, 6=每天）",
        "established_scales": [
            "Maslach倦怠问卷 (MBI; Maslach & Jackson, 1981) — 22题",
            "Oldenburg倦怠问卷 (OLBI; Demerouti et al., 2003)",
        ],
        "references": [
            "Maslach, C., & Jackson, S. E. (1981). The measurement of experienced burnout. Journal of Organizational Behavior, 2(2), 99-113.",
        ],
    },

    # ================================================================
    # 认知心理学
    # ================================================================
    "元认知": {
        "name_zh": "元认知",
        "name_en": "Metacognition",
        "domain": "认知",
        "definition": (
            "元认知是个体对自己认知过程的知识、监控和调节（Flavell, 1979）。"
            "包含元认知知识（关于认知的知识）和元认知调节（对认知过程的控制和监控）"
            "两个层面。"
        ),
        "dimensions": [
            {"name": "元认知知识", "desc": "对自己认知能力和策略的了解",
             "item_count": 5, "example": "我知道自己的学习优势和弱点"},
            {"name": "元认知监控", "desc": "对当前认知活动的监督和评价",
             "item_count": 4, "example": "学习时我会检查自己是否理解了内容"},
            {"name": "元认知调节", "desc": "根据监控结果调整认知策略",
             "item_count": 4, "example": "发现理解不了时会换一种学习方法"},
        ],
        "typical_scale": "5点同意度量表（1=完全不符合, 5=完全符合）",
        "established_scales": [
            "元认知意识问卷 (MAI; Schraw & Dennison, 1994) — 52题",
            "状态元认知问卷 (O'Neil & Abedi, 1996)",
        ],
        "references": [
            "Flavell, J. H. (1979). Metacognition and cognitive monitoring. American Psychologist, 34(10), 906-911.",
            "Schraw, G., & Dennison, R. S. (1994). Assessing metacognitive awareness. Contemporary Educational Psychology, 19(4), 460-475.",
        ],
    },

    # ═══════════════════════════════════════════════════════
    # 组织行为学 (8个新构念)
    # ═══════════════════════════════════════════════════════
    "工作投入": {
        "name_zh": "工作投入", "name_en": "Work Engagement", "domain": "组织行为",
        "definition": "工作投入是一种与工作相关的积极、充实的心理状态，以活力（vigor）、奉献（dedication）和专注（absorption）为核心特征（Schaufeli et al., 2002）。活力指工作时的高能量和心理韧性；奉献指对工作的意义感、热情和自豪；专注指全神贯注沉浸于工作的状态。",
        "dimensions": [
            {"name": "活力", "desc": "工作时的高能量水平、心理韧性和努力意愿", "item_count": 6, "example": "早上起床时，我很想去工作"},
            {"name": "奉献", "desc": "对工作的意义感、热情、激励和挑战感受", "item_count": 5, "example": "我对自己的工作充满热情"},
            {"name": "专注", "desc": "全神贯注沉浸于工作，感觉时间飞逝", "item_count": 6, "example": "当我专心工作时，我感到快乐"},
        ],
        "typical_scale": "7点频率量表（0=从不, 6=每天）",
        "established_scales": [
            "Utrecht工作投入量表 (UWES; Schaufeli et al., 2002) — 17题和9题简版",
            "工作投入量表中文版 (张轶文, 甘怡群, 2005) — 15题",
        ],
        "references": [
            "Schaufeli, W. B., Salanova, M., González-Romá, V., & Bakker, A. B. (2002). The measurement of engagement and burnout: A two sample confirmatory factor analytic approach. Journal of Happiness Studies, 3(1), 71-92.",
            "张轶文, 甘怡群. (2005). 中文版Utrecht工作投入量表的信效度检验. 中国临床心理学杂志, 13(3), 268-270.",
        ],
    },
    "工作倦怠": {
        "name_zh": "工作倦怠", "name_en": "Job Burnout", "domain": "组织行为",
        "definition": "工作倦怠是个体在工作环境中因长期承受情绪和人际压力而产生的一种以情绪耗竭（emotional exhaustion）、去人格化/玩世不恭（depersonalization/cynicism）和成就感降低（reduced personal accomplishment）为特征的心理综合征（Maslach & Jackson, 1981）。",
        "dimensions": [
            {"name": "情绪耗竭", "desc": "感到情感资源被耗尽、身心疲惫", "item_count": 5, "example": "工作让我感到身心俱疲"},
            {"name": "去人格化", "desc": "对工作对象和环境产生消极、冷漠的态度", "item_count": 5, "example": "我对工作的热情已经消失了"},
            {"name": "成就感降低", "desc": "对自己工作能力和成就的负面评价", "item_count": 6, "example": "我完成了很多有价值的工作（反向题）"},
        ],
        "typical_scale": "7点频率量表（0=从不, 6=每天）",
        "established_scales": [
            "Maslach职业倦怠问卷 (MBI; Maslach & Jackson, 1981) — 22题",
            "MBI-GS通用版 (Schaufeli et al., 1996) — 16题",
        ],
        "references": [
            "Maslach, C., & Jackson, S. E. (1981). The measurement of experienced burnout. Journal of Organizational Behavior, 2(2), 99-113.",
        ],
    },
    "组织承诺": {
        "name_zh": "组织承诺", "name_en": "Organizational Commitment", "domain": "组织行为",
        "definition": "组织承诺是员工对组织的心理依恋和认同程度，反映了个体与组织之间的心理契约强度。Allen和Meyer(1990)提出三维模型：情感承诺（对组织的情感依恋）、持续承诺（离职成本的认知）和规范承诺（留任的义务感）。",
        "dimensions": [
            {"name": "情感承诺", "desc": "对组织的情感依恋和认同", "item_count": 5, "example": "我很乐意在这个组织中度过我余下的职业生涯"},
            {"name": "持续承诺", "desc": "因离开组织的成本而留在组织的倾向", "item_count": 5, "example": "如果现在离开组织，我的生活会受到很大影响"},
            {"name": "规范承诺", "desc": "感到应该留在组织中的道德义务", "item_count": 5, "example": "我觉得应该对现在的组织保持忠诚"},
        ],
        "typical_scale": "7点同意度量表（1=非常不同意, 7=非常同意）",
        "established_scales": [
            "组织承诺量表 TCM (Allen & Meyer, 1990) — 18题三维度",
            "情感承诺量表 ACS 简版 (Meyer, Allen & Smith, 1993) — 6题情感承诺单维",
            "中文修订版 (Chen & Francesco, 2003) — 应用心理学，华人本土化效度验证",
        ],
        "references": [
            "Allen, N. J., & Meyer, J. P. (1990). The measurement and antecedents of affective, continuance and normative commitment to the organization. Journal of Occupational Psychology, 63(1), 1-18.",
            "Meyer, J. P., Allen, N. J., & Smith, C. A. (1993). Commitment to organizations and occupations: Extension and test of a three-component conceptualization. Journal of Applied Psychology, 78(4), 538-551.",
            "Chen, Z. X., & Francesco, A. M. (2003). The relationship between the three components of commitment and employee performance in China. Journal of Vocational Behavior, 62(3), 490-510.",
        ],
    },
    "心理资本": {
        "name_zh": "心理资本", "name_en": "Psychological Capital", "domain": "组织行为",
        "definition": "心理资本是个体在成长和发展过程中表现出来的一种积极心理状态，包含自我效能感、乐观、希望和韧性四个维度（Luthans et al., 2007）。心理资本是可以测量、开发和管理的状态类积极心理资源。",
        "dimensions": [
            {"name": "自我效能", "desc": "面对挑战性任务时有信心付出必要努力并取得成功", "item_count": 6, "example": "我相信自己能够分析长远问题并找到解决方案"},
            {"name": "乐观", "desc": "对当前和未来成功做积极归因", "item_count": 6, "example": "我对工作的未来感到乐观"},
            {"name": "希望", "desc": "坚持目标，必要时调整路径以实现目标", "item_count": 6, "example": "我能想出很多办法来摆脱工作中的困境"},
            {"name": "韧性", "desc": "面对困难和挫折时能够坚持和复原", "item_count": 6, "example": "在工作中遇到挫折后我能很快恢复过来"},
        ],
        "typical_scale": "6点同意度量表",
        "established_scales": [
            "心理资本问卷 (PCQ-24; Luthans et al., 2007) — 24题",
        ],
        "references": [
            "Luthans, F., Youssef, C. M., & Avolio, B. J. (2007). Psychological capital: Developing the human competitive edge. Oxford University Press.",
        ],
    },
    "变革型领导": {
        "name_zh": "变革型领导", "name_en": "Transformational Leadership", "domain": "组织行为",
        "definition": "变革型领导是通过激发下属的高层次需要、建立互信关系和树立榜样来促使下属超越个人利益、追求集体目标和实现非凡成就的领导行为（Bass, 1985）。包含理想化影响、鼓舞性激励、智力激发和个性化关怀四个维度。",
        "dimensions": [
            {"name": "理想化影响", "desc": "领导者成为下属的榜样和楷模", "item_count": 5, "example": "我的领导让我对他/她产生尊敬"},
            {"name": "鼓舞性激励", "desc": "为下属提供富有意义和挑战性的愿景", "item_count": 4, "example": "我的领导用对未来的乐观描述激励我"},
            {"name": "智力激发", "desc": "鼓励下属创新思维和质疑旧有假设", "item_count": 4, "example": "我的领导鼓励我从不同角度看待问题"},
            {"name": "个性化关怀", "desc": "关注每个下属的成长需求和发展", "item_count": 4, "example": "我的领导会花时间一对一指导我"},
        ],
        "typical_scale": "5点频率量表（0=从不, 4=总是）",
        "established_scales": [
            "多因素领导力问卷 (MLQ; Bass & Avolio, 1995)",
        ],
        "references": [
            "Bass, B. M. (1985). Leadership and performance beyond expectations. Free Press.",
        ],
    },
    "工作-家庭冲突": {
        "name_zh": "工作-家庭冲突", "name_en": "Work-Family Conflict", "domain": "组织行为",
        "definition": "工作-家庭冲突是指工作角色要求和家庭角色要求之间发生不可协调的压力时产生的一种角色间冲突（Greenhaus & Beutell, 1985）。包含工作干扰家庭（WIF）和家庭干扰工作（FIW）两个方向。",
        "dimensions": [
            {"name": "工作干扰家庭", "desc": "工作责任干扰家庭生活角色的履行", "item_count": 5, "example": "工作花去的时间让我难以履行家庭责任"},
            {"name": "家庭干扰工作", "desc": "家庭责任干扰工作角色的履行", "item_count": 5, "example": "家庭生活占据的时间干扰了我的工作"},
        ],
        "typical_scale": "5点同意度量表",
        "established_scales": [
            "工作家庭冲突量表 (Carlson, Kacmar & Williams, 2000) — 18题三维度（时间/压力/行为）",
            "双向工作家庭冲突量表 (Netemeyer, Boles & McMurrian, 1996) — WFC 5题 + FWC 5题，最高被引",
            "工作家庭充实量表 (Carlson, Kacmar, Wayne & Grzywacz, 2006) — 18题，捕捉双向促进面",
        ],
        "references": [
            "Greenhaus, J. H., & Beutell, N. J. (1985). Sources of conflict between work and family roles. Academy of Management Review, 10(1), 76-88.",
            "Netemeyer, R. G., Boles, J. S., & McMurrian, R. (1996). Development and validation of work-family conflict and family-work conflict scales. Journal of Applied Psychology, 81(4), 400-410.",
            "Carlson, D. S., Kacmar, K. M., Wayne, J. H., & Grzywacz, J. G. (2006). Measuring the positive side of the work-family interface: Development and validation of a work-family enrichment scale. Journal of Vocational Behavior, 68(1), 131-164.",
        ],
    },
    "组织公民行为": {
        "name_zh": "组织公民行为", "name_en": "Organizational Citizenship Behavior", "domain": "组织行为",
        "definition": "组织公民行为是指未被正式报酬体系直接认可但能在总体上提高组织效能的员工的自主性行为（Organ, 1988）。包括利他、责任心、运动员精神、礼貌和公民美德等维度。",
        "dimensions": [
            {"name": "利他行为", "desc": "主动帮助他人解决工作相关问题", "item_count": 4, "example": "我愿意花时间帮助在工作中遇到困难的同事"},
            {"name": "责任心", "desc": "超出角色要求的认真负责行为", "item_count": 4, "example": "即使无人监督我也严格遵守公司规定"},
            {"name": "公民美德", "desc": "积极参与和关心组织事务", "item_count": 4, "example": "我密切关注组织的重要公告和通知"},
        ],
        "typical_scale": "5点频率量表",
        "established_scales": [
            "OCB 量表 (Podsakoff et al., 1990) — 24题五维度（利他/责任/运动家精神/礼貌/公民美德）",
            "华人 OCB 量表 (Farh, Earley & Lin, 1997) — Administrative Science Quarterly，识别华人文化特有维度",
            "扩展华人 OCB 量表 (Farh, Zhong & Organ, 2004) — 5维度 20题，含保护公司资源/参与社会公益",
        ],
        "references": [
            "Organ, D. W. (1988). Organizational citizenship behavior: The good soldier syndrome. Lexington Books.",
            "Farh, J. L., Earley, P. C., & Lin, S. C. (1997). Impetus for action: A cultural analysis of justice and organizational citizenship behavior in Chinese society. Administrative Science Quarterly, 42(3), 421-444.",
            "Farh, J. L., Zhong, C. B., & Organ, D. W. (2004). Organizational citizenship behavior in the People's Republic of China. Organization Science, 15(2), 241-253.",
        ],
    },
    "成就动机": {
        "name_zh": "成就动机", "name_en": "Achievement Motivation", "domain": "组织行为",
        "definition": "成就动机是个体在完成有意义任务时追求成功、超越标准的内在驱动力，包含追求成功的动机（hope of success）和避免失败的动机（fear of failure）两个维度（Atkinson, 1957）。",
        "dimensions": [
            {"name": "追求成功", "desc": "追求卓越、达成目标的积极动机", "item_count": 5, "example": "我更喜欢选择有挑战性的任务"},
            {"name": "避免失败", "desc": "回避失败和负面评价的防御性动机", "item_count": 5, "example": "我通常避免做我不确定自己能做好的事情（反向题）"},
        ],
        "typical_scale": "5点同意度量表",
        "established_scales": [
            "成就动机量表 (AMS; Gjesme & Nygard, 1970) — 30题",
            "叶仁敏修订中文版 (1988)",
        ],
        "references": [
            "Atkinson, J. W. (1957). Motivational determinants of risk-taking behavior. Psychological Review, 64(6), 359-372.",
        ],
    },
    "员工敬业度": {
        "name_zh": "员工敬业度", "name_en": "Work Engagement", "domain": "组织行为",
        "definition": "员工敬业度是员工在工作中持续表现出的积极、充实的认知-情感状态（Schaufeli & Bakker, 2003），由活力（vigor）、奉献（dedication）和专注（absorption）三个维度构成。它是职业倦怠的对立面，反映员工与工作角色的高质量心理投入，是 People Analytics 与 HRBP 实务最常追踪的核心指标之一。",
        "dimensions": [
            {"name": "活力", "desc": "工作中的高水平能量与心理韧性、不易疲倦", "item_count": 6, "example": "工作时我感到充满能量"},
            {"name": "奉献", "desc": "对工作的强烈投入感、意义感与挑战感", "item_count": 5, "example": "我对自己所做的工作充满热情"},
            {"name": "专注", "desc": "全神贯注于工作、时间感扭曲", "item_count": 6, "example": "我工作时时间过得很快"},
        ],
        "typical_scale": "7点频率量表（0=从不, 6=每天）",
        "established_scales": [
            "Utrecht 工作投入量表 UWES-17 (Schaufeli & Bakker, 2003) — 17题三维度全测",
            "UWES-9 简版 (Schaufeli, Bakker & Salanova, 2006) — 9题，中国研究最常用",
            "中文修订版 (张轶文, 甘怡群, 2005) — 中国临床心理学杂志，华人样本效度验证",
        ],
        "references": [
            "Schaufeli, W. B., & Bakker, A. B. (2003). UWES - Utrecht Work Engagement Scale: Test manual. Utrecht University.",
            "Schaufeli, W. B., Bakker, A. B., & Salanova, M. (2006). The measurement of work engagement with a short questionnaire: A cross-national study. Educational and Psychological Measurement, 66(4), 701-716.",
            "张轶文, 甘怡群. (2005). 中文版 Utrecht 工作投入量表(UWES)的信效度检验. 中国临床心理学杂志, 13(3), 268-270.",
        ],
    },
    "家长式领导": {
        "name_zh": "家长式领导", "name_en": "Paternalistic Leadership", "domain": "组织行为",
        "definition": "家长式领导是华人组织情境下特有的领导风格（郑伯埙等, 2000, 2004），表现为类似父母对待子女的方式管理下属，包含威权、仁慈与德行三个核心维度。是华人 OB 研究的标志性本土化构念，被《心理学报》《管理世界》大量引用，具有不可替代的文化嵌入性。",
        "dimensions": [
            {"name": "威权领导", "desc": "强调权威、控制与服从的管理行为", "item_count": 9, "example": "我的领导经常以严厉的口气与下属说话"},
            {"name": "仁慈领导", "desc": "对下属个人福祉与困难给予全面关怀", "item_count": 11, "example": "我的领导会给予下属个别化的体贴与照顾"},
            {"name": "德行领导", "desc": "以个人品德为榜样赢得下属敬佩", "item_count": 6, "example": "我的领导以身作则做事公正"},
        ],
        "typical_scale": "5点同意度量表（1=非常不同意, 5=非常同意）",
        "established_scales": [
            "家长式领导量表 PLS-26 (郑伯埙, 周丽芳, 樊景立, 2000) — 本土心理学研究，原始版",
            "国际版 (Cheng, Chou, Wu, Huang & Farh, 2004) — Asian Journal of Social Psychology",
        ],
        "references": [
            "郑伯埙, 周丽芳, 樊景立. (2000). 家长式领导: 三元模式的建构与测量. 本土心理学研究, 14, 3-64.",
            "Cheng, B. S., Chou, L. F., Wu, T. Y., Huang, M. P., & Farh, J. L. (2004). Paternalistic leadership and subordinate responses: Establishing a leadership model in Chinese organizations. Asian Journal of Social Psychology, 7(1), 89-117.",
        ],
    },
    "伦理型领导": {
        "name_zh": "伦理型领导", "name_en": "Ethical Leadership", "domain": "组织行为",
        "definition": "伦理型领导是指领导者通过个人行为和人际关系展现出符合规范的恰当行为，并通过双向沟通、强化和决策向下属传递这些行为的领导方式（Brown, Treviño & Harrison, 2005）。它强调领导者既要做「道德人」也要做「道德管理者」，对员工伦理行为、组织公民行为有显著示范效应，近年在华人 OB 研究中被引量快速上升。",
        "dimensions": [
            {"name": "道德人", "desc": "个人品德与道德规范的展现（榜样面）", "item_count": 5, "example": "我的领导以身作则展示诚信"},
            {"name": "道德管理者", "desc": "通过沟通、奖惩、决策塑造员工伦理行为（管理面）", "item_count": 5, "example": "我的领导明确传达对员工伦理行为的期望"},
        ],
        "typical_scale": "5点同意度量表",
        "established_scales": [
            "伦理型领导量表 ELS-10 (Brown, Treviño & Harrison, 2005) — 10题单因子结构",
            "中文版 (徐世勇等, 2009) — 心理科学，中国情境验证",
        ],
        "references": [
            "Brown, M. E., Treviño, L. K., & Harrison, D. A. (2005). Ethical leadership: A social learning perspective for construct development and testing. Organizational Behavior and Human Decision Processes, 97(2), 117-134.",
            "徐世勇, 朱金强, 王晓晨. (2009). 伦理型领导对员工组织公民行为的影响: 中介与调节效应分析. 心理科学, 32(2), 348-351.",
        ],
    },
    "领导-成员交换": {
        "name_zh": "领导-成员交换", "name_en": "Leader-Member Exchange", "domain": "组织行为",
        "definition": "领导-成员交换理论关注领导者与每个下属之间形成的一对一独特交换关系，区别于关注「领导风格」的传统视角（Graen & Uhl-Bien, 1995）。高质量 LMX 包含相互信任、尊重和义务感，关系质量直接影响下属的工作态度、绩效与离职意向，是华人 OB 研究的标配中介/控制变量。",
        "dimensions": [
            {"name": "情感", "desc": "双方情感连接与人际吸引", "item_count": 3, "example": "我的上级是我喜欢以朋友身份相处的人"},
            {"name": "贡献", "desc": "双方为彼此工作目标付出的努力", "item_count": 3, "example": "我愿意为我的上级超越职责范围工作"},
            {"name": "忠诚", "desc": "公开支持彼此的承诺", "item_count": 3, "example": "我的上级会在他人面前为我辩护"},
            {"name": "专业尊重", "desc": "对彼此专业能力的认可", "item_count": 3, "example": "我钦佩我上级的专业能力"},
        ],
        "typical_scale": "5点同意度量表 / 5点频率量表",
        "established_scales": [
            "LMX-7 (Graen & Uhl-Bien, 1995) — 7题单维评估，最常用",
            "LMX-MDM (Liden & Maslyn, 1998) — 12题四维度（情感/贡献/忠诚/专业尊重）",
        ],
        "references": [
            "Graen, G. B., & Uhl-Bien, M. (1995). Relationship-based approach to leadership: Development of leader-member exchange (LMX) theory of leadership over 25 years: Applying a multi-level multi-domain perspective. Leadership Quarterly, 6(2), 219-247.",
            "Liden, R. C., & Maslyn, J. M. (1998). Multidimensionality of leader-member exchange: An empirical assessment through scale development. Journal of Management, 24(1), 43-72.",
        ],
    },
    "工作旺盛感": {
        "name_zh": "工作旺盛感", "name_en": "Thriving at Work", "domain": "组织行为",
        "definition": "工作旺盛感是员工在工作中同时体验到学习（认知层面，习得新知识与技能）和活力（情感层面，感到精力充沛）的心理状态（Spreitzer et al., 2005; Porath et al., 2012）。它是员工持续主动成长的指标，区别于敬业度的「投入」焦点，更强调「前进感」，是积极组织行为学的新热点。",
        "dimensions": [
            {"name": "学习", "desc": "在工作中获得新知识、新技能的体验", "item_count": 5, "example": "我经常在工作中发现自己在学习新东西"},
            {"name": "活力", "desc": "在工作中感到精力充沛、富有生命力", "item_count": 5, "example": "我在工作中感到自己充满活力"},
        ],
        "typical_scale": "7点同意度量表",
        "established_scales": [
            "工作旺盛感量表 (Porath, Spreitzer, Gibson & Garnett, 2012) — 10题双维度",
            "中文修订 (Liu, Wang & Zhang, 2015) — 中国情境效度验证",
        ],
        "references": [
            "Spreitzer, G., Sutcliffe, K., Dutton, J., Sonenshein, S., & Grant, A. M. (2005). A socially embedded model of thriving at work. Organization Science, 16(5), 537-549.",
            "Porath, C., Spreitzer, G., Gibson, C., & Garnett, F. G. (2012). Thriving at work: Toward its measurement, construct validation, and theoretical refinement. Journal of Organizational Behavior, 33(2), 250-275.",
        ],
    },

    # ═══════════════════════════════════════════════════════
    # 发展心理学 (7个)
    # ═══════════════════════════════════════════════════════
    "心理韧性": {
        "name_zh": "心理韧性", "name_en": "Resilience", "domain": "发展心理学",
        "definition": "心理韧性是指个体在面对逆境、创伤、威胁或重大压力时的适应能力和积极应对过程（Luthar et al., 2000）。它不是一种固定的人格特质，而是包括个人能力、社会支持和外部资源交互作用的动态适应过程。",
        "dimensions": [
            {"name": "个人能力", "desc": "自信、坚持和自我效能等内在资源", "item_count": 8, "example": "我能够适应变化"},
            {"name": "社会支持", "desc": "来自家人、朋友和社会网络的外部资源", "item_count": 6, "example": "我有可以信赖的人在我需要时帮助我"},
            {"name": "积极接纳", "desc": "对逆境的接纳态度和积极的重新解释", "item_count": 5, "example": "即使处于困境，我也能看到积极的一面"},
        ],
        "typical_scale": "5点同意度量表",
        "established_scales": [
            "Connor-Davidson韧性量表 (CD-RISC; Connor & Davidson, 2003) — 25题",
            "青少年韧性量表 (胡月琴, 甘怡群, 2008) — 27题",
        ],
        "references": [
            "Connor, K. M., & Davidson, J. R. T. (2003). Development of a new resilience scale. Depression and Anxiety, 18(2), 76-82.",
            "胡月琴, 甘怡群. (2008). 青少年心理韧性量表的编制和效度验证. 心理学报, 40(8), 902-912.",
        ],
    },
    "情绪智力": {
        "name_zh": "情绪智力", "name_en": "Emotional Intelligence", "domain": "发展心理学",
        "definition": "情绪智力（EI）是个体识别、理解、管理和利用自己及他人情绪的能力（Mayer & Salovey, 1997）。涉及情绪感知、情绪促进思维、情绪理解和情绪管理四个分支。",
        "dimensions": [
            {"name": "情绪感知", "desc": "准确识别和表达自己及他人的情绪", "item_count": 4, "example": "我能轻易看出来别人是高兴、生气还是难过"},
            {"name": "情绪利用", "desc": "利用情绪促进思维和问题解决", "item_count": 4, "example": "情绪好时我能产生更多新颖的想法"},
            {"name": "情绪理解", "desc": "理解情绪的复杂关系和变化", "item_count": 4, "example": "我理解他人的感受从何而来"},
            {"name": "情绪管理", "desc": "管理和调节自己及他人的情绪", "item_count": 4, "example": "我能很好地控制自己的情绪"},
        ],
        "typical_scale": "5点同意度量表",
        "established_scales": [
            "Wong-Law情绪智力量表 (WLEIS; Wong & Law, 2002) — 16题",
            "特质情绪智力问卷 (TEIQue; Petrides & Furnham, 2006)",
        ],
        "references": [
            "Mayer, J. D., & Salovey, P. (1997). What is emotional intelligence? In P. Salovey & D. Sluyter (Eds.), Emotional development and emotional intelligence. Basic Books.",
        ],
    },
    "依恋风格": {
        "name_zh": "依恋风格", "name_en": "Attachment Style", "domain": "发展心理学",
        "definition": "依恋风格是指个体在亲密关系中形成的情感联结模式，源于早期与主要照料者的互动经验，影响成人后的人际关系。Bartholomew和Horowitz(1991)基于焦虑和回避两维度提出四类依恋：安全型、焦虑型、回避型和恐惧型。",
        "dimensions": [
            {"name": "依恋焦虑", "desc": "担心被拒绝和抛弃的程度", "item_count": 6, "example": "我担心伴侣不像我关心他/她那样关心我"},
            {"name": "依恋回避", "desc": "对亲密关系和依赖的不适感", "item_count": 6, "example": "我不喜欢和伴侣太过亲密"},
        ],
        "typical_scale": "7点同意度量表",
        "established_scales": [
            "亲密关系体验量表 (ECR; Brennan et al., 1998) — 36题",
            "ECR修订版 (ECR-R; Fraley et al., 2000)",
        ],
        "references": [
            "Brennan, K. A., Clark, C. L., & Shaver, P. R. (1998). Self-report measurement of adult attachment. In J. A. Simpson & W. S. Rholes (Eds.), Attachment theory and close relationships. Guilford Press.",
        ],
    },
    "自我同一性": {
        "name_zh": "自我同一性", "name_en": "Ego Identity", "domain": "发展心理学",
        "definition": "自我同一性是Erikson发展理论的核心概念，指个体对自我的连续性、一致性和独特性的主观体验。Marcia(1966)根据探索和承诺两个维度提出四种同一性状态：达成、延缓、早闭和扩散。",
        "dimensions": [
            {"name": "探索", "desc": "对人生目标、价值观和角色的积极探索", "item_count": 6, "example": "我正在尝试确定自己的生活方式"},
            {"name": "承诺", "desc": "对特定目标、信念和方向的坚定投入", "item_count": 6, "example": "我已经清楚地知道自己想要什么"},
        ],
        "typical_scale": "6点同意度量表",
        "established_scales": [
            "自我同一性状态量表 (EOM-EIS-II; Bennion & Adams, 1986)",
        ],
        "references": [
            "Marcia, J. E. (1966). Development and validation of ego-identity status. Journal of Personality and Social Psychology, 3(5), 551-558.",
        ],
    },
    "亲社会行为": {
        "name_zh": "亲社会行为", "name_en": "Prosocial Behavior", "domain": "发展心理学",
        "definition": "亲社会行为是指个体自愿采取的有益于他人或社会的行为，包括帮助、分享、捐赠、安慰和合作等。这些行为可能出于利他动机或互惠期望（Eisenberg et al., 2006）。",
        "dimensions": [
            {"name": "利他行为", "desc": "不期望回报的帮助行为", "item_count": 5, "example": "我会帮助陌生人捡起掉落的物品"},
            {"name": "合作行为", "desc": "与他人协作完成共同目标", "item_count": 4, "example": "在小组中我乐于与他人合作"},
            {"name": "情感方面", "desc": "对他人困境的关心和同情", "item_count": 4, "example": "看到别人难过时我也会感到难过"},
        ],
        "typical_scale": "5点频率量表",
        "established_scales": [
            "亲社会倾向量表 (PTM; Carlo & Randall, 2002) — 25题",
        ],
        "references": [
            "Eisenberg, N., Fabes, R. A., & Spinrad, T. L. (2006). Prosocial development. In N. Eisenberg (Ed.), Handbook of child psychology (6th ed.). Wiley.",
        ],
    },
    "学业自我效能感": {
        "name_zh": "学业自我效能感", "name_en": "Academic Self-Efficacy", "domain": "发展心理学",
        "definition": "学业自我效能感是学生对自身完成学业任务、达成学习目标的能力的信念和判断（Bandura, 1997; Schunk, 1991）。它是影响学习投入、学业坚持和学业成就的核心动机变量。",
        "dimensions": [
            {"name": "学习能力感", "desc": "对自己学习能力的信心", "item_count": 6, "example": "我确信自己能理解课堂上最难的内容"},
            {"name": "学习行为感", "desc": "对自己能有效执行学习策略的信心", "item_count": 6, "example": "我能合理安排学习时间来完成作业"},
        ],
        "typical_scale": "5点同意度量表",
        "established_scales": [
            "学业自我效能感量表 (Pintrich & De Groot, 1990)",
            "梁宇颂修订中文版 (2000)",
        ],
        "references": [
            "Bandura, A. (1997). Self-efficacy: The exercise of control. W. H. Freeman.",
        ],
    },
    "拖延": {
        "name_zh": "拖延", "name_en": "Procrastination", "domain": "发展心理学",
        "definition": "拖延是指尽管预见到延迟会导致不利后果，但仍自愿推迟计划好的任务执行的行为倾向（Steel, 2007）。研究发现拖延与自我调节失败、任务厌恶、冲动性和时间管理能力差有密切关联。",
        "dimensions": [
            {"name": "任务拖延", "desc": "推迟任务开始和完成的倾向", "item_count": 5, "example": "我总是等到最后一刻才开始做作业"},
            {"name": "决策拖延", "desc": "推迟做出决定的倾向", "item_count": 4, "example": "面对多个选择时我总是迟迟下不了决定"},
            {"name": "时间管理不良", "desc": "对时间的组织和利用不足", "item_count": 4, "example": "我经常低估完成任务所需的时间"},
        ],
        "typical_scale": "5点频率量表",
        "established_scales": [
            "一般拖延量表 (GPS; Lay, 1986) — 20题",
            "拖延评估量表学生版 (PASS; Solomon & Rothblum, 1984)",
        ],
        "references": [
            "Steel, P. (2007). The nature of procrastination: A meta-analytic and theoretical review. Psychological Bulletin, 133(1), 65-94.",
        ],
    },
    "学业倦怠": {
        "name_zh": "学业倦怠", "name_en": "Academic Burnout", "domain": "发展心理学",
        "definition": "学业倦怠是指学生在学习过程中因长期承受学业压力而产生的一种以情绪耗竭、去人格化和成就感降低为特征的心理状态（Schaufeli et al., 2002）。反映了学生面对学业需求时心理资源的耗损。",
        "dimensions": [
            {"name": "情绪耗竭", "desc": "因学业要求而感到心力交瘁", "item_count": 5, "example": "早上起来想到要面对一天的学习就感到很累"},
            {"name": "玩世不恭", "desc": "对学业的疏离和消极态度", "item_count": 5, "example": "我对学习的热情已经减退了"},
            {"name": "成就感降低", "desc": "对学业成就的负面评价", "item_count": 5, "example": "我在学习中取得了不少成就（反向题）"},
        ],
        "typical_scale": "5点频率量表",
        "established_scales": [
            "学业倦怠量表 (MBI-SS; Schaufeli et al., 2002) — 15题",
        ],
        "references": [
            "Schaufeli, W. B., Martínez, I. M., Pinto, A. M., Salanova, M., & Bakker, A. B. (2002). Burnout and engagement in university students. Journal of Cross-Cultural Psychology, 33(5), 464-481.",
        ],
    },

    # ═══════════════════════════════════════════════════════
    # 认知心理学 (5个)
    # ═══════════════════════════════════════════════════════
    "工作记忆": {
        "name_zh": "工作记忆", "name_en": "Working Memory", "domain": "认知心理学",
        "definition": "工作记忆是Baddeley和Hitch(1974)提出的一种容量有限的认知系统，负责信息的暂时存储和同时加工。包含语音回路、视觉空间画板、中央执行系统和情境缓冲器四个子系统。",
        "dimensions": [
            {"name": "语音回路", "desc": "暂时存储和复述言语信息", "item_count": 4, "example": "我能记住刚听到的电话号码"},
            {"name": "视觉空间画板", "desc": "暂时存储和操作视觉空间信息", "item_count": 4, "example": "我能想象物体旋转后的样子"},
            {"name": "中央执行", "desc": "分配注意资源、协调子系统、抑制无关信息", "item_count": 4, "example": "在做复杂任务时我能排除干扰"},
        ],
        "typical_scale": "行为任务（如N-back、数字广度、Corsi block）",
        "established_scales": [
            "工作记忆问卷 (WMQ; Vallat-Azouvi et al., 2012)",
        ],
        "references": [
            "Baddeley, A. D., & Hitch, G. (1974). Working memory. In G. H. Bower (Ed.), The psychology of learning and motivation (Vol. 8). Academic Press.",
        ],
    },
    "认知灵活性": {
        "name_zh": "认知灵活性", "name_en": "Cognitive Flexibility", "domain": "认知心理学",
        "definition": "认知灵活性是个体根据环境变化灵活调整认知策略、转换思维定势、从多角度思考问题的能力（Martin & Rubin, 1995）。它是执行功能的核心成分，与创造力、问题解决和适应能力密切相关。",
        "dimensions": [
            {"name": "策略转换", "desc": "在任务或规则变化时调整认知策略", "item_count": 5, "example": "一个方法行不通时我能很快想到其他方法"},
            {"name": "多元思维", "desc": "同时考虑多种视角和可能性", "item_count": 5, "example": "面对问题我总能从多个角度分析"},
            {"name": "适应意愿", "desc": "愿意接受新情况和变化", "item_count": 4, "example": "我乐于接受改变和新的挑战"},
        ],
        "typical_scale": "6点同意度量表",
        "established_scales": [
            "认知灵活性量表 (CFS; Martin & Rubin, 1995) — 12题",
        ],
        "references": [
            "Martin, M. M., & Rubin, R. B. (1995). A new measure of cognitive flexibility. Psychological Reports, 76(2), 623-626.",
        ],
    },
    "执行功能": {
        "name_zh": "执行功能", "name_en": "Executive Function", "domain": "认知心理学",
        "definition": "执行功能是一组负责目标导向行为的高级认知过程，主要包括抑制控制（inhibitory control）、工作记忆更新（updating）和认知灵活性（shifting）三个核心成分（Miyake et al., 2000）。",
        "dimensions": [
            {"name": "抑制控制", "desc": "抑制优势反应或无关干扰的能力", "item_count": 5, "example": "我需要专心时能屏蔽周围噪音的影响"},
            {"name": "任务切换", "desc": "在不同任务或心理定势间灵活转换", "item_count": 4, "example": "被打断后我能快速回到原来的工作上"},
            {"name": "计划与组织", "desc": "设定目标、规划步骤并按优先级执行", "item_count": 5, "example": "面对复杂任务我能制定清晰的行动计划"},
        ],
        "typical_scale": "行为任务（Stroop、Wisconsin卡片分类、Tower of London等）",
        "established_scales": [
            "执行功能行为评定量表 (BRIEF; Gioia et al., 2000)",
        ],
        "references": [
            "Miyake, A., Friedman, N. P., Emerson, M. J., Witzki, A. H., Howerter, A., & Wager, T. D. (2000). The unity and diversity of executive functions. Cognitive Psychology, 41(1), 49-100.",
        ],
    },
    "注意控制": {
        "name_zh": "注意控制", "name_en": "Attentional Control", "domain": "认知心理学",
        "definition": "注意控制是指个体调节注意力分配、集中和转移的能力，包括注意集中、注意转移和注意分散控制三个方面（Derryberry & Reed, 2002）。它在情绪调节和认知表现中起着关键作用。",
        "dimensions": [
            {"name": "注意集中", "desc": "将注意力维持在目标任务上的能力", "item_count": 5, "example": "即使在嘈杂环境中我也能专注于当前任务"},
            {"name": "注意转移", "desc": "在任务或刺激之间灵活转换注意的能力", "item_count": 5, "example": "我能很快从一项任务切换到另一项任务"},
        ],
        "typical_scale": "4点频率量表",
        "established_scales": [
            "注意控制量表 (ACS; Derryberry & Reed, 2002) — 20题",
        ],
        "references": [
            "Derryberry, D., & Reed, M. A. (2002). Anxiety-related attentional biases and their regulation by attentional control. Journal of Abnormal Psychology, 111(2), 225-236.",
        ],
    },
    "冲动性": {
        "name_zh": "冲动性", "name_en": "Impulsivity", "domain": "认知心理学",
        "definition": "冲动性是一种未经充分思考即做出快速、非计划性反应的人格特质，涉及行为抑制困难、延迟满足能力和认知冲动（缺乏计划）三个维度（Barratt, 1985; Patton et al., 1995）。",
        "dimensions": [
            {"name": "注意冲动", "desc": "注意力不集中、思维跳跃快", "item_count": 5, "example": "我的注意力常常从一个想法跳到另一个想法"},
            {"name": "动作冲动", "desc": "不经思考的快速行动", "item_count": 5, "example": "我做事常常不经过深思熟虑"},
            {"name": "非计划性", "desc": "缺乏对未来的规划", "item_count": 5, "example": "我更多是活在当下，不太考虑未来"},
        ],
        "typical_scale": "4点频率量表",
        "established_scales": [
            "Barratt冲动性量表 (BIS-11; Patton et al., 1995) — 30题",
        ],
        "references": [
            "Patton, J. H., Stanford, M. S., & Barratt, E. S. (1995). Factor structure of the Barratt impulsiveness scale. Journal of Clinical Psychology, 51(6), 768-774.",
        ],
    },

    # ═══════════════════════════════════════════════════════
    # 社会心理学 (7个)
    # ═══════════════════════════════════════════════════════
    "归属感": {
        "name_zh": "归属感", "name_en": "Sense of Belonging", "domain": "社会心理学",
        "definition": "归属感是个体感受到自己被重要他人、群体或社区接纳、重视和需要的心理体验（Baumeister & Leary, 1995）。归属需要被认为是人类的基本心理需要，对心理健康和幸福感具有深远影响。",
        "dimensions": [
            {"name": "接纳感", "desc": "感受到被他人接纳和欢迎", "item_count": 5, "example": "我觉得自己在群体中是受欢迎的"},
            {"name": "参与感", "desc": "感到自己是群体中有价值的一员", "item_count": 5, "example": "我能在群体中做出有意义的贡献"},
            {"name": "联结感", "desc": "与他人的情感联结和共鸣", "item_count": 4, "example": "我和周围的人有密切的联系"},
        ],
        "typical_scale": "5点同意度量表",
        "established_scales": [
            "归属感量表 (SOBI; Hagerty & Patusky, 1995)",
        ],
        "references": [
            "Baumeister, R. F., & Leary, M. R. (1995). The need to belong. Psychological Bulletin, 117(3), 497-529.",
        ],
    },
    "社会称许性": {
        "name_zh": "社会称许性", "name_en": "Social Desirability", "domain": "社会心理学",
        "definition": "社会称许性是指个体在回答问卷或进行自我报告时，倾向于按照社会期望而非真实情况来呈现自己的反应偏差（Paulhus, 1991）。包含自我欺骗增强（无意识的积极自我呈现）和印象管理（有意识的他人导向呈现）两个维度。",
        "dimensions": [
            {"name": "自我欺骗", "desc": "无意识的、诚实的但过度积极的自我描述", "item_count": 5, "example": "我从来不后悔自己的决定"},
            {"name": "印象管理", "desc": "有意识地迎合社会期望的形象呈现", "item_count": 5, "example": "我从来不撒谎（即使善意的谎言也没有）"},
        ],
        "typical_scale": "7点同意度量表",
        "established_scales": [
            "Marlowe-Crowne社会称许量表 (MCSDS; Crowne & Marlowe, 1960) — 33题",
            "平衡的社会称许反应量表 (BIDR; Paulhus, 1991) — 40题",
        ],
        "references": [
            "Paulhus, D. L. (1991). Measurement and control of response bias. In J. P. Robinson et al. (Eds.), Measures of personality and social psychological attitudes. Academic Press.",
        ],
    },
    "感恩": {
        "name_zh": "感恩", "name_en": "Gratitude", "domain": "社会心理学",
        "definition": "感恩是个体在认识到他人给予恩惠或积极体验源自外部因素时产生的一种积极情绪和态度（McCullough et al., 2002）。感恩包含情感倾向、行为表达和认知评价三个层面。",
        "dimensions": [
            {"name": "感恩情感", "desc": "体验到的感恩情绪频率和强度", "item_count": 3, "example": "生活中有很多值得感恩的事情"},
            {"name": "感恩表达", "desc": "向他人表达感谢的行为倾向", "item_count": 3, "example": "我经常向帮助过我的人表达感谢"},
        ],
        "typical_scale": "7点同意度量表",
        "established_scales": [
            "感恩问卷 (GQ-6; McCullough et al., 2002) — 6题",
        ],
        "references": [
            "McCullough, M. E., Emmons, R. A., & Tsang, J. A. (2002). The grateful disposition. Journal of Personality and Social Psychology, 82(1), 112-127.",
        ],
    },
    "共情": {
        "name_zh": "共情", "name_en": "Empathy", "domain": "社会心理学",
        "definition": "共情是指个体理解和分享他人情感体验的能力，包含认知共情（理解他人观点和情绪状态）和情感共情（对他人情绪状态产生相应的情绪反应）两个维度（Davis, 1983）。",
        "dimensions": [
            {"name": "认知共情", "desc": "理解他人的观点和感受", "item_count": 5, "example": "我试着从每个人的角度看问题"},
            {"name": "情感共情", "desc": "与他人情绪产生共鸣和共同感受", "item_count": 4, "example": "看到别人哭我也会想哭"},
            {"name": "共情关怀", "desc": "对他人遭遇困境的关心和同情", "item_count": 4, "example": "看到别人受到不公正对待我会很气愤"},
        ],
        "typical_scale": "5点同意度量表",
        "established_scales": [
            "人际反应指针 (IRI; Davis, 1983) — 28题",
            "IRI中文修订版 (张凤凤等, 2010)",
        ],
        "references": [
            "Davis, M. H. (1983). Measuring individual differences in empathy. Journal of Personality and Social Psychology, 44(1), 113-126.",
        ],
    },
    "社交焦虑": {
        "name_zh": "社交焦虑", "name_en": "Social Anxiety", "domain": "社会心理学",
        "definition": "社交焦虑是指个体在社交或表演情境中因担心被他人评价或拒绝而产生的显著紧张、不安和回避行为（Leary, 1983）。从正常的社交害羞到社交焦虑障碍构成一个连续谱。",
        "dimensions": [
            {"name": "社交恐惧", "desc": "在社交情境中的恐惧和紧张", "item_count": 6, "example": "在聚会中与陌生人交谈让我焦虑"},
            {"name": "社交回避", "desc": "回避或逃避社交情境的行为倾向", "item_count": 5, "example": "我会找借口避开社交活动"},
            {"name": "评价恐惧", "desc": "对被他人负面评价的过度担忧", "item_count": 5, "example": "我担心别人会认为我的言行很愚蠢"},
        ],
        "typical_scale": "5点频率量表",
        "established_scales": [
            "社交回避与苦恼量表 (SAD; Watson & Friend, 1969) — 28题",
            "Liebowitz社交焦虑量表 (LSAS; Liebowitz, 1987)",
        ],
        "references": [
            "Leary, M. R. (1983). Understanding social anxiety. SAGE Publications.",
        ],
    },
    "完美主义": {
        "name_zh": "完美主义", "name_en": "Perfectionism", "domain": "社会心理学",
        "definition": "完美主义是设定极端高标准并伴随过度自我批判的人格特质（Frost et al., 1990）。多维完美主义包含个人标准、担心错误、父母期望、怀疑行动和组织性等多个侧面。",
        "dimensions": [
            {"name": "个人标准", "desc": "为自己设定极高的表现标准", "item_count": 5, "example": "我给自己设定的目标比大多数人都高"},
            {"name": "担心错误", "desc": "对犯错误的过度担忧和负面反应", "item_count": 5, "example": "犯一点小错就会让我耿耿于怀"},
            {"name": "怀疑行动", "desc": "对自己完成任务质量的不确定感", "item_count": 4, "example": "完成任务后我总觉得还不够完美"},
        ],
        "typical_scale": "5点同意度量表",
        "established_scales": [
            "Frost多维完美主义量表 (FMPS; Frost et al., 1990) — 35题",
        ],
        "references": [
            "Frost, R. O., Marten, P., Lahart, C., & Rosenblate, R. (1990). The dimensions of perfectionism. Cognitive Therapy and Research, 14(5), 449-468.",
        ],
    },
    "自我控制": {
        "name_zh": "自我控制", "name_en": "Self-Control", "domain": "社会心理学",
        "definition": "自我控制是个体有意识地监控、调整和抑制冲动行为、情绪和欲望以达到长期目标的能力（Baumeister et al., 2007）。自我控制被视为一种有限的资源，会因使用而暂时损耗。",
        "dimensions": [
            {"name": "冲动抑制", "desc": "抵制即时满足和冲动行为", "item_count": 5, "example": "看到想吃的东西我能控制住自己不吃太多"},
            {"name": "情绪调节", "desc": "管理情绪反应的强度和表达", "item_count": 4, "example": "生气时我也能控制住自己不对别人发火"},
            {"name": "习惯打破", "desc": "克服坏习惯和建立新行为模式", "item_count": 4, "example": "我能够改掉不好的习惯"},
        ],
        "typical_scale": "5点频率量表",
        "established_scales": [
            "自我控制量表 (SCS; Tangney et al., 2004) — 36题和13题简版",
        ],
        "references": [
            "Tangney, J. P., Baumeister, R. F., & Boone, A. L. (2004). High self-control predicts good adjustment. Journal of Personality, 72(2), 271-324.",
        ],
    },

    # ═══════════════════════════════════════════════════════
    # 临床与健康 / 积极心理学 (5个)
    # ═══════════════════════════════════════════════════════
    "正念": {
        "name_zh": "正念", "name_en": "Mindfulness", "domain": "临床与健康",
        "definition": "正念是有目的地、非评判地将注意力集中在当下时刻的意识状态（Kabat-Zinn, 2003）。包含观察、描述、有觉知地行动、非评判的内在体验和对内在体验的非反应性五个方面（Baer et al., 2006）。",
        "dimensions": [
            {"name": "观察", "desc": "注意和觉察内外在刺激", "item_count": 5, "example": "我注意到周围环境中的细节"},
            {"name": "描述", "desc": "用语言标识内在体验", "item_count": 5, "example": "我能找到词描述我的感受"},
            {"name": "非评判", "desc": "对内在体验采取非评价的态度", "item_count": 5, "example": "我会评判自己的情绪是好是坏（反向题）"},
            {"name": "非反应", "desc": "让情绪和想法来来去去而不陷入其中", "item_count": 5, "example": "当我感到难受时，我不会被情绪淹没"},
        ],
        "typical_scale": "5点频率量表",
        "established_scales": [
            "五因素正念量表 (FFMQ; Baer et al., 2006) — 39题",
            "正念注意觉知量表 (MAAS; Brown & Ryan, 2003) — 15题",
        ],
        "references": [
            "Kabat-Zinn, J. (2003). Mindfulness-based interventions in context. Clinical Psychology: Science and Practice, 10(2), 144-156.",
        ],
    },
    "生命意义感": {
        "name_zh": "生命意义感", "name_en": "Meaning in Life", "domain": "临床与健康",
        "definition": "生命意义感是个体对自己生命的存在、目的和重要性的理解和体验（Steger et al., 2006）。包含意义存在（对生命意义的认知评价）和意义寻求（积极寻找意义的动机）两个维度。",
        "dimensions": [
            {"name": "意义存在", "desc": "感受到生命有意义和目的", "item_count": 5, "example": "我明白自己人生的意义"},
            {"name": "意义寻求", "desc": "主动追寻和探索生命意义的动机", "item_count": 5, "example": "我正在寻找让自己的人生有意义的东西"},
        ],
        "typical_scale": "7点同意度量表",
        "established_scales": [
            "生命意义问卷 (MLQ; Steger et al., 2006) — 10题",
        ],
        "references": [
            "Steger, M. F., Frazier, P., Oishi, S., & Kaler, M. (2006). The meaning in life questionnaire. Journal of Counseling Psychology, 53(1), 80-93.",
        ],
    },
    "心理幸福感": {
        "name_zh": "心理幸福感", "name_en": "Psychological Well-Being", "domain": "临床与健康",
        "definition": "心理幸福感是Ryff(1989)提出的基于实现论（eudaimonic）的幸福感模型，强调自我实现和心理潜能的充分发挥，包含自主性、环境掌控、个人成长、积极的人际关系、生活目标和自我接纳六个维度。",
        "dimensions": [
            {"name": "自我接纳", "desc": "对自我积极肯定的态度", "item_count": 5, "example": "我喜欢自己的大部分个性"},
            {"name": "个人成长", "desc": "持续发展和实现潜能的感觉", "item_count": 5, "example": "我感到自己多年来成长了很多"},
            {"name": "生活目标", "desc": "对生活有方向和意义的信念", "item_count": 5, "example": "我对未来有清晰的计划和目标"},
            {"name": "人际关系", "desc": "与他人温暖、信任的关系质量", "item_count": 5, "example": "我有温暖、值得信赖的人际关系"},
            {"name": "环境掌控", "desc": "有效管理周围环境和机会的能力", "item_count": 5, "example": "我能很好地处理日常生活中的各种事务"},
            {"name": "自主性", "desc": "按照自己的标准和信念生活", "item_count": 5, "example": "我有信心按照自己的信念生活，即使与大多数人不同"},
        ],
        "typical_scale": "6点同意度量表",
        "established_scales": [
            "心理幸福感量表 (PWBS; Ryff, 1989) — 84题和42题简版",
        ],
        "references": [
            "Ryff, C. D. (1989). Happiness is everything, or is it? Journal of Personality and Social Psychology, 57(6), 1069-1081.",
        ],
    },
    "核心自我评价": {
        "name_zh": "核心自我评价", "name_en": "Core Self-Evaluation", "domain": "临床与健康",
        "definition": "核心自我评价是个体对自身价值和能力的基本评价，由Judge等人(1997)提出，整合了自尊、一般自我效能感、控制点和神经质四个特质。高核心自我评价者倾向于以更积极的方式看待自己。",
        "dimensions": [
            {"name": "整体自我评价", "desc": "对自身价值和能力的整体正面评价", "item_count": 6, "example": "我相信我能处理好生活中的大多数挑战"},
            {"name": "控制感", "desc": "对自己能够掌控结果的信念", "item_count": 4, "example": "我的成功取决于自己的努力而非运气"},
            {"name": "情绪稳定性", "desc": "情绪的稳定性和抗压能力（反向）", "item_count": 4, "example": "我经常感到紧张不安（反向题）"},
        ],
        "typical_scale": "5点同意度量表",
        "established_scales": [
            "核心自我评价量表 (CSES; Judge et al., 2003) — 12题",
        ],
        "references": [
            "Judge, T. A., Erez, A., Bono, J. E., & Thoresen, C. J. (2003). The core self-evaluations scale. Personnel Psychology, 56(2), 303-331.",
        ],
    },
    "工作满意度": {
        "name_zh": "工作满意度", "name_en": "Job Satisfaction", "domain": "组织行为",
        "definition": "工作满意度是个体对其工作及工作经历的整体评价性反应（Locke, 1976），反映了员工对工作各方面（薪酬、晋升、上司、同事、工作本身）的情感态度。可分为整体工作满意度（overall job satisfaction）和分面工作满意度（facet job satisfaction）两类测量取向。",
        "dimensions": [
            {"name": "薪酬满意度", "desc": "对薪资水平、加薪频率与公平性的评价", "item_count": 4, "example": "我对自己的薪资水平感到满意"},
            {"name": "晋升满意度", "desc": "对晋升机会与发展前景的评价", "item_count": 4, "example": "组织提供了公平的晋升机会"},
            {"name": "上司满意度", "desc": "对直接上级管理风格与支持的评价", "item_count": 4, "example": "我的直接上司能力胜任管理工作"},
            {"name": "同事满意度", "desc": "对同事关系与合作氛围的评价", "item_count": 4, "example": "我喜欢和同事一起工作"},
            {"name": "工作本身", "desc": "对工作内容、自主性与挑战性的评价", "item_count": 4, "example": "我的工作让我有成就感"},
        ],
        "typical_scale": "5点同意度量表（1=非常不同意, 5=非常同意）",
        "established_scales": [
            "工作满意度量表 (JSS; Spector, 1985) — 36题，9个分面",
            "明尼苏达满意度问卷 (MSQ; Weiss et al., 1967) — 短版20题/长版100题",
            "工作描述指数 (JDI; Smith, Kendall & Hulin, 1969) — 5个分面72题",
        ],
        "references": [
            "Locke, E. A. (1976). The nature and causes of job satisfaction. In M. D. Dunnette (Ed.), Handbook of Industrial and Organizational Psychology (pp. 1297-1349). Rand McNally.",
            "Spector, P. E. (1985). Measurement of human service staff satisfaction: Development of the Job Satisfaction Survey. American Journal of Community Psychology, 13(6), 693-713.",
        ],
    },
    "离职意愿": {
        "name_zh": "离职意愿", "name_en": "Turnover Intention", "domain": "组织行为",
        "definition": "离职意愿是员工在心理上离开当前组织、寻找其他就业机会的主观倾向，是实际离职行为的最稳定且最强的预测变量（Mobley, 1977; Tett & Meyer, 1993）。包括思考离职（thinking of quitting）、寻找替代工作（intent to search）和离职意图（intent to quit）三个递进阶段。",
        "dimensions": [
            {"name": "思考离职", "desc": "对离开当前组织的认知思考频率", "item_count": 2, "example": "我经常想到要离开现在的工作"},
            {"name": "寻找替代", "desc": "主动寻找其他工作机会的行为意向", "item_count": 2, "example": "我会主动浏览其他公司的招聘信息"},
            {"name": "离职意图", "desc": "在可预见时间内离职的明确意图", "item_count": 2, "example": "未来一年内我可能会离开当前的组织"},
        ],
        "typical_scale": "5点同意度量表（1=非常不同意, 5=非常同意）",
        "established_scales": [
            "离职意愿量表 (TIS-6; Bothma & Roodt, 2013) — 6题",
            "Mobley离职意愿量表 (Mobley et al., 1978) — 3题",
            "组织承诺问卷-离职分量表 (Cammann et al., 1979) — 3题",
        ],
        "references": [
            "Mobley, W. H. (1977). Intermediate linkages in the relationship between job satisfaction and employee turnover. Journal of Applied Psychology, 62(2), 237-240.",
            "Tett, R. P., & Meyer, J. P. (1993). Job satisfaction, organizational commitment, turnover intention, and turnover: Path analyses based on meta-analytic findings. Personnel Psychology, 46(2), 259-293.",
            "Bothma, C. F. C., & Roodt, G. (2013). The validation of the turnover intention scale. SA Journal of Human Resource Management, 11(1), 1-12.",
        ],
    },
}

# 用于匹配的关键词索引
CONSTRUCT_KEYWORDS = {
    "焦虑": ["焦虑", "紧张", "担忧", "担心", "焦虑症", "社交焦虑", "考试焦虑"],
    "抑郁": ["抑郁", "沮丧", "消沉", "低落", "忧郁", "不开心"],
    "压力": ["压力", "应激", "紧张", "压感", "压力感"],
    "主观幸福感": ["幸福", "幸福感", "快乐", "满意", "生活满意度", "生活品质"],
    "自尊": ["自尊", "自我价值", "自信", "自信水平", "自尊心"],
    "自我效能感": ["自我效能", "效能感", "能力信念", "自我效能感"],
    "社会支持": ["社会支持", "人际支持", "支持系统", "支持利用"],
    "孤独感": ["孤独", "寂寞", "孤单"],
    "学习动机": ["学习动机", "学习动力", "学业动机", "学习积极性"],
    "考试焦虑": ["考试焦虑", "考试紧张", "考试压力", "测验焦虑"],
    "工作满意度": ["工作满意度", "工作满意", "工作满足", "工作满意感"],
    "职业倦怠": ["倦怠", "倦怠感", "工作倦怠", "职业倦怠", "耗竭"],
    # ── I/O 域 2026-05-30 加 ────────────────────────────────────────
    "员工敬业度": ["员工敬业度", "工作敬业度", "敬业度", "工作投入", "UWES", "work engagement", "employee engagement"],
    "家长式领导": ["家长式领导", "家长领导", "威权领导", "仁慈领导", "德行领导", "PLS", "paternalistic"],
    "伦理型领导": ["伦理型领导", "道德型领导", "伦理领导", "ELS", "ethical leadership"],
    "领导-成员交换": ["领导-成员交换", "领导成员交换", "上下级交换", "LMX", "LMX-7", "leader-member exchange"],
    "工作旺盛感": ["工作旺盛感", "工作活力", "thriving", "thriving at work"],
    "元认知": ["元认知", "认知策略", "学习策略", "自我监控", "反思"],
    # ── 新增构念 ────────────────────────────────────────
    "工作投入": ["工作投入", "投入度", "工作卷入", "敬业度", "工作参与"],
    "组织承诺": ["组织承诺", "组织忠诚", "组织认同", "归属感"],
    "心理资本": ["心理资本", "积极心理资本", "心理资源", "心理优势"],
    "变革型领导": ["变革型领导", "领导风格", "领导力", "变革领导", "领导行为"],
    "组织公民行为": ["组织公民行为", "公民行为", "角色外行为", "助人行为"],
    "工作-家庭冲突": ["工作家庭冲突", "角色冲突", "工作家庭平衡", "家庭工作冲突"],
    "工作倦怠": ["倦怠", "倦怠感", "工作倦怠", "职业倦怠", "耗竭"],
    "依恋风格": ["依恋", "依恋风格", "依恋类型", "成人依恋", "依恋模式"],
    "心理韧性": ["心理韧性", "韧性", "抗逆力", "复原力", "弹性", "心理弹性"],
    "情绪智力": ["情绪智力", "情商", "情绪能力", "情绪理解", "情绪管理"],
    "自我同一性": ["自我同一性", "同一性", "自我认同", "认同危机"],
    "亲社会行为": ["亲社会", "助人行为", "利他行为", "分享行为"],
    "学业自我效能感": ["学业自我效能", "学习自我效能", "学业自信", "学习信心"],
    "拖延": ["拖延", "拖延行为", "拖延症", "学业拖延", "延迟"],
    "工作记忆": ["工作记忆", "短时记忆", "记忆广度", "记忆容量"],
    "认知灵活性": ["认知灵活性", "认知弹性", "转换能力", "灵活思维"],
    "执行功能": ["执行功能", "执行控制", "抑制控制", "认知控制"],
    "注意控制": ["注意控制", "注意力控制", "注意调节", "专注力"],
    "归属感": ["归属感", "归属需要", "人际归属", "社会归属", "群体归属"],
    "社会称许性": ["社会称许性", "社会赞许", "赞许性", "印象管理"],
    "感恩": ["感恩", "感激", "感恩情绪", "感恩品质", "知恩图报"],
    "共情": ["共情", "同理心", "移情", "共感", "情绪理解"],
    "完美主义": ["完美主义", "追求完美", "高标准", "完美倾向"],
    "冲动性": ["冲动性", "冲动", "冲动行为", "冲动控制", "即时满足"],
    "自我控制": ["自我控制", "自控力", "自我调节", "自律", "意志力"],
    "正念": ["正念", "正念水平", "正念状态", "觉察", "不评判"],
    "生命意义感": ["生命意义", "人生意义", "生活意义", "意义感", "存在意义"],
    "心理幸福感": ["心理幸福感", "幸福感", "心理福祉", "心理繁荣"],
    "社交焦虑": ["社交焦虑", "社交恐惧", "社交回避", "社交不安"],
    "学业倦怠": ["学业倦怠", "学习倦怠", "学业耗竭", "厌学"],
    "成就动机": ["成就动机", "成就需要", "成就目标", "追求成功"],
    "核心自我评价": ["核心自我评价", "自我评价", "核心评价", "自我认知"],
    "工作满意度": ["工作满意度", "工作满意", "职业满意度", "JSS", "薪酬满意", "晋升满意"],
    "离职意愿": ["离职意愿", "离职倾向", "辞职意愿", "辞职倾向", "TIS", "turnover intention"],
}

# 领域关键词（用于模糊匹配时判断领域）
DOMAIN_KEYWORDS = {
    "临床与健康": [
        "焦虑", "抑郁", "症状", "心理健康", "疾病", "治疗", "干预",
        "正念", "生命意义", "意义感", "幸福感", "心理幸福", "核心自我评价",
    ],
    "人格": ["人格", "性格", "特质", "个性", "自我", "自尊"],
    "社会心理": [
        "社会", "人际", "关系", "群体", "态度", "偏见",
        "归属", "归属感", "称许", "社会称许", "感恩", "共情", "移情",
        "社交焦虑", "社交", "完美主义", "自我控制", "自控",
    ],
    "教育心理": [
        "学习", "学业", "教育", "考试", "学校", "成绩",
        "学业倦怠", "学习倦怠",
    ],
    "认知": [
        "认知", "注意", "记忆", "思维", "策略", "决策",
        "工作记忆", "认知灵活", "灵活性", "执行功能", "注意控制", "冲动",
    ],
    "组织行为": [
        "工作", "职业", "组织", "员工", "企业", "团队",
        "工作投入", "投入", "倦怠", "工作倦怠", "组织承诺", "承诺",
        "心理资本", "变革型领导", "领导", "工作-家庭冲突", "家庭冲突",
        "组织公民行为", "公民行为", "成就动机", "成就",
        "工作满意度", "满意度", "离职意愿", "离职", "辞职",
        "敬业度", "员工敬业度", "UWES",
        "家长式领导", "威权领导", "仁慈领导", "德行领导", "PLS",
        "伦理型领导", "道德型领导", "ELS",
        "领导-成员交换", "上下级交换", "LMX",
        "工作旺盛感", "工作活力", "thriving",
    ],
    "发展": [
        "儿童", "青少年", "发展", "阶段", "年龄", "老年",
        "心理韧性", "韧性", "情绪智力", "情商", "依恋",
        "同一性", "自我同一性", "亲社会", "拖延",
    ],
}
