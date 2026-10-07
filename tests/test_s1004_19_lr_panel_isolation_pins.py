# -*- coding: utf-8 -*-
"""s1004-19：文献面板外部调用面 P0/P1 结构钉（s930-42 普查翻面依据同笔落地）。

翻面语义：s930-42 时代「主入口 try≤1」钉的是『重算段唯一 try』现状；P0（ingest 包
try）＋P1（四 tab 前三 tab 各自隔离）落地后，钉面翻转为**正向隔离钉**——
每风险点必须在**自己的渲染区**内被 try 包住（AST 判据，见各用例）。
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "ui" / "literature_review_panel.py"


def _tree() -> ast.Module:
    return ast.parse(SRC.read_text(encoding="utf-8"))


def _fn(tree: ast.Module, name: str) -> ast.FunctionDef:
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


def _contains_try_calling(fn: ast.FunctionDef, callee: str) -> bool:
    """fn 子树内存在 Try，其 body 里调用名为 callee 的函数。"""
    for node in ast.walk(fn):
        if not isinstance(node, ast.Try):
            continue
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                f = stmt.func
                if (isinstance(f, ast.Name) and f.id == callee) or (
                    isinstance(f, ast.Attribute) and f.attr == callee
                ):
                    return True
    return False


def test_p0_ingest_wrapped_in_try_with_error():
    """P0：ingest_files 调用点必须被 try 包住（render 嵌套函数面内）。"""
    tree = _tree()
    fn = _fn(tree, "_render_drop_and_review_section")
    assert _contains_try_calling(fn, "ingest_files"), "P0 钉：ingest_files 必须在 try 内"
    assert "文献解析失败" in SRC.read_text(encoding="utf-8"), "P0 降级文案在册"


def test_p1_three_tabs_individually_isolated():
    """P1：themes/gaps/export 三 tab 渲染器调用必须各自在 try 内。"""
    tree = _tree()
    fn = _fn(tree, "render_literature_review")
    for callee in ("_render_themes_tab", "_render_gaps_tab", "_render_export_tab"):
        assert _contains_try_calling(fn, callee), f"P1 钉：{callee} 必须在 try 内"
    text = SRC.read_text(encoding="utf-8")
    assert text.count("渲染失败，已保留原有数据") >= 3, "P1 三 tab 降级文案在册"


def test_finish_tab_not_double_wrapped():
    """:4 finish tab 无外部调用面，保持裸调（钉住不过度隔离）。"""
    tree = _tree()
    fn = _fn(tree, "render_literature_review")
    assert not _contains_try_calling(fn, "_render_finish_tab"), "finish tab 不应包 try"
