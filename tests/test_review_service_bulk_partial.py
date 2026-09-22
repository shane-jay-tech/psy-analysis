"""`src/literature_feed/review_service.py:103` 吞异常面钉桩（s922-135，s922-07 R2 的前置）。

## 为什么钉

``bulk_review_candidates``（:85-105）在逐条循环里写的是::

    except (ValueError, Exception) as e:          # :103
        logger.warning("bulk_review skip candidate %d: %s", cid, e)   # :104

``(ValueError, Exception)`` 里的 ``ValueError`` 是**装饰性冗余**（``ValueError`` 是
``Exception`` 的子类），真实语义是「吞掉一切非 BaseException」：写库失败、键冲突、
ZeroDivision、编码错误……统统降成一条 WARNING，函数照常返回一个 int。

于是 **R2 换路径（s922-07）时最容易被顺手改坏的两件事**：

1. 把「部分成功」悄悄改成「全成/全败」（例如中途 raise、或让一条失败就把 count 清零）；
2. 把吞掉的东西改成上抛，从而把已有调用方的行为整个换掉，而没有任何测试会红。

本件把这**三条语义**（部分成功返回值 / 异常不外逃只 WARNING / 审计表只为成功条目写）
锁死，并在每条测试的 docstring 里写明「改它必须是显式决策」。

**R2 采纳时须配「成功 x/N」回显**（N＝入参候选数，x＝返回的 count）——
本测试锁住部分成功语义不被静默改成全成/全败，但**不代替**那层回显；
若 R2 落地时只改了回显没改本函数，本件仍应全绿（回显在 UI 层）。

零 sqlite：全程内存假 store（``FakeStore``），并在关键用例里把
``sqlite3.connect`` 现场改成「一调就炸」，用来自证这条路径根本不碰库文件。
"""
from __future__ import annotations

import contextlib
import logging
import sqlite3

import pytest

from src.literature_feed import review_service as rs

# 三条候选；第 2 条在 UPDATE 时炸（任务书点名「第 2 条抛 RuntimeError」）
CIDS = [101, 102, 103]
POISONED = 102
BOOM = "database is locked"


class FakeStore:
    """内存假 store：只满足 ``review_candidate`` 用到的三件事——
    ``.connection.execute(sql, params)``、``.transaction()``、以及按 cid 查旧状态。

    记录三类调用，供断言「谁真落库了」：
      * ``selects``  —— 每条候选都会被 SELECT 一次旧状态（含失败那条）
      * ``updates``  —— 只成功条目走到 UPDATE
      * ``audit``    —— 只成功条目写 ``candidate_review_events``
    """

    def __init__(self, statuses=None, poison=(), exc_factory=lambda cid: RuntimeError(BOOM)):
        self.statuses = dict(statuses or {c: "pending" for c in CIDS})
        self.poison = set(poison)
        self.exc_factory = exc_factory
        self.selects: list[int] = []
        self.updates: list[int] = []
        self.audit: list[tuple] = []
        self.transactions = 0

    @property
    def connection(self):
        return _FakeConn(self)

    @contextlib.contextmanager
    def transaction(self):
        self.transactions += 1
        yield None


class _FakeConn:
    def __init__(self, store: FakeStore):
        self._s = store

    def execute(self, sql, params=()):
        head = " ".join(sql.split()).upper()
        if head.startswith("SELECT"):
            cid = params[0]
            self._s.selects.append(cid)
            return _Result(self._s.statuses.get(cid))
        if "UPDATE LLM_CANDIDATES" in head:
            cid = params[-1]                       # 末尾参数才是 candidate_id
            if cid in self._s.poison:
                raise self._s.exc_factory(cid)
            self._s.updates.append(cid)
            return _Result(None)
        if "INSERT INTO CANDIDATE_REVIEW_EVENTS" in head:
            self._s.audit.append(tuple(params))     # params[0] = candidate_id
            return _Result(None)
        raise AssertionError(f"FakeStore 收到预期外 SQL：{head[:60]}")


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        if self._row is None:
            return None
        return {"status": self._row}

    def fetchall(self):
        return []


def _bulk(store, cids=CIDS, decision="approved", **kw):
    return rs.bulk_review_candidates(store, cids, decision, "reviewer-x", **kw)


# ────────────────────────── 1. 部分成功语义 ──────────────────────────
def test_second_candidate_raising_yields_partial_count_two():
    """3 条候选、第 2 条抛 RuntimeError ⇒ 返回 **2**（部分成功），且**没有异常逃出来**。

    这条是 R2 的红线：既不许悄悄变成 0（一条失败就全败），也不许变成 3（把失败也算成功）。
    """
    store = FakeStore(poison={POISONED})

    with _no_sqlite_on_disk():
        count = _bulk(store)                        # 不 raise 本身就是断言

    assert count == 2
    assert store.updates == [101, 103]              # 失败那条从未 UPDATE
    assert store.selects == CIDS                    # 但三条都被尝试过


def test_count_never_exceeds_the_number_of_audit_rows_written():
    """count 与审计表条数**必须同数**：返回 2 就不能写 3 条事件（反之亦然）。"""
    store = FakeStore(poison={POISONED})

    count = _bulk(store)

    assert len(store.audit) == count == 2


