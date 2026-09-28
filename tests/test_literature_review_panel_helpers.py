# -*- coding: utf-8 -*-
"""src/ui/literature_review_panel.py 三个助手钉桩（s920-13）。

锚点（实测仍成立）：`:198 _do_relevance_rescore(upstream, lr_state)`、`:222 _render_completeness_badge(lr_state)`、
`:754 _materialize_items(items_dict_list)` —— 三者此前在 `tests/` 里**零命中**，唯一调用方是同文件主入口
`render_literature_review`（:109 / :122 / :126）。渲染主干一行不碰。

`rescore_existing_items` / `calculate_completeness` 是模块级 `from ... import` ⇒ 打在 `lrp` 属性上。
假 `st` 对未预期调用当场 assert 红。零网络、零 LLM、零真实 session_state。

**s927-29 追加（2026-09-28，A＋B 施工单）**：文件末尾新增主入口 `:121-123` 的护栏用例，
它**只读**主入口那段（其余渲染口全桩掉），生产码改动见
`docs/insights/s927-29-dirtynum-ab.md`；上面「渲染主干一行不碰」仍适用于 s920-13 本批原始钉桩。
"""
import pytest

import src.ui.literature_review_panel as lrp
from src.literature_review.models import LiteratureItem


class _Ctx:
    def __init__(self, host, label="", kwargs=None):
        self.host, self.label, self.kwargs = host, label, kwargs or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSt:
    def __init__(self):
        self.successes, self.errors, self.captions, self.markdowns = [], [], [], []
        self.expanders, self.columns_args = [], []
        self.warnings = []

    def success(self, msg, **k):
        self.successes.append(msg)

    def error(self, msg, **k):
        self.errors.append(msg)

    def warning(self, msg, **k):
        self.warnings.append(msg)

    def caption(self, msg, **k):
        self.captions.append(msg)

    def markdown(self, msg, **k):
        self.markdowns.append(msg)

    def expander(self, label, **k):
        self.expanders.append((label, k))
        return _Ctx(self, label, k)

    def columns(self, spec=None, **k):
        self.columns_args.append(spec)
        return [_Ctx(self, f"col{i}") for i in range(len(spec or [1]))]

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


def _sub(name, score, weight, suggestion=""):
    from types import SimpleNamespace

    return SimpleNamespace(name=name, score=score, weight=weight, suggestion=suggestion)


def _result(grade, total, subs):
    from types import SimpleNamespace

    return SimpleNamespace(grade=grade, total=total, sub_scores=subs)


@pytest.fixture
def st(monkeypatch):
    fake = FakeSt()
    monkeypatch.setattr(lrp, "st", fake)
    return fake


# ─────────────────────────── _materialize_items ───────────────────────────
def test_materialize_empty_and_none_both_yield_list():
    assert lrp._materialize_items([]) == []
    assert lrp._materialize_items(None) == []  # `or []` 兜底：session 里存了 None 也不炸


def test_materialize_preserves_order_and_yields_real_items():
    dicts = [{"key": "k2", "title": "第二篇"}, {"key": "k1", "title": "第一篇"}]
    items = lrp._materialize_items(dicts)

    assert all(isinstance(i, LiteratureItem) for i in items)
    assert [i.key for i in items] == ["k2", "k1"] and [i.title for i in items] == ["第二篇", "第一篇"]


def test_materialize_backfills_every_missing_field():
    (it,) = lrp._materialize_items([{}])  # 一个键都没有

    assert it.title == "" and it.journal == "" and it.doi == "" and it.authors == [] and it.tags == []
    assert it.year == 0 and it.citation_count == 0 and it.relevance_score == 0.0
    assert it.reading_status == "unread"  # 存的是英文枚举，展示层才翻成中文
    assert it.key and it.added_at  # 缺 id/时间时由 from_dict 现场生成，不留空


