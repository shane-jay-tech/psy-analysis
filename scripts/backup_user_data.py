#!/usr/bin/env python3
"""Backup psy-analysis user data.

Packs %USERPROFILE%/.psy_analysis/projects/ (whole tree) plus the repo-local
data/literature_feed/feed.sqlite into D:/code/backups/psy-analysis/psy-<stamp>.zip,
keeping the newest 10 archives. Writing outside the repo is explicitly
authorized by task 20260904-185801-12f1.
"""
import argparse
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


def create_backup() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    out = BACKUP_ROOT / f"psy-{stamp}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        if PROJECTS_DIR.is_dir():
            for p in sorted(PROJECTS_DIR.rglob("*")):
                if p.is_file():
                    zf.write(p, arcname=str(p.relative_to(PROJECTS_DIR.parent)))
        else:
            print(f"[backup] WARN projects dir missing: {PROJECTS_DIR}")
        if FEED_DB.exists():
            zf.write(FEED_DB, arcname="literature_feed/feed.sqlite")
        else:
            print(f"[backup] WARN feed db missing: {FEED_DB}")
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
