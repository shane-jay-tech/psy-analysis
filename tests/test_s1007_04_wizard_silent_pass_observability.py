# -*- coding: utf-8 -*-
"""s1007-04：undergrad_wizard 两支 except-pass 静默点补观测结构钉（s1002-19 同款形态）。

两支点位（render_undergrad_wizard 内）：断点位置记录（update_last_position 包裹段）
与亮点提示渲染（render_post_demo_highlight 包裹段）。钉语义＝handler 必须携带
logger.warning（可观测输出在册）且不再有裸 pass（防回退）。
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "ui" / "undergrad_wizard.py"


def _handlers_by_callee(callee: str) -> list[ast.ExceptHandler]:
    """返回「try 体调用 callee」的 try 块所挂的 except handler。"""
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        calls_callee = any(
            isinstance(call, ast.Call)
            and (
                (isinstance(call.func, ast.Name) and call.func.id == callee)
                or (isinstance(call.func, ast.Attribute) and call.func.attr == callee)
            )
            for stmt in node.body
            for call in ast.walk(stmt)
        )
        if calls_callee:
            out.extend(node.handlers)
    return out


def _has_logger_warning(handler: ast.ExceptHandler) -> bool:
    for stmt in handler.body:
        for call in ast.walk(stmt):
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
                if call.func.attr == "warning":
                    return True
    return False


def _has_bare_pass(handler: ast.ExceptHandler) -> bool:
    return any(isinstance(stmt, ast.Pass) for stmt in handler.body)


def test_position_recorder_handler_now_logs():
    """断点位置记录段的 except 必须有 logger.warning 且无裸 pass。"""
    handlers = _handlers_by_callee("update_last_position")
    assert handlers, "未找到 update_last_position 的包裹 try"
    for h in handlers:
        assert _has_logger_warning(h), "断点记录 handler 缺 logger.warning（s1007-04 钉）"
        assert not _has_bare_pass(h), "断点记录 handler 回退成裸 pass（禁止回归）"


def test_post_demo_highlight_handler_now_logs():
    """亮点提示渲染段的 except 必须有 logger.warning 且无裸 pass。"""
    handlers = _handlers_by_callee("render_post_demo_highlight")
    assert handlers, "未找到 render_post_demo_highlight 的包裹 try"
    for h in handlers:
        assert _has_logger_warning(h), "亮点提示 handler 缺 logger.warning（s1007-04 钉）"
        assert not _has_bare_pass(h), "亮点提示 handler 回退成裸 pass（禁止回归）"
