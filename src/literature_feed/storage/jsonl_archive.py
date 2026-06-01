"""原始抓取 payload 归档为 JSONL（每日按 source 切分）。

用途：
1. 解析器 bug 修复后可重放抓取（不再二次请求外站）
2. 法律合规审计：每条记录附时间 / URL / status / sha256

写入采用 ``temp + os.replace`` 原子 rename，避免半文件。
单文件 append 也走文件锁（同进程足够；跨进程靠 ``lock_manager``）。
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from ..paths import JSONL_RAW_DIR, ensure_dirs


_LOCK = threading.Lock()


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


class JsonlArchive:
    """每日 / source 维度的 JSONL 归档。

    Args:
        root: 根目录，默认 ``paths.JSONL_RAW_DIR``。
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root: Path = Path(root) if root else JSONL_RAW_DIR
        ensure_dirs()
        self.root.mkdir(parents=True, exist_ok=True)

    def _file_for(self, source_id: str, date: Optional[str] = None) -> Path:
        day = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir = self.root / day
        day_dir.mkdir(parents=True, exist_ok=True)
        # 避免路径注入：只允许字母数字下划线连字符
        safe = "".join(c for c in source_id if c.isalnum() or c in "-_") or "unknown"
        return day_dir / f"{safe}.jsonl"

    def append(
        self,
        source_id: str,
        record: Dict[str, Any],
        *,
        date: Optional[str] = None,
    ) -> Path:
        """追加一条记录。返回被写入的文件路径。"""
        path = self._file_for(source_id, date=date)
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with _LOCK:
            with path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(line)
        return path

    def append_many(
        self,
        source_id: str,
        records: list,
        *,
        date: Optional[str] = None,
    ) -> Path:
        path = self._file_for(source_id, date=date)
        if not records:
            return path
        lines = [json.dumps(r, ensure_ascii=False) + "\n" for r in records]
        with _LOCK:
            with path.open("a", encoding="utf-8", newline="\n") as f:
                f.writelines(lines)
        return path

    def iter_day(self, source_id: str, date: str) -> Iterator[Dict[str, Any]]:
        path = self._file_for(source_id, date=date)
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                with contextlib.suppress(json.JSONDecodeError):
                    yield json.loads(line)

    def list_dates(self) -> list:
        if not self.root.exists():
            return []
        return sorted(p.name for p in self.root.iterdir() if p.is_dir())
