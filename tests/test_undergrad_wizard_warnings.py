# -*- coding: utf-8 -*-
"""src/ui/undergrad_wizard.py 三个「警告渲染器」钉桩（s920-15）。

锚点（实测仍成立）：`:945 render_pii_warning(df)`、`:1729 render_common_mistake_warnings(output, df, plan)`、
`:1824 render_assumption_failure_guidance(output, plan, df)` —— 三符号此前在 `tests/` 里**零命中**，
唯一调用方是 `app.py:1109 / :1401 / :1404`。

只钉「哪条分支被走到 + 落了什么提示/按钮键」，**不判断任何统计数值、不给结论背书**：
  · `detect_pii_columns` / `hash_column` 打在**源模块属性**上（函数体内部 `from ... import`，每次执行重读）；
  · `st` 整体换成假对象，未预期的 `st.*` 调用当场 assert 红（宁可红，也不要"悄悄走了别的路径还测绿"）；
  · 假数据都是手造两行，不读任何真实问卷。
"""
import pandas as pd
import pytest

import src.ui.undergrad_wizard as uw
import src.utils.guardrails as gr


class FakeState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


class FakeSt:
    """记录式假 st。`button_click=True` 时所有按钮都返回「被点了」。"""

    def __init__(self, button_click=False, state=None):
        self.session_state = state if state is not None else FakeState()
        self._button_click = button_click
        self.errors, self.warnings, self.successes, self.infos = [], [], [], []
        self.captions, self.writes, self.markdowns, self.expanders = [], [], [], []
        self.buttons, self.reruns = [], 0

    def error(self, msg, **k):
        self.errors.append(msg)

    def warning(self, msg, **k):
        self.warnings.append(msg)

    def success(self, msg, **k):
        self.successes.append(msg)

    def info(self, msg, **k):
        self.infos.append(msg)

    def caption(self, msg, **k):
        self.captions.append(msg)

    def write(self, msg, **k):
        self.writes.append(msg)

    def markdown(self, msg, **k):
        self.markdowns.append(msg)

    def button(self, label, **k):
        self.buttons.append((label, k.get("key")))
        return self._button_click

    def rerun(self, **k):
        self.reruns += 1

    class _expander_ctx:
        def __init__(self, host, label, **k):
            self.host, self.label = host, label
            self.kwargs = k

        def __enter__(self):
            self.host.expanders.append((self.label, self.kwargs))
            return None

        def __exit__(self, *exc):
            return False

    def expander(self, label, **k):
        return FakeSt._expander_ctx(self, label, **k)

    def __getattr__(self, name):
        raise AssertionError(f"未预期调用 st.{name}")


@pytest.fixture
def pii(monkeypatch):
    """把 PII 检测/哈希换成可控桩，返回 (假 st, 记录本)。"""
    calls = {"detect": 0, "hash": []}

    def fake_detect(df):
        calls["detect"] += 1
        return calls["pii"]

    def fake_hash(df, col):
        calls["hash"].append(col)
        if isinstance(calls.get("hash_error"), Exception):
            raise calls["hash_error"]
        return pd.Series([f"<{c}>" for c in df[col]])

    monkeypatch.setattr(gr, "detect_pii_columns", fake_detect)
    monkeypatch.setattr(gr, "hash_column", fake_hash)
    return calls


def _run_pii(st, pii, df=None, any_flag=True, **more):
    pii["pii"] = {"high": [], "medium": [], "low": [], "any": any_flag, **more}
    frame = df
    if isinstance(frame, dict):
        frame = pd.DataFrame(frame)
    elif frame is None:
        frame = pd.DataFrame({"学号": ["S1", "S2"]})
    uw.render_pii_warning(frame)


# ────────────────────────── render_pii_warning ──────────────────────────
def test_pii_any_flag_is_the_only_gate_list_content_does_not_count(pii, monkeypatch):
    """`any` 是唯一总开关：它 False 时即便 high/medium 列了列名也一个字都不出。"""
    st = FakeSt()
    monkeypatch.setattr(uw, "st", st)
    _run_pii(st, pii, any_flag=False, high=["姓名"], medium=["学号"], low=["编号"])

    assert pii["detect"] == 1
    assert st.errors == st.warnings == st.successes == st.markdowns == []
    assert st.expanders == [] and st.buttons == [] and st.reruns == 0


