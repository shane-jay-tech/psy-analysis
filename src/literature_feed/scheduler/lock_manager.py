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
        # s1002-18（s924-70 遗留5）：追加累积形态下取**最末条** pid——re.search 取首条
        # 会把持有者长期报成最老那位（矿源实测报 130036 而非 135684）。可读性修复，
        # TTL/is_stale/break_stale 锁语义零改动。
        matches = re.findall(r"pid=(\d+)", text)
        return int(matches[-1]) if matches else None

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
    def acquire(self, now: Optional[float] = None):
        """非阻塞抢锁；失败抛 ``LockBusyError``。

        Args:
            now: s927-35 加的**时钟接缝**（与 ``is_stale`` 同款、同样可选）。``None``
                （缺省）= 内部按真实时钟判陈旧，行为与旧版逐字一致；传入 epoch 秒 =
                用这个"现在"判陈旧，并把它透传给 ``_open_and_lock`` → ``is_stale`` /
                ``break_stale``，让"判陈旧"与"删档"共用同一个读数。
                有了它，``_open_and_lock`` 里那条 stale 强抢路径（现 :191-192）可以精确
                压线断言，测试不必再在 ``os.utime`` 与 SUT 取时之间留裕量（s922-109 遗留 1）。
        """
        self._open_and_lock(now=now)
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

    def is_stale(self, now: Optional[float] = None) -> bool:
        """锁文件是否陈旧（mtime 距今 > ttl_seconds）。

        Args:
            now: s921-13 加的**时钟接缝**。``None``（缺省）= 现算 ``time.time()``，
                行为与旧版逐字一致；传入 epoch 秒 = 用这个"现在"做判据。
                有了它，``>`` 与 ``>=`` 的边界可以用 ``now = mtime + ttl`` 精确断言，
                测试不必再两侧留裕量（见 s920-24 遗留 1）。
                同一次调用的 age 与告警里的 age_min 共用这一个读数；旧版调了两次
                ``time.time()``，两个值之间夹着 stat 与字符串格式化，会差出调度抖动。
        """
        try:
            # s930-09：exists() 也可能因竞态/权限抛 OSError（3.12 Path.exists 不兜
            # 全部 OSError 形态）——并入本 try，stat() 分支一并优雅降级（s922-109 遗留 2）。
            if not self.lock_path.exists():
                return False
            mtime = self.lock_path.stat().st_mtime
        except OSError:
            return False
        if now is None:
            now = time.time()
        age = now - mtime
        stale = age > self.ttl_seconds
        if stale:
            age_min = int(age / 60)
            # s930-09：ttl<60s 时 age_min 恒 0 ⇒「stale for 0 min」截断文案误导
            #（实际是 X 秒）；<1 分钟改显式秒数。
            detail = (f"stale for {int(age)}s (<1 min)" if age_min < 1
                      else f"stale for {age_min} min")
            self._alert_once(
                "stale_lock",
                f"lock={self.lock_path} {detail} (ttl={self.ttl_seconds}s)",
            )
        return stale

    def break_stale(self, now: Optional[float] = None) -> bool:
        """删除 stale 锁文件。返回是否真的删了。

        Args:
            now: s927-35 加的**时钟接缝**（与 ``is_stale`` 同款、同样可选）。``None``
                （缺省）= 真实时钟，行为与旧版逐字一致（旧版本就硬调
                ``self.is_stale()`` 不带参）；传入 epoch 秒 = 原样透传给
                ``is_stale(now=…)``，判据与告警年龄都用这个读数。
        """
        if not self.is_stale(now=now):
            return False
        with contextlib.suppress(OSError):
            self.lock_path.unlink()
            return True
        return False

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #

    def _open_and_lock(self, now: Optional[float] = None) -> None:
        if self._fh is not None:
            raise RuntimeError("LockManager 已经持锁，不要嵌套 acquire")

        # 处理 stale：mtime 太老的强抢（s927-35：注入的 now 一路透传，两侧同读数）
        if self.is_stale(now=now):
            self.break_stale(now=now)

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

