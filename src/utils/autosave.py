"""自动保存（v3.1 改造）— 每次关键操作后把工作区写到当前活跃项目。

v3.1 行为变化：
- 不再写 ~/.psy_analysis/autosave.json（旧路径由 ensure_active_project_on_first_visit 一次性迁移）
- 改为写 project_manager.save_workspace(active_id, workspace)
- 节流逻辑保留（30s 内同 session 不重复写）
- render_restore_prompt 仍保留向后兼容（如检测到旧 autosave 会显示），但 ensure_active_project_on_first_visit 应已自动迁移

调用方式不变（trigger_autosave）；语义从「保存到全局 autosave」变为「保存到当前项目」。
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# 旧 v3.0 路径（保留只做一次性迁移检测）
LEGACY_AUTOSAVE_FILE = Path.home() / ".psy_analysis" / "autosave.json"
LEGACY_META_FILE = Path.home() / ".psy_analysis" / "autosave_meta.json"

DEFAULT_THROTTLE_SECONDS = 30


@dataclass
class AutosaveStatus:
    exists: bool = False
    saved_at: str = ""
    file_size_kb: float = 0.0
    has_dataframe: bool = False
    has_analysis: bool = False
    has_collection: bool = False


# --------------------------------------------------------------------------- #
# Streamlit 集成
# --------------------------------------------------------------------------- #

SESSION_LAST_SAVE_KEY = "_autosave_last_ts"


def trigger_autosave(session_state: Any, workspace_builder, *, force: bool = False):
    """v3.1: 把工作区保存到当前活跃项目。

    Args:
        session_state: streamlit session_state
        workspace_builder: 0 参函数，返回 workspace dict
        force: 跳过节流

    Returns:
        是否实际保存
    """
    last = session_state.get(SESSION_LAST_SAVE_KEY)
    now = time.time()

    if not force and last is not None:
        if now - last < DEFAULT_THROTTLE_SECONDS:
            return False  # 节流冷却中

    # 拿当前活跃项目
    try:
        from src.utils import project_manager as pm
        active_id = pm.get_active_project_id(session_state)
        if active_id is None:
            return False  # 还没有项目，跳过
        ws = workspace_builder()
    except Exception:
        logger.debug("autosave: workspace 构建失败", exc_info=True)
        return False

    try:
        from src.utils import project_manager as pm
        ok = pm.save_workspace(active_id, ws)
        if ok:
            session_state[SESSION_LAST_SAVE_KEY] = now
        return ok
    except Exception:
        logger.debug("autosave: 保存到项目失败", exc_info=True)
        return False


# --------------------------------------------------------------------------- #
# 旧 v3.0 兼容层（已弃用，仅供迁移检测使用）
# --------------------------------------------------------------------------- #

def has_legacy_autosave() -> bool:
    """v3.0 的 ~/.psy_analysis/autosave.json 是否还存在。

    由 ensure_active_project_on_first_visit() 调用一次性迁移后会被清理。
    """
    return LEGACY_AUTOSAVE_FILE.exists()


def render_restore_prompt(st_module):
    """v3.1: 此函数保留为兼容接口但已无操作。

    迁移逻辑已挪到 project_panel.ensure_active_project_on_first_visit()。
    保留空实现避免破坏 app.py 的现有 import。
    """
    return


# --------------------------------------------------------------------------- #
# 测试辅助
# --------------------------------------------------------------------------- #

def get_active_workspace_status(session_state: Any) -> AutosaveStatus:
    """返回当前活跃项目的元信息（UI 用）。"""
    try:
        from src.utils import project_manager as pm
        active = pm.get_active_project(session_state)
        if active is None or not active.file_path.exists():
            return AutosaveStatus()
        size_kb = active.file_path.stat().st_size / 1024
        ws = pm.load_workspace(active.id) or {}
        return AutosaveStatus(
            exists=True,
            saved_at=active.updated_at,
            file_size_kb=size_kb,
            has_dataframe="df_b64" in ws,
            has_analysis="analysis_output" in ws,
            has_collection=bool(ws.get("figure_collection")),
        )
    except Exception:
        return AutosaveStatus()
