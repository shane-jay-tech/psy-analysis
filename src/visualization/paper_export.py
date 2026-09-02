"""论文版图表导出 — Plotly Figure → 高清 PNG（300 dpi，学术配色）。

设计目标：
- 一键把交互式 Plotly 图表转换为可直接贴论文的静态 PNG
- 支持彩色 / 灰度 / 黑白线条三种学术配色
- 中英文字体兼容（嵌入 CJK 字体名）
- kaleido 不可用时优雅降级，给出明确安装提示
"""

from __future__ import annotations

import copy
import io
import os
from pathlib import Path
from typing import Literal

import plotly.graph_objects as go

from .fonts import get_chinese_font


PaletteName = Literal["color", "grayscale", "mono"]


PAPER_PALETTES: dict[str, list[str]] = {
    "color": [
        "#1F3A93", "#C0392B", "#27AE60", "#D35400",
        "#7D3C98", "#16A085", "#2C3E50", "#B7950B",
    ],
    "grayscale": [
        "#1A1A1A", "#5A5A5A", "#8C8C8C", "#B8B8B8",
        "#2E2E2E", "#6E6E6E", "#A0A0A0", "#CECECE",
    ],
    "mono": [
        "#000000", "#000000", "#000000", "#000000",
        "#000000", "#000000", "#000000", "#000000",
    ],
}

PAPER_DASH_CYCLE = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
PAPER_MARKER_CYCLE = ["circle", "square", "diamond", "triangle-up", "x", "cross"]

DEFAULT_DPI = 300
DEFAULT_WIDTH_PX = 1800
DEFAULT_HEIGHT_PX = 1200


class KaleidoMissingError(RuntimeError):
    """kaleido 或其浏览器运行时不可用时抛出，UI 层统一友好提示。"""

    def __init__(self, detail: str = ""):
        suffix = f"\n原因：{detail}" if detail else ""
        super().__init__(
            "导出 PNG 需要 kaleido 和可用的 Chrome/Chromium。请运行：\n"
            "    pip install -U kaleido\n"
            "    kaleido_get_chrome\n"
            "也可安装 Playwright Chromium；临时无法安装时请导出 HTML。"
            f"{suffix}"
        )


def _kaleido_available() -> bool:
    try:
        import kaleido  # noqa: F401
        return True
    except ImportError:
        return False


def _find_local_chromium() -> Path | None:
    """寻找 Kaleido 可用的浏览器，优先 Chrome 与 Playwright Chromium。"""
    configured = os.environ.get("BROWSER_PATH")
    if configured:
        configured_path = Path(configured)
        if configured_path.is_file():
            return configured_path

    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        playwright_root = Path(local_app_data) / "ms-playwright"
        if playwright_root.is_dir():
            candidates.extend(
                sorted(
                    playwright_root.glob("chromium-*/chrome-win*/chrome.exe"),
                    reverse=True,
                )
            )
    return next((path for path in candidates if path.is_file()), None)


def _render_static_image(fig: go.Figure, **kwargs) -> bytes:
    """渲染静态图；为 Kaleido 设置已安装的可靠浏览器并统一错误。"""
    browser_path = _find_local_chromium()
    if browser_path is not None:
        os.environ["BROWSER_PATH"] = str(browser_path)
    try:
        return fig.to_image(**kwargs)
    except Exception as exc:
        raise KaleidoMissingError(str(exc)) from exc


