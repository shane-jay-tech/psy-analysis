"""测试 v4.4 维度粘贴解析：4 种格式 + 题号边界 + 异常处理。"""
from __future__ import annotations

import pandas as pd
import pytest

from src.questionnaire.dimensions_paste_parser import (
    parse_dimensions_text,
    parse_indices_text,
)


# ---------------------------------------------------------------------------
# parse_indices_text
# ---------------------------------------------------------------------------

class TestParseIndicesText:
    def test_simple_comma(self):
        idxs, errs = parse_indices_text("1,2,3", 10)
        assert idxs == [1, 2, 3]
        assert errs == []

    def test_chinese_comma(self):
        idxs, errs = parse_indices_text("1，2，3", 10)
        assert idxs == [1, 2, 3]
        assert errs == []

    def test_chinese_dunhao(self):
        idxs, errs = parse_indices_text("1、2、3", 10)
        assert idxs == [1, 2, 3]
        assert errs == []

    def test_range_dash(self):
        idxs, errs = parse_indices_text("1-5", 10)
        assert idxs == [1, 2, 3, 4, 5]
        assert errs == []

    def test_range_tilde(self):
        idxs, errs = parse_indices_text("3~5", 10)
        assert idxs == [3, 4, 5]
        assert errs == []

    def test_range_chinese_tilde(self):
        idxs, errs = parse_indices_text("3～5", 10)
        assert idxs == [3, 4, 5]
        assert errs == []

    def test_mixed_range_and_list(self):
        idxs, errs = parse_indices_text("1,2,5-7", 10)
        assert idxs == [1, 2, 5, 6, 7]
        assert errs == []

    def test_with_ti_prefix(self):
        idxs, errs = parse_indices_text("题1, 题2", 10)
        assert idxs == [1, 2]
        assert errs == []

    def test_with_q_prefix(self):
        idxs, errs = parse_indices_text("Q1, Q2", 10)
        assert idxs == [1, 2]
        assert errs == []

    def test_dedup(self):
        idxs, errs = parse_indices_text("1,2,2,1", 10)
        assert idxs == [1, 2]
        assert errs == []

    def test_out_of_range(self):
        idxs, errs = parse_indices_text("1, 5, 99", 10)
        assert idxs == [1, 5]
        assert any("99" in e and "超出" in e for e in errs)

    def test_invalid_token(self):
        idxs, errs = parse_indices_text("1, abc, 3", 10)
        assert idxs == [1, 3]
        assert any("abc" in e for e in errs)

    def test_reverse_range(self):
        """范围倒序（5-1）也能解析。"""
        idxs, errs = parse_indices_text("5-1", 10)
        assert idxs == [1, 2, 3, 4, 5]

    def test_empty(self):
        idxs, errs = parse_indices_text("", 10)
        assert idxs == []
        assert errs == []


# ---------------------------------------------------------------------------
# parse_dimensions_text — Markdown 表格
# ---------------------------------------------------------------------------

class TestMarkdownTable:
    def test_basic_with_header(self):
        text = """\
| 维度名 | 维度定义 | 题号 | 备注 |
| --- | --- | --- | --- |
| 上级互动 | 在上级面前的紧张感 | 1,2 | |
| 客户回避 | 陌生客户的回避 | 3 | |
| 会议发言 | 公开发言的恐惧 | 4-6 | 本研究创新 |
"""
        df, errs = parse_dimensions_text(text, 6)
        assert df is not None
        assert len(df) == 3
        assert df.iloc[0]["维度名"] == "上级互动"
        assert df.iloc[0]["维度定义"] == "在上级面前的紧张感"
        assert df.iloc[0]["题号（1-based，逗号分隔）"] == "1,2"
        assert df.iloc[2]["题号（1-based，逗号分隔）"] == "4,5,6"
        assert df.iloc[2]["备注"] == "本研究创新"
        assert df.attrs.get("parser") == "markdown"

    def test_no_header(self):
        """没有表头也能解析。"""
        text = """\
| A | 维度A定义 | 1,2 | |
| B | 维度B定义 | 3 | |
"""
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None
        assert len(df) == 2
        assert df.iloc[0]["维度名"] == "A"

    def test_three_columns_only(self):
        """只有 3 列（无备注）也能解析。"""
        text = """\
| 维度名 | 维度定义 | 题号 |
| --- | --- | --- |
| A | da | 1 |
"""
        df, errs = parse_dimensions_text(text, 3)
        assert df is not None
        assert df.iloc[0]["备注"] == ""


# ---------------------------------------------------------------------------
# parse_dimensions_text — Tab 分隔
# ---------------------------------------------------------------------------

