# -*- coding: utf-8 -*-
"""s927-59：app.py 路由链必须带兜底 else（链外 mode 回默认页），AST 哨兵。

背景（s924-20 遗留）：路由链 if/elif 七支曾无兜底——PAGE_MODES 与路由分支漂移
（新页挂进 radio 但没接分支）时整树静默空白。本哨兵用 AST 钉住「链存在＋末支
orelse 非空＋orelse 会 rerun 回默认页」三件事，防漂移复发。
"""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"


def _route_chain_root():
    """返回路由链首节点（test 为 mode == "📈 数据分析" 的顶层 If）。"""
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.If) and _compares_mode_to(node.test, "📈 数据分析"):
            return node
    raise AssertionError("路由链首支（mode == '📈 数据分析'）未找到——链被挪走/改名？")


def _compares_mode_to(test, page: str) -> bool:
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "mode"
        and any(isinstance(c, ast.Constant) and c.value == page for c in test.comparators)
    )


def _chain_last(node):
    """沿 if/elif 链走到末支（orelse 为空或不是同型 If 的那支）。"""
    seen = 1
    while len(node.orelse) == 1 and _is_mode_compare(node.orelse[0]):
        node = node.orelse[0]
        seen += 1
    return node, seen


def _is_mode_compare(node) -> bool:
    return (
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "mode"
    )


def test_route_chain_exists_with_seven_branches():
    root = _route_chain_root()
    last, n = _chain_last(root)
    assert n == 7, f"路由支数漂移：现 {n}（增页忘接分支或删页未清分支都算漂移）"


def test_route_chain_has_fallback_else_with_rerun():
    root = _route_chain_root()
    last, _ = _chain_last(root)
    assert last.orelse, "路由链无兜底 else——链外 mode 会静默空白（s924-20 事故形态回归）"
    src = APP.read_text(encoding="utf-8")
    seg = "\n".join(
        ast.get_source_segment(src, stmt) or "" for stmt in last.orelse
    )
    assert "st.rerun" in seg, "兜底分支必须 st.rerun() 回默认页"
    assert "数据分析" in seg, "兜底分支必须落回默认页（📈 数据分析）"
