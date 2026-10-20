# -*- coding: utf-8 -*-
"""s930-07：「两侧收集差=11 且全来自 playwright_e2e」钉桩（s927-27 遗留）。

背景：tests/test_playwright_e2e.py 的 11 例在 .venv 侧解释器下静默不收集
（playwright 依赖只在系统侧装）——两侧不红、只是分母变（s927-27 的静默面）。
本件把「差集恰 11 且全部属于 playwright_e2e」钉成断言：差集变大/变小/
混入非 e2e 件都红，逼收集面变化显性化。

运行：python -m pytest tests/test_interpreter_collect_gap_s93007.py -q
（注意：本件内部起两次 --collect-only 子进程，约 30 秒。）
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"


def _collect(py: str) -> set:
    r = subprocess.run([py, "-m", "pytest", "--collect-only", "-q"],
                       cwd=str(ROOT), capture_output=True, text="utf-8",
                       errors="replace", timeout=300)
    return {ln.strip() for ln in r.stdout.splitlines() if "::" in ln}


def test_collect_gap_is_exactly_11_all_from_playwright_e2e():
    """两侧收集差=11 且全部属于 tests/test_playwright_e2e.py（s927-27 钉）。"""
    sys_py = sys.executable
    if not VENV_PY.exists():
        pytest_skip = True
        import pytest
        pytest.skip(f".venv 解释器不存在：{VENV_PY}")
    if os.path.abspath(sys_py) == os.path.abspath(str(VENV_PY)):
        import pytest
        pytest.skip("系统侧与 .venv 侧是同一解释器，差集恒 0（环境形态变化）")

    venv_side = _collect(str(VENV_PY))
    system_side = _collect(sys_py)

    only_system = system_side - venv_side
    only_venv = venv_side - system_side

    e2e = {x for x in only_system if "test_playwright_e2e.py" in x}
    assert len(only_system) == 11 and e2e == only_system, (
        f"收集差漂移：system−venv = {len(only_system)} 条（期望恰 11 且全为 "
        f"playwright_e2e）。非 e2e 的混入：{sorted(only_system - e2e)[:6]}；"
        f"e2e 缺席：{sorted(only_system - e2e) and ''}{len(e2e)}/11"
    )
    assert not only_venv, (
        f"反向差出现（venv 侧独有 {len(only_venv)} 条）＝另一向静默面：{sorted(only_venv)[:6]}"
    )
