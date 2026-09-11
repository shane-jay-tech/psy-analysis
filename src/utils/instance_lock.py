# -*- coding: utf-8 -*-
"""多实例并发保护：OS 文件锁（v5.10 P1，任务 20260905-110400-1003）。

设计（照 implementation 约束执行，仅探活原语按平台适配）：
- 锁文件：lock_dir/.psy_project.lock，内容 "pid ISO时间戳"。
- 获取：os.open(O_CREAT|O_EXCL) 原子创建；已存在时读 pid 探活。
  * POSIX：os.kill(pid, 0)（ProcessLookupError=死，PermissionError=活）。
  * Windows：os.kill(pid, 0) 在本平台是 TerminateProcess 语义（会误杀持有者，
    已实测），故用标准库 ctypes OpenProcess+GetExitCodeProcess 等义探活。
- 陈旧锁：锁龄 > stale_seconds 且 pid 不存活 → os.replace 挪走再删（防双夺取竞态）后重取。
- 获取失败抛 ProjectLockedError（含持有者 pid），不静默等待。
- 同进程重入：按 pid+depth 计数放行（配合同进程内保留的线程锁分层），仅最外层释放时删文件。
"""
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

LOCK_FILENAME = ".psy_project.lock"
DEFAULT_STALE_SECONDS = 600.0  # 10 分钟


def locked_user_prompt(resource: str, holder: str = "") -> str:
    """锁定占用的统一用户提示（dab0 同源化）：project_panel 与文献面板共用。"""
    holder_part = f"（持有者: {holder}）" if holder else ""
    return f"🔒 {resource}正被另一实例占用{holder_part}，请关闭对方或稍后重试。"


class ProjectLockedError(RuntimeError):
    """项目工作区被另一个实例持有。"""

    def __init__(self, lock_path: str, holder_pid: int, holder_since: str = ""):
        self.lock_path = lock_path
        self.holder_pid = holder_pid
        self.holder_since = holder_since
        super().__init__(
            f"project workspace is locked by another instance "
            f"(pid={holder_pid}, since={holder_since or 'unknown'}): {lock_path}"
        )


_depth_by_path: dict = {}


def _pid_alive(pid: int) -> bool:
    """探活：Windows 走 OpenProcess（os.kill 是 TerminateProcess 语义，会误杀）；POSIX 走 os.kill(pid,0)。"""
    if pid == os.getpid():
        return True
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        else:
            return True
    import ctypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False  # 打开失败：进程大概率已退出
    try:
        exit_code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return True  # 查询失败，保守按存活
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _read_lock(path: Path):
    """返回 (pid, since_str)；解析失败返回 (None, "")。"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        pid_str, _, since = text.partition(" ")
        return int(pid_str.strip()), since.strip()
    except Exception:
        return None, ""


@contextmanager
def project_lock(lock_dir, *, stale_seconds: float = DEFAULT_STALE_SECONDS):
    """跨进程项目互斥锁（非阻塞：被占即抛 ProjectLockedError）。

    同进程内可重入（按 pid+depth），仅最外层创建/删除锁文件；
    线程互斥仍由调用方的 threading 锁承担（本锁只管跨进程）。
    """
    lock_dir = Path(lock_dir)
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / LOCK_FILENAME
    key = str(lock_path)

    depth = _depth_by_path.get(key, 0)
    if depth > 0:
        _depth_by_path[key] = depth + 1
        try:
            yield lock_path
        finally:
            depth = _depth_by_path[key] - 1
            _depth_by_path[key] = depth
        return

    fd = None
    for _attempt in range(3):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                holder_pid, holder_since = _read_lock(lock_path)
                age = time.time() - lock_path.stat().st_mtime
            except FileNotFoundError:
                continue  # 锁刚被持有者释放：直接重试获取
            if age > stale_seconds and (holder_pid is None or not _pid_alive(holder_pid)):
                # 陈旧锁：先挪走再删，避免双夺取竞态
                moved = f"{lock_path}.stale-{uuid.uuid4().hex[:8]}"
                try:
                    os.replace(str(lock_path), moved)
                    os.unlink(moved)
                except OSError:
                    pass
                continue
            raise ProjectLockedError(str(lock_path), holder_pid or -1, holder_since)
    if fd is None:
        raise ProjectLockedError(str(lock_path), -1, "")
    os.write(fd, f"{os.getpid()} {datetime.now().isoformat(timespec='seconds')}".encode("ascii"))
    os.close(fd)
    _depth_by_path[key] = 1
    try:
        yield lock_path
    finally:
        depth = _depth_by_path.get(key, 1) - 1
        if depth <= 0:
            _depth_by_path.pop(key, None)
            try:
                lock_path.unlink()
            except OSError:
                pass
        else:
            _depth_by_path[key] = depth
