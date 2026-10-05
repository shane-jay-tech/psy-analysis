# -*- coding: utf-8 -*-
"""s1002-16：project_panel 三处静默 except 改锁定横幅的行为断言（s924-62 遗留 1 施工）。

三处（现取 :63/:84/:98，均为 restore_workspace 调用点的 try/except Exception: pass）
改为捕获后 st.error 可读横幅（拒载可观测）——非重抛，主流程不炸口径维持。
:42 的 save 面静默不属矿源三处指认，未动。

变异刀：把三处 except 体临时换回 pass（源码字符串替换＋AppTest 重跑）⇒ 横幅断言转红。
脚本形态照抄兄弟件 test_project_panel_ui.py 的 _PREAMBLE/AppTest 模板（真渲染路径、
隔离由 conftest autouse 供给——本文件名已在 _APP_TEST_FILES 白名单）。
"""
from __future__ import annotations

import json
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

from src.utils import project_manager as pm

_ROOT = pathlib.Path(__file__).resolve().parents[1].as_posix()
PANEL_SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "ui" / "project_panel.py"

_PREAMBLE = """
import sys
if "__ROOT__" not in sys.path:
    sys.path.insert(0, "__ROOT__")
import streamlit as st
from src.utils import instance_lock, project_manager as pm
""".replace("__ROOT__", _ROOT)

# 首访路径：无活跃项目 ⇒ 走 ensure_active_project_on_first_visit 的恢复分支
_ENSURE = _PREAMBLE + """
from src.ui.project_panel import ensure_active_project_on_first_visit
ensure_active_project_on_first_visit()
"""

_BROKEN_WS = {"version": 999, "schema": "definitely-not-a-known-shape",
              "df": {"__broken__": True}}


def _seed_broken_workspace(monkeypatch, tmp_path, which: str):
    """造一个「恢复必炸」的工作区快照：load_workspace 返回坏形状、restore 必抛。"""
    orig_load = pm.load_workspace

    def broken_load(sid):
        if sid == which:
            return dict(_BROKEN_WS)
        return orig_load(sid)

    def broken_restore(ws):
        raise ValueError("人造恢复失败（s1002-16 桩）")

    monkeypatch.setattr(pm, "load_workspace", broken_load)
    from src.utils import workspace as wsmod
    monkeypatch.setattr(wsmod, "restore_workspace", broken_restore)


def _run_script(monkeypatch, script: str) -> AppTest:
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    return at


def _errors(at: AppTest) -> list[str]:
    return [str(e.value) for e in at.error]


# ---------- 三分支行为断言 ----------

def test_migrated_branch_restore_failure_shows_banner(monkeypatch, tmp_path):
    _seed_broken_workspace(monkeypatch, tmp_path, "__MIGRATED__")
    # migrate_legacy_autosave 返回一个假迁移项目
    fake_proj = SimpleNamespace(id="__MIGRATED__") if False else type(
        "P", (), {"id": "__MIGRATED__"})()
    monkeypatch.setattr(pm, "migrate_legacy_autosave", lambda: fake_proj)
    at = _run_script(monkeypatch, _ENSURE)
    assert not at.exception, f"主流程炸了（非重抛口径被破坏）：{[e.value for e in at.exception]}"
    assert any("旧版 autosave 迁移" in e and "ValueError" in e for e in _errors(at)), \
        f"迁移支横幅未出现：{_errors(at)}"


def test_recent_project_branch_restore_failure_shows_banner(monkeypatch, tmp_path):
    _seed_broken_workspace(monkeypatch, tmp_path, "__RECENT__")
    fake_proj = type("P", (), {"id": "__RECENT__"})()
    monkeypatch.setattr(pm, "migrate_legacy_autosave", lambda: None)
    monkeypatch.setattr(pm, "list_projects", lambda: [fake_proj])
    at = _run_script(monkeypatch, _ENSURE)
    assert not at.exception
    assert any("最近项目工作区恢复失败" in e and "ValueError" in e for e in _errors(at)), \
        f"最近项目支横幅未出现：{_errors(at)}"


def test_switch_branch_restore_failure_shows_banner(monkeypatch, tmp_path):
    _seed_broken_workspace(monkeypatch, tmp_path, "__TARGET__")
    monkeypatch.setattr(pm, "migrate_legacy_autosave", lambda: None)
    monkeypatch.setattr(pm, "list_projects", lambda: [])
    script = _PREAMBLE + """
from src.ui.project_panel import _save_active_then_load
_save_active_then_load("__TARGET__")
"""
    at = _run_script(monkeypatch, script)
    assert not at.exception
    assert any("项目工作区恢复失败" in e and "ValueError" in e for e in _errors(at)), \
        f"切换支横幅未出现：{_errors(at)}"


# ---------- 变异刀：还原为 pass ⇒ 横幅断言转红 ----------

def test_mutation_revert_to_pass_turns_banner_assertions_red(monkeypatch, tmp_path):
    """把三处横幅 except 体压回「except Exception: pass」（行级替换，f-string 免疫正则），
    落临时模块执行同一场景 ⇒ 横幅不得出现（出现＝断言无判别力）。"""
    import re as _re

    src_lines = PANEL_SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    out = []
    i = 0
    mutated_hits = 0
    while i < len(src_lines):
        line = src_lines[i]
        if "except Exception as e:" in line and i + 1 < len(src_lines) and "s1002-16" in src_lines[i + 1]:
            indent = line[: len(line) - len(line.lstrip())]
            # 跳过注释行与 st.error 行，压成 pass
            j = i + 1
            while j < len(src_lines) and ("#" in src_lines[j] or "st.error" in src_lines[j]):
                j += 1
            out.append(indent + "except Exception:" + "\n")
            out.append(indent + "    pass" + "\n")
            mutated_hits += 1
            i = j
            continue
        out.append(line)
        i += 1
    mutated = "".join(out)
    assert mutated_hits == 3, f"变异只命中 {mutated_hits}/3 处——行级替换需复检"
    assert mutated != PANEL_SRC.read_text(encoding="utf-8")

    tmp_src = PANEL_SRC.with_name("project_panel_MUTATED_tmp.py")
    mutated_script = _PREAMBLE + """
import importlib.util, sys
spec = importlib.util.spec_from_file_location("pp_mut", r"__MUT__")
pp_mut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp_mut)
pp_mut.ensure_active_project_on_first_visit()
""".replace("__MUT__", tmp_src.as_posix())

    tmp_src.write_text(mutated, encoding="utf-8")
    try:
        fake_proj = type("P", (), {"id": "__RECENT__"})()
        monkeypatch.setattr(pm, "migrate_legacy_autosave", lambda: None)
        monkeypatch.setattr(pm, "list_projects", lambda: [fake_proj])

        def broken_restore(ws):
            raise ValueError("人造恢复失败（s1002-16 桩）")

        from src.utils import workspace as wsmod
        monkeypatch.setattr(wsmod, "restore_workspace", broken_restore)
        orig_load = pm.load_workspace

        def broken_load(sid):
            if sid == "__RECENT__":
                return dict(_BROKEN_WS)
            return orig_load(sid)

        monkeypatch.setattr(pm, "load_workspace", broken_load)
        at = _run_script(monkeypatch, mutated_script)
        assert not [e for e in _errors(at) if "恢复失败" in e], (
            "变异体（还原 pass）下横幅仍出现——断言无判别力")
    finally:
        if tmp_src.exists():
            tmp_src.unlink()


from types import SimpleNamespace  # noqa: E402  （test_migrated 分支用）
