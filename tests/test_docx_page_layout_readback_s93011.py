# -*- coding: utf-8 -*-
"""s930-11：docx 页面版式常量读回钉桩（s927-45 遗留「路 B 档二缺面」）。

q927-45 点名：`_setup_page` 的 `Cm(21)/Cm(29.7)` 与 `S.MARGIN_*_CM` 无任何测试
读回——「常量存在、产物无人钉」。本件产出真实 docx 后读回 section 六值，
以容差 0.005 cm（＝TWIPS_GRANULARITY_CM，收窄属人工不在本单）钉现值。

运行：python -m pytest tests/test_docx_page_layout_readback_s93011.py -q
"""
import io

from docx import Document

from src.output import docx_styles as S
from src.output.docx_exporter import build_experiment_protocol_docx

TOL_CM = 0.005


def _readback_sections():
    """产出真实 docx 并读回所有 section 的六值（cm 浮点）。"""
    from src.experiment_design.design_engine import ExperimentDesign

    design = ExperimentDesign(title="合成实验设计（测试夹具，无真实结论）",
                              ethics=["知情同意（夹具）"])
    raw = build_experiment_protocol_docx(design)
    doc = Document(io.BytesIO(raw))
    return [
        {
            "page_width_cm": sec.page_width.cm,
            "page_height_cm": sec.page_height.cm,
            "top": sec.top_margin.cm,
            "bottom": sec.bottom_margin.cm,
            "left": sec.left_margin.cm,
            "right": sec.right_margin.cm,
        }
        for sec in doc.sections
    ]


def test_page_size_is_a4_21_by_29_7():
    """页宽/页高钉 A4：Cm(21)×Cm(29.7)（防回退 Letter 12240×15840 的历史病）。"""
    for i, sec in enumerate(_readback_sections()):
        assert abs(sec["page_width_cm"] - 21.0) <= TOL_CM, f"section{i} 页宽 {sec['page_width_cm']}"
        assert abs(sec["page_height_cm"] - 29.7) <= TOL_CM, f"section{i} 页高 {sec['page_height_cm']}"


def test_margins_match_docx_styles_constants():
    """四向 margin 逐向读回钉 S.MARGIN_*_CM（常量与产物双面同源）。"""
    expect = {"top": S.MARGIN_TOP_CM, "bottom": S.MARGIN_BOTTOM_CM,
              "left": S.MARGIN_LEFT_CM, "right": S.MARGIN_RIGHT_CM}
    for i, sec in enumerate(_readback_sections()):
        for side, want in expect.items():
            assert abs(sec[side] - want) <= TOL_CM, (
                f"section{i}.{side} = {sec[side]} ≠ S.{side.upper()} = {want}")


def test_all_sections_uniform():
    """多 section 文档的版式一致性：所有 section 六值彼此相等。"""
    secs = _readback_sections()
    assert len(secs) >= 1
    first = secs[0]
    for i, sec in enumerate(secs[1:], 1):
        assert sec == first, f"section{i} 与 section0 版式不一致：{sec} vs {first}"
