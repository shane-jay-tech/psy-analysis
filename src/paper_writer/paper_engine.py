"""论文写作引擎 — 论文初稿生成的核心调度器"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

import pandas as pd

from .psychology_report_format import PAPER_SECTIONS
from .literature_manager import LiteratureManager, LiteratureEntry, smart_search_literature
from .interactive_qa import InteractiveQA, Question
from .section_writers import (
    PaperContext,
    write_title, write_abstract, write_keywords,
    write_introduction, write_methods, write_results,
    write_discussion, write_references,
)


@dataclass
class PaperState:
    """论文写作会话状态"""
    # 基本信息
    topic: str = ""
    title_hint: str = ""
    research_questions: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)

    # 方法
    participants_n: int = 0
    participants_desc: str = ""
    male_ratio: float = 0.5
    age_mean: float = 0.0
    age_sd: float = 0.0
    materials: List[Dict] = field(default_factory=list)
    procedure: str = ""
    ethics: str = ""

    # 讨论
    theoretical_contributions: List[str] = field(default_factory=list)
    practical_implications: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    future_directions: List[str] = field(default_factory=list)
    control_vars: List[str] = field(default_factory=list)

    # 数据与结果
    df: Optional[pd.DataFrame] = None
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    table_data: Dict[str, pd.DataFrame] = field(default_factory=dict)
    chart_files: Dict[str, str] = field(default_factory=dict)

    # 文献
    user_literature: List[Dict] = field(default_factory=list)
    suggested_literature: List[Dict] = field(default_factory=list)

    # 生成状态
    generated_sections: Dict[str, str] = field(default_factory=dict)
    reference_list: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    # 问答
    qa_questions: List[Dict] = field(default_factory=list)
    qa_answers: Dict[str, str] = field(default_factory=dict)

    # 日志
    logs: List[str] = field(default_factory=list)
    current_step: str = "idle"


class PaperEngine:
    """论文写作引擎"""

    def __init__(self):
        self.state = PaperState()
        self.lit_manager = LiteratureManager()
        self.qa_engine: Optional[InteractiveQA] = None

    # ================================================================
    # Step 1: 设置研究信息
    # ================================================================
    def set_topic(
        self,
        topic: str,
        research_questions: List[str] = None,
        hypotheses: List[str] = None,
        title_hint: str = "",
    ):
        """设置研究主题和假设"""
        self.state.topic = topic
        self.state.title_hint = title_hint
        self.state.research_questions = research_questions or []
        self.state.hypotheses = hypotheses or []
        self.state.current_step = "topic_set"
        self.state.logs.append(f"✅ 已设置研究主题：{topic}")
        if hypotheses:
            self.state.logs.append(f"   共{len(hypotheses)}个研究假设")

    def set_methods(
        self,
        participants_n: int = 0,
        male_ratio: float = 0.5,
        age_mean: float = 0.0,
        age_sd: float = 0.0,
        participants_desc: str = "",
        materials: List[Dict] = None,
        procedure: str = "",
        ethics: str = "",
        control_vars: List[str] = None,
    ):
        """设置方法信息"""
        self.state.participants_n = participants_n
        self.state.male_ratio = male_ratio
        self.state.age_mean = age_mean
        self.state.age_sd = age_sd
        self.state.participants_desc = participants_desc
        self.state.materials = materials or []
        self.state.procedure = procedure
        self.state.ethics = ethics
        self.state.control_vars = control_vars or []
        self.state.current_step = "methods_set"
        self.state.logs.append(f"✅ 已设置方法信息（N={participants_n or '待定'}）")

    def set_discussion(
        self,
        theoretical: List[str] = None,
        practical: List[str] = None,
        limitations: List[str] = None,
        future: List[str] = None,
    ):
        """设置讨论要点"""
        self.state.theoretical_contributions = theoretical or []
        self.state.practical_implications = practical or []
        self.state.limitations = limitations or []
        self.state.future_directions = future or []
        self.state.current_step = "discussion_set"
        self.state.logs.append("✅ 已设置讨论要点")

    # ================================================================
    # Step 2: 导入分析结果
    # ================================================================
    def import_analysis_results(self, analysis_outputs: Dict[str, Dict]):
        """
        从分析系统导入结果。

        参数：
            analysis_outputs: {test_type: output_dict, ...}
            其中 output_dict 是 runner.run_analysis() 的返回值
        """
        self.state.analysis_results = analysis_outputs

        # 自动提取表格和图表数据
        for test_type, output in analysis_outputs.items():
            if isinstance(output, dict):
                # 提取描述统计表
                desc = output.get("descriptive")
                if desc is not None and isinstance(desc, pd.DataFrame):
                    self.state.table_data[f"{test_type}_descriptive"] = desc

                # 提取结果
                result = output.get("result")
                if result is not None:
                    if hasattr(result, "table"):
                        self.state.table_data[f"{test_type}_table"] = result.table
                    if hasattr(result, "coef_table"):
                        self.state.table_data[f"{test_type}_coef"] = result.coef_table
                    if hasattr(result, "loadings"):
                        self.state.table_data[f"{test_type}_loadings"] = result.loadings

        self.state.current_step = "results_imported"
        n_results = len(analysis_outputs)
        self.state.logs.append(f"✅ 已导入{len(analysis_outputs)}项分析结果")
        return self

    def set_data(self, df: pd.DataFrame):
        """设置原始数据"""
        self.state.df = df
        self.state.logs.append(f"✅ 已载入数据（{len(df)}行 × {len(df.columns)}列）")

    # ================================================================
    # Step 3: 文献搜索
    # ================================================================
    def search_literature(self, keywords: List[str] = None) -> List[Dict]:
        """搜索相关文献"""
        if keywords is None:
            # 从主题和假设中提取关键词
            keywords = []
            if self.state.topic:
                keywords.extend(self.state.topic.split()[:3])
            for hyp in self.state.hypotheses[:2]:
                keywords.extend(hyp.split()[:3])

        results = self.lit_manager.search_presets(keywords, n=8)
        self.state.suggested_literature = [
            {
                "key": e.key,
                "authors": e.authors,
                "year": e.year,
                "title": e.title,
                "journal": e.journal,
                "is_chinese": e.is_chinese,
                "source": e.source,
                "relevance": e.relevance_note,
            }
            for e in results
        ]
        self.state.current_step = "literature_searched"
        self.state.logs.append(f"✅ 已搜索到{len(self.state.suggested_literature)}篇相关文献")
        return self.state.suggested_literature

    def add_user_literature(self, lit_dicts: List[Dict]):
        """添加用户指定的文献"""
        for ld in lit_dicts:
            entry = LiteratureEntry(
                key=ld.get("key", f"user_{len(self.state.user_literature)}"),
                authors=ld.get("authors", []),
                year=ld.get("year", ""),
                title=ld.get("title", ""),
                journal=ld.get("journal", ""),
                is_chinese=ld.get("is_chinese", True),
                source="user",
                relevance_note=ld.get("relevance", ""),
            )
            self.lit_manager.add_entry(entry)
            self.state.user_literature.append(ld)
        self.state.logs.append(f"✅ 已添加{len(lit_dicts)}篇用户指定文献")

    # ================================================================
    # 文件导入
    # ================================================================
    def import_methods_from_file(self, file_path: str):
        """从文件导入方法信息（支持JSON和Excel）。

        JSON格式示例:
        {
          "participants_n": 300,
          "male_ratio": 0.45,
          "age_mean": 20.5,
          "age_sd": 2.1,
          "participants_desc": "在校大学生",
          "materials": [
            {"name": "自尊量表(SES)", "items": "10", "alpha": "0.85", "source": "Rosenberg, 1965"},
            {"name": "社交焦虑量表(SAS)", "items": "20", "alpha": "0.89", "source": "Zung, 1971"}
          ],
          "procedure": "通过网络平台在线施测...",
          "ethics": "XX大学伦理委员会批准",
          "control_vars": ["性别", "年龄"],
          "theoretical": ["理论贡献1", "理论贡献2"],
          "practical": ["实践意义1"],
          "limitations": ["局限1", "局限2"],
          "future": ["未来方向1"]
        }
        """
        path = Path(file_path)

        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif path.suffix.lower() in (".xlsx", ".xls"):
            data = self._parse_methods_excel(path)
        else:
            raise ValueError(f"不支持的文件格式: {path.suffix}。请使用 .json 或 .xlsx 文件。")

        # 填充方法信息
        self.set_methods(
            participants_n=data.get("participants_n", self.state.participants_n),
            male_ratio=data.get("male_ratio", self.state.male_ratio),
            age_mean=data.get("age_mean", self.state.age_mean),
            age_sd=data.get("age_sd", self.state.age_sd),
            participants_desc=data.get("participants_desc", self.state.participants_desc),
            materials=data.get("materials", self.state.materials),
            procedure=data.get("procedure", self.state.procedure),
            ethics=data.get("ethics", self.state.ethics),
            control_vars=data.get("control_vars", self.state.control_vars),
        )

        self.set_discussion(
            theoretical=data.get("theoretical", self.state.theoretical_contributions),
            practical=data.get("practical", self.state.practical_implications),
            limitations=data.get("limitations", self.state.limitations),
            future=data.get("future", self.state.future_directions),
        )

        self.state.logs.append(f"✅ 已从文件导入方法信息: {path.name}")
        return self

    def _parse_methods_excel(self, path: Path) -> Dict:
        """解析Excel格式的方法信息文件"""
        df_dict = pd.read_excel(path, sheet_name=None)

        data = {}
        # sheet "基本信息": participants_n, male_ratio, age_mean, age_sd, etc.
        if "基本信息" in df_dict:
            info = df_dict["基本信息"]
            row = info.iloc[0] if len(info) > 0 else {}
            for col in info.columns:
                val = row.get(col, "")
                if col == "participants_n":
                    data["participants_n"] = int(val) if pd.notna(val) else 0
                elif col == "male_ratio":
                    data["male_ratio"] = float(val) if pd.notna(val) else 0.5
                elif col == "age_mean":
                    data["age_mean"] = float(val) if pd.notna(val) else 0.0
                elif col == "age_sd":
                    data["age_sd"] = float(val) if pd.notna(val) else 0.0
                elif col == "participants_desc":
                    data["participants_desc"] = str(val) if pd.notna(val) else ""
                elif col == "procedure":
                    data["procedure"] = str(val) if pd.notna(val) else ""
                elif col == "ethics":
                    data["ethics"] = str(val) if pd.notna(val) else ""
                elif col == "control_vars":
                    data["control_vars"] = [c.strip() for c in str(val).split(",") if c.strip()] if pd.notna(val) else []

        # sheet "量表": materials
        if "量表" in df_dict:
            materials = []
            for _, row in df_dict["量表"].iterrows():
                materials.append({
                    "name": str(row.get("name", row.get("名称", ""))),
                    "items": str(row.get("items", row.get("题数", ""))),
                    "alpha": str(row.get("alpha", row.get("信度", ""))),
                    "source": str(row.get("source", row.get("来源", ""))),
                })
            data["materials"] = materials

        # sheet "讨论": theoretical, practical, limitations, future
        if "讨论" in df_dict:
            disc = df_dict["讨论"]
            for col in disc.columns:
                vals = [str(v) for v in disc[col].dropna().tolist() if str(v).strip()]
                if "理论" in col:
                    data["theoretical"] = vals
                elif "实践" in col:
                    data["practical"] = vals
                elif "局限" in col:
                    data["limitations"] = vals
                elif "未来" in col:
                    data["future"] = vals

        return data

    def import_literature_from_file(self, file_path: str):
        """从文件导入文献（支持BibTeX、CSV、JSON）。

        BibTeX格式(.bib): 标准BibTeX条目
        CSV格式(.csv): 列名 authors, year, title, journal, is_chinese
        JSON格式(.json): [{"authors": [...], "year": "", "title": "", ...}]
        """
        import re
        path = Path(file_path)
        suffix = path.suffix.lower()

        lit_dicts = []
        if suffix == ".bib":
            lit_dicts = self._parse_bibtex(path)
        elif suffix == ".csv":
            lit_dicts = self._parse_lit_csv(path)
        elif suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                lit_dicts = json.load(f)
        else:
            raise ValueError(f"不支持的文献文件格式: {suffix}。请使用 .bib, .csv 或 .json 文件。")

        self.add_user_literature(lit_dicts)
        self.state.logs.append(f"✅ 已从文件导入{len(lit_dicts)}篇文献: {path.name}")
        return self

    def _parse_bibtex(self, path: Path) -> List[Dict]:
        """解析BibTeX文件"""
        import re
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        entries = []
        # 匹配 @article{...}, @book{...} 等
        pattern = r'@\w+\{([^,]+),\s*(.*?)\}'
        for match in re.finditer(pattern, content, re.DOTALL):
            key = match.group(1).strip()
            fields_str = match.group(2)

            fields = {}
            # 解析字段: field = {value} 或 field = "value"
            field_pattern = r'(\w+)\s*=\s*[{"]([^}"]*)[}"]'
            for fm in re.finditer(field_pattern, fields_str):
                fields[fm.group(1).lower()] = fm.group(2)

            authors_str = fields.get("author", "")
            authors = [a.strip() for a in re.split(r'\s+and\s+', authors_str) if a.strip()]

            title = fields.get("title", "").replace("{", "").replace("}", "")
            # 检查是否中文
            is_chinese = any("一" <= c <= "鿿" for c in title + authors_str)

            entries.append({
                "key": key,
                "authors": authors,
                "year": fields.get("year", ""),
                "title": title,
                "journal": fields.get("journal", fields.get("booktitle", fields.get("publisher", ""))),
                "is_chinese": is_chinese,
                "source": f"bibtex:{path.name}",
                "relevance": "",
            })

        return entries

    def _parse_lit_csv(self, path: Path) -> List[Dict]:
        """解析CSV格式的文献文件"""
        df = pd.read_csv(path, encoding="utf-8")
        entries = []
        for _, row in df.iterrows():
            authors_val = row.get("authors", "")
            if isinstance(authors_val, str):
                authors = [a.strip() for a in authors_val.split(";") if a.strip()]
            else:
                authors = []

            entries.append({
                "key": row.get("key", f"csv_{len(entries)}"),
                "authors": authors,
                "year": str(row.get("year", "")),
                "title": str(row.get("title", "")),
                "journal": str(row.get("journal", "")),
                "is_chinese": bool(row.get("is_chinese", True)),
                "source": f"csv:{path.name}",
                "relevance": str(row.get("relevance", "")),
            })

        return entries

    # ================================================================
    # Step 4: 交互问答
    # ================================================================
    def generate_questions(self) -> List[Question]:
        """生成需要向用户确认的问题"""
        context = self._build_context()
        self.qa_engine = InteractiveQA(context)
        questions = self.qa_engine.generate_questions(
            categories=["research_gap", "method", "results", "discussion"]
        )
        self.state.qa_questions = [
            {
                "id": q.id,
                "category": q.category,
                "question": q.question,
                "hint": q.hint,
                "importance": q.importance,
                "default_answer": q.default_answer,
            }
            for q in questions
        ]
        self.state.current_step = "questions_generated"
        self.state.logs.append(f"✅ 已生成{len(questions)}个确认问题")
        return questions

    def answer_questions(self, answers: Dict[str, str]):
        """记录用户的回答"""
        if self.qa_engine is None:
            return
        for qid, answer in answers.items():
            self.qa_engine.answer_question(qid, answer)
            self.state.qa_answers[qid] = answer
        self.state.logs.append(f"✅ 已记录{len(answers)}条回答")

    def get_pending_gaps(self) -> List[Dict]:
        """获取影响论文质量的未回答高优先级问题"""
        if self.qa_engine is None:
            return []
        pending = self.qa_engine.get_pending_questions()
        return [
            {"id": q.id, "question": q.question, "hint": q.hint, "importance": q.importance}
            for q in pending
        ]

    # ================================================================
    # Step 5: 生成论文
    # ================================================================
    def generate_full_paper(self) -> Dict[str, str]:
        """生成完整论文初稿"""
        context = self._build_context()
        context.literature_manager = self.lit_manager

        sections = {}

        # 生成各章节
        sections["title"] = write_title(context)
        sections["abstract"] = write_abstract(context)
        sections["keywords"] = ", ".join(write_keywords(context))
        sections["introduction"] = write_introduction(context)
        sections["methods"] = write_methods(context)
        sections["results"] = write_results(context)
        sections["discussion"] = write_discussion(context)
        sections["references"] = write_references(context)

        self.state.generated_sections = sections
        self.state.reference_list = self.lit_manager.format_reference_list()
        self.state.keywords = write_keywords(context)
        self.state.current_step = "paper_generated"
        self.state.logs.append("✅ 论文初稿已生成")

        return sections

    def generate_section(self, section_name: str) -> str:
        """生成单个章节"""
        writers = {
            "title": write_title,
            "abstract": write_abstract,
            "introduction": write_introduction,
            "methods": write_methods,
            "results": write_results,
            "discussion": write_discussion,
            "references": write_references,
        }
        writer = writers.get(section_name)
        if writer is None:
            return f"未知章节: {section_name}"

        context = self._build_context()
        context.literature_manager = self.lit_manager

        text = writer(context)
        self.state.generated_sections[section_name] = text
        return text

    def assemble_manuscript(self) -> str:
        """组装完整稿件（用于输出）"""
        sections = self.state.generated_sections
        if not sections:
            sections = self.generate_full_paper()

        lines = []
        lines.append(f"# {sections.get('title', '心理学实证研究')}")
        lines.append("")
        lines.append("## 摘要")
        lines.append(sections.get("abstract", ""))
        lines.append("")
        kw = sections.get("keywords", "")
        lines.append(f"**关键词：** {kw}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(sections.get("introduction", ""))
        lines.append("")
        lines.append(sections.get("methods", ""))
        lines.append("")
        lines.append(sections.get("results", ""))
        lines.append("")
        lines.append(sections.get("discussion", ""))
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(sections.get("references", ""))

        return "\n".join(lines)

    # ================================================================
    # 辅助
    # ================================================================
    def _build_context(self) -> PaperContext:
        """构建论文写作上下文"""
        # 整合用户回答
        user_answers = {
            q["id"]: self.state.qa_answers.get(q["id"], q.get("default_answer", ""))
            for q in self.state.qa_questions
        }

        return PaperContext(
            title_hint=self.state.title_hint,
            topic=self.state.topic,
            research_questions=self.state.research_questions,
            hypotheses=self.state.hypotheses,
            participants_n=self.state.participants_n,
            participants_desc=self.state.participants_desc,
            male_ratio=self.state.male_ratio,
            age_mean=self.state.age_mean,
            age_sd=self.state.age_sd,
            materials=self.state.materials,
            procedure=self.state.procedure,
            ethics=self.state.ethics,
            analysis_results=self.state.analysis_results,
            df=self.state.df,
            table_data=self.state.table_data,
            chart_files=self.state.chart_files,
            theoretical_contributions=self.state.theoretical_contributions,
            practical_implications=self.state.practical_implications,
            limitations=self.state.limitations,
            future_directions=self.state.future_directions,
            control_vars=self.state.control_vars,
            user_answers=user_answers,
            literature_manager=self.lit_manager,
        )

    def get_logs(self) -> List[str]:
        return self.state.logs

    def get_gaps_summary(self) -> str:
        """获取信息缺口摘要"""
        gaps = []
        if not self.state.topic:
            gaps.append("❌ 未设置研究主题")
        if not self.state.hypotheses:
            gaps.append("⚠ 未填写研究假设")
        if not self.state.participants_n:
            gaps.append("⚠ 未填写被试数量")
        if not self.state.materials:
            gaps.append("⚠ 未填写量表信息")
        if not self.state.analysis_results:
            gaps.append("⚠ 未导入分析结果")
        if not gaps:
            return "✅ 所有关键信息已就绪，可以生成论文。"
        return "\n".join(gaps)


# ===========================================================================
# LLM 语言润色 (Task 12)
# ===========================================================================

# ===========================================================================
# v3.6: 反问式审阅（哲学统一：先你写一稿，AI 追问而非替写）
# ===========================================================================

REVIEWER_SYSTEM_PROMPT = """\
你是心理学学术写作审稿人。学生写了一段论文初稿（{section_zh}部分），
请用**苏格拉底式追问**指出可改进点，而不是直接帮他改写。

