"""``FeedStore.transaction()`` 的**真库**回滚／提交语义钉桩（s924-30）。

补的缺口来自 `zcode-bridge/done/s922-135-reviewservice-bulk-partial.result.md:58`：
「`store.transaction()` 的假替身只满足「可进可出」，没有模拟「事务内第二条 SQL 失败 ⇒
第一条 UPDATE 回滚」……R2 若要主张原子性，需另开单。」本件即那张"另开单"。

沙盒口径（仓内 `data/` 零写入）：`LITERATURE_FEED_DATA_ROOT` 指 `tmp_path` ＋
`FeedStore(显式库路径)`（在册形态见 tests/test_method_weights_io_seed.py 的 `feed_store` 夹具）。
隔离口径（同 s924-29 的教训）：`FeedStore` 一律在夹具期现取，不做模块期绑定 ——
`tests/` 现值仍有 8 件兄弟夹具会把 `src.literature_feed*` 整批驱逐出 `sys.modules`。
"""
from __future__ import annotations

import importlib
import sqlite3

import pytest

STORE_MODULE = "src.literature_feed.storage.feed_store"
SOURCE_ID = "s924_30_journal"
ORIG_NOTES = "改前原值"
ORIG_JOURNAL = "改前刊名"
MISSING_TABLE_SQL = "UPDATE __no_such_table_s924_30__ SET notes = 1"


def _feed_store_cls():
    """夹具期现取，避免模块期引用被兄弟夹具的 sys.modules 驱逐变成僵尸对象。"""
    return importlib.import_module(STORE_MODULE).FeedStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(tmp_path))
    db = tmp_path / "feed_s924_30.sqlite"
    s = _feed_store_cls()(db)
    assert s.db_path == db and db.parent == tmp_path, "库文件必须只在 pytest tmp 里"

    s.upsert_source(SOURCE_ID, journal_name=ORIG_JOURNAL,
                    fetcher_type="manual", notes=ORIG_NOTES)
    seeded = s.get_source(SOURCE_ID)
    assert seeded["notes"] == ORIG_NOTES and seeded["journal_name"] == ORIG_JOURNAL
    try:
        yield s
    finally:
        s.close()


def _notes(s):
    return s.get_source(SOURCE_ID)["notes"]


def _break_midway(s, first_notes: str):
    """事务内第一条 UPDATE 成功、第二条故意报错 ⇒ 让 transaction() 走 except 分支回滚。"""
    with pytest.raises(sqlite3.OperationalError):
        with s.transaction() as conn:
            conn.execute("UPDATE sources SET notes = ? WHERE source_id = ?",
                         (first_notes, SOURCE_ID))
            conn.execute(MISSING_TABLE_SQL)


def test_second_failing_sql_rolls_back_the_first_update(store):
    """【回滚态】事务内第二条 SQL 失败 ⇒ 第一条 UPDATE 不留下任何痕迹（读回＝改前原值）。"""
    _break_midway(store, "篡改值")

    assert _notes(store) == ORIG_NOTES, "回滚失效：第一条 UPDATE 漏到了库外"
    assert store.get_source(SOURCE_ID)["journal_name"] == ORIG_JOURNAL


def test_rolled_back_transaction_leaves_a_seeded_row_untouched(store):
    """【回滚态·连带面】回滚不能顺手把种下的行抹掉／改坏，也不能多写一行。"""
    before = store.get_source(SOURCE_ID)
    _break_midway(store, "又一条篡改值")
    after = store.get_source(SOURCE_ID)

    assert after == before, "回滚后整行不应当有任何字段漂移"
    assert len(store.list_sources()) == 1


def test_connection_is_still_writable_after_a_rollback(store):
    """【连接可用】回滚之后同一个连接必须能再开事务并提交。"""
    _break_midway(store, "篡改值")

    with store.transaction() as conn:
        conn.execute("UPDATE sources SET notes = ? WHERE source_id = ?",
                     ("回滚后可写", SOURCE_ID))

    assert _notes(store) == "回滚后可写"


def test_two_updates_in_one_transaction_commit_together(store, tmp_path):
    """【提交态】正常出块 ⇒ 两条 UPDATE 一起生效，且重开连接（真库落盘）仍读得到。"""
    with store.transaction() as conn:
        conn.execute("UPDATE sources SET notes = ? WHERE source_id = ?",
                     ("提交-1", SOURCE_ID))
        conn.execute("UPDATE sources SET journal_name = ? WHERE source_id = ?",
                     ("提交-2", SOURCE_ID))

    row = store.get_source(SOURCE_ID)
    assert row["notes"] == "提交-1" and row["journal_name"] == "提交-2"

    reopened = _feed_store_cls()(tmp_path / "feed_s924_30.sqlite", ensure=False)
    try:
        persisted = reopened.get_source(SOURCE_ID)
    finally:
        reopened.close()
    assert persisted["notes"] == "提交-1" and persisted["journal_name"] == "提交-2"


def test_control_the_same_update_outside_a_transaction_persists(store):
    """【判别力对照组，不是"绕过事务"的规范背书】同一条 UPDATE 不经 `transaction()` 会落地。

    目的：证明回滚例的红绿**来自事务边界**，而不是"这条 UPDATE 本来就不生效"或
    "fixture 种的数据是假的"。`FeedStore` 的连接构造时是 `isolation_level=None`
    （构造函数注"我们手动管理事务"）⇒ autocommit 是 sqlite 既有语义，本例只登记它当对照，
    不代表"写操作可以不走事务"（模块 docstring 的规范仍是所有写走显式事务）。
    真判别力变异（删 `feed_store.transaction()` 的 rollback 分支）属临时改生产码，
    按纪律档 §十三.7 未做，已列进 result 遗留问题交主班裁。
    """
    store.connection.execute("UPDATE sources SET notes = ? WHERE source_id = ?",
                             ("无事务直写", SOURCE_ID))

    assert _notes(store) == "无事务直写"


def test_uncommitted_update_is_invisible_to_a_second_connection(store, tmp_path):
    """【真事务，不是"看着像"】未提交期间第二条连接读到的仍是原值；提交后才可见。

    `transaction()` 的 docstring 主张 BEGIN IMMEDIATE ⇒ 这条钉住"它确实是事务边界"，
    而不是只满足 s922-135 说的"可进可出"。
    """
    other = sqlite3.connect(str(tmp_path / "feed_s924_30.sqlite"),
                            timeout=5, isolation_level=None)
    try:
        with store.transaction() as conn:
            conn.execute("UPDATE sources SET notes = ? WHERE source_id = ?",
                         ("事务内未提交", SOURCE_ID))
            assert _notes(store) == "事务内未提交"          # 同连接：未提交即可见
            assert other.execute(
                "SELECT notes FROM sources WHERE source_id = ?", (SOURCE_ID,)
            ).fetchone()[0] == ORIG_NOTES                   # 第二连接：读不到
    finally:
        other.close()

    after = sqlite3.connect(str(tmp_path / "feed_s924_30.sqlite"),
                            timeout=5, isolation_level=None)
    try:
        assert after.execute(
            "SELECT notes FROM sources WHERE source_id = ?", (SOURCE_ID,)
        ).fetchone()[0] == "事务内未提交"                    # 出块即提交
    finally:
        after.close()
