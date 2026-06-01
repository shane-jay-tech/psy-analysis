"""Round 3 — I/O 构念关键词索引回归（2026-05-30）。

io-domain-seed 那次只把 5 条新构念加进 CONSTRUCTS，没同步加进
CONSTRUCT_KEYWORDS / DOMAIN_KEYWORDS["组织行为"]，结果 design_engine
在用户输入「员工敬业度」「LMX」「家长式领导」时无法路由到这些条目。

本测试覆盖：
- 5 条新构念在 CONSTRUCT_KEYWORDS 里有 entry
- 每条至少含一个能匹配真实用户输入的同义词（中文 + 英文缩写）
- 5 条都被 DOMAIN_KEYWORDS["组织行为"] 锚定
- design_engine._match_construct 在 use_chain=False 兜底路径下
  能把含同义词的研究问题路由到对应构念
"""

from __future__ import annotations

import pytest

from src.questionnaire.construct_kb import (
    CONSTRUCTS,
    CONSTRUCT_KEYWORDS,
    DOMAIN_KEYWORDS,
)


NEW_IO_CONSTRUCTS = [
    "员工敬业度",
    "家长式领导",
    "伦理型领导",
    "领导-成员交换",
    "工作旺盛感",
]


class TestConstructKeywordIndex:
    @pytest.mark.parametrize("name", NEW_IO_CONSTRUCTS)
    def test_in_construct_keywords(self, name):
        assert name in CONSTRUCT_KEYWORDS, (
            f"{name} 必须在 CONSTRUCT_KEYWORDS 有 entry，否则 design_engine 关键词路径无法命中"
        )
        kws = CONSTRUCT_KEYWORDS[name]
        assert isinstance(kws, list) and len(kws) >= 2, (
            f"{name} 至少需要 2 个同义词"
        )

    def test_uwes_synonyms_cover_english_acronym(self):
        kws = CONSTRUCT_KEYWORDS["员工敬业度"]
        joined = " ".join(kws).lower()
        assert "uwes" in joined, "员工敬业度 应有 UWES 缩写匹配"
        assert "engagement" in joined, "员工敬业度 应有英文 engagement 匹配"

    def test_lmx_synonyms_cover_acronym_and_chinese(self):
        kws = CONSTRUCT_KEYWORDS["领导-成员交换"]
        joined = " ".join(kws).lower()
        assert "lmx" in joined, "领导-成员交换 应有 LMX 缩写匹配"
        assert any("上下级" in k or "成员交换" in k for k in kws), (
            "领导-成员交换 应有中文同义词"
        )

    def test_paternalistic_synonyms_cover_three_dimensions(self):
        kws = CONSTRUCT_KEYWORDS["家长式领导"]
        joined = " ".join(kws)
        assert "威权" in joined, "家长式领导应识别「威权」维度词"
        assert "仁慈" in joined, "家长式领导应识别「仁慈」维度词"


class TestDomainKeywordsIndex:
    @pytest.mark.parametrize("name", NEW_IO_CONSTRUCTS)
    def test_in_organizational_domain(self, name):
        ob_kws = DOMAIN_KEYWORDS["组织行为"]
        # 不强制要求构念全名，但至少有一个核心词在域关键词里
        construct_kws = CONSTRUCT_KEYWORDS[name]
        overlap = [k for k in construct_kws if k in ob_kws]
        assert len(overlap) >= 1, (
            f"{name} 至少有 1 个同义词被 DOMAIN_KEYWORDS['组织行为'] 锚定，否则模糊匹配无法识别为 OB 域。"
            f" 当前 overlap={overlap}"
        )


class TestDesignEngineRouting:
    """端到端：用户输入含 I/O 关键词时 _match_construct 兜底路径能路由到对应构念。"""

    @pytest.mark.parametrize("question, expected", [
        ("员工敬业度对工作绩效的影响", "员工敬业度"),
        ("UWES 测量的是什么？", "员工敬业度"),
        ("家长式领导对下属创新的影响机制研究", "家长式领导"),
        ("威权领导和仁慈领导的差异研究", "家长式领导"),
        ("LMX 与员工创造力的关系", "领导-成员交换"),
        ("工作旺盛感与职业发展研究", "工作旺盛感"),
    ])
    def test_match_io_constructs_via_keyword_path(self, question, expected):
        from src.questionnaire.design_engine import _match_construct

        # use_chain=False 强制走兜底关键词匹配，不依赖 LLM
        construct, info = _match_construct(
            words=list(question), question=question, use_chain=False,
        )
        assert construct is not None, (
            f"问题「{question}」应能命中构念，实际未命中（info={info}）"
        )
        # name_zh 等于预期，或 best_name 命中（构念匹配是 fuzzy 的，允许一定容错）
        matched_name = construct.get("name_zh", "")
        assert matched_name == expected or expected in matched_name, (
            f"问题「{question}」期望命中「{expected}」，实际命中「{matched_name}」"
        )

    def test_ethical_leadership_when_only_term_in_question(self):
        """伦理型领导：避免和「组织公民行为」共现导致的歧义命中。"""
        from src.questionnaire.design_engine import _match_construct

        question = "伦理型领导对下属道德行为的预测作用"
        construct, info = _match_construct(
            words=list(question), question=question, use_chain=False,
        )
        assert construct is not None
        assert construct["name_zh"] == "伦理型领导", (
            f"期望命中「伦理型领导」，实际命中「{construct['name_zh']}」"
        )
