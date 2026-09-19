"""scripts/seed_literature_sources.py 入库契约钉桩测试（s918-54）。

库走 `tmp_path` 的真 FeedStore（**autouse 挡掉 `ensure_dirs()`**，否则会在真实 data 目录下建库），
网络侧 `build_fetcher` 一律打桩 ⇒ **零联网、零真实库**。
锚点：:57 `def seed(store: FeedStore) -> None:`、:95 `def main(argv=None) -> int:`（112 行）。
"""
import pytest

import src.literature_feed.storage.feed_store as fs_mod
from scripts import seed_literature_sources as sls


@pytest.fixture(autouse=True)
def no_prod_dirs(monkeypatch):
    monkeypatch.setattr(fs_mod, "ensure_dirs", lambda: None)


@pytest.fixture
def store(tmp_path):
    st = fs_mod.FeedStore(tmp_path / "feed.sqlite")
    yield st
    st.close()


def _disable(store, source_id="jap"):
    store._conn.execute("UPDATE sources SET enabled = 0 WHERE source_id = ?", (source_id,))
    store._conn.commit()


def _note(store, source_id, text):
    store._conn.execute("UPDATE sources SET notes = ? WHERE source_id = ?", (text, source_id))
    store._conn.commit()


def test_seed_is_idempotent_in_row_count(store):
    sls.seed(store)
    first = store.list_sources()
    sls.seed(store)
    second = store.list_sources()

    assert len(first) == len(second) == len(sls.SOURCES) == 8
    assert [r["source_id"] for r in second] == sorted(s["source_id"] for s in sls.SOURCES)


def test_seed_carries_curated_fields_and_enables_every_source(store):
    sls.seed(store)
    rows = {r["source_id"]: r for r in store.list_sources()}

    acta = rows["acta_psych_sinica"]
    assert acta["issn"] == "0439-755X" and acta["doi_prefix"] == "10.3724"
    assert acta["fetcher_type"] == "crossref"
    assert rows["jap"]["issn"] == "0021-9010" and rows["jap"]["doi_prefix"] is None
    assert all(r["enabled"] for r in rows.values())


def test_reseed_reenables_a_source_the_operator_disabled(store):
    """upsert 的 DO UPDATE 含 enabled ⇒ 重复 seed 会把人工停用的源**重新打开**。"""
    sls.seed(store)
    _disable(store, "jap")
    assert [r for r in store.list_sources(enabled_only=True) if r["source_id"] == "jap"] == []

    sls.seed(store)

    assert any(r["source_id"] == "jap" for r in store.list_sources(enabled_only=True))


def test_reseed_clears_operator_notes_to_null(store):
    """同一个 DO UPDATE 里带 notes=excluded.notes，而 seed 不传 notes（默认 None）
    ⇒ 重跑 seed 会**抹掉人工写在 sources.notes 上的备注**。"""
    sls.seed(store)
    _note(store, "jap", "ISSN 已核实为电子版")

    sls.seed(store)

    assert {r["source_id"]: r["notes"] for r in store.list_sources()}["jap"] is None


def test_enabled_is_stored_as_int_so_list_current_prints_1(store, capsys):
    sls.seed(store)

    sls.list_current(store)

    out = capsys.readouterr().out
    assert f"sources 表现有 {len(sls.SOURCES)} 行" in out
    assert "enabled=True" not in out            # sqlite 存 int，回读是 1/0 不是 True/False
    assert "enabled=1" in out


def test_probe_reports_failure_per_source_without_raising(store, monkeypatch, capsys):
    sls.seed(store)

    def boom(row):
        raise RuntimeError("crossref 503")

    import src.literature_feed.scheduler.daily_runner as dr
    monkeypatch.setattr(dr, "build_fetcher", boom)

    sls.probe(store)                                   # 不抛

    out = capsys.readouterr().out
    assert out.count("[失败]") == len(sls.SOURCES)
    assert "crossref 503" in out
    assert "RuntimeError" in out


def test_main_without_probe_seeds_lists_and_closes(monkeypatch):
    closed = []

    class FakeStore:
        def list_sources(self, *, enabled_only=False):
            return []

        def close(self):
            closed.append(1)

    calls = []
    monkeypatch.setattr(sls, "FeedStore", lambda: FakeStore())
    monkeypatch.setattr(sls, "seed", lambda st: calls.append("seed"))
    monkeypatch.setattr(sls, "list_current", lambda st: calls.append("list"))
    monkeypatch.setattr(sls, "probe", lambda st: calls.append("probe"))

    assert sls.main([]) == 0
    assert calls == ["seed", "list"] and closed == [1]


def test_main_with_probe_flag_runs_probe_after_seeding(monkeypatch):
    class FakeStore:
        def list_sources(self, *, enabled_only=False):
            return []

        def close(self):
            pass

    calls = []
    monkeypatch.setattr(sls, "FeedStore", lambda: FakeStore())
    monkeypatch.setattr(sls, "seed", lambda st: calls.append("seed"))
    monkeypatch.setattr(sls, "list_current", lambda st: calls.append("list"))
    monkeypatch.setattr(sls, "probe", lambda st: calls.append("probe"))

    assert sls.main(["--probe"]) == 0
    assert calls == ["seed", "list", "probe"]


def test_main_rejects_a_list_subcommand_with_exit_code_two(monkeypatch):
    """任务书写「main(["list"]) 返回 0」，但脚本只有 `--probe` 一个开关、没有位置参数
    ⇒ argparse 直接以退出码 2 拒绝。锚点与磁盘不符，按现状钉。"""
    monkeypatch.setattr(sls, "FeedStore", lambda: (_ for _ in ()).throw(AssertionError("不该建库")))

    with pytest.raises(SystemExit) as exc:
        sls.main(["list"])

    assert exc.value.code == 2
