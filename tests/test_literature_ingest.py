"""文献解析模块测试（ingest.py）：txt/docx/PDF 分派、容错、批量隔离。"""

import io

from docx import Document as DocxDocument
from unittest.mock import MagicMock

from src.literature_review.ingest import ingest_file, ingest_files


def test_txt_basic():
    data = "工作旺盛感研究综述\nWorld\n正文第一段内容若干字。".encode("utf-8")
    result = ingest_file("test.txt", data)
    assert result.extraction_ok
    assert result.item.title  # 抽到了某个标题
    assert "正文第一段" in result.full_text


def test_txt_gbk_fallback():
    data = "中文标题行较长一些\n摘要内容\n".encode("gbk")
    result = ingest_file("test.txt", data)
    assert result.extraction_ok
    assert "中文标题" in result.full_text


def test_unsupported_extension():
    result = ingest_file("test.xyz", b"dummy")
    assert not result.extraction_ok
    assert any("不支持的文件格式" in w for w in result.warnings)


def test_empty_file():
    result = ingest_file("empty.txt", b"")
    assert result.extraction_ok  # 空 txt 不算解析失败
    assert result.full_text == ""
    assert result.item.title == ""


def test_batch_single_failure_no_crash():
    results = ingest_files([("good.txt", b"hello world content here"), ("bad.xyz", b"")])
    assert len(results) == 2
    assert results[0].extraction_ok
    assert not results[1].extraction_ok


def test_docx_basic():
    doc = DocxDocument()
    doc.add_paragraph("Test paragraph content")
    buf = io.BytesIO()
    doc.save(buf)
    result = ingest_file("test.docx", buf.getvalue())
    assert result.extraction_ok
    assert "Test paragraph content" in result.full_text


def test_pdf_mock(monkeypatch):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Hello PDF content " * 5
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]
    monkeypatch.setattr("src.literature_review.ingest.pypdf.PdfReader",
                        lambda *a, **kw: mock_reader)
    result = ingest_file("test.pdf", b"dummy")
    assert result.extraction_ok
    assert "Hello PDF content" in result.full_text


def test_pdf_scan_warning(monkeypatch):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "   "
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]
    monkeypatch.setattr("src.literature_review.ingest.pypdf.PdfReader",
                        lambda *a, **kw: mock_reader)
    result = ingest_file("scan.pdf", b"dummy")
    assert not result.extraction_ok
    assert any("扫描版PDF" in w for w in result.warnings)


def test_keys_are_unique():
    results = ingest_files([("a.txt", b"same content"), ("a.txt", b"same content")])
    assert results[0].item.key != results[1].item.key
