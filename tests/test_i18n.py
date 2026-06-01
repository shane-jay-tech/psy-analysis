"""i18n 双语切换测试"""

import pytest
import streamlit as st

from src.utils.i18n import t
from config.settings import get_test_name


class TestI18n:
    def test_zh_translation(self):
        assert t("mean", "zh") == "均值"
        assert t("independent_ttest", "zh") == "独立样本t检验"

    def test_en_translation(self):
        assert t("mean", "en") == "Mean"
        assert t("independent_ttest", "en") == "Independent Samples t-test"

    def test_missing_key_returns_key(self):
        assert t("nonexistent_key", "zh") == "nonexistent_key"

    def test_session_state_language(self):
        st.session_state.clear()
        st.session_state.language = "en"
        assert t("mean") == "Mean"

    def test_get_test_name(self):
        st.session_state.clear()
        st.session_state.language = "zh"
        assert get_test_name("descriptive") == "描述性统计"
        st.session_state.language = "en"
        assert get_test_name("descriptive") == "Descriptive Statistics"

    def test_welch_anova_translation(self):
        assert t("welch_anova", "zh") == "Welch方差分析"
        assert t("welch_anova", "en") == "Welch's ANOVA"