def test_pii_high_uses_error_and_quotes_column_names(pii, monkeypatch):
    st = FakeSt()
    monkeypatch.setattr(uw, "st", st)
    _run_pii(st, pii, high=["姓名", "手机"])

    assert len(st.errors) == 1 and st.warnings == []
    msg = st.errors[0]
    assert "高敏感信息预警" in msg
    assert "`姓名`" in msg and "`手机`" in msg  # 列名逐个回显，用户才知道删哪列
    assert st.buttons == []  # 高危只让删，不给"一键脱敏"


def test_pii_medium_prompts_but_does_not_touch_data_until_clicked(pii, monkeypatch):
    st = FakeSt(button_click=False)
    monkeypatch.setattr(uw, "st", st)
    _run_pii(st, pii, medium=["学号"])

    assert len(st.warnings) == 1 and "可识别身份信息" in st.warnings[0]
    assert st.buttons == [("🔐 一键脱敏（哈希这些列）", "_pii_hash_all")]
    assert pii["hash"] == [] and st.successes == [] and st.reruns == 0  # 没点就不许改数据


def test_pii_medium_click_hashes_every_col_then_reruns(pii, monkeypatch):
    st = FakeSt(button_click=True)
    monkeypatch.setattr(uw, "st", st)
    df = pd.DataFrame({"学号": ["S1", "S2"], "姓名": ["甲", "乙"]})
    _run_pii(st, pii, df=df, medium=["学号", "姓名"])

    assert pii["hash"] == ["学号", "姓名"]
    assert list(df["学号"]) == ["<S1>", "<S2>"] and list(df["姓名"]) == ["<甲>", "<乙>"]
    assert st.successes == ["✅ 已对 2 个列做哈希脱敏；后续分析将使用脱敏后值。"]
    assert st.reruns == 1


def test_pii_medium_hash_failure_stays_visible_and_no_rerun(pii, monkeypatch):
    st = FakeSt(button_click=True)
    monkeypatch.setattr(uw, "st", st)
    pii["hash_error"] = RuntimeError("列不存在")
    _run_pii(st, pii, medium=["学号", "身份证"])

    assert len(st.errors) == 1 and st.errors[0].startswith("脱敏失败：")
    assert "列不存在" in st.errors[0]
    assert st.successes == [] and st.reruns == 0  # 失败不许谎报成功、不许悄悄重跑


def test_pii_low_only_goes_into_collapsed_expander(pii, monkeypatch):
    st = FakeSt()
    monkeypatch.setattr(uw, "st", st)
    _run_pii(st, pii, low=["编号", "题号"])

    assert st.errors == st.warnings == []
    assert len(st.expanders) == 1
    label, kwargs = st.expanders[0]
    assert "2 个" in label and kwargs == {"expanded": False}  # 弱标识默认折叠
    assert any("P001" in c for c in st.captions)
    assert st.writes == ["`编号`、`题号`"]


# ──────────────────── render_common_mistake_warnings ────────────────────
def _plan(test_type, ivs=(), dvs=()):
    from types import SimpleNamespace

    return SimpleNamespace(test_type=test_type, independent_vars=list(ivs), dependent_vars=list(dvs))


def test_cmw_none_plan_silence(monkeypatch):
    st = FakeSt()
    monkeypatch.setattr(uw, "st", st)
    uw.render_common_mistake_warnings({"test_type": "pearson_corr"}, None, None)

    assert st.markdowns == [] and st.errors == st.warnings == []


def test_cmw_multiple_dv_ttest_flagged_with_count(monkeypatch):
    st = FakeSt()
    monkeypatch.setattr(uw, "st", st)
    plan = _plan("independent_ttest", ivs=["组别"], dvs=["成绩", "满意度"])
    uw.render_common_mistake_warnings({}, pd.DataFrame({"x": [1.0] * 40}), plan)

    joined = "".join(st.markdowns)
    assert "多次比较提醒" in joined and "你同时对 2 个因变量" in joined
    assert "Bonferroni" in joined


