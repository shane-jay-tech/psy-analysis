# -*- coding: utf-8 -*-
"""s922-107：feed「一键批准高置信」**直接写库现状**钉桩（s922-07 冻结项，R1/R2 未放行）。

⚠️ 本档钉的是「现状」，不是「应有形态」。s922-07 §3 的两段式改造（R1 加确认帧 / R2 收敛到
`review_service.bulk_review_candidates`）一旦放行落地，本档用例会**主动转红**——那是设计内的
翻正信号，届时请改断言而不是删用例。每条 docstring 标了对应的 s922-07 §2 风险编号。

锚点复核（2026-09-22 本班按磁盘实况，HEAD `9551e1d`，**三处零漂移**）：
- `src/literature_feed/ui/feed_panel.py:177` `pending = store.list_candidates(status="pending", limit=20)`
- `:182` `high_conf = [c for c in pending if (c.get("confidence") or 0) >= 0.8]`
- `:187-197` 批准分支（按钮 → for 循环 → `update_candidate_status` → toast → rerun，**中间无确认帧、无 try**）
- `src/literature_feed/storage/feed_store.py:551-569` `update_candidate_status`：单事务、五字段**无条件 SET**

harness 口径：`FakeSt` / `FakeStore` / `_daily_state` **直接 import 自
`tests.test_feed_panel_charac`**（s920-14 建的假 st 跨帧夹具，s921-11 已在用），本班只在
`SliceStore` 里补两件事：① `list_candidates` 复刻真 SQL 的 `ORDER BY priority_score DESC,
candidate_id DESC LIMIT ?`（父类忽略 limit，用它钉不出「>20 静默漏批」）；② 记录关键字调用形态与
可注入的失败点。**零 sqlite 文件、零网络、零 LLM、零子进程、零写盘。**

按钮文案里的 emoji 不硬编码：先零点击渲染一遍、从 `st.buttons` 真实清单里取整串，
避免本档写死 surrogate 字符（工具链丢字符前科）。
"""
from __future__ import annotations

import pytest

from tests.test_feed_panel_charac import FakeStore, _daily_state

# 生产口径常量（钉的是现状；实现改动会让下面的用例红，而不是这里跟着改）
SLICE_LIMIT = 20
CONF_MIN = 0.8
BATCH_REVIEWER = "batch_high_conf"
APPROVE_LABEL_HINT = "一键批准高置信"
REJECT_LABEL_HINT = "全部拒绝"


class SliceStore(FakeStore):
    """内存假 store：带真 SQL 切片语义 + 调用形态留痕 + 可注入失败点。

    `raise_on_cid` 用于 s922-07 §2 风险 2（循环无 try）：第 k 条抛异常，看前 k-1 条是否已提交。
    """

    def __init__(self, candidates=(), *, raise_on_cid=None, **kw):
        super().__init__(candidates=list(candidates), **kw)
        self.list_calls: list[tuple[str, int]] = []
        self.writes: list[tuple[int, dict]] = []  # (candidate_id, 关键字参数原文)
        self.raise_on_cid = raise_on_cid

    def list_candidates(self, status="pending", limit=20):
        self.list_calls.append((status, limit))
        rows = [c for c in self.candidates if c.get("status", "pending") == status]
        # 逐字对照 feed_store.py:583 的 ORDER BY priority_score DESC, candidate_id DESC LIMIT ?
        rows.sort(key=lambda c: (-(c.get("priority_score") or 0), -int(c["candidate_id"])))
        return [dict(c) for c in rows[:limit]]

    def update_candidate_status(self, cid, **kw):
        if self.raise_on_cid is not None and cid == self.raise_on_cid:
            raise RuntimeError("模拟第 k 条写库炸（如 status CHECK 约束/连接中断）")
        self.writes.append((cid, dict(kw)))
        super().update_candidate_status(cid, **kw)

    def reset_records(self):
        """清累计读数。`_click_batch_approve` 要先零点击探一次文案，
        不清就会把两帧的 list_calls 混进断言（探帧本身零写，故写口不受影响）。
        """
        self.list_calls.clear()
        self.writes.clear()
        self.status_writes.clear()