# ────────────────────────── 2. 异常只降为 WARNING ──────────────────────────
def test_failure_surfaces_only_as_one_warning_on_the_module_logger(caplog):
    """失败只在 ``review_service`` 自己的 logger 上留 **一条** WARNING，级别不许是 error。

    钉住 :104 的文案骨架（``bulk_review skip candidate <cid>: <原因>``）——
    排查线上「批量审核少了两条」全靠这行，R2 改文案等于删掉可观测性。
    """
    store = FakeStore(poison={POISONED})

    with caplog.at_level(logging.WARNING, logger=rs.logger.name):
        _bulk(store)

    mine = [r for r in caplog.records if r.name == rs.logger.name]
    assert len(mine) == 1
    rec = mine[0]
    assert rec.levelno == logging.WARNING
    assert rec.msg == "bulk_review skip candidate %d: %s"       # 原文案一字不改
    # 注意：args 里存的是**异常对象本身**（`%s` 在 getMessage 时才格式化）——
    # 别把它误写成字符串元组，那会掩盖"%s 渲染异常"这一层事实。
    assert rec.args[0] == POISONED
    assert rec.getMessage() == f"bulk_review skip candidate {POISONED}: {BOOM}"
    assert rec.exc_info in (None, ())                          # 不上抛 ⇒ 不附 traceback


def test_no_log_record_when_everything_succeeds(caplog):
    """全成功的正常路径不许产生任何 WARNING（否则上一条测试就是假阳性）。"""
    store = FakeStore(poison=set())

    with caplog.at_level(logging.WARNING, logger=rs.logger.name):
        assert _bulk(store) == 3

    assert [r for r in caplog.records if r.name == rs.logger.name] == []
    assert store.audit and len(store.audit) == 3


# ────────────────────────── 3. 审计表只为成功条目写 ──────────────────────────
def test_audit_events_are_written_only_for_the_two_successes():
    """``candidate_review_events`` 的 INSERT 恰好 **2 次**，且 candidate_id 是 101／103。

    失败那条必须在审计表里**缺席**——R2 若改成「失败也记一笔 rejected 事件」，
    审核流水就会掺进没发生过的决策，这是比少记更糟的方向。
    """
    store = FakeStore(poison={POISONED})

    _bulk(store)

    assert len(store.audit) == 2
    assert [p[0] for p in store.audit] == [101, 103]
    assert {p[2] for p in store.audit} == {"approved"}          # new_status
    assert {p[1] for p in store.audit} == {"pending"}           # old_status 取自 SELECT


def test_all_three_failing_returns_zero_without_raising(caplog):
    """全失败也**静默返回 0**：这是 :103 吞异常面最极端的一格，同样要钉。

    调用方拿到 0 无法区分「一条都没提交」与「库里一条都没匹配上」——
    R2 的「成功 x/N 回显」就是为了补这一格；在补上之前本用例锁住现状不恶化。
    """
    store = FakeStore(poison=set(CIDS))

    with caplog.at_level(logging.WARNING, logger=rs.logger.name):
        count = _bulk(store)

    assert count == 0
    assert store.audit == [] and store.updates == []
    assert len([r for r in caplog.records if r.name == rs.logger.name]) == 3


# ────────────────────────── 4. 「吞一切」＝不只 ValueError ──────────────────────────
@pytest.mark.parametrize(
    "exc_type",
    [
        RuntimeError,          # :103 里 ValueError 之外的部分，证明它不是"只捕 ValueError"
        KeyError,
        sqlite3.OperationalError,
        ConnectionResetError,
        ZeroDivisionError,
        TypeError,
    ],
)
def test_the_except_clause_swallows_every_exception_type(exc_type):
    """任意 ``Exception`` 子类都被吞 ⇒ count 恒为 2、零异常外逃。

    只要有人把 :103 收窄成 ``except ValueError``（看着更"严谨"），本用例立刻红——
    这正是 s922-07 R2 需要知道的现状边界。
    """
    store = FakeStore(poison={POISONED}, exc_factory=lambda cid: exc_type("boom"))

    assert _bulk(store) == 2
    assert store.audit and len(store.audit) == 2


def test_baseexception_still_escapes():
    """``except Exception`` 不捕 ``BaseException``：``KeyboardInterrupt`` 必须上抛。

    钉住这条**唯一没被吞**的出口，免得 R2 有人顺手写成 ``except BaseException`` 把中断也吃掉。
    """
    store = FakeStore(poison={POISONED}, exc_factory=lambda cid: KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        _bulk(store)


def test_invalid_decision_is_swallowed_the_same_way(caplog):
    """``ValueError``（决策非法）与 RuntimeError 走的是同一个吞口 ⇒ 返回 0、只留 WARNING。

    说明 :103 的 ``ValueError`` 与 ``Exception`` 并列毫无区分度，纯冗余。
    """
    store = FakeStore(poison=set())

    with caplog.at_level(logging.WARNING, logger=rs.logger.name):
        count = _bulk(store, decision="ship_it")

    assert count == 0
    assert store.audit == []
    warns = [r for r in caplog.records if r.name == rs.logger.name]
    assert len(warns) == 3
    assert "Invalid decision" in warns[0].getMessage()


# ────────────────────────── 辅助 ──────────────────────────
@contextlib.contextmanager
def _no_sqlite_on_disk():
    """证明这条路径零 sqlite 落盘：期间任何 ``sqlite3.connect`` 一调就炸。"""
    real = sqlite3.connect

    def boom(*a, **k):  # pragma: no cover - 被调到即为失败
        raise AssertionError("bulk_review 路径不应打开 sqlite 连接（本用例要求零落盘）")

    sqlite3.connect = boom
    try:
        yield
    finally:
        sqlite3.connect = real


def test_zero_sqlite_on_disk_is_a_real_constraint():
    """显式复核上一条辅助器有效：真开一次 sqlite 就会被拦。

    （若 ``_no_sqlite_on_disk`` 写错成空操作，本用例先红，避免整件自证失效。）
    """
    with _no_sqlite_on_disk():
        with pytest.raises(AssertionError):
            sqlite3.connect(":memory:")
