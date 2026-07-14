"""ResearchDeliverableBundle — 完整研究交付包。

把论文、结果卡、证据表、图表、清洗记录、方法推荐、健康报告、AI diff 日志统一打包。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import json

from src.paper_writer.draft_bundle import PaperDraftBundle


@dataclass
class ResearchDeliverableBundle:
    """研究交付包。"""
    project_id: str = ""
    title: str = ""
    paper_bundle: Optional[PaperDraftBundle] = None
    analysis_cards: list[Any] = field(default_factory=list)
    evidence_records: list[Any] = field(default_factory=list)
    figures: list[Any] = field(default_factory=list)
    references: list[Any] = field(default_factory=list)
    data_cleaning_log: list[Any] = field(default_factory=list)
    method_recommendations: list[Any] = field(default_factory=list)
    health_report: list[Any] = field(default_factory=list)
    ai_diff_log: dict = field(default_factory=dict)
    export_meta: dict = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    def is_exportable(self) -> tuple[bool, list[str]]:
        """检查交付包是否可以导出。"""
        reasons = []
        if not self.paper_bundle:
            reasons.append("缺少论文 Bundle")
        if not self.analysis_cards:
            reasons.append("缺少统计结果卡")
        if self.health_report:
            errors = [h for h in self.health_report if isinstance(h, dict) and h.get("level") == "ERROR"]
            if errors:
                reasons.append(f"健康检查有 {len(errors)} 个 ERROR")
        return (len(reasons) == 0, reasons)

    def file_manifest(self) -> list[dict[str, str]]:
        """生成交付包文件清单。"""
        base = self.project_id or "research"
        manifest = []

        if self.paper_bundle:
            manifest.append({"path": f"{base}/论文正文.md", "type": "paper"})
        if self.analysis_cards:
            manifest.append({"path": f"{base}/统计结果卡.md", "type": "cards"})
        if self.evidence_records:
            manifest.append({"path": f"{base}/文献证据表.md", "type": "evidence"})
        if self.references:
            manifest.append({"path": f"{base}/参考文献.bib", "type": "references"})
        if self.data_cleaning_log:
            manifest.append({"path": f"{base}/数据清洗记录.md", "type": "cleaning"})
        if self.method_recommendations:
            manifest.append({"path": f"{base}/方法推荐记录.json", "type": "recommendations"})
        if self.health_report:
            manifest.append({"path": f"{base}/项目健康报告.md", "type": "health"})
        if self.ai_diff_log:
            manifest.append({"path": f"{base}/AI差异选择记录.json", "type": "ai_diff"})
        if self.figures:
            for i, _ in enumerate(self.figures):
                manifest.append({"path": f"{base}/figures/figure_{i + 1}.png", "type": "figure"})
        manifest.append({"path": f"{base}/导出元数据.json", "type": "meta"})
        return manifest

    def to_markdown_index(self) -> str:
        """生成交付包索引页（Markdown）。"""
        lines = [f"# 研究交付包: {self.title}\n"]
        lines.append(f"- 项目 ID: {self.project_id}")
        lines.append(f"- 生成时间: {self.created_at}")
        lines.append("")

        exportable, reasons = self.is_exportable()
        if exportable:
            lines.append("**状态: 可导出**\n")
        else:
            lines.append("**状态: 不可导出**")
            for r in reasons:
                lines.append(f"- {r}")
            lines.append("")

        lines.append("## 内容清单\n")
        lines.append(f"| 内容 | 状态 |")
        lines.append(f"|---|---|")
        lines.append(f"| 论文正文 | {'✅' if self.paper_bundle else '❌'} |")
        lines.append(f"| 统计结果卡 | {'✅ ' + str(len(self.analysis_cards)) + ' 张' if self.analysis_cards else '❌'} |")
        lines.append(f"| 文献证据表 | {'✅ ' + str(len(self.evidence_records)) + ' 条' if self.evidence_records else '—'} |")
        lines.append(f"| 参考文献 | {'✅ ' + str(len(self.references)) + ' 条' if self.references else '—'} |")
        lines.append(f"| 数据清洗记录 | {'✅' if self.data_cleaning_log else '—'} |")
        lines.append(f"| 方法推荐 | {'✅' if self.method_recommendations else '—'} |")
        lines.append(f"| 项目健康报告 | {'✅' if self.health_report else '—'} |")
        lines.append(f"| AI 差异记录 | {'✅' if self.ai_diff_log else '—'} |")
        lines.append(f"| 图表 | {'✅ ' + str(len(self.figures)) + ' 张' if self.figures else '—'} |")

        if self.health_report:
            errors = [h for h in self.health_report if isinstance(h, dict) and h.get("level") == "ERROR"]
            warns = [h for h in self.health_report if isinstance(h, dict) and h.get("level") == "WARN"]
            lines.append(f"\n## 健康检查摘要\n")
            lines.append(f"- ERROR: {len(errors)}")
            lines.append(f"- WARN: {len(warns)}")

        return "\n".join(lines)

    def export_meta_dict(self) -> dict:
        """导出元数据。"""
        return {
            "project_id": self.project_id,
            "title": self.title,
            "created_at": self.created_at,
            "paper_sections": list(self.paper_bundle.sections.keys()) if self.paper_bundle else [],
            "analysis_card_count": len(self.analysis_cards),
            "evidence_record_count": len(self.evidence_records),
            "figure_count": len(self.figures),
            "reference_count": len(self.references),
            "health_errors": sum(1 for h in self.health_report if isinstance(h, dict) and h.get("level") == "ERROR"),
            "health_warns": sum(1 for h in self.health_report if isinstance(h, dict) and h.get("level") == "WARN"),
            "has_ai_diff_log": bool(self.ai_diff_log),
            **self.export_meta,
        }
