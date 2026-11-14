# -*- coding: utf-8 -*-
"""Chromium 系浏览器探测（轻量件：仅 os/pathlib，零重型依赖）。

s1004-32（0e66 遗留）：kaleido 真渲染还要浏览器运行时，探测契约须覆盖到这一层。
原逻辑在 ``src/visualization/paper_export.py::_find_local_chromium``（顶部 import plotly，
env_check 不能拉）⇒ 抽到本轻量件供两处复用：paper_export（渲染路径）与 env_check（体检）。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def find_local_chromium() -> Optional[Path]:
    """寻找 Kaleido 可用的浏览器，优先 Chrome 与 Playwright Chromium。"""
    configured = os.environ.get("BROWSER_PATH")
    if configured:
        configured_path = Path(configured)
        if configured_path.is_file():
            return configured_path

    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    # s1114：Playwright 浏览器根有两形态——默认 LOCALAPPDATA\ms-playwright 与
    # PLAYWRIGHT_BROWSERS_PATH 自定义根（如 D:\ms-playwright）。只认默认根时，
    # 自定义根环境下探测返回 None ⇒ kaleido 有包无浏览器运行时（导出族 10F 根因，
    # s1004-32「探测契约须覆盖浏览器运行时层」的覆盖缺口）。
    playwright_roots = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        playwright_roots.append(Path(local_app_data) / "ms-playwright")
    custom_root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if custom_root:
        playwright_roots.append(Path(custom_root))
    for playwright_root in playwright_roots:
        if playwright_root.is_dir():
            candidates.extend(
                sorted(
                    playwright_root.glob("chromium-*/chrome-win*/chrome.exe"),
                    reverse=True,
                )
            )
    return next((path for path in candidates if path.is_file()), None)
