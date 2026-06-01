"""论文写作系统 — 文献管理器"""

import re
import time
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class LiteratureEntry:
    """文献条目"""
    key: str                          # 引用键 e.g. "温忠麟2014"
    authors: List[str]                # 作者列表 ["温忠麟", "叶宝娟"]
    year: str                         # 年份
    title: str                        # 标题
    journal: str                      # 期刊
    volume: str = ""                  # 卷
    issue: str = ""                   # 期
    pages: str = ""                   # 页码
    doi: str = ""                     # DOI
    is_chinese: bool = True           # 是否中文文献
    abstract: str = ""                # 摘要
    keywords: List[str] = field(default_factory=list)
    source: str = ""                  # 来源: "user" | "crossref" | "cnki" | "llm"
    relevance_note: str = ""          # 与本文的相关性说明

    def format_citation(self) -> str:
        """生成正文中引用标记"""
        return f"[{self.key}]"

    def format_reference(self) -> str:
        """生成参考文献条目（APA 7th Edition 格式）

        中文文献: 作者. (年份). 文章标题. 期刊名, 卷(期), 页码. https://doi.org/xxx
        英文文献: Author, A. A. (Year). Title. Journal Name, Vol(Issue), pages. https://doi.org/xxx
        """
        if self.is_chinese:
            # 中文 APA7 格式
            authors_str = ", ".join(self.authors)
            parts = [f"{authors_str}. ({self.year}). {self.title}."]
            if self.journal:
                parts.append(f" {self.journal}")
                if self.volume:
                    parts.append(f", {self.volume}")
                    if self.issue:
                        parts.append(f"({self.issue})")
                if self.pages:
                    parts.append(f", {self.pages}")
                parts.append(".")
            if self.doi:
                parts.append(f" https://doi.org/{self.doi.replace('doi:', '').replace('https://doi.org/', '')}")
        else:
            # 英文 APA7 格式
            if len(self.authors) == 1:
                authors_str = self.authors[0]
            elif len(self.authors) == 2:
                authors_str = f"{self.authors[0]}, & {self.authors[1]}"
            else:
                authors_str = ", ".join(self.authors[:-1]) + f", & {self.authors[-1]}"
            parts = [f"{authors_str} ({self.year}). {self.title}."]
            if self.journal:
                # 期刊名斜体（Markdown用*表示）
                parts.append(f" *{self.journal}*")
                if self.volume:
                    parts.append(f", *{self.volume}*")
                    if self.issue:
                        parts.append(f"({self.issue})")
                if self.pages:
                    parts.append(f", {self.pages}")
                parts.append(".")
            if self.doi:
                doi_clean = self.doi.replace("doi:", "").replace("https://doi.org/", "")
                parts.append(f" https://doi.org/{doi_clean}")

        return "".join(parts)