def apply_paper_style(
    fig: go.Figure,
    palette: PaletteName = "grayscale",
    *,
    title_size: int = 18,
    body_size: int = 14,
) -> go.Figure:
    """把交互式图表转换为论文样式（不修改原图）。

    - 替换为学术配色
    - 字体放大到 14pt，标题 18pt
    - 背景纯白，网格淡灰，边框黑色
    - 折线/散点自动循环 dash/marker 形状（黑白印刷可辨识）
    """
    paper_fig = go.Figure(fig)

    colors = PAPER_PALETTES.get(palette, PAPER_PALETTES["grayscale"])
    font_family = get_chinese_font()

    line_idx = 0
    marker_idx = 0
    color_idx = 0

    for trace in paper_fig.data:
        ttype = getattr(trace, "type", "")

        if ttype in ("scatter", "scattergl"):
            mode = trace.mode or ""
            color = colors[color_idx % len(colors)]
            color_idx += 1

            if "lines" in mode:
                if trace.line is None:
                    trace.line = {}
                trace.line.color = color
                trace.line.dash = PAPER_DASH_CYCLE[line_idx % len(PAPER_DASH_CYCLE)]
                trace.line.width = max(trace.line.width or 2, 2)
                line_idx += 1

            if "markers" in mode:
                if trace.marker is None:
                    trace.marker = {}
                trace.marker.color = color
                trace.marker.symbol = PAPER_MARKER_CYCLE[marker_idx % len(PAPER_MARKER_CYCLE)]
                trace.marker.size = max(trace.marker.size or 8, 8)
                marker_idx += 1

        elif ttype == "bar":
            n = len(trace.x) if trace.x is not None else 1
            trace.marker.color = [colors[i % len(colors)] for i in range(n)]
            trace.marker.line = {"color": "black", "width": 1}

        elif ttype == "box":
            color = colors[color_idx % len(colors)]
            color_idx += 1
            trace.marker.color = color
            if trace.line is None:
                trace.line = {}
            trace.line.color = "black"

        elif ttype == "heatmap":
            if palette in ("grayscale", "mono"):
                trace.colorscale = "Greys"
            # color palette 保持原 RdBu_r

        elif ttype == "histogram":
            color = colors[color_idx % len(colors)]
            color_idx += 1
            trace.marker.color = color
            trace.marker.line = {"color": "black", "width": 0.5}

    paper_fig.update_layout(
        template="simple_white",
        font=dict(family=font_family, size=body_size, color="black"),
        title=dict(font=dict(family=font_family, size=title_size, color="black")),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            showline=True, linewidth=1.2, linecolor="black",
            ticks="outside", tickcolor="black", tickwidth=1,
            gridcolor="rgba(0,0,0,0.08)",
            title_font=dict(family=font_family, size=body_size, color="black"),
        ),
        yaxis=dict(
            showline=True, linewidth=1.2, linecolor="black",
            ticks="outside", tickcolor="black", tickwidth=1,
            gridcolor="rgba(0,0,0,0.08)",
            title_font=dict(family=font_family, size=body_size, color="black"),
        ),
        legend=dict(
            font=dict(family=font_family, size=body_size - 2, color="black"),
            bordercolor="black", borderwidth=0.5,
        ),
        margin=dict(l=80, r=40, t=80, b=80),
    )

    return paper_fig


def to_paper_png(
    fig: go.Figure,
    palette: PaletteName = "grayscale",
    *,
    width_px: int = DEFAULT_WIDTH_PX,
    height_px: int = DEFAULT_HEIGHT_PX,
    scale: float = 1.0,
    apply_style: bool = True,
) -> bytes:
    """把 Plotly Figure 渲染为 PNG bytes（300 dpi 等价分辨率）。

    Args:
        fig: 原始 plotly figure
        palette: "color" / "grayscale" / "mono"
        width_px / height_px: 输出像素尺寸（默认 1800×1200，对应 6×4 英寸 @ 300dpi）
        scale: 额外缩放系数（1.0 = 默认；2.0 = 双倍清晰度）
        apply_style: 是否先应用论文样式（默认 True）

    Returns:
        PNG 字节流

    Raises:
        KaleidoMissingError: kaleido 未安装
    """
    if not _kaleido_available():
        raise KaleidoMissingError()

    target = apply_paper_style(fig, palette=palette) if apply_style else copy.deepcopy(fig)

    return _render_static_image(
        target,
        format="png",
        width=width_px,
        height=height_px,
        scale=scale,
    )


