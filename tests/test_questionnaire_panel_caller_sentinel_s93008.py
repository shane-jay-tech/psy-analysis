# -*- coding: utf-8 -*-
"""s930-08：questionnaire_panel 生产调用方哨兵（s927-31 遗留·第三副本风险守卫）。

矿源原案「生产调用方为零」在现盘不成立：app.py:1570 `from src.ui.questionnaire_panel
import classify_questionnaire_sub_mode` 是 s927-25 消双份的**有意接线**（qpanel 补丁
a81291f，合法白名单面）。哨兵按风险实质收窄为两断言：

  S1 接线面：生产码对 questionnaire_panel 的 import 符号 ⊆ {classify_questionnaire_sub_mode}
     ——出现渲染级符号（render_* 等）或新符号 ⇒ 红（第三副本/私接线的信号）；
  S2 副本面：src/ 下（除 panel 自身）不存在与 panel 函数名指纹重合 ≥3 的第二文件
     ——复制粘贴第三副本出现 ⇒ 红。

「差异行数==71」按任务书不钉（避免与在箱 s927-25 面板补丁耦合）。

运行：python -m pytest tests/test_questionnaire_panel_caller_sentinel_s93008.py -q
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "src" / "ui" / "questionnaire_panel.py"
ALLOWED_IMPORTS = {"classify_questionnaire_sub_mode"}


def _iter_prod_py():
    """生产面 = src/ 全部 .py + 根 app.py（排除 panel 自身与 tests）。"""
    yield app_root if (app_root := ROOT / "app.py").exists() else None
    for p in (ROOT / "src").rglob("*.py"):
        if p.resolve() != PANEL.resolve():
            yield p


def test_s1_prod_imports_of_panel_are_whitelisted():
    """S1 接线面：生产码 import 自 questionnaire_panel 的符号 ⊆ 白名单。"""
    offenders = []
    for p in filter(None, _iter_prod_py()):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and \
                    node.module.endswith("questionnaire_panel"):
                names = {a.asname or a.name for a in node.names}
                bad = names - ALLOWED_IMPORTS
                if bad:
                    offenders.append(f"{p.relative_to(ROOT)}: {sorted(bad)}")
    assert not offenders, (
        f"questionnaire_panel 生产接线越出白名单（渲染级接线＝第三副本信号）：{offenders}"
    )


def test_s2_no_second_copy_by_function_fingerprint():
    """S2 副本面：panel 的顶层函数名指纹在其他 src/ 文件重合 ≥3 ⇒ 第三副本。"""
    panel_tree = ast.parse(PANEL.read_text(encoding="utf-8"))
    panel_fns = {n.name for n in panel_tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert len(panel_fns) >= 3, "panel 指纹基准过小，哨兵失真"
    offenders = []
    for p in (ROOT / "src").rglob("*.py"):
        if p.resolve() == PANEL.resolve():
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        fns = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        overlap = fns & panel_fns
        if len(overlap) >= 3:
            offenders.append(f"{p.relative_to(ROOT)}: 重合 {sorted(overlap)[:5]}")
    assert not offenders, f"疑似 questionnaire_panel 第三副本（函数指纹重合≥3）：{offenders}"
