# -*- coding: utf-8 -*-
"""s1010-12 _sklearn_compat 垫片行为钉桩：探测/wraps/新名优先/uninstall 还原四性。

自证原则：用自造签名的假 check_array 经 sys.modules 注入，不依赖本机 sklearn 版本形态；
每例 try/finally（fixture）保证 uninstall＋sys.modules 还原＋重装进场态，不污染同进程后续测试。
"""
import sys
import types

import pytest

from src.analysis import _sklearn_compat as shim

_FAKE_KEYS = ("sklearn", "sklearn.utils", "sklearn.utils.validation")


def _make_fake(legacy_supported: bool):
    sklearn = types.ModuleType("sklearn")
    utils = types.ModuleType("sklearn.utils")
    validation = types.ModuleType("sklearn.utils.validation")

    if legacy_supported:
        def fake_check_array(array, force_all_finite=True, copy=True):
            return ("fake-legacy", array, force_all_finite, copy)
    else:
        def fake_check_array(array, ensure_all_finite=True, copy=True):
            return ("fake", array, ensure_all_finite, copy)

    validation.check_array = fake_check_array
    utils.check_array = fake_check_array
    utils.validation = validation
    sklearn.utils = utils
    return sklearn, utils, validation, fake_check_array


def _inject(legacy_supported: bool):
    saved = {k: sys.modules.get(k) for k in _FAKE_KEYS}
    sklearn, utils, validation, original = _make_fake(legacy_supported)
    sys.modules["sklearn"] = sklearn
    sys.modules["sklearn.utils"] = utils
    sys.modules["sklearn.utils.validation"] = validation
    return utils, validation, original, saved


def _restore(saved):
    for k, v in saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v


@pytest.fixture()
def fake_env():
    """进场先卸真实补丁，出场卸假补丁＋还原 sys.modules＋重装进场态。"""
    shim.uninstall()
    utils, validation, original, saved = _inject(legacy_supported=False)
    try:
        yield utils, validation, original
    finally:
        shim.uninstall()
        _restore(saved)
        shim.install()


def test_a_unsupported_env_patches_and_wraps(fake_env):
    """性 a：不支持旧名环境 install 生效，functools.wraps 元数据保留。"""
    utils, validation, original = fake_env
    assert shim.install() is True
    patched = validation.check_array
    assert patched is not original
    assert getattr(patched, "__wrapped__", None) is original
    assert patched.__name__ == original.__name__
    assert utils.check_array is patched  # 别名面同步补丁
    assert patched("arr", force_all_finite=False) == ("fake", "arr", False, True)


def test_a2_probe_positive_skips_patch():
    """性 a 补面：探测到旧名仍支持（或 **kwargs 兜底）→ 不打补丁。"""
    shim.uninstall()
    utils, validation, original, saved = _inject(legacy_supported=True)
    try:
        assert shim.install() is False
        assert validation.check_array is original
    finally:
        shim.uninstall()
        _restore(saved)
        shim.install()


def test_b_new_name_wins_no_multiple_values(fake_env):
    """性 b：新旧参名同传 → 旧名丢弃、新名优先，不炸 multiple values。"""
    utils, validation, original = fake_env
    shim.install()
    out = validation.check_array("arr", force_all_finite=False, ensure_all_finite=True)
    assert out == ("fake", "arr", True, True)  # 新名 True 胜出


def test_c_uninstall_restores_original(fake_env):
    """性 c：uninstall 还原原函数对象；重复卸载返回 False；卸后可重装。"""
    utils, validation, original = fake_env
    shim.install()
    assert shim.uninstall() is True
    assert validation.check_array is original
    assert utils.check_array is original
    assert shim.uninstall() is False
    assert shim.install() is True
    assert validation.check_array.__wrapped__ is original


def test_d_repeated_install_idempotent(fake_env):
    """性 d：重复 install 幂等——返回 True 且不二次包裹。"""
    utils, validation, original = fake_env
    assert shim.install() is True
    first = validation.check_array
    assert shim.install() is True
    assert validation.check_array is first
    assert first.__wrapped__ is original  # 包裹深度恒 1
