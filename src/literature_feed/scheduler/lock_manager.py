"""跨进程文件锁。

Windows Task Scheduler 起的 Python 进程 vs Streamlit 应用进程都可能触发
``daily_runner``，单纯 SQLite WAL 不挡跨进程多 writer 同时写。这里用
文件锁做"谁先起谁干活"的硬互斥。

Windows 用 ``msvcrt.locking``，POSIX 用 ``fcntl.flock``。锁文件存
``data/literature_feed/locks/feed_fetch.lock``。
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..paths import FETCH_LOCK_FILE, ensure_dirs


_IS_WINDOWS = sys.platform.startswith("win")


class LockBusyError(RuntimeError):
    """锁已被其他进程持有。"""


class LockManager:
    """跨进程文件锁。

    用法：
        lock = LockManager()
        try:
            with lock.acquire():
                # 整个抓取流程
                ...
        except LockBusyError:
            print("已在运行中")

    Args:
        lock_path: 锁文件路径。``None`` 用 ``paths.FETCH_LOCK_FILE``。
        ttl_seconds: 锁文件的 TTL，超过这个时间没释放视为 stale 强抢。默认 6 小时（21600s）。
    """

    def __init__(
        self,
        lock_path: Optional[Path] = None,
        *,
        ttl_seconds: int = 21600,  # 6h — daily run + LLM 抽取最坏情况也用不到
    ) -> None:
        self.lock_path: Path = Path(lock_path) if lock_path else FETCH_LOCK_FILE
        self.ttl_seconds = int(ttl_seconds)
        self._fh: Optional[Any] = None
        # d914-19：一次性告警守卫（同一实例同一告警只发一次，防 UI 轮询刷屏）
        self._alerted: set[str] = set()
        ensure_dirs()
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 告警（d914-19：可选告警日志，只记不改锁行为）
    # ------------------------------------------------------------------ #

    def _read_owner_pid(self) -> Optional[int]:
        """尽力从锁文件读持锁 pid（读不到返回 None，属最小信息口径）。

        必须从 offset 1 起读：Windows 下 byte 0 被 ``msvcrt.locking`` 独占，持锁期内
        任何整文件读取都会 ``PermissionError``；而 ``_write_owner_info`` 本就把
        ``pid=…`` 写在 byte 1 之后（以 ``\\n`` 当 sentinel），偏移 1 正好绕开锁字节。
        """
        try:
            with open(self.lock_path, "rb") as fh:
                fh.seek(1)
                text = fh.read().decode("utf-8", errors="replace")
        except OSError:
            return None
        m = re.search(r"pid=(\d+)", text)
        return int(m.group(1)) if m else None

    def _owner_suffix(self) -> str:
        """给"抢锁失败"补一句是谁占着——读不到就当 unknown，绝不因为取信息而改变结论。"""
        pid = self._read_owner_pid()
        return f"（持有者 pid={pid if pid is not None else 'unknown'}）"

    def _alert_once(self, kind: str, message: str) -> None:
        """同一实例同一 kind 只告警一次。"""
        if kind in self._alerted:
            return
        self._alerted.add(kind)
        logging.warning("[lock-alert] %s %s", kind, message)

    # ------------------------------------------------------------------ #
    # 主要 API
    # ------------------------------------------------------------------ #

    @contextlib.contextmanager
    def acquire(self):
        """非阻塞抢锁；失败抛 ``LockBusyError``。"""
        self._open_and_lock()
        try:
            self._write_owner_info()
            yield self
        finally:
            self._unlock_and_close()

    def is_held_by_other(self) -> bool:
        """快速探测：另一个进程是否持有这个锁。

        实现：尝试非阻塞抢一下，立刻释放。注意有窗口 race，仅供 UI 提示。
        """
        try:
            self._open_and_lock()
        except LockBusyError:
            pid = self._read_owner_pid()
            self._alert_once(
                "held_by_other",
                f"lock={self.lock_path} held by pid={pid if pid is not None else 'unknown'}",
            )
            return True
        else:
            self._unlock_and_close()
            return False

    def is_stale(self) -> bool:
        if not self.lock_path.exists():
            return False
        try:
            mtime = self.lock_path.stat().st_mtime
        except OSError:
            return False
        stale = (time.time() - mtime) > self.ttl_seconds
        if stale:
            age_min = int((time.time() - mtime) / 60)
            self._alert_once(
                "stale_lock",
                f"lock={self.lock_path} stale for {age_min} min (ttl={self.ttl_seconds}s)",
            )
        return stale

    def break_stale(self) -> bool:
        """删除 stale 锁文件。返回是否真的删了。"""
        if not self.is_stale():
            return False
        with contextlib.suppress(OSError):
            self.lock_path.unlink()
            return True
        return False

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #

    def _open_and_lock(self) -> None:
        if self._fh is not None:
            raise RuntimeError("LockManager 已经持锁，不要嵌套 acquire")

        # 处理 stale：mtime 太老的强抢
        if self.is_stale():
            self.break_stale()

        # 打开/创建文件
        try:
            fh = open(self.lock_path, "a+", encoding="utf-8")
        except OSError as exc:
            raise LockBusyError(f"无法打开锁文件 {self.lock_path}: {exc}") from exc

        try:
            self._do_lock(fh)
        except LockBusyError as exc:
            with contextlib.suppress(OSError):
                fh.close()
            raise LockBusyError(f"{exc}{self._owner_suffix()}") from exc
        except OSError as exc:
            with contextlib.suppress(OSError):
                fh.close()
            raise LockBusyError(f"获取锁失败: {exc}{self._owner_suffix()}") from exc

        self._fh = fh

    def _do_lock(self, fh) -> None:
        if _IS_WINDOWS:
            import msvcrt
            # msvcrt.locking 锁的是 "当前文件位置开始的 N 个字节"，
            # 必须把所有竞争方都钉到同一个字节（这里选 byte 0），否则锁不到一起
            try:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise LockBusyError("锁已被其他进程持有") from exc
        else:
            import fcntl
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise LockBusyError("锁已被其他进程持有") from exc

    def _unlock_and_close(self) -> None:
        fh = self._fh
        self._fh = None
        if fh is None:
            return
        with contextlib.suppress(Exception):
            if _IS_WINDOWS:
                import msvcrt
                try:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
        with contextlib.suppress(OSError):
            fh.close()

    def _write_owner_info(self) -> None:
        # 故意不在锁字节区域之外写：锁了 byte 0，写从 byte 1 开始（用 \n 当 sentinel）
        try:
            assert self._fh is not None
            # 先回到文件末尾追加，不动 byte 0（保留为锁字节）
            self._fh.seek(0, 2)
            payload = (
                f"\npid={os.getpid()} "
                f"acquired_at={datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
            )
            self._fh.write(payload)
            self._fh.flush()
            os.fsync(self._fh.fileno())
        except (OSError, ValueError) as exc:
            # 写不进去不算致命，锁还是有效的——但"谁在干活"这条可观测性没了，必须吱一声
            self._alert_once(
                "owner_write_failed",
                f"lock={self.lock_path} 持有者信息写入失败（锁仍有效）：{exc!r}",
            )