def test_cmw_single_dv_and_non_ttest_both_skip_multi_compare(monkeypatch):
    """dv_count<=1 或 test_type 不在 t/Mann-Whitney 之列 ⇒ 都不该弹多次比较。"""
    df = pd.DataFrame({"x": [1.0] * 40})
    for plan in (_plan("pearson_corr", dvs=["a", "b"]), _plan("independent_ttest", dvs=["a"])):
        st = FakeSt()
        monkeypatch.setattr(uw, "st", st)
        uw.render_common_mistake_warnings({}, df, plan)
        assert "多次比较提醒" not in "".join(st.markdowns)


def test_cmw_test_type_falls_back_to_output_when_plan_lacks_attr(monkeypatch):
    st = FakeSt()
    monkeypatch.setattr(uw, "st", st)
    plan = object()  # 无 test_type / independent_vars / dependent_vars
    uw.render_common_mistake_warnings({"test_type": "pearson_corr"}, None, plan)

    joined = "".join(st.markdowns)
    assert "相关 ≠ 因果" in joined  # test_type 从 output 取到了
    assert "多次比较提醒" not in joined  # 缺 iv/dv 属性时计数按 0，不许炸


def test_cmw_missing_and_small_sample_warnings_read_from_df(monkeypatch):
    st = FakeSt()
    monkeypatch.setattr(uw, "st", st)
    df = pd.DataFrame({"a": [1.0, None], "b": [2.0, 3.0]})
    uw.render_common_mistake_warnings({}, df, _plan("mediation", ivs=["x"], dvs=["y"]))

    joined = "".join(st.markdowns)
    assert "中介效应分析前提" in joined
    assert "缺失数据提醒" in joined and "1 个缺失值（25.0%）" in joined and "<strong>缺失列：</strong>a" in joined
    assert "小样本提醒" in joined and "当前数据仅 2 行" in joined


def test_cmw_small_sample_threshold_is_exactly_30_rows(monkeypatch):
    """n<30 是写死的经验阈值，挪动它必须让本用例红（M6 变异测出来的口径）。"""

    def markdowns_for(n_rows):
        st = FakeSt()
        monkeypatch.setattr(uw, "st", st)
        df = pd.DataFrame({"a": [float(i) for i in range(n_rows)], "b": [1.0] * n_rows})
        uw.render_common_mistake_warnings({}, df, _plan("pearson_corr", dvs=["a", "b"]))
        return "".join(st.markdowns)

    assert "小样本提醒" in markdowns_for(29)
    assert "小样本提醒" not in markdowns_for(30)


def test_cmw_anova_posthoc_hint_only_when_more_than_two_levels(monkeypatch):
    st_yes, st_no = FakeSt(), FakeSt()
    df3 = pd.DataFrame({"g": ["a", "b", "c"], "y": [1.0, 2.0, 3.0]})
    monkeypatch.setattr(uw, "st", st_yes)
    uw.render_common_mistake_warnings({}, df3, _plan("one_way_anova", ivs=["g"], dvs=["y"]))
    monkeypatch.setattr(uw, "st", st_no)
    df2 = pd.DataFrame({"g": ["a", "b"], "y": [1.0, 2.0]})
    uw.render_common_mistake_warnings({}, df2, _plan("one_way_anova", ivs=["g"], dvs=["y"]))

    assert "事后比较提示" in "".join(st_yes.markdowns)
    assert "事后比较提示" not in "".join(st_no.markdowns)


# ────────────────── render_assumption_failure_guidance ──────────────────
def test_afg_none_input_silence(monkeypatch):
    st = FakeSt()
    monkeypatch.setattr(uw, "st", st)
    uw.render_assumption_failure_guidance(None, _plan("independent_ttest"), None)
    uw.render_assumption_failure_guidance({"assumptions": {"normality": {"passed": False}}}, None, None)

    assert st.markdowns == [] and st.buttons == [] and st.reruns == 0


