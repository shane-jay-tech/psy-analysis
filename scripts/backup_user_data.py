#!/usr/bin/env python3
"""Backup psy-analysis user data.

Packs %USERPROFILE%/.psy_analysis/projects/ (whole tree) plus the repo-local
data/literature_feed/feed.sqlite into D:/code/backups/psy-analysis/psy-<stamp>.zip,
keeping the newest 10 archives. Writing outside the repo is explicitly
authorized by task 20260904-185801-12f1.
"""
import argparse
import sqlite3
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROJECTS_DIR = Path.home() / ".psy_analysis" / "projects"
FEED_DB = REPO / "data" / "literature_feed" / "feed.sqlite"
BACKUP_ROOT = Path(r"D:\code\backups\psy-analysis")
KEEP = 10


def _live_article_count() -> "int | None":
    """活库（含未折叠 WAL）的 articles 行数；读不到返回 None（不把"读不到"当 0）。"""
    if not FEED_DB.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{FEED_DB.as_posix()}?mode=ro", uri=True, timeout=30)
        try:
            return int(con.execute("SELECT count(*) FROM articles").fetchone()[0])
        finally:
            con.close()
    except sqlite3.Error as e:
        print(f"[backup] WARN live article count unavailable: {e}")
        return None


def _snapshot_sqlite(src: Path, dst: Path) -> int:
    """SQLite backup API 取一致快照（**含未折叠的 WAL 内容**），返回快照 articles 行数。

    s927-A1（2026-09-27 用户授权）：改前是 `zf.write(FEED_DB)` 只打包主文件 ⇒
    `feed.sqlite-wal` 里未折叠的事务整批丢失，沙盒实测每份周备份少约 13.7% 的
    articles（151/175）、fetch_runs（43/44），而脚本退出码仍是 0（**假成功**）。
    backup() 走 SQLite 自己的复制协议，落盘即自洽：恢复只需解出这一个文件。
    """
    uri = f"file:{src.as_posix()}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=30)
    except sqlite3.OperationalError:
        # 只读打不开（-shm 不可映射等）时退到普通连接；本函数不改源库内容。
        con = sqlite3.connect(str(src), timeout=30)
    try:
        out = sqlite3.connect(str(dst))
        try:
            con.backup(out)
        finally:
            out.close()
        try:
            return int(con.execute("SELECT count(*) FROM articles").fetchone()[0])
        except sqlite3.Error:
            return -1
    finally:
        con.close()


def create_backup() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    out = BACKUP_ROOT / f"psy-{stamp}.zip"
    with tempfile.TemporaryDirectory(prefix="psy_bak_src_") as tmp:
        snap = Path(tmp) / "feed.sqlite"
        snap_count = None
        if FEED_DB.exists():
            snap_count = _snapshot_sqlite(FEED_DB, snap)
            live = _live_article_count()
            if live is not None and snap_count >= 0:
                gap = live - snap_count
                # 允许 1 行以内的在途写入；差得多说明快照没跟上 ⇒ 拒绝产出"看起来成功"的残档
                if gap > max(1, live // 100):
                    raise RuntimeError(
                        f"快照落后活库 {gap} 行（快照 {snap_count} / 活库 {live}）⇒ 拒绝落档，请重跑")
                if gap > 0:
                    print(f"[backup] NOTE snapshot trails live by {gap} row(s) (in-flight write)")
            print(f"[backup] feed snapshot: {snap_count} articles (WAL folded in)")
        else:
            print(f"[backup] WARN feed db missing: {FEED_DB}")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            if PROJECTS_DIR.is_dir():
                for p in sorted(PROJECTS_DIR.rglob("*")):
                    if p.is_file():
                        zf.write(p, arcname=str(p.relative_to(PROJECTS_DIR.parent)))
            else:
                print(f"[backup] WARN projects dir missing: {PROJECTS_DIR}")
            if snap_count is not None:
                zf.write(snap, arcname="literature_feed/feed.sqlite")
    return out


def prune(keep: int = KEEP) -> int:
    if keep < 1:
        # s919-22：keep=0 会让下面的切片变成"删掉全部备份"，且本函数是唯一有破坏性的入口。
        raise ValueError(f"prune(keep={keep}) 被拒绝：keep 必须 >= 1，否则将清空 {BACKUP_ROOT} 下全部备份")
    zips = sorted(BACKUP_ROOT.glob("psy-*.zip"), reverse=True)
    removed = 0
    for old in zips[keep:]:
        try:
            old.unlink()
            removed += 1
        except OSError as e:
            print(f"[backup] WARN could not delete {old.name}: {e}")
    return removed


def verify(archive: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        assert bad is None, f"corrupt member: {bad}"
        names = zf.namelist()
        # s919-12：只数"文件条目"。改前拿 extracted（rglob 只会数到文件）去等 namelist 全长，
        # 任何带目录条目（"dir/"）的 zip 都被判成损坏——create_backup 自己不打目录条目所以
        # 自家备份相安无事，但 `--verify-only <外部 zip>` 一验一个准（s918-35 遗留段）。
        file_entries = [n for n in names if not zf.getinfo(n).is_dir()]
        with tempfile.TemporaryDirectory(prefix="psy_bak_") as tmp:
            zf.extractall(tmp)
            extracted = sum(1 for p in Path(tmp).rglob("*") if p.is_file())
            # s927-A1：档里的 feed.sqlite 必须是可开的自洽快照（改前只装主文件、无 WAL）。
            feed = Path(tmp) / "literature_feed" / "feed.sqlite"
            if feed.exists():
                con = sqlite3.connect(f"file:{feed.as_posix()}?mode=ro", uri=True)
                try:
                    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
                    assert integrity == "ok", f"archive feed.sqlite integrity_check={integrity}"
                    n_articles = con.execute("SELECT count(*) FROM articles").fetchone()[0]
                finally:
                    con.close()
                print(f"[backup] feed snapshot integrity ok: {n_articles} articles")
    assert extracted == len(file_entries), f"extracted {extracted} != file entries {len(file_entries)}"
    print(f"[backup] verify ok: {len(file_entries)} files / {len(names)} entries, "
          f"{archive.stat().st_size} bytes")


def main():
    ap = argparse.ArgumentParser(description="backup psy user data (retention 10)")
    ap.add_argument("--verify-only", metavar="ZIP", help="verify an existing archive")
    args = ap.parse_args()

    t0 = time.time()
    if args.verify_only:
        verify(Path(args.verify_only))
        return 0
    out = create_backup()
    verify(out)
    removed = prune()
    print(f"[backup] done in {time.time() - t0:.1f}s -> {out} (pruned {removed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
