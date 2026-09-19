"""src/ui/literature_review_queue_panel.py 纯逻辑分支特征化测试（s918-26）。

只打 `_load_candidates` / `_render_filters` / `_do_review` 三个非浏览器单元：
fake store ＋假 st（monkeypatch，用例结束自动还原），不落任何真实库文件。
重点钉「幻觉不入库」的前端闸门：validate 不过时**绝不能触达 review_candidate**。
不测浏览器行为，不判文献内容对错。
"""
import pytest

import src.ui.literature_review_queue_panel as pnl
from src.literature_feed.review_queue_ui import QueueItem


class RerunRequested(BaseException):
    """与真实 Streamlit 同基类：`ScriptControlException` 故意继承 BaseException
    （见 streamlit/runtime/scriptrunner_utils/exceptions.py 注释），
    才不会被 `_do_review` 的 `except Exception` 吞掉。测试替身若继承 Exception 会误判。"""


class _Col:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeStreamlit:
    def __init__(self, answers=None, slider_value=0.0):
        self.answers = answers or {}
        self.slider_value = slider_value
        self.errors = []
        self.successes = []
        self.seen_options = {}
        self.reruns = 0

    def columns(self, n):
        return [_Col() for _ in range(n)]

    def selectbox(self, label, options=None, key=None, **kw):
        self.seen_options[key or label] = list(options)
        return self.answers.get(key or label, options[0])

    def slider(self, label, *args, key=None, **kw):
        return self.slider_value

    def rerun(self):
        self.reruns += 1
        raise RerunRequested()

    def error(self, msg):
        self.errors.append(msg)

    def success(self, msg):
        self.successes.append(msg)

    def __getattr__(self, name):
        return lambda *a, **k: None


class FakeStore:
    """只提供 .connection.execute(...).fetchall()，不碰 sqlite。"""

    def __init__(self, rows):
        self.rows = rows
        self.sql = []

    @property
    def connection(self):
        outer = self

        class _Conn:
            def execute(self, sql):
                outer.sql.append(sql)

                class _Res:
                    def fetchall(self):
                        return outer.rows

                return _Res()

        return _Conn()


def _item(cid, status="pending", source="arxiv", rel=0.5):
    return QueueItem(candidate_id=cid, title=f"T{cid}", source=source,
                     status=status, relevance_score=rel)