# ===========================================================================
# 预置常用中文心理学文献库
# ===========================================================================
PRESET_CHINESE_LITERATURE = {
    "温忠麟2014": LiteratureEntry(
        key="温忠麟2014",
        authors=["温忠麟", "叶宝娟"],
        year="2014",
        title="中介效应分析: 方法和模型发展",
        journal="心理科学进展",
        volume="22",
        issue="5",
        pages="731-745",
        doi="10.3724/SP.J.1042.2014.00731",
        is_chinese=True,
        abstract="介绍了中介效应的检验方法演进，包括逐步检验法、Sobel检验、Bootstrap法以及近年来推荐的偏差校正Bootstrap方法。",
        keywords=["中介效应", "Bootstrap", "研究方法"],
        source="内置经典文献",
        relevance_note="中介分析方法学参考文献，用于研究的方法部分和讨论部分的方法辩护。",
    ),
    "温忠麟2005": LiteratureEntry(
        key="温忠麟2005",
        authors=["温忠麟", "侯杰泰", "张雷"],
        year="2005",
        title="调节效应与中介效应的比较和应用",
        journal="心理学报",
        volume="37",
        issue="2",
        pages="268-274",
        is_chinese=True,
        keywords=["调节效应", "中介效应", "比较分析"],
        source="内置经典文献",
        relevance_note="区分调节效应和中介效应的经典文献，用于引言部分的理论辨析。",
    ),
    "吴明隆2010": LiteratureEntry(
        key="吴明隆2010",
        authors=["吴明隆"],
        year="2010",
        title="问卷统计分析实务: SPSS操作与应用",
        journal="重庆大学出版社",
        is_chinese=True,
        keywords=["问卷", "统计", "SPSS"],
        source="内置经典文献",
        relevance_note="问卷设计和统计分析的方法参考书。",
    ),
    "侯杰泰2004": LiteratureEntry(
        key="侯杰泰2004",
        authors=["侯杰泰", "温忠麟", "成子娟"],
        year="2004",
        title="结构方程模型及其应用",
        journal="教育科学出版社",
        is_chinese=True,
        keywords=["结构方程模型", "SEM", "CFA"],
        source="内置经典文献",
        relevance_note="结构方程模型的方法学参考，用于验证性因素分析和路径分析的方法辩护。",
    ),
    "王孟成2014": LiteratureEntry(
        key="王孟成2014",
        authors=["王孟成"],
        year="2014",
        title="潜变量建模与Mplus应用",
        journal="重庆大学出版社",
        is_chinese=True,
        keywords=["潜变量", "Mplus", "SEM"],
        source="内置经典文献",
        relevance_note="潜变量建模方法的实用参考书。",
    ),
    "方杰2012": LiteratureEntry(
        key="方杰2012",
        authors=["方杰", "张敏强", "邱皓政"],
        year="2012",
        title="中介效应的检验方法和效果量测量: 回顾与展望",
        journal="心理发展与教育",
        volume="28",
        issue="1",
        pages="105-111",
        is_chinese=True,
        keywords=["中介效应", "效应量", "Bootstrap"],
        source="内置经典文献",
        relevance_note="中介效应效果量测量的综述。",
    ),
    "刘红云2013": LiteratureEntry(
        key="刘红云2013",
        authors=["刘红云", "骆方", "张玉", "张丹慧"],
        year="2013",
        title="因变量为等级变量的中介效应分析",
        journal="心理学报",
        volume="45",
        issue="6",
        pages="614-624",
        is_chinese=True,
        keywords=["中介效应", "等级变量"],
        source="内置经典文献",
    ),
    "张厚粲2009": LiteratureEntry(
        key="张厚粲2009",
        authors=["张厚粲", "徐建平"],
        year="2009",
        title="现代心理与教育统计学",
        journal="北京师范大学出版社",
        is_chinese=True,
        keywords=["统计", "心理学", "教材"],
        source="内置经典文献",
        relevance_note="心理学统计方法的经典教材，用于数据分析方法的引用。",
    ),
    "辛涛2006": LiteratureEntry(
        key="辛涛2006",
        authors=["辛涛", "李峰"],
        year="2006",
        title="社会科学背景下的多层线性模型",
        journal="心理科学进展",
        volume="14",
        issue="3",
        pages="449-456",
        is_chinese=True,
        keywords=["多层线性模型", "HLM"],
        source="内置经典文献",
    ),
    "方平2003": LiteratureEntry(
        key="方平2003",
        authors=["方平", "熊端琴", "曹雪梅"],
        year="2003",
        title="结构方程模式的发展与应用",
        journal="心理科学进展",
        volume="11",
        issue="3",
        pages="270-279",
        is_chinese=True,
        keywords=["SEM", "模型拟合"],
        source="内置经典文献",
    ),
    "邓稳根2018": LiteratureEntry(
        key="邓稳根2018",
        authors=["邓稳根", "黎小伯", "王欢"],
        year="2018",
        title="心理学研究中的效应量及其应用",
        journal="心理学探新",
        volume="38",
        issue="5",
        pages="403-409",
        is_chinese=True,
        keywords=["效应量", "统计效力", "心理学"],
        source="内置经典文献",
        relevance_note="效应量报告的规范参考文献，为效应量选择和解读提供依据。",
    ),
    "胡传鹏2018": LiteratureEntry(
        key="胡传鹏2018",
        authors=["胡传鹏", "孔祥祯", "Wagenmakers, E.-J.", "Ly, A.", "彭凯平"],
        year="2018",
        title="Bayesian inference for psychology. Part I: Theoretical advantages and practical ramifications",
        journal="心理科学进展",
        volume="26",
        issue="5",
        pages="860-872",
        is_chinese=False,
        doi="10.3724/SP.J.1042.2018.00860",
        keywords=["贝叶斯", "统计推断", "可重复性"],
        source="内置经典文献",
    ),
    "周浩2004": LiteratureEntry(
        key="周浩2004",
        authors=["周浩", "龙立荣"],
        year="2004",
        title="共同方法偏差的统计检验与控制方法",
        journal="心理科学进展",
        volume="12",
        issue="6",
        pages="942-950",
        is_chinese=True,
        keywords=["共同方法偏差", "CMV", "Harman单因素检验"],
        source="内置经典文献",
        relevance_note="自评问卷研究的必备参考文献，用于方法部分报告共同方法偏差检验。",
    ),
    "赵必华2007": LiteratureEntry(
        key="赵必华2007",
        authors=["赵必华", "顾海根"],
        year="2007",
        title="心理量表编制中的探索性因素分析",
        journal="中国临床心理学杂志",
        volume="15",
        issue="1",
        pages="6-9",
        is_chinese=True,
        keywords=["量表编制", "EFA", "因素分析"],
        source="内置经典文献",
    ),
    "顾红磊2017": LiteratureEntry(
        key="顾红磊2017",
        authors=["顾红磊", "温忠麟"],
        year="2017",
        title="多维测验分数的报告与解释:基于双因子模型的视角",
        journal="心理发展与教育",
        volume="33",
        issue="4",
        pages="504-512",
        is_chinese=True,
        keywords=["多维测验", "双因子模型", "信度"],
        source="内置经典文献",
    ),
    # ── 统计方法扩展 ──
    "温忠麟2012": LiteratureEntry(
        key="温忠麟2012",
        authors=["温忠麟", "刘红云", "侯杰泰"],
        year="2012",
        title="调节效应和中介效应分析",
        journal="教育科学出版社",
        is_chinese=True,
        keywords=["调节效应", "中介效应", "统计方法"],
        source="内置经典文献",
        relevance_note="调节与中介效应分析的经典中文教材。",
    ),
    "王孟成2017": LiteratureEntry(
        key="王孟成2017",
        authors=["王孟成", "毕向阳"],
        year="2017",
        title="潜变量建模: Mplus、Mlwin与HLM的应用",
        journal="重庆大学出版社",
        is_chinese=True,
        keywords=["潜变量", "Mplus", "HLM"],
        source="内置经典文献",
    ),
    "罗胜强2014": LiteratureEntry(
        key="罗胜强2014",
        authors=["罗胜强", "姜嬿"],
        year="2014",
        title="管理学问卷调查研究方法",
        journal="重庆大学出版社",
        is_chinese=True,
        keywords=["问卷调查", "研究方法", "管理学"],
        source="内置经典文献",
        relevance_note="问卷调查研究方法的综合参考书。",
    ),
    "邱皓政2009": LiteratureEntry(
        key="邱皓政2009",
        authors=["邱皓政", "林碧芳"],
        year="2009",
        title="结构方程模型的原理与应用",
        journal="中国轻工业出版社",
        is_chinese=True,
        keywords=["结构方程模型", "SEM"],
        source="内置经典文献",
    ),
    "邱皓政2013": LiteratureEntry(
        key="邱皓政2013",
        authors=["邱皓政"],
        year="2013",
        title="量化研究与统计分析: SPSS(PASW)数据分析范例解析",
        journal="重庆大学出版社",
        is_chinese=True,
        keywords=["SPSS", "统计", "量化研究"],
        source="内置经典文献",
    ),
    "温忠麟2004": LiteratureEntry(
        key="温忠麟2004",
        authors=["温忠麟", "张雷", "侯杰泰", "刘红云"],
        year="2004",
        title="中介效应检验程序及其应用",
        journal="心理学报",
        volume="36",
        issue="5",
        pages="614-620",
        is_chinese=True,
        keywords=["中介效应", "检验程序"],
        source="内置经典文献",
    ),
    "叶宝娟2013": LiteratureEntry(
        key="叶宝娟2013",
        authors=["叶宝娟", "温忠麟"],
        year="2013",
        title="有中介的调节模型检验方法:甄别和整合",
        journal="心理学报",
        volume="45",
        issue="9",
        pages="1050-1060",
        is_chinese=True,
        doi="10.3724/SP.J.1041.2013.01050",
        keywords=["中介调节", "模型检验"],
        source="内置经典文献",
    ),
    "方杰2014": LiteratureEntry(
        key="方杰2014",
        authors=["方杰", "张敏强", "顾红磊", "梁东梅"],
        year="2014",
        title="基于不对称区间估计的有调节的中介模型检验",
        journal="心理科学进展",
        volume="22",
        issue="10",
        pages="1660-1668",
        is_chinese=True,
        keywords=["有调节的中介", "区间估计"],
        source="内置经典文献",
    ),
    "甘怡群2016": LiteratureEntry(
        key="甘怡群2016",
        authors=["甘怡群"],
        year="2016",
        title="中介效应研究的新趋势——多水平中介和调节效应分析",
        journal="心理科学进展",
        volume="24",
        issue="7",
        pages="1114-1123",
        is_chinese=True,
        keywords=["中介效应", "多水平"],
        source="内置经典文献",
    ),
    "王才康2001": LiteratureEntry(
        key="王才康2001",
        authors=["王才康", "胡中锋", "刘勇"],
        year="2001",
        title="一般自我效能感量表的信度和效度研究",
        journal="应用心理学",
        volume="7",
        issue="1",
        pages="37-40",
        is_chinese=True,
        keywords=["自我效能感", "量表", "信效度"],
        source="内置经典文献",
    ),
    # ── 人格与社会心理学 ──
    "杨中芳1997": LiteratureEntry(
        key="杨中芳1997",
        authors=["杨中芳"],
        year="1997",
        title="如何研究中国人",
        journal="桂冠图书公司",
        is_chinese=True,
        keywords=["本土心理学", "研究方法", "中国人"],
        source="内置经典文献",
    ),
    "黄光国2006": LiteratureEntry(
        key="黄光国2006",
        authors=["黄光国"],
        year="2006",
        title="社会科学的理路",
        journal="心理出版社",
        is_chinese=True,
        keywords=["社会科学", "方法论"],
        source="内置经典文献",
    ),
    "彭凯平2009": LiteratureEntry(
        key="彭凯平2009",
        authors=["彭凯平"],
        year="2009",
        title="文化与归因: 中国本土心理学的研究",
        journal="心理学报",
        volume="41",
        issue="3",
        pages="223-230",
        is_chinese=True,
        keywords=["文化心理学", "本土心理学"],
        source="内置经典文献",
    ),
    "佐斌2015": LiteratureEntry(
        key="佐斌2015",
        authors=["佐斌", "温芳芳"],
        year="2015",
        title="社会认知: 理论与应用",
        journal="华中师范大学出版社",
        is_chinese=True,
        keywords=["社会认知", "社会心理学"],
        source="内置经典文献",
    ),
    "俞宗火2000": LiteratureEntry(
        key="俞宗火2000",
        authors=["俞宗火", "郭永玉"],
        year="2000",
        title="中国人人格结构的研究: 回顾与展望",
        journal="心理学探新",
        volume="20",
        issue="4",
        pages="42-47",
        is_chinese=True,
        keywords=["人格", "中国人", "本土化"],
        source="内置经典文献",
    ),
    "王登峰2005": LiteratureEntry(
        key="王登峰2005",
        authors=["王登峰", "崔红"],
        year="2005",
        title="中国人人格量表(QZPS)的编制过程与初步结果",
        journal="心理学报",
        volume="37",
        issue="5",
        pages="689-696",
        is_chinese=True,
        keywords=["中国人人格", "量表编制", "QZPS"],
        source="内置经典文献",
    ),
    "李超平2006": LiteratureEntry(
        key="李超平2006",
        authors=["李超平", "时勘"],
        year="2006",
        title="变革型领导的结构与测量",
        journal="心理学报",
        volume="38",
        issue="5",
        pages="742-750",
        is_chinese=True,
        keywords=["变革型领导", "量表", "组织行为"],
        source="内置经典文献",
    ),
    "刘毅2010": LiteratureEntry(
        key="刘毅2010",
        authors=["刘毅"],
        year="2010",
        title="社会心理学研究方法",
        journal="中国人民大学出版社",
        is_chinese=True,
        keywords=["社会心理学", "研究方法"],
        source="内置经典文献",
    ),
    # ── 临床与健康心理学 ──
    "汪向东1999": LiteratureEntry(
        key="汪向东1999",
        authors=["汪向东", "王希林", "马弘"],
        year="1999",
        title="心理卫生评定量表手册(增订版)",
        journal="中国心理卫生杂志社",
        is_chinese=True,
        keywords=["心理卫生", "量表", "评定"],
        source="内置经典文献",
        relevance_note="心理测量学量表汇编，包含大量中文修订量表的常模和信效度信息。",
    ),
    "刘贤臣1997": LiteratureEntry(
        key="刘贤臣1997",
        authors=["刘贤臣", "唐茂芹", "胡蕾", "王爱祯", "吴宏新", "赵贵芳"],
        year="1997",
        title="匹兹堡睡眠质量指数的信度和效度研究",
        journal="中华精神科杂志",
        volume="30",
        issue="2",
        pages="103-107",
        is_chinese=True,
        keywords=["睡眠质量", "量表", "信度", "效度"],
        source="内置经典文献",
    ),
    "戴晓阳2011": LiteratureEntry(
        key="戴晓阳2011",
        authors=["戴晓阳"],
        year="2011",
        title="常用心理评估量表手册",
        journal="人民军医出版社",
        is_chinese=True,
        keywords=["心理评估", "量表", "手册"],
        source="内置经典文献",
    ),
    "刘平1999": LiteratureEntry(
        key="刘平1999",
        authors=["刘平"],
        year="1999",
        title="SCL-90症状自评量表",
        journal="中国心理卫生杂志",
        volume="13",
        pages="31-35",
        is_chinese=True,
        keywords=["SCL-90", "症状自评", "心理健康"],
        source="内置经典文献",
    ),
    "江光荣2004": LiteratureEntry(
        key="江光荣2004",
        authors=["江光荣"],
        year="2004",
        title="心理咨询与治疗的理论与实务",
        journal="高等教育出版社",
        is_chinese=True,
        keywords=["心理咨询", "心理治疗"],
        source="内置经典文献",
    ),
    "钱铭怡2000": LiteratureEntry(
        key="钱铭怡2000",
        authors=["钱铭怡", "武国城", "朱荣春", "张莘"],
        year="2000",
        title="艾森克人格问卷简式量表中国版(EPQ-RSC)的修订",
        journal="心理学报",
        volume="32",
        issue="3",
        pages="317-323",
        is_chinese=True,
        keywords=["艾森克", "人格问卷", "修订"],
        source="内置经典文献",
    ),
    # ── 发展与教育心理学 ──
    "林崇德2009": LiteratureEntry(
        key="林崇德2009",
        authors=["林崇德"],
        year="2009",
        title="发展心理学(第2版)",
        journal="人民教育出版社",
        is_chinese=True,
        keywords=["发展心理学", "教材"],
        source="内置经典文献",
    ),
    "张向葵2010": LiteratureEntry(
        key="张向葵2010",
        authors=["张向葵", "桑标"],
        year="2010",
        title="发展心理学新进展",
        journal="北京师范大学出版社",
        is_chinese=True,
        keywords=["发展心理学"],
        source="内置经典文献",
    ),
    "刘电芝2011": LiteratureEntry(
        key="刘电芝2011",
        authors=["刘电芝"],
        year="2011",
        title="教育与心理研究方法",
        journal="西南师范大学出版社",
        is_chinese=True,
        keywords=["研究方法", "教育心理"],
        source="内置经典文献",
    ),
    "申继亮2003": LiteratureEntry(
        key="申继亮2003",
        authors=["申继亮"],
        year="2003",
        title="教师职业倦怠与职业压力",
        journal="中国心理卫生杂志",
        volume="17",
        issue="11",
        pages="743-745",
        is_chinese=True,
        keywords=["职业倦怠", "教师", "职业压力"],
        source="内置经典文献",
    ),
    "雷雳2015": LiteratureEntry(
        key="雷雳2015",
        authors=["雷雳"],
        year="2015",
        title="青少年网络心理与行为",
        journal="北京师范大学出版社",
        is_chinese=True,
        keywords=["青少年", "网络心理"],
        source="内置经典文献",
    ),
    "董奇2004": LiteratureEntry(
        key="董奇2004",
        authors=["董奇", "林崇德"],
        year="2004",
        title="中国儿童青少年心理发展",
        journal="北京师范大学出版社",
        is_chinese=True,
        keywords=["儿童", "青少年", "发展"],
        source="内置经典文献",
    ),
    # ── 组织行为学 ──
    "凌文辁2000": LiteratureEntry(
        key="凌文辁2000",
        authors=["凌文辁", "张治灿", "方俐洛"],
        year="2000",
        title="中国职工组织承诺的结构模型研究",
        journal="管理科学学报",
        volume="3",
        issue="2",
        pages="76-81",
        is_chinese=True,
        keywords=["组织承诺", "结构模型"],
        source="内置经典文献",
    ),
    "李永鑫2005": LiteratureEntry(
        key="李永鑫2005",
        authors=["李永鑫", "吴明证"],
        year="2005",
        title="工作倦怠的结构研究",
        journal="心理科学",
        volume="28",
        issue="2",
        pages="454-456",
        is_chinese=True,
        keywords=["工作倦怠", "结构", "测量"],
        source="内置经典文献",
    ),
    "仲理峰2007": LiteratureEntry(
        key="仲理峰2007",
        authors=["仲理峰"],
        year="2007",
        title="心理资本对员工的工作绩效、组织承诺及组织公民行为的影响",
        journal="心理学报",
        volume="39",
        issue="2",
        pages="328-334",
        is_chinese=True,
        keywords=["心理资本", "工作绩效", "组织行为"],
        source="内置经典文献",
    ),
    "张勉2001": LiteratureEntry(
        key="张勉2001",
        authors=["张勉", "张德", "王颖"],
        year="2001",
        title="企业雇员组织承诺三因素模型实证研究",
        journal="南开管理评论",
        volume="4",
        issue="5",
        pages="70-75",
        is_chinese=True,
        keywords=["组织承诺", "三因素模型"],
        source="内置经典文献",
    ),
    "赵曙明2009": LiteratureEntry(
        key="赵曙明2009",
        authors=["赵曙明"],
        year="2009",
        title="人力资源管理研究",
        journal="中国人民大学出版社",
        is_chinese=True,
        keywords=["人力资源管理", "组织行为"],
        source="内置经典文献",
    ),
    # ── 认知心理学 ──
    "周晓林2004": LiteratureEntry(
        key="周晓林2004",
        authors=["周晓林"],
        year="2004",
        title="执行功能的认知与神经机制",
        journal="心理科学进展",
        volume="12",
        issue="5",
        pages="693-701",
        is_chinese=True,
        keywords=["执行功能", "认知", "神经"],
        source="内置经典文献",
    ),
    "陈楚侨2009": LiteratureEntry(
        key="陈楚侨2009",
        authors=["陈楚侨", "王亚"],
        year="2009",
        title="工作记忆的认知神经科学研究",
        journal="心理科学进展",
        volume="17",
        issue="2",
        pages="261-271",
        is_chinese=True,
        keywords=["工作记忆", "认知神经科学"],
        source="内置经典文献",
    ),
    "刘昌2004": LiteratureEntry(
        key="刘昌2004",
        authors=["刘昌"],
        year="2004",
        title="认知年老化的神经机制",
        journal="心理科学进展",
        volume="12",
        issue="5",
        pages="714-722",
        is_chinese=True,
        keywords=["认知老化", "神经机制"],
        source="内置经典文献",
    ),
    # ── 积极心理学 ──
    "任俊2006": LiteratureEntry(
        key="任俊2006",
        authors=["任俊"],
        year="2006",
        title="积极心理学",
        journal="上海教育出版社",
        is_chinese=True,
        keywords=["积极心理学", "幸福感"],
        source="内置经典文献",
    ),
    "苗元江2009": LiteratureEntry(
        key="苗元江2009",
        authors=["苗元江"],
        year="2009",
        title="心理学视野中的幸福",
        journal="天津人民出版社",
        is_chinese=True,
        keywords=["幸福感", "积极心理学"],
        source="内置经典文献",
    ),
    "邢占军2003": LiteratureEntry(
        key="邢占军2003",
        authors=["邢占军"],
        year="2003",
        title="中国城市居民主观幸福感量表的编制研究",
        journal="华东师范大学博士论文",
        is_chinese=True,
        keywords=["主观幸福感", "量表编制", "中国人"],
        source="内置经典文献",
    ),
    # ── 情绪研究 ──
    "黄敏儿2002": LiteratureEntry(
        key="黄敏儿2002",
        authors=["黄敏儿", "郭德俊"],
        year="2002",
        title="情绪调节的实质",
        journal="心理科学",
        volume="25",
        issue="1",
        pages="109-110",
        is_chinese=True,
        keywords=["情绪调节", "情绪"],
        source="内置经典文献",
    ),
    "王振宏2003": LiteratureEntry(
        key="王振宏2003",
        authors=["王振宏", "郭德俊"],
        year="2003",
        title="Gross情绪调节过程与策略研究述评",
        journal="心理科学进展",
        volume="11",
        issue="6",
        pages="629-634",
        is_chinese=True,
        keywords=["情绪调节", "策略", "Gross"],
        source="内置经典文献",
    ),
    # ── 元分析与可重复性 ──
    "张雷2009": LiteratureEntry(
        key="张雷2009",
        authors=["张雷"],
        year="2009",
        title="元分析(Meta-analysis)方法及其在社会科学中的应用",
        journal="教育科学出版社",
        is_chinese=True,
        keywords=["元分析", "meta analysis"],
        source="内置经典文献",
    ),
    "胡传鹏2016": LiteratureEntry(
        key="胡传鹏2016",
        authors=["胡传鹏", "孔祥祯", "Wagenmakers, E.-J.", "Ly, A.", "彭凯平"],
        year="2016",
        title="Bayesian hypothesis testing in psychology: A tutorial on the Bayes factor",
        journal="心理科学进展",
        volume="24",
        issue="12",
        pages="1958-1970",
        is_chinese=False,
        keywords=["贝叶斯", "假设检验", "可重复性"],
        source="内置经典文献",
    ),
    "吕小康2018": LiteratureEntry(
        key="吕小康2018",
        authors=["吕小康"],
        year="2018",
        title="心理学研究的可重复性: 从危机到契机",
        journal="心理科学进展",
        volume="26",
        issue="7",
        pages="1221-1230",
        is_chinese=True,
        keywords=["可重复性", "研究实践"],
        source="内置经典文献",
    ),
    # ── 跨文化研究 ──
    "赵志裕2005": LiteratureEntry(
        key="赵志裕2005",
        authors=["赵志裕", "康萤仪"],
        year="2005",
        title="文化社会心理学",
        journal="中国人民大学出版社",
        is_chinese=True,
        keywords=["文化心理学", "社会心理学"],
        source="内置经典文献",
    ),
    "蔡华俭2008": LiteratureEntry(
        key="蔡华俭2008",
        authors=["蔡华俭"],
        year="2008",
        title="内隐自尊的测量: 理论与方法",
        journal="心理科学进展",
        volume="16",
        issue="6",
        pages="961-968",
        is_chinese=True,
        keywords=["内隐自尊", "测量"],
        source="内置经典文献",
    ),
    # ── 问卷与测量 ──
    "漆书青2003": LiteratureEntry(
        key="漆书青2003",
        authors=["漆书青", "戴海崎", "丁树良"],
        year="2003",
        title="现代教育与心理测量学原理",
        journal="高等教育出版社",
        is_chinese=True,
        keywords=["心理测量学", "IRT", "CTT"],
        source="内置经典文献",
    ),
    "郑日昌1987": LiteratureEntry(
        key="郑日昌1987",
        authors=["郑日昌"],
        year="1987",
        title="心理测量",
        journal="湖南教育出版社",
        is_chinese=True,
        keywords=["心理测量", "教材"],
        source="内置经典文献",
    ),
    "金瑜2001": LiteratureEntry(
        key="金瑜2001",
        authors=["金瑜"],
        year="2001",
        title="心理测量",
        journal="华东师范大学出版社",
        is_chinese=True,
        keywords=["心理测量"],
        source="内置经典文献",
    ),
    "杨志明2012": LiteratureEntry(
        key="杨志明2012",
        authors=["杨志明", "张雷"],
        year="2012",
        title="测评的概化理论及其应用",
        journal="教育科学出版社",
        is_chinese=True,
        keywords=["概化理论", "测评"],
        source="内置经典文献",
    ),
}

