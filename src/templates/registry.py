"""项目模板注册表 — 管理可用模板和创建新项目。"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


TEMPLATES_DIR = Path(__file__).parent.parent.parent / "project_templates"


@dataclass
class ProjectTemplate:
    """项目模板元数据。"""
    template_id: str
    name: str
    description: str
    research_type: str
    recommended_method: str
    variable_roles: dict[str, str] = field(default_factory=dict)
    sample_size_hint: str = ""
    paper_sections: list[str] = field(default_factory=list)
    directory: str = ""

    def get_path(self) -> Path:
        return TEMPLATES_DIR / self.template_id

    def has_data(self) -> bool:
        return (self.get_path() / "data.csv").exists()

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "research_type": self.research_type,
            "recommended_method": self.recommended_method,
            "variable_roles": self.variable_roles,
            "sample_size_hint": self.sample_size_hint,
            "paper_sections": self.paper_sections,
        }


_TEMPLATES: list[ProjectTemplate] = [
    ProjectTemplate(
        template_id="questionnaire_correlation",
        name="问卷相关研究",
        description="探索两个心理变量的相关关系（如焦虑与自尊）",
        research_type="correlational",
        recommended_method="pearson_corr",
        variable_roles={"x": "连续变量 1（如焦虑）", "y": "连续变量 2（如自尊）"},
        sample_size_hint="建议 N ≥ 50",
        paper_sections=["引言", "方法", "结果", "讨论", "参考文献"],
    ),
    ProjectTemplate(
        template_id="independent_group_comparison",
        name="独立样本组间比较",
        description="比较两个独立组在某指标上的差异（如实验组 vs 对照组）",
        research_type="experimental",
        recommended_method="independent_ttest",
        variable_roles={"dv": "连续因变量（如成绩）", "iv": "分组变量（如条件）"},
        sample_size_hint="每组建议 N ≥ 30",
        paper_sections=["引言", "方法", "结果", "讨论", "参考文献"],
    ),
    ProjectTemplate(
        template_id="pre_post_experiment",
        name="前后测实验",
        description="同一组被试在干预前后的变化（配对样本）",
        research_type="pre_post",
        recommended_method="paired_ttest",
        variable_roles={"dv": "连续因变量", "iv": "时间点（前测/后测）"},
        sample_size_hint="建议 N ≥ 30",
        paper_sections=["引言", "方法", "结果", "讨论", "参考文献"],
    ),
    ProjectTemplate(
        template_id="mediation_questionnaire",
        name="中介模型问卷研究",
        description="探索自变量通过中介变量影响因变量的间接效应",
        research_type="mediation",
        recommended_method="mediation_analysis",
        variable_roles={
            "iv": "自变量（自我效能、社会支持）",
            "mediator": "中介变量（学业动机）",
            "dv": "因变量（学业表现）",
        },
        sample_size_hint="建议 N ≥ 100",
        paper_sections=["引言", "方法", "结果", "讨论", "参考文献"],
    ),
    ProjectTemplate(
        template_id="moderation_questionnaire",
        name="调节模型问卷研究",
        description="探索调节变量如何改变自变量与因变量之间关系的强度或方向",
        research_type="moderation",
        recommended_method="moderation_analysis",
        variable_roles={
            "iv": "自变量（工作压力）",
            "moderator": "调节变量（心理韧性）",
            "dv": "因变量（工作满意度）",
            "covariate": "协变量（性别）",
        },
        sample_size_hint="建议 N ≥ 120",
        paper_sections=["引言", "方法", "结果", "讨论", "参考文献"],
    ),
    ProjectTemplate(
        template_id="scale_validation",
        name="量表信效度检验研究",
        description="对自编或修订量表进行信度和效度的全面检验",
        research_type="psychometrics",
        recommended_method="cfa",
        variable_roles={
            "items": "12 个题目（4 因子 x 3 题目）",
            "criterion": "效标分数",
        },
        sample_size_hint="建议 N ≥ 200",
        paper_sections=["引言", "方法", "结果", "讨论", "参考文献"],
    ),
]


def list_templates() -> list[ProjectTemplate]:
    """列出所有可用模板。"""
    return list(_TEMPLATES)


def get_template(template_id: str) -> Optional[ProjectTemplate]:
    """按 ID 获取模板。"""
    for t in _TEMPLATES:
        if t.template_id == template_id:
            return t
    return None


def create_project_from_template(
    template_id: str,
    target_dir: Path,
    project_name: str = "",
) -> Path:
    """从模板创建新项目目录。"""
    tpl = get_template(template_id)
    if not tpl:
        raise ValueError(f"未知模板: {template_id}")

    source = tpl.get_path()
    if not source.exists():
        raise FileNotFoundError(f"模板目录不存在: {source}")

    project_dir = target_dir / (project_name or tpl.template_id)
    if project_dir.exists():
        raise FileExistsError(f"目标目录已存在: {project_dir}")

    shutil.copytree(source, project_dir)
    return project_dir
