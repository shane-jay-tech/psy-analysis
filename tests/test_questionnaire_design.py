"""问卷设计系统测试"""
import pytest
from src.questionnaire.design_engine import design_questionnaire
from src.questionnaire.construct_kb import CONSTRUCTS, DOMAIN_KEYWORDS
from src.questionnaire.academic_literature import (
    search_established_scales,
    get_academic_reference_for_construct,
    generate_academic_report,
)


class TestDesignEngine:
    def test_design_with_known_construct(self):
        result = design_questionnaire("调查大学生的心理韧性水平")
        assert result["construct_name"] == "心理韧性"
        assert len(result["dimensions_used"]) > 0
        assert len(result["items"]) > 0
        assert "items" in result
        assert "instructions" in result
        assert "scale_config" in result

    def test_design_with_partial_match(self):
        result = design_questionnaire("了解中学生的社交焦虑情况")
        assert result["construct_name"] == "社交焦虑"
        assert result["is_exact_match"] is True

    def test_design_without_match(self):
        result = design_questionnaire("探索某未知概念")
        assert result["is_exact_match"] is False
        assert result["construct_name"] is not None
        assert len(result["dimensions_used"]) > 0

    def test_academic_enrichment(self):
        result = design_questionnaire(
            "调查员工的心理资本水平",
            use_academic_sources=True,
        )
        assert result.get("academic_enrichment") is not None

    def test_output_structure(self):
        result = design_questionnaire("调查大学生的幸福感")
        required_keys = [
            "research_question", "construct_name", "dimensions_used",
            "template_used", "scale_config", "items", "instructions",
            "scoring", "psychometrics", "llm_used",
        ]
        for key in required_keys:
            assert key in result, f"缺少 {key}"

    def test_scale_config(self):
        result = design_questionnaire("调查大学生的自我效能感")
        sc = result["scale_config"]
        assert sc["points"] >= 4
        assert sc["n_items"] >= 5
        assert sc["n_dimensions"] >= 1
        assert isinstance(sc["n_reverse"], int)

    def test_items_have_required_fields(self):
        result = design_questionnaire("调查大学生的焦虑水平")
        for item in result["items"]:
            assert "index" in item
            assert "text" in item
            assert "dimension" in item
            assert "reverse" in item
            assert len(item["text"]) >= 3


class TestAcademicLiterature:
    def test_search_scales(self):
        scales = search_established_scales("心理资本", "组织行为")
        assert len(scales) >= 1

    def test_academic_reference_package(self):
        pkg = get_academic_reference_for_construct("心理韧性", "发展")
        assert "established_scales" in pkg
        assert "academic_references_apa7" in pkg
        assert "scale_reliability_norms" in pkg
        assert pkg["academic_source_count"] >= 0

    def test_generate_report(self):
        pkg = get_academic_reference_for_construct("焦虑", "临床")
        report = generate_academic_report("焦虑", pkg)
        assert "焦虑" in report
        assert len(report) > 50


class TestConstructKB:
    def test_domain_keywords_coverage(self):
        """确保DOMAIN_KEYWORDS覆盖5个以上领域"""
        assert len(DOMAIN_KEYWORDS) >= 5

    def test_construct_count(self):
        """确保内置构念数量充足"""
        assert len(CONSTRUCTS) >= 40

    def test_all_constructs_have_dimensions(self):
        for name, entry in CONSTRUCTS.items():
            dims = entry.get("dimensions", [])
            assert len(dims) >= 1, f"{name} 缺少维度"
            for dim in dims:
                assert "name" in dim, f"{name} 维度缺少name"
                assert "item_count" in dim, f"{name} 维度缺少item_count"

    def test_all_constructs_have_references(self):
        for name, entry in CONSTRUCTS.items():
            refs = entry.get("references", [])
            assert len(refs) >= 1, f"{name} 缺少参考文献"