def _cand(cid, conf, priority, **extra):
    row = {
        "candidate_id": cid,
        "kind": "construct",
        "name": f"候选{cid}",
        "confidence": conf,
        "priority_score": priority,
        "definition": "",
        "evidence_quote": "",
        "iohr_hits_json": "[]",
    }
    row.update(extra)
    return row


def _render(store, *, state=None, clicked=(), monkeypatch=None):
    return _daily_state(store, dict(state or {}), clicked=tuple(clicked), monkeypatch=monkeypatch)


def _label_of(st, hint):
    """从真实渲染出的按钮清单里取含 hint 的整串文案；取不到即 AssertionError。"""
    hits = [lbl for lbl, _kw in st.buttons if hint in lbl]
    assert hits, f"页面没有含 {hint!r} 的按钮：{[b[0] for b in st.buttons]}"
    assert len(hits) == 1, f"{hint!r} 命中多个按钮，钉桩对象不唯一：{hits}"
    return hits[0]


def _click_batch_approve(store, monkeypatch, *, state=None):
    """两帧法：先零点击渲染探出批准键完整文案，清掉探帧读数，再以「本帧点了它」渲染。

    返回值里的 writes / list_calls 因此**只含点击帧**，断言不会被两次渲染污染。
    """
    probe = _render(store, monkeypatch=monkeypatch)
    label = _label_of(probe, APPROVE_LABEL_HINT)
    store.reset_records()
    return label, _render(store, state=state, clicked={label}, monkeypatch=monkeypatch)


# ───────────────────────── 现状形态判据（与 s922-104 的 _pinned_paths 同构） ─────────────────────────
def _pinned_approve_form(writes, st) -> list[str]:
    """四条「直接写库」形态判据收进一处：现状返回空列表，漂向 R1/R2 形态即返回偏离原因。

    正向用例断言它 == []；反向用例拿同页面**真实存在的**两段式拒绝分支喂它，断言必报红 ——
    以此证明判据不是恒真（假绿鉴别法，照 s922-104 的两条 monkeypatch 反向用例的路子）。
    """
    fails: list[str] = []

    if not writes:
        fails.append("点击批量批准后本帧没有任何 update_candidate_status 调用：确认帧出现了（R1 形态）")
    armed = {k for k in st.session_state if "confirm" in k.lower() or "_approv" in k.lower()}
    if armed:
        fails.append(f"批准路径不该置任何确认态键，实测置了：{sorted(armed)}")
    for _cid, kw in writes:
        if set(kw) != {"status", "reviewer"}:
            fails.append(f"写库关键字形态偏离现状（期望 status+reviewer）：{sorted(kw)}")
        if kw.get("status") != "approved":
            fails.append(f"status 不是 approved：{kw.get('status')!r}")
        if kw.get("reviewer") != BATCH_REVIEWER:
            fails.append(f"reviewer 不是 {BATCH_REVIEWER!r}：{kw.get('reviewer')!r}")
    return fails


# ─────────────────────────────── 钉桩用例 ───────────────────────────────
def test_single_click_writes_in_same_frame_no_confirmation_gate(monkeypatch):
    """s922-07 §2 风险 1 + 风险 4a：一次点击即逐条写库，没有拒绝路径那样的确认帧。

    现状钉桩（R1 放行后翻正）。对照面：同 tab 的批量**拒绝**要两帧（首击只置
    `_confirm_batch_reject` + rerun、零写），而**批准**首击就落库——风险方向相反的两者防护倒挂。
    """
    store = SliceStore([_cand(1, 0.91, 5.0), _cand(2, 0.80, 4.0), _cand(3, 0.30, 3.0)])
    label, st = _click_batch_approve(store, monkeypatch)

    assert [cid for cid, _kw in store.writes] == [1, 2]  # 低置信的第 3 条不进批
    assert st.reruns == 1 and any("已批准 2 条高置信度候选" in t for t in st.toasts)
    assert _pinned_approve_form(store.writes, st) == []
    assert st.session_state.get("_confirm_batch_approve") is None  # R1 的键名现在不存在
    # 文案里的 (N) 就是本帧真正会落库的条数，用户点下去前没有任何二次确认机会
    assert f"({len(store.writes)})" in label