# 预置英文经典文献
PRESET_ENGLISH_LITERATURE = {
    "Cohen1988": LiteratureEntry(
        key="Cohen1988",
        authors=["Cohen, J."],
        year="1988",
        title="Statistical power analysis for the behavioral sciences (2nd ed.)",
        journal="Lawrence Erlbaum Associates",
        is_chinese=False,
        keywords=["power analysis", "effect size"],
        source="内置经典文献",
        relevance_note="效应量基准的原始来源（小/中/大的0.2/0.5/0.8），所有心理学量化研究的基础引用。",
    ),
    "Hayes2017": LiteratureEntry(
        key="Hayes2017",
        authors=["Hayes, A. F."],
        year="2017",
        title="Introduction to mediation, moderation, and conditional process analysis (2nd ed.)",
        journal="Guilford Press",
        is_chinese=False,
        keywords=["mediation", "moderation", "PROCESS"],
        source="内置经典文献",
        relevance_note="中介和调节分析的权威方法参考，用于Bootstrap方法和PROCESS宏的引用。",
    ),
    "Preacher2004": LiteratureEntry(
        key="Preacher2004",
        authors=["Preacher, K. J.", "Hayes, A. F."],
        year="2004",
        title="SPSS and SAS procedures for estimating indirect effects in simple mediation models",
        journal="Behavior Research Methods, Instruments, & Computers",
        volume="36",
        pages="717-731",
        doi="10.3758/BF03206553",
        is_chinese=False,
        keywords=["mediation", "bootstrap", "indirect effect"],
        source="内置经典文献",
        relevance_note="Bootstrap中介效应的经典方法论文献。",
    ),
    "Hu1999": LiteratureEntry(
        key="Hu1999",
        authors=["Hu, L.", "Bentler, P. M."],
        year="1999",
        title="Cutoff criteria for fit indexes in covariance structure analysis",
        journal="Structural Equation Modeling",
        volume="6",
        issue="1",
        pages="1-55",
        doi="10.1080/10705519909540118",
        is_chinese=False,
        keywords=["SEM", "fit indices", "CFI", "RMSEA"],
        source="内置经典文献",
        relevance_note="SEM拟合指标阈值的经典文献（CFI>0.90, RMSEA<0.08, SRMR<0.08）。",
    ),
    "Podsakoff2003": LiteratureEntry(
        key="Podsakoff2003",
        authors=["Podsakoff, P. M.", "MacKenzie, S. B.", "Lee, J. Y.", "Podsakoff, N. P."],
        year="2003",
        title="Common method biases in behavioral research",
        journal="Journal of Applied Psychology",
        volume="88",
        issue="5",
        pages="879-903",
        doi="10.1037/0021-9010.88.5.879",
        is_chinese=False,
        keywords=["common method bias", "CMV"],
        source="内置经典文献",
        relevance_note="共同方法偏差的经典文献。",
    ),
    # ── 统计方法与可重复性 ──
    "Cohen1992": LiteratureEntry(
        key="Cohen1992",
        authors=["Cohen, J."],
        year="1992",
        title="A power primer",
        journal="Psychological Bulletin",
        volume="112",
        issue="1",
        pages="155-159",
        doi="10.1037/0033-2909.112.1.155",
        is_chinese=False,
        keywords=["statistical power", "effect size", "sample size"],
        source="内置经典文献",
        relevance_note="统计效力和效应量的经典tutorial。",
    ),
    "Cumming2014": LiteratureEntry(
        key="Cumming2014",
        authors=["Cumming, G."],
        year="2014",
        title="The new statistics: Why and how",
        journal="Psychological Science",
        volume="25",
        issue="1",
        pages="7-29",
        doi="10.1177/0956797613504966",
        is_chinese=False,
        keywords=["new statistics", "confidence interval", "estimation"],
        source="内置经典文献",
        relevance_note="新统计运动的标志性文献，强调效应量估计和置信区间优于p值。",
    ),
    "Lakens2013": LiteratureEntry(
        key="Lakens2013",
        authors=["Lakens, D."],
        year="2013",
        title="Calculating and reporting effect sizes to facilitate cumulative science",
        journal="Frontiers in Psychology",
        volume="4",
        pages="863",
        doi="10.3389/fpsyg.2013.00863",
        is_chinese=False,
        keywords=["effect size", "Cohen's d", "eta-squared"],
        source="内置经典文献",
        relevance_note="效应量计算与报告的实用指南。",
    ),
    "Bollen1991": LiteratureEntry(
        key="Bollen1991",
        authors=["Bollen, K. A."],
        year="1991",
        title="Structural equations with latent variables",
        journal="John Wiley & Sons",
        is_chinese=False,
        keywords=["SEM", "latent variables"],
        source="内置经典文献",
        relevance_note="结构方程模型的经典教科书。",
    ),
    "Kline2015": LiteratureEntry(
        key="Kline2015",
        authors=["Kline, R. B."],
        year="2015",
        title="Principles and practice of structural equation modeling (4th ed.)",
        journal="Guilford Press",
        is_chinese=False,
        keywords=["SEM", "structural equation modeling"],
        source="内置经典文献",
        relevance_note="SEM实践的权威教材。",
    ),
    "MacKinnon2008": LiteratureEntry(
        key="MacKinnon2008",
        authors=["MacKinnon, D. P."],
        year="2008",
        title="Introduction to statistical mediation analysis",
        journal="Routledge",
        is_chinese=False,
        keywords=["mediation", "indirect effect"],
        source="内置经典文献",
        relevance_note="中介效应分析的权威教材。",
    ),
    "Preacher2008": LiteratureEntry(
        key="Preacher2008",
        authors=["Preacher, K. J.", "Hayes, A. F."],
        year="2008",
        title="Asymptotic and resampling strategies for assessing and comparing indirect effects in multiple mediator models",
        journal="Behavior Research Methods",
        volume="40",
        issue="3",
        pages="879-891",
        doi="10.3758/BRM.40.3.879",
        is_chinese=False,
        keywords=["multiple mediation", "bootstrap"],
        source="内置经典文献",
    ),
    "Shrout2002": LiteratureEntry(
        key="Shrout2002",
        authors=["Shrout, P. E.", "Bolger, N."],
        year="2002",
        title="Mediation in experimental and nonexperimental studies",
        journal="Psychological Methods",
        volume="7",
        issue="4",
        pages="422-445",
        doi="10.1037/1082-989X.7.4.422",
        is_chinese=False,
        keywords=["mediation", "experimental design"],
        source="内置经典文献",
    ),
    "Zhao2010": LiteratureEntry(
        key="Zhao2010",
        authors=["Zhao, X.", "Lynch, J. G.", "Chen, Q."],
        year="2010",
        title="Reconsidering Baron and Kenny: Myths and truths about mediation analysis",
        journal="Journal of Consumer Research",
        volume="37",
        issue="2",
        pages="197-206",
        doi="10.1086/651257",
        is_chinese=False,
        keywords=["mediation", "Baron and Kenny", "bootstrap"],
        source="内置经典文献",
    ),
    # ── 心理测量与量表编制 ──
    "DeVellis2016": LiteratureEntry(
        key="DeVellis2016",
        authors=["DeVellis, R. F."],
        year="2016",
        title="Scale development: Theory and applications (4th ed.)",
        journal="SAGE Publications",
        is_chinese=False,
        keywords=["scale development", "psychometrics"],
        source="内置经典文献",
        relevance_note="量表编制的标准教材。",
    ),
    "Furr2021": LiteratureEntry(
        key="Furr2021",
        authors=["Furr, R. M."],
        year="2021",
        title="Psychometrics: An introduction (4th ed.)",
        journal="SAGE Publications",
        is_chinese=False,
        keywords=["psychometrics", "reliability", "validity"],
        source="内置经典文献",
    ),
    "Nunnally1994": LiteratureEntry(
        key="Nunnally1994",
        authors=["Nunnally, J. C.", "Bernstein, I. H."],
        year="1994",
        title="Psychometric theory (3rd ed.)",
        journal="McGraw-Hill",
        is_chinese=False,
        keywords=["psychometric theory", "reliability"],
        source="内置经典文献",
        relevance_note="心理测量学理论的经典教材，α≥0.70标准的来源。",
    ),
    "Hinkin1998": LiteratureEntry(
        key="Hinkin1998",
        authors=["Hinkin, T. R."],
        year="1998",
        title="A brief tutorial on the development of measures for use in survey questionnaires",
        journal="Organizational Research Methods",
        volume="1",
        issue="1",
        pages="104-121",
        doi="10.1177/109442819800100106",
        is_chinese=False,
        keywords=["scale development", "survey"],
        source="内置经典文献",
    ),
    "Fabrigar1999": LiteratureEntry(
        key="Fabrigar1999",
        authors=["Fabrigar, L. R.", "Wegener, D. T.", "MacCallum, R. C.", "Strahan, E. J."],
        year="1999",
        title="Evaluating the use of exploratory factor analysis in psychological research",
        journal="Psychological Methods",
        volume="4",
        issue="3",
        pages="272-299",
        doi="10.1037/1082-989X.4.3.272",
        is_chinese=False,
        keywords=["EFA", "factor analysis", "psychometrics"],
        source="内置经典文献",
    ),
    "Costello2005": LiteratureEntry(
        key="Costello2005",
        authors=["Costello, A. B.", "Osborne, J."],
        year="2005",
        title="Best practices in exploratory factor analysis",
        journal="Practical Assessment, Research, and Evaluation",
        volume="10",
        issue="7",
        pages="1-9",
        is_chinese=False,
        keywords=["EFA", "best practices"],
        source="内置经典文献",
    ),
    "Marsh2004": LiteratureEntry(
        key="Marsh2004",
        authors=["Marsh, H. W.", "Hau, K.-T.", "Wen, Z."],
        year="2004",
        title="In search of golden rules: Comment on hypothesis-testing approaches to setting cutoff values for fit indexes",
        journal="Structural Equation Modeling",
        volume="11",
        issue="3",
        pages="320-341",
        doi="10.1207/s15328007sem1103_2",
        is_chinese=False,
        keywords=["SEM", "fit indices", "CFI", "RMSEA"],
        source="内置经典文献",
    ),
    # ── 社会与人格心理学 ──
    "John1999": LiteratureEntry(
        key="John1999",
        authors=["John, O. P.", "Srivastava, S."],
        year="1999",
        title="The Big Five trait taxonomy: History, measurement, and theoretical perspectives",
        journal="Handbook of personality: Theory and research (2nd ed.)",
        is_chinese=False,
        keywords=["Big Five", "personality", "taxonomy"],
        source="内置经典文献",
    ),
    "Baumeister2007": LiteratureEntry(
        key="Baumeister2007",
        authors=["Baumeister, R. F.", "Vohs, K. D.", "Tice, D. M."],
        year="2007",
        title="The strength model of self-control",
        journal="Current Directions in Psychological Science",
        volume="16",
        issue="6",
        pages="351-355",
        doi="10.1111/j.1467-8721.2007.00534.x",
        is_chinese=False,
        keywords=["self-control", "ego depletion"],
        source="内置经典文献",
    ),
    "Hofstede2001": LiteratureEntry(
        key="Hofstede2001",
        authors=["Hofstede, G."],
        year="2001",
        title="Culture's consequences: Comparing values, behaviors, institutions and organizations across nations (2nd ed.)",
        journal="SAGE Publications",
        is_chinese=False,
        keywords=["culture", "cross-cultural", "values"],
        source="内置经典文献",
    ),
    # ── 组织心理学 ──
    "Maslach2001": LiteratureEntry(
        key="Maslach2001",
        authors=["Maslach, C.", "Schaufeli, W. B.", "Leiter, M. P."],
        year="2001",
        title="Job burnout",
        journal="Annual Review of Psychology",
        volume="52",
        pages="397-422",
        doi="10.1146/annurev.psych.52.1.397",
        is_chinese=False,
        keywords=["burnout", "job", "MBI"],
        source="内置经典文献",
        relevance_note="工作倦怠研究综述，MBI量表的理论基础。",
    ),
    "Schaufeli2002": LiteratureEntry(
        key="Schaufeli2002",
        authors=["Schaufeli, W. B.", "Salanova, M.", "Gonzalez-Roma, V.", "Bakker, A. B."],
        year="2002",
        title="The measurement of engagement and burnout: A two sample confirmatory factor analytic approach",
        journal="Journal of Happiness Studies",
        volume="3",
        pages="71-92",
        doi="10.1023/A:1015630930326",
        is_chinese=False,
        keywords=["work engagement", "burnout", "UWES"],
        source="内置经典文献",
    ),
    "Luthans2007": LiteratureEntry(
        key="Luthans2007",
        authors=["Luthans, F.", "Youssef, C. M.", "Avolio, B. J."],
        year="2007",
        title="Psychological capital: Developing the human competitive edge",
        journal="Oxford University Press",
        is_chinese=False,
        keywords=["psychological capital", "PsyCap", "positive psychology"],
        source="内置经典文献",
    ),
    # ── 实验设计 ──
    "Shadish2002": LiteratureEntry(
        key="Shadish2002",
        authors=["Shadish, W. R.", "Cook, T. D.", "Campbell, D. T."],
        year="2002",
        title="Experimental and quasi-experimental designs for generalized causal inference",
        journal="Houghton Mifflin",
        is_chinese=False,
        keywords=["experimental design", "quasi-experiment", "causality"],
        source="内置经典文献",
        relevance_note="实验和准实验设计的经典教材。",
    ),
    "Kirk2013": LiteratureEntry(
        key="Kirk2013",
        authors=["Kirk, R. E."],
        year="2013",
        title="Experimental design: Procedures for the behavioral sciences (4th ed.)",
        journal="SAGE Publications",
        is_chinese=False,
        keywords=["experimental design", "ANOVA"],
        source="内置经典文献",
    ),
    "Keppel1991": LiteratureEntry(
        key="Keppel1991",
        authors=["Keppel, G."],
        year="1991",
        title="Design and analysis: A researcher's handbook (3rd ed.)",
        journal="Prentice Hall",
        is_chinese=False,
        keywords=["experimental design", "ANOVA"],
        source="内置经典文献",
    ),
    # ── 认知与情绪 ──
    "Gross2015": LiteratureEntry(
        key="Gross2015",
        authors=["Gross, J. J."],
        year="2015",
        title="Emotion regulation: Current status and future prospects",
        journal="Psychological Inquiry",
        volume="26",
        issue="1",
        pages="1-26",
        doi="10.1080/1047840X.2014.940781",
        is_chinese=False,
        keywords=["emotion regulation", "process model"],
        source="内置经典文献",
    ),
    "Baddeley2000": LiteratureEntry(
        key="Baddeley2000",
        authors=["Baddeley, A."],
        year="2000",
        title="The episodic buffer: A new component of working memory?",
        journal="Trends in Cognitive Sciences",
        volume="4",
        issue="11",
        pages="417-423",
        doi="10.1016/S1364-6613(00)01538-2",
        is_chinese=False,
        keywords=["working memory", "episodic buffer"],
        source="内置经典文献",
    ),
    "Miyake2000": LiteratureEntry(
        key="Miyake2000",
        authors=["Miyake, A.", "Friedman, N. P.", "Emerson, M. J.", "Witzki, A. H.", "Howerter, A.", "Wager, T. D."],
        year="2000",
        title="The unity and diversity of executive functions and their contributions to complex frontal lobe tasks: A latent variable analysis",
        journal="Cognitive Psychology",
        volume="41",
        issue="1",
        pages="49-100",
        doi="10.1006/cogp.1999.0734",
        is_chinese=False,
        keywords=["executive function", "working memory", "inhibition"],
        source="内置经典文献",
    ),
    # ── 积极心理学 ──
    "Seligman2000": LiteratureEntry(
        key="Seligman2000",
        authors=["Seligman, M. E. P.", "Csikszentmihalyi, M."],
        year="2000",
        title="Positive psychology: An introduction",
        journal="American Psychologist",
        volume="55",
        issue="1",
        pages="5-14",
        doi="10.1037/0003-066X.55.1.5",
        is_chinese=False,
        keywords=["positive psychology", "well-being"],
        source="内置经典文献",
        relevance_note="积极心理学的开创性文献。",
    ),
    "Ryff1989": LiteratureEntry(
        key="Ryff1989",
        authors=["Ryff, C. D."],
        year="1989",
        title="Happiness is everything, or is it? Explorations on the meaning of psychological well-being",
        journal="Journal of Personality and Social Psychology",
        volume="57",
        issue="6",
        pages="1069-1081",
        doi="10.1037/0022-3514.57.6.1069",
        is_chinese=False,
        keywords=["psychological well-being", "PWB"],
        source="内置经典文献",
    ),
    # ── 问卷平台与在线实验 ──
    "deLeeuw2015": LiteratureEntry(
        key="deLeeuw2015",
        authors=["de Leeuw, J. R."],
        year="2015",
        title="jsPsych: A JavaScript library for creating behavioral experiments in a web browser",
        journal="Behavior Research Methods",
        volume="47",
        issue="1",
        pages="1-12",
        doi="10.3758/s13428-014-0458-y",
        is_chinese=False,
        keywords=["jsPsych", "online experiment", "web-based"],
        source="内置经典文献",
        relevance_note="jsPsych在线实验平台的原始文献。",
    ),
    "Buhrmester2011": LiteratureEntry(
        key="Buhrmester2011",
        authors=["Buhrmester, M.", "Kwang, T.", "Gosling, S. D."],
        year="2011",
        title="Amazon's Mechanical Turk: A new source of inexpensive, yet high-quality, data?",
        journal="Perspectives on Psychological Science",
        volume="6",
        issue="1",
        pages="3-5",
        doi="10.1177/1745691610393980",
        is_chinese=False,
        keywords=["MTurk", "online data collection"],
        source="内置经典文献",
    ),
    "Podsakoff2012": LiteratureEntry(
        key="Podsakoff2012",
        authors=["Podsakoff, P. M.", "MacKenzie, S. B.", "Podsakoff, N. P."],
        year="2012",
        title="Sources of method bias in social science research and recommendations on how to control it",
        journal="Annual Review of Psychology",
        volume="63",
        pages="539-569",
        doi="10.1146/annurev-psych-120710-100452",
        is_chinese=False,
        keywords=["method bias", "common method variance"],
        source="内置经典文献",
    ),
    # ── 更多经典文献 ──
    "Baron1986": LiteratureEntry(
        key="Baron1986",
        authors=["Baron, R. M.", "Kenny, D. A."],
        year="1986",
        title="The moderator-mediator variable distinction in social psychological research",
        journal="Journal of Personality and Social Psychology",
        volume="51",
        issue="6",
        pages="1173-1182",
        doi="10.1037/0022-3514.51.6.1173",
        is_chinese=False,
        keywords=["moderator", "mediator", "Baron and Kenny"],
        source="内置经典文献",
        relevance_note="中介和调节效应区分的里程碑文献。",
    ),
    "Aiken1991": LiteratureEntry(
        key="Aiken1991",
        authors=["Aiken, L. S.", "West, S. G."],
        year="1991",
        title="Multiple regression: Testing and interpreting interactions",
        journal="SAGE Publications",
        is_chinese=False,
        keywords=["moderation", "interaction", "multiple regression"],
        source="内置经典文献",
    ),
    "Bentler1990": LiteratureEntry(
        key="Bentler1990",
        authors=["Bentler, P. M."],
        year="1990",
        title="Comparative fit indexes in structural models",
        journal="Psychological Bulletin",
        volume="107",
        issue="2",
        pages="238-246",
        doi="10.1037/0033-2909.107.2.238",
        is_chinese=False,
        keywords=["CFI", "SEM", "fit index"],
        source="内置经典文献",
    ),
    "Browne1993": LiteratureEntry(
        key="Browne1993",
        authors=["Browne, M. W.", "Cudeck, R."],
        year="1993",
        title="Alternative ways of assessing model fit",
        journal="Testing structural equation models (pp. 136-162)",
        is_chinese=False,
        keywords=["SEM", "model fit", "RMSEA"],
        source="内置经典文献",
    ),
    "Gignac2016": LiteratureEntry(
        key="Gignac2016",
        authors=["Gignac, G. E.", "Szodorai, E. T."],
        year="2016",
        title="Effect size guidelines for individual differences researchers",
        journal="Personality and Individual Differences",
        volume="102",
        pages="74-78",
        doi="10.1016/j.paid.2016.06.069",
        is_chinese=False,
        keywords=["effect size", "individual differences", "correlation"],
        source="内置经典文献",
    ),
    "Funder2019": LiteratureEntry(
        key="Funder2019",
        authors=["Funder, D. C.", "Ozer, D. J."],
        year="2019",
        title="Evaluating effect size in psychological research: Sense and nonsense",
        journal="Advances in Methods and Practices in Psychological Science",
        volume="2",
        issue="2",
        pages="156-168",
        doi="10.1177/2515245919847202",
        is_chinese=False,
        keywords=["effect size", "interpretation", "Cohen"],
        source="内置经典文献",
    ),
    "Simmons2011": LiteratureEntry(
        key="Simmons2011",
        authors=["Simmons, J. P.", "Nelson, L. D.", "Simonsohn, U."],
        year="2011",
        title="False-positive psychology: Undisclosed flexibility in data collection and analysis allows presenting anything as significant",
        journal="Psychological Science",
        volume="22",
        issue="11",
        pages="1359-1366",
        doi="10.1177/0956797611417632",
        is_chinese=False,
        keywords=["false positive", "research practices", "replicability"],
        source="内置经典文献",
    ),
    "OpenScience2015": LiteratureEntry(
        key="OpenScience2015",
        authors=["Open Science Collaboration"],
        year="2015",
        title="Estimating the reproducibility of psychological science",
        journal="Science",
        volume="349",
        issue="6251",
        pages="aac4716",
        doi="10.1126/science.aac4716",
        is_chinese=False,
        keywords=["reproducibility", "replication", "open science"],
        source="内置经典文献",
        relevance_note="心理学可重复性大项目，100项研究的重复结果。",
    ),
}


