# -*- coding: utf-8 -*-
"""prune_archive.py 特征化安全测试（916p-a4-007）。

全部 tmp_path 隔离（monkeypatch 模块级 ARCHIVE_DIR/RAW_DIR），零真实 archive/ 触碰。
固定现状（含 docstring/实现不符与非目录条目风险），修复建议只写报告不落盘。
可复跑：.venv/Scripts/python.exe -m pytest tests/test_prune_archive.py -q
"""
import importlib.util
from pathlib import Path as _P

import pytest

_SCRIPT = _P(__file__).resolve().parents[1] / "scripts" / "prune_archive.py"
_spec = importlib.util.spec_from_file_location("prune_archive_under_test", _SCRIPT)
prune_archive = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prune_archive)


def _mk_dirs(monkeypatch, names, keep=20):
    """建隔离 archive 目录与 keep/2 个快照目录，返回模块与目录路径。"""
    import tempfile, pathlib
    root = pathlib.Path(tempfile.mkdtemp())
    archive = root / "archive"
    archive.mkdir()
    for n in names:
        (archive / n).mkdir()
    monkeypatch.setattr(prune_archive, "ARCHIVE_DIR", archive)
    monkeypatch.setattr(prune_archive, "ARCHIVE_KEEP", keep)
    return prune_archive, archive


def test_dry_run_does_not_delete_excess(monkeypatch):
    """apply=False：超额目录不被删除（断言目录仍在）。口径：scripts/prune_archive.py:31-37。"""
    mod, archive = _mk_dirs(monkeypatch, [f"2026_01_{i:02d}" for i in range(25)], keep=20)
    excess = mod.rule_archive(apply=False)
    assert len(excess) == 5
    assert len(list(archive.iterdir())) == 25  # 未删除


def test_apply_deletes_only_excess_keep_equals_keep(monkeypatch):
    """apply=True：只删超额项，保留数 == ARCHIVE_KEEP。"""
    mod, archive = _mk_dirs(monkeypatch, [f"2026_02_{i:02d}" for i in range(25)], keep=20)
    mod.rule_archive(apply=True)
    assert len(list(archive.iterdir())) == 20


def test_sort_order_keeping_which_batch(monkeypatch):
    """排序口径：按名称排序，保留名称最大（最新）的 20 个，删名称最小 5 个。"""
    mod, archive = _mk_dirs(monkeypatch, [f"2026_03_{i:02d}" for i in range(25)], keep=20)
    excess = mod.rule_archive(apply=False)
    names = [p.name for p in excess]
    assert names == [f"2026_03_{i:02d}" for i in range(5)]  # 最小命名 5 个进超额


def test_non_dir_entry_in_excess_fixed_current_behaviour(monkeypatch):
    """现状固定：混入非目录条目（index.json）落入超额集合 → rmtree 抛 NotADirectoryError（无捕获）。"""
    import tempfile, pathlib
    root = pathlib.Path(tempfile.mkdtemp())
    archive = root / "archive"
    archive.mkdir()
    for i in range(20):
        (archive / f"2026_04_{i:02d}").mkdir()
    (archive / "00_index.json").write_text("{}", encoding="utf-8")  # 名称最小 → 必落入超额
    monkeypatch.setattr(prune_archive, "ARCHIVE_DIR", archive)
    monkeypatch.setattr(prune_archive, "ARCHIVE_KEEP", 20)
    # 排序按名称：index.json 排最前（数字目录名 '2' 开头大于 'i'？实测 'i'>'2'，
    # index.json 排最后）→ 必进超额集合，rmtree 对文件抛 NotADirectoryError
    with pytest.raises(OSError):  # NotADirectoryError 是 OSError 子类（按现状钉死）
        prune_archive.rule_archive(apply=True)


def test_rule_raw_age_filter_and_dry_run(monkeypatch, tmp_path):
    """rule_raw：超 RAW_KEEP_DAYS 的列入、未超的不列入；apply=False 不删。"""
    import os, time
    raw = tmp_path / "raw"
    raw.mkdir()
    old_f = raw / "old.txt"
    new_f = raw / "new.txt"
    old_f.write_text("o", encoding="utf-8")
    new_f.write_text("n", encoding="utf-8")
    old_stamp = time.time() - 120 * 86400
    os.utime(old_f, (old_stamp, old_stamp))
    monkeypatch.setattr(prune_archive, "RAW_DIR", raw)
    stale = prune_archive.rule_raw(apply=False)
    assert [p.name for p in stale] == ["old.txt"]
    assert old_f.exists() and new_f.exists()  # dry-run 不删


def test_archive_dir_missing_returns_empty(monkeypatch, tmp_path):
    """目录缺失：返回空列表且不抛异常。"""
    monkeypatch.setattr(prune_archive, "ARCHIVE_DIR", tmp_path / "not_there")
    assert prune_archive.rule_archive(apply=True) == []
    monkeypatch.setattr(prune_archive, "RAW_DIR", tmp_path / "raw_not_there")
    assert prune_archive.rule_raw(apply=True) == []