def test_materialize_coerces_numeric_strings_but_skips_garbage(st):
    """④ 翻正（s927-29 放行 A 案后按注释改断言，不删例）：数字串照旧强转，脏条**跳过并告警**不再抛。

    原注释「现状：脏数字直接抛出，整页起不来（只钉不改）」的改法已由 `s927-29` 落码
    （`docs/insights/psy-dirtynum-rescore-material-20260921.md` §四 A ＋ §五 测试点 1）。
    """
    (it,) = lrp._materialize_items([{"year": "2019", "citation_count": "12", "relevance_score": "0.75"}])
    assert (it.year, it.citation_count, it.relevance_score) == (2019, 12, 0.75)

    assert lrp._materialize_items([{"title": "脏年", "year": "约 2019"}]) == []  # 不抛，坏条被弃
    assert len(st.warnings) == 1 and "约 2019" in st.warnings[0]  # 告警点名坏在哪个字段


# ── s927-29 §五 测试点 1：一条脏不拖垮整表（改前必红：现状整表弃） ──
def test_materialize_one_dirty_row_keeps_the_good_ones_and_warns_once(st):
    """[好, 脏, 好] ⇒ 产出 2 条（顺序不变）＋恰好 1 条 st.warning（s922-05 §五 测试点 1）。"""
    rows = [
        {"key": "good-1", "title": "前置好条目", "year": "2019"},
        {"key": "dirty", "title": "脏年", "year": "约 2019"},
        {"key": "good-2", "title": "后置好条目", "year": "2020"},
    ]
    items = lrp._materialize_items(rows)

    assert [i.key for i in items] == ["good-1", "good-2"]
    assert [i.year for i in items] == [2019, 2020]
    assert len(st.warnings) == 1, f"应恰好一条告警，实为 {st.warnings}"
    assert "脏年" in st.warnings[0] and "1 条" in st.warnings[0]
    assert st.errors == []  # 告警面是 warning，不升级为 error


# ── s927-29 §五 测试点 2：全脏 ⇒ 空列表 ＋ 一条告警（走空态而非红页） ──
def test_materialize_all_dirty_rows_yields_empty_list_with_single_warning(st):
    """[脏, 脏] ⇒ 返 `[]`（主入口据此走「暂无文献」空态）＋**只一条**告警，不逐条刷屏。"""
    rows = [{"key": "d1", "title": "脏一", "year": "约 2019"},
            {"key": "d2", "title": "脏二", "citation_count": "1,234"}]

    assert lrp._materialize_items(rows) == []
    assert len(st.warnings) == 1
    assert "2 条" in st.warnings[0]


def test_materialize_non_dict_element_still_raises(monkeypatch, st):
    """A 案只兜 `ValueError`/`TypeError`：非 dict 元素照旧抛 ⇒ 不静默掩盖编程错误。

    这条是 A 的**边界否证**：若把 except 放宽成 `Exception`，本例当场红。
    """
    with pytest.raises(AttributeError):
        lrp._materialize_items(["我不是 dict"])
    assert st.warnings == []


def test_materialize_does_not_mutate_or_alias_the_session_list():
    src = [{"key": "a", "title": "原文"}]
    items = lrp._materialize_items(src)
    items[0].title = "改过了"

    assert src[0]["title"] == "原文"  # 拿到的是实例化副本，不是 dict 的引用


# ─────────────────────────── _do_relevance_rescore ───────────────────────────
def test_rescore_skips_silently_when_no_items(monkeypatch, st):
    def never(*a):
        raise AssertionError("没有文献时不该调重打分")

    monkeypatch.setattr(lrp, "rescore_existing_items", never)
    for empty in ([], None):
        lr_state = {"literature_items": empty}
        lrp._do_relevance_rescore({"research_question": "新 RQ"}, lr_state)
        assert lr_state["literature_items"] is empty  # 原样不动（None 也不被改写成 []）
    assert st.successes == []


