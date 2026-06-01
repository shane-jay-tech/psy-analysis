"""v4.7 自学习模块 — LLM 抽取层测试（Phase 4c）。

覆盖：
- grounding: quote_in_abstract / parse_llm_json
- prompts: PROMPT_VERSION 稳定 / 模板包含必需字段
- LLMExtractor: 端到端 mock LLM 路径，构念入候选表
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture
def feed_root(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    import sys
    for mod in list(sys.modules):
        if mod.startswith("src.literature_feed"):
            del sys.modules[mod]
    return tmp_path


# =============================================================================
# grounding
# =============================================================================

class TestGrounding:

    def test_quote_in_abstract_verbatim(self):
        from src.literature_feed.extract.grounding import quote_in_abstract

        abs_ = "本研究探讨变革型领导对员工工作满意度的影响。"
        assert quote_in_abstract("变革型领导对员工工作满意度", abs_)

    def test_quote_in_abstract_normalizes_whitespace(self):
        from src.literature_feed.extract.grounding import quote_in_abstract

        abs_ = "本研究  探讨  变革型领导   对员工工作满意度的影响。"
        # quote 用单空格，abstract 用多空格 / 全角空格 → NFKC 折叠后应该匹配
        assert quote_in_abstract("变革型领导 对员工工作满意度的影响", abs_)

    def test_quote_in_abstract_too_short(self):
        from src.literature_feed.extract.grounding import quote_in_abstract

        # min_len=10，9 字符的 quote → 拒绝
        assert quote_in_abstract("短引用一二三四", "短引用一二三四不在 abstract 里别管") is False

    def test_quote_in_abstract_not_present(self):
        from src.literature_feed.extract.grounding import quote_in_abstract

        abs_ = "完全不相关的摘要文本，写得很长很长很长很长。"
        assert quote_in_abstract("变革型领导对员工的影响", abs_) is False

    def test_parse_llm_json_plain(self):
        from src.literature_feed.extract.grounding import parse_llm_json

        assert parse_llm_json('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}

    def test_parse_llm_json_with_fence(self):
        from src.literature_feed.extract.grounding import parse_llm_json

        text = "```json\n{\"a\": 1}\n```"
        assert parse_llm_json(text) == {"a": 1}

    def test_parse_llm_json_with_prose_prefix(self):
        from src.literature_feed.extract.grounding import parse_llm_json

        # 包裹了多余文字 → 抓首尾 {} 段
        text = '抱歉，这是结果：{"a": 1, "b": [1,2,3]} 希望有用'
        out = parse_llm_json(text)
        assert out == {"a": 1, "b": [1, 2, 3]}

    def test_parse_llm_json_returns_none_on_garbage(self):
        from src.literature_feed.extract.grounding import parse_llm_json

        assert parse_llm_json("not json at all") is None
        assert parse_llm_json("") is None
        assert parse_llm_json("[1, 2, 3]") is None  # array 不是 dict


# =============================================================================
# prompts
# =============================================================================

class TestPrompts:

    def test_prompt_version_is_stable_string(self):
        from src.literature_feed.extract import prompts

        # PROMPT_VERSION 必须存在且非空，用作缓存 key
        assert hasattr(prompts, "PROMPT_VERSION")
        assert isinstance(prompts.PROMPT_VERSION, str)
        assert len(prompts.PROMPT_VERSION) > 0

    def test_build_construct_prompt_contains_required(self):
        from src.literature_feed.extract.prompts import build_construct_prompt

        msgs = build_construct_prompt(
            title="变革型领导对员工工作满意度的影响",
            abstract="本研究通过 300 名员工的调查...",
            journal="心理科学",
        )
        assert isinstance(msgs, list) and len(msgs) >= 2
        # 系统消息 + 用户消息
        roles = [m.get("role") for m in msgs]
        assert "system" in roles and "user" in roles
        user_content = next(m["content"] for m in msgs if m["role"] == "user")
        assert "变革型领导" in user_content
        assert "心理科学" in user_content

    def test_build_method_prompt_contains_required(self):
        from src.literature_feed.extract.prompts import build_method_prompt

        msgs = build_method_prompt(
            title="实验法研究决策",
            abstract="采用 2x2 被试间设计...",
            journal="心理学报",
        )
        user_content = next(m["content"] for m in msgs if m["role"] == "user")
        assert "实验法研究决策" in user_content


# =============================================================================
# LLMExtractor end-to-end (mocked)
# =============================================================================

class TestLLMExtractor:

    def test_extract_construct_inserts_candidate(self, feed_root):
        from src.literature_feed.extract.extractor import LLMExtractor
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.budget_tracker import BudgetTracker
        from src.literature_feed.storage.feed_store import ArticleRow

        store = FeedStore()
        budget = BudgetTracker(monthly_limit_usd=10.0)
        store.upsert_source(source_id="J", journal_name="心理科学", fetcher_type="manual")
        aid = store.upsert_article(ArticleRow(
            title="变革型领导对员工工作满意度的影响",
            source_id="J",
            provenance="manual",
            title_norm="变革型领导对员工工作满意度的影响",
            abstract="本研究探讨变革型领导对员工工作满意度的影响，调查 300 名员工，验证心理资本的中介作用。",
            issued_date="2026-05-01",
            fetched_at="2026-05-29T00:00:00Z",
        ))

        def fake_chat(messages, *, model, temperature):
            content = (
                '{"constructs":[{"name":"变革型领导","definition":"领导者通过愿景激励下属",'
                '"evidence_quote":"变革型领导对员工工作满意度的影响","confidence":0.85,"novelty_hint":null}]}'
            )
            return SimpleNamespace(
                content=content,
                fields={"usage": {"prompt_tokens": 200, "completion_tokens": 50}},
            )

        ext = LLMExtractor(store, budget, llm_chat_fn=fake_chat)
        stats = ext.extract_for_article(aid)
        assert stats.constructs_kept >= 1
        # 候选应入库
        assert store.count_candidates(status="pending") >= 1
        store.close()

    def test_extract_grounding_failure_drops_candidate(self, feed_root):
        from src.literature_feed.extract.extractor import LLMExtractor
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.budget_tracker import BudgetTracker
        from src.literature_feed.storage.feed_store import ArticleRow

        store = FeedStore()
        budget = BudgetTracker(monthly_limit_usd=10.0)
        store.upsert_source(source_id="J", journal_name="心理科学", fetcher_type="manual")
        aid = store.upsert_article(ArticleRow(
            title="t", source_id="J", provenance="manual", title_norm="t",
            abstract="一段完全不会包含 quote 的摘要，只讲 ABC 三个字母。",
            issued_date="2026-05-01",
            fetched_at="2026-05-29T00:00:00Z",
        ))

        def fake_chat(messages, *, model, temperature):
            # quote 不在 abstract 里 → grounding fail
            content = (
                '{"constructs":[{"name":"假构念","definition":"x",'
                '"evidence_quote":"完全没出现的逐字内容十字以上abc","confidence":0.9,"novelty_hint":null}]}'
            )
            return SimpleNamespace(
                content=content,
                fields={"usage": {"prompt_tokens": 100, "completion_tokens": 30}},
            )

        ext = LLMExtractor(store, budget, llm_chat_fn=fake_chat)
        stats = ext.extract_for_article(aid)
        # grounding 失败 → constructs_kept 应为 0；retry 后仍失败会落到 needs_review 或 rejected
        assert stats.constructs_kept == 0
        assert (stats.constructs_rejected + stats.needs_review) >= 1
        store.close()

    def test_extract_returns_zero_when_no_abstract(self, feed_root):
        from src.literature_feed.extract.extractor import LLMExtractor
        from src.literature_feed.storage import FeedStore
        from src.literature_feed.storage.budget_tracker import BudgetTracker
        from src.literature_feed.storage.feed_store import ArticleRow

        store = FeedStore()
        budget = BudgetTracker(monthly_limit_usd=10.0)
        store.upsert_source(source_id="J", journal_name="心理科学", fetcher_type="manual")
        aid = store.upsert_article(ArticleRow(
            title="无摘要", source_id="J", provenance="manual", title_norm="无摘要",
            abstract=None, issued_date="2026-05-01",
            fetched_at="2026-05-29T00:00:00Z",
        ))

        called = {"n": 0}

        def fake_chat(messages, *, model, temperature):
            called["n"] += 1
            return SimpleNamespace(content="{}", fields={"usage": {"prompt_tokens": 1, "completion_tokens": 1}})

        ext = LLMExtractor(store, budget, llm_chat_fn=fake_chat)
        stats = ext.extract_for_article(aid)
        # 没摘要 → 应该跳过，不调 LLM
        assert called["n"] == 0
        assert stats.constructs_kept == 0
        assert stats.methods_kept == 0
        store.close()
