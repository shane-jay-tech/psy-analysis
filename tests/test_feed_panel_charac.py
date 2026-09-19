# -*- coding: utf-8 -*-
"""src/literature_feed/ui/feed_panel.py 入口与「每日动态」分支头钉桩（s920-14）。

锚点（实测仍成立）：`:60 render_literature_feed()`（模块 882 行）与 `:121 _render_daily_tab(store)`
—— 两者此前在 `tests/` 里**零命中**（`test_literature_feed_ui.py` 测的是别的模块，
`_apply_trending_override` 已有 s918 那批 7 例，本单不重复）。

假 `st` harness：`FeedStore` / `bootstrap_check` 三入口 / `load_default_*` 全打在
**feed_panel 模块属性**上（它们是模块级 `from ... import`，一次性绑定，换源模块没用）⇒
**零 sqlite、零联网、零 LLM、零子进程**。未预期的 `st.*` 当场 assert 红。
"""
from types import SimpleNamespace

import pytest

import src.literature_feed.ui.feed_panel as fp


class FakeState(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _Ctx:
    def __init__(self, host, label="", kind="ctx"):
        self.host, self.label, self.kind = host, label, kind

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _ColConfig:
    @staticmethod
    def TextColumn(label, **k):
        return ("text", label, k)


class FakeSt:
    def __init__(self, clicked=()):
        self.session_state = FakeState()
        self.clicked = set(clicked)
        self.titles, self.captions, self.markdowns = [], [], []
        self.errors, self.warnings, self.successes, self.infos, self.toasts = [], [], [], [], []
        self.tabs_arg, self.columns_args, self.dataframes = None, [], []
        self.buttons, self.dividers, self.reruns = [], 0, 0
        self.containers = 0
        self.column_config = _ColConfig()

    def title(self, msg, **k):
        self.titles.append(msg)

    def caption(self, msg, **k):
        self.captions.append(msg)

    def markdown(self, msg, **k):
        self.markdowns.append(msg)

    def error(self, msg, **k):
        self.errors.append(msg)

    def warning(self, msg, **k):
        self.warnings.append(msg)

    def success(self, msg, **k):
        self.successes.append(msg)

    def info(self, msg, **k):
        self.infos.append(msg)

    def toast(self, msg, **k):
        self.toasts.append(msg)

    def divider(self, **k):
        self.dividers += 1

    def container(self, **k):
        self.containers += 1
        return _Ctx(self, kind="container")

    def expander(self, label, **k):
        return _Ctx(self, label, kind="expander")

    def tabs(self, labels, **k):
        self.tabs_arg = list(labels)
        return [_Ctx(self, lbl, kind="tab") for lbl in labels]

    def columns(self, widths=None, **k):
        self.columns_args.append(widths)
        return [_Ctx(self, f"col{i}", kind="col") for i in range(len(widths or [1]))]

    def dataframe(self, data, **k):
        self.dataframes.append((list(data), k))

    def button(self, label, **k):
        self.buttons.append((label, k))
        return label in self.clicked

    def rerun(self, **k):
        self.reruns += 1

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


class FakeStore:
    def __init__(self, candidates=(), articles=(), pending_total=None, boom=False):
        self.candidates, self.articles = list(candidates), list(articles)
        self.pending_total = pending_total if pending_total is not None else len(self.candidates)
        self.boom, self.closed, self.status_writes = boom, 0, []

    def __call__(self, *a, **k):  # 顶替 FeedStore() 构造
        if self.boom:
            raise RuntimeError("unable to open database file")
        return self

    def list_candidates(self, status="pending", limit=20):
        return list(self.candidates)

    def count_candidates(self, status="pending"):
        return self.pending_total

    def list_articles(self, since=None, limit=30):
        return list(self.articles)

    def update_candidate_status(self, cid, status="approved", reviewer=""):
        self.status_writes.append((cid, status, reviewer))

    def close(self):
        self.closed += 1


@pytest.fixture
def entry(monkeypatch):
    """入口级 harness：四个 tab 渲染器换成记录桩，只钉"接线"不下钻。"""
    st = FakeSt()
    store = FakeStore()
    calls = {"trigger": 0, "rendered": [], "weights_arg": None, "trending_arg": None}

    monkeypatch.setattr(fp, "st", st)
    monkeypatch.setattr(fp, "FeedStore", store)

    def fake_trigger():
        calls["trigger"] += 1

    monkeypatch.setattr(fp, "maybe_trigger_async", fake_trigger)

    def rec(kind, name):
        def _fn(*a, **k):
            calls["rendered"].append((kind, a))
            if kind == "trend":
                calls["weights_arg"], calls["trending_arg"] = a[1], a[2]
            if kind == "settings":
                calls["weights_arg"] = a[1]

        return _fn

    for kind, fn in (("daily", "_render_daily_tab"), ("trend", "_render_trend_tab"),
                     ("sources", "_render_sources_tab"), ("settings", "_render_settings_tab")):
        monkeypatch.setattr(fp, fn, rec(kind, fn))
    return st, store, calls, monkeypatch


def _set_weights(entry, impl):
    _, _, _, monkeypatch = entry
    monkeypatch.setattr(fp, "load_default_weights", impl)


# ─────────────────────────── 入口 render_literature_feed ───────────────────────────
def test_entry_renders_four_tabs_in_order_and_always_closes_store(entry):
    st, store, calls, _ = entry
    fp.render_literature_feed()

    assert st.titles == ["📡 文献雷达"] and len(st.captions) == 1
    assert st.tabs_arg == ["📰 每日动态", "📊 趋势分析", "🛰 来源管理", "⚙️ 设置"]
    assert [k for k, _ in calls["rendered"]] == ["daily", "trend", "sources", "settings"]
    assert store.closed == 1  # 短生命周期：render 用完必关


def test_entry_closes_store_even_when_a_tab_raises(entry):
    st, store, calls, monkeypatch = entry

    def boom(*a):
        raise RuntimeError("tab 里炸了")

    monkeypatch.setattr(fp, "_render_sources_tab", boom)
    with pytest.raises(RuntimeError):
        fp.render_literature_feed()

    assert store.closed == 1  # finally 兜底：炸在半路也不留连接


def test_entry_bootstrap_fires_once_per_session(entry):
    st, store, calls, _ = entry
    fp.render_literature_feed()
    fp.render_literature_feed()

    assert calls["trigger"] == 1  # 第二次不再触发 ⇒ 不制造 rerun 风暴
    assert st.session_state[fp._BOOTSTRAP_SESSION_KEY] is True


def test_entry_bootstrap_failure_is_swallowed_yet_key_still_set(entry):
    st, store, calls, monkeypatch = entry

    def boom():
        raise OSError("没有网络")

    monkeypatch.setattr(fp, "maybe_trigger_async", boom)
    fp.render_literature_feed()

    assert st.errors == [] and st.warnings == []  # 现状：只 logger.warning，用户零知情
    assert st.session_state[fp._BOOTSTRAP_SESSION_KEY] is True  # 失败也算"本 session 试过了"
    assert [k for k, _ in calls["rendered"]] == ["daily", "trend", "sources", "settings"]


def test_entry_db_open_failure_short_circuits_before_any_tab(entry):
    st, _, calls, monkeypatch = entry
    broken = FakeStore(boom=True)
    monkeypatch.setattr(fp, "FeedStore", broken)

    fp.render_literature_feed()

    assert calls["rendered"] == [] and st.tabs_arg is None
    assert len(st.errors) == 1 and "数据库打开失败" in st.errors[0] and "unable to open" in st.errors[0]
    assert any("--trigger init" in i for i in st.infos)  # 给的可执行补救命令，不是"未知错误"


def test_entry_weights_failure_degrades_to_empty_vocab_and_keeps_rendering(entry):
    st, store, calls, _ = entry
    _set_weights(entry, lambda: (_ for _ in ()).throw(FileNotFoundError("权重 yaml 不在")))

    fp.render_literature_feed()

    assert len(st.warnings) == 1 and "加载域权重失败" in st.warnings[0]
    assert isinstance(calls["weights_arg"], fp.DomainWeights)
    assert [k for k, _ in calls["rendered"]] == ["daily", "trend", "sources", "settings"]
    assert store.closed == 1


def test_entry_trending_failure_is_logger_only(entry):
    st, store, calls, monkeypatch = entry
    _set_weights(entry, lambda: fp.DomainWeights.empty())
    monkeypatch.setattr(fp, "load_default_trending",
                        lambda: (_ for _ in ()).throw(ValueError("trending 坏了")))

    fp.render_literature_feed()

    assert isinstance(calls["trending_arg"], fp.TrendingWeights)
    assert len(calls["trending_arg"].promoted) == 0 and len(calls["trending_arg"].ignored) == 0  # 落到 empty()
    assert st.errors == []  # 与权重失败不同：这条对用户完全静默（现状，只钉不改）


# ─────────────────────────── Tab 1 _render_daily_tab ───────────────────────────
def _daily(store=None, running=False, hours=None, last_result=None, clicked=(), monkeypatch=None):
    st = FakeSt(clicked=clicked)
    monkeypatch.setattr(fp, "st", st)
    monkeypatch.setattr(fp, "bootstrap_is_running", lambda: running)
    monkeypatch.setattr(fp, "bootstrap_evaluate", lambda: SimpleNamespace(last_success_hours=hours))
    monkeypatch.setattr(fp, "bootstrap_last_result", lambda: last_result)
    fp._render_daily_tab(store or FakeStore())
    return st


@pytest.mark.parametrize(
    "running,hours,want",
    [
        (True, None, ("info", "后台抓取进行中")),
        (False, None, ("warning", "从未跑过自动抓取")),
        (False, 3.5, ("success", "上次成功抓取于 3.5 小时前")),
        (False, 30.0, ("warning", "距上次成功 30.0h")),
    ],
)
def test_daily_status_banner_has_exactly_one_voice(running, hours, want, monkeypatch):
    level, frag = want
    st = _daily(running=running, hours=hours, monkeypatch=monkeypatch)
    said = {"info": st.infos, "warning": st.warnings, "success": st.successes, "error": st.errors}

    assert any(frag in m for m in said[level]), (level, frag, said)
    assert sum(len(v) for v in said.values()) == 1  # 四态互斥，一次只出一个声音


def test_daily_running_disables_the_manual_button(monkeypatch):
    st = _daily(running=True, hours=None, monkeypatch=monkeypatch)
    label, kwargs = st.buttons[0]
    assert label == "🚀 立即抓取" and kwargs["disabled"] is True


def test_daily_last_result_failed_is_error_otherwise_caption_with_budget_flag(monkeypatch):
    st = _daily(last_result={"status": "failed", "error": "锁被占"}, monkeypatch=monkeypatch)
    assert any("上次后台运行失败：锁被占" in e for e in st.errors)

    st2 = _daily(
        last_result={"status": "ok", "sources_ok": 4, "sources_total": 5,
                     "extracted_constructs": 9, "extracted_methods": 3, "budget_exceeded": True},
        monkeypatch=monkeypatch,
    )
    joined = "".join(st2.captions)
    assert "来源 4/5" in joined and "抽取构念 9、方法 3" in joined and "触及月度预算" in joined
    assert st2.errors == []

    st3 = _daily(last_result={"status": "ok", "sources_ok": 1, "sources_total": 1},
                 monkeypatch=monkeypatch)
    assert "触及月度预算" not in "".join(st3.captions)  # 预算标记缺省时不许凭空加上


def test_daily_empty_store_paths_say_so_and_call_no_write(monkeypatch):
    store = FakeStore()
    st = _daily(store=store, hours=1.0, monkeypatch=monkeypatch)

    assert any("当前没有待审候选" in c for c in st.captions)
    assert any("近 14 天新文（共 0 篇" in m for m in st.markdowns)
    assert any("近 14 天没有新文章" in c and "来源管理" in c for c in st.captions)  # 空态给下一步，不摆空表
    assert store.status_writes == [] and st.reruns == 0
    assert st.dataframes == []


def test_daily_article_rows_are_mapped_and_title_capped_at_80(monkeypatch):
    long_title = "T" * 100
    store = FakeStore(articles=[{"source_id": "psyyc", "title": long_title,
                                "issued_date": "2026-09-01", "doi": "10.1/x"},
                               {"source_id": "rss", "title": "短标题"}])  # 缺 issued/doi
    st = _daily(store=store, hours=1.0, monkeypatch=monkeypatch)

    rows, kwargs = st.dataframes[0]
    assert rows[0] == {"source": "psyyc", "title": "T" * 80, "issued": "2026-09-01", "doi": "10.1/x"}
    assert rows[1] == {"source": "rss", "title": "短标题", "issued": "", "doi": ""}  # 缺字段补空串不补 None
    assert len(rows[0]["title"]) == 80  # 表格标题截断 80 字符
    assert kwargs["hide_index"] is True and kwargs["width"] == "stretch"


def test_daily_manual_trigger_click_toasts_then_reruns(monkeypatch):
    fired = {"n": 0}
    monkeypatch.setattr(fp, "maybe_trigger_async", lambda: fired.__setitem__("n", fired["n"] + 1))
    st = _daily(hours=99.0, clicked={"🚀 立即抓取"}, monkeypatch=monkeypatch)

    assert fired["n"] == 1 and st.toasts and st.reruns == 1


def test_daily_manual_trigger_failure_stays_on_page(monkeypatch):
    def boom():
        raise RuntimeError("锁被别的进程占着")

    monkeypatch.setattr(fp, "maybe_trigger_async", boom)
    st = _daily(hours=99.0, clicked={"🚀 立即抓取"}, monkeypatch=monkeypatch)

    assert any("触发失败：锁被别的进程占着" in e for e in st.errors)
    assert st.toasts == [] and st.reruns == 0  # 失败不许 toast 成功、不许重跑盖掉错误
