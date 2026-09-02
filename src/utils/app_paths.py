"""应用持久化路径的单一配置入口。

默认值保持历史布局不变；测试、便携部署或受管环境可通过环境变量重定向，
从而让 Streamlit/Playwright 子进程也不会接触真实用户数据。
"""

from __future__ import annotations

import os
from pathlib import Path


def _configured_path(env_name: str, default: Path) -> Path:
    value = os.environ.get(env_name, "").strip()
    return Path(value).expanduser() if value else default


APP_HOME = _configured_path("PSY_ANALYSIS_HOME", Path.home() / ".psy_analysis")
PROJECTS_DIR = APP_HOME / "projects"
PREFS_FILE = APP_HOME / "user_prefs.json"
LEGACY_AUTOSAVE_FILE = APP_HOME / "autosave.json"
LEGACY_META_FILE = APP_HOME / "autosave_meta.json"

# 这两项历史上位于仓库/当前工作目录，默认值不可改变；仅允许显式重定向。
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent
ARCHIVE_ROOT = _configured_path("PSY_ANALYSIS_ARCHIVE_DIR", REPOSITORY_ROOT / "archive")
LOG_DIR = _configured_path("PSY_ANALYSIS_LOG_DIR", Path("logs"))
