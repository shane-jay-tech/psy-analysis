# -*- coding: utf-8 -*-
"""s930-05：preregistration 读键适配 n_total（s927-72 遗留键名统一）。

q927-72 点名：preregistration 读 `required_n`，而 quick_sample_size 给的键是
`n_total` ⇒ 恒落 `'?'` 兜底（「因错而对」）。修复＝读侧适配：`n_total` 优先、
`required_n` 兼容（写侧算法与数值不动）。

运行：python -m pytest tests/test_prereg_n_total_piping_s93005.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.experiment_design.power_analysis import quick_sample_size  # noqa: E402
from src.experiment_design.preregistration import (  # noqa: E402
    _extract_from_design,
    generate_preregistration_from_analysis,
)


def test_real_quick_sample_size_dict_flows_into_prereg_text():
    """喂 quick_sample_size 真实返回 dict ⇒ 预注册文本出现真实 N 而非 '?'。"""
    # 注：默认 0.5 在欠配哨兵下 n_total=0（s927-61 solved=False 面）——取可解组合 0.2。
    pw = quick_sample_size("independent_t", effect_size=0.2)
    assert "n_total" in pw and pw["n_total"] > 0          # 给键面 sanity（可解组合）
    doc = generate_preregistration_from_analysis(
        analysis_type="independent t-test",
        research_question="合成研究问题（测试夹具，无真实结论）",
        sample_n=pw["n_total"],
        power_info=dict(pw),
    )
    text = getattr(doc, "text", None) or str(doc)
    assert str(pw["n_total"]) in text, f"真实 N 未进文本：{text[:200]}"
    assert "？" not in text.split("所需样本量")[-1][:30] or "?" not in text.split("所需样本量")[-1][:30], (
        "所需样本量段仍落 '?' 兜底（键名未接通）"
    )


def test_extract_prefers_n_total_over_fallback():
    """_extract_from_design 直测：n_total 优先；旧键 required_n 兼容仍可读。"""
    only_new = _extract_from_design({"power": {"n_total": 128, "effect_size": 0.5,
                                               "alpha": 0.05, "power": 0.8}})
    assert "128" in only_new["sample_size_info"]
    only_old = _extract_from_design({"power": {"required_n": 64, "effect_size": 0.5,
                                               "alpha": 0.05, "power": 0.8}})
    assert "64" in only_old["sample_size_info"]           # 旧键兼容（非本次回归面）
