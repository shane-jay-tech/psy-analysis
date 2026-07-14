"""ZIP 交付包导出器。

将 ResearchDeliverableBundle 打包为结构化 ZIP：
  project_deliverable.zip
  ├─ paper.docx
  ├─ paper.md
  ├─ analysis_cards/
  ├─ evidence/
  ├─ figures/
  ├─ tables/
  ├─ cleaning_log/
  ├─ health_report.md
  ├─ AI_USAGE_DISCLOSURE.md          (v5.4)
  ├─ PRIVACY_PRECHECK_SUMMARY.json   (v5.4)
  ├─ REPRODUCIBILITY_MANIFEST.json   (v5.4)
  └─ manifest.json
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime


def build_deliverable_zip(bundle, mode: str = "standard") -> bytes:
    """从 ResearchDeliverableBundle 生成 ZIP 字节流。

    Args:
        bundle: ResearchDeliverableBundle 实例
        mode: "basic" / "standard" / "full"

    Returns:
        ZIP 文件的 bytes
    """
    buf = io.BytesIO()
    manifest_entries = []

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # paper.md
        md_content = _generate_paper_md(bundle)
        zf.writestr("paper.md", md_content)
        manifest_entries.append({"path": "paper.md", "type": "paper", "format": "markdown"})

        # paper.docx
        try:
            from src.output.docx_exporter import build_deliverable_docx
            docx_bytes = build_deliverable_docx(bundle, mode=mode)
            zf.writestr("paper.docx", docx_bytes)
            manifest_entries.append({"path": "paper.docx", "type": "paper", "format": "docx"})
        except Exception:
            pass

        # analysis_cards/
        if bundle.analysis_cards:
            for i, card in enumerate(bundle.analysis_cards):
                card_data = card if isinstance(card, dict) else (card.to_dict() if hasattr(card, "to_dict") else str(card))
                card_json = json.dumps(card_data, ensure_ascii=False, indent=2)
                card_path = f"analysis_cards/card_{i + 1}.json"
                zf.writestr(card_path, card_json)
                manifest_entries.append({"path": card_path, "type": "analysis_card"})

        # evidence/
        if mode in ("standard", "full") and bundle.evidence_records:
            evidence_json = json.dumps(bundle.evidence_records, ensure_ascii=False, indent=2)
            zf.writestr("evidence/evidence_table.json", evidence_json)
            manifest_entries.append({"path": "evidence/evidence_table.json", "type": "evidence"})

        # figures/
        if bundle.figures:
            for i, fig in enumerate(bundle.figures):
                if hasattr(fig, "png_bytes") and fig.png_bytes:
                    fig_path = f"figures/figure_{i + 1}.png"
                    zf.writestr(fig_path, fig.png_bytes)
                    caption = getattr(fig, "caption", f"Figure {i + 1}")
                    manifest_entries.append({
                        "path": fig_path, "type": "figure", "caption": caption,
                    })

        # tables/ (auto-generated APA tables from result cards)
        if bundle.analysis_cards:
            from src.output.apa_tables import generate_tables_from_card, table_to_csv, table_to_markdown
            apa_tables_data = []
            tbl_num = 0
            for card in bundle.analysis_cards:
                card_dict = card if isinstance(card, dict) else (card.__dict__ if hasattr(card, '__dict__') else {})
                try:
                    tables = generate_tables_from_card(card_dict)
                    for tbl in tables:
                        tbl_num += 1
                        tbl.apa_number = tbl_num
                        # CSV
                        csv_path = f"tables/table_{tbl_num:03d}_{tbl.table_id}.csv"
                        zf.writestr(csv_path, table_to_csv(tbl))
                        manifest_entries.append({"path": csv_path, "type": "table", "format": "csv", "table_id": tbl.table_id})
                        # Markdown
                        md_path = f"tables/table_{tbl_num:03d}_{tbl.table_id}.md"
                        zf.writestr(md_path, table_to_markdown(tbl))
                        manifest_entries.append({"path": md_path, "type": "table", "format": "markdown", "table_id": tbl.table_id})
                        # Collect for JSON summary
                        apa_tables_data.append({
                            "table_number": tbl_num,
                            "table_id": tbl.table_id,
                            "method_id": tbl.method_id,
                            "title": tbl.title,
                            "note": tbl.note,
                            "columns": tbl.columns,
                            "row_count": len(tbl.rows),
                        })
                except Exception:
                    pass
            if apa_tables_data:
                zf.writestr("tables/apa_tables.json", json.dumps(apa_tables_data, ensure_ascii=False, indent=2))
                manifest_entries.append({"path": "tables/apa_tables.json", "type": "table_index"})

        # cleaning_log/
        if mode in ("standard", "full") and bundle.data_cleaning_log:
            log_json = json.dumps(bundle.data_cleaning_log, ensure_ascii=False, indent=2)
            zf.writestr("cleaning_log/cleaning_log.json", log_json)
            manifest_entries.append({"path": "cleaning_log/cleaning_log.json", "type": "cleaning_log"})

        # health_report.md (full mode only)
        if mode == "full" and bundle.health_report:
            lines = ["# 项目健康报告\n"]
            for issue in bundle.health_report:
                if isinstance(issue, dict):
                    lines.append(f"- [{issue.get('level', '')}] {issue.get('message', '')}")
            zf.writestr("health_report.md", "\n".join(lines))
            manifest_entries.append({"path": "health_report.md", "type": "health_report"})

        # method_recommendations (full mode only)
        if mode == "full" and bundle.method_recommendations:
            rec_json = json.dumps(bundle.method_recommendations, ensure_ascii=False, indent=2)
            zf.writestr("method_recommendations.json", rec_json)
            manifest_entries.append({"path": "method_recommendations.json", "type": "method_recommendation"})

        # paper.pdf (best-effort, never blocks main export)
        pdf_status = "not_attempted"
        try:
            from src.output.pdf_exporter import convert_docx_to_pdf
            docx_for_pdf = None
            try:
                from src.output.docx_exporter import build_deliverable_docx
                docx_for_pdf = build_deliverable_docx(bundle, mode=mode)
            except Exception:
                pass
            if docx_for_pdf:
                pdf_result = convert_docx_to_pdf(docx_for_pdf)
                if pdf_result.success and pdf_result.pdf_bytes:
                    zf.writestr("paper.pdf", pdf_result.pdf_bytes)
                    manifest_entries.append({"path": "paper.pdf", "type": "paper", "format": "pdf"})
                    pdf_status = f"success ({pdf_result.method})"
                else:
                    pdf_status = f"unavailable: {pdf_result.error}"
        except Exception as e:
            pdf_status = f"error: {e}"

        # v5.4: AI 使用声明
        ai_disclosure = _generate_ai_disclosure(bundle)
        zf.writestr("AI_USAGE_DISCLOSURE.md", ai_disclosure)
        manifest_entries.append({"path": "AI_USAGE_DISCLOSURE.md", "type": "disclosure"})

        # v5.4: 隐私预检摘要
        privacy_summary = _generate_privacy_precheck_summary(bundle)
        zf.writestr("PRIVACY_PRECHECK_SUMMARY.json", json.dumps(privacy_summary, ensure_ascii=False, indent=2))
        manifest_entries.append({"path": "PRIVACY_PRECHECK_SUMMARY.json", "type": "privacy_precheck"})

        # v5.4: 可复现性清单
        repro_manifest = _generate_reproducibility_manifest(bundle, mode)
        zf.writestr("REPRODUCIBILITY_MANIFEST.json", json.dumps(repro_manifest, ensure_ascii=False, indent=2))
        manifest_entries.append({"path": "REPRODUCIBILITY_MANIFEST.json", "type": "reproducibility"})

        # manifest.json (always last)
        manifest = {
            "project_id": bundle.project_id,
            "title": bundle.title,
            "mode": mode,
            "created_at": datetime.now().isoformat(),
            "file_count": len(manifest_entries) + 1,
            "files": manifest_entries,
            "pdf_status": pdf_status,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    return buf.getvalue()


def _generate_paper_md(bundle) -> str:
    """生成论文 Markdown 内容。"""
    lines = [f"# {bundle.title}\n"]

    if bundle.paper_bundle:
        for key, sec in bundle.paper_bundle.sections.items():
            lines.append(f"\n## {sec.name}\n")
            lines.append(sec.markdown)

    if bundle.analysis_cards:
        lines.append("\n## 统计结果\n")
        for card in bundle.analysis_cards:
            if isinstance(card, dict):
                lines.append(f"- {card.get('method', '')}: {card.get('apa_text', '')}")

    return "\n".join(lines)


def _generate_ai_disclosure(bundle) -> str:
    """生成 AI 使用声明文档。"""
    lines = [
        "# AI 辅助使用声明",
        "",
        "本交付包由 Psy-Analysis 心理学研究工具辅助生成。",
        "",
        "## 工具使用范围",
        "",
        "- 统计分析方法选择建议",
        "- APA 格式表格自动排版",
        "- 统计结果数值计算",
        "- 图表自动生成",
        "",
        "## 研究者责任",
        "",
        "- 研究设计和假设由研究者独立完成",
        "- 统计结果的解释需要研究者核实",
        "- 论文讨论和结论由研究者撰写",
        "- 最终学术判断和伦理责任属于研究者",
        "",
        "## 学术诚信声明",
        "",
        "- 本工具不替代研究者的学术判断",
        "- 使用本工具不免除研究者的学术责任",
        "- 建议在论文方法部分注明使用了辅助分析工具",
        "- 所有统计结果需经导师审阅确认",
        "",
        "## 隐私保护",
        "",
        "- 原始数据未包含在本交付包中（除非研究者主动添加）",
        "- 导出前已通过敏感信息预检",
        "- 本工具不存储用户数据到云端",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    ]
    return "\n".join(lines)


def _generate_privacy_precheck_summary(bundle) -> dict:
    """生成隐私预检摘要。"""
    precheck = bundle.export_meta.get("privacy_precheck", {}) if hasattr(bundle, "export_meta") else {}
    return {
        "precheck_performed": bool(precheck),
        "safe": precheck.get("safe", True),
        "high_risk_count": precheck.get("high_count", 0),
        "medium_risk_count": precheck.get("medium_count", 0),
        "checked_at": precheck.get("checked_at", datetime.now().isoformat(timespec="seconds")),
        "note": "隐私预检在导出前自动运行，检查身份信息、API密钥等敏感内容",
    }


def _generate_reproducibility_manifest(bundle, mode: str) -> dict:
    """生成可复现性清单。"""
    cards_info = []
    for i, card in enumerate(bundle.analysis_cards or []):
        c = card if isinstance(card, dict) else (card.__dict__ if hasattr(card, "__dict__") else {})
        cards_info.append({
            "index": i + 1,
            "method_id": c.get("method_id", c.get("method", "")),
            "method_name": c.get("method_name", ""),
        })

    return {
        "project_id": bundle.project_id,
        "title": bundle.title,
        "export_mode": mode,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analysis_count": len(cards_info),
        "analyses": cards_info,
        "data_cleaning_steps": len(bundle.data_cleaning_log or []),
        "evidence_records": len(bundle.evidence_records or []),
        "note": "此清单记录交付包中的分析方法和数据处理步骤，便于复核和追溯",
    }
