"""LLM 月预算 + 摘要 hash 缓存。

用户 2026-05-28 拍：月预算 **$10**，"完全不担心"。
但仍要熔断：80% 弹警告，100% 阻断"非必要"调用（重抽 / 手动触发），
保留"必要"调用（每日定时单跑）。

所有用量记 ``data/literature_feed/llm_budget.json``，按 ``YYYY-MM`` 分桶。
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from ..paths import BUDGET_PATH, ensure_dirs


# 价格快照（USD / 1M token）；2026-05 估算，价格变动手动改
# 注：实际中转站价格可能不同，这里用 OpenAI 同名模型作上限估算
_PRICE_USD_PER_M_TOKEN: Dict[str, Dict[str, float]] = {
    # 估算：input/output 平均
    "gpt-5.5": {"input": 5.0, "output": 15.0},
    "deepseek-v4": {"input": 0.27, "output": 1.10},
    "kimi-k2": {"input": 0.5, "output": 2.0},
    "claude-opus-4-8": {"input": 15.0, "output": 75.0},
    "default": {"input": 2.0, "output": 6.0},
}


def _price_for(model: str) -> Dict[str, float]:
    if not model:
        return _PRICE_USD_PER_M_TOKEN["default"]
    m = model.lower()
    for key, price in _PRICE_USD_PER_M_TOKEN.items():
        if key in m:
            return price
    return _PRICE_USD_PER_M_TOKEN["default"]


def estimate_cost_usd(*, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = _price_for(model)
    return (prompt_tokens / 1_000_000) * p["input"] + (completion_tokens / 1_000_000) * p["output"]


class BudgetExceededError(RuntimeError):
    """超过月预算硬上限时抛出。仅对"非必要"调用抛；"必要"调用记账后放行。"""


@dataclass
class _Bucket:
    month: str  # YYYY-MM
    total_usd: float = 0.0
    total_tokens: int = 0
    calls: int = 0
    by_caller: Dict[str, Dict[str, float]] = field(default_factory=dict)
    cache_hits: int = 0


class BudgetTracker:
    """月度 LLM 预算守门员。

    Args:
        monthly_limit_usd: 月预算上限。默认 10.0（用户 2026-05-28 决策）。
        path: 持久化文件路径。``None`` 用 ``paths.BUDGET_PATH``。
        warn_ratio: 警告阈值（默认 0.8）。
        hard_block_ratio: 硬阻断阈值（默认 1.0）。
    """

    def __init__(
        self,
        *,
        monthly_limit_usd: float = 10.0,
        path: Optional[Path] = None,
        warn_ratio: float = 0.8,
        hard_block_ratio: float = 1.0,
    ) -> None:
        self.monthly_limit_usd = float(monthly_limit_usd)
        self.warn_ratio = float(warn_ratio)
        self.hard_block_ratio = float(hard_block_ratio)
        self.path: Path = Path(path) if path else BUDGET_PATH
        self._lock = Lock()
        ensure_dirs()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 文件 I/O
    # ------------------------------------------------------------------ #

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "buckets": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "buckets": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        # 原子写：临时文件 + os.replace
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False,
            dir=str(self.path.parent), prefix=".llm_budget_", suffix=".tmp",
        )
        try:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, self.path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp.name)
            raise

    @staticmethod
    def _current_month() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    # ------------------------------------------------------------------ #
    # 公开 API
    # ------------------------------------------------------------------ #

    def current_usage(self) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
            month = self._current_month()
            bucket = data.get("buckets", {}).get(month, {
                "month": month, "total_usd": 0.0, "total_tokens": 0,
                "calls": 0, "by_caller": {}, "cache_hits": 0,
            })
            ratio = (bucket["total_usd"] / self.monthly_limit_usd) if self.monthly_limit_usd else 1.0
            return {
                "month": month,
                "total_usd": float(bucket.get("total_usd", 0.0)),
                "total_tokens": int(bucket.get("total_tokens", 0)),
                "calls": int(bucket.get("calls", 0)),
                "cache_hits": int(bucket.get("cache_hits", 0)),
                "limit_usd": self.monthly_limit_usd,
                "ratio": ratio,
                "warn": ratio >= self.warn_ratio,
                "exceeded": ratio >= self.hard_block_ratio,
                "by_caller": dict(bucket.get("by_caller", {})),
            }

    def can_call(self, *, essential: bool = False) -> bool:
        """是否允许下一次调用。``essential=True`` 即使超额也放行。"""
        usage = self.current_usage()
        if essential:
            return True
        return not usage["exceeded"]

    def precheck(self, *, essential: bool = False) -> None:
        """用法：在 LLM 调用前 ``budget.precheck()``，超额抛 ``BudgetExceededError``。"""
        if not self.can_call(essential=essential):
            usage = self.current_usage()
            raise BudgetExceededError(
                f"月度 LLM 预算已超额：{usage['total_usd']:.2f}/{usage['limit_usd']:.2f} USD"
            )

    def record(
        self,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        caller: str = "literature_feed",
        cache_hit: bool = False,
    ) -> Dict[str, Any]:
        """登记一次调用。返回当前用量快照。"""
        with self._lock:
            data = self._load()
            month = self._current_month()
            buckets = data.setdefault("buckets", {})
            bucket = buckets.setdefault(month, {
                "month": month, "total_usd": 0.0, "total_tokens": 0,
                "calls": 0, "by_caller": {}, "cache_hits": 0,
            })

            if cache_hit:
                bucket["cache_hits"] = int(bucket.get("cache_hits", 0)) + 1
            else:
                cost = estimate_cost_usd(
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
                bucket["total_usd"] = float(bucket.get("total_usd", 0.0)) + cost
                bucket["total_tokens"] = int(bucket.get("total_tokens", 0)) + prompt_tokens + completion_tokens
                bucket["calls"] = int(bucket.get("calls", 0)) + 1
                by_caller = bucket.setdefault("by_caller", {})
                cstat = by_caller.setdefault(caller, {"calls": 0, "usd": 0.0, "tokens": 0})
                cstat["calls"] = int(cstat.get("calls", 0)) + 1
                cstat["usd"] = float(cstat.get("usd", 0.0)) + cost
                cstat["tokens"] = int(cstat.get("tokens", 0)) + prompt_tokens + completion_tokens

            self._save(data)

        return self.current_usage()

    def reset_month(self, month: Optional[str] = None) -> None:
        """测试用：清空指定月（默认当月）。"""
        target = month or self._current_month()
        with self._lock:
            data = self._load()
            buckets = data.setdefault("buckets", {})
            buckets.pop(target, None)
            self._save(data)

    def list_months(self) -> List[str]:
        with self._lock:
            data = self._load()
            return sorted(data.get("buckets", {}).keys())
