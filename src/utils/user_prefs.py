"""用户偏好持久化（v3.7）。

解决问题：streamlit session_state 关浏览器就丢，导致隐私声明 / 新手指引每次启动都弹。
存储位置：~/.psy_analysis/user_prefs.json

字段：
- privacy_accepted: bool        — 是否已阅读隐私声明
- onboarding_completed: bool    — 是否已完成新手引导
- funnel_intro_shown: bool      — 是否看过漏斗用户契约
- _quality_preview_dismissed: bool — 是否关闭过反问质量预览
- last_provider, last_model     — 上次用的 LLM 配置（便于跨会话恢复）
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict

from src.utils.app_paths import APP_HOME, PREFS_FILE


PREFS_DIR = APP_HOME
_PREFS_LOCK = threading.RLock()


# 这些字段从 session_state 持久化到文件
PERSISTED_KEYS = {
    "privacy_accepted",
    "onboarding_completed",
    "funnel_intro_shown",
    "_quality_preview_dismissed",
    "_onboarding_skipped",
    "language",
    "output_language",
}

# v3.7: 联网获取的模型列表（按 provider 分别持久化）
RUNTIME_MODEL_KEYS = {
    "_runtime_models_deepseek",
    "_runtime_models_openai",
    "_runtime_models_zhipu",
    "_runtime_models_moonshot",
    "_runtime_models_claude",
    "_runtime_models_ollama",
    "_runtime_models_custom",
}

def _ensure_dir() -> None:
    PREFS_DIR.mkdir(parents=True, exist_ok=True)


def load_prefs() -> Dict[str, Any]:
    """读取本地偏好；不存在或损坏返回空 dict。"""
    with _PREFS_LOCK:
        if not PREFS_FILE.exists():
            return {}
        try:
            return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}


def save_prefs(prefs: Dict[str, Any]) -> bool:
    """原子写入本地偏好文件，失败时保留上一份有效内容。"""
    with _PREFS_LOCK:
        temp_path: Path | None = None
        try:
            _ensure_dir()
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=PREFS_DIR,
                prefix=".user_prefs.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(prefs, temp_file, ensure_ascii=False, indent=2)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, PREFS_FILE)
            return True
        except (OSError, TypeError, ValueError):
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            return False


def update_pref(key: str, value: Any) -> bool:
    """更新单个偏好（读 → 改 → 写）。"""
    with _PREFS_LOCK:
        prefs = load_prefs()
        prefs[key] = value
        return save_prefs(prefs)


def apply_to_session(session_state: Any) -> None:
    """启动时把用户真实保存过的偏好恢复到 session_state。

    偏好文件不存在时不写入任何默认值，确保全新用户能看到一次新手引导。
    """
    prefs = load_prefs()
    if not prefs:
        return

    # 已有 prefs：只恢复白名单字段，未知字段不进入 session_state。
    for key in PERSISTED_KEYS:
        if key in prefs:
            session_state[key] = prefs[key]
    # v3.7: 联网获取的模型列表也恢复
    for key in RUNTIME_MODEL_KEYS:
        if key in prefs:
            session_state[key] = prefs[key]


def sync_from_session(session_state: Any) -> bool:
    """同步 session_state 中的持久字段到本地文件。"""
    with _PREFS_LOCK:
        current = load_prefs()
        changed = False
        for key in PERSISTED_KEYS | RUNTIME_MODEL_KEYS:
            new_val = session_state.get(key) if hasattr(session_state, "get") else None
            if new_val is None:
                continue
            if current.get(key) != new_val:
                current[key] = new_val
                changed = True
        if changed:
            return save_prefs(current)
        return True


def update_runtime_models(provider: str, models: list) -> bool:
    """v3.7: 持久化联网获取的模型列表（按 provider 分别存）。"""
    if not provider or not models:
        return False
    key = f"_runtime_models_{provider}"
    return update_pref(key, list(models))


def reset_prefs() -> bool:
    """清空本地偏好（用户手动重置时调用）。"""
    with _PREFS_LOCK:
        try:
            if PREFS_FILE.exists():
                PREFS_FILE.unlink()
            return True
        except OSError:
            return False
