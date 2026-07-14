"""演示项目数据完整性验证 — 离线可运行，不依赖 Playwright。"""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.questionnaire.import_cleaning import ScaleDimension, run_questionnaire_cleaning
from src.analysis.method_recommender import ResearchDesignInput, recommend_method
from src.literature.evidence_record import EvidenceRecord, EvidenceStore

DEMO_DIR = Path(__file__).parent.parent / "demo_projects" / "psychology_questionnaire_demo"


class TestDemoProjectIntegrity:
    """离线验证演示项目数据和结构。"""

    def test_demo_dir_exists(self):
        assert DEMO_DIR.exists()

    def test_data_csv_valid(self):
        df = pd.read_csv(DEMO_DIR / "data.csv")
        assert len(df) == 30
        assert "Q1" in df.columns
        assert "Q10" in df.columns
        assert "gender" in df.columns
        assert "duration_seconds" in df.columns

    def test_schema_valid(self):
        with open(DEMO_DIR / "questionnaire_schema.json", encoding="utf-8") as f:
            schema = json.load(f)
        assert len(schema["dimensions"]) == 2
        assert schema["dimensions"][0]["name"] == "焦虑"
        assert "Q3" in schema["dimensions"][0]["reverse_items"]

    def test_literature_seed_valid(self):
        with open(DEMO_DIR / "literature_seed.json", encoding="utf-8") as f:
            seeds = json.load(f)
        assert len(seeds) == 3
        assert all("citation_key" in s for s in seeds)

    def test_expected_cards_valid(self):
        with open(DEMO_DIR / "expected_analysis_cards.json", encoding="utf-8") as f:
            cards = json.load(f)
        assert len(cards) >= 4
        methods = [c["method_id"] for c in cards]
        assert "cronbach_alpha" in methods
        assert "pearson_corr" in methods

    def test_cleaning_pipeline_end_to_end(self):
        df = pd.read_csv(DEMO_DIR / "data.csv")
        with open(DEMO_DIR / "questionnaire_schema.json", encoding="utf-8") as f:
            schema = json.load(f)

        dims = [
            ScaleDimension(
                name=d["name"], items=d["items"],
                reverse_items=d["reverse_items"],
                max_score=d["max_score"], min_score=d["min_score"],
            )
            for d in schema["dimensions"]
        ]
        result = run_questionnaire_cleaning(
            df, dimensions=dims,
            duration_column="duration_seconds",
            min_duration_seconds=schema["invalid_detection"]["min_duration_seconds"],
        )
        assert result.summary["valid_n"] == 27
        assert result.summary["invalid_n"] == 3
        assert "焦虑_mean" in result.df_scored.columns
        assert "自尊_mean" in result.df_scored.columns

    def test_method_recommendation_for_demo(self):
        rec = recommend_method(ResearchDesignInput(
            purpose="correlation", dv_type="continuous", sample_size=27
        ))
        assert rec.primary_method == "pearson_corr"

    def test_evidence_coverage_for_demo(self):
        with open(DEMO_DIR / "literature_seed.json", encoding="utf-8") as f:
            seeds = json.load(f)

        store = EvidenceStore()
        for s in seeds:
            store.add(EvidenceRecord(
                literature_id=s["id"],
                citation_key=s["citation_key"],
                claim=s.get("relevance", ""),
                section_target="introduction",
            ))
        coverage = store.check_citation_coverage(["wang2023", "li2022", "zhang2021"])
        assert coverage["coverage_rate"] == 1.0