class TestTabSeparated:
    def test_basic(self):
        text = "上级互动\t在上级面前的紧张感\t1,2\t\n客户回避\t陌生客户的回避\t3\t\n"
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None
        assert len(df) == 2
        assert df.iloc[0]["维度名"] == "上级互动"
        assert df.iloc[1]["题号（1-based，逗号分隔）"] == "3"
        assert df.attrs.get("parser") == "tab"

    def test_with_header_skipped(self):
        text = "维度名\t维度定义\t题号\t备注\n会议发言\t公开发言恐惧\t1-3\t本研究创新\n"
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None
        assert len(df) == 1  # 表头被跳过
        assert df.iloc[0]["维度名"] == "会议发言"
        assert df.iloc[0]["题号（1-based，逗号分隔）"] == "1,2,3"


# ---------------------------------------------------------------------------
# parse_dimensions_text — CSV
# ---------------------------------------------------------------------------

class TestCSV:
    def test_csv_with_quoted_indices(self):
        """CSV 题号字段含逗号，必须加引号。"""
        text = '上级互动,在上级面前的紧张感,"1,2",\n客户回避,陌生客户的回避,3,\n'
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None
        assert len(df) == 2
        assert df.iloc[0]["题号（1-based，逗号分隔）"] == "1,2"


# ---------------------------------------------------------------------------
# parse_dimensions_text — 段落键值
# ---------------------------------------------------------------------------

class TestParagraphKV:
    def test_basic_paragraph(self):
        text = """\
上级互动
定义：在上级面前的紧张感
题号：1, 2

客户回避
定义：陌生客户的回避
题号：3
备注：本研究创新
"""
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None, f"errs={errs}"
        assert len(df) == 2
        assert df.iloc[0]["维度名"] == "上级互动"
        assert df.iloc[0]["维度定义"] == "在上级面前的紧张感"
        assert df.iloc[0]["题号（1-based，逗号分隔）"] == "1,2"
        assert df.iloc[1]["备注"] == "本研究创新"

    def test_inline_paren_definition(self):
        """形如 "上级互动（在上级面前的紧张感）" 自动拆名+定义。"""
        text = """\
上级互动（在上级面前的紧张感）
题号：1, 2
"""
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["维度名"] == "上级互动"
        assert df.iloc[0]["维度定义"] == "在上级面前的紧张感"
        assert df.iloc[0]["题号（1-based，逗号分隔）"] == "1,2"

    def test_numbered_prefix_stripped(self):
        """形如 "1. 上级互动" 编号会被剥离。"""
        text = """\
1. 上级互动
定义：在上级面前的紧张感
题号：1, 2
"""
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None
        assert df.iloc[0]["维度名"] == "上级互动"


# ---------------------------------------------------------------------------
# 越界 / 重名 / 重复归属
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_duplicate_assignment_keeps_first(self):
        """题号被两个维度归属 → 第一个保留，第二个被剥离 + warning。"""
        text = """\
| A | da | 1,2 | |
| B | db | 2,3 | |
"""
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None
        assert df.iloc[0]["题号（1-based，逗号分隔）"] == "1,2"
        # B 应只剩 3
        assert df.iloc[1]["题号（1-based，逗号分隔）"] == "3"
        assert any("已被前面" in e or "占用" in e for e in errs)

    def test_duplicate_name_dropped(self):
        text = """\
| A | da1 | 1 | |
| A | da2 | 2 | |
"""
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None
        assert len(df) == 1  # 第二行被丢
        assert any("重复" in e for e in errs)

    def test_empty_name_dropped(self):
        text = """\
| | da | 1 | |
| B | db | 2 | |
"""
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["维度名"] == "B"
        assert any("维度名为空" in e for e in errs)

    def test_out_of_range_indices_warn(self):
        text = """\
| A | da | 1,2,99 | |
"""
        df, errs = parse_dimensions_text(text, 5)
        assert df is not None
        assert df.iloc[0]["题号（1-based，逗号分隔）"] == "1,2"
        assert any("99" in e and "超出" in e for e in errs)

    def test_empty_text(self):
        df, errs = parse_dimensions_text("", 5)
        assert df is None
        assert errs

    def test_garbage_text(self):
        df, errs = parse_dimensions_text("hello world", 5)
        # 兜底 CSV 解析会把 "hello world" 当作一个 cell；视为名而无定义/题号
        # 依然返回 1 行 + warnings；这是合理的"宽松"行为
        if df is not None:
            assert df.iloc[0]["维度名"] == "hello world"
            assert any("题号为空" in e or "定义" in e for e in errs)


# ---------------------------------------------------------------------------
# DataFrame 形状与列名
# ---------------------------------------------------------------------------

class TestDataFrameShape:
    def test_columns_match_editor(self):
        text = "| A | da | 1 | n |\n"
        df, _ = parse_dimensions_text(text, 5)
        assert list(df.columns) == [
            "维度名", "维度定义", "题号（1-based，逗号分隔）", "备注",
        ]

    def test_attrs_records_parser(self):
        for text, expected in [
            ("| A | da | 1 | |\n", "markdown"),
            ("A\tda\t1\t\n", "tab"),
        ]:
            df, _ = parse_dimensions_text(text, 5)
            assert df.attrs.get("parser") == expected
