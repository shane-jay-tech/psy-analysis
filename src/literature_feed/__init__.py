"""v4.7 自学习文献雷达模块。

每天自动抓 4 本中文心理/管理学顶刊（心理学报 / 心理科学进展 / 心理科学 /
管理世界）的新文章，LLM 抽候选构念与方法，进入 staging 待人工审核，
聚合成 30/90 天领域热点反哺选题漏斗。

架构决策：见 ``docs/decisions/2026-05-28-debate-self-learning-architecture.md``
"""

from .paths import (
    DATA_ROOT,
    DB_PATH,
    JSONL_RAW_DIR,
    LOCK_DIR,
    DOMAIN_WEIGHTS_PATH,
    BUDGET_PATH,
    FETCH_LOCK_FILE,
)

__all__ = [
    "DATA_ROOT",
    "DB_PATH",
    "JSONL_RAW_DIR",
    "LOCK_DIR",
    "DOMAIN_WEIGHTS_PATH",
    "BUDGET_PATH",
    "FETCH_LOCK_FILE",
]
