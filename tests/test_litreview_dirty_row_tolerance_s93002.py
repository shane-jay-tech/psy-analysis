# -*- coding: utf-8 -*-
"""s930-02：search/notes 脏行容错（s927-29 遗留·孪生漂移闭合）。

q927-29 点名「只修文献侧会出现文献容错、笔记/检索整表弃的新不一致」——本件把
`search.rescore_existing_items`（:230 一条脏 dict ⇒ 列表推导炸 ⇒ 整表弃）与
`notes.notes_from_dict_list`（:157 同形状）对齐到文献侧 s927-29 A 案语义：
**只兜解析/转换层（ValueError/TypeError），好行照常产出，脏行 logger 显式标注**。

运行：python -m pytest tests/test_litreview_dirty_row_tolerance_s93002.py -q
"""
import logging

from src.literature_review import notes as notes_mod
from src.literature_review import search as search_mod


def _good_item(i):
    return {"key": f"k{i}", "title": f"文献{i}", "authors": ["某人"],
            "year": 2024, "journal": "测试期刊", "doi": "", "abstract": "", "citation_count": 5}


def test_search_one_dirty_row_does_not_kill_the_table(caplog):
    """search：1 脏行（year="abc" 触发 int() ValueError）＋2 好行 ⇒ 产出 2 行
    且脏行在 caplog 有显式标注（不静默消失）。"""
    rows = [_good_item(1), {"key": "kbad", "title": "脏行", "year": "abc"}, _good_item(2)]
    with caplog.at_level(logging.WARNING, logger=search_mod.logger.name):
        out = search_mod.rescore_existing_items(rows, "测试问题", candidate_vars={})
    assert len(out) == 2, f"好行应照常产出，实得 {len(out)}"
    assert all(r["key"] in ("k1", "k2") for r in out)
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "脏行已跳过" in joined and "脏行" in joined, f"脏行未显式标注：{joined}"


def test_search_all_clean_zero_warnings(caplog):
    """反例对照：全好行 ⇒ 零 WARNING（容错层不在干净路径上噪音）。"""
    with caplog.at_level(logging.WARNING, logger=search_mod.logger.name):
        out = search_mod.rescore_existing_items([_good_item(1), _good_item(2)], "q", candidate_vars={})
    assert len(out) == 2
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_notes_one_dirty_row_does_not_kill_the_table(monkeypatch, caplog):
    """notes：1 脏行＋1 好行 ⇒ 产出 1 行且脏行显式标注。

    现版 ReadingNote.from_dict 全字段 .get 带默认（无可抛字段）——脏值注入用
    monkeypatch 模拟（证明容错层本身有牙）；若未来 from_dict 增加严格校验字段，
    本例无需改动即自然覆盖真实脏值。
    """
    real = notes_mod.ReadingNote.__dict__["from_dict"].__func__

    def _dirty_on_marker(cls, data):
        if isinstance(data, dict) and data.get("poison"):
            raise ValueError("synthetic dirty note (year-like parse)")
        return real(cls, data)

    monkeypatch.setattr(notes_mod.ReadingNote, "from_dict", classmethod(_dirty_on_marker))
    rows = [{"poison": True, "title": "脏笔记"}, {"title": "好笔记", "content": "x"}]
    with caplog.at_level(logging.WARNING, logger=notes_mod.logger.name):
        out = notes_mod.notes_from_dict_list(rows)
    assert len(out) == 1, f"好行应照常产出，实得 {len(out)}"
    assert out[0].content == "x"
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "脏行已跳过" in joined, f"脏行未显式标注：{joined}"


def test_notes_non_dict_still_skipped_and_clean_dict_passes():
    """既有语义保持：非 dict 行沿用 isinstance 过滤跳过（本单未改该面）。"""
    out = notes_mod.notes_from_dict_list(["不是dict", {"title": "好"}])
    assert len(out) == 1
