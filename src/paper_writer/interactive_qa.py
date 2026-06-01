"""论文写作系统 — 交互问答引擎

在写作过程中识别信息缺口，向用户提问以提高论文质量。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable


@dataclass
class Question:
    """向用户提出的问题"""
    id: str
    category: str                      # "research_gap", "method", "results", "discussion", "literature"
    question: str                      # 问题文本
    hint: str = ""                     # 提示/示例答案
    importance: str = "high"           # "high" | "medium" | "low"
    default_answer: str = ""           # 智能猜测的默认答案
    user_answer: str = ""              # 用户回答
    answered: bool = False


@dataclass
class QAResult:
    questions: List[Question]
    answered_count: int
    pending_count: int
    summary: str                       # 对用户回答的提炼摘要


# 问题模板库
QUESTION_TEMPLATES = {
    "research_gap": [
        {
            "template": "您的研究与以往研究相比，最主要的创新点或不同之处是什么？",
            "hint": "例如：首次在中文样本中检验了X对Y的中介机制；引入了Z作为新的调节变量；使用了纵向设计而非横断设计等。",
            "importance": "high",
        },
        {
            "template": "本研究的理论框架主要基于哪些理论？请简要说明。",
            "hint": "例如：自我决定理论(SDT)、资源保存理论(COR)、社会认知理论等。",
            "importance": "high",
        },
        {
            "template": "本研究的被试群体有什么特殊性吗？如果有，请说明。",
            "hint": "例如：特定年龄段、特定职业群体、临床样本等。如果没有特殊性，可以说明是普通成人样本。",
            "importance": "medium",
        },
        {
            "template": "您预期的主要研究发现是什么？请用1-2句话概括。",
            "hint": "例如：预期X通过M的中介作用正向预测Y，且这一关系受Z的调节。",
            "importance": "high",
        },
    ],
    "method": [
        {
            "template": "被试的招募方式是什么？是否有纳入/排除标准？",
            "hint": "例如：通过网络平台(如Credamo/问卷星)招募，排除标准为...",
            "importance": "high",
        },
        {
            "template": "研究所用量表是否有中文修订版？信效度数据是否已知？",
            "hint": "例如：XXX量表中文版由XXX(2020)修订，在本研究中的Cronbach's α=0.85。",
            "importance": "high",
        },
        {
            "template": "施测是如何进行的？是线上还是线下？有无时间限制？",
            "hint": "例如：通过Credamo平台在线施测，完成时间约15-20分钟。",
            "importance": "medium",
        },
        {
            "template": "研究是否获得了伦理审批？如果有，请提供审批信息。",
            "hint": "例如：本研究已获得XX大学伦理委员会批准（批准号：XXX）。",
            "importance": "medium",
        },
        {
            "template": "样本量是如何确定的？是否进行了事前统计效力分析？",
            "hint": "例如：基于G*Power分析，中等效应量(f²=0.15)，80%统计效力，需N≥XXX。",
            "importance": "high",
        },
    ],
    "results": [
        {
            "template": "是否有需要特别强调的描述统计结果？",
            "hint": "例如：各变量的均值、标准差，以及某些值得注意的人口学差异。",
            "importance": "medium",
        },
        {
            "template": "除了假设检验，是否进行了补充分析（如控制性别/年龄后的稳健性检验）？",
            "hint": "例如：将性别和年龄作为协变量重新分析后结果基本一致。",
            "importance": "medium",
        },
        {
            "template": "是否检测了共同方法偏差？结果如何？",
            "hint": "例如：Harman单因素检验显示第一个因子解释了XX%的变异（<40%），共同方法偏差不严重。",
            "importance": "high",
        },
    ],
    "discussion": [
        {
            "template": "您认为本研究最重要的实践意义是什么？对哪个领域或人群最有启发？",
            "hint": "例如：对学校心理健康教育、企业员工管理、临床干预等领域的启示。",
            "importance": "high",
        },
        {
            "template": "本研究是否存在您已经意识到的不足或局限？",
            "hint": "例如：横断设计无法推断因果、自评问卷可能存在社会赞许偏差、样本代表性有限等。",
            "importance": "high",
        },
        {
            "template": "您是否有计划中的后续研究来弥补本研究的不足？",
            "hint": "例如：后续将采用纵向追踪设计、多来源数据、实验法等进行交叉验证。",
            "importance": "medium",
        },
    ],
    "literature": [
        {
            "template": "您是否有特别希望引用的文献？如果有，请提供文献信息。",
            "hint": "例如：XXX等人(2022)在《心理学报》上发表的关于...的研究。系统会自动在预置文献库和在线数据库中进行补充搜索。",
            "importance": "medium",
        },
    ],
}


class InteractiveQA:
    """交互问答管理器"""

    def __init__(self, paper_context: dict):
        self.context = paper_context
        self.questions: List[Question] = []
        self.question_index = 0

    def generate_questions(
        self,
        categories: Optional[List[str]] = None,
        max_per_category: int = 2,
    ) -> List[Question]:
        """根据论文上下文生成问题列表"""
        if categories is None:
            categories = ["research_gap", "method", "results", "discussion", "literature"]

        self.questions = []
        qid = 0

        for cat in categories:
            templates = QUESTION_TEMPLATES.get(cat, [])
            for i, tmpl in enumerate(templates):
                if i >= max_per_category:
                    break
                qid += 1

                # 尝试智能填充默认答案
                default = self._guess_answer(cat, tmpl["template"])

                self.questions.append(Question(
                    id=f"q{qid}",
                    category=cat,
                    question=tmpl["template"],
                    hint=tmpl.get("hint", ""),
                    importance=tmpl.get("importance", "medium"),
                    default_answer=default,
                ))

        return self.questions

    def _guess_answer(self, category: str, template: str) -> str:
        """基于已有上下文智能猜测答案"""
        ctx = self.context
        if category == "research_gap" and "创新" in template:
            dvs = ctx.get("dependent_vars", [])
            ivs = ctx.get("independent_vars", [])
            if dvs and ivs:
                return f"探讨{'、'.join(ivs)}对{'、'.join(dvs)}的影响机制"

        if category == "method" and "伦理" in template:
            return "本研究已获得伦理审批（待补充具体信息）。"

        if category == "results" and "共同方法" in template:
            return "采用Harman单因素检验进行了共同方法偏差检验（待填入具体结果）。"

        if category == "discussion" and "不足" in template:
            return "需讨论横断设计的局限性，以及自评问卷可能存在的偏差。"

        if category == "literature" and "希望引用" in template:
            return "暂无特别指定的文献，可依赖系统自动推荐。"

        return ""

    def answer_question(self, question_id: str, answer: str):
        """记录用户的回答"""
        for q in self.questions:
            if q.id == question_id:
                q.user_answer = answer
                q.answered = True
                break

    def get_pending_questions(self) -> List[Question]:
        """获取未回答的高优先级问题"""
        pending = [q for q in self.questions if not q.answered and q.importance == "high"]
        if not pending:
            pending = [q for q in self.questions if not q.answered]
        return pending

    def get_summary(self) -> QAResult:
        """获取问答摘要"""
        answered = [q for q in self.questions if q.answered]
        pending = [q for q in self.questions if not q.answered]

        if answered:
            summary_parts = []
            for q in answered:
                summary_parts.append(f"• {q.question[:30]}... → {q.user_answer[:50]}...")
            summary = "\n".join(summary_parts)
        else:
            summary = "尚未收到任何回答。"

        return QAResult(
            questions=self.questions,
            answered_count=len(answered),
            pending_count=len(pending),
            summary=summary,
        )

    def incorporate_answers(self) -> Dict[str, str]:
        """将用户回答整合为论文写作指令"""
        instructions = {}

        for category in set(q.category for q in self.questions):
            answers_in_cat = [q for q in self.questions if q.category == category and q.answered]
            if answers_in_cat:
                instructions[category] = "\n".join(
                    f"- {q.question}: {q.user_answer}" for q in answers_in_cat
                )

        return instructions
