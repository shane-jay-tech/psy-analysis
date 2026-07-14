"""文献雷达无头 LLM 解析测试（修复：无 UI 会话时抽取拿不到 key）。

覆盖：
- resolve_headless_model: 首选命中 / 回退链 / 全缺返回 None / env 覆盖首选
- make_headless_llm_chat: 注入 llm_config=cfg、强制用 cfg['model']（忽略传入 model）
- DailyRunner 集成: 解析不到 → _build_extractor 返回 None 且 _run_extraction 优雅跳过不调 LLM；
  解析到 → extractor.model == cfg['model']

全程不真调网络。
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
    # 不让真实 PSY_FEED_MODEL_ID 干扰默认路径
    monkeypatch.delenv("PSY_FEED_MODEL_ID", raising=False)
    return tmp_path


_FULL_CFG = {"provider": "openai", "base_url": "http://x", "api_key": "k-123",
             "model": "deepseek-v4-pro", "timeout": 60}


# =============================================================================
# resolve_headless_model
# =============================================================================

class TestResolveHeadlessModel:

    def test_preferred_default_deepseek_hit(self, feed_root, monkeypatch):
        import src.llm_gateway.quick_models as qm
        monkeypatch.setattr(qm, "load_env_local", lambda *a, **k: {})
        calls = []

        def _fake_cfg(mid):
            calls.append(mid)
            return dict(_FULL_CFG) if mid == "deepseek" else None

        monkeypatch.setattr(qm, "get_quick_model_config", _fake_cfg)
        from src.literature_feed.extract.headless_llm import resolve_headless_model
        cfg = resolve_headless_model()
        assert cfg is not None
        assert cfg["api_key"] == "k-123"
        assert cfg["model"] == "deepseek-v4-pro"
        assert calls[0] == "deepseek"  # 默认首选

    def test_env_overrides_preferred(self, feed_root, monkeypatch):
        monkeypatch.setenv("PSY_FEED_MODEL_ID", "gpt")
        import src.llm_gateway.quick_models as qm
        monkeypatch.setattr(qm, "load_env_local", lambda *a, **k: {})

        def _fake_cfg(mid):
            if mid == "gpt":
                return {**_FULL_CFG, "model": "gpt-5.5-pro"}
            return None

        monkeypatch.setattr(qm, "get_quick_model_config", _fake_cfg)
        from src.literature_feed.extract.headless_llm import resolve_headless_model
        cfg = resolve_headless_model()
        assert cfg is not None
        assert cfg["model"] == "gpt-5.5-pro"

    def test_falls_back_when_preferred_missing(self, feed_root, monkeypatch):
        import src.llm_gateway.quick_models as qm
        monkeypatch.setattr(qm, "load_env_local", lambda *a, **k: {})

        # deepseek（首选）配不齐，gpt 可用 → 回退到 gpt
        def _fake_cfg(mid):
            if mid == "gpt":
                return {**_FULL_CFG, "model": "gpt-5.5-pro"}
            return None  # deepseek/kimi/claude 全缺

        monkeypatch.setattr(qm, "get_quick_model_config", _fake_cfg)
        from src.literature_feed.extract.headless_llm import resolve_headless_model
        cfg = resolve_headless_model()
        assert cfg is not None
        assert cfg["model"] == "gpt-5.5-pro"

    def test_returns_none_when_all_missing(self, feed_root, monkeypatch):
        import src.llm_gateway.quick_models as qm
        monkeypatch.setattr(qm, "load_env_local", lambda *a, **k: {})
        monkeypatch.setattr(qm, "get_quick_model_config", lambda mid: None)
        from src.literature_feed.extract.headless_llm import resolve_headless_model
        assert resolve_headless_model() is None

    def test_cfg_without_apikey_is_rejected(self, feed_root, monkeypatch):
        import src.llm_gateway.quick_models as qm
        monkeypatch.setattr(qm, "load_env_local", lambda *a, **k: {})
        # 有 model 但无 api_key → 视为不可用
        monkeypatch.setattr(qm, "get_quick_model_config",
                            lambda mid: {"model": "m", "api_key": ""})
        from src.literature_feed.extract.headless_llm import resolve_headless_model
        assert resolve_headless_model() is None


# =============================================================================
# make_headless_llm_chat
# =============================================================================

class TestMakeHeadlessLLMChat:

    def test_injects_llm_config_and_forces_model(self, feed_root, monkeypatch):
        import src.llm_gateway.gateway as gw
        captured = {}

        def _fake_llm_chat(messages, *, model=None, temperature=0.7,
                           llm_config=None, **kw):
            captured["model"] = model
            captured["temperature"] = temperature
            captured["llm_config"] = llm_config
            return SimpleNamespace(content="ok", fields={})

        monkeypatch.setattr(gw, "llm_chat", _fake_llm_chat)

        from src.literature_feed.extract.headless_llm import make_headless_llm_chat
        cfg = dict(_FULL_CFG)
        chat = make_headless_llm_chat(cfg)
        # 调用方故意传一个错的 model，应被忽略
        resp = chat([{"role": "user", "content": "hi"}], model="gpt-5.5-pro", temperature=0.9)

        assert resp.content == "ok"
        assert captured["llm_config"] == cfg           # 注入了 cfg
        assert captured["model"] == "deepseek-v4-pro"  # 强制用 cfg 的模型名，忽略传入
        assert captured["temperature"] == 0.9          # 透传 temperature


# =============================================================================
# DailyRunner 集成
# =============================================================================

class TestBuildExtractorIntegration:

    def _make_runner(self):
        from src.literature_feed.scheduler import DailyRunner
        from src.literature_feed.storage import FeedStore
        store = FeedStore()
        return DailyRunner(store=store), store

    def test_build_extractor_none_when_unresolved(self, feed_root, monkeypatch):
        import src.literature_feed.extract.headless_llm as hlm
        monkeypatch.setattr(hlm, "resolve_headless_model", lambda: None)
        runner, store = self._make_runner()
        try:
            assert runner._build_extractor() is None
        finally:
            store.close()

    def test_run_extraction_skips_gracefully_when_none(self, feed_root, monkeypatch):
        import src.literature_feed.extract.headless_llm as hlm
        monkeypatch.setattr(hlm, "resolve_headless_model", lambda: None)
        from src.literature_feed.scheduler.daily_runner import RunSummary
        runner, store = self._make_runner()
        try:
            summary = RunSummary(run_id=1, trigger="test", started_at="2026-06-05T00:00:00Z")
            # 不应抛异常、不应调 LLM、计数保持 0
            runner._run_extraction(summary, article_ids=[1, 2, 3])
            assert summary.extracted_articles == 0
            assert summary.extracted_failed == 0
        finally:
            store.close()

    def test_build_extractor_uses_resolved_model(self, feed_root, monkeypatch):
        import src.literature_feed.extract.headless_llm as hlm
        monkeypatch.setattr(hlm, "resolve_headless_model", lambda: dict(_FULL_CFG))
        # make_headless_llm_chat 返回一个不会真调网络的占位
        monkeypatch.setattr(hlm, "make_headless_llm_chat",
                            lambda cfg: (lambda *a, **k: None))
        runner, store = self._make_runner()
        try:
            extractor = runner._build_extractor()
            assert extractor is not None
            assert extractor.model == "deepseek-v4-pro"  # model 设成真实模型名
        finally:
            store.close()

    def test_factory_path_unchanged(self, feed_root):
        """传 extractor_factory 时仍走工厂，不碰 headless 解析。"""
        from src.literature_feed.scheduler import DailyRunner
        from src.literature_feed.storage import FeedStore
        sentinel = object()

        def _factory(store, budget):
            return sentinel

        store = FeedStore()
        runner = DailyRunner(store=store, extractor_factory=_factory)
        try:
            assert runner._build_extractor() is sentinel
        finally:
            store.close()
