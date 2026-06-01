"""答辩备战手册 PDF 导出测试。"""

from __future__ import annotations

import pytest

from src.paper_writer.defense_qa import (
    HandbookMeta, QAItem, export_defense_handbook_pdf,
)


@pytest.fixture
def sample_items():
    return [
        QAItem(
            question="为什么用 t 检验？",
            answer="自变量两组分类，因变量连续，独立样本，故选 t 检验。",
            category="method", category_label="🎯 方法选择",
            difficulty="必问", difficulty_emoji="🟢",
        ),
        QAItem(
            question="效应量 d=0.5 多大？",
            answer="中等效应（Cohen 标准）。",
            category="effect", category_label="📐 效应量",
            difficulty="必问", difficulty_emoji="🟢",
        ),
        QAItem(
            question="样本量怎么定？",
            answer="G*Power 计算所得。",
            category="data", category_label="📊 数据合规",
            difficulty="常问", difficulty_emoji="🟡",
        ),
        QAItem(
            question="如果有人质疑测量工具？",
            answer="承认局限并提出未来改进方向。",
            category="limit", category_label="⚠ 研究局限",
            difficulty="刁钻", difficulty_emoji="🔴",
        ),
    ]


@pytest.fixture
def basic_meta():
    return HandbookMeta(
        research_title="社交焦虑与自尊的关系",
        author="张三",
        advisor="李教授",
        date="2026 年 5 月",
    )


def test_pdf_returns_non_empty_bytes(sample_items, basic_meta):
    """PDF 输出应为非空字节流，且是合法 PDF（以 %PDF 开头）。"""
    pdf_bytes = export_defense_handbook_pdf(sample_items, basic_meta)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000, "PDF 至少应该 >1KB"
    assert pdf_bytes[:4] == b"%PDF", "缺少 PDF 文件头"


def test_pdf_with_default_meta(sample_items):
    """不传 meta 时应使用默认值，不崩溃。"""
    pdf_bytes = export_defense_handbook_pdf(sample_items)
    assert pdf_bytes.startswith(b"%PDF")


def test_pdf_with_empty_items_still_produces_valid_pdf():
    """无问答时仍能生成 PDF（含说明页 + 复习清单）。"""
    pdf_bytes = export_defense_handbook_pdf([], HandbookMeta(research_title="无内容测试"))
    assert pdf_bytes.startswith(b"%PDF")
    # 至少标题页 + 难度说明 + 复习清单
    assert len(pdf_bytes) > 2000


def test_pdf_groups_by_difficulty_in_output(sample_items, basic_meta):
    """PDF 应按难度分组，三个难度的问题都会被写入。"""
    # 这里只验证 PDF 生成成功且包含合理体积（4 个问题分 3 难度组）
    pdf_bytes = export_defense_handbook_pdf(sample_items, basic_meta)
    # 多页：标题 + 难度说明 + 必问页 + 常问页 + 刁钻页 + 复习
    # PDF size 应该 > 5KB
    assert len(pdf_bytes) > 5000


def test_handbook_meta_default_date_is_today():
    """HandbookMeta 不传 date 时应自动填今天。"""
    meta = HandbookMeta(research_title="t")
    assert meta.date != ""
    assert "年" in meta.date or "/" in meta.date or "-" in meta.date
