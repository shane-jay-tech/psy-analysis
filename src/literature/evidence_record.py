"""文献证据表 — 把审核通过的文献转化为论文可用的证据记录。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import csv
import io
import json


@dataclass
class EvidenceRecord:
    """单条文献证据记录。"""
    literature_id: str
    citation_key: str
    claim: str
    evidence_quote: str = ""
    research_design: str = ""
    sample: str = ""
    variables: list[str] = field(default_factory=list)
    measurement_tools: list[str] = field(default_factory=list)
    statistical_methods: list[str] = field(default_factory=list)
    main_findings: str = ""
    limitations: str = ""
    section_target: str = ""  # introduction / method / discussion / limitation
    tags: list[str] = field(default_factory=list)
    confidence_note: str = ""

    def to_dict(self) -> dict:
        return {
            "literature_id": self.literature_id,
            "citation_key": self.citation_key,
            "claim": self.claim,
            "evidence_quote": self.evidence_quote,
            "research_design": self.research_design,
            "sample": self.sample,
            "variables": self.variables,
            "measurement_tools": self.measurement_tools,
            "statistical_methods": self.statistical_methods,
            "main_findings": self.main_findings,
            "limitations": self.limitations,
            "section_target": self.section_target,
            "tags": self.tags,
            "confidence_note": self.confidence_note,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EvidenceRecord":
        return cls(
            literature_id=d.get("literature_id", ""),
            citation_key=d.get("citation_key", ""),
            claim=d.get("claim", ""),
            evidence_quote=d.get("evidence_quote", ""),
            research_design=d.get("research_design", ""),
            sample=d.get("sample", ""),
            variables=d.get("variables", []),
            measurement_tools=d.get("measurement_tools", []),
            statistical_methods=d.get("statistical_methods", []),
            main_findings=d.get("main_findings", ""),
            limitations=d.get("limitations", ""),
            section_target=d.get("section_target", ""),
            tags=d.get("tags", []),
            confidence_note=d.get("confidence_note", ""),
        )


@dataclass
class EvidenceStore:
    """证据表管理。"""
    records: list[EvidenceRecord] = field(default_factory=list)

    def add(self, record: EvidenceRecord):
        self.records.append(record)

    def get_by_section(self, section: str) -> list[EvidenceRecord]:
        return [r for r in self.records if r.section_target == section]

    def get_by_citation_key(self, key: str) -> list[EvidenceRecord]:
        return [r for r in self.records if r.citation_key == key]

    def get_by_tag(self, tag: str) -> list[EvidenceRecord]:
        return [r for r in self.records if tag in r.tags]

    def check_citation_coverage(self, cited_keys: list[str]) -> dict:
        """检查引用覆盖：哪些引用有证据支撑，哪些缺失。"""
        store_keys = {r.citation_key for r in self.records}
        covered = [k for k in cited_keys if k in store_keys]
        missing = [k for k in cited_keys if k not in store_keys]
        return {"covered": covered, "missing": missing, "coverage_rate": len(covered) / max(len(cited_keys), 1)}

    def to_markdown(self) -> str:
        if not self.records:
            return "暂无证据记录。\n"
        lines = ["# 文献证据表\n"]
        sections = {}
        for r in self.records:
            target = r.section_target or "未分类"
            sections.setdefault(target, []).append(r)

        section_labels = {
            "introduction": "引言", "method": "方法",
            "discussion": "讨论", "limitation": "局限",
            "未分类": "未分类",
        }
        for sec, recs in sections.items():
            lines.append(f"\n## {section_labels.get(sec, sec)}\n")
            for r in recs:
                lines.append(f"### [{r.citation_key}] {r.claim}\n")
                if r.evidence_quote:
                    lines.append(f"> {r.evidence_quote}\n")
                if r.research_design:
                    lines.append(f"- 研究设计: {r.research_design}")
                if r.sample:
                    lines.append(f"- 样本: {r.sample}")
                if r.main_findings:
                    lines.append(f"- 主要发现: {r.main_findings}")
                if r.limitations:
                    lines.append(f"- 局限: {r.limitations}")
                if r.tags:
                    lines.append(f"- 标签: {', '.join(r.tags)}")
                lines.append("")
        return "\n".join(lines)

    def to_csv(self) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "citation_key", "claim", "section_target", "research_design",
            "sample", "main_findings", "limitations", "confidence_note",
        ])
        writer.writeheader()
        for r in self.records:
            writer.writerow({
                "citation_key": r.citation_key,
                "claim": r.claim,
                "section_target": r.section_target,
                "research_design": r.research_design,
                "sample": r.sample,
                "main_findings": r.main_findings,
                "limitations": r.limitations,
                "confidence_note": r.confidence_note,
            })
        return output.getvalue()

    def to_json(self) -> str:
        return json.dumps([r.to_dict() for r in self.records], ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, data: str) -> "EvidenceStore":
        records = [EvidenceRecord.from_dict(d) for d in json.loads(data)]
        return cls(records=records)