def test_rescore_passes_new_rq_and_candidate_vars_and_writes_back(monkeypatch, st):
    seen = {}
    new_items = [{"key": "a", "relevance_score": 0.9}]

    def fake_rescore(items, rq, vars_):
        seen["args"] = (items, rq, vars_)
        return new_items

    monkeypatch.setattr(lrp, "rescore_existing_items", fake_rescore)
    old = [{"key": "a", "relevance_score": 0.1}]
    lr_state = {"literature_items": old}
    lrp._do_relevance_rescore({"research_question": " 压力与绩效 ", "candidate_vars": {"iv": "压力"}}, lr_state)

    assert seen["args"] == (old, " 压力与绩效 ", {"iv": "压力"})  # 参数原样透传，不替用户 trim
    assert lr_state["literature_items"] is new_items  # 结果必须回写，否则排名看不见
    assert len(st.successes) == 1 and "重新计算" in st.successes[0]


def test_rescore_treats_missing_candidate_vars_as_empty_dict(monkeypatch, st):
    seen = {}
    monkeypatch.setattr(lrp, "rescore_existing_items",
                        lambda items, rq, vars_: seen.update(v=vars_, rq=rq) or items)
    lrp._do_relevance_rescore({}, {"literature_items": [{"key": "a"}]})

    assert seen["v"] == {} and seen["rq"] == ""  # 上游没填也不能传 None 给打分器


def test_rescore_failure_propagates_and_leaves_state_untouched(monkeypatch, st):
    def boom(*a):
        raise RuntimeError("LLM 打分挂了")

    monkeypatch.setattr(lrp, "rescore_existing_items", boom)
    old = [{"key": "a"}]
    lr_state = {"literature_items": old}

    with pytest.raises(RuntimeError):  # 现状：助手内无 try，失败会冒到主入口
        lrp._do_relevance_rescore({"research_question": "q"}, lr_state)
    assert lr_state["literature_items"] is old and st.successes == []  # 抛之前没写半成品


# ─────────────────────────── _render_completeness_badge ───────────────────────────
@pytest.mark.parametrize("grade,tone", [
    ("优秀", "success"), ("良好", "warning"), ("及格", "warning"), ("不足", "danger"),
    ("满分", "neutral"), ("", "neutral"),
])
def test_badge_grade_maps_to_a_known_css_tone(monkeypatch, st, grade, tone):
    monkeypatch.setattr(lrp, "calculate_completeness",
                        lambda s: _result(grade, 72.4, [_sub("结构", 8, 10)]))
    lrp._render_completeness_badge({})

    html = "".join(st.markdowns)
    assert f"psy-score-badge--{tone}" in html
    assert "完成度 72/100" in html  # .0f 四舍五入，不显示小数
    assert f"<span>{grade}</span>" in html


def test_badge_failure_warns_once_and_still_skips_the_badge(monkeypatch, st):
    """s921-09 翻正（s920-13 遗留①预告的改法）：评分器抛异常 ⇒ 恰好一条 st.warning（带 exc 摘要），
    徽标依旧不渲染（原「静默隐身」红在此处按注释翻正）。errors 仍留空：只降级提示，不升级为报错。"""
    def boom(s):
        raise ValueError("评分器读不懂这份 state")

    monkeypatch.setattr(lrp, "calculate_completeness", boom)
    lrp._render_completeness_badge({})

    assert len(st.warnings) == 1 and "评分器读不懂这份 state" in st.warnings[0]
    assert st.markdowns == [] and st.expanders == [] and st.errors == []


def test_badge_detail_marks_are_scored_against_eighty_percent_of_weight(monkeypatch, st):
    subs = [_sub("已达标", 8, 10, "继续保持"), _sub("刚过线", 5, 10, ""),
            _sub("零分", 0, 10, "建议补方法部分")]
    monkeypatch.setattr(lrp, "calculate_completeness", lambda s: _result("良好", 60, subs))
    lrp._render_completeness_badge({})

    assert st.expanders == [("📈 完成度子项详情", {"expanded": False})]  # 子项默认折叠，不抢主视野
    body = "".join(st.markdowns)
    assert "✅ **已达标**：8/10" in body and "🟡 **刚过线**：5/10" in body and "⚪ **零分**：0/10" in body
    assert st.captions == ["   继续保持", "   建议补方法部分"]  # 无建议的子项不许冒出空行


