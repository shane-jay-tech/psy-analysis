"""文献综述数据模型测试。"""

from src.literature_review.models import (
    NOTE_TYPES,
    READING_STATUS_DONE,
    READING_STATUS_READING,
    READING_STATUS_UNREAD,
    GapAnalysis,
    LiteratureItem,
    LiteratureMatrix,
    ReadingNote,
    ThemeCluster,
)


class TestLiteratureItem:
    def test_default_initialization(self):
        it = LiteratureItem(title="Test", year=2024)
        assert it.key   # 自动生成
        assert it.reading_status == READING_STATUS_UNREAD
        assert it.relevance_score == 0.0

    def test_to_dict_from_dict_round_trip(self):
        it = LiteratureItem(
            title="X 的影响", authors=["张三", "李四"], year=2024,
            doi="10.1234/abc", relevance_score=0.85,
            reading_status=READING_STATUS_READING,
            tags=["核心"], abstract="摘要内容",
        )
        data = it.to_dict()
        restored = LiteratureItem.from_dict(data)
        assert restored.title == "X 的影响"
        assert restored.authors == ["张三", "李四"]
        assert restored.relevance_score == 0.85
        assert restored.reading_status == READING_STATUS_READING
        assert "核心" in restored.tags

    def test_from_crawled_compatibility(self):
        from types import SimpleNamespace
        crawled = SimpleNamespace(
            title="测试",
            authors=["A"],
            year=2023,
            journal="期刊",
            doi="10.1/x",
            abstract="摘",
            citation_count=10,
            source="crossref",
            url="http://x",
        )
        it = LiteratureItem.from_crawled(crawled)
        assert it.title == "测试"
        assert it.year == 2023
        assert it.citation_count == 10
        assert it.reading_status == READING_STATUS_UNREAD   # 新加字段

    def test_short_citation_format(self):
        it = LiteratureItem(
            title="非常长的论文标题超过了六十个字符的限制需要被截短显示否则太占地方",
            authors=["Smith"], year=2022,
        )
        sc = it.short_citation
        assert "Smith (2022)" in sc
        assert len(sc) <= 100

    def test_reading_status_emoji(self):
        it = LiteratureItem(reading_status=READING_STATUS_DONE)
        assert it.reading_status_emoji == "📘"


class TestReadingNote:
    def test_default_init(self):
        n = ReadingNote(literature_key="lit1", content="笔记")
        assert n.note_id
        assert n.type == "其他"
        assert n.created_at == n.updated_at

    def test_update_content_changes_updated_at(self):
        import time
        n = ReadingNote(content="原始")
        original = n.updated_at
        time.sleep(1.05)
        n.update_content("新的")
        assert n.content == "新的"
        assert n.updated_at != original

    def test_round_trip(self):
        n = ReadingNote(
            literature_key="lit1", content="X 的实验", type="方法",
            page_or_section="p.42",
        )
        restored = ReadingNote.from_dict(n.to_dict())
        assert restored.content == "X 的实验"
        assert restored.type == "方法"
        assert restored.page_or_section == "p.42"


class TestThemeCluster:
    def test_round_trip(self):
        t = ThemeCluster(
            theme_name="主题1", literature_keys=["k1", "k2"],
            centroid_keywords=["焦虑", "压力"], summary="覆盖 2 篇",
        )
        restored = ThemeCluster.from_dict(t.to_dict())
        assert restored.theme_name == "主题1"
        assert "焦虑" in restored.centroid_keywords


class TestGapAnalysis:
    def test_round_trip(self):
        g = GapAnalysis(
            gap_description="缺X方面证据",
            suggested_direction="可探索 X",
            confidence=0.7,
            source="llm",
        )
        restored = GapAnalysis.from_dict(g.to_dict())
        assert restored.gap_description == "缺X方面证据"
        assert restored.confidence == 0.7
        assert restored.source == "llm"


class TestLiteratureMatrix:
    def test_set_get_cell(self):
        m = LiteratureMatrix(dimensions=["样本量"])
        m.set_cell("lit1", "样本量", "200")
        assert m.get_cell("lit1", "样本量") == "200"
        assert m.get_cell("lit2", "样本量") == ""

    def test_add_remove_dimension(self):
        m = LiteratureMatrix(dimensions=["A", "B"])
        m.add_dimension("C")
        assert "C" in m.dimensions
        m.remove_dimension("A")
        assert "A" not in m.dimensions

    def test_remove_dimension_clears_cells(self):
        m = LiteratureMatrix(dimensions=["A", "B"])
        m.set_cell("lit1", "A", "v1")
        m.set_cell("lit1", "B", "v2")
        m.remove_dimension("A")
        assert "A" not in m.cells["lit1"]
        assert m.cells["lit1"]["B"] == "v2"

    def test_empty_cells_count(self):
        m = LiteratureMatrix(dimensions=["A", "B"])
        m.set_cell("lit1", "A", "v")
        m.set_cell("lit2", "A", "v")
        # lit1.B and lit2.B 为空
        assert m.empty_cells_count() == 2

    def test_round_trip(self):
        m = LiteratureMatrix(dimensions=["A", "B"], highlighted_keys=["lit1"])
        m.set_cell("lit1", "A", "v1")
        restored = LiteratureMatrix.from_dict(m.to_dict())
        assert restored.dimensions == ["A", "B"]
        assert restored.get_cell("lit1", "A") == "v1"
        assert restored.highlighted_keys == ["lit1"]


class TestLiteratureMatrixDeepCopyGate:
    """s1002-11（s924-64 B-3 升格门禁）：from_dict 的防御性拷贝＝session_state 隔离层。

    矿源 E4 运行时证成的形态钉成门禁：调用方侧对象（raw dict / cells 内层 dict /
    dimensions / highlighted_keys）任意变异后， LiteratureMatrix 内部状态必须不变。
    变异刀：浅拷贝实现（to_dict 去掉 dict(v)/list(...) 包裹）会让本例当场红。
    """

    def test_caller_side_mutations_never_leak_into_matrix(self):
        raw = {
            "dimensions": ["a", "b"],
            "cells": {"k1": {"a": "v1"}},
            "highlighted_keys": ["k1"],
        }
        m = LiteratureMatrix.from_dict(raw)

        # 调用方侧四路变异（E4 同款）
        raw["cells"]["k1"]["a"] = "MUTATED"
        raw["cells"]["k2"] = {"a": "injected"}
        raw["dimensions"].append("POLLUTED")
        raw["highlighted_keys"].append("X")

        assert m.get_cell("k1", "a") == "v1", "内层 cells 被别名共享（浅拷贝）"
        assert "k2" not in m.cells, "外层 cells 被别名共享"
        assert m.dimensions == ["a", "b"], "dimensions 被别名共享"
        assert m.highlighted_keys == ["k1"], "highlighted_keys 被别名共享"

        # 反向：矩阵侧变异也不得渗回 raw（隔离是双向的）
        m.set_cell("k1", "a", "CHANGED")
        m.dimensions.append("M2")
        assert raw["cells"]["k1"]["a"] == "MUTATED"  # raw 保持调用方自己的值
        assert "M2" not in raw["dimensions"]
