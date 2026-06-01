"""论文交付包 ZIP 测试。"""

from __future__ import annotations

import io
import zipfile

import plotly.graph_objects as go
import pytest

from src.output.delivery_package import (
    DeliverySpec, build_delivery_package,
)


@pytest.fixture
def docx_bytes():
    """模拟一个 Word 字节流（不需要是真合法 docx，只检查打包入口）。"""
    return b"PK\x03\x04 fake docx content here"


@pytest.fixture
def pdf_bytes():
    return b"%PDF-1.3\nfake pdf body\n%%EOF"


@pytest.fixture
def fig():
    return go.Figure(go.Scatter(x=[1, 2], y=[3, 4]))


def test_zip_has_correct_structure_with_all_components(docx_bytes, pdf_bytes, fig):
    """v2.9: 全量交付包含 docx + pdf + 图表 PNG + README。"""
    spec = DeliverySpec(
        thesis_docx=docx_bytes,
        handbook_pdf=pdf_bytes,
        figures=[
            {"fig": fig, "test_name_zh": "独立样本t检验",
             "chart_type": "箱线图", "variables": ["焦虑"]},
        ],
        research_title="测试论文",
        author="张三",
    )
    zip_bytes = build_delivery_package(spec)
    assert zip_bytes[:2] == b"PK"

    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = zf.namelist()
    assert "论文初稿.docx" in names
    assert "答辩备战手册.pdf" in names
    assert "README.txt" in names

    readme = zf.read("README.txt").decode("utf-8-sig")
    assert "测试论文" in readme
    assert "张三" in readme


def test_zip_gracefully_degrades_without_thesis(pdf_bytes):
    """缺失 thesis_docx 时 README 应说明，并不崩溃。"""
    spec = DeliverySpec(thesis_docx=None, handbook_pdf=pdf_bytes)
    zip_bytes = build_delivery_package(spec)
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = zf.namelist()
    assert "论文初稿.docx" not in names
    assert "答辩备战手册.pdf" in names
    readme = zf.read("README.txt").decode("utf-8-sig")
    assert "未生成" in readme or "请在向导第 7 步" in readme


def test_zip_gracefully_degrades_without_handbook(docx_bytes):
    """缺失 handbook_pdf 时 README 应说明，不崩溃。"""
    spec = DeliverySpec(thesis_docx=docx_bytes, handbook_pdf=None)
    zip_bytes = build_delivery_package(spec)
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = zf.namelist()
    assert "答辩备战手册.pdf" not in names
    readme = zf.read("README.txt").decode("utf-8-sig")
    assert "答辩备战手册" in readme


def test_zip_with_no_figures_lists_in_readme(docx_bytes, pdf_bytes):
    """无图表时 README 提示「未收藏图表」。"""
    spec = DeliverySpec(
        thesis_docx=docx_bytes, handbook_pdf=pdf_bytes, figures=[],
    )
    zip_bytes = build_delivery_package(spec)
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    readme = zf.read("README.txt").decode("utf-8-sig")
    assert "未收藏" in readme or "图表集" in readme


def test_zip_completely_empty_still_produces_valid_zip():
    """完全空的 spec 应生成有效 ZIP（仅含 README）。"""
    spec = DeliverySpec()
    zip_bytes = build_delivery_package(spec)
    assert zip_bytes[:2] == b"PK"
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    assert "README.txt" in zf.namelist()


def test_readme_lists_all_inventory_items(docx_bytes, pdf_bytes):
    """README 应列出所有交付物清单。"""
    spec = DeliverySpec(
        thesis_docx=docx_bytes, handbook_pdf=pdf_bytes,
        research_title="社交焦虑研究", author="李四",
        extra_notes="本论文 2026-06 提交终审版",
    )
    zip_bytes = build_delivery_package(spec)
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    readme = zf.read("README.txt").decode("utf-8-sig")
    assert "社交焦虑研究" in readme
    assert "李四" in readme
    assert "📄" in readme  # 文件清单 emoji
    assert "使用说明" in readme
    assert "终审版" in readme  # extra_notes
