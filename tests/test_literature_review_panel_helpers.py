# -*- coding: utf-8 -*-
"""src/ui/literature_review_panel.py 三个助手钉桩（s920-13）。

锚点（实测仍成立）：`:198 _do_relevance_rescore(upstream, lr_state)`、`:222 _render_completeness_badge(lr_state)`、
`:754 _materialize_items(items_dict_list)` —— 三者此前在 `tests/` 里**零命中**，唯一调用方是同文件主入口
`render_literature_review`（:109 / :122 / :126）。渲染主干一行不碰。

`rescore_existing_items` / `calculate_completeness` 是模块级 `from ... import` ⇒ 打在 `lrp` 属性上。
假 `st` 对未预期调用当场 assert 红。零网络、零 LLM、零真实 session_state。
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


def test_materialize_coerces_numeric_strings_but_not_garbage():
    (it,) = lrp._materialize_items([{"year": "2019", "citation_count": "12", "relevance_score": "0.75"}])
    assert (it.year, it.citation_count, it.relevance_score) == (2019, 12, 0.75)

    with pytest.raises(ValueError):  # 现状：脏数字直接抛出，整页起不来（只钉不改）
        lrp._materialize_items([{"year": "约 2019"}])


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
