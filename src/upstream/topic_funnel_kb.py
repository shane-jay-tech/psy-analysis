"""选题漏斗知识库：Fallback 模板 + Few-shot 范例 + 好/差选题对比 + 语义匹配。

- FALLBACK_QUESTIONS  — LLM 不可用/3 次失败时降级使用的反问模板
- GOOD_BAD_EXAMPLES   — 心理学 6 大领域好/差选题对比（v3.3 扩到 18 条）
- FUNNEL_FEW_SHOT     — 苏格拉底反问的 few-shot 范例（嵌入 system prompt）
- match_examples_by_semantics — v3.3 语义检索（接 IntentRecognitionChain）
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Fallback：LLM 失败时按阶段降级到模板问题（每阶段 ≥5 条，避免重复）
# ---------------------------------------------------------------------------

FALLBACK_QUESTIONS: Dict[int, List[str]] = {
    1: [
        "这个现象在哪些人身上更明显？",
        "你是在自己身上观察到的，还是在别人身上看到的？",
        "为什么这件事让你感到困惑或不爽？",
        "如果有一天它消失了，你会觉得失去了什么？",
        "你对这个现象的第一感受是什么——好奇？担心？还是别的？",
    ],
    2: [
        "「{topic}」具体指什么——一个行为？一种感受？还是一类人？",
        "你最想搞清楚的是「为什么会这样」还是「在什么条件下会这样」？",
        "你能描述一个最典型的场景吗？什么人，在做什么，结果怎样？",
        "如果让你只挑一个最关键的差异来研究，你会挑什么？",
        "和它最像但你不想研究的是什么？为什么不想？",
    ],
    3: [
        "你说的「{topic}」哪个方面是要测量的——它本身？还是它的某个后果？",
        "在你的现象里，什么先发生，什么后发生？",
        "如果用一句话写「X 越多，Y 就越___」，X 和 Y 各是什么？",
        "可能影响这个关系的「第三方」会是什么——年龄？性别？还是别的？",
        "这两个变量之间，你预期的是相关，还是因果？",
    ],
    4: [
        "如果你的假设错了，你会观察到什么样的数据？",
        "什么样的结果会让你说「我的研究问题不成立」？",
        "你打算用什么量表或工具测量「{topic}」？这个工具靠谱吗？",
        "本科一年时间，最难的部分会是哪一步？",
        "你的研究和已经发表的研究比，多出了什么新东西？",
    ],
    5: [
        "把它写成「在[人群]中，[X] 是否影响 [Y]？」——你会怎么填？",
        "如果只能保留一个核心问题，你选哪个？",
        "这个最终问题里，哪个词如果换掉就完全不是你想要的研究了？",
        "你担心的最大风险是什么——找不到被试？数据不显著？",
        "想象答辩老师问「你为什么研究这个」，你的一句话回答是？",
    ],
}


def get_fallback_question(stage: int, topic: str = "") -> str:
    """返回该阶段的 fallback 反问；若有 topic 则做模板替换。"""
    pool = FALLBACK_QUESTIONS.get(stage) or FALLBACK_QUESTIONS[1]
    raw = pool[0]
    if topic and "{topic}" in raw:
        return raw.replace("{topic}", topic)
    for q in pool:
        if "{topic}" not in q:
            return q
    return raw.replace("{topic}", topic or "这个现象")


# ---------------------------------------------------------------------------
# Few-shot：苏格拉底反问的范例（嵌入 system prompt 用）
# ---------------------------------------------------------------------------

FUNNEL_FEW_SHOT: List[Dict[str, str]] = [
    {
        "stage": "1",
        "student": "我想研究抑郁。",
        "good_response": "是哪种人的抑郁让你最在意——大学生？老人？还是产后？",
    },
    {
        "stage": "2",
        "student": "我想研究大学生学习压力。",
        "good_response": "「学习压力」具体是哪一类——考试前的紧张？还是日常感到学不完？",
    },
    {
        "stage": "3",
        "student": "我想研究睡眠和成绩的关系。",
        "good_response": "你关心的是「睡多久」还是「睡得好不好」？这两件事在数据上不一样。",
    },
    {
        "stage": "4",
        "student": "我假设刷手机时间越长焦虑越高。",
        "good_response": "如果你的假设错了，数据会长什么样？是没相关，还是反向？",
    },
    {
        "stage": "5",
        "student": "我想研究运动对心理健康的影响。",
        "good_response": "「心理健康」太宽——你最想看到运动改善哪一个？焦虑？睡眠？还是孤独感？",
    },
]


# ---------------------------------------------------------------------------
# 好/差选题对比（v3.3: 6 大领域 × 3 例 = 18 条；本科生可执行）
# ---------------------------------------------------------------------------

GOOD_BAD_EXAMPLES: Dict[str, List[Dict]] = {
    # ===== 社会心理学 =====
    "social": [
        {
            "vague": "我想研究社交焦虑",
            "bad_q": "社交焦虑和什么有关？",
            "good_q": "在大学新生中，每日社交媒体使用时长是否通过孤独感影响线下社交焦虑水平？",
            "transformation": [
                "兴趣：社交焦虑（太宽）",
                "现象：大学新生在面对面社交场合紧张",
                "变量：DV=社交焦虑（SIAS），IV=社交媒体使用时长，M=孤独感",
                "可证伪：若假设错，孤独感无中介作用，应观察到 a×b 路径不显著",
                "陈述：标准三变量中介模型句式",
            ],
            "why_better": "锁定具体人群+可测变量+理论机制（中介），可证伪可操作",
        },
        {
            "vague": "我想研究群体偏见",
            "bad_q": "为什么人们会对外群体有偏见？",
            "good_q": "在 18-22 岁大学生中，接触多元文化经历是否降低对农村学生的隐性偏见（IAT 测量）？",
            "transformation": [
                "兴趣：群体偏见（太抽象）",
                "现象：身边同学对农村背景学生有刻板印象",
                "变量：DV=隐性偏见（IAT 反应时差），IV=多元文化接触量表分",
                "可证伪：若假设错，IAT 差值与接触分无显著负相关",
                "陈述：相关研究句式",
            ],
            "why_better": "用 IAT 客观测量替代自报，减少社会称许性偏差",
        },
        {
            "vague": "我想研究亲社会行为",
            "bad_q": "什么样的人愿意帮助别人？",
            "good_q": "在 18-25 岁大学生中，共情能力（IRI）是否预测日常亲社会行为频次（自报日记法）？",
            "transformation": [
                "兴趣：亲社会行为（不知怎么测）",
                "现象：志愿服务投入度因人差异大",
                "变量：DV=亲社会行为日记（连续 7 天）频次，IV=IRI 共情得分",
                "可证伪：若假设错，共情高分组与低分组日均行为数无差异",
                "陈述：相关 + 组间比较",
            ],
            "why_better": "用日记法替代单次自报，提高生态效度",
        },
    ],
    # ===== 临床与健康心理学 =====
    "clinical": [
        {
            "vague": "我想研究抑郁",
            "bad_q": "什么样的人容易抑郁？",
            "good_q": "在产后 6 个月内的初产妇中，社会支持感知是否调节睡眠质量与产后抑郁倾向的关系？",
            "transformation": [
                "兴趣：抑郁（人群不明）",
                "现象：身边产妇晚上睡不好情绪也不好",
                "变量：DV=EPDS 抑郁分，IV=PSQI 睡眠质量，W=PSSS 社会支持",
                "可证伪：若假设错，交互项不显著",
                "陈述：调节模型句式",
            ],
            "why_better": "聚焦特殊人群+成熟量表三件齐全+可由 SPSS PROCESS 跑出",
        },
        {
            "vague": "我想研究焦虑",
            "bad_q": "考试焦虑严重吗？",
            "good_q": "在大三本科生中，正念冥想练习（4 周 vs 控制）是否降低考试焦虑（TAI）水平？",
            "transformation": [
                "兴趣：焦虑（场景不明）",
                "现象：大三同学考前情绪波动大",
                "变量：DV=TAI 考试焦虑，IV=干预（正念 vs 等待）",
                "可证伪：若假设错，两组前后测变化无差异",
                "陈述：前后测对照实验",
            ],
            "why_better": "用低成本干预（每日 15 分钟正念）+ 前后测设计，本科可独立完成",
        },
        {
            "vague": "我想研究创伤后应激",
            "bad_q": "PTSD 患者怎么治疗？",
            "good_q": "在亲历自然灾害的大学生中，自我同情程度（SCS）是否与 PTSD 症状严重程度（PCL-5）呈负相关？",
            "transformation": [
                "兴趣：创伤后应激（涉及临床患者门槛高）",
                "现象：身边经历过疫情或地震的同学反应不同",
                "变量：DV=PCL-5 症状分（自报，非诊断），IV=SCS 自我同情",
                "可证伪：若假设错，相关不显著或正向",
                "陈述：相关研究句式",
            ],
            "why_better": "用自报量表（非诊断）+ 已经历群体（非招募患者），避开临床伦理审批",
        },
    ],
    # ===== 教育心理学 =====
    "educational": [
        {
            "vague": "我想研究学习动机",
            "bad_q": "怎么提高学生的学习动机？",
            "good_q": "在大学英语课堂中，教师反馈类型（过程性 vs 结果性）是否影响学生的内在学习动机？",
            "transformation": [
                "兴趣：学习动机（不知如何测）",
                "现象：英语课不同老师风格不同，学生投入差很多",
                "变量：DV=AMS 内在动机分，IV=反馈类型（2 水平）",
                "可证伪：若假设错，两组均值无差异",
                "陈述：单因素被试间设计句式",
            ],
            "why_better": "把'怎么提高'（行动）转为'何种条件下更高'（实证）",
        },
        {
            "vague": "我想研究学业拖延",
            "bad_q": "为什么大学生总是拖延？",
            "good_q": "在大学生中，自我效能感（GSES）是否预测学业拖延行为（PASS 量表），完美主义是否调节这一关系？",
            "transformation": [
                "兴趣：拖延（原因太多）",
                "现象：身边同学 deadline 前才动手",
                "变量：DV=PASS 拖延分，IV=GSES 自我效能，W=完美主义（FMPS）",
                "可证伪：若假设错，效能与拖延相关不显著或交互不显著",
                "陈述：调节模型句式",
            ],
            "why_better": "把'为什么'（探索性）转为'X 是否影响 Y，W 是否调节'（验证性）",
        },
        {
            "vague": "我想研究师生关系",
            "bad_q": "好的师生关系对学生有什么好处？",
            "good_q": "在初中三年级学生中，感知到的师生关系质量（TSRS）是否与学业投入度（UWES-S）呈正相关？",
            "transformation": [
                "兴趣：师生关系（变量不明）",
                "现象：班主任风格不同的班级氛围差异大",
                "变量：DV=UWES-S 学业投入，IV=TSRS 师生关系感知",
                "可证伪：若假设错，相关不显著",
                "陈述：横断面相关研究",
            ],
            "why_better": "锁定关键学段（初三）+ 自报量表本科可发放，无需进课堂观察",
        },
    ],
    # ===== 发展心理学 =====
    "developmental": [
        {
            "vague": "我想研究亲子关系",
            "bad_q": "亲子关系好不好对孩子重要吗？",
            "good_q": "在 12-15 岁青少年中，父母依恋质量是否预测心理韧性，且这一关系是否被自尊水平所中介？",
            "transformation": [
                "兴趣：亲子关系（太抽象）",
                "现象：身边初中生与父母沟通差异大",
                "变量：DV=CD-RISC 韧性，IV=IPPA 父母依恋，M=Rosenberg 自尊",
                "可证伪：若假设错，间接效应 95% CI 跨过 0",
                "陈述：三变量中介模型句式",
            ],
            "why_better": "明确年龄段+三个量表都成熟+理论框架（依恋理论）支撑",
        },
        {
            "vague": "我想研究自我同一性",
            "bad_q": "大学生为什么会迷茫？",
            "good_q": "在大一新生中，自我同一性发展状态（EOMEIS-2）与生涯决策困难（CDDQ）是否呈负相关？",
            "transformation": [
                "兴趣：迷茫（构念不清）",
                "现象：大一同学频繁换专业方向",
                "变量：DV=CDDQ 生涯决策困难，IV=EOMEIS-2 同一性状态",
                "可证伪：若假设错，相关不显著",
                "陈述：横断面相关研究",
            ],
            "why_better": "用 Marcia 同一性理论的成熟量表，避开主观'迷茫'的歧义",
        },
        {
            "vague": "我想研究亲子冲突",
            "bad_q": "为什么青春期会和父母吵架？",
            "good_q": "在 14-17 岁高中生中，亲子冲突频率（CPS）是否被自主性需求满足程度（BPNS）所中介，进而影响生活满意度（SWLS）？",
            "transformation": [
                "兴趣：亲子冲突（年龄段不清）",
                "现象：高中同学回家后情绪低落",
                "变量：DV=SWLS 生活满意度，IV=CPS 冲突频率，M=BPNS 自主性满足",
                "可证伪：若假设错，间接效应 CI 跨 0",
                "陈述：中介模型",
            ],
            "why_better": "用自我决定理论（SDT）的 BPNS 作中介，机制清晰",
        },
    ],
    # ===== 认知心理学 =====
    "cognitive": [
        {
            "vague": "我想研究注意力",
            "bad_q": "玩手机会不会影响人的注意力？",
            "good_q": "在 18-25 岁大学生中，短视频日均使用时长是否与持续性注意（数字划消任务）成绩呈负相关？",
            "transformation": [
                "兴趣：注意力（哪一种？）",
                "现象：刷短视频后听课走神更厉害",
                "变量：DV=数字划消任务正确率/RT，IV=短视频时长（自报）",
                "可证伪：若假设错，r 不显著或正向",
                "陈述：相关研究句式",
            ],
            "why_better": "把'影响'（因果）降级为'相关'（横断面能做），用客观任务而非自报",
        },
        {
            "vague": "我想研究工作记忆",
            "bad_q": "工作记忆能不能训练？",
            "good_q": "在 18-22 岁大学生中，n-back 任务训练（2 周）是否提升日常学业相关工作记忆容量（WMS-IV 数字广度）？",
            "transformation": [
                "兴趣：工作记忆训练（结果尚有争议）",
                "现象：考试时记不住公式步骤",
                "变量：DV=WMS-IV 数字广度，IV=n-back 训练（训练组 vs 对照）",
                "可证伪：若假设错，两组前后测增量无差异",
                "陈述：前后测对照实验",
            ],
            "why_better": "用线上 n-back 工具+前后测设计，避开 EEG/fMRI 高门槛",
        },
        {
            "vague": "我想研究决策偏差",
            "bad_q": "人为什么会做错决定？",
            "good_q": "在大学生中，时间压力（30 秒 vs 无限制）是否影响损失厌恶程度（前景理论赌博任务）？",
            "transformation": [
                "兴趣：决策偏差（太宽）",
                "现象：考试题目时间不够时容易蒙",
                "变量：DV=损失厌恶系数 λ，IV=时间压力（2 水平被试内）",
                "可证伪：若假设错，两条件下 λ 无差异",
                "陈述：被试内实验设计",
            ],
            "why_better": "用经典赌博任务+被试内设计（n=30 即可），本科 PsychoPy 可实现",
        },
    ],
    # ===== 组织行为/工业心理学 =====
    "organizational": [
        {
            "vague": "我想研究职场倦怠",
            "bad_q": "为什么这么多人加班还不开心？",
            "good_q": "在 25-35 岁互联网从业者中，工作-家庭冲突是否预测职业倦怠，组织支持感是否缓冲这一关系？",
            "transformation": [
                "兴趣：倦怠（不知谁的倦怠）",
                "现象：互联网行业朋友都喊累但同公司差异大",
                "变量：DV=MBI 倦怠，IV=WFC 冲突，W=POS 组织支持",
                "可证伪：若假设错，POS×WFC 交互不显著",
                "陈述：调节模型句式",
            ],
            "why_better": "锁定特定行业+三个量表+理论（资源保存理论）支撑",
        },
        {
            "vague": "我想研究工作满意度",
            "bad_q": "什么样的工作让人开心？",
            "good_q": "在新入职 1 年内的应届生中，主管反馈频率是否预测工作满意度（MSQ），心理资本是否中介？",
            "transformation": [
                "兴趣：工作满意度（边界不明）",
                "现象：身边毕业的同学新工作适应度差很多",
                "变量：DV=MSQ 满意度，IV=主管反馈频率（自报次数），M=PsyCap 心理资本",
                "可证伪：若假设错，间接效应 CI 跨 0",
                "陈述：中介模型",
            ],
            "why_better": "锁定新员工（人群明确）+ 简单的频率自报变量+ PsyCap 量表",
        },
        {
            "vague": "我想研究领导风格",
            "bad_q": "什么样的领导最受欢迎？",
            "good_q": "在制造业基层员工中，变革型领导行为（MLQ）是否预测组织承诺（OCQ），LMX 是否中介？",
            "transformation": [
                "兴趣：领导风格（评价不一）",
                "现象：实习时不同主管下属投入度差异大",
                "变量：DV=OCQ 组织承诺，IV=MLQ 变革型领导分，M=LMX 领导成员交换",
                "可证伪：若假设错，间接效应 CI 跨 0",
                "陈述：中介模型",
            ],
            "why_better": "锁定行业+经典量表三件套+本科论文常见框架",
        },
    ],
}


def get_examples_by_domain(domain: str) -> List[Dict]:
    """按领域返回好/差选题对比。"""
    return GOOD_BAD_EXAMPLES.get(domain, []) or []


def list_all_domains() -> List[str]:
    return list(GOOD_BAD_EXAMPLES.keys())


def list_all_examples() -> List[Dict]:
    """扁平化返回所有 18 条范例（每条带 domain 字段）。

    v3.5: 优先用 streamlit cache_resource 缓存（避免每次 rerun 重建）。
    """
    return _cached_list_all_examples()


def _build_all_examples() -> List[Dict]:
    out: List[Dict] = []
    for domain, items in GOOD_BAD_EXAMPLES.items():
        for ex in items:
            entry = dict(ex)
            entry["domain"] = domain
            out.append(entry)
    return out


# v3.5 启动缓存：18 条范例只构建一次
try:
    import streamlit as _st
    _cached_list_all_examples = _st.cache_resource(_build_all_examples)
except Exception:
    # streamlit 不可用（如测试环境裸跑）→ 直接函数无缓存
    _cached_list_all_examples = _build_all_examples


# ---------------------------------------------------------------------------
# v3.3 语义匹配：利用 IntentRecognitionChain 提取关键构念，匹配最相关 top_k 范例
# ---------------------------------------------------------------------------

# 领域关键词锚点（与 construct_kb 的 7 域不完全对应，因为 GOOD_BAD_EXAMPLES 用 6 域）
_DOMAIN_ANCHORS: Dict[str, List[str]] = {
    "social": ["社交", "群体", "偏见", "歧视", "亲社会", "助人", "孤独", "归属", "认同"],
    "clinical": ["抑郁", "焦虑", "创伤", "应激", "PTSD", "睡眠", "心理健康", "障碍", "症状"],
    "educational": ["学习", "学业", "教师", "课堂", "拖延", "动机", "效能", "成绩", "师生"],
    "developmental": ["亲子", "依恋", "青少年", "同一性", "儿童", "父母", "发展", "青春期"],
    "cognitive": ["注意", "记忆", "决策", "偏差", "认知", "执行", "工作记忆", "反应时", "n-back"],
    "organizational": ["工作", "职场", "倦怠", "领导", "员工", "组织", "薪酬", "上司", "职业"],
}


def _char_bigram_overlap(a: str, b: str) -> float:
    """字符级 bigram 相似度（0-1），对中文短文本友好。"""
    if not a or not b:
        return 0.0
    bg_a = {a[i:i+2] for i in range(max(0, len(a) - 1))}
    bg_b = {b[i:i+2] for i in range(max(0, len(b) - 1))}
    if not bg_a or not bg_b:
        return 0.0
    inter = len(bg_a & bg_b)
    union = len(bg_a | bg_b)
    return inter / union if union else 0.0


def _domain_score(text: str, domain: str) -> float:
    """根据领域锚点关键词命中数返回 0-1 分。"""
    anchors = _DOMAIN_ANCHORS.get(domain, [])
    if not anchors:
        return 0.0
    hits = sum(1 for kw in anchors if kw in text)
    return min(1.0, hits / 3.0)  # 3 个命中视为满分


def _try_extract_constructs_with_chain(text: str) -> List[str]:
    """尝试用 IntentRecognitionChain 提取构念名（失败返回空，不抛异常）。"""
    try:
        from src.questionnaire.construct_kb import CONSTRUCTS, CONSTRUCT_KEYWORDS
        from src.questionnaire.construct_kb_extended import EXTENDED_CONSTRUCTS
        from src.questionnaire.intent_recognizer import create_default_chain
        chain = create_default_chain(
            constructs=CONSTRUCTS,
            keywords=CONSTRUCT_KEYWORDS,
            extended_constructs=EXTENDED_CONSTRUCTS,
        )
        result = chain.recognize(text)
        return [c.construct_name for c in (result.candidates or [])[:3]]
    except Exception:
        return []


def match_examples_by_semantics(
    user_input: str,
    top_k: int = 2,
    *,
    similarity_threshold: float = 0.05,
) -> List[Dict[str, Any]]:
    """根据用户输入返回最相关的 top_k 个范例（含 domain）。

    评分 = 0.5 × 字符 bigram 相似度（vague 字段）
         + 0.3 × 领域锚点命中分
         + 0.2 × 构念名出现得分（IntentRecognitionChain 提取的构念是否出现在 vague/good_q）

    低于 similarity_threshold 视为无匹配，返回空列表。
    """
    if not user_input or not user_input.strip():
        return []
    text = user_input.strip()

    constructs = _try_extract_constructs_with_chain(text)
    construct_set = {c.lower() for c in constructs if c}

    scored: List[tuple] = []
    for ex in list_all_examples():
        bigram = _char_bigram_overlap(text, ex.get("vague", ""))
        domain_s = _domain_score(text, ex.get("domain", ""))
        c_score = 0.0
        if construct_set:
            blob = (ex.get("vague", "") + " " + ex.get("good_q", "")).lower()
            c_score = min(1.0, sum(1 for c in construct_set if c in blob) / len(construct_set))
        score = 0.5 * bigram + 0.3 * domain_s + 0.2 * c_score
        scored.append((score, ex))

    scored.sort(key=lambda x: -x[0])
    out: List[Dict[str, Any]] = []
    for score, ex in scored[: max(0, int(top_k))]:
        if score < similarity_threshold:
            break
        entry = dict(ex)
        entry["_score"] = round(score, 3)
        out.append(entry)
    return out


def render_examples_for_prompt(examples: List[Dict[str, Any]], max_chars: int = 600) -> str:
    """把匹配到的范例渲染为 LLM prompt 友好的简短文本（避免 token 浪费）。"""
    if not examples:
        return ""
    lines: List[str] = ["# 可参考的同类好/差选题对比范例（仅供启发，不要照搬）"]
    for i, ex in enumerate(examples, 1):
        snippet = (
            f"\n## 范例 {i}（{ex.get('domain', '')}）\n"
            f"- 模糊起点：{ex.get('vague', '')}\n"
            f"- 收敛后：{ex.get('good_q', '')}\n"
            f"- 关键转折：{ex.get('why_better', '')}"
        )
        if sum(len(l) for l in lines) + len(snippet) > max_chars:
            break
        lines.append(snippet)
    return "\n".join(lines)
