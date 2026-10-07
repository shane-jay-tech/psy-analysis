# -*- coding: utf-8 -*-
"""s1010-11 thresholds.py 常量 golden 钉桩（s1006-01 落地后的防漂移腿）。

口径：与设计稿 psy-thresholds-module-design-20261006 §一登记表逐位对平后，把 2026-10-08
盘面现值逐组钉死；任何字段漂移即红。零生产码改动（统计红线）。
边界：test_reliability_bands 钉的是 **α 档位函数行为**（s920-05 那族），本件钉的是
**thresholds 常量字段值**——面不重叠（行为 vs 常量）。
"""
from src.analysis import thresholds as th

EXPECTED = {
    # name: (good, acceptable, direction, label)
    "CFA": (0.95, 0.90, "ge", "CFI"),
    "TLI": (0.95, 0.90, "ge", "TLI"),
    "RMSEA": (0.05, 0.08, "le", "RMSEA"),
    "SRMR": (0.08, 0.08, "le", "SRMR"),
    "SCVI": (0.90, 0.90, "ge", "S-CVI/Ave"),
    "ICVI": (0.78, 0.78, "ge", "I-CVI"),
    "CVI": (0.80, 0.80, "ge", "CVI"),
    "KMO": (0.80, 0.80, "ge", "KMO"),
    "LOADING": (0.40, 0.40, "ge", "因子载荷"),
    "AVE": (0.50, 0.50, "ge", "AVE"),
    "CR": (0.70, 0.70, "ge", "CR"),
    "ICC": (0.70, 0.70, "ge", "ICC"),
    "SPLIT_HALF": (0.70, 0.70, "ge", "分半信度"),
    "OMEGA": (0.70, 0.60, "ge", "McDonald's ω"),  # acceptable=0.60 §一登记表无出处，盘面照钉留主班核
    "CITC": (0.30, 0.30, "le", "CITC"),
}


def test_golden_threshold_sets():
    """15 组 ThresholdSet 逐组四字段断言（golden，漂移即红）。"""
    assert len(EXPECTED) == 15
    for name, (good, acceptable, direction, label) in EXPECTED.items():
        ts = getattr(th, name)
        assert isinstance(ts, th.ThresholdSet), name
        assert ts.good == good, f"{name}.good"
        assert ts.acceptable == acceptable, f"{name}.acceptable"
        assert ts.direction == direction, f"{name}.direction"
        assert ts.label == label, f"{name}.label"


def test_golden_two_single_values():
    """两单值：CROSS_LOADING=0.30；ALPHA_ITEM_CORR=(0.15, 0.50)。"""
    assert th.CROSS_LOADING == 0.30
    assert th.ALPHA_ITEM_CORR == (0.15, 0.50)


def test_direction_domain():
    """direction 域检查：只允许 ge/le（防手滑写入第三态）。"""
    for name in EXPECTED:
        assert getattr(th, name).direction in ("ge", "le"), name


def test_frozen_immutable():
    """ThresholdSet frozen：改字段必须抛错（防运行期漂移）。"""
    ts = th.CFA
    try:
        ts.good = 0.0  # type: ignore[misc]
    except Exception as exc:
        assert isinstance(exc, (AttributeError, TypeError))
    else:
        raise AssertionError("ThresholdSet 应为 frozen，赋值未抛错")
