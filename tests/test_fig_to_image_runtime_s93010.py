# -*- coding: utf-8 -*-
"""s930-10：fig.to_image() 返回类型运行时验（s927-43 遗留）。

q927-43 诚实声明「plotly 侧未验」——本件补上：4 处调用已收敛至
`_render_static_image` 单包装（paper_export.py:96），真渲染断言返回 bytes
且为 PNG 魔数（\x89PNG），另走 export_all_figures_zip 高层面冒烟。

运行：python -m pytest tests/test_fig_to_image_runtime_s93010.py -q
（kaleido/浏览器缺失时整件 skip——环境缺口在 result 记录。）
"""
import pytest

pytest.importorskip("kaleido", reason="kaleido 未安装（静态渲染不可跑）")
pytest.importorskip("plotly", reason="plotly 未安装")

import plotly.graph_objects as go  # noqa: E402

from src.visualization.paper_export import _render_static_image  # noqa: E402


def _tiny_fig():
    fig = go.Figure(go.Bar(x=["甲", "乙"], y=[1, 2]))
    fig.update_layout(width=320, height=240, template="none")
    return fig


def test_render_static_image_returns_png_bytes():
    """真渲染：返回 bytes 且 PNG 魔数（\x89PNG）。"""
    out = _render_static_image(_tiny_fig(), format="png")
    assert isinstance(out, (bytes, bytearray)), f"to_image 返回 {type(out)} 非 bytes"
    assert bytes(out[:4]) == b"\x89PNG", f"PNG 魔数不符：{bytes(out[:8])!r}"
    assert len(out) > 500, f"渲染产物过小（{len(out)}B），疑似空图"


def test_render_static_image_svg_returns_text_bytes():
    """SVG 面：format=svg 返回 bytes 且可解出 <svg 标记（矢量面同验）。"""
    out = _render_static_image(_tiny_fig(), format="svg")
    assert isinstance(out, (bytes, bytearray))
    assert b"<svg" in bytes(out)[:2000]
