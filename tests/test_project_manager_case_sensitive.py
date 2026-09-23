"""s923-37：`project_manager` 在 win32 大小写不敏感语义下的暴露面钉桩。

**只加测试，不改生产码。** 被钉的两行：
`src/utils/project_manager.py:131` `for workspace_file in sorted(PROJECTS_DIR.glob("*.json")):`
`src/utils/project_manager.py:132` `if workspace_file == INDEX_FILE:`
（`INDEX_FILE = PROJECTS_DIR / "index.json"`，:39）
生产入口是 `_read_index()` 的索引损坏分支（:160-175 调 `_recover_index_from_workspaces()`），
`list_projects()` 经它落到用户可见的项目列表。

隔离声明（完成标准第 2 条）：所有用例只读写 pytest `tmp_path`，并把
`pm.PROJECTS_DIR` 与 `pm.INDEX_FILE` **两个**模块常量一起 monkeypatch 到沙盒
（只搬 `PROJECTS_DIR` 会让 `:132` 比到真实家目录的 index 上，得出假结论）。
被测函数本身只 `glob`/`stat`；唯一的写盘发生在端到端用例的沙盒内。
真实 `~/.psy_analysis/projects` 全程零写，由末例反向自证。

现场取证结论（Python 3.12.9 / Windows / NTFS，读数见 outbox/s923-37.result.md）：
1. `glob("*.json")` 在 win32 **确实大小写不敏感** ⇒ `index.JSON`、`INDEX.json`
   都会被匹配到 —— 卷宗前提前半条成立。
2. 但 `:132` 用的是 **Path 对象相等**，而 `WindowsPath.__eq__/__hash__` 走
   `normcase`（同样大小写不敏感）⇒ 变体**会被排除**。故卷宗「名为 `index.JSON`
   的文件会被当成一个项目」在本机**不成立，已否证**
   （见 `test_uppercase_extension_index_is_excluded_by_the_guard`）。
3. 残留的真实风险是**判据依赖的相等语义**：一旦有人把 :132「收紧」成按 `.name`
   或 `str()` 比较（看着更像严格），大小写变体立刻漏成一个假项目
   （id 取 `stem` ⇒ `index` 或 `INDEX`）⇒ 用三例钉住这条因果：
   `test_guard_relies_on_case_insensitive_path_equality`（现在的语义）
   ＋ `test_index_json_leaks_as_bogus_project_when_guard_does_not_match`
   ＋ `test_variant_index_json_leaks_as_bogus_project_on_win32`（不匹配时确实漏，
   证明本文件不是恒真绿）。

NTFS 事实（`test_case_variant_names_are_the_same_file_on_windows` 钉住）：
同目录下 `index.JSON` 与 `index.json`、以及 `INDEX.json` 三者都是**同一个文件**
⇒ 夹具必须把不同变体放不同沙盒，不得在同一目录里造两名并存。

平台门：带 win32 大小写语义的 8 例在 POSIX（大小写敏感卷）结论相反——POSIX 上
`glob("*.json")` 根本不匹配 `index.JSON`，故按 `os.name != "nt"` skip 并写明理由；
本机 nt 12 例全跑，POSIX 下仍有 4 例执行（小写排除组＋泄漏判别力＋两型隔离自证）。

判别力（tmp 变异取证，生产码零改动，读数见 result 的证据节）：
M1 把 :132 换成大小写敏感的 `.name` 比较 ⇒ 恰 2 例红（两型变体排除例）；
M2 把 :132 短路成 `if False` ⇒ 恰 3 例红（再加小写对照例）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List

import pytest

from src.utils import app_paths
from src.utils import project_manager as pm

# 打桩前（真实值）只读快照，供末例反向自证「夹具文件没漏进真实用户目录」
_REAL_PROJECTS_DIR = app_paths.PROJECTS_DIR
_FIXTURE_ARTIFACT_NAMES = frozenset(
    {"index.JSON", "INDEX.json", "abc123.json", "def456.json", "other-index.json"}
)

requires_win32_case_insensitivity = pytest.mark.skipif(
    os.name != "nt",
    reason="win32 大小写不敏感语义专属：POSIX 上 glob 与 Path 相等都大小写敏感，结论相反",
)


def _sandbox(
    monkeypatch: "pytest.MonkeyPatch",
    root: Path,
    *,
    names: Iterable[str],
    index_name: str = "index.json",
) -> Path:
    """把 PROJECTS_DIR / INDEX_FILE 一起搬到沙盒，并按 names 造占位工作区文件。"""
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        (root / name).write_text(json.dumps({"placeholder": True}), encoding="utf-8")
    monkeypatch.setattr(pm, "PROJECTS_DIR", root)
    monkeypatch.setattr(pm, "INDEX_FILE", root / index_name)
    return root


def _ids(projects: "List[pm.Project]") -> "set[str]":
    return {p.id for p in projects}


# --------------------------------------------------------------------------- #
# 1. 前提前半条：glob 模式本身确实大小写不敏感（暴露面的入口）
# --------------------------------------------------------------------------- #

@requires_win32_case_insensitivity
def test_glob_matches_uppercase_extension_variant(tmp_path, monkeypatch):
    root = _sandbox(monkeypatch, tmp_path / "p", names=["index.JSON", "abc123.json"])

    hit = {p.name for p in root.glob("*.json")}

    assert hit == {"index.JSON", "abc123.json"}, 'glob("*.json") 应在 win32 上匹配大写扩展名变体'


@requires_win32_case_insensitivity
def test_glob_matches_uppercase_basename_variant(tmp_path, monkeypatch):
    root = _sandbox(monkeypatch, tmp_path / "p", names=["INDEX.json", "abc123.json"])

    hit = {p.name for p in root.glob("*.json")}

    assert hit == {"INDEX.json", "abc123.json"}, 'glob("*.json") 应匹配到大写主名变体'


# --------------------------------------------------------------------------- #
# 2. 现状钉死：`:132` 的相等比较把两种变体都挡掉了（否证卷宗后半条）
# --------------------------------------------------------------------------- #

@requires_win32_case_insensitivity
def test_uppercase_extension_index_is_excluded_by_the_guard(tmp_path, monkeypatch):
    _sandbox(monkeypatch, tmp_path / "p", names=["index.JSON", "abc123.json"])

    recovered = pm._recover_index_from_workspaces()

    assert _ids(recovered) == {"abc123"}
    assert "index" not in _ids(recovered), (
        "现状：index.JSON 被 :132 排除，不会被当成一个项目（卷宗此条已否证）"
    )


@requires_win32_case_insensitivity
def test_uppercase_basename_index_is_excluded_by_the_guard(tmp_path, monkeypatch):
    _sandbox(monkeypatch, tmp_path / "p", names=["INDEX.json", "abc123.json"])

    recovered = pm._recover_index_from_workspaces()

    assert _ids(recovered) == {"abc123"}, "INDEX.json 同理被排除；若漏则 id 会是 INDEX"


@requires_win32_case_insensitivity
def test_guard_relies_on_case_insensitive_path_equality(tmp_path, monkeypatch):
    """钉住「为什么挡得住」：Path 相等大小写不敏感，而 name/str 相等敏感。

    谁把 :132 改成 `workspace_file.name == "index.json"` 或 `str()` 比较，
    本例立刻红——那时上面两例的排除结论也必须同时改写（见两型泄漏例）。
    """
    root = _sandbox(monkeypatch, tmp_path / "p", names=["index.JSON", "abc123.json"])
    variant = root / "index.JSON"

    assert variant == pm.INDEX_FILE
    assert variant.name != pm.INDEX_FILE.name
    assert str(variant) != str(pm.INDEX_FILE)
    assert (root / "INDEX.json") == pm.INDEX_FILE


# --------------------------------------------------------------------------- #
# 3. 判别力对照：守卫一旦不匹配，漏出来的假项目长什么样
# --------------------------------------------------------------------------- #

def test_index_json_leaks_as_bogus_project_when_guard_does_not_match(tmp_path, monkeypatch):
    """跨平台可跑：INDEX_FILE 指到别处 ⇒ 真索引文件被当成一个项目返回。

    这条保证本文件不是恒真绿——`_recover_index_from_workspaces()` 确实在消费
    glob 结果，且假项目的形状是 id 取 `stem`。
    """
    _sandbox(
        monkeypatch,
        tmp_path / "p",
        names=["index.json", "def456.json"],
        index_name="other-index.json",
    )

    recovered = pm._recover_index_from_workspaces()

    assert _ids(recovered) == {"def456", "index"}
    bogus = next(p for p in recovered if p.id == "index")
    assert bogus.name == "恢复的项目 index"
    assert bogus.note.startswith("从损坏的项目索引自动恢复")
    assert bogus.file_path.name == "index.json"


@requires_win32_case_insensitivity
def test_variant_index_json_leaks_as_bogus_project_on_win32(tmp_path, monkeypatch):
    """同型的「变体版」：把 :132 换成大小写敏感比较后就会是这个读数。"""
    _sandbox(
        monkeypatch,
        tmp_path / "p",
        names=["index.JSON", "abc123.json"],
        index_name="other-index.json",
    )

    recovered = pm._recover_index_from_workspaces()

    assert _ids(recovered) == {"abc123", "index"}


def test_lowercase_index_json_is_excluded(tmp_path, monkeypatch):
    """卷宗要求的对照组：全小写 index.json 正常排除。"""
    _sandbox(monkeypatch, tmp_path / "p", names=["index.json", "def456.json"])

    recovered = pm._recover_index_from_workspaces()

    assert _ids(recovered) == {"def456"}


@requires_win32_case_insensitivity
def test_variant_index_reaches_user_visible_list_via_public_api(tmp_path, monkeypatch):
    """端到端：沙盒里的 index 变体写成损坏索引，走 `list_projects()` 看用户读数。

    win32 上 `INDEX_FILE.exists()` 同样命中变体（NTFS 同一文件），
    所以损坏索引被隔离重建后，用户可见列表只含真实工作区。

    ⚠️ 此例对 :132 的守卫**不具判别力**（变异取证实测 M1/M2 都不让它红）：
    变体在恢复之前已被 `os.replace` 改名成 `index.corrupt.*.bak`，glob 再也看不见它。
    它钉的是「exists() 也命中变体」这一半，与守卫无关——别把它当守卫的护栏。
    """
    root = _sandbox(monkeypatch, tmp_path / "p", names=["index.JSON", "abc123.json"])
    (root / "index.JSON").write_text("{ this is not json", encoding="utf-8")

    projects = pm.list_projects()

    assert _ids(projects) == {"abc123"}
    assert (root / "index.json").exists()
    assert [d["id"] for d in json.loads((root / "index.json").read_text(encoding="utf-8"))] == ["abc123"]
    assert len(list(root.glob("index.corrupt.*.bak"))) == 1


# --------------------------------------------------------------------------- #
# 4. 夹具有效性 ＆ 零触碰真实用户目录
# --------------------------------------------------------------------------- #

@requires_win32_case_insensitivity
def test_case_variant_names_are_the_same_file_on_windows(tmp_path):
    """NTFS 上三种大小写写法是同一个文件——夹具不得在同一目录造两名并存。"""
    root = tmp_path / "p"
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.JSON").write_text('{"via": "uppercase"}', encoding="utf-8")

    assert [p.name for p in root.iterdir()] == ["index.JSON"]
    assert json.loads((root / "index.json").read_text(encoding="utf-8")) == {"via": "uppercase"}
    assert (root / "index.JSON").stat().st_ino == (root / "index.json").stat().st_ino


def test_sandbox_moves_both_module_constants(tmp_path, monkeypatch):
    """两个常量必须一起搬：只改 PROJECTS_DIR 会让 :132 比到真实家目录上。"""
    root = _sandbox(monkeypatch, tmp_path / "p", names=[])

    assert pm.PROJECTS_DIR == root
    assert pm.INDEX_FILE == root / "index.json"
    assert Path(str(pm.PROJECTS_DIR)).is_relative_to(tmp_path)
    assert Path(str(pm.INDEX_FILE)).is_relative_to(tmp_path)
    assert pm.PROJECTS_DIR != _REAL_PROJECTS_DIR


def test_no_fixture_artifact_in_real_projects_dir():
    """零触碰自证：夹具用的文件名一个都不该出现在真实 ~/.psy_analysis/projects。"""
    if not _REAL_PROJECTS_DIR.exists():
        return
    leaked = {p.name for p in _REAL_PROJECTS_DIR.iterdir()} & _FIXTURE_ARTIFACT_NAMES
    assert leaked == set(), f"夹具文件漏进了真实用户目录：{sorted(leaked)}"
