"""多研究项目管理 — 把"当前 workspace"扩展为多个独立项目。

存储布局：
~/.psy_analysis/
├── projects/
│   ├── index.json              # 所有项目元信息（名称、时间戳、文件名）
│   ├── <project_id>.json       # 项目工作区（沿用 workspace 格式 + tutor 对话）
│   └── ...
└── autosave.json               # 旧 v3.0 路径（v3.1 启动时一次性迁移）

设计原则：
- 项目 ID 用 UUID（避免重名冲突），文件名 = ID
- 显示用 "name"（用户可改）
- 每次切换项目 = 把当前 workspace 写到旧项目 + 读新项目到 session_state
- "活跃项目 ID" 存在 session_state 中，autosave 据此决定写哪个文件
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
import uuid
from functools import wraps
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.app_paths import PROJECTS_DIR

logger = logging.getLogger(__name__)


INDEX_FILE = PROJECTS_DIR / "index.json"
_IO_LOCK = threading.RLock()


@dataclass
class Project:
    """单个研究项目的元信息。"""
    id: str
    name: str
    created_at: str
    updated_at: str
    note: str = ""

    @property
    def file_path(self) -> Path:
        return PROJECTS_DIR / f"{self.id}.json"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Project":
        return cls(
            id=d["id"], name=d["name"],
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            note=d.get("note", ""),
        )


# --------------------------------------------------------------------------- #
# 存储工具
# --------------------------------------------------------------------------- #

def _ensure_dir():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _locked(func):
    """串行化同一应用进程内的项目读改写操作。"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with _IO_LOCK:
            return func(*args, **kwargs)
    return wrapper


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _atomic_write_json(path: Path, payload: Any, *, indent: int | None = None) -> None:
    """在目标目录写临时文件后原子替换，避免中断写盘损坏原项目。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(payload, temp_file, ensure_ascii=False, default=str, indent=indent)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    except Exception:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _recover_index_from_workspaces() -> List[Project]:
    """从仍在磁盘上的工作区重建最小索引，绝不删除原项目文件。"""
    recovered: List[Project] = []
    if not PROJECTS_DIR.exists():
        return recovered
    for workspace_file in sorted(PROJECTS_DIR.glob("*.json")):
        if workspace_file == INDEX_FILE:
            continue
        try:
            modified = datetime.fromtimestamp(workspace_file.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except OSError:
            modified = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        recovered.append(Project(
            id=workspace_file.stem,
            name=f"恢复的项目 {workspace_file.stem}",
            created_at=modified,
            updated_at=modified,
            note="从损坏的项目索引自动恢复；请核对并重命名",
        ))
    return recovered


def _read_index() -> List[Project]:
    with _IO_LOCK:
        if not INDEX_FILE.exists():
            return []
        try:
            with open(INDEX_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("项目索引根节点不是列表")
            return [Project.from_dict(d) for d in data if isinstance(d, dict)]
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            # 先隔离损坏索引，再从 workspace 文件重建；隔离失败就抛出，
            # 防止后续 create_project 把唯一的损坏证据覆盖掉。
            backup = INDEX_FILE.with_name(
                f"index.corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S')}.{uuid.uuid4().hex[:6]}.bak"
            )
            os.replace(INDEX_FILE, backup)
            recovered = _recover_index_from_workspaces()
            _write_index(recovered)
            logger.error(
                "项目索引损坏，已隔离到 %s 并恢复 %d 个工作区",
                backup,
                len(recovered),
                exc_info=True,
            )
            return recovered


def _write_index(projects: List[Project]):
    _ensure_dir()
    _atomic_write_json(INDEX_FILE, [p.to_dict() for p in projects], indent=2)


# --------------------------------------------------------------------------- #
# 公共 API
# --------------------------------------------------------------------------- #

def list_projects() -> List[Project]:
    """返回所有项目，按 updated_at 倒序（最近访问的在前）。"""
    projects = _read_index()
    projects.sort(key=lambda p: p.updated_at, reverse=True)
    return projects


def get_project(project_id: str) -> Optional[Project]:
    for p in _read_index():
        if p.id == project_id:
            return p
    return None


@_locked
def create_project(name: str, *, note: str = "") -> Project:
    """新建空项目，返回 Project。同名允许（用 ID 区分）。"""
    if not name.strip():
        name = "未命名项目"
    _ensure_dir()
    now = _now_str()
    proj = Project(
        id=_new_id(), name=name.strip(),
        created_at=now, updated_at=now, note=note,
    )
    projects = _read_index()
    projects.append(proj)
    _write_index(projects)
    # 创建空工作区文件
    save_workspace(proj.id, {"_schema": "v2.9", "_version": "2.9", "_saved_at": now})
    return proj


@_locked
def rename_project(project_id: str, new_name: str) -> bool:
    """重命名。返回是否成功。"""
    new_name = new_name.strip()
    if not new_name:
        return False
    projects = _read_index()
    for p in projects:
        if p.id == project_id:
            p.name = new_name
            p.updated_at = _now_str()
            _write_index(projects)
            return True
    return False


@_locked
def update_note(project_id: str, note: str) -> bool:
    projects = _read_index()
    for p in projects:
        if p.id == project_id:
            p.note = note
            p.updated_at = _now_str()
            _write_index(projects)
            return True
    return False


@_locked
def delete_project(project_id: str) -> bool:
    """删除项目（含工作区文件）。"""
    projects = _read_index()
    target = next((p for p in projects if p.id == project_id), None)
    if target is None:
        return False
    if target.file_path.exists():
        try:
            target.file_path.unlink()
        except Exception:
            logger.debug("project_manager: 操作失败", exc_info=True)
            pass
    projects = [p for p in projects if p.id != project_id]
    _write_index(projects)
    return True


@_locked
def copy_project(project_id: str, new_name: Optional[str] = None) -> Optional[Project]:
    """复制一个项目（含工作区数据），返回新项目。"""
    src = get_project(project_id)
    if src is None:
        return None
    new_name = (new_name or f"{src.name} (副本)").strip()
    new_proj = create_project(new_name, note=src.note)
    # 复制工作区文件
    if src.file_path.exists():
        shutil.copy2(src.file_path, new_proj.file_path)
    return new_proj


@_locked
def touch_project(project_id: str) -> bool:
    """更新 updated_at 时间戳（项目被切换访问时调用）。"""
    projects = _read_index()
    for p in projects:
        if p.id == project_id:
            p.updated_at = _now_str()
            _write_index(projects)
            return True
    return False


# --------------------------------------------------------------------------- #
# 工作区 IO（每个项目一个文件）
# --------------------------------------------------------------------------- #

@_locked
def save_workspace(project_id: str, workspace: Dict[str, Any]) -> bool:
    proj = get_project(project_id)
    if proj is None:
        return False
    _ensure_dir()
    try:
        _atomic_write_json(proj.file_path, workspace)
        touch_project(project_id)
        return True
    except Exception:
        logger.debug("project_manager: 操作失败", exc_info=True)
        return False


def load_workspace(project_id: str) -> Optional[Dict[str, Any]]:
    proj = get_project(project_id)
    if proj is None or not proj.file_path.exists():
        return None
    try:
        with open(proj.file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.debug("project_manager: 操作失败", exc_info=True)
        return None


# --------------------------------------------------------------------------- #
# v3.0 → v3.1 迁移：把旧 ~/.psy_analysis/autosave.json 转为「未命名项目」
# --------------------------------------------------------------------------- #

def migrate_legacy_autosave() -> Optional[Project]:
    """把 v3.0 的 autosave.json 一次性迁移为新项目，返回新建的项目。

    幂等：迁移成功后删除旧文件；旧文件不存在时返回 None。
    """
    # 跟随 PROJECTS_DIR，便于测试/便携部署把全部持久化重定向到隔离目录。
    legacy_file = PROJECTS_DIR.parent / "autosave.json"
    if not legacy_file.exists():
        return None
    try:
        with open(legacy_file, encoding="utf-8") as f:
            ws = json.load(f)
    except Exception:
        logger.debug("project_manager: 操作失败", exc_info=True)
        return None

    proj = create_project(name="自动恢复的工作区", note="从 v3.0 autosave 迁移")
    save_workspace(proj.id, ws)

    # 清理旧文件
    try:
        legacy_file.unlink()
        legacy_meta = PROJECTS_DIR.parent / "autosave_meta.json"
        if legacy_meta.exists():
            legacy_meta.unlink()
    except Exception:
        pass
    return proj


# --------------------------------------------------------------------------- #
# Streamlit session_state 集成
# --------------------------------------------------------------------------- #

ACTIVE_PROJECT_KEY = "_active_project_id"


def get_active_project_id(session_state: Any) -> Optional[str]:
    return session_state.get(ACTIVE_PROJECT_KEY)


def set_active_project(session_state: Any, project_id: str):
    session_state[ACTIVE_PROJECT_KEY] = project_id
    touch_project(project_id)


def get_active_project(session_state: Any) -> Optional[Project]:
    pid = get_active_project_id(session_state)
    return get_project(pid) if pid else None
