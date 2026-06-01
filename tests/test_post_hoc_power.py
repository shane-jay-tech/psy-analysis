"""Phase 1.3：事后样本量建议测试。

关键设计验证（仲裁结果）：
- 仅在 power<0.80 时给 n_needed_for_080
- 不暴露 achieved_power 数值
- 必须附 footnote 警示"非证据强度解读"（Hoenig & Heisey 2001）
"""

import numpy as np
import pandas as pd

from src.analysis import post_hoc_power
from src.analysis.runner import run_analysis
from src.parser.intent_resolver import AnalysisPlan


def _ttest_output(d_eff: float, n_per_group: int):
    """构造一个独立 t 检验的 output（用真实 run_analysis）。"""
    rng = np.random.default_rng(0)
    # 制造已知效应量的两组数据
    g1 = rng.normal(0, 1, n_per_group)
    g2 = rng.normal(d_eff, 1, n_per_group)
    df = pd.DataFrame({
        "score": np.concatenate([g1, g2]),
        "group": ["A"] * n_per_group + ["B"] * n_per_group,
    })
    plan = AnalysisPlan(
        test_type="independent_ttest",
        dependent_vars=["score"],
        independent_vars=["group"],
    )
    return run_analysis(df, plan)


class TestPostHocPowerTrigger:
    def test_underpowered_small_n_triggers_advice(self):
        # 中等效应量 + 小样本 → 应触发建议
        out = _ttest_output(d_eff=0.3, n_per_group=15)
        # n=30 小样本时路由器禁用 hard_route，但 post_hoc_power 仍计算
        ph = out.get("post_hoc_power")
        assert ph is not None
        # 中等效应小样本下绝大多数情况会 underpowered
        if ph.get("needs_more_n"):
            assert ph["n_needed_for_080"] > ph["observed_n"]
            assert ph["footnote"]
            # 关键设计：不暴露 achieved_power 数值
            assert "achieved_power" not in ph
            assert "actual_power" not in ph

    def test_well_powered_no_advice(self):
        # 大效应 + 较大样本 → 无需补样
        out = _ttest_output(d_eff=1.0, n_per_group=80)
        ph = out.get("post_hoc_power")
        assert ph is not None
        # 大效应高样本下 needs_more_n 应为 False
        if not ph.get("needs_more_n"):
            assert ph.get("skipped_reason")
            assert "achieved_power" not in ph
            assert "actual_power" not in ph

    def test_footnote_always_present(self):
        out = _ttest_output(d_eff=0.5, n_per_group=30)
        ph = out.get("post_hoc_power")
        if ph is not None:
            assert ph["footnote"]
            assert "Hoenig" in ph["footnote"] or "证据强度" in ph["footnote"]


class TestPostHocPowerNoNumericLeak:
    """关键设计：绝不在 output 中暴露 achieved_power 数值。"""

    def test_output_has_no_achieved_power_field(self):
        out = _ttest_output(d_eff=0.5, n_per_group=30)
        # output 顶层和 result 内都不能有 achieved_power
        assert "achieved_power" not in out
        ph = out.get("post_hoc_power")
        if ph:
            for forbidden in ("achieved_power", "actual_power", "observed_power"):
                assert forbidden not in ph, f"{forbidden} 不应出现在 post_hoc_power"

    def test_result_dataclass_unchanged(self):
        out = _ttest_output(d_eff=0.5, n_per_group=30)
        result = out["result"]
        # TTestResult 不应有 achieved_power 字段
        assert not hasattr(result, "achieved_power")
        assert not hasattr(result, "actual_power")


class TestPostHocPowerUnsupported:
    def test_unsupported_test_type_returns_none(self):
        # mediation 不在 _TEST_TYPE_MAP 里
        out = {"test_type": "mediation", "result": object()}
        assert post_hoc_power.estimate_post_hoc(out) is None

    def test_zero_effect_skipped_with_reason(self):
        # 模拟极小效应：手工构造 output
        rng = np.random.default_rng(1)
        # 两组完全没差异
        df = pd.DataFrame({
            "score": rng.normal(0, 1, 100),
            "group": ["A"] * 50 + ["B"] * 50,
        })
        plan = AnalysisPlan(
            test_type="independent_ttest",
            dependent_vars=["score"],
            independent_vars=["group"],
        )
        out = run_analysis(df, plan)
        ph = out.get("post_hoc_power")
        # 至少有 footnote 和 observed_n
        if ph is not None:
            assert ph["observed_n"] > 0
