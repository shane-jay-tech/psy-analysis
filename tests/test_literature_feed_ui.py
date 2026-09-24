"""v4.7 自学习模块 — UI 层测试（Phase 4f）。

只能测纯函数（不依赖 Streamlit 全局）。Streamlit-testing 框架要等 Phase 4g+ 接入。
覆盖 _save_domain_weights：round-trip / 原子替换 / 空行过滤 / domain 验证。

夹具清理面（pd07 案 A，台账 #94）：原先按前缀删掉**所有** `src.literature_feed*`，
撞上 tests/test_feed_panel_trending_override.py 的「模块期绑定 × 生产函数级懒导入」
⇒ 同跑 8 failed，且那 8 例会把 trending_weights.yaml **真写进 data/literature_feed/**。
现只删本件真正作用的三个模块名（见 _FEED_UI_MODULES）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

# 本件唯一作用的缓存点：paths 计算 DATA_ROOT 与各 *_PATH（导入期求值），
# trend / ui.feed_panel 在导入期把 DOMAIN_WEIGHTS_PATH 绑成模块常量。
# 刻意**不删** src.literature_feed.trend.trending_weights：兄弟件在模块期 import 它
# 并 monkeypatch 其 write_trending_yaml，删了就让补丁打空、生产码懒导入拿到新对象。
_FEED_UI_MODULES = (
    "src.literature_feed.paths",
    "src.literature_feed.trend",
    "src.literature_feed.ui.feed_panel",
)


@pytest.fixture
def feed_root(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    import sys
    for mod in _FEED_UI_MODULES:
        sys.modules.pop(mod, None)
    return tmp_path


class TestSaveDomainWeights:

    def test_round_trip(self, feed_root):
        from src.literature_feed.trend import (
            DOMAIN_WEIGHTS_FILENAME, DomainWeights, default_weights_path,
            load_default_weights,
        )
        from src.literature_feed.ui.feed_panel import _save_domain_weights

        rows = [
            {"domain": "IO", "canonical": "变革型领导", "synonyms": "transformational leadership, 变革型"},
            {"domain": "HR", "canonical": "员工敬业度", "synonyms": "employee engagement"},
            {"domain": "OB", "canonical": "组织承诺", "synonyms": ""},
        ]
        _save_domain_weights(rows, default_weight=1.5, domain_multiplier=2.5)

        target = default_weights_path()
        assert target.exists()
        assert target.name == DOMAIN_WEIGHTS_FILENAME

        w = load_default_weights()
        assert w.default_weight == 1.5
        assert w.domain_multiplier == 2.5
        assert w.canonical_for("transformational leadership") == "变革型领导"
        assert w.canonical_for("employee engagement") == "员工敬业度"
        assert w.domain_for("组织承诺") == "OB"

    def test_skips_empty_canonical(self, feed_root):
        from src.literature_feed.trend import load_default_weights
        from src.literature_feed.ui.feed_panel import _save_domain_weights

        rows = [
            {"domain": "IO", "canonical": "  ", "synonyms": "x"},  # 空 canonical 跳过
            {"domain": "IO", "canonical": "变革型领导", "synonyms": ""},
            {"domain": "", "canonical": "无效域", "synonyms": "x"},  # 空 domain 跳过
        ]
        _save_domain_weights(rows, default_weight=1.0, domain_multiplier=1.5)
        w = load_default_weights()
        assert "变革型领导" in w.flat_synonyms()
        assert "无效域" not in w.flat_synonyms()

    def test_invalid_domain_filtered(self, feed_root):
        from src.literature_feed.trend import load_default_weights
        from src.literature_feed.ui.feed_panel import _save_domain_weights

        rows = [
            {"domain": "XYZ", "canonical": "野域概念", "synonyms": ""},
            {"domain": "IO", "canonical": "正常概念", "synonyms": ""},
        ]
        _save_domain_weights(rows, default_weight=1.0, domain_multiplier=1.5)
        w = load_default_weights()
        assert "正常概念" in w.flat_synonyms()
        assert "野域概念" not in w.flat_synonyms()

    def test_synonyms_split_by_comma(self, feed_root):
        from src.literature_feed.trend import load_default_weights
        from src.literature_feed.ui.feed_panel import _save_domain_weights

        rows = [
            {"domain": "IO", "canonical": "变革型领导",
             "synonyms": "transformational leadership, 变革型,  TFL "},
        ]
        _save_domain_weights(rows, default_weight=1.0, domain_multiplier=1.5)
        w = load_default_weights()
        synonyms = w.flat_synonyms()["变革型领导"]
        assert "transformational leadership" in synonyms
        assert "变革型" in synonyms
        assert "TFL" in synonyms  # 两端 strip

    def test_atomic_replace_preserves_old_on_failure(self, feed_root, monkeypatch):
        """模拟 yaml.safe_dump 抛异常，原文件应不变。"""
        from src.literature_feed.trend import default_weights_path
        from src.literature_feed.ui.feed_panel import _save_domain_weights

        target = default_weights_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("old: content\n", encoding="utf-8")

        import yaml
        original_dump = yaml.safe_dump

        def boom(*a, **kw):
            raise RuntimeError("simulated yaml failure")

        monkeypatch.setattr(yaml, "safe_dump", boom)

        with pytest.raises(RuntimeError):
            _save_domain_weights(
                [{"domain": "IO", "canonical": "x", "synonyms": ""}],
                default_weight=1.0, domain_multiplier=1.5,
            )

        # 原文件应该还在
        assert target.read_text(encoding="utf-8") == "old: content\n"

    def test_compute_domain_summary_key_matches_ui_usage(self):
        """回归保护：UI 用 'weighted' key，aggregator 也得返回这个 key（不要改成 weighted_count）。"""
        from src.literature_feed.trend import TrendRow, compute_domain_summary

        rows = [TrendRow("a", "变革型领导", "IO", 1, 2.0, "2026-05-01")]
        out = compute_domain_summary(rows)
        # UI feed_panel.py 第 ~190 行用 bucket['weighted']，必须一致
        assert "weighted" in out["IO"]
        assert out["IO"]["weighted"] == pytest.approx(2.0)
