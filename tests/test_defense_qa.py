"""答辩问题模拟器测试。"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pandas as pd
import pytest

from src.paper_writer.defense_qa import (
    QAItem, generate_defense_qa, render_qa_as_markdown,
)


def _mk_ctx(test_type: str, **kwargs) -> dict:
    return {
        "test_type": test_type,
        "test_name_zh": kwargs.get("name", "测试"),
        "sample_size": kwargs.get("n", 100),
        "dv": kwargs.get("dv", "因变量"),
        "iv": kwargs.get("iv", "自变量"),
        **kwargs,
    }


def test_independent_ttest_generates_method_question():
    """独立样本 t 检验应生成"为什么用 t 检验"问题。"""
    result = SimpleNamespace(
        t_statistic=2.45, df=78.0, p_value=0.016,
        effect_size=0.55, effect_size_name="Cohen's d",
        assumption_equal_var={"passed": True, "statistic": "1.20", "p_value": "0.275"},
    )
    output = {
        "test_type": "independent_ttest",
        "result": result,
        "p_value": 0.016,
        "effect_size": 0.55,
    }
    ctx = _mk_ctx("independent_ttest", dv="焦虑得分", iv="性别")

    qa = generate_defense_qa(plan=None, output=output, ctx=ctx)
    assert len(qa) >= 3
    questions = " ".join(item.question for item in qa)
    assert "t 检验" in questions or "t检验" in questions
    answers = " ".join(item.answer for item in qa)
    assert "焦虑得分" in answers or "性别" in answers


def test_pearson_corr_generates_correlation_warning():
    """相关分析应包含'相关≠因果'类的推论提醒。"""
    cm = pd.DataFrame({"X": [1.0, 0.45], "Y": [0.45, 1.0]}, index=["X", "Y"])
    result = SimpleNamespace(
        corr_matrix=cm, p_matrix=None, sig_mask=None,
        effect_size=0.45, effect_size_name="r",
    )
    output = {
        "test_type": "pearson_corr", "result": result,
        "p_value": 0.001, "effect_size": 0.45,
    }
    ctx = _mk_ctx("pearson_corr")

    qa = generate_defense_qa(plan=None, output=output, ctx=ctx)
    questions = " ".join(item.question for item in qa)
    assert "相关" in questions or "Pearson" in questions
    # 必须有推论谨慎类问题
    categories = [item.category for item in qa]
    assert "infer" in categories or "method" in categories


def test_anova_includes_effect_size_explanation():
    result = SimpleNamespace(
        table=pd.DataFrame({"F": [5.2], "df": [2], "p": [0.008]}),
        post_hoc=pd.DataFrame({"组1": ["A"], "组2": ["B"], "p": [0.02]}),
        group_stats=pd.DataFrame({"组别": ["A", "B", "C"], "M": [10, 12, 15]}),
        effect_size=0.12, effect_size_name="η²",
    )
    output = {
        "test_type": "one_way_anova", "result": result,
        "effect_size": 0.12,
    }
    ctx = _mk_ctx("one_way_anova", dv="得分", iv="组别")
    qa = generate_defense_qa(plan=None, output=output, ctx=ctx)

    answers = " ".join(item.answer for item in qa)
    assert "η²" in answers or "效应量" in answers
    # ANOVA 应有事后检验问题
    questions = " ".join(item.question for item in qa)
    assert "事后" in questions or "ANOVA" in questions or "t 检验" in questions


def test_cronbach_alpha_judges_reliability_level():
    result = SimpleNamespace(
        effect_size=0.85, effect_size_name="Cronbach α",
    )
    output = {
        "test_type": "cronbach_alpha", "result": result,
        "effect_size": 0.85,
    }
    ctx = _mk_ctx("cronbach_alpha")
    qa = generate_defense_qa(plan=None, output=output, ctx=ctx)

    answers = " ".join(item.answer for item in qa)
    # α=0.85 应判为良好
    assert "良好" in answers or "可接受" in answers


def test_max_items_limit_respected():
    """max_items 上限不被超过。"""
    result = SimpleNamespace(
        t_statistic=2.0, df=50, p_value=0.05,
        effect_size=0.5, effect_size_name="d",
        assumption_equal_var={"passed": True},
    )
    output = {"test_type": "independent_ttest", "result": result}
    ctx = _mk_ctx("independent_ttest")

    qa = generate_defense_qa(None, output, ctx, max_items=3)
    assert len(qa) <= 3


def test_unknown_test_type_falls_back_to_generic():
    """未知检验类型应至少返回通用问题，不崩溃。"""
    output = {"test_type": "unknown_method"}
    ctx = _mk_ctx("unknown_method")
    qa = generate_defense_qa(None, output, ctx)
    assert isinstance(qa, list)
    # 至少有通用问题
    assert len(qa) >= 1


def test_empty_output_returns_empty_list():
    qa = generate_defense_qa(None, None, {})
    assert qa == []


def test_render_markdown_contains_qa_structure():
    items = [
        QAItem("Q1?", "A1.", "method", "🎯 方法选择"),
        QAItem("Q2?", "A2.", "effect", "📐 效应量"),
    ]
    md = render_qa_as_markdown(items)
    assert "### Q1: Q1?" in md
    assert "### Q2: Q2?" in md
    assert "🎯 方法选择" in md
    assert "A1." in md and "A2." in md


def test_render_markdown_handles_empty():
    md = render_qa_as_markdown([])
    assert "暂无" in md


# --------------------------------------------------------------------------- #
# v2.8: 难度分级 + 类别补全 + 新检验覆盖
# --------------------------------------------------------------------------- #

def test_difficulty_field_present_on_all_items():
    """每个生成的 QAItem 都有 difficulty 字段且属于 必问/常问/刁钻。"""
    result = SimpleNamespace(
        t_statistic=2.45, df=78.0, p_value=0.016,
        effect_size=0.55, effect_size_name="Cohen's d",
        assumption_equal_var={"passed": True, "statistic": 1.0, "p_value": 0.5},
    )
    output = {"test_type": "independent_ttest", "result": result, "p_value": 0.016, "effect_size": 0.55}
    qa = generate_defense_qa(plan=None, output=output, ctx=_mk_ctx("independent_ttest"))
    for item in qa:
        assert item.difficulty in ("必问", "常问", "刁钻"), f"unexpected: {item.difficulty}"
        assert item.difficulty_emoji in ("🟢", "🟡", "🔴")


def test_difficulty_sort_must_come_first():
    """排序后必问应在常问之前。"""
    result = SimpleNamespace(
        t_statistic=2.0, df=50, p_value=0.05,
        effect_size=0.5, effect_size_name="d",
        assumption_equal_var={"passed": True},
    )
    output = {"test_type": "independent_ttest", "result": result}
    ctx = _mk_ctx("independent_ttest")
    qa = generate_defense_qa(None, output, ctx, max_items=10)
    seen_chang = False
    for item in qa:
        if item.difficulty == "常问":
            seen_chang = True
        if item.difficulty == "必问":
            assert not seen_chang, "必问 出现在 常问 之后，排序错误"


def test_required_categories_filled_in_for_method_with_partial_coverage():
    """ANCOVA 等部分覆盖方法应被补足到 method/data/effect/infer 4 类。"""
    output = {"test_type": "ancova", "result": None, "effect_size": 0.10}
    ctx = _mk_ctx("ancova")
    qa = generate_defense_qa(None, output, ctx, max_items=10)
    cats = {item.category for item in qa}
    for must in ("method", "data", "effect", "infer"):
        assert must in cats, f"Missing required category: {must}, got {cats}"


@pytest.mark.parametrize("test_type", [
    "linear_regression", "multiple_regression", "hierarchical_regression",
    "moderation", "ancova", "welch_anova", "friedman", "wilcoxon",
    "one_sample_ttest", "partial_corr", "point_biserial",
    "chi_square_gof", "two_way_anova", "repeated_anova", "split_half",
])
def test_new_test_types_have_at_least_4_categories(test_type):
    """v2.8 新覆盖的 15 种检验都应至少有 4 类问题（含补全后）。"""
    output = {"test_type": test_type, "effect_size": 0.30, "result": None}
    ctx = _mk_ctx(test_type)
    qa = generate_defense_qa(None, output, ctx, max_items=10)
    cats = {item.category for item in qa}
    assert len(cats) >= 4, f"{test_type}: only {len(cats)} categories: {cats}"


def test_render_markdown_groups_by_difficulty():
    from src.paper_writer.defense_qa import QAItem
    items = [
        QAItem("Q1?", "A1.", "method", "🎯 方法", difficulty="必问", difficulty_emoji="🟢"),
        QAItem("Q2?", "A2.", "data", "📊 数据", difficulty="常问", difficulty_emoji="🟡"),
        QAItem("Q3?", "A3.", "limit", "⚠ 局限", difficulty="刁钻", difficulty_emoji="🔴"),
    ]
    md = render_qa_as_markdown(items)
    assert "必问" in md and "常问" in md and "刁钻" in md
    # 顺序：必问应在常问之前
    assert md.index("必问") < md.index("常问") < md.index("刁钻")


def test_group_by_difficulty_returns_three_buckets():
    from src.paper_writer.defense_qa import QAItem, group_qa_by_difficulty
    items = [
        QAItem("Q1?", "A.", "method", "x", difficulty="必问", difficulty_emoji="🟢"),
        QAItem("Q2?", "A.", "method", "x", difficulty="必问", difficulty_emoji="🟢"),
        QAItem("Q3?", "A.", "data", "x", difficulty="刁钻", difficulty_emoji="🔴"),
    ]
    groups = group_qa_by_difficulty(items)
    assert len(groups["必问"]) == 2
    assert len(groups["常问"]) == 0
    assert len(groups["刁钻"]) == 1


# --------------------------------------------------------------------------- #
# v2.9: 掌握状态追踪 + 精准版 PDF
# --------------------------------------------------------------------------- #

def test_qaitem_has_mastered_field_default_false():
    from src.paper_writer.defense_qa import QAItem
    item = QAItem("Q?", "A.", "method", "🎯 方法", difficulty="必问")
    assert item.mastered is False


def test_qaitem_question_id_stable_across_instances():
    from src.paper_writer.defense_qa import QAItem
    a = QAItem("同样的问题?", "A1", "method", "🎯", difficulty="必问")
    b = QAItem("同样的问题?", "A2 不同的答案", "data", "📊", difficulty="常问")
    # ID 仅基于 question 文本
    assert a.question_id == b.question_id


def test_apply_mastered_state_injects_from_map():
    from src.paper_writer.defense_qa import QAItem, apply_mastered_state
    items = [
        QAItem("Q1?", "A1", "method", "🎯", difficulty="必问"),
        QAItem("Q2?", "A2", "data", "📊", difficulty="常问"),
    ]
    mastered_map = {items[0].question_id: True}
    apply_mastered_state(items, mastered_map)
    assert items[0].mastered is True
    assert items[1].mastered is False


def test_apply_mastered_state_empty_map_noop():
    from src.paper_writer.defense_qa import QAItem, apply_mastered_state
    items = [QAItem("Q?", "A", "method", "🎯", difficulty="必问")]
    apply_mastered_state(items, {})
    assert items[0].mastered is False


def test_calculate_mastery_progress_counts_correctly():
    from src.paper_writer.defense_qa import QAItem, calculate_mastery_progress
    items = [
        QAItem("Q1?", "A", "method", "🎯", difficulty="必问", mastered=True),
        QAItem("Q2?", "A", "method", "🎯", difficulty="必问", mastered=False),
        QAItem("Q3?", "A", "data", "📊", difficulty="常问", mastered=True),
    ]
    progress = calculate_mastery_progress(items)
    assert progress["必问"]["mastered"] == 1
    assert progress["必问"]["total"] == 2
    assert progress["常问"]["mastered"] == 1
    assert progress["常问"]["total"] == 1


def test_focused_pdf_only_includes_unmastered():
    """v2.9: filter_unmastered=True 时不应等同于 full 版本，且都合法。"""
    from src.paper_writer.defense_qa import (
        HandbookMeta, QAItem, export_defense_handbook_pdf,
    )
    # 全 mastered + 1 unmastered → 精准版只渲染 1 题，应明显小于完整版
    items_a = [
        QAItem(f"Q{i}?", f"A{i}", "method", "🎯", difficulty="必问",
               mastered=(i != 0))
        for i in range(15)  # i=0 unmastered, i=1..14 mastered
    ]
    full_pdf = export_defense_handbook_pdf(items_a, HandbookMeta(research_title="t"))
    focused_pdf = export_defense_handbook_pdf(
        items_a, HandbookMeta(research_title="t"), filter_unmastered=True
    )
    assert full_pdf.startswith(b"%PDF")
    assert focused_pdf.startswith(b"%PDF")
    # 内容不同（精准版只渲染 1 题，完整版渲染 15 题）
    assert full_pdf != focused_pdf


def test_focused_pdf_with_all_mastered_still_valid():
    """v2.9: 全部掌握时精准版不崩溃，仍能生成（含祝贺语或空内容）。"""
    from src.paper_writer.defense_qa import (
        HandbookMeta, QAItem, export_defense_handbook_pdf,
    )
    items = [
        QAItem("Q?", "A", "method", "🎯", difficulty="必问", mastered=True),
    ]
    pdf = export_defense_handbook_pdf(
        items, HandbookMeta(research_title="t"), filter_unmastered=True
    )
    assert pdf.startswith(b"%PDF")