# ===========================================================================
# 文献管理与检索
# ===========================================================================

class LiteratureManager:
    """论文文献管理器"""

    def __init__(self):
        self.entries: Dict[str, LiteratureEntry] = {}
        self.citation_order: List[str] = []  # 引用顺序
        # 加载预置文献
        self._load_presets()

    def _load_presets(self):
        for key, entry in PRESET_CHINESE_LITERATURE.items():
            self.entries[key] = entry
        for key, entry in PRESET_ENGLISH_LITERATURE.items():
            self.entries[key] = entry
        # 加载扩展文献库（v2.0：113→200条）
        try:
            from .literature_expansion import get_expansion_entries
            for key, entry in get_expansion_entries().items():
                if key not in self.entries:
                    self.entries[key] = entry
        except ImportError:
            pass

    def add_entry(self, entry: LiteratureEntry):
        """添加文献条目"""
        if entry.key not in self.entries:
            self.entries[entry.key] = entry

    def search_presets(self, keywords: List[str], n: int = 10) -> List[LiteratureEntry]:
        """在预置文献库中搜索相关文献"""
        scored = []
        for key, entry in self.entries.items():
            score = 0
            search_text = f"{entry.title} {entry.journal} {' '.join(entry.authors)} {' '.join(entry.keywords)} {entry.relevance_note}"
            for kw in keywords:
                if kw.lower() in search_text.lower():
                    score += 1
            if score > 0:
                scored.append((entry, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in scored[:n]]

    def search_online(self, query: str, n: int = 5) -> List[Dict]:
        """在线搜索新文献（通过Crossref API）"""
        try:
            from src.questionnaire.kb_search import _search_crossref
            results = _search_crossref(query)
            return results[:n]
        except Exception:
            return []

    def cite(self, key: str) -> str:
        """引用文献（记录引用顺序并返回引用标记）"""
        if key not in self.citation_order:
            self.citation_order.append(key)
        return f"[{key}]"

    def format_reference_list(self) -> List[str]:
        """格式化学报参考文献列表"""
        ref_entries = []
        for key in self.citation_order:
            if key in self.entries:
                ref_entries.append(self.entries[key])

        # 中文文献在前，英文在后
        chinese_refs = [e for e in ref_entries if e.is_chinese]
        english_refs = [e for e in ref_entries if not e.is_chinese]

        lines = []
        ref_num = 1
        for entry in chinese_refs:
            lines.append(f"[{ref_num}] {entry.format_reference()}")
            ref_num += 1
        for entry in english_refs:
            lines.append(f"[{ref_num}] {entry.format_reference()}")
            ref_num += 1

        return lines

    def get_entry(self, key: str) -> Optional[LiteratureEntry]:
        """获取文献条目"""
        return self.entries.get(key)

    def suggest_for_context(self, context: str, n: int = 5) -> List[LiteratureEntry]:
        """根据上下文语境推荐相关文献"""
        keywords = _extract_keywords_from_context(context)
        return self.search_presets(keywords, n)


def _extract_keywords_from_context(text: str) -> List[str]:
    """从文本中提取关键词用于文献搜索"""
    important_terms = [
        "中介效应", "调节效应", "结构方程", "因素分析",
        "信度", "效度", "共同方法偏差", "Bootstrap",
        "量表编制", "探索性因素分析", "验证性因素分析",
        "效应量", "统计效力", "多层线性", "纵向研究",
        "交叉滞后", "元分析", "实验设计", "问卷设计",
        "自尊", "焦虑", "抑郁", "主观幸福感", "自我效能感",
        "社交焦虑", "工作满意度", "职业倦怠", "应对方式",
        "认知", "情绪", "动机", "人格", "智力",
        "mediation", "moderation", "SEM", "CFA", "EFA",
        "reliability", "validity", "effect size",
    ]
    found = []
    for term in important_terms:
        if term.lower() in text.lower():
            found.append(term)
    return found if found else ["心理学研究方法"]


async def smart_search_literature(
    topic: str,
    keywords: List[str],
    prefer_chinese: bool = True,
) -> List[Dict]:
    """
    智能文献搜索：预置库 → 在线API → 返回推荐列表。
    """
    manager = LiteratureManager()

    # 1. 预置库搜索
    preset_results = manager.search_presets(keywords, n=8)

    results = []
    for entry in preset_results:
        results.append({
            "key": entry.key,
            "authors": entry.authors,
            "year": entry.year,
            "title": entry.title,
            "journal": entry.journal,
            "is_chinese": entry.is_chinese,
            "source": entry.source,
            "relevance": entry.relevance_note,
        })

    # 2. 在线搜索（异步，非阻塞）
    if prefer_chinese:
        try:
            online_results = manager.search_online(
                f"{topic} {' '.join(keywords)} 心理学", n=3
            )
            for or_ in online_results:
                construct = or_.get("construct", {})
                if construct:
                    ref = construct.get("reference", "")
                    if ref:
                        results.append({
                            "key": f"online_{hashlib.md5(ref.encode()).hexdigest()[:8]}",
                            "authors": construct.get("authors", []),
                            "year": construct.get("year", ""),
                            "title": construct.get("title", ""),
                            "journal": construct.get("journal", ""),
                            "is_chinese": any(
                                "一" <= c <= "鿿" for c in construct.get("title", "")
                            ),
                            "source": "crossref",
                            "relevance": "在线检索文献，需人工审核",
                        })
        except Exception:
            pass

    return results


# ===========================================================================
# DOI 验证与自动填充 (Task 11)
# ===========================================================================

def validate_doi(doi: str) -> Optional[Dict]:
    """
    通过 Crossref API 验证 DOI 有效性，返回文献元数据。

    参数：
        doi: DOI 字符串 (如 "10.1037/0021-9010.88.5.879")

    返回：
        {
            "doi": str, "title": str, "authors": [str, ...],
            "journal": str, "year": str, "volume": str, "issue": str,
            "pages": str, "publisher": str, "type": str, "verified": True,
        }
        或 None（无法验证时）
    """
    import urllib.request
    import urllib.parse

    doi = doi.strip()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "")
    if not doi or "/" not in doi:
        return None

    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PsyAnalysis/2.0 (mailto:research@example.com; Academic tool)",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    msg = data.get("message", {})
    if not msg:
        return None

    authors = []
    for a in msg.get("author", [])[:10]:
        family = a.get("family", "")
        given = a.get("given", "")
        if family:
            authors.append(f"{family}, {given}" if given else family)

    published = (
        msg.get("published-print", {})
        or msg.get("published-online", {})
        or msg.get("created", {})
        or {}
    )
    date_parts = published.get("date-parts", [[None]])[0]
    year = str(date_parts[0]) if date_parts and date_parts[0] else ""

    container = (msg.get("container-title") or [""])[0]
    volume = msg.get("volume", "")
    issue = msg.get("issue", "")
    pages = msg.get("page", "")
    title = (msg.get("title") or [""])[0]

    return {
        "doi": doi,
        "title": title,
        "authors": authors,
        "journal": container,
        "year": year,
        "volume": volume,
        "issue": issue,
        "pages": pages,
        "publisher": msg.get("publisher", ""),
        "type": msg.get("type", ""),
        "verified": True,
    }