你必须遵守的规则：
1. **输出 3-5 条具体追问**，每条以「？」结尾，每条 ≤80 字
2. **指向具体问题**，不要空泛说"建议优化"——要点出"哪一句话/哪个数据/哪个方法不够清楚"
3. **覆盖 APA7 检查点**（按章节）：
   - methods: 是否报告样本量？是否说明数据清洗？是否报告效应量？是否提到信度/效度？
   - results: 是否报告 t/F 值 + df + p 值 + 效应量？是否有置信区间？是否区分显著与不显著？
   - discussion: 是否解读效应量大小？是否承认局限？是否对比已有研究？是否提出未来方向？
   - introduction: 是否清楚阐明研究问题？是否回顾已有文献？是否提出明确假设？
4. **禁止改写示例**——不要给出"建议改成 XX"的具体替换文本
5. **禁止赞美**——不要说"你写得很好"
6. **保持学术严谨**——不要用情感化或口语化语言

输出格式（严格遵循）：
1. <追问1>？
2. <追问2>？
3. <追问3>？
（最多 5 条；不要加总结、不要加编号说明）
"""


REVISER_SYSTEM_PROMPT = """\
你是心理学学术写作助手。学生写了一段{section_zh}初稿，并被审稿人提出了若干追问，
请基于学生的回答和审稿建议**整合修订**，输出修订后的完整段落。

