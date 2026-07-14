"""论文写作工作流服务层 — 简化常见操作的 facade。

为 UI 层提供单步调用接口，内部协调 PaperEngine 的多步骤流程。
避免 UI 层需要了解 PaperEngine 的完整状态机。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .paper_engine import PaperEngine, PaperState

logger = logging.getLogger(__name__)


@dataclass
class QuickPaperRequest:
    """一键生成论文的请求参数（UI 层只填这个）。"""
    topic: str = ""
    title_hint: str = ""
    research_questions: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)

    participants_n: int = 0
    participants_desc: str = ""
    male_ratio: float = 0.5
    age_mean: float = 0.0
    age_sd: float = 0.0
    materials: List[Dict] = field(default_factory=list)
    procedure: str = ""
    ethics: str = ""
    control_vars: List[str] = field(default_factory=list)

    theoretical_contributions: List[str] = field(default_factory=list)
    practical_implications: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    future_directions: List[str] = field(default_factory=list)

    df: Optional[pd.DataFrame] = None
    analysis_results: Dict[str, Any] = field(default_factory=dict)

    user_literature: List[Dict] = field(default_factory=list)
    search_keywords: Optional[List[str]] = None


@dataclass
class PaperResult:
    """论文生成结果。"""
    sections: Dict[str, str] = field(default_factory=dict)
    manuscript: str = ""
    reference_list: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    engine: Optional[PaperEngine] = None


def generate_paper_quick(req: QuickPaperRequest) -> PaperResult:
    """一键生成论文初稿 — 从请求到完整论文的一步调用。

    等价于手动调用 PaperEngine 的 set_topic → set_methods → set_discussion
    → import_analysis → search_literature → generate_full_paper → assemble
    但 UI 层只需填一个 QuickPaperRequest。
    """
    engine = PaperEngine()

    engine.set_topic(
        topic=req.topic,
        research_questions=req.research_questions,
        hypotheses=req.hypotheses,
        title_hint=req.title_hint,
    )

    engine.set_methods(
        participants_n=req.participants_n,
        male_ratio=req.male_ratio,
        age_mean=req.age_mean,
        age_sd=req.age_sd,
        participants_desc=req.participants_desc,
        materials=req.materials,
        procedure=req.procedure,
        ethics=req.ethics,
        control_vars=req.control_vars,
    )

    engine.set_discussion(
        theoretical=req.theoretical_contributions,
        practical=req.practical_implications,
        limitations=req.limitations,
        future=req.future_directions,
    )

    if req.df is not None:
        engine.set_data(req.df)

    if req.analysis_results:
        engine.import_analysis_results(req.analysis_results)

    if req.user_literature:
        engine.add_user_literature(req.user_literature)

    if req.search_keywords:
        engine.search_literature(req.search_keywords)

    sections = engine.generate_full_paper()
    manuscript = engine.assemble_manuscript()

    return PaperResult(
        sections=sections,
        manuscript=manuscript,
        reference_list=engine.state.reference_list,
        logs=engine.get_logs(),
        engine=engine,
    )


def regenerate_section(engine: PaperEngine, section_name: str) -> str:
    """重新生成单个章节（用户修改参数后）。"""
    return engine.generate_section(section_name)
