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
from pathlib import Path
from typing import Any, Dict


PREFS_DIR = Path.home() / ".psy_analysis"
PREFS_FILE = PREFS_DIR / "user_prefs.json"


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

# v3.7: 默认值——首次启动时这些被默认设为 True（直接跳过新手引导）
DEFAULT_TRUE_ON_FIRST_RUN = {
    "onboarding_completed",
    "funnel_intro_shown",
    "_quality_preview_dismissed",
    "_onboarding_skipped",
}


def _ensure_dir() -> None:
    PREFS_DIR.mkdir(parents=True, exist_ok=True)


def load_prefs() -> Dict[str, Any]:
    """读取本地偏好；不存在或损坏返回空 dict。"""
    if not PREFS_FILE.exists():
        return {}
    try:
        return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_prefs(prefs: Dict[str, Any]) -> bool:
    """写入本地偏好文件。"""
    try:
        _ensure_dir()
        PREFS_FILE.write_text(
            json.dumps(prefs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def update_pref(key: str, value: Any) -> bool:
    """更新单个偏好（读 → 改 → 写）。"""
    prefs = load_prefs()
    prefs[key] = value
    return save_prefs(prefs)


def apply_to_session(session_state: Any) -> None:
    """启动时调：把本地偏好覆盖到 session_state。

    v3.7：用户明确要求「删除新手引导」，所以**每次启动**都强制把引导类标志置 True
    （不依赖 prefs 文件是否存在 / 旧值是什么）。如未来需要恢复，可加重置按钮。
    """
    prefs = load_prefs()

    # v3.7: 引导类标志强制 True（每次启动都覆盖，无视旧值）
    for key in DEFAULT_TRUE_ON_FIRST_RUN:
        session_state[key] = True

    # 写回文件（保持 prefs 一致）
    if any(prefs.get(k) is not True for k in DEFAULT_TRUE_ON_FIRST_RUN):
        for k in DEFAULT_TRUE_ON_FIRST_RUN:
            prefs[k] = True
        save_prefs(prefs)

    if not prefs:
        return

    # 已有 prefs：恢复其他持久字段（语言/隐私同意/联网模型列表）
    for key in PERSISTED_KEYS:
        if key in prefs and key not in DEFAULT_TRUE_ON_FIRST_RUN:
            session_state[key] = prefs[key]
    # v3.7: 联网获取的模型列表也恢复
    for key in RUNTIME_MODEL_KEYS:
        if key in prefs:
            session_state[key] = prefs[key]


def sync_from_session(session_state: Any) -> bool:
    """同步 session_state 中的持久字段到本地文件。"""
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
    try:
        if PREFS_FILE.exists():
            PREFS_FILE.unlink()
        return True
    except OSError:
        return False