@pytest.fixture(autouse=True)
def fake_st(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(pnl, "st", fake)
    return fake


@pytest.fixture
def svc(monkeypatch):
    """拦下真正的入库调用，改成记录器；默认成功。"""
    calls = []

    def ok(store, cid, decision, reviewer, **kw):
        calls.append((cid, decision, reviewer, kw))

    monkeypatch.setattr(pnl, "review_candidate", ok)
    return calls


def test_load_candidates_queries_newest_first_and_returns_dicts():
    store = FakeStore([{"candidate_id": 7, "title": "A"}, {"candidate_id": 3, "title": "B"}])

    rows = pnl._load_candidates(store)

    assert store.sql == ["SELECT * FROM llm_candidates ORDER BY candidate_id DESC"]
    assert rows == [{"candidate_id": 7, "title": "A"}, {"candidate_id": 3, "title": "B"}]


def test_load_candidates_on_empty_table_returns_empty_list():
    assert pnl._load_candidates(FakeStore([])) == []


def test_filters_return_everything_when_both_selectboxes_say_all(fake_st):
    items = [_item(1, "pending", "arxiv"), _item(2, "approved", "pubmed")]

    assert pnl._render_filters(items) == items
    assert fake_st.seen_options["rq_status_filter"][0] == "全部"
    assert fake_st.seen_options["rq_source_filter"] == ["全部", "arxiv", "pubmed"]


def test_source_options_are_sorted_and_deduplicated(fake_st):
    items = [_item(1, source="zlib"), _item(2, source="arxiv"), _item(3, source="zlib")]

    pnl._render_filters(items)

    assert fake_st.seen_options["rq_source_filter"] == ["全部", "arxiv", "zlib"]


def test_status_and_relevance_filters_narrow_the_list(monkeypatch, fake_st):
    monkeypatch.setattr(pnl, "st", FakeStreamlit(answers={"rq_status_filter": "pending"}, slider_value=0.6))
    items = [_item(1, "pending", rel=0.8), _item(2, "approved", rel=0.9), _item(3, "pending", rel=0.2)]

    kept = pnl._render_filters(items)

    assert [i.candidate_id for i in kept] == [1]


def test_rejected_without_reason_never_reaches_the_service(fake_st, svc):
    pnl._do_review(FakeStore([]), 11, "rejected")

    assert svc == []
    assert fake_st.errors == ["排除操作必须选择原因"]
    assert fake_st.reruns == 0


def test_merged_without_target_never_reaches_the_service(fake_st, svc):
    pnl._do_review(FakeStore([]), 12, "merged")

    assert svc == []
    assert fake_st.errors == ["合并操作必须选择目标文献"]


def test_unknown_decision_is_rejected_with_the_decision_echoed(fake_st, svc):
    pnl._do_review(FakeStore([]), 13, "ship_it")

    assert svc == []
    assert fake_st.errors == ["无效的审核决策: ship_it"]


def test_approve_writes_with_reviewer_user_then_reruns(fake_st, svc):
    with pytest.raises(RerunRequested):
        pnl._do_review(FakeStore([]), 14, "approved")

    assert svc == [(14, "approved", "user", {"rejection_reason": None, "target_kb_id": None})]
    assert fake_st.successes == ["已纳入"]


@pytest.mark.parametrize(
    "decision,expected",
    [
        ("approved", "已纳入"),
        ("rejected", "已排除"),
        ("merged", "已合并"),
        ("deferred", "待定"),          # 标签本就不带「已」：旧代码给它加前缀成"已待定"，同一种错
    ],
)
def test_success_text_is_the_label_verbatim(fake_st, svc, decision, expected):
    """`STATUS_LABELS` 的值自带「已」，f-string 前缀再加一层就成了「已已纳入」（s918-26 遗留段）。

    四个合法决策（`ReviewAction.validate` 的白名单）全过一遍——上游只举了"已纳入"一例。
    """
    kwargs = {"rejected": {"rejection_reason": "duplicate"},
              "merged": {"target_kb_id": "kb-7"}}.get(decision, {})
    with pytest.raises(RerunRequested):
        pnl._do_review(FakeStore([]), 21, decision, **kwargs)

    assert fake_st.successes == [expected]
    assert "已已" not in fake_st.successes[0]


def test_reject_passes_reason_through(svc):
    with pytest.raises(RerunRequested):
        pnl._do_review(FakeStore([]), 15, "rejected", rejection_reason="duplicate")

    assert svc[0][1] == "rejected"
    assert svc[0][3]["rejection_reason"] == "duplicate"


def test_service_failure_becomes_an_error_and_does_not_rerun(monkeypatch, fake_st):
    def boom(*a, **k):
        raise RuntimeError("db locked")

    monkeypatch.setattr(pnl, "review_candidate", boom)

    pnl._do_review(FakeStore([]), 16, "approved")

    assert fake_st.errors == ["审核失败: db locked"]
    assert fake_st.successes == []
    assert fake_st.reruns == 0


# ───────────── s920-04：四种决策的成功文案分型（只改回显，落库参数一字未动） ─────────────
def _ok_review(fake_st, svc, decision, **kw):
    fake_st.successes.clear()                              # 每次只看这一条回显
    with pytest.raises(RerunRequested):
        pnl._do_review(FakeStore([]), 21, decision, **kw)
    assert len(fake_st.successes) == 1
    return fake_st.successes[0]


def test_each_decision_gets_its_own_sentence_naming_the_object(fake_st, svc):
    msgs = {
        "approved": _ok_review(fake_st, svc, "approved", title="工作压力与绩效"),
        "deferred": _ok_review(fake_st, svc, "deferred", title="工作压力与绩效"),
        "rejected": _ok_review(fake_st, svc, "rejected", title="工作压力与绩效",
                              rejection_reason="weak_evidence"),
        "merged": _ok_review(fake_st, svc, "merged", title="工作压力与绩效", target_kb_id="kb-7"),
    }

    assert len(set(msgs.values())) == 4                        # 四句彼此不同
    assert all("工作压力与绩效" in m for m in msgs.values())    # 每条都说得出动了哪篇
    assert msgs["approved"] == "已纳入《工作压力与绩效》"
    assert msgs["deferred"] == "已标记《工作压力与绩效》为待定"
    assert msgs["rejected"].startswith("已排除《工作压力与绩效》")
    assert msgs["rejected"] == "已排除《工作压力与绩效》（原因：证据薄弱）"   # 回显中文标签，不是内部键
    assert msgs["merged"].endswith("→ 目标 kb-7")


def test_missing_title_falls_back_to_the_bare_status_label(fake_st, svc):
    for title in (None, "", "   "):
        fake_st.successes.clear()
        svc.clear()
        assert _ok_review(fake_st, svc, "approved", title=title) == "已纳入"   # 绝不渲染空的《》


def test_the_new_copy_argument_never_reaches_the_persistence_layer(fake_st, svc):
    with pytest.raises(RerunRequested):
        pnl._do_review(FakeStore([]), 31, "merged", title="只给我看", target_kb_id="kb-9")

    cid, decision, reviewer, kw = svc[-1]
    assert (cid, decision, reviewer) == (31, "merged", "user")
    assert kw == {"rejection_reason": None, "target_kb_id": "kb-9"}   # 落库参数与改前完全同形
    assert "title" not in kw and "只给我看" not in repr(svc)


def test_validation_gate_still_runs_before_any_copy(fake_st, svc):
    """文案分型不许把校验挤后：validate 不过 ⇒ 零入库、零 success。"""
    pnl._do_review(FakeStore([]), 41, "merged", title="有标题也不给过")

    assert svc == [] and fake_st.successes == []
    assert fake_st.errors == ["合并操作必须选择目标文献"]


def test_unknown_decision_still_echoes_instead_of_inventing_a_sentence(fake_st, svc):
    from src.literature_feed.review_queue_ui import review_success_message

    assert review_success_message("ship_it", title="X") == "ship_it"
    assert review_success_message("ship_it") == "ship_it"
