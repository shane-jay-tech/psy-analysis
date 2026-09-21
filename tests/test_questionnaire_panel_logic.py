# -*- coding: utf-8 -*-
"""纯函数单测（零 st、秒级）：classify_questionnaire_sub_mode（s921-06，设计稿 §4.1「测点」）
+ compute_pending_elapsed 边界例（s921-07，设计稿 §4.2）。
页面侧行为等价性由 test_questionnaire_panel_charac.py 的分支头五例继续把关。
"""
import pytest

from src.ui.questionnaire_panel import classify_questionnaire_sub_mode

UPLOAD_LABEL = "📤 上传现有题目（预审 + 排版导出）"
IMPORT_LABEL = "📊 问卷数据导入与清洗"
AI_LABEL = "🆕 AI 设计新问卷"


# ── compute_pending_elapsed（s921-07 计时面实装，边界例：缺失/正常/跨日）──
def test_pending_elapsed_missing_started_at_returns_none():
    """started_at 缺失（None 或 0）→ None，页面显示「—」——不再恒 0。"""
    from src.ui.questionnaire_panel import compute_pending_elapsed
    assert compute_pending_elapsed(None, 1000.0) is None
    assert compute_pending_elapsed(0, 1000.0) is None


def test_pending_elapsed_normal_diff_is_int_seconds():
    from src.ui.questionnaire_panel import compute_pending_elapsed
    assert compute_pending_elapsed(1000.0, 1042.7) == 42
    assert compute_pending_elapsed(1000.0, 1000.4) == 0      # 刚起步仍是真 0，不是兜底假 0


def test_pending_elapsed_cross_day_counts_full_seconds():
    from src.ui.questionnaire_panel import compute_pending_elapsed
    assert compute_pending_elapsed(1_000_000.0, 1_000_000.0 + 90_000) == 90_000  # 跨日 25h


def test_three_real_labels_map_to_their_branches():
    assert classify_questionnaire_sub_mode(AI_LABEL) == "ai_design"
    assert classify_questionnaire_sub_mode(UPLOAD_LABEL) == "upload_items"
    assert classify_questionnaire_sub_mode(IMPORT_LABEL) == "import_clean"


def test_empty_string_falls_through_to_ai_design():
    assert classify_questionnaire_sub_mode("") == "ai_design"


@pytest.mark.parametrize("choice", [
    "📤 上传现有题目（预审 + 排版导出）",   # 全串原样
    "📤上传现有题目（预审 + 排版导出）",     # 丢 emoji 后空格 ⇒ 前缀仍命中
    "📤",                                     # 只有前缀
])
def test_upload_prefix_is_matched_prefix_only(choice):
    assert classify_questionnaire_sub_mode(choice) == "upload_items"


@pytest.mark.parametrize("choice", [
    "📊 问卷数据导入与清洗",
    "📊问卷数据导入与清洗",
    "📊",
])
def test_import_prefix_is_matched_prefix_only(choice):
    assert classify_questionnaire_sub_mode(choice) == "import_clean"


@pytest.mark.parametrize("choice", [
    " 📤 上传现有题目（预审 + 排版导出）",    # 前导空格 ⇒ startswith 失效
    "📥 上传现有题目（预审 + 排版导出）",    # emoji 变体 ⇒ 静默改道
    "上传现有题目（预审 + 排版导出）",        # 丢 emoji ⇒ 静默改道
    "🆕 AI 设计新问卷 ",                       # 尾部空格仍是 AI 分支
    "random text",
])
def test_label_perturbations_fall_through_silently_to_ai_design(choice):
    """现状风险（设计稿 §4.1）：判据只认 emoji 前缀，任何文案扰动都悄悄回到 AI 设计页。"""
    assert classify_questionnaire_sub_mode(choice) == "ai_design"


def test_return_domain_is_exactly_the_three_branches():
    outs = set()
    corpus = [AI_LABEL, UPLOAD_LABEL, IMPORT_LABEL, "", "x", " 📤 a", "📊", "📥"]
    for c in corpus:
        outs.add(classify_questionnaire_sub_mode(c))
    assert outs <= {"ai_design", "upload_items", "import_clean"}


@pytest.mark.parametrize("choice", [
    AI_LABEL, UPLOAD_LABEL, IMPORT_LABEL, "", " 📤", "📥 x", "📊b", "🆕", "  ", "📤📊"
])
def test_parity_with_old_inline_predicate(choice):
    """与抽取前的内联 if/elif（startswith 📤 → 上传；elif startswith 📊 → 导入；否则 AI）逐串对拍。"""
    if choice.startswith("📤"):
        expected = "upload_items"
    elif choice.startswith("📊"):
        expected = "import_clean"
    else:
        expected = "ai_design"
    assert classify_questionnaire_sub_mode(choice) == expected