def test_write_call_is_keyword_only_status_and_reviewer_literal(monkeypatch):
    """s922-07 §2 风险 1 + 风险 3：reviewer 固定 `batch_high_conf`，且只写 llm_candidates 一张表。

    现状钉桩。`feed_store.py:551-559` 的 status/reviewer 是 keyword-only（`*,` 之后），
    位置传参会 TypeError —— 这里把调用形态一起钉住，防止改造时悄悄换成位置参数量。
    审计面（风险 3）：`candidate_review_events` 在本路径**零留痕**，见同档 test_review_event_table_untouched。
    """
    store = SliceStore([_cand(7, 0.95, 1.0)])
    _label, st = _click_batch_approve(store, monkeypatch)

    assert store.writes == [(7, {"status": "approved", "reviewer": BATCH_REVIEWER})]
    assert st.errors == []  # 成功路径不产错误声音


def test_review_event_audit_table_gets_no_row_from_batch_approve(monkeypatch):
    """s922-07 §2 风险 3：批量批准只动 `llm_candidates`，审计事件表零调用。

    现状钉桩（R2 落地后本用例应翻正——`review_service.bulk_review_candidates` 带审计写入）。
    判据取「假 store 只实现了 update_candidate_status 一个写口」这一事实：`FakeSt.__getattr__`
    对未预期 st.* 当场 assert 红，故本帧能跑完即证明面板没经过任何额外审计/事件通道。
    """
    store = SliceStore([_cand(11, 0.9, 2.0)])
    _label, _st = _click_batch_approve(store, monkeypatch)

    assert len(store.status_writes) == 1  # 父类记录口：唯一一次写
    assert store.closed == 0  # 本函数不负责关连接（关由入口 render_literature_feed 的 finally 兜）


def test_high_confidence_predicate_uses_raw_value_while_card_badge_uses_rounded(monkeypatch):
    """s922-07 §2 风险 4b（同族新证据）：0.799 的卡片亮「高置信」徽章，但**不在**批量批准名单里。

    现状钉桩。`feed_panel.py:182` 用 `(confidence or 0) >= 0.8` 原值判，
    而 `:227/:249` 卡片徽章用 `round(confidence or 0, 2) >= 0.8` —— 两套谓词。
    用户看到的是「高置信」绿标，点一键批准却不会批它（实测 round(0.799, 2) == 0.8）。
    """
    assert round(0.799, 2) == CONF_MIN  # 前提自证：徽章谓词确实会把它抬到线上
    store = SliceStore([_cand(21, 0.799, 9.0), _cand(22, 0.8, 8.0), _cand(23, 0.795, 7.0)])
    label, _st = _click_batch_approve(store, monkeypatch)

    assert [cid for cid, _k in store.writes] == [22]  # 0.799 / 0.795 都不批
    assert "(1)" in label  # 按钮计数也只算 1 条，与徽章数不一致


def test_only_first_20_slice_is_approved_rest_silently_skipped(monkeypatch):
    """s922-07 §2 风险 4b：23 条 pending 全高置信，只有切片内前 20 条被批，后 3 条**静默**漏批。

    现状钉桩（R1 的「实际待审共 M 条」文案会一并修掉这条）。
    切片顺序 = 真 SQL 的 `priority_score DESC, candidate_id DESC`，不是插入顺序。
    caption 明写「显示前 20」，但按钮文案是「一键批准高置信 (20)」——文案说全部、作用域是切片。
    """
    rows = [_cand(cid, 0.9, float(cid)) for cid in range(1, 24)]  # 23 条，全是高置信
    store = SliceStore(rows)
    label, st = _click_batch_approve(store, monkeypatch)

    assert store.list_calls == [("pending", SLICE_LIMIT)]  # 面板确实按 limit=20 取数
    assert len(store.writes) == SLICE_LIMIT, f"批准数应等于切片大小，实测 {len(store.writes)}"
    approved = {cid for cid, _k in store.writes}
    assert approved == set(range(4, 24))  # 优先级最高 20 条（cid 23..4）
    assert approved != set(range(1, 24))  # cid 1/2/3 静默停在 pending
    assert f"({SLICE_LIMIT})" in label
    joined = "".join(st.captions)
    assert "共 23 条待审" in joined and "显示前 20" in joined  # 只有 caption 交代了真相


