"""问卷正式文档导出测试（v4.1）。

覆盖：
- build_questionnaire_docx 输出非空且为 zip 格式（.docx 是 zip）
- build_questionnaire_pdf 输出非空且 %PDF magic
- 中文 / 反向题 / 自定义锚点 烟雾测试
- 入参校验：scale_points / anchors 长度
- 空白施测卷页尺寸钉桩（s924-26：Letter→A4，按 twips 整数钉产物面）
"""

from __future__ import annotations

import pytest

from src.questionnaire.items_loader import items_doc_from_lines


@pytest.fixture
def sample_doc():
    return items_doc_from_lines(
        ["我在陌生人面前感到紧张",
         "我能轻松开始对话",
         "我在公开场合保持冷静",
         "我害怕被别人评价"],
        title="社交焦虑预试量表",
        instructions="请根据近一周的实际感受作答；没有对错之分。",
        reverse_indices=[1, 2],
    )


# ---------------------------------------------------------------------------
# Word 导出
# ---------------------------------------------------------------------------


class TestQuestionnaireDocx:
    def test_basic_output(self, sample_doc):
        from src.output.docx_exporter import build_questionnaire_docx

        out = build_questionnaire_docx(sample_doc, scale_points=5)
        assert isinstance(out, bytes)
        assert len(out) > 5_000  # 至少 5 KB
        # .docx 是 zip：开头 "PK\x03\x04"
        assert out[:4] == b"PK\x03\x04"

    def test_seven_point(self, sample_doc):
        from src.output.docx_exporter import build_questionnaire_docx

        out = build_questionnaire_docx(sample_doc, scale_points=7)
        assert out[:4] == b"PK\x03\x04"
        assert len(out) > 5_000

    def test_custom_anchors(self, sample_doc):
        from src.output.docx_exporter import build_questionnaire_docx

        out = build_questionnaire_docx(
            sample_doc,
            scale_points=4,
            anchors=["从不", "偶尔", "经常", "总是"],
        )
        assert out[:4] == b"PK\x03\x04"

    def test_with_header_meta(self, sample_doc):
        from src.output.docx_exporter import build_questionnaire_docx

        out = build_questionnaire_docx(
            sample_doc,
            scale_points=5,
            header_meta={
                "researcher": "张三",
                "project": "毕业论文",
                "version": "v1.0",
                "date": "2026-05-23",
            },
        )
        assert out[:4] == b"PK\x03\x04"

    def test_blank_paper_is_a4_not_letter(self, sample_doc):
        """空白施测卷页尺寸＝**A4**（s924-26 放行的用户可见改版；改版前实测继承模板的 US Letter）。

        口径同 `tests/test_exporters_docx_geometry.py`（s923-06）：十进制意图值经 OOXML 的
        twips 量化后不可能逐位相等 ⇒ **按 twips 整数钉产物面**。
        别写成 `section.page_width.cm == 21`，那在本仓口径下当场是红的（真实读回 21.000861）。
        """
        import io

        from docx import Document

        from src.output.docx_exporter import build_questionnaire_docx

        out = build_questionnaire_docx(sample_doc, scale_points=5)
        doc = Document(io.BytesIO(out))
        assert len(doc.sections) == 1
        section = doc.sections[0]
        assert section.page_width.twips == 11906    # A4 宽；改版前实测 12240（US Letter）
        assert section.page_height.twips == 16838   # A4 高；改版前实测 15840（US Letter）

    def test_invalid_scale_points(self, sample_doc):
        from src.output.docx_exporter import build_questionnaire_docx

        with pytest.raises(ValueError, match="scale_points"):
            build_questionnaire_docx(sample_doc, scale_points=1)
        with pytest.raises(ValueError, match="scale_points"):
            build_questionnaire_docx(sample_doc, scale_points=20)

    def test_anchors_length_mismatch(self, sample_doc):
        from src.output.docx_exporter import build_questionnaire_docx

        with pytest.raises(ValueError, match="anchors"):
            build_questionnaire_docx(
                sample_doc,
                scale_points=5,
                anchors=["a", "b", "c"],  # 长度 3 ≠ 5
            )

    def test_empty_items_raises(self):
        from src.output.docx_exporter import build_questionnaire_docx

        empty = items_doc_from_lines([], title="空")
        with pytest.raises(ValueError, match="items.*为空"):
            build_questionnaire_docx(empty, scale_points=5)


# ---------------------------------------------------------------------------
# PDF 导出
# ---------------------------------------------------------------------------


