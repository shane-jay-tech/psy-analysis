"""文献雷达模块的路径常量。

唯一原则：所有自学习数据落在 ``D:\\code\\psy-analysis\\data\\literature_feed\\``
之下，**绝不**写到 ``C:\\Users\\.claude`` 或仓库其它目录。
用户 2026-05-28 明确要求"存储进 D 盘"。

测试可通过 ``LITERATURE_FEED_DATA_ROOT`` 环境变量覆盖根目录（指向临时目录）。
"""

from __future__ import annotations

import os
from pathlib import Path


def _resolve_data_root() -> Path:
    override = os.environ.get("LITERATURE_FEED_DATA_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    here = Path(__file__).resolve()
    repo_root = here.parents[2]  # src/literature_feed/paths.py -> repo root
    return repo_root / "data" / "literature_feed"


DATA_ROOT: Path = _resolve_data_root()
DB_PATH: Path = DATA_ROOT / "feed.sqlite"
JSONL_RAW_DIR: Path = DATA_ROOT / "raw"
LOCK_DIR: Path = DATA_ROOT / "locks"
DOMAIN_WEIGHTS_PATH: Path = DATA_ROOT / "domain_weights.yaml"
METHOD_WEIGHTS_PATH: Path = DATA_ROOT / "method_weights.yaml"
TRENDING_WEIGHTS_PATH: Path = DATA_ROOT / "trending_weights.yaml"
BUDGET_PATH: Path = DATA_ROOT / "llm_budget.json"
FETCH_LOCK_FILE: Path = LOCK_DIR / "feed_fetch.lock"


def ensure_dirs() -> None:
    """首次运行时把目录骨架建出来。幂等。"""
    for directory in (DATA_ROOT, JSONL_RAW_DIR, LOCK_DIR):
        directory.mkdir(parents=True, exist_ok=True)
