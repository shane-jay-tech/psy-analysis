"""P0-3: PDF 导出测试。

验证 PDF 转换器的降级逻辑、结果结构、ZIP 集成。
"""

import json
import io
import zipfile
from unittest.mock import patch, MagicMock

import pytest

from src.output.pdf_exporter import (
    PDFResult,
    convert_docx_to_pdf,
    check_pdf_availability,
    _word_com_available,
    _libreoffice_available,
)


class TestPDFResult:
    def test_success_result(self):
        r = PDFResult(success=True, pdf_bytes=b"%PDF-1.4", method="word_com")
        assert r.success
        assert r.pdf_bytes == b"%PDF-1.4"
        assert r.method == "word_com"

    def test_failure_result(self):
        r = PDFResult(success=False, error="Not available", suggestion="Install Word")
        assert not r.success
        assert "Not available" in r.error
        assert "Install" in r.suggestion


class TestCheckAvailability:
    def test_returns_tuple(self):
        available, method = check_pdf_availability()
        assert isinstance(available, bool)
        assert isinstance(method, str)

    @patch("src.output.pdf_exporter._word_com_available", return_value=True)
    def test_word_available(self, _):
        available, method = check_pdf_availability()
        assert available
        assert "Word" in method

    @patch("src.output.pdf_exporter._word_com_available", return_value=False)
    @patch("src.output.pdf_exporter._libreoffice_available", return_value=True)
    def test_libreoffice_fallback(self, _, __):
        available, method = check_pdf_availability()
        assert available
        assert "LibreOffice" in method

    @patch("src.output.pdf_exporter._word_com_available", return_value=False)
    @patch("src.output.pdf_exporter._libreoffice_available", return_value=False)
    def test_nothing_available(self, _, __):
        available, method = check_pdf_availability()
        assert not available
        assert method == ""


class TestConvertDocx:
    @patch("src.output.pdf_exporter._try_word_com")
    @patch("src.output.pdf_exporter._try_libreoffice")
    def test_all_fail_gives_graceful_fallback(self, mock_libre, mock_word):
        mock_word.return_value = PDFResult(success=False, method="word_com", error="no word")
        mock_libre.return_value = PDFResult(success=False, method="libreoffice", error="no lo")
        result = convert_docx_to_pdf(b"fake docx")
        assert not result.success
        assert "无可用" in result.error
        assert result.suggestion != ""

    @patch("src.output.pdf_exporter._try_word_com")
    def test_word_success_skips_libreoffice(self, mock_word):
        mock_word.return_value = PDFResult(success=True, pdf_bytes=b"%PDF", method="word_com")
        result = convert_docx_to_pdf(b"fake docx")
        assert result.success
        assert result.method == "word_com"

    @patch("src.output.pdf_exporter._try_word_com")
    @patch("src.output.pdf_exporter._try_libreoffice")
    def test_word_fail_tries_libreoffice(self, mock_libre, mock_word):
        mock_word.return_value = PDFResult(success=False, method="word_com", error="fail")
        mock_libre.return_value = PDFResult(success=True, pdf_bytes=b"%PDF-lo", method="libreoffice")
        result = convert_docx_to_pdf(b"fake docx")
        assert result.success
        assert result.method == "libreoffice"


class TestZipPDFIntegration:
    def test_zip_records_pdf_status_in_manifest(self):
        from src.paper_writer.draft_bundle import PaperDraftBundle, PaperSection
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.output.zip_exporter import build_deliverable_zip

        paper = PaperDraftBundle(
            title="Test", sections={"r": PaperSection(name="结果", markdown="t=2.1", source="t")},
            source="test",
        )
        bundle = ResearchDeliverableBundle(
            project_id="pdf_test", title="PDF Test", paper_bundle=paper,
            analysis_cards=[{"method": "ttest", "apa_text": "t=2.1"}],
        )
        zip_bytes = build_deliverable_zip(bundle, mode="basic")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            assert "pdf_status" in manifest

    def test_zip_still_works_without_pdf(self):
        from src.paper_writer.research_deliverable import ResearchDeliverableBundle
        from src.output.zip_exporter import build_deliverable_zip

        bundle = ResearchDeliverableBundle(project_id="no_pdf", title="No PDF")
        zip_bytes = build_deliverable_zip(bundle, mode="basic")
        assert zip_bytes[:2] == b"PK"
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "manifest.json" in zf.namelist()


class TestWordComDetection:
    @patch("os.name", "posix")
    def test_non_windows_returns_false(self):
        assert not _word_com_available()


class TestLibreOfficeDetection:
    @patch("subprocess.run", side_effect=FileNotFoundError)
    @patch("pathlib.Path.exists", return_value=False)
    def test_not_installed_returns_false(self, _, __):
        assert not _libreoffice_available()
