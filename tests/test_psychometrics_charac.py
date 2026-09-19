# -*- coding: utf-8 -*-
"""src/questionnaire/psychometrics.py 六个公共符号的结构钉桩（s920-19）。

现状（改前实测）：本模块 167 行、6 个符号，`tests/` 里**一次都没被测过**
（唯一调用方是 `src/questionnaire/design_engine.py:161`）。
本文件只钉**返回结构与契约**：类型、非空、话题关键词、幂等、不改入参、畸形入参当前的异常类型。
红线：不核对、不背书任何统计阈值（文内的 CVI/α 数值属被测模块自带文案，本文件不断言其正确性）。
"""
import copy

import pytest

from src.questionnaire import psychometrics as ps


CONSTRUCT = {
    "name_zh": "社交焦虑",
    "definition": "在社交场合感到不自在的稳定倾向",
    "dimensions": [{"name": "认知"}, {"name": "情感"}, {"name": "行为"}],
}


def test_three_guidance_functions_return_non_empty_markdown_strings():
    """三个按构念定制的 guidance：str、非空、含"**" 加粗小标题、含话题词。"""
    cases = {
        "content_validity_guidance": "内容效度",
        "construct_validity_guidance": "结构效度",
        "reliability_guidance": "信度",
    }
    for name, topic in cases.items():
        text = getattr(ps, name)(copy.deepcopy(CONSTRUCT))
        assert isinstance(text, str), name
        assert text.strip(), f"{name} 返回空文本"
        assert "**" in text, f"{name} 丢了 markdown 小标题结构"
        assert topic in text, f"{name} 没提到本行主题 {topic}"


def test_social_desirability_guidance_is_argument_free_and_non_empty():
    text = ps.social_desirability_guidance()

    assert isinstance(text, str) and text.strip()
    assert "社会称许" in text


def test_face_validity_checklist_returns_list_of_non_empty_strings():
    items = ps.face_validity_checklist()

    assert isinstance(items, list) and items
    assert all(isinstance(x, str) and x.strip() for x in items)
    assert len(items) >= 3, "表面效度清单至少要有可勾选项"


def test_report_has_exactly_the_five_sections_and_all_are_text():
    report = ps.generate_psychometric_report(copy.deepcopy(CONSTRUCT))

    assert isinstance(report, dict)
    assert list(report.keys()) == ["内容效度", "表面效度", "结构效度", "信度", "社会称许性控制"]
    assert all(isinstance(v, str) and v.strip() for v in report.values())
    # 表面效度这一段是拼出来的（前缀 + ☐ 逐项），钉它的组装形态而不是内容
    assert report["表面效度"].startswith("请逐项检查")
    assert "☐" in report["表面效度"]


def test_guidance_functions_do_not_mutate_the_construct():
    """纯函数契约：四个 guidance 与 report 都不许改入参 dict（与 s919-10 那条 in-place 主题同一类）。"""
    original = copy.deepcopy(CONSTRUCT)

    ps.content_validity_guidance(CONSTRUCT)
    ps.construct_validity_guidance(CONSTRUCT)
    ps.reliability_guidance(CONSTRUCT)
    ps.generate_psychometric_report(CONSTRUCT)

    assert CONSTRUCT == original, "guidance 侧就地改了调用方的 construct"


def test_output_is_deterministic_across_calls():
    """两次调用逐字相同：文案里不掺随机/时间，报告数才可比。"""
    a = ps.generate_psychometric_report(copy.deepcopy(CONSTRUCT))
    b = ps.generate_psychometric_report(copy.deepcopy(CONSTRUCT))

    assert a == b
    assert ps.face_validity_checklist() == ps.face_validity_checklist()


def test_empty_construct_falls_back_instead_of_crashing():
    """没有维度时必须走"通用版"文案，不能抛——设计向导第一步就是空维度。"""
    text = ps.content_validity_guidance({"dimensions": []})

    assert "保障策略" in text
    assert list(ps.generate_psychometric_report({}).keys()) == [
        "内容效度", "表面效度", "结构效度", "信度", "社会称许性控制"]


def test_malformed_dimensions_currently_raises_type_error():
    """现状：`dimensions` 给成字符串列表 ⇒ `d["name"]` 直接 TypeError（**不**是优雅降级）。

    钉住它是为了让"改成 .get 兜底"这个决定有代价可见：现在所有调用方必须传 dict 形状的维度。
    """
    with pytest.raises(TypeError):
        ps.content_validity_guidance({"dimensions": ["认知", "情感"]})
