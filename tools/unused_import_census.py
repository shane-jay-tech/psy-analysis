"""AST unused-import 普查工具（txt=1 高置信口径＋再输出链排除＋monkeypatch 陷阱标注）。

谱系：s930-03 防回流钉 → s1004-02 AST 普查 19 件 → s1010-05/06 新矿批 A/B → s1010-39 常驻化收编。
只报不动：本工具只输出普查清单，删除执行归人工单。

口径：
- usage：AST 层 ast.Name 引用计数（import 别名本身不计）——typo 名/字符串/注释不算使用。
- txt：源码文本中该名字的 \b 词边界出现次数；txt==1（仅 import 行）才有资格判高置信死件。
- kind：dead（全仓零外部引用）＞ 保守类 reexport（他文件 import 行同名引用——可能为再输出链，
  也可能仅同名 import；一律保护不判死，真再输出归属由人工单核）
  ＞ string_ref（他文件引号内引用，monkeypatch.setattr/getattr 陷阱）＞ crossref（他文件其他形态引用）
  ＞ suspect（本文件 AST 零使用但文本另有出现：注释/docstring/typo 变体，需人工定性）。
  保护类优先于 dead：凡命中保护类一律不判死。

用法：
    python tools/unused_import_census.py <文件或目录> [--root 仓库根] [--json]

root 供全仓引用扫描（再输出链/字符串引用跨文件才可见），缺省=目标路径本身；
对 psy 仓常规用法：python tools/unused_import_census.py src --root . --json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from datetime import datetime
from pathlib import Path

_IMPORT_STOP = "__future__"


def _collect_imports(tree: ast.AST):
    """返回 [(绑定名, 行号)]；import a.b.c 绑定 a；from m import n as p 绑定 p。"""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bind = (alias.asname or alias.name).split(".")[0]
                out.append((bind, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            for alias in node.names:
                out.append((alias.asname or alias.name, node.lineno))
    return out


def _usage_count(tree: ast.AST, name: str) -> int:
    return sum(1 for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == name)


def _txt_count(src: str, name: str) -> int:
    return len(re.findall(rf"\b{re.escape(name)}\b", src))


def _is_import_line(line: str, name: str) -> bool:
    return bool(re.match(rf"^\s*(from\s+\S+\s+)?import\b[^#]*\b{re.escape(name)}\b", line))


def _in_quotes(line: str, name: str) -> bool:
    return any(
        re.search(rf"['\"][^'\"]*\b{re.escape(name)}\b[^'\"]*['\"]", seg)
        for seg in re.findall(r"['\"].*?['\"]|[^'\"]+", line)
        if seg.startswith(("'", '"'))
    )


def census(target: Path, root: Path):
    """主普查：返回 items 列表（不含 used，即未列出的 import 名均 usage>0）。"""
    files = sorted(target.rglob("*.py")) if target.is_dir() else [target]
    candidates = []  # (file_rel, line, name, txt)
    for path in files:
        try:
            src = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        for name, lineno in _collect_imports(tree):
            if _usage_count(tree, name) == 0:
                candidates.append((str(rel), lineno, name, _txt_count(src, name)))

    # —— 全仓单趟扫描：alternation 一次过每行，替代逐候选趟（O(行数) 而非 O(候选×行数)）——
    repo_cache = []  # [(abs_path_str, rel_path, [lines])]
    for path in root.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            repo_cache.append((str(path), path, path.read_text(encoding="utf-8").splitlines()))
        except (UnicodeDecodeError, OSError):
            continue
    names = sorted({c[2] for c in candidates if c[3] <= 1})
    alt = re.compile(rf"\b({'|'.join(re.escape(n) for n in names)})\b") if names else None
    hits: dict[str, list] = {}  # name -> [(kind, abs_path, evidence_str)]
    if alt:
        for abs_path, rel_path, lines in repo_cache:
            rel2 = str(rel_path.relative_to(root)) if rel_path.is_relative_to(root) else str(rel_path)
            for i, line in enumerate(lines, 1):
                found = alt.findall(line)
                if not found:
                    continue
                for name in dict.fromkeys(found):  # 去重保序
                    k = "reexport" if _is_import_line(line, name) else (
                        "string_ref" if _in_quotes(line, name) else "crossref")
                    hits.setdefault(name, []).append((k, abs_path, f"{rel2}:{i}: {line.strip()[:80]}"))

    items = []
    for rel, lineno, name, txt in candidates:
        if txt > 1:
            items.append({"file": rel, "line": lineno, "name": name, "txt": txt, "kind": "suspect", "evidence": ""})
            continue
        defining = str(root / rel)
        file_hits = [h for h in hits.get(name, []) if h[1] != defining]
        kinds = {k for k, _, _ in file_hits}
        kind = "reexport" if "reexport" in kinds else (
            "string_ref" if "string_ref" in kinds else (
                "crossref" if "crossref" in kinds else "dead"))
        evidence = next((ev for k, _, ev in file_hits if k == kind), "")
        items.append({"file": rel, "line": lineno, "name": name, "txt": txt, "kind": kind, "evidence": evidence})
    items.sort(key=lambda d: (d["file"], d["line"], d["name"]))
    return items


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="AST unused-import 普查（只报不动）")
    ap.add_argument("target", help="普查目标文件或目录")
    ap.add_argument("--root", default=None, help="全仓引用扫描根（缺省=目标路径）")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args(argv)
    target, root = Path(args.target), Path(args.root) if args.root else Path(args.target)
    items = census(target, root)
    totals: dict[str, int] = {}
    for it in items:
        totals[it["kind"]] = totals.get(it["kind"], 0) + 1
    payload = {
        "tool": "unused_import_census",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target": str(target), "root": str(root), "totals": totals, "items": items,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        print(f"unused_import_census: target={target} root={root}")
        for kind in ("dead", "reexport", "string_ref", "crossref", "suspect"):
            if totals.get(kind):
                print(f"  {kind}: {totals[kind]}")
        for it in items:
            print(f"  {it['file']}:{it['line']} {it['name']} [{it['kind']}] {it['evidence']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
