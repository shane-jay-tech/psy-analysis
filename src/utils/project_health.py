"""项目健康检查 — 把分散模块收束为研究项目状态。

检查项目当前状态，输出结构化问题列表。
ERROR 级问题阻止最终交付包导出。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProjectHealthIssue:
    """单个健康检查问题。"""
    level: str  # ERROR / WARN / INFO
    code: str
    title: str
    detail: str
    module: str
    action_label: str = ""
    action_target: str = ""


def run_health_checks(
    *,
    has_data: bool = False,
    variable_types_set: bool = False,
    literature_pending_count: int = 0,
    literature_approved_count: int = 0,
    paper_bundle: Any = None,
    analysis_results: list | None = None,
    reverse_items_configured: bool = True,
) -> list[ProjectHealthIssue]:
    """执行项目健康检查，返回问题列表。"""
    issues = []

    # 数据检查
    if not has_data:
        issues.append(ProjectHealthIssue(
            level="ERROR",
            code="NO_DATA",
            title="未上传数据",
            detail="无法进行统计分析，请先上传数据文件",
            module="data",
            action_label="上传数据",
            action_target="data_upload",
        ))

    # 变量类型
    if has_data and not variable_types_set:
        issues.append(ProjectHealthIssue(
            level="WARN",
            code="VAR_TYPES_MISSING",
            title="变量类型未设置",
            detail="影响方法推荐和假设检查，建议设置变量角色",
            module="data",
            action_label="设置变量",
            action_target="variable_config",
        ))

    # 问卷反向题
    if not reverse_items_configured:
        issues.append(ProjectHealthIssue(
            level="WARN",
            code="REVERSE_ITEMS_NOT_SET",
            title="问卷反向题未设置",
            detail="影响量表计分结果的准确性",
            module="questionnaire",
            action_label="配置反向题",
            action_target="questionnaire_config",
        ))

    # 文献检查
    if literature_pending_count > 0:
        issues.append(ProjectHealthIssue(
            level="INFO",
            code="LITERATURE_PENDING",
            title=f"有 {literature_pending_count} 篇待审核文献",
            detail="建议完成文献审核以支撑综述写作",
            module="literature",
            action_label="审核文献",
            action_target="literature_review",
        ))

    if literature_approved_count < 3:
        issues.append(ProjectHealthIssue(
            level="WARN",
            code="LITERATURE_INSUFFICIENT",
            title="已纳入文献数量不足",
            detail=f"当前仅 {literature_approved_count} 篇，建议至少纳入 5 篇",
            module="literature",
            action_label="查找文献",
            action_target="literature_search",
        ))

    # 论文 bundle 检查
    if paper_bundle is not None:
        if hasattr(paper_bundle, "warnings") and paper_bundle.warnings:
            for w in paper_bundle.warnings:
                issues.append(ProjectHealthIssue(
                    level="WARN",
                    code="BUNDLE_WARNING",
                    title="论文草稿有警告",
                    detail=w,
                    module="paper",
                    action_label="查看论文",
                    action_target="paper_preview",
                ))

        if hasattr(paper_bundle, "sections"):
            result_section = paper_bundle.sections.get("result")
            if result_section and not analysis_results:
                issues.append(ProjectHealthIssue(
                    level="ERROR",
                    code="RESULT_NO_ANALYSIS",
                    title="论文结果章缺少统计绑定",
                    detail="导出前必须完成统计分析并绑定结果",
                    module="paper",
                    action_label="运行分析",
                    action_target="analysis",
                ))

    return issues


def has_blocking_issues(issues: list[ProjectHealthIssue]) -> bool:
    """是否有 ERROR 级问题（阻止导出）。"""
    return any(i.level == "ERROR" for i in issues)


def issues_summary(issues: list[ProjectHealthIssue]) -> dict[str, int]:
    """按级别统计问题数。"""
    counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
    for i in issues:
        counts[i.level] = counts.get(i.level, 0) + 1
    return counts
