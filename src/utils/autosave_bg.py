"""方案B 后台保存 worker（2026-09-11，B-079/psy-snapshot-perf-20260911.md §③）。

分工：
- 主线程（Streamlit UI 线程，autosave.trigger_autosave 内）只做「引用级捕获」：
  把 session_state 全部键值按引用拷进普通 dict —— 零序列化、零深拷贝；
- 本模块的单 worker 线程把捕获 dict 当作 session_state，喂给
  ``src.utils.workspace.build_workspace_snapshot`` 的私有模块副本执行真实配方，
  再经 project_manager.save_workspace 原子落盘 —— 序列化 + 写盘全部离开 UI 线程；
- 单 worker + 单槽 pending（新捕获覆盖旧捕获 = 尾延迟合并）；结果存 _result 槽，
  由主线程下次 trigger_autosave 时 drain 进 session_state（主线程 atomic swap）。

约束与前提：
- 不跨线程读 st.session_state：捕获发生在主线程；worker 只碰普通 dict；
- 不全局 monkeypatch streamlit：st 替换发生在 workspace 的私有模块副本上
  （importlib 加载、不注册 sys.modules，主线程用的原模块对象不受影响）；
- 被捕获的大对象（df 等）按 Streamlit 惯例「整体替换、不就地改」；若未来引入
  就地变更，捕获需改为浅拷贝（见 KNOWN_ISSUES「大工作区快照」条目跟进）。
"""

from __future__ import annotations

import importlib.util
import logging
import threading
import time
import types
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_SRC_MODULE = 'src.utils.workspace'

_lock = threading.Lock()
_cond = threading.Condition(_lock)
_pending: Optional[Dict[str, Any]] = None  # {'project_id':..., 'refs':...}
_busy = False
_result: Optional[Dict[str, Any]] = None  # {'ok':..., 'error':...}
_last_worker_ms = 0.0
_thread: Optional[threading.Thread] = None
_dropped_coalesced = 0  # 被 newer 捕获覆盖掉的 pending 数（观测用）
_private_mod = None  # workspace 私有副本（懒加载，单 worker 独占）


def _get_private_builder():
    """加载 workspace 私有副本并缓存；其 st 替换为捕获 dict 的壳，配方与源码永远一致。"""
    global _private_mod
    if _private_mod is None:
        spec = importlib.util.find_spec(_SRC_MODULE)
        mod = importlib.util.module_from_spec(spec)
        # workspace.py 内部均为绝对导入，exec 期间复用 sys.modules 缓存；
        # 副本不注册进 sys.modules，主线程 import src.utils.workspace 拿到的仍是原模块。
        spec.loader.exec_module(mod)
        mod.st = types.SimpleNamespace(session_state={})
        _private_mod = mod
    return _private_mod


def _worker_loop():
    global _busy, _result, _last_worker_ms, _pending
    while True:
        with _cond:
            while _pending is None:
                _cond.wait()
            job = _pending
            _pending = None
            _busy = True
        t0 = time.perf_counter()
        ok, err = False, None
        try:
            mod = _get_private_builder()
            mod.st.session_state = job['refs']
            ws = mod.build_workspace_snapshot()
            from src.utils import project_manager as pm
            ok = pm.save_workspace(job['project_id'], ws)
            if not ok:
                err = '自动保存写入失败，请检查磁盘空间或导出快照'
        except Exception:
            logger.debug('autosave-bg: 后台保存失败', exc_info=True)
            err = '自动保存写入失败，请检查磁盘空间或导出快照'
        ms = (time.perf_counter() - t0) * 1000
        with _cond:
            _result = {'ok': ok, 'error': err, 'project_id': job['project_id']}
            _last_worker_ms = ms
            _busy = False
            _cond.notify_all()


def _ensure_thread() -> None:
    global _thread
    with _cond:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_worker_loop, name='psy-autosave-bg', daemon=True)
            _thread.start()


def submit(project_id: str, refs: Dict[str, Any]) -> bool:
    """提交一次后台保存；已有 pending 时新任务覆盖旧任务（尾延迟合并）。"""
    global _pending, _dropped_coalesced
    _ensure_thread()
    with _cond:
        if _pending is not None:
            _dropped_coalesced += 1
        _pending = {'project_id': project_id, 'refs': refs}
        _cond.notify()
    return True


def drain_result() -> Optional[Dict[str, Any]]:
    """主线程取走最近一次后台结果（原子 swap）；无则返回 None。"""
    global _result
    with _cond:
        res, _result = _result, None
    return res


def flush(timeout: float = 10.0) -> Tuple[bool, float]:
    """等 pending 清空且在跑任务完成（退出钩子/测试用）。返回 (是否完成, 末次 worker 毫秒)。"""
    deadline = time.monotonic() + timeout
    with _cond:
        while (_pending is not None or _busy) and time.monotonic() < deadline:
            _cond.wait(timeout=max(0.01, min(0.1, deadline - time.monotonic())))
        return (_pending is None and not _busy), _last_worker_ms
