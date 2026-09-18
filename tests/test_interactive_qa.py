# -*- coding: utf-8 -*-
"""s918-39：论文交互问答模块测试（interactive_qa.py，模板驱动纯离线）。"""
import pytest

from src.paper_writer.interactive_qa import InteractiveQA, QAResult

CONTEXT = {
    "research_topic": "社交媒体使用与青少年心理健康",
    "method": "问卷调查法",
    "sample": "某市中学生 500 名",
    "hypotheses": ["社交媒体使用时长与焦虑水平正相关"],
}


def test_generate_questions_counts_and_ids():
    """问题数 = 类别数 × max_per_category（默认 5 类×2 = 10 上限内）；id 从 0 递增。"""
    qa = InteractiveQA(CONTEXT)
    questions = qa.generate_questions()
    assert len(questions) > 0
    ids = [q.id for q in questions]
    assert ids == sorted(ids), "id 应递增"
    assert len(set(ids)) == len(ids), "id 不重复"


def test_max_per_category_cap():
    """max_per_category=2 上限：单类别生成数 ≤ 2。"""
    qa = InteractiveQA(CONTEXT)
    questions = qa.generate_questions(categories=["research_gap"], max_per_category=2)
    assert 0 < len(questions) <= 2


def test_custom_categories_subset():
    """指定单类别：只生成该类别问题。"""
    qa = InteractiveQA(CONTEXT)
    questions = qa.generate_questions(categories=["method"])
    assert len(questions) > 0


def test_guess_answer_fallback_on_missing_fields():
    """_guess_answer 缺失字段兜底：context 为空字典也不抛错。"""
    qa = InteractiveQA({})
    questions = qa.generate_questions()
    assert isinstance(questions, list)


def test_qa_result_defaults():
    """QAResult 字段默认值结构。"""
    import dataclasses
    fields = {f.name for f in dataclasses.fields(QAResult)}
    assert {"questions", "answered_count", "pending_count", "summary"} <= fields
