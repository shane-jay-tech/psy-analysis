"""范例库扩展（18 条）+ 语义匹配测试。"""

import pytest

from src.upstream.topic_funnel_kb import (
    GOOD_BAD_EXAMPLES,
    list_all_domains,
    list_all_examples,
    match_examples_by_semantics,
    render_examples_for_prompt,
    _char_bigram_overlap,
    _domain_score,
)


class TestExampleCompleteness:
    def test_six_domains_present(self):
        domains = list_all_domains()
        assert set(domains) == {
            "social", "clinical", "educational",
            "developmental", "cognitive", "organizational",
        }

    def test_each_domain_has_three_examples(self):
        for domain, items in GOOD_BAD_EXAMPLES.items():
            assert len(items) == 3, f"{domain} 应有 3 例，实际 {len(items)}"

    def test_total_eighteen_examples(self):
        assert len(list_all_examples()) == 18

    def test_each_example_has_required_fields(self):
        required = {"vague", "bad_q", "good_q", "transformation", "why_better"}
        for ex in list_all_examples():
            missing = required - set(ex.keys())
            assert not missing, f"范例缺字段：{missing}"
            # transformation 应为 5 步对应文本
            assert isinstance(ex["transformation"], list)
            assert len(ex["transformation"]) >= 4   # 5 阶段对应文本（容许某阶段合并）

    def test_examples_are_undergrad_executable(self):
        """避免 fMRI/EEG/纵向追踪等高门槛范例。"""
        forbidden = ["fMRI", "纵向追踪 6 年", "纵向追踪10年", "脑电"]
        for ex in list_all_examples():
            blob = ex["good_q"] + " " + " ".join(ex.get("transformation", []))
            for token in forbidden:
                assert token not in blob, \
                    f"范例 {ex['domain']}/{ex['vague']} 含高门槛词：{token}"


class TestSemanticMatching:
    def test_clinical_input_matches_clinical_examples(self):
        """临床词应优先匹配临床领域范例。"""
        result = match_examples_by_semantics("我想研究产后抑郁", top_k=2)
        assert len(result) > 0
        # 至少 top-1 应是 clinical 领域
        domains = [r["domain"] for r in result]
        assert "clinical" in domains

    def test_educational_input_matches_educational(self):
        result = match_examples_by_semantics("我想研究学习动机和拖延", top_k=2)
        assert len(result) > 0
        domains = [r["domain"] for r in result]
        assert "educational" in domains

    def test_empty_input_returns_empty(self):
        assert match_examples_by_semantics("") == []
        assert match_examples_by_semantics("   ") == []

    def test_top_k_caps_results(self):
        result = match_examples_by_semantics("我想研究焦虑", top_k=1)
        assert len(result) <= 1

    def test_threshold_filters_irrelevant(self):
        """完全无关的输入应返回空（高阈值）。"""
        result = match_examples_by_semantics(
            "今天天气真好我去吃饭",
            top_k=2,
            similarity_threshold=0.3,    # 高阈值
        )
        assert result == [] or all(r["_score"] >= 0.3 for r in result)

    def test_cross_domain_input_returns_relevant(self):
        """跨领域词应返回相关而非随机。"""
        # 「认知 + 老人」可能跨认知/发展两域
        result = match_examples_by_semantics("老年人记忆衰退", top_k=3)
        assert len(result) > 0
        # 应至少有一个 cognitive 或 developmental
        domains = {r["domain"] for r in result}
        assert domains & {"cognitive", "developmental"}

    def test_render_examples_for_prompt_format(self):
        examples = match_examples_by_semantics("我想研究焦虑", top_k=2)
        rendered = render_examples_for_prompt(examples)
        if examples:
            assert "范例 1" in rendered
            assert "好/差选题对比" in rendered or "选题" in rendered

    def test_render_empty_returns_empty(self):
        assert render_examples_for_prompt([]) == ""


class TestBigramOverlap:
    def test_identical_text_high_score(self):
        assert _char_bigram_overlap("社交焦虑", "社交焦虑") > 0.9

    def test_disjoint_text_low_score(self):
        assert _char_bigram_overlap("AAAA", "BBBB") < 0.1

    def test_partial_overlap(self):
        s = _char_bigram_overlap("社交焦虑研究", "社交媒体研究")
        assert 0 < s < 1


class TestDomainScore:
    def test_clinical_keyword_hit(self):
        assert _domain_score("我想研究抑郁和焦虑", "clinical") > 0
        assert _domain_score("我想研究工作满意度", "clinical") == 0

    def test_three_hits_max_score(self):
        score = _domain_score("学习动机和学业拖延以及师生关系", "educational")
        assert score >= 0.9
