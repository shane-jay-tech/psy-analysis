"""Round 3 — method_weights UI 保存 + scheduler 接入回归（2026-05-30）。

验证：
1. _save_method_weights 写出来的 YAML 能被 MethodWeights.from_yaml_path 重新读回，
   round-trip 一致（canonical / synonyms / multiplier 全保持）
2. _save_method_weights 容忍空 canonical（不应写入空行）
3. DailyRunner 默认会加载 method_weights（不传也能跑）
4. DailyRunner 接受外部注入的 method_weights
"""

from __future__ import annotations

import pytest

from src.literature_feed.trend.method_weights import MethodWeights
from src.literature_feed.ui.feed_panel import _save_method_weights


@pytest.fixture
def tmp_method_yaml(tmp_path):
    """临时 method_weights.yaml 路径（通过 target_path 显式注入，避免 monkeypatch 模块属性）。"""
    return tmp_path / "method_weights.yaml"


class TestSaveRoundTrip:
    def test_save_and_reload(self, tmp_method_yaml):
        rows = [
            {"canonical": "纵向设计", "synonyms": "longitudinal, longitudinal study"},
            {"canonical": "HLM", "synonyms": "multilevel model, 多层模型"},
            {"canonical": "experience sampling", "synonyms": "ESM, EMA"},
        ]
        _save_method_weights(
            rows, default_weight=1.0, method_multiplier=1.5,
            target_path=tmp_method_yaml,
        )

        assert tmp_method_yaml.exists()
        mw = MethodWeights.from_yaml_path(tmp_method_yaml)
        assert mw.default_weight == 1.0
        assert mw.method_multiplier == 1.5
        canonicals = mw.all_canonical()
        assert canonicals == ["纵向设计", "HLM", "experience sampling"]

        # synonyms 反查
        assert mw.canonical_for("longitudinal study") == "纵向设计"
        assert mw.canonical_for("multilevel model") == "HLM"
        assert mw.canonical_for("ESM") == "experience sampling"

    def test_save_skips_empty_canonical(self, tmp_method_yaml):
        rows = [
            {"canonical": "纵向设计", "synonyms": "longitudinal"},
            {"canonical": "  ", "synonyms": "this should be dropped"},  # 空 canonical
            {"canonical": "", "synonyms": ""},                            # 完全空
            {"canonical": "HLM", "synonyms": ""},
        ]
        _save_method_weights(
            rows, default_weight=1.0, method_multiplier=1.5,
            target_path=tmp_method_yaml,
        )

        mw = MethodWeights.from_yaml_path(tmp_method_yaml)
        canonicals = mw.all_canonical()
        assert canonicals == ["纵向设计", "HLM"], (
            f"空 canonical 应被丢弃，实际剩余 {canonicals}"
        )

    def test_save_with_custom_multiplier(self, tmp_method_yaml):
        rows = [{"canonical": "纵向设计", "synonyms": "longitudinal"}]
        _save_method_weights(
            rows, default_weight=1.0, method_multiplier=2.0,
            target_path=tmp_method_yaml,
        )

        mw = MethodWeights.from_yaml_path(tmp_method_yaml)
        assert mw.method_multiplier == 2.0
        # 验证乘子真的被使用：每个命中现在是 (2.0 - 1.0) = 1.0 不是 0.5
        assert abs(mw.score_hits(["纵向设计"]) - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# DailyRunner 接入
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_store(tmp_path):
    """tmp DB FeedStore，避免 DailyRunner 默认构造打开真实 DB。"""
    from src.literature_feed.storage.feed_store import FeedStore
    db = tmp_path / "test_feed.sqlite"
    store = FeedStore(db)
    yield store
    store.close()


class TestDailyRunnerLoadsMethodWeights:
    def test_runner_default_loads_method_weights_from_disk(self, isolated_store):
        """不传 method_weights 时，runner.method_weights 不应该是 None。"""
        from src.literature_feed.scheduler.daily_runner import DailyRunner

        runner = DailyRunner(store=isolated_store)
        try:
            assert runner.method_weights is not None
            # 用 type-name 检查避免 pytest 双重 import 导致的 isinstance False positive
            assert type(runner.method_weights).__name__ == "MethodWeights"
            # 行为检查：实例响应 score_hits / all_canonical
            assert hasattr(runner.method_weights, "score_hits")
            assert isinstance(runner.method_weights.all_canonical(), list)
        finally:
            runner.close()

    def test_runner_accepts_injected_method_weights(self, isolated_store):
        from src.literature_feed.scheduler.daily_runner import DailyRunner

        custom = MethodWeights.from_mapping({
            "version": 1,
            "default_weight": 1.0,
            "method_multiplier": 3.0,
            "methods": [{"canonical": "纵向设计", "synonyms": ["longitudinal"]}],
        })

        runner = DailyRunner(store=isolated_store, method_weights=custom)
        try:
            assert runner.method_weights is custom
            assert runner.method_weights.method_multiplier == 3.0
        finally:
            runner.close()
