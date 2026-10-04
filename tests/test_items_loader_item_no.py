"""s1004-47：items_loader item_no 稳定题号解析层（d598 遗留 C3）。

有题号例断言原题号保留（含乱序/跳号/中文编号）；无题号例 item_nos 空表＝回落
位置生成（下游 Q1..Qn），其余解析输出与旧版 golden 逐字一致。仅解析层，零计分面。
"""

import io

from src.questionnaire.items_loader import parse_items_file


class TestItemNoCapture:
    def test_numbered_keeps_source_numbers(self):
        """编号题（含乱序 3/7/9 跳号）原题号逐字保留，不重排。"""
        text = (
            "# 测试量表\n\n"
            "3. 我经常感到心情平静（反向）\n"
            "7. 我对小事容易烦躁\n"
            "9. 我睡眠质量很好\n"
        )
        doc = parse_items_file(io.BytesIO(text.encode("utf-8")), "x.txt")
        assert doc.item_nos == [3, 7, 9]
        assert doc.n_items() == 3
        # 原题号保留的同时，题目文本与反向面不受影响
        assert doc.items[0].startswith("我经常感到心情平静")
        assert doc.reverse_indices == [0]

    def test_no_numbers_falls_back_positional(self):
        """bullet/段落题无源号 ⇒ item_nos 空表（回落 Q1..Qn），其余输出与旧版一致。"""
        text = (
            "# 测试量表\n\n"
            "- 我经常感到心情平静\n"
            "- 我对小事容易烦躁\n"
            "- 我睡眠质量很好\n"
        )
        doc = parse_items_file(io.BytesIO(text.encode("utf-8")), "x.txt")
        assert doc.item_nos == []
        assert doc.items == [
            "我经常感到心情平静",
            "我对小事容易烦躁",
            "我睡眠质量很好",
        ]
        assert doc.reverse_indices == []

    def test_mixed_numbered_and_bullet(self):
        """混排：编号条目带源号、bullet 条目=None，平行表长度=items。"""
        text = (
            "# 混排量表\n\n"
            "1. 第一题\n"
            "- 补充题\n"
            "2. 第二题\n"
        )
        doc = parse_items_file(io.BytesIO(text.encode("utf-8")), "x.txt")
        assert doc.item_nos == [1, None, 2]
        assert doc.n_items() == 3
