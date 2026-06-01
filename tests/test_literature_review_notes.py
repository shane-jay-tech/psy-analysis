"""阅读笔记 CRUD + 聚合 + 导出测试。"""

from src.literature_review.models import LiteratureItem, ReadingNote
from src.literature_review.notes import (
    create_note,
    delete_note,
    edit_note,
    export_notes_markdown,
    filter_notes_by_type,
    get_notes_by_literature,
    get_notes_by_theme,
    notes_from_dict_list,
    notes_to_dict_list,
)


class TestNotesCRUD:
    def test_create_appends_note(self):
        notes = []
        n = create_note(notes, literature_key="lit1", content="X", type="方法")
        assert len(notes) == 1
        assert n.content == "X"
        assert n.type == "方法"

    def test_invalid_type_falls_back_to_other(self):
        notes = []
        n = create_note(notes, literature_key="lit1", content="X", type="不存在的类型")
        assert n.type == "其他"

    def test_edit_updates_content(self):
        notes = []
        n = create_note(notes, literature_key="lit1", content="原始")
        ok = edit_note(notes, n.note_id, "新的")
        assert ok is True
        assert notes[0].content == "新的"

    def test_edit_unknown_id_returns_false(self):
        notes = []
        ok = edit_note(notes, "nonexistent", "x")
        assert ok is False

    def test_delete_removes_note(self):
        notes = []
        n1 = create_note(notes, literature_key="lit1", content="A")
        n2 = create_note(notes, literature_key="lit1", content="B")
        delete_note(notes, n1.note_id)
        assert len(notes) == 1
        assert notes[0].note_id == n2.note_id


class TestNotesAggregation:
    def test_get_by_literature(self):
        notes = []
        create_note(notes, literature_key="lit1", content="A")
        create_note(notes, literature_key="lit2", content="B")
        create_note(notes, literature_key="lit1", content="C")
        result = get_notes_by_literature(notes, "lit1")
        assert len(result) == 2

    def test_get_by_theme(self):
        notes = []
        create_note(notes, literature_key="lit1", content="A")
        create_note(notes, literature_key="lit2", content="B")
        create_note(notes, literature_key="lit3", content="C")
        # 主题包含 lit1 + lit3
        result = get_notes_by_theme(notes, ["lit1", "lit3"])
        assert len(result) == 2
        contents = {n.content for n in result}
        assert contents == {"A", "C"}

    def test_filter_by_type(self):
        notes = []
        create_note(notes, literature_key="lit1", content="A", type="方法")
        create_note(notes, literature_key="lit1", content="B", type="结果")
        create_note(notes, literature_key="lit1", content="C", type="方法")
        result = filter_notes_by_type(notes, "方法")
        assert len(result) == 2


class TestNotesMarkdownExport:
    def test_empty_notes_returns_placeholder(self):
        md = export_notes_markdown([], title="测试")
        assert "# 测试" in md
        assert "暂无笔记" in md

    def test_export_with_lookup(self):
        notes = []
        create_note(notes, literature_key="lit1", content="**重点**", type="方法")
        item = LiteratureItem(key="lit1", title="X 研究", authors=["张三"], year=2023)
        md = export_notes_markdown(notes, literature_lookup={"lit1": item})
        assert "张三 (2023)" in md
        assert "X 研究" in md
        assert "**重点**" in md   # 保留 markdown


class TestNotesSerialization:
    def test_round_trip(self):
        notes = []
        create_note(notes, literature_key="lit1", content="A", type="方法")
        create_note(notes, literature_key="lit2", content="B", type="结果")
        data = notes_to_dict_list(notes)
        restored = notes_from_dict_list(data)
        assert len(restored) == 2
        assert restored[0].content == "A"
        assert restored[1].type == "结果"

    def test_invalid_input_returns_empty(self):
        assert notes_from_dict_list("not a list") == []
        assert notes_from_dict_list([]) == []
