"""论文交付包打包 — 把 Word/PDF/图表集打包成一个 ZIP。

入口：build_delivery_package(spec) -> bytes
"""

from __future__ import annotations

import io
import zipfile
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DeliverySpec:
    """论文交付包打包规范。每个字段可选；缺失则在 ZIP 中跳过对应文件。"""

    thesis_docx: Optional[bytes] = None
    thesis_filename: str = "论文初稿.docx"

    handbook_pdf: Optional[bytes] = None
    handbook_filename: str = "答辩备战手册.pdf"
    handbook_is_focused: bool = False

    figures: List[Dict] = field(default_factory=list)
    """图表列表，每项 {fig: plotly Figure, title, chart_type, variables, test_name_zh, timestamp}"""

    figure_palette: str = "grayscale"

    research_title: str = "本科毕业论文"
    author: str = ""

    extra_notes: str = ""


def build_delivery_package(spec: DeliverySpec) -> bytes:
    """构建论文交付包 ZIP，返回字节流。

    ZIP 结构：
    - 论文初稿.docx
    - 答辩备战手册.pdf
    - 图表集/图1_xxx.png ...
    - README.txt
    """
    from src.visualization.paper_export import (
        export_all_figures_zip, _kaleido_available, to_paper_png, KaleidoMissingError,
    )

    buf = io.BytesIO()
    inventory: List[str] = []  # 用于 README

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 论文初稿
        if spec.thesis_docx:
            zf.writestr(spec.thesis_filename, spec.thesis_docx)
            inventory.append(f"📄 {spec.thesis_filename}（论文初稿，APA7 格式）")
        else:
            inventory.append("📄 论文初稿.docx（未生成 — 请在向导第 7 步先生成 Word）")

        # 答辩手册
        if spec.handbook_pdf:
            zf.writestr(spec.handbook_filename, spec.handbook_pdf)
            ver_label = "重点版" if spec.handbook_is_focused else "完整版"
            inventory.append(f"📘 {spec.handbook_filename}（{ver_label}，含笔记区与复习计划）")
        else:
            inventory.append("📘 答辩备战手册.pdf（未生成 — 请在向导第 7 步生成答辩问题后导出 PDF）")

        # 图表集
        if spec.figures:
            if not _kaleido_available():
                inventory.append(
                    "📁 图表集/（⚠ kaleido 未安装，无法生成 PNG。"
                    "请运行 pip install kaleido 后重新打包）"
                )
            else:
                fig_count = 0
                for i, fig_spec in enumerate(spec.figures, start=1):
                    fig = fig_spec.get("fig")
                    if fig is None:
                        continue
                    test_name = fig_spec.get("test_name_zh", "分析")
                    chart_type = fig_spec.get("chart_type", "图表")
                    safe_name = f"图{i}_{test_name}_{chart_type}"
                    for ch in '<>:"/\\|?*':
                        safe_name = safe_name.replace(ch, "_")
                    filename = f"图表集/{safe_name}.png"
                    try:
                        png = to_paper_png(
                            fig, palette=spec.figure_palette,
                            width_px=1500, height_px=1000,
                        )
                        zf.writestr(filename, png)
                        fig_count += 1
                    except KaleidoMissingError:
                        break
                    except Exception:
                        logger.debug("图表导出失败: %s", filename, exc_info=True)
                        continue
                inventory.append(f"📁 图表集/（共 {fig_count} 张论文版 PNG，{spec.figure_palette} 配色）")
        else:
            inventory.append("📁 图表集/（未收藏图表 — 请在分析后点击「📌 加入论文图表集」）")

        # README
        readme = _build_readme(spec, inventory)
        zf.writestr("README.txt", readme.encode("utf-8-sig"))

    return buf.getvalue()


def _build_readme(spec: DeliverySpec, inventory: List[str]) -> str:
    parts = [
        "心理学论文交付包",
        "=" * 40,
        "",
        f"研究主题：{spec.research_title}",
    ]
    if spec.author:
        parts.append(f"作者：{spec.author}")
    parts.append(f"打包时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    parts.append("生成系统：Psy Analysis v2.9")
    parts.append("")
    parts.append("文件清单：")
    parts.append("-" * 40)
    for line in inventory:
        parts.append(line)
    parts.append("")
    parts.append("使用说明：")
    parts.append("-" * 40)
    parts.append("1. 论文初稿.docx：用 Microsoft Word 2016+ 或 WPS 打开，正文已是 APA7 格式。")
    parts.append("2. 答辩备战手册.pdf：建议打印随身携带，按「考前 3 天复习计划」练习。")
    parts.append("3. 图表集/：300dpi 高清 PNG，可直接拖入 Word 文档作论文配图。")
    parts.append("4. 提交论文前，请仔细复核所有数值（系统模板可能含占位符）。")
    parts.append("")
    if spec.extra_notes:
        parts.append("作者备注：")
        parts.append("-" * 40)
        parts.append(spec.extra_notes)
        parts.append("")
    parts.append("祝答辩顺利！💪")
    return "\n".join(parts)