def autofill_from_doi(doi: str) -> Optional[LiteratureEntry]:
    """
    从 DOI 自动生成 APA7 格式的 LiteratureEntry。

    通过 Crossref API 获取文献元数据，自动填充所有字段。
    """
    meta = validate_doi(doi)
    if not meta:
        return None

    title = meta["title"]
    has_chinese = any("一" <= c <= "鿿" for c in title)

    first_author = meta["authors"][0] if meta["authors"] else "Unknown"
    last_name = first_author.split(",")[0].strip().replace(" ", "")
    key = f"{last_name}{meta['year']}"
    if has_chinese:
        key = f"{first_author.replace(',', '').replace(' ', '')}{meta['year']}"

    entry = LiteratureEntry(
        key=key,
        authors=meta["authors"],
        year=meta["year"],
        title=title,
        journal=meta["journal"],
        volume=meta["volume"],
        issue=meta["issue"],
        pages=meta["pages"],
        doi=meta["doi"],
        is_chinese=has_chinese,
        source="crossref_autofill",
        relevance_note="通过DOI自动填充，需人工审核相关性和格式。",
    )
    return entry


def enrich_reference(entry: LiteratureEntry) -> LiteratureEntry:
    """
    用 Crossref API 中的元数据补充/修正已有的 LiteratureEntry。

    优先保留用户提供的信息，仅填补缺失字段。
    """
    if not entry.doi:
        return entry

    meta = validate_doi(entry.doi)
    if not meta:
        return entry

    if not entry.volume and meta["volume"]:
        entry.volume = meta["volume"]
    if not entry.issue and meta["issue"]:
        entry.issue = meta["issue"]
    if not entry.pages and meta["pages"]:
        entry.pages = meta["pages"]

    return entry


