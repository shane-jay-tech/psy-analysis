"""i18n 双语切换测试"""

import pytest
import streamlit as st

from src.utils.i18n import TRANSLATIONS, get_test_name_zh, t
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


class TestGetTestNameZh:
    """`get_test_name_zh`（src/utils/i18n.py:269）双语钉桩（s920-11）。

    此前全树零命中：本文件只 import 了 `t`，而这个"名字里写着 zh、其实双语都吃"的
    转发函数才是界面层真正在调的那个。
    """

    @pytest.mark.parametrize(
        "key,zh,en",
        [
            ("independent_ttest", "独立样本t检验", "Independent Samples t-test"),
            ("paired_ttest", "配对样本t检验", "Paired Samples t-test"),
            ("mann_whitney", "Mann-Whitney U检验", "Mann-Whitney U Test"),
            ("one_way_anova", "单因素方差分析", "One-Way ANOVA"),
            ("pearson_corr", "Pearson相关分析", "Pearson Correlation"),
            ("welch_anova", "Welch方差分析", "Welch's ANOVA"),
            ("descriptive", "描述性统计", "Descriptive Statistics"),
            ("reliability", "信度分析", "Reliability Analysis"),
            ("mediation", "中介效应分析", "Mediation Analysis"),
            ("hierarchical_regression", "分层回归", "Hierarchical Regression"),
        ],
    )
    def test_common_test_keys_have_both_languages(self, key, zh, en):
        assert get_test_name_zh(key, "zh") == zh
        assert get_test_name_zh(key, "en") == en

    def test_name_says_zh_but_explicit_lang_wins(self):
        """命名坑：函数叫 `_zh`，传 `lang="en"` 就给英文——不是"永远中文"。

        顺带钉一处测试卫生：`lang=None` 走的是**全局** `st.session_state["language"]`，
        前面用例设过 "en" 就会漏下来（本仓现测就有这个残留），所以这里必须显式设态。
        """
        st.session_state.clear()
        try:
            st.session_state.language = "zh"
            assert get_test_name_zh("independent_ttest") == "独立样本t检验"
            assert get_test_name_zh("independent_ttest", "en") == "Independent Samples t-test"
            assert get_test_name_zh("independent_ttest") != get_test_name_zh("independent_ttest", "en")
        finally:
            st.session_state.clear()

    def test_unknown_key_falls_back_to_the_key_verbatim(self):
        assert get_test_name_zh("nonexistent_key", "zh") == "nonexistent_key"
        assert get_test_name_zh("nonexistent_key", "en") == "nonexistent_key"
        assert get_test_name_zh("", "zh") == ""  # 空键也照原样回，不报错也不变 None

    def test_lang_none_follows_session_language_then_default(self):
        st.session_state.clear()
        try:
            st.session_state.language = "en"
            assert get_test_name_zh("mean") == "Mean"
            st.session_state.language = "zh"
            assert get_test_name_zh("mean") == "均值"
            del st.session_state.language
            assert get_test_name_zh("mean") == "均值"  # 缺省回落 DEFAULT_LANG="zh"
        finally:
            st.session_state.clear()

    def test_unsupported_language_degrades_to_default_not_error(self):
        """`TRANSLATIONS.get(lang, 默认)`：不认识的 lang 静默按中文出，不抛、不回键名。"""
        assert get_test_name_zh("mean", "fr") == "均值"
        assert get_test_name_zh("nonexistent_key", "fr") == "nonexistent_key"

    def test_two_language_tables_are_key_symmetric(self):
        """扩容门禁：只往一种语言加词条，本用例就红。"""
        assert set(TRANSLATIONS) == {"zh", "en"}
        assert set(TRANSLATIONS["zh"]) == set(TRANSLATIONS["en"])
        assert len(TRANSLATIONS["zh"]) == 106
        assert all(isinstance(v, str) and v.strip() for table in TRANSLATIONS.values() for v in table.values())