def to_paper_svg(
    fig: go.Figure,
    palette: PaletteName = "grayscale",
    *,
    apply_style: bool = True,
) -> bytes:
    """SVG 版本，适合矢量编辑/Word 嵌入。"""
    if not _kaleido_available():
        raise KaleidoMissingError()

    target = apply_paper_style(fig, palette=palette) if apply_style else copy.deepcopy(fig)
    return _render_static_image(target, format="svg")


def get_palette_label(palette: PaletteName) -> str:
    """供 UI 显示用的中文标签。"""
    return {
        "color": "彩色（适合电子稿/PPT）",
        "grayscale": "灰度（适合期刊投稿/论文）",
        "mono": "纯黑（适合复印/扫描）",
    }.get(palette, palette)


# --------------------------------------------------------------------------- #
# v2.8: 批量 ZIP 导出
# --------------------------------------------------------------------------- #

def export_all_figures_zip(
    figure_specs: list,
    palette: PaletteName = "grayscale",
    *,
    width_px: int = DEFAULT_WIDTH_PX,
    height_px: int = DEFAULT_HEIGHT_PX,
) -> bytes:
    """把多张图表打包为 ZIP，附 图表说明.txt。

    Args:
        figure_specs: 列表，每项是 dict 含字段：
            - "fig": plotly Figure 对象
            - "test_type": 检验类型（用于命名，如 "independent_ttest"）
            - "test_name_zh": 中文检验名（用于命名/说明）
            - "chart_type": 图表类型（中文，如 "箱线图"）
            - "variables": 变量列表（可选，写入说明）
            - "timestamp": 生成时间戳（可选）
        palette: 配色

    Returns:
        ZIP 文件字节流。文件命名："图1_独立样本t检验_箱线图.png"。
        若 kaleido 不可用，返回的 ZIP 仅含 图表说明.txt + 错误说明。
    """
    import io as _io
    import zipfile
    from datetime import datetime

    buf = _io.BytesIO()
    desc_lines = ["心理学分析图表批量导出说明", "=" * 40, ""]

    has_kaleido = _kaleido_available()

    successes = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if not has_kaleido:
            desc_lines.append("⚠ kaleido 未安装，无法生成 PNG。")
            desc_lines.append("解决：在终端运行 `pip install kaleido` 后重试。")
            zf.writestr(
                "图表说明.txt",
                "\n".join(desc_lines).encode("utf-8-sig"),
            )
        else:
            for i, spec in enumerate(figure_specs, start=1):
                fig = spec.get("fig")
                test_name = spec.get("test_name_zh", "未知检验")
                chart_type = spec.get("chart_type", "图表")
                variables = spec.get("variables", [])
                timestamp = spec.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M"))

                safe_name = f"图{i}_{test_name}_{chart_type}"
                for ch in '<>:"/\\|?*':
                    safe_name = safe_name.replace(ch, "_")
                filename = f"{safe_name}.png"

                try:
                    png_bytes = to_paper_png(
                        fig, palette=palette,
                        width_px=width_px, height_px=height_px,
                    )
                    zf.writestr(filename, png_bytes)
                    successes += 1
                    desc_lines.append(
                        f"图{i}：{test_name} - {chart_type}\n"
                        f"  文件名：{filename}\n"
                        f"  变量：{', '.join(variables) if variables else '—'}\n"
                        f"  生成时间：{timestamp}\n"
                    )
                except Exception as e:
                    desc_lines.append(
                        f"图{i}：{test_name} - {chart_type} ❌ 生成失败：{e}\n"
                    )

            desc_lines.insert(2, f"成功导出：{successes} / {len(figure_specs)} 张")
            desc_lines.insert(3, f"配色方案：{get_palette_label(palette)}")
            desc_lines.insert(4, "")

            zf.writestr(
                "图表说明.txt",
                "\n".join(desc_lines).encode("utf-8-sig"),
            )

    return buf.getvalue()
