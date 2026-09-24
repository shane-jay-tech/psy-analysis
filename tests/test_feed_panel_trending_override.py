"""src/literature_feed/ui/feed_panel._apply_trending_override 钉桩（s918-46）。

`write_trending_yaml` 打桩成捕获器 ⇒ **不写真实 trending_weights.yaml**；
TrendingWeights 用真类型（frozen dataclass）构造，不渲染 Streamlit。
锚点：src/literature_feed/ui/feed_panel.py（模块期常量 DOMAIN_WEIGHTS_PATH、
函数级懒导入 write_trending_yaml；此前仅 _save_domain_weights 被测）。

隔离口径（s924-29）：本件**不做模块期绑定**。兄弟件 tests/test_literature_feed_*.py
的 feed_root 夹具会把 src.literature_feed* 整批从 sys.modules 删掉，模块期 import
到的模块对象因此变成僵尸对象 ⇒ patch 打空、生产码懒导入拿到新模块、
**真写 trending_weights.yaml** 且用例只报 IndexError。现由 `written` 夹具在用例内
现取现 patch（见 test_capture_survives_a_sibling_evicting_every_feed_module）。
"""
import importlib
import sys

import pytest

from src.literature_feed.trend.trending_weights import TrendingWeights
from src.literature_feed.ui.feed_panel import _apply_trending_override

# 与生产懒导入 `from ..trend.trending_weights import ...` 同名的唯一字面串
TRENDING_WEIGHTS_MODULE = "src.literature_feed.trend.trending_weights"
FEED_PACKAGE_PREFIX = "src.literature_feed"


def _tw(ignored=(), promoted=(), log=()):
    return TrendingWeights(entries=(), generated_at="2026-09-19T00:00:00+00:00",
                           window_days=30, baseline_days=90, multiplier_cap=1.2,
                           ignored=tuple(ignored), promoted=tuple(promoted),
                           promoted_log=tuple(log))


@pytest.fixture
def wide_eviction(tmp_path, monkeypatch):
    """复刻兄弟件 feed_root 的**宽口径**驱逐：把 FEED_PACKAGE_PREFIX 下所有模块删出
    sys.modules（现值：7 个 test_literature_feed_* 件仍是这种写法），并留下还原点。

    本夹具刻意不用 monkeypatch.setitem 做还原——它在 teardown 会**再删一次**键，
    等于把驱逐泄漏给后面的用例。
    """
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    snapshot = {k: v for k, v in sys.modules.items() if k.startswith(FEED_PACKAGE_PREFIX)}
    for name in snapshot:
        del sys.modules[name]
    try:
        yield tmp_path
    finally:
        for name in [k for k in sys.modules if k.startswith(FEED_PACKAGE_PREFIX)]:
            del sys.modules[name]
        sys.modules.update(snapshot)


@pytest.fixture
def written(monkeypatch):
    """捕获 write_trending_yaml 的调用；模块对象在夹具期现取，不缓存模块期引用。"""
    calls = []

    def capture(weights, path):
        calls.append((weights, path))

    monkeypatch.setattr(importlib.import_module(TRENDING_WEIGHTS_MODULE),
                        "write_trending_yaml", capture)
    return calls


def test_capture_survives_a_sibling_evicting_every_feed_module(wide_eviction, written):
    """【隔离回归钉桩 s924-29】宽口径驱逐之后，捕获必须仍然命中且不落真盘。

    原缺陷读数（本单实测，非卷宗点名的那一对文件）：与仍做宽口径驱逐的兄弟件连跑时
    本件 8 例全红，错误是 `IndexError: list index out of range`（`written[0]` 取空表），
    同时 trending_weights.yaml 被**真写进沙盒根目录** —— 沙盒守卫缺失时即真库。
    """
    panel = importlib.import_module("src.literature_feed.ui.feed_panel")

    panel._apply_trending_override(_tw(ignored=["AI"], promoted=[]), "推广该关键词", "AI")

    assert len(written) == 1, "补丁打空：本件又退化成模块期绑定，兄弟夹具一驱逐就会真写盘"
    weights, path = written[0]
    assert weights.promoted == ("AI",) and weights.ignored == ()
    assert str(path).endswith("trending_weights.yaml")
    assert not (wide_eviction / "trending_weights.yaml").exists(), \
        "捕获失效 ⇒ 生产码真写盘了（真库无守卫时会落在 data/literature_feed/）"


