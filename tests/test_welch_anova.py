"""Welch ANOVA 测试"""

import pytest
import pandas as pd
import numpy as np

from src.analysis.anova import welch_anova, ANOVAResult


class TestWelchANOVA:
    def test_basic_welch_anova(self):
        df = pd.DataFrame({
            "score": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            "group": ["A", "A", "A", "A", "B", "B", "B", "B", "C", "C", "C", "C"],
        })
        result = welch_anova(df, "score", "group")
        assert isinstance(result, ANOVAResult)
        assert result.test_type == "one_way"
        assert not result.table.empty
        assert "F" in result.table.columns
        assert "p" in result.table.columns
        # Welch ANOVA 不应要求方差齐性
        assert result.assumption_homogeneity["passed"] is False
        assert "不要求方差齐性" in result.assumption_homogeneity["note"]

    def test_welch_anova_with_unequal_variance(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "score": list(np.random.normal(0, 1, 30)) + list(np.random.normal(0, 5, 30)),
            "group": ["A"] * 30 + ["B"] * 30,
        })
        result = welch_anova(df, "score", "group")
        assert isinstance(result, ANOVAResult)
        assert result.effect_size_name == "η²"
        assert 0 <= result.effect_size <= 1

    def test_welch_anova_posthoc_games_howell(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "score": list(np.random.normal(0, 1, 20)) +
                     list(np.random.normal(2, 1, 20)) +
                     list(np.random.normal(4, 1, 20)),
            "group": ["A"] * 20 + ["B"] * 20 + ["C"] * 20,
        })
        result = welch_anova(df, "score", "group")
        # 3组且p<0.05时应有Games-Howell事后检验
        assert result.post_hoc is not None
        assert "p (Games-Howell)" in result.post_hoc.columns

    def test_less_than_two_groups_raises(self):
        df = pd.DataFrame({
            "score": [1, 2, 3],
            "group": ["A", "A", "A"],
        })
        with pytest.raises(ValueError, match="至少"):
            welch_anova(df, "score", "group")
