# -*- coding: utf-8 -*-
"""s1004-08：export_all_figures_zip 高层冒烟钉桩（zip 打包语义面）。

kaleido 可用 ⇒ 断言 zip 存在/成员名/可开（2+ 断言）；
kaleido 缺席 ⇒ 函数自身降级（说明 txt + 错误说明），用例改断言降级形态并注明。
（两种环境都有断言面，不 skip——比 importorskip 更强：降级形态也被钉住。）
"""
from __future__ import annotations

import io
import zipfile

import plotly.graph_objects as go
import pytest

from src.visualization.paper_export import _kaleido_available, export_all_figures_zip


def _spec(i: int):
    fig = go.Figure(go.Bar(x=["a", "b"], y=[i, i + 1]))
    return {"fig": fig, "test_type": f"ttest_{i}",
            "test_name_zh": f"独立样本t检验{i}", "chart_type": "箱线图",
            "variables": ["A", "B"]}


def test_zip_smoke_members_and_openable():
    specs = [_spec(1), _spec(2)]
    blob = export_all_figures_zip(specs)
    assert isinstance(blob, (bytes, bytearray)) and blob[:2] == b"PK"
    zf = zipfile.ZipFile(io.BytesIO(blob))
    names = set(zf.namelist())
    assert zf.testzip() is None
    if _kaleido_available():
        assert "图1_独立样本t检验1_箱线图.png" in names
        assert "图2_独立样本t检验2_箱线图.png" in names
        assert any(n.endswith("图表说明.txt") for n in names)
        pngs = [n for n in names if n.endswith(".png")]
        assert zf.read(sorted(pngs)[0])[:4] == b"\x89PNG"
    else:
        assert any(n.endswith("图表说明.txt") for n in names)
        desc = zf.read([n for n in names if n.endswith("图表说明.txt")][0])
        assert "kaleido 未安装".encode("utf-8") in desc


def test_zip_empty_specs_still_valid_zip():
    blob = export_all_figures_zip([])
    zf = zipfile.ZipFile(io.BytesIO(blob))
    assert zf.testzip() is None
    assert any(n.endswith("图表说明.txt") for n in zf.namelist())
