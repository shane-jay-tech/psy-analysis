# -*- coding: utf-8 -*-
"""s927-58：`feed_panel` 读侧键名与生产者 `RunSummary.to_dict()` 的契约钉桩。

缺陷（s924-17 交主班定单）：`src/literature_feed/ui/feed_panel.py` 的「最近抓取审计」表
读 `summary.get("articles_new"/"constructs"/"methods")`，而生产者
`src/literature_feed/scheduler/daily_runner.py::RunSummary.to_dict()` 写的键是
`extracted_articles` / `extracted_constructs` / `extracted_methods` —— **三键全失配**，
`dict.get` 拿默认值 0 ⇒ UI 恒显示 0，把「这次抓到多少篇」的账静默抹平。

盘上实况（本班 `git status --porcelain` 现点，产出时 feed_panel.py 干净、可动）：
`data/literature_feed/feed.sqlite` 里 44 条 fetch_runs、34 条带 summary_json，
其中 18 条 extracted_* 非零，**0 条**带 articles_new/constructs/methods 旧键
⇒ 无需向后兼容分支（加了就是死代码）。

口径：**生产者零改动**（完成标准③）。三例分别钉：
① 契约：读侧用到的每个 summary 键必须 ∈ 生产者键集（这条就是漏掉的闸）；
② 行为：非零 run 渲染出非零读数（修复前恒 0，红）；
③ 反向：生产者键集里不存在旧读键（防有人把失配键「补」成兼容分支）。

harness 复用 tests/test_feed_panel_charac.py 的假 `st` 思路：零 sqlite、零联网、
零 LLM、零子进程 —— 真库只在本文件的「盘上实况」注释里被引用，测试不打开它。
"""
from __future__ import annotations

import inspect
import json
import re
from typing import Any, Dict, List

import pytest

import src.literature_feed.ui.feed_panel as fp
from src.literature_feed.scheduler.daily_runner import RunSummary

# 生产者写入的三个读数键（改这里必须同步改生产码，否则 ① 立刻红）
PRODUCER_READ_KEYS = ("extracted_articles", "extracted_constructs", "extracted_methods")
# 修复前读侧用错的三个键（s924-17 原报口径）
LEGACY_WRONG_KEYS = ("articles_new", "constructs", "methods")


# ───────────────────────────── 假 st / 假 store ─────────────────────────────
# s930-15：_Ctx 与收集桶基座抽至 tests/_feed_st_harness.py（s927-58 遗留「单点抽出」）；
# button（恒 False 零副作用口径）/columns（int 断言）/dataframe（list 形状）三核心语义
# 已分叉，由本件覆写保留。本件无 session_state 面（不继承 FakeState 需求）。
from tests._feed_st_harness import FeedStBase, _Ctx  # noqa: F401


class _ColConfig:
    @staticmethod
    def CheckboxColumn(**k):
        return ("checkbox", k)


class FakeSt(FeedStBase):
    def __init__(self):
        super().__init__()
        self.dataframes: List[List[Dict[str, Any]]] = []
        self.buttons: List[str] = []
        self.column_config = _ColConfig()




    def columns(self, n=1, **k):
        assert isinstance(n, int), "feed_panel 只按 int 请求列，勿在此扩面"
        return [_Ctx(self, f"col{i}", kind="col") for i in range(n)]

    def button(self, label, **k):
        # 恒 False：不点「立即抓取」/「刷新」，否则会用子进程或 st.rerun 打破零副作用口径
        self.buttons.append(label)
        return False

    def dataframe(self, data, **k):
        self.dataframes.append(list(data))

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return list(self._rows)


class _Conn:
    """只认 feed_panel 实际发出的那条 SELECT，其余 SQL 当场红（防悄悄扩面）。"""

    def __init__(self, rows, seen):
        self._rows, self._seen = rows, seen

    def execute(self, sql, *a, **k):
        self._seen.append(" ".join(sql.split()))
        return _Result(self._rows)


class FakeStore:
    def __init__(self, run_rows):
        self._run_rows = run_rows
        self.seen_sql: List[str] = []
        self.connection = _Conn(self._run_rows, self.seen_sql)

    def list_sources(self):
        # 只要有一条来源，_render_sources_tab 才会走到「最近抓取审计」段
        return [{"source_id": "src-1", "journal_name": "Acta Psychologica",
                 "fetcher_type": "crossref", "status": "ok",
                 "last_success_at": "2026-09-23T04:00:00Z", "enabled": 1}]


