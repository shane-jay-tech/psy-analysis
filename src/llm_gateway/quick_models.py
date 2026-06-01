"""快捷模型预设（v4.3）。

把 D:\\code\\.env.local 中预先配好的 4 组模型（GPT-5.5 / DeepSeek V4 Pro /
Kimi K2.6 / Claude Opus 4.8）封装成统一接口，UI 端只需要一个 selectbox。

设计：
- 启动时读 D:\\code\\.env.local 的 GPT_*/KIMI_*/DEEPSEEK_*/CLAUDE_* 三件套
- 暴露 ``QUICK_MODELS`` 列表 + ``get_quick_model_config(id)`` 工厂
- 返回的 dict 形状与 gateway._resolve_llm_config() 对齐：
  ``{provider, base_url, api_key, model, timeout}``
- 缺失的键不会抛错，只是该模型 ``available=False``，UI 端可灰掉选项。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 4 个固定模型条目
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QuickModel:
    """单个快捷模型条目。"""
    id: str             # "gpt" / "deepseek" / "kimi" / "claude"
    label: str          # UI 显示名
    env_prefix: str     # .env.local 前缀
    provider: str       # 路由到 gateway 的 provider 字段
    description: str    # 用户提示语


QUICK_MODELS: List[QuickModel] = [
    QuickModel(
        id="gpt",
        label="GPT-5.5",
        env_prefix="GPT",
        provider="openai",
        description="主程序员：清楚、温度强制 1.0",
    ),
    QuickModel(
        id="deepseek",
        label="DeepSeek V4 Pro",
        env_prefix="DEEPSEEK",
        provider="deepseek",
        description="评审官：批判性强，推理类，温度默认 0.3",
    ),
    QuickModel(
        id="kimi",
        label="Kimi K2.6",
        env_prefix="KIMI",
        provider="moonshot",
        description="调研员：长文档总结、查文献，温度强制 1.0",
    ),
    QuickModel(
        id="claude",
        label="Claude Opus 4.8",
        env_prefix="CLAUDE",
        provider="claude",
        description="架构师 / 总指挥：综合判断、写作、规划",
    ),
]


# ---------------------------------------------------------------------------
# .env.local 加载
# ---------------------------------------------------------------------------

# 这些模型需要强制 temperature=1（与 D:\\code\\scripts\\llm_call.py 一致）
_FORCED_TEMPERATURE: Dict[str, float] = {
    "gpt": 1.0,
    "kimi": 1.0,
}


def _candidate_env_paths() -> List[Path]:
    """返回 .env.local 的可能位置：父目录 D:/code，再到 psy-analysis 自身。"""
    here = Path(__file__).resolve()
    candidates: List[Path] = []
    for parent in [here.parent, *here.parents]:
        candidates.append(parent / ".env.local")
        if (parent / ".git").exists() or (parent / "CLAUDE.md").exists():
            # 已经到顶层 D:\code 了，再往上不必走
            break
    # 兜底：D:\code\.env.local（写死路径，避免 cwd 异常）
    fallback = Path("D:/code/.env.local")
    if fallback.exists() and fallback not in candidates:
        candidates.append(fallback)
    return candidates


def load_env_local(force: bool = False) -> Dict[str, str]:
    """读 .env.local 三件套到 os.environ（不覆盖已有 env），返回 {key: value} 拷贝。

    Args:
        force: True 时即使 os.environ 已有同名 key 也覆盖。默认 False（与
            llm_call.py 行为一致）。
    """
    out: Dict[str, str] = {}
    for path in _candidate_env_paths():
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            out[key] = value
            if force or key not in os.environ:
                os.environ[key] = value
        break  # 只读首个找到的 .env.local
    return out


# ---------------------------------------------------------------------------
# Quick model 解析
# ---------------------------------------------------------------------------

def get_quick_model_by_id(model_id: str) -> Optional[QuickModel]:
    """按 id 查找。找不到返回 None。"""
    for m in QUICK_MODELS:
        if m.id == model_id:
            return m
    return None


def get_quick_model_config(
    model_id: str,
    *,
    timeout: int = 600,
) -> Optional[Dict[str, Any]]:
    """返回与 gateway._resolve_llm_config 形状一致的 dict；缺关键 env 时返回 None。

    Args:
        model_id: ``"gpt"`` / ``"deepseek"`` / ``"kimi"`` / ``"claude"``
        timeout: 请求超时秒（默认 600，与 llm_call.py 一致；推理模型留足时间）
    """
    qm = get_quick_model_by_id(model_id)
    if qm is None:
        return None

    # 确保 .env.local 已经被读入 os.environ（多次调用幂等）
    load_env_local()

    base_url = os.environ.get(f"{qm.env_prefix}_BASE_URL", "").strip()
    api_key = os.environ.get(f"{qm.env_prefix}_API_KEY", "").strip()
    model = os.environ.get(f"{qm.env_prefix}_MODEL", "").strip()

    if not (base_url and api_key and model):
        return None

    return {
        "provider": qm.provider,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "timeout": timeout,
        "_quick_model_id": model_id,    # 调用方可凭此识别
    }


def get_forced_temperature(model_id: str) -> Optional[float]:
    """部分模型只支持 temperature=1（GPT / Kimi 系列）；返回强制值或 None。"""
    return _FORCED_TEMPERATURE.get(model_id)


def list_available_quick_models() -> List[Dict[str, Any]]:
    """返回 4 个条目，每个含 id/label/description/available 字段（UI 渲染用）。"""
    load_env_local()
    out: List[Dict[str, Any]] = []
    for qm in QUICK_MODELS:
        cfg = get_quick_model_config(qm.id)
        out.append({
            "id": qm.id,
            "label": qm.label,
            "description": qm.description,
            "model": cfg["model"] if cfg else "",
            "available": cfg is not None,
        })
    return out
