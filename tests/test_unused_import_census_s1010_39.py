# -*- coding: utf-8 -*-
"""s1010-39 unused_import_census 三支单测：typo 名/再输出名/字符串引用均不误报。"""
import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "unused_import_census.py"


def _run(target: Path, root: Path):
    proc = subprocess.run(
        [sys.executable, str(TOOL), str(target), "--root", str(root), "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_typo_variant_still_dead(tmp_path):
    """typo 变体（OrderedDictd）骗不过本口径：AST usage=0、词边界 txt=1 → 正确判 dead。

    纯文本「子串计数」普查会把 OrderedDictd 误当使用（count=2 → 漏报）；
    AST+\\b 词边界口径不受 typo 名蒙蔽，该报就报（不误判为活）。
    """
    (tmp_path / "mod.py").write_text(
        "from collections import OrderedDict\n"
        "OrderedDictd = 1\n",  # typo：多一个 d；AST 层 id 不同，文本词边界不匹配
        encoding="utf-8",
    )
    payload = _run(tmp_path, tmp_path)
    items = {(i["file"], i["name"]): i for i in payload["items"]}
    assert ("mod.py", "OrderedDict") in items, "AST 零使用必须入报告（子串文本口径会漏报）"
    assert items[("mod.py", "OrderedDict")]["kind"] == "dead"


def test_reexport_name_not_dead(tmp_path):
    """包 __init__ 再输出的名字：报 reexport 保护类，不判 dead（s1010-06 陷阱①口径）。"""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .mod import HELPER\n", encoding="utf-8")
    (pkg / "mod.py").write_text("from .defs import HELPER\n", encoding="utf-8")
    (pkg / "defs.py").write_text("HELPER = 1\n", encoding="utf-8")
    payload = _run(pkg, tmp_path)
    items = {(i["file"], i["name"]): i for i in payload["items"]}
    key = (str(Path("pkg") / "mod.py"), "HELPER")
    assert key in items
    assert items[key]["kind"] == "reexport"
    assert items[key]["kind"] != "dead"
    assert "__init__.py" in items[key]["evidence"]


def test_string_ref_not_dead(tmp_path):
    """monkeypatch.setattr 字符串引用：报 string_ref 陷阱类，不判 dead（s1010-06 陷阱②口径）。"""
    (tmp_path / "autosave.py").write_text(
        "from legacy import LEGACY_META_FILE\n", encoding="utf-8"
    )
    (tmp_path / "conftest.py").write_text(
        "import autosave\n"
        "monkeypatch.setattr(autosave, \"LEGACY_META_FILE\", 'x')\n",
        encoding="utf-8",
    )
    payload = _run(tmp_path, tmp_path)
    items = {(i["file"], i["name"]): i for i in payload["items"]}
    key = ("autosave.py", "LEGACY_META_FILE")
    assert key in items
    assert items[key]["kind"] == "string_ref"
    assert items[key]["kind"] != "dead"
    assert "conftest.py" in items[key]["evidence"]
