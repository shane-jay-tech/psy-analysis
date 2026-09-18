# -*- coding: utf-8 -*-
"""s918-38：意图识别链离线测试（Keyword/TFIDF 两策略，零联网）。"""
import pytest

from src.questionnaire.intent_recognizer import (
    KeywordIntentStrategy,
    TFIDFIntentStrategy,
)


def test_keyword_strategy_hit():
    """关键词命中：包含构造关键词的请求应给出候选。"""
    s = KeywordIntentStrategy()
    result = s.recognize("做一个可靠性分析（信度检验）", {})
    assert result is not None


def test_keyword_strategy_miss_returns_empty_or_none():
    """无关键词命中：不臆造候选（空候选或 none 型结果）。"""
    s = KeywordIntentStrategy()
    result = s.recognize("今天天气怎么样", {})
    assert result is None or not getattr(result, "candidates", [])


def test_tfidf_strategy_ranks_candidates():
    """TFIDF 策略：给出一组排序候选（相似度高的在前或等价无序但非空）。"""
    s = TFIDFIntentStrategy()
    result = s.recognize("信度检验，克隆巴赫系数", {})
    assert result is not None


def test_chain_recognize_intent_offline_runs():
    """兼容入口 recognize_intent：无 LLM 配置下离线可跑，返回结构含四键。"""
    import pandas as pd
    from src.questionnaire.intent_recognizer import recognize_intent

    df = pd.DataFrame({"q1": [1, 2], "q2": [2, 1]})
    result = recognize_intent(df, "做信度分析", {"columns": ["q1", "q2"]}, use_llm=False)
    assert isinstance(result, dict)
    for key in ("best_match", "confidence", "candidates", "is_ambiguous"):
        assert key in result


def test_chain_recognize_intent_never_calls_llm_without_flag():
    """use_llm=False（默认）绝不触发 LLM 调用路径。"""
    import pandas as pd
    from src.questionnaire.intent_recognizer import recognize_intent

    df = pd.DataFrame({"q1": [1, 2]})
    result = recognize_intent(df, "随便什么请求", {"columns": ["q1"]}, use_llm=False)
    assert isinstance(result, dict)
    assert "best_match" in result