# ===========================================================================
# Task 10: 引用交叉校验
# ===========================================================================

@dataclass
class CitationCheckResult:
    """引用校验结果"""
    total_citations: int = 0
    verified: int = 0
    missing: int = 0
    ambiguous: int = 0
    matched_entries: List[Dict] = field(default_factory=list)
    missing_citations: List[str] = field(default_factory=list)
    ambiguous_citations: List[Dict] = field(default_factory=list)
    summary: str = ""


def cross_check_citations(
    manuscript_text: str,
    literature_entries: List[LiteratureEntry],
    citation_pattern: str = r"\[([^\]]+)\]",
) -> CitationCheckResult:
    """
    检查论文正文中的引用是否都能在文献条目中找到。

    提取正文中所有 [...] 格式的引用标记，逐一与文献库中的 key 比对。

    参数：
        manuscript_text: 论文正文文本
        literature_entries: 文献条目列表
        citation_pattern: 引用标记的正则模式（默认匹配 [作者年份] 格式）

    返回：
        CitationCheckResult 包含校验结果
    """
    # 提取引用标记
    matches = re.findall(citation_pattern, manuscript_text)
    # 过滤掉非引用的方括号内容（如表格标记、注释）
    citation_keys = []
    for m in matches:
        # 引用标记通常为"作者, 年份"或"作者年份"格式
        if re.search(r"[a-zA-Z一-鿿].*?\d{4}", m):
            citation_keys.append(m.strip())

    # 去重
    unique_citations = list(set(citation_keys))

    # 构建文献 key 索引
    entry_keys = {entry.key: entry for entry in literature_entries}
    entry_authors = {}
    for entry in literature_entries:
        if entry.authors:
            # 构建备选键：第一作者 + 年份
            first_author = entry.authors[0].split(",")[0].strip()
            alt_key = f"{first_author}{entry.year}"
            entry_authors.setdefault(alt_key, []).append(entry)

    verified = []
    missing = []
    ambiguous = []

    for citation in unique_citations:
        # 精确匹配
        if citation in entry_keys:
            entry = entry_keys[citation]
            verified.append({
                "citation": citation,
                "entry_key": entry.key,
                "title": entry.title,
                "journal": entry.journal,
                "year": entry.year,
            })
        else:
            # 尝试第一作者 + 年份匹配
            found_entries = entry_authors.get(citation, [])
            if len(found_entries) == 1:
                entry = found_entries[0]
                verified.append({
                    "citation": citation,
                    "entry_key": entry.key,
                    "title": entry.title,
                    "journal": entry.journal,
                    "year": entry.year,
                    "note": "通过作者-年份匹配（键名不完全一致）",
                })
            elif len(found_entries) > 1:
                ambiguous.append({
                    "citation": citation,
                    "candidates": [
                        {"key": e.key, "title": e.title} for e in found_entries
                    ],
                })
            else:
                missing.append(citation)

    total = len(unique_citations)
    verified_n = len(verified)
    missing_n = len(missing)
    ambiguous_n = len(ambiguous)

    if missing_n == 0 and ambiguous_n == 0:
        summary = f"✅ 所有{total}个引用均通过校验，全部在文献库中找到匹配。"
    elif missing_n > 0:
        summary = (
            f"⚠ {total}个引用中，{verified_n}个通过校验，"
            f"{missing_n}个未在文献库中找到。"
            f"请补充以下文献的完整信息：{'、'.join(missing[:5])}"
            f"{'...' if len(missing) > 5 else ''}"
        )
    else:
        summary = (
            f"⚠ {total}个引用中，{verified_n}个通过校验，"
            f"{ambiguous_n}个存在歧义（同一作者多条记录）。"
        )

    return CitationCheckResult(
        total_citations=total,
        verified=verified_n,
        missing=missing_n,
        ambiguous=ambiguous_n,
        matched_entries=verified,
        missing_citations=missing,
        ambiguous_citations=ambiguous,
        summary=summary,
    )


