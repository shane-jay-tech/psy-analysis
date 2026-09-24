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
        try:
            st.session_state.language = "en"
            assert t("mean") == "Mean"
        finally:
            st.session_state.clear()

    def test_get_test_name(self):
        st.session_state.clear()
        try:
            st.session_state.language = "zh"
            assert get_test_name("descriptive") == "描述性统计"
            st.session_state.language = "en"
            assert get_test_name("descriptive") == "Descriptive Statistics"
        finally:
            st.session_state.clear()

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


# ══════════════════════════════════════════════════════════════════════════
# s924-22：本件 ↔ `config/settings.py::TEST_NAMES_ZH` 键集一致性对拍
# 补的是 s923-17 F3 的缺口（原文见 `zcode-bridge/done/s923-17.result.md:67`）：
# 「`tests/test_i18n.py` 与 `config/settings.py:TEST_NAMES_ZH` 之间**零一致性断言**（F3）⇒
#   两表可各自漂移而门禁不响」——本块就是那声门禁。**只比键集，不比文案值**（任务书硬约束）。
#
# 取数口径（绑磁盘 AST 实取，不 import 本件、不执行 app）：
#   `_i18n_referenced_keys()` 扫本文件源码，收 `t()` / `get_test_name()` / `get_test_name_zh()`
#   三个入口的**首参字符串字面量** ＋ `parametrize("key,…"）` 表格首列，去重后剔哨兵键，
#   得「本件声称存在的检验键集」。
#   复算命令（现取时点 2026-09-25T05:0x）：
#     $ .venv\Scripts\python.exe -c "from config.settings import TEST_NAMES_ZH; print(len(TEST_NAMES_ZH))" → 48
#     本件真键 11 枚：与 TEST_NAMES_ZH 交集 9、差集 2（`mean`/`reliability`，两枚都在
#     `src/utils/i18n.py::TRANSLATIONS["zh"]` 里，即「走另一张表」的活样本，不是孤儿键）。
#
# 为什么收「子集＋固化差集」而不是「键集相等」（任务书留的口径选择）：
#   差集实测**非空**（2 枚）⇒ 一上来钉「相等」必红；按卷宗「先实测差集，若非空先落 result 记录再收紧」，
#   这里把两个方向都钉死：交集固化（TEST_NAMES_ZH 掉一件在用的键→红）、
#   差集固化（有人给 TEST_NAMES_ZH 补了 `mean`/`reliability`→红，提醒回写本块；
#   有人在本件引用了两张表都没有的新键→红，防孤儿键）。
#
# ⚠ 维护提示：本块自身**不得**新增 `t("…")` / `get_test_name("…")` / `get_test_name_zh("…")`
#   形态的字面量首参调用——那会让「件内真键数」自己 +1，把上面的锚点读数改成假红。
# ══════════════════════════════════════════════════════════════════════════

# 现值内联（完成标准③：执行时实测两侧数）
SETTINGS_TABLE_KEY_COUNT = 48  # config/settings.py::TEST_NAMES_ZH
I18N_REFERENCED_KEY_COUNT = 11  # 本件 AST 读出的真键数（已剔哨兵）

# 哨兵键：故意测「查不到就原样回键名」的路径，不属于任何表，必须显式声明而不是被静默放行。
SENTINEL_PROBE_KEYS = frozenset({"", "nonexistent_key"})

# 交集锚点：本件在用、且 TEST_NAMES_ZH 也登记了的键（9 枚，排序固化便于红名直读）。
I18N_KEYS_ALSO_IN_SETTINGS = [
    "descriptive",
    "hierarchical_regression",
    "independent_ttest",
    "mann_whitney",
    "mediation",
    "one_way_anova",
    "paired_ttest",
    "pearson_corr",
    "welch_anova",
]

# 差集锚点：本件在用、但 TEST_NAMES_ZH **没有**的键（2 枚）——s923-17 说的那处漂移面。
I18N_KEYS_MISSING_FROM_SETTINGS = ["mean", "reliability"]