def test_kth_failure_leaves_prefix_already_committed(monkeypatch):
    """s922-07 §2 风险 2：for 循环无 try —— 第 k 条抛异常时前 k-1 条**已各自提交**，不可回滚。

    现状钉桩（R2 收敛到 `bulk_review_candidates` 后应翻正）。
    真 store 的 `update_candidate_status` 每条各开一个 `transaction()`（feed_store.py:560），
    故「半批态」不是推演：异常外抛、页面整页红、toast/rerun 都不执行、剩余条停在 pending。
    """
    rows = [_cand(31, 0.9, 3.0), _cand(32, 0.9, 2.0), _cand(33, 0.9, 1.0)]
    store = SliceStore(rows, raise_on_cid=32)

    with pytest.raises(RuntimeError):
        _click_batch_approve(store, monkeypatch)

    assert [cid for cid, _k in store.writes] == [31]  # 第 1 条已提交，第 3 条没机会


def test_no_approve_button_at_all_when_slice_has_no_high_confidence(monkeypatch):
    """s922-07 §2 风险 4b：`if high_conf and st.button(...)` —— 切片内零高置信时按钮**不渲染**，
    此时页面仍显示「共 N 条待审」，用户看不出被裁掉的到底是哪些。现状钉桩。
    """
    rows = [_cand(cid, 0.2, float(cid)) for cid in range(1, 24)]
    store = SliceStore(rows)
    st = _render(store, monkeypatch=monkeypatch)

    assert [b[0] for b in st.buttons] and not any(APPROVE_LABEL_HINT in b[0] for b in st.buttons)
    assert store.writes == [] and st.reruns == 0


# ───────────────────────────── 鉴别力反向用例 ─────────────────────────────
def test_form_predicate_rejects_the_two_stage_reject_branch(monkeypatch):
    """反向用例：把同页面**真实的**两段式拒绝首击帧喂给形态判据，它必须报红。

    这一条不测生产码，测的是本班判据有没有鉴别力 —— 若 `_pinned_approve_form` 恒真，
    「批准无确认帧」就是假绿断言。拒绝首击（`feed_panel.py:216-219`）置确认态、零写，正是 R1 形态。
    """
    store = SliceStore([_cand(41, 0.9, 1.0), _cand(42, 0.9, 2.0)])
    probe = _render(store, monkeypatch=monkeypatch)
    reject_label = _label_of(probe, REJECT_LABEL_HINT)
    st = _render(store, clicked={reject_label}, monkeypatch=monkeypatch)

    assert store.writes == []  # 前提自证：拒绝首击确实不落库
    assert st.session_state["_confirm_batch_reject"] is True
    failures = _pinned_approve_form(store.writes, st)
    assert failures, "判据失鉴别力：两段式确认帧居然不报红"
    assert any("确认帧" in r for r in failures)
    assert any("确认态键" in r for r in failures)


def test_slice_pin_disappears_when_store_ignores_limit(monkeypatch):
    """反向用例二：同一批 23 条数据，换回父类 `FakeStore`（它忽略 limit）就会批掉 23 条。

    证明「只批 20 条」的读数来自本班真的复刻了 SQL 切片，而不是假 store 恰好少给数据。
    """
    rows = [_cand(cid, 0.9, float(cid)) for cid in range(1, 24)]
    naive = FakeStore(candidates=rows)  # 父类：list_candidates 无视 limit，全量返回
    st_probe = _render(naive, monkeypatch=monkeypatch)
    label = _label_of(st_probe, APPROVE_LABEL_HINT)
    _render(naive, clicked={label}, monkeypatch=monkeypatch)

    assert len(naive.status_writes) == 23  # 无切片 ⇒ 无漏批，本班漏批断言因此非恒真


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
