"""证据表 (EvidenceRecord + EvidenceStore) 测试。"""

import json
import pytest

from src.literature.evidence_record import EvidenceRecord, EvidenceStore


@pytest.fixture
def sample_records():
    return [
        EvidenceRecord(
            literature_id="lit001",
            citation_key="wang2023",
            claim="焦虑与学业倦怠正相关",
            evidence_quote="r=0.45, p<0.001",
            research_design="横断面问卷调查",
            sample="大学生 N=500",
            variables=["焦虑", "学业倦怠"],
            measurement_tools=["SAS", "MBI-SS"],
            statistical_methods=["Pearson 相关", "多元回归"],
            main_findings="焦虑显著正向预测学业倦怠",
            limitations="横断面设计无法推断因果",
            section_target="introduction",
            tags=["焦虑", "学业倦怠", "大学生"],
            confidence_note="高，样本量充足且工具信效度好",
        ),
        EvidenceRecord(
            literature_id="lit002",
            citation_key="li2022",
            claim="自尊在焦虑与倦怠间起中介作用",
            research_design="纵向追踪",
            sample="高中生 N=300",
            variables=["焦虑", "自尊", "学业倦怠"],
            statistical_methods=["中介分析", "Bootstrap"],
            main_findings="间接效应显著，95% CI 不含零",
            section_target="discussion",
            tags=["中介", "自尊"],
        ),
        EvidenceRecord(
            literature_id="lit003",
            citation_key="zhang2021",
            claim="SAS 中文版具有良好信效度",
            section_target="method",
            research_design="工具验证",
            sample="大学生 N=1000",
            measurement_tools=["SAS"],
            tags=["量表", "信效度"],
        ),
    ]


@pytest.fixture
def store(sample_records):
    s = EvidenceStore()
    for r in sample_records:
        s.add(r)
    return s


class TestEvidenceRecord:
    def test_to_dict_roundtrip(self, sample_records):
        r = sample_records[0]
        d = r.to_dict()
        r2 = EvidenceRecord.from_dict(d)
        assert r2.citation_key == "wang2023"
        assert r2.claim == r.claim
        assert r2.variables == ["焦虑", "学业倦怠"]

    def test_from_dict_with_missing_fields(self):
        r = EvidenceRecord.from_dict({"citation_key": "test", "claim": "test claim"})
        assert r.literature_id == ""
        assert r.variables == []


class TestEvidenceStore:
    def test_add_and_count(self, store):
        assert len(store.records) == 3

    def test_get_by_section(self, store):
        intro = store.get_by_section("introduction")
        assert len(intro) == 1
        assert intro[0].citation_key == "wang2023"

    def test_get_by_citation_key(self, store):
        results = store.get_by_citation_key("li2022")
        assert len(results) == 1
        assert results[0].section_target == "discussion"

    def test_get_by_tag(self, store):
        anxiety = store.get_by_tag("焦虑")
        assert len(anxiety) == 1
        assert anxiety[0].citation_key == "wang2023"

    def test_check_citation_coverage_all_covered(self, store):
        cited = ["wang2023", "li2022"]
        result = store.check_citation_coverage(cited)
        assert result["covered"] == cited
        assert result["missing"] == []
        assert result["coverage_rate"] == 1.0

    def test_check_citation_coverage_partial(self, store):
        cited = ["wang2023", "chen2024", "li2022"]
        result = store.check_citation_coverage(cited)
        assert "chen2024" in result["missing"]
        assert result["coverage_rate"] == pytest.approx(2 / 3)

    def test_check_citation_coverage_empty(self, store):
        result = store.check_citation_coverage([])
        assert result["coverage_rate"] == 0.0

    def test_to_markdown(self, store):
        md = store.to_markdown()
        assert "# 文献证据表" in md
        assert "wang2023" in md
        assert "引言" in md
        assert "讨论" in md

    def test_to_csv(self, store):
        csv_text = store.to_csv()
        assert "citation_key" in csv_text
        assert "wang2023" in csv_text
        assert "li2022" in csv_text
        lines = csv_text.strip().split("\n")
        assert len(lines) == 4  # header + 3 records

    def test_to_json_roundtrip(self, store):
        json_text = store.to_json()
        store2 = EvidenceStore.from_json(json_text)
        assert len(store2.records) == 3
        assert store2.records[0].citation_key == "wang2023"
        assert store2.records[1].tags == ["中介", "自尊"]

    def test_empty_store_markdown(self):
        store = EvidenceStore()
        md = store.to_markdown()
        assert "暂无" in md
