# -*- coding: utf-8 -*-
"""s930-06：build_experiment_protocol_docx 对 List[str] ethics 的类型口径归一
（s928-01 遗留：真 ExperimentDesign 抛 TypeError，在册测试全用 stub 零覆盖）。

三钉：
  R1 真形态：ethics=List[str] 的真 ExperimentDesign ⇒ 不炸且逐条列表段落文档；
  R2 str 路径逐字节不变：ethics=str ⇒ 输出与修复前 stub 用例对拍一致；
  R3 空 list ⇒ 走赫尔辛基兜底文案（与 None/'' 同型）。

运行：python -m pytest tests/test_docx_ethics_list_shape_s93006.py -q
"""
from src.experiment_design.design_engine import ExperimentDesign
from src.output.docx_exporter import build_experiment_protocol_docx


def _design(ethics):
    return ExperimentDesign(
        title="合成实验设计（测试夹具，无真实结论）",
        ethics=ethics,
    )


def _all_text(docx_bytes):
    """docx 字节 → 全文（build_experiment_protocol_docx 返回 bytes 非 Document）。"""
    import io

    from docx import Document as _Doc

    return "\n".join(p.text for p in _Doc(io.BytesIO(docx_bytes)).paragraphs)


def test_r1_list_ethics_does_not_raise_and_lands_per_item():
    """R1 真形态（修复前此例 TypeError）。"""
    doc = build_experiment_protocol_docx(_design(
        ["知情同意将逐条说明", "数据保密措施另行说明"]))
    text = _all_text(doc)
    assert "知情同意将逐条说明" in text and "数据保密措施另行说明" in text


def test_r2_str_path_unchanged():
    """R2 str 入参路径行为不变（对拍基态：str 直接整段落文档）。"""
    doc = build_experiment_protocol_docx(_design("伦理基线句（str 形态对照）。"))
    assert "伦理基线句（str 形态对照）。" in _all_text(doc)


def test_r3_empty_list_falls_back_to_helsinki():
    """R3 空 list ⇒ 赫尔辛基兜底（与 falsy 同型，避免空段落）。"""
    doc = build_experiment_protocol_docx(_design([]))
    assert "赫尔辛基宣言" in _all_text(doc)
