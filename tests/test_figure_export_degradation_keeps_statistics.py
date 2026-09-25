"""图形依赖（kaleido）缺失时的降级取证 — 降级只影响配图，不得吞掉统计结果。

对应信箱单 20260925-120708-0e66：
「检查 kaleido 等图形依赖缺失时是否降级而不吞掉统计结果。
 验收：有依赖和无依赖两条路径，错误信息能指导安装或改用静态表。」

本件把两条路径都钉成可执行断言：

- 无依赖路径：把 ``sys.modules["kaleido"]`` 置为 ``None``，让 ``import kaleido`` 当场失败。
  **不卸载包、不改 requirements-lock.txt**（零安装手段）。
  开头的 ``test_missing_kaleido_simulation_actually_takes_effect`` 是生效反证：
  若将来把可用性探测换成 ``find_spec`` 之类的实现，这个屏蔽手法会失效，
  该用例当场转红，而不是让后面的降级用例静默空跑。
- 有依赖路径：本机装了 kaleido 时真的渲染一次 PNG，并检查 docx / ZIP 真的落图。

统计结果面（描述统计表 / 追加表 / 结果正文 / docx 字节）在两条路径下必须一致。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import logging
import sys
import zipfile

import pandas as pd
import plotly.graph_objects as go
import pytest
from docx import Document

import src.visualization.paper_export as pe
from src.output.delivery_package import DeliverySpec, build_delivery_package
from src.output.docx_exporter import (
    ThesisMeta, build_thesis_docx, plotly_figs_to_figure_items,
)


KALEIDO_PRESENT = importlib.util.find_spec("kaleido") is not None
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@contextlib.contextmanager
def kaleido_unavailable():
    """让 `import kaleido` 真实失败（等价于未安装），不动任何已装包与锁文件。"""
    sentinel = object()
    saved = sys.modules.get("kaleido", sentinel)
    sys.modules["kaleido"] = None
    try:
        yield
    finally:
        if saved is sentinel:
            sys.modules.pop("kaleido", None)
        else:
            sys.modules["kaleido"] = saved


@pytest.fixture
def missing_kaleido():
    with kaleido_unavailable():
        yield


def _docx_specs(n: int = 2):
    return [
        (f"图{i + 1} 条件均值对比", go.Figure(go.Bar(x=["A", "B"], y=[1.0, 2.0])))
        for i in range(n)
    ]


def _desc_table() -> pd.DataFrame:
    return pd.DataFrame({
        "变量": ["社交焦虑", "自尊"],
        "M": [42.31, 28.50],
        "SD": [8.12, 5.23],
        "n": [200, 200],
    })


def _extra_tables():
    return [(
        "各组均值比较",
        pd.DataFrame({"组": ["低焦虑", "高焦虑"], "M": [38.1, 46.4], "SD": [7.0, 8.4]}),
    )]


def _figure_specs(n: int = 2):
    return [
        {
            "fig": go.Figure(go.Scatter(x=[1.0, 2.0], y=[3.0, 4.0])),
            "test_type": "independent_ttest",
            "test_name_zh": "独立样本t检验",
            "chart_type": "箱线图",
            "variables": ["焦虑"],
        }
        for _ in range(n)
    ]


RESULT_MD = (
    "### 结果\n\n"
    "独立样本 t 检验显示两组差异显著，t(198) = 5.42, p < .001, d = 0.77。"
    "相关分析 r = -.41 (p < .001)。"
)


def _docx_text(docx_bytes: bytes) -> str:
    doc = Document(io.BytesIO(docx_bytes))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def _docx_table_count(docx_bytes: bytes) -> int:
    return len(Document(io.BytesIO(docx_bytes)).tables)


def _docx_tables_text(docx_bytes: bytes) -> str:
    """只取统计表格面（正文段落会含图注，两条路径本就应有差别）。"""
    doc = Document(io.BytesIO(docx_bytes))
    parts: list[str] = []
    for table in doc.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def _docx_paragraph_count(docx_bytes: bytes) -> int:
    return len(Document(io.BytesIO(docx_bytes)).paragraphs)


def _build_thesis() -> bytes:
    return build_thesis_docx(
        ThesisMeta(title="社交焦虑与自尊的关系研究", author="张三"),
        result_md=RESULT_MD,
        descriptive_table=_desc_table(),
        extra_tables=_extra_tables(),
    )


# --------------------------------------------------------------------------- #
# 0. 生效反证 —— 屏蔽必须真的咬住，否则整件都是空跑
# --------------------------------------------------------------------------- #

def test_missing_kaleido_simulation_actually_takes_effect(missing_kaleido):
    """前提自证：置 None 后 `import kaleido` 当场 ImportError，探针读到不可用。

    这条把「patch 探针函数本身」和「依赖真的不可用」区分开：
    若探测实现换成 find_spec / 别的 import 写法，这里会先转红，
    后面的降级用例就不会假装通过。
    """
    with pytest.raises(ImportError):
        import kaleido  # noqa: F401

    assert pe._kaleido_available() is False

    with pytest.raises(pe.KaleidoMissingError):
        pe.to_paper_png(go.Figure(go.Scatter(x=[1, 2], y=[3.0, 4.0])))


def test_simulation_leaves_environment_untouched_after_exit():
    """反证的反证：上下文退出后依赖面复原，不给后续用例留全局污染。"""
    assert importlib.util.find_spec("kaleido") is not None  # 没卸载任何东西
    with kaleido_unavailable():
        assert pe._kaleido_available() is False
    assert pe._kaleido_available() is True
    assert importlib.util.find_spec("kaleido") is not None


# --------------------------------------------------------------------------- #
# 1. 有依赖路径 —— 真的出图，不是被 skip 掉就算数
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not KALEIDO_PRESENT, reason="本机未安装 kaleido，有依赖路径无从渲染")
def test_dependency_path_renders_real_png():
    """装了依赖：to_paper_png 出合法 PNG 字节。"""
    fig = go.Figure(go.Scatter(x=[1, 2, 3], y=[4.0, 5.0, 6.0]))
    png = pe.to_paper_png(fig, palette="grayscale", width_px=600, height_px=400)
    assert isinstance(png, bytes)
    assert png[:8] == PNG_MAGIC
    assert len(png) > 1000


@pytest.mark.skipif(not KALEIDO_PRESENT, reason="本机未安装 kaleido，有依赖路径无从渲染")
def test_dependency_path_docx_helper_returns_full_items():
    """有依赖时 helper 返回全部图，数量与 specs 一致。"""
    items = plotly_figs_to_figure_items(_docx_specs(2), width_px=600, height_px=400)
    assert len(items) == 2
    assert all(i.png_bytes[:8] == PNG_MAGIC for i in items)


@pytest.mark.skipif(not KALEIDO_PRESENT, reason="本机未安装 kaleido，有依赖路径无从渲染")
def test_dependency_path_delivery_zip_keeps_figure_pngs():
    """有依赖时交付包真的含 图表集/*.png（既有测试只断言 docx/pdf，没断言这条）。"""
    spec = DeliverySpec(
        thesis_docx=b"PK\x03\x04 fake docx",
        handbook_pdf=b"%PDF-1.3\nfake\n%%EOF",
        figures=_figure_specs(1),
    )
    zf = zipfile.ZipFile(io.BytesIO(build_delivery_package(spec)))
    names = zf.namelist()
    pngs = [n for n in names if n.startswith("图表集/") and n.endswith(".png")]
    assert len(pngs) == 1, names


# --------------------------------------------------------------------------- #
# 2. 无依赖路径 —— 降级只砍配图，统计结果一字不少
# --------------------------------------------------------------------------- #

def test_missing_kaleido_docx_helper_degrades_to_empty(missing_kaleido):
    """无依赖时 helper 返回空列表而不是把异常抛穿到调用方（向导据此继续出正文）。"""
    assert plotly_figs_to_figure_items(_docx_specs(3)) == []


def test_missing_kaleido_keeps_descriptive_and_extra_tables(missing_kaleido):
    """核心判据：图形降级后，描述统计表 + 追加表 + 统计正文仍在 docx 里。"""
    assert plotly_figs_to_figure_items(_docx_specs(2)) == []

    docx_bytes = build_thesis_docx(
        ThesisMeta(title="社交焦虑与自尊的关系研究", author="张三"),
        result_md=RESULT_MD,
        descriptive_table=_desc_table(),
        extra_tables=_extra_tables(),
        figures=[],
    )
    text = _docx_text(docx_bytes)

    assert _docx_table_count(docx_bytes) == 2
    for token in ("描述性统计", "各组均值比较", "42.31", "28.50", "8.12", "38.1", "46.4"):
        assert token in text, f"统计结果被降级路径吞掉：缺 {token}"

    for token in ("t(198) = 5.42", "p < .001", "d = 0.77", "r = -.41"):
        assert token in text, f"统计正文被降级路径吞掉：缺 {token}"


@pytest.mark.skipif(not KALEIDO_PRESENT, reason="两条路径互比需要有依赖侧，本机无 kaleido 时无从比较")
def test_degraded_and_normal_docx_have_identical_statistics():
    """有依赖 vs 无依赖两条路径的 docx，统计面必须逐字相同（差别只在配图）。"""
    normal_items = plotly_figs_to_figure_items(_docx_specs(2), width_px=600, height_px=400)
    assert len(normal_items) == 2
    meta = ThesisMeta(title="社交焦虑与自尊的关系研究", author="张三")
    normal = build_thesis_docx(
        meta, result_md=RESULT_MD, descriptive_table=_desc_table(),
        extra_tables=_extra_tables(), figures=normal_items,
    )

    with kaleido_unavailable():
        degraded_items = plotly_figs_to_figure_items(_docx_specs(2))
    assert degraded_items == []
    degraded = build_thesis_docx(
        meta, result_md=RESULT_MD, descriptive_table=_desc_table(),
        extra_tables=_extra_tables(), figures=degraded_items,
    )

    assert _docx_table_count(normal) == _docx_table_count(degraded) == 2
    # 统计表格面逐字相同；图注属配图面，两条路径本就应有差别
    assert _docx_tables_text(normal) == _docx_tables_text(degraded)
    for token in ("t(198) = 5.42", "r = -.41", "42.31", "描述性统计", "各组均值比较"):
        assert token in _docx_text(normal), token
        assert token in _docx_text(degraded), f"降级路径丢了 {token}"

    # 有依赖侧真的多出配图（否则这条互比是空跑）
    assert _docx_paragraph_count(normal) == _docx_paragraph_count(degraded) + 4

    # 降级侧 == 一篇「完全没配图」的文档，说明除图之外没有任何连带损失
    baseline = build_thesis_docx(
        meta, result_md=RESULT_MD, descriptive_table=_desc_table(),
        extra_tables=_extra_tables(), figures=[],
    )
    assert _docx_text(degraded) == _docx_text(baseline)


def test_missing_kaleido_delivery_package_keeps_statistics_and_guides(missing_kaleido):
    """交付包降级：docx / pdf 仍在 ZIP 里，README 说明「为什么没图」并给安装指引。"""
    thesis = _build_thesis()
    spec = DeliverySpec(
        thesis_docx=thesis,
        handbook_pdf=b"%PDF-1.3\nfake pdf body\n%%EOF",
        figures=_figure_specs(2),
        research_title="社交焦虑与自尊的关系研究",
    )
    zf = zipfile.ZipFile(io.BytesIO(build_delivery_package(spec)))
    names = zf.namelist()

    # 统计结果所在的两个文件一个都没掉
    assert "论文初稿.docx" in names, names
    assert "答辩备战手册.pdf" in names, names
    assert zf.read("论文初稿.docx") == thesis  # 字节级未被降级路径改写

    # 无 PNG 时必须在 README 里可解释，且给出安装指引
    readme = zf.read("README.txt").decode("utf-8-sig")
    assert "kaleido" in readme
    assert "pip install" in readme, readme
    assert not any(n.endswith(".png") for n in names), names


def test_missing_kaleido_error_message_gives_install_and_static_fallback(missing_kaleido):
    """错误文案要能指导「装依赖」或「改用静态/HTML 导出」，不能只报“失败了”。"""
    with pytest.raises(pe.KaleidoMissingError) as exc_info:
        pe.to_paper_png(go.Figure(go.Scatter(x=[1], y=[1.0])))
    msg = str(exc_info.value)
    assert "pip install -U kaleido" in msg, msg
    assert "HTML" in msg, msg


def test_missing_kaleido_figure_zip_falls_back_to_description_only(missing_kaleido):
    """批量导出降级：仍返回有效 ZIP，说明文件给安装指引，且不谎称“已导出 N 张”。"""
    zf = zipfile.ZipFile(io.BytesIO(pe.export_all_figures_zip(_figure_specs(2))))
    names = zf.namelist()
    assert "图表说明.txt" in names, names
    assert not any(n.endswith(".png") for n in names), names
    desc = zf.read("图表说明.txt").decode("utf-8-sig")
    assert "pip install kaleido" in desc, desc


def test_docx_helper_degradation_is_logged_not_silent(missing_kaleido, caplog):
    """降级至少留痕：helper 返回空列表时，日志得看得见原因和出路。"""
    with caplog.at_level(logging.WARNING, logger="src.output.docx_exporter"):
        assert plotly_figs_to_figure_items(_docx_specs(2)) == []
    texts = " ".join(r.getMessage() for r in caplog.records)
    assert "kaleido" in texts.lower(), texts
    assert ("pip install" in texts) or ("HTML" in texts), texts
