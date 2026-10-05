# -*- coding: utf-8 -*-
"""s1002-09：清洗链 _CLEANED_KEY 写入面＋_render_results AppTest 补钉（纯人造数值）。

来账：s921-15 遗留 2（:155-163 点击写入点无人测——它在统计结论域边上）＋
s922-10 遗留 4（_render_results / get_cleaning_log_for_deliverable 补面；后者
「有 result 但 log 为空」形态由兄弟件补过，本件不重复）。

🔴 统计红线（本件承重墙）：夹具=全题恒定值（每人四题全同值，触发同质作答过滤）——
无效样本判定/维度得分等**数值结论一个不断**；断言只落三类：键存在性/对象类型/
summary **键集合相等**（新增键会红＝提醒同步本钉，键名不含数值）。

AppTest 真运行时（本文件名已在 conftest::_APP_TEST_FILES 白名单，s924-01 登记，
沙盒隔离由 autouse 夹具供给；另有 feed_sandbox 双保险）。
"""
from __future__ import annotations

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import src.ui.questionnaire_import_panel as qip
from src.questionnaire.import_cleaning import CleaningResult

# 纯人造：4 题全恒定（每行同一取值），时长全低于 60s 阈值 ⇒ 同质+时长双过滤都会咬。
# 断言面零数值：不写「valid_n==几」——只看键/类型/键集合。
_CONSTANT_CSV = (
    b"Q1,Q2,Q3,Q4,gender,duration_sec\n"
    b"3,3,3,3,a,30\n"
    b"3,3,3,3,b,30\n"
    b"3,3,3,3,c,30\n"
    b"3,3,3,3,d,30\n"
)
_KEY_RAW = "questionnaire_raw_df"
_KEY_DIMS = "questionnaire_dimensions"
BTN_CLEAN = "执行清洗与计分"

_PANEL_SCRIPT = """
import sys
if "__ROOT__" not in sys.path:
    sys.path.insert(0, "__ROOT__")
from src.ui.questionnaire_import_panel import render_questionnaire_import_panel

render_questionnaire_import_panel()
""".replace("__ROOT__", str(__import__("pathlib").Path(__file__).resolve().parents[1]))


@pytest.fixture
def feed_sandbox(monkeypatch, tmp_path):
    root = tmp_path / "feed_root"
    monkeypatch.setenv("LITERATURE_FEED_DATA_ROOT", str(root))
    return root


def _aptest(feed_sandbox) -> AppTest:
    at = AppTest.from_string(_PANEL_SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, f"主干渲染抛异常：{[e.value for e in at.exception]}"
    return at


def _upload(at: AppTest) -> AppTest:
    at.file_uploader[0].set_value(("const.csv", _CONSTANT_CSV, "text/csv")).run()
    assert not at.exception
    return at


def _click(at: AppTest, label: str) -> AppTest:
    hits = [b for b in at.button if b.label == label]
    assert len(hits) == 1, f"按钮「{label}」唯一锚点失效"
    hits[0].click().run()
    assert not at.exception, f"点「{label}」抛异常：{[e.value for e in at.exception]}"
    return at


EXPECTED_SUMMARY_KEYS = {
    "original_n", "valid_n", "invalid_n",
    "item_columns", "dimensions_scored",
    "out_of_range_cells", "out_of_range_rows", "out_of_range_cells_after_filter",
}


# ---------- 写入点（:155-163 现取）：点击后 _CLEANED_KEY 三断言 ----------

def test_click_writes_cleaned_key_with_expected_shape(feed_sandbox):
    at = _click(_upload(_aptest(feed_sandbox)), BTN_CLEAN)
    ss = at.session_state
    assert qip._CLEANED_KEY in ss, "点击清洗后 _CLEANED_KEY 未写入 session_state"
    result = ss[qip._CLEANED_KEY]
    assert isinstance(result, CleaningResult), f"类型漂移：{type(result)}"
    assert set(result.summary.keys()) == EXPECTED_SUMMARY_KEYS, (
        f"summary 键集合漂移（新增/删键需同步本钉）：{set(result.summary) ^ EXPECTED_SUMMARY_KEYS}")
    assert isinstance(result.df_cleaned, pd.DataFrame)
    assert isinstance(result.log, list)


def test_click_writes_via_button_not_import_side_effect(feed_sandbox):
    """负对照：只上传不点击 ⇒ 键不存在（写入点确实挂在按钮回调后面）。"""
    at = _upload(_aptest(feed_sandbox))
    assert qip._CLEANED_KEY not in at.session_state


def test_success_banner_renders_after_clean(feed_sandbox):
    at = _click(_upload(_aptest(feed_sandbox)), BTN_CLEAN)
    assert any("清洗完成" in str(s.value) for s in at.success), "成功横幅未渲染"


# ---------- 消费面（_render_results）与摊平面 ----------

def test_render_results_consumes_the_clicked_result(feed_sandbox):
    at = _click(_upload(_aptest(feed_sandbox)), BTN_CLEAN)
    # 三个 metric 的 label 在场（数值断言零——label 是结构、value 是统计结论域）
    labels = [m.label for m in at.metric]
    for want in ("原始样本", "有效样本", "剔除样本"):
        assert want in labels, f"摘要 metric「{want}」未渲染"
    assert any("### 清洗日志" in str(m.value) for m in at.markdown)
    assert any("📥 下载清洗日志" in str(b.label) for b in at.download_button)


def test_deliverable_flatten_matches_log_entries(feed_sandbox):
    """get_cleaning_log_for_deliverable：摊平字段五键逐条对应 log（零数值断言）。

    注：AppTest 的 session_state 不支持 .get()（生产码 :203 用 .get 读键 ⇒ 真运行时
    不能直接喂 at.session_state），故摊平例走「同帧提取的 result 回灌普通 dict」——
    会话内容与点击帧逐位一致（AppTest state 在 .run() 后即冻结为该帧值）。
    """
    at = _click(_upload(_aptest(feed_sandbox)), BTN_CLEAN)
    result = at.session_state[qip._CLEANED_KEY]
    plain_state = {qip._CLEANED_KEY: result}
    flat = qip.get_cleaning_log_for_deliverable(plain_state)
    assert isinstance(flat, list) and len(flat) == len(result.log)
    for row, entry in zip(flat, result.log):
        assert set(row.keys()) == {"step", "action", "affected_rows",
                                   "affected_cols", "detail"}
        assert row["step"] == entry.step and row["action"] == entry.action
