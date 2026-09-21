"""问卷设计系统测试"""
import copy

import pytest

from src.questionnaire.design_engine import design_questionnaire
from src.questionnaire.construct_kb import CONSTRUCTS, DOMAIN_KEYWORDS
from src.questionnaire.academic_literature import (
    search_established_scales,
    get_academic_reference_for_construct,
    generate_academic_report,
)
from src.questionnaire.report_generator import (
    generate_design_report,
    generate_design_summary,
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


# ==================== s922-15 钉桩：generate_design_summary ====================
# 口径：只钉现状（含已知的表述分叉与空节残留），不改判据、不改数值、不修实现。


def _md_level(line: str):
    """该行是 Markdown 标题则返回层级，否则 None（代码围栏内的 # 不算）。"""
    s = line.strip()
    if not s.startswith("#"):
        return None
    body = s.lstrip("#").strip()
    if not body or set(body) <= {"`"}:
        return None
    return len(s) - len(s.lstrip("#"))


def _empty_md_sections(text: str) -> list:
    """返回「标题下没有任何正文」的标题行。

    往下扫到 `---` 或同级/更浅标题为止；区间内除空行与 ``` 围栏标记外
    没有正文，即判为空节。
    """
    lines = text.split("\n")
    heads = [(i, _md_level(l)) for i, l in enumerate(lines) if _md_level(l)]
    bad = []
    for i, level in heads:
        stop = len(lines)
        for j in range(i + 1, len(lines)):
            s = lines[j].strip()
            lv = _md_level(lines[j])
            if s == "---" or (lv and lv <= level):
                stop = j
                break
        body = [
            lines[j].strip()
            for j in range(i + 1, stop)
            if lines[j].strip() and not lines[j].strip().startswith("```")
        ]
        if not body:
            bad.append(lines[i].strip())
    return bad


class TestDesignSummaryPins:
    """同一 fixture 同时喂 summary 与 report，钉两者的事实一致性与空节现状。"""

    @pytest.fixture(scope="class")
    def matched_design(self):
        return design_questionnaire("调查大学生的心理韧性水平", use_academic_sources=False)

    @pytest.fixture(scope="class")
    def unmatched_design(self):
        return design_questionnaire("探索某未知概念", use_academic_sources=False)

    def test_summary_facts_all_have_report_counterparts(self, matched_design):
        """summary 里的每条事实都能在 report 里找到同值表述（summary ⊆ report 事实集）。"""
        design = matched_design
        summary = generate_design_summary(design)
        report = generate_design_report(design)
        sc = design["scale_config"]
        tpl = design["template_used"]["name"]
        minutes = max(3, sc["n_items"] // 3)

        # (摘要侧原文, 报告侧对应原文)
        pairs = [
            (f"**构念**：{design['construct_name']}", f"「**{design['construct_name']}**」"),
            (f"**题型**：{tpl}", f"| 题型 | {tpl} |"),
            (f"（{sc['points']}点计分）", f"| 量表点数 | {sc['points']} 点 Likert |"),
            (f"**题量**：{sc['n_items']} 题", f"| 总题量 | {sc['n_items']} 题 |"),
            (f"（{sc['n_dimensions']}个维度）", f"| 维度数 | {sc['n_dimensions']} |"),
            (f"**反向题**：{sc['n_reverse']} 题", f"| 反向题数 | {sc['n_reverse']} 题"),
            (f"约 {minutes} 分钟", f"| 预计用时 | 约 {minutes} 分钟 |"),
        ]
        for i, dim in enumerate(design["dimensions_used"]):
            pairs.append((
                f"- {dim['name']}：{dim['item_count']} 题",
                f"**{i + 1}. {dim['name']}**",
            ))
            pairs.append((
                f"- {dim['name']}：{dim['item_count']} 题",
                f"   - 题目数：{dim['item_count']} 题",
            ))
        assert pairs, "事实对未生成，断言会退化成空跑"
        for s_frag, r_frag in pairs:
            assert s_frag in summary, f"摘要里没有事实 {s_frag!r}（生成器文案变了）"
            assert r_frag in report, f"报告里没有同值事实 {r_frag!r}（摘要与报告开始各说各话）"
        # 维度计数在 fixture 上自洽：表格里写 n_dimensions，正文里写 len(dimensions_used)
        assert sc["n_dimensions"] == len(design["dimensions_used"])

    def test_summary_and_report_have_no_empty_section(self, matched_design):
        summary = generate_design_summary(matched_design)
        report = generate_design_report(matched_design)
        assert _empty_md_sections(summary) == []
        assert _empty_md_sections(report) == []

    def test_match_method_wording_diverges_by_design(self, matched_design):
        """现状分叉：摘要写死措辞，报告用 match_reason（钉住，不统一）。"""
        design = matched_design
        summary = generate_design_summary(design)
        report = generate_design_report(design)
        assert "**匹配方式**：精确匹配已有构念知识库" in summary
        assert design["match_reason"] in report
        # 摘要那句写死的话在报告里根本不出现 —— 两者非字面包含关系，只能按事实值对齐
        assert "精确匹配已有构念知识库" not in report

    def test_summary_unmatched_branch_wording(self, unmatched_design):
        assert unmatched_design["is_exact_match"] is False
        summary = generate_design_summary(unmatched_design)
        assert "**匹配方式**：基于关键词推断" in summary
        assert "精确匹配已有构念知识库" not in summary

    def test_empty_design_has_no_degradation_text_and_raises(self):
        """现状：空 design 没有降级文案，两个生成器都直接 KeyError（钉异常类型与首个缺的键）。"""
        with pytest.raises(KeyError) as si:
            generate_design_summary({})
        assert si.value.args[0] == "scale_config"
        with pytest.raises(KeyError) as ri:
            generate_design_report({})
        assert ri.value.args[0] == "research_question"

    def test_empty_dimensions_leave_dangling_summary_section(self, matched_design):
        """现状：dimensions_used 清空后摘要尾巴挂着空标题，报告只把维度数写成 0（钉缺陷不修）。"""
        design = copy.deepcopy(matched_design)
        design["dimensions_used"] = []
        summary = generate_design_summary(design)
        report = generate_design_report(design)
        assert summary.rstrip("\n").endswith("### 维度分配：")
        assert _empty_md_sections(summary) == ["### 维度分配："]
        assert "本问卷包含 **0** 个理论维度：" in report
        assert _empty_md_sections(report) == []