def test_badge_is_rendered_in_the_narrow_right_column(monkeypatch, st):
    monkeypatch.setattr(lrp, "calculate_completeness", lambda s: _result("优秀", 90, []))
    lrp._render_completeness_badge({})

    assert st.columns_args == [[3, 1]] and st.expanders
    assert len(st.markdowns) == 1  # 只有徽标本身；子项循环没有内容


# ─────────────── 主入口 `:121-123` rescore 护栏（s927-29 B 案，§五 测试点 3） ───────────────

_MAIN_ENTRY_NOOPS = (
    "_render_header", "_render_completeness_badge", "_render_revise_research_q_button",
    "_render_drop_and_review_section", "_render_search_bar", "_render_literature_list",
    "_render_literature_detail", "_render_matrix_view", "_render_themes_tab",
    "_render_gaps_tab", "_render_export_tab", "_render_finish_tab",
)


class _MainEntrySt:
    """主入口最小假 st：session_state 用真 dict（有 `.get` 与下标赋值），只记 info/error。

    `columns`/`tabs`/`divider` 是主入口**内联**调用的布局口（不是可桩掉的 `_render_*` 助手），
    故必须给；其余未预期调用照样红。
    """

    def __init__(self, session):
        self.session_state = session
        self.errors, self.infos = [], []

    def error(self, msg, **k):
        self.errors.append(msg)

    def info(self, msg, **k):
        self.infos.append(msg)

    def divider(self, **k):
        pass

    def columns(self, spec=None, **k):
        return [_Ctx(self, f"col{i}") for i in range(len(spec or [1]))]

    def tabs(self, labels, **k):
        return [_Ctx(self, f"tab{i}") for i in range(len(labels))]

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


def _launch_main_entry(monkeypatch, session, lr_state, scorer):
    """只跑主入口「置位 → 重打分 → 物料化」这段，其余渲染口全桩掉（零 AppTest、零真实 session_state）。"""
    monkeypatch.setattr(lrp, "get_upstream_state", lambda ss: {"research_question": "新研究问题"})
    monkeypatch.setattr(lrp, "get_literature_review_state", lambda ss: lr_state)
    monkeypatch.setattr(lrp, "rescore_existing_items", scorer)
    for name in _MAIN_ENTRY_NOOPS:
        monkeypatch.setattr(lrp, name, lambda *a, **k: None)
    fake = _MainEntrySt(session)
    monkeypatch.setattr(lrp, "st", fake)
    return fake


def test_main_entry_rescore_failure_degrades_to_one_error_and_clears_flag(monkeypatch):
    """§五 测试点 3。改前必红：现状异常直穿主入口（整页红）且开关留 True ⇒ 每次 rerun 重烧打分器。

    判据三件：主入口**不抛**、`st.error` 恰好 1 次（带异常摘要）、`_lr_pending_rescore` **必为 False**。
    第三条是 `finally` 的证据 —— 只加 `try` 不加 `finally` 的半修写法在此必红；
    结构面另有 `tests/test_lr_dirty_number_frozen_pins.py` 的 AST 钉桩一起兜。
    零网络、零 LLM（打分器是桩）。
    """
    calls = []

    def boom(items, rq, vars_):
        calls.append(len(items))
        raise RuntimeError("打分器炸了（模拟 LLM/网络失败）")

    session = {"_lr_pending_rescore": True}
    lr_state = {"literature_items": [{"key": "a", "year": 2019}]}
    fake = _launch_main_entry(monkeypatch, session, lr_state, boom)

    lrp.render_literature_review(tier="beginner")  # 改前：RuntimeError 从这里逃逸 ⇒ 本行红

    assert len(calls) == 1, "打分器该被调到（失败发生在打分器内部，不是压根没调）"
    assert len(fake.errors) == 1 and "打分器炸了" in fake.errors[0]
    assert session["_lr_pending_rescore"] is False, "开关没落回 False ⇒ 会逐帧重烧 LLM"
    assert lr_state["literature_items"] == [{"key": "a", "year": 2019}]  # 失败不写半成品