规则：
1. **保留学生的核心论述和表达风格**，仅在追问指出的具体点上修改
2. **不要扩写未必要的部分**——简洁优于冗长
3. **遵守 APA7 规范**：p 值无前导零、效应量两位小数、引用格式正确
4. **不修改任何数据/统计值**——这些必须与原文一致
5. 直接输出修订后的段落正文，**不要加标题、不要加说明**

学生原文与审稿追问见下方 user 消息。"""


def _format_gap_context(gap_analysis: Optional[List[Any]]) -> str:
    """v3.7: 把 literature_review 的 gap 列表格式化为 system prompt 注入。

    Args:
        gap_analysis: List[GapAnalysis] 或 List[dict]（兼容两种）

    Returns:
        若 gap_analysis 为空或无效，返回空字符串；否则返回带换行的注入段落。
    """
    if not gap_analysis:
        return ""
    descriptions: List[str] = []
    for g in gap_analysis:
        if isinstance(g, dict):
            desc = (g.get("gap_description") or "").strip()
        else:
            desc = (getattr(g, "gap_description", "") or "").strip()
        if desc:
            descriptions.append(desc)
    if not descriptions:
        return ""
    bullet = "\n".join(f"  - {d[:200]}" for d in descriptions[:5])
    return (
        "\n\n【学生已在文献综述阶段识别以下研究空白 (gap)】\n"
        f"{bullet}\n"
        "因此请**避免重复追问这些 gap**——学生已系统思考过，再问会让审阅显得啰嗦。"
        "你的追问应聚焦学生当前章节文本本身的写作和报告完整性问题。\n"
    )


def generate_reviewer_questions(
    text: str,
    section: str = "methods",
    *,
    gap_analysis: Optional[List[Any]] = None,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
) -> Dict[str, Any]:
    """v3.6: 对学生初稿生成 3-5 条反问式审阅建议（哲学统一核心）。
    v3.7: gap_analysis 注入——避免重复追问学生已识别的研究空白。

    Args:
        text: 学生初稿
        section: 章节（methods/results/discussion/introduction/abstract）
        gap_analysis: 文献综述阶段识别的 GapAnalysis 列表（dict 或 dataclass）
        llm_config / requests_module: 测试注入

    Returns:
        {"questions": [...], "method": "llm" | "rule" | "skip", "raw": str,
         "gap_context_used": bool}
    """
    if not text or len(text.strip()) < 20:
        return {
            "questions": [],
            "method": "skip",
            "raw": "",
            "reason": "文本过短，建议先写至少 50 字再审阅",
            "gap_context_used": False,
        }

    section_zh = {
        "methods": "方法", "results": "结果", "discussion": "讨论",
        "introduction": "引言", "abstract": "摘要",
    }.get(section, "正文")

    sys_prompt = REVIEWER_SYSTEM_PROMPT.replace("{section_zh}", section_zh)
    gap_block = _format_gap_context(gap_analysis)
    if gap_block:
        sys_prompt = sys_prompt + gap_block
    gap_used = bool(gap_block)

    user_msg = f"以下是学生写的「{section_zh}」初稿：\n\n{text[:3000]}"

    try:
        from src.llm_gateway import LLMUnavailableError, llm_chat
        response = llm_chat(
            [{"role": "system", "content": sys_prompt},
              {"role": "user", "content": user_msg}],
            temperature=0.4,
            llm_config=llm_config,
            requests_module=requests_module,
            retries=0,
        )
        if not response.ok:
            result = _rule_reviewer_questions(text, section_zh)
            result["gap_context_used"] = gap_used
            return result

        questions = _parse_reviewer_output(response.content)
        if 2 <= len(questions) <= 8:
            return {
                "questions": questions[:5],
                "method": "llm",
                "raw": response.content,
                "gap_context_used": gap_used,
            }
    except (LLMUnavailableError, Exception):
        pass

    result = _rule_reviewer_questions(text, section_zh)
    result["gap_context_used"] = gap_used
    return result


def _parse_reviewer_output(text: str) -> List[str]:
    """解析 LLM 输出的反问列表。"""
    if not text:
        return []
    questions: List[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 去掉编号
        line = line.lstrip("0123456789.、) ").strip()
        if "？" in line or "?" in line:
            # 截到最后一个问号
            last_q = max(line.rfind("？"), line.rfind("?"))
            questions.append(line[:last_q + 1])
    return questions


def _rule_reviewer_questions(text: str, section_zh: str) -> Dict[str, Any]:
    """LLM 不可用时的规则反问（按章节模板）。"""
    APA_CHECKLIST = {
        "方法": [
            "你的样本量是多少？为什么这个样本量？",
            "数据清洗步骤是否说明？是否处理了缺失值？",
            "是否报告了量表的信度（如 Cronbach's α）？",
            "为什么选择这个统计方法而非其他？",
            "是否说明显著性水平（α=0.05）？",
        ],
        "结果": [
            "是否报告了 t/F 值 + df + p 值的完整组合？",
            "是否报告了效应量（如 Cohen's d / η²）及其大小解读？",
            "是否给出 95% 置信区间？",
            "对于不显著的结果，你如何解读（如 power 不足？）？",
            "结果是否按假设顺序逐一回应？",
        ],
        "讨论": [
            "你的效应量大小在已有研究中是大、中、小？",
            "结果与你引用的哪些研究一致或不一致？为什么？",
            "你研究的主要局限是什么——样本？测量？设计？",
            "未来研究可以从哪个方向延伸你的发现？",
            "对实务（如教学/咨询）有什么启示？",
        ],
        "引言": [
            "你的研究问题用一句话能写出来吗？",
            "已有文献最重要的 3 个发现是什么？",
            "你的研究在已有文献的哪个 gap 上？",
            "你的假设具体是什么——方向性还是非方向性？",
            "为什么这个问题对心理学/社会重要？",
        ],
    }
    questions = APA_CHECKLIST.get(section_zh, APA_CHECKLIST["方法"])[:4]
    return {
        "questions": questions,
        "method": "rule",
        "raw": "",
    }


def generate_revised_with_questions(
    text: str,
    questions_with_answers: List[Dict[str, str]],
    section: str = "methods",
    *,
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
) -> Dict[str, Any]:
    """v3.6: 基于学生原文 + 追问回答生成修订版（可选，非默认）。

    Args:
        questions_with_answers: [{"question": "...", "answer": "..."}, ...]

    Returns:
        {"revised_text": str, "method": "llm" | "skip"}
    """
    if not text or not questions_with_answers:
        return {"revised_text": text, "method": "skip"}

    section_zh = {
        "methods": "方法", "results": "结果", "discussion": "讨论",
        "introduction": "引言", "abstract": "摘要",
    }.get(section, "正文")

    sys_prompt = REVISER_SYSTEM_PROMPT.replace("{section_zh}", section_zh)
    qa_block = "\n\n".join(
        f"【审稿追问 {i + 1}】{qa.get('question', '')}\n【学生回答】{qa.get('answer', '（未回答）')}"
        for i, qa in enumerate(questions_with_answers)
    )
    user_msg = f"学生原文：\n\n{text[:3000]}\n\n---\n\n{qa_block}"

    try:
        from src.llm_gateway import LLMUnavailableError, llm_chat
        response = llm_chat(
            [{"role": "system", "content": sys_prompt},
              {"role": "user", "content": user_msg}],
            temperature=0.3,
            llm_config=llm_config,
            requests_module=requests_module,
            retries=0,
        )
        if response.ok and response.content:
            return {"revised_text": response.content.strip(), "method": "llm"}
    except (LLMUnavailableError, Exception):
        pass

    return {"revised_text": text, "method": "skip"}


def generate_revised_with_questions_stream(
    text: str,
    questions_with_answers: List[Dict[str, str]],
    *,
    section: str = "methods",
    llm_config: Optional[Dict[str, Any]] = None,
    requests_module: Any = None,
):
    """v3.7 N1: generate_revised_with_questions 的流式变体。

    yield 每一段文本片段，结束后 yield 完整结果 dict {"revised_text": str, "method": str}。
    若不支持流式则直接退化为一次性输出（一次 yield 整段 + 一次 yield dict）。
    """
    if not questions_with_answers:
        yield {"revised_text": text, "method": "skip"}
        return

    sys_prompt = (
        f"你是一位 APA7 学术论文修订专家。请基于学生的原文 + 审稿追问 + 学生回答，"
        f"产出一段修订后的「{section}」章节文字。要求：\n"
        "- 仅整合学生明确回答了的追问；学生未回答的追问留白处理\n"
        "- 不要捏造未提供的数据（如样本量、效应量、置信区间）\n"
        "- 保持学术中文风格，长度与原文相当\n"
        "- 直接输出修订后的段落（无引号、无解释、无 Markdown 标题）"
    )
    qa_block = "\n\n".join(
        f"【审稿追问 {i + 1}】{qa.get('question', '')}\n【学生回答】{qa.get('answer', '（未回答）')}"
        for i, qa in enumerate(questions_with_answers)
    )
    user_msg = f"学生原文：\n\n{text[:3000]}\n\n---\n\n{qa_block}"

    chunks: List[str] = []
    try:
        from src.llm_gateway import llm_chat_stream
        for chunk in llm_chat_stream(
            [{"role": "system", "content": sys_prompt},
              {"role": "user", "content": user_msg}],
            temperature=0.3,
            llm_config=llm_config,
            requests_module=requests_module,
        ):
            chunks.append(chunk)
            yield chunk
        full = "".join(chunks).strip()
        if full:
            yield {"revised_text": full, "method": "llm"}
            return
    except Exception:
        pass

    # 流式失败 → 退化到一次性
    result = generate_revised_with_questions(
        text, questions_with_answers, section=section,
        llm_config=llm_config, requests_module=requests_module,
    )
    yield result.get("revised_text", text)
    yield result


def polish_with_llm(
    text: str,
    section: str = "methods",
    api_key: str = "",
    base_url: str = "",
    model: str = "deepseek-chat",
    style: str = "academic",
) -> Dict:
    """
    使用 LLM 对论文段落进行学术语言润色（仅优化语言表达，不修改数据）。

    参数：
        text: 原始文本
        section: 章节类型 ("methods", "results", "discussion", "introduction")
        api_key: LLM API key
        base_url: LLM API base URL
        model: 模型名称
        style: 写作风格 — "academic" (学术严谨), "concise" (简洁), "polished" (流畅优美)

    返回：
        {
            "polished_text": str,
            "changes_summary": str,  # 修改摘要
            "original_length": int,
            "polished_length": int,
            "success": bool,
            "error": str,
        }
    """
    if not api_key:
        return {
            "polished_text": text,
            "changes_summary": "未配置API密钥，无法使用LLM润色。",
            "original_length": len(text),
            "polished_length": len(text),
            "success": False,
            "error": "no_api_key",
        }

    if not text or len(text.strip()) < 20:
        return {
            "polished_text": text,
            "changes_summary": "文本过短，无需润色。",
            "original_length": len(text),
            "polished_length": len(text),
            "success": True,
            "error": "",
        }

    section_zh = {
        "methods": "方法",
        "results": "结果",
        "discussion": "讨论",
        "introduction": "引言",
        "abstract": "摘要",
    }.get(section, "正文")

    style_instructions = {
        "academic": "保持学术严谨的写作风格，使用规范的学术用语，逻辑清晰，层次分明。",
        "concise": "尽量简洁，删除冗余表述，保留核心信息，使用精炼的学术语言。",
        "polished": "在保证学术严谨的前提下，使语言更加流畅优美，增强可读性。",
    }
    style_hint = style_instructions.get(style, style_instructions["academic"])

    system_prompt = (
        "你是一位心理学学术期刊的资深编辑，擅长中文学术论文的语言润色。"
        "你的任务是优化以下论文{section_zh}部分的语言表达，使其符合APA 7th写作规范。"
        "请严格遵守以下原则：\n"
        "1. 仅优化语言表达（措辞、句式、连贯性），绝对不修改任何数据、数值、统计结果\n"
        "2. 保持原文的学术信息和逻辑结构不变\n"
        "3. 避免口语化表达，使用规范的学术用语\n"
        "4. 确保APA格式规范（如p值不带前导零、效应量保留两位小数等）\n"
        "5. 中文表达应准确、简洁、通顺\n"
        "6. {style_hint}\n\n"
        "请输出JSON格式：\n"
        '{{"polished_text": "润色后的完整文本", "changes": ["主要修改点1", "主要修改点2", ...]}}\n'
        "只返回JSON，不要加任何解释文字。"
    ).replace("{section_zh}", section_zh).replace("{style_hint}", style_hint)

    user_prompt = f"请润色以下论文「{section_zh}」部分：\n\n{text}"

    try:
        import urllib.request

        api_data = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": min(4096, int(len(text) * 1.5)),
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=api_data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        content = data["choices"][0]["message"]["content"]
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(content[json_start:json_end])
        else:
            result = {"polished_text": text, "changes": ["LLM返回格式异常，保持原文"]}

        polished = result.get("polished_text", text)
        changes = result.get("changes", [])

        return {
            "polished_text": polished,
            "changes_summary": "；".join(changes) if changes else "无明显修改",
            "original_length": len(text),
            "polished_length": len(polished),
            "success": True,
            "error": "",
        }

    except Exception as e:
        return {
            "polished_text": text,
            "changes_summary": f"LLM润色失败: {str(e)[:100]}",
            "original_length": len(text),
            "polished_length": len(text),
            "success": False,
            "error": str(e)[:200],
        }


def polish_paper_sections(
    sections: Dict[str, str],
    sections_to_polish: List[str] = None,
    api_key: str = "",
    base_url: str = "",
    model: str = "deepseek-chat",
    style: str = "academic",
) -> Dict:
    """
    对论文多个章节进行批量润色。

    参数：
        sections: {"methods": "...", "results": "...", "discussion": "..."}
        sections_to_polish: 需要润色的章节列表，默认 ["methods", "results"]
        api_key: LLM API key
        base_url: LLM API base URL
        model: 模型名称
        style: 写作风格

    返回：
        {
            "polished_sections": {"methods": "...", "results": "..."},
            "summaries": {"methods": "修改摘要", ...},
            "total_changes": 修改总数,
        }
    """
    if sections_to_polish is None:
        sections_to_polish = ["methods", "results"]

    polished_sections = dict(sections)
    summaries = {}
    total_changes = 0

    for section_name in sections_to_polish:
        if section_name not in sections:
            continue

        original_text = sections[section_name]
        result = polish_with_llm(
            text=original_text,
            section=section_name,
            api_key=api_key,
            base_url=base_url,
            model=model,
            style=style,
        )

        polished_sections[section_name] = result["polished_text"]
        summaries[section_name] = result["changes_summary"]
        if result["success"]:
            change_count = len(result["changes_summary"].split("；"))
            total_changes += change_count

    return {
        "polished_sections": polished_sections,
        "summaries": summaries,
        "total_changes": total_changes,
    }
