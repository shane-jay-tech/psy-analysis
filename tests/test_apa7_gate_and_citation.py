"""APA7 门禁 A3 + 引用 B 类必修项回归（任务 20260909-014512-pa3n）。

用例全部来自 docs/insights/apa7-gate-escape-scan-20260905.md 的扫描表
（A3 NaN / B1 无作者 / B3 无年份 n.d. / B5 空标题拒绝 / B8 无来源无裸斜体 / B11 >20 作者截断）。
纯合成数据，零 LLM 零联网。
"""
import math

import pytest

from src.output.formatter import check_effect_size_required
from src.paper_writer.literature_library import format_citation_apa7


# ---------------- A3：效应量 NaN/非法值拦截 ----------------

class _Result:
    def __init__(self, effect_size):
        self.effect_size = effect_size


def test_a3_nan_effect_size_intercepted():
    ok, _ = check_effect_size_required(
        {"test_type": "t_test", "result": None, "effect_size": float("nan")})
    assert ok is False


def test_a3_nan_on_result_object_intercepted():
    ok, _ = check_effect_size_required(
        {"test_type": "t_test", "result": _Result(float("nan"))})
    assert ok is False


def test_a3_valid_effect_size_still_passes():
    ok, _ = check_effect_size_required(
        {"test_type": "t_test", "result": _Result(0.5)})
    assert ok is True


# ---------------- B 类必修项 ----------------

def test_b1_missing_author_title_moves_up():
    out = format_citation_apa7((("", 2020, "Title Here", "Journal")))
    assert out == "Title Here (2020). Title Here. *Journal*."


def test_b2_none_author_never_prints_none():
    out = format_citation_apa7(((None, 2020, "Title Here", "Journal")))
    assert "None" not in out


def test_b3_b4_missing_or_none_year_is_n_d():
    assert "(n.d.)" in format_citation_apa7((("Smith", "", "T", "J")))
    assert "(n.d.)" in format_citation_apa7((("Smith", None, "T", "J")))


def test_b5_empty_title_rejected():
    with pytest.raises(ValueError):
        format_citation_apa7((("A", 2020, "", "J")))


def test_b8_book_without_source_no_bare_italic():
    out = format_citation_apa7((("A", 2020, "Book Title", "")))
    assert out == "A (2020). Book Title."
    assert "**" not in out


def test_b11_more_than_20_authors_truncated():
    authors = ", ".join(f"A{i}" for i in range(1, 22))  # 21 人
    out = format_citation_apa7(((authors, 2020, "T", "J")))
    assert "A19" in out and "…, & A21" in out and "A20" not in out


def test_normal_entry_unchanged():
    assert format_citation_apa7(("温忠麟, 叶宝娟", 2014, "T", "J")) == \
        "温忠麟, 叶宝娟 (2014). T. *J*."
    assert math.isnan(float("nan"))  # 语义哨兵：math 可用性自证
