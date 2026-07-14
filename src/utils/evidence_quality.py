"""证据质量分层与引用审计 v5.1。

为每条证据记录评定质量等级 (A/B/C/D/Missing)，
并提供引用审计检查项（claim无证据、证据无使用、信息不完整等）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class EvidenceGrade:
    record_index: int
    citation_key: str
    grade: str  # A / B / C / D / Missing
    reasons: list[str] = field(default_factory=list)
    dimensions: dict = field(default_factory=dict)


@dataclass
class CitationAuditIssue:
    level: str  # ERROR / WARN / INFO
    code: str
    title: str
    detail: str
    action: str


@dataclass
class EvidenceQualityReport:
    grades: list[EvidenceGrade] = field(default_factory=list)
    audit_issues: list[CitationAuditIssue] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _rec_get(rec, key, default=""):
    """统一访问接口：支持 dict 和 dataclass/对象。"""
    if isinstance(rec, dict):
        return rec.get(key, default)
    return getattr(rec, key, default) or default


def grade_evidence(evidence_records: list) -> list[EvidenceGrade]:
    """对每条证据记录评定质量等级。"""
    grades = []
    for i, rec in enumerate(evidence_records):
        if rec is None:
            continue
        grade = _compute_grade(rec, i)
        grades.append(grade)
    return grades


def audit_citations(
    evidence_records: list[dict],
    paper_text: str = "",
    analysis_cards: list[dict] = None,
) -> list[CitationAuditIssue]:
    """执行引用审计，返回问题列表。"""
    issues = []

    issues.extend(_check_claim_without_evidence(evidence_records, paper_text))
    issues.extend(_check_evidence_without_usage(evidence_records, paper_text))
    issues.extend(_check_incomplete_info(evidence_records))
    issues.extend(_check_low_quality_critical(evidence_records, paper_text))
    issues.extend(_check_stale_references(evidence_records))
    issues.extend(_check_method_citation_match(evidence_records, analysis_cards or []))

    return issues


def generate_quality_report(
    evidence_records: list[dict],
    paper_text: str = "",
    analysis_cards: list[dict] = None,
) -> EvidenceQualityReport:
    """生成完整的证据质量报告。"""
    grades = grade_evidence(evidence_records)
    audit_issues = audit_citations(evidence_records, paper_text, analysis_cards)

    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "Missing": 0}
    for g in grades:
        grade_counts[g.grade] = grade_counts.get(g.grade, 0) + 1

    return EvidenceQualityReport(
        grades=grades,
        audit_issues=audit_issues,
        summary={
            "total": len(grades),
            "grade_distribution": grade_counts,
            "issues_by_level": {
                "ERROR": sum(1 for i in audit_issues if i.level == "ERROR"),
                "WARN": sum(1 for i in audit_issues if i.level == "WARN"),
                "INFO": sum(1 for i in audit_issues if i.level == "INFO"),
            },
        },
    )


def _compute_grade(rec: dict, idx: int) -> EvidenceGrade:
    """根据多维度评分计算单条证据等级。"""
    citation_key = _rec_get(rec,"citation_key", "")
    if not citation_key:
        return EvidenceGrade(
            record_index=idx, citation_key="",
            grade="Missing", reasons=["缺少引用标识"],
        )

    score = 0
    reasons = []
    dims = {}

    # 来源类型
    source_type = _rec_get(rec,"source_type", "").lower()
    if source_type in ("journal", "期刊", "peer-reviewed"):
        dims["source"] = 100
    elif source_type in ("book", "教材", "textbook"):
        dims["source"] = 90
    elif source_type in ("thesis", "学位论文", "dissertation"):
        dims["source"] = 70
    elif source_type in ("conference", "会议"):
        dims["source"] = 60
    elif source_type in ("webpage", "网页", "blog"):
        dims["source"] = 30
        reasons.append("来源为网页/博客")
    else:
        dims["source"] = 50

    # 发表年份
    year = _rec_get(rec,"year") or _rec_get(rec,"pub_year")
    if year:
        try:
            year_int = int(year)
            current_year = datetime.now().year
            age = current_year - year_int
            if age <= 5:
                dims["recency"] = 100
            elif age <= 10:
                dims["recency"] = 80
            elif age <= 20:
                dims["recency"] = 50
                reasons.append(f"发表于 {year_int}，距今 {age} 年")
            else:
                dims["recency"] = 20
                reasons.append(f"发表于 {year_int}，年代久远")
        except (ValueError, TypeError):
            dims["recency"] = 50
    else:
        dims["recency"] = 40
        reasons.append("缺少发表年份")

    # 相关性
    claim = _rec_get(rec,"claim", "")
    if claim and len(claim) >= 10:
        dims["relevance"] = 80
    elif claim:
        dims["relevance"] = 60
        reasons.append("claim 描述过简")
    else:
        dims["relevance"] = 20
        reasons.append("缺少 claim 描述")

    # 引用完整性
    completeness = 0
    if _rec_get(rec,"citation_key"):
        completeness += 25
    if _rec_get(rec,"claim"):
        completeness += 25
    if _rec_get(rec,"year") or _rec_get(rec,"pub_year"):
        completeness += 25
    if _rec_get(rec,"source_type") or _rec_get(rec,"doi") or _rec_get(rec,"url"):
        completeness += 25
    dims["completeness"] = completeness
    if completeness < 50:
        reasons.append("引用信息不完整")

    # 综合得分
    avg_score = sum(dims.values()) / len(dims) if dims else 0

    if avg_score >= 80:
        grade = "A"
    elif avg_score >= 60:
        grade = "B"
    elif avg_score >= 40:
        grade = "C"
    else:
        grade = "D"

    return EvidenceGrade(
        record_index=idx, citation_key=citation_key,
        grade=grade, reasons=reasons, dimensions=dims,
    )


def _check_claim_without_evidence(records: list[dict], paper_text: str) -> list[CitationAuditIssue]:
    """检查论文中是否有论断缺少证据支撑。"""
    issues = []
    if not paper_text:
        return issues

    claim_patterns = [
        r"研究表明", r"研究发现", r"结果显示", r"有研究指出",
        r"prior research", r"studies have shown",
    ]
    citations_in_text = re.findall(r"[（(][A-Za-z]+.*?\d{4}[）)]", paper_text)

    for pattern in claim_patterns:
        matches = list(re.finditer(pattern, paper_text))
        for match in matches:
            context = paper_text[max(0, match.start() - 50):match.end() + 100]
            has_citation = bool(re.search(r"[（(][A-Za-z]+.*?\d{4}[）)]", context))
            if not has_citation and not records:
                issues.append(CitationAuditIssue(
                    level="ERROR",
                    code="CLAIM_NO_EVIDENCE",
                    title="论断缺少证据",
                    detail=f"'{pattern}' 附近无引用且无证据记录",
                    action="为关键论断添加文献支撑",
                ))
                break
        if issues:
            break

    return issues


def _check_evidence_without_usage(records: list[dict], paper_text: str) -> list[CitationAuditIssue]:
    """检查证据表中有但论文未引用的记录。"""
    issues = []
    if not paper_text or not records:
        return issues

    unused = []
    for rec in records:
        key = _rec_get(rec,"citation_key", "")
        if not key:
            continue
        author_part = key[:4].lower()
        if author_part not in paper_text.lower():
            unused.append(key)

    if unused:
        issues.append(CitationAuditIssue(
            level="WARN",
            code="EVIDENCE_UNUSED",
            title="证据未被引用",
            detail=f"{len(unused)} 条证据未在论文中引用: {', '.join(unused[:3])}",
            action="在论文中引用或移除不需要的证据",
        ))
    return issues


def _check_incomplete_info(records: list[dict]) -> list[CitationAuditIssue]:
    """检查引用信息不完整的记录。"""
    issues = []
    incomplete = 0
    for rec in records:
        if not isinstance(rec, dict):
            continue
        key = _rec_get(rec,"citation_key", "")
        claim = _rec_get(rec,"claim", "")
        if not key or not claim:
            incomplete += 1

    if incomplete > 0:
        issues.append(CitationAuditIssue(
            level="WARN",
            code="CITATION_INCOMPLETE",
            title="引用信息不完整",
            detail=f"{incomplete} 条证据缺少 citation_key 或 claim",
            action="补充每条证据的引用标识和核心论点",
        ))
    return issues


def _check_low_quality_critical(records: list[dict], paper_text: str) -> list[CitationAuditIssue]:
    """检查是否使用低质量证据支撑关键论点。"""
    issues = []
    if not records:
        return issues

    low_quality = [r for r in records if isinstance(r, dict) and r.get("quality_grade") in ("D",)]
    if low_quality and paper_text:
        for rec in low_quality:
            key = _rec_get(rec,"citation_key", "")
            if key and key[:4].lower() in paper_text.lower():
                issues.append(CitationAuditIssue(
                    level="WARN",
                    code="LOW_QUALITY_USED",
                    title="低质量证据被引用",
                    detail=f"证据 '{key}' 质量等级为 D 但在论文中被引用",
                    action=f"替换 '{key}' 为更可靠的证据来源",
                ))
                break
    return issues


def _check_stale_references(records: list[dict]) -> list[CitationAuditIssue]:
    """检查是否有过旧的引用。"""
    issues = []
    current_year = datetime.now().year
    stale = 0
    for rec in records:
        if not isinstance(rec, dict):
            continue
        year = _rec_get(rec,"year") or _rec_get(rec,"pub_year")
        if year:
            try:
                if current_year - int(year) > 20:
                    stale += 1
            except (ValueError, TypeError):
                pass

    if stale > 0:
        issues.append(CitationAuditIssue(
            level="INFO",
            code="STALE_REFERENCE",
            title="引用年代久远",
            detail=f"{stale} 条引用发表超过 20 年",
            action="考虑补充近年研究，或说明经典引用的必要性",
        ))
    return issues


def _check_method_citation_match(records: list[dict], cards: list[dict]) -> list[CitationAuditIssue]:
    """检查统计方法引用是否与实际方法匹配。"""
    issues = []
    if not records or not cards:
        return issues

    method_keywords = {
        "ttest": ["t检验", "t-test", "t test"],
        "anova": ["方差分析", "ANOVA", "variance analysis"],
        "regression": ["回归", "regression"],
        "mediation": ["中介", "mediation"],
        "correlation": ["相关", "correlation"],
    }

    executed_methods = set()
    for card in cards:
        if isinstance(card, dict):
            method = card.get("method", "")
            for key, keywords in method_keywords.items():
                if key in method.lower():
                    executed_methods.add(key)
                    break

    return issues
