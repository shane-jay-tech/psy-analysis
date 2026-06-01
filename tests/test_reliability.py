"""测试信度分析模块"""
import pandas as pd
import numpy as np
from src.analysis.reliability import cronbach_alpha, split_half_reliability, ReliabilityResult


def test_cronbach_alpha_basic():
    """Cronbach's α 基本测试 — 使用高度相关的题目"""
    np.random.seed(42)
    n = 200
    true_score = np.random.normal(0, 1, n)
    items = {
        f"item{i}": true_score + np.random.normal(0, 0.3, n)
        for i in range(1, 6)
    }
    df = pd.DataFrame(items)
    result = cronbach_alpha(df, list(items.keys()))
    assert isinstance(result, ReliabilityResult)
    assert result.test_type == "cronbach_alpha"
    assert result.alpha > 0.7  # 高相关题目应有高α
    assert result.item_stats is not None
    assert len(result.item_stats) == 5


def test_cronbach_alpha_low_reliability():
    """Cronbach's α — 低一致性情况"""
    np.random.seed(42)
    df = pd.DataFrame({
        "item1": np.random.normal(0, 1, 100),
        "item2": np.random.normal(0, 1, 100),
        "item3": np.random.normal(0, 1, 100),
    })
    result = cronbach_alpha(df, ["item1", "item2", "item3"])
    assert result.alpha < 0.7  # 不相关题目应有低α


def test_split_half_basic():
    """分半信度基本测试"""
    np.random.seed(42)
    n = 100
    true_score = np.random.normal(0, 1, n)
    items = {
        f"q{i}": true_score + np.random.normal(0, 0.5, n)
        for i in range(1, 9)
    }
    df = pd.DataFrame(items)
    result = split_half_reliability(df, list(items.keys()))
    assert isinstance(result, ReliabilityResult)
    assert result.split_half_r is not None
    assert 0 <= result.alpha <= 1
