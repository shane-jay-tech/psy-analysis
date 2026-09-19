# -*- coding: utf-8 -*-
"""备份链路口径清点＝坏输入行为钉桩（s920-22，**只读清点，不改生产码**）。

四个入口：`create_backup()` / `prune()` / `verify()` / `main(--verify-only ZIP)`。
钉的是"喂进去一个坏路径/坏内容时今天到底发生什么"，供日间决定要不要加前置校验。
隔离纪律：`BACKUP_ROOT`/`PROJECTS_DIR`/`FEED_DB` 一律换到 `tmp_path`——
`prune()` 是本模块**唯一有破坏性的入口**（ unlink 真文件），绝不允许碰 D:/code/backups。
"""
import sys
import zipfile
from pathlib import Path

import pytest

import scripts.backup_user_data as bud


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    backup_root = tmp_path / "backups"
    monkeypatch.setattr(bud, "BACKUP_ROOT", backup_root)
    monkeypatch.setattr(bud, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(bud, "FEED_DB", tmp_path / "feed.sqlite")
    return tmp_path, backup_root


def _make_zip(path: Path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, body in entries:
            zf.writestr(name, body)
    return path


# ---------- 入口三：verify() ----------

def test_verify_missing_path_raises_filenotfound(sandbox):
    """坏输入①：路径不存在 ⇒ 抛 FileNotFoundError，**不是**"校验失败"的干净报错。

    s919-12 遗留段原话就是这条（`--verify-only` 不校验存在性就进 `ZipFile`）。
    """
    tmp_path, _ = sandbox
    with pytest.raises(FileNotFoundError):
        bud.verify(tmp_path / "no-such-backup.zip")


def test_verify_directory_raises_permission_error_on_windows(sandbox):
    """坏输入②：把目录当 zip 传进来 ⇒ 实测 **PermissionError**（不是 IsADirectoryError）。

    `zipfile.ZipFile(dir)` 走到 `io.open(dir, "rb")`，Windows 上抛 PermissionError；
    POSIX 才是 IsADirectoryError ⇒ 钉当前平台实况（跨平台跑要改成 `OSError`）。
    与"校验失败"是两种语义：调用方拿到的是一个像权限问题的异常。
    """
    tmp_path, _ = sandbox
    with pytest.raises(PermissionError):
        bud.verify(tmp_path)


def test_verify_non_zip_file_raises_badzip(sandbox):
    """坏输入③：存在但不是 zip ⇒ zipfile.BadZipFile（三种坏路径里唯一语义清楚的一种）。"""
    tmp_path, _ = sandbox
    not_a_zip = tmp_path / "notes.txt"
    not_a_zip.write_text("这只是个文本文件，不是 zip", encoding="utf-8")

    with pytest.raises(zipfile.BadZipFile):
        bud.verify(not_a_zip)


def test_verify_accepts_archive_with_directory_entries(sandbox, capsys):
    """正例对照（s919-12 的成果，别被上面的钉桩盖过去）：带目录条目的 zip 判**完好**。

    改前拿 namelist 全长去等"解出的文件数"，任何含 `dir/` 的外部包都会被误判损坏。
    """
    tmp_path, _ = sandbox
    arc = _make_zip(tmp_path / "external.zip", [("dir/", ""), ("dir/a.txt", "x"), ("b.txt", "y")])

    bud.verify(arc)                                    # 不抛
    out = capsys.readouterr().out
    assert "verify ok" in out and "2 files" in out and "3 entries" in out


# ---------- 入口四：main(--verify-only) ----------

def test_main_verify_only_propagates_the_same_error(sandbox, monkeypatch):
    """CLI 面：坏路径经 `main()` 出来仍是 FileNotFoundError ⇒ 今天没有用户友好的前置校验。

    只测 `main` 的异常类型，不去跑 `__main__` 的 `sys.exit()`（那要 subprocess）。
    """
    tmp_path, _ = sandbox
    monkeypatch.setattr(sys, "argv",
                        ["backup_user_data.py", "--verify-only", str(tmp_path / "ghost.zip")])

    with pytest.raises(FileNotFoundError):
        bud.main()


# ---------- 入口一：create_backup() ----------

def test_create_backup_with_both_sources_missing_still_writes_an_empty_zip(sandbox, capsys):
    """坏输入④：源目录与 feed 库都不在 ⇒ 今天**照样产出一个 0 条目的 zip 并返回成功**。

    这是清单里最要紧的一条：`main()` 随后 `verify(out)` 也会过（0 文件 == 0 条目），
    日志还会打 "done" ⇒ 一次"成功的备份"里其实什么都没有。只 WARN 不失败。
    """
    _, backup_root = sandbox

    out = bud.create_backup()

    assert out.exists() and out.suffix == ".zip"
    with zipfile.ZipFile(out) as zf:
        assert zf.namelist() == []          # 现状是空 zip；若哪天改成拒绝产出，这条会红，同步本注释
    logged = capsys.readouterr().out
    assert "WARN projects dir missing" in logged and "WARN feed db missing" in logged


def test_created_empty_zip_passes_verify(sandbox, capsys):
    """接上一条：空 zip 过 verify ⇒ "备份成功"与"备份了东西"两件事今天无法区分（登记，不修）。"""
    out = bud.create_backup()
    capsys.readouterr()

    bud.verify(out)
    assert "verify ok" in capsys.readouterr().out


# ---------- 入口二：prune() ----------

def test_prune_rejects_keep_below_one(sandbox):
    """已有守卫（s919-12 落地的 `keep < 1` 拒绝）：这里补一条"备份目录不存在时"的对照。"""
    with pytest.raises(ValueError, match="keep 必须 >= 1"):
        bud.prune(keep=0)


def test_prune_on_missing_backup_root_returns_zero_silently(sandbox, monkeypatch, tmp_path):
    """坏输入⑤：`BACKUP_ROOT` 不存在 ⇒ 返回 0、不建目录、不炸也不 WARN（静默"没什么可清"）。"""
    monkeypatch.setattr(bud, "BACKUP_ROOT", tmp_path / "never_created")

    assert bud.prune(keep=5) == 0
    assert not (tmp_path / "never_created").exists()
