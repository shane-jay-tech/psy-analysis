"""专业一致性检查器 v3。

v1: 正则启发式（7 项）
v2: 结构化证据链检查（15 项），覆盖结果卡、图表、证据、manifest、PDF
v3: 表格追溯 & 隐私预检（22 项），新增 table source/ref/manifest/numbering/note + privacy + golden

在导出前检查不同交付资产之间的一致性，发现明显的专业错误。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class ConsistencyIssue:
    """一致性问题（v2 增强 schema）。"""
    level: str  # ERROR / WARN / INFO
    code: str
    title: str
    detail: str
    source: str
    action: str
    check_id: str = ""
    target_type: str = ""
    target_id: str = ""
    blocking: bool = False
    confidence: str = "high"

    def __post_init__(self):
        if not self.check_id:
            self.check_id = self.code
        if self.level == "ERROR":
            self.blocking = True


def check_consistency(bundle) -> list[ConsistencyIssue]:
    """对 ResearchDeliverableBundle 执行全部一致性检查（v3: 22 项）。"""
    issues = []
    # v1 checks (7)
    issues.extend(_check_result_card_binding(bundle))
    issues.extend(_check_stat_consistency(bundle))
    issues.extend(_check_citation_refs(bundle))
    issues.extend(_check_evidence_coverage(bundle))
    issues.extend(_check_figure_refs(bundle))
    issues.extend(_check_method_match(bundle))
    issues.extend(_check_variable_naming(bundle))
    # v2 new checks (8)
    issues.extend(_check_effect_size_coverage(bundle))
    issues.extend(_check_orphan_figures(bundle))
    issues.extend(_check_recommendation_execution_match(bundle))
    issues.extend(_check_card_apa_text_completeness(bundle))
    issues.extend(_check_evidence_quality(bundle))
    issues.extend(_check_manifest_integrity(bundle))
    issues.extend(_check_figure_card_binding(bundle))
    issues.extend(_check_template_asset_completeness(bundle))
    # v3 new checks (7): table & privacy
    issues.extend(_check_table_source_card(bundle))
    issues.extend(_check_table_text_reference(bundle))
    issues.extend(_check_table_manifest_entry(bundle))
    issues.extend(_check_privacy_precheck_status(bundle))
    issues.extend(_check_table_numbering_continuous(bundle))
    issues.extend(_check_table_note_complete(bundle))
    issues.extend(_check_golden_coverage_mark(bundle))
    return issues


def _check_result_card_binding(bundle) -> list[ConsistencyIssue]:
    """检查结果章是否有结果卡绑定。"""
    issues = []
    if not bundle.paper_bundle:
        return issues

    sections = bundle.paper_bundle.sections
    has_result_section = any(
        "结果" in sec.name or "result" in sec.name.lower()
        for sec in sections.values()
    )
    if has_result_section and not bundle.analysis_cards:
        issues.append(ConsistencyIssue(
            level="ERROR",
            code="RESULT_NO_CARD",
            title="结果章缺少结果卡绑定",
            detail="论文有结果章但无统计结果卡，结果不可复核",
            source="paper_bundle.sections / analysis_cards",
            action="请在数据分析中生成结果卡",
        ))
    return issues


def _check_stat_consistency(bundle) -> list[ConsistencyIssue]:
    """检查论文正文中的统计数字是否与结果卡一致。"""
    issues = []
    if not bundle.paper_bundle:
        return issues

    paper_text = ""
    for sec in bundle.paper_bundle.sections.values():
        paper_text += sec.markdown + "\n"

    stat_pattern = re.compile(
        r"[tFrχ²]\s*[(（]\s*[\d.]+[)）]\s*=\s*[\d.]+|"
        r"p\s*[<>=]\s*\.?\d+|"
        r"r\s*=\s*[−\-.]?\d[\d.]*"
    )
    paper_stats = stat_pattern.findall(paper_text)

    card_apa_texts = []
    for card in bundle.analysis_cards:
        if isinstance(card, dict):
            apa = card.get("apa_text", "")
            if apa:
                card_apa_texts.append(apa)
        elif hasattr(card, "apa_text"):
            card_apa_texts.append(card.apa_text)

    if paper_stats and not card_apa_texts:
        issues.append(ConsistencyIssue(
            level="ERROR",
            code="STAT_NO_SOURCE",
            title="论文统计数字无结果卡来源",
            detail=f"论文正文发现 {len(paper_stats)} 处统计报告但无结果卡 APA 文本",
            source="paper_bundle / analysis_cards",
            action="确保结果卡覆盖论文中引用的所有统计结果",
        ))
    return issues


def _check_citation_refs(bundle) -> list[ConsistencyIssue]:
    """检查正文引用是否都在参考文献/证据表中。"""
    issues = []
    if not bundle.paper_bundle:
        return issues

    paper_text = ""
    for sec in bundle.paper_bundle.sections.values():
        paper_text += sec.markdown + "\n"

    cite_pattern = re.compile(r"[（(]([A-Za-z]+(?:\s+(?:et al\.)?)?,?\s*\d{4})[）)]")
    citations = cite_pattern.findall(paper_text)

    evidence_keys = set()
    for rec in (bundle.evidence_records or []):
        if isinstance(rec, dict):
            key = rec.get("citation_key", "")
            if key:
                evidence_keys.add(key.lower())

    for cite in citations:
        author_year = cite.strip().lower().replace(" ", "").replace(",", "")
        matched = any(author_year[:6] in k for k in evidence_keys)
        if not matched and evidence_keys:
            issues.append(ConsistencyIssue(
                level="ERROR",
                code="CITATION_MISSING",
                title="正文引用不在证据表中",
                detail=f"引用 '{cite}' 未在证据表中找到对应记录",
                source="paper_bundle / evidence_records",
                action=f"在证据表中添加 {cite} 的记录",
            ))
            break  # only report first missing to avoid flooding

    return issues


def _check_evidence_coverage(bundle) -> list[ConsistencyIssue]:
    """检查核心论点是否有证据支撑。"""
    issues = []
    if not bundle.paper_bundle:
        return issues

    sections = bundle.paper_bundle.sections
    has_intro = any("引言" in s.name or "introduction" in s.name.lower() for s in sections.values())
    has_discussion = any("讨论" in s.name or "discussion" in s.name.lower() for s in sections.values())

    if (has_intro or has_discussion) and not bundle.evidence_records:
        issues.append(ConsistencyIssue(
            level="WARN",
            code="NO_EVIDENCE",
            title="核心论点无证据记录",
            detail="论文有引言/讨论章但无文献证据表，综述可信度不足",
            source="paper_bundle / evidence_records",
            action="在证据表中添加支撑论点的文献",
        ))
    return issues


def _check_figure_refs(bundle) -> list[ConsistencyIssue]:
    """检查论文中引用的图表编号是否有对应图表。"""
    issues = []
    if not bundle.paper_bundle:
        return issues

    paper_text = ""
    for sec in bundle.paper_bundle.sections.values():
        paper_text += sec.markdown + "\n"

    fig_refs = re.findall(r"[图Figure]\s*(\d+)", paper_text)
    actual_count = len(bundle.figures) if bundle.figures else 0

    for ref_num in fig_refs:
        if int(ref_num) > actual_count:
            issues.append(ConsistencyIssue(
                level="ERROR",
                code="FIGURE_MISSING",
                title="引用的图表不存在",
                detail=f"正文引用了图 {ref_num}，但交付包仅有 {actual_count} 张图",
                source="paper_bundle / figures",
                action=f"生成图 {ref_num} 或修改引用编号",
            ))
            break

    return issues


def _check_method_match(bundle) -> list[ConsistencyIssue]:
    """检查实际分析方法是否与推荐方法一致。"""
    issues = []
    if not bundle.analysis_cards or not bundle.method_recommendations:
        return issues

    rec_methods = set()
    for rec in bundle.method_recommendations:
        if isinstance(rec, dict):
            r = rec.get("recommendation", "")
            if r:
                rec_methods.add(r)

    card_methods = set()
    for card in bundle.analysis_cards:
        if isinstance(card, dict):
            m = card.get("method_zh", card.get("method", ""))
            if m:
                card_methods.add(m)

    if rec_methods and card_methods and not rec_methods.intersection(card_methods):
        issues.append(ConsistencyIssue(
            level="WARN",
            code="METHOD_MISMATCH",
            title="实际分析方法与推荐方法不同",
            detail=f"推荐: {', '.join(rec_methods)} | 实际: {', '.join(card_methods)}",
            source="method_recommendations / analysis_cards",
            action="如有理由改用其他方法，请在方法章说明",
        ))
    return issues


def _check_variable_naming(bundle) -> list[ConsistencyIssue]:
    """检查变量名在各处是否一致。"""
    issues = []
    if not bundle.paper_bundle or not bundle.analysis_cards:
        return issues

    card_vars = set()
    for card in bundle.analysis_cards:
        if isinstance(card, dict):
            apa = card.get("apa_text", "")
            card_vars.update(re.findall(r"[一-鿿]+得分|[一-鿿]+量表", apa))

    if not card_vars:
        return issues

    paper_text = ""
    for sec in bundle.paper_bundle.sections.values():
        paper_text += sec.markdown + "\n"

    paper_vars = set(re.findall(r"[一-鿿]+得分|[一-鿿]+量表", paper_text))

    if card_vars:
        card_only = card_vars - paper_vars
        if len(card_only) > 2:
            issues.append(ConsistencyIssue(
                level="WARN",
                code="VAR_NAME_INCONSISTENT",
                title="变量名在结果卡和论文中不一致",
                detail=f"结果卡有但论文未提及: {', '.join(list(card_only)[:3])}",
                source="analysis_cards / paper_bundle",
                action="统一变量命名，确保论文正文与结果卡使用相同术语",
            ))

    return issues


# ---------------------------------------------------------------------------
# v2 新增检查项 (8)
# ---------------------------------------------------------------------------

def _check_effect_size_coverage(bundle) -> list[ConsistencyIssue]:
    """检查结果卡是否都包含效应量。"""
    issues = []
    if not bundle.analysis_cards:
        return issues

    methods_needing_es = {
        "independent_ttest", "paired_ttest", "one_way_anova",
        "pearson_corr", "multiple_regression", "mann_whitney",
        "wilcoxon", "kruskal_wallis", "two_way_anova",
    }
    for i, card in enumerate(bundle.analysis_cards):
        if isinstance(card, dict):
            method = card.get("method_id", card.get("method", ""))
            if method in methods_needing_es:
                effect_sizes = card.get("effect_sizes", [])
                if not effect_sizes:
                    issues.append(ConsistencyIssue(
                        level="WARN",
                        code="MISSING_EFFECT_SIZE",
                        title="结果卡缺少效应量",
                        detail=f"结果卡 #{i+1} ({method}) 未包含效应量",
                        source=f"analysis_cards[{i}]",
                        action="确保分析结果包含效应量（如 Cohen's d、η²、r 等）",
                        target_type="analysis_card",
                        target_id=str(i),
                    ))
                    break
    return issues


def _check_orphan_figures(bundle) -> list[ConsistencyIssue]:
    """检查 ZIP/交付包中有图表但正文未引用。"""
    issues = []
    if not bundle.figures or not bundle.paper_bundle:
        return issues

    paper_text = ""
    for sec in bundle.paper_bundle.sections.values():
        paper_text += sec.markdown + "\n"

    has_figure_ref = bool(re.search(r"[图Figure]\s*\d+|见图|如图|参见图", paper_text))

    if bundle.figures and not has_figure_ref:
        issues.append(ConsistencyIssue(
            level="WARN",
            code="ORPHAN_FIGURE",
            title="孤立图表",
            detail=f"交付包有 {len(bundle.figures)} 张图表，但论文正文未引用任何图表",
            source="figures / paper_bundle",
            action="在结果部分添加图表引用（如'如图 1 所示'）",
            target_type="figure",
        ))
    return issues


def _check_recommendation_execution_match(bundle) -> list[ConsistencyIssue]:
    """检查推荐方法与实际执行方法是否对齐（精确版）。"""
    issues = []
    if not bundle.analysis_cards or not bundle.method_recommendations:
        return issues

    recommended_ids = set()
    for rec in bundle.method_recommendations:
        if isinstance(rec, dict):
            method_id = rec.get("method_id", rec.get("primary_method", ""))
            if method_id:
                recommended_ids.add(method_id)

    executed_ids = set()
    for card in bundle.analysis_cards:
        if isinstance(card, dict):
            method_id = card.get("method_id", card.get("method", ""))
            if method_id:
                executed_ids.add(method_id)

    if recommended_ids and executed_ids:
        mismatch = executed_ids - recommended_ids
        if mismatch and not recommended_ids.intersection(executed_ids):
            issues.append(ConsistencyIssue(
                level="WARN",
                code="REC_EXEC_MISMATCH",
                title="推荐方法与执行方法不一致",
                detail=f"推荐: {', '.join(recommended_ids)} | 执行: {', '.join(executed_ids)}",
                source="method_recommendations / analysis_cards",
                action="如有理由改用其他方法，请在方法章说明理由",
                confidence="medium",
            ))
    return issues


def _check_card_apa_text_completeness(bundle) -> list[ConsistencyIssue]:
    """检查结果卡的 APA 文本是否完整。"""
    issues = []
    if not bundle.analysis_cards:
        return issues

    for i, card in enumerate(bundle.analysis_cards):
        if isinstance(card, dict):
            apa_text = card.get("apa_text", "")
            if not apa_text or len(apa_text) < 10:
                issues.append(ConsistencyIssue(
                    level="ERROR",
                    code="APA_TEXT_INCOMPLETE",
                    title="结果卡 APA 文本不完整",
                    detail=f"结果卡 #{i+1} 的 APA 文本过短或为空",
                    source=f"analysis_cards[{i}]",
                    action="重新执行分析或手动补充 APA 结果文本",
                    target_type="analysis_card",
                    target_id=str(i),
                ))
                break
    return issues


def _check_evidence_quality(bundle) -> list[ConsistencyIssue]:
    """检查证据记录的基本质量。"""
    issues = []
    if not bundle.evidence_records:
        return issues

    incomplete_count = 0
    for rec in bundle.evidence_records:
        if isinstance(rec, dict):
            key = rec.get("citation_key", "")
            claim = rec.get("claim", "")
            if not key or not claim:
                incomplete_count += 1

    if incomplete_count > 0:
        issues.append(ConsistencyIssue(
            level="WARN",
            code="EVIDENCE_INCOMPLETE",
            title="证据记录不完整",
            detail=f"{incomplete_count} 条证据缺少 citation_key 或 claim",
            source="evidence_records",
            action="补充每条证据的引用标识和核心论点",
            target_type="evidence",
        ))
    return issues


def _check_manifest_integrity(bundle) -> list[ConsistencyIssue]:
    """检查交付包 manifest 完整性。"""
    issues = []
    manifest = bundle.file_manifest() if hasattr(bundle, "file_manifest") else None
    if manifest is None:
        return issues

    if not manifest:
        issues.append(ConsistencyIssue(
            level="ERROR",
            code="MANIFEST_EMPTY",
            title="交付包 manifest 为空",
            detail="file_manifest() 返回空列表，导出结构异常",
            source="bundle.file_manifest()",
            action="确保交付包至少包含论文正文",
            target_type="manifest",
        ))
    return issues


def _check_figure_card_binding(bundle) -> list[ConsistencyIssue]:
    """检查图表是否与结果卡绑定。"""
    issues = []
    if not bundle.figures:
        return issues

    unbound = 0
    for fig in bundle.figures:
        rec_id = getattr(fig, "recommendation_id", "") if hasattr(fig, "recommendation_id") else ""
        method = getattr(fig, "method", "") if hasattr(fig, "method") else ""
        if not rec_id and not method:
            unbound += 1

    if unbound > 0:
        issues.append(ConsistencyIssue(
            level="WARN",
            code="FIGURE_UNBOUND",
            title="图表未绑定结果来源",
            detail=f"{unbound} 张图表未关联 recommendation_id 或 method",
            source="figures",
            action="确保图表通过 generate_figures_from_card() 生成以保持来源追踪",
            target_type="figure",
            confidence="medium",
        ))
    return issues


def _check_template_asset_completeness(bundle) -> list[ConsistencyIssue]:
    """检查从模板创建的项目是否有完整资产。"""
    issues = []
    template_source = getattr(bundle, "template_source", None)
    if not template_source:
        return issues

    if not bundle.analysis_cards:
        issues.append(ConsistencyIssue(
            level="WARN",
            code="TEMPLATE_NO_ANALYSIS",
            title="模板项目未执行分析",
            detail=f"项目来自模板 '{template_source}'，但尚未生成分析结果",
            source="template_source / analysis_cards",
            action="使用推荐方法完成数据分析",
            target_type="template",
        ))
    return issues


# ---------------------------------------------------------------------------
# v3 新增检查项 (7): 表格 & 隐私
# ---------------------------------------------------------------------------

def _check_table_source_card(bundle) -> list[ConsistencyIssue]:
    """检查所有 APA 表格是否能追溯到结果卡片。"""
    issues = []
    tables = getattr(bundle, "tables", None)
    if not tables:
        return issues

    card_ids = set()
    for card in (bundle.analysis_cards or []):
        if isinstance(card, dict):
            cid = card.get("card_id", card.get("id", ""))
            if cid:
                card_ids.add(cid)
        elif hasattr(card, "card_id"):
            card_ids.add(card.card_id)

    untraced = []
    for i, table in enumerate(tables):
        source_card = None
        if isinstance(table, dict):
            source_card = table.get("source_card_id", table.get("card_id", ""))
        elif hasattr(table, "source_card_id"):
            source_card = table.source_card_id
        if not source_card or (card_ids and source_card not in card_ids):
            label = ""
            if isinstance(table, dict):
                label = table.get("label", table.get("title", f"#{i+1}"))
            else:
                label = getattr(table, "label", f"#{i+1}")
            untraced.append(label)

    if untraced:
        issues.append(ConsistencyIssue(
            level="ERROR",
            code="TABLE_NO_SOURCE_CARD",
            title="APA 表格无法追溯到结果卡",
            detail=f"{len(untraced)} 张表格缺少 source_card_id 或指向不存在的卡: {', '.join(untraced[:3])}",
            source="tables / analysis_cards",
            action="确保每张表格通过 source_card_id 关联到对应的结果卡",
            check_id="table_source_card",
            target_type="table",
        ))
    return issues


def _check_table_text_reference(bundle) -> list[ConsistencyIssue]:
    """检查正文引用的表格是否存在。"""
    issues = []
    if not bundle.paper_bundle:
        return issues

    paper_text = ""
    for sec in bundle.paper_bundle.sections.values():
        paper_text += sec.markdown + "\n"

    # Match patterns like "表1", "表 2", "Table 1", "Table 3"
    table_refs = re.findall(r"(?:表|Table)\s*(\d+)", paper_text)
    if not table_refs:
        return issues

    tables = getattr(bundle, "tables", None) or []
    actual_count = len(tables)

    missing_refs = []
    for ref_num in table_refs:
        if int(ref_num) > actual_count:
            missing_refs.append(ref_num)

    if missing_refs:
        issues.append(ConsistencyIssue(
            level="ERROR",
            code="TABLE_REF_MISSING",
            title="正文引用的表格不存在",
            detail=f"正文引用了表 {', '.join(missing_refs[:5])}，但交付包仅有 {actual_count} 张表格",
            source="paper_bundle / tables",
            action="生成缺失的表格或修改正文引用编号",
            check_id="table_text_reference",
            target_type="table",
        ))
    return issues


def _check_table_manifest_entry(bundle) -> list[ConsistencyIssue]:
    """检查 manifest 中的表格文件是否真实存在。"""
    issues = []
    manifest = bundle.file_manifest() if hasattr(bundle, "file_manifest") else None
    if manifest is None:
        return issues

    tables = getattr(bundle, "tables", None) or []
    table_files_in_manifest = []
    for entry in manifest:
        path = entry if isinstance(entry, str) else (entry.get("path", "") if isinstance(entry, dict) else "")
        if re.search(r"tables/|apa_table", path, re.IGNORECASE):
            table_files_in_manifest.append(path)

    if not table_files_in_manifest:
        return issues

    # Check if manifest table entries have corresponding table objects
    if table_files_in_manifest and not tables:
        issues.append(ConsistencyIssue(
            level="ERROR",
            code="TABLE_MANIFEST_ORPHAN",
            title="manifest 表格文件无对应表格对象",
            detail=f"manifest 列出 {len(table_files_in_manifest)} 个表格文件，但 bundle.tables 为空",
            source="file_manifest / tables",
            action="确保 manifest 中的表格文件与实际生成的表格一致",
            check_id="table_manifest_entry",
            target_type="table",
        ))
    return issues


def _check_privacy_precheck_status(bundle) -> list[ConsistencyIssue]:
    """检查导出包是否包含隐私预检结果。"""
    issues = []
    privacy_result = getattr(bundle, "privacy_precheck", None)
    if privacy_result is None:
        # Also check alternative attribute names
        privacy_result = getattr(bundle, "privacy_check_result", None)

    if privacy_result is None:
        issues.append(ConsistencyIssue(
            level="WARN",
            code="PRIVACY_NO_PRECHECK",
            title="导出包缺少隐私预检结果",
            detail="bundle 未包含 privacy_precheck 字段，建议导出前运行隐私预检",
            source="bundle.privacy_precheck",
            action="在导出前运行隐私预检（privacy precheck），确保不含可识别个人信息",
            check_id="privacy_precheck_status",
            target_type="privacy",
        ))
    elif isinstance(privacy_result, dict):
        passed = privacy_result.get("passed", privacy_result.get("status", "") == "pass")
        if not passed:
            issues.append(ConsistencyIssue(
                level="ERROR",
                code="PRIVACY_PRECHECK_FAILED",
                title="隐私预检未通过",
                detail=f"隐私预检结果: {privacy_result.get('reason', '未通过')}",
                source="bundle.privacy_precheck",
                action="修复隐私问题后重新导出",
                check_id="privacy_precheck_status",
                target_type="privacy",
            ))
    return issues


def _check_table_numbering_continuous(bundle) -> list[ConsistencyIssue]:
    """检查表格编号是否连续。"""
    issues = []
    tables = getattr(bundle, "tables", None)
    if not tables or len(tables) < 2:
        return issues

    numbers = []
    for table in tables:
        num = None
        if isinstance(table, dict):
            num = table.get("number", table.get("table_number", None))
            if num is None:
                # Try to extract from label like "Table 1" or "表1"
                label = table.get("label", "")
                match = re.search(r"(\d+)", label)
                if match:
                    num = int(match.group(1))
        elif hasattr(table, "number"):
            num = table.number
        if num is not None:
            numbers.append(int(num))

    if not numbers:
        return issues

    numbers.sort()
    gaps = []
    for i in range(len(numbers) - 1):
        if numbers[i + 1] - numbers[i] > 1:
            gaps.append(f"{numbers[i]}→{numbers[i+1]}")

    if gaps:
        issues.append(ConsistencyIssue(
            level="WARN",
            code="TABLE_NUMBER_GAP",
            title="表格编号不连续",
            detail=f"表格编号存在跳跃: {', '.join(gaps[:3])}",
            source="tables",
            action="重新编号表格，确保从 1 开始连续递增",
            check_id="table_numbering_continuous",
            target_type="table",
        ))
    return issues


def _check_table_note_complete(bundle) -> list[ConsistencyIssue]:
    """检查表注是否包含 N、缩写说明。"""
    issues = []
    tables = getattr(bundle, "tables", None)
    if not tables:
        return issues

    incomplete_notes = []
    for i, table in enumerate(tables):
        note = ""
        if isinstance(table, dict):
            note = table.get("note", table.get("table_note", ""))
        elif hasattr(table, "note"):
            note = table.note or ""

        if not note:
            label = ""
            if isinstance(table, dict):
                label = table.get("label", f"#{i+1}")
            else:
                label = getattr(table, "label", f"#{i+1}")
            incomplete_notes.append(label)
            continue

        # Check for sample size indicator
        has_n = bool(re.search(r"[Nn]\s*=\s*\d+|样本量|被试数|人数", note))
        if not has_n:
            label = ""
            if isinstance(table, dict):
                label = table.get("label", f"#{i+1}")
            else:
                label = getattr(table, "label", f"#{i+1}")
            incomplete_notes.append(label)

    if incomplete_notes:
        issues.append(ConsistencyIssue(
            level="WARN",
            code="TABLE_NOTE_INCOMPLETE",
            title="表注缺少必要信息",
            detail=f"{len(incomplete_notes)} 张表的表注缺少 N 或缩写说明: {', '.join(incomplete_notes[:3])}",
            source="tables",
            action="在表注中添加样本量 (N = ...) 和缩写含义说明",
            check_id="table_note_complete",
            target_type="table",
        ))
    return issues


def _check_golden_coverage_mark(bundle) -> list[ConsistencyIssue]:
    """高风险方法是否有 golden 标记。"""
    issues = []
    if not bundle.analysis_cards:
        return issues

    # High-risk methods that should have golden test coverage
    high_risk_methods = {
        "multiple_regression", "logistic_regression", "mediation",
        "moderation", "structural_equation", "factor_analysis",
        "multilevel_model", "path_analysis", "sem",
    }

    unmarked = []
    for i, card in enumerate(bundle.analysis_cards):
        if isinstance(card, dict):
            method_id = card.get("method_id", card.get("method", ""))
            if method_id in high_risk_methods:
                golden = card.get("golden", card.get("golden_mark", False))
                if not golden:
                    unmarked.append(f"#{i+1}({method_id})")
        elif hasattr(card, "method_id"):
            if card.method_id in high_risk_methods:
                golden = getattr(card, "golden", getattr(card, "golden_mark", False))
                if not golden:
                    unmarked.append(f"#{i+1}({card.method_id})")

    if unmarked:
        issues.append(ConsistencyIssue(
            level="WARN",
            code="GOLDEN_MARK_MISSING",
            title="高风险方法缺少 golden 标记",
            detail=f"{len(unmarked)} 张高风险结果卡未标记 golden: {', '.join(unmarked[:3])}",
            source="analysis_cards",
            action="为高风险统计方法的结果卡设置 golden=True 以启用回归测试保护",
            check_id="golden_coverage_mark",
            target_type="analysis_card",
            confidence="medium",
        ))
    return issues
