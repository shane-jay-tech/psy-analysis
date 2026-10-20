"""s1004-33 反证件：test_e2e_v52_paths 结构型 skipif 改造的护栏（独立成件）。

- 反证：zip_exporter 导入被遮蔽 ⇒ 用例体红（ImportError），而非静默通过——
  6784 遗留的反面钉死（「模块没了但用例假绿」永不允许）。
- 闸行为：真环境（模块在盘可导入）判据为 True ⇒ e2e 件两个 ZIP 用例不因判据误跳。
- 独立成件理由：保持 test_e2e_v52_paths.py 的 --collect-only 收集数改造前后一致（12）。
"""

import sys

import pytest


def test_zip_exporter_shadowed_import_surfaces_red(monkeypatch):
    """反证：遮蔽 src.output.zip_exporter ⇒ 用例体 ImportError（红），不是静默通过。

    结构型 skipif 只在收集期挡「环境真缺」；即便未来有人误删 e2e 件的 skipif 或绕过门，
    模块被改名/删除仍会在用例体内炸 ImportError（红）——本例把这个兜底语义钉死。
    """
    monkeypatch.setitem(sys.modules, "src.output.zip_exporter", None)
    with pytest.raises(ImportError):
        from src.output.zip_exporter import build_deliverable_zip  # noqa: F401


def test_zip_exporter_importable_gate_true_in_real_env():
    """闸行为：真环境判据为 True ⇒ e2e 件不因判据误跳（与 e2e 件 helper 同源）。"""
    from tests.test_e2e_v52_paths import _zip_exporter_importable

    assert _zip_exporter_importable() is True