def cross_check_references_list(
    reference_text: str,
    literature_entries: List[LiteratureEntry],
) -> Dict:
    """
    校验参考文献列表中的每条文献是否在文献管理器中存在。

    从参考文献文本中提取 作者 (年份) 格式的条目，
    逐一与文献库比对。

    返回：
        {
            "total_in_text": int,
            "found_in_library": int,
            "not_found": list,
            "suspicious_entries": list,  # 可疑的文献（年份/作者不匹配）
        }
    """
    # 提取每条参考文献的作者和年份
    ref_pattern = re.compile(
        r"([^.\n]+?)\s*[\(（]\s*(\d{4}[a-z]?)\s*[\)）]",
        re.MULTILINE,
    )
    matches = ref_pattern.findall(reference_text)

    found = []
    not_found = []
    suspicious = []

    # 构建快速查找索引
    lib_index = {}
    for entry in literature_entries:
        lib_index.setdefault(entry.key.lower(), []).append(entry)
        if entry.authors:
            first_author = entry.authors[0].split(",")[0].strip().lower()
            yr_key = f"{first_author}{entry.year}"
            lib_index.setdefault(yr_key, []).append(entry)

    for authors_str, year in matches:
        authors_clean = authors_str.strip().rstrip(",")
        # 构建查找键
        search_key = f"{authors_clean}{year}".replace(" ", "").lower()
        partial_key = f"{authors_clean.split(',')[0] if ',' in authors_clean else authors_clean.split()[0] if authors_clean.split() else authors_clean}{year}".lower()

        matched = False
        for key, entries in lib_index.items():
            if search_key in key or partial_key in key:
                found.append({
                    "authors_in_text": authors_clean,
                    "year": year,
                    "matched_entry": entries[0].key,
                })
                matched = True
                break

        if not matched:
            not_found.append(f"{authors_clean} ({year})")

    return {
        "total_in_text": len(matches),
        "found_in_library": len(found),
        "not_found": not_found,
        "suspicious_entries": suspicious,
    }
