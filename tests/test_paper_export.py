"""论文版图表导出测试 — apply_paper_style 不依赖 kaleido，可纯单元测试。

PNG 实际渲染依赖 kaleido 二进制；如本机已安装则连同烟雾测试一起跑，
否则跳过 (xfail) 但不视为失败。
"""

from __future__ import annotations

import importlib

import pytest
import plotly.graph_objects as go

from src.visualization.paper_export import (
    PAPER_PALETTES, KaleidoMissingError, apply_paper_style,
    get_palette_label, to_paper_png,
)


@pytest.fixture
def sample_fig():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], mode="lines+markers", name="A"))
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[2, 3, 5], mode="lines+markers", name="B"))
    fig.update_layout(title="测试图")
    return fig


def test_palette_constants_have_expected_keys():
    assert set(PAPER_PALETTES.keys()) == {"color", "grayscale", "mono"}
    for name, palette in PAPER_PALETTES.items():
        assert len(palette) >= 4, f"{name} 配色至少需要 4 色"


def test_apply_paper_style_does_not_mutate_original(sample_fig):
    original_first_color = sample_fig.data[0].line.color if sample_fig.data[0].line else None
    styled = apply_paper_style(sample_fig, palette="grayscale")
    assert styled is not sample_fig
    # 原图未被修改
    assert sample_fig.data[0].line.color == original_first_color


def test_apply_paper_style_grayscale_uses_dark_colors(sample_fig):
    styled = apply_paper_style(sample_fig, palette="grayscale")
    first_line_color = styled.data[0].line.color
    assert first_line_color in PAPER_PALETTES["grayscale"]


def test_apply_paper_style_mono_makes_lines_distinguishable_by_dash(sample_fig):
    styled = apply_paper_style(sample_fig, palette="mono")
    dashes = [trace.line.dash for trace in styled.data]
    # 黑白模式下颜色相同，必须用 dash 区分
    assert len(set(dashes)) >= 2, "纯黑模式下应使用不同 dash 区分多条线"


def test_apply_paper_style_layout_is_publication_grade(sample_fig):
    styled = apply_paper_style(sample_fig, palette="color")
    assert styled.layout.plot_bgcolor == "white"
    assert styled.layout.paper_bgcolor == "white"
    assert styled.layout.template.layout.plot_bgcolor in ("white", "rgba(255,255,255,1)")


def test_get_palette_label_returns_chinese():
    assert "灰度" in get_palette_label("grayscale")
    assert "彩色" in get_palette_label("color")
    assert "纯黑" in get_palette_label("mono")


def test_to_paper_png_raises_friendly_error_when_kaleido_missing(sample_fig, monkeypatch):
    """模拟 kaleido 不可用，确认抛 KaleidoMissingError 并含安装提示。"""
    import src.visualization.paper_export as pe
    monkeypatch.setattr(pe, "_kaleido_available", lambda: False)

    with pytest.raises(KaleidoMissingError) as exc_info:
        to_paper_png(sample_fig)
    assert "pip install" in str(exc_info.value)


def test_export_zip_returns_zip_with_description_when_kaleido_missing(monkeypatch, sample_fig):
    """v2.8: kaleido 缺失时仍返回有效 ZIP（含错误说明），不崩溃。"""
    import src.visualization.paper_export as pe
    monkeypatch.setattr(pe, "_kaleido_available", lambda: False)

    from src.visualization.paper_export import export_all_figures_zip
    specs = [{
        "fig": sample_fig, "test_name_zh": "测试", "chart_type": "测试图",
        "variables": ["x"],
    }]
    zip_bytes = export_all_figures_zip(specs)
    # ZIP 文件头
    assert zip_bytes[:2] == b"PK"
    # 应含说明 txt
    import zipfile, io
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    assert "图表说明.txt" in zf.namelist()
    desc = zf.read("图表说明.txt").decode("utf-8-sig")
    assert "kaleido" in desc.lower()


def test_export_zip_empty_specs():
    """v2.8: 空 specs 返回包含说明的 ZIP。"""
    from src.visualization.paper_export import export_all_figures_zip
    zip_bytes = export_all_figures_zip([])
    assert zip_bytes[:2] == b"PK"


@pytest.mark.skipif(
    importlib.util.find_spec("kaleido") is None,
    reason="kaleido not installed",
)
def test_export_zip_smoke(sample_fig):
    """v2.8: 有 kaleido 时端到端打包成功。"""
    from src.visualization.paper_export import export_all_figures_zip
    import zipfile, io
    specs = [
        {"fig": sample_fig, "test_name_zh": "独立样本t检验", "chart_type": "箱线图", "variables": ["焦虑"]},
        {"fig": sample_fig, "test_name_zh": "独立样本t检验", "chart_type": "散点图", "variables": ["焦虑", "自尊"]},
    ]
    zip_bytes = export_all_figures_zip(specs, palette="grayscale", width_px=600, height_px=400)
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = zf.namelist()
    # 应有 2 张 PNG + 1 个说明
    assert len(names) == 3
    pngs = [n for n in names if n.endswith(".png")]
    assert len(pngs) == 2
    # 命名规范："图1_独立样本t检验_箱线图.png"
    assert any("图1" in n and "箱线图" in n for n in pngs)
    assert any("图2" in n and "散点图" in n for n in pngs)


@pytest.mark.skipif(
    importlib.util.find_spec("kaleido") is None,
    reason="kaleido not installed; smoke test skipped",
)
def test_to_paper_png_smoke(sample_fig):
    """有 kaleido 时跑一次端到端，验证返回的是非空 PNG bytes。"""
    png_bytes = to_paper_png(sample_fig, palette="grayscale", width_px=600, height_px=400)
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 1000  # PNG 头 + 内容至少 1KB
    # PNG magic header
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
