"""论文就绪度评分器 v5.1。

汇总数据健康、方法匹配、结果卡、图表、证据、导出状态，
输出总分(0-100)、等级、阻断项和下一步建议。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ReadinessItem:
    dimension: str
    score: float  # 0-100
    weight: float
    status: str  # "good" / "warning" / "error" / "missing"
    detail: str = ""
    action: str = ""


@dataclass
class ReadinessReport:
    total_score: float
    grade: str  # "未就绪" / "基本就绪" / "接近完成" / "可提交前检查"
    items: list[ReadinessItem] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    high_priority: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)
    next_step: str = ""


def compute_readiness(session_state: dict) -> ReadinessReport:
    """根据 session_state 中的项目状态计算论文就绪度。"""
    items = []

    # 1. 数据健康 (15%)
    items.append(_score_data_health(session_state))
    # 2. 方法匹配 (15%)
    items.append(_score_method_match(session_state))
    # 3. 统计结果完整性 (20%)
    items.append(_score_statistical_results(session_state))
    # 4. 图表完整性 (10%)
    items.append(_score_figures(session_state))
    # 5. 证据完整性 (15%)
    items.append(_score_evidence(session_state))
    # 6. 证据质量 (10%)
    items.append(_score_evidence_quality(session_state))
    # 7. 交付完整性 (10%)
    items.append(_score_delivery(session_state))
    # 8. 一致性检查 (5%)
    items.append(_score_consistency(session_state))

    total = sum(item.score * item.weight for item in items)
    total = min(100.0, max(0.0, total))

    blockers = [f"[{it.dimension}] {it.action}" for it in items if it.status == "error"]
    high_priority = [f"[{it.dimension}] {it.action}" for it in items if it.status == "warning"]
    optional = [f"[{it.dimension}] {it.action}" for it in items if it.status == "missing" and it.action]

    if blockers:
        grade = "未就绪"
    elif total < 40:
        grade = "未就绪"
    elif total < 65:
        grade = "基本就绪"
    elif total < 85:
        grade = "接近完成"
    else:
        grade = "可提交前检查"

    next_step = _determine_next_step(items)

    return ReadinessReport(
        total_score=round(total, 1),
        grade=grade,
        items=items,
        blockers=blockers,
        high_priority=high_priority,
        optional=optional,
        next_step=next_step,
    )


def _score_data_health(ss: dict) -> ReadinessItem:
    df = ss.get("uploaded_df")
    if df is None:
        return ReadinessItem(
            dimension="数据健康", score=0, weight=0.15,
            status="missing", detail="未上传数据",
            action="上传研究数据或从模板创建项目",
        )
    missing_pct = df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100
    n_rows = len(df)
    if n_rows < 10:
        return ReadinessItem(
            dimension="数据健康", score=30, weight=0.15,
            status="warning", detail=f"样本量过小 (n={n_rows})",
            action="增加样本量到至少 30",
        )
    if missing_pct > 20:
        return ReadinessItem(
            dimension="数据健康", score=50, weight=0.15,
            status="warning", detail=f"缺失率 {missing_pct:.1f}%",
            action="处理缺失值（删除或插补）",
        )
    return ReadinessItem(
        dimension="数据健康", score=100, weight=0.15,
        status="good", detail=f"n={n_rows}, 缺失率 {missing_pct:.1f}%",
    )


def _score_method_match(ss: dict) -> ReadinessItem:
    recs = ss.get("method_recommendations", [])
    cards = ss.get("analysis_cards", [])
    if not recs and not cards:
        return ReadinessItem(
            dimension="方法匹配", score=0, weight=0.15,
            status="missing", detail="未生成推荐或结果",
            action="进入方法推荐获得分析建议",
        )
    if recs and not cards:
        return ReadinessItem(
            dimension="方法匹配", score=40, weight=0.15,
            status="warning", detail="有推荐但未执行分析",
            action="执行推荐的分析方法",
        )
    return ReadinessItem(
        dimension="方法匹配", score=100, weight=0.15,
        status="good", detail=f"推荐 {len(recs)} 项, 执行 {len(cards)} 项",
    )


def _score_statistical_results(ss: dict) -> ReadinessItem:
    cards = ss.get("analysis_cards", [])
    if not cards:
        return ReadinessItem(
            dimension="统计结果", score=0, weight=0.20,
            status="missing", detail="无结果卡",
            action="执行数据分析生成结果卡",
        )
    has_es = sum(1 for c in cards if isinstance(c, dict) and c.get("effect_sizes"))
    has_apa = sum(1 for c in cards if isinstance(c, dict) and len(c.get("apa_text", "")) >= 10)
    score = min(100, (has_apa / len(cards)) * 80 + (has_es / len(cards)) * 20)
    if has_apa < len(cards):
        return ReadinessItem(
            dimension="统计结果", score=score, weight=0.20,
            status="warning", detail=f"APA 文本完整: {has_apa}/{len(cards)}",
            action="补全缺失的 APA 结果文本",
        )
    return ReadinessItem(
        dimension="统计结果", score=score, weight=0.20,
        status="good", detail=f"{len(cards)} 张结果卡，效应量 {has_es}/{len(cards)}",
    )


def _score_figures(ss: dict) -> ReadinessItem:
    figures = ss.get("apa_figures", [])
    cards = ss.get("analysis_cards", [])
    if not cards:
        return ReadinessItem(
            dimension="图表", score=0, weight=0.10,
            status="missing", detail="无分析结果",
            action="先完成数据分析",
        )
    if not figures:
        return ReadinessItem(
            dimension="图表", score=30, weight=0.10,
            status="warning", detail="无 APA 图表",
            action="生成 APA 图表以增强论文可读性",
        )
    return ReadinessItem(
        dimension="图表", score=100, weight=0.10,
        status="good", detail=f"{len(figures)} 张 APA 图表",
    )


def _score_evidence(ss: dict) -> ReadinessItem:
    evidence = ss.get("evidence_records", [])
    if not evidence:
        return ReadinessItem(
            dimension="证据完整性", score=0, weight=0.15,
            status="warning", detail="无证据记录",
            action="在证据表中添加文献支撑",
        )
    complete = sum(1 for e in evidence if isinstance(e, dict) and e.get("citation_key") and e.get("claim"))
    score = min(100, (complete / len(evidence)) * 100)
    if complete < len(evidence):
        return ReadinessItem(
            dimension="证据完整性", score=score, weight=0.15,
            status="warning", detail=f"完整: {complete}/{len(evidence)}",
            action="补全证据的引用标识和核心论点",
        )
    return ReadinessItem(
        dimension="证据完整性", score=score, weight=0.15,
        status="good", detail=f"{len(evidence)} 条证据记录",
    )


def _score_evidence_quality(ss: dict) -> ReadinessItem:
    evidence = ss.get("evidence_records", [])
    if not evidence:
        return ReadinessItem(
            dimension="证据质量", score=0, weight=0.10,
            status="missing", detail="无证据记录",
            action="添加文献证据",
        )
    graded = sum(1 for e in evidence if isinstance(e, dict) and e.get("quality_grade"))
    if graded == 0:
        return ReadinessItem(
            dimension="证据质量", score=50, weight=0.10,
            status="warning", detail="证据未分级",
            action="对证据进行质量分级（A/B/C/D）",
        )
    high_quality = sum(1 for e in evidence if isinstance(e, dict) and e.get("quality_grade") in ("A", "B"))
    score = min(100, (high_quality / len(evidence)) * 100)
    return ReadinessItem(
        dimension="证据质量", score=score, weight=0.10,
        status="good" if score >= 60 else "warning",
        detail=f"高质量: {high_quality}/{len(evidence)}",
        action="" if score >= 60 else "替换低质量证据",
    )


def _score_delivery(ss: dict) -> ReadinessItem:
    paper = ss.get("paper_bundle")
    cards = ss.get("analysis_cards", [])
    if not paper and not cards:
        return ReadinessItem(
            dimension="交付完整性", score=0, weight=0.10,
            status="missing", detail="无论文和结果",
            action="完成分析后可在交付中心导出",
        )
    if paper:
        return ReadinessItem(
            dimension="交付完整性", score=100, weight=0.10,
            status="good", detail="论文草稿已生成",
        )
    return ReadinessItem(
        dimension="交付完整性", score=50, weight=0.10,
        status="warning", detail="有结果卡但无论文草稿",
        action="在论文写作中生成草稿",
    )


def _score_consistency(ss: dict) -> ReadinessItem:
    issues = ss.get("consistency_issues", [])
    if issues is None:
        return ReadinessItem(
            dimension="一致性检查", score=80, weight=0.05,
            status="good", detail="未运行检查",
            action="",
        )
    errors = [i for i in issues if getattr(i, "level", "") == "ERROR" or (isinstance(i, dict) and i.get("level") == "ERROR")]
    if errors:
        return ReadinessItem(
            dimension="一致性检查", score=20, weight=0.05,
            status="error", detail=f"{len(errors)} 个阻断错误",
            action="修复一致性检查中的 ERROR 级问题",
        )
    warns = [i for i in issues if getattr(i, "level", "") == "WARN" or (isinstance(i, dict) and i.get("level") == "WARN")]
    score = max(60, 100 - len(warns) * 10)
    return ReadinessItem(
        dimension="一致性检查", score=score, weight=0.05,
        status="good" if not warns else "warning",
        detail=f"{len(warns)} 条警告",
        action="" if not warns else "建议处理一致性警告",
    )


def _determine_next_step(items: list[ReadinessItem]) -> str:
    for it in items:
        if it.status == "error":
            return f"优先处理: {it.action}"
        if it.status == "missing" and it.weight >= 0.15:
            return f"下一步: {it.action}"
    for it in items:
        if it.status == "warning":
            return f"建议: {it.action}"
    return "所有维度状态良好，可准备最终导出"
