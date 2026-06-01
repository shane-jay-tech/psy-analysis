"""问卷题目解析器测试（v4.1）。

覆盖：
- 三种格式（.md / .docx / .txt）
- 三种抽题方式（编号 / bullet / 段落兜底）
- 反向题标记识别
- 边界（空、纯标题、错乱编号、混排表格、代码块）
"""

from __future__ import annotations

import io
from typing import List

import pytest

from src.questionnaire.items_loader import (
    ItemsDoc,
    items_doc_from_lines,
    parse_items_file,
)


def _bytesio(text: str) -> io.BytesIO:
    bio = io.BytesIO(text.encode("utf-8"))
    bio.name = "test.md"  # placeholder, overridden in caller
    return bio


# ---------------------------------------------------------------------------
# .txt 测试
# ---------------------------------------------------------------------------


class TestParseTxt:
    def test_numbered_simple(self):
        text = (
            "社交焦虑量表\n"
            "请根据自己最近一周的感受作答。\n"
            "\n"
            "1. 我在陌生人面前感到紧张\n"
            "2. 在聚会上我会担心别人怎么看我\n"
            "3. 公开发言前我会感到强烈不安\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        bio.name = "scale.txt"
        doc = parse_items_file(bio, "scale.txt")
        assert doc.source_format == "txt"
        assert doc.title == "社交焦虑量表"
        assert "请根据自己最近一周" in doc.instructions
        assert doc.items == [
            "我在陌生人面前感到紧张",
            "在聚会上我会担心别人怎么看我",
            "公开发言前我会感到强烈不安",
        ]
        assert doc.reverse_indices == []

    def test_chinese_numbering_styles(self):
        text = (
            "1、第一道题\n"
            "2） 第二道题\n"
            "(3) 第三道题\n"
            "（4） 第四道题\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.items == [
            "第一道题",
            "第二道题",
            "第三道题",
            "第四道题",
        ]

    def test_reverse_marker_variants(self):
        text = (
            "反向题示例\n"
            "1. 我喜欢和朋友交谈\n"
            "2. 我害怕被关注 (反向)\n"
            "3. 我能轻松开始对话 [R]\n"
            "4. 我对人群感到不适\n"
            "5. 我享受聚会 (R)\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.n_items() == 5
        assert doc.reverse_indices == [1, 2, 4]
        # 反向标记应被剥掉
        assert "(反向)" not in doc.items[1]
        assert "[R]" not in doc.items[2]
        assert "(R)" not in doc.items[4]
        assert doc.items[1] == "我害怕被关注"
        assert doc.items[4] == "我享受聚会"

    def test_gbk_encoding(self):
        text = "1. 用 GBK 编码的中文题目\n2. 第二道\n3. 第三道\n"
        raw = text.encode("gb18030")
        bio = io.BytesIO(raw)
        doc = parse_items_file(bio, "scale.txt")
        assert doc.items[0].startswith("用 GBK")
        assert doc.n_items() == 3

    def test_empty_file_raises(self):
        bio = io.BytesIO(b"")
        with pytest.raises(ValueError, match="未能在文件中识别到任何题目"):
            parse_items_file(bio, "empty.txt")

    def test_title_only_no_items_raises(self):
        bio = io.BytesIO("仅有标题\n".encode("utf-8"))
        with pytest.raises(ValueError):
            parse_items_file(bio, "x.txt")


# ---------------------------------------------------------------------------
# .md 测试
# ---------------------------------------------------------------------------


class TestParseMd:
    def test_md_h1_title_and_bullets(self):
        text = (
            "# 工作满意度量表\n"
            "\n"
            "请根据近一个月在公司的实际感受作答。\n"
            "\n"
            "- 我对工作内容感到满意\n"
            "- 上司给我足够的支持\n"
            "- 我感到工作压力适中\n"
            "- 同事之间关系融洽\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.md")
        assert doc.source_format == "md"
        assert doc.title == "工作满意度量表"
        assert "近一个月" in doc.instructions
        assert doc.n_items() == 4
        assert doc.items[0] == "我对工作内容感到满意"

    def test_md_skips_pipe_table(self):
        text = (
            "# 含表格的文件\n"
            "\n"
            "| col1 | col2 |\n"
            "|------|------|\n"
            "| a | b |\n"
            "\n"
            "1. 题目一\n"
            "2. 题目二\n"
            "3. 题目三\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.md")
        # 表格的 |--| 行不应混进来
        assert doc.n_items() == 3
        assert all("|" not in s for s in doc.items)

    def test_md_skips_code_block(self):
        text = (
            "# 题库\n"
            "\n"
            "```python\n"
            "1. 这不是题目，是代码\n"
            "```\n"
            "\n"
            "1. 真实题目一\n"
            "2. 真实题目二\n"
            "3. 真实题目三\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.md")
        assert doc.n_items() == 3
        assert doc.items[0] == "真实题目一"

    def test_markdown_extension_alias(self):
        text = "# t\n1. a\n2. b\n3. c\n"
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.markdown")
        assert doc.source_format == "md"
        assert doc.n_items() == 3


# ---------------------------------------------------------------------------
# .docx 测试
# ---------------------------------------------------------------------------


@pytest.fixture
def make_docx_bytes():
    """工厂：用 python-docx 造一份测试文档。"""
    from docx import Document

    def _make(paragraphs: List[tuple]) -> bytes:
        """paragraphs: [(text, style_name)]，style_name 可选用 "Heading 1" / 'Normal'。"""
        d = Document()
        for text, style in paragraphs:
            p = d.add_paragraph(text)
            if style:
                try:
                    p.style = style
                except Exception:
                    pass
        bio = io.BytesIO()
        d.save(bio)
        return bio.getvalue()

    return _make


class TestParseDocx:
    def test_docx_heading_and_numbered(self, make_docx_bytes):
        raw = make_docx_bytes([
            ("情绪调节量表", "Heading 1"),
            ("请根据日常感受作答。", None),
            ("", None),
            ("1. 我能控制自己的情绪", None),
            ("2. 我容易冲动 (反向)", None),
            ("3. 我能快速从负面情绪中恢复", None),
            ("4. 我在压力下保持冷静", None),
        ])
        bio = io.BytesIO(raw)
        doc = parse_items_file(bio, "scale.docx")
        assert doc.source_format == "docx"
        assert doc.title == "情绪调节量表"
        assert "日常感受" in doc.instructions
        assert doc.n_items() == 4
        assert doc.reverse_indices == [1]
        assert doc.items[1] == "我容易冲动"

    def test_docx_no_heading_first_line_as_title(self, make_docx_bytes):
        raw = make_docx_bytes([
            ("简易量表", None),
            ("1. 题目一", None),
            ("2. 题目二", None),
            ("3. 题目三", None),
        ])
        bio = io.BytesIO(raw)
        doc = parse_items_file(bio, "x.docx")
        assert doc.title == "简易量表"
        assert doc.n_items() == 3


# ---------------------------------------------------------------------------
# 混合场景与兜底
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_paragraph_fallback(self):
        text = (
            "无编号题目\n"
            "\n"
            "我经常感到焦虑\n"
            "我难以入睡\n"
            "我对未来感到担忧\n"
            "我的食欲减退\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.n_items() == 4
        assert "已按" in " ".join(doc.raw_warnings) or "段落" in " ".join(doc.raw_warnings)

    def test_unsupported_extension(self):
        with pytest.raises(ValueError, match="不支持"):
            parse_items_file(io.BytesIO(b"abc"), "scale.pdf")

    def test_high_reverse_ratio_warning(self):
        text = (
            "1. 题一 (反向)\n"
            "2. 题二 (反向)\n"
            "3. 题三 (反向)\n"
            "4. 题四\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.n_reverse() == 3
        assert any("反向题占比" in w for w in doc.raw_warnings)

    def test_messy_numbering_still_works(self):
        text = (
            "标题\n"
            "1. 题一\n"
            "3. 题三（编号跳了）\n"
            "5. 题五\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.n_items() == 3
        assert "题一" in doc.items[0]


# ---------------------------------------------------------------------------
# v4.5 段落兜底分支：指导语启发式不再吞题、且不再放过非典型指导语
# ---------------------------------------------------------------------------


class TestInstructionHeuristic:
    """段落兜底（无编号 / 无 bullet）分支的指导语过滤。"""

    def test_known_prefix_filtered_into_instructions(self):
        """以"指导语"开头的行进 instructions，不进 items。"""
        text = (
            "焦虑量表\n"
            "\n"
            "指导语：请根据您的真实情况作答\n"
            "\n"
            "我经常感到紧张\n"
            "我难以入睡\n"
            "我对未来担忧\n"
            "我食欲下降\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.n_items() == 4
        assert all("指导语" not in s for s in doc.items)
        assert "指导语" in doc.instructions or "请根据" in doc.instructions

    def test_long_text_with_keyword_filtered(self):
        """"本问卷不涉及对错，结果仅用于学术研究"长指导语不再被当题。"""
        text = (
            "工作满意度量表\n"
            "\n"
            "本问卷不涉及对错，您的回答将用于学术研究，请如实作答\n"
            "\n"
            "我对工作内容感到满意\n"
            "我对工作环境感到满意\n"
            "我对薪酬感到满意\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.n_items() == 3
        # 指导语行不应混入题目
        for s in doc.items:
            assert "本问卷" not in s
            assert "学术研究" not in s

    def test_super_long_line_filtered_even_without_keyword(self):
        """超过 80 字的长行直接当指导语（典型 Likert 题干很少这么长）。

        故意构造一个不命中前缀、也不含弱信号关键词的长段落，
        验证「长度阈值」路径独立生效。
        """
        long_intro = (
            "测验题目用于评估您在过去三十天里的整体心理状态，"
            "每一道题对应的时间段以最近一周为准请先想想再选择，"
            "并保持思路集中状态稳定不要随意作答以免影响信效度，"
            "整体填答时间大约为五分钟左右请尽量在安静环境下完成"
        )
        # 自检：长度足够触发"超长行"路径
        assert len(long_intro) >= 80, f"实际长度 {len(long_intro)}"
        text = (
            "工作压力量表\n"
            f"{long_intro}\n"
            "\n"
            "我感到工作量很大\n"
            "我感到时间不够用\n"
            "我感到精力透支\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.n_items() == 3
        for s in doc.items:
            assert "测验题目" not in s
            assert "信效度" not in s

    def test_multiple_instruction_prefixes(self):
        """多种前缀并存：感谢/欢迎/答题方式/注意事项 都该被过滤。"""
        text = (
            "情绪量表\n"
            "\n"
            "亲爱的同学：\n"
            "感谢您参与本次问卷\n"
            "答题方式：直接选择\n"
            "注意事项：请独立完成\n"
            "\n"
            "我心情愉快\n"
            "我精力充沛\n"
            "我充满希望\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.n_items() == 3
        # 没有指导语行混进题目
        joined = " | ".join(doc.items)
        for keyword in ["感谢", "答题方式", "注意事项", "亲爱的"]:
            assert keyword not in joined

    def test_instruction_does_not_eat_real_short_items(self):
        """启发式不应把真实的短题干误判为指导语。"""
        text = (
            "自评量表\n"
            "\n"
            "我感到放松\n"
            "我感到平静\n"
            "我感到愉快\n"
            "我感到满意\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.n_items() == 4

    def test_numbered_path_unaffected_by_heuristic(self):
        """有编号题目时，启发式不参与（编号题独立路径）。"""
        text = (
            "标题\n"
            "本问卷不涉及对错（这一行在编号路径里位于第 1 题之前，应进 instructions）\n"
            "1. 我经常担忧\n"
            "2. 我容易紧张\n"
            "3. 我难以放松\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        doc = parse_items_file(bio, "x.txt")
        assert doc.n_items() == 3
        # 题目纯净
        for s in doc.items:
            assert "本问卷" not in s
        # 指导语字段含这一行
        assert "本问卷" in doc.instructions

    def test_empty_after_filter_falls_through(self):
        """全是指导语 → 段落兜底拿不到 ≥ 3 条 → 抛 ValueError。"""
        text = (
            "标题\n"
            "\n"
            "指导语：请阅读\n"
            "本问卷不涉及对错\n"
            "感谢您的参与\n"
        )
        bio = io.BytesIO(text.encode("utf-8"))
        with pytest.raises(ValueError, match="未能.*识别到任何题目"):
            parse_items_file(bio, "x.txt")


class TestItemsDocFromLines:
    def test_factory_basic(self):
        d = items_doc_from_lines(
            ["题一", "题二", "题三"],
            title="测试量表",
            instructions="请作答",
            reverse_indices=[1],
        )
        assert d.title == "测试量表"
        assert d.n_items() == 3
        assert d.reverse_indices == [1]
        assert d.source_format == "manual"

    def test_factory_filters_empty(self):
        d = items_doc_from_lines(["a", "", "  ", "b"])
        assert d.n_items() == 2

    def test_factory_clamps_reverse_indices(self):
        d = items_doc_from_lines(["a", "b"], reverse_indices=[0, 5, -1])
        assert d.reverse_indices == [0]
