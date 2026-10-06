#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ast_return_census — AST return 归属普查常驻工具（s1004-10 收编，s930-16 形状）。

按函数递归 visit：遇嵌套 FunctionDef 另列 nested、Return 只记当前层；
**lambda 的 return 语义（表达式即返回）按设计不收**——若未来要统计 lambda 面
需另立形状（边界见 s930-16 遗留）。

只读解析：零 import、零执行目标模块。

用法：
  python scripts/ast_return_census.py <目标.py 或目录> [--json]
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def census_source(src: str) -> dict:
    tree = ast.parse(src)
    out = {"functions": {}, "nested": {}}

    def visit_fn(fn: ast.FunctionDef | ast.AsyncFunctionDef, qualified: str) -> None:
        direct = []
        nested = []
        for child in fn.body:
            if isinstance(child, ast.Return):
                direct.append(child.lineno)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nested.append(child.name)
                visit_fn(child, f"{qualified}.{child.name}")
            elif isinstance(child, (ast.For, ast.While, ast.If, ast.With,
                                    ast.Try, ast.AsyncFor, ast.With)):
                for sub in ast.walk(child):
                    if isinstance(sub, ast.Return):
                        direct.append(sub.lineno)
                    elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        nested.append(sub.name)
        out["functions"][qualified] = sorted(set(direct))
        if nested:
            out["nested"].setdefault(qualified, []).extend(nested)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 只从顶层/类层入口进入一次（walk 会重复命中嵌套函数，用 qualified 去重）
            pass
    # 顶层入口：遍历模块体（类方法也算一层）
    def walk_module(body, prefix=""):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit_fn(node, f"{prefix}{node.name}")
            elif isinstance(node, ast.ClassDef):
                walk_module(node.body, f"{prefix}{node.name}.")

    walk_module(tree.body)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="AST return 归属普查（只读；lambda 不收）")
    ap.add_argument("target", help="目标 .py 文件或目录")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    target = Path(a.target)
    files = sorted(target.rglob("*.py")) if target.is_dir() else [target]
    report = {}
    for f in files:
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
            rep = census_source(src)
        except SyntaxError as exc:
            report[str(f)] = {"error": str(exc)}
            continue
        if rep["functions"]:
            report[str(f)] = rep
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        for f, rep in report.items():
            if "error" in rep:
                print(f"{f}: 解析失败 {rep['error']}")
                continue
            total = sum(len(v) for v in rep["functions"].values())
            print(f"{f}: 函数 {len(rep['functions'])} 个，直接 return {total} 处")
            for fn, lns in rep["functions"].items():
                print(f"  {fn}: {lns}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
