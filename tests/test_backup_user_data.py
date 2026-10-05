"""scripts/backup_user_data.py 备份三分支特征化测试（s918-35）。

钉住现状：create 落 zip / prune 按 keep 截断 / verify 双向校验。
备份根与用户目录全部 monkeypatch 到 tmp，真实 D:/code/backups 零触碰。
"""
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import backup_user_data as bud

STAMPS = [f"2026{m:02d}01-000000" for m in range(1, 13)]


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    projects = tmp_path / "home" / ".psy_analysis" / "projects"
    (projects / "p1").mkdir(parents=True)
    (projects / "p1" / "notes.md").write_text("note", encoding="utf-8")
    feed = tmp_path / "repo" / "data" / "literature_feed" / "feed.sqlite"
    feed.parent.mkdir(parents=True)
    # s1004-21（s930-47 归因落地）：夹具喂**真 sqlite 库**（含 articles 表）——
    # r5 A1（6fb6b16）把备份改走 sqlite3.backup() 真库协议后，旧的 11 字节假串
    # 会被正确报 DatabaseError。顺带激活 _live_article_count 的非 None 分支。
    import sqlite3

    con = sqlite3.connect(feed)
    try:
        con.execute("CREATE TABLE articles (id INTEGER PRIMARY KEY, title TEXT)")
        con.executemany("INSERT INTO articles (title) VALUES (?)", [(f"t{i}",) for i in range(3)])
        con.commit()
    finally:
        con.close()
    root = tmp_path / "backups"
    monkeypatch.setattr(bud, "PROJECTS_DIR", projects)
    monkeypatch.setattr(bud, "FEED_DB", feed)
    monkeypatch.setattr(bud, "BACKUP_ROOT", root)
    return SimpleNamespace(projects=projects, feed=feed, root=root)


def _seed_archives(root: Path, stamps=STAMPS):
    root.mkdir(parents=True, exist_ok=True)
    for stamp in stamps:
        (root / f"psy-{stamp}.zip").write_bytes(b"PK")
    return sorted(root.glob("psy-*.zip"))


def test_create_backup_packs_projects_tree_and_feed_db(sandbox):
    out = bud.create_backup()

    assert out.parent == sandbox.root
    assert out.name.startswith("psy-") and out.suffix == ".zip"
    with zipfile.ZipFile(out) as zf:
        names = [n.replace("\\", "/") for n in zf.namelist()]
    assert "literature_feed/feed.sqlite" in names
    # arcname 相对 PROJECTS_DIR.parent，故 ".psy_analysis" 这一层不进归档名
    assert "projects/p1/notes.md" in names


def test_verify_accepts_archive_right_after_create(sandbox, capsys):
    out = bud.create_backup()

    bud.verify(out)

    assert "verify ok" in capsys.readouterr().out


def test_prune_keeps_newest_and_removes_oldest(sandbox):
    seeded = _seed_archives(sandbox.root)

    removed = bud.prune(keep=10)

    assert removed == 2
    assert sorted(sandbox.root.glob("psy-*.zip")) == seeded[2:]
    assert (sandbox.root / "psy-20261201-000000.zip").exists()
    assert not (sandbox.root / "psy-20260101-000000.zip").exists()
    assert not (sandbox.root / "psy-20260201-000000.zip").exists()


def test_prune_with_fewer_archives_than_keep_deletes_nothing(sandbox):
    seeded = _seed_archives(sandbox.root, STAMPS[:3])

    assert bud.prune() == 0
    assert sorted(sandbox.root.glob("psy-*.zip")) == seeded


def test_prune_rejects_keep_below_one(sandbox):
    """s919-22 下限守卫：keep=0/负数一律 ValueError，且**一个文件都不许少**。
    改前现状是 `prune(keep=0)` 把备份根清空（本用例前一版钉的就是它，守卫落地后按新契约改写）。"""
    seeded = _seed_archives(sandbox.root, STAMPS[:3])

    for bad in (0, -1):
        with pytest.raises(ValueError) as ei:
            bud.prune(keep=bad)
        assert "keep" in str(ei.value) and str(bad) in str(ei.value)

    assert sorted(sandbox.root.glob("psy-*.zip")) == seeded


def test_prune_keep_one_is_allowed_boundary(sandbox):
    """守卫不能顺手把合法边界也拦掉：keep=1 保留最新 1 份、删掉其余。"""
    seeded = _seed_archives(sandbox.root, STAMPS[:3])

    assert bud.prune(keep=1) == 2
    assert list(sandbox.root.glob("psy-*.zip")) == [seeded[-1]]


def test_verify_rejects_crc_corrupted_member(sandbox, tmp_path):
    bogus = tmp_path / "psy-bogus.zip"
    with zipfile.ZipFile(bogus, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("payload.txt", "hello")
    raw = bytearray(bogus.read_bytes())
    raw[raw.index(b"hello"):raw.index(b"hello") + 5] = b"HELLO"
    bogus.write_bytes(bytes(raw))

    with pytest.raises(AssertionError, match="corrupt member"):
        bud.verify(bogus)


def test_verify_accepts_archive_carrying_directory_entries(tmp_path, capsys):
    """s919-12 翻正（旧用例 `test_verify_rejects_archive_carrying_directory_entries`
    钉的是那句误判 `extracted 1 != entries 2`）：目录条目不该计入"应被解出的文件数"。
    这是 `--verify-only <外部 zip>` 的常见形态（多数打包工具会写目录条目），改前一律误判损坏。"""
    with_dirs = tmp_path / "psy-dirs.zip"
    with zipfile.ZipFile(with_dirs, "w") as zf:
        zf.writestr("payload.txt", "hello")
        zf.writestr("empty_dir/", "")                 # 目录条目（名以 / 结尾）
        zf.writestr("d/a.txt", "a")
        zf.writestr("d/b.txt", "b")

    bud.verify(with_dirs)                             # 不再抛

    assert "3 files / 4 entries" in capsys.readouterr().out


def test_verify_counts_only_file_entries_when_archive_is_all_directories(tmp_path, capsys):
    """上一条的边界：全是目录条目的空壳包应当判"0 个文件、完好"，
    守卫若写成"跳过名字以 / 结尾的项但计数仍用 namelist"，这条会红。"""
    only_dirs = tmp_path / "psy-onlydirs.zip"
    with zipfile.ZipFile(only_dirs, "w") as zf:
        zf.writestr("a/", "")
        zf.writestr("b/", "")

    bud.verify(only_dirs)

    assert "0 files / 2 entries" in capsys.readouterr().out


def test_create_backup_degrades_loudly_when_sources_missing(sandbox, capsys):
    sandbox.projects.replace(sandbox.root.parent / "elsewhere")
    sandbox.feed.unlink()

    out = bud.create_backup()

    printed = capsys.readouterr().out
    assert out.exists()
    assert "projects dir missing" in printed and "feed db missing" in printed
    with zipfile.ZipFile(out) as zf:
        assert zf.namelist() == []