class TestQuestionnairePdf:
    def test_basic_output(self, sample_doc):
        from src.questionnaire.exporters import build_questionnaire_pdf

        out = build_questionnaire_pdf(sample_doc, scale_points=5)
        assert isinstance(out, bytes)
        assert len(out) > 5_000
        assert out[:4] == b"%PDF"

    def test_seven_point(self, sample_doc):
        from src.questionnaire.exporters import build_questionnaire_pdf

        out = build_questionnaire_pdf(sample_doc, scale_points=7)
        assert out[:4] == b"%PDF"

    def test_pdf_output_container_is_normalized_to_bytes(self, sample_doc, monkeypatch):
        """s927-55：把「出口归一为 bytes」钉成断言——这层语义原先只由一段恒真死分支**装着**在做。

        被清掉的尾部四行两支同体（`if isinstance(out, (bytes, bytearray))` 与 else 都
        `return bytes(out)`），条件永不影响结果 ⇒ 删它属零行为变化。但删完之后，"归一"
        这件事只剩一处 `bytes(pdf.output())`，所以这里断的是**剩下的那一处真的在归一**：
        现场探得本仓 fpdf2 2.8.7 的 `output()` 返 bytearray，再用 monkeypatch 强制走
        bytearray 路并锁内容逐字节不变。变异自证：把 `bytes(...)` 剥掉 ⇒ 本例第 3 条断言转红。
        """
        from fpdf import FPDF

        from src.questionnaire.exporters import build_questionnaire_pdf

        real_output = FPDF.output
        handed_back = {}

        def fake_output(self, *args, **kwargs):
            buf = bytearray(real_output(self, *args, **kwargs))
            handed_back["buf"] = buf
            return buf

        monkeypatch.setattr(FPDF, "output", fake_output)
        out = build_questionnaire_pdf(sample_doc, scale_points=5)

        assert handed_back, "monkeypatch 没被走到 ⇒ 本例什么都没断（假绿守卫）"
        assert isinstance(handed_back["buf"], bytearray)      # 交回来的确实是 bytearray
        assert type(out) is bytes                             # 精确类型，不是"可缓冲"就算过
        assert not isinstance(out, bytearray)                 # 没退化成带着旧容器返回
        assert out == bytes(handed_back["buf"])               # 内容逐字节不变：清的是判别，不是数据

    def test_with_header_meta(self, sample_doc):
        from src.questionnaire.exporters import build_questionnaire_pdf

        out = build_questionnaire_pdf(
            sample_doc,
            scale_points=5,
            header_meta={"researcher": "李四", "date": "2026-05-23"},
        )
        assert out[:4] == b"%PDF"

    def test_invalid_scale_points(self, sample_doc):
        from src.questionnaire.exporters import build_questionnaire_pdf

        with pytest.raises(ValueError, match="scale_points"):
            build_questionnaire_pdf(sample_doc, scale_points=1)

    def test_anchors_length_mismatch(self, sample_doc):
        from src.questionnaire.exporters import build_questionnaire_pdf

        with pytest.raises(ValueError, match="anchors"):
            build_questionnaire_pdf(
                sample_doc, scale_points=5, anchors=["a", "b"],
            )

    def test_empty_items_raises(self):
        from src.questionnaire.exporters import build_questionnaire_pdf

        empty = items_doc_from_lines([], title="空")
        with pytest.raises(ValueError, match="items.*为空"):
            build_questionnaire_pdf(empty, scale_points=5)


# ---------------------------------------------------------------------------
# 集成：解析 → 导出
# ---------------------------------------------------------------------------


class TestIntegrationParseToExport:
    def test_md_file_to_docx_pdf(self):
        """端到端：.md 题目文件 → 解析 → Word/PDF 输出。"""
        import io

        from src.questionnaire.items_loader import parse_items_file
        from src.output.docx_exporter import build_questionnaire_docx
        from src.questionnaire.exporters import build_questionnaire_pdf

        md = (
            "# 学习投入量表\n"
            "\n"
            "请根据上学期的实际投入作答。\n"
            "\n"
            "1. 我课前会预习\n"
            "2. 我上课走神 (反向)\n"
            "3. 我课后会复习\n"
            "4. 我主动找资料\n"
            "5. 我和同学讨论问题\n"
        )
        bio = io.BytesIO(md.encode("utf-8"))
        doc = parse_items_file(bio, "scale.md")
        assert doc.n_items() == 5
        assert doc.reverse_indices == [1]

        docx_bytes = build_questionnaire_docx(doc, scale_points=5)
        pdf_bytes = build_questionnaire_pdf(doc, scale_points=5)
        assert docx_bytes[:4] == b"PK\x03\x04"
        assert pdf_bytes[:4] == b"%PDF"
