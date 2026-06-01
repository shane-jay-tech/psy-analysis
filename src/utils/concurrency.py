"""单用户多 tab 编辑锁（v3.5）。

设计：
- 单用户场景下也可能开多个浏览器 tab 编辑同一项目
- 基于 session_state["_lock_dict"]，键为资源名，值为 (holder_id, expire_at)
- 默认 ttl=30 秒，过期后任何 tab 可重新获取
- 读不抢锁；写前必须 acquire，失败则提示「另一标签页正在编辑」

API:
- ensure_tab_id(session_state) -> str  自动生成持久 tab_id
- SessionLock.acquire/release/is_locked
- with_lock(resource, ...) 上下文管理器（推荐用法）
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any, Optional


_LOCK_DICT_KEY = "_lock_dict"
_TAB_ID_KEY = "_tab_id"
DEFAULT_LOCK_TTL = 30   # 秒


def ensure_tab_id(session_state: Any = None) -> str:
    """每个 tab 加载时调用，生成（或获取已有的）唯一 tab_id。"""
    if session_state is None:
        try:
            import streamlit as st
            session_state = st.session_state
        except Exception:
            return uuid.uuid4().hex[:12]
    tid = session_state.get(_TAB_ID_KEY) if hasattr(session_state, "get") else None
    if not tid:
        tid = uuid.uuid4().hex[:12]
        session_state[_TAB_ID_KEY] = tid
    return tid


def _get_lock_dict(session_state: Any) -> dict:
    d = session_state.get(_LOCK_DICT_KEY) if hasattr(session_state, "get") else None
    if not isinstance(d, dict):
        d = {}
        session_state[_LOCK_DICT_KEY] = d
    return d


class SessionLock:
    """资源锁。资源名是字符串（如 "literature_notes"、"matrix"）。"""

    def __init__(self, session_state: Any = None):
        if session_state is None:
            try:
                import streamlit as st
                session_state = st.session_state
            except Exception:
                session_state = {}
        self._session_state = session_state
        # 初始化锁 dict
        _get_lock_dict(self._session_state)

    def acquire(
        self,
        resource: str,
        holder_id: Optional[str] = None,
        ttl: int = DEFAULT_LOCK_TTL,
    ) -> bool:
        """尝试获取锁。

        - 资源未锁定 → 获取
        - 锁已过期（now > expire_at）→ 接管
        - 锁还活着且 holder_id 不同 → 失败
        - 同 holder_id → 续约
        """
        if holder_id is None:
            holder_id = ensure_tab_id(self._session_state)
        d = _get_lock_dict(self._session_state)
        existing = d.get(resource)
        now = time.time()
        if existing is not None:
            cur_holder, expire_at = existing
            if cur_holder != holder_id and expire_at > now:
                return False
        d[resource] = (holder_id, now + ttl)
        return True

    def release(self, resource: str, holder_id: Optional[str] = None) -> bool:
        """释放锁；只有持有者才能释放。"""
        if holder_id is None:
            holder_id = ensure_tab_id(self._session_state)
        d = _get_lock_dict(self._session_state)
        existing = d.get(resource)
        if existing is None:
            return False
        if existing[0] != holder_id:
            return False
        d.pop(resource, None)
        return True

    def is_locked(self, resource: str, by_others: bool = False) -> bool:
        """资源是否被锁定。

        - by_others=False: 任何人锁定都返回 True（排除已过期）
        - by_others=True: 仅当被其他 tab 锁定时返回 True
        """
        d = _get_lock_dict(self._session_state)
        existing = d.get(resource)
        if existing is None:
            return False
        cur_holder, expire_at = existing
        if expire_at <= time.time():
            return False
        if by_others:
            my_id = ensure_tab_id(self._session_state)
            return cur_holder != my_id
        return True

    def get_holder(self, resource: str) -> Optional[str]:
        """返回当前持有者（过期视为无持有）。"""
        d = _get_lock_dict(self._session_state)
        existing = d.get(resource)
        if existing is None:
            return None
        holder, expire_at = existing
        if expire_at <= time.time():
            return None
        return holder


@contextmanager
def with_lock(resource: str, *, session_state: Any = None, ttl: int = DEFAULT_LOCK_TTL):
    """上下文管理器：进入时 acquire，退出时 release。

    用法：
        with with_lock("literature_notes") as got:
            if not got:
                st.warning("当前数据正在另一个标签页中编辑")
            else:
                # 安全写入
                ...

    注意：失败时不抛异常（避免上层崩），返回 False 让调用方处理。
    """
    lock = SessionLock(session_state)
    holder_id = ensure_tab_id(lock._session_state)
    got = lock.acquire(resource, holder_id=holder_id, ttl=ttl)
    try:
        yield got
    finally:
        if got:
            lock.release(resource, holder_id=holder_id)
