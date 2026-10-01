"""sklearn 兼容垫片。

背景（2026-09-25 P16/P09 取证）：本机 scikit-learn 已移除 check_array(force_all_finite=...)
（1.6 起改名为 ensure_all_finite），而 factor_analyzer 仍按旧名调用 ⇒ 所有走
factor_analyzer 的路径（EFA、McDonald ω、CFA 的 AVE/CR 载荷回退）直接抛
TypeError: check_array() got an unexpected keyword argument 'force_all_finite'。

设计约束（评审意见 #5，GPT，2026-09-25）：
  * 只在目标版本确实**不支持**旧参数名时才打补丁（用 signature 探测，支持就完全不碰）；
  * 补丁必须保留原函数的签名/元数据（functools.wraps）；
  * 两个参数名同时出现时以新名优先并丢弃旧名，避免 "got multiple values"；
  * 全局 monkeypatch 只是**兼容层兜底**，正解是锁定经测试的 sklearn/factor_analyzer 版本组合；
    因此这里只做参数改名转发，不改任何数值语义，且支持 uninstall() 还原。
"""
from __future__ import annotations

import functools

_PATCHED = False
_ORIGINAL = None


def _supports_legacy_kwarg(fn) -> bool:
    """目标 check_array 是否仍然接受 force_all_finite。"""
    try:
        import inspect

        params = inspect.signature(fn).parameters
        return "force_all_finite" in params or any(
            p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
    except Exception:
        return True  # 探测不了就当它支持 → 不打补丁（保守）


def install() -> bool:
    """幂等地把 check_array 的旧参数名转发到新名字。返回是否已完成补丁。"""
    global _PATCHED, _ORIGINAL
    if _PATCHED:
        return True
    try:
        from sklearn.utils import validation as _validation
    except Exception:  # sklearn 不存在：无需求
        return False

    original = getattr(_validation, "check_array", None)
    if original is None or _supports_legacy_kwarg(original):
        return False  # 旧版 sklearn 本来就支持旧名，不打补丁

    @functools.wraps(original)
    def _check_array_compat(*args, **kwargs):
        if "force_all_finite" in kwargs:
            legacy = kwargs.pop("force_all_finite")
            kwargs.setdefault("ensure_all_finite", legacy)   # 新名优先，避免重复传参
        return original(*args, **kwargs)

    _validation.check_array = _check_array_compat
    try:  # sklearn.utils.check_array 常是同一对象的别名
        from sklearn import utils as _utils

        if getattr(_utils, "check_array", None) is original:
            _utils.check_array = _check_array_compat
    except Exception:
        pass
    _ORIGINAL = (original, _validation)
    _PATCHED = True
    return True


def uninstall() -> bool:
    """还原被替换的 check_array（测试/排查用）。"""
    global _PATCHED, _ORIGINAL
    if not _PATCHED or _ORIGINAL is None:
        return False
    original, module = _ORIGINAL
    module.check_array = original
    try:
        from sklearn import utils as _utils

        if getattr(_utils, "check_array", None) is not original:
            _utils.check_array = original
    except Exception:
        pass
    _PATCHED = False
    _ORIGINAL = None
    return True


install()
