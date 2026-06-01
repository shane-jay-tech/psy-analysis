"""SessionLock 测试（v3.5 多 tab 编辑锁）。"""

import time

import streamlit as st

from src.utils.concurrency import (
    DEFAULT_LOCK_TTL,
    SessionLock,
    ensure_tab_id,
    with_lock,
)


class TestEnsureTabId:
    def test_generates_persistent_id(self):
        st.session_state.clear()
        tid1 = ensure_tab_id(st.session_state)
        tid2 = ensure_tab_id(st.session_state)
        assert tid1 == tid2
        assert len(tid1) >= 8


class TestSessionLockBasic:
    def test_acquire_and_release(self):
        st.session_state.clear()
        lock = SessionLock(st.session_state)
        assert lock.acquire("res1", holder_id="tab_A") is True
        assert lock.is_locked("res1") is True
        assert lock.release("res1", holder_id="tab_A") is True
        assert lock.is_locked("res1") is False

    def test_other_holder_cannot_acquire_locked_resource(self):
        st.session_state.clear()
        lock = SessionLock(st.session_state)
        lock.acquire("res1", holder_id="tab_A", ttl=10)
        # tab B 尝试获取
        assert lock.acquire("res1", holder_id="tab_B", ttl=10) is False
        # tab A 仍持有
        assert lock.get_holder("res1") == "tab_A"

    def test_other_holder_cannot_release(self):
        st.session_state.clear()
        lock = SessionLock(st.session_state)
        lock.acquire("res1", holder_id="tab_A")
        # tab B 尝试释放
        assert lock.release("res1", holder_id="tab_B") is False
        # tab A 仍持有
        assert lock.is_locked("res1") is True

    def test_same_holder_can_renew(self):
        st.session_state.clear()
        lock = SessionLock(st.session_state)
        lock.acquire("res1", holder_id="tab_A", ttl=1)
        # 续约
        assert lock.acquire("res1", holder_id="tab_A", ttl=10) is True
        # 续约后仍持有
        assert lock.get_holder("res1") == "tab_A"


class TestLockExpiry:
    def test_expired_lock_can_be_acquired_by_others(self):
        st.session_state.clear()
        lock = SessionLock(st.session_state)
        lock.acquire("res1", holder_id="tab_A", ttl=0)   # 立刻过期
        time.sleep(0.05)
        # tab B 现在应能获取
        assert lock.acquire("res1", holder_id="tab_B", ttl=10) is True
        assert lock.get_holder("res1") == "tab_B"

    def test_expired_lock_not_locked(self):
        st.session_state.clear()
        lock = SessionLock(st.session_state)
        lock.acquire("res1", holder_id="tab_A", ttl=0)
        time.sleep(0.05)
        assert lock.is_locked("res1") is False
        assert lock.get_holder("res1") is None


class TestByOthersCheck:
    def test_my_lock_not_by_others(self):
        st.session_state.clear()
        lock = SessionLock(st.session_state)
        my_id = ensure_tab_id(st.session_state)
        lock.acquire("res1", holder_id=my_id)
        assert lock.is_locked("res1", by_others=False) is True
        assert lock.is_locked("res1", by_others=True) is False

    def test_others_lock_is_by_others(self):
        st.session_state.clear()
        lock = SessionLock(st.session_state)
        # ensure my id
        ensure_tab_id(st.session_state)
        # 另一 tab 锁
        lock.acquire("res1", holder_id="other_tab")
        assert lock.is_locked("res1", by_others=True) is True


class TestWithLockContext:
    def test_with_lock_acquires_on_enter_releases_on_exit(self):
        st.session_state.clear()
        ensure_tab_id(st.session_state)
        with with_lock("res1") as got:
            assert got is True
            # 锁中
            lock = SessionLock(st.session_state)
            assert lock.is_locked("res1") is True
        # 退出后释放
        assert SessionLock(st.session_state).is_locked("res1") is False

    def test_with_lock_returns_false_when_held_by_other(self):
        st.session_state.clear()
        # 先让其他 tab 持有
        SessionLock(st.session_state).acquire("res1", holder_id="other_tab", ttl=10)
        with with_lock("res1") as got:
            assert got is False


class TestSessionLockUIIntegration:
    """v3.6: SessionLock 接入文献综述 UI 写入路径。"""

    def test_check_lock_or_warn_blocks_when_other_holds(self):
        from src.ui.literature_review_panel import _check_lock_or_warn, _LR_NOTES_LOCK
        st.session_state.clear()
        # 其他 tab 占用
        SessionLock(st.session_state).acquire(_LR_NOTES_LOCK, holder_id="other_tab", ttl=30)
        # 当前 tab 应被阻塞
        result = _check_lock_or_warn(_LR_NOTES_LOCK)
        assert result is False

    def test_check_lock_or_warn_passes_when_free(self):
        from src.ui.literature_review_panel import _check_lock_or_warn, _LR_NOTES_LOCK
        st.session_state.clear()
        result = _check_lock_or_warn(_LR_NOTES_LOCK)
        assert result is True

    def test_lock_resources_distinct(self):
        """笔记锁与矩阵锁是独立资源，互不干扰。"""
        from src.ui.literature_review_panel import _LR_NOTES_LOCK, _LR_MATRIX_LOCK
        st.session_state.clear()
        lock = SessionLock(st.session_state)
        lock.acquire(_LR_NOTES_LOCK, holder_id="tab_A")
        # 矩阵锁仍可被其他 tab 获取
        assert lock.acquire(_LR_MATRIX_LOCK, holder_id="tab_B") is True
