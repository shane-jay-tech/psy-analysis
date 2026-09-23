# -*- coding: utf-8 -*-
"""`export_to_pdf` **正常分支**的正向 PDF 字节断言（s923-04）。

补的是 s922-13 留在 `zcode-bridge/done/s922-13-psy-exporters-docx.result.md:85-88` 的出口①：
该单只测了 `export_to_pdf`（`src/questionnaire/exporters.py:259`）的**两条降级路**
（`find_chinese_font→None` 抛 RuntimeError / `sys.modules["fpdf"]=None` 抛 ImportError），
正常分支「本机真有中文字体时到底出不出稿」零覆盖 —— 降级测得再全也证不出正向路径没坏。

口径（任务书出口①）：
- 用 `@pytest.mark.skipif` 承认机器绑定 —— 无中文字体或没有 fpdf 时**整件 skip**，
  不写「拿 monkeypatch 造一个假字体路径」的常绿断言（那测的是自己写的桩，不是生产码）。
- 正向断言只钉**字节层**：`%PDF` 头、非空、`%%EOF` 收尾；外加一条「字体真被嵌进去了」
  （`/FontFile2` 字体程序流存在），因为正向分支独有价值就在这里 ——
  降级桩永远测不到「CJK 字体有没有真的进 PDF」。

不动生产码、不装依赖、不碰版式数值（版式回归属 s923-06）。

红线自约：design 全是「合成构念/合成题干」的人造文案，不含真实被试数据，
不含任何统计/研究结论数值（CFA/SEM/power 相关字面量一个都没写）。
"""
from __future__ import annotations

import importlib.util
import re

import pytest

from src.questionnaire.exporters import export_to_pdf
from src.visualization.fonts import find_chinese_font

# ── 机器能力探针：skip 与否由它决定，不写死 ──────────────────────────────
_FONT_PATH = find_chinese_font()
_HAS_CJK_FONT = _FONT_PATH is not None
_HAS_FPDF = importlib.util.find_spec("fpdf") is not None

requires_cjk_renderer = pytest.mark.skipif(
    not (_HAS_CJK_FONT and _HAS_FPDF),
    reason=(
        "export_to_pdf 正向分支需本机真有中文字体与 fpdf："
        f"find_chinese_font()={_FONT_PATH!r}、fpdf 可导入={_HAS_FPDF}"
        "（无字体机上该分支必然走 RuntimeError 降级，正向断言无从成立）"
    ),
)


def _design() -> dict:
    """与 `tests/test_questionnaire_export_docx.py::minimal_design` 同型的最小可出稿 design。

    这里**故意重定义一份而不是 import 那份**：那份是别的班的产物，
    跨文件依赖会让本件的 skip 结论被别人的改动左右。
    """
    return {
        "construct_name": "合成构念",
        "research_question": "合成研究问题？",
        "template_used": {"name": "合成题型"},
        "scale_config": {
            "points": 5, "n_items": 2, "n_dimensions": 1, "n_reverse": 1, "reverse_ratio": "50%",
            "anchors": ["完全不同意", "完全同意"],
        },
        "match_reason": "合成匹配理由",
        "dimensions_used": [{"name": "维度甲", "desc": "合成描述", "item_count": 2, "example": "合成示例"}],
        "instructions": "合成指导语",
        "items": [
            {"dimension": "维度甲", "reverse": False, "index": 1, "text": "合成题干一"},
            {"dimension": "维度甲", "reverse": True, "index": 2, "text": "合成题干二"},
        ],
        "scoring": "合成计分方式",
        "psychometrics": {"信度": "合成信度策略\n第二条", "效度": "合成效度策略"},
    }


@requires_cjk_renderer
def test_positive_branch_returns_nonempty_pdf_bytes_with_magic_header() -> None:
    """任务的正题：正常分支出**非空**字节且以 `%PDF` 头开头（:268-435 全跑通、`pdf.output()` 有货）。

    降级桩给不出这条证据 —— 它只证明「抛得对」，不证明「不抛时出的是能开的文件」。
    """
    blob = export_to_pdf(_design())

    assert len(blob) > 0, "正向分支返回空字节 ⇒ 上游 UI 会静默给一个 0 字节 .pdf"
    assert bytes(blob)[:5] == b"%PDF-"                      # PDF magic（版本号为 1.x，不钉死小版本）
    assert bytes(blob).rstrip().endswith(b"%%EOF")          # 尾部闭合：截断的 PDF 打不开
    assert b"startxref" in bytes(blob)                      # xref 表在 ⇒ 不是裸文本拼的假 PDF


@requires_cjk_renderer
def test_positive_branch_actually_embeds_a_cjk_font_program() -> None:
    """正向分支独有价值：`:274-275` 的两次 `add_font` 要把字体程序真的嵌进 PDF。

    断的是 `/FontFile2`（TrueType 字体流）与 `/CIDFontType2` 存在，
    **不**断 `/BaseFont` 的具体名字 —— 子集前缀（`MPDFAA+` 之类）每次随机、
    字体名随机器字体而变，钉它就成了本机专属常绿。
    """
    raw = bytes(export_to_pdf(_design())).decode("latin-1")

    assert "/FontFile2" in raw, "没嵌字体程序 ⇒ 中文在别的机器上必成豆腐块"
    assert "/CIDFontType2" in raw and "/Type0" in raw       # CJK 复合字体的两层结构
    assert raw.count("/FontFile2") >= 2                      # 常规 + 粗体各注册一次（同一路径，见 :274-275）
    assert re.search(r"/Count\s+\d+", raw)                   # 页面树有数


@requires_cjk_renderer
def test_positive_branch_currently_returns_a_bytearray_not_bytes() -> None:
    """**在册现状钉桩**（不是修）：`-> bytes` 的签名在正向分支上并不成立。

    `:435` 直接 `return pdf.output()` 而未做类型归一；同文件的
    `build_questionnaire_pdf:569-572` 却显式 `bytes(out)` 并注释「fpdf2 新版本返回 bytearray」。
    fpdf2 2.8.7（本仓 .venv 实测）确实返 `bytearray` ⇒ 两个 PDF 出口**返回类型不一致**。
    本例把「不一致」钉成断言：哪天 fpdf 升级改返 bytes，或有人给 :435 补了归一，这条会红，
    届时**连生产码一起回看**，别只摘用例。改 `:435` 属行为改动，本单未授权。
    """
    blob = export_to_pdf(_design())

    assert type(blob) is bytearray                          # 不是 bytes；只 isinstance 就测不到这件事
    assert isinstance(blob, (bytes, bytearray))             # 但仍是可缓冲对象，调用方 st.download_button 能吃下


@requires_cjk_renderer
def test_skip_gate_mirrors_the_live_probe_so_it_cannot_be_frozen_true() -> None:
    """守卫守卫：skip 判据必须等于「现场再探一次」的结果，防止有人把 `_HAS_*` 写成常量。

    本例能跑起来就说明门是开着的；于是再现场探一遍比对，
    保证「门开」是真事实（字体路径非空且是可注册的后缀、fpdf 真能 import），
    而不是文件顶部写了个 `= True`。
    """
    live_font = find_chinese_font()
    assert _HAS_CJK_FONT is (live_font is not None)
    assert _HAS_FPDF is (importlib.util.find_spec("fpdf") is not None)
    assert live_font is not None and live_font.lower().endswith((".ttf", ".ttc", ".otf"))
    assert importlib.import_module("fpdf").FPDF is not None
