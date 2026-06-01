"""论文写作系统测试"""
import pytest
from src.paper_writer.literature_manager import (
    LiteratureManager,
    LiteratureEntry,
    validate_doi,
    autofill_from_doi,
    PRESET_CHINESE_LITERATURE,
    PRESET_ENGLISH_LITERATURE,
)
from src.paper_writer.paper_engine import polish_with_llm, polish_paper_sections


class TestLiteratureManager:
    def test_load_presets(self):
        lm = LiteratureManager()
        assert len(lm.entries) > 100
        assert "温忠麟2014" in lm.entries
        assert "Cohen1988" in lm.entries

    def test_preset_ratio(self):
        cn = len(PRESET_CHINESE_LITERATURE)
        en = len(PRESET_ENGLISH_LITERATURE)
        total = cn + en
        assert total >= 100, f"总文献数 {total} < 100"
        cn_ratio = cn / total
        assert 0.55 <= cn_ratio <= 0.70, f"中文比例 {cn_ratio:.0%} 不在55-70%范围"

    def test_apa7_format_chinese(self):
        lm = LiteratureManager()
        ref = lm.get_entry("温忠麟2014").format_reference()
        # APA7格式不应包含 [J] 等GB/T标记
        assert "[J]" not in ref
        assert "doi:" not in ref  # 应使用 https://doi.org/
        assert "https://doi.org/" in ref if "doi" in ref.lower() else True

    def test_apa7_format_english(self):
        lm = LiteratureManager()
        ref = lm.get_entry("Cohen1988").format_reference()
        assert "Cohen, J." in ref
        assert "(1988)" in ref

    def test_search_presets(self):
        lm = LiteratureManager()
        results = lm.search_presets(["中介效应", "Bootstrap"], n=5)
        assert len(results) > 0
        assert any("中介" in e.title for e in results)

    def test_suggest_for_context(self):
        lm = LiteratureManager()
        results = lm.suggest_for_context(
            "本研究采用Bootstrap法检验中介效应，使用结构方程模型验证因素结构",
            n=5,
        )
        assert len(results) > 0

    def test_entry_fields(self):
        lm = LiteratureManager()
        entry = lm.get_entry("温忠麟2014")
        assert entry.authors == ["温忠麟", "叶宝娟"]
        assert entry.year == "2014"
        assert len(entry.title) > 5
        assert entry.is_chinese is True

    def test_online_search_graceful(self):
        lm = LiteratureManager()
        results = lm.search_online("psychology test")
        assert isinstance(results, list)


class TestDOIFunctions:
    def test_validate_invalid_doi(self):
        result = validate_doi("invalid-doi-string")
        assert result is None

    def test_validate_empty_doi(self):
        result = validate_doi("")
        assert result is None


class TestPolishFunctions:
    def test_polish_no_api_key(self):
        result = polish_with_llm(
            "本研究采用问卷调查法。",
            section="methods",
            api_key="",
        )
        assert result["success"] is False
        assert "API" in result["changes_summary"]

    def test_polish_short_text(self):
        result = polish_with_llm(
            "太短",
            section="methods",
            api_key="fake_key",
            base_url="http://x",
        )
        assert result["success"] is True  # 短文本无需润色但不算失败
        assert result["polished_text"] == "太短"

    def test_polish_paper_sections(self):
        sections = {
            "methods": "本研究采用方便取样法。",
            "results": "t检验表明两组差异显著。",
        }
        result = polish_paper_sections(
            sections,
            api_key="",
        )
        assert result["polished_sections"]["methods"] == sections["methods"]
        assert result["polished_sections"]["results"] == sections["results"]
