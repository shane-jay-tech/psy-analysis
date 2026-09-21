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


def test_pending_elapsed_future_started_at_clamps_to_zero_not_negative():
    """s922-02（s921-07 遗留 1）：started_at 在未来（时钟回拨/跨机时差）⇒ 钳 0，负秒不外泄。"""
    from src.ui.questionnaire_panel import compute_pending_elapsed
    assert compute_pending_elapsed(2000.0, 1000.0) == 0     # 回拨 1000s：旧实现给 -1000
    assert compute_pending_elapsed(1000.5, 1000.4) == 0     # 亚秒级未来
    assert compute_pending_elapsed(None, 1000.0) is None    # 缺失仍是 None（不被钳成 0，两态可分）
    assert compute_pending_elapsed(1000.0, 1000.4) == 0     # 真 0 与钳 0 同值 ⇒ 需 anomaly 判据区分


def test_pending_elapsed_clock_anomaly_is_the_only_negative_source():
    """判据域：True ⇔ started_at 严格晚于 now；缺失/为 0 归「耗时未知」而非「时钟异常」。"""
    from src.ui.questionnaire_panel import pending_clock_anomaly
    assert pending_clock_anomaly(2000.0, 1000.0) is True
    assert pending_clock_anomaly(1000.0, 2000.0) is False
    assert pending_clock_anomaly(1000.0, 1000.0) is False   # 恰等不算异常（< 而非 <=）
    assert pending_clock_anomaly(None, 1000.0) is False
    assert pending_clock_anomaly(0, 1000.0) is False


@pytest.mark.parametrize("started_at,now", [
    (2000.0, 1000.0), (1e9, 0.0), (1000.5, 1000.4),        # 异常族
    (1000.0, 1000.4), (1000.0, 1000.0), (900.0, 1000.0),   # 正常族（含真 0）
])
def test_pending_elapsed_anomaly_true_always_pairs_with_clamped_zero(started_at, now):
    """两函数同源于同一 now 的不变式：判异常 ⇒ 秒必为钳后的 0；不判异常 ⇒ 秒就是真差值。"""
    from src.ui.questionnaire_panel import compute_pending_elapsed, pending_clock_anomaly
    e = compute_pending_elapsed(started_at, now)
    assert e is not None and e >= 0                         # 钳 0 后全谱非负
    if pending_clock_anomaly(started_at, now):
        assert e == 0
    else:
        assert e == int(now - started_at)                   # 未回拨时钳位不改值（真 0 仍是真 0）


def test_pending_elapsed_page_puts_the_clock_anomaly_branch_before_the_under_30_branch():
    """s921-07 遗留原文的病就是「负秒落进 <30 正常文案」——分支次序与单一 now 就是病灶，源码次序钉住。

    只钉次序不钉渲染：页面级 pending 渲染目前无假 st 覆盖（charac 的 StrictSt 只够跑分支头），
    次序一被调换（把 clock_anomaly 挪到 <30 之后）或 now 被拆成两次 time.time() 本例立刻红。
    """
    import inspect
    import src.ui.questionnaire_panel as qp
    src = inspect.getsource(qp.render_questionnaire_page)
    body = src.split(chr(10))

    def first(snip):
        hits = [i for i, ln in enumerate(body) if snip in ln]
        assert hits, snip
        return hits[0]

    assert first("elapsed_txt =") > first("clock_anomaly =") > first("_now = _t.time()")
    chain = ["elif elapsed is None:", "elif clock_anomaly:", '"🕐 时钟异常', "elif elapsed < 30:"]
    assert [first(c) for c in chain] == sorted([first(c) for c in chain])
    assert first("elif clock_anomaly:") < first("elif elapsed < 30:")
    assert src.count("_now = _t.time()") == 1                       # 单一时钟读数，两判据同源
    assert "compute_pending_elapsed(started_at, _t.time())" not in src   # 旧的一次性读数写法已消失



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