def _run_afg(monkeypatch, plan, output, df=None):
    st = FakeSt()
    monkeypatch.setattr(uw, "st", st)
    uw.render_assumption_failure_guidance(output, plan, df if df is not None else pd.DataFrame({"y": [1.0, 2.0]}))
    return st


def test_afg_normality_fail_recommends_nonparametic_sibling(monkeypatch):
    st = _run_afg(
        monkeypatch,
        _plan("independent_ttest", ivs=["g"], dvs=["y"]),
        {"assumptions": {"normality": {"passed": False}}},
    )
    joined = "".join(st.markdowns)
    assert "假设条件不满足" in joined and "Mann-Whitney U 检验" in joined
    assert "检测到问题：</strong>正态性检验未通过<" in joined
    assert st.buttons == [("🔄 一键切换为 Mann-Whitney U 检验", "switch_mann_whitney")]


def test_afg_homogeneity_only_recommends_welch(monkeypatch):
    st = _run_afg(
        monkeypatch,
        _plan("one_way_anova", ivs=["g"], dvs=["y"]),
        {"assumptions": {"homogeneity": {"passed": False}}},
    )
    joined = "".join(st.markdowns)
    assert "Welch ANOVA" in joined and "方差齐性假设不满足" in joined
    assert "Mann-Whitney" not in joined  # 只丢方差齐性时不许升级成非参数


def test_afg_both_fail_reasons_are_both_reported(monkeypatch):
    st = _run_afg(
        monkeypatch,
        _plan("pearson_corr", dvs=["a", "b"]),
        {"assumptions": {"normality": {"passed": False}, "homogeneity": {"passed": False}}},
    )
    joined = "".join(st.markdowns)
    assert "正态性检验未通过；方差齐性假设不满足" in joined
    assert "Spearman 等级相关" in joined


def test_afg_error_message_text_path_also_triggers(monkeypatch):
    st = _run_afg(
        monkeypatch,
        _plan("paired_ttest", dvs=["y"]),
        {"errors": [{"message": " Shapiro 检验：数据不符合正态分布"}], "assumptions": {}},
    )
    joined = "".join(st.markdowns)
    assert "Wilcoxon 符号秩检验" in joined and st.buttons[0][1] == "switch_wilcoxon"


def test_afg_already_welch_short_circuits_the_switch_button(monkeypatch):
    from types import SimpleNamespace

    st = _run_afg(
        monkeypatch,
        _plan("independent_ttest", ivs=["g"], dvs=["y"]),
        {
            "assumptions": {"homogeneity": {"passed": False}},
            "result": SimpleNamespace(is_welch=True),
        },
    )
    joined = "".join(st.markdowns)
    assert "方差不齐已自动处理" in joined and "无需切换方法" in joined
    assert st.buttons == [] and st.reruns == 0  # 已经 Welch 过了，不再推销切换


def test_afg_list_shaped_assumptions_are_all_counted_as_normality(monkeypatch):
    """现状：list 形态**不分 key** —— 方差齐性以 list 报失败也会被记成"正态性未通过"，
    于是走非参数路线而不是 Welch。只钉不改（与 dict 形态的两条对照着看）。"""
    st = _run_afg(
        monkeypatch,
        _plan("independent_ttest", ivs=["g"], dvs=["y"]),
        {"assumptions": {"homogeneity": [{"passed": True}, {"passed": False}]}},
    )
    joined = "".join(st.markdowns)
    assert "正态性检验未通过" in joined and "方差齐性假设不满足" not in joined
    assert "Mann-Whitney U 检验" in joined and "Welch" not in joined


def test_afg_test_type_without_mapped_alternative_stays_silent(monkeypatch):
    st = _run_afg(
        monkeypatch,
        _plan("mediation", ivs=["x"], dvs=["y"]),
        {"assumptions": {"normality": {"passed": False}}},
    )
    assert st.markdowns == [] and st.buttons == [] and st.reruns == 0