def _producer_row(run_id: int, *, articles: int, constructs: int, methods: int) -> Dict[str, Any]:
    """按生产者的真实序列化路径造一行：RunSummary.to_dict() → json.dumps。"""
    summary = RunSummary(
        run_id=run_id, trigger="ui_manual",
        started_at="2026-09-23T04:00:00Z", ended_at="2026-09-23T04:01:00Z",
        status="completed",
        extracted_articles=articles, extracted_constructs=constructs,
        extracted_methods=methods, extracted_failed=0,
    )
    return {
        "run_id": run_id, "trigger": "ui_manual",
        "started_at": summary.started_at, "ended_at": summary.ended_at,
        "status": summary.status,
        "summary_json": json.dumps(summary.to_dict(), ensure_ascii=False),
    }


@pytest.fixture
def render(monkeypatch):
    def _render(run_rows):
        st = FakeSt()
        monkeypatch.setattr(fp, "st", st)
        store = FakeStore(run_rows)
        fp._render_sources_tab(store)
        return st, store
    return _render


# ───────────────────────────── ① 键名契约 ─────────────────────────────
def test_readside_summary_keys_are_subset_of_producer_keys():
    """读侧 `summary.get("<key>")` 的每个键必须真在生产者键集里。

    这是 s924-17 缺的那道闸：键名失配不会抛错，只会静默取默认值，
    所以只能用「源码里读到的键 ⊆ 生产者写出的键」来钉。
    """
    src = inspect.getsource(fp._render_sources_tab)
    read_keys = set(re.findall(r'summary\.get\(\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']', src))
    assert read_keys, "锚点漂移：_render_sources_tab 里已无 summary.get(...) 可读键，请复核本单"

    producer_keys = set(RunSummary(
        run_id=1, trigger="t", started_at="x",
    ).to_dict())

    assert read_keys <= producer_keys, (
        f"读侧键 {sorted(read_keys - producer_keys)} 生产者从不写入 ⇒ UI 恒为默认值"
    )
    assert read_keys == set(PRODUCER_READ_KEYS), f"读数键集应为 {PRODUCER_READ_KEYS}，实为 {sorted(read_keys)}"


def test_producer_never_writes_the_legacy_wrong_keys():
    """反向闸：生产者键集里没有 articles_new/constructs/methods。

    命中即说明有人改生产码去「兼容」旧读键 —— 那是把失配搬到另一侧，
    本单口径是**生产者零改动**、只改读侧。
    """
    producer_keys = set(RunSummary(run_id=1, trigger="t", started_at="x").to_dict())
    assert not (producer_keys & set(LEGACY_WRONG_KEYS))


# ───────────────────────────── ② 行为读数 ─────────────────────────────
def test_render_shows_nonzero_counts_from_producer_dict(render):
    """run_id=33 盘上实况：extracted_articles=12 / constructs=4 / methods=0。

    修复前两列恒 0（失配），修复后取到 12/4；methods 本来就写 0，
    用「非零列必须非零」而非「全列相等」来断言，避免被 0 掩过去。
    """
    st, _store = render([_producer_row(33, articles=12, constructs=4, methods=0)])
    assert len(st.dataframes) == 2, "应为「抓取来源」＋「最近抓取审计」两帧"
    audit = st.dataframes[1]
    assert len(audit) == 1
    row = audit[0]
    assert row["新文章"] == 12
    assert row["构念"] == 4
    assert row["方法"] == 0
    assert row["run_id"] == 33 and row["状态"] == "completed"


def test_render_zero_row_is_not_masked_as_missing(render):
    """生产者全写 0 时读侧也显示 0 —— 与「键失配导致的 0」同形，
    故用非零例（上一测）与 NULL 例（本测）配对，钉住「0 来自数据而非失配」。
    """
    null_row = {"run_id": 42, "trigger": "scheduler", "started_at": "2026-09-20T00:00:00Z",
                "ended_at": None, "status": "abandoned", "summary_json": None}
    st, _store = render([null_row])
    row = st.dataframes[1][0]
    assert (row["新文章"], row["构念"], row["方法"]) == (0, 0, 0)
    assert row["结束"] == ""


def test_only_the_expected_select_is_issued(render):
    """扩面自检：本函数对 store.connection 只发 fetch_runs 那一条 SELECT。"""
    st, store = render([_producer_row(33, articles=12, constructs=4, methods=0)])
    assert len(store.seen_sql) == 1
    assert store.seen_sql[0].startswith("SELECT run_id, trigger, started_at, ended_at, status, summary_json FROM fetch_runs")
