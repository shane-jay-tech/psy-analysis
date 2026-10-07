# -*- coding: utf-8 -*-
"""s1007-07：文献面板外部调用面 P2 残余结构钉（s930-42 普查九点清单收尾）。

P2 两点＝:109 完成度徽章（低概率外部面）＋:131 _materialize_items 解析残余。
钉语义与 s1004-19 P0/P1 同款（正向隔离钉）：每风险点必须在主入口内被 try 包住
＋降级文案在册。与 s1004-19 钉件分文件（该件在途未 commit，零叠改）。
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


def test_p2_completeness_badge_wrapped_in_try():
    """P2 钉①：_render_completeness_badge 必须在主入口 try 内。"""
    tree = _tree()
    fn = _fn(tree, "render_literature_review")
    assert _contains_try_calling(fn, "_render_completeness_badge"), "P2 钉：徽章调用必须在 try 内"
    assert "完成度徽章渲染失败" in SRC.read_text(encoding="utf-8"), "P2 徽章降级文案在册"


def test_p2_materialize_items_wrapped_in_try_with_degradation():
    """P2 钉②：_materialize_items 解析残余必须在 try 内且失败降级空列表。"""
    tree = _tree()
    fn = _fn(tree, "render_literature_review")
    assert _contains_try_calling(fn, "_materialize_items"), "P2 钉：解析调用必须在 try 内"
    text = SRC.read_text(encoding="utf-8")
    assert "文献数据解析失败，已按空列表降级" in text, "P2 解析降级文案在册"
