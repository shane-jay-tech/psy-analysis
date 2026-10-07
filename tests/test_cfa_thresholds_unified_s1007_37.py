# -*- coding: utf-8 -*-
"""s1007-37 CFA 双源归一钉桩：三键与 thresholds.py 单源逐位相等；srmr 本地冲突留档。"""
from src.analysis import cfa
from src.analysis import thresholds as th


def test_three_keys_unified_with_thresholds_module():
    """cfi/tli/rmsea 三键归一后与 thresholds.py 逐位相等（零语义变更实证）。"""
    assert cfa.FIT_THRESHOLDS["cfi"] == {"good": th.CFA.good, "acceptable": th.CFA.acceptable}
    assert cfa.FIT_THRESHOLDS["tli"] == {"good": th.TLI.good, "acceptable": th.TLI.acceptable}
    assert cfa.FIT_THRESHOLDS["rmsea"] == {"good": th.RMSEA.good, "acceptable": th.RMSEA.acceptable}


def test_srmr_local_conflict_pinned():
    """srmr 本地 0.05/0.08 钉住（与 thresholds.py SRMR 0.08/0.08 的 good 档冲突在档，
    待主班裁以谁为准；裁决②键面已定谳 s930-17）。"""
    assert cfa.FIT_THRESHOLDS["srmr"] == {"good": 0.05, "acceptable": 0.08}
    assert th.SRMR.good == 0.08 and th.SRMR.acceptable == 0.08  # 冲突对侧现值
