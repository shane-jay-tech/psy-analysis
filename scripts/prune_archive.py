#!/usr/bin/env python3
"""Archive retention for psy-analysis.

Rule 1: repo archive/ holds entries of any kind (snapshot dirs AND loose
        files, name-sorted); when more than 20 entries exist, the oldest are
        deleted until 20 remain. Non-directory entries in the excess set are
        skipped and counted (is_dir guard, 916p-a4-007/917-33).
Rule 2: data/literature_feed/raw/ keeps only the last 90 days.

Default is --dry-run (print only). Pass --apply to actually delete.
"""
import argparse
import re
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = REPO / "archive"
ARCHIVE_KEEP = 20
RAW_DIR = REPO / "data" / "literature_feed" / "raw"
RAW_KEEP_DAYS = 90


def rule_archive(apply: bool) -> list:
    if not ARCHIVE_DIR.is_dir():
        print(f"[prune] archive dir missing: {ARCHIVE_DIR}")
        return []
    entries = [p for p in ARCHIVE_DIR.iterdir()]
    entries.sort(key=lambda p: p.name)
    excess = entries[:-ARCHIVE_KEEP] if len(entries) > ARCHIVE_KEEP else []
    skipped_non_dir = 0
    print(f"[prune] rule1 archive/: {len(entries)} entries, keep {ARCHIVE_KEEP}, "
          f"to delete {len(excess)}")
    for p in excess:
        print(f"  - {p.name}")
        if apply:
            if not p.is_dir():
                # 917-33 is_dir 守卫：非目录超额条目跳过并记录，绝不 rmtree
                print(f"  - [skip] non-directory entry, not removed: {p.name}")
                skipped_non_dir += 1
                continue
            shutil.rmtree(p)
    if skipped_non_dir:
        print(f"[prune] skipped non-directory entries: {skipped_non_dir}")
    return excess


def rule_raw(apply: bool) -> list:
    if not RAW_DIR.is_dir():
        print(f"[prune] raw dir missing: {RAW_DIR}")
        return []
    cutoff = time.time() - RAW_KEEP_DAYS * 86400
    stale = [p for p in RAW_DIR.iterdir() if p.stat().st_mtime < cutoff]
    stale.sort(key=lambda p: p.name)
    print(f"[prune] rule2 raw/ keep {RAW_KEEP_DAYS}d (cutoff "
          f"{datetime.fromtimestamp(cutoff):%Y-%m-%d}): {len(stale)} to delete")
    for p in stale:
        age_days = (time.time() - p.stat().st_mtime) / 86400
        print(f"  - {p.name} ({age_days:.0f}d old)")
        if apply:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    return stale


def main():
    ap = argparse.ArgumentParser(description="archive retention (dry-run by default)")
    ap.add_argument("--apply", action="store_true",
                    help="actually delete; default is dry-run print only")
    args = ap.parse_args()
    print(f"[prune] mode: {'APPLY' if args.apply else 'DRY-RUN (no changes)'}")
    rule_archive(args.apply)
    rule_raw(args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
