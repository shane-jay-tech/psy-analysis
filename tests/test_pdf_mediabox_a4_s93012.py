# -*- coding: utf-8 -*-
"""s930-12：PDF MediaBox A4 钉桩（s927-45 遗留「PDF 族尚无档二快照件」）。

q927-45 探针读数：MediaBox 595.28/841.89（A4 竖版，pt）——本件把探针读数
钉成断言：export_to_pdf 真产出 bytes 后解析首页 MediaBox。

运行：python -m pytest tests/test_pdf_mediabox_a4_s93012.py -q
"""
import re

from src.questionnaire.exporters import export_to_pdf


def _design():
    """复用既有 minimal_design 夹具（test_questionnaire_export_docx 的完整可跑面）。"""
    from tests.test_questionnaire_export_docx import minimal_design

    return minimal_design()


def test_pdf_mediabox_is_a4_portrait():
    """首页 MediaBox 钉 595.28×841.89（A4 竖版 pt，q927-45 探针读数转正）。"""
    raw = export_to_pdf(_design())
    assert isinstance(raw, (bytes, bytearray)) and len(raw) > 500
    m = re.search(rb"/MediaBox\s*\[\s*0 0 ([\d.]+) ([\d.]+)\s*\]", bytes(raw))
    assert m, "输出未找到 /MediaBox（PDF 结构面变化，需复点）"
    w, h = float(m.group(1)), float(m.group(2))
    assert abs(w - 595.28) < 0.5 and abs(h - 841.89) < 0.5, (
        f"MediaBox {w}/{h} ≠ A4 竖版 595.28/841.89"
    )


def test_pdf_container_is_bytes():
    """容器类型：export_to_pdf -> bytes（:483 bytes(pdf.output()) 归一在位——
    fpdf2 2.8.7 实测 output() 仍返 bytearray，:482 注释「与本函数 -> bytes 声明
    不符」经本班复测仍然准确，q927-55 的「轻微过时」判断被否证）。"""
    raw = export_to_pdf(_design())
    assert isinstance(raw, bytes), f"export_to_pdf 返回 {type(raw)}，归一写法破坏"
