"""图表收藏夹测试。"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from src.utils.figure_collection import (
    FigureCollection, FigureEntry, get_collection_from_session,
)


@pytest.fixture
def fig():
    return go.Figure(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], mode="lines+markers"))


@pytest.fixture
def fig2():
    return go.Figure(go.Bar(x=["A", "B"], y=[1, 2]))


def test_add_returns_unique_ids(fig, fig2):
    coll = FigureCollection()
    id1 = coll.add(title="图1", test_type="t", variables=["x"], fig_object=fig, chart_type="散点图")
    id2 = coll.add(title="图2", test_type="t", variables=["y"], fig_object=fig2, chart_type="柱状图")
    assert id1 != id2
    assert len(coll) == 2


def test_remove_existing_id(fig):
    coll = FigureCollection()
    fid = coll.add(title="图", test_type="t", variables=["x"], fig_object=fig)
    assert coll.remove(fid) is True
    assert len(coll) == 0


def test_remove_nonexistent_returns_false(fig):
    coll = FigureCollection()
    coll.add(title="图", test_type="t", variables=["x"], fig_object=fig)
    assert coll.remove("nonexistent-id") is False
    assert len(coll) == 1


def test_update_note(fig):
    coll = FigureCollection()
    fid = coll.add(title="图", test_type="t", variables=["x"], fig_object=fig)
    assert coll.update_note(fid, "重要图表，论文必用") is True
    assert coll.get(fid).note == "重要图表，论文必用"


def test_clear_all(fig, fig2):
    coll = FigureCollection()
    coll.add(title="A", test_type="t", variables=[], fig_object=fig)
    coll.add(title="B", test_type="t", variables=[], fig_object=fig2)
    n = coll.clear_all()
    assert n == 2
    assert len(coll) == 0


def test_find_duplicate_matches_same_signature(fig, fig2):
    """相同 test_type + variables + chart_type 应被识别为重复。"""
    coll = FigureCollection()
    coll.add(
        title="第一次", test_type="independent_ttest",
        variables=["焦虑", "性别"], fig_object=fig, chart_type="箱线图",
    )
    dup = coll.find_duplicate(
        test_type="independent_ttest",
        variables=["性别", "焦虑"],  # 顺序不同
        chart_type="箱线图",
    )
    assert dup is not None
    assert dup.title == "第一次"


def test_find_duplicate_returns_none_for_different_signature(fig):
    coll = FigureCollection()
    coll.add(
        title="A", test_type="independent_ttest", variables=["x"],
        fig_object=fig, chart_type="箱线图",
    )
    assert coll.find_duplicate(
        test_type="one_way_anova", variables=["x"], chart_type="箱线图",
    ) is None


def test_serialize_and_restore_preserves_figure(fig, fig2):
    """序列化往返后图表对象仍可重建。"""
    coll = FigureCollection()
    coll.add(title="散点", test_type="pearson_corr", variables=["x", "y"],
             fig_object=fig, note="测试备注", chart_type="散点图")
    coll.add(title="柱状", test_type="one_way_anova", variables=["g"],
             fig_object=fig2, chart_type="柱状图")

    data = coll.to_serializable()
    assert isinstance(data, list)
    assert len(data) == 2
    assert all("fig_json" in d for d in data)

    restored = FigureCollection.from_serializable(data)
    assert len(restored) == 2
    e0 = restored.entries[0]
    assert e0.title == "散点"
    assert e0.note == "测试备注"
    assert e0.variables == ["x", "y"]
    assert isinstance(e0.fig_object, go.Figure)
    # plotly figure 应保留 trace
    assert len(e0.fig_object.data) == 1


def test_session_state_helper_initializes_empty():
    fake_state = {}
    coll = get_collection_from_session(fake_state)
    assert isinstance(coll, FigureCollection)
    assert len(coll) == 0
    # 二次调用返回同一实例
    coll2 = get_collection_from_session(fake_state)
    assert coll is coll2


def test_from_serializable_empty_returns_empty_collection():
    assert len(FigureCollection.from_serializable([])) == 0
    assert len(FigureCollection.from_serializable(None)) == 0


def test_from_serializable_skips_corrupt_entries(fig):
    """单条 corrupt 不影响其他条目恢复。"""
    coll = FigureCollection()
    coll.add(title="OK", test_type="t", variables=["x"], fig_object=fig)
    data = coll.to_serializable()
    # 加一个 corrupt 项
    data.append({"figure_id": "bad", "fig_json": "{not json"})
    restored = FigureCollection.from_serializable(data)
    # 至少还原 OK 那条
    assert len(restored) >= 1
