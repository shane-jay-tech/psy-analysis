"""缓存与临时文件管理 v5.1。

提供系统级的清理策略：
- 临时图表文件过期清理
- PDF 转换中间文件清理
- ZIP 导出缓存清理
- 诊断日志手动清理
- 本地数据留存说明
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class CacheEntry:
    path: Path
    category: str
    size_bytes: int
    created: datetime
    description: str


@dataclass
class CacheReport:
    entries: list[CacheEntry]
    total_size_bytes: int
    total_files: int
    categories: dict  # category -> size_bytes


CACHE_DIRS = {
    "temp_figures": Path("data/temp_figures"),
    "pdf_temp": Path("data/pdf_temp"),
    "zip_cache": Path("data/zip_cache"),
    "feedback_logs": Path("data/feedback_logs"),
    "perf_logs": Path("data"),
}


def scan_cache() -> CacheReport:
    """扫描系统缓存和临时文件。"""
    entries = []
    categories = {}

    for category, dir_path in CACHE_DIRS.items():
        if not dir_path.exists():
            continue

        if category == "perf_logs":
            perf_file = dir_path / "perf_log.jsonl"
            if perf_file.exists():
                size = perf_file.stat().st_size
                entries.append(CacheEntry(
                    path=perf_file, category="perf_logs",
                    size_bytes=size,
                    created=datetime.fromtimestamp(perf_file.stat().st_ctime),
                    description="性能事件日志",
                ))
                categories["perf_logs"] = size
            continue

        cat_size = 0
        for f in dir_path.rglob("*"):
            if f.is_file():
                size = f.stat().st_size
                cat_size += size
                entries.append(CacheEntry(
                    path=f, category=category,
                    size_bytes=size,
                    created=datetime.fromtimestamp(f.stat().st_ctime),
                    description=f"{category}/{f.name}",
                ))
        categories[category] = cat_size

    total_size = sum(categories.values())
    return CacheReport(
        entries=entries,
        total_size_bytes=total_size,
        total_files=len(entries),
        categories=categories,
    )


def clear_category(category: str) -> int:
    """清除指定类别的缓存。返回删除的文件数。"""
    if category not in CACHE_DIRS:
        return 0

    dir_path = CACHE_DIRS[category]

    if category == "perf_logs":
        perf_file = dir_path / "perf_log.jsonl"
        if perf_file.exists():
            perf_file.unlink()
            return 1
        return 0

    if not dir_path.exists():
        return 0

    count = 0
    for f in dir_path.rglob("*"):
        if f.is_file():
            f.unlink()
            count += 1
    return count


def clear_all_cache() -> dict:
    """清除所有缓存。返回每类删除的文件数。"""
    result = {}
    for category in CACHE_DIRS:
        result[category] = clear_category(category)
    return result


def clear_expired(max_age_hours: int = 24) -> int:
    """清除超过指定小时数的临时文件。"""
    now = time.time()
    threshold = now - (max_age_hours * 3600)
    count = 0

    for category in ("temp_figures", "pdf_temp", "zip_cache"):
        dir_path = CACHE_DIRS.get(category)
        if not dir_path or not dir_path.exists():
            continue
        for f in dir_path.rglob("*"):
            if f.is_file() and f.stat().st_mtime < threshold:
                f.unlink()
                count += 1
    return count


def format_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