def _i18n_referenced_keys() -> set[str]:
    """AST 扫本文件源码 → 三处取键入口的首参字面量 ＋ parametrize 表首列（不执行本件）。"""
    import ast
    import pathlib

    source = pathlib.Path(__file__).resolve().read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(pathlib.Path(__file__).resolve()))
    entry_functions = {"t", "get_test_name", "get_test_name_zh"}
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Name)
                and func.id in entry_functions
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                found.add(node.args[0].value)
            elif (
                isinstance(func, ast.Attribute)
                and func.attr == "parametrize"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value.split(",")[0].strip() == "key"
            ):
                for row in node.args[1].elts:
                    if isinstance(row, ast.Tuple) and isinstance(row.elts[0], ast.Constant):
                        if isinstance(row.elts[0].value, str):
                            found.add(row.elts[0].value)
    if not found:
        raise AssertionError("本件里 AST 一个取键调用都没读到——提取器与文件形态不符，看守已失效")
    return found


class TestSettingsTableNameKeyConsistency:
    """s924-22 补面：件内键集与 `TEST_NAMES_ZH` 键集的双向对拍（**不碰文案值**）。"""

    def test_referenced_keys_match_settings_table_key_set(self):
        from config.settings import TEST_NAMES_ZH

        referenced = _i18n_referenced_keys()
        real = referenced - SENTINEL_PROBE_KEYS
        settings_keys = set(TEST_NAMES_ZH)

        # 哨兵防线：声明过的探针键必须仍在件内出现（有人删了负例用例，这里先红，免得锚点空转）
        assert SENTINEL_PROBE_KEYS <= referenced, (
            f"哨兵键 {sorted(SENTINEL_PROBE_KEYS - referenced)} 已不在本件被引用——"
            "请同步删掉 SENTINEL_PROBE_KEYS 或恢复对应负例"
        )

        shared = real & settings_keys
        missing = real - settings_keys

        assert sorted(shared) == I18N_KEYS_ALSO_IN_SETTINGS, (
            f"件内与 TEST_NAMES_ZH 的交集漂移：只剩={sorted(shared)}，锚点={I18N_KEYS_ALSO_IN_SETTINGS}；"
            f"掉的是 {sorted(set(I18N_KEYS_ALSO_IN_SETTINGS) - shared)}（settings 表删了在用键？）"
        )
        assert sorted(missing) == I18N_KEYS_MISSING_FROM_SETTINGS, (
            f"件内引用但 TEST_NAMES_ZH 没有的键漂移：实读={sorted(missing)}，锚点={I18N_KEYS_MISSING_FROM_SETTINGS}"
            "（若有人给 settings 表补了 mean/reliability，请把该键移进交集清单并同步 s923-17 的结论）"
        )
        assert not (shared & missing), "交集与差集不该有重叠（重叠说明提取器读了两遍同一个键）"
        assert len(shared) + len(missing) == len(real) == I18N_REFERENCED_KEY_COUNT, (
            f"基数不闭合：交集 {len(shared)} ＋ 差集 {len(missing)} ≠ 件内真键 {len(real)}"
            f"（锚点真键数 {I18N_REFERENCED_KEY_COUNT}）"
        )
        assert len(settings_keys) == SETTINGS_TABLE_KEY_COUNT, (
            f"TEST_NAMES_ZH 键数从 {SETTINGS_TABLE_KEY_COUNT} 变成 {len(settings_keys)}："
            "本件锚点需按现值重取，并回写 docs/insights/psy-dup-method-text-tables-20260924.md 的 T1 计数"
        )

        # 孤儿键防线：件内真键至少要在两张表之一登记（都在 i18n 表就是「走另一入口」，不算孤儿）。
        orphans = sorted(real - settings_keys - set(TRANSLATIONS["zh"]))
        assert orphans == [], f"本件引用了两张表都没有的孤儿键：{orphans}"

