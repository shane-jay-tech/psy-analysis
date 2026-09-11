"""自动保存（v3.1 改造）— 每次关键操作后把工作区写到当前活跃项目。

v3.1 行为变化：
- 不再写 ~/.psy_analysis/autosave.json（旧路径由 ensure_active_project_on_first_visit 一次性迁移）
- 改为写 project_manager.save_workspace(active_id, workspace)
- 节流逻辑保留（30s 内同 session 不重复写）
- render_restore_prompt 仍保留向后兼容（如检测到旧 autosave 会显示），但 ensure_active_project_on_first_visit 应已自动迁移

调用方式不变（trigger_autosave）；语义从「保存到全局 autosave」变为「保存到当前项目」。
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.app_paths import LEGACY_AUTOSAVE_FILE, LEGACY_META_FILE

logger = logging.getLogger(__name__)


# 旧 v3.0 路径（保留只做一次性迁移检测）
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
SESSION_LAST_PROJECT_KEY = "_autosave_last_project_id"
SESSION_LAST_ERROR_KEY = "_autosave_last_error"
SESSION_LAST_SAVED_LABEL_KEY = "_workspace_last_saved"


# --------------------------------------------------------------------------- #
# 方案B：后台保存（2026-09-11，psy-snapshot-perf-20260911.md §③）
# --------------------------------------------------------------------------- #

# 回滚开关：置 False 全量退回同步保存（设计稿迁移步骤的回滚点）
BACKGROUND_AUTOSAVE_ENABLED = True


class FakeSessionState:
    """非 dict 会话态包装（测试/脚本用）。

    trigger_autosave 以「非 dict ⇒ Streamlit 运行时」判定是否走后台路径，
    本类让脚本环境也能显式走后台分支。
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._data = dict(data or {})

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def pop(self, key, *args):
        return self._data.pop(key, *args)

    def keys(self):
        return self._data.keys()


def _capture_refs(session_state: Any) -> Optional[Dict[str, Any]]:
    """主线程引用级捕获全部键值（零序列化、零深拷贝）。

    大对象（df 等）按 Streamlit 惯例「整体替换、不就地改」；捕获失败返回 None，
    调用方落回同步路径。
    """
    try:
        return {k: session_state[k] for k in list(session_state.keys())}
    except Exception:
        logger.debug("autosave: 引用捕获失败，回退同步保存", exc_info=True)
        return None


def _drain_background_result(session_state: Any) -> None:
    """把已完成的后台结果结转进 session_state（必须只在主线程调用）。"""
    try:
        from src.utils import autosave_bg
    except Exception:
        return
    res = autosave_bg.drain_result()
    if res is None:
        return
    if res.get("ok"):
        session_state[SESSION_LAST_SAVED_LABEL_KEY] = datetime.now().strftime("%Y-%m-%d %H:%M")
        session_state.pop(SESSION_LAST_ERROR_KEY, None)
    elif res.get("error"):
        session_state[SESSION_LAST_ERROR_KEY] = res["error"]


def flush_background(timeout: float = 10.0):
    """等待后台保存队列清空（退出钩子/测试/脚本用）。返回 (是否完成, 末次 worker 毫秒)。"""
    try:
        from src.utils import autosave_bg
        return autosave_bg.flush(timeout)
    except Exception:
        return True, 0.0


atexit.register(flush_background, 5.0)


def trigger_autosave(session_state: Any, workspace_builder, *, force: bool = False):
    """v3.6: 把工作区保存到当前活跃项目。

    方案B（2026-09-11）：Streamlit 运行时（非 dict 会话态）走后台队列 ——
    主线程只做引用级捕获（零序列化）后立即返回 True（受理）；序列化+落盘在
    autosave_bg worker 完成，保存标签/错误键在后续 trigger 调用时结转。
    dict 会话态（测试/脚本）保持原同步语义：返回时已落盘。
    回滚：BACKGROUND_AUTOSAVE_ENABLED = False。

    Args:
        session_state: streamlit session_state
        workspace_builder: 0 参函数，返回 workspace dict
        force: 跳过节流

    Returns:
        是否实际保存（同步路径）/ 是否受理（后台路径）
    """
    # 后台路径先结转上一次的后台结果（主线程 atomic swap，即使本轮节流跳过也反馈）
    if BACKGROUND_AUTOSAVE_ENABLED and not isinstance(session_state, dict):
        _drain_background_result(session_state)

    # 拿当前活跃项目
    try:
        from src.utils import project_manager as pm
        active_id = pm.get_active_project_id(session_state)
        if active_id is None:
            session_state[SESSION_LAST_ERROR_KEY] = "没有可保存的当前项目"
            return False  # 还没有项目，跳过
    except Exception:
        logger.debug("autosave: 获取当前项目失败", exc_info=True)
        session_state[SESSION_LAST_ERROR_KEY] = "自动保存准备失败，请手动导出项目快照"
        return False

    last = session_state.get(SESSION_LAST_SAVE_KEY)
    last_project_id = session_state.get(SESSION_LAST_PROJECT_KEY)
    now = time.time()
    if (
        not force
        and last is not None
        and last_project_id == active_id
        and now - last < DEFAULT_THROTTLE_SECONDS
    ):
        return False  # 同一项目仍在节流冷却中

    # 方案B 主路径：引用捕获 → 后台队列（捕获失败才落回同步）
    if BACKGROUND_AUTOSAVE_ENABLED and not isinstance(session_state, dict):
        try:
            from src.utils import autosave_bg
        except Exception:
            logger.debug("autosave: autosave_bg 导入失败，回退同步", exc_info=True)
            autosave_bg = None
        if autosave_bg is not None:
            refs = _capture_refs(session_state)
            if refs is not None:
                autosave_bg.submit(active_id, refs)
                session_state[SESSION_LAST_SAVE_KEY] = now
                session_state[SESSION_LAST_PROJECT_KEY] = active_id
                return True  # 已受理；落盘结果由后续调用的 _drain_background_result 结转

    try:
        ws = workspace_builder()
    except Exception:
        logger.debug("autosave: workspace 构建失败", exc_info=True)
        session_state[SESSION_LAST_ERROR_KEY] = "自动保存准备失败，请手动导出项目快照"
        return False

    try:
        from src.utils import project_manager as pm
        ok = pm.save_workspace(active_id, ws)
        if ok:
            session_state[SESSION_LAST_SAVE_KEY] = now
            session_state[SESSION_LAST_PROJECT_KEY] = active_id
            session_state[SESSION_LAST_SAVED_LABEL_KEY] = datetime.now().strftime(
                "%Y-%m-%d %H:%M"
            )
            session_state.pop(SESSION_LAST_ERROR_KEY, None)
        else:
            session_state[SESSION_LAST_ERROR_KEY] = "自动保存写入失败，请检查磁盘空间或导出快照"
        return ok
    except Exception:
        logger.debug("autosave: 保存到项目失败", exc_info=True)
        session_state[SESSION_LAST_ERROR_KEY] = "自动保存写入失败，请检查磁盘空间或导出快照"
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
