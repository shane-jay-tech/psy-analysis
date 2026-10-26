# -*- coding: utf-8 -*-
"""s1025-01：SRM 占位三案命名施工钉桩（案A·占位注记）。

选案依据：claims.log D1025-nod#10（2026-10-25 主班拍板「SRM 选案=材料推荐案」），
材料档 artifacts/s-srm-naming.md 推荐案 A「占位注记案」。

口径（红线）：
  * 只钉标签形状：占位 0.0 的展示标签带显式身份注记，不冒充"完美拟合"实测
    （s930-17 定谳：semopy 无 SRMR 键，上游 cfa.py 恒回退 0.0 占位）；
  * 零数值行为变更：effect_sizes 维持 {"name": "SRMR", "value": 0.0} 收录（案A明确，数值主班闸）；
  * 真实非零 SRMR 原样展示，绝不被误标占位（统计呈现面语义安全）。
"""
from dataclasses import dataclass, field

from src.analysis.result_card import build_card_from_output

PLACEHOLDER_NOTE = "（占位值：semopy 未提供 SRMR，不参与拟合判读）"


@dataclass
class _FakeFitResult:
    """只带 fit_indices 的最小结果对象（_build_cfa/_build_sem 消费面）。"""

    fit_indices: dict = field(default_factory=dict)


def _card(method_id: str, srmr_value):
    return build_card_from_output({
        "test_type": method_id,
        "result": _FakeFitResult(fit_indices={
            "chi2": 12.3, "df": 4, "p": 0.015, "CFI": 0.96, "TLI": 0.95,
            "RMSEA": 0.04, "SRMR": srmr_value,
        }),
    })


class TestSrmPlaceholderLabelS102501:
    def test_cfa_card_placeholder_zero_gets_note(self):
        """CFA 卡：占位 0.0 展示标签带显式身份注记（案A候选名逐字）。"""
        card = _card("cfa", 0.0)
        assert f"SRMR = 0.000{PLACEHOLDER_NOTE}" in card.apa_text

    def test_sem_card_placeholder_zero_gets_note(self):
        """SEM 卡：占位 0.0 展示标签带显式身份注记（案A候选名逐字）。"""
        card = _card("sem", 0.0)
        assert f"SRMR = 0.000{PLACEHOLDER_NOTE}" in card.apa_text

    def test_effect_sizes_keeps_zero_value(self):
        """零数值行为变更：effect_sizes 维持占位 0.0 收录（案A明确，两卡同）。"""
        for method_id in ("cfa", "sem"):
            card = _card(method_id, 0.0)
            entry = next(e for e in card.effect_sizes if e["name"] == "SRMR")
            assert entry == {"name": "SRMR", "value": 0.0}, method_id

    def test_real_nonzero_value_unlabeled(self):
        """真实非零 SRMR 原样展示，不带占位注记（不误标）。"""
        for method_id in ("cfa", "sem"):
            card = _card(method_id, 0.056)
            assert f"SRMR = 0.056" in card.apa_text, method_id
            assert PLACEHOLDER_NOTE not in card.apa_text, method_id