def test_promote_adds_to_promoted_logs_it_and_clears_ignored(written):
    _apply_trending_override(_tw(ignored=["AI"], promoted=[]), "推广该关键词", "AI")

    weights, path = written[0]
    assert weights.promoted == ("AI",)
    assert weights.ignored == ()
    assert len(weights.promoted_log) == 1 and weights.promoted_log[0].endswith("promoted: AI")
    assert str(path).endswith("trending_weights.yaml")


def test_ignore_adds_to_ignored_and_clears_promoted(written):
    _apply_trending_override(_tw(promoted=["AI"]), "忽略", "AI")

    weights, _ = written[0]
    assert weights.ignored == ("AI",)
    assert weights.promoted == ()
    assert weights.promoted_log == ()          # 忽略不写日志


@pytest.mark.parametrize("action,expect_promoted,expect_ignored", [
    ("取消推广", (), ("AI",)),
    ("取消忽略", ("AI",), ()),
])
def test_undo_actions_touch_only_their_own_list(written, action, expect_promoted, expect_ignored):
    _apply_trending_override(_tw(ignored=["AI"], promoted=["AI"]), action, "AI")

    weights, _ = written[0]
    assert weights.promoted == expect_promoted
    assert weights.ignored == expect_ignored


def test_repeated_promote_does_not_duplicate_promoted_but_grows_log_every_time(written):
    """【不对称现状】promoted 有 `if keyword not in promoted` 守卫，promoted_log 却**无条件追加**。
    按 UI 真实节律模拟：每次 `st.rerun()` 后把上一轮落盘的权重对象喂回来。"""
    trending = _tw()

    for _ in range(3):
        _apply_trending_override(trending, "推广", "AI")
        trending, _ = written[-1]

    assert trending.promoted == ("AI",)               # 去重生效
    assert len(trending.promoted_log) == 3            # 日志每点一次就多一条
    assert all(line.endswith("promoted: AI") for line in trending.promoted_log)


def test_promoted_stores_the_raw_keyword_so_case_and_space_variants_duplicate(written):
    """【缺陷钉桩】去重比较用**归一后的 key**（strip+lower）来"移除"，
    但**加入时判的是原文 `keyword not in promoted` 且存的是原文**
    ⇒ "AI" 与 " ai " 会被当成两个不同条目一起落盘。"""
    _apply_trending_override(_tw(), "推广", "AI")
    weights_after_first, _ = written[0]

    _apply_trending_override(weights_after_first, "推广", "  ai  ")

    weights, _ = written[-1]
    assert weights.promoted == ("AI", "  ai  ")
    assert len({k.strip().lower() for k in weights.promoted}) == 1   # 语义上是同一个词


def test_unknown_action_still_rewrites_the_yaml_without_protection(written):
    """【落盘无保护】action 不匹配任何分支时，函数不报错也不跳过，
    照样用原列表重建并 `write_trending_yaml` 覆盖落盘一次。"""
    trending = _tw(ignored=["AI"], promoted=["X"])

    _apply_trending_override(trending, "随便点什么", "AI")

    assert len(written) == 1
    weights, _ = written[0]
    assert weights.ignored == ("AI",) and weights.promoted == ("X",)


def test_the_persisted_fields_survive_the_rebuild(written):
    """重建 TrendingWeights 时逐字段照抄 ⇒ 窗口/基线/上限/时间戳/entries 都不能被覆写成默认值。"""
    trending = TrendingWeights(entries=(), generated_at="G", window_days=15,
                               baseline_days=120, multiplier_cap=1.5,
                               ignored=("a",), promoted=("b",), promoted_log=("c",))

    _apply_trending_override(trending, "忽略", "NEW")

    weights, _ = written[0]
    assert weights.generated_at == "G" and weights.window_days == 15
    assert weights.baseline_days == 120 and weights.multiplier_cap == 1.5
    assert weights.entries == () and weights.promoted == ("b",)
    assert weights.ignored == ("a", "NEW")
    assert weights.promoted_log == ("c",)
